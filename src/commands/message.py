"""Message command: push messages to users."""

import json

import click

from ..client import EmooClient
from ..formatters import success


@click.group()
def message():
    """消息推送."""


@message.command()
@click.option("--type", "-t", "message_type", type=click.Choice(["normal", "agent"]), required=True, help="消息类型")
@click.option("--content", "-c", required=True, help="消息内容 (最长300字符)")
@click.option("--user-id", "-u", "emoo_user_id", default=None, help="接收者 Emoo User ID")
@click.option("--from-title", default=None, help="(normal) 来源名称")
@click.option("--from-image-url", default=None, help="(normal) 来源头像 URL")
@click.option("--detail-link", default=None, help="(normal) 详情链接")
@click.option("--agent-key", default=None, help="(agent) Agent Key")
@click.option("--chat-id", type=int, default=None, help="(agent) 目标对话 ID")
@click.pass_context
def push(ctx, message_type, content, emoo_user_id, from_title, from_image_url, detail_link, agent_key, chat_id):
    """主动推送消息给指定用户."""
    body = {"message_type": message_type, "content": content}
    if emoo_user_id:
        body["emoo_user_id"] = emoo_user_id

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
            body["agent_message_info"]["chat_id"] = str(chat_id)

    client = EmooClient(base_url=ctx.obj.get("base_url"), user_id=ctx.obj.get("user_id"))
    resp = client.post("/message", body=body)
    success(resp, as_json=ctx.obj.get("as_json", False))
