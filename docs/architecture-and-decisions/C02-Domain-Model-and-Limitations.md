# Architektura a rozhodnutí — C02

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



## Umístění business logiky

`reservation/services.py` obsahuje OP-01 až OP-05, obnovu aktivity a expiraci.
Modely popisují data a databázová omezení. Testy v `reservation/tests.py`
volají služby přímo; reservation nemá HTTP API. `notification` zapisuje
outboxové požadavky v rezervační transakci a samostatný dispatcher je doručuje.

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
