# @dacrypt/xiao-skill

npm wrapper around the upstream `xiao` Claude Code / agentskills.io skill
for [skills.sh](https://skills.sh) auto-indexing.

## What's here

- `package.json` — npm metadata with `agentskills` field pointing at `SKILL.md`
- `SKILL.md` — **not committed**; copied from `.claude/skills/xiao/SKILL.md`
  by the `prepublish` step below
- `AGENTS.md` — same, copied from the repo root
- `README.md` — this file, pulled into the npm page

Everything that describes the skill lives in the upstream repo. This
directory exists only to package it for npm.

## How to publish (for maintainers)

From the repo root:

```bash
# 1. Copy the current SKILL.md + AGENTS.md into this directory
#    (README.md is already in place; no action needed for it)
cp .claude/skills/xiao/SKILL.md scripts/skills-sh/SKILL.md
cp AGENTS.md                     scripts/skills-sh/AGENTS.md

# 2. (Optional) validate the SKILL.md against agentskills.io spec
npx skills-ref validate scripts/skills-sh

# 3. Login to npm once:
npm login

# 4. Publish:
cd scripts/skills-sh
npm publish --access public

# 5. Verify the listing appears at skills.sh:
open https://skills.sh/skills/@dacrypt/xiao-skill
```

Bump `version` in `package.json` before each publish.

## Upstream

- Main repo: https://github.com/dacrypt/xiao
- Canonical SKILL.md: https://github.com/dacrypt/xiao/blob/main/.claude/skills/xiao/SKILL.md
- AGENTS.md: https://github.com/dacrypt/xiao/blob/main/AGENTS.md
