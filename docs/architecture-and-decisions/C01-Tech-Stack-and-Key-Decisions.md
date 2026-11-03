# C01 — Tech stack and key decisions

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [Project Frame](../intent-and-change/C01-Project-Frame.md) · [Engineering spike](../evidence-and-evolution/C01-Engineering-Spike.md)

## Tech stack

- **Jazyk:** Python 3
- **Framework:** Django 6.1
- **Databáze:** SQLite (vývojové prostředí) — přes Django ORM
- **Testování:** vestavěný Django `TestCase` (`python manage.py test`)

## Project structure

Jeden Django projekt `rezervace_divadlo` se dvěma aplikacemi: `reservation`
pro lifecycle a `notification` pro outbox/delivery.



## Key decisions

| Rozhodnutí | Zdůvodnění |
|---|---|
| Použít Django + Django ORM místo samostatné persistentní vrstvy | Nejrychlejší cesta k funkčnímu a testovatelnému doménovému modelu pro C01; migrace a constrainty v ORM pokrývají naše aktuální potřeby (unikátnostní pravidla) bez nutnosti dalších nástrojů. |
| Použít SQLite pro vývoj | Nulové nastavení, dostatečné pro ověření doménové logiky a spouštění testů lokálně/v CI. Přehodnotíme pro CP1, pokud budeme potřebovat garance pro souběžné zápisy (viz future pressure: 20× souběžných rezervací). |
| Vynutit exkluzivitu podmíněným unikátním constraintem na `ReservationSeat` | Databáze odmítne druhou aktivní alokaci stejného sedadla a představení. Zrušení, zamítnutí a expirace vypnou alokace, ale zachovají historii. Všechny aplikační zápisy procházejí `services.py` v transakci. SQLite používá `BEGIN IMMEDIATE`; zámek spisovatele vzniká před čtením dostupnosti. |
| Jedna Django aplikace (`reservation`) místo rozdělení modelů do více aplikací | Doména je zatím malá (5 modelů); rozdělování by teď přidalo strukturu bez reálného přínosu. Přehodnotíme, pokud aplikace výrazně naroste. |
