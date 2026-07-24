"""文件管理命令: file credentials / confirm / download-url。

完整上传流程:
  1. emoo file credentials -f '<json>'   → 拿到 upload 指令 + file_key
  2. 客户端按 upload 指令直传对象存储 (PUT 二进制 / POST multipart)
  3. emoo file confirm -f '<json>'       → 通知 emoo 上传完成, 返回 24h 下载链接
  4. emoo file download-url <file_key>   → 刷新下载链接 (24h 后)
"""

from __future__ import annotations

import click

from ..client import EmooClient
from ..formatters import output, success


@click.group("file", help="知识库文件管理 (上传凭证/确认/下载链接)")
def file_group() -> None:
    pass


def _parse_files(value: str) -> list:
    """Parse --files from JSON string or file path."""
    import json as _json
    try:
        data = _json.loads(value)
    except _json.JSONDecodeError:
        try:
            with open(value) as f:
                data = _json.load(f)
        except FileNotFoundError:
            raise click.BadParameter(f"文件不存在: {value}")
        except _json.JSONDecodeError as e:
            raise click.BadParameter(f"JSON 格式错误: {e}")

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "files" in data:
        return data["files"]
    raise click.BadParameter("--files 需为 JSON 数组或含 files 字段的对象")


@file_group.command("credentials")
@click.option("--files", "-f", "files_json", required=True, type=str,
              help="文件信息 JSON: [{\"file_name\",\"file_size\",\"mime_type?\"}, ...] (1-20个)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def file_credentials(ctx: click.Context, files_json: str, dry_run: bool) -> None:
    """获取一批文件的上传凭证 (1-20 个, 凭证 1h 过期)。
    返回 upload 指令 (method=PUT 直传二进制 / method=POST multipart) + file_key。
    """
    import json as _json
    files = _parse_files(files_json)
    if not (1 <= len(files) <= 20):
        raise click.BadParameter(f"文件数量需 1-20，当前 {len(files)}")

    body = {"files": files}

    if dry_run:
        click.echo("DRY-RUN POST /data/files/upload-credentials")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/data/files/upload-credentials", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@file_group.command("confirm")
@click.option("--files", "-f", "files_json", required=True, type=str,
              help="确认信息 JSON: [{\"file_key\",\"file_name\",\"file_size\",\"mime_type?\"}, ...]")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def file_confirm(ctx: click.Context, files_json: str, dry_run: bool) -> None:
    """确认文件上传完成, 创建文件元数据记录, 返回每个文件 24h 下载链接。"""
    import json as _json
    files = _parse_files(files_json)
    if not (1 <= len(files) <= 20):
        raise click.BadParameter(f"文件数量需 1-20，当前 {len(files)}")

    body = {"files": files}

    if dry_run:
        click.echo("DRY-RUN POST /data/files/confirm")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/data/files/confirm", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@file_group.command("download-url")
@click.argument("file_key", type=str)
@click.pass_context
def file_download_url(ctx: click.Context, file_key: str) -> None:
    """获取文件下载链接 (24h 有效, confirm 返回的 URL 过期后用此刷新)。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("GET", "/data/files/download-url", params={"file_key": file_key})
    output(resp, as_json=ctx.obj.get("as_json", False) or True)
