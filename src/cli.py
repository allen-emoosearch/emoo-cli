"""EMOO OpenAPI CLI — main entry point."""

import json
import sys
from importlib.metadata import version as _pkg_version

import click

from .commands import auth, contact, data, chat, message, base, app, skill
from .commands.api import api
from .commands.schema_cmd import schema
from .errors import EmooError, set_json_mode

EPILOG = """\b
快速开始:
  emoo auth login --api-key <key>       API Key 登录 (推荐)
  emoo auth status                      查看认证状态
  emoo api GET /v1/apps                 通用 API 透传 (L3)
  emoo schema data.search               查看端点参数/响应/权限
  emoo skill init                       初始化 + 注册到 Claude Code
  emoo data search -k "关键词"           搜索数据
  emoo chat send -q "你好"              发送对话

更多帮助: emoo <command> --help
"""


_V = _pkg_version("emoo-cli")

@click.group(epilog=EPILOG, help=f"EMOO 开放平台命令行工具 v{_V} — 鉴权、通讯录、数据搜索、对话、消息推送、Base 数据表操作、应用概览.")
@click.version_option(version=_V, prog_name="emoo-cli", message="%(prog)s v%(version)s")
@click.option("--json", "as_json", is_flag=True, help="输出原始 JSON 格式")
@click.option("--user-id", envvar="EMOO_USER_ID",
              help="用户 open_id (OAuth2 方式，可用 emoo contact list 获取)")
@click.option("--base-url", envvar="EMOO_BASE_URL",
              help="API Base URL (默认 https://app.emoosearch.com/open-api/v1)")
@click.pass_context
def cli(ctx, as_json, user_id, base_url):
    """EMOO 开放平台命令行工具 — 鉴权、通讯录、数据搜索、对话、消息推送、Base 数据表操作、应用概览."""
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json
    ctx.obj["user_id"] = user_id
    ctx.obj["base_url"] = base_url
    set_json_mode(as_json)


def main():
    """Entry point with EmooError → stderr handling."""
    try:
        cli(standalone_mode=False)
    except EmooError as e:
        e.emit()
        sys.exit(1)
    except click.ClickException as e:
        e.show()
        sys.exit(1)
    except click.exceptions.Exit:
        raise


cli.add_command(auth.auth)
cli.add_command(contact.contact)
cli.add_command(data.data)
cli.add_command(chat.chat)
cli.add_command(message.message)
cli.add_command(base.base)
cli.add_command(app.app)
cli.add_command(skill.skill)
cli.add_command(api)
cli.add_command(schema)
