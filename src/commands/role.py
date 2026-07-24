"""角色管理命令: role list / create / update / delete / members-add / members-remove."""

from __future__ import annotations

import click

from ..client import EmooClient
from ..formatters import output, success, _progress


@click.group("role", help="角色管理 (工作区角色/群组)")
def role_group() -> None:
    pass


@role_group.command("list")
@click.option("--page-size", default=20, type=int, help="每页数量 (1-200)")
@click.option("--current-page", default=1, type=int, help="页码")
@click.option("--keyword", "-k", default=None, type=str, help="按角色名称模糊搜索")
@click.pass_context
def role_list(ctx: click.Context, page_size: int, current_page: int, keyword: str | None) -> None:
    """获取角色列表（分页）。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    params: dict = {"page_size": str(page_size), "current_page": str(current_page)}
    if keyword:
        params["keyword"] = keyword
    resp = client.request("GET", "/ws-groups", params=params)
    data = resp["data"]
    results = data.get("results", [])

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    total = data.get("total", 0)
    _progress(f"total={total}, page_size={data.get('page_size')}, current_page={data.get('current_page')}, "
              f"total_pages={data.get('total_pages')}")

    if not results:
        click.echo("暂无角色")
        return

    from rich.table import Table
    table = Table(title="角色列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称")
    table.add_column("描述")
    table.add_column("创建时间")

    for r in results:
        table.add_row(
            str(r.get("id", "")),
            r.get("group_name", ""),
            r.get("group_desc", "") or "",
            r.get("created_at", ""),
        )

    from rich.console import Console
    Console().print(table)


@role_group.command("create")
@click.option("--name", "-n", "name", required=True, type=str, help="角色名称 (唯一)")
@click.option("--desc", "-d", "desc", default=None, type=str, help="角色描述")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def role_create(ctx: click.Context, name: str, desc: str | None, dry_run: bool) -> None:
    """创建角色。"""
    body: dict = {"group_name": name}
    if desc:
        body["group_desc"] = desc

    import json as _json
    if dry_run:
        click.echo("DRY-RUN POST /ws-groups")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/ws-groups", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@role_group.command("update")
@click.argument("role_id", type=int)
@click.option("--name", "-n", "name", default=None, type=str, help="新名称")
@click.option("--desc", "-d", "desc", default=None, type=str, help="新描述")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def role_update(ctx: click.Context, role_id: int, name: str | None, desc: str | None,
                dry_run: bool) -> None:
    """更新角色基础信息。"""
    body: dict = {}
    if name is not None:
        body["group_name"] = name
    if desc is not None:
        body["group_desc"] = desc

    if not body:
        click.echo("⚠ 未指定任何要更新的字段")
        return

    import json as _json
    if dry_run:
        click.echo(f"DRY-RUN PATCH /ws-groups/{role_id}")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("PATCH", f"/ws-groups/{role_id}", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@role_group.command("delete")
@click.argument("role_id", type=int)
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def role_delete(ctx: click.Context, role_id: int, force: bool, dry_run: bool) -> None:
    """删除角色。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除角色 ID={role_id}？成员关系自动解除", abort=True)

    if dry_run:
        click.echo(f"DRY-RUN DELETE /ws-groups/{role_id}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("DELETE", f"/ws-groups/{role_id}")
    success(resp, as_json=ctx.obj.get("as_json", False))


@role_group.command("members-add")
@click.argument("role_id", type=int)
@click.argument("open_ids", type=str, nargs=-1)
@click.option("--file", "-f", "from_file", default=None, type=str,
              help="从文件读取 open_id (每行一个)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def role_members_add(ctx: click.Context, role_id: int, open_ids: tuple[str, ...],
                     from_file: str | None, dry_run: bool) -> None:
    """批量添加成员到角色。

    可以直接传 open_id，或用 --file 从文件读取。
    """
    ids = list(open_ids)
    if from_file:
        with open(from_file, "r") as f:
            ids.extend(line.strip() for line in f if line.strip())
    if not ids:
        click.echo("⚠ 未指定任何 open_id")
        return

    body = {"open_ids": ids}

    import json as _json
    if dry_run:
        click.echo(f"DRY-RUN POST /ws-groups/{role_id}/members")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", f"/ws-groups/{role_id}/members", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@role_group.command("members-remove")
@click.argument("role_id", type=int)
@click.argument("open_id", type=str)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def role_members_remove(ctx: click.Context, role_id: int, open_id: str,
                        dry_run: bool) -> None:
    """从角色中移除单个成员。"""
    if dry_run:
        click.echo(f"DRY-RUN DELETE /ws-groups/{role_id}/members/{open_id}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("DELETE", f"/ws-groups/{role_id}/members/{open_id}")
    success(resp, as_json=ctx.obj.get("as_json", False))
