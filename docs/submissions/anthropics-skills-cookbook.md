# anthropics/skills cookbook

**URL:** https://github.com/anthropics/skills
**Mechanism:** GitHub PR to add `xiao` as a community example.
**Approval:** Anthropic team review.

## Suggested PR flow

1. Fork `anthropics/skills`.
2. Add a new directory at the appropriate location (check repo conventions — likely `skills/community/xiao/` or `examples/xiao/`).
3. Copy `.claude/skills/xiao/SKILL.md` from this repo.
4. Add a short `README.md` in that dir with install + usage snippet.
5. Link back to upstream at https://github.com/dacrypt/xiao.
6. Open PR.

## PR title
```
Add `xiao` — agent-ready Xiaomi Robot Vacuum CLI skill
```

## PR body (paste-ready)

```markdown
## What

Adds the `xiao` skill to the community examples. `xiao` is an open-source
Python CLI that controls a Xiaomi Robot Vacuum X20+ (model
`xiaomi.vacuum.c102gl`) via the Xiaomi Cloud API. It's built CLI-first so
Claude (and any other agent that can exec a subprocess) can drive the
vacuum end to end.

## Why add it here

- Clean, minimal SKILL.md with complete frontmatter (name, description with
  WHAT + WHEN, ≤1024 chars).
- Ships with `AGENTS.md` and `llms.txt` at the upstream repo.
- Machine-readable contract: `--json` flag, canonical exit codes, explicit
  error-recovery protocol documented in AGENTS.md.
- CI green on Python 3.12/3.13 (ruff + mypy + pytest).
- MIT licensed.

## Checklist

- [x] SKILL.md validates against agentskills.io spec
- [x] Links back to upstream for full docs, issues, contributions
- [x] License-compatible (MIT)
- [x] No credentials / tokens in the skill file

## Upstream

- Repo: https://github.com/dacrypt/xiao
- AGENTS.md: https://github.com/dacrypt/xiao/blob/main/AGENTS.md
- SKILL.md: https://github.com/dacrypt/xiao/blob/main/.claude/skills/xiao/SKILL.md
```

## Suggested diff preview

```
anthropics-skills/
└── skills/
    └── community/
        └── xiao/
            ├── README.md            # short intro + link to upstream
            └── SKILL.md             # copy of .claude/skills/xiao/SKILL.md
```

## Before submitting

- [ ] Read `anthropics/skills` contribution guide if one exists.
- [ ] Confirm the community/ directory naming matches existing examples.
- [ ] Keep the fork up to date so the PR is rebaseable.
