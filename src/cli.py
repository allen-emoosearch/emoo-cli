"""EMOO OpenAPI CLI — main entry point."""

import click

from .commands import auth, contact, data, chat, message, base

EPILOG = """\b
快速开始:
  emoo auth login --api-key <key>       API Key 登录 (推荐)
  emoo auth login --client-id <id> ...  OAuth2 登录
  emoo auth status                      查看认证状态
  emoo data search -k "关键词"           搜索数据
  emoo chat send -q "你好"              发送对话

更多帮助: emoo <command> --help
"""


@click.group(epilog=EPILOG)
@click.option("--json", "as_json", is_flag=True, help="输出原始 JSON 格式")
@click.option("--user-id", envvar="EMOO_USER_ID", help="用户 open_id (OAuth2 方式，可用 emoo contact list 获取)")
@click.option("--base-url", envvar="EMOO_BASE_URL", help="API Base URL (默认 https://app.emoosearch.com/open-api/v1)")
@click.pass_context
def cli(ctx, as_json, user_id, base_url):
    """EMOO 开放平台命令行工具 — 鉴权、通讯录、数据搜索、对话、消息推送、Base 数据表操作."""
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json
    ctx.obj["user_id"] = user_id
    ctx.obj["base_url"] = base_url


cli.add_command(auth.auth)
cli.add_command(contact.contact)
cli.add_command(data.data)
cli.add_command(chat.chat)
cli.add_command(message.message)
cli.add_command(base.base)
