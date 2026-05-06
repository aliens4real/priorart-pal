"""initial schema — 8 tables + pgvector extension + HNSW index

Revision ID: 0001
Revises:
Create Date: 2026-05-05

Tables created:
  patents              corpus metadata
  patent_chunks        per-(patent, claim) chunked text we embed
  embeddings           vector(1024) per chunk; HNSW cosine index
  ontology_graphs      JSONB graph extracted by Claude per patent/claim
  llm_calls            per-LLM-call metrics row (cost / latency / tokens)
  canonical_types      runtime-editable ontology: types
  canonical_synonyms   runtime-editable ontology: surface forms
  ontology_changes     append-only audit log of ontology mutations

Hand-written rather than `alembic revision --autogenerate` because:
- pgvector's HNSW index syntax is not detected by autogen
- GIN indexes on JSONB / array columns need explicit `postgresql_using`
- We want the `CREATE EXTENSION` statement under our control
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIM = 1024


def upgrade() -> None:
    # 1. pgvector extension. Idempotent.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. patents
    op.create_table(
        "patents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("publication_number", sa.String(32), nullable=False, unique=True),
        sa.Column("kind_code", sa.String(8)),
        sa.Column("is_pre_grant", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("title", sa.Text()),
        sa.Column("abstract", sa.Text()),
        sa.Column("cpc_codes", postgresql.ARRAY(sa.String(32))),
        sa.Column("assignee", sa.Text()),
        sa.Column("filing_date", sa.Date()),
        sa.Column("grant_date", sa.Date()),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_patents_publication_number", "patents", ["publication_number"])
    op.create_index("ix_patents_grant_date", "patents", ["grant_date"])
    op.create_index(
        "ix_patents_cpc_codes", "patents", ["cpc_codes"], postgresql_using="gin"
    )

    # 3. patent_chunks
    op.create_table(
        "patent_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "patent_id",
            sa.BigInteger(),
            sa.ForeignKey("patents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_kind", sa.String(32), nullable=False),
        sa.Column("claim_num", sa.Integer()),
        sa.Column("paragraph_num", sa.Integer()),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer()),
        sa.Column("char_end", sa.Integer()),
        sa.Column("ontology_version_hash", sa.String(64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "patent_id", "chunk_kind", "claim_num", "paragraph_num",
            name="uq_chunk_within_patent",
        ),
        sa.CheckConstraint(
            "chunk_kind IN ('claim_indep', 'claim_dep', 'spec', 'abstract')",
            name="ck_chunk_kind_valid",
        ),
    )
    op.create_index("ix_patent_chunks_patent_id", "patent_chunks", ["patent_id"])

    # 4. embeddings
    op.create_table(
        "embeddings",
        sa.Column(
            "chunk_id",
            sa.BigInteger(),
            sa.ForeignKey("patent_chunks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_type", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # HNSW index with cosine distance. m=16 / ef_construction=200 are
    # well-tuned defaults from pgvector docs for corpora under ~10M vectors.
    op.execute(
        "CREATE INDEX ix_embeddings_hnsw_cosine "
        "ON embeddings USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 200)"
    )

    # 5. ontology_graphs
    op.create_table(
        "ontology_graphs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "patent_id",
            sa.BigInteger(),
            sa.ForeignKey("patents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_num", sa.Integer()),
        sa.Column("graph", postgresql.JSONB(), nullable=False),
        sa.Column("ontology_version_hash", sa.String(64), nullable=False),
        sa.Column("extracted_by_model", sa.String(64), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "patent_id", "claim_num", "ontology_version_hash",
            name="uq_graph_per_patent_claim_version",
        ),
    )
    op.create_index("ix_ontology_graphs_patent_id", "ontology_graphs", ["patent_id"])
    op.create_index(
        "ix_ontology_graphs_graph_gin",
        "ontology_graphs",
        ["graph"],
        postgresql_using="gin",
    )

    # 6. llm_calls
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("tokens_in", sa.Integer()),
        sa.Column("tokens_out", sa.Integer()),
        sa.Column("cached_tokens_in", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("cost_usd_micros", sa.BigInteger()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_class", sa.String(128)),
        sa.Column("user_id", sa.String(64)),
        sa.Column(
            "called_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "purpose IN ('embed', 'rerank', 'generate', 'extract')",
            name="ck_llm_call_purpose",
        ),
        sa.CheckConstraint(
            "status IN ('success', 'error', 'timeout')",
            name="ck_llm_call_status",
        ),
    )
    op.create_index("ix_llm_calls_request_id", "llm_calls", ["request_id"])
    op.create_index("ix_llm_calls_user_id", "llm_calls", ["user_id"])
    op.create_index("ix_llm_calls_called_at", "llm_calls", ["called_at"])

    # 7. canonical_types (ontology — types). Self-referencing parent_type FK.
    op.create_table(
        "canonical_types",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column(
            "parent_type",
            sa.String(64),
            sa.ForeignKey("canonical_types.code", ondelete="SET NULL"),
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("extraction_rule", sa.Text()),
        sa.Column("disambiguation", sa.Text()),
        sa.Column("attributes", postgresql.JSONB()),
        sa.Column("typical_subsystems", postgresql.ARRAY(sa.String(64))),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "category IN ('node', 'edge', 'content', 'frequency', 'threshold')",
            name="ck_canonical_type_category",
        ),
    )

    # 8. canonical_synonyms
    op.create_table(
        "canonical_synonyms",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "canonical_code",
            sa.String(64),
            sa.ForeignKey("canonical_types.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("surface_form", sa.Text(), nullable=False),
        sa.Column("tightness", sa.String(8), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="seed"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "canonical_code", "surface_form", name="uq_synonym_per_canonical"
        ),
        sa.CheckConstraint(
            "tightness IN ('tight', 'loose')", name="ck_synonym_tightness"
        ),
        sa.CheckConstraint(
            "source IN ('seed', 'examiner', 'corpus_mining')",
            name="ck_synonym_source",
        ),
    )
    op.create_index(
        "ix_canonical_synonyms_canonical_code",
        "canonical_synonyms",
        ["canonical_code"],
    )

    # 9. ontology_changes (audit log)
    op.create_table(
        "ontology_changes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("user_id", sa.String(64)),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("canonical_code", sa.String(64)),
        sa.Column("before", postgresql.JSONB()),
        sa.Column("after", postgresql.JSONB()),
        sa.Column("reason", sa.Text()),
    )
    op.create_index("ix_ontology_changes_changed_at", "ontology_changes", ["changed_at"])


def downgrade() -> None:
    # Drop in reverse-dependency order.
    op.drop_index("ix_ontology_changes_changed_at", table_name="ontology_changes")
    op.drop_table("ontology_changes")

    op.drop_index(
        "ix_canonical_synonyms_canonical_code", table_name="canonical_synonyms"
    )
    op.drop_table("canonical_synonyms")

    op.drop_table("canonical_types")

    op.drop_index("ix_llm_calls_called_at", table_name="llm_calls")
    op.drop_index("ix_llm_calls_user_id", table_name="llm_calls")
    op.drop_index("ix_llm_calls_request_id", table_name="llm_calls")
    op.drop_table("llm_calls")

    op.drop_index("ix_ontology_graphs_graph_gin", table_name="ontology_graphs")
    op.drop_index("ix_ontology_graphs_patent_id", table_name="ontology_graphs")
    op.drop_table("ontology_graphs")

    op.execute("DROP INDEX IF EXISTS ix_embeddings_hnsw_cosine")
    op.drop_table("embeddings")

    op.drop_index("ix_patent_chunks_patent_id", table_name="patent_chunks")
    op.drop_table("patent_chunks")

    op.drop_index("ix_patents_cpc_codes", table_name="patents")
    op.drop_index("ix_patents_grant_date", table_name="patents")
    op.drop_index("ix_patents_publication_number", table_name="patents")
    op.drop_table("patents")

    # Don't drop the extension — other databases on the cluster may use it.
