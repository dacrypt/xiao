# Contributing to xiao

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/dacrypt/xiao.git
cd xiao

# Install dependencies (requires uv and Python 3.12+)
uv sync

# Install in editable mode
uv pip install -e .

# Install Playwright browsers (needed for cloud login)
uv run playwright install chromium
```

## Running Tests

```bash
uv run pytest tests/ -v
```

## Code Quality

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/xiao/
```

## Making Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and linting
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/) (see below)
6. Push and open a Pull Request

## Commit messages — Conventional Commits

Releases and the changelog are automated via
[release-please](https://github.com/googleapis/release-please). The next
version is computed from the commit prefixes since the last tag, so the
prefix you pick directly shapes the release. Use one of:

| Prefix       | When                                           | Release effect  |
|--------------|------------------------------------------------|-----------------|
| `feat:`      | User-visible new capability                    | Minor bump      |
| `fix:`       | User-visible bug fix                           | Patch bump      |
| `perf:`      | Performance improvement                        | Patch bump      |
| `refactor:`  | Internal restructuring, no behavior change     | Patch bump      |
| `docs:`      | Documentation only                             | Patch bump      |
| `chore:`     | Tooling / maintenance not worth a release note | No release      |
| `ci:`        | CI/CD config                                    | No release      |
| `test:`      | Tests only                                      | No release      |
| `style:`     | Formatting only                                 | No release      |

Breaking changes: add `!` after the type (`feat!: drop Python 3.11`) or a
`BREAKING CHANGE:` footer. Either triggers a major bump.

Optional scope in parentheses after the type — e.g. `feat(cli): add
--json flag`, `fix(cloud): retry on 429`. Scopes show up in the changelog.

Examples:

```
feat(cli): add `xiao zones` command
fix(cloud): handle empty consumable response
docs: clarify Chromium CDP setup in README
chore: bump dev dependencies
feat!: drop Python 3.11 support

BREAKING CHANGE: minimum supported Python is now 3.12.
```

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if needed
- Follow existing code style (enforced by ruff)
- The PR title should also follow Conventional Commits — squash merges use
  the PR title as the commit message, which release-please then parses

## MIoT Spec

If you're adding support for new device properties or actions, refer to the
[MIoT spec](https://home.miot-spec.com/) for your device model. The mapping
lives in `src/xiao/core/cloud_vacuum.py`.

## Source-Tree Layout

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
│   ├── token_refresh.py  # Token refresh via Chromium CDP (persistent session)
│   └── vacuum.py         # Local interface (unused in cloud mode)
├── dashboard/     # Web UI
│   ├── server.py  # FastAPI backend
│   └── index.html # Single-file glassmorphism frontend
└── ui/
    └── formatters.py  # Rich terminal formatters
```

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include your Python version, OS, and vacuum model
- For cloud API issues, include the error message (redact tokens/credentials)
