# 🤖 Let an AI Agent Operate This Project

> This document is the authoritative guide for driving Agnes Video Generator with a coding agent.
> The website guide and the wiki page about agent usage both summarize this page — when they
> disagree with it, this page wins.

Agnes Video Generator was built to be operated by an AI coding assistant. You install one skill set,
then you describe the result you want instead of running commands:

> "Make a 90-second poetry video from 'Quiet Night Thought' and add narration."

That is the whole shape of it. The rest of this page is the install step, the three skills behind it,
and what to do when you would rather not use an agent at all.

---

## 1. Install once

The skills are plain directories plus small scripts — no service code, and no credentials ever pass
through them. Clone them, then hand the directory to your agent:

```bash
git clone https://github.com/lcy362/agnes-video-generator-skills.git
npx flint-skills-hub      # opens the local UI on http://localhost:8787
# Sources → add the cloned directory; flint reads the skills from its skills/ subdirectory
```

[**flint**](https://github.com/lcy362/flint) is a local-first, open-source skills manager. It deploys
the skills into any agent directory (Claude Code, Cursor, Codex, TRAE and more) by symlink or copy,
and it works on **local** sources only — it never clones anything for you. Local-only: no cloud, no
account, no telemetry. The skills stay plain directories on your disk, so they keep working even if
you stop using flint. **[Star flint on GitHub ⭐](https://github.com/lcy362/flint)**

No flint? Copy them in by hand:

```bash
git clone https://github.com/lcy362/agnes-video-generator-skills.git /tmp/agnes-skills
cp -R /tmp/agnes-skills/skills/* .agents/skills/     # any agent that reads .agents/skills
```

### The skill installs the service too

You do **not** need this repository cloned first. The `agnes-video-usage` skill runs
`scripts/bootstrap.py install`, which:

- installs the service under `~/.agnes-video` (override with `AGNES_HOME`),
- keeps its own virtualenv there, and re-runs `pip` only when requirements change,
- starts the service on `localhost:8765` and verifies it through the real endpoints,
- stores config, workspace and finished videos in that same data root.

Nothing is written into your current project, and the next run installs nothing again.

---

## 2. Then ask for outcomes

Once the skills are in front of your agent, stop writing commands and state the goal:

> Make a creative long video about the Voyager probes, with narration and subtitles.

> My task `4de1bcd26fda` failed — find out why and tell me if it is worth fixing.

> The portrait video came out sideways. Diagnose it and fix the configuration.

> Take my finished task, improve the storyboard prompts, and regenerate only the affected scenes.

The agent picks the matching skill, deploys or reuses the service, submits the task, reports progress,
and tells you where the file landed.

---

## 3. What the three skills cover

| Skill | Use it when you want to |
|-------|-------------------------|
| **`agnes-video-usage`** | Go from nothing to finished videos: install and start the service, configure the key, pick among the six task types, submit and watch a task, and edit artifacts at Manual Mode checkpoints |
| **`agnes-video-troubleshoot`** | Work out why a run failed: queue saturation, `401` domain mismatch, timeouts, wrong resolution, a sideways portrait video, or subtitles that broke after a resume — and decide whether it is configuration, upstream capacity, or something worth fixing |
| **`agnes-video-contrib`** | Change the project's code and get the PR through CI: English commits, the frontend rebuild rule, i18n, tests and the large-version regression |

Each skill is a decision tree plus small scripts: `agnes_task.py` (create / poll / inspect a task),
`verify_deploy.sh` (deployment checklist), `diagnose_task.py` (evidence collection), `check_media.py`
(resolution and orientation), `preflight.sh` (local CI gate).

Repository: [**lcy362/agnes-video-generator-skills**](https://github.com/lcy362/agnes-video-generator-skills)

---

## 4. Where agents help most: Manual Mode

Manual Mode pauses a run at a checkpoint and lets the agent change the artifacts before continuing.
The agent reads the task's `manifest.json`, edits the file in place, previews which downstream steps
will re-run, and approves — so "polish the narration" or "fix the subtitles" becomes one job instead
of a copy-paste round trip.

Details: [Manual Mode Guide](manual_mode_guide.md).

---

## 5. If you would rather not use an agent

| You want | Use |
|----------|-----|
| A video right now, nothing installed | [Studio](https://video.lichuanyang.top/studio) — runs in the browser |
| Full features, local data | [Getting Started](getting-started.md) — Docker or `./start.sh` |
| To change this project's code yourself | [`AGENTS.md`](../../AGENTS.md) — conventions, verification, release workflow |

The agent route exists for people who would rather describe an outcome than run commands — not
because the Web UI is second-class.

---

## See also

- [Getting Started](getting-started.md) — Option D is this page's shortest form, kept in sync with it
- [Usage Guide](usage.md) — modes, checkpoints, configuration
- [Manual Mode Guide](manual_mode_guide.md) — checkpoints and the external-agent protocol
- [API Reference](api.md) — the endpoints an agent drives
- [FAQ](faq.md) — including "how do I keep the skills in sync across agents?"
