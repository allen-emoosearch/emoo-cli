"""Output formatters using rich for pretty-printing API results."""

import json
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()
# For JSON output, use plain print to avoid rich control chars in pipes
plain_console = Console(force_terminal=False)


def output(data: dict, as_json: bool = False) -> None:
    """Main output dispatcher."""
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        _pretty(data)


def _pretty(data: dict) -> None:
    """Try to pretty-print a paginated response."""
    inner = data.get("data", data)

    if isinstance(inner, dict) and "results" in inner:
        _paginated(inner)
    elif isinstance(inner, list):
        _list(inner)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def _paginated(data: dict) -> None:
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
        table = Table(title=f"共 {total} 条 (每页 {page_size}, 第 {current_page} 页)")

        for k in keys:
            table.add_column(k, style="cyan", overflow="fold")

        for row in results:
            table.add_row(*[_truncate(row.get(k, "")) for k in keys])

        console.print(table)


def _list(data: list) -> None:
    """Render a simple list."""
    if not data:
        console.print("[dim]无数据[/dim]")
        return

    if isinstance(data[0], dict):
        keys = list(data[0].keys())
        table = Table()

        for k in keys:
            table.add_column(k, style="cyan", overflow="fold")

        for row in data:
            table.add_row(*[_truncate(row.get(k, "")) for k in keys])

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
    else:
        table.add_row("状态", "未登录")
    console.print(table)
