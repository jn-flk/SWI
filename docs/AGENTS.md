# Agent rules for `docs/`

Rules for anyone (person or AI agent) who edits the documentation.

## Structure

| Folder | Contents |
|---|---|
| `intent-and-change/` | What the system must do: domain, rules, states, operations |
| `architecture-and-decisions/` | How the system is built and why |
| `evidence-and-evolution/` | Proof: tests, verification, assessment, risks |
| `diagrams/c0X/` | PlantUML sources (`.puml`) and rendered images (`.png`) |

- One file per exercise and topic: `C0X-Short-Topic.md`, for example `C05-Detailed-Design.md`.
- The first-level heading is `# C0X — Title`.
- Under the heading, each document has one navigation line: links to the
  navigator, the traceability table and the other documents of the same exercise.
- [NAVIGATOR.md](NAVIGATOR.md) is the index of all documents.
- [TRACEABILITY.md](TRACEABILITY.md) links each requirement and rule to code and tests.

## After every change

1. **Update the navigator.** A new, renamed, moved or deleted document or
   diagram must be reflected in [NAVIGATOR.md](NAVIGATOR.md) and in the
   navigation lines of the related documents.
2. **Update traceability.** A new or changed requirement, rule, service
   function or test must be reflected in [TRACEABILITY.md](TRACEABILITY.md).
3. **Keep every link working.** When a file moves or is renamed, update all
   links to it in `docs/` and in the root `README.md`.
4. **Run the link check** from the repository root. It must print `broken 0`.

```bash
python3 -c "
import os, re
bad = n = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git', 'venv', '.venv', 'node_modules')]
    for f in files:
        if not f.endswith('.md'):
            continue
        p = os.path.join(root, f)
        t = open(p, encoding='utf-8').read()
        t = re.sub(r'(?s)\`\`\`.*?\`\`\`', '', t)
        refs = re.findall(r'\]\(([^)\s]+)\)', t) + re.findall(r'(?m)^\[[^\]]+\]: (\S+)', t)
        for x in refs:
            if x.startswith(('http', '#', 'mailto:')):
                continue
            n += 1
            if not os.path.exists(os.path.normpath(os.path.join(root, x.split('#')[0]))):
                print('BROKEN', p, x)
                bad += 1
print('links', n, 'broken', bad)
"
```

## Writing style

- **Short and to the point.** One idea per sentence. Cut filler.
- **Descriptive.** Say what something is or does, not only its ID.
- **No obfuscation.** Give every code its name, for example
  `BR-04 (Confirmation policy)`, `OP-03 (Confirm Reservation)` or
  `statická architektura (G2)`. Explain jargon once, or link to where it is
  explained, such as the "Glossary" section in
  [C05-Detailed-Design.md](architecture-and-decisions/C05-Detailed-Design.md).
- **Readable formatting.** Labels are headings or bold, never plain text that
  runs into the next line. Use lists and tables for anything list-like.
- **Language.** All headings and bold labels are in English. Body text is in
  Czech. File names, BR/OP names and code identifiers stay in English.

## Accuracy

- Do not change facts, numbers, commit hashes or test names while rewording.
- Every claim of "verified" or "PASS" needs a test, command output or file
  that exists at the stated commit.
- Mark anything without evidence as `NOT VERIFIED`.
