# C08 — Controlled change

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C02 domain rules](C02-Domain-Rules.md) · [C09 release](../evidence-and-evolution/C09-Implementation-CI-Release.md)

## Baseline

Baseline je commit `1e83127680a61b48b276788f273c9b16bda1b4fb` na větvi
`main`. Schéma databáze je tvořeno migracemi `reservation.0001` a
`reservation.0002`; aktuální model používá `Reservation.hold_until` a
`ReservationSeat`. Aplikace běží na Pythonu 3.12+ a Django 6.1.1, databází je
SQLite s `transaction_mode = IMMEDIATE`. Hesla ani jiné tajné hodnoty nejsou
součástí konfigurace pro tento běh.

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

### Acceptance conditions

| ID | Podmínka přijetí |
|---|---|
| AC-01 | Nově vytvořený `DRAFT` má `hold_until` přesně 15 minut od vytvoření. |
| AC-02 | Odeslání kontaktních údajů ani validace držení jeho deadline neprodlouží. |
| AC-03 | V okamžiku `hold_until` je držení odmítnuto, přejde do `EXPIRED` a sedadla se uvolní. |
| AC-04 | Návrat na výběr sedadel zruší pouze vlastní nedokončená držení pro dané představení. |
| AC-05 | Existující potvrzení, schvalování, zrušení, expirace a exkluzivita sedadel zůstanou beze změny. |

AC-01 až AC-04 jsou pozitivní, negativní i hraniční scénáře; AC-05 je
regresní podmínka.

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

## Impact matrix

| Vrstva | Dopad | Odůvodnění a požadovaný důkaz |
|---|---|---|
| Specifikace a stavový model | CHANGE | BR-07 a přechod `DRAFT -> EXPIRED` musí uvádět pevný deadline; důkazem jsou C02 dokumenty a testy. |
| Architektura | CHECK | Vlastník lifecycle zůstává v rezervačních službách; ověřuje se zachování atomických přechodů. |
| Kód | CHANGE | `create_reservation`, `touch_reservation`, expirace a návrat na výběr musí používat serverový `hold_until`. |
| Databáze | CHECK | Stávající `hold_until`, stavové constrainty a migrace `0002` jsou dostatečné; nová migrace není potřeba. |
| API | NO IMPACT | Aplikace nemá veřejné HTTP API; změna je v aplikačních službách a server-renderovaných pohledech. |
| Konfigurace | CHANGE | `RESERVATION_HOLD_MINUTES = 15` je explicitní a pinne se v reprodukovatelném prostředí. |
| Testy | CHANGE | Přidává se důkaz neprodloužení, hranice deadline, persistence a zachování cizího držení. |
| Provoz | CHECK | Expirační management command zůstává spouštěčem; ověří se jeho idempotence. |

## Options matrix

| Varianta | AC | Náročnost | Riziko | Reverzibilita |
|---|---|---:|---|---|
| A — ponechat obnovování držení | Nesplní AC-01 až AC-03 | nízká | dlouhé blokování a nekonzistentní dostupnost | vysoká |
| B — pevný deadline od vytvoření | Splní AC-01 až AC-05 | střední | vyžaduje kontrolu všech kroků a regresní testy | vysoká |
| C — zkrátit držení bez změny pravidla aktivity | Nesplní AC-02 | nízká | uživatel může přijít o rezervaci během formuláře | vysoká |

## Decision

**Status: ACCEPT.** Zvolena je varianta B. Nejmenší delta je zachovat
`hold_until` jako jediný autoritativní deadline, odstranit jeho prodlužování,
ověřit expiraci na hranici a aktualizovat specifikaci, testy a CI. Datový model
a migrace se nemění.

Peer review je připraveno k posouzení spolužákem. Reviewer má zkontrolovat
AC-01 až AC-05, impact matrix, volbu varianty B a návaznost evidence C09;
do provedení review není rozhodnutí označeno jako peer-reviewed.

## C09 entry criteria

C09 musí doložit čistý commit změny, běh testů přes skutečnou SQLite databázi,
automatizovaný příkaz v CI, clean checkout podle README a identifikaci release
candidate včetně omezení rollbacku.
