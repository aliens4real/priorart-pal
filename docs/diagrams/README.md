# Diagrams

Two tools, two purposes:

- **D2** for **structural / system architecture diagrams** (boxes, layers, deployment topologies). Source `.d2` files live here; rendered `.svg` is committed alongside.
- **Mermaid** for **flow / pipeline diagrams** (data flow, sequence, RAG pipeline). Embedded inline in markdown — GitHub renders it natively, no compile step.

## When to use which

| Diagram type | Tool | Where it lives |
|---|---|---|
| Static architecture (deployment, components, layers) | D2 | `docs/diagrams/<name>.d2` + `<name>.svg` |
| Data flow / RAG pipeline / ML stages | Mermaid | Inline in `README.md`, `NOTES.md`, etc. |
| Sequence (interaction over time) | Mermaid | Inline in markdown |
| Hand-drawn presentation slides (interview-time) | Excalidraw | Separate tool, not committed here |

## D2 workflow

- Source: `<name>.d2`
- Rendered: `<name>.svg` (committed alongside source for direct GitHub README rendering)
- Render command: `d2 <name>.d2 <name>.svg`
- Watch mode: `d2 --watch <name>.d2 <name>.svg`

## Current diagrams

| File | Tool | Subject |
|---|---|---|
| [`architecture.svg`](architecture.svg) | D2 | System architecture v1 — edge / auth, App Runner, AI providers, data plane, observability |
| _(in repo `README.md`)_ | Mermaid | RAG pipeline — ingestion + query stages with ML concept callouts |

## Adding a new diagram

**For D2** (architecture / static structure):

1. Write `<name>.d2`. See existing files for style conventions (color classes, layout, label format).
2. Render: `d2 <name>.d2 <name>.svg`
3. Commit both files.

**For Mermaid** (flow / sequence / pipeline):

1. Author the diagram inline in the markdown file where it belongs (`README.md`, a `NOTES.md` section, etc.) wrapped in a ` ```mermaid ` code fence.
2. Verify it renders correctly by viewing the file on GitHub (or via VS Code's Mermaid preview extension).
3. No SVG to commit.

## Color classes (used across diagrams)

| Class | Used for | Color |
|---|---|---|
| `external` | User / outside-the-system actors | indigo |
| `aws` | AWS-managed services | amber |
| `ai` | External AI providers (Voyage, Cohere, Anthropic) | violet |
| `data` | Data plane (RDS, Secrets Manager) | green |
| `obs` | Observability + cost guardrails | yellow |

## Tip — escapes

D2 treats `$` as variable-substitution start. To put a literal `$` in a label, write `\$` or rephrase ("USD 20" instead of "$20"). Same caution for `{` and `}` in labels.
