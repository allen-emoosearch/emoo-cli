#!/usr/bin/env python3
"""Read-only smoke test for the EMOO API surface used by the CLI.

Run from the project root after `pip install --force-reinstall .`:

    python scripts/smoke_test.py
    python scripts/smoke_test.py --json

The script uses the current ~/.emoo/config.json credentials. It only calls
read-only endpoints (plus an aggregate query), so it is safe to run against
production.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.client import EmooClient  # noqa: E402
from src.errors import EmooError  # noqa: E402


CASES = [
    ("app.list", "GET", "/apps", None, None),
    ("agent.list", "GET", "/agents", {"page_size": 1}, None),
    ("chat.list", "GET", "/chat", {"page_size": 1}, None),
    ("contact.list", "GET", "/ws-user", {"page_size": 1}, None),
    ("role.list", "GET", "/ws-groups", {"page_size": 1}, None),
    ("todo.list", "GET", "/work_item", {"page_size": 1}, None),
    ("todo.tag-list", "GET", "/work_item/tags", None, None),
    ("shortcut.list", "GET", "/shortcut", None, None),
    ("base.table-list", "GET", "/data/table", {"page_size": 1}, None),
    ("folder.list", "GET", "/data/folder/items", None, None),
    ("data.aggregate", "POST", "/search/aggregate", None, {"metric_type": "count"}),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()

    client = EmooClient()
    rows = []
    failures = 0
    for name, method, path, params, body in CASES:
        started = time.time()
        try:
            resp = client.request(method, path, params=params, body=body)
            elapsed = (time.time() - started) * 1000
            code = resp.get("code", 200)
            ok = code == 200
            detail = f"code={code}"
            if name == "data.aggregate":
                detail += f" total_docs={resp.get('data', {}).get('total_docs')}"
            rows.append({"name": name, "method": method, "path": path,
                         "ok": ok, "ms": round(elapsed), "detail": detail})
            if not ok:
                failures += 1
        except EmooError as exc:
            elapsed = (time.time() - started) * 1000
            failures += 1
            rows.append({"name": name, "method": method, "path": path,
                         "ok": False, "ms": round(elapsed),
                         "detail": f"{type(exc).__name__}: {exc.message}"})
        except Exception as exc:  # noqa: BLE001 - report every failure
            elapsed = (time.time() - started) * 1000
            failures += 1
            rows.append({"name": name, "method": method, "path": path,
                         "ok": False, "ms": round(elapsed), "detail": repr(exc)})

    if args.json:
        print(json.dumps({"passed": len(rows) - failures, "failed": failures,
                          "results": rows}, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            mark = "✅" if row["ok"] else "❌"
            print(f"{mark} {row['name']:18} {row['method']:5} {row['path']:28} "
                  f"{row['ms']:>5}ms  {row['detail']}")
        print(f"\n通过 {len(rows) - failures}/{len(rows)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
