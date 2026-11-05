# C06 — Internal Evidence Assessment

← [Navigator](../NAVIGATOR.md) · [Traceability](../TRACEABILITY.md) · Related: [C07 review and risks](../evidence-and-evolution/C07-Technical-Review-and-Risk-Register.md)

## Assessed baseline

- **Tag `C05`**, commit `5f528647f6b132ceac27b9c0ef95270ae5ae3e24`
  (`5f52864`), aktuální lokální `main` po návratu na tuto verzi.
  Posouzení zahrnuje dokumentaci, kód a testy tohoto commitu, bez pozdějších
  oprav z PR #17. Datum zápisu: 1. 11. 2026.
- Historické milníky: `C01` (`1137bbf`), `C02` (`6ebfcc1`),
  `C03` (`1799c7b`). Tag `C05` zahrnuje implementaci outboxu, DD
  a doplněnou verifikaci; identifikuje také C05 evidenci s TODO v [C05-DD-Verification.md](C05-DD-Verification.md).
- Podklad: hodnocení našeho týmu HAH týmem SIGMA z 19. 10. 2026. F1–F3 byly znovu porovnány s aktuálními
  soubory; rozhodnutí níže se vztahují výhradně k tagu `C05`.
- Ve zdrojích je 23 rezervačních a 23 notifikačních testů. [C05 evidence](C05-DD-Verification.md)
  zaznamenává 46 úspěšných testů za 0,393 s na Pythonu 3.11.9
  s Django 5.2.18. Při tomto zápisu testy znovu spuštěny nebyly, protože
  dostupnému prostředí chybí Django. Nové ověření je statické porovnání
  specifikace, diagramových zdrojů, implementace a testových očekávání.

## Verified findings

- **F1 — C02, VERIFIED FINDING:** OP-01/OP-03 neúplně popisují
  implementovaný cutoff 15 minut, minimální předstih 24 hodin pro
  schvalovanou rezervaci a `approval_deadline = now + 24 h`. OP-03
  neodkazuje na BR-08; obnova držení není plně zachycena ve specifikaci
  a diagramech. Guardy stavového diagramu se překrývají pro celý sál
  s nejvýše 10 sedadly. Evidence: `intent-and-change/C02-Operations-and-Requirements.md`, `intent-and-change/C02-Domain-Rules.md`,
  `diagrams/c02/state.puml` a aktivity oproti
  `reservation/services.py:_check_lead_time`, `_requires_approval`,
  `confirm_reservation`, `touch_reservation` a příslušným testům.
- **F2 — C03, VERIFIED FINDING:** statická architektura (G2), sekvence Confirm (H1) a C03 evidence stále uvádějí
  post-commit adaptér, runtime a nasazení (G4) neukazuje dispatcher. Skutečná cesta je
  `_notify` → `notification.services.record_notification` uvnitř
  rezervační transakce; doručuje samostatný dispatcher mimo transakci.
  Citovaný test `test_notification_side_effect_is_isolated_to_integration_adapter`
  v aktuální sadě neexistuje. C05 sice označuje starý návrh za historický,
  ale původní pohledy a PASS zůstávají neoznačené. ADR také připouští
  dispatch ve smyčce expirace, zatímco implementace používá samostatný
  příkaz `dispatch_notifications --watch`.
- **F3 — C05, VERIFIED FINDING:** Stavový model a pseudokód DD vynechávají
  `expirovaný lease + attempts >= max → FAILED`.
  `notification/dispatcher.py:_claim` přechod provádí a test
  `test_crash_on_last_attempt_becomes_failed_without_another_send`
  jej kontroluje. C05 evidence slibuje úpravu DD, která v tagu `C05`
  chybí. Selhání uložená tímto úklidem se navíc nezapočítávají do
  `counts["failed"]` vráceného dispatcherem.

## Owner disposition

| Finding | Disposition | Důvod / evidence |
|---|---|---|
| F1 | ACCEPTED — change required | Specifikace a diagramy musí úplně zachycovat implementovaná časová pravidla a prioritu schválení celého sálu. |
| F2 | ACCEPTED — change required | Aktuální outbox neodpovídá starým pohledům a tvrzenému conformance PASS; sjednotit architekturu a evidenci. |
| F3 | ACCEPTED — change required | DD vynechává implementovaný a testem popsaný přechod; vyjasnit také kontrakt počitadla selhání. |

## Actions / justified no-change decisions

- **F1:** Doplnit OP-01/OP-03, odkazy na pravidla a diagramy o časové
  kontroly, schvalovací deadline a obnovu držení; vyloučit celý sál
  z guardu přímého potvrzení. Zachovat implementované časové chování.
- **F2:** Aktualizovat statickou architekturu (G2), runtime a nasazení (G4), sekvenci Confirm (H1) a ADR pro transakční outbox a samostatný
  dispatch worker. Staré závěry označit jako nahrazené; nedoložený PASS
  odstranit nebo nahradit existující opakovatelnou kontrolou.
  Zachovat transakční zápis a doručování mimo transakci.
- **F3:** Doplnit terminální úklid lease do DD modelu a pseudokódu.
  Zachovat ochranu proti věčnému `PENDING`; rozhodnout, zda `failed`
  zahrnuje i úklid, a sjednotit kontrakt, implementaci a test.
- V tagu `C05` nejsou tyto opravy dokončené. Tento zápis je evidencí
  posouzení a rozhodnutí, nikoli důkazem uzavření nálezů. Konkrétní
  vlastníky a termíny navazujících akcí tým dosud neurčil.

## Remaining evidence gaps

- Nový reprodukovatelný běh testů svázaný s tagem `C05`. Původní review
  uvádí úspěšný B2, ale ve F1–F3 tvrdí, že testy nebyly spuštěny;
  tento rozpor nelze považovat za doklad nového ověření.
- Pro položky Q1–Q3 (kvalita a měření, C04) chybí definovaný workload, přijatelné latence a četnost
  `busy` i skutečné měření 20 souběžných rezervací a rozhodnutí z výsledku.
- Chybějí testy souběžného Confirm, Confirm s neaktivním sedadlem,
  souběžných claimů dvou workerů, kladných nastavení, zkrácení chyby
  na 2 000 znaků, outbox DB constraintů a počítání úklidových selhání.
- Sjednotit ownership expirace v pohledu vlastnictví přechodů (G3) s rezervačními službami a zachytit
  lazy expiry. Po opravách doložit návaznost původního tagu `C05`
  na nový reporting commit/tag a důkazy uzavření F1–F3.
