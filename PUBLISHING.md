# Publishing & Distribution

This file is for maintainers. If you're a user, see [README.md](README.md).

`xiao` is agent-ready — it ships with `AGENTS.md`, `llms.txt`, a Claude Code
skill at `.claude/skills/xiao/SKILL.md`, `--json` output, and canonical exit
codes. To benefit from that work, we publish `xiao` to agent-tool registries
and community hubs so LLM agents and their users can discover it.

All per-venue submission copy lives under
[`docs/submissions/`](docs/submissions/). Each file contains the exact text,
URLs, and checklist for one venue. Shared artefacts (pitch, description,
tags) live in [`docs/submissions/_shared.md`](docs/submissions/_shared.md).

## Tier 1 — do these first

| Venue | URL | Submission | Status | Draft |
|---|---|---|---|---|
| **skills.sh** (agentskills.io) | https://skills.sh | Publish npm package — auto-indexed | — | [`skills-sh.md`](docs/submissions/skills-sh.md) |
| **llms.txt directory** | https://directory.llmstxt.cloud | Tally form (5 min) | — | [`llms-txt-directory.md`](docs/submissions/llms-txt-directory.md) |
| **Hermes Skills Hub** (Nous Research) | https://hermes-agent.nousresearch.com/docs/skills | Issue on `0xNyk/awesome-hermes-agent` | — | [`hermes.md`](docs/submissions/hermes.md) |
| **Anthropic plugin directory** | https://github.com/anthropics/claude-plugins-official | Form: `clau.de/plugin-directory-submission` | — | [`anthropic-plugin-directory.md`](docs/submissions/anthropic-plugin-directory.md) |
| **anthropics/skills cookbook** | https://github.com/anthropics/skills | GitHub PR | — | [`anthropics-skills-cookbook.md`](docs/submissions/anthropics-skills-cookbook.md) |

## Tier 2 — MCP ecosystem (requires MCP wrapper, ~1–2 h extra work)

A thin MCP server wrapper around `xiao` would expose ~10 tools (`status`,
`start`, `stop`, `dock`, `clean_room`, …). Not yet built; tracked in
[BACKLOG.md](BACKLOG.md). Once available, submit to:

| Venue | URL | Submission |
|---|---|---|
| Official MCP Registry | https://registry.modelcontextprotocol.io | `mcp-publisher` CLI (`io.github.dacrypt` namespace) |
| Smithery | https://smithery.ai | "Submit Server" |
| PulseMCP | https://www.pulsemcp.com/submit | Form (curated) |
| `wong2/awesome-mcp-servers` | https://github.com/wong2/awesome-mcp-servers | PR |
| `mcp.so` | https://mcp.so | "Submit" button |
| `VoltAgent/awesome-agent-skills` | https://github.com/VoltAgent/awesome-agent-skills | PR (needs non-zero install count first) |

## Tier 3 — Community launch (after Tier 1 is live)

- **Show HN** — title: `Show HN: xiao – control a Xiaomi Robot Vacuum via CLI, agent-ready`. Tue-Thu 9am-12pm PT.
- **Reddit**: r/LocalLLaMA, r/ClaudeAI, r/homeassistant, r/Xiaomi, r/RobotVacuums (cross-post with HN link for social proof).
- **Home Assistant forum** — "Share your Projects!" category.
- **Dev.to / Hashnode** — article angle: "Making my robot vacuum agent-ready in a weekend".

## Before submitting anywhere (checklist)

- [ ] `SKILL.md` frontmatter validates (name ≤ 64 chars lowercase, description ≤ 1024 chars, says WHAT and WHEN). Already verified 2026-04-21.
- [ ] `llms.txt` is reachable at the repo root. Already present.
- [ ] `AGENTS.md` is current. Already present.
- [ ] PyPI package `xiao` published and `pip install xiao && xiao --help` works.
- [ ] A 10-second terminal GIF showing `xiao status --json` exists (for Show HN, Reddit, Dev.to).
- [ ] Repo description on GitHub is concise and matches the 1-liner pitch.
- [ ] GitHub topics include: `xiaomi`, `roborock`, `vacuum`, `agent-tool`, `mcp`, `claude-skill`, `llms-txt`, `agents-md`.
