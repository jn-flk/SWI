# Architektura a rozhodnutí

## Technologický stack

- **Jazyk:** Python 3
- **Framework:** Django 6.1
- **Databáze:** SQLite (vývojové prostředí) — přes Django ORM
- **Testování:** vestavěný Django `TestCase` (`python manage.py test`)

## Struktura projektu

Jeden Django projekt `rezervace_divadlo` s jednou aplikací: `reservation`.



## Doménový model

Aplikace `reservation` aktuálně definuje pět modelů:

- **Play** — divadelní hra (název, popis, délka trvání)
- **Hall** — fyzický prostor/sál
- **Seat** — patří k `Hall`; unikátní podle kombinace `(hall, row, number)`
- **Performance** — konkrétní uvedení `Play` v daném `Hall` v daný čas (`start_at`)
- **Reservation** — reprezentuje jednu rezervaci pro konkrétní `Performance` a
	může obsahovat jedno nebo více vybraných `Seat`. Jedno sedadlo nesmí být pro
	stejné představení součástí více aktivních rezervací. Rezervace používá
	stavy `DRAFT`, `PENDING_APPROVAL`, `CONFIRMED`, `CANCELLED`, `REJECTED` a
	`EXPIRED`. Aktivní `DRAFT` drží všechna vybraná sedadla po dobu
	`hold_until`; `PENDING_APPROVAL` je blokuje do rozhodnutí nebo vypršení;
	`CONFIRMED` je blokuje trvale pro dané představení; `CANCELLED`,
	`REJECTED` a `EXPIRED` sedadla neblokují.

Uživatel nejdříve zobrazí sál a vybere jedno nebo více sedadel. Teprve po
stisku tlačítka pro pokračování s rezervací vznikne jedna `Reservation` pro
všechna vybraná sedadla. Rezervace pro pět nebo více sedadel je hromadná a
vyžaduje schválení oprávněnou osobou. Rezervace celého sálu schválení vyžaduje
bez ohledu na počet sedadel.



## Klíčová rozhodnutí

| Rozhodnutí | Zdůvodnění |
|---|---|
| Použít Django + Django ORM místo samostatné persistentní vrstvy | Nejrychlejší cesta k funkčnímu a testovatelnému doménovému modelu pro C01; migrace a constrainty v ORM pokrývají naše aktuální potřeby (unikátnostní pravidla) bez nutnosti dalších nástrojů. |
| Použít SQLite pro vývoj | Nulové nastavení, dostatečné pro ověření doménové logiky a spouštění testů lokálně/v CI. Přehodnotíme pro CP1, pokud budeme potřebovat garance pro souběžné zápisy (viz future pressure: 20× souběžných rezervací). |
| Vynutit pravidlo "žádné dvojí rezervace" pomocí DB-level constraintu nebo atomické aplikační kontroly místo pouze aplikační logiky | U vazby jedné `Reservation` na více `Seat` musí persistence zabránit tomu, aby stejné sedadlo pro stejné představení patřilo dvěma aktivním rezervacím, a to i při souběžných požadavcích. Přesná podoba constraintu se ověří při implementaci modelu. |
| Jedna Django aplikace (`reservation`) místo rozdělení modelů do více aplikací | Doména je zatím malá (5 modelů); rozdělování by teď přidalo strukturu bez reálného přínosu. Přehodnotíme, pokud aplikace výrazně naroste. |

## Známá omezení (stav k C02)

- Zatím nejsou implementovaná žádná API/views — ověřený je pouze datový model a persistence.
- `Reservation` zatím nemá pole `status` ani `hold_until` a operace OP-01 až OP-05 ještě nejsou implementované.
- Boundary na Notification Service je definovaná koncepčně, ale zatím není implementovaná ani nastubovaná.
- Automatické ukončení neaktivní rezervační relace a mechanismus automatické
  expirace zatím nejsou implementované.