"""EMOO Base commands: CRUD operations on data table records."""

import json

import click

from ..client import EmooClient
from ..formatters import success, output


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
    """EMOO Base 数据表操作 (增删改查记录)."""


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


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--page-size", default=20, help="每页数量 (最大100)")
@click.option("--current-page", default=1, help="页码")
@click.option("--filter", "-f", "filters", default=None, help="过滤条件, 逗号分隔 (如 status:eq:active,score:gte:60)")
@click.option("--sort", default=None, help="排序 (如 created_at:desc)")
@click.pass_context
def record_list(ctx, table_key, table_name, page_size, current_page, filters, sort):
    """查询记录列表。"""
    _ensure_table(table_key, table_name)
    if page_size > 100:
        raise click.BadParameter(f"page-size 最大 100，当前为 {page_size}")

    body = {"page_size": page_size, "current_page": current_page}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name
    if filters:
        body["filters"] = [f.strip() for f in filters.split(",")]
    if sort:
        body["sort"] = sort

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
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
    """获取表详情（含完整列信息）。"""
    _ensure_table(table_key, table_name)

    params = {}
    if table_key:
        params["table_key"] = table_key
    else:
        params["table_name"] = table_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.get("/data/table", params=params)
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
