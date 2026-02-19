"""
檔案用途：結構化 Logging 基礎設施
職責：
  - 提供 JSON 格式的結構化日誌輸出
  - 自動包含 timestamp, level, module, function 等 metadata
  - 支援分級輸出 (DEBUG, INFO, WARNING, ERROR)
  - 不包含敏感資訊 (API Key, Token)

使用範例：
    from core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("開始執行 Step B", week_id="2025-W52", fp_code="abc12345")
    logger.error("Step B 失敗", error=exception, details=["錯誤細節"])
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import TAIPEI_TZ


class JSONFormatter(logging.Formatter):
    """JSON 格式化器：將 log record 轉換為 JSON 格式"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self._format_timestamp(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Trace ID（若有啟用 core.tracing）
        try:
            from core.tracing import get_trace_id

            trace_id = get_trace_id()
            if trace_id:
                log_data["trace_id"] = trace_id
        except Exception:
            pass

        # 加入額外資訊（由 logger.info(msg, **extra) 傳入）
        extra_data = getattr(record, "extra_data", None)
        if extra_data is not None:
            log_data["extra"] = extra_data

        # 加入 exception 資訊
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

    def _format_timestamp(self) -> str:
        """產生 ISO 8601 格式的時間戳記"""
        if TAIPEI_TZ:
            return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
        return datetime.now().isoformat(timespec="seconds")


class StructuredLogger:
    """結構化 Logger 包裝類別"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重複加入 handler
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """設定 log handlers：console + file"""

        # Console handler (stderr)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)

        # File handler (logs/app.log)
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File 記錄所有層級
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

    def debug(self, message: str, **extra: Any) -> None:
        """記錄 DEBUG 訊息"""
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, **extra: Any) -> None:
        """記錄 INFO 訊息"""
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, **extra: Any) -> None:
        """記錄 WARNING 訊息"""
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, error: Exception | None = None, **extra: Any) -> None:
        """記錄 ERROR 訊息，可選包含 exception"""
        if error:
            extra["error_type"] = type(error).__name__
            extra["error_message"] = str(error)
        self._log(logging.ERROR, message, extra, exc_info=error is not None)

    def _log(self, level: int, message: str, extra: dict[str, Any], exc_info: bool = False) -> None:
        """內部 log 方法"""
        # 過濾敏感資訊
        filtered_extra = self._filter_sensitive_data(extra)

        # 使用 extra 參數傳遞額外資訊
        self.logger.log(level, message, extra={"extra_data": filtered_extra}, exc_info=exc_info)

    def _filter_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """過濾敏感資訊（API Key, Token, Password）"""
        filtered = {}
        sensitive_keys = {"api_key", "token", "password", "secret", "credential"}

        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value

        return filtered


# 全域 logger cache
_logger_cache: dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """
    取得 StructuredLogger 實例（單例模式）

    Args:
        name: logger 名稱，通常使用 __name__

    Returns:
        StructuredLogger 實例

    Example:
        logger = get_logger(__name__)
        logger.info("Processing started", week_id="2025-W52")
    """
    if name not in _logger_cache:
        _logger_cache[name] = StructuredLogger(name)
    return _logger_cache[name]


def set_log_level(level: str) -> None:
    """
    設定全域 log level

    Args:
        level: "DEBUG", "INFO", "WARNING", "ERROR"
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    log_level = level_map.get(level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)
