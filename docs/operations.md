# Operace a požadavky

Tato baseline používá stavy `DRAFT`, `PENDING_APPROVAL`, `CONFIRMED`,
`REJECTED`, `CANCELLED` a `EXPIRED`. Význam stavů a společná pravidla jsou
definovány jednou v `intent_and_change.md`; zde se na ně pouze odkazuje.

## OP-01 — Create Reservation

Cíl / hodnota pro uživatele:
Uživatel si v mapě sálu vybere jedno nebo více sedadel a pokračováním
s rezervací vytvoří jednu časově omezenou rezervaci pro všechna vybraná
sedadla.

Spouštěcí událost:
Autorizovaný návštěvník vybere alespoň jedno volné sedadlo a stiskne tlačítko
pro pokračování s rezervací.

Pozorovatelný požadavek:
REQ-01: Systém atomicky vytvoří jednu rezervaci ve stavu `DRAFT` pro všechna
vybraná existující sedadla s platným `hold_until`, pouze pokud žádné z nich
není drženo, čeká na schválení ani potvrzeno pro stejné představení.

Předpoklady:
- uživatel je oprávněn rezervace vytvářet;
- představení existuje a všechna sedadla patří do sálu představení;
- seznam vybraných sedadel není prázdný a neobsahuje duplicity;
- délka držení je kladná a je určena systémem.

Stav po úspěšném provedení:
- existuje právě jedna nová rezervace ve stavu `DRAFT`;
- všechna vybraná sedadla jsou do `hold_until` blokována pro ostatní návštěvníky.

Změna stavu: `[none] -> DRAFT`.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-05.

Hlavní úspěšný scénář:
1. Uživatel zobrazí sál a vybere jedno nebo více volných sedadel.
2. Po výběru se zobrazí tlačítko pro pokračování s rezervací.
3. Uživatel tlačítko stiskne.
4. Systém v jedné atomické operaci ověří dostupnost všech sedadel a vytvoří
	`DRAFT`.
5. Systém vrátí identifikátor rezervace a čas `hold_until`.
6. Po dobu držení se žádné z vybraných sedadel nezobrazí jako volné jinému
	uživateli.

Alternativní / chybové výsledky:
- neoprávněný uživatel -> odmítnout, rezervace nevznikne;
- neznámý Resource nebo sedadlo mimo sál -> odmítnout, rezervace nevznikne;
- některé sedadlo už drží, čeká na schválení nebo je potvrzené -> odmítnout,
	rezervace nevznikne;
- vypršené držení -> odmítnout nebo nejdříve atomicky uvolnit;
- neaktivní rezervační relace po pěti minutách -> držení přejde do
	`EXPIRED` a sedadla se uvolní.

Příklady ověření:
- výběr tří sedadel a pokračování -> jedna `DRAFT` pro tři sedadla;
- dva souběžné pokusy o stejné sedadlo -> nejvýše jedna `DRAFT`;
- neaktivita po pěti minutách -> `DRAFT -> EXPIRED` a dostupnost se obnoví;
- `start == end` -> odmítnuto;
- neznámý Resource -> odmítnuto.


## OP-02 — Check Availability

Cíl / hodnota pro uživatele:
Uživatel zjistí, zda je sedadlo pro představení v požadovaném intervalu
dostupné. V rozhraní se tato kontrola projeví jako mapa sálu: volná sedadla
lze vybrat a po výběru alespoň jednoho sedadla se zobrazí tlačítko pro
pokračování s rezervací.

Spouštěcí událost:
Uživatel nebo systém se dotáže na Resource a platný interval.

Pozorovatelný požadavek:
REQ-02: Pro platné představení systém vrátí `UNAVAILABLE`, pokud existuje
aktivní `DRAFT`, `PENDING_APPROVAL` nebo `CONFIRMED` rezervace stejného
sedadla; jinak vrátí `AVAILABLE`.

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
2. Systém vyhledá aktivní `DRAFT`, `PENDING_APPROVAL` a `CONFIRMED`
	rezervace.
3. Systém vrátí dostupnost.

Alternativní / chybové výsledky:
- neznámý Resource -> odmítnout;
- neplatný interval -> odmítnout;
- `CANCELLED`, `REJECTED` a `EXPIRED` dostupnost neblokují.

Příklady ověření:
- `CONFIRMED [10:00,11:00)` + dotaz `[09:00,10:00)` -> `AVAILABLE`;
- stejná rezervace + `[10:30,11:30)` -> `UNAVAILABLE`;
- stejná rezervace + `[11:00,12:00)` -> `AVAILABLE`;


## OP-03 — Confirm Reservation

Cíl / hodnota pro uživatele:
Systém dokončí `DRAFT` podle počtu sedadel a pravidel schvalování.

Spouštěcí událost:
Autorizovaný návštěvník požádá o potvrzení rezervace X.

Pozorovatelné požadavky:
REQ-03: Systém nastaví existující `DRAFT` na `CONFIRMED`, pokud obsahuje
méně než pět sedadel, nebo na `PENDING_APPROVAL`, pokud obsahuje pět či více
sedadel či celý sál. V obou případech musí být držení platné a všechna
sedadla aktivní bez kolize s jinou aktivní rezervací.

REQ-04: Při souběžných konfliktních pokusech může do `CONFIRMED` nebo
`PENDING_APPROVAL` přejít nejvýše jedna kolidující rezervace.

Předpoklady:
- rezervace existuje a je ve stavu `DRAFT`;
- uživatel je oprávněn ji potvrdit.

Stav po úspěšném provedení:
- podle větve je rezervace `CONFIRMED` nebo `PENDING_APPROVAL` a všechna
  její sedadla jsou blokována;
- BR-02 zůstává splněno.

Změna stavu: `DRAFT -> CONFIRMED` nebo `DRAFT -> PENDING_APPROVAL`.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-03, BR-04, BR-05.

Hlavní úspěšný scénář:
1. Systém ověří oprávnění, existenci a stav `DRAFT`.
2. Ověří počet sedadel, případnou rezervaci celého sálu, platnost držení,
	aktivní sedadla a kolizi s jinými rezervacemi.
3. Atomicky nastaví `CONFIRMED` nebo `PENDING_APPROVAL`.
4. Systém vrátí aktuální stav.

Alternativní / chybové výsledky:
- neaktivní sedadlo -> odmítnout, stav zůstává `DRAFT`;
- vypršené držení -> odmítnout a držení přejde do `EXPIRED`;
- existující kolize -> odmítnout, stav zůstává `DRAFT`;
- jiný zdrojový stav -> odmítnout bez změny;
- při souběhu rozhodne atomická změna stavu a pouze jedna kolidující
	rezervace může být `CONFIRMED` nebo `PENDING_APPROVAL`.

Příklady ověření:
- aktivní rezervace pro méně než pět sedadel bez kolize -> `CONFIRMED`;
- aktivní rezervace pro pět nebo více sedadel bez kolize ->
	`PENDING_APPROVAL`;
- kolize -> odmítnuto, zůstává `DRAFT`;
- dva souběžné konfliktní pokusy -> nejvýše jedna rezervace přejde do
	`CONFIRMED` nebo `PENDING_APPROVAL`.


## OP-04 — Cancel Reservation

Cíl / hodnota pro uživatele:
Uživatel stáhne oprávněnou rezervaci před začátkem představení.

Spouštěcí událost:
Oprávněný návštěvník požádá o zrušení rezervace X.

Pozorovatelný požadavek:
REQ-05: Systém dovolí zrušit `DRAFT`, `PENDING_APPROVAL` nebo `CONFIRMED`,
pokud `now < start`. Zrušený záznam zůstane uložen jako `CANCELLED`.

Předpoklady:
- rezervace existuje;
- uživatel je k ní oprávněn;
- stav je `DRAFT`, `PENDING_APPROVAL` nebo `CONFIRMED`;
- `now < start` podle zdroje času systému.

Stav po úspěšném provedení:
- stav je `CANCELLED`;
- rezervace neblokuje Resource.

Změna stavu: `DRAFT|PENDING_APPROVAL|CONFIRMED -> CANCELLED`.

Odkaz na pravidla / invarianty: BR-01, BR-02, BR-03, BR-05.

Hlavní úspěšný scénář:
1. Systém ověří existenci, oprávnění, stav a aktuální čas.
2. Atomicky nastaví `CANCELLED`.
3. Vrátí stav; všechna sedadla rezervace se okamžitě uvolní.

Alternativní / chybové výsledky:
- `now >= start` -> odmítnout, stav se nemění;
- `CANCELLED` -> odmítnout, stav se nemění;
- `REJECTED` nebo `EXPIRED` -> odmítnout, stav se nemění;
- souběh s potvrzením -> uspěje pouze první platná atomická změna; druhá
	obdrží neplatný zdrojový stav nebo odmítnutí podle výsledného stavu.

Příklady ověření:
- `DRAFT` před začátkem -> `CANCELLED` a sedadla se uvolní;
- `PENDING_APPROVAL` před začátkem -> `CANCELLED` a všechna sedadla se
	uvolní;
- `CONFIRMED` před začátkem -> `CANCELLED` a dostupnost se obnoví;
- v okamžiku začátku nebo později -> odmítnuto;
- opakované zrušení -> explicitně odmítnuto.


## OP-05 — Approve Reservation

Cíl / hodnota pro uživatele:
Oprávněná osoba rozhodne o hromadné rezervaci, která čeká na manuální
schválení.

Spouštěcí událost:
Schvalovatel požádá o schválení nebo zamítnutí rezervace X ve stavu
`PENDING_APPROVAL`.

Pozorovatelné požadavky:
REQ-06: Systém dovolí schvalovateli atomicky změnit `PENDING_APPROVAL` na
`CONFIRMED` nebo `REJECTED`.

REQ-07: Schválení je možné pouze tehdy, když žádné sedadlo rezervace
nekoliduje s jinou aktivní rezervací a neuplynula lhůta pro schválení.

Předpoklady:
- rezervace existuje a je ve stavu `PENDING_APPROVAL`;
- schvalovatel má oprávnění rozhodnout;
- `now` je před začátkem představení i před lhůtou pro schválení;
- všechna sedadla rezervace jsou stále aktivně blokována touto rezervací.

Stav po úspěšném provedení:
- při schválení je stav `CONFIRMED` a všechna sedadla zůstávají blokována;
- při zamítnutí je stav `REJECTED` a všechna sedadla se uvolní;
- rozhodnutí je atomické a opakované rozhodnutí je odmítnuto.

Změna stavu: `PENDING_APPROVAL -> CONFIRMED|REJECTED`.

Odkaz na pravidla / invarianty: BR-02, BR-03, BR-05, BR-06, BR-08.

Hlavní úspěšný scénář:
1. Systém ověří oprávnění schvalovatele, existenci a stav
	`PENDING_APPROVAL`.
2. Ověří lhůtu pro schválení, začátek představení a kolize všech sedadel.
3. Schvalovatel zvolí schválení nebo zamítnutí.
4. Systém atomicky nastaví `CONFIRMED` nebo `REJECTED`.
5. Systém vrátí aktuální stav a výsledek rozhodnutí.

Alternativní / chybové výsledky:
- neoprávněný aktér -> odmítnout bez změny;
- jiný zdrojový stav -> odmítnout bez změny;
- vypršená lhůta nebo neaktivní držení -> atomicky nastavit `EXPIRED`;
- kolize při schvalování -> schválení odmítnout a stav ponechat
	`PENDING_APPROVAL`, pokud není dosažena lhůta pro expiraci;
- souběh schválení, zamítnutí, zrušení a expirace -> uspěje pouze první
	platný atomický přechod.

Příklady ověření:
- schválená hromadná rezervace -> `CONFIRMED`, sedadla zůstávají
	nepřístupná;
- zamítnutá hromadná rezervace -> `REJECTED`, sedadla jsou dostupná;
- rozhodnutí po expiraci -> odmítnuto nebo `EXPIRED` podle prvního platného
	přechodu;
- běžný návštěvník se schválením -> odmítnuto.