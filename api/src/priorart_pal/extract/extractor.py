r"""Claude-driven ontology graph extraction.

For each patent claim, this:

1. Sends the ontology v1 spec as a (cached) system prompt — repeats
   across every call but the prompt cache makes that ~10x cheaper than
   uncached.
2. Sends the claim text as the user message.
3. Forces Claude to call the `extract_ontology_graph` tool, which
   guarantees structured JSON output matching our schema.
4. Returns the structured graph + provenance fields (model, version
   hash, tokens, cost).

Cost shape: with prompt caching enabled, the ~30K-token system prompt
is read once per session and cached. Per-claim cost is dominated by
output tokens (the graph) — usually ~500-1500 tokens / claim. Estimated
~$0.015-$0.04 per claim at Sonnet pricing.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic

from priorart_pal.extract.schema import ONTOLOGY_EXTRACT_TOOL
from priorart_pal.logging_config import get_logger
from priorart_pal.settings import get_settings

# Anthropic SDK is fairly chatty at INFO. We have our own structured logs.
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

log = get_logger(__name__)

# Path to the ontology spec we send to the model. Until Phase 2.6 lands
# the canonical_types DB seeder, this markdown is the source of truth.
_REPO_ROOT = Path(__file__).resolve().parents[4]
ONTOLOGY_SPEC_PATH = _REPO_ROOT / "docs" / "ontology-v1.md"

MAX_RETRIES = 3
BACKOFF_BASE_SEC = 2.0


@dataclass
class ExtractionResult:
    """Return shape of `OntologyExtractor.extract_one`."""

    graph: dict[str, Any]
    model: str
    ontology_version_hash: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int


def _ontology_version_hash(spec_text: str) -> str:
    """Stable hash of the ontology context the model was given.

    Stored alongside extracted graphs so we can mark them stale if the
    ontology mutates (per the editable-ontology design in NOTES.md).
    """
    return hashlib.sha256(spec_text.encode("utf-8")).hexdigest()[:16]


def _build_system_prompt(ontology_spec: str) -> str:
    return f"""\
You are a patent-claim structural extractor for PriorArt Pal, a tool that
helps USPTO examiners do prior-art search by matching patents on their
structural topology rather than just keyword similarity.

For each independent claim you receive, identify the structural graph
underlying the claim — components, the relations between them, what
data flows over those relations, and the source character spans. Map
every surface form to a canonical type from the ontology below. When
in doubt, prefer accuracy: it's better to put a phrase in `unmapped`
than to guess a wrong canonical type.

Use the `extract_ontology_graph` tool exactly once per call. Do not
emit prose; the tool call is the response.

# Ontology v1

The full canonical-type catalog with descriptions, synonyms, extraction
rules, and disambiguation notes follows. Match every node, edge, and
content type against this catalog.

{ontology_spec}
"""


class OntologyExtractor:
    """Async extractor — reuse one instance per process."""

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        ontology_spec_path: Path = ONTOLOGY_SPEC_PATH,
        api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model
        key = api_key or settings.anthropic_api_key
        if not key:
            raise RuntimeError(
                "PAP_ANTHROPIC_API_KEY not set. Add it to .env (or Secrets Manager "
                "in production) before calling the extractor."
            )
        self._client = AsyncAnthropic(api_key=key)
        self._spec_text = ontology_spec_path.read_text(encoding="utf-8")
        self._system_prompt = _build_system_prompt(self._spec_text)
        self.ontology_version_hash = _ontology_version_hash(self._spec_text)

    async def extract_one(
        self,
        *,
        patent_pub_no: str,
        claim_num: int,
        claim_text: str,
    ) -> ExtractionResult:
        """Extract a graph from a single claim. Retries on transient errors."""
        if not claim_text.strip():
            raise ValueError("claim_text must be non-empty")

        # Prompt cache: mark the (large, stable) system prompt as cached.
        # System prompt reuses across calls -> 10x cheaper after first hit.
        system_blocks = [
            {
                "type": "text",
                "text": self._system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        user_text = (
            f"Patent: {patent_pub_no}, claim {claim_num}.\n\n"
            f"Claim text:\n\n{claim_text}\n"
        )

        response = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # The anthropic SDK's overloads are very strict about
                # exact param types. Our args are valid at runtime; the
                # ignore is for the dict-vs-TypedDict mismatch in tools.
                response = await self._client.messages.create(  # type: ignore[call-overload]
                    model=self.model,
                    max_tokens=4096,
                    system=system_blocks,
                    tools=[ONTOLOGY_EXTRACT_TOOL],
                    tool_choice={"type": "tool", "name": "extract_ontology_graph"},
                    messages=[{"role": "user", "content": user_text}],
                )
                break
            except Exception as exc:  # noqa: BLE001 — Anthropic SDK errors aren't fully typed
                if attempt == MAX_RETRIES:
                    raise
                wait = BACKOFF_BASE_SEC * (2**attempt)
                log.warning(
                    "extract.retry",
                    patent=patent_pub_no,
                    claim=claim_num,
                    attempt=attempt + 1,
                    wait_sec=wait,
                    error_class=type(exc).__name__,
                )
                await asyncio.sleep(wait)

        if response is None:
            raise RuntimeError("unreachable")

        # The model was forced to use our tool, so the first content block
        # of type 'tool_use' contains the structured graph.
        graph: dict[str, Any] | None = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                graph = dict(block.input)
                break
        if graph is None:
            raise RuntimeError(
                "Claude did not call the extract_ontology_graph tool — "
                "this shouldn't happen with tool_choice forced."
            )

        usage = response.usage
        return ExtractionResult(
            graph=graph,
            model=response.model,
            ontology_version_hash=self.ontology_version_hash,
            input_tokens=usage.input_tokens,
            cached_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            output_tokens=usage.output_tokens,
        )
