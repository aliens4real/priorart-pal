"""Tests for ontology extraction.

Two flavors:

- Schema tests (always run): verify the tool-use schema and the prompt
  builder produce the expected shapes.
- Integration test (`PAP_RUN_LOCAL_DB_TESTS=1`): hits the live Claude
  API to extract one claim. Skipped in CI to avoid spend.
"""
from __future__ import annotations

import os

import pytest

from priorart_pal.extract.extractor import _ontology_version_hash
from priorart_pal.extract.schema import ONTOLOGY_EXTRACT_TOOL


def test_tool_schema_has_required_fields() -> None:
    schema = ONTOLOGY_EXTRACT_TOOL["input_schema"]
    assert schema["required"] == ["nodes", "edges"]
    assert "nodes" in schema["properties"]
    assert "edges" in schema["properties"]
    assert "unmapped" in schema["properties"]


def test_tool_node_requires_canonical_type_surface_form_and_cite() -> None:
    node_schema = ONTOLOGY_EXTRACT_TOOL["input_schema"]["properties"]["nodes"]["items"]
    required = set(node_schema["required"])
    assert {"id", "canonical_type", "surface_form", "cite"} <= required


def test_tool_edge_includes_canonical_relation_in_required() -> None:
    edge_schema = ONTOLOGY_EXTRACT_TOOL["input_schema"]["properties"]["edges"]["items"]
    assert "canonical_relation" in edge_schema["required"]
    # The enum on category enforces the 5 canonical frequency buckets:
    freq_enum = edge_schema["properties"]["frequency"]["properties"]["category"]["enum"]
    assert set(freq_enum) == {
        "REAL_TIME",
        "PERIODIC",
        "EVENT_DRIVEN",
        "ON_DEMAND",
        "ASYNCHRONOUS",
    }


def test_ontology_version_hash_is_stable_and_short() -> None:
    h1 = _ontology_version_hash("ontology v1")
    h2 = _ontology_version_hash("ontology v1")
    h3 = _ontology_version_hash("ontology v1 + a comma")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16


@pytest.mark.skipif(
    os.environ.get("PAP_RUN_LOCAL_DB_TESTS") != "1",
    reason="needs Anthropic API key + live network; opt in via PAP_RUN_LOCAL_DB_TESTS=1",
)
@pytest.mark.asyncio
async def test_extractor_returns_well_shaped_graph() -> None:
    from priorart_pal.extract.extractor import OntologyExtractor

    extractor = OntologyExtractor()
    result = await extractor.extract_one(
        patent_pub_no="US-TEST-CLAIM",
        claim_num=1,
        claim_text=(
            "A vehicle control system comprising: a forward-facing camera "
            "configured to capture image data of a roadway ahead of the "
            "vehicle; a perception module that detects pedestrians from "
            "the image data and outputs an object detection list to a "
            "planning module; and a brake actuator that engages when the "
            "perception module classifies a detected object as a "
            "pedestrian within 30 meters of the vehicle."
        ),
    )
    # Structural sanity, not semantic — we don't lock specific node types.
    assert isinstance(result.graph, dict)
    assert "nodes" in result.graph and len(result.graph["nodes"]) >= 1
    assert "edges" in result.graph
    assert result.input_tokens > 0
    assert result.output_tokens > 0
