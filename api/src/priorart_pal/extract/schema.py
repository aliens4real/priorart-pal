"""Tool-use schema for ontology graph extraction.

We pass this schema to Claude as the input_schema of a single tool. The
model is then forced to call the tool, which guarantees the output is
valid JSON matching the shape we expect — much more reliable than
asking for "JSON" in the prompt.

Schema mirrors the example in `docs/ontology-v1.md` (§"JSON schema").
"""
from __future__ import annotations

from typing import Any

ONTOLOGY_EXTRACT_TOOL: dict[str, Any] = {
    "name": "extract_ontology_graph",
    "description": (
        "Extract the structural representation of a patent claim per "
        "the PriorArt Pal ontology v1. Identify components (nodes), "
        "the relations between them (edges), the data flowing over "
        "those edges (content), and the source character spans. Map "
        "each surface form to a canonical type from the ontology. If "
        "you encounter a phrase that doesn't fit any canonical type, "
        "add it to the `unmapped` list rather than guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "description": "Components / modules / entities mentioned in the claim.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Local identifier within this graph, e.g. 'n1'.",
                        },
                        "canonical_type": {
                            "type": "string",
                            "description": (
                                "The canonical code from the ontology "
                                "(e.g., PERCEPTION_MODULE)."
                            ),
                        },
                        "surface_form": {
                            "type": "string",
                            "description": (
                                "The phrase actually used in the claim "
                                "(e.g., 'object detection neural network')."
                            ),
                        },
                        "attributes": {
                            "type": "object",
                            "description": (
                                "Per-type attributes from the ontology "
                                "(e.g., for RANGING_SENSOR: modality=lidar). "
                                "Empty object if none."
                            ),
                        },
                        "cite": {
                            "type": "object",
                            "description": "Where this node was identified in the source text.",
                            "properties": {
                                "char_start": {"type": "integer"},
                                "char_end": {"type": "integer"},
                            },
                            "required": ["char_start", "char_end"],
                        },
                    },
                    "required": ["id", "canonical_type", "surface_form", "cite"],
                },
            },
            "edges": {
                "type": "array",
                "description": "Relations between nodes (sends_to, controls, fuses_from, etc.).",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "from": {
                            "type": "string",
                            "description": "id of the source node",
                        },
                        "to": {
                            "type": "string",
                            "description": "id of the target node",
                        },
                        "canonical_relation": {
                            "type": "string",
                            "description": (
                                "Canonical edge code: SENDS_TO, CONTROLS, "
                                "FUSES_FROM, MEASURES, DETECTS, ALERTS_TO, "
                                "OVERRIDES, CLASSIFIES, READS_FROM, WRITES_TO, "
                                "PUBLISHES, SUBSCRIBES_TO, AUTHENTICATES_WITH, "
                                "PART_OF, MOUNTED_ON, BROADCASTS_TO."
                            ),
                        },
                        "content": {
                            "type": "object",
                            "description": "What flows over this edge, if any.",
                            "properties": {
                                "canonical_type": {"type": "string"},
                                "surface_form": {"type": "string"},
                                "attributes": {"type": "object"},
                            },
                        },
                        "frequency": {
                            "type": "object",
                            "description": "Cycle / timing characteristics.",
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "enum": [
                                        "REAL_TIME",
                                        "PERIODIC",
                                        "EVENT_DRIVEN",
                                        "ON_DEMAND",
                                        "ASYNCHRONOUS",
                                    ],
                                },
                                "value_hz": {"type": "number"},
                                "value_ms_period": {"type": "number"},
                            },
                        },
                        "condition": {
                            "type": "object",
                            "description": "Threshold / guard expression on this edge.",
                            "properties": {
                                "form": {
                                    "type": "string",
                                    "enum": [
                                        "NUMERIC_THRESHOLD",
                                        "RANGE_THRESHOLD",
                                        "TIME_THRESHOLD",
                                        "ENUM_CONDITION",
                                        "COMPOSITE",
                                    ],
                                },
                                "expression": {"type": "string"},
                                "units": {"type": "string"},
                            },
                        },
                        "cite": {
                            "type": "object",
                            "properties": {
                                "char_start": {"type": "integer"},
                                "char_end": {"type": "integer"},
                            },
                            "required": ["char_start", "char_end"],
                        },
                    },
                    "required": ["id", "from", "to", "canonical_relation", "cite"],
                },
            },
            "unmapped": {
                "type": "array",
                "description": (
                    "Phrases you couldn't confidently map to a canonical type. "
                    "Surface them so the ontology can evolve."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "surface_form": {"type": "string"},
                        "guessed_type": {
                            "type": "string",
                            "description": "Best-guess canonical code if any, or empty string.",
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "cite": {
                            "type": "object",
                            "properties": {
                                "char_start": {"type": "integer"},
                                "char_end": {"type": "integer"},
                            },
                        },
                    },
                    "required": ["surface_form", "confidence"],
                },
            },
        },
        "required": ["nodes", "edges"],
    },
}
