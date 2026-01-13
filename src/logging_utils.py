from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from src.config import AppConfig


class JsonFormatter(logging.Formatter):
    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": self.run_id,
        }
        extras = _extract_extras(record)
        if extras:
            payload.update(extras)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def _extract_extras(record: logging.LogRecord) -> Dict[str, Any]:
    reserved = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
    }
    extras: Dict[str, Any] = {}
    for key, value in record.__dict__.items():
        if key in reserved:
            continue
        extras[key] = _json_safe(value)
    return extras


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def configure_logging(config: AppConfig) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(config.run_id))

    root = logging.getLogger()
    root.setLevel(config.log_level)
    root.handlers = [handler]
