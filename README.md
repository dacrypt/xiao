# xiao — Xiaomi Vacuum CLI & Mission Control

[![CI](https://github.com/dacrypt/xiao/actions/workflows/ci.yml/badge.svg)](https://github.com/dacrypt/xiao/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/xiao-cli)](https://pypi.org/project/xiao-cli/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Agent-ready](https://img.shields.io/badge/agent--ready-AGENTS.md%20%7C%20llms.txt-blueviolet)](AGENTS.md)

CLI + web dashboard to control a **Xiaomi Robot Vacuum X20+** (model: `xiaomi.vacuum.c102gl`) via the **Xiaomi Cloud API**.

> **Cloud-only.** This vacuum model has no local-network control path. Every command goes through Xiaomi Cloud with RC4-signed MIoT requests.

> **Agent-first.** `xiao` is designed to be driven by LLM agents (Claude, OpenClaw, Cursor, Aider, Codex…) as a subprocess. If you are an agent reading this repo, start with [AGENTS.md](AGENTS.md).

![xiao demo](docs/demo/demo.gif)

---

## Agent Quick Reference

| Fact | Value |
|---|---|
| Tool name | `xiao` |
| Install | `pip install xiao-cli` |
| Verify | `xiao --help` → lists subcommands; exits 0 |
| State command | `xiao status` (Rich panel) or `xiao status --json` (machine-readable) |
| Machine-readable | `xiao status --json` / `xiao consumables --json`; or `xiao web` → `GET /api/status` |
| Exit codes | `0` success · `1` generic · `2` not configured · `77` auth failed · `78-80` reserved ([AGENTS.md](AGENTS.md#exit-codes)) |
| Agent guide | [AGENTS.md](AGENTS.md) — canonical commands, intent mapping, error recovery |
| Machine index | [llms.txt](llms.txt) |

---

## Features

- Full vacuum control — start / stop / pause / dock / find / room / zone / spot.
- Base-station controls — mop wash, mop dry, dust collect, tray eject.
- Settings — fan speed, water level, volume, Do-Not-Disturb window.
- Consumable tracking with remaining life %.
- Schedule viewer with parsed room / day / setting data.
- **Mission Control** — glassmorphism web dashboard with real-time status.
- Auto token refresh via a persistent Chromium session (no repeated email 2FA).
- Full MIoT property/action support for `c102gl`.

---

## Installation

```bash
pip install xiao-cli
# or from source
git clone https://github.com/dacrypt/xiao.git
cd xiao && uv sync
```

Then install Playwright's Chromium (needed for the cloud-login fallback):

```bash
playwright install chromium
```

### Docker

A lightweight image is published to GHCR on every release. It's meant for
running vacuum commands against an existing config — run `xiao setup
cloud` once on your workstation, then mount the resulting config dir:

```bash
docker run --rm -v "$HOME/.config/xiao:/root/.config/xiao" \
  ghcr.io/dacrypt/xiao status
```

(On macOS the host path is `~/Library/Application Support/xiao`.)

### MCP server (optional)

Install with the `mcp` extra and `xiao` exposes vacuum control as a
[Model Context Protocol](https://modelcontextprotocol.io) server, so
hosts like Claude Desktop / Cursor / mcp.so can drive the vacuum as
structured tools (no shelling out):

```bash
pip install "xiao-cli[mcp]"
xiao mcp           # speaks MCP over stdio
```

Host config snippet (Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "xiao": { "command": "xiao", "args": ["mcp"] }
  }
}
```

Exposed tools: `status`, `start_cleaning`, `stop_cleaning`,
`pause_cleaning`, `return_to_dock`, `find_vacuum`, `consumables`,
`clean_room`, `list_rooms`. The server reuses the same `config.toml` and
browser profile as the CLI.

**Compatibility:** Python 3.12+. Tested against vacuum model `xiaomi.vacuum.c102gl` on Xiaomi Cloud API as of 2024. Token refresh tested with Chromium ≥ 120 (currently running 147).

### Shell completions (optional)

```bash
xiao --install-completion   # bash / zsh / fish / pwsh — auto-detected
```

Restart your shell afterwards. `xiao <TAB>` will now complete subcommands.

### Handy defaults

- `xiao` with no subcommand prints the current vacuum status.
- `XIAO_DEBUG=1 xiao ...` enables verbose logging for issue reports.
- `XIAO_NO_CTA=1` silences the GitHub-star banner.

---

## Prerequisites

Before any `xiao` command will work:

1. `xiao` installed (see above) + `playwright install chromium` run once.
2. `xiao setup cloud` completed — writes `config.toml` at:
   - macOS: `~/Library/Application Support/xiao/config.toml`
   - Linux: `~/.config/xiao/config.toml`

That's it. `xiao setup cloud` will also offer to run `xiao setup
browser-login` at the end: a one-time Chromium window where you log into
`account.xiaomi.com`. The session cookies are saved to a private profile
under your config dir, so every future token refresh runs headless — no
captcha, no email 2FA.

You can rerun `xiao setup browser-login` anytime if a token expires or
the profile is cleared. Power users who already maintain a Chromium
session exposed over CDP can skip the profile entirely by setting
`XIAO_CDP_PORT=18800` (or whatever port).

---

## Setup

```bash
xiao setup cloud         # Interactive: email → password → region → device discovery → save
xiao setup show          # Print current config (tokens redacted)
```

---

## Quick Start

```bash
xiao status              # Current state, battery, fan speed, mode
xiao status --full       # Comprehensive status (+ DND, water, consumables)
xiao start               # Full-house clean
xiao stop                # Stop cleaning
xiao dock                # Return to charging dock
xiao find                # Beep to locate vacuum
xiao report              # Full report: status + consumables + schedules + history
```

Example `xiao status`:

```
╭─────────────────────────────── Vacuum Status ────────────────────────────────╮
│   State:    Drying                                                           │
│   Battery:  ███████████░░░░░░░░░ 56%                                         │
│   Fan:      turbo                                                            │
│   Charging: Charging                                                         │
│   dry_left_time_min:  470                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Example `xiao consumables`:

```
                Consumables
┏━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Component  ┃ Life ┃ Hours Left ┃ Status ┃
┡━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ Main Brush │  90% │       272h │        │
│ Side Brush │  86% │       172h │        │
│ Filter     │  81% │       122h │        │
│ Mop Pad    │  72% │        57h │        │
└────────────┴──────┴────────────┴────────┘
```

---

## Command Reference

Every command. One row each. Full catalog also lives in [AGENTS.md](AGENTS.md).

| Command | What it does | Notable flags |
|---|---|---|
| `xiao status [--full] [--json]` | State + battery + fan + mode | `--full` adds DND/water/consumables; `--json` for machine-readable output |
| `xiao start` | Full-house clean (always mop-washes first) | — |
| `xiao stop` / `xiao pause` | Stop / pause current clean | — |
| `xiao dock` | Return to charging dock | — |
| `xiao find` | Beep to locate | — |
| `xiao clean -r <id\|alias>` | Clean one or more rooms | `-r` repeatable, `--speed`, `-w`, `--repeat` |
| `xiao clean -z "x1,y1,x2,y2"` | Clean a rectangle (coords in mm) | `-z` repeatable, `--speed`, `-w`, `--repeat` |
| `xiao clean -s` | Spot clean at current location | `--speed`, `-w` |
| `xiao wash` / `xiao dry [--stop]` | Base-station mop wash / dry | — |
| `xiao dust` / `xiao eject` | Dust collect / eject tray | — |
| `xiao settings speed <level>` | Fan: `silent` \| `standard` \| `medium` \| `turbo` | no arg → print current |
| `xiao settings water <level>` | Mop water: `low` \| `medium` \| `high` | no arg → print current |
| `xiao settings volume <0-100>` | Voice volume | no arg → print current |
| `xiao settings dnd on/off` | Do-not-disturb | `--start HH:MM --end HH:MM` |
| `xiao map rooms` | List room IDs → names | — |
| `xiao map show` | Show raw map metadata from the cloud | — |
| `xiao rooms alias <id> "<name>"` | Add friendly-name alias | — |
| `xiao rooms rename <id\|alias> "<new>"` | Rename an alias | — |
| `xiao schedule list` | Show parsed schedules | — |
| `xiao consumables [--json]` | Brush / filter / mop health | `--json` for machine-readable output |
| `xiao consumables reset <part>` | Reset counter (`main_brush` \| `side_brush` \| `filter` \| `mop` \| `all`) | — |
| `xiao report` | Full combined report | — |
| `xiao cloud-login` | Force full re-login (captcha + 2FA) | — |
| `xiao web` | Launch Mission Control dashboard | `--port 8120` |
| `xiao raw <siid> <aiid> [params…]` | Raw MIoT call (escape hatch) | — |

### Flag reference

- **`--speed` / `--fan`:** `silent` · `standard` · `medium` · `turbo`
- **`-w` / `--water`:** `low` · `medium` · `high`
- **`--repeat N`:** integer ≥ 1, default `1`

---

## Room Cleaning

```bash
xiao clean -r 4                   # Clean Study
xiao clean -r 3 -r 7              # Clean Living Room + Dining Room
xiao clean --speed turbo -r 8     # Turbo clean Kitchen
xiao clean -r 3 -w high           # Living Room with high water (heavy mop)
```

### Room Management

Room IDs are specific to your vacuum's map — they're generated by the Xiaomi Home app the first time the robot maps the house.

```bash
xiao map rooms                    # ALWAYS run this first to discover IDs
xiao rooms alias 3 "Living Room"  # Create an alias
xiao rooms rename 3 "Lounge"      # Rename
```

Once aliased, names also work:

```bash
xiao clean -r "Living Room" -r "Kitchen"
```

> **Rule for agents:** never pass a room ID you haven't verified with `xiao map rooms`. Maps can be re-generated by the Xiaomi Home app.

---

## Zone Cleaning

Zones clean an **arbitrary rectangle** — useful for spot work (*"just the dining table area"*) or for rooms the vacuum hasn't segmented correctly.

A zone is four coordinates in millimeters on the vacuum's internal map:

```
x1,y1,x2,y2
└─┬─┘ └─┬─┘
 top-    bottom-
 left    right
```

Origin `(0,0)` sits at the center of the map. Rooms typically fall in the `20000–40000` range on each axis. The easiest way to get real numbers is to draw a zone once inside the Xiaomi Home app and copy them.

```bash
# Single zone
xiao clean -z "25000,25000,35000,35000"

# Multiple zones in one run
xiao clean -z "23000,24000,27000,28000" \
           -z "31000,25000,35000,30000"

# Zone + turbo fan + high water (deep-clean a specific patch)
xiao clean -z "25000,25000,35000,35000" --speed turbo -w high

# Two passes over the same zone
xiao clean -z "25000,25000,35000,35000" --repeat 2
```

---

## Base Station

```bash
xiao wash                # Start mop washing
xiao dry                 # Start mop drying
xiao dry --stop          # Stop drying
xiao dust                # Dust collection
xiao eject               # Eject base tray
```

---

## Settings

```bash
xiao settings speed turbo        # silent | standard | medium | turbo
xiao settings water high         # low | medium | high (mop water level)
xiao settings volume 50          # 0-100
xiao settings dnd on --start 22:00 --end 07:00
xiao settings dnd off

# Call any of the above without an argument to print the current value:
xiao settings speed              # → Current fan speed: turbo
xiao settings water              # → Water level: High (raw: High)
```

### Machine-readable output

Use `--json` on read commands for deterministic parsing:

```bash
xiao status --json
# {
#   "state": "Drying",
#   "battery": 84,
#   "fan_speed": "turbo",
#   "charging": "Charging",
#   "dry_left_time_min": 388
# }

xiao consumables --json
```

---

## Agent Intent Mapping

Short table of "user says X → run Y". The canonical, longer version lives in [AGENTS.md](AGENTS.md#intent-mapping).

| User request | Command |
|---|---|
| "clean the house" | `xiao start` |
| "stop" / "cancel" | `xiao stop` |
| "go home" / "dock" | `xiao dock` |
| "battery?" / "status?" | `xiao status` |
| "clean the `<room>`" | `xiao map rooms` → find id → `xiao clean -r <id>` |
| "turbo mode in `<room>`" | `xiao clean -r <id> --speed turbo` |
| "deep mop `<room>`" | `xiao clean -r <id> --speed turbo -w high` |
| "wash the mop" | `xiao wash` |
| "empty the dust bin" | `xiao dust` |
| "do not disturb 22 to 7" | `xiao settings dnd on --start 22:00 --end 07:00` |
| "open the dashboard" | `xiao web --port 8120` |

---

## Error Recovery

Agents should apply these in order before asking the user.

| Signal | Retry step | If still failing |
|---|---|---|
| Stderr contains `token` / `401` / `auth` | Re-run the same command once (CDP refresh fires on next call) | `xiao cloud-login`, then retry |
| Stderr: `Cannot connect to browser CDP on port 18800` | Launch `chromium --remote-debugging-port=18800 --user-data-dir=~/.xiao-chromium`, user logs in at `account.xiaomi.com` | Fall back to `xiao cloud-login` |
| `State: 21` / "WashingMopPause" / "Water Tank Alert" | User refills clean water / empties dirty water → `xiao start` | Press physical play button on the robot |
| `xiao clean -r <id>` returns code 0 but `xiao status` after 10s still shows `Idle`/`Docked` | Fall back to `xiao start` | Report to user |
| Fan speed set rejected while docked | Start the clean first, then set speed; or pass `--speed` inline on the clean command | — |
| `xiao map rooms` → "No rooms found" | Vacuum hasn't mapped the house yet — user must run `xiao start` once first | — |
| Fan level printed as raw % (e.g. `68`) | Map via thresholds: `≤30=Silent, ≤55=Standard, ≤75=Medium, >75=Turbo` | — |

---

## Mission Control (Web Dashboard)

```bash
xiao web --port 8120
# Open http://localhost:8120
```

Glassmorphism + neon sci-fi dashboard:

- Animated vacuum SVG (pulses cleaning, dims docked).
- Battery ring with gradient + estimated runtime.
- Room selector with fan / water presets.
- Base-station controls with status badges.
- Consumable health bars (color-coded, days-until-replacement).
- Cleaning history stats, schedule table, settings panel.
- Keyboard: `S`=start, `X`=stop, `D`=dock, `F`=find, `R`=refresh.
- Mobile-first responsive, auto-refresh every 10s.

### REST API

All endpoints at `http://localhost:8120/api/` — use these for **programmatic / JSON** consumption:

| Endpoint | Method | Description |
|---|---|---|
| `/status` | GET | State, battery, fan, mode |
| `/status/live` | GET | Minimal payload for fast polling (5s) |
| `/consumables` | GET | Brush / filter health |
| `/rooms` | GET | Room list |
| `/schedules` | GET | Parsed schedules |
| `/start` | POST | Start clean |
| `/stop` | POST | Stop |
| `/dock` | POST | Return to dock |
| `/clean/rooms` | POST | `{room_ids, fan, water}` |
| `/wash` | POST | Mop wash |
| `/dry` | POST | Start/stop dry |
| `/dust` | POST | Dust collect |
| `/settings/speed` | POST | `{level: 0-3}` |
| `/settings/volume` | POST | `{level: 0-100}` |

---

## Use `xiao` as a Skill in an Agent

Because `xiao` is just a CLI, teaching an agent to drive your vacuum is really just teaching it which commands to run. Paste this prompt into **OpenClaw** (or any LLM agent that can run a subprocess) to bootstrap:

> **"Set up the Xiaomi vacuum skill"**
>
> ```
> I want you to act as my Xiaomi vacuum controller using the `xiao` CLI
> (https://github.com/dacrypt/xiao). Read AGENTS.md from that repo and
> follow its instructions. Then set it up end-to-end:
>
> 1. Install:    pip install xiao-cli && playwright install chromium
> 2. Verify:     xiao --help
> 3. Walk me through `xiao setup cloud` interactively (ask me for email,
>    password, region — one of us/cn/eu/ru/sg/tw/i2 — then discover device).
> 4. Open https://account.xiaomi.com/pass/login in your own browser tab on
>    remote-debugging port 18800. I'll solve the captcha + email 2FA once.
>    Leave that tab open — it's the long-lived session xiao reuses.
> 5. Confirm with `xiao status` and `xiao consumables`.
>
> From now on, translate vacuum-related requests ("clean the kitchen",
> "send it home", "what's the battery?", "turbo in the living room") into
> the right `xiao` command using AGENTS.md's intent-mapping table. Never
> guess room IDs — always run `xiao map rooms` first.
>
> On errors, follow the Error Recovery protocol in AGENTS.md before
> asking me.
> ```

Works the same way in Claude Code, Cursor, Aider, Codex. A ready-made Claude Code skill ships with the repo at [`.claude/skills/xiao/SKILL.md`](.claude/skills/xiao/SKILL.md) — it's picked up automatically when you open this directory in Claude Code.

---

## Cloud Token Refresh

Xiaomi Cloud `serviceToken`s expire every ~6-8h. A full re-login requires captcha + email 2FA, which can't be automated headlessly. To avoid that, `xiao` reuses a long-lived Xiaomi session inside a Chromium browser you keep running in the background with CDP on port `18800`.

**The browser** is just regular Chromium launched once with:

```bash
chromium --remote-debugging-port=18800 --user-data-dir=~/.xiao-chromium
```

…then logged into `https://account.xiaomi.com` manually. The login cookies persist in the user-data-dir, so future refreshes reuse them. No specific fork or external tool required.

**Refresh flow** (when the saved `serviceToken` is missing/expired, [`core/token_refresh.py`](src/xiao/core/token_refresh.py)):

1. Connects via CDP at `http://127.0.0.1:18800` (Playwright `connect_over_cdp`).
2. Navigates to `account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true` to obtain a fresh `_sign` — httpOnly cookies travel automatically.
3. Submits a hidden `<form>` POST to `serviceLoginAuth2` (form submission because `fetch`/`xhr` don't send httpOnly cookies). Response yields `ssecurity` + `location`.
4. Follows `location`, which sets the `serviceToken` cookie on the redirect.
5. Returns `{userId, serviceToken, ssecurity}` to the caller → persisted to `config.toml`.

If the browser isn't reachable, `xiao` falls back to a full Playwright login (headless Chromium). Manual trigger: `xiao cloud-login`.

---

## Troubleshooting

*(Agents: the machine-oriented decision tree is in [Error Recovery](#error-recovery) above — this section is for humans.)*

**`Cannot connect to browser CDP on port 18800`**
The Chromium instance that holds your Xiaomi session isn't running (or isn't listening on 18800). Launch it:
```bash
chromium --remote-debugging-port=18800 --user-data-dir=~/.xiao-chromium
```
Then log into `https://account.xiaomi.com` once in that window. Leave it running. As a fallback, `xiao cloud-login` performs a full re-login with captcha + email 2FA.

**`Cloud mode enabled but not configured` (exit 2)**
Run `xiao setup cloud` — the wizard asks for email / password / region and discovers your device.

**Commands hang or time out**
Usually a Xiaomi Cloud issue. Check connectivity (`curl -I https://api.io.mi.com`). The RC4-signed endpoint can also return 500s during Xiaomi maintenance windows.

**`xiao clean -r 3` returns OK but the vacuum doesn't move**
Known issue with room-specific cleans on some X20+ firmwares. Fallback: `xiao start` (full-house clean). Tracked in [BACKLOG.md](BACKLOG.md).

**"No rooms found" from `xiao map rooms`**
The robot hasn't mapped your house yet. Run `xiao start` once end-to-end and let it learn the layout, then retry.

**Fan speed setting is rejected while docked**
Some MIoT properties are only writable while the robot is off the dock. Start a clean first, or pass `--speed` inline on the `clean` command.

**Water tank alert (state 21)**
Refill the clean-water tank / empty the dirty-water tank at the base. Then `xiao start` to resume. If the robot still sits in state 21, press the physical play button on the top of the robot.

---

## Cleaning Cycle

When you call `xiao start`, the X20+ runs the full sequence:

1. **Washing mop** — washes pads at base station (~2-3 min).
2. **Cleaning** — sweeps/mops the house.
3. **Returning** — back to dock.
4. **Drying** — auto-dries mop pads.

> `start` always triggers a mop wash first, even in sweep-only mode.

---

## Why this project exists

*(Read this if you like origin stories. Agents can skip to [AGENTS.md](AGENTS.md).)*

`xiao` started as a specific itch: drive my Xiaomi vacuum from an LLM agent — first **OpenClaw**, then **Claude**.

The internet wasn't encouraging. ChatGPT and most forum threads said some variant of *"this model is cloud-only, the API is signed, you can't control it from a script."* That turned out to be wrong — just tedious. Sitting down with Claude Code and poking at my own robot (sniffing requests, reversing the RC4 signing, mapping the MIoT spec for `xiaomi.vacuum.c102gl`), the protocol gave up pretty quickly.

Once the CLI worked, the rest followed fast. Anthropic's general guidance for letting agents touch the real world is unsexy but effective: give them a CLI. The same binary you run by hand is the one the agent execs. So `xiao` is deliberately CLI-first — the dashboard, the REST API, the skill integrations are all thin layers over the same core.

At that point it stops mattering *which* LLM is driving, because the vacuum doesn't care. This repo is really a **skill** — a small, reusable capability you can bolt onto any agent. Routines, voice assistants, cross-device automations, home dashboards — all downstream.

---

## Development

```bash
uv sync
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/xiao/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for source-tree layout, MIoT spec notes, and PR guidelines.

---

## Privacy

`xiao` collects **nothing**. No telemetry, no analytics, no backend. Your
Xiaomi credentials and session tokens live exclusively on your machine.
See [PRIVACY.md](PRIVACY.md) for the full statement.

## License

[MIT](LICENSE)
