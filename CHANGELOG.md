# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0](https://github.com/dacrypt/xiao/compare/v0.6.5...v0.7.0) (2026-05-12)


### Added

* add Mission Control advanced X20+ settings ([35ed6a3](https://github.com/dacrypt/xiao/commit/35ed6a3d5eb50c56ed59ea752c96746d6cd1583c))
* add vacuum-extend toggle commands ([3774dc7](https://github.com/dacrypt/xiao/commit/3774dc7000978b4ccc06625eddb7d1debeba11a5))
* **auth:** self-manage Chromium profile for silent token refresh ([bf59014](https://github.com/dacrypt/xiao/commit/bf590143a7b154615ddd3ad21867d1115a13de68))
* **cli:** add GitHub star CTA across three surfaces ([907778b](https://github.com/dacrypt/xiao/commit/907778bfc4c4c400505e78b5e366d7db48e06998))
* **cli:** add rooms rename command with TDD coverage ([#1](https://github.com/dacrypt/xiao/issues/1)) ([4a3e0d2](https://github.com/dacrypt/xiao/commit/4a3e0d28777a25b978366c86d08993b4b94e959d))
* **cli:** ergonomics — default command, XIAO_DEBUG, doctor, completion docs ([ccd7b47](https://github.com/dacrypt/xiao/commit/ccd7b47b893f783e721483da2910e9d8cae4e49c))
* collapse verbose dashboard diagnostics ([59b2800](https://github.com/dacrypt/xiao/commit/59b28009562ad6f142cd48de5d564f9d589b6c8d))
* collapse verbose dashboard diagnostics ([dad7fad](https://github.com/dacrypt/xiao/commit/dad7fad06363113e06730913162598750610fe9d))
* **dashboard:** add advanced x20+ settings controls ([6fedad5](https://github.com/dacrypt/xiao/commit/6fedad553357e75a0e518574d6362d26d85fc825))
* **docker:** publish OCI image to GHCR on every release ([f149a5f](https://github.com/dacrypt/xiao/commit/f149a5fdceb20813129bb89b8ef7e5ae4436140d))
* **mcp:** add optional MCP server — `xiao mcp` ([d561216](https://github.com/dacrypt/xiao/commit/d5612165cc1630290dfdfddcadf41d0e81399ea2))
* **plugin:** make xiao a valid Claude Code plugin for marketplace submission ([#7](https://github.com/dacrypt/xiao/issues/7)) ([d64e904](https://github.com/dacrypt/xiao/commit/d64e9044072a33abb5f588b80af240af3901c40a))
* **settings:** add vacuum-extend toggle commands ([0da507d](https://github.com/dacrypt/xiao/commit/0da507d682184420d0da1d6d21fff6be57462f8f))


### Fixed

* add persistent Mission Control theme toggle ([d0152bc](https://github.com/dacrypt/xiao/commit/d0152bc292dd63552c479ea48225be77123e4667))
* align history surfaces with clean-log totals ([551b73a](https://github.com/dacrypt/xiao/commit/551b73a729f0eff4dd29e7b9f9c4c7f9fd6dd76b))
* align history surfaces with clean-log totals ([b474631](https://github.com/dacrypt/xiao/commit/b47463160f33b4d15c65d14aeb935c6b3739c9a5))
* **cli:** streamline schedule viewing ([7ab0f58](https://github.com/dacrypt/xiao/commit/7ab0f5873bb21f4086f2ac018b85740a41b38af4))
* **dashboard:** add persistent theme toggle ([a4845ca](https://github.com/dacrypt/xiao/commit/a4845ca8af795b778704c38cf0e3287b01382c50))
* **docker:** multi-stage build with gcc for netifaces ([06105b7](https://github.com/dacrypt/xiao/commit/06105b7422315fee1d492893f0fc49615da73ac3))
* **history:** expose estimated cleaning energy from clean logs ([8b90a70](https://github.com/dacrypt/xiao/commit/8b90a70bbe12be1d8355c67ff0894be65845b0cc))
* **history:** expose estimated cleaning energy from clean logs ([74a203a](https://github.com/dacrypt/xiao/commit/74a203a6280555734bf6beb396d784e8872eb537))
* keep state 21 as WashingMopPause ([48b2f33](https://github.com/dacrypt/xiao/commit/48b2f33e977ff4f298f20156b0957fc705d92993))
* **settings:** add carpet avoidance mode ([#21](https://github.com/dacrypt/xiao/issues/21)) ([04431c2](https://github.com/dacrypt/xiao/commit/04431c260a1925070407d37f23014ea60ba1339c))
* **settings:** add clean-rags tip interval control ([#20](https://github.com/dacrypt/xiao/issues/20)) ([44c6993](https://github.com/dacrypt/xiao/commit/44c6993b17ff44c8503b7d88f731e7f8356ef099))
* **settings:** add smart wash toggle ([#19](https://github.com/dacrypt/xiao/issues/19)) ([173432e](https://github.com/dacrypt/xiao/commit/173432e8885bf6fab26472e87785fa84a60680f9))
* **status:** keep state 21 as WashingMopPause ([cabab18](https://github.com/dacrypt/xiao/commit/cabab185ccad785cea3369fe01d5eeea53dac56c))
* **status:** surface dry time instead of stale sweep type ([fa804ac](https://github.com/dacrypt/xiao/commit/fa804ac61760b5b9344c35c8624822c6775f1cf8))
* **status:** surface waterbox attachment status ([3630172](https://github.com/dacrypt/xiao/commit/3630172b2d7d4a6483e2cdcbca2d6dc4f7cfe2e9))
* streamline schedule viewing ([bec6556](https://github.com/dacrypt/xiao/commit/bec6556033ad82ad8c1c7ee0b147fa8570b77db6))
* surface dry time instead of stale sweep type ([ce95e75](https://github.com/dacrypt/xiao/commit/ce95e75061f1507d747e6be9a6d7f2eaac735429))
* surface waterbox attachment status ([a6a76cc](https://github.com/dacrypt/xiao/commit/a6a76ccc429ba1e6c7816746669f4e174b1a8378))
* verify room-clean commands actually leave the dock ([1f00d2c](https://github.com/dacrypt/xiao/commit/1f00d2c531ea382ff7ba1e19e50cde16ead85dde))
* verify room-clean commands actually leave the dock ([1c9ea15](https://github.com/dacrypt/xiao/commit/1c9ea15175b48fb23f10bfc014f8305572b72604))


### Documentation

* add 10s terminal demo GIF via vhs ([fa5034d](https://github.com/dacrypt/xiao/commit/fa5034dc8c5b984a7c5f8802a0c2d265e702bda8))
* add PRIVACY.md — no data collection, OSS, all local ([#8](https://github.com/dacrypt/xiao/issues/8)) ([4f3b08a](https://github.com/dacrypt/xiao/commit/4f3b08a78b24e5a23416251fd91dd084a2273610))
* document Conventional Commits for release-please automation ([5c5a271](https://github.com/dacrypt/xiao/commit/5c5a271c7a15177286ccf20035b7ab1923f3285f))
* make xiao agent-ready (AGENTS.md, llms.txt, --json, exit codes) ([#2](https://github.com/dacrypt/xiao/issues/2)) ([e884cd3](https://github.com/dacrypt/xiao/commit/e884cd354e1ff7b8542f10f1071ba74079195395))
* **publishing:** agent-registry distribution plan + paste-ready submission drafts ([#3](https://github.com/dacrypt/xiao/issues/3)) ([23816a5](https://github.com/dacrypt/xiao/commit/23816a5011e59906a5586f304b123cc6ebddd872))
* **publishing:** execute Tier-1 agent-registry submissions ([#5](https://github.com/dacrypt/xiao/issues/5)) ([79931d3](https://github.com/dacrypt/xiao/commit/79931d34e879ac79139a6bc9fddadfd463e1a41a))
* **publishing:** mark skills.sh published — @dacrypt/xiao-skill@0.1.0 ([#6](https://github.com/dacrypt/xiao/issues/6)) ([5f857e4](https://github.com/dacrypt/xiao/commit/5f857e4784af1453e57bebf5fa0acbf086d71046))

## [0.6.5](https://github.com/dacrypt/xiao/compare/v0.6.4...v0.6.5) (2026-05-12)

### Fixed

* **status:** surface the X20+ `waterbox-status` (`siid 4 piid 6`) across CLI and Mission Control so users can immediately see whether the mop water box is attached during mopping/setup diagnostics

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
