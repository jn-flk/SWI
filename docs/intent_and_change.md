# C02 - Doménová pravidla a baseline

## Stavy rezervace

- `DRAFT`: rezervace vznikla výběrem sedadla a sedadlo je po omezenou dobu
    dočasně drženo pro daného návštěvníka. Stav má `hold_until`.
- `CONFIRMED`: návštěvník dokončil formulář a systém rezervaci přijal.
    Sedadlo je blokováno pro dané představení.
- `CANCELLED`: rezervace byla zrušena nebo její držení vypršelo. Stav je
    terminální a sedadlo již není blokováno.

Přechody jsou `[none] -> DRAFT`, `DRAFT -> CONFIRMED`,
`DRAFT -> CANCELLED` a `CONFIRMED -> CANCELLED`. Držení ve stavu `DRAFT`
vyprší po dosažení `hold_until` a systém ho převede do `CANCELLED`.

## Společná pravidla

BR-01 — Interval semantics
Rezervační intervaly používají polouzavřenou sémantiku `[start,end)`. Dotyk
na hranici, například `[09:00,10:00)` a `[10:00,11:00)`, není překryv.

BR-02 — Exclusive Resource invariant
Pro jedno představení nesmí být stejné sedadlo současně drženo nebo potvrzeno
více než jednou. Aktivní `DRAFT` i `CONFIRMED` proto blokují stejné sedadlo.

BR-03 — Cancellation policy
`DRAFT` a `CONFIRMED` lze zrušit pouze při `now < start`.
Změna je atomická, záznam se nemaže a opakované zrušení terminálního stavu je
explicitně odmítnuto.

BR-04 — Confirmation policy
OP-03 je přímé potvrzení uživatelem. Při úspěšném potvrzení vzniká
`CONFIRMED` atomicky s kontrolou platnosti držení a kolize.

BR-05 — Availability policy
Dostupnost blokují aktivní `DRAFT` a `CONFIRMED` rezervace. `CANCELLED` a
`DRAFT` po `hold_until` se do výsledku dostupnosti nezapočítávají.

BR-06 — Concurrent outcome
Vytvoření držení i jeho potvrzení musí rozhodnout atomická změna s kontrolou
BR-02. Při závodu dvou návštěvníků uspěje pouze první platné držení; druhý
uvidí sedadlo jako nedostupné. Při závodu s cancel uspěje první platná změna
stavu.

BR-07 — Hold policy
Kliknutí na volné sedadlo vytvoří držení ještě před zobrazením formuláře.
Dokud držení trvá, jiný návštěvník se nesmí dostat do vytvoření rezervace na
stejné sedadlo. Po odeslání formuláře se držení buď atomicky potvrdí, nebo se
uvolní podle výsledku operace.

## Kontrola přijetí požadavků

Požadavky jsou ověřitelné přes stav rezervace, `hold_until`, dostupnost
sedadla a atomické chování při souběhu. Konkrétní framework ani databáze zde
nejsou předepsány; implementace musí zachovat pozorovatelné podmínky tohoto
modelu.



# C01 - Project Frame

Resource - sedadlo
Reservation - konkrétní představení
STACK - Django - SQLite

## Reservation domain
Co konkrétně rezervujeme?

sedadla v divadle na představení

## Purpose
1-3 věty: komu systém slouží a proč.

Systém slouží pro návštěvníky divadla, kteří by si chtěli rezervovat sedadla předem nebo přes web.

## Users / Stakeholders
1–3 role.

Návštěvníci divadla

## Core concepts
Reservation, Resource, User + případně 0–3 další pojmy.

## Core operations
- Create reservation
- Confirm / approve reservation
- Cancel reservation
- Check availability

## Persistent state
Co ukládáme o Reservation a Resource.
Resource (sedadlo) - řada, číslo sedadla
Reservation (konkrétní představení) - časový slot, hra, 

## State-changing operation
[none] -> DRAFT

DRAFT -> CONFIRMED

DRAFT -> CANCELLED

CONFIRMED -> CANCELLED

## Common business rule
Sedadlo v konkrétním představení může být rezervováno jenom jednou.

## Domain-specific business rule
Nelze rezervovat 15 min před začátkem představení.

## External / system boundary
Notification Service

## Assumption
Django ORM and a relational database are sufficient to represent
and persist our core reservation entities: Seat, Play, Performance, Hall and Reservation.

## Unknown
We do not yet know whether our proposed model relationships can
actually persist and retrieve a Reservation correctly from the database.

## Selected future pressure
Category: Q
Concrete pressure: 20x souběžnch rezervací
