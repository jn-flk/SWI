"""Local Notification Service adapter for C02; no external messages are sent."""

import logging

logger = logging.getLogger(__name__)


def notify(reservation_id, event):
    logger.info("Reservation %s: %s", reservation_id, event)
