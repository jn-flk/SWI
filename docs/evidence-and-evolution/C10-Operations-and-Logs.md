# C10 — Operations and logs

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C10 logging detail](../architecture-and-decisions/C10-Logging-Detail.md)

Ověření čtyř provozních situací na lokální instanci s testovacími daty.
Seznam všech logovacích záznamů (L-01 až L-12) je v
[C10 Logging Detail](../architecture-and-decisions/C10-Logging-Detail.md).


## Results

| Situace | Očekávaný a skutečný výsledek | Jak jste správnost ověřili | Co ukazují logy / je log potřeba? |
|---|---|---|---|
| **Úspěšné potvrzení** | **Očekávaný:** rezervace přejde z `DRAFT` do `CONFIRMED`, vybraná sedadla zůstanou blokovaná, aplikace zobrazí stránku úspěchu.<br>**Skutečný:** odpovídá | Stránka úspěchu v aplikaci; v adminu stav `CONFIRMED` a aktivní alokace (`ReservationSeat`) vybraných sedadel. | Log **není potřeba** a nevznikl.  |
| **Zamítnutá kolize** | **Očekávaný:** druhý uživatel nezíská sedadla blokovaná rezervací prvního, rezervace prvního se nezmění.<br>**Skutečný:** odpovídá | Dva různé účty ve dvou prohlížečích. | Log **není potřeba** a nevznikl. |
| **Technická porucha a obnova** | **Očekávaný:** při databázi jen pro čtení potvrzení selže (HTTP 500), transakce se vrátí a rezervace zůstane `DRAFT`. Po obnově a kontrole stavu lze rezervaci potvrdit.<br>**Skutečný:** odpovídá | Databáze nastavena jen pro čtení (`chmod 444`), po pokusu obnovena (`chmod 644`). Před opakováním ověřen stav `DRAFT` v adminu, teprve potom znovu potvrzeno. | Log **je potřeba**. |
| **Restart aplikace** | **Očekávaný:** po zastavení (Ctrl+C) a novém spuštění zůstane potvrzená rezervace `CONFIRMED` a další rezervace projde. V logu bude start (L-01), zastavení (L-12) a nový start se stejným commitem.<br>**Skutečný:** odpovídá. | Stav rezervace 13 před a po restartu dotazem do databáze; server zastaven Ctrl+C; po novém startu přihlášení, výběr sedadla, kontaktní údaje a potvrzení přes HTTP, výsledek stránka úspěchu a `CONFIRMED` v databázi. | Log **ukazuje průběh restartu**. |

## Log excerpts

Jen relevantní řádky z `app.log`; tracebacky z `django.request` jsou zkrácené.

### Technical failure

```text
2026-11-18 11:43:55,529 ERROR reservation.services operation=confirm_reservation failure=OperationalError detail=attempt to write a readonly database outcome=rolled_back
2026-11-18 11:43:55,564 ERROR django.request Internal Server Error: /reservations/14/summary/
2026-11-18 11:46:07,387 ERROR reservation.services operation=confirm_reservation failure=OperationalError detail=attempt to write a readonly database outcome=rolled_back
2026-11-18 11:46:07,418 ERROR django.request Internal Server Error: /reservations/15/summary/
2026-11-18 11:46:16,057 ERROR django.request Internal Server Error: /admin/login/
  ... request.session.flush() ... django.db.utils.OperationalError: attempt to write a readonly database
2026-11-18 11:48:07,754 ERROR reservation.services operation=confirm_reservation failure=OperationalError detail=attempt to write a readonly database outcome=rolled_back
2026-11-18 11:48:07,783 ERROR django.request Internal Server Error: /reservations/16/summary/
```

### Application restart

```text
2026-11-18 12:05:09,815 INFO config.startup operation=app_start pid=42274 commit=1dbaa65 debug=True database=sqlite3 notification_sender=LoggingSender outcome=started
2026-11-18 12:05:11,857 INFO config.startup operation=app_stop pid=42274 uptime=2s outcome=stopped
2026-11-18 12:05:13,597 INFO config.startup operation=app_start pid=42280 commit=1dbaa65 debug=True database=sqlite3 notification_sender=LoggingSender outcome=started
2026-11-18 12:05:15,887 INFO config.startup operation=app_stop pid=42280 uptime=2s outcome=stopped
```
