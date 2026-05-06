"""Run Claude ontology extraction over the seeded patent corpus.

Pulls patent_chunks that don't yet have a graph for the current
ontology_version_hash, calls the OntologyExtractor, writes resulting
graphs to ontology_graphs.

Idempotent across runs:
  - Skips chunks that already have a graph at the current version hash.
  - On ontology change (different hash), re-extraction runs naturally
    because the unique constraint is (patent_id, claim_num, hash).

Usage (from repo root):

    cd api && uv run python ../scripts/extract_graphs.py --limit 5      # smoke
    cd api && uv run python ../scripts/extract_graphs.py                # full run
    cd api && uv run python ../scripts/extract_graphs.py --concurrency 5

Cost estimate: ~\$0.015-\$0.04 per claim with prompt caching enabled.
1,430 claims => ~\$22-\$57 worst case. Run --limit small first.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

_API_SRC = Path(__file__).resolve().parent.parent / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from sqlalchemy import select  # noqa: E402

from priorart_pal.db.models import OntologyGraph, Patent, PatentChunk  # noqa: E402
from priorart_pal.db.session import close_engine, get_sessionmaker  # noqa: E402
from priorart_pal.extract.extractor import OntologyExtractor  # noqa: E402
from priorart_pal.logging_config import configure_logging, get_logger  # noqa: E402

# Anthropic Sonnet pricing (verify in their billing docs if it changes).
# Used only for the cost estimate printed at the end.
COST_USD_PER_M_INPUT_UNCACHED = 3.0
COST_USD_PER_M_INPUT_CACHED = 0.30
COST_USD_PER_M_OUTPUT = 15.0


@dataclass
class ExtractStats:
    chunks_in_scope: int = 0
    chunks_skipped: int = 0
    chunks_extracted: int = 0
    extract_failed: int = 0
    input_tokens_uncached: int = 0
    input_tokens_cached: int = 0
    output_tokens: int = 0
    elapsed_sec: float = 0.0
    failures: list[tuple[str, int, str]] = field(default_factory=list)

    @property
    def estimated_cost_usd(self) -> float:
        return (
            (self.input_tokens_uncached / 1_000_000) * COST_USD_PER_M_INPUT_UNCACHED
            + (self.input_tokens_cached / 1_000_000) * COST_USD_PER_M_INPUT_CACHED
            + (self.output_tokens / 1_000_000) * COST_USD_PER_M_OUTPUT
        )


async def _select_pending_chunks(session, ontology_version_hash: str, limit: int | None):
    """Find chunks that don't yet have a graph at the current ontology version."""
    # Subquery: chunk ids that already have a graph at this hash
    have_graph = (
        select(OntologyGraph.patent_id, OntologyGraph.claim_num)
        .where(OntologyGraph.ontology_version_hash == ontology_version_hash)
        .subquery()
    )
    stmt = (
        select(
            PatentChunk.id,
            PatentChunk.patent_id,
            PatentChunk.claim_num,
            PatentChunk.chunk_text,
            Patent.publication_number,
        )
        .join(Patent, Patent.id == PatentChunk.patent_id)
        .outerjoin(
            have_graph,
            (have_graph.c.patent_id == PatentChunk.patent_id)
            & (have_graph.c.claim_num == PatentChunk.claim_num),
        )
        .where(
            PatentChunk.chunk_kind == "claim_indep",
            have_graph.c.patent_id.is_(None),
        )
        .order_by(PatentChunk.id)
    )
    if limit:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.all()


async def _process_chunk(
    extractor: OntologyExtractor,
    sem: asyncio.Semaphore,
    chunk_row,
    sessionmaker,
    stats: ExtractStats,
    log,  # noqa: ANN001
):
    pub_no = chunk_row.publication_number
    claim_num = chunk_row.claim_num or 0
    text = chunk_row.chunk_text

    async with sem:
        try:
            result = await extractor.extract_one(
                patent_pub_no=pub_no,
                claim_num=claim_num,
                claim_text=text,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("extract.failed", patent=pub_no, claim=claim_num, err=type(exc).__name__, msg=str(exc)[:200])
            stats.extract_failed += 1
            stats.failures.append((pub_no, claim_num, type(exc).__name__))
            return

    # Persist
    async with sessionmaker() as session:
        graph_row = OntologyGraph(
            patent_id=chunk_row.patent_id,
            claim_num=claim_num,
            graph=result.graph,
            ontology_version_hash=result.ontology_version_hash,
            extracted_by_model=result.model,
        )
        session.add(graph_row)
        await session.commit()

    stats.chunks_extracted += 1
    uncached_in = max(result.input_tokens - result.cached_input_tokens, 0)
    stats.input_tokens_uncached += uncached_in
    stats.input_tokens_cached += result.cached_input_tokens
    stats.output_tokens += result.output_tokens

    nodes_n = len(result.graph.get("nodes", []))
    edges_n = len(result.graph.get("edges", []))
    unmapped_n = len(result.graph.get("unmapped", []))
    log.info(
        "extract.ok",
        patent=pub_no,
        claim=claim_num,
        nodes=nodes_n,
        edges=edges_n,
        unmapped=unmapped_n,
        in_tok=result.input_tokens,
        cached_tok=result.cached_input_tokens,
        out_tok=result.output_tokens,
    )


async def run(*, limit: int | None, concurrency: int) -> ExtractStats:
    log = get_logger(__name__)
    stats = ExtractStats()
    started = perf_counter()

    extractor = OntologyExtractor()
    log.info("extract.start", ontology_version_hash=extractor.ontology_version_hash)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        chunks = await _select_pending_chunks(
            session, extractor.ontology_version_hash, limit
        )
    stats.chunks_in_scope = len(chunks)
    log.info("extract.scope", chunks=len(chunks))

    if not chunks:
        log.info("extract.nothing_to_do")
        return stats

    sem = asyncio.Semaphore(concurrency)
    tasks = [_process_chunk(extractor, sem, c, sessionmaker, stats, log) for c in chunks]
    await asyncio.gather(*tasks)

    stats.elapsed_sec = perf_counter() - started
    return stats


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="extract only first N pending chunks")
    parser.add_argument("--concurrency", type=int, default=4, help="max parallel Claude calls (default 4)")
    args = parser.parse_args()

    configure_logging()
    stats = await run(limit=args.limit, concurrency=args.concurrency)

    print()
    print("=" * 60)
    print(f"  extract @ {datetime.now(UTC).isoformat()}")
    print("=" * 60)
    print(f"  chunks in scope:    {stats.chunks_in_scope}")
    print(f"  chunks extracted:   {stats.chunks_extracted}")
    print(f"  chunks failed:      {stats.extract_failed}")
    print(f"  input tokens (uncached): {stats.input_tokens_uncached:>10,}")
    print(f"  input tokens (cached):   {stats.input_tokens_cached:>10,}")
    print(f"  output tokens:           {stats.output_tokens:>10,}")
    print(f"  estimated cost:          ${stats.estimated_cost_usd:>10.3f}")
    print(f"  elapsed:                 {stats.elapsed_sec:>10.1f}s")
    if stats.failures[:5]:
        print()
        print("  first 5 failures:")
        for pub, claim, err in stats.failures[:5]:
            print(f"    {pub} claim {claim}: {err}")
    print()

    await close_engine()
    return 0 if stats.extract_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
