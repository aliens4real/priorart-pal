# Diagrams

Software architecture diagrams as D2 source + rendered SVG.

## Convention

- Source: `<name>.d2`
- Rendered: `<name>.svg` (committed alongside source for direct GitHub README rendering)
- Render command: `d2 <name>.d2 <name>.svg`
- Watch mode: `d2 --watch <name>.d2 <name>.svg`

## Current diagrams

| File | Subject |
|---|---|
| [`architecture.svg`](architecture.svg) | System architecture v1 — edge / auth, App Runner, AI providers, data plane, observability |

## Adding a new diagram

1. Write `<name>.d2`. See existing files for style conventions (color classes, layout, label format).
2. Render: `d2 <name>.d2 <name>.svg`
3. Commit both files.

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
