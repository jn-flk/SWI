# C09 — Implementation, CI and release

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C08 change](../intent-and-change/C08-Controlled-Change.md) · [C07 risk register](C07-Technical-Review-and-Risk-Register.md)

## Implementation delta

C09 přebírá rozhodnutí C08, variantu B. Změna se týká pevného `hold_until` od
vytvoření `DRAFT`, validace bez prodloužení, expirace a návratu vlastníka na
výběr sedadel. Kód je v `reservation/services.py` a pohledech rezervace;
regresní testy jsou v `reservation/tests.py` a `reservation/tests_views.py`.

Nedotčené zůstávají schvalování, zrušení, notifikační outbox, intervalová
sémantika, databázové constrainty a migrace. Nová migrace není nutná.

## Verification scenarios

| Scénář | Očekávaný výsledek | Důkaz |
|---|---|---|
| Vytvoření `DRAFT` | `hold_until` je 15 minut od `created_at`. | `test_create_confirm_cancel_preserves_history_and_releases_seats` |
| Aktivita po čtyřech minutách | Deadline zůstane stejný. | `test_activity_does_not_extend_hold_and_expiration_is_idempotent` |
| Odeslání kontaktních údajů | Deadline zůstane stejný i po persistenci. | `test_submitting_contact_details_keeps_fixed_hold` |
| Přesný deadline | Rezervace je `EXPIRED`, aktivní alokace neexistuje. | `test_confirm_at_hold_deadline_expires_reservation` |
| Návrat na výběr | Uvolní vlastní hold, cizí hold zachová. | `test_returning_to_seat_selection_releases_own_active_hold`, `test_returning_to_seat_selection_keeps_other_users_hold` |
| Regrese souběhu | O stejné sedadlo nebo přechod soupeří jeden vítěz. | `reservation/tests_concurrency.py` |

Testy používají Django test runner a skutečnou izolovanou SQLite databázi
vytvořenou test runnerem; nejde o mock persistence.

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

Lokální release-candidate ověření proběhlo na Pythonu 3.14.3 a Django 6.1.1:

```text
python src\rezervace_divadlo\manage.py migrate --noinput
System check identified no issues (0 silenced).
Found 68 test(s).
Ran 68 tests in 3.840s
OK
```

Lokální výsledek je **READY**, protože všechny požadované důkazy
jsou reprodukovatelné; peer review C08 zůstává jediným otevřeným hodnocením.

Schéma zůstává na migracích `reservation.0001` a `reservation.0002`.
Rollback nevyžaduje migraci: návrat na předchozí commit obnoví původní kód,
ale může znovu povolit obnovování držení, proto se musí vrátit i odpovídající
specifikace a testy. CI je povinný automatizovaný krok a spustí se při pushi nebo pull requestu.
