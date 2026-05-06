# Seed corpus — autonomous passenger vehicles

This is the v1 ground-truth corpus PriorArt Pal is built against. Confirmed by the project owner (USPTO Primary Examiner in this art) on 2026-05-03.

The seed list is intentionally narrow: 10 foundational patents in autonomous passenger vehicles. The Phase 2 ingestion pipeline will expand this into a full corpus by walking the citation graph (each seed's "cited by" list) — see [`NOTES.md`](../NOTES.md) for the planned method.

## Seed patents

| # | Patent | Assignee | Subject |
|---|---|---|---|
| 1 | [US 9,383,753 B1](https://patents.google.com/patent/US9383753B1) | Waymo (Google) | Reactive control / wide field-of-view rover |
| 2 | [US 9,086,273](https://patents.google.com/patent/US9086273) | Waymo | Lidar / mapping (Uber/Waymo trade-secret case) |
| 3 | [US 9,254,846](https://patents.google.com/patent/US9254846) | Waymo | ML-based predictive vehicle speed control |
| 4 | [US 9,097,800](https://patents.google.com/patent/US9097800) | Waymo | Lidar — 3D point map of vehicle surroundings |
| 5 | [US 8,660,734 B2](https://patents.google.com/patent/US8660734B2) | Google / Waymo | Predicting behaviors of detected objects |
| 6 | [US 10,296,794 B2](https://patents.google.com/patent/US10296794B2) | (third-party) | On-demand AI roadway stewardship |
| 7 | [US 2016/0291134 A1](https://patents.google.com/patent/US20160291134A1) | Waymo | Long-range steerable lidar |
| 8 | [WO 2015/056105 A1](https://patents.google.com/patent/WO2015056105A1) | Mobileye | Forward-facing multi-imaging system for navigation |
| 9 | [US 2020/0257317 A1](https://patents.google.com/patent/US20200257317A1) | Tesla | Autonomous + user-controlled vehicle summon |
| 10 | [US 7,923,144 B2](https://patents.google.com/patent/US7923144B2) | Tesla | (Tesla's most-cited overall — verify AV-relevance during ingest) |

## Why these

- **Foundational for the art.** Heavily cited by downstream filers, including in continuations and child applications.
- **Architectural diversity.** Lidar-first (Waymo), vision-first (Mobileye), camera-only with neural compute (Tesla). The structural retrieval needs to discriminate between these architectures.
- **Anchors for citation-graph expansion.** Each patent's "cited by" list on Google Patents is a clean 1-hop expansion path into the broader corpus.

## Expansion plan (Phase 2)

1. Ingest all 10 seed patents end-to-end first (download → parse → extract structure → embed → store).
2. For each seed, fetch the "cited by" list from Google Patents — capped at top-200 per seed.
3. De-duplicate the union. Expected total: 1,000–1,500 patents (significant overlap across seeds).
4. Ingest the expansion. Estimated cost: dominated by Claude extraction calls (~$0.005/patent at Sonnet pricing with prompt caching enabled). 1,500 × $0.005 = **~$8 one-time**.
5. Reserve ability to re-ingest if the ontology evolves — extracted JSON is stored, not derived on the fly.

## Out of scope for v1 corpus

- Foreign patents (EP, JP, KR, CN) — same art, but parsing complexity isn't worth it for v1.
- Pre-1995 patents — older formatting, less relevant to modern AV architecture.
- Non-passenger (commercial trucks, ag, mining, military) — even if cited, pruned during ingest.
- Non-patent literature (papers, standards). Maybe v2.
