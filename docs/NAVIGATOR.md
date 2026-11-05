# Documentation navigator

Rozcestník všech dokumentů projektu Rezervace divadlo. Dokumenty jsou rozdělené
do čtyř složek podle typu a uvnitř podle cvičení (C01–C07).

| Složka | Co v ní je |
|---|---|
| [intent-and-change/](intent-and-change/) | Co má systém dělat: doména, pravidla, stavy, operace |
| [architecture-and-decisions/](architecture-and-decisions/) | Jak je systém postavený a proč |
| [evidence-and-evolution/](evidence-and-evolution/) | Jak víme, že to platí: testy, ověření, assessment, rizika |
| [diagrams/](diagrams/) | Diagramy PlantUML (`.puml`) a jejich obrázky (`.png`) |

Vazby požadavků a pravidel na kód a testy jsou v [TRACEABILITY.md](TRACEABILITY.md).
Pravidla pro úpravy dokumentace (struktura, odkazy, styl) jsou v [AGENTS.md](AGENTS.md).

## By exercise

| Cvičení | Specifikace | Architektura a návrh | Evidence |
|---|---|---|---|
| C01 | [Project Frame](intent-and-change/C01-Project-Frame.md) | [Tech stack and key decisions](architecture-and-decisions/C01-Tech-Stack-and-Key-Decisions.md) | [Engineering Spike](evidence-and-evolution/C01-Engineering-Spike.md) |
| C02 | [Domain rules](intent-and-change/C02-Domain-Rules.md), [States and transitions](intent-and-change/C02-States-and-Transitions.md), [Operations and requirements](intent-and-change/C02-Operations-and-Requirements.md) | [Domain model and known limitations](architecture-and-decisions/C02-Domain-Model-and-Limitations.md) | [Specification → running application](evidence-and-evolution/C02-Specification-to-Running-App.md) |
| C03 | – | [Current implementation of Confirm (AS-IS)](architecture-and-decisions/C03-AS-IS-Mapping.md), [Architecture design and ADR-01](architecture-and-decisions/C03-Architecture-Design.md) | [Architecture Evidence](evidence-and-evolution/C03-Architecture-Evidence.md) |
| C04 | – | – | Měření souběhu je v [části A dokumentu C07](evidence-and-evolution/C07-Technical-Review-and-Risk-Register.md) |
| C05 | – | [Detailed Design](architecture-and-decisions/C05-Detailed-Design.md) | [DD Verification Evidence](evidence-and-evolution/C05-DD-Verification.md) |
| C06 | – | – | [Internal Evidence Assessment](evidence-and-evolution/C06-Internal-Evidence-Assessment.md) |
| C07 | – | – | [Finding disposition, technical arguments and risk register](evidence-and-evolution/C07-Technical-Review-and-Risk-Register.md) |

## Common questions

| Hledám… | Kde |
|---|---|
| který test ověřuje daný požadavek nebo pravidlo | [Traceability](TRACEABILITY.md) |
| pravidla BR-01 až BR-08 | [Doménová pravidla](intent-and-change/C02-Domain-Rules.md) |
| operace OP-01 až OP-05 a požadavky REQ-01 až REQ-07 | [Operace a požadavky](intent-and-change/C02-Operations-and-Requirements.md) |
| stavy rezervace a povolené přechody | [Stavy a přechody](intent-and-change/C02-States-and-Transitions.md), [stavový diagram](diagrams/c02/state.png) |
| rozhodnutí o notifikacích (outbox) | ADR-01 v [Návrhu architektury](architecture-and-decisions/C03-Architecture-Design.md) |
| vysvětlení pojmů outbox, claim, lease, fencing | část „Glossary“ v [Detailed Design](architecture-and-decisions/C05-Detailed-Design.md) |
| nálezy F1–F3 a jejich vypořádání | [Assessment C06](evidence-and-evolution/C06-Internal-Evidence-Assessment.md), [vypořádání v C07](evidence-and-evolution/C07-Technical-Review-and-Risk-Register.md) |
| rizika R-01 až R-04 | část B v [C07](evidence-and-evolution/C07-Technical-Review-and-Risk-Register.md) |
| aktuální běh testů | část A v [C07](evidence-and-evolution/C07-Technical-Review-and-Risk-Register.md) |

## Diagrams

### C02 — System behaviour

| Diagram | Obrázek | Zdroj |
|---|---|---|
| Diagram případů užití | [use-case.png](diagrams/c02/use-case.png) | [use-case.puml](diagrams/c02/use-case.puml) |
| Stavový diagram | [state.png](diagrams/c02/state.png) | [state.puml](diagrams/c02/state.puml) |
| Aktivity — vytvořit rezervaci (OP-01) | [activity-op01-create.png](diagrams/c02/activity-op01-create.png) | [activity-op01-create.puml](diagrams/c02/activity-op01-create.puml) |
| Aktivity — zjistit dostupnost (OP-02) | [activity-op02-availability.png](diagrams/c02/activity-op02-availability.png) | [activity-op02-availability.puml](diagrams/c02/activity-op02-availability.puml) |
| Aktivity — potvrdit rezervaci (OP-03) | [activity-op03-confirm.png](diagrams/c02/activity-op03-confirm.png) | [activity-op03-confirm.puml](diagrams/c02/activity-op03-confirm.puml) |
| Aktivity — zrušit rezervaci (OP-04) | [activity-op04-cancel.png](diagrams/c02/activity-op04-cancel.png) | [activity-op04-cancel.puml](diagrams/c02/activity-op04-cancel.puml) |
| Aktivity — schválit / zamítnout (OP-05) | [activity-op05-approve.png](diagrams/c02/activity-op05-approve.png) | [activity-op05-approve.puml](diagrams/c02/activity-op05-approve.puml) |
| Aktivity — expirace rezervace | [activity-expiration.png](diagrams/c02/activity-expiration.png) | [activity-expiration.puml](diagrams/c02/activity-expiration.puml) |

### C03 — Architecture

| Diagram | Obrázek | Zdroj |
|---|---|---|
| AS-IS — Confirm Reservation | [as-is-confirm-reservation.png](diagrams/c03/as-is-confirm-reservation.png) | [as-is-confirm-reservation.puml](diagrams/c03/as-is-confirm-reservation.puml) |
| Doménový model | [domain-model.png](diagrams/c03/domain-model.png) | [domain-model.puml](diagrams/c03/domain-model.puml) |
| Kontextový diagram (G1) | [context.png](diagrams/c03/context.png) | [context.puml](diagrams/c03/context.puml) |
| Statická architektura (G2) | [static-architecture.png](diagrams/c03/static-architecture.png) | [static-architecture.puml](diagrams/c03/static-architecture.puml) |
| Vlastnictví přechodů stavů (G3) | [state-ownership.png](diagrams/c03/state-ownership.png) | [state-ownership.puml](diagrams/c03/state-ownership.puml) |
| Runtime a nasazení (G4) | [runtime-deployment.png](diagrams/c03/runtime-deployment.png) | [runtime-deployment.puml](diagrams/c03/runtime-deployment.puml) |
| Sekvence Confirm (H1) | [design-sequence-confirm.png](diagrams/c03/design-sequence-confirm.png) | [design-sequence-confirm.puml](diagrams/c03/design-sequence-confirm.puml) |
| Návrhový třídní diagram (H2) | [focused-design-class.png](diagrams/c03/focused-design-class.png) | [focused-design-class.puml](diagrams/c03/focused-design-class.puml) |

### C05 — Detailed design

| Diagram | Obrázek | Zdroj |
|---|---|---|
| Doručování notifikací přes outbox | [c05-notification-outbox.png](diagrams/c05/c05-notification-outbox.png) | [c05-notification-outbox.puml](diagrams/c05/c05-notification-outbox.puml) |

## Code and tests

| Co | Soubor |
|---|---|
| Rezervační služby (OP-01 až OP-05, expirace) | [reservation/services.py](../src/rezervace_divadlo/reservation/services.py) |
| Modely a databázová omezení | [reservation/models.py](../src/rezervace_divadlo/reservation/models.py) |
| Testy rezervací | [reservation/tests.py](../src/rezervace_divadlo/reservation/tests.py), [reservation/tests_concurrency.py](../src/rezervace_divadlo/reservation/tests_concurrency.py) |
| Notifikační outbox a dispatcher | [notification/services.py](../src/rezervace_divadlo/notification/services.py), [notification/dispatcher.py](../src/rezervace_divadlo/notification/dispatcher.py) |
| Testy notifikací | [notification/tests.py](../src/rezervace_divadlo/notification/tests.py) |
| Nastavení (limity, databáze) | [settings.py](../src/rezervace_divadlo/rezervace_divadlo/settings.py) |
