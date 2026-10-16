"""Compatibility entry point; new code should use notification.services."""

from notification.services import record_notification

from .models import Reservation


def notify(reservation_id, event):
    """Enqueue within the caller's transaction; never contact the sender inline."""
    return record_notification(Reservation.objects.get(pk=reservation_id), event)
