"""Structured error system for EMOO CLI.

Every error carries a hint telling both human and Agent how to fix it.
When --json is active, errors are serialized to stderr as structured JSON.
"""

from __future__ import annotations

import json
import sys
from typing import Optional


class EmooError(Exception):
    """Base error for all EMOO CLI failures."""

    def __init__(self, message: str, code: Optional[int] = None,
                 hint: str = "", recoverable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint
        self.recoverable = recoverable

    def to_dict(self) -> dict:
        d: dict = {
            "error": type(self).__name__,
            "message": self.message,
        }
        if self.code is not None:
            d["code"] = self.code
        if self.hint:
            d["hint"] = self.hint
        if self.recoverable:
            d["recoverable"] = True
        return d

    def emit(self) -> None:
        """Write structured JSON error to stderr, or plain text to stderr."""
        if _json_mode:
            sys.stderr.write(json.dumps(self.to_dict(), ensure_ascii=False) + "\n")
        else:
            hint_str = f"\n  → {self.hint}" if self.hint else ""
            sys.stderr.write(f"错误: {self.message}{hint_str}\n")


# Global flag set by CLI entry point when --json is active
_json_mode = False


def set_json_mode(on: bool) -> None:
    global _json_mode
    _json_mode = on


# ── Error hierarchy ──────────────────────────────────────────────────────────

class AuthError(EmooError):
    """Authentication/credential failures (code 4083, token expired)."""

    def __init__(self, message: str = "", code: int = 0):
        super().__init__(
            message=message or "认证失败",
            code=code or 4083,
            hint="请重新登录: emoo auth login --api-key <key>  或  emoo auth login --client-id <id> --client-secret <secret>",
            recoverable=True,
        )


class PermissionError(EmooError):
    """Permission denied (code 4042, 4084)."""

    def __init__(self, message: str = "", code: int = 0):
        super().__init__(
            message=message or "无权限访问",
            code=code or 4042,
            hint="请检查 Emoo-User-Id 是否正确 (emoo auth status)，或确认当前用户有权访问此资源",
            recoverable=False,
        )


class NotFoundError(EmooError):
    """Resource not found (code 4008, 4044, 4133)."""

    def __init__(self, message: str = "", code: int = 0,
                 resource: str = ""):
        hint = f"请检查 {resource} 是否正确" if resource else \
               "请检查参数是否正确，或在 EMOO 管理后台确认资源是否存在"
        super().__init__(
            message=message or "资源不存在",
            code=code or 4008,
            hint=hint,
            recoverable=False,
        )


class ValidationError(EmooError):
    """Request validation failure (HTTP 400, bad parameters)."""

    def __init__(self, message: str = "", code: int = 0):
        super().__init__(
            message=message or "请求参数错误",
            code=code or 400,
            hint="请使用 emoo schema <resource>.<method> 查看参数说明，或使用 --help 查看命令用法",
            recoverable=False,
        )


class ServerError(EmooError):
    """Server-side failure (HTTP 500, unknown API errors)."""

    def __init__(self, message: str = "", code: int = 0):
        super().__init__(
            message=message or "服务器内部错误",
            code=code or 500,
            hint="EMOO 服务端异常，请稍后重试。如持续出现请联系技术支持",
            recoverable=True,
        )


# ── Mapping: EMOO error code → error class ──────────────────────────────────

_ERROR_CODE_MAP = {
    4083: AuthError,
    4084: PermissionError,
    4008: NotFoundError,
    4044: ValidationError,
    4092: NotFoundError,
    4133: NotFoundError,
    4042: PermissionError,
}

_HTTP_STATUS_MAP = {
    400: ValidationError,
    401: AuthError,
    403: PermissionError,
    404: NotFoundError,
    500: ServerError,
}


def from_api_response(code: int, http_status: int,
                      message: str = "") -> EmooError:
    """Build the right error class from an API response code + HTTP status."""
    cls = _ERROR_CODE_MAP.get(code) or _HTTP_STATUS_MAP.get(http_status)
    if cls is None:
        return ServerError(message=message or f"未知错误 [code={code}]", code=code)
    return cls(message=message, code=code)
