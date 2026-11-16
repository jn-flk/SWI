# C05 — DD Verification Evidence

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [Detailed design](../architecture-and-decisions/C05-Detailed-Design.md)

DD znamená detailní návrh, viz [C05-Detailed-Design.md](../architecture-and-decisions/C05-Detailed-Design.md),
kde jsou vysvětleny i pojmy jako claim, lease a fencing.

## Tests derived from the detailed design

| DD element / decision | What must hold? | Test level | Test case |
|---|---|---|---|
| Kontrakt `record_notification` — předpoklad | Volání mimo transakci rezervace selže `RuntimeError` a nic nezapíše. | jednotkový | `test_recording_outside_transaction_is_rejected_without_writing` |
| Kontrakt `record_notification` — chování při chybě | Nepodporovaný event selže `ValueError` a nic nezapíše. | jednotkový | `test_unsupported_event_is_rejected_without_writing` |
| Snapshot a větev audience | `approval_requested` míří na `approvers`, ostatní eventy na `owner`; payload obsahuje vlastníka, představení a stav. | jednotkový | `test_snapshot_and_audience_follow_event` |
| Transakční hranice outboxu | Změna stavu rezervace a outbox záznam se commitnou nebo vrátí společně — při pádu po vložení i při selhání vložení. | komponentový | `test_outbox_record_and_status_change_share_one_transaction`; dílčí `test_outbox_record_is_rolled_back_with_its_transaction` |
| Eventy rozhodnutí a expirace | Zamítnutí i expirace zapíší event pro vlastníka rezervace. | komponentový | `test_decision_and_expiry_enqueue_owner_notifications` |
| Spolupráce rezervace → outbox → dispatcher → sender | Commitnuté přechody doručí dispatcher přes `NotificationSender` se snapshotem; záznamy skončí `SENT` a znovu se neodešlou. | komponentový/integrační | `test_committed_transitions_are_delivered_through_sender` |
| Žádné inline doručení | Potvrzení rezervace pouze zapíše `PENDING` záznam, sender se nevolá. | komponentový | `test_confirmation_enqueues_notification_without_inline_delivery` |
| Kontrakt senderu a snapshot | Sender obdrží uložený snapshot mimo databázovou transakci a ID zůstane stabilní. | komponentový | `test_success_sends_snapshot_outside_transaction_and_marks_sent` |
| Algoritmus opakování | Neúspěšný pokus uloží chybu, zachová ID a naplánuje přesnou prodlevu. | jednotkový/komponentový | `test_failure_schedules_retry_at_exact_deadline_with_stable_id` |
| Větev backoffu | Prodleva se zdvojnásobuje a nepřekročí nastavené maximum. | jednotkový/komponentový | `test_backoff_doubles_and_is_capped` |
| Terminální selhání | Maximální počet pokusů nastaví `FAILED` a zpráva se znovu neodešle. | komponentový | `test_final_failure_stops_retries` |
| Obnova lease | Expirovaný lease se převezme novým tokenem při zachování ID zprávy. | komponentový | `test_expired_lease_is_recovered_with_same_message_id` |
| Přechod expirovaný lease po posledním pokusu → `FAILED` | Pád workeru při posledním pokusu nenechá věčně `PENDING` záznam a nevyvolá další odeslání. | komponentový | `test_crash_on_last_attempt_becomes_failed_without_another_send` |
| Invariant převzetí | Budoucí, terminální a platně převzaté záznamy se nedoručují. | komponentový | `test_future_terminal_and_unexpired_claims_are_not_delivered` |
| Fencing invariant | Pozdní worker nemůže přepsat novější claim. | komponentový | `test_late_worker_cannot_overwrite_new_claim_on_success_or_failure` |
| Kontrakt HTTP adaptéru | HTTP sender odešle JSON, timeout a idempotency klíč; chyby se propagují. | jednotkový | `test_http_posts_snapshot_with_idempotency_key_and_timeout`, `test_http_transport_and_server_errors_propagate_for_retry` |
| Provozní rozhraní | Jednorázový příkaz zpracuje dávku a vypíše počty; neplatné volby selžou. | komponentový | `test_one_shot_command_dispatches_and_prints_counts`, `test_invalid_command_options_are_rejected` |

## Selected test levels

**`test_outbox_record_and_status_change_share_one_transaction`**

- Selected level: komponentový (`reservation.services` + transakce Django + `NotificationRequest` na testovací DB).
- Why this level: atomicitu dvou zápisů nelze ověřit s mockovanou persistencí;
  test volá skutečné `confirm_reservation` a nahrazuje jen `record_notification`
  (pád po vložení, resp. selhání vložení).
- What design decision does this test verify? Outbox záznam vzniká ve stejné
  transakci jako změna stavu rezervace, ne až po commitu (`on_commit` z C03).
  Rezervace zůstane `DRAFT` a outbox prázdný v obou směrech selhání.

**`test_recording_outside_transaction_is_rejected_without_writing`**

- Selected level: jednotkový (rezervace je nahrazena stubem se čtyřmi poli,
  které kontrakt čte).
- Why this level: ověřuje se předpoklad samotné operace `record_notification`,
  nezávisle na rezervační logice. Použit je `TransactionTestCase`, protože
  `TestCase` obaluje test transakcí a předpoklad by nešel porušit.
- What design decision does this test verify? Precondition kontraktu
  „`connection.in_atomic_block` je pravda“ — volající nemůže zapsat notifikaci
  mimo transakci rezervace a vytvořit tak záznam bez commitnuté změny stavu.

**`test_committed_transitions_are_delivered_through_sender`**

- Selected level: komponentový/integrační (rezervační služby → outbox →
  dispatcher → test double `NotificationSender`).
- Why this level: jde o spolupráci, kterou žádný jednotkový test nepokryje;
  externí služba je nahrazena `Mock` senderem, aby test nezávisel na síti.
- What design decision does this test verify? Rozdělení na transakční zápis a
  asynchronní doručení: sender dostane snapshot uložený v okamžiku přechodu
  (stav `PENDING_APPROVAL`, ne pozdější `CONFIRMED`), audience podle eventu a
  záznam se po `SENT` znovu neodešle.

**Kontrakt HTTP senderu — jednotková úroveň.** `HttpSender` je izolován za
`urlopen`; test nahrazuje pouze síťovou hranici a ověřuje tvar požadavku,
timeout a idempotency hlavičku bez kontaktování externí služby.

**Fencing pozdního workeru — komponentová úroveň.** Podmíněná databázová změna
je návrhové rozhodnutí, které test ověřuje. Test simuluje náhradní claim mezi
odesláním a potvrzením a ověří, že zastaralý worker nezmění žádný stav.

## Test sensitivity to design violations

Nové testy byly ověřeny dočasnou úpravou kódu (po ověření vráceno):

| Porušení návrhu | Testy, které selhaly |
|---|---|
| Odstraněna kontrola `in_atomic_block` v `record_notification` | `test_recording_outside_transaction_is_rejected_without_writing` |
| Všechny eventy posílány audience `owner` | `test_snapshot_and_audience_follow_event`, `test_decision_and_expiry_enqueue_owner_notifications`, `test_committed_transitions_are_delivered_through_sender` |
| `_notify` vrácen na C03 styl `transaction.on_commit(...)` | `test_outbox_record_and_status_change_share_one_transaction`, `test_confirmation_enqueues_notification_without_inline_delivery`, `test_decision_and_expiry_enqueue_owner_notifications`, `test_committed_transitions_are_delivered_through_sender` |

## Executed unit and component tests

Příkaz spuštěný z adresáře `src\rezervace_divadlo`:

```text
python manage.py test notification reservation
```

Výsledek (původní sada od implementace C05):

```text
Ran 40 tests
OK
System check identified no issues (0 silenced).
```

Výsledek po doplnění testů odvozených z DD (6 nových testů: 3 v
`notification`, 3 v `reservation`; celkem 23 + 23):

```text
Found 46 test(s).
..............................................
----------------------------------------------------------------------
Ran 46 tests in 0.393s

OK
```

Ověřovací běh proběhl na Pythonu 3.11.9 s Django 5.2.18 (Django 6 vyžaduje
Python ≥ 3.12). Django 5.2 navíc hlásí varování `models.W042` pro modely
`reservation` (jiný výchozí `DEFAULT_AUTO_FIELD` než Django 6); na testy nemá
vliv a projekt cílí na Django 6.

Sada nesimuluje oddělené procesy operačního systému ani zamykání řádků
v produkčním stylu mezi více databázovými spojeními.

## Design ↔ implementation mismatch

| DD decision | Implemented? | Evidence | Action |
|---|---|---|---|
| Zapsat outbox uvnitř transakce rezervace | ANO | `notification/services.py:record_notification`; `reservation/services.py:_notify`; `test_outbox_record_and_status_change_share_one_transaction` | zachovat |
| Kontrakt `record_notification` (precondition, nepodporovaný event, audience) | ANO | kontroly v `record_notification`; `RecordNotificationContractTests` | zachovat |
| Notifikace pro všechny čtyři eventy (`approval_requested`, `approved`, `rejected`, `expired`) | ANO | `_notify` v `confirm_reservation`, `approve_reservation`, `_expire_one`; `test_decision_and_expiry_enqueue_owner_notifications`, `test_committed_transitions_are_delivered_through_sender` | zachovat |
| Stavový model DD obsahuje všechny přechody | ČÁSTEČNĚ | Kód i `test_crash_on_last_attempt_becomes_failed_without_another_send` mají přechod „expirovaný lease a `attempts >= max` → `FAILED`“, který ve stavovém modelu DD chybí | aktualizovat DD |
| Původní test transakční hranice ověřuje rezervační službu | NE | `test_outbox_record_is_rolled_back_with_its_transaction` vytváří záznam přímo přes ORM, rezervační službu nevolá | doplněn test `test_outbox_record_and_status_change_share_one_transaction` |
| Zachovat payload jako neměnný event snapshot | ANO | `NotificationRequest.payload`; konstrukce `NotificationMessage` | zachovat |
| Claim s lease a token fencingem | ANO | `notification/dispatcher.py:_claim`, podmíněný `owned.update` | zachovat |
| Externí I/O mimo databázovou transakci | ANO | kontrola v dispatcheru a test úspěšné cesty | zachovat |
| Opakování s omezeným exponenciálním backoffem | ANO | výpočet v dispatcheru a test backoffu | zachovat |
| Stabilní ID / idempotence přijímače | ANO | UUID primární klíč, `Idempotency-Key`, test adaptéru | zachovat |
| Oddělit skutečný a neznámý externí výsledek | ČÁSTEČNĚ | Lokální stavy jsou pouze `SENT`/`FAILED`; pád po odeslání může být nejednoznačný | zdokumentovat riziko |
| Prokázat paralelní claimy na produkční databázi | ČÁSTEČNĚ | Pouze sekvenční testy; SQLite se liší od databází se zamykáním řádků | doplnit později |

## Resolution

Původní popis C03 s `on_commit` a pouze logovacím adaptérem je historická
baseline. C05 jej nahrazuje transakčním outboxem a asynchronním dispatcherem.
Implementace a testy odpovídají aktualizovaným rozhodnutím C05; změna kódu
není nutná.

Ověřování odhalilo dvě mezery na straně verifikace, ne kódu: kontrakt
`record_notification` neměl přímé testy a test transakční hranice neprocházel
rezervační službou. Obojí je doplněno testy výše. Chybějící přechod ve stavovém
modelu je nesoulad v DD — kód je správně (zabraňuje věčnému `PENDING` záznamu),
proto se upraví DD, ne kód.

## Remaining design risks

- Doručení typu at-least-once může po pádu workeru vytvořit duplicity.
- Přijímač ignorující `Idempotency-Key` může duplicity skutečně zaznamenat.
- Lokální `FAILED` neprokazuje, že externí služba zprávu nepřijala.
- SQLite testy nepotvrzují chování při produkčním zamykání řádků.
- Payload nyní obsahuje ID a stav, nikoli verzované veřejné schéma.

## Commit / tag

Implementační baseline: `a23efc8` — `integrated notification app to the system`.
Tato dokumentace C05 a zaměřený diagram `.puml` představují důkazní změnu
pro implementovanou část notifikační služby.

Testy odvozené z DD a tato verifikace: tag `C05` (`5f52864`, merge PR #15).

## Create Reservation — DD verification

Ověření detailního návrhu `create_reservation` z části
[Create Reservation — detailed design](../architecture-and-decisions/C05-Detailed-Design.md#create-reservation--detailed-design).

### Tests derived from the Create design

| DD element / decision | What must hold? | Test level | Test case |
|---|---|---|---|
| Autorizace | Anonymní uživatel rezervaci nevytvoří. | komponentový | `test_anonymous_user_and_other_owner_cannot_change_reservation` |
| Validace představení | Neexistující představení vrátí `not_found` a nic nezapíše. | komponentový | `test_create_for_unknown_performance_is_rejected` |
| Validace výběru | Prázdný, duplicitní a neznámý výběr, cizí sál a neaktivní sedadlo jsou odmítnuty bez zápisu. | komponentový | `test_empty_duplicate_and_unknown_seats_are_rejected`, `test_wrong_hall_and_inactive_seat_are_rejected` |
| Cutoff 15 minut | Přesně 15 minut před začátkem `too_late`, při 15 minutách a 1 sekundě úspěch. | komponentový | `test_create_is_rejected_exactly_fifteen_minutes_before_start` |
| Předstih 24 h (BR-08) | Hromadná rezervace i celý sál pod 24 h `approval_too_late`, přesně 24 h úspěch. | komponentový | `test_bulk_create_requires_at_least_twenty_four_hours`, `test_entire_hall_create_requires_twenty_four_hours` |
| Pevný deadline | `hold_until = now + 15 min` a konfigurace má 15 minut. | komponentový | `test_new_draft_holds_seats_exactly_fifteen_minutes` |
| Lazy expirace a commit při `unavailable` | Prošlé cizí držení přejde do `EXPIRED` i při odmítnutí Create, outbox má `expired` pro vlastníka, nový `DRAFT` notifikaci nemá. | komponentový | `test_create_expires_stale_hold_before_collision_check` |
| Vše nebo nic | Jedno obsazené sedadlo odmítne celý výběr bez částečné rezervace. | komponentový | `test_one_occupied_seat_rejects_entire_selection` |
| Persistence | Rezervace se třemi sedadly se načte z DB jako `DRAFT` a blokuje dostupnost. | komponentový | `test_create_confirm_cancel_preserves_history_and_releases_seats` |
| Atomicita při souběhu | Ze dvou souběžných pokusů o stejné sedadlo uspěje právě jeden. | integrační (2 DB spojení) | `test_concurrent_creation_has_one_winner_for_one_seat` |
| Zobrazení chyby ve view | Chyba služby i obsazené sedadlo se zobrazí ve formuláři, rezervace nevznikne. | systémový (Django test client) | `test_service_error_is_shown_in_form`, `test_unavailable_seat_cannot_be_reserved` |
| Validace vstupů kontraktu | Nečíselné, nulové a záporné ID představení vrátí `invalid_id`, čas bez časové zóny `invalid_time`, hra s nulovou délkou `invalid_interval`; nic se nezapíše. | komponentový | `test_create_rejects_invalid_performance_id_and_naive_time`, `test_create_for_play_without_positive_duration_is_rejected` |
| Překlad `IntegrityError` na `conflict` | Konkurenční alokace vložená po kontrole obsazenosti poruší `unique_active_performance_seat`; Create vrátí `conflict` a celá transakce se vrátí. | komponentový | `test_concurrent_allocation_after_check_is_rolled_back_as_conflict` |
| Překlad zamčené DB na `busy` | `OperationalError` „database is locked“ uvnitř transakce vrátí `busy` bez zápisu. | komponentový | `test_locked_database_is_reported_as_busy_without_writing` |
| „Celý sál“ počítá i neaktivní sedadla | Sál se třemi sedadly, z nichž jedno je neaktivní: rezervace dvou aktivních sedadel se potvrdí přímo jako `CONFIRMED`. | komponentový | `test_entire_hall_counts_inactive_seats` |

### Selected test levels

**`test_create_expires_stale_hold_before_collision_check`**

- Selected level: komponentový (`create_reservation` + transakce + skutečná SQLite testovací DB + outbox).
- Why this level: ověřuje se, co zůstane commitnuto po odmítnutí. To nejde
  ověřit s mockovanou persistencí.
- What design decision does this test verify? `unavailable` je vrácený
  výsledek, ne výjimka v transakci. Expirace a její outbox záznam se proto
  uloží i při odmítnutí Create.

**`test_concurrent_creation_has_one_winner_for_one_seat`**

- Selected level: integrační, `TransactionTestCase` se dvěma vlákny a dvěma
  databázovými spojeními synchronizovanými přes `Barrier`.
- Why this level: atomicitu kontroly obsazenosti a zápisu nelze ověřit
  v jedné transakci `TestCase`.
- What design decision does this test verify? Kontrola obsazenosti a zápis
  alokací jsou jedna transakce s `transaction_mode = IMMEDIATE`, pojištěná
  constraintem `unique_active_performance_seat`.

### Test sensitivity to design violations

Ověřeno 16. 11. 2026 dočasnou úpravou kódu, po ověření vráceno
(`git diff` prázdný):

| Porušení návrhu | Testy, které selhaly |
|---|---|
| Odstraněna lazy expirace (`_expire_for_performance`) z Create | `test_create_expires_stale_hold_before_collision_check` |
| Create volá `_check_lead_time` bez příznaku schválení | `test_bulk_create_requires_at_least_twenty_four_hours`, `test_entire_hall_create_requires_twenty_four_hours` |
| `unavailable` vyhozen jako výjimka uvnitř transakce (expirace se vrátí) | `test_create_expires_stale_hold_before_collision_check` |
| `RESERVATION_HOLD_MINUTES = 5` (hodnota před C08) | `test_new_draft_holds_seats_exactly_fifteen_minutes` |
| `_atomic_operation` nepřekládá `IntegrityError` | `test_concurrent_allocation_after_check_is_rolled_back_as_conflict` |
| `_atomic_operation` nepřekládá zamčenou DB na `busy` | `test_locked_database_is_reported_as_busy_without_writing`, `test_concurrent_creation_has_one_winner_for_one_seat`, `test_concurrent_confirm_has_one_winner_for_one_reservation` |
| „Celý sál“ počítá jen aktivní sedadla | `test_entire_hall_counts_inactive_seats` |
| `_now` přijme čas bez časové zóny | `test_create_rejects_invalid_performance_id_and_naive_time` |

Selhání obou souběžných testů po vypnutí překladu na `busy` ukazuje, že
souběžné běhy nad SQLite zámek skutečně vyvolávají.

### Design ↔ implementation mismatch

| DD decision | Implemented? | Evidence | Action |
|---|---|---|---|
| Pořadí kontrol a chybové kódy podle kontraktu | ANO | `reservation/services.py:create_reservation`, `_seats`, `_check_lead_time`; testy výše | zachovat |
| Lazy expirace a commit expirací při `unavailable` | ANO | `_atomic_operation`, `_expire_for_performance`; `test_create_expires_stale_hold_before_collision_check` | zachovat |
| Pevný `hold_until` 15 minut | ANO | `settings.RESERVATION_HOLD_MINUTES`; `test_new_draft_holds_seats_exactly_fifteen_minutes` | zachovat |
| Kódy `invalid_id`, `invalid_time`, `invalid_interval` | ANO | `_performance`, `_now`; `test_create_rejects_invalid_performance_id_and_naive_time`, `test_create_for_play_without_positive_duration_is_rejected` | zachovat |
| `conflict` po porušení constraintu, rollback celé transakce | ANO | `_atomic_operation`; `test_concurrent_allocation_after_check_is_rolled_back_as_conflict` | zachovat |
| `busy` při zamčené DB | ANO | `_atomic_operation`; `test_locked_database_is_reported_as_busy_without_writing` (simulovaná chyba), souběžné testy (skutečný zámek SQLite) | zachovat; skutečné vypršení `timeout = 20 s` se netestuje |
| „Celý sál“ počítá i neaktivní sedadla | ANO | `_requires_approval` (`hall.seats.count()`); `test_entire_hall_counts_inactive_seats` | zachovat |

### Executed tests

Spuštěno 16. 11. 2026 na Linuxu, Python 3.14.10, Django 6.1.2, nad
pracovním stromem větve `c10-after-presentation-doc-revision` (základ
`be0b3be`, změny zatím necommitnuté):

```text
python src/rezervace_divadlo/manage.py test notification reservation
Found 77 test(s).
System check identified no issues (0 silenced).
Ran 77 tests in 2.162s

OK
```
