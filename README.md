# dev — your AI standup teammate

You open GitHub every morning. You scan your notifications. You check who's waiting on you. You write the same standup you wrote last week. You do this every single day.

**dev does all of that in 2 seconds.**

```bash
$ dev standup

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

That's it. No dashboard. No Slack bot. No manual input. Just run it and go.

---

## What dev actually does

Three commands. Nothing else.

**`dev init`** — connects to your GitHub and sets up your LLM provider. Takes about 60 seconds.

**`dev standup`** — reads your GitHub activity from yesterday and writes your standup for you. Knows what you merged, what you reviewed, what's waiting on you.

**`dev prs`** — shows your open PRs ranked by what actually needs attention right now. Not by date. By what will hurt you if you ignore it.

```bash
$ dev prs

─────────────────────────────────────
  NEEDS ATTENTION NOW

  🔴 PR #67 — auth middleware refactor
     Priya is waiting on your review
     Open 72hrs — your team ships bugs
     on auth PRs left this long
     → Review this first (~23 min)

  🟡 PR #51 — rate limiter
     Your PR — no reviewers assigned yet
     → Assign someone today

  🟢 PR #69 — update docs
     1 approval, low risk, ready to merge
     → Merge when you get a moment
─────────────────────────────────────
```

---

## Works however you want

Run it on Groq and get responses in under 2 seconds. Run it on Ollama and keep everything on your machine. Switch anytime with a flag.

```bash
# cloud — fast, free tier available
$ dev standup --provider groq

# local — nothing leaves your machine  
$ dev standup --provider ollama

# set your default once during init
# never think about it again
```

Supported providers:
- **Groq** — fastest, free tier, recommended for most people
- **OpenAI** — if you already have a key
- **Ollama** — fully local, needs Ollama running
- **LM Studio** — fully local, needs LM Studio running

---

## Installation

```bash
pip install dev-agent
dev init
```

That's the whole install. No Docker. No Postgres. No config files to edit manually. `dev init` walks you through everything — GitHub token, LLM provider, done.

**Requirements:**
- Python 3.10+
- A GitHub personal access token (scopes: `repo`, `read:user`)
- One of the providers above

---

## Setup walkthrough

```bash
$ dev init

Welcome. Let's get you set up.

GitHub token: ghp_...
✓ Connected as rahuldev

Choose your provider:
  1. groq      (cloud, ~1s, free tier)
  2. openai    (cloud, ~2s, paid)
  3. ollama    (local, speed depends on hardware)
  4. lmstudio  (local, speed depends on hardware)

> 1

Groq API key: gsk_...
✓ Connected. Response time: 0.8s

Setup complete.
Run: dev standup
```

---

## Team usage

Everyone on your team installs dev locally and points it at the same GitHub org. That's it — no shared server, no accounts to manage.

```bash
# each person runs this once
$ dev init
GitHub org: your-team-name

# now dev prs shows the whole team's PRs
# and highlights what each person specifically needs to do
```

dev doesn't need a backend to understand your team. Your GitHub org is already the shared source of truth. dev just reads it intelligently.

---

## Privacy

If you run Ollama or LM Studio, nothing leaves your machine. Your GitHub data stays local, your standup is generated locally, nothing is sent to any third-party AI service.

If you run Groq or OpenAI, your GitHub activity summary is sent to their API to generate the standup. Same as using ChatGPT to write something — just faster and automatic.

---

## Why not just use GitHub's built-in tools?

GitHub shows you everything. dev tells you what matters.

There's a difference between seeing 12 open PRs and knowing that PR #67 is the one that will bite you if you don't look at it today. dev learns your team's patterns over time and gets better at that distinction every week.

---

## Why not just use a Slack standup bot?

Slack bots ask you to fill in what you did. dev reads what you actually did and writes it for you. You don't type anything.

---

## Roadmap

**Now (v1)**
- `dev init`, `dev standup`, `dev prs`
- Groq, OpenAI, Ollama, LM Studio support
- PR risk scoring with visible reasoning
- Local SQLite — zero infrastructure

**Later (v2)**
- `dev focus` — single most important thing to do right now
- Pattern learning that improves over 30 days
- Optional shared team backend for collective intelligence
- Linear and Jira integration

---

## Contributing

Issues and PRs welcome. If something doesn't work, open an issue with your OS, Python version, and provider — that's usually enough to debug it fast.

---

## Built by

[your name] — built this during a focused engineering year after getting frustrated writing the same standup every morning.

If it saves you time, star it. If it doesn't work, tell me why.
