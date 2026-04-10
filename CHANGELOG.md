# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
