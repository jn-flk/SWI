# C02 - Doménová pravidla a baseline

Změna C02 rozšiřuje rezervaci o výběr více sedadel, schvalování hromadných
rezervací a automatické vypršení neaktivních nebo dlouho čekajících stavů.
Hranice pro hromadnou rezervaci je více než deset sedadel; rezervace celého sálu
vyžaduje schválení vždy. Jedna `Reservation` může obsahovat více sedadel.

## Stavy rezervace

- `DRAFT`: uživatel vybral jedno nebo více sedadel a pokračoval k rezervaci.
    Sedadla jsou po omezenou dobu dočasně držena pro daného návštěvníka.
    Stav má `hold_until`.
- `PENDING_APPROVAL`: hromadná rezervace byla odeslána ke schválení. Stav je
    nefinální a všechna její sedadla zůstávají blokována.
- `CONFIRMED`: běžná rezervace byla přijata nebo hromadná rezervace schválena.
    Všechna sedadla jsou blokována pro dané představení.
- `REJECTED`: hromadná rezervace byla zamítnuta schvalovatelem. Stav je
    terminální a sedadla již nejsou blokována.
- `CANCELLED`: existující rezervace nebo držení bylo aktivně zrušeno
    oprávněným aktérem. Stav je terminální a sedadla již nejsou blokována.
- `EXPIRED`: držení nebo čekání na schválení vypršelo bez aktivního
    rozhodnutí. Stav je terminální a sedadla již nejsou blokována.

## Přechody

- `[none] -> DRAFT`: vznikne nová rezervace pro vybraná sedadla a systém je
    po omezenou dobu drží pro daného návštěvníka.
- `DRAFT -> CONFIRMED`: běžná rezervace s nejvýše deseti sedadly je po
    dokončení uživatelem přijata a sedadla jsou trvale blokována.
- `DRAFT -> PENDING_APPROVAL`: hromadná rezervace s více než deseti sedadly
    nebo rezervace celého sálu je odeslána ke schválení. Sedadla zůstávají
    blokována do rozhodnutí nebo vypršení.
- `DRAFT -> CANCELLED`: návštěvník nebo jiný oprávněný aktér aktivně zruší
    držení před jeho potvrzením. Sedadla se uvolní.
- `DRAFT -> EXPIRED`: držení automaticky vyprší, například po ukončení
    neaktivní rezervační relace. Sedadla se uvolní bez aktivního zrušení.
- `PENDING_APPROVAL -> CONFIRMED`: schvalovatel hromadnou rezervaci přijme.
    Sedadla zůstávají trvale blokována.
- `PENDING_APPROVAL -> REJECTED`: schvalovatel hromadnou rezervaci zamítne.
    Sedadla se uvolní a žádost je terminálně ukončena.
- `PENDING_APPROVAL -> EXPIRED`: žádost nebyla schválena před uplynutím
    stanovené lhůty. Sedadla se uvolní automaticky.
- `PENDING_APPROVAL -> CANCELLED`: návštěvník nebo jiný oprávněný aktér
    čekající žádost aktivně zruší před rozhodnutím. Sedadla se uvolní.
- `CONFIRMED -> CANCELLED`: návštěvník nebo jiný oprávněný aktér aktivně
    zruší potvrzenou rezervaci před začátkem představení. Sedadla se uvolní.

## Společná pravidla

BR-01 — Interval semantics
Rezervační intervaly používají polouzavřenou sémantiku `[start,end)`. Dotyk
na hranici, například `[09:00,10:00)` a `[10:00,11:00)`, není překryv.

BR-02 — Exclusive Resource invariant
Pro jedno představení nesmí být stejné sedadlo současně součástí více
aktivních rezervací. Aktivní `DRAFT`, `PENDING_APPROVAL` i `CONFIRMED` proto
blokují stejné sedadlo.

BR-03 — Cancellation policy
`DRAFT`, `PENDING_APPROVAL` a `CONFIRMED` lze aktivně zrušit pouze při
`now < start`. Změna je atomická a záznam se nemaže. Opakované zrušení již
`CANCELLED` rezervace oprávněným aktérem vrací idempotentní úspěch se stavem
`CANCELLED`, bez další změny a bez ohledu na čas začátku. Stavy `REJECTED`
a `EXPIRED` zrušit nelze.

BR-04 — Confirmation policy
OP-03 je dokončení rezervace uživatelem. U rezervace s nejvýše deseti sedadly
vede k `CONFIRMED`; u hromadné rezervace nebo rezervace celého sálu vede k
`PENDING_APPROVAL`. Přechod je atomický s kontrolou platnosti držení.
Kolize se kontroluje při vytvoření `DRAFT`; sedadla zůstávají blokována
také v `PENDING_APPROVAL`. OP-03 ani OP-05 proto dostupnost nebo kolizi
znovu nekontrolují a při potvrzení či schválení zachovávají existující
blokování podle BR-02.

BR-05 — Availability policy
Dostupnost blokují aktivní `DRAFT`, `PENDING_APPROVAL` a `CONFIRMED`
rezervace. `CANCELLED`, `REJECTED` a `EXPIRED` se do výsledku dostupnosti
nezapočítávají.

BR-06 — Concurrent outcome
Vytvoření držení musí atomicky ověřit dostupnost podle BR-02 a zablokovat
vybraná sedadla. Při závodu dvou návštěvníků o stejné sedadlo uspěje pouze
první platná alokace. Dokončení rezervace, schválení, zrušení a expirace
atomicky ověřují zdrojový stav a zachovávají nebo uvolňují existující
blokování; novou kontrolu kolize neprovádějí. Při závodu schválení, zrušení
a expirace uspěje pouze první platný přechod.

BR-07 — Hold and inactivity policy
Uživatel nejdříve zobrazí sál a vybere jedno nebo více volných sedadel.
Tlačítko pro pokračování s rezervací se zobrazí až po výběru alespoň jednoho
sedadla. Po jeho stisku systém atomicky vytvoří jednu `Reservation` pro
všechna vybraná sedadla ve stavu `DRAFT` s `hold_until`. Neaktivní
rezervační relace se po pěti minutách ukončí a aktivní držení přejde do
`EXPIRED`; serverový `hold_until` je autoritativní.

BR-08 — Bulk approval lead time
Hromadná rezervace musí být vytvořena s dostatečným předstihem před začátkem
představení, aby zůstala lhůta pro manuální schválení. Konkrétní minimální
předstih je součástí rezervační politiky; po jeho překročení systém
hromadnou žádost odmítne vytvořit nebo přijmout ke schválení.

## Kontrola přijetí požadavků

Požadavky jsou ověřitelné přes stav rezervace, počet jejích sedadel,
`hold_until`, lhůtu pro schválení, dostupnost sedadel a atomické chování při
souběhu. Ověřit je nutné také zpožděné schválení, zamítnutí, expiraci a
uvolnění všech sedadel skupinové rezervace.

## Co se nezměnilo

Intervalová sémantika `[start,end)`, pravidlo jediné aktivní rezervace pro
sedadlo a představení, možnost zrušení před začátkem představení, použití
Django ORM, SQLite pro vývoj a externí hranice Notification Service zůstávají
beze změny. C02 pouze rozšiřuje stavy, aktéry a časový životní cyklus
rezervace.



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

Návštěvníci divadla; oprávněný schvalovatel rezervací.

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
Reservation (konkrétní představení) - časový slot, hra, jedno nebo více
vybraných sedadel, stav, `hold_until` a případná lhůta pro schválení.

## Common business rule
Sedadlo v konkrétním představení může být rezervováno jenom jednou.

## Domain-specific business rule
Nelze rezervovat 15 min před začátkem představení. Rezervace více než deseti
sedadel je hromadná a vyžaduje schválení. Rezervace celého sálu vyžaduje
schválení vždy. Hromadnou rezervaci nelze vytvořit bez dostatečného předstihu
před začátkem představení.

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
