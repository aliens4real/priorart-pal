"""Quick sanity check that HNSW retrieval works end-to-end.

Embeds a single query via Voyage (input_type='query'), runs an ANN search
against the embeddings table, prints the top-K patents.

Usage:
    cd api && uv run python ../scripts/sanity_search.py "your query text"

If no query passed, uses a default about lane-keeping perception.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_API_SRC = Path(__file__).resolve().parent.parent / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from sqlalchemy import select  # noqa: E402

from priorart_pal.db.models import Embedding, Patent, PatentChunk  # noqa: E402
from priorart_pal.db.session import close_engine, get_sessionmaker  # noqa: E402
from priorart_pal.embed.voyage import VoyageEmbedder  # noqa: E402

DEFAULT_QUERY = (
    "A perception module that detects pedestrians and cyclists ahead of "
    "the vehicle using a forward-facing camera and lidar fusion, then "
    "passes detections to a behavior planner."
)
TOP_K = 5


async def main() -> int:
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUERY
    print(f"\nQuery:\n  {query}\n")

    embedder = VoyageEmbedder()
    qvec = await embedder.embed_query(query)
    print(f"Embedded query (1024-dim Voyage voyage-3-large)")

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        # pgvector cosine distance: smaller = more similar
        stmt = (
            select(
                Patent.publication_number,
                Patent.title,
                PatentChunk.claim_num,
                Embedding.embedding.cosine_distance(qvec).label("distance"),
            )
            .join(PatentChunk, PatentChunk.id == Embedding.chunk_id)
            .join(Patent, Patent.id == PatentChunk.patent_id)
            .order_by("distance")
            .limit(TOP_K)
        )
        result = await session.execute(stmt)
        rows = result.all()

    print(f"\nTop-{TOP_K} matches (by cosine distance, lower = more similar):\n")
    for i, (pub_no, title, claim, distance) in enumerate(rows, start=1):
        print(f"  {i}. [{distance:.4f}]  {pub_no}  claim {claim}")
        print(f"      {(title or '')[:90]}")
        print()

    await close_engine()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
