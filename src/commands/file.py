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


@file_group.command("register")
@click.option("--file-key", required=True, help="confirm 后拿到的 file_key")
@click.option("--file-name", required=True, help="原始文件名 (含扩展名)")
@click.option("--file-size", type=int, required=True, help="文件字节数")
@click.option("--mime-type", default=None, help="MIME 类型")
@click.option("--folder-id", type=int, default=None, help="归属 folder id (默认根目录)")
@click.option("--title", default=None, help="展示名 (默认 = file_name)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def file_register(ctx: click.Context, file_key: str, file_name: str, file_size: int,
                  mime_type: str | None, folder_id: int | None, title: str | None,
                  dry_run: bool) -> None:
    """把已上传的文件登记为知识库文件 (可归属 folder)。"""
    import json as _json
    body: dict = {
        "file_key": file_key,
        "file_name": file_name,
        "file_size": file_size,
    }
    if mime_type:
        body["mime_type"] = mime_type
    if folder_id is not None:
        body["folder_id"] = folder_id
    if title:
        body["title"] = title

    if dry_run:
        click.echo("DRY-RUN POST /data/kb-file")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/data/kb-file", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@file_group.command("delete")
@click.argument("doc_key", type=str)
@click.option("--force", "-f", is_flag=True, help="跳过确认")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def file_delete(ctx: click.Context, doc_key: str, force: bool, dry_run: bool) -> None:
    """删除知识库文件 (软删除)。"""
    if not force and not dry_run and not ctx.obj.get("as_json"):
        click.confirm(f"确认删除知识库文件 {doc_key}？", abort=True)

    if dry_run:
        click.echo(f"DRY-RUN DELETE /data/kb-file  doc_key={doc_key}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("DELETE", "/data/kb-file", body={"doc_key": doc_key})
    success(resp, as_json=ctx.obj.get("as_json", False))


@file_group.command("permission-get")
@click.argument("doc_key", type=str)
@click.pass_context
def file_permission_get(ctx: click.Context, doc_key: str) -> None:
    """读取知识库文件的可见/可删除权限。"""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("GET", f"/data/kb-file/{doc_key}/permission")
    output(resp, as_json=ctx.obj.get("as_json", False))


def _audience(prefix: str, kind: str, users: tuple[str, ...], groups: tuple[int, ...]) -> dict:
    if kind == "specified" and not users and not groups:
        raise click.BadParameter(
            f"--{prefix}-type=specified 需要至少一个 --{prefix}-user 或 --{prefix}-group"
        )
    audience: dict = {"type": kind}
    if kind == "specified":
        if users:
            audience["user_open_ids"] = list(users)
        if groups:
            audience["group_ids"] = list(groups)
    return audience


@file_group.command("permission-set")
@click.argument("doc_key", type=str)
@click.option("--visible-type", type=click.Choice(["all", "none", "specified"]),
              default="all", show_default=True, help="谁可见")
@click.option("--visible-user", "visible_users", multiple=True, help="可见用户 open_id (可重复)")
@click.option("--visible-group", "visible_groups", multiple=True, type=int,
              help="可见角色 ws_group_id (可重复)")
@click.option("--deletable-type", type=click.Choice(["all", "none", "specified"]),
              default="none", show_default=True, help="谁可删除")
@click.option("--deletable-user", "deletable_users", multiple=True, help="可删除用户 open_id")
@click.option("--deletable-group", "deletable_groups", multiple=True, type=int,
              help="可删除角色 ws_group_id")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def file_permission_set(ctx: click.Context, doc_key: str, visible_type: str,
                        visible_users: tuple[str, ...], visible_groups: tuple[int, ...],
                        deletable_type: str, deletable_users: tuple[str, ...],
                        deletable_groups: tuple[int, ...], dry_run: bool) -> None:
    """整体覆盖设置知识库文件权限 (visible + deletable 都必填)。"""
    import json as _json
    body = {
        "visible": _audience("visible", visible_type, visible_users, visible_groups),
        "deletable": _audience("deletable", deletable_type, deletable_users, deletable_groups),
    }

    if dry_run:
        click.echo(f"DRY-RUN PUT /data/kb-file/{doc_key}/permission")
        click.echo(f"  Body:\n{_json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("PUT", f"/data/kb-file/{doc_key}/permission", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@file_group.command("extract")
@click.argument("file_keys", nargs=-1)
@click.option("--file", "-f", "from_file", default=None,
              help="从文件读取 file_key (每行一个，或 JSON 数组)")
@click.option("--output-dir", default=None, help="把解析出的文本写入该目录")
@click.pass_context
def file_extract(ctx: click.Context, file_keys: tuple[str, ...],
                 from_file: str | None, output_dir: str | None) -> None:
    """批量解析文件内容为纯文本 (≤20 个，同步返回)。"""
    import json as _json
    from pathlib import Path

    keys = list(file_keys)
    if from_file:
        with open(from_file, encoding="utf-8") as f:
            text = f.read().strip()
        if text.startswith("["):
            keys.extend(_json.loads(text))
        else:
            keys.extend(line.strip() for line in text.splitlines() if line.strip())
    keys = list(dict.fromkeys(k for k in keys if k))
    if not keys:
        raise click.BadParameter("未指定 file_key")
    if len(keys) > 20:
        raise click.BadParameter(f"file_key 最多 20 个，当前 {len(keys)}")

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.request("POST", "/data/files/extract-content",
                          body={"file_keys": keys})

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    results = resp.get("data") or []
    out_dir = Path(output_dir).expanduser() if output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    from rich.console import Console
    from rich.table import Table
    table = Table(title="文件解析结果")
    table.add_column("file_key")
    table.add_column("字符数")
    table.add_column("状态/原因")
    for item in results:
        content = item.get("content") or ""
        reason = item.get("reason") or ("ok" if content else "empty")
        if out_dir:
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in item.get("file_key", "file"))
            target = out_dir / f"{safe}.txt"
            target.write_text(content, encoding="utf-8")
            reason = f"{reason}; -> {target}"
        table.add_row(item.get("file_key", ""), str(len(content)), reason)
    Console().print(table)
