"""claude-atlas: scan, map, and visualize your Claude Code setup."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("claude-atlas")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
