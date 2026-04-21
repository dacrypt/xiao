# Anthropic `claude-plugins-official` directory

**URL:** https://github.com/anthropics/claude-plugins-official
**Submission flow:** in-app via Claude — try `claude.ai/settings/plugins/submit` or `platform.claude.com/plugins/submit`. The short URL `clau.de/plugin-directory-submission` redirects to the current docs (`code.claude.com/docs/en/plugins#submit-your-plugin-to-the-official-marketplace`) — **check docs first** as the submission path may have moved since this draft was written (2026-04-21).
**Mechanism:** In-app submission form; manually reviewed by Anthropic for quality and security.
**Approval:** Curated, 1–2 week review.
**Why it matters:** Highest-prestige Claude-specific listing; appears in Claude Code's built-in marketplace UI.

## Form answers (paste-ready)

These are the answers to fill into the submission form.

### Plugin name
```
xiao
```

### One-line description (≤120 chars)
```
Control a Xiaomi Robot Vacuum X20+ via the `xiao` CLI — agent-ready with AGENTS.md, llms.txt, SKILL.md, --json output.
```

### Long description
```
`xiao` is an open-source Python CLI that lets Claude (and any other LLM
agent) control a Xiaomi / Roborock X20+ robot vacuum end to end: start a
clean, send it home, read battery, manage rooms and zones, set fan/water
levels, and recover from token expiry autonomously. It was built CLI-first
specifically so agents can drive it as a subprocess.

The repo ships with a ready-to-use Claude Code skill at
`.claude/skills/xiao/SKILL.md` (agentskills.io format), a cross-tool
`AGENTS.md` canonical reference, an `llms.txt` index, `--json` output on
read commands for deterministic parsing, and canonical exit codes (`2 =
not configured`, `77 = auth failed`) so agents can dispatch retries without
parsing stderr. MIT licensed. Tested against `xiaomi.vacuum.c102gl` on
Xiaomi Cloud as of 2024.
```

### Repository URL
```
https://github.com/dacrypt/xiao
```

### Skill / plugin path in repo
```
.claude/skills/xiao/SKILL.md
```

### Categories / tags
```
home-automation, iot, cli, agent-tool, xiaomi, roborock, vacuum, smart-home
```

### License
```
MIT
```

### Maintainer contact
```
<fill in your GitHub email / display name>
```

### Installation command
```
pip install xiao && playwright install chromium
```

### Verification command
```
xiao --help
```

### Sample agent prompt
```
"Clean the living room in turbo mode" → agent runs `xiao map rooms` → finds ID → `xiao clean -r <id> --speed turbo`.
```

## Before submitting

- [ ] Make sure the GitHub repo is public and has a clear README (done).
- [ ] Make sure `LICENSE` file is present (done — MIT).
- [ ] Confirm `pip install xiao` actually works from a fresh environment.
- [ ] Have a 1-minute screen recording ready in case review asks for a demo.
