"""Message commands: push, batch push, and source-system status callbacks."""

from __future__ import annotations

import json
import sys

import click

from ..client import EmooClient
from ..formatters import output, success


def _dry_run_output(ctx, method, path, body):
    """Print dry-run preview of a request."""
    if ctx.obj.get("as_json"):
        click.echo(json.dumps({"dry_run": True, "method": method, "path": path, "body": body},
                              ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.syntax import Syntax
        console = Console()
        console.print(f"[yellow]DRY-RUN[/yellow] {method} {path}")
        console.print("Body:")
        console.print(Syntax(json.dumps(body, ensure_ascii=False, indent=2), "json"))


def _load_json_arg(value: str, name: str):
    """Parse a JSON string, file path, or '-' (stdin)."""
    if value == "-":
        return json.load(sys.stdin)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            with open(value, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise click.BadParameter(f"{name} 不是合法 JSON，也不是已存在的文件: {value}")
        except json.JSONDecodeError as exc:
            raise click.BadParameter(f"{name} 文件 JSON 格式错误: {exc}")


def _collect_keys(keys: tuple[str, ...], from_file: str | None) -> list[str]:
    """Collect thread keys from positional args and/or a file."""
    result = list(keys)
    if from_file:
        with open(from_file, encoding="utf-8") as f:
            text = f.read().strip()
        if text.startswith("["):
            result.extend(json.loads(text))
        else:
            result.extend(line.strip() for line in text.splitlines() if line.strip())
    # de-dup, keep order
    seen: set[str] = set()
    out = []
    for key in result:
        key = str(key)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    if not out:
        raise click.BadParameter("未指定 thread_key (位置参数或 --file)")
    if len(out) > 100:
        raise click.BadParameter(f"thread_key 最多 100 个，当前 {len(out)}")
    return out


def _client(ctx) -> EmooClient:
    return EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))


@click.group()
def message():
    """消息推送与工作项回调 (普通通知、Agent 消息、批量推送、核销/对账)."""


@message.command()
@click.option("--type", "-t", "message_type", type=click.Choice(["normal", "agent"]),
              required=True, help="消息类型")
@click.option("--content", "-c", required=True,
              help="消息内容 (工作项存前 500 字；agent 原文写入对话)")
@click.option("--user-id", "-u", "emoo_user_id", default=None, help="接收者 open_id")
@click.option("--thread-key", default=None,
              help="业务单据 id (≤128 字符；同 user+thread_key 只保留一条工作项，重推即复活)")
@click.option("--due-at", default=None,
              help="截止时间 (ISO 8601，建议带时区偏移，如 2026-09-10T18:00:00+08:00)")
@click.option("--from-title", default=None, help="(normal) 来源名称")
@click.option("--from-image-url", default=None, help="(normal) 来源头像 URL")
@click.option("--detail-link", default=None, help="(normal) 详情链接")
@click.option("--agent-key", default=None, help="(agent) Agent Key")
@click.option("--chat-id", type=int, default=None, help="(agent) 目标对话 ID，省略则自动创建")
@click.option("--dry-run", is_flag=True, help="预览请求而不实际推送")
@click.pass_context
def push(ctx, message_type, content, emoo_user_id, thread_key, due_at,
         from_title, from_image_url, detail_link, agent_key, chat_id, dry_run):
    """推送消息 (每次推送在目标用户待办列表落地一条工作项)。"""
    body: dict = {"message_type": message_type, "content": content}
    if emoo_user_id:
        body["emoo_user_id"] = emoo_user_id
    if thread_key:
        if len(thread_key) > 128:
            raise click.BadParameter("--thread-key 最长 128 字符")
        body["thread_key"] = thread_key
    if due_at:
        body["due_at"] = due_at

    if message_type == "normal":
        if not from_title:
            raise click.BadParameter("normal 类型消息需要 --from-title")
        body["normal_message_info"] = {"from_title": from_title}
        if from_image_url:
            body["normal_message_info"]["from_image_url"] = from_image_url
        if detail_link:
            body["normal_message_info"]["detail_link"] = detail_link

    elif message_type == "agent":
        if not agent_key:
            raise click.BadParameter("agent 类型消息需要 --agent-key")
        body["agent_message_info"] = {"ws_agent_key": agent_key}
        if chat_id:
            body["agent_message_info"]["chat_id"] = chat_id

    if dry_run:
        _dry_run_output(ctx, "POST", "/message", body)
        return

    resp = _client(ctx).post("/message", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@message.command("batch")
@click.option("--file", "-f", "messages_json", required=True,
              help="messages JSON：数组，或含 messages 字段的对象；支持文件路径 / '-' stdin")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def batch(ctx: click.Context, messages_json: str, dry_run: bool) -> None:
    """批量推送消息 (≤50 条，逐条返回结果，不整体原子)。"""
    data = _load_json_arg(messages_json, "--file")
    if isinstance(data, dict):
        messages = data.get("messages")
    else:
        messages = data
    if not isinstance(messages, list) or not messages:
        raise click.BadParameter("需要非空的 messages 数组")
    if len(messages) > 50:
        raise click.BadParameter(f"messages 最多 50 条，当前 {len(messages)}")

    body = {"messages": messages}
    if dry_run:
        _dry_run_output(ctx, "POST", "/message/batch", body)
        return

    resp = _client(ctx).post("/message/batch", body=body)
    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    data_block = resp.get("data", {})
    click.echo(f"成功 {data_block.get('success_count', 0)} 条，"
               f"失败 {data_block.get('failure_count', 0)} 条")
    for item in data_block.get("results", []):
        if item.get("code") != 200:
            click.echo(f"  ✗ index={item.get('index')} code={item.get('code')} "
                       f"{item.get('message', '')}", err=True)


@message.command("status")
@click.argument("thread_keys", nargs=-1)
@click.option("--file", "-f", "from_file", default=None,
              help="从文件读取 thread_key (每行一个，或 JSON 数组)")
@click.option("--status", "target_status", type=click.Choice(["resolved", "reopened"]),
              required=True, help="resolved=核销 (done)；reopened=复活 (pending)")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def status(ctx: click.Context, thread_keys: tuple[str, ...], from_file: str | None,
           target_status: str, dry_run: bool) -> None:
    """按 thread_key 批量核销/复活工作项 (≤100，幂等)。"""
    keys = _collect_keys(thread_keys, from_file)
    body = {"thread_keys": keys, "status": target_status}

    if dry_run:
        _dry_run_output(ctx, "POST", "/message/status", body)
        return

    resp = _client(ctx).post("/message/status", body=body)
    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    for item in resp.get("data", {}).get("results", []):
        click.echo(f"{item.get('thread_key')}: {item.get('status')} "
                   f"(更新 {item.get('updated_count', 0)} 条)")


@message.command("status-query")
@click.argument("thread_keys", nargs=-1)
@click.option("--file", "-f", "from_file", default=None,
              help="从文件读取 thread_key (每行一个，或 JSON 数组)")
@click.pass_context
def status_query(ctx: click.Context, thread_keys: tuple[str, ...],
                 from_file: str | None) -> None:
    """按 thread_key 对账查询各收件人的工作项状态 (≤100)。"""
    keys = _collect_keys(thread_keys, from_file)
    resp = _client(ctx).post("/message/status/query", body={"thread_keys": keys})

    if ctx.obj.get("as_json"):
        output(resp, as_json=True)
        return

    results = resp.get("data", {}).get("results", [])
    if not results:
        click.echo("无结果")
        return

    from rich.console import Console
    from rich.table import Table
    console = Console()
    for entry in results:
        items = entry.get("items") or []
        table = Table(title=f"{entry.get('thread_key')} ({len(items)} 个收件人)")
        table.add_column("item_id")
        table.add_column("open_id")
        table.add_column("status")
        table.add_column("has_read")
        table.add_column("done_source")
        for item in items:
            table.add_row(
                str(item.get("item_id", "")),
                item.get("emoo_user_id", ""),
                item.get("status", ""),
                "✅" if item.get("has_read") else "❌",
                item.get("done_source") or "",
            )
        console.print(table)
