# xiao — Backlog & Roadmap

## Priority Legend
- 🔴 P1 — Bug / broken functionality
- 🟠 P2 — Important improvement
- 🔵 P3 — Nice to have
- ⚪ P4 — Research / exploration

## Active Bugs
- 🔴 Room-specific cleaning still needs on-device verification — `clean_rooms_miot()` now preloads `siid 4 piid 10` `clean-extend-data` and then calls official `siid 2 aiid 3`, but actual X20+ hardware behavior still needs confirmation after this sequence change. (Updated 2026-04-08)
- 🔴 FIXED: `set_fan_speed()` was writing to siid 2 piid 2 (device fault, read-only!) instead of piid 3 (mode/fan). This means every `xiao speed set` command was attempting to write a fault code. Also `status()` was mapping piid 2 (fault) → `fan_speed` display, causing garbage values. Fixed 2026-03-31.
- 🔴 FIXED: `set_water_level()` was writing to siid 18 piid 1 (mop-life-level, READ-ONLY %) instead of siid 4 piid 5 (mop-mode, 1=Low, 2=Medium, 3=High). Every water level command was corrupting mop consumable tracking. Also `water_level()` returned a stub string instead of reading from the device. Fixed 2026-04-02.
- 🔴 FIXED: `status()` mapped state 13 → "In Dock" but official MIoT spec says 13 = "Charging Completed". Fixed 2026-04-02.

## Improvements Planned
- 🟠 Dashboard: clean up lower sections (Audio, Clean Log Raw, All Properties) — too verbose, collapse by default
- 🔵 Dashboard: add dark/light theme toggle
- 🔵 CLI: `xiao rooms rename <id> <name>` — interactive room renaming
- 🔵 CLI: `xiao schedule` — view schedules in a nice table
- 🔵 Sweep type decoding — raw values (448, 467, 472) — NOTE: per official MIoT spec, siid 2 piid 5 is `dry-left-time` (minutes), NOT sweep type. The 448/467/472 values may have been fault codes from piid 2.

## Research / Exploration
- ⚪ Map extraction — MITM Mi Home app traffic to find decryption key for cloud map data
- ⚪ Room IDs verification — map room IDs to actual room names from Mi Home app
- ⚪ **clean-logs (siid 12) corrected from official miot-spec.org JSON (2026-04-07):**
  - piid 1 = `first-clean-time` (unix timestamp) — **NOT** `last-clean-time`
  - piid 2 = `total-clean-time` (minutes)
  - piid 3 = `total-clean-times` (count)
  - piid 4 = `total-clean-area`
  - Implication: current cloud API/spec does not expose a dedicated `last-clean-date` field for c102gl via siid 12; any real per-run history likely needs app/cloud log endpoints or map/log filenames from siid 4 piid 9.
- ⚪ **vacuum-extend (siid 4) — fully mapped from official miot-spec.org JSON (2026-04-02):**
  - piid 4 = cleaning-mode (0=Quiet, 1=Standard, 2=Medium, 3=Strong) — READ-ONLY mirror of fan mode
  - piid 5 = mop-mode / water level (1=Low, 2=Medium, 3=High) — **WRITABLE** ✅ Now implemented
  - piid 6 = waterbox-status (0=No, 1=Yes) — reads whether water box is attached
  - piid 7 = task-status (uint8 0-255) — unknown semantics
  - piid 10 = clean-extend-data (string, **write-only**) — likely the room cleaning JSON param!
  - piid 11 = break-point-restart (0=Off, 1=On) — resume after charging — writable
  - piid 12 = carpet-press (0=Off, 1=On) — carpet boost — writable
  - piid 16 = clean-rags-tip (0-120 minutes) — mop wash reminder — writable
  - piid 17 = keep-sweeper-time (int32 minutes) — unknown
  - piid 18 = faults (string) — extended fault string
  - piid 27 = child-lock (0=Off, 1=On) — writable
  - piid 34 = smart-wash-switch (0=Off, 1=On) — smart mop wash
  - piid 36 = carpet-escape (1=Escape, 2=Auto) — carpet avoidance mode
- ⚪ **Room cleaning deep dive:** Official spec: `siid 2 aiid 3 = start-room-sweep`, in=[piid 4 (Room IDs string)]. The piid 4 (room-ids) has `access: []` meaning NO standalone read/write — it only works as an action param. Next step: test `clean_rooms_miot()` with piid 4 value as comma-separated string like "3,8,7,6". Also try `clean-extend-data` (siid 4 piid 10) as alternative path — write JSON before calling start-sweep.
- ⚪ **Room cleaning research update (2026-04-08):**
  - Official spec page for `xiaomi.vacuum.c102gl` still points to `siid 2 aiid 3` (`start-room-sweep`) with room IDs passed as `piid 4` string.
  - `hass-xiaomi-miot` README example shows Dreame/Xiaomi custom room cleaning via `siid 4 aiid 1` with params `piid 1 = 18` and `piid 10 = clean-extend-data`, where `clean-extend-data` is JSON under `selects`.
  - `dreame-vacuum` issue #910 logs show the `selects` rows encode at least room id, repeat count, fan mode, water mode, and explicit order: e.g. `[[1,1,3,1,1],[3,1,3,1,2], ...]`.
  - `openHAB` miio binding docs list both `vacuum-start-room-sweep` and `vacuum-extend-start-clean` actions for `xiaomi.vacuum.c102gl`, which supports the idea that both paths exist on X20+.
  - Community reports still describe `code=0` / accepted actions that do nothing, so success responses alone are not proof of movement.
- ⚪ **X20+ / c102gl community notes (2026-04-08):**
  - An ioBroker forum thread reports X20+ exposes `map-req` / `update-map`, but room-id extraction remains unclear for some users even with the official spec.
  - No clear Valetudo support signal for `xiaomi.vacuum.c102gl` turned up in this pass; keep this as watch-only research, not an actionable integration path yet.
- ⚪ **Session blocker (2026-04-08):**
  - This sandbox allows editing tracked files but denies writes inside `.git/`. `git add` / `git commit` failed with `fatal: Unable to create '.git/index.lock': Operation not permitted`, so this session could not create the requested local commit.
- ⚪ **Test-suite findings (2026-04-09):**
  - Full `pytest tests/ -v` currently still has 8 unrelated failures in `tests/test_cloud_vacuum.py`.
  - Failing areas: status parsing / fan-speed decoding regressions, plus missing `total_clean_duration_display` in `clean_history()`.
  - These pre-existing failures are outside the token-refresh scope and should be handled as a separate bugfix pass.
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
- ✅ Device list token auto-refresh — `XiaomiCloud.get_devices()` now catches `TokenExpiredError`, refreshes cloud tokens via browser CDP helper, and retries once before surfacing the error. This closes the remaining gap where setup/device listing could still fail on expired Xiaomi cloud sessions even though RPC/property helpers already retried. Added regression tests for both refresh-success and refresh-failure paths. (2026-04-09)
- ✅ Room cleaning reliability improvement — `clean_rooms_miot()` now preloads `vacuum-extend` `clean-extend-data` (`siid 4 piid 10`) using a `selects` payload derived from room order, repeat count, current fan mode, and current water mode, then calls the official `siid 2 aiid 3` room-sweep action. CLI `xiao clean --room ... --repeat N` now forwards `repeat` into that MIoT path instead of silently dropping it. Added regression tests. Hardware verification still pending. (2026-04-08)
- ✅ Clean history / first-clean-time mapping fix — `siid 12 piid 1` was incorrectly treated as `last-clean-time`, which made `last_clean_date` stale/misleading. Official MIoT spec confirms siid 12 is `clean-logs`: piid 1 = `first-clean-time`, piid 2 = `total-clean-time`, piid 3 = `total-clean-times`, piid 4 = `total-clean-area`. Updated `clean_history()`, `last_clean()`, and history scan output to expose `first_clean_date` and correct aggregate totals instead of fake last-run fields. Added regression tests. (2026-04-07)
- ✅ Water level MIoT property bug fix — `set_water_level()` was writing to siid 18 piid 1 (mop-life-level, READ-ONLY %) instead of siid 4 piid 5 (mop-mode, writable). Official MIoT spec confirms: siid 4 piid 5 = `mop-mode` (1=Low, 2=Medium, 3=High). Also fixed `water_level()` to actually read from the device instead of returning stub string. Added 7 new tests. (2026-04-02)
- ✅ Status 13 corrected — `status()` mapped state 13 → "In Dock" but official MIoT spec says 13 = "Charging Completed". Fixed with test. (2026-04-02)
- ✅ MIOT_SPEC extended — Added mop-mode, break-point-restart, carpet-press, child-lock, clean-rags-tip, clean-extend-data to MIOT_SPEC dict. Updated module comments to reflect siid 4 = vacuum-extend (not clean-log). (2026-04-02)
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
