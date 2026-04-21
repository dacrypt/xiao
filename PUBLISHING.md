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

## Automated release flow

`xiao` uses **[release-please](https://github.com/googleapis/release-please)**
+ **PyPI OIDC trusted publishing** so releases, changelogs, and PyPI uploads
happen with zero manual steps.

### How it works

1. You merge commits to `main` using [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, `refactor:`, `perf:` …).
2. [`.github/workflows/release-please.yml`](.github/workflows/release-please.yml)
   runs on every push and keeps an open **release PR** that accumulates the
   pending changelog and the next version bump in `pyproject.toml`.
3. When you merge that release PR:
   - It creates a `vX.Y.Z` tag.
   - It creates a GitHub Release with release notes.
   - [`.github/workflows/publish.yml`](.github/workflows/publish.yml) fires on
     `release: published`, runs `uv build`, and uploads to PyPI via OIDC
     (no API token stored in the repo).

### Bump rules

| Commit type            | Bump        |
|------------------------|-------------|
| `feat:`                | minor       |
| `fix:`, `perf:`, `refactor:`, `revert:` | patch       |
| Footer `BREAKING CHANGE:` or `feat!:` | major       |
| `docs:`, `chore:`, `ci:`, `test:`, `style:` | no release  |

Version state lives in [`.release-please-manifest.json`](.release-please-manifest.json);
changelog sections are configured in [`release-please-config.json`](release-please-config.json).

### One-time PyPI setup (already required for first automated release)

On [pypi.org/manage/project/xiao/settings/publishing/](https://pypi.org/manage/project/xiao/settings/publishing/),
add a **Trusted Publisher** with:

- Owner: `dacrypt`
- Repository name: `xiao`
- Workflow name: `publish.yml`
- Environment name: `pypi`

Also create a GitHub environment named `pypi` (Settings → Environments) with no
required reviewers — the workflow references it for the OIDC claim.

### Manual release (fallback)

If release-please is unavailable, bump `version` in `pyproject.toml`, update
`CHANGELOG.md`, tag, and publish manually:

```bash
uv build
uv publish    # requires PYPI_TOKEN env var (not used by CI)
```


## Tier 1 — status

| Venue | URL | Submission | Status | Draft |
|---|---|---|---|---|
| **skills.sh** (agentskills.io) | https://skills.sh | Publish npm package — auto-indexed | ✅ **published** — [`@dacrypt/xiao-skill@0.1.0`](https://www.npmjs.com/package/@dacrypt/xiao-skill) on npm (2026-04-21); skills.sh indexation typically within 24h | [`skills-sh.md`](docs/submissions/skills-sh.md) |
| **llms.txt directory** | https://directory.llmstxt.cloud | Tally form (5 min) | ⏳ **user action:** submit https://tally.so/r/wAydjB (needs your email) | [`llms-txt-directory.md`](docs/submissions/llms-txt-directory.md) |
| **Hermes Skills Hub** (Nous Research) | https://hermes-agent.nousresearch.com/docs/skills | Issue on `0xNyk/awesome-hermes-agent` | ✅ **submitted** — [issue #38](https://github.com/0xNyk/awesome-hermes-agent/issues/38) | [`hermes.md`](docs/submissions/hermes.md) |
| **Anthropic plugin directory** | https://github.com/anthropics/claude-plugins-official | In-app form at [claude.ai/settings/plugins/submit](https://claude.ai/settings/plugins/submit) | ⏳ **user action:** repo now has `.claude-plugin/plugin.json` + `skills/xiao/` (required by Anthropic). Submit in-app using paste-ready answers. | [`anthropic-plugin-directory.md`](docs/submissions/anthropic-plugin-directory.md) |
| **anthropics/skills cookbook** | https://github.com/anthropics/skills | GitHub PR | ✅ **submitted** — [PR #997](https://github.com/anthropics/skills/pull/997) | [`anthropics-skills-cookbook.md`](docs/submissions/anthropics-skills-cookbook.md) |

### What's left for you (venues that need your credentials)

1. **llms.txt directory** — open https://tally.so/r/wAydjB, paste the answers from [`docs/submissions/llms-txt-directory.md`](docs/submissions/llms-txt-directory.md), add your email, submit.

2. **Anthropic plugin directory** — in Claude Code / claude.ai, navigate to `settings/plugins/submit` (or check current docs at [code.claude.com/docs/en/plugins](https://code.claude.com/docs/en/plugins#submit-your-plugin-to-the-official-marketplace)). Use paste-ready answers from [`docs/submissions/anthropic-plugin-directory.md`](docs/submissions/anthropic-plugin-directory.md).

### Republishing `@dacrypt/xiao-skill` (skills.sh keeps fresh via npm)

Bump `version` in [`scripts/skills-sh/package.json`](scripts/skills-sh/package.json), then from repo root:

```bash
cp .claude/skills/xiao/SKILL.md scripts/skills-sh/SKILL.md
cp AGENTS.md                    scripts/skills-sh/AGENTS.md
cd scripts/skills-sh
npm publish --access public
```

Requires `npm login` (session usually cached) and that your npm 2FA is set to "Authorization only" (not "Authorization and writes") — npm CLI doesn't support passkeys mid-publish.

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

- [x] `SKILL.md` frontmatter validates (name ≤ 64 chars lowercase, description ≤ 1024 chars, says WHAT and WHEN). Verified 2026-04-21.
- [x] `llms.txt` is reachable at the repo root.
- [x] `AGENTS.md` is current.
- [x] PyPI package `xiao-cli` published and `pip install xiao-cli && xiao --help` works.
- [x] Repo description on GitHub matches the 1-liner pitch.
- [x] GitHub topics include: `xiaomi`, `roborock`, `vacuum`, `robot-vacuum`, `agent-tool`, `llm-tool`, `mcp`, `claude-skill`, `agents-md`, `llms-txt`, `home-automation`, `cli`, `python`, `smart-home`, `iot`. Set 2026-04-21.
- [ ] A 10-second terminal GIF showing `xiao status --json` (for Show HN, Reddit, Dev.to). Still pending — record with e.g. `asciinema` or `vhs`.
