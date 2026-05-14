"""EMOO OpenAPI CLI — main entry point."""

import click

from .commands import auth, contact, data, chat, message, base


@click.group()
@click.option("--json", "as_json", is_flag=True, help="输出原始 JSON 格式")
@click.option("--user-id", envvar="EMOO_USER_ID", help="Emoo-User-Id header 值")
@click.option("--base-url", envvar="EMOO_BASE_URL", help="API Base URL")
@click.pass_context
def cli(ctx, as_json, user_id, base_url):
    """EMOO 开放平台命令行工具."""
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
