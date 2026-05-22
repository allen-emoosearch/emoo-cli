"""L3 universal API passthrough — covers 100% of the API surface."""

import json
import os
import sys

import click

from ..client import EmooClient
from ..errors import EmooError


@click.group()
def api():
    """通用 API 透传 — 调用任意 EMOO 端点 (L3 层).

    一条命令覆盖全部 API，无需等待封装。

    \b
    示例:
      emoo api GET /v1/apps
      emoo api GET "/v1/app/{key}/doc-groups?page_size=10"
      emoo api POST /v1/search -d '{"keyword":"test","page_size":5,"current_page":1}'
      emoo api GET /v1/auth/token -q "grant_type=client_credentials"
    """


def _parse_data(data_str: str) -> dict:
    """Parse -d/--data: JSON string, JSON from stdin ('-'), or JSON file path."""
    if data_str == "-":
        return json.load(sys.stdin)
    if os.path.isfile(data_str):
        with open(data_str, encoding="utf-8") as f:
            return json.load(f)
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        raise click.BadParameter(f"无法解析为 JSON: {data_str[:100]}")


def _parse_path(path: str):
    """Split a URL path into base path + query params dict."""
    if "?" in path:
        base, qs = path.split("?", 1)
        params = {}
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
        return base, params
    return path, None


@api.command(name="GET")
@click.argument("path")
@click.option("--dry-run", is_flag=True, help="预览请求而不执行")
@click.pass_context
def api_get(ctx, path, dry_run):
    """GET 透传.  PATH 可含 query string: /v1/apps?page_size=10."""
    _do_request(ctx, "GET", path, dry_run)


@api.command(name="POST")
@click.argument("path")
@click.option("-d", "--data", default=None, help="请求体 (JSON 字符串 / 文件路径 / '-' stdin)")
@click.option("--dry-run", is_flag=True, help="预览请求而不执行")
@click.pass_context
def api_post(ctx, path, data, dry_run):
    """POST 透传."""
    _do_request(ctx, "POST", path, dry_run, data=data)


@api.command(name="PUT")
@click.argument("path")
@click.option("-d", "--data", default=None, help="请求体 (JSON 字符串 / 文件路径 / '-' stdin)")
@click.option("--dry-run", is_flag=True, help="预览请求而不执行")
@click.pass_context
def api_put(ctx, path, data, dry_run):
    """PUT 透传."""
    _do_request(ctx, "PUT", path, dry_run, data=data)


@api.command(name="DELETE")
@click.argument("path")
@click.option("-d", "--data", default=None, help="请求体 (JSON 字符串 / 文件路径 / '-' stdin)")
@click.option("--dry-run", is_flag=True, help="预览请求而不执行")
@click.pass_context
def api_delete(ctx, path, data, dry_run):
    """DELETE 透传."""
    _do_request(ctx, "DELETE", path, dry_run, data=data)


def _do_request(ctx, method, path, dry_run, data=None):
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    base_path, query_params = _parse_path(path)
    body = _parse_data(data) if data else None

    if dry_run:
        dry = {"method": method, "path": base_path, "params": query_params}
        if body is not None:
            dry["body"] = body
        if ctx.obj.get("as_json"):
            click.echo(json.dumps(dry, ensure_ascii=False, indent=2))
        else:
            from rich.console import Console
            from rich.syntax import Syntax
            console = Console()
            console.print(f"[yellow]DRY-RUN[/yellow] {method} {base_path}")
            if query_params:
                console.print(f"  Query: {json.dumps(query_params, ensure_ascii=False)}")
            if body is not None:
                console.print(f"  Body:")
                console.print(Syntax(json.dumps(body, ensure_ascii=False, indent=2), "json"))
        return

    # Strip /v1 prefix if present — base URL already includes /open-api/v1
    if base_path.startswith("/v1/"):
        base_path = base_path[3:]
    elif base_path.startswith("v1/"):
        base_path = base_path[2:]

    try:
        resp = client.request(method, base_path, params=query_params, body=body)
    except EmooError as e:
        if ctx.obj.get("as_json"):
            sys.stderr.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
            sys.exit(1)
        raise click.ClickException(str(e))

    if ctx.obj.get("as_json"):
        click.echo(json.dumps(resp, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        console = Console()
        code = resp.get("code", "?")
        msg = resp.get("message", "")
        console.print(f"[dim]HTTP 200  code={code}  {msg}[/dim]")
        data_obj = resp.get("data")
        if isinstance(data_obj, dict) and "results" in data_obj:
            from rich.table import Table
            results = data_obj.pop("results")
            meta_str = ", ".join(f"{k}={v}" for k, v in data_obj.items())
            console.print(f"[dim]{meta_str}[/dim]")
            if results and isinstance(results[0], dict):
                table = Table(title="Results")
                keys = list(results[0].keys())[:6]
                for k in keys:
                    table.add_column(k)
                for r in results[:50]:
                    table.add_row(*[str(r.get(k, ""))[:80] for k in keys])
                console.print(table)
                if len(results) > 50:
                    console.print(f"[dim]... 还有 {len(results) - 50} 条[/dim]")
            else:
                console.print(results)
        else:
            formatted = json.dumps(resp, ensure_ascii=False, indent=2)
            from rich.syntax import Syntax
            console.print(Syntax(formatted, "json"))
