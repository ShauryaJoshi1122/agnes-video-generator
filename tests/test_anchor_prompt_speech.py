"""Regression tests for visible speaking motion in digital-anchor prompts."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.screenwriter import Screenwriter


def test_anchor_loop_prompt_requests_visible_speech(monkeypatch):
    """The post-stitch clip must not instruct the video model to freeze the mouth."""
    writer = object.__new__(Screenwriter)
    writer.language = "en"
    captured = {}

    def fake_chat(system_prompt, user_prompt):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return "The anchor speaks naturally with gentle, continuous mouth movement."

    monkeypatch.setattr(writer, "_chat", fake_chat)

    result = writer.generate_anchor_smooth_loop_prompt(
        anchor_prompt="A professional news anchor facing the camera."
    )

    assert result
    assert "continuous, clearly visible natural speaking motion" in captured["system_prompt"]
    assert "Mouth should have near-zero movement" not in captured["system_prompt"]
    assert "audio is added afterward" in captured["system_prompt"]
    assert "A professional news anchor facing the camera." in captured["user_prompt"]
