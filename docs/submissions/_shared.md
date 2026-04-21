# Shared submission artefacts

Copy from here; don't rewrite per venue.

## Canonical 1-liner (use as repo description, HN title suffix, tagline)

> `xiao` is an open-source Python CLI that lets LLM agents control a Xiaomi Robot Vacuum X20+ (`xiaomi.vacuum.c102gl`). Agent-ready: ships with `AGENTS.md`, `llms.txt`, `SKILL.md`, `--json` output, and canonical exit codes.

## 2-paragraph description (use for Hermes issue, Anthropic form, Dev.to intro)

> `xiao` controls a Xiaomi / Roborock X20+ robot vacuum via the Xiaomi Cloud API (RC4-signed MIoT calls). It was built specifically so LLM agents — Claude, OpenClaw, Cursor, Aider, Codex, Gemini CLI — can drive the vacuum end to end: start a clean, send it to dock, read battery, report consumable life, set fan/water levels, manage zones and rooms, and recover from token expiry autonomously. The CLI is first-class: the dashboard and REST API are thin layers over the same core.
>
> What makes `xiao` different from typical smart-home CLIs is the agent-ready packaging. The repo ships an `AGENTS.md` (cross-tool canonical reference following agents.md spec), an `llms.txt` (per llmstxt.org), a Claude Code skill at `.claude/skills/xiao/SKILL.md` (agentskills.io format), `--json` output on read commands for deterministic parsing, and a small set of canonical exit codes (`2 = not configured`, `77 = auth failed`) so agents can dispatch retries without parsing stderr. Installation is `pip install xiao-cli` + `playwright install chromium`. MIT-licensed, tested against vacuum model `xiaomi.vacuum.c102gl` on Xiaomi Cloud as of 2024. Repo: https://github.com/dacrypt/xiao.

## Pitch bullets (use for forms that want feature lists)

- Full vacuum control: start, stop, pause, dock, find, room cleaning, zone cleaning, spot cleaning.
- Base-station controls: mop wash, dry, dust collect, tray eject.
- Settings: fan speed, water level, volume, Do-Not-Disturb window.
- Consumable tracking (brush / filter / mop pad with remaining life %).
- Persistent-Chromium-over-CDP token refresh — no captcha/2FA on every token expiry.
- Glassmorphism web dashboard (`xiao web`) with REST API.
- Machine-readable contract: `--json` flag, exit codes, intent-mapping table.

## Category tags (use where tag lists are accepted)

`xiaomi`, `roborock`, `vacuum`, `robot-vacuum`, `miot`, `cli`, `python`, `home-automation`, `smart-home`, `iot`, `agent-tool`, `llm-tool`, `mcp`, `claude-skill`, `agents-md`, `llms-txt`.

## URLs

- Repo: https://github.com/dacrypt/xiao
- PyPI: https://pypi.org/project/xiao-cli/
- Issues: https://github.com/dacrypt/xiao/issues
- Canonical agent guide: https://github.com/dacrypt/xiao/blob/main/AGENTS.md
- Skill definition: https://github.com/dacrypt/xiao/blob/main/.claude/skills/xiao/SKILL.md
- `llms.txt`: https://raw.githubusercontent.com/dacrypt/xiao/main/llms.txt

## Demo script (for GIF / screenshot)

Record a ~10s terminal clip running (in order):

```bash
xiao status
xiao status --json
xiao consumables --json
```

Show the Rich panel for the first, then the clean JSON output for the next
two. No sensitive data appears in any of them (state / battery / fan speed /
consumable %).
