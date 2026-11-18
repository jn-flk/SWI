# C10 — Logging Detail

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C05 Detailed Design](C05-Detailed-Design.md)

Přehled všech logovacích záznamů, které aplikace zapisuje: kde vznikají,
proč a s jakou úrovní.

## Format and storage

- **Formát:** `čas ÚROVEŇ logger operation=… <identifikátory> failure=… detail=… outcome=…`.
  Každý záznam tak obsahuje čas, komponentu (název loggeru), operaci, typ
  problému a pozorovaný výsledek.
- **Úložiště:** soubor `src/rezervace_divadlo/app.log`, nastavení v `LOGGING` v
  [settings.py](../../src/rezervace_divadlo/backend/config/settings.py).

## Loggers

| Logger | Minimální úroveň | Část aplikace |
|---|---|---|
| `config.startup` | INFO | start aplikace a kontrola konfigurace |
| `reservation.services` | WARNING | rezervační služby (doménová zamítnutí se nelogují) |
| `notification.dispatcher` | INFO | dispatcher a odesílací adaptéry |
| `django.request` | ERROR | neošetřené výjimky (HTTP 500) i při `DEBUG=False` |

## Log catalog

| # | Úroveň | Logger | Co loguje | Kde v kódu |
|---|---|---|---|---|
| L-01 | INFO | `config.startup` | Start aplikace (commit, režim, databáze, odesílač notifikací). | [`log_startup`](../../src/rezervace_divadlo/backend/config/startup.py) |
| L-02 | ERROR | `config.startup` | Neexistující třída odesílače notifikací. | [`_check_notification_sender`](../../src/rezervace_divadlo/backend/config/startup.py) |
| L-03 | ERROR | `config.startup` | Chybějící URL notifikační služby. | [`_check_notification_sender`](../../src/rezervace_divadlo/backend/config/startup.py) |
| L-04 | ERROR | `reservation.services` | Neočekávané porušení integrity dat. | `_atomic_operation` v [services.py](../../src/rezervace_divadlo/backend/reservation/services.py) |
| L-05 | ERROR | `reservation.services` | Technická chyba databáze (např. nedostupná DB). | `_atomic_operation` v [services.py](../../src/rezervace_divadlo/backend/reservation/services.py) |
| L-06 | WARNING | `reservation.services` | Zamčená databáze, požadavek odmítnut. | `_atomic_operation` v [services.py](../../src/rezervace_divadlo/backend/reservation/services.py) |
| L-07 | WARNING | `notification.dispatcher` | Neúspěšný pokus o odeslání notifikace, bude zopakován. | [`dispatch_notifications`](../../src/rezervace_divadlo/backend/notification/dispatcher.py) |
| L-08 | ERROR | `notification.dispatcher` | Notifikace definitivně selhala. | [`dispatch_notifications`](../../src/rezervace_divadlo/backend/notification/dispatcher.py) |
| L-09 | WARNING | `notification.adapters` | Pomalá odpověď notifikační služby. | `HttpSender.send` v [adapters.py](../../src/rezervace_divadlo/backend/notification/adapters.py) |
| L-10 | INFO | `notification.adapters` | Notifikace zapsaná lokálně do logu (vývoj). | `LoggingSender.send` v [adapters.py](../../src/rezervace_divadlo/backend/notification/adapters.py) |
| L-11 | ERROR | `django.request` | Neošetřená výjimka při požadavku (HTTP 500). | `LOGGING` v [settings.py](../../src/rezervace_divadlo/backend/config/settings.py) |
