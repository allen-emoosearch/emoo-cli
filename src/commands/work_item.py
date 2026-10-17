"""Work item (待办/工作项) commands: todo list/create/update/delete + tags.

API: /work_item and /work_item/tags. `emoo message push` lands a work item for
the target user, so these commands close the loop: list, tag, complete, delete.
"""

from __future__ import annotations

import json

import click

from ..client import EmooClient
from ..formatters import output, success


def _dry_run(ctx, method: str, path: str, body: dict | None = None) -> None:
    payload: dict = {"dry_run": True, "method": method, "path": path}
    if body is not None:
        payload["body"] = body
    if ctx.obj.get("as_json"):
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        click.echo(f"DRY-RUN {method} {path}")
        if body is not None:
            click.echo(f"  Body:\n{json.dumps(body, ensure_ascii=False, indent=2)}")


def _client(ctx) -> EmooClient:
    return EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))


@click.group("todo", help="工作项/待办管理 (列表/创建/更新/删除 + Tag)")
def todo_group() -> None:
    pass


@todo_group.command("list")
@click.option("--page-size", default=50, type=int, help="每页数量 (1-500，默认 50)")
@click.option("--current-page", default=1, type=int, help="页码")
@click.option("--scope", type=click.Choice(["pending", "done"]), default="pending",
              help="pending=待处理 (默认)；done=已完成")
@click.option("--tag-id", type=int, default=None, help="按 Tag 过滤 (正整数)")
@click.option("--not-taged", "--not-tagged", "not_taged", is_flag=True,
              help="仅查无 Tag 项 (与 --tag-id 互斥)")
@click.pass_context
def todo_list(ctx: click.Context, page_size: int, current_page: int, scope: str,
              tag_id: int | None, not_taged: bool) -> None:
    """列出当前用户的工作项。"""
    if not (1 <= page_size <= 500):
        raise click.BadParameter("page-size 需在 1-500 之间")
    if tag_id is not None and tag_id > 0 and not_taged:
        raise click.BadParameter("--tag-id 与 --not-taged 不能同时使用")

    params: dict = {
        "page_size": page_size,
        "current_page": current_page,
        "scope": scope,
    }
    if tag_id:
        params["tag_id"] = tag_id
    if not_taged:
        params["not_taged"] = True

    resp = _client(ctx).request("GET", "/work_item", params=params)
    output(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("create")
@click.option("--content", "-c", required=True, help="工作项内容")
@click.option("--due-at", default=None, help="截止时间 (ISO 8601，建议带时区偏移)")
@click.option("--tag-id", type=int, default=None, help="关联 Tag id")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_create(ctx: click.Context, content: str, due_at: str | None,
                tag_id: int | None, dry_run: bool) -> None:
    """创建自建工作项 (source=self)。"""
    body: dict = {"content": content}
    if due_at:
        body["due_at"] = due_at
    if tag_id:
        body["tag_id"] = tag_id

    if dry_run:
        _dry_run(ctx, "POST", "/work_item", body)
        return

    resp = _client(ctx).request("POST", "/work_item", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("update")
@click.argument("item_id", type=int)
@click.option("--content", "-c", default=None, help="新内容 (仅 self 来源可改)")
@click.option("--due-at", default=None, help="新截止时间 (ISO 8601)")
@click.option("--clear-due-at", is_flag=True, help="清空截止时间")
@click.option("--remind-at", default=None, help="稍后提醒时间 (ISO 8601)")
@click.option("--clear-remind-at", is_flag=True, help="清空提醒时间")
@click.option("--tag-id", type=int, default=None, help="Tag id；传 0 清空 Tag")
@click.option("--status", type=click.Choice(["pending", "done"]), default=None,
              help="状态：pending=恢复待处理；done=完成")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_update(ctx: click.Context, item_id: int, content: str | None,
                due_at: str | None, clear_due_at: bool, remind_at: str | None,
                clear_remind_at: bool, tag_id: int | None, status: str | None,
                dry_run: bool) -> None:
    """部分更新工作项。不传的字段不修改。"""
    if due_at and clear_due_at:
        raise click.BadParameter("--due-at 与 --clear-due-at 不能同时使用")
    if remind_at and clear_remind_at:
        raise click.BadParameter("--remind-at 与 --clear-remind-at 不能同时使用")

    body: dict = {}
    if content is not None:
        body["content"] = content
    if due_at:
        body["due_at"] = due_at
    elif clear_due_at:
        body["due_at"] = None
    if remind_at:
        body["remind_at"] = remind_at
    elif clear_remind_at:
        body["remind_at"] = None
    if tag_id is not None:
        body["tag_id"] = tag_id
    if status:
        body["status"] = status

    if not body:
        click.echo("⚠ 未指定任何要更新的字段")
        return

    if dry_run:
        _dry_run(ctx, "PUT", f"/work_item/{item_id}", body)
        return

    resp = _client(ctx).request("PUT", f"/work_item/{item_id}", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("delete")
@click.argument("item_id", type=int)
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_delete(ctx: click.Context, item_id: int, force: bool, dry_run: bool) -> None:
    """删除工作项 (仅 self 来源可删)。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除工作项 {item_id}？", abort=True)

    if dry_run:
        _dry_run(ctx, "DELETE", f"/work_item/{item_id}")
        return

    resp = _client(ctx).request("DELETE", f"/work_item/{item_id}")
    success(resp, as_json=ctx.obj.get("as_json", False))


# ── Tags ────────────────────────────────────────────────────────────────────

@todo_group.command("tag-list")
@click.pass_context
def todo_tag_list(ctx: click.Context) -> None:
    """列出当前用户的全部 Tag。"""
    resp = _client(ctx).request("GET", "/work_item/tags")
    output(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("tag-create")
@click.option("--name", "-n", required=True, help="Tag 名称 (同一用户下唯一)")
@click.option("--color", required=True, help="Tag 颜色 (如 #FFFFFF)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_tag_create(ctx: click.Context, name: str, color: str, dry_run: bool) -> None:
    """创建 Tag (每用户最多 10 个)。"""
    body = {"name": name, "color": color}
    if dry_run:
        _dry_run(ctx, "POST", "/work_item/tags", body)
        return
    resp = _client(ctx).request("POST", "/work_item/tags", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("tag-update")
@click.argument("tag_id", type=int)
@click.option("--name", "-n", required=True, help="Tag 名称")
@click.option("--color", required=True, help="Tag 颜色")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_tag_update(ctx: click.Context, tag_id: int, name: str, color: str,
                    dry_run: bool) -> None:
    """整体更新 Tag (name + color 都必填)。"""
    body = {"name": name, "color": color}
    if dry_run:
        _dry_run(ctx, "PUT", f"/work_item/tags/{tag_id}", body)
        return
    resp = _client(ctx).request("PUT", f"/work_item/tags/{tag_id}", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("tag-delete")
@click.argument("tag_id", type=int)
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_tag_delete(ctx: click.Context, tag_id: int, force: bool, dry_run: bool) -> None:
    """删除 Tag (关联工作项的 tag_id 会被置空)。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除 Tag {tag_id}？关联工作项将失去该 Tag", abort=True)

    if dry_run:
        _dry_run(ctx, "DELETE", f"/work_item/tags/{tag_id}")
        return

    resp = _client(ctx).request("DELETE", f"/work_item/tags/{tag_id}")
    success(resp, as_json=ctx.obj.get("as_json", False))


@todo_group.command("tag-reorder")
@click.argument("tag_ids", type=int, nargs=-1)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def todo_tag_reorder(ctx: click.Context, tag_ids: tuple[int, ...], dry_run: bool) -> None:
    """按新顺序重排全部 Tag (必须传当前用户的全部 tag_id)。"""
    body = {"tag_ids": list(tag_ids)}
    if dry_run:
        _dry_run(ctx, "POST", "/work_item/tags/order", body)
        return
    resp = _client(ctx).request("POST", "/work_item/tags/order", body=body)
    output(resp, as_json=ctx.obj.get("as_json", False))
