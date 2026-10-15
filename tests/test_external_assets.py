"""v7.6 外部素材模式单元测试。

覆盖：
- ``core/providers.py`` 注册表（get_provider 回退 / list / has_capability / render_prompt / provider_public）
- ``web.routes.video_routes._resolve_scene_target`` 导入映射
- ``utils.video.normalize_external_video`` / ``probe_media``、``utils.image.normalize_external_image``
- ``BasePipeline._keeps_video_audio``
- ``POST /api/tasks/{id}/artifacts/import`` + ``GET /api/tasks/{id}/artifacts/probe``（TestClient 端到端）

写路径隔离：通过 ``AGNES_REGRESSION_WORKING_DIR`` 环境变量把工作区指向 tmp_path。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import providers
from core.task_manager import TaskManager
from models.task import (
    AudioConfig,
    CreativeVideoTask,
    ManualConfig,
    SceneTask,
    SubtitleConfig,
)
from utils.image import normalize_external_image
from utils.video import normalize_external_video, probe_media
from web.routes import utility_routes, video_routes

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_regression", "assets")
_FIXTURE_VIDEO = os.path.join(_ASSETS, "test_video_5s.mp4")
_FIXTURE_IMAGE = os.path.join(_ASSETS, "test_image.png")


# ═══════════════════════════════════════════════
# core/providers.py
# ═══════════════════════════════════════════════

def test_provider_registry_has_jimeng_only():
    ids = [p.id for p in providers.list_providers()]
    assert ids == ["jimeng"]
    assert providers.DEFAULT_PROVIDER == "jimeng"


def test_get_provider_falls_back_to_default():
    assert providers.get_provider("jimeng").id == "jimeng"
    # 非法 / 空 → 回退默认（设计 §四）
    assert providers.get_provider("bogus").id == "jimeng"
    assert providers.get_provider("").id == "jimeng"


def test_jimeng_capabilities_and_prompts():
    p = providers.get_provider("jimeng")
    for cap in ("native_audio", "duration_control", "subtitle_export", "image_gen"):
        assert providers.has_capability("jimeng", cap)
    # 检查点提示词覆盖 scenes / references / videos / subtitle
    for cp in ("scenes", "references", "videos", "subtitle"):
        assert cp in p.checkpoint_prompts


def test_render_prompt_fills_placeholders():
    prompt = providers.render_prompt(
        "jimeng", "videos", "/tmp/taskdir",
        {"scene_count": 3, "total_duration": 15},
    )
    assert "/tmp/taskdir" in prompt
    assert "<任务目录>" not in prompt
    # 未定义的检查点 → 空串
    assert providers.render_prompt("jimeng", "final", "/tmp") == ""


def test_provider_public_excludes_prompt_templates():
    pub = providers.provider_public("jimeng")
    assert pub["id"] == "jimeng"
    assert "checkpoint_prompts" not in pub
    with_prompts = providers.provider_public("jimeng", with_prompts=True)
    assert "checkpoint_prompts" in with_prompts


# ═══════════════════════════════════════════════
# _resolve_scene_target 映射
# ═══════════════════════════════════════════════

def test_resolve_scene_target_mapping():
    r = video_routes._resolve_scene_target
    # 文件名数字 N → scene_{N-1}
    assert r("creative", "video", {}, "scene_1.mp4", 0) == os.path.join("scene_0", "video.mp4")
    # 文件名无数字（去扩展名后）→ 按上传顺序
    assert r("creative", "video", {}, "movie.mp4", 2) == os.path.join("scene_2", "video.mp4")
    # scene_map 显式指定
    assert r("creative", "video", {"1": "scene_2"}, "a.mp4", 0) == os.path.join("scene_2", "video.mp4")
    # 稿件 → para_ 前缀
    assert r("manuscript", "video", {}, "p1.mp4", 0) == os.path.join("para_0", "video.mp4")
    # 图片 → ref.png
    assert r("poetry", "image", {}, "2.png", 1) == os.path.join("scene_1", "ref.png")
    # anchor 无逐场景目录
    assert r("anchor", "video", {}, "x.mp4", 0) == "clip/clip.mp4"
    assert r("anchor", "image", {}, "x.png", 0) == "anchor.png"


# ═══════════════════════════════════════════════
# 归一化 + 探针（依赖 ffmpeg / ffprobe，可用则跑）
# ═══════════════════════════════════════════════

def _ffmpeg_available() -> bool:
    from core.compositor.ffmpeg_tool import resolve_binary

    return bool(resolve_binary("ffmpeg"))


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg 不可用")
def test_normalize_external_video_and_probe(tmp_path):
    dst = str(tmp_path / "scene_0" / "video.mp4")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    normalize_external_video(_FIXTURE_VIDEO, dst, 768, 1152)
    assert os.path.exists(dst)

    info = probe_media(dst)
    assert info["duration"] and info["duration"] > 0
    assert info["width"] == 768 and info["height"] == 1152
    assert info["fps"] and info["fps"] > 0
    assert info["vcodec"] == "h264"


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg 不可用")
def test_normalize_external_image_and_probe(tmp_path):
    dst = str(tmp_path / "scene_0" / "ref.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    normalize_external_image(_FIXTURE_IMAGE, dst, 768, 1152)
    assert os.path.exists(dst)
    from PIL import Image

    with Image.open(dst) as img:
        assert img.size == (768, 1152)


def test_probe_media_missing_file(tmp_path):
    info = probe_media(str(tmp_path / "nope.mp4"))
    assert info["duration"] == 0.0
    assert info["has_audio"] is False


# ═══════════════════════════════════════════════
# BasePipeline._keeps_video_audio
# ═══════════════════════════════════════════════

class _P:
    """最小鸭子类型：仅提供 _state。"""

    def __init__(self, state):
        self._state = state


def _creative_state(execution_mode="external", audio_source="video"):
    return CreativeVideoTask(
        task_id="ext000000001",
        idea="x",
        scene_count=2,
        scene_durations=[5, 5],
        duration_source="manual",
        audio_config=AudioConfig(enabled=False),
        subtitle_config=SubtitleConfig(enabled=True),
        manual_config=ManualConfig(
            enabled=True,
            pause_points=["videos"],
            execution_mode=execution_mode,
            provider="jimeng",
            audio_source=audio_source,
        ),
    )


def test_keeps_video_audio_flag():
    from core.pipelines import BasePipeline

    assert BasePipeline._keeps_video_audio(_P(_creative_state())) is True
    assert BasePipeline._keeps_video_audio(_P(_creative_state(audio_source="project"))) is False
    assert BasePipeline._keeps_video_audio(_P(_creative_state(execution_mode="manual"))) is False
    # 无 _state（测试替身）不应抛异常
    assert BasePipeline._keeps_video_audio(object()) is False


# ═══════════════════════════════════════════════
# 导入 / 探针端点（端到端）
# ═══════════════════════════════════════════════

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AGNES_REGRESSION_WORKING_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(utility_routes.router)
    app.include_router(video_routes.router)
    return TestClient(app)


def _seed_creative_task(task_id="exttask00001", execution_mode="external"):
    """在工作区落一个 creative 任务（external 模式，2 场景）。"""
    state = CreativeVideoTask(
        task_id=task_id,
        idea="x",
        video_width=768,
        video_height=1152,
        scene_count=2,
        scene_durations=[5, 5],
        duration_source="manual",
        audio_config=AudioConfig(enabled=False),
        subtitle_config=SubtitleConfig(enabled=True),
        manual_config=ManualConfig(
            enabled=True,
            pause_points=["videos"],
            execution_mode=execution_mode,
            provider="jimeng",
            audio_source="video",
        ),
    )
    state.scenes = [SceneTask(index=i) for i in range(2)]
    TaskManager(task_id, dir_name=task_id).create(state)
    return task_id


def test_get_providers_endpoint(client):
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert [p["id"] for p in body["providers"]] == ["jimeng"]
    assert "checkpoint_prompts" not in body["providers"][0]


def test_import_kind_validation(client):
    tid = _seed_creative_task()
    resp = client.post(
        f"/api/tasks/{tid}/artifacts/import",
        data={"kind": "audio"},
        files={"files": ("a.mp4", b"x", "video/mp4")},
    )
    assert resp.status_code == 422


def test_import_scene_map_validation(client):
    tid = _seed_creative_task()
    resp = client.post(
        f"/api/tasks/{tid}/artifacts/import",
        data={"kind": "video", "scene_map": "not-json"},
        files={"files": ("a.mp4", b"x", "video/mp4")},
    )
    assert resp.status_code == 422


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg 不可用")
def test_import_video_end_to_end(client):
    tid = _seed_creative_task()
    with open(_FIXTURE_VIDEO, "rb") as f:
        content = f.read()
    resp = client.post(
        f"/api/tasks/{tid}/artifacts/import",
        data={"kind": "video"},
        files=[
            ("files", ("scene_1.mp4", content, "video/mp4")),
            ("files", ("scene_2.mp4", content, "video/mp4")),
        ],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True and body["imported"] == 2 and body["failed"] == 0
    targets = [r["target"] for r in body["results"]]
    assert targets == [os.path.join("scene_0", "video.mp4"), os.path.join("scene_1", "video.mp4")]
    for r in body["results"]:
        assert r["probe"]["width"] == 768 and r["probe"]["height"] == 1152

    # 落盘校验 + 探针端点回显
    task_dir = os.path.join(os.environ["AGNES_REGRESSION_WORKING_DIR"], tid)
    assert os.path.exists(os.path.join(task_dir, "scene_0", "video.mp4"))
    probe = client.get(
        f"/api/tasks/{tid}/artifacts/probe", params={"relpath": "scene_0/video.mp4"},
    )
    assert probe.status_code == 200
    assert probe.json()["width"] == 768


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg 不可用")
def test_import_image_registers_scene_reference(client):
    tid = _seed_creative_task()
    with open(_FIXTURE_IMAGE, "rb") as f:
        content = f.read()
    resp = client.post(
        f"/api/tasks/{tid}/artifacts/import",
        data={"kind": "image"},
        files=[("files", ("ref.png", content, "image/png"))],
    )
    assert resp.status_code == 200, resp.text
    task_dir = os.path.join(os.environ["AGNES_REGRESSION_WORKING_DIR"], tid)
    assert os.path.exists(os.path.join(task_dir, "scene_0", "ref.png"))
    state = TaskManager(tid, dir_name=tid).load()
    assert state.scene_reference_images and state.scene_reference_images[0].endswith(
        os.path.join("scene_0", "ref.png")
    )


def test_probe_endpoint_path_traversal_denied(client):
    tid = _seed_creative_task()
    resp = client.get(
        f"/api/tasks/{tid}/artifacts/probe", params={"relpath": "../task_state.json"},
    )
    assert resp.status_code == 404


def test_external_hint_on_checkpoint(client):
    tid = _seed_creative_task()
    resp = client.get(f"/api/tasks/{tid}/checkpoints/videos")
    assert resp.status_code == 200
    hint = resp.json()["external_hint"]
    assert hint is not None
    assert hint["provider"]["id"] == "jimeng"
    assert hint["prompt"]
