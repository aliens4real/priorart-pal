"""Structural-matching eval: BRI matcher rules.

Hand-crafted test cases verifying the matcher applies the two BRI rules
correctly:

- parent_type substitution (vertical):
    query has PEDESTRIAN, patent discloses ROAD_OBSTACLE -> partial match
    query has ROAD_OBSTACLE, patent discloses PEDESTRIAN -> full match
    sibling types under same parent -> no match

- Agency abstraction (compositional):
    patent has VEHICLE SENDS_TO server, query has TELEMATICS_CONTROLLER
    SENDS_TO server -> agency-substituted partial match

- Surface-form synonym filters:
    excluded synonym should not produce a match
    novel surface form (canonical type but unconfirmed phrasing) should
    produce a flagged-tentative match

Stub for Phase 1 — full implementation in Phase 3 once the matcher
exists.
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Phase 1 stub. Phase 3 wires this once the structural matcher "
        "(parent_type + agency-abstraction rules) is implemented."
    )


if __name__ == "__main__":
    main()
