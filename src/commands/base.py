"""EMOO Base commands: CRUD operations on data table records."""

import json
import sys

import click

from ..client import EmooClient
from ..formatters import success, output, _progress


def _parse_records(value):
    """Parse --records from JSON string or file path."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            with open(value) as f:
                return json.load(f)
        except FileNotFoundError:
            raise click.BadParameter(f"records 文件不存在: {value}")
        except json.JSONDecodeError as e:
            raise click.BadParameter(f"records 文件 JSON 格式错误: {e}")


def _ensure_table(table_key, table_name):
    """Validate that at least one of table_key or table_name is provided."""
    if not table_key and not table_name:
        raise click.BadParameter("需要 --table-key 或 --table-name")
    return table_key, table_name


@click.group()
def base():
    """EMOO Base 数据表操作 (表/列/记录增删改查)."""


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--records", "-r", required=True, help="记录 JSON 字符串或文件路径 (数组, 最多100条)")
@click.pass_context
def record_create(ctx, table_key, table_name, records):
    """插入记录到数据表。"""
    _ensure_table(table_key, table_name)
    records_data = _parse_records(records)
    if not isinstance(records_data, list):
        raise click.BadParameter("records 必须是 JSON 数组")
    if len(records_data) > 100:
        raise click.BadParameter(f"单次最多插入 100 条，当前 {len(records_data)} 条")

    body = {"records": records_data}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/data/records", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--record-key", default=None, help="记录标识 (与 --record-title 二选一，优先使用)")
@click.option("--record-title", default=None, help="记录标题 (依赖 title column)")
@click.option("--fields", "-f", required=True, help="需要更新的字段 JSON 对象或文件路径")
@click.pass_context
def record_update(ctx, table_key, table_name, record_key, record_title, fields):
    """更新单条记录。"""
    _ensure_table(table_key, table_name)
    if not record_key and not record_title:
        raise click.BadParameter("需要 --record-key 或 --record-title")
    try:
        fields_data = json.loads(fields)
    except json.JSONDecodeError:
        try:
            with open(fields) as f:
                fields_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise click.BadParameter(f"无法解析 fields: {fields}")

    body = {"fields": fields_data}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if record_key:
        body["record_key"] = record_key
    else:
        body["record_title"] = record_title

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.put("/data/records", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--records", "-r", required=True, help="记录数组 JSON 或文件路径 (每条含 record_key 和 fields, 最多100条)")
@click.pass_context
def record_batch_update(ctx, table_key, table_name, records):
    """批量更新记录。"""
    _ensure_table(table_key, table_name)
    records_data = _parse_records(records)
    if not isinstance(records_data, list):
        raise click.BadParameter("records 必须是 JSON 数组")
    if len(records_data) > 100:
        raise click.BadParameter(f"单次最多更新 100 条，当前 {len(records_data)} 条")

    body = {"records": records_data}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/data/records/batch-update", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--record-keys", "-k", default=None, help="记录标识数组 JSON 或文件路径 (与 --record-titles 二选一，优先使用)")
@click.option("--record-titles", default=None, help="记录标题数组 JSON 或文件路径 (依赖 title column)")
@click.pass_context
def record_delete(ctx, table_key, table_name, record_keys, record_titles):
    """删除记录。"""
    _ensure_table(table_key, table_name)
    if record_keys:
        keys_data = _parse_records(record_keys)
        if not isinstance(keys_data, list):
            raise click.BadParameter("record_keys 必须是 JSON 字符串数组")
        if len(keys_data) > 100:
            raise click.BadParameter(f"单次最多删除 100 条，当前 {len(keys_data)} 条")
        body = {"record_keys": keys_data}
    elif record_titles:
        titles_data = _parse_records(record_titles)
        if not isinstance(titles_data, list):
            raise click.BadParameter("record_titles 必须是 JSON 字符串数组")
        if len(titles_data) > 100:
            raise click.BadParameter(f"单次最多删除 100 条，当前 {len(titles_data)} 条")
        body = {"record_titles": titles_data}
    else:
        raise click.BadParameter("需要 --record-keys 或 --record-titles")

    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.delete("/data/records", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


def _parse_filter_clause(raw: str) -> tuple:
    """Parse a filter like 'field:op:value' → (field, op, value).
    Supports: eq, neq, gte, lte, in, nin, contains (client-side).
    """
    parts = raw.split(":", 2)
    if len(parts) == 3:
        return parts[0].strip(), parts[1].strip(), parts[2].strip()
    raise click.BadParameter(f"过滤格式错误，应为 field:op:value，当前: {raw}")


def _apply_contains_filter(results: list, field: str, value: str) -> list:
    """Client-side contains filter (case-insensitive)."""
    v_lower = value.lower()
    filtered = []
    for r in results:
        fval = str(r.get("fields", {}).get(field, "")).lower()
        if v_lower in fval:
            filtered.append(r)
    return filtered


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--page-size", default=20, help="每页数量 (最大100)")
@click.option("--current-page", default=1, help="页码")
@click.option("--filter", "-f", "filters", default=None,
              help="过滤条件, 逗号分隔 (eq/neq/gte/lte/in/nin/contains, 如 content:contains:发货,msgtime:gte:2026-06-01)")
@click.option("--room-id", default=None, help="按聊天群ID过滤 (客户端过滤，支持多个逗号分隔)")
@click.option("--group-field", default="roomid", help="群ID字段名 (默认 roomid, 不同表可能不同)")
@click.option("--sort", default=None, help="排序 (如 created_at:desc)")
@click.option("--max-results", type=int, default=None, help="最多返回条数，自动翻页")
@click.pass_context
def record_list(ctx, table_key, table_name, page_size, current_page, filters, sort, max_results, room_id, group_field):
    """查询记录列表。支持 contains 模糊搜索 (客户端过滤，大小写不敏感)。"""
    _ensure_table(table_key, table_name)
    if page_size > 100:
        raise click.BadParameter(f"page-size 最大 100，当前为 {page_size}")

    # Separate API filters from client-side contains filters
    api_filters = []
    contains_filters = []
    if filters:
        for f in filters.split(","):
            f = f.strip()
            if not f:
                continue
            field, op, value = _parse_filter_clause(f)
            if op == "contains":
                contains_filters.append((field, value))
            else:
                api_filters.append(f)

    body = {"page_size": 100 if contains_filters else page_size, "current_page": 1}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if api_filters:
        body["filters"] = api_filters
    if sort:
        body["sort"] = sort

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))

    # Parse room filter
    room_ids = [r.strip() for r in room_id.split(",")] if room_id else []

    if contains_filters or room_ids:
        # Fetch ALL source pages, then filter, then paginate for display
        all_matched = []
        limit = max_results or 5000
        source_total = 0
        source_pages = 0
        page = 1
        while True:
            body["current_page"] = page
            resp = client.post("/data/records/list", body=body)
            raw_results = resp.get("data", {}).get("results", [])
            if not raw_results:
                break
            source_total += len(raw_results)
            source_pages += 1

            # Apply room filter (client-side)
            filtered = list(raw_results)
            if room_ids:
                filtered = [r for r in filtered if r.get("fields", {}).get(group_field) in room_ids]

            # Apply contains filters
            for field, value in contains_filters:
                filtered = _apply_contains_filter(filtered, field, value)

            all_matched.extend(filtered)
            _progress(f"  已翻 {source_pages} 页, 源数据 {source_total} 条, 匹配 {len(all_matched)} 条")

            if len(all_matched) >= limit:
                all_matched = all_matched[:limit]
                break
            # Stop when source pages exhausted (not filtered results)
            if len(raw_results) < body["page_size"]:
                break
            page += 1

        # Display pagination: when max_results is set, return all matched
        total_matched = len(all_matched)
        display_page_size = page_size
        if max_results and max_results > page_size:
            display_page_size = min(max_results, 1000)

        start = (current_page - 1) * display_page_size
        end = start + display_page_size
        paginated = all_matched[start:end]

        resp["data"]["results"] = paginated
        resp["data"]["total"] = total_matched
        resp["data"]["page_size"] = display_page_size
        resp["data"]["current_page"] = current_page
        resp["data"]["total_pages"] = -(-total_matched // display_page_size) if total_matched > 0 else 0
        resp["data"]["_source_total"] = source_total
        resp["data"]["_source_pages"] = source_pages
        resp["data"]["_matched_total"] = total_matched
        if limit and total_matched >= 1000:
            resp["data"]["_truncated"] = True
    else:
        body["page_size"] = page_size
        body["current_page"] = current_page
        resp = client.post("/data/records/list", body=body)

    output(resp, as_json=ctx.obj.get("as_json", False))


# ── Table management ──────────────────────────────────────────────

def _parse_json_or_file(value, name="参数"):
    """Parse a JSON string or file path."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            with open(value) as f:
                return json.load(f)
        except FileNotFoundError:
            raise click.BadParameter(f"{name} 文件不存在: {value}")
        except json.JSONDecodeError as e:
            raise click.BadParameter(f"{name} 文件 JSON 格式错误: {e}")


@base.command(name="table-create")
@click.option("--table-name", "-n", required=True, help="表名称")
@click.option("--extra", default=None, help="扩展元数据 JSON 对象或文件路径")
@click.option("--columns", default=None, help="初始列定义 JSON 数组或文件路径 (ColumnDef)")
@click.pass_context
def table_create(ctx, table_name, extra, columns):
    """创建数据表，可同时指定初始列定义。"""
    body: dict = {"table_name": table_name}
    if extra:
        body["extra"] = _parse_json_or_file(extra, "extra")
    if columns:
        cols = _parse_json_or_file(columns, "columns")
        if not isinstance(cols, list):
            raise click.BadParameter("columns 必须是 JSON 数组")
        body["columns"] = cols

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/data/table", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command(name="table-list")
@click.option("--page-size", default=20, help="每页数量 (最大100)")
@click.option("--current-page", default=1, help="页码")
@click.pass_context
def table_list(ctx, page_size, current_page):
    """分页获取数据表列表。"""
    if page_size > 100:
        raise click.BadParameter(f"page-size 最大 100，当前为 {page_size}")

    params = {"page_size": page_size, "current_page": current_page}
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.get("/data/table", params=params)
    output(resp, as_json=ctx.obj.get("as_json", False))


@base.command(name="table-update")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--new-table-name", default=None, help="新表名称 (与 --extra 二选一)")
@click.option("--extra", default=None, help="扩展元数据 JSON 对象或文件路径")
@click.pass_context
def table_update(ctx, table_key, table_name, new_table_name, extra):
    """更新数据表名称或扩展元数据。"""
    _ensure_table(table_key, table_name)
    if not new_table_name and not extra:
        raise click.BadParameter("需要 --new-table-name 或 --extra")

    body: dict = {}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if new_table_name:
        body["new_table_name"] = new_table_name
    if extra:
        body["extra"] = _parse_json_or_file(extra, "extra")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.put("/data/table", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command(name="table-delete")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.pass_context
def table_delete(ctx, table_key, table_name):
    """软删除数据表。"""
    _ensure_table(table_key, table_name)

    body: dict = {}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.delete("/data/table", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command(name="table-get")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.pass_context
def table_get(ctx, table_key, table_name):
    """获取表详情（当前通过列表 + 客户端过滤，后续 API 支持直查后切换）。"""
    _ensure_table(table_key, table_name)

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    # 当前 API 的 GET /data/table 不支持 query 过滤，拉全量后客户端匹配
    resp = client.get("/data/table", params={"page_size": 100})
    results = resp.get("data", {}).get("results", [])

    match = None
    for t in results:
        if table_key and t.get("table_key") == table_key:
            match = t
            break
        if table_name and t.get("table_name") == table_name:
            match = t
            break

    if not match:
        identifier = table_key or table_name
        click.echo(f"未找到表: {identifier}", err=True)
        ctx.exit(1)

    resp["data"] = match
    output(resp, as_json=ctx.obj.get("as_json", False))


# ── Column management ────────────────────────────────────────────

@base.command(name="column-add")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--column-name", "-n", required=True, help="列名称")
@click.option("--type", "-t", "col_type", required=True,
              type=click.Choice(["string", "number", "boolean", "date", "time",
                                 "datetime", "reference", "file", "user", "group", "select"]),
              help="列类型")
@click.option("--title-column/--no-title-column", default=False, help="是否为标题列")
@click.option("--multiple/--no-multiple", default=False, help="是否多选")
@click.option("--reference-table-key", default=None, help="关联表的 table_key (reference 类型时使用)")
@click.option("--options", default=None, help="列选项 JSON 对象或文件路径 (select 类型时使用)")
@click.option("--extra", default=None, help="扩展元数据 JSON 对象或文件路径")
@click.pass_context
def column_add(ctx, table_key, table_name, column_name, col_type, title_column,
               multiple, reference_table_key, options, extra):
    """向数据表添加一列。"""
    _ensure_table(table_key, table_name)

    body: dict = {"column_name": column_name, "type": col_type}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if title_column:
        body["title_column"] = True
    if multiple:
        body["multiple"] = True
    if reference_table_key:
        body["reference_table_key"] = reference_table_key
    if options:
        body["options"] = _parse_json_or_file(options, "options")
    if extra:
        body["extra"] = _parse_json_or_file(extra, "extra")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/data/table/columns", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command(name="column-update")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--column-key", default=None, help="列标识 (与 --column-name 二选一)")
@click.option("--column-name", default=None, help="列名称 (与 --column-key 二选一)")
@click.option("--new-column-name", default=None, help="新列名称")
@click.option("--extra", default=None, help="扩展元数据 JSON 对象或文件路径")
@click.pass_context
def column_update(ctx, table_key, table_name, column_key, column_name,
                  new_column_name, extra):
    """更新列属性。"""
    _ensure_table(table_key, table_name)
    if not column_key and not column_name:
        raise click.BadParameter("需要 --column-key 或 --column-name")
    if not new_column_name and not extra:
        raise click.BadParameter("需要 --new-column-name 或 --extra")

    body: dict = {}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if column_key:
        body["column_key"] = column_key
    else:
        body["column_name"] = column_name
    if new_column_name:
        body["new_column_name"] = new_column_name
    if extra:
        body["extra"] = _parse_json_or_file(extra, "extra")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.put("/data/table/columns", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@base.command(name="column-delete")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--column-key", default=None, help="列标识 (与 --column-name 二选一)")
@click.option("--column-name", default=None, help="列名称 (与 --column-key 二选一)")
@click.pass_context
def column_delete(ctx, table_key, table_name, column_key, column_name):
    """软删除列。"""
    _ensure_table(table_key, table_name)
    if not column_key and not column_name:
        raise click.BadParameter("需要 --column-key 或 --column-name")

    body: dict = {}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if column_key:
        body["column_key"] = column_key
    else:
        body["column_name"] = column_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.delete("/data/table/columns", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


# ──────────────────────────── 表权限管理 ────────────────────────────


def _resolve_table_key(client: EmooClient, table_key: str | None, table_name: str | None) -> str:
    """根据 table_key 或 table_name 解析出真实的 table_key。"""
    if table_key:
        return table_key
    # 通过 table_name 查 table_key
    resp = client.request("GET", "/data/table", params={"page_size": "200", "current_page": "1"})
    tables = resp.get("data", {}).get("results", [])
    for t in tables:
        if t.get("table_name") == table_name:
            return t["table_key"]
    raise click.BadParameter(f"未找到表: {table_name}")


@base.group(name="permission", help="表权限策略管理")
def permission_group() -> None:
    pass


@permission_group.command("list")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.pass_context
def permission_list(ctx: click.Context, table_key: str | None, table_name: str | None) -> None:
    """获取指定表的所有权限策略。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    tk = _resolve_table_key(client, table_key, table_name)
    resp = client.request("GET", f"/data/table/{tk}/permissions")
    data = resp.get("data", [])

    if ctx.obj.get("as_json"):
        resp["data"] = data
        output(resp, as_json=True)
        return

    if not data:
        click.echo("该表暂无权限策略")
        return

    from rich.table import Table
    table = Table(title=f"表权限策略 (table_key={tk})")
    table.add_column("role_key", style="cyan")
    table.add_column("描述")
    table.add_column("受众")
    table.add_column("数据范围")
    table.add_column("允许增")
    table.add_column("允许删")
    table.add_column("允许改表")

    for p in data:
        audience = p.get("audience", {})
        aud_type = audience.get("type", "")
        if aud_type == "all":
            aud_label = "所有人"
        elif aud_type == "specified":
            aud_label = f"指定成员({len(audience.get('user_open_ids', []))}人)"
        else:
            aud_label = str(aud_type)
        table.add_row(
            p.get("role_key", ""),
            p.get("description", ""),
            aud_label,
            p.get("data_range", ""),
            "✅" if p.get("allow_create") else "❌",
            "✅" if p.get("allow_delete") else "❌",
            "✅" if p.get("allow_schema_update") else "❌",
        )

    from rich.console import Console
    Console().print(table)


@permission_group.command("create")
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--desc", "-d", default="", type=str, help="策略描述")
@click.option("--audience-type", default="all", type=str, help="受众类型: all / specified")
@click.option("--user-open-ids", default=None, type=str, help="受众 open_id，逗号分隔 (audience-type=specified 时)")
@click.option("--group-ids", default=None, type=str, help="受众角色 ID，逗号分隔 (audience-type=specified 时)")
@click.option("--data-range", default="all", type=str, help="数据范围: all")
@click.option("--column-perms", default=None, type=str,
              help="列权限 JSON: {\"column_key\":\"editable\", ...}")
@click.option("--allow-create/--no-create", default=True)
@click.option("--allow-delete/--no-delete", default=False)
@click.option("--allow-schema-update/--no-schema-update", default=False)
@click.option("--allow-schema-delete/--no-schema-delete", default=False)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def permission_create(ctx: click.Context, table_key: str | None, table_name: str | None,
                      desc: str, audience_type: str, user_open_ids: str | None,
                      group_ids: str | None, data_range: str, column_perms: str | None,
                      allow_create: bool, allow_delete: bool, allow_schema_update: bool,
                      allow_schema_delete: bool, dry_run: bool) -> None:
    """为指定表创建一条权限策略。"""
    import json as _json
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    tk = _resolve_table_key(client, table_key, table_name)

    audience: dict = {"type": audience_type}
    if audience_type == "specified" and (user_open_ids or group_ids):
        if user_open_ids:
            audience["user_open_ids"] = [x.strip() for x in user_open_ids.split(",")]
        if group_ids:
            audience["group_ids"] = [int(x.strip()) for x in group_ids.split(",")]

    body: dict = {
        "description": desc,
        "audience": audience,
        "data_range": data_range,
        "conditions": [],
        "column_permissions": _json.loads(column_perms) if column_perms else {},
        "allow_create": allow_create,
        "allow_delete": allow_delete,
        "allow_schema_update": allow_schema_update,
        "allow_schema_delete": allow_schema_delete,
    }

    if dry_run:
        click.echo(f"DRY-RUN POST /data/table/{tk}/permissions")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    resp = client.request("POST", f"/data/table/{tk}/permissions", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@permission_group.command("update")
@click.argument("role_key", type=str)
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--desc", "-d", default=None, type=str, help="策略描述")
@click.option("--audience-type", default=None, type=str, help="受众类型: all / specified")
@click.option("--user-open-ids", default=None, type=str, help="受众 open_id，逗号分隔")
@click.option("--group-ids", default=None, type=str, help="受众角色 ID，逗号分隔")
@click.option("--data-range", default=None, type=str, help="数据范围")
@click.option("--column-perms", default=None, type=str, help="列权限 JSON")
@click.option("--allow-create/--no-create", default=None)
@click.option("--allow-delete/--no-delete", default=None)
@click.option("--allow-schema-update/--no-schema-update", default=None)
@click.option("--allow-schema-delete/--no-schema-delete", default=None)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def permission_update(ctx: click.Context, role_key: str, table_key: str | None, table_name: str | None,
                      desc: str | None, audience_type: str | None, user_open_ids: str | None,
                      group_ids: str | None, data_range: str | None, column_perms: str | None,
                      allow_create: bool | None, allow_delete: bool | None,
                      allow_schema_update: bool | None, allow_schema_delete: bool | None,
                      dry_run: bool) -> None:
    """更新权限策略（整策略覆盖）。

    注意：API 为整策略覆盖语义，未传的 required 字段会被置默认值。
    为避免误清空，未指定的 audience/data_range/column_permissions 会从当前策略继承。
    """
    import json as _json
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    tk = _resolve_table_key(client, table_key, table_name)

    # 整策略覆盖：先取当前策略作为基底，确保 required 字段始终存在
    cur_resp = client.request("GET", f"/data/table/{tk}/permissions")
    current: dict = {}
    for p in cur_resp.get("data", []):
        if p.get("role_key") == role_key:
            current = p
            break
    if not current:
        raise click.BadParameter(f"未找到权限策略 '{role_key}' (table={tk})")

    # 服务端约束: 标题列不可设为 hidden (base_title_column_hidden_forbidden)
    # 继承当前列权限时，自动把 hidden 的标题列提级为 visible
    raw_col_perms = dict(current.get("column_permissions", {}))
    fixed_col_perms = {
        k: ("visible" if v == "hidden" else v)
        for k, v in raw_col_perms.items()
    } if raw_col_perms else {}

    body: dict = {
        "description": current.get("description", ""),
        "audience": current.get("audience", {"type": "all"}),
        "data_range": current.get("data_range", "all"),
        "conditions": current.get("conditions", []),
        "column_permissions": fixed_col_perms,
        "allow_create": current.get("allow_create", False),
        "allow_delete": current.get("allow_delete", False),
        "allow_schema_update": current.get("allow_schema_update", False),
        "allow_schema_delete": current.get("allow_schema_delete", False),
    }
    # 应用用户指定字段的覆盖
    if desc is not None:
        body["description"] = desc
    if audience_type is not None:
        audience: dict = {"type": audience_type}
        if audience_type == "specified" and (user_open_ids or group_ids):
            if user_open_ids:
                audience["user_open_ids"] = [x.strip() for x in user_open_ids.split(",")]
            if group_ids:
                audience["group_ids"] = [int(x.strip()) for x in group_ids.split(",")]
        body["audience"] = audience
    if data_range is not None:
        body["data_range"] = data_range
    if column_perms is not None:
        body["column_permissions"] = _json.loads(column_perms)
    if allow_create is not None:
        body["allow_create"] = allow_create
    if allow_delete is not None:
        body["allow_delete"] = allow_delete
    if allow_schema_update is not None:
        body["allow_schema_update"] = allow_schema_update
    if allow_schema_delete is not None:
        body["allow_schema_delete"] = allow_schema_delete

    if dry_run:
        click.echo(f"DRY-RUN PUT /data/table/{tk}/permissions/{role_key}")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    resp = client.request("PUT", f"/data/table/{tk}/permissions/{role_key}", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@permission_group.command("delete")
@click.argument("role_key", type=str)
@click.option("--table-key", default=None, help="表标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表名称 (与 --table-key 二选一)")
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def permission_delete(ctx: click.Context, role_key: str, table_key: str | None, table_name: str | None,
                      force: bool, dry_run: bool) -> None:
    """删除权限策略。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除权限策略 '{role_key}'？此操作不可逆", abort=True)

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    tk = _resolve_table_key(client, table_key, table_name)

    if dry_run:
        click.echo(f"DRY-RUN DELETE /data/table/{tk}/permissions/{role_key}")
        return

    resp = client.request("DELETE", f"/data/table/{tk}/permissions/{role_key}")
    success(resp, as_json=ctx.obj.get("as_json", False))
