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
