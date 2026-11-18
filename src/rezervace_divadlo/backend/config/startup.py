"""INFO lines when a server process starts and stops, plus ERRORs for broken dependency config.

Called from wsgi.py, so it runs for runserver and real WSGI servers,
but not for tests or other management commands.
"""

import atexit
import logging
import os
import signal
import subprocess
import sys
import time
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


def _log_shutdown(started):
    # Runs on normal exit, Ctrl+C (SIGINT), SIGTERM (see below) and runserver reloads.
    # A hard kill (SIGKILL) or a crash of the interpreter cannot be logged.
    logger.info(
        "operation=app_stop pid=%s uptime=%.0fs outcome=stopped",
        os.getpid(), time.monotonic() - started,
    )


def _exit_on_sigterm(signum, frame):
    sys.exit(0)  # turn SIGTERM into a normal exit so atexit handlers run


def log_startup():
    database = settings.DATABASES["default"]
    logger.info(
        "operation=app_start pid=%s commit=%s debug=%s database=%s notification_sender=%s outcome=started",
        os.getpid(), _commit(), settings.DEBUG, database["ENGINE"].rsplit(".", 1)[-1],
        settings.NOTIFICATION_SENDER.rsplit(".", 1)[-1],
    )
    _check_notification_sender()
    atexit.register(_log_shutdown, time.monotonic())
    # Only take over SIGTERM when nobody else handles it (a WSGI server may).
    try:
        if signal.getsignal(signal.SIGTERM) is signal.SIG_DFL:
            signal.signal(signal.SIGTERM, _exit_on_sigterm)
    except ValueError:
        pass  # not in the main thread; leave signals alone
