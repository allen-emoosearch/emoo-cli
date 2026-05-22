"""HTTP client with auto token management, auto-refresh, and 4083 retry."""

import time
from typing import Optional

import requests

from . import config
from .errors import AuthError, from_api_response, EmooError


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
            if time.time() > expires - 60:
                self._refresh_token()

    def _refresh_token(self) -> None:
        client_id, client_secret = config.get_client_credentials()
        if not client_id or not client_secret:
            raise AuthError(
                message="未配置 client_id/client_secret",
                hint="请先运行: emoo auth login --client-id <id> --client-secret <secret>",
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
            raise from_api_response(
                code=body.get("code", 0),
                http_status=resp.status_code,
                message=body.get("message", "获取 token 失败"),
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

    def _check_response(self, resp: requests.Response) -> dict:
        """Check API response and return body or raise structured error."""
        body = resp.json()
        code = body.get("code")
        if code is not None and code != 200:
            raise from_api_response(
                code=code,
                http_status=resp.status_code,
                message=body.get("message", "") or body.get("error", ""),
            )
        if code is None and not resp.ok:
            raise from_api_response(
                code=resp.status_code,
                http_status=resp.status_code,
                message=body.get("message", "") or body.get("error", ""),
            )
        return body

    def _request(self, method: str, path: str,
                 params: Optional[dict] = None, body: Optional[dict] = None) -> dict:
        """Make HTTP request, auto-refresh token on auth error and retry once."""
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
            return self._check_response(resp)
        except AuthError:
            if not self._use_api_key:
                self._refresh_token()
                resp = requests.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    params=params,
                    json=body,
                    timeout=60,
                )
                return self._check_response(resp)
            raise

    def request(self, method: str, path: str,
                params: Optional[dict] = None, body: Optional[dict] = None) -> dict:
        """Public raw request method (for L3 passthrough)."""
        return self._request(method, path, params=params, body=body)

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Optional[dict] = None) -> dict:
        return self._request("POST", path, body=body)

    def put(self, path: str, body: dict | list | None = None) -> dict:
        return self._request("PUT", path, body=body)

    def delete(self, path: str, body: Optional[dict] = None) -> dict:
        return self._request("DELETE", path, body=body)
