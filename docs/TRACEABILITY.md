# Traceability

← [Navigator](NAVIGATOR.md)

Každý požadavek a pravidlo s místem v kódu a testy, které ho ověřují.
Požadavky jsou v [Operations and requirements](intent-and-change/C02-Operations-and-Requirements.md),
pravidla v [Domain rules](intent-and-change/C02-Domain-Rules.md).

Kód: [services.py](../src/rezervace_divadlo/backend/reservation/services.py),
[models.py](../src/rezervace_divadlo/backend/reservation/models.py).
Testy: [tests.py](../src/rezervace_divadlo/backend/reservation/tests.py),
[tests_concurrency.py](../src/rezervace_divadlo/backend/reservation/tests_concurrency.py).

## Requirements

| Požadavek | Operace | Pravidla | Kód | Testy |
|---|---|---|---|---|
| **REQ-01** — Create vytvoří jednu `DRAFT` pro všechna volná sedadla | OP-01 (Create Reservation) | BR-02, BR-05, BR-07, BR-08 | `create_reservation`, `_check_lead_time` | `test_create_confirm_cancel_preserves_history_and_releases_seats`, `test_empty_duplicate_and_unknown_seats_are_rejected`, `test_wrong_hall_and_inactive_seat_are_rejected`, `test_one_occupied_seat_rejects_entire_selection`, `test_create_is_rejected_exactly_fifteen_minutes_before_start`, `test_bulk_create_requires_at_least_twenty_four_hours`, `test_concurrent_creation_has_one_winner_for_one_seat` |
| **REQ-02** — dostupnost podle aktivních rezervací | OP-02 (Check Availability) | BR-01, BR-05 | `check_availability` | `test_availability_treats_touching_intervals_as_available`, `test_one_occupied_seat_rejects_entire_selection` |
| **REQ-03** — Confirm vede na `CONFIRMED` nebo `PENDING_APPROVAL` | OP-03 (Confirm Reservation) | BR-04, BR-08 | `confirm_reservation`, `_requires_approval`, `_check_lead_time` | `test_ten_seats_confirm_directly_but_eleven_require_approval`, `test_entire_small_hall_requires_approval`, `test_bulk_confirm_also_requires_twenty_four_hours`, `test_confirm_at_hold_deadline_expires_reservation`, `test_confirm_with_seat_deactivated_after_create_is_rejected` |
| **REQ-04** — souběžné potvrzení má jednoho vítěze | OP-03 (Confirm Reservation) | BR-06 | `confirm_reservation` v transakci `_atomic_operation` | `test_concurrent_confirm_has_one_winner_for_one_reservation`, `test_confirm_cannot_be_repeated` (sekvenčně) |
| **REQ-05** — Cancel před začátkem, opakované zrušení je idempotentní | OP-04 (Cancel Reservation) | BR-03 | `cancel_reservation` | `test_create_confirm_cancel_preserves_history_and_releases_seats`, `test_first_cancel_at_start_is_rejected`, `test_repeated_cancel_succeeds_even_after_start` |
| **REQ-06** — schvalovatel změní `PENDING_APPROVAL` na `CONFIRMED` nebo `REJECTED` | OP-05 (Approve Reservation) | BR-06 | `approve_reservation` | `test_only_approver_can_decide_and_rejection_releases_seats`, `test_approval_just_before_deadline_succeeds` |
| **REQ-07** — schválení jen před lhůtou | OP-05 (Approve Reservation) | — | `approve_reservation`, `_expire_one` | `test_approval_just_before_deadline_succeeds`, `test_approval_at_deadline_expires_reservation` |

## Rules without their own requirement

| Pravidlo | Kód | Testy |
|---|---|---|
| **BR-02** (Exclusive Resource invariant) | DB constraint `unique_active_performance_seat` v `models.py`; `create_reservation` | `test_one_occupied_seat_rejects_entire_selection`, `test_concurrent_creation_has_one_winner_for_one_seat` |
| **BR-07** (Fixed hold and return-to-selection policy), OP-01a (Validate Reservation Hold) | `touch_reservation`, `release_draft_reservations`, `_expire_one`, `expire_reservations` | `test_activity_does_not_extend_hold_and_expiration_is_idempotent`, `test_submitting_contact_details_keeps_fixed_hold`, `test_returning_to_seat_selection_releases_own_active_hold`, `test_returning_to_seat_selection_keeps_other_users_hold`, `test_confirm_at_hold_deadline_expires_reservation` |
| Oprávnění (předpoklad OP-01 až OP-05) | `_authorize`, `_authorize_owner`, oprávnění `approve_reservation` | `test_anonymous_user_and_other_owner_cannot_change_reservation`, `test_only_approver_can_decide_and_rejection_releases_seats` |
| Notifikace přes outbox (ADR-01) | `_notify` → `notification.services.record_notification` | `test_confirmation_enqueues_notification_without_inline_delivery`, `test_outbox_record_and_status_change_share_one_transaction`, `test_decision_and_expiry_enqueue_owner_notifications`, `test_committed_transitions_are_delivered_through_sender`; testy dispatcheru v [C05 evidence](evidence-and-evolution/C05-DD-Verification.md) |

## Gaps

Chování ze specifikace, které žádný test neověřuje:

- zrušení rezervace ve stavu `PENDING_APPROVAL` (REQ-05);
- odmítnutí zrušení `REJECTED` nebo `EXPIRED` rezervace (BR-03);
- souběh schválení, zamítnutí, zrušení a expirace (BR-06);
- přesná hranice 15 minut od vytvoření je ověřena přes parametrizovaný test
  nastavení hold duration; UI zobrazuje pouze zbývající celé minuty.
