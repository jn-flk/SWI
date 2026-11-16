# C09 — Implementation, CI and release

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C08 change](../intent-and-change/C08-Controlled-Change.md) · [C07 risk register](C07-Technical-Review-and-Risk-Register.md)

## Before and after

| Položka | Hodnota |
|---|---|
| **C08 Change Card** | [C08 — Controlled change](../intent-and-change/C08-Controlled-Change.md), rozhodnutí ACCEPT, varianta B |
| **Before** | `54de0e2` |
| **After** | `a355983` (sloučeno v PR #20, merge commit `c99af28`) |
| **Dokumentace a CI** | `06e7a87`; kód v `src/` je shodný s `a355983` |

## Implementation delta

C09 přebírá rozhodnutí C08, variantu B. Změna se týká pevného `hold_until` od
vytvoření `DRAFT`, validace bez prodloužení, expirace a návratu vlastníka na
výběr sedadel. Kód je v `reservation/services.py` a pohledech rezervace;
regresní testy jsou v `reservation/tests.py` a `reservation/tests_views.py`.

Nedotčené zůstávají schvalování, zrušení, notifikační outbox, intervalová
sémantika, databázové constrainty a migrace. Nová migrace není nutná.


## Verification

| Test ID | Accepted oracle | Test | Expected | Actual | Verdict | Evidence |
|---|---|---|---|---|---|---|
| AC-01 | `hold_until` = vytvoření + `RESERVATION_HOLD_MINUTES` (15) | `test_activity_does_not_extend_hold_and_expiration_is_idempotent` | Expirace přesně v čase vytvoření + 15 min, ne o sekundu dříve | Prošel | PASS | [Test run](#test-run) |
| AC-02 | Aktivita deadline neprodlouží | `test_activity_does_not_extend_hold_and_expiration_is_idempotent` | Validace v polovině lhůty nezmění `hold_until` | Prošel | PASS | [Test run](#test-run) |
| AC-02 | Odeslání kontaktních údajů deadline neprodlouží | `test_submitting_contact_details_keeps_fixed_hold` | `hold_until` po uložení beze změny | Prošel | PASS | [Test run](#test-run) |
| AC-03 | Odmítnutí přesně v `hold_until` | `test_confirm_at_hold_deadline_expires_reservation` | `expired`, stav `EXPIRED`, žádná aktivní alokace | Prošel | PASS | [Test run](#test-run) |
| AC-04 | Návrat ruší vlastní hold | `test_returning_to_seat_selection_releases_own_active_hold` | Vlastní `DRAFT` zrušen, sedadla volná | Prošel | PASS | [Test run](#test-run) |
| AC-04 | Návrat zachová cizí hold | `test_returning_to_seat_selection_keeps_other_users_hold` | Cizí `DRAFT` beze změny | Prošel | PASS | [Test run](#test-run) |
| C08 TC-01 | Aktivita deadline neprodlouží | `test_activity_does_not_extend_hold_and_expiration_is_idempotent` | Viz [C08 TC-01](../intent-and-change/C08-Controlled-Change.md) | Prošel | PASS | [Test run](#test-run) |
| C08 TC-02 | Expirace na deadline uvolní sedadla | `test_confirm_at_hold_deadline_expires_reservation` | Viz [C08 TC-02](../intent-and-change/C08-Controlled-Change.md) | Prošel | PASS | [Test run](#test-run) |
| AC-05 | O stejné sedadlo nebo přechod soupeří jeden vítěz | `reservation/tests_concurrency.py` | Právě jeden úspěch | Prošel | PASS | [Test run](#test-run) |

### Test run

Spustil Honza 2026-11-15 na commitu `06e7a87`, Windows, venv, Python 3.12,
Django 6.1.1:

```text
python src/rezervace_divadlo/manage.py test notification reservation
Found 68 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
Ran 68 tests in 2.121s

OK
Destroying test database for alias 'default'...
```


## Integration boundary

Testy používají Django test runner a skutečnou izolovanou SQLite databázi
vytvořenou test runnerem; nejde o mock persistence. Po každé operaci se stav
znovu čte z databáze (`refresh_from_db`, dotazy na aktivní alokace).
`reservation/tests_concurrency.py` používá `TransactionTestCase` a souběžná
databázová spojení.

## CI

Jeden reprodukovatelný příkaz pro lokální ověření je:

```powershell
python -m pip install -r requirements.txt
python src\rezervace_divadlo\manage.py migrate --noinput
python src\rezervace_divadlo\manage.py check
python src\rezervace_divadlo\manage.py test notification reservation
```

Stejný postup běží v [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
na Pythonu 3.12 při každém pushi a pull requestu. Instalace je uzamčena v
`requirements.txt`.

## Clean checkout

V novém adresáři bez lokálních souborů autora:

```powershell
git clone https://github.com/jn-flk/SWI.git
cd SWI
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\rezervace_divadlo\manage.py migrate --noinput
python src\rezervace_divadlo\manage.py check
python src\rezervace_divadlo\manage.py test notification reservation
```

Výsledkem je databáze vytvořená migracemi a testovací databáze vytvořená
Djangem. Produkční `db.sqlite3` ani demo data nejsou pro ověření potřeba.

## Release candidate

Lokální release-candidate ověření proběhlo na Pythonu 3.12.10 a Django 6.1.1:

```text
python src\rezervace_divadlo\manage.py migrate --noinput
System check identified no issues (0 silenced).
Found 68 test(s).
Ran 68 tests in 3.840s
OK
```

Lokální výsledek je **READY**, protože všechny požadované důkazy
jsou reprodukovatelné; peer review C08 zůstává jediným otevřeným hodnocením.

### Re-verification with extended tests

Dodatek z 16. 11. 2026 (C10). Výše uvedený záznam pro `06e7a87` platí
beze změny. Po vydání přibylo 9 testů funkce Create (`create_reservation`),
odvozených z jejího detailního návrhu v
[C05](../architecture-and-decisions/C05-Detailed-Design.md#create-reservation--detailed-design).
Produkční kód se nezměnil; změněn je pouze `reservation/tests.py`.
AC-01 má nově přímý test `test_new_draft_holds_seats_exactly_fifteen_minutes`.
Ten na rozdíl od původního testu odhalí i návrat konfigurace na 5 minut.

Spuštěno nad pracovním stromem větve `c10-after-presentation-doc-revision`
(základ `be0b3be`), Linux, Python 3.14.10, Django 6.1.2. Místo `migrate`
byly použity kontroly bez zápisu do lokální databáze:

```text
python src/rezervace_divadlo/manage.py migrate --check          # exit 0
python src/rezervace_divadlo/manage.py makemigrations --check --dry-run
No changes detected
python src/rezervace_divadlo/manage.py check
System check identified no issues (0 silenced).
python src/rezervace_divadlo/manage.py test notification reservation
Found 77 test(s).
Ran 77 tests in 2.176s
OK
```

Výsledek zůstává **READY**: schéma ani migrace se nemění a rozšířená sada
prochází. Prostředí neodpovídá uzamčenému `requirements.txt` (Python 3.12,
Django 6.1.1); běh CI v uzamčeném prostředí je NOT VERIFIED, dokud nebude
změna pushnuta.

Schéma zůstává na migracích `reservation.0001` a `reservation.0002`.
Rollback nevyžaduje migraci: návrat na předchozí commit obnoví původní kód,
ale může znovu povolit obnovování držení, proto se musí vrátit i odpovídající
specifikace a testy. CI je povinný automatizovaný krok a spustí se při pushi nebo pull requestu.
