# gitdar

You open GitHub every morning. You scan your notifications. You write the same standup you wrote last week.

**gitdar does all of that in seconds.**

```bash
$ gitdar standup

─────────────────────────────────────
  YESTERDAY
  ✓ Merged PR #42 — auth refactor
  ✓ Reviewed PR #39 — payments (approved)
  ✓ Opened PR #51 — rate limiter

  TODAY
  → PR #51 needs reviewers before it can merge
  → PR #67 from Priya is waiting on your review

  BLOCKED
  → Nothing blocking you
─────────────────────────────────────
Generated in 1.4s. Copy to clipboard? (y/n)
```

No dashboard. No Slack bot. No manual input. Run it and go.

---

## What gitdar does

Three commands. Nothing else.

**`gitdar init`** — connects to GitHub and sets up your AI provider. Takes about 60 seconds.

**`gitdar standup`** — reads your GitHub activity from yesterday and writes your standup for you.

**`gitdar prs`** — shows your open PRs ranked by what actually needs attention right now.

```bash
$ gitdar prs

─────────────────────────────────────
  NEEDS ATTENTION NOW

  🔴 PR #67 — auth middleware refactor
     Priya is waiting on your review
     Open 72hrs — needs attention
     → Review this first

  🟡 PR #51 — rate limiter
     Your PR — no reviewers assigned yet
     → Assign someone today

  🟢 PR #69 — update docs
     1 approval, low risk, ready to merge
     → Merge when you get a moment
─────────────────────────────────────
```

---

## Installation

```bash
pip install gitdar
gitdar init
```

No Docker. No Postgres. No config files to edit manually.

**Requirements:**
- Python 3.10+
- A GitHub personal access token (scopes: `repo`, `read:user`)
- LM Studio running locally (v1) — download at lmstudio.ai

---

## Setup

```bash
$ gitdar init

Welcome to gitdar setup.

Choose your provider:
  1. LM Studio (local — nothing leaves your machine)

> 1

✓ LM Studio server is running
✓ Model loaded: phi-3-mini

GitHub token: ghp_...
✓ Connected as rahuldev

Setup complete.
Run: gitdar standup
```

---

## Privacy

gitdar runs entirely on your machine using LM Studio.
Your GitHub activity never leaves your computer.
No cloud API. No usage tracking. Nothing.

---

## Roadmap

**v1 — now**
- `gitdar init`, `gitdar standup`, `gitdar prs`
- LM Studio support (fully local)
- PR risk scoring with visible reasoning
- Local SQLite — zero infrastructure

**v2 — later**
- Groq, OpenAI, Ollama provider support
- Pattern learning that improves over 30 days
- `gitdar focus` — single most important thing right now
- Team standup aggregation

---

## Contributing

Issues and PRs welcome. If something doesn't work, open an issue with your OS, Python version, and LM Studio version.

---

## Built by

Built during an intensive AI engineering learning year.
If it saves you time, star it.