"""Data commands: search and get documents."""

import json

import click

from ..client import EmooClient
from ..formatters import output


def _parse_filter(ctx, param, value):
    """Parse --filter from JSON string or file path."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # Try as file path
        try:
            with open(value) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raise click.BadParameter(f"无法解析 filter: {value}")


@click.group()
def data():
    """数据搜索与获取."""


@data.command()
@click.option("--keyword", "-k", required=True, help="搜索关键词")
@click.option("--page-size", default=20, help="每页条数 (最大100)")
@click.option("--current-page", default=1, help="页码")
@click.option("--text-format", type=click.Choice(["plain", "markdown"]), default="plain", help="文本格式")
@click.option("--ws-agent-key", default=None, help="Agent Key (Dify/Coze/Timus 平台需传入)")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None, help="过滤条件 JSON 字符串或文件路径")
@click.pass_context
def search(ctx, keyword, page_size, current_page, text_format, ws_agent_key, filter_conditions):
    """搜索数据."""
    body = {
        "page_size": page_size,
        "current_page": current_page,
        "keyword": keyword,
        "text_format": text_format,
    }
    if ws_agent_key:
        body["ws_agent_key"] = ws_agent_key
    if filter_conditions:
        body["filter_conditions"] = filter_conditions

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/search", body=body)
    output(resp, as_json=ctx.obj.get("as_json", False))


@data.command()
@click.option("--page-size", default=50, help="每页条数 (最大200)")
@click.option("--cursor", default="", help="分页游标")
@click.option("--text-format", type=click.Choice(["plain", "markdown"]), default="plain", help="文本格式")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None, help="过滤条件 JSON 字符串或文件路径")
@click.pass_context
def get(ctx, page_size, cursor, text_format, filter_conditions):
    """获取数据 (游标分页)."""
    body = {
        "page_size": page_size,
        "cursor": cursor,
        "text_format": text_format,
    }
    if filter_conditions:
        body["filter_conditions"] = filter_conditions

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/data", body=body)
    output(resp, as_json=ctx.obj.get("as_json", False))
