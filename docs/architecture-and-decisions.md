# Architektura a rozhodnutí

## Technologický stack

- **Jazyk:** Python 3
- **Framework:** Django 6.1
- **Databáze:** SQLite (vývojové prostředí) — přes Django ORM
- **Testování:** vestavěný Django `TestCase` (`python manage.py test`)

## Struktura projektu

Jeden Django projekt `rezervace_divadlo` s jednou aplikací: `reservation`.



## Doménový model

Aplikace `reservation` definuje pět doménových modelů a model alokace sedadel:

- **Play** — divadelní hra (název, popis, délka trvání)
- **Hall** — fyzický prostor/sál
- **Seat** — patří k `Hall`; unikátní podle kombinace `(hall, row, number)`
  a obsahuje příznak `is_active`.
- **Performance** — konkrétní uvedení `Play` v daném `Hall` v daný čas (`start_at`)
- **Reservation** — reprezentuje jednu rezervaci pro konkrétní `Performance` a
	může obsahovat jedno nebo více vybraných `Seat`. Jedno sedadlo nesmí být pro
	stejné představení součástí více aktivních rezervací. Rezervace používá
	stavy `DRAFT`, `PENDING_APPROVAL`, `CONFIRMED`, `CANCELLED`, `REJECTED` a
	`EXPIRED`. Aktivní `DRAFT` drží všechna vybraná sedadla po dobu
	`hold_until`; `PENDING_APPROVAL` je blokuje do rozhodnutí nebo vypršení;
	`CONFIRMED` je blokuje trvale pro dané představení; `CANCELLED`,
	`REJECTED` a `EXPIRED` sedadla neblokují.
- **ReservationSeat** — vazba rezervace na sedadlo a představení. Uchovává
  historii sedadel; příznak `active` odlišuje aktuální blokování. Podmíněný
  unikátní constraint dovolí pouze jednu aktivní alokaci pro `(performance, seat)`.

Uživatel nejdříve zobrazí sál a vybere jedno nebo více sedadel. Teprve po
stisku tlačítka pro pokračování s rezervací vznikne jedna `Reservation` pro
všechna vybraná sedadla. Rezervace pro více než deset sedadel je hromadná a
vyžaduje schválení oprávněnou osobou. Rezervace celého sálu schválení vyžaduje
bez ohledu na počet sedadel.



## Klíčová rozhodnutí

| Rozhodnutí | Zdůvodnění |
|---|---|
| Použít Django + Django ORM místo samostatné persistentní vrstvy | Nejrychlejší cesta k funkčnímu a testovatelnému doménovému modelu pro C01; migrace a constrainty v ORM pokrývají naše aktuální potřeby (unikátnostní pravidla) bez nutnosti dalších nástrojů. |
| Použít SQLite pro vývoj | Nulové nastavení, dostatečné pro ověření doménové logiky a spouštění testů lokálně/v CI. Přehodnotíme pro CP1, pokud budeme potřebovat garance pro souběžné zápisy (viz future pressure: 20× souběžných rezervací). |
| Vynutit exkluzivitu podmíněným unikátním constraintem na `ReservationSeat` | Databáze odmítne druhou aktivní alokaci stejného sedadla a představení. Zrušení, zamítnutí a expirace vypnou alokace, ale zachovají historii. Všechny aplikační zápisy procházejí `services.py` v transakci. SQLite používá `BEGIN IMMEDIATE`; zámek spisovatele vzniká před čtením dostupnosti. |
| Jedna Django aplikace (`reservation`) místo rozdělení modelů do více aplikací | Doména je zatím malá (5 modelů); rozdělování by teď přidalo strukturu bez reálného přínosu. Přehodnotíme, pokud aplikace výrazně naroste. |

## Umístění business logiky

`reservation/services.py` obsahuje OP-01 až OP-05, obnovu aktivity a expiraci.
Modely popisují data a databázová omezení. Testy v `reservation/tests.py`
volají služby přímo; reservation nemá HTTP API. `notifications.py` je lokální adaptér
Notification Service, volaný až po potvrzení transakce.

`expire_reservations --watch` zajišťuje časovač. I při jeho zpoždění služby
odmítnou operaci po deadline a dostupnost ignoruje vypršené držení bez
změny stavu. Pro pravidelné přepisování stavu do `EXPIRED` musí časovač běžet.

## Známá omezení (stav k C02)

- Notification Service zatím pouze zapisuje události do lokálního logu;
  externí doručování a jeho retry nejsou implementované.
- SQLite serializuje všechny spisovatele. Současná jednoduchá sada testuje
  hraniční případy sekvenčně; neověřuje paralelní zápisy ani produkční výkon.
- Záznamy C01 migrace zachová jako `CONFIRMED` bez známého vlastníka;
  spravovat je smí uživatel s oprávněním `change_reservation`.
- Návrat migrace více sedadel na původní jednosedadlový model je záměrně
  nepodporovaný, protože by mohl ztratit historii. Před migrací existující
  databáze je třeba zachovat její zálohu.
- Přímé změny stavů či alokací přes ORM obcházejí pravidla služeb;
  aplikace používá pro všechny business operace `services.py`.

## C03 - současná realizace Confirm Reservation

### Sledovaný scénář

| Položka | Hodnota |
|---|---|
| Operace | OP-03 — Confirm Reservation |
| Požadavky | REQ-03, REQ-04 — [operations.md](operations.md) |
| Pravidla | BR-02, BR-04, BR-06, BR-07, BR-08 — [intent_and_change.md](intent_and_change.md) |
| Baseline | v0.2 — [evidence-and-evolution.md](evidence-and-evolution.md) |

Doklady níže uvádějí soubor a funkci/model. [Testy](../src/rezervace_divadlo/reservation/tests.py) byly přečteny, nově se nespouštěly.

### Hlavní průchod scénáře → kód

| Krok scénáře z C02 | Realizace v kódu | Doklad |
|---|---|---|
| Přijmout požadavek a načíst rezervaci. | Přímé volání služby; načtení rezervace a představení v transakci. | [services.py][services]: `confirm_reservation`, `_reservation`, `_atomic_operation` |
| Ověřit oprávnění a platný `DRAFT`. | Kontrola vlastníka/oprávnění, deadline a zdrojového stavu. | [services.py][services]: `_authorize_owner`, `_expire_one`, `confirm_reservation` |
| Ověřit sedadla a předstih. | Aktivní sedadla; více než 10 nebo celý sál vyžaduje schválení. Cutoff 15 min, pro schvalování předstih 24 h. | [services.py][services]: `confirm_reservation`, `_requires_approval`, `_check_lead_time` |
| Změnit a uložit stav. | `CONFIRMED` nebo `PENDING_APPROVAL`; zrušit držení, případně nastavit deadline schválení. Blokování zůstává, kolize se znovu nekontroluje. | [services.py][services]: `_set_status`, `confirm_reservation` |
| Vrátit výsledek. | Vrátit `Reservation`; u schvalovací větve po commitu zalogovat žádost. | [services.py][services]: `confirm_reservation`, `_notify`; [notifications.py][notifications]: `notify` |

### Důležitá chybová větev

| Co říká v0.2 | Kde se podmínka zjistí | Kde se rozhodne výsledek | Co dostane volající |
|---|---|---|---|
| Vypršené držení → odmítnout a nastavit `EXPIRED`. | [services.py][services]: `_expire_one`, `now >= hold_until` | `_set_status` uloží expiraci a uvolní sedadla; `_atomic_operation` vyhodí chybu až po commitu. | `ReservationError("expired", ...)`; expirace zůstane v DB. Test: `test_confirm_at_hold_deadline_expires_reservation`. |

| Specifikace | Implementace | Doklad |
|---|---|---|
| BR-04 uvádí schválení od 5 sedadel; REQ-03 má rozporné hranice. | Schválení nad 10 sedadel nebo pro celý sál. | [services.py][services]: `_requires_approval`; [settings.py][settings]: limit 10; test `test_ten_seats_confirm_directly_but_eleven_require_approval` |
| BR-08 neuvádí přesný předstih. | Alespoň 24 h před začátkem. | [services.py][services]: `_check_lead_time`; [settings.py][settings]: `RESERVATION_APPROVAL_HOURS` |

### Hlavní části implementace

| Část implementace | Typ / obsah | Role v tomto scénáři | Doklad |
|---|---|---|---|
| Rezervační služby | Modul `services.py` | Kontroly, rozhodnutí a transakce. | [services.py][services]: `confirm_reservation` a pomocné funkce |
| Doménové modely | Modul `models.py`: Reservation, ReservationSeat, Seat, Performance, Hall, Play | Stav, vztahy a DB omezení. | [models.py][models] |
| Konfigurace | Modul `settings.py` | Limity politiky a připojení DB. | [settings.py][settings] |
| Notifikace | Modul `notifications.py` | Lokální log události po commitu. | [notifications.py][notifications]: `notify` |

### Stav, změna stavu a pravidlo

| Otázka | Odpověď | Doklad |
|---|---|---|
| Kde je stav trvale uložen? | SQLite: `reservation_reservation` (stav, deadline), `reservation_reservationseat` (blokování). | [models.py][models]: `Reservation`, `ReservationSeat`; [settings.py][settings]: `DATABASES` |
| Kdo rozhoduje a provádí přechod? | `confirm_reservation` rozhoduje, `_set_status` ukládá; `_expire_one` rozhoduje o expiraci. | [services.py][services] |

Pravidlo BR-04: potvrdit pouze platný `DRAFT`.

| Otázka | Odpověď | Doklad |
|---|---|---|
| Kde se zjistí podmínka? | Kontrola deadline, stavu a aktivních sedadel. | [services.py][services]: `_expire_one`, `confirm_reservation` |
| Kde se rozhodne? | `confirm_reservation` zvolí potvrzení, schvalování nebo chybu; `_expire_one` zvolí expiraci. | [services.py][services] |
| Kde se změní stav? | `_set_status` uloží stav; při expiraci vypne alokace. | [services.py][services]: `_set_status` |

BR-02 chrání už Create a DB constraint `unique_active_performance_seat`; Confirm blokování zachovává.

### Relevantní závislosti

| Závislost | Kde se napojuje | Která část zná technické API | Doklad |
|---|---|---|---|
| SQLite přes Django ORM | Načtení, uložení a transakce. | `services.py` používá ORM a `transaction.atomic`; modely definují constrainty. | [services.py][services], [models.py][models], [settings.py][settings] |
| Notification Service — lokální adaptér | `_notify` po commitu při žádosti o schválení nebo expiraci. | `notifications.py` používá logging; vzdálená služba není připojena. | [services.py][services]: `_notify`; [notifications.py][notifications]: `notify` |
| Django auth | Kontrola předaného uživatele a oprávnění. | `services.py`: `is_authenticated`, `is_active`, `has_perm`. | [services.py][services]: `_authorize_owner` |

### AS-IS strukturální diagram

Diagram je ve složce [c03-diagrams/](c03-diagrams/):
[AS-IS — Confirm Reservation (PlantUML)](c03-diagrams/as-is-confirm-reservation.puml).

Obsah modulů viz tabulka hlavních částí. Auth a logging jsou frameworkové závislosti; notifikace se při přímém potvrzení nevolá.

### Otázka pro další architektonický návrh

| Položka | Obsah |
|---|---|
| Otázka | Zvládne SQLite požadovaných 20 souběžných rezervací při zachování REQ-04? |
| Doklad | [settings.py][settings]: `IMMEDIATE`, timeout 20 s; [services.py][services]: chyba `busy` při zamčené DB. Test `test_confirm_cannot_be_repeated` ověřuje jen sekvenční opakování. |
| Proč je důležitá | SQLite serializuje zápisy; souběžný experiment musí ověřit správnost přechodů, čekání a četnost `busy`. |

[services]: ../src/rezervace_divadlo/reservation/services.py
[models]: ../src/rezervace_divadlo/reservation/models.py
[settings]: ../src/rezervace_divadlo/rezervace_divadlo/settings.py
[notifications]: ../src/rezervace_divadlo/reservation/notifications.py
