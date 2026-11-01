# Evidence C01: Engineering Spike
## Question / unknown:
Can we create, persist and retrieve a Reservation with its
related Seat and Performance using Django ORM and SQLite?
## What we did:
We created the Django reservation app with models for Seat,
Play, Hall, Performance and Reservation.

We created the SQLite database schema using Django migrations and
implemented an automated test that:

1. creates a Play, Hall and Seat,
2. creates a Performance for the Play in the Hall,
3. creates a Reservation for the Performance and Seat,
4. retrieves the Reservation from the database,
5. verifies the expected Play, Hall and Seat relationships,
6. attempts to create a duplicate Reservation for the same
	Performance and Seat,
7. verifies that the database constraint prevents the duplicate.

## Observed result:
The Reservation was successfully persisted and retrieved from
SQLite with the expected relationships.

The database also prevented a second Reservation for the same
Performance and Seat because of the unique constraint.

## Decision / what changes because of the result:
We will use Django ORM and the current relational model as the
persistence approach for the CP1 implementation.

# Evidence C02: specifikace → běžící aplikace

## Přijatá baseline:

Výchozí specifikací je baseline v0.2 se schvalováním, popsaná v
[operations.md](operations.md), [intent_and_change.md](intent_and_change.md)
a diagramech v `c02-diagrams/`. Pro implementaci byly uživatelem přijaty
následující podmínky:

- Jedna rezervace obsahuje jedno nebo více sedadel pro konkrétní představení.
- Create vytvoří `DRAFT` a atomicky zablokuje všechna vybraná sedadla.
- Nejvýše 10 sedadel se potvrdí přímo; více než 10 sedadel nebo celý sál
  vyžaduje `PENDING_APPROVAL` a rozhodnutí oprávněného schvalovatele.
- Hromadná rezervace nebo celý sál musí mít alespoň 24 hodin do začátku
  při vytvoření i při odeslání ke schválení. Schvalovací lhůta je 24 hodin.
- Vytvoření a potvrzení rezervace jsou odmítnuty při 15 minutách nebo méně
  do začátku. Platné držení trvá pět minut od poslední zaznamenané aktivity.
- Cancel je povolen před začátkem. Opakované zrušení již `CANCELLED`
  rezervace oprávněným aktérem je idempotentní.
- Confirm ani Approve znovu nekontrolují kolizi; zachovávají blokování
  vzniklé při Create. `CANCELLED`, `REJECTED` a `EXPIRED` sedadla uvolňují
  a záznam rezervace i její sedadla zůstávají v historii.

Tento seznam zachycuje dohodnuté a implementované chování. Úplné schválení
baseline týmem není v repozitáři explicitně doloženo.

## Předvedené základní operace:

V automatických testech byly přímo přes
[reservation/services.py](../src/rezervace_divadlo/reservation/services.py)
provedeny všechny čtyři základní operace:

- OP-01 Create Reservation — vytvoření a uložení rezervace více sedadel.
- OP-02 Check Availability — dostupnost podle blokování a překryvu intervalů.
- OP-03 Confirm Reservation — přímé potvrzení nebo odeslání ke schválení.
- OP-04 Cancel Reservation — zrušení, uvolnění sedadel a zachování historie.

Dále byly provedeny OP-05 Approve Reservation, zamítnutí, obnova aktivity
přes `touch_reservation` a expirace přes `expire_reservations`. Rozhraním
pro reprodukci jsou testy a Django shell; API není součástí aplikace.

## Skutečně provedené příklady ověření:

Poslední skutečně provedený běh aktuální sady
[reservation/tests.py](../src/rezervace_divadlo/reservation/tests.py)
skončil výsledkem **20 testů, všechny prošly**. Django systémová kontrola
byla bez chyb. Testy používají izolovanou SQLite databázi a řízené hodnoty
času, takže není potřeba čekat na skutečné timeouty.

Příkazy z kořene repozitáře:

```powershell
.\.venv\Scripts\python.exe .\src\rezervace_divadlo\manage.py test reservation --verbosity 2
.\.venv\Scripts\python.exe .\src\rezervace_divadlo\manage.py check
```

| Oblast | Skutečně ověřené příklady |
|---|---|
| Create a persistence | Tři sedadla vytvoří jednu uloženou `DRAFT`; prázdný, duplicitní či neznámý výběr, jiný sál a neaktivní sedadlo jsou odmítnuty. Jedno obsazené sedadlo odmítne celou skupinu bez částečné rezervace. |
| Availability | Blokované sedadlo je nedostupné a po zrušení či zamítnutí dostupné. Dotyk hranic intervalů je dostupný, překryv nedostupný; nulový interval je odmítnut. |
| Confirm | 10 sedadel přejde do `CONFIRMED`, 11 do `PENDING_APPROVAL`. Celý sál se dvěma sedadly vyžaduje schválení. Opakované potvrzení je odmítnuto; pokus přesně při konci držení uloží `EXPIRED`. |
| Cancel | Zrušení zachová historii, uvolní sedadla a umožní novou rezervaci. První zrušení přesně při začátku je odmítnuto; opakované zrušení již `CANCELLED` rezervace uspěje i při začátku. |
| Approve / Reject | Oprávněný schvalovatel uspěje jednu sekundu před deadline. Při deadline žádost přejde do `EXPIRED`. Zamítnutí uvolní sedadla a další rozhodnutí je odmítnuto. |
| Časové hranice | Create při 15 minutách do začátku je odmítnuto, při 15 minutách a jedné sekundě uspěje. Hromadné Create při 24 hodinách uspěje, o sekundu později je odmítnuto. Podmínka 24 hodin se kontroluje také při Confirm. |
| Oprávnění | Anonymní uživatel nevytvoří rezervaci, jiný vlastník ji nepotvrdí ani nezruší a běžný návštěvník nemůže schvalovat. |
| Aktivita a expirace | Aktivita po čtyřech minutách obnoví držení do deváté minuty. Sekundu před deadline rezervace nevyprší, při deadline vyprší a opakovaná expirace nic nezmění. Vypršené držení nelze obnovit. |

## Nalezený nesoulad a způsob vyřešení:

- Původní model dovoloval pouze jedno sedadlo a neobsahoval stav ani lhůty.
  Doplněny byly stavy, vlastník, `hold_until`, `approval_deadline` a vazba
  `ReservationSeat`. Migrace `0002` převádí původní rezervace na potvrzené
  alokace; aktuální sada samostatně netestuje převod existujících dat.
- Původní bezpodmínečný constraint znemožňoval opětovnou rezervaci sedadla
  při zachování starého záznamu. Byl nahrazen unikátním omezením pouze
  aktivních alokací; uvolnění a opětovná rezervace jsou ověřeny testem.
- Opakované Cancel a kontrola kolize při Confirm/Approve se lišily mezi
  textem a diagramy. Text i implementace nyní používají idempotentní
  Cancel a blokování od Create bez opakované kontroly kolize.
- Hranice schvalování byla sjednocena na nejvýše 10 sedadel pro přímé
  potvrzení a více než 10 sedadel nebo celý sál pro `PENDING_APPROVAL`.
  Implementace, testy, `intent_and_change.md` i OP-03 v `operations.md`
  nyní používají stejnou hranici.
- BR-08 je v souladu s implementací konkretizován jako minimální předstih
  24 hodin při vytvoření i potvrzení hromadné rezervace. Schvalovací lhůta
  je rovněž 24 hodin.
- Na žádost uživatele bylo odstraněno API a testování sjednoceno do
  `tests.py`. Aktuální evidence proto neuvádí API ani původní rozsáhlejší
  sadu jako současnou součást aplikace.

## Shrnutí dopadu změny:

Schvalovací proces rozdělil Confirm na přímé potvrzení běžné rezervace
nebo přechod do `PENDING_APPROVAL`. Přibyl aktér schvalovatele a samostatná
operace Approve/Reject. Čekající žádost dále blokuje všechna sedadla;
zamítnutí, zrušení nebo vypršení je uvolní. Změna vyžaduje uložený stav,
časové lhůty, oprávnění a atomické přechody.

Intervalová sémantika `[start,end)`, exkluzivita sedadla pro představení,
zachování historie při zrušení a Django ORM se SQLite zůstaly zachovány.
Více sedadel a obnova držení rozšiřují původní model. Odstranění API změnilo
způsob volání aplikace; business operace se nadále provádějí přes služby.

## Zbývající předpoklad / neznámá:

- Doplnit diagram aktivity OP-02 a časové podmínky v diagramech;
  explicitní schválení baseline v0.1/v0.2 týmem není doloženo.
- Aktuální jednoduché testy neověřují paralelní zápisy, výkon při
  20 souběžných požadavcích ani zachování dat při migraci existující databáze.
- Notifikace používají pouze lokální logovací adaptér. Externí doručování,
  jeho selhání a opakování nejsou ověřené.
- Pravidelné ukládání stavu `EXPIRED` vyžaduje spuštěný příkaz
  `python manage.py expire_reservations --watch`. Jeho nepřetržitý provoz
  a zotavení po výpadku nejsou součástí současné jednoduché testovací sady.

## C03 — Architecture Evidence

Baseline: v0.2
Part A: OP-03 Confirm Reservation, včetně přímého potvrzení a schvalovací větve.

Drivers:

- zachovat atomické blokování sedadel od vytvoření;
- mít jednoznačné vlastnictví životního cyklu rezervace;
- izolovat hranici Notification Service;
- zachovat možnost schválení hromadné rezervace a expirace.

Decision question: Jak rozdělit odpovědnosti pro potvrzení rezervace tak,
aby stav, aktivní alokace, schválení a notifikace měly jasné vlastníky bez
zavedení více deployables?

Alternatives:

- ponechat veškerou logiku v jednom controlleru bez explicitních hranic;
- rozdělit doménu do více procesů/aplikací;
- použít jednu Django aplikaci s logickými prvky a službami uvnitř procesu.

Zvolena byla třetí alternativa. Odpovídá ADR o jedné Django aplikaci,
Django ORM/SQLite a business zápisech přes `services.py`.

Scenario walkthrough: Visitor zavolá Confirm Reservation. Reservation
Management načte a zamkne rezervaci, ověří vlastníka, platnost držení a
aktivní sedadla. Approval Workflow vyhodnotí limit 10 sedadel nebo celý sál.
Při přímé větvi Reservation Management uloží `CONFIRMED`; při schvalovací
větvi uloží `PENDING_APPROVAL` a deadline. Notifikace vzniká až po commitu.
Při expiraci se stav nastaví na `EXPIRED` a aktivní alokace se uvolní.

ADR: Přijato — logické prvky se mapují do jednoho Django procesu; aktivní
alokace chrání podmíněný unikátní databázový constraint; Notification Service
je za adapter boundary a je volán přes post-commit notifikaci.

Views:

- domain class — [domain-model.puml](c03-diagrams/domain-model.puml)
- context — [context.puml](c03-diagrams/context.puml)
- static architecture — [static-architecture.puml](c03-diagrams/static-architecture.puml)
- state ownership — [state-ownership.puml](c03-diagrams/state-ownership.puml)
- runtime/deployment — [runtime-deployment.puml](c03-diagrams/runtime-deployment.puml)
- design sequence — [design-sequence-confirm.puml](c03-diagrams/design-sequence-confirm.puml)
- focused design class — [focused-design-class.puml](c03-diagrams/focused-design-class.puml)

Cross-view issues found/resolved: Ownership přechodů byl doplněn tak, že
Reservation Management rozhoduje o přímém potvrzení a odeslání ke schválení,
Approval Workflow rozhoduje o approve/reject a Expiration Scheduler pouze
spouští expiraci. Sekvence používá jen prvky ze statické architektury.
Runtime mapuje všechny logické prvky do jednoho Django procesu.

| Kontrola | Výsledek |
|---|---|
| C02 ↔ G2: architektura realizuje lifecycle, dostupnost, schválení, expiraci a notifikace | PASS |
| C2 ↔ G2: každá významná odpovědnost má právě jednoho hlavního ownera | PASS |
| G2 ↔ H1: sekvence používá pouze povolené prvky a závislosti | PASS |
| H1 ↔ H2: významné operace mají vlastníka v třídním návrhu | PASS |
| statechart ↔ G3/H1: transition rozhoduje správný owner | PASS |
| G2 ↔ G4: všechny logické prvky jsou namapované do Django procesu | PASS |
| ADR ↔ G2/G4: jedna Django aplikace, ORM/SQLite a constraint jsou viditelné | PASS |

AS-IS → TO-BE delta:

| Oblast | AS-IS | TO-BE | Akce |
|---|---|---|---|
| změna `Reservation.state` | controller + service | pouze Reservation Management | KEEP |
| `CHANGE` notifikace | lokální adapter v `notifications.py` | Notification Integration za boundary | KEEP |
| persistence dependency | Django ORM + SQLite | stejná persistence | KEEP |
| dependency rule | implicitní import boundary | ověřená izolace logging/adapteru | VERIFY |
| runtime | jedna Django aplikace | jeden Reservation Application process | KEEP |

Implementation changes: Žádná řádka `CHANGE` nebyla nalezena. Přidána byla
jen opakovatelná architektonická kontrola v
[reservation/tests.py](../src/rezervace_divadlo/reservation/tests.py), která
ověřuje, že import `logging` zůstává izolován v `notifications.py`.

Behaviour verification:

| Ověření | Výsledek | Doklad |
|---|---|---|
| success path — přímé potvrzení | PASS | `test_ten_seats_confirm_directly_but_eleven_require_approval` |
| alternative/failure — expirace držení | PASS | `test_confirm_at_hold_deadline_expires_reservation` |
| alternative/failure — approve/reject | PASS | `test_only_approver_can_decide_and_rejection_releases_seats` |
| relevant boundary/concurrency rule | PARTIAL | 20 Django testů + `manage.py check`; atomická ochrana a constraint jsou ověřeny sekvenční sadou, skutečný paralelní test zatím chybí |

Architecture conformance rule + result:

```text
Architektonické pravidlo:
  Vedlejší efekt Notification Service (logging/adaptér) smí být importován
  pouze v Notification Integration, tedy v notifications.py.
Kontrola:
  ReservationTests.test_notification_side_effect_is_isolated_to_integration_adapter
  staticky projde AST všech modulů reservation/*.py.
Výsledek:
  PASS — jediný modul importující logging je notifications.py.
```

Remaining uncertainty / risk: Sada neprokazuje výkon při 20 paralelních
požadavcích ani skutečné doručení a retry externích notifikací. Samostatně
není otestován převod existujících dat migrací `0002`.

Commit/tag: `2c9915b` — `docs: G-M diagrams, test implementation, evidence`;
pozdější dokumentační opravy jsou součástí commitu `699b501`.

## C05 DD Verification Evidence

### Testy odvozené z detailního návrhu

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

### Vybrané úrovně testů

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

### Ověření citlivosti testů na porušení návrhu

Nové testy byly ověřeny dočasnou úpravou kódu (po ověření vráceno):

| Porušení návrhu | Testy, které selhaly |
|---|---|
| Odstraněna kontrola `in_atomic_block` v `record_notification` | `test_recording_outside_transaction_is_rejected_without_writing` |
| Všechny eventy posílány audience `owner` | `test_snapshot_and_audience_follow_event`, `test_decision_and_expiry_enqueue_owner_notifications`, `test_committed_transitions_are_delivered_through_sender` |
| `_notify` vrácen na C03 styl `transaction.on_commit(...)` | `test_outbox_record_and_status_change_share_one_transaction`, `test_confirmation_enqueues_notification_without_inline_delivery`, `test_decision_and_expiry_enqueue_owner_notifications`, `test_committed_transitions_are_delivered_through_sender` |

### Spuštěné jednotkové a komponentové testy

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

### Nesoulad návrhu a implementace

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

### Vyřešení

Původní popis C03 s `on_commit` a pouze logovacím adaptérem je historická
baseline. C05 jej nahrazuje transakčním outboxem a asynchronním dispatcherem.
Implementace a testy odpovídají aktualizovaným rozhodnutím C05; změna kódu
není nutná.

Ověřování odhalilo dvě mezery na straně verifikace, ne kódu: kontrakt
`record_notification` neměl přímé testy a test transakční hranice neprocházel
rezervační službou. Obojí je doplněno testy výše. Chybějící přechod ve stavovém
modelu je nesoulad v DD — kód je správně (zabraňuje věčnému `PENDING` záznamu),
proto se upraví DD, ne kód.

### Zbývající návrhová rizika

- Doručení typu at-least-once může po pádu workeru vytvořit duplicity.
- Přijímač ignorující `Idempotency-Key` může duplicity skutečně zaznamenat.
- Lokální `FAILED` neprokazuje, že externí služba zprávu nepřijala.
- SQLite testy nepotvrzují chování při produkčním zamykání řádků.
- Payload nyní obsahuje ID a stav, nikoli verzované veřejné schéma.

### Commit / tag

Implementační baseline: `a23efc8` — `integrated notification app to the system`.
Tato dokumentace C05 a zaměřený diagram `.puml` představují důkazní změnu
pro implementovanou část notifikační služby.

Testy odvozené z DD a tato verifikace: TODO — hash commitu / tag `C05`.

## C06 Internal Evidence Assessment

Assessed baseline:

- **Tag `C05`**, commit `5f528647f6b132ceac27b9c0ef95270ae5ae3e24`
  (`5f52864`), aktuální lokální `main` po návratu na tuto verzi.
  Posouzení zahrnuje dokumentaci, kód a testy tohoto commitu, bez pozdějších
  oprav z PR #17. Datum zápisu: 1. 11. 2026.
- Historické milníky: `C01` (`1137bbf`), `C02` (`6ebfcc1`),
  `C03` (`1799c7b`). Tag `C05` zahrnuje implementaci outboxu, DD
  a doplněnou verifikaci; identifikuje také C05 evidenci s TODO výše.
- Podklad: [assessed_project.md](../../assessed_project.md), hodnocení
  SIGMA → HAH z 19. 10. 2026. F1–F3 byly znovu porovnány s aktuálními
  soubory; rozhodnutí níže se vztahují výhradně k tagu `C05`.
- Ve zdrojích je 23 rezervačních a 23 notifikačních testů. C05 evidence
  výše zaznamenává 46 úspěšných testů za 0,393 s na Pythonu 3.11.9
  s Django 5.2.18. Při tomto zápisu testy znovu spuštěny nebyly, protože
  dostupnému prostředí chybí Django. Nové ověření je statické porovnání
  specifikace, diagramových zdrojů, implementace a testových očekávání.

Verified findings:

- **F1 — C02, VERIFIED FINDING:** OP-01/OP-03 neúplně popisují
  implementovaný cutoff 15 minut, minimální předstih 24 hodin pro
  schvalovanou rezervaci a `approval_deadline = now + 24 h`. OP-03
  neodkazuje na BR-08; obnova držení není plně zachycena ve specifikaci
  a diagramech. Guardy stavového diagramu se překrývají pro celý sál
  s nejvýše 10 sedadly. Evidence: `operations.md`, `intent_and_change.md`,
  `c02-diagrams/state.puml` a aktivity oproti
  `reservation/services.py:_check_lead_time`, `_requires_approval`,
  `confirm_reservation`, `touch_reservation` a příslušným testům.
- **F2 — C03, VERIFIED FINDING:** G2/H1 a C03 evidence stále uvádějí
  post-commit adaptér, G4 neukazuje dispatcher. Skutečná cesta je
  `_notify` → `notification.services.record_notification` uvnitř
  rezervační transakce; doručuje samostatný dispatcher mimo transakci.
  Citovaný test `test_notification_side_effect_is_isolated_to_integration_adapter`
  v aktuální sadě neexistuje. C05 sice označuje starý návrh za historický,
  ale původní pohledy a PASS zůstávají neoznačené. ADR také připouští
  dispatch ve smyčce expirace, zatímco implementace používá samostatný
  příkaz `dispatch_notifications --watch`.
- **F3 — C05, VERIFIED FINDING:** Stavový model a pseudokód DD vynechávají
  `expirovaný lease + attempts >= max → FAILED`.
  `notification/dispatcher.py:_claim` přechod provádí a test
  `test_crash_on_last_attempt_becomes_failed_without_another_send`
  jej kontroluje. C05 evidence slibuje úpravu DD, která v tagu `C05`
  chybí. Selhání uložená tímto úklidem se navíc nezapočítávají do
  `counts["failed"]` vráceného dispatcherem.

Owner disposition:

| Finding | Disposition | Důvod / evidence |
|---|---|---|
| F1 | ACCEPTED — change required | Specifikace a diagramy musí úplně zachycovat implementovaná časová pravidla a prioritu schválení celého sálu. |
| F2 | ACCEPTED — change required | Aktuální outbox neodpovídá starým pohledům a tvrzenému conformance PASS; sjednotit architekturu a evidenci. |
| F3 | ACCEPTED — change required | DD vynechává implementovaný a testem popsaný přechod; vyjasnit také kontrakt počitadla selhání. |

Actions / justified no-change decisions:

- **F1:** Doplnit OP-01/OP-03, odkazy na pravidla a diagramy o časové
  kontroly, schvalovací deadline a obnovu držení; vyloučit celý sál
  z guardu přímého potvrzení. Zachovat implementované časové chování.
- **F2:** Aktualizovat G2/G4/H1 a ADR pro transakční outbox a samostatný
  dispatch worker. Staré závěry označit jako nahrazené; nedoložený PASS
  odstranit nebo nahradit existující opakovatelnou kontrolou.
  Zachovat transakční zápis a doručování mimo transakci.
- **F3:** Doplnit terminální úklid lease do DD modelu a pseudokódu.
  Zachovat ochranu proti věčnému `PENDING`; rozhodnout, zda `failed`
  zahrnuje i úklid, a sjednotit kontrakt, implementaci a test.
- V tagu `C05` nejsou tyto opravy dokončené. Tento zápis je evidencí
  posouzení a rozhodnutí, nikoli důkazem uzavření nálezů. Konkrétní
  vlastníky a termíny navazujících akcí tým dosud neurčil.

Remaining evidence gaps:

- Nový reprodukovatelný běh testů svázaný s tagem `C05`. Původní review
  uvádí úspěšný B2, ale ve F1–F3 tvrdí, že testy nebyly spuštěny;
  tento rozpor nelze považovat za doklad nového ověření.
- Pro Q1–Q3 chybí definovaný workload, přijatelné latence a četnost
  `busy` i skutečné měření 20 souběžných rezervací a rozhodnutí z výsledku.
- Chybějí testy souběžného Confirm, Confirm s neaktivním sedadlem,
  souběžných claimů dvou workerů, kladných nastavení, zkrácení chyby
  na 2 000 znaků, outbox DB constraintů a počítání úklidových selhání.
- Sjednotit ownership expirace v G3 s rezervačními službami a zachytit
  lazy expiry. Po opravách doložit návaznost původního tagu `C05`
  na nový reporting commit/tag a důkazy uzavření F1–F3.

## Následné vypořádání nálezů po assessmentu C05

| Oblast | Co bylo provedeno | Konkrétní evidence |
|---|---|---|
| F1 — specifikace a pravidla | C02 operations, pravidla a diagramové zdroje byly sjednoceny s cutoffem 15 minut, předstihem 24 hodin, prioritou schválení celého sálu a obnovou držení. | [`operations.md`](operations.md) OP-01, OP-01a a OP-03; [`intent_and_change.md`](intent_and_change.md) BR-07/BR-08; [`activity-op03-confirm.puml`](c02-diagrams/activity-op03-confirm.puml), [`activity-op01-create.puml`](c02-diagrams/activity-op01-create.puml), [`state.puml`](c02-diagrams/state.puml), [`use-case.puml`](c02-diagrams/use-case.puml) |
| F2 — architektura a evidence | Pohledy C03 a evidence používají transakční outbox a samostatný dispatcher; starý `on_commit` popis je historická baseline. | [`architecture-and-decisions.md`](architecture-and-decisions.md); [`design-sequence-confirm.puml`](c03-diagrams/design-sequence-confirm.puml); [`static-architecture.puml`](c03-diagrams/static-architecture.puml); [`dispatcher.py`](../src/rezervace_divadlo/notification/dispatcher.py) |
| F3 — DD a dispatcher | DD popisuje terminální přechod expirovaného lease do `FAILED`; dispatcher započítává úklidová selhání do `counts["failed"]`. | [`architecture-and-decisions.md`](architecture-and-decisions.md) — stavový model a pseudokód; [`dispatcher.py`](../src/rezervace_divadlo/notification/dispatcher.py); [`test_crash_on_last_attempt_becomes_failed_without_another_send`](../src/rezervace_divadlo/notification/tests.py) |
| C04/Q evidence | Byl doplněn reprodukovatelný příkaz a testovací podklad pro lokální měření dvaceti souběžných pokusů. | [`measure_reservation_concurrency.py`](../src/rezervace_divadlo/reservation/management/commands/measure_reservation_concurrency.py); [`tests_concurrency.py`](../src/rezervace_divadlo/reservation/tests_concurrency.py) |
| Confirm diagram | Zdroj a vyrenderovaný obrázek Confirm sekvence byly po architektonické opravě sjednoceny. | [`design-sequence-confirm.puml`](c03-diagrams/design-sequence-confirm.puml) a [`design-sequence-confirm.png`](c03-diagrams/design-sequence-confirm.png) |

Stav vypořádání:

| Finding | Stav v reporting baseline | Zbývající akce |
|---|---|---|
| F1 | CLOSED pro aktuální reporting baseline. | `touch_reservation` je zachycen v use-case, stavovém, activity a ownership pohledu; implementace je v [`services.py`](../src/rezervace_divadlo/reservation/services.py) a test obnovy v [`tests.py`](../src/rezervace_divadlo/reservation/tests.py). |
| F2 | CLOSED pro aktuální architekturu a evidenci. | Udržovat [`architecture-and-decisions.md`](architecture-and-decisions.md), diagramy a [`dispatcher.py`](../src/rezervace_divadlo/notification/dispatcher.py) synchronizované při dalších změnách. |
| F3 | CLOSED pro aktuální implementaci. | Zachovat [`test_crash_on_last_attempt_becomes_failed_without_another_send`](../src/rezervace_divadlo/notification/tests.py) a při změně dispatcheru znovu ověřit kontrakt počitadla. |


## A — Technické argumenty a evidence aktuální baseline

| Technický argument | Aktuální tvrzení | Evidence | Omezení |
|---|---|---|---|
| Životní cyklus rezervace a exkluzivita sedadel | Create atomicky zablokuje vybraná sedadla; Confirm provede přímé potvrzení nebo odešle rezervaci ke schválení; Cancel, Reject a Expire uvolní aktivní alokace a zachovají historii. | `reservation/services.py`, `reservation/models.py`, `docs/operations.md`, `docs/intent_and_change.md`, testy `reservation`. | Ověření probíhá přes aplikační služby, nikoli přes HTTP API; API není součástí aktuálního projektu. |
| Schvalovací a časová pravidla | Hranice 10 sedadel, priorita celého sálu, cutoff 15 minut, předstih 24 hodin a pětiminutové obnovitelné držení jsou implementované a ověřené na hranicích. | OP-01, OP-01a a OP-03 v `docs/operations.md`, pravidla v `docs/intent_and_change.md`, testy časových hranic a obnovy držení. | Důkaz je z lokální testovací databáze; není to důkaz produkčního nasazení. |
| Notifikační integrace | Rezervační přechod zapíše neměnný outbox snapshot ve stejné transakci; samostatný dispatcher provádí claim, doručení, retry, backoff a fencing. | `docs/architecture-and-decisions.md`, `docs/c03-diagrams/`, `notification/services.py`, `notification/dispatcher.py`, testy `notification`. | Externí doručení je zastoupeno adaptérem nebo test double; skutečný externí receiver není součástí baseline. |
| Lokální souběh rezervací | Měření 20 workerů v 5 kolech vytvořilo 5 vítězných alokací, zaznamenalo 95 konfliktů, 0 `busy`, medián latence 201,14 ms a propustnost 19,6 pokusu/s. | `measure_reservation_concurrency --workers 20 --rounds 5` po migraci lokální SQLite databáze. | Výsledek platí pouze pro deklarovaný lokální workload a SQLite; není kapacitní garancí pro produkční databázi. |
| Aktuální verifikace | Aktuální větev má 48 testů a `manage.py check` nehlásí systémové chyby. | `python src/rezervace_divadlo/manage.py test notification reservation`; aktuální ověřovací běh. | Nejsou plně ověřené migrace existujících dat, produkční recovery ani externí doručení. |

## B — Risk register aktuální baseline

Následující rizika jsou samostatná od historických findings F1–F3. Likelihood
a impact používají stupnici 1–3; priorita je `L × I`. Skutečné reziduální
riziko je `NOT VERIFIED`, dokud není doložena účinnost opatření.

### R-01 — Přenositelnost SQLite concurrency

- **Kategorie:** Technická / výkonová
- **Příčina → nejistá událost → důsledek:** SQLite serializuje zápisy; produkční
  workload nebo databázový engine se bude chovat jinak než lokální měření;
  vzroste latence, lock contention nebo počet odmítnutých požadavků.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH.
- **Response:** MITIGATE — zachovat reprodukovatelné lokální měření a před
  volbou produkční databáze definovat workload a prahové hodnoty.
- **Opatření / vlastník / termín:** HAH; zapsat workload, limity a další
  měření před příštím CP1 review.
- **Důkaz účinnosti:** 20 workerů × 5 kol: 0 `busy`, medián 201,14 ms,
  propustnost 19,6 pokusu/s.
- **Očekávané reziduum:** 1 / 3 / MEDIUM.
- **Skutečné reziduum:** NOT VERIFIED pro produkční databázi.
- **Trigger / contingency / další review:** `busy` nebo latence nad limitem;
  vyhodnotit PostgreSQL či jinou strategii zamykání; review při CP1.
- **Rozhodnutí:** Přijmout omezení pouze pro lokální baseline; vlastník HAH.

### R-02 — Duplicity při at-least-once notifikacích

- **Kategorie:** Integrace / spolehlivost
- **Příčina → nejistá událost → důsledek:** Worker selže po přijetí zprávy
  externím receiverem, ale před uložením `SENT`; retry doručí duplicitu.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH.
- **Response:** MITIGATE — zachovat stabilní ID zprávy a `Idempotency-Key`;
  vyžadovat deduplikaci na straně receiveru.
- **Opatření / vlastník / termín:** vlastník notifikační integrace; zdokumentovat
  a ověřit idempotenci receiveru před externí integrací.
- **Důkaz účinnosti:** test HTTP adaptéru ověřuje stabilní idempotency key;
  deduplikace skutečného receiveru ověřena není.
- **Očekávané reziduum:** 1 / 2 / MEDIUM.
- **Skutečné reziduum:** NOT VERIFIED.
- **Trigger / contingency / další review:** duplicita nebo receiver bez
  idempotence; pozastavit doručování či provést reconciliaci podle ID.
- **Rozhodnutí:** Přijmout dočasně do uzavření kontraktu receiveru; vlastník HAH.

### R-03 — Dostupnost dispatcheru a expiry workeru

- **Kategorie:** Provozní
- **Příčina → nejistá událost → důsledek:** Dispatcher nebo expiry command
  neběží, zpozdí se nebo ztratí lease; doručení a persistované `EXPIRED`
  přechody se zpozdí.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH.
- **Response:** MITIGATE — používat management commands s `--watch`, sledovat
  výstup a zachovat lease recovery a retry.
- **Opatření / vlastník / termín:** provozní vlastník; definovat supervision,
  restart policy a alert thresholds před nasazením.
- **Důkaz účinnosti:** testy commandů, lease recovery a retry procházejí;
  dlouhý běh ani restart drill proveden nebyl.
- **Očekávané reziduum:** 1 / 2 / MEDIUM.
- **Skutečné reziduum:** NOT VERIFIED.
- **Trigger / contingency / další review:** stale `PENDING` nebo overdue hold;
  restart workeru a one-shot recovery; review při operational readiness.
- **Rozhodnutí:** Přijmout pouze pro development baseline; produkční provoz
  vyžaduje doplnění supervision evidence.

### R-04 — Migrace existujících dat

- **Kategorie:** Data / migrace
- **Příčina → nejistá událost → důsledek:** Migrace `0002` převádí staré
  rezervace do více-sedadlového modelu, ale nebyla provedena fixture-based
  zkouška reprezentativní staré databáze; může vzniknout ztráta dat nebo
  nesprávná aktivní alokace.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH.
- **Response:** MITIGATE — vytvořit legacy fixture, provést forward migration,
  ověřit rezervace i alokace a zachovat backup.
- **Opatření / vlastník / termín:** vlastník persistence; provést rehearsal
  před použitím existující databáze.
- **Důkaz účinnosti:** existují migrační soubory a požadavek na backup;
  fixture-based rehearsal doložen není.
- **Očekávané reziduum:** 1 / 2 / MEDIUM.
- **Skutečné reziduum:** NOT VERIFIED.
- **Trigger / contingency / další review:** nesoulad počtů nebo kontrol migrace;
  obnovit backup a zastavit rollout; review před data-bearing deploymentem.
- **Rozhodnutí:** Pro produkční rollout zatím nepřijmout; vlastník HAH.
