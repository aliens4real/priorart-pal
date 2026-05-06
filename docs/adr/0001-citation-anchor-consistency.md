# ADR-0001: Citation anchors map to pre-grant publication paragraph numbers

**Status:** Accepted
**Date:** 2026-05-05
**Deciders:** @aliens4real (project owner, USPTO Primary Examiner — domain authority)

## Context

A patent has two parallel citation systems that don't always align:

| System | Source format | Citation form |
|---|---|---|
| Paragraph numbers | XML / SGML / structured text — and the form examiners write in office actions | `¶ 0042` |
| Column / line numbers | PDF / printed-page rendering | `col. 5, lines 30–40` |

Worse, the **pre-grant publication** (`-A1` / `-A2` kind codes) and the **granted patent** (`-B1` / `-B2` kind codes) of the same application are **different documents**:

- Amendments during prosecution can change the paragraph structure of the spec
- A `¶ 0042` in the pre-grant pub may not be `¶ 0042` in the granted patent (or may not exist at all)
- Examiners cite prior art by its **pre-grant publication** form because that's the document admissible against later applications

If our system anchors generation cites to the wrong version, every cite the user clicks will land on text that doesn't match what the model claimed — destroying trust instantly.

## Decision

**All paragraph-numbered citations in PriorArt Pal anchor to pre-grant publication text.**

Specifically:

1. **Generation cites** are formatted as `<pre-grant pub no>, ¶<NNNN>` — e.g., `US20180047289A1, ¶0042`. The format makes the version explicit so the reader and the tool agree on which document.

2. **Ingestion preserves paragraph anchors.** When a patent's text is chunked for embedding, the `<para num="0042">…</para>` markup is kept in the stored `chunk_text` field rather than stripped. The retrieval layer indexes the chunked text; the generation layer cites the original anchors.

3. **Where multiple versions exist (pre-grant + granted)**, we ingest the **pre-grant publication** as the canonical text. The granted patent record exists for metadata purposes (citation graph, family info) but is not the source of paragraph anchors.

4. **For pre-2001 patents** (where no pre-grant publication exists — pre-grant publication became standard in 2001 under AIPA), fall back to **column / line citation** against the granted patent: `col. 5, lines 30–40`. The matcher distinguishes between citation styles by document kind code.

5. **When parsing OCE office-action data** (`patents-public-data.uspto_oce_office_actions`), the `cited_pub_no` field already encodes which document the examiner cited. Use that exact form — do **not** normalize to grant.

## Consequences

### Positive

- **Zero citation drift.** What the model cites is what the user sees when they click the cite — both bound to the same document.
- **Aligns with examiner workflow.** Examiners already cite by pre-grant pub no; the system mirrors their convention.
- **Eval ground truth lines up.** Office-action gold sets cite by pre-grant pub no; our retrieval and generation must speak the same language.

### Negative / accepted tradeoffs

- **More storage.** We ingest both pre-grant and granted records when both exist (granted for metadata, pre-grant for text). Roughly 1.5× corpus size.
- **Two citation formats to support.** Pre-2001 patents force column/line citations alongside paragraph-numbered citations. The ontology and the highlighter need to handle both.
- **Slightly more complex ingestion.** Need to detect kind codes and route appropriately.

### Neutral

- This decision aligns with the project owner's existing rule (recorded in personal memory): *"When citing paragraph numbers, use the pre-grant publication number (not the granted patent number)."* The ADR makes that rule explicit at the repo level.

## Implementation notes

- BigQuery `patents-public-data.patents.publications` has both pre-grant and granted rows for the same application — distinguished by `kind_code` (`A1`, `A2` for pre-grant; `B1`, `B2` for granted).
- The `claims_localized.text` and `description_localized.text` fields preserve paragraph markup in most cases — verify during the first ingest sample.
- The structural-retrieval layer's `cite` field on extracted nodes/edges should always reference the pre-grant pub no.

## Related

- [`docs/ontology-v1.md`](../ontology-v1.md) — JSON schema for extracted graphs includes a `cite` field with paragraph anchors. This ADR pins down which document those anchors refer to.
- [`evals/sql/office_actions_eval.sql`](../../evals/sql/office_actions_eval.sql) — the office-action eval set construction. Joins on `cited_pub_no` and pulls pre-grant text where available.
- Project owner's notes on `~/Desktop/patent-analyzer/` — the older Patent Analyzer tool already follows the pre-grant-pub convention; PriorArt Pal continues it.
