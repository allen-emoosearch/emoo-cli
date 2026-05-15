"""Output formatters using rich for pretty-printing API results."""

import json
import re
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()
# For JSON output, use plain print to avoid rich control chars in pipes
plain_console = Console(force_terminal=False)

# Columns to prioritize in table view; others are hidden to avoid unreadable wide tables
_PRIORITY_COLS = {
    'id', 'app_doc_id', 'title', 'url', 'name', 'content', 'content_type',
    'created_at', 'updated_at', 'app_created_at', 'app_updated_at',
    'open_id', 'user_id', 'ws_username', 'ws_user_type', 'email', 'mobile_num',
    'chat_id', 'message_id', 'complete_response',
}

# Columns that should not wrap
_NO_WRAP_COLS = {'mobile_num', 'email', 'ws_user_type', 'id', 'user_id', 'chat_id', 'message_id'}

_ISO_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


def _format_cell(value, col_name: str = "") -> str:
    """Format a cell value for display: shorten timestamps, truncate long IDs."""
    s = str(value) if value is not None else ""
    if not s:
        return s
    # Shorten ISO timestamps: 2025-04-23T09:07:53... → 2025-04-23 09:07
    if _ISO_PATTERN.match(s):
        return s[:16].replace('T', ' ')
    # Truncate long open_id: open_TjTotdpKfgmZ5fSlGyn8phTVFQIF77P3 → open_TjTotdp...
    if col_name == 'open_id' and len(s) > 16:
        return s[:12] + '...'
    return s


def _is_iso_timestamp(s: str) -> bool:
    return bool(_ISO_PATTERN.match(s))


def _detect_no_wrap_cols(results: list[dict], keys: list[str]) -> set[str]:
    """Detect columns that should not wrap: numeric IDs, emails, short codes."""
    no_wrap = set()
    if not results:
        return no_wrap
    sample = results[:5]
    for k in keys:
        if k in _NO_WRAP_COLS:
            no_wrap.add(k)
            continue
        vals = [str(r.get(k, "")) for r in sample if r.get(k) is not None]
        if not vals:
            continue
        # All-numeric or short numeric-like
        if all(v.replace('-', '').replace('+', '').isdigit() for v in vals if v):
            no_wrap.add(k)
        # Email
        if any('@' in v for v in vals):
            no_wrap.add(k)
    return no_wrap


def output(data: dict, as_json: bool = False, columns: Optional[list[str]] = None) -> None:
    """Main output dispatcher."""
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        _pretty(data, columns=columns)


def _pretty(data: dict, columns: Optional[list[str]] = None) -> None:
    """Try to pretty-print a paginated response."""
    inner = data.get("data", data)

    if isinstance(inner, dict) and "results" in inner:
        _paginated(inner, columns=columns)
    elif isinstance(inner, list):
        _list(inner, columns=columns)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def _paginated(data: dict, columns: Optional[list[str]] = None) -> None:
    """Render paginated results as a table."""
    results = data.get("results", [])
    total = data.get("total", len(results))
    page_size = data.get("page_size", "")
    current_page = data.get("current_page", "")

    if not results:
        console.print("[dim]无数据[/dim]")
        return

    if isinstance(results[0], dict):
        keys = list(results[0].keys())
        # User-specified columns take priority, then priority filter, then all keys
        if columns:
            keys = [k for k in columns if k in results[0]]
        elif len(keys) > 6:
            keys = [k for k in keys if k in _PRIORITY_COLS]
        no_wrap_cols = _detect_no_wrap_cols(results, keys)
        table = Table(title=f"共 {total} 条 (每页 {page_size}, 第 {current_page} 页)")

        for k in keys:
            table.add_column(k, style="cyan", overflow="fold", no_wrap=(k in no_wrap_cols))

        for row in results:
            table.add_row(*[_truncate(_format_cell(row.get(k, ""), k)) for k in keys])

        if columns is None and len(results[0]) > len(keys):
            console.print("[dim](部分列已隐藏，使用 --json 查看完整数据，或 --columns 指定列)[/dim]")

        console.print(table)


def _list(data: list, columns: Optional[list[str]] = None) -> None:
    """Render a simple list."""
    if not data:
        console.print("[dim]无数据[/dim]")
        return

    if isinstance(data[0], dict):
        keys = list(data[0].keys())
        if columns:
            keys = [k for k in columns if k in data[0]]
        no_wrap_cols = _detect_no_wrap_cols(data, keys)
        table = Table()

        for k in keys:
            table.add_column(k, style="cyan", overflow="fold", no_wrap=(k in no_wrap_cols))

        for row in data:
            table.add_row(*[_truncate(_format_cell(row.get(k, ""), k)) for k in keys])

        console.print(table)
    else:
        for item in data:
            console.print(str(item))


def _truncate(value, max_len: int = 200) -> str:
    s = str(value) if value is not None else ""
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def success(data: dict, as_json: bool = False) -> None:
    """Print a success response from non-list endpoints."""
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        inner = data.get("data", data)
        if isinstance(inner, dict) and len(inner) <= 10:
            table = Table(show_header=True)
            table.add_column("Key", style="bold green")
            table.add_column("Value")
            for k, v in inner.items():
                table.add_row(k, str(v))
            console.print(table)
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))


def token_status(cfg: dict) -> None:
    """Render token status info."""
    table = Table(title="Auth Status")
    table.add_column("Key", style="bold green")
    table.add_column("Value")

    if cfg.get("access_token"):
        import time
        expires = cfg.get("expires_at", 0)
        remaining = max(0, int(expires - time.time()))
        table.add_row("Token", cfg["access_token"][:20] + "...")
        table.add_row("剩余有效时间", f"{remaining}s ({remaining // 60}min)")
        table.add_row("Base URL", cfg.get("base_url", "N/A"))
        table.add_row("Default User ID", cfg.get("default_user_id", "未设置"))
        if cfg.get("default_user_name"):
            table.add_row("Default User Name", cfg["default_user_name"])
        table.add_row("", "")
        table.add_row("需要 --user-id 的命令", "data search / get, chat, contact, message push, base")
        table.add_row("设置默认值", "emoo auth set-default-user-id <open_id>")
        table.add_row("环境变量", "export EMOO_USER_ID=<open_id>")
    else:
        table.add_row("状态", "未登录")
    console.print(table)
