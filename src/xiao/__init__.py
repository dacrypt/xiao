"""xiao - CLI tool to control Xiaomi/Roborock robot vacuums."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: pyproject.toml (bumped by release-please).
    __version__ = version("xiao-cli")
except PackageNotFoundError:  # pragma: no cover - running from an unbuilt checkout
    __version__ = "0.0.0+unknown"
