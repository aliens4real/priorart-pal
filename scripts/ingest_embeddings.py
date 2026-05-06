"""Ingest the seed corpus into Postgres + pgvector.

Reads `data_cache/independent_claims.jsonl` (output of the BigQuery →
extract_independent_claims.py pipeline) and writes:

  patents          one row per patent in the file
  patent_chunks    one row per independent claim
  embeddings       Voyage voyage-3-large 1024-dim vector per chunk

Idempotent: skips patents whose `publication_number` is already in the
database. Re-running is safe but won't re-embed existing patents (rerun
after `DELETE FROM patents WHERE …` if you actually want to re-embed).

Usage (from repo root):

    cd api && uv run python ../scripts/ingest_embeddings.py --limit 5     # smoke
    cd api && uv run python ../scripts/ingest_embeddings.py               # full run

Options:

  --limit N           ingest only first N patents (smoke testing)
  --dry-run           skip Voyage call + DB writes; print what would happen
  --reset-corpus      DROP existing patents (DESTRUCTIVE; asks confirmation)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter

# Make `priorart_pal` importable regardless of how the script is invoked.
# uv's editable install via .pth doesn't always get picked up under
# miniforge-based interpreters; this guarantees src is on sys.path.
_API_SRC = Path(__file__).resolve().parent.parent / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from priorart_pal.db.models import Embedding, Patent, PatentChunk  # noqa: E402
from priorart_pal.db.session import close_engine, get_sessionmaker  # noqa: E402
from priorart_pal.embed.voyage import VOYAGE_BATCH_SIZE, VoyageEmbedder  # noqa: E402
from priorart_pal.logging_config import configure_logging, get_logger  # noqa: E402
from priorart_pal.settings import get_settings  # noqa: E402

DEFAULT_INPUT = (
    Path(__file__).resolve().parent.parent / "data_cache" / "independent_claims.jsonl"
)


@dataclass
class IngestStats:
    patents_in_file: int = 0
    patents_skipped_existing: int = 0
    patents_inserted: int = 0
    chunks_inserted: int = 0
    embeddings_inserted: int = 0
    voyage_tokens: int = 0
    voyage_calls: int = 0
    elapsed_sec: float = 0.0


def _parse_grant_date(s: str | int | None) -> date | None:
    """BigQuery emits grant_date as YYYYMMDD int or string."""
    if s is None:
        return None
    s = str(s).strip()
    if not s or len(s) != 8 or not s.isdigit():
        return None
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _detect_kind_code(publication_number: str) -> tuple[str | None, bool]:
    """Best-effort split of US-1234567-B2 into kind_code + is_pre_grant.

    A1/A2 = pre-grant publication; B1/B2 = granted patent.
    """
    if "-" in publication_number:
        parts = publication_number.split("-")
        if len(parts) >= 3:
            kind = parts[-1]
            is_pre_grant = kind.upper().startswith("A")
            return kind, is_pre_grant
    return None, True  # unknown — assume pre-grant per ADR-0001


async def _existing_pub_numbers(
    session: AsyncSession, pub_numbers: list[str]
) -> set[str]:
    if not pub_numbers:
        return set()
    rows = await session.execute(
        select(Patent.publication_number).where(
            Patent.publication_number.in_(pub_numbers)
        )
    )
    return {row[0] for row in rows.all()}


async def _ingest_batch(
    session: AsyncSession,
    embedder: VoyageEmbedder,
    rows: list[dict],
    stats: IngestStats,
    log,  # noqa: ANN001
) -> None:
    """Process one batch of patents inside a single transaction.

    Each batch: insert Patent rows, flush to get IDs, build PatentChunk rows,
    insert + flush, embed all chunk texts, write Embedding rows. One commit
    per batch keeps memory low and lets Voyage retries roll back cleanly.
    """
    pub_numbers = [r["patent"] for r in rows]
    existing = await _existing_pub_numbers(session, pub_numbers)

    new_rows = [r for r in rows if r["patent"] not in existing]
    stats.patents_skipped_existing += len(rows) - len(new_rows)
    if not new_rows:
        return

    # Insert patents
    patents: list[Patent] = []
    for r in new_rows:
        kind_code, is_pre_grant = _detect_kind_code(r["patent"])
        patents.append(
            Patent(
                publication_number=r["patent"],
                kind_code=kind_code,
                is_pre_grant=is_pre_grant,
                title=r.get("title"),
                cpc_codes=r.get("cpc_codes") or None,
                assignee=r.get("assignee"),
                grant_date=_parse_grant_date(r.get("grant_date")),
            )
        )
    session.add_all(patents)
    await session.flush()
    stats.patents_inserted += len(patents)

    # Build chunks (one per independent claim)
    chunks: list[PatentChunk] = []
    chunk_texts: list[str] = []
    for patent_obj, r in zip(patents, new_rows, strict=True):
        for i, claim in enumerate(r.get("independent_claims", []), start=1):
            claim_text = (claim or "").strip()
            if not claim_text:
                continue
            chunk = PatentChunk(
                patent_id=patent_obj.id,
                chunk_kind="claim_indep",
                claim_num=i,
                paragraph_num=None,
                chunk_text=claim_text,
                char_start=None,
                char_end=None,
                ontology_version_hash=None,  # filled in Phase 3 alongside extraction
            )
            chunks.append(chunk)
            chunk_texts.append(claim_text)

    if not chunks:
        return

    session.add_all(chunks)
    await session.flush()
    stats.chunks_inserted += len(chunks)

    # Embed — one Voyage call per VOYAGE_BATCH_SIZE chunks
    log.info("embed.start", chunks=len(chunks), batches=(len(chunks) + VOYAGE_BATCH_SIZE - 1) // VOYAGE_BATCH_SIZE)
    result = await embedder.embed_documents(chunk_texts)
    stats.voyage_tokens += result.total_tokens
    stats.voyage_calls += 1 + (len(chunks) - 1) // VOYAGE_BATCH_SIZE

    # Write embeddings
    for chunk, vec in zip(chunks, result.embeddings, strict=True):
        session.add(
            Embedding(
                chunk_id=chunk.id,
                embedding=vec,
                model=result.model,
                input_type=result.input_type,
            )
        )
    stats.embeddings_inserted += len(chunks)
    await session.commit()


async def run(input_path: Path, *, limit: int | None, dry_run: bool) -> IngestStats:
    log = get_logger(__name__)
    stats = IngestStats()
    started = perf_counter()

    # Load JSONL
    log.info("ingest.load", path=str(input_path))
    rows: list[dict] = []
    with input_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if limit:
        rows = rows[:limit]
    stats.patents_in_file = len(rows)
    log.info("ingest.loaded", patents=len(rows))

    if dry_run:
        chunks_total = sum(len(r.get("independent_claims", [])) for r in rows)
        chars_total = sum(
            sum(len(c or "") for c in r.get("independent_claims", []))
            for r in rows
        )
        # Voyage charges by tokens, ~4 chars/token.
        log.info(
            "ingest.dry_run",
            patents=len(rows),
            chunks=chunks_total,
            estimated_tokens=chars_total // 4,
            estimated_voyage_calls=(chunks_total + VOYAGE_BATCH_SIZE - 1) // VOYAGE_BATCH_SIZE,
        )
        return stats

    # Ingest in batches; one batch = one DB transaction
    embedder = VoyageEmbedder()
    sessionmaker = get_sessionmaker()
    BATCH = 25  # patents per DB tx — small enough to roll back cleanly on error
    for batch_start in range(0, len(rows), BATCH):
        batch = rows[batch_start : batch_start + BATCH]
        log.info(
            "ingest.batch",
            batch_start=batch_start,
            batch_size=len(batch),
            cumulative_inserted=stats.patents_inserted,
        )
        async with sessionmaker() as session:
            await _ingest_batch(session, embedder, batch, stats, log)

    stats.elapsed_sec = perf_counter() - started
    return stats


async def reset_corpus() -> None:
    """DESTRUCTIVE — wipes patents, patent_chunks, embeddings, ontology_graphs."""
    print("⚠️  This will DELETE ALL patents, chunks, embeddings, and graphs.")
    print(f"   Database: {get_settings().database_url}")
    if input("Type 'yes' to confirm: ").strip().lower() != "yes":
        print("Aborted.")
        return
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(text("TRUNCATE patents, patent_chunks, embeddings, ontology_graphs CASCADE"))
        await session.commit()
    print("✓ Corpus reset.")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--limit", type=int, default=None, help="ingest only first N patents")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset-corpus", action="store_true")
    args = parser.parse_args()

    configure_logging()

    if args.reset_corpus:
        await reset_corpus()
        return 0

    if not args.input.exists():
        print(f"ERROR: {args.input} not found. Run scripts/extract_independent_claims.py first.")
        return 2

    stats = await run(args.input, limit=args.limit, dry_run=args.dry_run)
    print()
    print("=" * 60)
    print(f"  ingest @ {datetime.now(UTC).isoformat()}")
    print("=" * 60)
    print(f"  patents in file:        {stats.patents_in_file}")
    print(f"  patents skipped (exist): {stats.patents_skipped_existing}")
    print(f"  patents inserted:        {stats.patents_inserted}")
    print(f"  chunks inserted:         {stats.chunks_inserted}")
    print(f"  embeddings inserted:     {stats.embeddings_inserted}")
    print(f"  voyage tokens:           {stats.voyage_tokens:,}")
    print(f"  voyage calls:            {stats.voyage_calls}")
    print(f"  elapsed:                 {stats.elapsed_sec:.1f}s")
    print()

    await close_engine()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
