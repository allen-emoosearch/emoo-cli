"""EMOO Base command: create records."""

import json

import click

from ..client import EmooClient
from ..formatters import success


@click.group()
def base():
    """EMOO Base 操作."""


@base.command()
@click.option("--table-key", default=None, help="表的系统标识 (与 --table-name 二选一)")
@click.option("--table-name", default=None, help="表的显示名称 (与 --table-key 二选一)")
@click.option("--records", "-r", required=True, help="记录 JSON 字符串或文件路径")
@click.pass_context
def record_create(ctx, table_key, table_name, records):
    """新建 Record."""
    if not table_key and not table_name:
        raise click.BadParameter("需要 --table-key 或 --table-name")

    try:
        records_data = json.loads(records)
    except json.JSONDecodeError:
        try:
            with open(records) as f:
                records_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raise click.BadParameter(f"无法解析 records: {records}")

    body = {"records": records_data}
    if table_key:
        body["table_key"] = table_key
    else:
        body["table_name"] = table_name

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/data/records", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))
