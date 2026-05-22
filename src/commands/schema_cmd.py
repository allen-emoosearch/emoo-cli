"""Schema introspection: look up endpoint params, body, response, permissions."""

import json
import os

import click


SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "endpoints.json")


def _load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _find_endpoint(name: str) -> tuple:
    """Find endpoint by name, supporting fuzzy matching. Returns (key, info)."""
    data = _load_schema()

    if name in data:
        return name, data[name]

    candidates = [(k, v) for k, v in data.items() if name in k]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        names = [c[0] for c in candidates]
        raise click.BadParameter(f"'{name}' 匹配到多个端点: {', '.join(names)}，请使用完整名称")

    raise click.BadParameter(f"未找到端点: '{name}'。使用 emoo schema list 查看所有端点")


def _print_endpoint(key, info, ctx):
    """Print detailed info about one endpoint."""
    if ctx.obj.get("as_json"):
        click.echo(json.dumps({"name": key, **info}, ensure_ascii=False, indent=2))
        return

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()

    auth_tags = []
    if info.get("auth_required"):
        auth_tags.append("Bearer Token")
    if info.get("user_id_required"):
        auth_tags.append("Emoo-User-Id")
    auth_str = " + ".join(auth_tags) if auth_tags else "无需认证"

    console.print(Panel(
        f"[bold cyan]{info['method']}[/bold cyan] {info['path']}\n"
        f"认证: {auth_str}\n"
        f"{info.get('description', '')}",
        title=f"[bold]{key}[/bold]",
    ))

    if info.get("path_params"):
        pt = Table(title="路径参数")
        pt.add_column("参数", style="green")
        pt.add_column("类型")
        pt.add_column("必填")
        pt.add_column("说明")
        for p in info["path_params"]:
            pt.add_row(p["name"], p["type"], "是" if p.get("required") else "否",
                       p.get("desc", ""))
        console.print(pt)
        console.print()

    if info.get("params"):
        pt = Table(title="Query 参数")
        pt.add_column("参数", style="green")
        pt.add_column("类型")
        pt.add_column("必填")
        pt.add_column("说明")
        for p in info["params"]:
            req = "是" if p.get("required") == True else ("条件" if p.get("required") else "否")
            pt.add_row(p["name"], p["type"], req, p.get("desc", ""))
        console.print(pt)
        console.print()

    if info.get("body"):
        bt = Table(title="Body 参数 (JSON)")
        bt.add_column("参数", style="green")
        bt.add_column("类型")
        bt.add_column("必填")
        bt.add_column("说明")
        for p in info["body"]:
            req = "是" if p.get("required") == True else ("条件" if p.get("required") else "否")
            bt.add_row(p["name"], p["type"], req, p.get("desc", ""))
        console.print(bt)
        console.print()

    if info.get("response"):
        console.print("[bold]响应字段:[/bold]")
        for field, desc in info["response"].items():
            console.print(f"  [green]{field}[/green]: {desc}")
        console.print()

    if info.get("filter_fields"):
        console.print(f"[bold]可过滤字段:[/bold] {', '.join(info['filter_fields'])}")
    if info.get("filter_operators"):
        console.print(f"[bold]过滤运算符:[/bold] {', '.join(info['filter_operators'])}")
        console.print()

    console.print(f"  [dim]emoo api {info['method']} {info['path']}[/dim]")


@click.group(invoke_without_command=True)
@click.argument("endpoint", required=False)
@click.pass_context
def schema(ctx, endpoint):
    """API Schema 自省 — 查看端点参数、请求体、响应、权限.

    给 Agent "先查再调，不要猜字段" 的命脉。

    \b
    示例:
      emoo schema data.search    查看 search 端点详情
      emoo schema search          模糊匹配
      emoo schema list            列出所有端点
    """
    if endpoint is None:
        # No argument given — show help
        click.echo(ctx.get_help())
        return

    if endpoint == "list":
        _list_endpoints(ctx)
        return

    key, info = _find_endpoint(endpoint)
    _print_endpoint(key, info, ctx)


@schema.command("list")
@click.pass_context
def schema_list(ctx):
    """列出所有已知的 API 端点."""
    _list_endpoints(ctx)


def _list_endpoints(ctx):
    data = _load_schema()
    if ctx.obj.get("as_json"):
        click.echo(json.dumps(list(data.keys()), ensure_ascii=False, indent=2))
        return

    from rich.console import Console
    from rich.table import Table
    console = Console()

    by_prefix: dict[str, list] = {}
    for name, info in sorted(data.items()):
        prefix = name.split(".")[0]
        by_prefix.setdefault(prefix, []).append((name, info))

    for prefix, items in sorted(by_prefix.items()):
        table = Table(title=f"{prefix} ({len(items)} endpoints)")
        table.add_column("名称", style="cyan")
        table.add_column("方法")
        table.add_column("路径")
        table.add_column("说明")
        for name, info in items:
            table.add_row(name, info["method"], info["path"],
                          (info.get("description", "") or "")[:55])
        console.print(table)
        console.print()
