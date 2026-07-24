"""文件夹管理命令: folder list / create / update / delete."""

from __future__ import annotations

import click

from ..client import EmooClient
from ..formatters import output, success, _progress


@click.group("folder", help="知识库文件夹管理 (限超管)")
def folder_group() -> None:
    pass


@folder_group.command("list")
@click.option("--folder-id", "-f", "folder_id", default=None, type=int,
              help="父 folder ID; 不传=列根级")
@click.pass_context
def folder_list(ctx: click.Context, folder_id: int | None) -> None:
    """列出 folder 直接 children (混合 folder+table+document，不递归)。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    params: dict = {}
    if folder_id is not None:
        params["folder_id"] = str(folder_id)
    resp = client.request("GET", "/data/folder/items", params=params)
    data = resp.get("data", [])

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    items = data if isinstance(data, list) else data.get("items", []) if isinstance(data, dict) else []
    _progress(f"共 {len(items)} 项")

    if not items:
        click.echo("该 folder 为空")
        return

    from rich.table import Table
    table = Table(title="Folder 内容")
    table.add_column("类型", style="cyan")
    table.add_column("ID")
    table.add_column("名称")
    table.add_column("额外信息")

    for it in items:
        it_type = it.get("type", it.get("item_type", ""))
        it_id = it.get("id") or it.get("folder_id") or it.get("table_key") or it.get("doc_id", "")
        name = it.get("name") or it.get("folder_name") or it.get("table_name") or it.get("title", "")
        extra = ""
        if it_type == "table" or "table_key" in it:
            extra = f"table_key={it.get('table_key', '')}"
        elif it_type == "document" or "doc_id" in it:
            extra = f"doc_id={it.get('doc_id', '')}"
        table.add_row(str(it_type), str(it_id), str(name), extra)

    from rich.console import Console
    Console().print(table)


@folder_group.command("create")
@click.option("--name", "-n", "name", required=True, type=str, help="folder 名称 (≤200字符, 同 parent 唯一)")
@click.option("--parent-id", "-p", "parent_id", default=None, type=int, help="父 folder ID; 不传=根 folder")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def folder_create(ctx: click.Context, name: str, parent_id: int | None, dry_run: bool) -> None:
    """创建 folder (限 workspace 超管)。"""
    body: dict = {"name": name}
    if parent_id is not None:
        body["parent_id"] = parent_id

    import json as _json
    if dry_run:
        click.echo("DRY-RUN POST /data/folder")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/data/folder", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@folder_group.command("update")
@click.option("--folder-id", "-f", "folder_id", required=True, type=int, help="目标 folder ID")
@click.option("--name", "-n", "name", default=None, type=str, help="新名称")
@click.option("--parent-id", "-p", "parent_id", default=None, type=int,
              help="父 folder ID; 不传=不改; 用 --to-root 移到根")
@click.option("--to-root", is_flag=True, help="移到根 folder (parent_id=null)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def folder_update(ctx: click.Context, folder_id: int, name: str | None,
                  parent_id: int | None, to_root: bool, dry_run: bool) -> None:
    """更新 folder (改名/移动, 限超管)。name 或 parent_id 至少传一项。"""
    body: dict = {"folder_id": folder_id}
    if name is not None:
        body["name"] = name
    if to_root:
        body["parent_id"] = None
    elif parent_id is not None:
        body["parent_id"] = parent_id

    if len(body) == 1:
        click.echo("⚠ 需至少提供 --name 或 --parent-id 之一")
        return

    import json as _json
    if dry_run:
        click.echo(f"DRY-RUN PUT /data/folder")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("PUT", "/data/folder", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@folder_group.command("delete")
@click.option("--folder-id", "-f", "folder_id", required=True, type=int, help="目标 folder ID")
@click.option("--force", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def folder_delete(ctx: click.Context, folder_id: int, force: bool, dry_run: bool) -> None:
    """删除 folder (子孙级联删除, 下属 table/document 上浮到祖父, 限超管)。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除 folder ID={folder_id}？子孙 folder 级联删除", abort=True)

    if dry_run:
        click.echo(f"DRY-RUN DELETE /data/folder  body={{\"folder_id\":{folder_id}}}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("DELETE", "/data/folder", body={"folder_id": folder_id})
    success(resp, as_json=ctx.obj.get("as_json", False))
