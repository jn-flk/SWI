"""Record immutable delivery requests inside the reservation transaction."""

from django.db import connection

from .models import NotificationRequest


EVENTS = {"approval_requested", "approved", "rejected", "expired"}


def record_notification(reservation, event):
    if not connection.in_atomic_block:
        raise RuntimeError("Notification recording requires the reservation transaction")
    if event not in EVENTS:
        raise ValueError(f"Unsupported notification event: {event}")
    return NotificationRequest.objects.create(
        reservation_id=reservation.pk,
        event=event,
        payload={
            "owner_id": reservation.owner_id,
            "performance_id": reservation.performance_id,
            "status": reservation.status,
            "audience": "approvers" if event == "approval_requested" else "owner",
        },
    )
