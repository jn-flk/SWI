"""Only adapters know the external service protocol.

A successful send returns None; a failed send raises an exception.
Receivers must deduplicate by message.id (also the HTTP Idempotency-Key).
"""

import json
import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationMessage:
    id: str
    reservation_id: int
    event: str
    payload: dict


class NotificationSender(Protocol):
    def send(self, message: NotificationMessage) -> None: ...


class LoggingSender:
    """Development sink: SENT means logged locally, not externally delivered."""

    def send(self, message: NotificationMessage) -> None:
        logger.info("Notification %s: reservation=%s event=%s payload=%s",
                    message.id, message.reservation_id, message.event, message.payload)


class HttpSender:
    """POST JSON to a configured service; any non-2xx result is a failure."""

    def send(self, message: NotificationMessage) -> None:
        endpoint = settings.NOTIFICATION_SERVICE_URL
        if not endpoint:
            raise ValueError("NOTIFICATION_SERVICE_URL is required for HttpSender")
        data = json.dumps({
            "id": message.id,
            "reservation_id": message.reservation_id,
            "event": message.event,
            "payload": message.payload,
        }).encode("utf-8")
        request = Request(endpoint, data=data, method="POST", headers={
            "Content-Type": "application/json",
            "Idempotency-Key": message.id,
        })
        with urlopen(request, timeout=settings.NOTIFICATION_TIMEOUT_SECONDS) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Notification service returned HTTP {response.status}")
