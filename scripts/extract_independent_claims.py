"""Extract independent claims from a Google Patents BigQuery JSON export.

Input  : data_cache/patents_500.json  (output of `SELECT *` on
         patents-public-data.patents.publications, exported as JSON
         from BigQuery Console)
Output : data_cache/independent_claims.jsonl  (one row per patent, with
         the parsed independent claims as a list)
         data_cache/sample_for_mining.txt   (40 AV-relevant patents
         sampled for human review, formatted for easy scanning)

Why heuristic (not Claude) for the parse:
    Independent vs dependent classification is rule-based by design — every
    dependent claim contains "of claim N" / "according to claim N" / etc.
    Pure regex catches >99% with no API spend. Reserve Claude for the
    semantic gap-mining step on the small sampled subset.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data_cache"
INPUT = DATA / "patents_500.json"
OUT_JSONL = DATA / "independent_claims.jsonl"
OUT_SAMPLE = DATA / "sample_for_mining.txt"

# CPC prefixes considered tightly AV-passenger-relevant for the sampling step
AV_TIGHT_PREFIXES = ("B60W30", "B60W40", "B60W50", "B60W60", "G05D1", "G08G1")

SAMPLE_SIZE = 40
RANDOM_SEED = 42

# Regex spotting "of claim 5" / "according to claim 5" / "in accordance with
# claim 5" / "as in claim 5" / "as recited in claim 5" / "as set forth in
# claim 5" — case-insensitive. Matches both "claim" and "claims" with optional
# "any (one) of".
DEPENDENT_REFERENCE = re.compile(
    r"(?:of|according to|in accordance with|as in|as recited in|"
    r"as claimed in|as set forth in)\s+(?:any\s+(?:one\s+)?of\s+)?"
    r"claims?\s+\d",
    re.IGNORECASE,
)

# Split claims_text on patterns like "1." or "1 ." beginning a numbered claim.
# claims_localized in BigQuery typically has numbered claims separated by
# newlines, with each starting "<n>.". We split greedily and pair number with
# body.
CLAIM_SPLIT = re.compile(r"(?:^|\n)\s*(\d+)\s*\.\s+")

HTML_ENTITIES = {
    "&#39;": "'",
    "&quot;": '"',
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
}


def decode_entities(s: str | None) -> str:
    if not s:
        return ""
    out = s
    for k, v in HTML_ENTITIES.items():
        out = out.replace(k, v)
    return out


def parse_claims(claims_text: str | None) -> list[dict]:
    if not claims_text:
        return []
    text = decode_entities(claims_text)
    parts = CLAIM_SPLIT.split(text)
    # parts[0] is preamble text before claim 1; subsequent pairs are
    # (number, body).
    out = []
    for i in range(1, len(parts) - 1, 2):
        try:
            num = int(parts[i])
        except ValueError:
            continue
        body = parts[i + 1].strip()
        out.append({
            "num": num,
            "text": body,
            "independent": not DEPENDENT_REFERENCE.search(body),
        })
    return out


def is_av_relevant(cpc_codes: list[str]) -> bool:
    return any(
        any(c.startswith(prefix) for prefix in AV_TIGHT_PREFIXES)
        for c in cpc_codes
    )


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(f"Missing input: {INPUT}\n"
                         f"Run the BigQuery export first (see docs).")

    with INPUT.open() as f:
        patents = json.load(f)

    parsed = []
    for p in patents:
        claims = parse_claims(p.get("claims_text", ""))
        indep = [c["text"] for c in claims if c["independent"]]
        if not indep:
            continue
        parsed.append({
            "patent": p["publication_number"],
            "title": decode_entities(p.get("title", "")),
            "cpc_codes": p.get("cpc_codes", []),
            "assignee": p.get("assignee") or "UNKNOWN",
            "grant_date": p.get("grant_date"),
            "independent_claims": indep,
        })

    # Persist all parsed claims as JSONL (one patent per line)
    OUT_JSONL.parent.mkdir(exist_ok=True)
    with OUT_JSONL.open("w") as f:
        for row in parsed:
            f.write(json.dumps(row) + "\n")

    print(f"patents in:                {len(patents)}")
    print(f"patents with parsed claims: {len(parsed)}")
    print(f"total independent claims:   {sum(len(p['independent_claims']) for p in parsed)}")
    print(f"-> {OUT_JSONL}")

    # Sample AV-tight subset for human review
    av_relevant = [p for p in parsed if is_av_relevant(p["cpc_codes"])]
    rng = random.Random(RANDOM_SEED)
    sample = rng.sample(av_relevant, min(SAMPLE_SIZE, len(av_relevant)))

    with OUT_SAMPLE.open("w") as f:
        for i, p in enumerate(sample, 1):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"PATENT {i}: {p['patent']}  |  {p['assignee']}\n")
            f.write(f"TITLE: {p['title']}\n")
            f.write(f"CPC: {', '.join(p['cpc_codes'][:5])}\n")
            for j, claim in enumerate(p["independent_claims"][:2], 1):
                clipped = claim if len(claim) < 4000 else claim[:4000] + " ...[truncated]"
                f.write(f"\n--- INDEP CLAIM {j} ---\n{clipped}\n")

    print(f"AV-tight patents:          {len(av_relevant)}")
    print(f"sampled for review:        {len(sample)}")
    print(f"-> {OUT_SAMPLE}  ({OUT_SAMPLE.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
