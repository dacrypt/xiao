# xiao — Backlog & Roadmap

## Priority Legend
- 🔴 P1 — Bug / broken functionality
- 🟠 P2 — Important improvement
- 🔵 P3 — Nice to have
- ⚪ P4 — Research / exploration

## Active Bugs
- 🔴 Room-specific cleaning unreliable — `clean_rooms_miot()` returns code=0 but vacuum doesn't move. Need to investigate alternative params or sequences.
- 🔴 `last_clean_date` shows 2026-01-12 (stale) — the unix timestamp (1768243787) might be wrong or siid 12 piid 1 is something else on this model.
- 🔴 FIXED: `set_fan_speed()` was writing to siid 2 piid 2 (device fault, read-only!) instead of piid 3 (mode/fan). This means every `xiao speed set` command was attempting to write a fault code. Also `status()` was mapping piid 2 (fault) → `fan_speed` display, causing garbage values. Fixed 2026-03-31.

## Improvements Planned
- 🟠 Token auto-refresh on 401 — detect expired token, auto-refresh via browser CDP, retry command
- 🟠 Better room cleaning — research if X20+ needs specific clean_param JSON format or a different action sequence
- 🟠 Dashboard: clean up lower sections (Audio, Clean Log Raw, All Properties) — too verbose, collapse by default
- 🔵 Dashboard: add dark/light theme toggle
- 🔵 CLI: `xiao rooms rename <id> <name>` — interactive room renaming
- 🔵 CLI: `xiao schedule` — view schedules in a nice table
- 🔵 Sweep type decoding — raw values (448, 467, 472) — NOTE: per official MIoT spec, siid 2 piid 5 is `dry-left-time` (minutes), NOT sweep type. The 448/467/472 values may have been fault codes from piid 2.

## Research / Exploration
- ⚪ Map extraction — MITM Mi Home app traffic to find decryption key for cloud map data
- ⚪ Room IDs verification — map room IDs to actual room names from Mi Home app
- ⚪ Local UDP fallback — periodically check if vacuum becomes reachable locally
- ⚪ Valetudo compatibility — monitor if X20+ (c102gl) gets rooting support
- ⚪ Home Assistant integration — MQTT or REST sensor for HA
- ⚪ Notification system — Telegram alerts for cleaning complete, errors, consumable low
- ⚪ Energy estimation — track cleaning time × estimated wattage for power consumption
- ⚪ Floor plan editor — manual room layout in dashboard (drag & drop)
- ⚪ vacuum-extend service (siid 4) — investigate writable properties found in official spec:
  - piid 5 = mop-mode (1=Low, 2=Medium, 3=High) — actual water level control!
  - piid 11 = break-point-restart (0=Close, 1=Open) — resume after charging
  - piid 12 = carpet-press (0=Close, 1=Open) — carpet boost
  - piid 27 = child-lock (0=Close, 1=Open)
  - piid 16 = clean-rags-tip (minutes, 0-120) — mop wash reminder interval
- ⚪ vacuum-extend piid 10 (clean-extend-data, write-only string) — this is likely the room cleaning param!
  Format: probably JSON with segments, fan level, water level. Worth testing with clean_rooms_miot().

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
- ✅ Fan speed MIoT property bug fix — `set_fan_speed()` was writing to siid 2 piid 2 (device fault, read-only!). Official MIoT spec confirms: piid 2 = fault, piid 3 = mode/fan speed (0=Silent, 1=Basic, 2=Strong, 3=Full Speed). Fixed read and write paths. Added 5 new tests confirming correct piid usage. (2026-03-31)
- ✅ Status fan_speed parsing corrected — was mapping piid 2 (fault code) to fan speed display. Now correctly reads piid 3 for fan speed and stores piid 2 as `fault_code`. (2026-03-31)
- ✅ MIOT_SPEC corrected — `fan_level` now points to piid 3, `fault_code` added for piid 2, `dry_left_time` added for piid 5 (was wrongly called `sweep_type`). (2026-03-31)
- ✅ Dashboard history section: fixed "--" for zero/falsy values — added `total_clean_duration_display` field to `clean_history()` (e.g. "2h 10min"), fixed JS to use `??` null-coalescing so `0` shows as `0` not `--`, fixed total-time label (was incorrectly appending `h` to a minutes value).
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
