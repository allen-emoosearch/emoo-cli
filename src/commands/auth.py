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


@auth.command(name="clear-cache")
def clear_cache():
    """清除请求缓存 (包括 GET 请求缓存)."""
    from ..client import clear_cache as _clear_cache
    _clear_cache()
    click.echo("请求缓存已清除")


@auth.command(name="switch")
@click.argument("name", required=False)
@click.option("--save", "save_as", default=None, help="将当前配置另存为指定名称")
@click.option("--list", "list_only", is_flag=True, default=False, help="列出所有可用配置")
def switch(name, save_as, list_only):
    """切换/管理多工作区配置文件。

    \b
    不带参数: 列出所有可用配置
    --save <name>: 将当前激活的 config.json 另存为 config.<name>.json
    <name>: 切换至 config.<name>.json (复制为 config.json)

    \b
    示例:
      emoo auth switch              # 列出所有配置
      emoo auth switch fengkai      # 切换至 config.fengkai.json
      emoo auth switch qingliu      # 切换至 config.qingliu.json
      emoo auth switch --save 930   # 保存当前配置为 config.930.json
    """
    import os
    import shutil

    config_dir = os.path.expanduser("~/.emoo")
    active = os.path.join(config_dir, "config.json")

    # --save: backup current
    if save_as:
        if not os.path.exists(active):
            click.echo("当前无激活的配置文件", err=True)
            return
        dest = os.path.join(config_dir, f"config.{save_as}.json")
        shutil.copy2(active, dest)
        click.echo(f"已保存: config.{save_as}.json")
        return

    # List or switch
    configs = []
    for f in sorted(os.listdir(config_dir)):
        if f.startswith("config.") and f.endswith(".json"):
            name_part = f[7:-5]  # extract "xxx" from "config.xxx.json"
            if name_part:
                configs.append(name_part)

    # --list or no args: show all
    if list_only or not name:
        if not configs:
            click.echo("无已保存的配置")
            return

        # Show current active (compare by file content hash)
        current_hash = ""
        try:
            from hashlib import md5
            with open(active, "rb") as f:
                current_hash = md5(f.read()).hexdigest()
        except Exception:
            pass

        click.echo("可用配置:")
        for c in sorted(configs):
            cfg_path = os.path.join(config_dir, f"config.{c}.json")
            cfg_key = ""
            cfg_hash = ""
            try:
                with open(cfg_path, "rb") as f:
                    cfg_hash = md5(f.read()).hexdigest()  # noqa: F821
                with open(cfg_path) as f:
                    cfg_data = json.load(f)  # noqa: F821
                cfg_key = (cfg_data.get("api_key") or cfg_data.get("client_id", ""))[:16]
            except Exception:
                pass
            marker = " ← 当前" if cfg_hash == current_hash else ""
            label = f"{c} ({cfg_key}...)" if cfg_key else c
            click.echo(f"  {label}{marker}")
        return

    # Switch
    src = os.path.join(config_dir, f"config.{name}.json")
    if not os.path.exists(src):
        click.echo(f"配置不存在: config.{name}.json", err=True)
        click.echo(f"可用: {', '.join(configs)}", err=True)
        return

    shutil.copy2(src, active)
    click.echo(f"已切换至: {name}")
