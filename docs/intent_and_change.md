# Project Frame

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
Reservation, Resource (Seat), User + Performance, Play, Hall

## Core operations
- Create reservation
- Confirm / approve reservation
- Cancel reservation
- Check availability

## Persistent state
Co ukládáme o Reservation a Resource.
Resource (sedadlo) - řada, číslo sedadla
Reservation (konkrétní představení) - časový slot, hra, sedadlo, stav rezervace, čas vytvoření 

## State-changing operation
-> RESERVED
RESERVED -> CANCELED
RESERVED -> DONE

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
Concrete pressure: 20x souběžných rezervací
Why it is relevant to our reservation system: Systém aktuálně neřeší souběžný přístup více uživatelů ke stejnému sedadlu ve stejný okamžik (např. při prodeji vstupenek na premiéru). Databázový unique constraint sice zabrání uložení duplicitní rezervace, ale při vyšší zátěži je potřeba řešit i uživatelský zážitek (race condition – dva lidé vidí sedadlo jako volné současně) a výkon databáze při větším počtu souběžných požadavků.