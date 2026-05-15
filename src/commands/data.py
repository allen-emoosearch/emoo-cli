"""Data commands: search and get documents."""

import json

import click

from ..client import EmooClient
from ..formatters import output


def _parse_filter(ctx, param, value):
    """Parse --filter from JSON string or file path.  Auto-wraps dict into [[...]] format."""
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        # Try as file path
        try:
            with open(value) as f:
                parsed = json.load(f)
        except FileNotFoundError:
            raise click.BadParameter(f"filter 文件不存在: {value}")
        except json.JSONDecodeError as e:
            raise click.BadParameter(f"filter 文件 JSON 格式错误: {e}")
    except Exception:
        raise click.BadParameter(f"无法解析 filter: {value}")

    # Auto-wrap conveniences:
    #    {"field":"ws_app.ws_app_key","operator":"eq","value":"abc"}
    #        → [[{"field":"ws_app.ws_app_key","operator":"eq","value":"abc"}]]
    #    [{"field":...,"operator":...,"value":...}]
    #        → [[{"field":...,"operator":...,"value":...}]]
    #    [[{...}],[{...}]]  →  passed through as-is
    if isinstance(parsed, dict):
        parsed = [[parsed]]
    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict) and 'field' in parsed[0]:
        parsed = [parsed]
    return parsed


@click.group()
def data():
    """数据搜索与获取."""


def _validate_page_size(ctx, param, value):
    if value < 1:
        raise click.BadParameter("page-size 必须 >= 1")
    return value


@data.command()
@click.option("--keyword", "-k", required=True, help="搜索关键词")
@click.option("--page-size", default=20, callback=_validate_page_size, help="每页条数 (最大100)")
@click.option("--current-page", default=1, help="页码")
@click.option("--text-format", type=click.Choice(["plain", "markdown"]), default="plain", help="文本格式")
@click.option("--ws-agent-key", default=None, help="Agent Key (Dify/Coze/Timus 平台需传入)")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None, help='过滤条件: JSON 或文件路径。合法字段: id, app_doc_id, doc_group.id, doc_group.app_group_id, app_created_at, app_updated_at, ws_app.ws_app_key。运算符: eq, neq, in, nin, gte, lte。简写: -f \'{"field":"ws_app.ws_app_key","operator":"eq","value":"KEY"}\'')
@click.pass_context
def search(ctx, keyword, page_size, current_page, text_format, ws_agent_key, filter_conditions):
    """搜索数据."""
    if page_size > 100:
        raise click.BadParameter(f"page-size 最大 100，当前为 {page_size}")
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
@click.option("--page-size", default=50, callback=_validate_page_size, help="每页条数 (最大200)")
@click.option("--cursor", default="", help="分页游标")
@click.option("--text-format", type=click.Choice(["plain", "markdown"]), default="plain", help="文本格式")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None, help='过滤条件: JSON 或文件路径。合法字段同上 search')
@click.pass_context
def get(ctx, page_size, cursor, text_format, filter_conditions):
    """获取数据 (游标分页)."""
    if page_size > 200:
        raise click.BadParameter(f"page-size 最大 200，当前为 {page_size}")
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
