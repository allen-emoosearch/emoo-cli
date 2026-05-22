"""Chat commands: list, create, and send messages."""

import json

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


@click.group()
def chat():
    """对话管理 (列表、创建、发送消息)."""


@chat.command()
@click.option("--page-size", default=50, help="每页条数")
@click.option("--current-page", default=1, help="页码")
@click.pass_context
def list(ctx, page_size, current_page):
    """获取对话列表."""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.get("/chat", params={"page_size": page_size, "current_page": current_page})
    output(resp, as_json=ctx.obj.get("as_json", False))


@chat.command()
@click.option("--title", default=None, help="对话标题")
@click.pass_context
def create(ctx, title):
    """创建新对话."""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    body = {}
    if title:
        body["title"] = title
    resp = client.post("/chat", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))


@chat.command()
@click.option("--query", "-q", required=True, help="提问内容")
@click.option("--chat-id", type=int, default=None, help="对话 ID，为空则创建新对话")
@click.option("--file-list", default=None, help="引用文件列表，逗号分隔")
@click.option("--ws-agent-key", default=None, help="指定 Agent Key")
@click.option("--dry-run", is_flag=True, help="预览请求而不实际发送")
@click.pass_context
def send(ctx, query, chat_id, file_list, ws_agent_key, dry_run):
    """发送对话消息."""
    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    body = {"query": query, "stream": False}
    if chat_id:
        body["chat_id"] = chat_id
    if file_list:
        body["file_list"] = [f.strip() for f in file_list.split(",")]
    if ws_agent_key:
        body["ws_agent_key"] = ws_agent_key

    if dry_run:
        _dry_run_output(ctx, "POST", "/chat/messages", body)
        return

    resp = client.post("/chat/messages", body=body)
    as_json = ctx.obj.get("as_json", False)
    if as_json:
        output(resp, as_json=True)
    else:
        inner = resp.get("data", resp)
        if isinstance(inner, dict):
            click.echo(f"chat_id: {inner.get('chat_id', 'N/A')}")
            click.echo(f"message_id: {inner.get('message_id', 'N/A')}")
            click.echo("---")
            click.echo(inner.get("complete_response", ""))
        else:
            output(resp)
