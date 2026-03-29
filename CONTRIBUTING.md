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
5. Commit with a clear message
6. Push and open a Pull Request

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if needed
- Follow existing code style (enforced by ruff)

## MIoT Spec

If you're adding support for new device properties or actions, refer to the
[MIoT spec](https://home.miot-spec.com/) for your device model. The mapping
lives in `src/xiao/core/cloud_vacuum.py`.

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include your Python version, OS, and vacuum model
- For cloud API issues, include the error message (redact tokens/credentials)
