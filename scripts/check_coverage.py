#!/usr/bin/env python3
"""Verify that every endpoint in src/commands/endpoints.json has an L2 command.

Run after `python scripts/sync_api_docs.py` to catch newly added API operations
that are registered in the schema but not yet wrapped by a CLI command.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cli import cli  # noqa: E402


def collect(group, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    for name, command in group.commands.items():
        path = prefix + (name,)
        paths.add(path)
        if hasattr(command, "commands"):
            paths |= collect(command, path)
    return paths


# Keys whose CLI command name differs from the registry suffix.
SPECIAL = {
    "auth.token": ("auth", "login"),
    "chat.agent-message": ("chat", "agent-send"),
}


def main() -> int:
    registry = json.loads((ROOT / "src" / "commands" / "endpoints.json").read_text(encoding="utf-8"))
    paths = collect(cli)
    missing: list[tuple[str, tuple[str, ...]]] = []

    for key in registry:
        if key in SPECIAL:
            want = SPECIAL[key]
        elif key.startswith("base.permission-"):
            want = ("base", "permission", key.split("-", 1)[1])
        else:
            prefix, suffix = key.split(".", 1)
            want = (prefix, suffix)
        if want not in paths:
            missing.append((key, want))

    print(f"registry: {len(registry)} keys | click commands: {len(paths)} | missing: {len(missing)}")
    for key, want in missing:
        print(f"  ✗ {key} -> emoo {' '.join(want)}")
    if missing:
        print("\n新增端点在 KEY_MAP 中登记后，还需要在 src/commands/ 下补对应 L2 命令。")
        return 1
    print("✅ 所有已登记端点都有对应的 L2 命令")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
