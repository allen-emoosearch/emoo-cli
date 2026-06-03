"""Auth commands: login and status."""

import click

from ..client import EmooClient
from .. import config
from ..formatters import token_status, output


@click.group()
def auth():
    """鉴权管理 (登录、查看状态、设置默认用户、切换Endpoint)."""


@auth.command()
@click.option("--client-id", envvar="EMOO_CLIENT_ID", help="客户端 ID (OAuth2 方式)")
@click.option("--client-secret", hide_input=True, envvar="EMOO_CLIENT_SECRET", help="客户端密钥 (OAuth2 方式)")
@click.option("--api-key", envvar="EMOO_API_KEY", help="API Key (以 emoo_ 开头，使用 API Key 认证)")
@click.option("--base-url", envvar="EMOO_BASE_URL", help="API Base URL")
def login(client_id, client_secret, api_key, base_url):
    """登录并获取 API Token (OAuth2 或 API Key 二选一)."""
    if api_key:
        cfg = config.load()
        cfg["api_key"] = api_key
        if base_url:
            cfg["base_url"] = base_url
        # Clear OAuth2 credentials when switching to API Key
        cfg.pop("client_id", None)
        cfg.pop("client_secret", None)
        cfg.pop("access_token", None)
        cfg.pop("expires_at", None)
        config.save(cfg)
        click.echo("API Key 已保存到 ~/.emoo/config.json")
    else:
        if not client_id:
            client_id = click.prompt("Client ID")
        if not client_secret:
            client_secret = click.prompt("Client Secret", hide_input=True)
        cfg = config.load()
        cfg["client_id"] = client_id
        cfg["client_secret"] = client_secret
        if base_url:
            cfg["base_url"] = base_url
        # Clear API Key when switching to OAuth2
        cfg.pop("api_key", None)
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


@auth.command(name="set-base-url")
@click.argument("base_url", required=False)
def set_base_url(base_url):
    """设置/查看 Base URL (持久化到 ~/.emoo/config.json).

    \b
    不带参数时显示当前 Base URL，带参数时更新。
    """
    if not base_url:
        current = config.get_base_url()
        click.echo(f"当前 Base URL: {current}")
        return

    config.set_("base_url", base_url)
    click.echo(f"Base URL 已设置为: {base_url}")
