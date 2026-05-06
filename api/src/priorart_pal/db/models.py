"""SQLAlchemy declarative models for PriorArt Pal.

Schema overview (single Postgres database; pgvector extension enabled):

  patents              one row per patent in the corpus (metadata)
  patent_chunks        one row per (patent, claim) chunk we embed
  embeddings           vector(1024) per chunk with HNSW index
  ontology_graphs      JSONB graph extracted by Claude per (patent, claim)
  llm_calls            per-LLM-call cost / latency / token row
  canonical_types      runtime-editable ontology: types
  canonical_synonyms   runtime-editable ontology: synonyms per type
  ontology_changes     append-only audit log of ontology mutations

Design decisions worth flagging here:

- **Citation anchors are pre-grant publication paragraph numbers** per
  ADR-0001. The `chunk_text` column preserves paragraph-numbered markup
  rather than stripping it, so the generation layer can cite anchors
  that round-trip back to highlightable source spans.
- **`ontology_version_hash` on patent_chunks and ontology_graphs** lets
  us mark patents as stale when the ontology changes; re-extraction
  runs lazily on next query (with an admin "re-extract all stale"
  button as escape hatch). Editable ontology design from NOTES.md.
- **Vector dim 1024** matches Voyage `voyage-3-large`. If we ever
  switch embedding models, that's a one-line config change here plus
  re-embedding the corpus.
- **HNSW index** with cosine distance — the standard production AV
  retrieval pattern. m=16, ef_construction=200 are pgvector defaults
  that work well for corpora under ~10M vectors.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

VECTOR_DIM = 1024  # Voyage voyage-3-large


class Base(DeclarativeBase):
    pass


# ─── corpus ──────────────────────────────────────────────────────────


class Patent(Base):
    """One row per patent in the corpus.

    `publication_number` is the canonical identifier — pre-grant pub
    number where available (per ADR-0001), granted patent number for
    pre-2001 references where no pre-grant pub exists.
    """

    __tablename__ = "patents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    publication_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    kind_code: Mapped[str | None] = mapped_column(String(8))
    is_pre_grant: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    cpc_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    assignee: Mapped[str | None] = mapped_column(Text)
    filing_date: Mapped[date | None] = mapped_column(Date)
    grant_date: Mapped[date | None] = mapped_column(Date)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunks: Mapped[list[PatentChunk]] = relationship(
        back_populates="patent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_patents_grant_date", "grant_date"),
        # GIN index for CPC-array filtering (e.g., "match any of B60W30/*")
        Index("ix_patents_cpc_codes", "cpc_codes", postgresql_using="gin"),
    )


class PatentChunk(Base):
    """One row per chunked claim (or paragraph). The unit of embedding."""

    __tablename__ = "patent_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    patent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patents.id", ondelete="CASCADE"), index=True
    )
    # chunk_kind in: 'claim_indep' / 'claim_dep' / 'spec' / 'abstract'
    chunk_kind: Mapped[str] = mapped_column(String(32))
    claim_num: Mapped[int | None] = mapped_column(Integer)
    paragraph_num: Mapped[int | None] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)  # paragraph-numbered markup preserved
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    ontology_version_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    patent: Mapped[Patent] = relationship(back_populates="chunks")
    embedding: Mapped[Embedding | None] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        UniqueConstraint(
            "patent_id", "chunk_kind", "claim_num", "paragraph_num",
            name="uq_chunk_within_patent",
        ),
        CheckConstraint(
            "chunk_kind IN ('claim_indep', 'claim_dep', 'spec', 'abstract')",
            name="ck_chunk_kind_valid",
        ),
    )


class Embedding(Base):
    """Vector embedding per chunk. HNSW-indexed for cosine ANN search."""

    __tablename__ = "embeddings"

    chunk_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("patent_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM))
    model: Mapped[str] = mapped_column(String(64))  # e.g., 'voyage-3-large'
    input_type: Mapped[str] = mapped_column(String(16))  # 'document' / 'query'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunk: Mapped[PatentChunk] = relationship(back_populates="embedding")

    __table_args__ = (
        # HNSW index with cosine distance. m=16 / ef_construction=200 are
        # the well-tuned defaults from pgvector docs for general use under
        # ~10M vectors. ef_search is set per-query in code.
        Index(
            "ix_embeddings_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 200},
        ),
    )


class OntologyGraph(Base):
    """Per-(patent, claim) extracted graph (nodes + edges + content + cites).

    The JSON shape matches docs/ontology-v1.md's example schema.
    """

    __tablename__ = "ontology_graphs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    patent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patents.id", ondelete="CASCADE"), index=True
    )
    claim_num: Mapped[int | None] = mapped_column(Integer)
    graph: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ontology_version_hash: Mapped[str] = mapped_column(String(64))
    extracted_by_model: Mapped[str] = mapped_column(String(64))
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "patent_id", "claim_num", "ontology_version_hash",
            name="uq_graph_per_patent_claim_version",
        ),
        Index(
            "ix_ontology_graphs_graph_gin", "graph", postgresql_using="gin"
        ),
    )


# ─── observability ──────────────────────────────────────────────────


class LlmCall(Base):
    """One row per LLM API call. Surfaces cost / latency / errors at
    `/admin/metrics`."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(32))  # 'embed' / 'rerank' / 'generate' / 'extract'
    provider: Mapped[str] = mapped_column(String(16))  # 'voyage' / 'cohere' / 'anthropic'
    model: Mapped[str] = mapped_column(String(64))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cached_tokens_in: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd_micros: Mapped[int | None] = mapped_column(BigInteger)  # 1e6 micros = $1
    status: Mapped[str] = mapped_column(String(16))  # 'success' / 'error' / 'timeout'
    error_class: Mapped[str | None] = mapped_column(String(128))
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        CheckConstraint(
            "purpose IN ('embed', 'rerank', 'generate', 'extract')",
            name="ck_llm_call_purpose",
        ),
        CheckConstraint(
            "status IN ('success', 'error', 'timeout')",
            name="ck_llm_call_status",
        ),
    )


# ─── editable ontology ──────────────────────────────────────────────


class CanonicalType(Base):
    """Runtime-editable canonical type (ontology node).

    Seeded from `docs/ontology-v1.md` via a one-shot loader on first
    boot; mutated thereafter via admin endpoints. Every change logged
    in `ontology_changes`.
    """

    __tablename__ = "canonical_types"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    # category in: 'node' / 'edge' / 'content' / 'frequency' / 'threshold'
    category: Mapped[str] = mapped_column(String(32))
    parent_type: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("canonical_types.code", ondelete="SET NULL"),
    )
    description: Mapped[str] = mapped_column(Text)
    extraction_rule: Mapped[str | None] = mapped_column(Text)
    disambiguation: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    typical_subsystems: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    synonyms: Mapped[list[CanonicalSynonym]] = relationship(
        back_populates="canonical_type",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('node', 'edge', 'content', 'frequency', 'threshold')",
            name="ck_canonical_type_category",
        ),
    )


class CanonicalSynonym(Base):
    """Surface forms that map to a canonical type. Per-query filtering
    references is_active + tightness."""

    __tablename__ = "canonical_synonyms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    canonical_code: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("canonical_types.code", ondelete="CASCADE"),
        index=True,
    )
    surface_form: Mapped[str] = mapped_column(Text)
    tightness: Mapped[str] = mapped_column(String(8))  # 'tight' / 'loose'
    # source in: 'seed' / 'examiner' / 'corpus_mining'
    source: Mapped[str] = mapped_column(String(16), default="seed")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    canonical_type: Mapped[CanonicalType] = relationship(back_populates="synonyms")

    __table_args__ = (
        UniqueConstraint(
            "canonical_code", "surface_form",
            name="uq_synonym_per_canonical",
        ),
        CheckConstraint(
            "tightness IN ('tight', 'loose')",
            name="ck_synonym_tightness",
        ),
        CheckConstraint(
            "source IN ('seed', 'examiner', 'corpus_mining')",
            name="ck_synonym_source",
        ),
    )


class OntologyChange(Base):
    """Append-only audit log of ontology mutations."""

    __tablename__ = "ontology_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(64))
    change_type: Mapped[str] = mapped_column(String(32))
    canonical_code: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)


# Convert numeric currency conveniently — `cost_usd_micros / 1e6` => USD.
USD_PER_MICRO = 0.000001


# Convert numeric currency conveniently
USD_PER_MICRO = 0.000001  # noqa: F841 — exposed for caller convenience
