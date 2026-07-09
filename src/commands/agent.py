"""Agent 管理命令: agent list / create / get / update / delete."""

from __future__ import annotations

import click

from ..client import EmooClient
from ..formatters import output, success, _progress


@click.group("agent", help="Agent 管理 (第三方集成)")
def agent_group() -> None:
    pass


@agent_group.command("list")
@click.option("--page-size", default=20, type=int, help="每页数量 (1-200)")
@click.option("--current-page", default=1, type=int, help="页码")
@click.option("--agent-type", "-t", "agent_type", default=None, type=str,
              help="按类型过滤: webhook / dify / coze / timus")
@click.pass_context
def agent_list(ctx: click.Context, page_size: int, current_page: int, agent_type: str | None) -> None:
    """获取 agent 列表（分页）。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    params: dict = {"page_size": str(page_size), "current_page": str(current_page)}
    if agent_type:
        params["agent_type"] = agent_type
    resp = client.request("GET", "/agents", params=params)
    data = resp["data"]
    results = data.get("results", [])

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    total = data.get("total", 0)
    _progress(f"total={total}, page_size={data.get('page_size')}, current_page={data.get('current_page')}, "
              f"total_pages={data.get('total_pages')}")

    if not results:
        click.echo("暂无 Agent")
        return

    from rich.table import Table
    table = Table(title="Agent 列表")
    table.add_column("ws_agent_key", style="cyan", no_wrap=True)
    table.add_column("标题")
    table.add_column("类型")
    table.add_column("启用")
    table.add_column("描述")
    table.add_column("scope")
    table.add_column("创建时间")

    for a in results:
        table.add_row(
            a.get("ws_agent_key", ""),
            a.get("title", ""),
            a.get("agent_type", ""),
            "✅" if a.get("is_enabled") else "❌",
            (a.get("description") or ""),
            a.get("scope", ""),
            a.get("created_at", ""),
        )

    from rich.console import Console
    Console().print(table)


@agent_group.command("create")
@click.option("--title", "-n", "title", required=True, type=str, help="Agent 显示名称")
@click.option("--agent-type", "-t", "agent_type", required=True, type=str,
              help="集成类型: webhook / dify / coze / timus")
@click.option("--config", "-c", "config_json", required=True, type=str,
              help="集成配置 JSON (webhook 需 url/auth_type; dify/coze/timus 需 base_url+credentials)")
@click.option("--description", "-d", "description", default=None, type=str, help="描述")
@click.option("--disabled", is_flag=True, help="创建后禁用")
@click.option("--scope", "scope", default="public", type=str,
              help="可见范围: public / specified_ws_groups")
@click.option("--group-ids", "group_ids", default=None, type=str,
              help="scope=specified_ws_groups 时的角色 ID，逗号分隔")
@click.option("--dry-run", is_flag=True, help="预览请求，不实际执行")
@click.pass_context
def agent_create(ctx: click.Context, title: str, agent_type: str, config_json: str,
                 description: str | None, disabled: bool, scope: str,
                 group_ids: str | None, dry_run: bool) -> None:
    """创建 Agent。"""
    import json as _json
    config = _json.loads(config_json)

    body: dict = {
        "title": title,
        "agent_type": agent_type,
        "config": config,
        "is_enabled": not disabled,
    }
    if description:
        body["description"] = description
    if scope:
        body["scope"] = scope
    if group_ids:
        body["specified_ws_group_ids"] = [int(g.strip()) for g in group_ids.split(",")]

    if dry_run:
        click.echo(f"DRY-RUN POST /agents")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/agents", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@agent_group.command("get")
@click.argument("ws_agent_key", type=str)
@click.pass_context
def agent_get(ctx: click.Context, ws_agent_key: str) -> None:
    """获取 Agent 详情。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("GET", f"/agents/{ws_agent_key}")

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    a = resp.get("data", {})
    from rich.table import Table
    table = Table(title=f"Agent: {a.get('title', ws_agent_key)}")
    table.add_column("字段", style="bold")
    table.add_column("值")
    for k, v in a.items():
        table.add_row(k, str(v))
    from rich.console import Console
    Console().print(table)


@agent_group.command("update")
@click.argument("ws_agent_key", type=str)
@click.option("--title", "-n", "title", default=None, type=str, help="新名称")
@click.option("--config", "-c", "config_json", default=None, type=str, help="新配置 JSON (符合当前 agent_type)")
@click.option("--description", "-d", "description", default=None, type=str, help="新描述")
@click.option("--enabled/--disabled", "is_enabled", default=None, help="启用/禁用")
@click.option("--scope", "scope", default=None, type=str, help="可见范围: public / specified_ws_groups")
@click.option("--group-ids", "group_ids", default=None, type=str, help="scope=specified_ws_groups 时的角色 ID，逗号分隔")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def agent_update(ctx: click.Context, ws_agent_key: str, title: str | None, config_json: str | None,
                 description: str | None, is_enabled: bool | None, scope: str | None,
                 group_ids: str | None, dry_run: bool) -> None:
    """部分更新 Agent — 仅传需要修改的字段。"""
    import json as _json
    body: dict = {}
    if title is not None:
        body["title"] = title
    if config_json is not None:
        body["config"] = _json.loads(config_json)
    if description is not None:
        body["description"] = description
    if is_enabled is not None:
        body["is_enabled"] = is_enabled
    if scope is not None:
        body["scope"] = scope
    if group_ids is not None:
        body["specified_ws_group_ids"] = [int(g.strip()) for g in group_ids.split(",")]

    if not body:
        click.echo("⚠ 未指定任何要更新的字段")
        return

    if dry_run:
        click.echo(f"DRY-RUN PATCH /agents/{ws_agent_key}")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("PATCH", f"/agents/{ws_agent_key}", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@agent_group.command("delete")
@click.argument("ws_agent_key", type=str)
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def agent_delete(ctx: click.Context, ws_agent_key: str, force: bool, dry_run: bool) -> None:
    """删除 Agent。"""
    if not force and not dry_run:
        click.confirm(f"确认删除 Agent '{ws_agent_key}'？此操作不可逆", abort=True)

    if dry_run:
        click.echo(f"DRY-RUN DELETE /agents/{ws_agent_key}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("DELETE", f"/agents/{ws_agent_key}")
    success(resp, as_json=ctx.obj.get("as_json", False))
