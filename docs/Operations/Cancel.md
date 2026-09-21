## OP-04 — Cancel Reservation

Goal / user value:
An eligible Reservation can be withdrawn and stops blocking Resource.

Observable requirement — EXAMPLE POLICY:
REQ-05:
The system shall allow a DRAFT or CONFIRMED Reservation to be
cancelled before its start time.

Preconditions:
- Reservation exists.
- Reservation.state ∈ {DRAFT, CONFIRMED}.
- currentTime < Reservation.start.

Success postcondition:
- Reservation.state = CANCELLED;
- Reservation no longer blocks Resource availability.

Failure outcomes:
- already CANCELLED → [team decides: idempotent success OR explicit rejection];
- start time reached/passed → reject;
- Cancel races with Confirm → team defines accepted observable outcome.

Verification examples:
DRAFT before start → CANCELLED
CONFIRMED before start → CANCELLED and Resource becomes available
CONFIRMED at/after start → rejected according to accepted policy