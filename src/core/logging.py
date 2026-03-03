import logging


class _DefaultEventFieldsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "action"):
            record.action = "-"
        if not hasattr(record, "user_id"):
            record.user_id = "-"
        if not hasattr(record, "chat_id"):
            record.chat_id = "-"
        return True


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s action=%(action)s user_id=%(user_id)s chat_id=%(chat_id)s %(message)s",
    )
    default_filter = _DefaultEventFieldsFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(default_filter)


class EventAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("action", "unknown")
        extra.setdefault("user_id", "-")
        extra.setdefault("chat_id", "-")
        return msg, kwargs
