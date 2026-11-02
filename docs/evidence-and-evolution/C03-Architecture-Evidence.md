# Evidence C03

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

- domain class — [domain-model.puml](../c03-diagrams/domain-model.puml)
- context — [context.puml](../c03-diagrams/context.puml)
- static architecture — [static-architecture.puml](../c03-diagrams/static-architecture.puml)
- state ownership — [state-ownership.puml](../c03-diagrams/state-ownership.puml)
- runtime/deployment — [runtime-deployment.puml](../c03-diagrams/runtime-deployment.puml)
- design sequence — [design-sequence-confirm.puml](../c03-diagrams/design-sequence-confirm.puml)
- focused design class — [focused-design-class.puml](../c03-diagrams/focused-design-class.puml)

Cross-view issues found/resolved: Ownership přechodů byl doplněn tak, že
Reservation Management rozhoduje o přímém potvrzení a odeslání ke schválení,
Approval Workflow rozhoduje o approve/reject a Expiration Scheduler pouze
spouští expiraci. Sekvence používá jen prvky ze statické architektury.
Runtime mapuje všechny logické prvky do jednoho Django procesu.

| Kontrola | Výsledek |
|---|---|
| C02 ↔ G2: architektura realizuje lifecycle, dostupnost, schválení, expiraci a notifikace | PASS |
| C2 ↔ G2: každá významná odpovědnost má právě jednoho hlavního ownera | PASS |
| G2 ↔ H1: sekvence používá pouze povolené prvky a závislosti | PASS |
| H1 ↔ H2: významné operace mají vlastníka v třídním návrhu | PASS |
| statechart ↔ G3/H1: transition rozhoduje správný owner | PASS |
| G2 ↔ G4: všechny logické prvky jsou namapované do Django procesu | PASS |
| ADR ↔ G2/G4: jedna Django aplikace, ORM/SQLite a constraint jsou viditelné | PASS |

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
[reservation/tests.py](../../src/rezervace_divadlo/reservation/tests.py), která
ověřuje, že import `logging` zůstává izolován v `notifications.py`.

Behaviour verification:

| Ověření | Výsledek | Doklad |
|---|---|---|
| success path — přímé potvrzení | PASS | `test_ten_seats_confirm_directly_but_eleven_require_approval` |
| alternative/failure — expirace držení | PASS | `test_confirm_at_hold_deadline_expires_reservation` |
| alternative/failure — approve/reject | PASS | `test_only_approver_can_decide_and_rejection_releases_seats` |
| relevant boundary/concurrency rule | PARTIAL | 20 Django testů + `manage.py check`; atomická ochrana a constraint jsou ověřeny sekvenční sadou, skutečný paralelní test zatím chybí |

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

Remaining uncertainty / risk: Sada neprokazuje výkon při 20 paralelních
požadavcích ani skutečné doručení a retry externích notifikací. Samostatně
není otestován převod existujících dat migrací `0002`.

Commit/tag: `2c9915b` — `docs: G-M diagrams, test implementation, evidence`;
pozdější dokumentační opravy jsou součástí commitu `699b501`.
