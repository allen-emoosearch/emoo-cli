"""Contact commands: list and update members."""

import click

from ..client import EmooClient
from ..formatters import output


@click.group()
def contact():
    """通讯录管理 (成员列表、更新成员信息)."""


@contact.command()
@click.option("--page-size", default=50, help="每页条数 (最大100)")
@click.option("--current-page", default=1, help="页码")
@click.option("--keyword", default=None, help="搜索关键词 (匹配 ws_username / open_id / email)")
@click.option("--columns", default=None, help="指定显示列，逗号分隔 (如 open_id,ws_username,email)")
@click.pass_context
def list(ctx, page_size, current_page, keyword, columns):
    """获取通讯录成员."""
    if page_size > 100:
        raise click.BadParameter(f"page-size 最大 100，当前为 {page_size}")
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    params = {"page_size": page_size, "current_page": current_page}
    if keyword:
        params["keyword"] = keyword
    resp = client.get("/ws-user", params=params)
    cols = [c.strip() for c in columns.split(",")] if columns else None
    output(resp, as_json=ctx.obj.get("as_json", False), columns=cols)


@contact.command()
@click.argument("open_id")
@click.option("--username", default=None, help="新的显示名称")
@click.option("--ext-info", default=None, help="扩展信息 JSON 字符串")
@click.pass_context
def update(ctx, open_id, username, ext_info):
    """更新成员信息."""
    body = [{"open_id": open_id}]
    if username:
        body[0]["ws_username"] = username
    if ext_info:
        import json
        body[0]["ext_info"] = json.loads(ext_info)

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.put("/ws-user", body=body)
    output(resp, as_json=ctx.obj.get("as_json", False))
