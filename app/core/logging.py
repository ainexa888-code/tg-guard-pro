import json
import logging
import sys
from datetime import UTC, datetime


class MaskingFormatter(logging.Formatter):
    """Sanitizes sensitive tokens or secrets from logs."""

    def __init__(self, token_to_mask: str = "", fmt: str = None):
        super().__init__(fmt)
        self.token_to_mask = token_to_mask

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if self.token_to_mask and len(self.token_to_mask) > 10:
            msg = msg.replace(self.token_to_mask, "[PROTECTED_BOT_TOKEN]")
        return msg


class JSONFormatter(logging.Formatter):
    """Outputs structured logs as JSON strings."""

    def __init__(self, token_to_mask: str = ""):
        super().__init__()
        self.token_to_mask = token_to_mask

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        raw_json = json.dumps(log_record)
        if self.token_to_mask and len(self.token_to_mask) > 10:
            raw_json = raw_json.replace(self.token_to_mask, "[PROTECTED_BOT_TOKEN]")
        return raw_json


def setup_logger(
    log_level: str = "INFO", bot_token: str = "", use_json: bool = False
) -> logging.Logger:
    logger = logging.getLogger("tg_guard_pro")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if use_json:
            formatter = JSONFormatter(token_to_mask=bot_token)
        else:
            formatter = MaskingFormatter(
                token_to_mask=bot_token,
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
            )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
