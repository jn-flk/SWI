# C03 — Současná realizace Confirm Reservation

## Sledovaný scénář

| Položka | Hodnota |
|---|---|
| Operace | OP-03 — Confirm Reservation |
| Požadavky | REQ-03, REQ-04 — [intent-and-change/C02-Operations-and-Requirements.md](../intent-and-change/C02-Operations-and-Requirements.md) |
| Pravidla | BR-02, BR-04, BR-06, BR-07, BR-08 — [intent-and-change/C02-Domain-Rules-and-Baseline.md](../intent-and-change/C02-Domain-Rules-and-Baseline.md) |
| Baseline | v0.2 — [evidence-and-evolution/C02-Specification-to-Running-App.md](../evidence-and-evolution/C02-Specification-to-Running-App.md) |

Doklady níže uvádějí soubor a funkci/model. [Testy](../../src/rezervace_divadlo/reservation/tests.py) byly přečteny, nově se nespouštěly.

## Hlavní průchod scénáře → kód

| Krok scénáře z C02 | Realizace v kódu | Doklad |
|---|---|---|
| Přijmout požadavek a načíst rezervaci. | Přímé volání služby; načtení rezervace a představení v transakci. | [services.py][services]: `confirm_reservation`, `_reservation`, `_atomic_operation` |
| Ověřit oprávnění a platný `DRAFT`. | Kontrola vlastníka/oprávnění, deadline a zdrojového stavu. | [services.py][services]: `_authorize_owner`, `_expire_one`, `confirm_reservation` |
| Ověřit sedadla a předstih. | Aktivní sedadla; více než 10 nebo celý sál vyžaduje schválení. Cutoff 15 min, pro schvalování předstih 24 h. | [services.py][services]: `confirm_reservation`, `_requires_approval`, `_check_lead_time` |
| Změnit a uložit stav. | `CONFIRMED` nebo `PENDING_APPROVAL`; zrušit držení, případně nastavit deadline schválení. Blokování zůstává, kolize se znovu nekontroluje. | [services.py][services]: `_set_status`, `confirm_reservation` |
| Vrátit výsledek. | Vrátit `Reservation`; u schvalovací větve ve stejné transakci zapsat `NotificationRequest`. | [services.py][services]: `confirm_reservation`, `_notify`; [notification services.py][notification-services]: `record_notification` |

## Důležitá chybová větev

| Co říká v0.2 | Kde se podmínka zjistí | Kde se rozhodne výsledek | Co dostane volající |
|---|---|---|---|
| Vypršené držení → odmítnout a nastavit `EXPIRED`. | [services.py][services]: `_expire_one`, `now >= hold_until` | `_set_status` uloží expiraci a uvolní sedadla; `_atomic_operation` vyhodí chybu až po commitu. | `ReservationError("expired", ...)`; expirace zůstane v DB. Test: `test_confirm_at_hold_deadline_expires_reservation`. |

| Specifikace | Implementace | Doklad |
|---|---|---|
| Hranice schvalování je sjednocena v aktuální specifikaci a implementaci. | Schválení nad 10 sedadel nebo pro celý sál. | [services.py][services]: `_requires_approval`; [settings.py][settings]: limit 10; test `test_ten_seats_confirm_directly_but_eleven_require_approval` |
| BR-08 používá politiku minimálního předstihu. | Alespoň 24 h před začátkem při Create i Confirm. | [services.py][services]: `_check_lead_time`; [settings.py][settings]: `RESERVATION_APPROVAL_HOURS` |

## Hlavní části implementace

| Část implementace | Typ / obsah | Role v tomto scénáři | Doklad |
|---|---|---|---|
| Rezervační služby | Modul `services.py` | Kontroly, rozhodnutí a transakce. | [services.py][services]: `confirm_reservation` a pomocné funkce |
| Doménové modely | Modul `models.py`: Reservation, ReservationSeat, Seat, Performance, Hall, Play | Stav, vztahy a DB omezení. | [models.py][models] |
| Konfigurace | Modul `settings.py` | Limity politiky a připojení DB. | [settings.py][settings] |
| Notifikace | Aplikace `notification` | Transakční outbox a asynchronní dispatcher; výchozí sender loguje lokálně. | [notification services.py][notification-services], [dispatcher.py][dispatcher] |

## Stav, změna stavu a pravidlo

| Otázka | Odpověď | Doklad |
|---|---|---|
| Kde je stav trvale uložen? | SQLite: `reservation_reservation` (stav, deadline), `reservation_reservationseat` (blokování). | [models.py][models]: `Reservation`, `ReservationSeat`; [settings.py][settings]: `DATABASES` |
| Kdo rozhoduje a provádí přechod? | `confirm_reservation` rozhoduje, `_set_status` ukládá; `_expire_one` rozhoduje o expiraci. | [services.py][services] |

Pravidlo BR-04: potvrdit pouze platný `DRAFT`.

| Otázka | Odpověď | Doklad |
|---|---|---|
| Kde se zjistí podmínka? | Kontrola deadline, stavu a aktivních sedadel. | [services.py][services]: `_expire_one`, `confirm_reservation` |
| Kde se rozhodne? | `confirm_reservation` zvolí potvrzení, schvalování nebo chybu; `_expire_one` zvolí expiraci. | [services.py][services] |
| Kde se změní stav? | `_set_status` uloží stav; při expiraci vypne alokace. | [services.py][services]: `_set_status` |

BR-02 chrání už Create a DB constraint `unique_active_performance_seat`; Confirm blokování zachovává.

## Relevantní závislosti

| Závislost | Kde se napojuje | Která část zná technické API | Doklad |
|---|---|---|---|
| SQLite přes Django ORM | Načtení, uložení a transakce. | `services.py` používá ORM a `transaction.atomic`; modely definují constrainty. | [services.py][services], [models.py][models], [settings.py][settings] |
| Notification Service — outbox a dispatcher | `_notify` zapíše outbox ve stejné transakci při žádosti o schválení nebo expiraci; samostatný dispatcher doručuje později. | `notification.services` validuje a snapshotuje událost; `notification.adapters` obsahuje logging/HTTP sendery. | [notification services.py][notification-services]; [dispatcher.py][dispatcher] |
| Django auth | Kontrola předaného uživatele a oprávnění. | `services.py`: `is_authenticated`, `is_active`, `has_perm`. | [services.py][services]: `_authorize_owner` |

## AS-IS strukturální diagram

Diagram je ve složce [diagrams/c03/](../diagrams/c03/):
[AS-IS — Confirm Reservation (PlantUML)](../diagrams/c03/as-is-confirm-reservation.puml).

Obsah modulů viz tabulka hlavních částí. Auth a logging jsou frameworkové závislosti; notifikace se při přímém potvrzení nevolá.

## Otázka pro další architektonický návrh

| Item | Content |
|---|---|
| Otázka | Zvládne SQLite požadovaných 20 souběžných rezervací při zachování REQ-04? |
| Doklad | [settings.py][settings]: `IMMEDIATE`, timeout 20 s; [services.py][services]: chyba `busy` při zamčené DB. Test `test_confirm_cannot_be_repeated` ověřuje jen sekvenční opakování. |
| Proč je důležitá | SQLite serializuje zápisy; souběžný experiment musí ověřit správnost přechodů, čekání a četnost `busy`. |

[services]: ../../src/rezervace_divadlo/reservation/services.py
[models]: ../../src/rezervace_divadlo/reservation/models.py
[settings]: ../../src/rezervace_divadlo/rezervace_divadlo/settings.py
[notifications]: ../../src/rezervace_divadlo/reservation/notifications.py
[notification-services]: ../../src/rezervace_divadlo/notification/services.py
[dispatcher]: ../../src/rezervace_divadlo/notification/dispatcher.py
