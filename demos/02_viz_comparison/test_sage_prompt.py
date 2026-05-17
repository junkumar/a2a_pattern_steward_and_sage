"""Tests for the Sage system prompt.

Runnable from inside Claude Code without a test framework:

    ./venv/bin/python demos/02_viz_comparison/test_sage_prompt.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from sage_prompt import (  # noqa: E402
    COLOR_THEORY,
    DATA_DRIVEN_FAMILIES,
    DESIGN_OPINIONS,
    EFFECTIVENESS_RANKING,
    EXPRESSIVENESS,
    OUTPUT_CONTRACT,
    READABILITY,
    ROLE,
    SECTIONS,
    build_system_prompt,
)


def test_prompt_assembles() -> None:
    p = build_system_prompt()
    assert p.strip(), "prompt is empty"
    for name, block in SECTIONS:
        assert block.strip() in p, f"section {name!r} missing from assembled prompt"


def test_grounding_phrases_present() -> None:
    """The prompt must surface the two foundational criteria by name so the
    model can reason with them, and must encode the perceptual rankings."""
    p = build_system_prompt()
    must_contain = [
        # Mackinlay's two criteria, named.
        "Expressiveness",
        "Effectiveness",
        # Position-beats-length-beats-angle ranking.
        "position",
        "length",
        "angle",
        # Wilkinson's "data characteristics first" framing.
        "data characteristics",
        # Concrete anti-patterns Mackinlay's ranking implies.
        "Avoid pie charts",
        # ColorBrewer scheme types matched to data type.
        "Sequential",
        "Diverging",
        "Qualitative",
        "colorblind",
        "viridis",
        "RdBu",
        # Vega-Lite output discipline.
        "$schema",
        "vega-lite",
        "vconcat",
        "facet",
        "log scale",
        "Pie charts cap at 6",
        "sort by value",
        "human-readable",
        # Four-stage reasoning: semantic + analytical framing before viz.
        "hidden dynamics",
        "cohort",
    ]
    for needle in must_contain:
        assert needle in p, f"missing required phrase: {needle!r}"


def test_section_subset_selection() -> None:
    only_contract = build_system_prompt(include=("output_contract",))
    assert "$schema" in only_contract
    assert "Mackinlay" not in only_contract  # other sections excluded


CONTENT_TESTS = [
    test_prompt_assembles,
    test_grounding_phrases_present,
    test_section_subset_selection,
]


def main() -> int:
    failed = 0
    for t in CONTENT_TESTS:
        try:
            t()
            print(f"ok  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")

    if failed:
        print(f"\n{failed} failure(s)")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
