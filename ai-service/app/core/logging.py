import json
import logging
import sys

from app.core.request_id import request_id, traceparent


def _trace_id(tp: str | None) -> str | None:
    if not tp:
        return None
    parts = tp.split("-")
    return parts[1] if len(parts) >= 2 else None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = request_id.get()
        if rid:
            payload["request_id"] = rid
        tp = traceparent.get()
        tid = _trace_id(tp)
        if tid:
            payload["trace_id"] = tid
        ctx = getattr(record, "ctx", None)
        if isinstance(ctx, dict):
            payload.update(ctx)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log(logger: logging.Logger, msg: str, **ctx) -> None:
    logger.info(msg, extra={"ctx": ctx})
