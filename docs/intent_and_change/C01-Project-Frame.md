# C01 — Project Frame

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
