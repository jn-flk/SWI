# C02 — States and transitions

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [Domain rules](../intent-and-change/C02-Domain-Rules.md) · [Operations](../intent-and-change/C02-Operations-and-Requirements.md) · [Domain model](../architecture-and-decisions/C02-Domain-Model-and-Limitations.md) · [C02 evidence](../evidence-and-evolution/C02-Specification-to-Running-App.md)

## Reservation states

- `DRAFT`: uživatel vybral jedno nebo více sedadel a pokračoval k rezervaci.
    Sedadla jsou po omezenou dobu dočasně držena pro daného návštěvníka.
    Stav má `hold_until`.
- `PENDING_APPROVAL`: hromadná rezervace byla odeslána ke schválení. Stav je
    nefinální a všechna její sedadla zůstávají blokována.
- `CONFIRMED`: běžná rezervace byla přijata nebo hromadná rezervace schválena.
    Všechna sedadla jsou blokována pro dané představení.
- `REJECTED`: hromadná rezervace byla zamítnuta schvalovatelem. Stav je
    terminální a sedadla již nejsou blokována.
- `CANCELLED`: existující rezervace nebo držení bylo aktivně zrušeno
    oprávněným aktérem. Stav je terminální a sedadla již nejsou blokována.
- `EXPIRED`: držení nebo čekání na schválení vypršelo bez aktivního
    rozhodnutí. Stav je terminální a sedadla již nejsou blokována.

## Transitions

- `[none] -> DRAFT`: vznikne nová rezervace pro vybraná sedadla a systém je
    po omezenou dobu drží pro daného návštěvníka.
- `DRAFT -> CONFIRMED`: běžná rezervace s nejvýše deseti sedadly je po
    dokončení uživatelem přijata a sedadla jsou trvale blokována.
- `DRAFT -> PENDING_APPROVAL`: hromadná rezervace s více než deseti sedadly
    nebo rezervace celého sálu je odeslána ke schválení. Sedadla zůstávají
    blokována do rozhodnutí nebo vypršení.
- `DRAFT -> CANCELLED`: návštěvník nebo jiný oprávněný aktér aktivně zruší
    držení před jeho potvrzením. Sedadla se uvolní.
- `DRAFT -> EXPIRED`: držení automaticky vyprší, například po ukončení
    neaktivní rezervační relace. Sedadla se uvolní bez aktivního zrušení.
- `PENDING_APPROVAL -> CONFIRMED`: schvalovatel hromadnou rezervaci přijme.
    Sedadla zůstávají trvale blokována.
- `PENDING_APPROVAL -> REJECTED`: schvalovatel hromadnou rezervaci zamítne.
    Sedadla se uvolní a žádost je terminálně ukončena.
- `PENDING_APPROVAL -> EXPIRED`: žádost nebyla schválena před uplynutím
    stanovené lhůty. Sedadla se uvolní automaticky.
- `PENDING_APPROVAL -> CANCELLED`: návštěvník nebo jiný oprávněný aktér
    čekající žádost aktivně zruší před rozhodnutím. Sedadla se uvolní.
- `CONFIRMED -> CANCELLED`: návštěvník nebo jiný oprávněný aktér aktivně
    zruší potvrzenou rezervaci před začátkem představení. Sedadla se uvolní.
