## OP-02 — Check Availability

Goal / user value:
User can determine whether an exclusive Resource is currently
available for a requested interval.

Observable requirement:
REQ-02:
For a valid interval, the system shall report a Resource as unavailable
if the interval overlaps any CONFIRMED Reservation of that Resource;
otherwise it shall report it as available.

Preconditions:
- Resource exists.
- requested interval is valid.

Success postcondition:
- availability result is returned;
- no Reservation state is changed.

Referenced rules:
BR-01 Interval semantics.
BR-02 Exclusive Resource invariant.

Verification examples:
Existing CONFIRMED: [10:00,11:00)

query [09:00,10:00) → AVAILABLE
query [10:30,11:30) → UNAVAILABLE
query [11:00,12:00) → AVAILABLE

Accepted semantics:
Intervals are half-open: [start,end).