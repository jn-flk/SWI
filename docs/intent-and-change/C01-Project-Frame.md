# C01 — Project Frame

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [Tech stack](../architecture-and-decisions/C01-Tech-Stack-and-Key-Decisions.md) · [Engineering spike](../evidence-and-evolution/C01-Engineering-Spike.md)

- **Resource:** sedadlo
- **Reservation:** konkrétní představení
- **Stack:** Django, SQLite

## Reservation domain
sedadla v divadle na představení

## Purpose
Systém slouží pro návštěvníky divadla, kteří by si chtěli rezervovat sedadla předem nebo přes web.

## Users / Stakeholders
Návštěvníci divadla; oprávněný schvalovatel rezervací.

## Core concepts
Reservation, Resource (sedadlo), User.

## Core operations
- Create reservation
- Confirm / approve reservation
- Cancel reservation
- Check availability

## Persistent state
- **Resource (sedadlo):** řada, číslo sedadla
- **Reservation (konkrétní představení):** časový slot, hra, jedno nebo více
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
- **Category:** Q
- **Concrete pressure:** 20× souběžných rezervací
