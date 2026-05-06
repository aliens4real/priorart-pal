"""Sanity tests for the SQLAlchemy model layer.

These don't hit a real database — they verify the model metadata is
internally consistent (table names, FK relationships, index definitions
present). Cheap insurance against accidental schema drift between the
ORM models and the migration.
"""
from __future__ import annotations

from priorart_pal.db.models import (
    VECTOR_DIM,
    Base,
    CanonicalSynonym,
    CanonicalType,
    Embedding,
    LlmCall,
    OntologyChange,
    OntologyGraph,
    Patent,
    PatentChunk,
)


def test_all_eight_tables_present() -> None:
    expected = {
        "patents",
        "patent_chunks",
        "embeddings",
        "ontology_graphs",
        "llm_calls",
        "canonical_types",
        "canonical_synonyms",
        "ontology_changes",
    }
    actual = set(Base.metadata.tables.keys())
    assert expected == actual, f"missing or extra: {expected ^ actual}"


def test_vector_dim_matches_voyage_3_large() -> None:
    """Vector(1024) for voyage-3-large. If we ever swap embedding models,
    this test pins the dimension that the rest of the system expects."""
    assert VECTOR_DIM == 1024
    column = Embedding.__table__.c.embedding
    assert column.type.dim == VECTOR_DIM


def test_chunk_kind_check_constraint_exists() -> None:
    """Ensures only the four valid chunk_kind values are accepted."""
    constraints = [
        c for c in PatentChunk.__table__.constraints if c.name == "ck_chunk_kind_valid"
    ]
    assert len(constraints) == 1


def test_llm_call_purpose_constraint_exists() -> None:
    constraints = [
        c for c in LlmCall.__table__.constraints if c.name == "ck_llm_call_purpose"
    ]
    assert len(constraints) == 1


def test_canonical_type_self_reference() -> None:
    """parent_type FK self-references canonical_types — that's how the
    BRI matcher's hierarchy traversal works."""
    fks = list(CanonicalType.__table__.c.parent_type.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "canonical_types"


def test_canonical_synonym_unique_per_canonical() -> None:
    """A single surface_form maps to at most one canonical_code (within
    that code). Prevents accidental duplicate inserts during seed."""
    constraints = [
        c
        for c in CanonicalSynonym.__table__.constraints
        if getattr(c, "name", None) == "uq_synonym_per_canonical"
    ]
    assert len(constraints) == 1


def test_patent_has_ingested_at_default() -> None:
    """ingested_at is server-side now() — important for "when did this
    patent enter the corpus" queries."""
    assert Patent.__table__.c.ingested_at.server_default is not None


def test_ontology_graph_has_version_hash() -> None:
    """Per-extraction version hash drives staleness detection when the
    ontology mutates."""
    assert "ontology_version_hash" in OntologyGraph.__table__.c
    assert OntologyGraph.__table__.c.ontology_version_hash.nullable is False


def test_ontology_change_is_append_only_in_spirit() -> None:
    """No update timestamp — `OntologyChange` is append-only by design.
    If this test ever fails, someone added an `updated_at` column and
    we should reconsider the audit-log model."""
    columns = {c.name for c in OntologyChange.__table__.c}
    assert "updated_at" not in columns
