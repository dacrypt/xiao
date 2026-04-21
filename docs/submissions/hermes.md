# Hermes Agent Skills Hub (Nous Research)

**URL:** https://hermes-agent.nousresearch.com/docs/skills
**Submission:** New issue on https://github.com/0xNyk/awesome-hermes-agent
**Mechanism:** GitHub issue using the "Recommend a new resource here" template.
**Approval:** Manual, curated — maintainer reviews for quality and live maintenance.

## Issue title

> Add `xiao` — Xiaomi Robot Vacuum agent-ready skill

## Issue body (paste-ready)

```markdown
## Skill

**Name:** `xiao`
**Repo:** https://github.com/dacrypt/xiao
**License:** MIT
**Format:** agentskills.io / SKILL.md (see `.claude/skills/xiao/SKILL.md`)

## What it does

`xiao` is an open-source Python CLI that lets LLM agents control a Xiaomi
Robot Vacuum X20+ (`xiaomi.vacuum.c102gl`) via the Xiaomi Cloud API. It
exposes full vacuum control (start, stop, dock, room/zone cleaning, base
station, settings, consumables) as a subprocess any agent can exec.

## Why it fits the Hermes Skills Hub

- Ships an **agentskills.io-compliant `SKILL.md`** with a complete
  description + when-to-trigger section.
- Comes with **`AGENTS.md`** (cross-tool canonical reference) and
  **`llms.txt`** for zero-config agent integration.
- Machine-readable contract: `--json` flag on read commands, canonical exit
  codes (`2 = not configured`, `77 = auth failed`), explicit error-recovery
  protocol for autonomous retry.
- Works across Claude Code, Codex CLI, Cursor, Aider, Gemini CLI, Copilot,
  and (by design) Hermes Agent.
- Tested: CI green on Python 3.12 and 3.13 (ruff + mypy + pytest).

## Install & verify

```bash
pip install xiao-cli
playwright install chromium
xiao --help
xiao status --json  # emits parseable JSON
```

## Category

Home automation / IoT / agent tool.

## Maintenance

Actively maintained — see recent CHANGELOG.md and PR history. Happy to
respond to issues in https://github.com/dacrypt/xiao/issues.
```

## Why this venue

Hermes is a curated skills hub with a technically sophisticated audience
(Nous Research community). Low friction to submit because the
agentskills.io compliance is already done via our existing `SKILL.md`.
