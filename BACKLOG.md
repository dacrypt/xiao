# xiao — Backlog & Roadmap

## Priority Legend
- 🔴 P1 — Bug / broken functionality
- 🟠 P2 — Important improvement
- 🔵 P3 — Nice to have
- ⚪ P4 — Research / exploration

## Active Bugs
- 🔴 Room-specific cleaning unreliable — `clean_rooms_miot()` returns code=0 but vacuum doesn't move. Need to investigate alternative params or sequences.
- 🔴 `last_clean_date` shows 2026-01-12 (stale) — the unix timestamp (1768243787) might be wrong or siid 12 piid 1 is something else on this model.

## Improvements Planned
- 🟠 Token auto-refresh on 401 — detect expired token, auto-refresh via browser CDP, retry command
- 🟠 Better room cleaning — research if X20+ needs specific clean_param JSON format or a different action sequence
- 🟠 Dashboard: fix history section displaying "--" for some fields
- 🟠 Dashboard: clean up lower sections (Audio, Clean Log Raw, All Properties) — too verbose, collapse by default
- 🔵 Dashboard: add dark/light theme toggle
- 🔵 CLI: `xiao rooms rename <id> <name>` — interactive room renaming
- 🔵 CLI: `xiao schedule` — view schedules in a nice table
- 🔵 Sweep type decoding — raw values (448, 467, 472) meaning unknown

## Research / Exploration
- ⚪ Map extraction — MITM Mi Home app traffic to find decryption key for cloud map data
- ⚪ Room IDs verification — map room IDs to actual room names from Mi Home app
- ⚪ Local UDP fallback — periodically check if vacuum becomes reachable locally
- ⚪ Valetudo compatibility — monitor if X20+ (c102gl) gets rooting support
- ⚪ Home Assistant integration — MQTT or REST sensor for HA
- ⚪ Notification system — Telegram alerts for cleaning complete, errors, consumable low
- ⚪ Energy estimation — track cleaning time × estimated wattage for power consumption
- ⚪ Floor plan editor — manual room layout in dashboard (drag & drop)

## Community Features to Research
Sources: Valetudo, python-miio, hass-xiaomi-miot, r/Xiaomi, r/homeassistant
- Zone cleaning with coordinates
- Virtual walls / no-go zones
- Carpet detection behavior
- Multi-floor map support
- Cleaning history heatmap
- Custom voice packs
- OTA firmware management

## Completed
- ✅ Cloud mode control (all basic actions)
- ✅ Mission Control dashboard (glassmorphism, real-time)
- ✅ Water Tank Alert detection (state 21) + auto-reset
- ✅ Water tank level estimator (area-based)
- ✅ Mop consumable tracking + reset
- ✅ Network info in dashboard (IP, WiFi, RSSI, MAC)
- ✅ All 4 consumable resets (main brush, side brush, filter, mop)
- ✅ Full MIoT property scan (39 properties documented)
- ✅ Schedule parser with room names
- ✅ Base station controls (wash, dry, dust, eject)
- ✅ Fan speed / water level / volume / DND settings
- ✅ Token refresh via browser CDP
