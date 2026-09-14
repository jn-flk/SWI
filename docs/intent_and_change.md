# Project Frame

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
! Jedna věc, kterou nyní považujete za pravdivou, ale není jistota.

## Unknown
! Jedna důležitá věc, kterou nyní nevíte.

## Selected future pressure
Category: Q
Concrete pressure: 20x souběžnch rezervací
Why it is relevant to our reservation system: 

Category: C
Concrete pressure: 
Why it is relevant to our reservation system: 

Category: R
Concrete pressure: 
Why it is relevant to our reservation system: 

Category: L
Concrete pressure: 
Why it is relevant to our reservation system: 