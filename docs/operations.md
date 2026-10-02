# Operace a požadavky

Tato baseline používá stavy `DRAFT`, `CONFIRMED` a `CANCELLED`. Význam stavů
a společná pravidla jsou definovány jednou v `intent_and_change.md`; zde se na
ně pouze odkazuje.

## OP-01 — Create Reservation

Cíl / hodnota pro uživatele:
Uživatel si výběrem sedadla okamžitě vytvoří časově omezené držení, aby mu
sedadlo během vyplňování formuláře nemohl převzít jiný návštěvník.

Spouštěcí událost:
Autorizovaný návštěvník klikne na sedadlo u konkrétního představení.

Pozorovatelný požadavek:
REQ-01: Systém atomicky vytvoří pro existující sedadlo jednu rezervaci ve
stavu `DRAFT` s platným `hold_until`, pouze pokud sedadlo není drženo ani
potvrzeno pro stejné představení.

Předpoklady:
- uživatel je oprávněn rezervace vytvářet;
- představení a sedadlo existují a sedadlo patří do sálu představení;
- délka držení je kladná a je určena systémem.

Stav po úspěšném provedení:
- existuje právě jedna nová rezervace ve stavu `DRAFT`;
- sedadlo je do `hold_until` blokováno pro ostatní návštěvníky.

Změna stavu: `[none] -> DRAFT`.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-05.

Hlavní úspěšný scénář:
1. Uživatel klikne na volné sedadlo.
2. Systém v jedné atomické operaci ověří dostupnost a vytvoří `DRAFT`.
3. Systém vrátí identifikátor rezervace a čas `hold_until`.
4. Uživatel vyplní formulář; po dobu držení se stejné sedadlo nezobrazí jako
	volné jinému návštěvníkovi.

Alternativní / chybové výsledky:
- neoprávněný uživatel -> odmítnout, rezervace nevznikne;
- neznámý Resource -> odmítnout, rezervace nevznikne;
- sedadlo už drží nebo má potvrzený jiný návštěvník -> odmítnout, rezervace
	nevznikne;
- vypršené držení -> odmítnout nebo nejdříve atomicky uvolnit.

Příklady ověření:
- kliknutí na volné sedadlo -> jedna aktivní `DRAFT` s `hold_until`;
- dva souběžné kliky na stejné sedadlo -> nejvýše jedna `DRAFT`;
- `start == end` -> odmítnuto;
- neznámý Resource -> odmítnuto.


## OP-02 — Check Availability

Cíl / hodnota pro uživatele:
Uživatel zjistí, zda je sedadlo pro představení v požadovaném intervalu
dostupné. V rozhraní se tato kontrola projeví jako mapa sedadel podobná
mapě v kině: volné sedadlo lze vybrat a tím se ihned vytvoří jeho držení.

Spouštěcí událost:
Uživatel nebo systém se dotáže na Resource a platný interval.

Pozorovatelný požadavek:
REQ-02: Pro platné představení systém vrátí `UNAVAILABLE`, pokud existuje
aktivní `DRAFT` nebo `CONFIRMED` rezervace stejného sedadla; jinak vrátí
`AVAILABLE`.

Předpoklady:
- Resource existuje;
- interval splňuje BR-01.

Stav po úspěšném provedení:
- výsledek dostupnosti je vrácen;
- žádný stav rezervace se nezmění.

Změna stavu: žádná.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-05.

Hlavní úspěšný scénář:
1. Systém ověří Resource a interval.
2. Systém vyhledá aktivní `DRAFT` a `CONFIRMED` rezervace.
3. Systém vrátí dostupnost.

Alternativní / chybové výsledky:
- neznámý Resource -> odmítnout;
- neplatný interval -> odmítnout;
- `CANCELLED` a `DRAFT` po `hold_until` dostupnost neblokují.

Příklady ověření:
- `CONFIRMED [10:00,11:00)` + dotaz `[09:00,10:00)` -> `AVAILABLE`;
- stejná rezervace + `[10:30,11:30)` -> `UNAVAILABLE`;
- stejná rezervace + `[11:00,12:00)` -> `AVAILABLE`;


## OP-03 — Confirm Reservation

Cíl / hodnota pro uživatele:
Systém přijme `DRAFT` jako platnou alokaci sedadla.

Spouštěcí událost:
Autorizovaný návštěvník požádá o potvrzení rezervace X.

Pozorovatelné požadavky:
REQ-03: Systém nastaví existující `DRAFT` na `CONFIRMED` pouze tehdy, když
je držení platné, sedadlo je aktivní a nekoliduje s jinou aktivní rezervací.

REQ-04: Při souběžných konfliktních pokusech může do `CONFIRMED` přejít
nejvýše jedna rezervace.

Předpoklady:
- rezervace existuje a je ve stavu `DRAFT`;
- uživatel je oprávněn ji potvrdit.

Stav po úspěšném provedení:
- `CONFIRMED` a Resource je blokován;
- BR-02 zůstává splněno.

Změna stavu: `DRAFT -> CONFIRMED`.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-03, BR-04, BR-05.

Hlavní úspěšný scénář:
1. Systém ověří oprávnění, existenci a stav `DRAFT`.
2. Ověří platnost držení, aktivní sedadlo a kolizi s jinými rezervacemi.
3. Atomicky nastaví `CONFIRMED`.
4. Systém vrátí aktuální stav.

Alternativní / chybové výsledky:
- neaktivní sedadlo -> odmítnout, stav zůstává `DRAFT`;
- vypršené držení -> odmítnout a držení uvolnit;
- existující kolize -> odmítnout, stav zůstává `DRAFT`;
- jiný zdrojový stav -> odmítnout bez změny;
- při souběhu rozhodne atomická změna stavu a pouze jedna kolidující
	rezervace může být `CONFIRMED`.

Příklady ověření:
- aktivní Resource bez kolize -> `CONFIRMED`;
- kolize -> odmítnuto, zůstává `DRAFT`;
- dva souběžné konfliktní pokusy -> nejvýše jedna `CONFIRMED`.


## OP-04 — Cancel Reservation

Cíl / hodnota pro uživatele:
Uživatel stáhne oprávněnou rezervaci před začátkem představení.

Spouštěcí událost:
Oprávněný návštěvník požádá o zrušení rezervace X.

Pozorovatelný požadavek:
REQ-05: Systém dovolí zrušit `DRAFT` nebo `CONFIRMED`,
pokud `now < start`. Zrušený záznam zůstane uložen jako `CANCELLED`.

Předpoklady:
- rezervace existuje;
- uživatel je k ní oprávněn;
- stav je `DRAFT` nebo `CONFIRMED`;
- `now < start` podle zdroje času systému.

Stav po úspěšném provedení:
- stav je `CANCELLED`;
- rezervace neblokuje Resource.

Změna stavu: `DRAFT|CONFIRMED -> CANCELLED`.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-03, BR-05.

Hlavní úspěšný scénář:
1. Systém ověří existenci, oprávnění, stav a aktuální čas.
2. Atomicky nastaví `CANCELLED`.
3. Vrátí stav; u `CONFIRMED` se Resource okamžitě uvolní.

Alternativní / chybové výsledky:
- `now >= start` -> odmítnout, stav se nemění;
- `CANCELLED` -> odmítnout, stav se nemění;
- souběh s potvrzením -> uspěje pouze první platná atomická změna; druhá
	obdrží neplatný zdrojový stav nebo odmítnutí podle výsledného stavu.

Příklady ověření:
- `DRAFT` před začátkem -> `CANCELLED`;
- `CONFIRMED` před začátkem -> `CANCELLED` a dostupnost se obnoví;
- v okamžiku začátku nebo později -> odmítnuto;
- opakované zrušení -> explicitně odmítnuto.
