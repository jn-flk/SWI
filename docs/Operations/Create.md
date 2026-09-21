## OP-01 — Create Reservation

Goal / user value:
User creates a reservation request that can later be confirmed.

Trigger:
Authorized User requests a Reservation for Resource R and interval I.

Observable requirement:
REQ-01:
The system shall create a DRAFT Reservation for an existing Resource
when the requested interval is valid.

Preconditions:
- User is authorized to create Reservations.
- Resource exists.
- start < end.

Success postcondition:
- one new Reservation exists;
- Reservation.state = DRAFT;
- no Resource allocation is committed yet.

State change:
[none] → DRAFT

Referenced rules:
BR-01 Interval semantics.

Main success scenario:
1. User submits Resource and interval.
2. System validates authorization, Resource and interval.
3. System creates Reservation in DRAFT.
4. System returns the Reservation identifier and current state.

Alternative / failure outcomes:
- unauthorized User → reject; no Reservation created;
- unknown Resource → reject; no Reservation created;
- invalid interval → reject; no Reservation created.

Verification examples:
valid Resource + [10:00,11:00) → one DRAFT created
start == end → rejected
unknown Resource → rejected

Rationale:
Creation records user intent without committing Resource allocation.