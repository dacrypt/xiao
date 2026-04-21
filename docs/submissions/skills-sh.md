# skills.sh (agentskills.io registry)

**URL:** https://skills.sh
**Docs:** https://skills.sh/docs
**Mechanism:** Publish the skill directory as an npm package — skills.sh auto-indexes from npm telemetry.
**Audience:** Every major agent platform (Claude Code, Codex CLI, Cursor, Gemini CLI, Copilot, Windsurf, Goose).
**Approval:** Automated; ranking grows with install count.

## Prep checklist

- [ ] Install the agentskills CLI: `npm i -g skills-ref`
- [ ] Validate the existing `.claude/skills/xiao/SKILL.md`:
  ```bash
  npx skills-ref validate .claude/skills/xiao
  ```
  Expected: zero errors; confirm `name: xiao` (lowercase, ≤64 chars) and description ≤1024 chars. Already manually verified (649/1024 chars, has WHAT + WHEN).

- [ ] Create an npm package wrapper at repo root or in a sibling dir. Minimum `package.json`:
  ```json
  {
    "name": "@dacrypt/xiao-skill",
    "version": "0.1.0",
    "description": "Control a Xiaomi Robot Vacuum X20+ via the xiao CLI — agent-ready skill for Claude Code, Codex, Cursor, Gemini CLI, Copilot.",
    "keywords": ["agent-skill", "agentskills.io", "claude-skill", "xiaomi", "roborock", "vacuum", "home-automation", "cli"],
    "license": "MIT",
    "repository": {"type": "git", "url": "https://github.com/dacrypt/xiao.git"},
    "files": [".claude/skills/xiao/SKILL.md", "AGENTS.md"],
    "agentskills": {
      "skills": [".claude/skills/xiao/SKILL.md"]
    }
  }
  ```
- [ ] `npm publish --access public` (requires logged-in npm account).
- [ ] Verify listing appears at `https://skills.sh/skills/@dacrypt/xiao-skill` within ~24h.

## Why this venue first

Zero-friction — the existing `SKILL.md` already conforms to agentskills.io.
All we're doing is packaging it for npm so skills.sh can pick it up. Lowest
effort per unit of reach: one npm publish → indexed across 7+ agent
platforms.
