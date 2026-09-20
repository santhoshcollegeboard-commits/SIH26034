"""Centralized persistent rotating logging system for PackCheck.

Provides:
1. RotatingFileHandler writing to logs/packcheck.log (maxBytes=5MB, backupCount=3).
2. Readable format: timestamp | level | event | key=value ...
3. Robust security redaction (API keys, Bearer tokens, Authorization headers, base64 payloads).
4. Safe API credential identification (e.g. key=GEMINI_API_KEY).
5. Request correlation via ContextVar (request_id and panel_idx).
6. High-level structured event logging helpers for lifecycle, OCR, fallback, and GTIN events.
7. Fail-safe design: logging failures never crash the application.
"""

from contextvars import ContextVar
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import sys
import time
from typing import Any, Optional

# Context variables for request correlation across async execution
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
panel_idx_ctx: ContextVar[Optional[int]] = ContextVar("panel_idx", default=None)

# Redaction regular expressions
REDACTION_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_-]{20,}"), "***REDACTED***"),
    (re.compile(r"gsk_[0-9A-Za-z_-]{20,}"), "***REDACTED***"),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.=]+", re.IGNORECASE), "Bearer ***REDACTED***"),
    (re.compile(r'(?i)(authorization["\']?\s*[:=]\s*["\']?)[^\s,"\']+', re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r'(?i)(password["\']?\s*[:=]\s*["\']?)[^\s,"\']+', re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{40,}"), "[IMAGE_BASE64_DATA_REDACTED]"),
    (re.compile(r"(?:[A-Za-z0-9+/]{80,}={0,2})"), "[BASE64_DATA_REDACTED]"),
]


def sanitize_log_message(msg: str) -> str:
    """Sanitize strings to prevent leaking credentials, tokens, or image payloads."""
    if not isinstance(msg, str):
        return str(msg)
    cleaned = msg
    for pattern, replacement in REDACTION_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


class RedactingFilter(logging.Filter):
    """Logging filter ensuring all emitted records have sanitized messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = sanitize_log_message(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: sanitize_log_message(v) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        sanitize_log_message(a) if isinstance(a, str) else a
                        for a in record.args
                    )
        except Exception:
            pass
        return True


class PackCheckLogFormatter(logging.Formatter):
    """Formats log records as: timestamp | level | [event |] key=value ..."""

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        ct = self.converter(record.created)
        return time.strftime("%Y-%m-%d %H:%M:%S", ct)

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record)
        level = record.levelname
        raw_msg = sanitize_log_message(record.getMessage())

        event = getattr(record, "packcheck_event", None)
        kv_pairs = getattr(record, "packcheck_kv", None)

        if event:
            if kv_pairs:
                line = f"{timestamp} | {level} | {event} | {kv_pairs}"
            else:
                line = f"{timestamp} | {level} | {event}"
        elif " | " in raw_msg:
            line = f"{timestamp} | {level} | {raw_msg}"
        else:
            line = f"{timestamp} | {level} | {raw_msg}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                line = f"{line}\n{sanitize_log_message(record.exc_text)}"

        return line


_logger_initialized: bool = False
_file_handler: Optional[RotatingFileHandler] = None
LOGGER_NAME = "backend.packcheck"


def get_default_log_path() -> Path:
    """Resolve default log file path at <project_root>/logs/packcheck.log."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    return root / "logs" / "packcheck.log"


def setup_logging(
    log_file_path: Optional[Path] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    level: int = logging.INFO,
    force_reconfigure: bool = False,
) -> Optional[RotatingFileHandler]:
    """Configure rotating file handler for PackCheck backend.

    Creates logs directory automatically if it does not exist.
    """
    global _logger_initialized, _file_handler
    if _logger_initialized and not force_reconfigure:
        return _file_handler

    try:
        path = log_file_path or get_default_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            filename=str(path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(PackCheckLogFormatter())
        handler.addFilter(RedactingFilter())

        target_logger = logging.getLogger()
        if _file_handler and _file_handler in target_logger.handlers:
            target_logger.removeHandler(_file_handler)
            try:
                _file_handler.close()
            except Exception:
                pass

        target_logger.addHandler(handler)
        if target_logger.level > level:
            target_logger.setLevel(level)

        _file_handler = handler
        _logger_initialized = True
        return handler
    except Exception as exc:
        sys.stderr.write(f"[PackCheck Logging Error] Failed to initialize file handler: {exc}\n")
        return None


def format_kv(
    request_id: Optional[str] = None,
    panel: Optional[int] = None,
    **kwargs: Any,
) -> str:
    """Format key-value pairs cleanly, prioritizing request_id and panel."""
    pairs: list[str] = []

    req_id = request_id or request_id_ctx.get()
    if req_id:
        pairs.append(f"request_id={req_id}")

    p_num = panel if panel is not None else panel_idx_ctx.get()
    if p_num is not None:
        pairs.append(f"panel={p_num}")

    for k, v in kwargs.items():
        if v is None:
            continue
        v_str = sanitize_log_message(str(v))
        if " " in v_str and not (v_str.startswith('"') and v_str.endswith('"')):
            v_str = f'"{v_str}"'
        pairs.append(f"{k}={v_str}")

    return " ".join(pairs)


def log_event(
    event: str,
    level: int = logging.INFO,
    request_id: Optional[str] = None,
    panel: Optional[int] = None,
    exc_info: Optional[Any] = None,
    **kwargs: Any,
) -> None:
    """Emit a structured event to PackCheck logs safely."""
    try:
        kv_pairs = format_kv(request_id=request_id, panel=panel, **kwargs)
        lg = logging.getLogger(LOGGER_NAME)
        extra = {
            "packcheck_event": event,
            "packcheck_kv": kv_pairs,
        }
        msg = f"{event} | {kv_pairs}" if kv_pairs else event
        lg.log(level, msg, extra=extra, exc_info=exc_info)
    except Exception as exc:
        # Logging failures must never crash PackCheck
        sys.stderr.write(f"[PackCheck Logging Warning] log_event failed: {exc}\n")


# -----------------------------------------------------------------------------
# Structured Event Helpers
# -----------------------------------------------------------------------------

def log_startup(app_name: str, version: str, environment: str, log_file: Optional[str] = None) -> None:
    log_event(
        "STARTUP",
        level=logging.INFO,
        app=app_name,
        version=version,
        env=environment,
        log_file=log_file or str(get_default_log_path()),
    )


def log_shutdown(app_name: str) -> None:
    log_event("SHUTDOWN", level=logging.INFO, app=app_name)


def log_verify_start(request_id: str, panel_count: int) -> None:
    log_event("VERIFY_START", level=logging.INFO, request_id=request_id, panels=panel_count)


def log_verify_complete(
    request_id: str,
    success: bool,
    duration_ms: int,
    verdict: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    level = logging.INFO if success else logging.ERROR
    log_event(
        "VERIFY_COMPLETE",
        level=level,
        request_id=request_id,
        success=str(success).lower(),
        duration_ms=duration_ms,
        verdict=verdict,
        error=error,
    )


def log_extract_start(request_id: str, panel_count: int) -> None:
    log_event("EXTRACT_START", level=logging.INFO, request_id=request_id, panels=panel_count)


def log_extract_complete(
    request_id: str,
    success: bool,
    duration_ms: int,
    model_used: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    level = logging.INFO if success else logging.ERROR
    log_event(
        "EXTRACT_COMPLETE",
        level=level,
        request_id=request_id,
        success=str(success).lower(),
        duration_ms=duration_ms,
        model_used=model_used,
        error=error,
    )


def log_ocr_attempt(
    provider: str,
    model: str,
    key_name: str,
    panel: Optional[int] = None,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "OCR_ATTEMPT",
        level=logging.INFO,
        request_id=request_id,
        panel=panel,
        provider=provider,
        model=model,
        key=key_name,
    )


def log_ocr_success(
    provider: str,
    model: str,
    duration_ms: int,
    panel: Optional[int] = None,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "OCR_SUCCESS",
        level=logging.INFO,
        request_id=request_id,
        panel=panel,
        provider=provider,
        model=model,
        duration_ms=duration_ms,
    )


def log_ocr_failure(
    provider: str,
    model: str,
    error_type: str,
    status_code: Optional[int] = None,
    error_msg: Optional[str] = None,
    panel: Optional[int] = None,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "OCR_FAILURE",
        level=logging.WARNING,
        request_id=request_id,
        panel=panel,
        provider=provider,
        model=model,
        error_type=error_type,
        status_code=status_code,
        error=error_msg,
    )


def log_fallback(
    from_model: str,
    to_model: str,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "FALLBACK",
        level=logging.INFO,
        request_id=request_id,
        **{"from": from_model, "to": to_model},
    )


def log_cooldown(
    candidate: str,
    reason: str,
    duration: str,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "COOLDOWN",
        level=logging.WARNING,
        request_id=request_id,
        candidate=candidate,
        reason=reason,
        duration=duration,
    )


def log_all_providers_exhausted(
    attempts: list[str],
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "ALL_PROVIDERS_EXHAUSTED",
        level=logging.ERROR,
        request_id=request_id,
        attempts="; ".join(attempts),
    )


def log_off_request(
    gtin: str,
    result: str,
    response_time_ms: int,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "OFF_REQUEST",
        level=logging.INFO,
        request_id=request_id,
        provider="OpenFoodFacts",
        gtin=gtin,
        result=result,
        response_time_ms=response_time_ms,
    )


def log_barcode_event(
    event_type: str,
    gtin: Optional[str] = None,
    message: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "BARCODE_EVENT",
        level=logging.INFO,
        request_id=request_id,
        status=event_type,
        gtin=gtin,
        message=message,
    )


def log_backend_exception(
    exc: Exception,
    context: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    log_event(
        "BACKEND_EXCEPTION",
        level=logging.ERROR,
        request_id=request_id,
        context=context,
        error_type=type(exc).__name__,
        error=str(exc),
        exc_info=True,
    )
