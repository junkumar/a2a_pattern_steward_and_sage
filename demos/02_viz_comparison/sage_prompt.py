"""Sage's proprietary system prompt, composed from named blocks.

The prompt text lives in `prompts/sage_system.md` (source of truth).
This module parses that file by `<!-- section: NAME -->` markers and
exposes each section body as a module-level constant (uppercase of the
marker name), plus a `SECTIONS` tuple and `build_system_prompt()`.
Editing the prompt is a markdown edit; no Python change needed.

Grounded in foundational references and benchmark findings:

- Mackinlay, J. (1986). "Automating the Design of Graphical Presentations
  of Relational Information." Two formal criteria drive chart selection:
    * Expressiveness: the chart must encode all and only the facts in the
      data. No false implications, no omitted relations.
    * Effectiveness: among expressive options, prefer the encoding whose
      perceptual channel is most accurate for the data type.
  Mackinlay's per-type rankings (most → least accurate channel):
    Quantitative: position > length > angle/slope > area > volume > color
    Ordinal:      position > density > color sat > color hue > texture
                  > connection > containment > length > angle > area
    Nominal:      position > color hue > texture > connection
                  > containment > density > color sat > shape > length

- Harrower, M. & Brewer, C. (2003). "ColorBrewer.org: An Online Tool for
  Selecting Colour Schemes for Maps." Color encoding must match data
  type: sequential schemes for ordered magnitude, diverging schemes for
  data with a meaningful midpoint, qualitative schemes for nominal
  categories. Lightness carries order (and survives colorblindness and
  monochrome reproduction); hue carries category.

- Wilkinson, L. (1999). "An automatic visualization system" (AutoVis).
  Chart family is driven by data characteristics (types Q/O/N, arity,
  cardinality, presence of a temporal axis, missingness), independent of
  any narrative the analyst may impose. Pick the family from the data
  first; tune the encoding for the question second.

Sage combines them: read the data characteristics (Wilkinson) to narrow
the chart family, then apply expressiveness + the effectiveness ranking
(Mackinlay) to pick the encoding inside that family.

The benchmark-driven guidance in `readability` targets failures that
persist on 2025-era frontier models, not the older VisEval-era failures
that modern code-LLMs already handle:

- Ford and Rios (EMNLP 2025 Findings, arXiv:2506.06175) audit 100
  frontier-LLM chart outputs that all run cleanly and find 67-93% fail
  basic colorblind / accessibility guidelines and ~11% stylistically
  miss the question's stated emphasis. "Code runs" is no longer the bar;
  perceptual quality and question-fidelity are.
- Pan et al. (CoDA, arXiv:2510.03194) measure Gemini 2.5-Pro and Claude
  3.5-Sonnet at 46-59% visual-success rate on single-pass MatPlotBench;
  the persistent gap is on questions that need multi-encoding judgement
  (e.g. revenue + margin together) where models reach for dual-axis or
  stacked-area shapes that are expressively wrong.
- Galimzyanov et al. (PandasPlotBench, arXiv:2412.02764) find frontier
  models still hallucinate plotting APIs at 22% for plotly. Sage sidesteps
  the API-hallucination axis by emitting Vega-Lite v5 JSON (a declarative
  spec, not imperative code), so the boundary is type-checked rather than
  exec-trusted.
"""
from __future__ import annotations

import re
from pathlib import Path

PROMPT_FILE = Path(__file__).parent / "prompts" / "sage_system.md"

# Only match lowercase marker names; this lets the preamble describe the
# marker syntax with an uppercase placeholder (e.g. `<!-- section: NAME -->`)
# without that documentation getting parsed as an actual section.
_SECTION_RE = re.compile(r"<!--\s*section:\s*([a-z_]+)\s*-->")


def _parse_sections(text: str) -> tuple[tuple[str, str], ...]:
    """Split the prompt markdown into `(name, body)` pairs by marker."""
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        raise ValueError(f"no `<!-- section: NAME -->` markers in {PROMPT_FILE}")
    parsed: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        name = m.group(1).lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            raise ValueError(f"section {name!r} in {PROMPT_FILE} is empty")
        parsed.append((name, body))
    return tuple(parsed)


SECTIONS: tuple[tuple[str, str], ...] = _parse_sections(PROMPT_FILE.read_text())

# Expose each section body as a module-level constant (uppercase name) so
# call sites and tests can `from sage_prompt import ROLE, EXPRESSIVENESS, ...`.
for _name, _body in SECTIONS:
    globals()[_name.upper()] = _body
del _name, _body


def build_system_prompt(include: tuple[str, ...] | None = None) -> str:
    """Compose the system prompt. Pass `include` to subset sections for tests."""
    chosen = SECTIONS if include is None else tuple((n, b) for n, b in SECTIONS if n in include)
    return "\n".join(block.rstrip() for _, block in chosen) + "\n"


if __name__ == "__main__":
    # Sanity print so `python sage_prompt.py` confirms the file parses.
    for name, body in SECTIONS:
        print(f"{name}: {len(body)} chars")
    print(f"total: {len(build_system_prompt())} chars")
