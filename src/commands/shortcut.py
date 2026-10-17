"""Personal shortcut commands: shortcut list/create/update/delete/reorder."""

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


@click.group("shortcut", help="个人快捷方式管理 (最多 10 个)")
def shortcut_group() -> None:
    pass


@shortcut_group.command("list")
@click.pass_context
def shortcut_list(ctx: click.Context) -> None:
    """列出当前用户的全部快捷方式。"""
    resp = _client(ctx).request("GET", "/shortcut")
    output(resp, as_json=ctx.obj.get("as_json", False))


@shortcut_group.command("create")
@click.option("--title", "-t", required=True, help="标题")
@click.option("--url", "-u", required=True, help="跳转链接 (支持自定义协议)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def shortcut_create(ctx: click.Context, title: str, url: str, dry_run: bool) -> None:
    """创建快捷方式 (追加到列表末尾)。"""
    body = {"title": title, "url": url}
    if dry_run:
        _dry_run(ctx, "POST", "/shortcut", body)
        return
    resp = _client(ctx).request("POST", "/shortcut", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@shortcut_group.command("update")
@click.argument("shortcut_id", type=int)
@click.option("--title", "-t", required=True, help="新标题")
@click.option("--url", "-u", required=True, help="新链接")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def shortcut_update(ctx: click.Context, shortcut_id: int, title: str, url: str,
                    dry_run: bool) -> None:
    """整体更新快捷方式 (title + url 都必填)。"""
    body = {"title": title, "url": url}
    if dry_run:
        _dry_run(ctx, "PUT", f"/shortcut/{shortcut_id}", body)
        return
    resp = _client(ctx).request("PUT", f"/shortcut/{shortcut_id}", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@shortcut_group.command("delete")
@click.argument("shortcut_id", type=int)
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def shortcut_delete(ctx: click.Context, shortcut_id: int, force: bool,
                    dry_run: bool) -> None:
    """删除快捷方式。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除快捷方式 {shortcut_id}？", abort=True)

    if dry_run:
        _dry_run(ctx, "DELETE", f"/shortcut/{shortcut_id}")
        return

    resp = _client(ctx).request("DELETE", f"/shortcut/{shortcut_id}")
    success(resp, as_json=ctx.obj.get("as_json", False))


@shortcut_group.command("reorder")
@click.argument("shortcut_ids", type=int, nargs=-1)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def shortcut_reorder(ctx: click.Context, shortcut_ids: tuple[int, ...],
                     dry_run: bool) -> None:
    """按新顺序重排全部快捷方式 (必须传当前用户的全部 shortcut_id)。"""
    body = {"shortcut_ids": list(shortcut_ids)}
    if dry_run:
        _dry_run(ctx, "POST", "/shortcut/order", body)
        return
    resp = _client(ctx).request("POST", "/shortcut/order", body=body)
    output(resp, as_json=ctx.obj.get("as_json", False))
