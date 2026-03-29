# xiao — Xiaomi Vacuum CLI & Mission Control

[![CI](https://github.com/dacrypt/xiao/actions/workflows/ci.yml/badge.svg)](https://github.com/dacrypt/xiao/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

CLI tool + web dashboard to control a **Xiaomi Robot Vacuum X20+** (model: `xiaomi.vacuum.c102gl`) via **Xiaomi Cloud API**.

> **Cloud-only mode.** This vacuum does not support local network control. All commands go through Xiaomi Cloud with RC4-signed requests.

## Features

- 🤖 Full vacuum control (start/stop/dock/find/rooms/zones)
- 🧽 Base station controls (mop wash, dry, dust collect, eject tray)
- ⚙️ Settings management (fan speed, water level, volume, DND)
- 🛠 Consumable tracking with remaining life %
- 📅 Schedule viewer with parsed room/day/setting data
- 🌐 **Mission Control** — glassmorphism web dashboard with real-time status
- 🔄 Auto token refresh via OpenClaw browser (no email verification)
- 📊 Full MIoT property/action support for c102gl

## Installation

```bash
pip install xiao
```

Or install from source:

```bash
git clone https://github.com/dacrypt/xiao.git
cd xiao
uv sync
```

Requires Python 3.12+. Playwright browsers are needed for cloud login:

```bash
playwright install chromium
```

## Setup

```bash
# Interactive cloud setup — logs in, discovers devices, saves config
xiao setup cloud

# Show current config
xiao setup show
```

Config is stored at your platform's config directory (e.g. `~/Library/Application Support/xiao/config.toml` on macOS, `~/.config/xiao/config.toml` on Linux).

## Quick Start

```bash
xiao status              # Current state, battery, fan speed, mode
xiao status --full       # Comprehensive status (+ DND, water, consumables)
xiao start               # Full house clean
xiao stop                # Stop cleaning
xiao dock                # Return to charging dock
xiao find                # Beep to locate vacuum
xiao report              # Full report: status + consumables + schedules + history
```

## Room Cleaning

```bash
xiao clean -r 4                   # Clean Estudio
xiao clean -r 3 -r 7              # Clean Sala + Comedor
xiao clean --speed turbo -r 8     # Turbo clean Cocina
xiao clean -z "25000,25000,35000,35000"  # Zone cleaning
```

### Room Management

Room IDs are specific to your vacuum's map. Use `xiao map rooms` to list yours, and `xiao rooms alias <id> <name>` to set friendly names.

## Base Station

```bash
xiao wash                # Start mop washing
xiao dry                 # Start mop drying
xiao dry --stop          # Stop drying
xiao dust                # Dust collection
xiao eject               # Eject base tray
```

## Settings

```bash
xiao settings speed turbo        # Fan: silent/standard/medium/turbo
xiao settings volume 50          # Volume: 0-100
xiao settings dnd on --start 22:00 --end 07:00
```

## Mission Control (Web Dashboard)

```bash
xiao web --port 8120
# Open http://localhost:8120
```

Glassmorphism + neon sci-fi themed dashboard with:
- Animated vacuum SVG (pulses when cleaning, dims when docked)
- Battery ring with gradient colors + estimated runtime
- Room selector with fan/water presets
- Base station controls with status badges
- Consumable health bars (color-coded, days until replacement)
- Cleaning history stats
- Schedule table
- Settings panel (fan, water, volume slider, DND toggle)
- Keyboard shortcuts: `S`=start, `X`=stop, `D`=dock, `F`=find, `R`=refresh
- Mobile-first responsive, auto-refresh every 10s

### REST API

All endpoints at `http://localhost:8120/api/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | State, battery, fan, mode |
| `/status/live` | GET | Minimal for fast polling (5s) |
| `/consumables` | GET | Brush/filter health |
| `/rooms` | GET | Room list |
| `/schedules` | GET | Parsed schedules |
| `/start` | POST | Start clean |
| `/stop` | POST | Stop |
| `/dock` | POST | Return to dock |
| `/clean/rooms` | POST | Room clean `{room_ids, fan, water}` |
| `/wash` | POST | Mop wash |
| `/dry` | POST | Start/stop dry |
| `/dust` | POST | Dust collect |
| `/settings/speed` | POST | Fan speed `{level: 0-3}` |
| `/settings/volume` | POST | Volume `{level: 0-100}` |

## Architecture

```
src/xiao/
├── cli/           # Typer CLI commands
│   ├── app.py     # Main entry + top-level commands
│   ├── clean.py   # Room/zone/spot cleaning
│   ├── rooms.py   # Room alias management
│   ├── schedule.py
│   ├── settings.py
│   └── setup.py   # Cloud/local setup wizard
├── core/          # Business logic
│   ├── cloud.py          # XiaomiCloud client (login, RC4, 2FA, captcha)
│   ├── cloud_vacuum.py   # CloudVacuumService (MIoT via cloud)
│   ├── config.py         # TOML config management
│   ├── token_refresh.py  # Token refresh via OpenClaw browser CDP
│   └── vacuum.py         # Local interface (unused in cloud mode)
├── dashboard/     # Web UI
│   ├── server.py  # FastAPI backend
│   └── index.html # Single-file glassmorphism frontend
└── ui/
    └── formatters.py  # Rich terminal formatters
```

## Cleaning Cycle

When you call `xiao start`, the X20+ runs the full sequence:

1. 🧽 **Washing mop** — washes pads at base station (~2-3 min)
2. 🧹 **Cleaning** — sweeps/mops the house
3. 🏠 **Returning** — goes back to dock
4. 💨 **Drying** — auto-dries mop pads

> **Note:** `start` always triggers a mop wash first, even in sweep-only mode. Room-specific cleaning (`clean -r`) is less reliable — sometimes the vacuum acknowledges but doesn't move. Use `xiao start` as fallback.

### Water Tank Alert (State 21)

If the base station detects empty clean water or full dirty water, the vacuum enters **state 21 (WashingMopPause)**. The dashboard shows "⚠️ Water Tank Alert".

**To fix:**
1. Refill the clean water tank / empty the dirty water tank
2. Run `xiao start` — this resumes the interrupted cycle
3. If that doesn't work, press the play button on the robot

## Known Issues

| Issue | Workaround |
|-------|------------|
| State 21 (Water Tank Alert) | Fix tanks, then `xiao start` to resume (or button press) |
| Fan speed can't be set from dock | Set after clean starts, or include in room request |
| Room clean returns OK but doesn't move | Use `xiao start` (full clean) as fallback |
| Fan level returns raw % (e.g. 68) | Mapped to names: ≤30=Silent, ≤55=Standard, ≤75=Medium, >75=Turbo |
| Map data encrypted on cloud | Investigation in progress (MITM needed) |

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Lint & format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/xiao/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## Cloud Token Refresh

Tokens expire every ~6-8h. Auto-refresh flow:
1. Connects to OpenClaw browser via CDP (port 18800)
2. Navigates to Xiaomi serviceLogin (uses existing cookies, no captcha)
3. Form POST → gets fresh ssecurity + serviceToken
4. Saves to config.toml

Manual: `xiao cloud-login`

## License

[MIT](LICENSE)
