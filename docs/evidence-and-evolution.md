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
- Hranice schvalování byla rozhodnuta jako více než 10 sedadel podle
  diagramů. Implementace a testy tomu odpovídají, ale `intent_and_change.md`
  stále uvádí pět a více sedadel a OP-03 v `operations.md` obsahuje
  neslučitelné hranice. Tento dokumentační nesoulad zůstává otevřený.
- BR-08 dosud neurčuje konkrétní předstih, zatímco implementace podle
  rozhodnutí uživatele vyžaduje 24 hodin. Text je třeba sjednotit také
  s lhůtou schválení a povolenými výsledky souběhu.
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

- Sjednotit textovou specifikaci s přijatou hranicí více než 10 sedadel,
  24hodinovým předstihem a sériovým posouzením stavů při souběhu.
- Doplnit chybějící diagram aktivity OP-02 a časové podmínky v diagramech;
  explicitní schválení baseline v0.1/v0.2 týmem není doloženo.
- Aktuální jednoduché testy neověřují paralelní zápisy, výkon při
  20 souběžných požadavcích ani zachování dat při migraci existující databáze.
- Notifikace používají pouze lokální logovací adaptér. Externí doručování,
  jeho selhání a opakování nejsou ověřené.
- Pravidelné ukládání stavu `EXPIRED` vyžaduje spuštěný příkaz
  `python manage.py expire_reservations --watch`. Jeho nepřetržitý provoz
  a zotavení po výpadku nejsou součástí současné jednoduché testovací sady.
