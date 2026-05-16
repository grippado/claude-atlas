"""Smoke test for the published .pre-commit-hooks.yaml.

Validates the shape so we don't ship a broken hook config to consumers.
The actual `pre-commit` framework does its own schema validation; this is
just a fast guard against typos.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_HOOKS_FILE = Path(__file__).resolve().parent.parent / ".pre-commit-hooks.yaml"
_REQUIRED_KEYS = {"id", "name", "entry", "language"}


def test_hooks_file_exists() -> None:
    assert _HOOKS_FILE.is_file(), "missing .pre-commit-hooks.yaml at repo root"


def test_hooks_file_is_valid_yaml_list() -> None:
    data = yaml.safe_load(_HOOKS_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 1


def test_each_hook_has_required_keys_and_entrypoint() -> None:
    data = yaml.safe_load(_HOOKS_FILE.read_text(encoding="utf-8"))
    seen_ids: set[str] = set()
    for hook in data:
        assert _REQUIRED_KEYS.issubset(hook.keys()), (
            f"hook {hook.get('id')!r} missing required keys: "
            f"{_REQUIRED_KEYS - hook.keys()}"
        )
        assert hook["entry"].startswith("claude-atlas"), (
            f"hook {hook['id']!r} entry must invoke the claude-atlas CLI"
        )
        assert hook["language"] == "python"
        assert hook["id"] not in seen_ids, f"duplicate hook id: {hook['id']}"
        seen_ids.add(hook["id"])


def test_default_hook_id_is_claude_atlas() -> None:
    data = yaml.safe_load(_HOOKS_FILE.read_text(encoding="utf-8"))
    ids = [h["id"] for h in data]
    assert ids[0] == "claude-atlas", (
        "the first hook should be the default 'claude-atlas' id; the README "
        "documents this as the recommended entry point"
    )
