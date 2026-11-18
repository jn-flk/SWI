"""One INFO line when a server process starts, plus ERRORs for broken dependency config.

Called from wsgi.py, so it runs for runserver and real WSGI servers,
but not for tests or other management commands.
"""

import logging
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def _commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent,
            capture_output=True, text=True, timeout=2, check=True,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _check_notification_sender():
    try:
        sender = import_string(settings.NOTIFICATION_SENDER)
    except ImportError as error:
        logger.error(
            "operation=app_start failure=invalid_notification_sender detail=%s "
            "outcome=notifications_will_fail", error,
        )
        return
    if sender.__name__ == "HttpSender" and not settings.NOTIFICATION_SERVICE_URL:
        logger.error(
            "operation=app_start failure=missing_notification_service_url "
            "outcome=notifications_will_fail",
        )


def log_startup():
    database = settings.DATABASES["default"]
    logger.info(
        "operation=app_start commit=%s debug=%s database=%s notification_sender=%s outcome=started",
        _commit(), settings.DEBUG, database["ENGINE"].rsplit(".", 1)[-1],
        settings.NOTIFICATION_SENDER.rsplit(".", 1)[-1],
    )
    _check_notification_sender()
