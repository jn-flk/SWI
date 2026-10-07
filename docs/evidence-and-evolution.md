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
baseline týmem není v repozitáři explicitně doloženo; textové podklady mají
ještě nesoulady uvedené níže.

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
skončil výsledkem **19 testů, všechny prošly**. Django systémová kontrola
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

- Doplnit chybějící diagram aktivity OP-02 a časové podmínky v diagramech;
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
| relevant boundary/concurrency rule | PASS | 20 Django testů + `manage.py check`; atomická ochrana a constraint jsou ověřeny sekvenční sadou |

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

Remaining uncertainty / risk: Textová specifikace stále obsahuje starší
hranici 5 sedadel; aktuální implementace, diagramy a evidence používají více
než 10 sedadel nebo celý sál. Sada neprokazuje výkon při 20 paralelních
požadavcích ani skutečné doručení a retry externích notifikací.

Commit/tag: změny připraveny v pracovním stromu; commit/tag nebyl vytvořen.
