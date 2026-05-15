"""Auth commands: login and status."""

import click

from ..client import EmooClient
from .. import config
from ..formatters import token_status, output


@click.group()
def auth():
    """鉴权管理."""


@auth.command()
@click.option("--client-id", prompt=True, envvar="EMOO_CLIENT_ID", help="客户端 ID")
@click.option("--client-secret", prompt=True, hide_input=True, envvar="EMOO_CLIENT_SECRET", help="客户端密钥")
@click.option("--base-url", envvar="EMOO_BASE_URL", help="API Base URL")
def login(client_id, client_secret, base_url):
    """登录并获取 API Token."""
    cfg = config.load()
    cfg["client_id"] = client_id
    cfg["client_secret"] = client_secret
    if base_url:
        cfg["base_url"] = base_url
    config.save(cfg)

    client = EmooClient(base_url=base_url)
    click.echo("Token 获取成功，已保存到 ~/.emoo/config.json")
    token_status(config.load())


@auth.command()
@click.pass_context
def status(ctx):
    """查看当前 Token 状态."""
    cfg = config.load()
    if ctx.obj.get("as_json", False):
        import json
        print(json.dumps(cfg, indent=2, ensure_ascii=False))
    else:
        token_status(cfg)


@auth.command()
@click.argument("user_id")
@click.option("--username", default=None, help="用户显示名称（可选，方便识别）")
def set_default_user_id(user_id, username):
    """设置默认 Emoo-User-Id，后续命令无需每次传 --user-id."""
    config.set_("default_user_id", user_id)
    if username:
        config.set_("default_user_name", username)
    click.echo(f"默认 User ID 已设置为: {user_id}" + (f" ({username})" if username else ""))
