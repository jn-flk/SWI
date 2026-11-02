# C07 — Vypořádání nálezů, technické argumenty a risk register

## Následné vypořádání nálezů po assessmentu C05

| Oblast | Co bylo provedeno | Konkrétní evidence |
|---|---|---|
| F1 — specifikace a pravidla | C02 operations, pravidla a diagramové zdroje byly sjednoceny s cutoffem 15 minut, předstihem 24 hodin, prioritou schválení celého sálu a obnovou držení. | [`intent-and-change/C02-Operations-and-Requirements.md`](../intent-and-change/C02-Operations-and-Requirements.md) OP-01, OP-01a a OP-03; [`intent-and-change/C02-Domain-Rules-and-Baseline.md`](../intent-and-change/C02-Domain-Rules-and-Baseline.md) BR-07/BR-08; [`activity-op03-confirm.puml`](../diagrams/c02/activity-op03-confirm.puml), [`activity-op01-create.puml`](../diagrams/c02/activity-op01-create.puml), [`state.puml`](../diagrams/c02/state.puml), [`use-case.puml`](../diagrams/c02/use-case.puml) |
| F2 — architektura a evidence | Pohledy C03 a evidence používají transakční outbox a samostatný dispatcher; starý `on_commit` popis je historická baseline. | [`architecture-and-decisions/C03-Architecture-Design.md`](../architecture-and-decisions/C03-Architecture-Design.md); [`design-sequence-confirm.puml`](../diagrams/c03/design-sequence-confirm.puml); [`static-architecture.puml`](../diagrams/c03/static-architecture.puml); [`dispatcher.py`](../../src/rezervace_divadlo/notification/dispatcher.py) |
| F3 — DD a dispatcher | DD popisuje terminální přechod expirovaného lease do `FAILED`; dispatcher započítává úklidová selhání do `counts["failed"]`. | [`architecture-and-decisions/C05-Detailed-Design.md`](../architecture-and-decisions/C05-Detailed-Design.md) — stavový model a pseudokód; [`dispatcher.py`](../../src/rezervace_divadlo/notification/dispatcher.py); [`test_crash_on_last_attempt_becomes_failed_without_another_send`](../../src/rezervace_divadlo/notification/tests.py) |
| C04/Q evidence | Byl doplněn reprodukovatelný příkaz a testovací podklad pro lokální měření dvaceti souběžných pokusů. | [`measure_reservation_concurrency.py`](../../src/rezervace_divadlo/reservation/management/commands/measure_reservation_concurrency.py); [`tests_concurrency.py`](../../src/rezervace_divadlo/reservation/tests_concurrency.py) |
| Confirm diagram | Zdroj a vyrenderovaný obrázek Confirm sekvence byly po architektonické opravě sjednoceny. | [`design-sequence-confirm.puml`](../diagrams/c03/design-sequence-confirm.puml) a [`design-sequence-confirm.png`](../diagrams/c03/design-sequence-confirm.png) |
| Testy Confirm (C06 remaining gap) | Doplněny chybějící testy Confirm s neaktivním sedadlem a souběžného Confirm téže rezervace. | [`test_confirm_with_seat_deactivated_after_create_is_rejected`](../../src/rezervace_divadlo/reservation/tests.py); [`test_concurrent_confirm_has_one_winner_for_one_reservation`](../../src/rezervace_divadlo/reservation/tests_concurrency.py) |
| Diagram OP-02 (zbývající položka C02) | Doplněn diagram aktivit Check Availability podle `check_availability`: validace intervalu, výběr sedadel, test překryvu `[start,end)`, blokující stavy. | [`activity-op02-availability.puml`](../diagrams/c02/activity-op02-availability.puml) a [`activity-op02-availability.png`](../diagrams/c02/activity-op02-availability.png) |

Stav vypořádání:

| Finding | Stav v reporting baseline | Zbývající akce |
|---|---|---|
| F1 | CLOSED pro aktuální reporting baseline. | `touch_reservation` je zachycen v use-case, stavovém, activity a ownership pohledu; implementace je v [`services.py`](../../src/rezervace_divadlo/reservation/services.py) a test obnovy v [`tests.py`](../../src/rezervace_divadlo/reservation/tests.py). |
| F2 | CLOSED pro aktuální architekturu a evidenci. | Udržovat [`architecture-and-decisions/C03-Architecture-Design.md`](../architecture-and-decisions/C03-Architecture-Design.md), diagramy a [`dispatcher.py`](../../src/rezervace_divadlo/notification/dispatcher.py) synchronizované při dalších změnách. |
| F3 | CLOSED pro aktuální implementaci. | Zachovat [`test_crash_on_last_attempt_becomes_failed_without_another_send`](../../src/rezervace_divadlo/notification/tests.py) a při změně dispatcheru znovu ověřit kontrakt počitadla. |


## A — Technické argumenty a evidence aktuální baseline

| Technický argument | Aktuální tvrzení | Evidence | Omezení |
|---|---|---|---|
| Životní cyklus rezervace a exkluzivita sedadel | Create atomicky zablokuje vybraná sedadla; Confirm provede přímé potvrzení nebo odešle rezervaci ke schválení; Cancel, Reject a Expire uvolní aktivní alokace a zachovají historii. | `reservation/services.py`, `reservation/models.py`, `docs/intent-and-change/C02-Operations-and-Requirements.md`, `docs/intent-and-change/C02-Domain-Rules-and-Baseline.md`, testy `reservation`. | Ověření probíhá přes aplikační služby, nikoli přes HTTP API; API není součástí aktuálního projektu. |
| Schvalovací a časová pravidla | Hranice 10 sedadel, priorita celého sálu, cutoff 15 minut, předstih 24 hodin a pětiminutové obnovitelné držení jsou implementované a ověřené na hranicích. | OP-01, OP-01a a OP-03 v `docs/intent-and-change/C02-Operations-and-Requirements.md`, pravidla v `docs/intent-and-change/C02-Domain-Rules-and-Baseline.md`, testy časových hranic a obnovy držení. | Důkaz je z lokální testovací databáze; není to důkaz produkčního nasazení. |
| Notifikační integrace | Rezervační přechod zapíše neměnný outbox snapshot ve stejné transakci; samostatný dispatcher provádí claim, doručení, retry, backoff a fencing. | `docs/architecture-and-decisions/`, `docs/diagrams/c03/`, `notification/services.py`, `notification/dispatcher.py`, testy `notification`. | Externí doručení je zastoupeno adaptérem nebo test double; skutečný externí receiver není součástí baseline. |
| Lokální souběh rezervací | Měření 20 workerů v 5 kolech vytvořilo 5 vítězných alokací, zaznamenalo 95 konfliktů, 0 `busy`, medián latence 201,14 ms a propustnost 19,6 pokusu/s. | `measure_reservation_concurrency --workers 20 --rounds 5` po migraci lokální SQLite databáze. | Výsledek platí pouze pro deklarovaný lokální workload a SQLite; není kapacitní garancí pro produkční databázi. |
| Souběh Confirm a neaktivní sedadlo | Dvě souběžná potvrzení téže rezervace skončí právě jedním úspěchem (druhé `invalid_state` / `busy`) a jednou aktivní alokací; Confirm s později deaktivovaným sedadlem je odmítnut a rezervace zůstane `DRAFT`. | `tests_concurrency.py`, `tests.py` (viz běh níže). | Souběh je ověřen dvěma vlákny nad SQLite (`transaction_mode = IMMEDIATE`), ne nad produkční databází. |
| Aktuální verifikace | Aktuální větev má 50 testů (24 reservation + 2 concurrency + 24 notification); všechny prošly a `manage.py check` nehlásí chyby. | `python src/rezervace_divadlo/manage.py test notification reservation`; záznam běhu níže. | Nejsou plně ověřené migrace existujících dat, produkční recovery ani externí doručení. |

### Ověřovací běh aktuální baseline

- Datum: 1. 11. 2026; větev `c08-verification` nad `ca2a9c5` (PR #18)
  + doplněné testy Confirm a diagram OP-02.
- Reporting commit / tag: doplnit po commitu (návrh: tag `C08`).
- Prostředí: Python 3.11.9, Django 5.2.18, SQLite.

```text
> python manage.py check
System check identified 6 issues (0 silenced).   # 6× models.W042 (Django 5.2), 0 chyb

> python manage.py test notification reservation
Found 50 test(s).
Ran 50 tests in 0.426s
OK
```

Celá sada byla spuštěna pětkrát po sobě se shodným výsledkem (souběžné testy
nejsou nestabilní). Varování `models.W042` vzniká pouze na Django 5.2;
projekt cílí na Django 6 (Python ≥ 3.12), na kterém tento běh proveden nebyl.

## B — Risk register aktuální baseline

Následující rizika jsou samostatná od historických findings F1–F3. Likelihood
a impact používají stupnici 1–3; priorita je `L × I` podle matice C07/C08
(1–2 LOW, 3–4 MEDIUM, 6–9 HIGH). Skutečné reziduální
riziko je `NOT VERIFIED`, dokud není doložena účinnost opatření.

### R-01 — Přenositelnost SQLite concurrency

- **Kategorie:** Technická / výkonová
- **Příčina → nejistá událost → důsledek:** SQLite serializuje zápisy; produkční
  workload nebo databázový engine se bude chovat jinak než lokální měření;
  vzroste latence, lock contention nebo počet odmítnutých požadavků.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH. L2: produkční databáze ani
  workload nejsou zvolené a SQLite zamyká celou databázi, takže rozdíl je
  reálný; I3: souběh rezervací je kritický scénář BR-02 a C04.
- **Response:** MITIGATE — zachovat reprodukovatelné lokální měření a před
  volbou produkční databáze definovat workload a prahové hodnoty.
- **Opatření / vlastník / termín:** HAH; zapsat workload, limity a další
  měření před příštím CP1 review.
- **Důkaz účinnosti:** 20 workerů × 5 kol: 0 `busy`, medián 201,14 ms,
  propustnost 19,6 pokusu/s; souběžné testy Create a Confirm procházejí
  (viz ověřovací běh v části A). Vše pouze nad lokální SQLite.
- **Očekávané reziduum:** 1 / 3 / MEDIUM.
- **Skutečné reziduum:** NOT VERIFIED pro produkční databázi.
- **Trigger / contingency / další review:** `busy` nebo latence nad limitem;
  vyhodnotit PostgreSQL či jinou strategii zamykání; review při CP1.
- **Rozhodnutí:** Přijmout omezení pouze pro lokální baseline; vlastník HAH.

### R-02 — Duplicity při at-least-once notifikacích

- **Kategorie:** Integrace / spolehlivost
- **Příčina → nejistá událost → důsledek:** Worker selže po přijetí zprávy
  externím receiverem, ale před uložením `SENT`; retry doručí duplicitu.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH. L2: at-least-once doručení
  duplicitu při pádu mezi odesláním a zápisem `SENT` z principu připouští
  a chování receiveru není známé; I3: duplicitní nebo rozporné oznámení
  o stavu rezervace (např. dvojí žádost o schválení) narušuje kritický scénář.
- **Response:** MITIGATE — zachovat stabilní ID zprávy a `Idempotency-Key`;
  vyžadovat deduplikaci na straně receiveru.
- **Opatření / vlastník / termín:** vlastník notifikační integrace; zdokumentovat
  a ověřit idempotenci receiveru před externí integrací.
- **Důkaz účinnosti:** test HTTP adaptéru ověřuje stabilní idempotency key;
  deduplikace skutečného receiveru ověřena není.
- **Očekávané reziduum:** 1 / 2 / LOW.
- **Skutečné reziduum:** NOT VERIFIED.
- **Trigger / contingency / další review:** duplicita nebo receiver bez
  idempotence; pozastavit doručování či provést reconciliaci podle ID.
- **Rozhodnutí:** Přijmout dočasně do uzavření kontraktu receiveru; vlastník HAH.

### R-03 — Dostupnost dispatcheru a expiry workeru

- **Kategorie:** Provozní
- **Příčina → nejistá událost → důsledek:** Dispatcher nebo expiry command
  neběží, zpozdí se nebo ztratí lease; doručení a persistované `EXPIRED`
  přechody se zpozdí.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH. L2: oba workery se spouštějí
  ručně jako `--watch` procesy bez supervize a restart policy; I3: bez nich
  se nedoručují notifikace a propadlé rezervace se nepřevádějí do `EXPIRED`.
- **Response:** MITIGATE — používat management commands s `--watch`, sledovat
  výstup a zachovat lease recovery a retry.
- **Opatření / vlastník / termín:** provozní vlastník; definovat supervision,
  restart policy a alert thresholds před nasazením.
- **Důkaz účinnosti:** testy commandů, lease recovery a retry procházejí;
  dlouhý běh ani restart drill proveden nebyl.
- **Očekávané reziduum:** 1 / 2 / LOW.
- **Skutečné reziduum:** NOT VERIFIED.
- **Trigger / contingency / další review:** stale `PENDING` nebo overdue hold;
  restart workeru a one-shot recovery; review při operational readiness.
- **Rozhodnutí:** Přijmout pouze pro development baseline; produkční provoz
  vyžaduje doplnění supervision evidence.

### R-04 — Migrace existujících dat

- **Kategorie:** Data / migrace
- **Příčina → nejistá událost → důsledek:** Migrace `0002` převádí staré
  rezervace do více-sedadlového modelu, ale nebyla provedena fixture-based
  zkouška reprezentativní staré databáze; může vzniknout ztráta dat nebo
  nesprávná aktivní alokace.
- **Počáteční L / I / priorita:** 2 / 3 / HIGH. L2: migrace `0002` mění
  strukturu dat (jedno sedadlo → `ReservationSeat`) a nebyla zkoušena na
  reprezentativních datech; I3: ztráta nebo chybná aktivní alokace porušuje
  BR-02 a zachování historie rezervací.
- **Response:** MITIGATE — vytvořit legacy fixture, provést forward migration,
  ověřit rezervace i alokace a zachovat backup.
- **Opatření / vlastník / termín:** vlastník persistence; provést rehearsal
  před použitím existující databáze.
- **Důkaz účinnosti:** existují migrační soubory a požadavek na backup;
  fixture-based rehearsal doložen není.
- **Očekávané reziduum:** 1 / 2 / LOW.
- **Skutečné reziduum:** NOT VERIFIED.
- **Trigger / contingency / další review:** nesoulad počtů nebo kontrol migrace;
  obnovit backup a zastavit rollout; review před data-bearing deploymentem.
- **Rozhodnutí:** Pro produkční rollout zatím nepřijmout; vlastník HAH.
