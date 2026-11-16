# C08 — Controlled change

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C02 domain rules](C02-Domain-Rules.md) · [C09 release](../evidence-and-evolution/C09-Implementation-CI-Release.md)

## Baseline

Baseline je commit `1e83127680a61b48b276788f273c9b16bda1b4fb` na větvi
`main`. Schéma databáze je tvořeno migracemi `reservation.0001` a
`reservation.0002`; aktuální model používá `Reservation.hold_until` a
`ReservationSeat`. Aplikace běží na Pythonu 3.12+ a Django 6.1.1, databází je
SQLite s `transaction_mode = IMMEDIATE`. Konfigurace obsahuje
`RESERVATION_HOLD_MINUTES = 5`. Hesla ani jiné tajné hodnoty nejsou součástí
konfigurace pro tento běh.

Výchozí testovací příkaz je:

```powershell
python -m pip install -r requirements.txt
python src\rezervace_divadlo\manage.py migrate
python src\rezervace_divadlo\manage.py test notification reservation
```

## Change request

### Need

Původní průchod rezervací mohl prodlužovat držení aktivitou uživatele. To
zvyšuje dobu blokování sedadel bez nové obchodní události a činí dostupnost
závislou na počtu kroků ve formuláři. Potřebujeme pevně ohraničit dobu držení
od jeho vytvoření a zachovat možnost ověřit platnost držení v dalších krocích.

### Previous behavior

`DRAFT` drží sedadla 5 minut. Každé volání `touch_reservation` nastaví
`hold_until = min(now + 5 min, začátek představení)`, takže aktivita deadline
posouvá.

### Acceptance conditions

| ID | Podmínka přijetí |
|---|---|
| AC-01 | Nově vytvořený `DRAFT` má `hold_until` přesně 15 minut od vytvoření (dříve 5 minut). |
| AC-02 | Odeslání kontaktních údajů ani validace držení jeho deadline neprodlouží. |
| AC-03 | V okamžiku `hold_until` je držení odmítnuto, přejde do `EXPIRED` a sedadla se uvolní. |
| AC-04 | Návrat na výběr sedadel zruší pouze vlastní nedokončená držení pro dané představení. |
| AC-05 | Existující potvrzení, schvalování, zrušení, expirace a exkluzivita sedadel zůstanou beze změny. |

AC-01 až AC-04 jsou pozitivní, negativní i hraniční scénáře; AC-05 je
regresní podmínka.

### Out of scope

Schvalování (`PENDING_APPROVAL`), notifikační outbox, intervalová sémantika,
databázové schéma a migrace se nemění.

## Baseline test cases

Očekávání byla zapsána před spuštěním. Oba případy používají Django test runner
nad skutečnou SQLite persistencí.

### TC-01 — Activity does not extend a hold

1. Vytvořit představení a volné sedadlo.
2. V čase `t0` vytvořit rezervaci ve stavu `DRAFT`.
3. Uložit původní `hold_until = t0 + 15 min`.
4. V čase uprostřed intervalu zavolat [`touch_reservation`](../../src/rezervace_divadlo/backend/reservation/services.py)
   pro validaci držení bez jeho prodloužení.
5. Načíst rezervaci z databáze.

**Očekávání před během:** stav zůstane `DRAFT` a `hold_until` bude přesně
původní deadline, nikoli `t0 + 19 min`.

**Výsledek:** PASS, ověřeno testem
[`test_activity_does_not_extend_hold_and_expiration_is_idempotent`](../../src/rezervace_divadlo/backend/reservation/tests.py).
Test používá polovinu hodnoty `RESERVATION_HOLD_MINUTES`; při aktuální
konfiguraci je to 7 minut a 30 sekund. Odeslání kontaktních údajů je navíc
ověřeno testem
[`test_submitting_contact_details_keeps_fixed_hold`](../../src/rezervace_divadlo/backend/reservation/tests_views.py).

### TC-02 — Deadline expires and releases the seat

1. Vytvořit `DRAFT` s jedním sedadlem.
2. Nastavit řízený čas přesně na hodnotu `hold_until`.
3. Pokusit se rezervaci potvrdit.
4. Načíst rezervaci a její alokaci z databáze.
5. Spustit expiraci znovu se stejným časem.

**Očekávání před během:** potvrzení bude odmítnuto jako `expired`, stav bude
`EXPIRED`, aktivní alokace nebude existovat a druhá expirace nezmění výsledek.

**Výsledek:** PASS, ověřeno testem
`test_confirm_at_hold_deadline_expires_reservation`.

### Test runs

| Commit | Prostředí | Příkaz | Výsledek | Evidence |
|---|---|---|---|---|
| `54de0e2` (before) | Windows, venv, Python 3.12, Django 6.1.1 | `python src/rezervace_divadlo/manage.py test notification reservation` | `Ran 68 tests`, `OK` | Spustil Honza; Spustil Honza 2026-11-04. |
| `06e7a87` (after, kód shodný s `a355983`) | Windows, venv, Python 3.12, Django 6.1.1 | `python src/rezervace_divadlo/manage.py test notification reservation` | `Ran 68 tests`, `OK` | Spustil Honza 2026-11-15; výstup v [C09](../evidence-and-evolution/C09-Implementation-CI-Release.md#test-run). |
| pracovní strom nad `be0b3be` (C10, rozšířená sada testů, produkční kód beze změny) | Linux, venv, Python 3.14.10, Django 6.1.2 | `python src/rezervace_divadlo/manage.py test notification reservation` | `Ran 77 tests`, `OK` | Spuštěno 2026-11-16; výstup v [C09](../evidence-and-evolution/C09-Implementation-CI-Release.md#re-verification-with-extended-tests). Prostředí neodpovídá uzamčenému `requirements.txt`; běh CI s Pythonem 3.12 a Django 6.1.1: NOT VERIFIED. |

## Impact matrix

| Vrstva | Dopad | Odůvodnění | Nutná akce | Důkaz |
|---|---|---|---|---|
| Specifikace a stavový model | CHANGE | BR-07 a přechod `DRAFT -> EXPIRED` musí uvádět pevný deadline. | Upravit BR-07 v C02. | [C02 domain rules](C02-Domain-Rules.md), AC-01 až AC-03 |
| Architektura | CHECK | Vlastník lifecycle zůstává v rezervačních službách. | Ověřit zachování atomických přechodů. | `reservation/tests_concurrency.py` |
| Kód | CHANGE | `create_reservation`, `touch_reservation`, expirace a návrat na výběr musí používat serverový `hold_until`. | Odstranit prodlužování, přidat `release_draft_reservations`. | Testy AC-01 až AC-04 |
| Databáze | CHECK | Stávající `hold_until`, stavové constrainty a migrace `0002` jsou dostatečné. Staré `DRAFT` záznamy mají `hold_until` podle 5minutového pravidla a vyprší nejpozději 5 minut po nasazení. | Žádná migrace. | Migrace beze změny |
| API | NO IMPACT | Aplikace nemá veřejné HTTP API; změna je v aplikačních službách. | — | — |
| Konfigurace | CHANGE | `RESERVATION_HOLD_MINUTES` se mění z 5 na 15 a pinne se v reprodukovatelném prostředí. | Upravit `settings.py`, pinnout Django v `requirements.txt`. | `settings.py`, `requirements.txt` |
| Testy | CHANGE | Přidává se důkaz neprodloužení, hranice deadline, persistence a zachování cizího držení. | Nahradit test prodlužování, přidat nové testy. | [C09 testy](../evidence-and-evolution/C09-Implementation-CI-Release.md) |
| Provoz | CHECK | Expirační management command zůstává spouštěčem. | Ověřit idempotenci expirace. | `test_activity_does_not_extend_hold_and_expiration_is_idempotent` |

## Options matrix

| Varianta | AC | Náročnost | Riziko | Reverzibilita | Jak ověříme |
|---|---|---:|---|---|---|
| A — ponechat obnovování držení | Nesplní AC-01 až AC-03 | nízká | dlouhé blokování a nekonzistentní dostupnost | vysoká | Stávající test prodlužování |
| B — pevný deadline od vytvoření | Splní AC-01 až AC-05 | střední | vyžaduje kontrolu všech kroků a regresní testy | vysoká | Testy AC-01 až AC-04, regrese TC-02 a souběhu |
| C — zkrátit držení bez změny pravidla aktivity | Nesplní AC-02 | nízká | uživatel může přijít o rezervaci během formuláře | vysoká | Test aktivity s kratší lhůtou |

## Decision

**Status: ACCEPT.** Zvolena je varianta B. Nejmenší delta je zachovat
`hold_until` jako jediný autoritativní deadline, odstranit jeho prodlužování,
ověřit expiraci na hranici a aktualizovat specifikaci, testy a CI. Datový model
a migrace se nemění.


## C09 handoff

| Předávka | Hodnota |
|---|---|
| **Before** | Commit `54de0e2`, BR-07 (5 minut, obnovování aktivitou), TC-01 a TC-02 |
| **Accepted** | Varianta B: pevný deadline 15 minut od vytvoření `DRAFT` |
| **Change** | `touch_reservation` bez prodloužení, `RESERVATION_HOLD_MINUTES = 15`, `release_draft_reservations` |
| **New test basis** | AC-01 až AC-04: 15 minut od vytvoření, aktivita neprodlouží, odmítnutí přesně v `hold_until`, návrat ruší jen vlastní hold |
| **Regression** | TC-02, potvrzení, schvalování, zrušení, souběh (`tests_concurrency.py`) |
| **Risk** | Staré `DRAFT` záznamy při nasazení doběhnou podle 5minutového deadline. |
| **C09 work** | Commit změny, běh testů přes skutečnou SQLite databázi, CI, clean checkout podle README, release candidate včetně omezení rollbacku |
