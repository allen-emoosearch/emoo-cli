"""HTTP client with auto token management, auto-refresh, and 4083 retry."""

import time
from typing import Optional

import click
import requests

from . import config

ERROR_CODES = {
    4083: "API Token 无效",
    4084: "Emoo-User-Id 无效，应为 open_id（可用 emoo contact list 获取）",
    4092: "ws_agent_key 不存在",
    4044: "对话消息不能为空",
}

HTTP_STATUS_MESSAGES = {
    400: "请求参数错误",
    401: "认证失败，请检查 API Key 或重新登录",
    403: "无权限访问",
    404: "资源不存在",
    500: "服务器内部错误",
}


class EmooClient:
    def __init__(self, base_url: Optional[str] = None, user_id: Optional[str] = None):
        self.base_url = (base_url or config.get_base_url()).rstrip("/")
        self._use_api_key = config.is_api_key_auth()
        self.user_id = None if self._use_api_key else (user_id or config.get_default_user_id())
        if not self._use_api_key:
            self._ensure_token()

    def _ensure_token(self) -> None:
        if self._use_api_key:
            return
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
        if self._use_api_key:
            return {"Authorization": f"Bearer {config.get_api_key()}"}
        h = {"Authorization": f"Bearer {config.get_token()}"}
        if self.user_id:
            h["Emoo-User-Id"] = self.user_id
        return h

    def _handle_response(self, resp: requests.Response) -> dict:
        body = resp.json()
        code = body.get("code")
        if code is not None and code != 200:
            msg = ERROR_CODES.get(code)
            if msg:
                raise click.ClickException(f"[{code}] {msg}")
            detail = body.get("message", "") or body.get("error", "") or str(body)
            raise click.ClickException(f"[{code}] 服务器错误: {detail}")
        if code is None and not resp.ok:
            http_msg = HTTP_STATUS_MESSAGES.get(resp.status_code, f"HTTP {resp.status_code}")
            detail = body.get("message", "") or body.get("error", "") or str(body)
            raise click.ClickException(f"[{resp.status_code}] {http_msg}: {detail}")
        return body

    def _request(self, method: str, path: str,
                 params: Optional[dict] = None, body: Optional[dict] = None) -> dict:
        """Make HTTP request, auto-refresh token on 4083 and retry once."""
        self._ensure_token()
        resp = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            json=body,
            timeout=60,
        )
        try:
            return self._handle_response(resp)
        except click.ClickException as e:
            if "4083" in str(e):
                self._refresh_token()
                resp = requests.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    params=params,
                    json=body,
                    timeout=60,
                )
                return self._handle_response(resp)
            raise

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Optional[dict] = None) -> dict:
        return self._request("POST", path, body=body)

    def put(self, path: str, body: dict | list | None = None) -> dict:
        return self._request("PUT", path, body=body)
