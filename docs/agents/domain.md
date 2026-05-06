# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This is a **single-context repo**. There's one `CONTEXT.md` at the root and one `docs/adr/` directory for architectural decision records.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — domain glossary, terminology, what the project means by its key terms
- **`docs/adr/`** — read ADRs that touch the area you're about to work in

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure

```
/
├── CONTEXT.md
├── docs/
│   ├── adr/
│   │   ├── 0001-<decision>.md     ← architectural decision records
│   │   └── 0002-<decision>.md
│   ├── agents/                    ← this directory; how skills should behave
│   ├── diagrams/                  ← D2 source + rendered SVGs
│   ├── ontology-v1.md             ← canonical types for the structural retriever
│   └── seed-corpus.md             ← v1 seed list of foundational patents
└── src/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

For PriorArt Pal specifically, also defer to **`docs/ontology-v1.md`** for the canonical-type vocabulary used by the structural retriever. It's the source of truth for node types, edge types, content types, and synonym lists. Editing it is part of the domain work, not an aside.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
