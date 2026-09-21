## OP-03 — Confirm Reservation

Goal / user value:
A valid DRAFT Reservation becomes the accepted allocation of Resource.

Trigger:
Authorized User requests confirmation of Reservation X.

Observable requirements:
REQ-03:
The system shall confirm a DRAFT Reservation only when its Resource
is active and its interval does not conflict with an existing
CONFIRMED Reservation of the same exclusive Resource.

REQ-04:
For concurrent confirmation attempts that conflict under BR-02,
at most one Reservation shall reach CONFIRMED.

Preconditions:
- Reservation exists.
- Reservation.state = DRAFT.

Success postcondition:
- Reservation.state = CONFIRMED;
- the Reservation blocks its Resource for its interval;
- BR-02 remains true.

Failure outcomes:
- inactive Resource → reject; Reservation remains DRAFT;
- overlap exists → reject; Reservation remains DRAFT;
- invalid source state → reject; state unchanged.

Verification examples:
DRAFT + active Resource + no overlap → CONFIRMED
DRAFT + overlap → rejected, remains DRAFT
two concurrent conflicting confirmations → at most one CONFIRMED