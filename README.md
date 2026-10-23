# Název týmu

## HAH
**Členové:** Honza, Adam, Honza

**Repozitář:** https://github.com/jn-flk/SWI


## Doména rezervací
Co konkrétně rezervujeme?

- Zdroj – sedadlo v divadle
- Rezervace – jedno nebo více sedadel na konkrétní představení
- Uživatel – návštěvník divadla
- Stavy – DRAFT, PENDING_APPROVAL, CONFIRMED, REJECTED, CANCELLED, EXPIRED
- Operace – vytvoření, potvrzení či schválení, zrušení a kontrola dostupnosti
- Společné pravidlo – stejné sedadlo nesmí být současně blokováno více aktivními rezervacemi pro stejné představení
- Hranice systému – služba oznámení (Notification Service)

Úplný popis domény je v [dokumentu o záměru a změnách](docs/intent_and_change.md).

## Instalace a spuštění

```bash
python3 -m venv venv
source venv/bin/activate
pip install django
python src/rezervace_divadlo/manage.py migrate
python src/rezervace_divadlo/manage.py test notification reservation
```

## CP1 – základní průchod aplikací

#### Funkčnost
Návštěvník si může rezervovat konkrétní sedadlo na konkrétní představení.

#### Průběh od požadavku po uložení
Volání aplikační služby (bez HTTP API):

- ověřit existenci představení;
- ověřit existenci sedadla;
- ověřit, že sedadlo patří do sálu daného představení;
- ověřit dostupnost sedadla pro dané představení;
- vytvořit rezervaci;
- uložit rezervaci do databáze;
- vrátit identifikátor rezervace.

## Dopad změny C02

### Rozšíření rezervace a pravidel

C02 rozšiřuje původní rezervaci jednoho sedadla o skupinové rezervace, ruční schvalování a časově omezené držení sedadel. Jedna rezervace má vlastníka a obsahuje jedno nebo více sedadel. Doménová logika je v `src/rezervace_divadlo/reservation/services.py`; HTTP API není součástí aplikace.

- Vytvoření rezervace atomicky ověří dostupnost a zablokuje všechna vybraná sedadla ve stavu `DRAFT`.
- Nejvýše 10 sedadel lze potvrdit přímo. Více než 10 sedadel nebo celý sál vyžaduje schválení, i když má sál méně než 11 sedadel.
- Hromadná rezervace vyžaduje alespoň 24 hodin do začátku představení při vytvoření i při odeslání ke schválení. Běžnou rezervaci nelze vytvořit ani potvrdit 15 minut před začátkem nebo později.
- `DRAFT` vyprší po 5 minutách neaktivity. Zaznamenaná aktivita prodlužuje držení; rozhodující je serverový `hold_until`.
- `PENDING_APPROVAL` má lhůtu 24 hodin. Oprávněný schvalovatel může rezervaci schválit nebo zamítnout před vypršením lhůty a začátkem představení.
- Zrušení je možné před začátkem představení. Opakované zrušení již `CANCELLED` rezervace je idempotentní, také po začátku představení.

### Stavy, operace a diagramy

`DRAFT`, `PENDING_APPROVAL` a `CONFIRMED` blokují sedadla. Přechod do `CANCELLED`, `REJECTED` nebo `EXPIRED` sedadla uvolní a zachová historii rezervace. Potvrzení ani schválení neopakují kontrolu kolize, protože sedadla jsou blokována od vytvoření.

Služby pokrývají vytvoření, zjištění dostupnosti, potvrzení, zrušení, schválení či zamítnutí, obnovení držení a expiraci. Diagram případů užití přidává schvalovatele a systémový časovač; stavový diagram a diagramy aktivit popisují nové přechody a uvolnění sedadel. Zdroje i obrázky jsou v [docs/c02-diagrams](docs/c02-diagrams/).

Expiraci lze zpracovat příkazem Django:

```bash
python src/rezervace_divadlo/manage.py expire_reservations
```

Pro průběžnou expiraci lze příkaz spustit s `--watch --interval 1`, případně zajistit pravidelné spouštění plánovačem. Oznámení vlastní Django aplikace `notification`: rezervační služby zapisují požadavky do outboxu atomicky se změnou rezervace. Samostatný dispatcher doručuje oznámení s retry a backoffem; výchozí adaptér zapisuje do logu.

SQLite concurrency measurement:

```bash
python src/rezervace_divadlo/manage.py migrate
python src/rezervace_divadlo/manage.py measure_reservation_concurrency --workers 20 --rounds 5
```

The measurement uses an isolated temporary dataset and cleans it up after the
run. It reports whether the single-seat winner invariant holds, database
`busy` outcomes, latency and throughput.

### Ověření a dopad na architekturu

`reservation/tests.py` obsahuje 23 testů služeb bez API a `notification/tests.py`
obsahuje 24 testů outboxu a dispatcheru (47 testů celkem). Pokrývají například hranici 10/11
sedadel, rezervaci celého malého sálu, předstih 24 hodin, hranici 15 minut,
expiraci přesně při uplynutí lhůty, neoprávněné změny, neplatný výběr sedadel,
uvolnění blokování, outbox rollback, retry a lease recovery. Tyto testy samy
neprokazují chování při skutečném souběhu více databázových spojení.

Zůstávají Django ORM, SQLite pro vývoj, intervaly `[start,end)` a pravidlo jediné aktivní rezervace sedadla pro dané představení. Datový model přidává vazbu `ReservationSeat`, stav, vlastníka a časové limity. Transakce a databázová omezení chrání aktivní alokace; změny schématu obsahuje migrace `0002`.

Pro C03 zůstávají témata ověření souběžných rezervací při vyšší zátěži, plánování expirace a napojení notifikací. Podrobnosti jsou v [architektonických rozhodnutích](docs/architecture-and-decisions.md) a [evidenci vývoje](docs/evidence-and-evolution.md).

Textová specifikace v `intent_and_change.md` a `operations.md` ještě obsahuje starší hranice schvalování. Přehled v tomto README vychází z diagramů, implementace a dohodnutého pravidla **více než 10 sedadel nebo celý sál**.
