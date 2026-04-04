"""Log sanitization filter for EntangledPdf.

Redacts sensitive data from log messages to prevent leakage.
"""

import logging
import re
from typing import Any, Set


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts sensitive data from log messages."""

    BLOCKED_KEYS: Set[str] = {
        "token", "password", "secret", "api_key", "apikey",
        "x-api-key", "authorization", "credentials",
        "websocket_token", "secret_key", "private_key"
    }

    BLOCKED_PATTERNS = [
        re.compile(r"://[^:]+:[^@]+@"),
        re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = self._sanitize_args(record.args)
        return True

    def _sanitize_args(self, args: tuple[Any, ...] | dict[str, Any]) -> tuple[Any, ...] | dict[str, Any]:
        if isinstance(args, dict):
            return self._sanitize_dict(args)
        if isinstance(args, tuple):
            return tuple(self._sanitize_arg(a) for a in args)
        return args

    def _sanitize_arg(self, arg: Any) -> Any:
        if isinstance(arg, dict):
            return self._sanitize_dict(arg)
        if isinstance(arg, str):
            return self._sanitize_string(arg)
        return arg

    def _sanitize_dict(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return data  # type: ignore[return-value]

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in self.BLOCKED_KEYS:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_string(value)
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_string(self, value: str) -> str:
        for pattern in self.BLOCKED_PATTERNS:
            value = pattern.sub("***REDACTED***", value)
        return value
