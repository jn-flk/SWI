# C02 — Operations and requirements

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [Domain rules](../intent-and-change/C02-Domain-Rules.md) · [States](../intent-and-change/C02-States-and-Transitions.md) · [Domain model](../architecture-and-decisions/C02-Domain-Model-and-Limitations.md) · [C02 evidence](../evidence-and-evolution/C02-Specification-to-Running-App.md)

Tato baseline používá stavy `DRAFT`, `PENDING_APPROVAL`, `CONFIRMED`,
`REJECTED`, `CANCELLED` a `EXPIRED`. Význam stavů a společná pravidla jsou
definovány jednou v [C02-States-and-Transitions.md](C02-States-and-Transitions.md) a
[C02-Domain-Rules.md](C02-Domain-Rules.md); zde se na ně pouze odkazuje.

## OP-01 — Create Reservation

### Goal / user value
Uživatel si v mapě sálu vybere jedno nebo více sedadel a pokračováním
s rezervací vytvoří jednu časově omezenou rezervaci pro všechna vybraná
sedadla.

### Trigger
Autorizovaný návštěvník vybere alespoň jedno volné sedadlo a stiskne tlačítko
pro pokračování s rezervací.

### Observable requirement
**REQ-01:** Systém atomicky vytvoří jednu rezervaci ve stavu `DRAFT` pro všechna
vybraná existující sedadla s platným `hold_until`, pouze pokud žádné z nich
není drženo, čeká na schválení ani potvrzeno pro stejné představení.

### Preconditions
- uživatel je oprávněn rezervace vytvářet;
- představení existuje a všechna sedadla patří do sálu představení;
- seznam vybraných sedadel není prázdný a neobsahuje duplicity;
- vybraná sedadla jsou aktivní;
- systém nastavuje pevný hold na 15 minut od vytvoření `DRAFT`;
- představení začíná později než za 15 minut; pokud rezervace vyžaduje
  schválení (více než 10 sedadel nebo celý sál), začíná nejméně za 24 hodin.

### State after success
- existuje právě jedna nová rezervace ve stavu `DRAFT`;
- všechna vybraná sedadla jsou do `hold_until` blokována pro ostatní návštěvníky.

**State change:** `[none] -> DRAFT`.

### Referenced rules / invariants
- BR-01 (Interval semantics)
- BR-02 (Exclusive Resource invariant)
- BR-05 (Availability policy)
- BR-07 (Fixed hold and return-to-selection policy)
- BR-08 (Bulk approval lead time)

### Main success scenario
1. Uživatel zobrazí sál a vybere jedno nebo více volných sedadel.
2. Po výběru se zobrazí tlačítko pro pokračování s rezervací.
3. Uživatel tlačítko stiskne.
4. Systém v jedné atomické operaci ověří dostupnost všech sedadel a vytvoří
   `DRAFT`.
5. Systém vrátí identifikátor rezervace a čas `hold_until`.
6. Po dobu držení se žádné z vybraných sedadel nezobrazí jako volné jinému
   uživateli.

### Alternative / failure outcomes
- neoprávněný uživatel -> odmítnout, rezervace nevznikne;
- neznámé sedadlo nebo sedadlo mimo sál -> odmítnout, rezervace nevznikne;
- některé sedadlo už drží, čeká na schválení nebo je potvrzené -> odmítnout,
   rezervace nevznikne;
- vypršené držení -> odmítnout nebo nejdříve atomicky uvolnit;
- návrat vlastníka na výběr sedadel pro stejné představení -> jeho aktivní
   nedokončená držení se nastaví na `CANCELLED` a sedadla se ihned uvolní;
   držení jiných uživatelů se nezmění;
- po 15 minutách od vytvoření `DRAFT` -> držení přejde do `EXPIRED` a
   sedadla se uvolní.

### Verification examples
- výběr tří sedadel a pokračování -> jedna `DRAFT` pro tři sedadla;
- dva souběžné pokusy o stejné sedadlo -> nejvýše jedna `DRAFT`;
- uplynutí 15 minut od vytvoření -> `DRAFT -> EXPIRED` a dostupnost se obnoví;
- návrat vlastníka na výběr -> vlastní `DRAFT` se zruší a sedadla se ihned
  uvolní;
- `start == end` -> odmítnuto;
- neznámé sedadlo -> odmítnuto.

## OP-01a — Validate Reservation Hold

### Goal / user value
Systém při odeslání kontaktních údajů ověří, že držení `DRAFT` stále platí,
aniž by jeho deadline měnil.

### Preconditions
- rezervace existuje, vlastník je oprávněný a stav je `DRAFT`;
- `hold_until` ještě nevypršel; jeho hodnota zůstává stejná.

### Behaviour
- systém pouze ověří platnost existujícího `hold_until`;
- přechod mezi kroky ani odeslání kontaktních údajů držení neprodlužují;
- vypršel-li původní hold, systém nejprve nastaví `EXPIRED`, uvolní sedadla
  a další postup odmítne;
- žádný jiný stav nelze touto operací validovat.

**Implementation:** `reservation.services.touch_reservation`

### Referenced rules / invariants
- BR-07 (Fixed hold and return-to-selection policy)

## OP-02 — Check Availability

### Goal / user value
Uživatel zjistí, zda je sedadlo pro představení v požadovaném intervalu
dostupné. V rozhraní se tato kontrola projeví jako mapa sálu: volná sedadla
lze vybrat a po výběru alespoň jednoho sedadla se zobrazí tlačítko pro
pokračování s rezervací.

### Trigger
Uživatel nebo systém se dotáže na sedadlo a platný interval.

### Observable requirement
**REQ-02:** Pro platné představení systém vrátí `UNAVAILABLE`, pokud existuje
aktivní `DRAFT`, `PENDING_APPROVAL` nebo `CONFIRMED` rezervace stejného
sedadla; jinak vrátí `AVAILABLE`.

### Preconditions
- sedadlo existuje;
- interval splňuje BR-01 (Interval semantics).

### State after success
- výsledek dostupnosti je vrácen;
- žádný stav rezervace se nezmění.

**State change:** žádná.

### Referenced rules / invariants
- BR-01 (Interval semantics)
- BR-02 (Exclusive Resource invariant)
- BR-05 (Availability policy)

### Main success scenario
1. Systém ověří sedadlo a interval.
2. Systém vyhledá aktivní `DRAFT`, `PENDING_APPROVAL` a `CONFIRMED`
   rezervace.
3. Systém vrátí dostupnost.

### Alternative / failure outcomes
- neznámé sedadlo -> odmítnout;
- neplatný interval -> odmítnout;
- `CANCELLED`, `REJECTED` a `EXPIRED` dostupnost neblokují.

### Verification examples
- `CONFIRMED [10:00,11:00)` + dotaz `[09:00,10:00)` -> `AVAILABLE`;
- stejná rezervace + `[10:30,11:30)` -> `UNAVAILABLE`;
- stejná rezervace + `[11:00,12:00)` -> `AVAILABLE`;


## OP-03 — Confirm Reservation

### Goal / user value
Systém dokončí `DRAFT` podle počtu sedadel a pravidel schvalování.

### Trigger
Autorizovaný návštěvník požádá o potvrzení rezervace X.

### Observable requirements
**REQ-03:** Systém nastaví existující `DRAFT` na `CONFIRMED`, pokud obsahuje
nejvýše deset sedadel, nebo na `PENDING_APPROVAL`, pokud obsahuje více než deset
sedadel či celý sál. V obou případech musí být držení platné a všechna
sedadla aktivní, musí platit 15minutový cutoff a u schvalovací větve také
minimální předstih 24 hodin. Schvalovací větev nastaví
`approval_deadline = now + 24 h`. Sedadla jsou blokována již od vytvoření `DRAFT` podle
BR-02 (Exclusive Resource invariant); kontrola kolize se při potvrzení neopakuje.

**REQ-04:** Při souběžných pokusech o potvrzení stejné rezervace uspěje pouze
jeden přechod z `DRAFT`.

### Preconditions
- rezervace existuje a je ve stavu `DRAFT`;
- uživatel je oprávněn ji potvrdit.
- `hold_until` ještě nevypršel;

### State after success
- podle větve je rezervace `CONFIRMED` nebo `PENDING_APPROVAL` a všechna
  její sedadla jsou blokována;
- BR-02 (Exclusive Resource invariant) zůstává splněno.

**State change:** `DRAFT -> CONFIRMED` nebo `DRAFT -> PENDING_APPROVAL`.

### Referenced rules / invariants
- BR-01 (Interval semantics)
- BR-02 (Exclusive Resource invariant)
- BR-03 (Cancellation policy)
- BR-04 (Confirmation policy)
- BR-05 (Availability policy)

### Main success scenario
1. Systém ověří oprávnění, existenci a stav `DRAFT`.
2. Pokud `hold_until` vypršel, atomicky nastaví `EXPIRED`, uvolní sedadla
   a požadavek odmítne.
3. Ověří aktivní sedadla, cutoff 15 minut a u schvalovací větve předstih
   24 hodin. Ověří počet sedadel a případnou rezervaci celého sálu.
   Dostupnost ani kolizi znovu nekontroluje podle BR-04 (Confirmation policy).
4. Atomicky nastaví `CONFIRMED` nebo `PENDING_APPROVAL`; ve druhé větvi
   nastaví `approval_deadline = now + 24 h` a zapíše outbox událost.
5. Systém vrátí aktuální stav.

### Alternative / failure outcomes
- neaktivní sedadlo -> odmítnout, stav zůstává `DRAFT`;
- vypršené držení -> odmítnout a držení přejde do `EXPIRED`;
- porušení cutoffu nebo lead-time -> odmítnout, stav zůstává `DRAFT`;
- jiný zdrojový stav -> odmítnout bez změny;
- při souběhu potvrzení stejné rezervace uspěje pouze první atomický
   přechod z `DRAFT`; další pokus je odmítnut kvůli zdrojovému stavu.

### Verification examples
- aktivní rezervace pro nejvýše deset sedadel -> `CONFIRMED`;
- aktivní rezervace pro více než deset sedadel ->
   `PENDING_APPROVAL`;
- potvrzení zachová blokování sedadel vytvořené při OP-01 bez nové
   kontroly dostupnosti;
- dva souběžné pokusy o potvrzení stejné rezervace -> jeden úspěšný
   přechod a jedno odmítnutí kvůli zdrojovému stavu.


## OP-04 — Cancel Reservation

### Goal / user value
Uživatel stáhne oprávněnou rezervaci před začátkem představení.

### Trigger
Oprávněný návštěvník požádá o zrušení rezervace X.

### Observable requirement
**REQ-05:** Systém dovolí zrušit `DRAFT`, `PENDING_APPROVAL` nebo `CONFIRMED`,
pokud `now < start`. Zrušený záznam zůstane uložen jako `CANCELLED`.
Opakované zrušení již `CANCELLED` rezervace oprávněným aktérem vrátí
idempotentní úspěch bez změny podle BR-03 (Cancellation policy).

### Preconditions
- rezervace existuje;
- uživatel je k ní oprávněn;
- pro nový přechod do `CANCELLED` je stav `DRAFT`, `PENDING_APPROVAL` nebo
  `CONFIRMED` a platí `now < start` podle zdroje času systému;
- pro opakované zrušení je stav `CANCELLED`; časová podmínka se neuplatní.

### State after success
- stav je `CANCELLED`;
- rezervace neblokuje sedadla.

**State change:** `DRAFT|PENDING_APPROVAL|CONFIRMED -> CANCELLED`;
u již `CANCELLED` rezervace žádná změna.

### Referenced rules / invariants
- BR-01 (Interval semantics)
- BR-02 (Exclusive Resource invariant)
- BR-03 (Cancellation policy)
- BR-05 (Availability policy)

### Main success scenario
1. Systém ověří existenci rezervace a oprávnění uživatele.
2. Je-li stav již `CANCELLED`, vrátí idempotentní úspěch bez změny.
3. Jinak ověří povolený zdrojový stav a aktuální čas podle BR-03 (Cancellation policy).
4. Atomicky nastaví `CANCELLED`.
5. Vrátí stav; všechna sedadla rezervace se okamžitě uvolní.

### Alternative / failure outcomes
- `now >= start` u dosud nezrušené rezervace -> odmítnout, stav se nemění;
- `CANCELLED` -> idempotentní úspěch, stav se nemění;
- `REJECTED` nebo `EXPIRED` -> odmítnout, stav se nemění;
- souběh s potvrzením -> uspěje pouze první platná atomická změna; druhá
   obdrží neplatný zdrojový stav nebo odmítnutí podle výsledného stavu.

### Verification examples
- `DRAFT` před začátkem -> `CANCELLED` a sedadla se uvolní;
- `PENDING_APPROVAL` před začátkem -> `CANCELLED` a všechna sedadla se
   uvolní;
- `CONFIRMED` před začátkem -> `CANCELLED` a dostupnost se obnoví;
- první zrušení v okamžiku začátku nebo později -> odmítnuto;
- opakované zrušení oprávněným uživatelem -> idempotentní úspěch se stavem
   `CANCELLED`, také po začátku představení.


## OP-05 — Approve Reservation

### Goal / user value
Oprávněná osoba rozhodne o hromadné rezervaci, která čeká na manuální
schválení.

### Trigger
Schvalovatel požádá o schválení nebo zamítnutí rezervace X ve stavu
`PENDING_APPROVAL`.

### Observable requirements
**REQ-06:** Systém dovolí schvalovateli atomicky změnit `PENDING_APPROVAL` na
`CONFIRMED` nebo `REJECTED`.

**REQ-07:** Schválení je možné pouze před uplynutím lhůty pro schválení.
Sedadla zůstávají blokována od vytvoření `DRAFT` i během `PENDING_APPROVAL`
podle BR-02 (Exclusive Resource invariant); schválení zachovává toto blokování bez nové kontroly kolize.

### Preconditions
- rezervace existuje a je ve stavu `PENDING_APPROVAL`;
- schvalovatel má oprávnění rozhodnout;
- `now` je před začátkem představení i před lhůtou pro schválení;
- všechna sedadla rezervace jsou stále aktivně blokována touto rezervací.

### State after success
- při schválení je stav `CONFIRMED` a všechna sedadla zůstávají blokována;
- při zamítnutí je stav `REJECTED` a všechna sedadla se uvolní;
- rozhodnutí je atomické a opakované rozhodnutí je odmítnuto.

**State change:** `PENDING_APPROVAL -> CONFIRMED|REJECTED`.

### Referenced rules / invariants
- BR-02 (Exclusive Resource invariant)
- BR-03 (Cancellation policy)
- BR-05 (Availability policy)
- BR-06 (Concurrent outcome)
- BR-08 (Bulk approval lead time)

### Main success scenario
1. Systém ověří oprávnění schvalovatele, existenci a stav
   `PENDING_APPROVAL`.
2. Ověří lhůtu pro schválení a začátek představení. Dostupnost ani kolizi
   sedadel znovu nekontroluje podle BR-04 (Confirmation policy).
3. Schvalovatel zvolí schválení nebo zamítnutí.
4. Systém atomicky nastaví `CONFIRMED` nebo `REJECTED`.
5. Systém vrátí aktuální stav a výsledek rozhodnutí.

### Alternative / failure outcomes
- neoprávněný aktér -> odmítnout bez změny;
- jiný zdrojový stav -> odmítnout bez změny;
- vypršená lhůta nebo neaktivní držení -> atomicky nastavit `EXPIRED`;
- souběh schválení, zamítnutí, zrušení a expirace -> uspěje pouze první
   platný atomický přechod.

### Verification examples
- schválená hromadná rezervace -> `CONFIRMED`, sedadla zůstávají
   nepřístupná bez nové kontroly dostupnosti;
- zamítnutá hromadná rezervace -> `REJECTED`, sedadla jsou dostupná;
- rozhodnutí po expiraci -> odmítnuto nebo `EXPIRED` podle prvního platného
   přechodu;
- běžný návštěvník se schválením -> odmítnuto.
