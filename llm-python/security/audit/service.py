import logging
from collections.abc import Callable


class AuditService:
    def __init__(self, writer: Callable[[object], None] | None = None):
        self._writer = writer

    def write_event(self, event) -> None:
        if self._writer is not None:
            self._writer(event)
            return
        logging.info(
            "audit service=%s action=%s result=%s details=%s",
            event.service,
            event.action,
            event.result,
            event.details,
        )
