# xiao — Agent Instructions

This file is read by LLM agents (Claude Code, Cursor, Aider, OpenClaw, Codex,
Gemini CLI). Humans should read [README.md](README.md). Keep this file ≤ 200
lines and kept up to date with the commands the CLI actually exposes.

`xiao` is a CLI that controls a Xiaomi Robot Vacuum X20+
(model: `xiaomi.vacuum.c102gl`) via the Xiaomi Cloud API. All commands exit 0
on success and non-zero on error.

## Prerequisites — these must all be true before any command will succeed

1. Python 3.12+ in the active environment.
2. `pip install xiao-cli` (or `uv sync` if working from source).
3. `playwright install chromium` has been run once on this machine.
4. `xiao setup cloud` has been completed — produces `config.toml` at:
   - macOS: `~/Library/Application Support/xiao/config.toml`
   - Linux: `~/.config/xiao/config.toml`
5. `xiao setup browser-login` has been run once — opens a Chromium window
   pointed at `https://account.xiaomi.com` where the human logs in. The
   session persists in a private profile (`<CONFIG_DIR>/chromium`) so
   future token refreshes run headless, no captcha or email 2FA. Step 4
   offers to run this automatically at the end of its flow.

If prerequisite 5 is missing (empty profile / expired session), token
refresh falls back to `xiao cloud-login` which requires captcha + email
2FA inside a Playwright-driven window. Instruct the user to rerun
`xiao setup browser-login` to restore silent refresh.

**Advanced:** if the user already maintains a Chromium over CDP for other
tooling, set `XIAO_CDP_PORT=<port>` and xiao will prefer that session
instead of the managed profile.

## Canonical commands

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `xiao status` | Current state, battery, fan, mode | `--full` for DND+water+consumables; `--json` / `-j` for machine-readable output |
| `xiao start` | Full-house clean (always mop-washes first) | — |
| `xiao stop` | Stop current clean | — |
| `xiao pause` | Pause (resume with `xiao start`) | — |
| `xiao dock` | Return to charging dock | — |
| `xiao find` | Beep to locate | — |
| `xiao report` | Status + consumables + schedules + history | — |
| `xiao clean -r <id-or-alias>` | Clean one or more rooms | `-r` repeatable, `--speed`, `-w`, `--repeat` |
| `xiao clean -z "x1,y1,x2,y2"` | Clean a rectangle (mm) | `-z` repeatable, `--speed`, `-w`, `--repeat` |
| `xiao clean -s` | Spot clean at current location | `--speed`, `-w` |
| `xiao wash` | Start mop-pad wash | — |
| `xiao dry` / `xiao dry --stop` | Start / stop mop dry | — |
| `xiao dust` | Dust collection at base | — |
| `xiao eject` | Eject base tray | — |
| `xiao settings speed <level>` | Set fan: `silent` \| `standard` \| `medium` \| `turbo` | no arg → prints current |
| `xiao settings water <level>` | Set mop water: `low` \| `medium` \| `high` | no arg → prints current |
| `xiao settings volume <0-100>` | Set voice volume | no arg → prints current |
| `xiao settings dnd on --start HH:MM --end HH:MM` / `off` | Do-not-disturb | no arg → prints current window |
| `xiao map rooms` | List room IDs → names (run this BEFORE any `clean -r`) | — |
| `xiao map show` | Show raw map metadata from the cloud | — |
| `xiao rooms alias <id> "<name>"` | Create a friendly-name alias | — |
| `xiao rooms rename <id-or-old-alias> "<new>"` | Rename | — |
| `xiao schedule list` | Show parsed schedules | — |
| `xiao consumables` | Brush / filter / mop health | `--json` / `-j` |
| `xiao consumables reset <part>` | Reset counter for `main_brush` / `side_brush` / `filter` / `mop` / `all` | — |
| `xiao cloud-login` | Force full login (captcha + email 2FA) | — |
| `xiao web --port 8120` | Launch Mission Control dashboard | — |
| `xiao raw <siid> <aiid> [params...]` | Escape hatch for raw MIoT calls | — |

### Canonical flag values

- `--speed` / `--fan`: `silent` | `standard` | `medium` | `turbo`
- `-w` / `--water`: `low` | `medium` | `high`
- `--repeat`: integer ≥ 1 (default 1)

## Intent mapping — "user says X, run Y"

| User request (natural language) | Command |
|---|---|
| "clean the house" / "start cleaning" | `xiao start` |
| "stop" / "cancel" | `xiao stop` |
| "pause" | `xiao pause` |
| "go home" / "dock" / "charge" | `xiao dock` |
| "where's the vacuum" / "find it" | `xiao find` |
| "battery?" / "status?" | `xiao status` |
| "full status" / "everything" | `xiao status --full` |
| "clean the <room>" | `xiao map rooms` → find id → `xiao clean -r <id>` |
| "clean <room A> and <room B>" | `xiao clean -r <idA> -r <idB>` |
| "turbo mode in the <room>" | `xiao clean -r <id> --speed turbo` |
| "deep mop the <room>" | `xiao clean -r <id> --speed turbo -w high` |
| "clean this zone: x1,y1 to x2,y2" | `xiao clean -z "x1,y1,x2,y2"` |
| "wash the mop" | `xiao wash` |
| "dry the mop" / "stop drying" | `xiao dry` / `xiao dry --stop` |
| "empty the dust bin" | `xiao dust` |
| "eject the tray" | `xiao eject` |
| "quiet mode" / "turbo mode" (as default) | `xiao settings speed silent` / `turbo` |
| "more / less water" / "heavy mop" / "light mop" | `xiao settings water high` / `low` |
| "volume <N>" / "volume up/down" | `xiao settings volume <N>` |
| "do not disturb from 22 to 7" | `xiao settings dnd on --start 22:00 --end 07:00` |
| "disable DND" | `xiao settings dnd off` |
| "show consumables" / "health" | `xiao consumables` |
| "open the dashboard" | `xiao web --port 8120` |

**Rule:** never pass a room ID you haven't just verified with `xiao map rooms`.
Room IDs are per-vacuum and can be re-generated by the Xiaomi Home app.

## Error recovery (autonomous retry protocol)

Apply these in order. Only ask the user after all automatic recovery fails.

| Signal | Retry step | If still failing |
|---|---|---|
| Exit code ≠ 0, stderr/stdout contains "token" / "401" / "auth" | Re-run the same command once (auto-refresh via CDP fires on next call) | Run `xiao cloud-login` then retry |
| Stderr: "Cannot connect to browser CDP on port 18800" | Launch `chromium --remote-debugging-port=18800 --user-data-dir=~/.xiao-chromium` and tell user to log in at `account.xiaomi.com` once | Fall back to `xiao cloud-login` |
| Output contains `State: 21` or "WashingMopPause" / "Water Tank Alert" | Ask user to refill clean-water / empty dirty-water, then `xiao start` | Ask user to press the physical play button on the robot |
| `xiao clean -r <id>` returns code 0 but vacuum doesn't move (check `xiao status` after 10s — still `Idle`/`Docked`) | Fall back to `xiao start` | Report to user |
| Fan speed change rejected with code ≠ 0 while docked | Start a clean first, then set speed (some MIoT fields are only writable off-dock) | Set `--speed` inline on the clean command |
| `xiao map rooms` → "No rooms found" | Tell user the vacuum hasn't mapped the house yet — they need to run a full `xiao start` once first | — |

## Output parsing

**Prefer `--json` / `-j` on read commands** — it's the only guaranteed
machine-readable path. Supported today:

```bash
xiao status --json         # { state, battery, fan_speed, charging, ... }
xiao status --full --json  # adds dnd, water, consumables
xiao consumables --json    # { main_brush_life, filter_life, mop_left_time, ... }
```

Commands without `--json` print Rich-formatted tables/panels to stdout. Parse
by line: look for `Key: value` prefixes; table rows for `consumables`. Fan
level may come back as a raw percentage that the CLI maps to names
(`≤30=Silent, ≤55=Standard, ≤75=Medium, >75=Turbo`).

For fully programmatic integrations, the REST API is an alternative:
`xiao web --port 8120` → `GET http://localhost:8120/api/status` returns JSON.
See README.md "REST API" for endpoint list.

## Exit codes

| Code | Meaning | Suggested agent action |
|---|---|---|
| `0` | Success | Continue |
| `1` | Generic failure | Parse stderr; may be recoverable |
| `2` | Not configured — `config.toml` missing or incomplete | Guide user through `xiao setup cloud` |
| `77` | Cloud auth / token refresh failed | Run `xiao cloud-login`, then retry |
| `78` | (reserved) Chromium CDP on port 18800 unreachable | Launch Chromium with `--remote-debugging-port=18800` |
| `79` | (reserved) State 21 / water-tank alert | Ask user to refill/empty tanks, then `xiao start` |
| `80` | Room-clean command accepted but the vacuum still looked docked/charging after verification | Re-check room IDs, then fall back to `xiao start` |

Today only code `80` is emitted consistently. Codes `78-79` remain reserved;
detect those conditions by inspecting `xiao status --json` output.

## Safety / guardrails

- Never commit or print the contents of `config.toml` — it contains the user's
  Xiaomi password hash and service tokens.
- Don't call `xiao raw` unless the user explicitly asks. It's an unchecked
  escape hatch into MIoT and can brick settings.
- `xiao start` always triggers a mop wash first — warn the user if they asked
  for sweep-only; there's no flag to skip the wash.

## Version compatibility

- Python: 3.12+
- Vacuum model: `xiaomi.vacuum.c102gl` (X20+). Other Roborock/Xiaomi models
  may work for basic actions but MIoT spec mappings are model-specific.
- Xiaomi Cloud API: as of 2024. If login suddenly requires new fields or the
  `serviceLoginAuth2` form changes shape, that's an upstream protocol shift
  and `xiao` will need an update.
- Chromium / Chrome: any modern version supporting CDP (≥ 120 tested).
