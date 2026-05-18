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
@click.option("--record-key", required=True, help="记录标识")
@click.option("--fields", "-f", required=True, help="需要更新的字段 JSON 对象或文件路径")
@click.pass_context
def record_update(ctx, table_key, table_name, record_key, fields):
    """更新单条记录。"""
    _ensure_table(table_key, table_name)
    try:
        fields_data = json.loads(fields)
    except json.JSONDecodeError:
        try:
            with open(fields) as f:
                fields_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise click.BadParameter(f"无法解析 fields: {fields}")

    body = {"record_key": record_key, "fields": fields_data}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name

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
@click.option("--record-keys", "-k", required=True, help="记录标识数组 JSON 或文件路径 (最多100条)")
@click.pass_context
def record_delete(ctx, table_key, table_name, record_keys):
    """删除记录。"""
    _ensure_table(table_key, table_name)
    keys_data = _parse_records(record_keys)
    if not isinstance(keys_data, list):
        raise click.BadParameter("record_keys 必须是 JSON 字符串数组")
    if len(keys_data) > 100:
        raise click.BadParameter(f"单次最多删除 100 条，当前 {len(keys_data)} 条")

    body = {"record_keys": keys_data}
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
