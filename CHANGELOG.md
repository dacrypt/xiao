# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.4](https://github.com/dacrypt/xiao/compare/v0.6.3...v0.6.4) (2026-05-11)

### Fixed

* **status:** keep X20+ state `21` as the official `WashingMopPause` label across CLI/Mission Control surfaces while preserving separate clean/dirty-water recovery guidance and the tank-reset heuristic

## [0.6.3](https://github.com/dacrypt/xiao/compare/v0.6.2...v0.6.3) (2026-05-08)

### Fixed

* **history:** add an explicit estimated cleaning energy readout (`kWh @ 75W`) from X20+ clean-log totals so Mission Control and CLI history surfaces expose lifetime power consumption without pretending it is measured device telemetry

## [0.6.2](https://github.com/dacrypt/xiao/compare/v0.6.1...v0.6.2) (2026-05-01)

### Fixed

* **room-cleaning:** stop treating X20+ room-clean `code=0` accepts as guaranteed movement by verifying follow-up status across CLI, Mission Control, and MCP, surfacing a warning when the robot still looks docked/charging, and emitting exit code `80` for the CLI's clearly unresponsive case

## [0.6.1](https://github.com/dacrypt/xiao/compare/v0.6.0...v0.6.1) (2026-04-30)

### Fixed

* **history:** align Mission Control and CLI history surfaces with the X20+ clean-log fields (`first_clean_date`, total time/count/area) so they stop pretending cloud aggregate data is a last-run record

## [0.6.0](https://github.com/dacrypt/xiao/compare/v0.5.3...v0.6.0) (2026-04-29)

### Added

* **dashboard:** let Mission Control read and change the advanced X20+ `vacuum-extend` controls (`resume-after-charge`, `carpet-boost`, `child-lock`, `smart-wash`, `carpet-avoidance`, and `clean-rags-tip`) so web users no longer need to drop back to CLI commands for those settings

## [0.5.3](https://github.com/dacrypt/xiao/compare/v0.5.2...v0.5.3) (2026-04-28)

### Fixed

* **settings:** add a validated `carpet-avoidance` mode (`avoid`/`auto`, plus `escape` compatibility) for the X20+ `vacuum-extend` service and include it in the dashboard settings snapshot so carpet handling no longer requires raw MIoT enum writes

## [0.5.2](https://github.com/dacrypt/xiao/compare/v0.5.1...v0.5.2) (2026-04-27)

### Fixed

* **settings:** add a validated `clean-rags-tip` minutes control (`0-120`) for the X20+ `vacuum-extend` service and include it in the settings snapshot so mop-wash reminders no longer require raw MIoT writes

## [0.5.1](https://github.com/dacrypt/xiao/compare/v0.5.0...v0.5.1) (2026-04-26)

### Fixed

* **settings:** add the X20+ `smart-wash` toggle as a cloud-backed `vacuum-extend` boolean (`siid 4 piid 34`) so base-station mop maintenance can be read and controlled from the CLI and settings API snapshot

## [0.5.0](https://github.com/dacrypt/xiao/compare/v0.4.4...v0.5.0) (2026-04-25)

### Added

* **settings:** add cloud-backed `resume-after-charge`, `carpet-boost`, and `child-lock` toggles so X20+ owners can read and change the most useful `vacuum-extend` boolean controls directly from the CLI

## [0.4.4](https://github.com/dacrypt/xiao/compare/v0.4.3...v0.4.4) (2026-04-24)

### Fixed

* **status:** replace stale dashboard sweep-type copy with the real MIoT dry-time-left field, show a drying countdown tag, and align the Mission Control state-13 label with `Charging Completed`

## [0.4.3](https://github.com/dacrypt/xiao/compare/v0.4.2...v0.4.3) (2026-04-23)

### Fixed

* **dashboard:** add a persistent dark/light theme toggle so Mission Control can switch to a brighter daytime palette without losing the existing dark glassmorphism default

## [0.4.2](https://github.com/dacrypt/xiao/compare/v0.4.1...v0.4.2) (2026-04-22)

### Fixed

* **cli:** make `xiao schedule` show the parsed schedule table by default and compress common cadence masks to `Every day`, `Weekdays`, `Weekends`, and `One time` for quicker terminal scanning

## [0.4.1](https://github.com/dacrypt/xiao/compare/v0.4.0...v0.4.1) (2026-04-21)


### Fixed

* **docker:** multi-stage build with gcc for netifaces ([06105b7](https://github.com/dacrypt/xiao/commit/06105b7422315fee1d492893f0fc49615da73ac3))

## [0.4.0](https://github.com/dacrypt/xiao/compare/v0.3.0...v0.4.0) (2026-04-21)


### Added

* **cli:** ergonomics — default command, XIAO_DEBUG, doctor, completion docs ([ccd7b47](https://github.com/dacrypt/xiao/commit/ccd7b47b893f783e721483da2910e9d8cae4e49c))
* **docker:** publish OCI image to GHCR on every release ([f149a5f](https://github.com/dacrypt/xiao/commit/f149a5fdceb20813129bb89b8ef7e5ae4436140d))

## [0.3.0](https://github.com/dacrypt/xiao/compare/v0.2.1...v0.3.0) (2026-04-21)


### Added

* **auth:** self-manage Chromium profile for silent token refresh ([bf59014](https://github.com/dacrypt/xiao/commit/bf590143a7b154615ddd3ad21867d1115a13de68))

## [0.2.1](https://github.com/dacrypt/xiao/compare/v0.2.0...v0.2.1) (2026-04-21)


### Documentation

* add 10s terminal demo GIF via vhs ([fa5034d](https://github.com/dacrypt/xiao/commit/fa5034dc8c5b984a7c5f8802a0c2d265e702bda8))
* document Conventional Commits for release-please automation ([5c5a271](https://github.com/dacrypt/xiao/commit/5c5a271c7a15177286ccf20035b7ab1923f3285f))

## [0.2.0](https://github.com/dacrypt/xiao/compare/v0.1.2...v0.2.0) (2026-04-21)


### Added

* **cli:** add GitHub star CTA across three surfaces ([907778b](https://github.com/dacrypt/xiao/commit/907778bfc4c4c400505e78b5e366d7db48e06998))
* **plugin:** make xiao a valid Claude Code plugin for marketplace submission ([#7](https://github.com/dacrypt/xiao/issues/7)) ([d64e904](https://github.com/dacrypt/xiao/commit/d64e9044072a33abb5f588b80af240af3901c40a))


### Documentation

* add PRIVACY.md — no data collection, OSS, all local ([#8](https://github.com/dacrypt/xiao/issues/8)) ([4f3b08a](https://github.com/dacrypt/xiao/commit/4f3b08a78b24e5a23416251fd91dd084a2273610))
* **publishing:** agent-registry distribution plan + paste-ready submission drafts ([#3](https://github.com/dacrypt/xiao/issues/3)) ([23816a5](https://github.com/dacrypt/xiao/commit/23816a5011e59906a5586f304b123cc6ebddd872))
* **publishing:** execute Tier-1 agent-registry submissions ([#5](https://github.com/dacrypt/xiao/issues/5)) ([79931d3](https://github.com/dacrypt/xiao/commit/79931d34e879ac79139a6bc9fddadfd463e1a41a))
* **publishing:** mark skills.sh published — @dacrypt/xiao-skill@0.1.0 ([#6](https://github.com/dacrypt/xiao/issues/6)) ([5f857e4](https://github.com/dacrypt/xiao/commit/5f857e4784af1453e57bebf5fa0acbf086d71046))

## [0.1.2] - 2026-04-21

### Changed

- Mission Control now collapses the verbose Audio, Clean Log (Raw), and All Properties sections by default so the main dashboard stays focused while diagnostics remain one click away

## [0.1.1] - 2026-04-10

### Added

- `xiao rooms rename <id> <name>` command for clearer room alias management

### Fixed

- Consumable reset support now includes mop pads
- Consumables CLI output now shows correct life and hours-left mapping for X20+ MIoT properties

## [0.1.0] - 2025-12-01

### Added

- CLI tool with full vacuum control (start/stop/dock/find)
- Room-specific and zone cleaning support
- Base station controls (mop wash, dry, dust collect, eject tray)
- Settings management (fan speed, water level, volume, DND)
- Consumable tracking with remaining life percentages
- Schedule viewer with parsed data
- Mission Control web dashboard with glassmorphism UI
- Cloud authentication with captcha OCR and email 2FA
- Auto token refresh via browser CDP
- TOML-based configuration with room aliases
- REST API for programmatic control
- Rich terminal output with formatted tables and panels
