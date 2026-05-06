# CONTEXT.md

Domain glossary for **PriorArt Pal**. This file is intentionally a stub — terms accrue here lazily as `/grill-with-docs` resolves them. **Do not pre-fill it.** Each entry should be earned by an actual conversation that pinned the term down.

## Domain glossary

_Empty stub. Add entries as terminology gets resolved._

The term entry format is:

```markdown
### Term Name

One-paragraph definition that's the source of truth when the term is ambiguous.

**Synonyms:** other words that map to this term in this project (used in claim-mining and structural retrieval).

**Avoid:** synonyms or near-misses we explicitly do NOT use.

**Where it appears:** which subsystem(s) this term shows up in.
```

## Where to look beyond this file

For the canonical-type vocabulary used by the structural retriever (node types like `TELEMATICS_CONTROLLER`, edge types like `SENDS_TO`, content types like `OBJECT_TRACK_LIST`), see **[`docs/ontology-v1.md`](docs/ontology-v1.md)**. That file is the live source of truth for the matcher's vocabulary.

For architectural decisions, see **[`docs/adr/`](docs/adr/)**.
