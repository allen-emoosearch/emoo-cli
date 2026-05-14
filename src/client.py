"""HTTP client with auto token management and error handling."""

import time
from typing import Optional

import click
import requests

from . import config

ERROR_CODES = {
    4083: "API Token 无效",
    4084: "Emoo-User-Id 无效",
    4092: "ws_agent_key 不存在",
    4044: "对话消息不能为空",
}


class EmooClient:
    def __init__(self, base_url: Optional[str] = None, user_id: Optional[str] = None):
        self.base_url = (base_url or config.get_base_url()).rstrip("/")
        self.user_id = user_id or config.get_default_user_id()
        self._ensure_token()

    def _ensure_token(self) -> None:
        token = config.get_token()
        if not token:
            self._refresh_token()
        else:
            expires = config.load().get("expires_at", 0)
            if time.time() > expires - 60:  # 60s buffer
                self._refresh_token()

    def _refresh_token(self) -> None:
        client_id, client_secret = config.get_client_credentials()
        if not client_id or not client_secret:
            raise click.ClickException(
                "未配置 client_id/client_secret，请先运行: emoo auth login"
            )

        resp = requests.get(
            f"{self.base_url}/auth/token",
            params={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=30,
        )
        body = resp.json()
        if body.get("code") != 200:
            raise click.ClickException(
                f"获取 token 失败: [{body.get('code')}] {body.get('message')}"
            )

        data = body["data"]
        cfg = config.load()
        cfg["access_token"] = data["access_token"]
        cfg["expires_at"] = int(time.time()) + data["expires_in"]
        config.save(cfg)

    def _headers(self) -> dict:
        h = {"Authorization": f"Bearer {config.get_token()}"}
        if self.user_id:
            h["Emoo-User-Id"] = self.user_id
        return h

    def _handle_response(self, resp: requests.Response) -> dict:
        body = resp.json()
        code = body.get("code")
        if code != 200:
            msg = ERROR_CODES.get(code, body.get("message", "未知错误"))
            raise click.ClickException(f"[{code}] {msg}")
        return body

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        self._ensure_token()
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=60,
        )
        return self._handle_response(resp)

    def post(self, path: str, body: Optional[dict] = None) -> dict:
        self._ensure_token()
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=body,
            timeout=60,
        )
        return self._handle_response(resp)

    def put(self, path: str, body: dict | list | None = None) -> dict:
        self._ensure_token()
        resp = requests.put(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=body,
            timeout=60,
        )
        return self._handle_response(resp)
