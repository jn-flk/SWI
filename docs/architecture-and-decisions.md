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
- **Reservation** — propojuje `Seat` s `Performance`; unikátní podle kombinace `(performance, seat)`, takže stejné sedadlo nelze na stejné představení zarezervovat dvakrát



## Klíčová rozhodnutí

| Rozhodnutí | Zdůvodnění |
|---|---|
| Použít Django + Django ORM místo samostatné persistentní vrstvy | Nejrychlejší cesta k funkčnímu a testovatelnému doménovému modelu pro C01; migrace a constrainty v ORM pokrývají naše aktuální potřeby (unikátnostní pravidla) bez nutnosti dalších nástrojů. |
| Použít SQLite pro vývoj | Nulové nastavení, dostatečné pro ověření doménové logiky a spouštění testů lokálně/v CI. Přehodnotíme pro CP1, pokud budeme potřebovat garance pro souběžné zápisy (viz future pressure: 20× souběžných rezervací). |
| Vynutit pravidlo "žádné dvojí rezervace" pomocí DB-level `UniqueConstraint` místo pouze aplikační logiky | Garantuje platnost pravidla i při souběžných požadavcích, protože samotná databáze odmítne duplicitní zápis (ověřeno v engineering spike v C01 — viz `evidence-and-evolution.md`). |
| Jedna Django aplikace (`reservation`) místo rozdělení modelů do více aplikací | Doména je zatím malá (5 modelů); rozdělování by teď přidalo strukturu bez reálného přínosu. Přehodnotíme, pokud aplikace výrazně naroste. |

## Známá omezení (stav k C01)

- Zatím nejsou implementovaná žádná API/views — ověřený je pouze datový model a persistence.
- `Reservation` zatím nemá pole `status`, i když doména definuje stavy `RESERVED / CANCELED / DONE` — tohle je součást minimální reservation domény, kterou je potřeba doimplementovat do C02, zatím to není v kódu.
- Boundary na Notification Service je definovaná koncepčně, ale zatím není implementovaná ani nastubovaná.