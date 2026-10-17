"""Data commands: search and get documents."""

import json

import click

from ..client import EmooClient
from ..formatters import output, _progress


API_RESULT_CAP = 500


def _parse_filter(ctx, param, value):
    """Parse --filter from JSON string or file path.  Auto-wraps dict into [[...]] format."""
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as json_err:
        looks_like_path = value.startswith(("./", "../", "/", "~/"))
        if looks_like_path:
            try:
                with open(value) as f:
                    parsed = json.load(f)
            except FileNotFoundError:
                raise click.BadParameter(f"filter 文件不存在: {value}")
            except json.JSONDecodeError as e:
                raise click.BadParameter(f"filter 文件 JSON 格式错误: {e}")
        else:
            raise click.BadParameter(
                f"filter 不是合法 JSON 也不是已存在的文件路径\n"
                f"  JSON 解析: {json_err}\n"
                f"  提示: 使用文件路径请以 ./ 或 ~/ 开头"
            )
    except Exception:
        raise click.BadParameter(f"无法解析 filter: {value}")

    if isinstance(parsed, dict):
        parsed = [[parsed]]
    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict) and 'field' in parsed[0]:
        parsed = [parsed]
    return parsed


@click.group()
def data():
    """数据搜索与获取 (关键词搜索、游标分页、过滤排序)."""


def _validate_page_size(ctx, param, value):
    if value < 1:
        raise click.BadParameter("page-size 必须 >= 1")
    return value


def _auto_paginate_search(client, body, max_results, ctx):
    """Auto-paginate through /search results until max_results or exhausted."""
    all_results = []
    page = 1
    api_total = 0

    while True:
        body["current_page"] = page
        resp = client.post("/search", body=body)
        results = resp.get("data", {}).get("results", [])
        api_total = resp.get("data", {}).get("total", 0)

        if not results:
            break

        all_results.extend(results)
        _progress(f"  已获取 {len(all_results)} 条 (第 {page} 页)")

        if len(all_results) >= max_results:
            all_results = all_results[:max_results]
            break

        if len(all_results) >= api_total or len(results) < body["page_size"]:
            break

        page += 1

    resp["data"]["_api_total"] = api_total
    resp["data"]["results"] = all_results
    resp["data"]["total"] = len(all_results)
    if page > 1:
        resp["data"]["_paginated"] = True
        resp["data"]["_page_count"] = page

    # search 端点有 500 条硬上限，total 永远不超过 500
    truncated = (api_total == API_RESULT_CAP and len(all_results) >= API_RESULT_CAP)
    if truncated:
        resp["data"]["_truncated"] = True
    return resp, truncated


@data.command()
@click.option("--keyword", "-k", required=True, help="搜索关键词")
@click.option("--page-size", default=20, callback=_validate_page_size, help="每页条数 (最大200)")
@click.option("--current-page", default=1, help="页码")
@click.option("--text-format", type=click.Choice(["plain", "markdown"]), default="plain",
              help="文本格式 (markdown 返回语雀 HTML)")
@click.option("--ws-agent-key", default=None, help="Agent Key (Dify/Coze/Timus 平台需传入)")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None,
              help='过滤条件，四种格式:\n'
                   '  ① dict: \'{"field":"...","operator":"eq","value":"..."}\'\n'
                   '  ② 一维数组(AND): \'[{...},{...}]\'\n'
                   '  ③ 二维数组(OR+AND): \'[[{...}],[{...}]]\'\n'
                   '  ④ 文件路径: ./filter.json\n'
                   '合法字段: id, app_doc_id, doc_group.id, doc_group.app_group_id, '
                   'app_created_at, app_updated_at, ws_app.id, ws_app.app_id, '
                   'ws_app.ws_app_key, author_ws_app_user_id\n'
                   '运算符: eq, neq, in, nin, gte, lte')
@click.option("--max-results", type=int, default=None,
              help=f"最多返回条数，自动翻页 (search 端点硬上限 {API_RESULT_CAP}，超出用 data get)")
@click.pass_context
def search(ctx, keyword, page_size, current_page, text_format, ws_agent_key,
           filter_conditions, max_results):
    """搜索数据.

    不加 --max-results 时单次查询，结果超过 {API_RESULT_CAP} 条会输出截断警告。
    加 --max-results 时自动翻页，但 search 端点有 {API_RESULT_CAP} 条硬上限无法突破。
    需要拉取超过 {API_RESULT_CAP} 条请用 emoo data get (游标翻页，无此限制)。

    \b
    示例:
      emoo data search -k "上海" --max-results 2000
      emoo data search -k "报告" -f '[[{{"field":"ws_app.ws_app_key","operator":"eq","value":"abc"}}]]'
    """.format(API_RESULT_CAP=API_RESULT_CAP)
    if page_size > 200:
        raise click.BadParameter(f"page-size 最大 200，当前为 {page_size}")

    # Use max page_size for auto-pagination to minimise round-trips
    if max_results and page_size < 200:
        page_size = min(200, max_results)

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

    if max_results:
        resp, truncated = _auto_paginate_search(client, dict(body), max_results, ctx)
        if truncated:
            _progress(
                f"⚠ 结果可能不完整: search 端点硬上限 {API_RESULT_CAP} 条，自动翻页也无法突破。"
            )
            _progress(f"  建议: 用 emoo data get (游标翻页无此限制) 配合日期过滤分段拉取。")
        output(resp, as_json=ctx.obj.get("as_json", False))
        return

    resp = client.post("/search", body=body)
    results = resp.get("data", {}).get("results", [])
    total = resp.get("data", {}).get("total", 0)

    if total >= API_RESULT_CAP and len(results) >= page_size:
        _progress(
            f"⚠ 结果可能不完整: API 单次上限 {API_RESULT_CAP} 条，当前已返回 {len(results)} 条。"
        )
        _progress(f"  使用 --max-results <N> 自动翻页获取更多 (如 --max-results 2000)，或按日期分段查询。")

    output(resp, as_json=ctx.obj.get("as_json", False))


@data.command()
@click.option("--page-size", default=50, callback=_validate_page_size, help="每页条数 (最大200)")
@click.option("--cursor", default="", help="分页游标")
@click.option("--text-format", type=click.Choice(["plain", "markdown"]), default="plain",
              help="文本格式 (markdown 返回语雀 HTML)")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None,
              help='过滤条件，四种格式同上 search')
@click.option("--max-results", type=int, default=None,
              help="最多返回条数，游标自动翻页直到拿满或数据源耗尽 (无 500 硬上限)")
@click.option("--stream", "stream_mode", is_flag=True, default=False,
              help="流式输出 (JSON Lines 格式，每行一条记录，适合大数据量管道处理)")
@click.pass_context
def get(ctx, page_size, cursor, text_format, filter_conditions, max_results, stream_mode):
    """获取数据 (游标分页).

    不加 --max-results 时单次查询。加 --max-results 时自动用游标翻页。
    --stream 模式输出 JSON Lines，适合管道渐进处理大数据集。
    """
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

    if max_results or stream_mode:
        limit = max_results or 10_000_000
        if not max_results:
            _progress("流式模式: 将拉取全部数据直到数据源耗尽...")
        if page_size < 200:
            page_size = min(200, limit)
            body["page_size"] = page_size

        all_results = []
        current_cursor = cursor
        page_count = 0
        stream_total = 0
        incomplete = False
        while True:
            body["cursor"] = current_cursor
            resp = client.post("/data", body=body)
            data_block = resp.get("data", {})
            results = data_block.get("results", [])
            page_count += 1
            if not results:
                break

            if stream_mode:
                for r in results:
                    click.echo(json.dumps(r, ensure_ascii=False))
                stream_total += len(results)
                _progress(f"  已输出 {stream_total} 条 (第 {page_count} 页)")
            else:
                all_results.extend(results)
                _progress(f"  已获取 {len(all_results)} 条 (第 {page_count} 页)")

            if not stream_mode and len(all_results) >= limit:
                all_results = all_results[:limit]
                incomplete = data_block.get("has_more", False)
                break
            if not data_block.get("has_more") or not data_block.get("next_cursor"):
                break
            if stream_mode and max_results and stream_total >= max_results:
                _progress(f"  已达到 max_results={max_results}，停止")
                break
            current_cursor = data_block["next_cursor"]

        if stream_mode:
            _progress(f"流式输出完成，共 {stream_total} 条，{page_count} 页")
            return

        resp["data"]["results"] = all_results
        resp["data"]["total"] = len(all_results)
        if page_count > 1:
            resp["data"]["_paginated"] = True
            resp["data"]["_page_count"] = page_count
        if incomplete:
            resp["data"]["_incomplete"] = True
        output(resp, as_json=ctx.obj.get("as_json", False))
        return

    resp = client.post("/data", body=body)
    output(resp, as_json=ctx.obj.get("as_json", False))


@data.command()
@click.option("--metric", "-m", "metric_type",
              type=click.Choice(["count", "sum", "avg", "min", "max", "values"]),
              required=True, help="聚合操作")
@click.option("--field", "metric_field", default=None,
              help="聚合字段名 (count 时可省；table 字段可用 '支付信息.*.金额')")
@click.option("--group-by", "group_by_field", default=None, help="分组字段名")
@click.option("--interval", "group_by_interval",
              type=click.Choice(["day", "week", "month", "quarter", "year"]),
              default=None, help="时间分桶粒度 (仅 date 字段生效)")
@click.option("--max-groups", type=int, default=None, help="分组桶上限 (hard cap 50)")
@click.option("--max-values", type=int, default=None, help="values 返回值上限 (hard cap 200)")
@click.option("--ws-agent-key", default=None, help="Agent 标识，限定聚合范围")
@click.option("--filter", "-f", "filter_conditions", callback=_parse_filter, default=None,
              help="过滤条件 (格式同 data search)")
@click.pass_context
def aggregate(ctx, metric_type, metric_field, group_by_field, group_by_interval,
              max_groups, max_values, ws_agent_key, filter_conditions):
    """聚合统计 — 在可见文档范围内做 metric + group_by 聚合。

    \b
    示例:
      emoo data aggregate -m count
      emoo data aggregate -m sum --field 合同金额
      emoo data aggregate -m count --group-by 部门
      emoo data aggregate -m count --group-by 签约日 --interval month
      emoo data aggregate -m values --field 工号
    """
    if metric_type != "count" and not metric_field:
        raise click.BadParameter(f"metric={metric_type} 需要 --field")
    if group_by_interval and not group_by_field:
        raise click.BadParameter("--interval 需要同时指定 --group-by")
    if max_groups is not None and not (1 <= max_groups <= 50):
        raise click.BadParameter("--max-groups 需在 1-50 之间")
    if max_values is not None and not (1 <= max_values <= 200):
        raise click.BadParameter("--max-values 需在 1-200 之间")

    body: dict = {"metric_type": metric_type}
    if metric_field:
        body["metric_field"] = metric_field
    if group_by_field:
        body["group_by_field"] = group_by_field
    if group_by_interval:
        body["group_by_interval"] = group_by_interval
    if max_groups is not None:
        body["max_groups"] = max_groups
    if max_values is not None:
        body["max_values"] = max_values
    if ws_agent_key:
        body["ws_agent_key"] = ws_agent_key
    if filter_conditions:
        body["filter_conditions"] = filter_conditions

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/search/aggregate", body=body)

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    data_block = resp.get("data", {})
    _progress(f"total_docs={data_block.get('total_docs', 0)} "
              f"metric={data_block.get('metric_type')}")
    if data_block.get("truncated"):
        _progress("⚠ 已触达分组/枚举上限，结果可能不完整")

    buckets = data_block.get("buckets") or []
    if not buckets:
        click.echo(data_block.get("note") or "无数据")
        return

    from rich.console import Console
    from rich.table import Table
    table = Table(title="聚合结果")
    table.add_column("key")
    table.add_column("doc_count")
    table.add_column("metric_value")
    table.add_column("values")
    for bucket in buckets:
        table.add_row(
            str(bucket.get("key", "")),
            str(bucket.get("doc_count", "")),
            str(bucket.get("metric_value", "")),
            ", ".join(map(str, bucket.get("values") or [])),
        )
    Console().print(table)
