"""Rendering for the Layer 2 demo.

Three entry points:

- `render_vegalite_to_png(spec)`: Vega-Lite v5 JSON spec to PNG via vl-convert.
  Sage emits a spec, so this is the Sage path.
- `render_freeform_to_png(text)`: format-detecting dispatcher for the
  open-ended baseline side. Tries Vega-Lite first (bare JSON or fenced
  ```vega-lite / ```json), then Python (fenced ```python or bare). Falls
  back to a placeholder PNG so the side-by-side always renders.
- `render_python_to_png(code)`: exec a `def render(ax):` snippet in a
  small sandbox with matplotlib/numpy/seaborn pre-bound. Demo-grade only.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import threading
import textwrap
from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
import vl_convert as vlc  # noqa: E402

FENCE_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)
ROOT = Path(__file__).resolve().parents[2]
BUILD_TMP_DIR = ROOT / "output" / "build_tmp"
_PYTHON_RENDER_LOCK = threading.Lock()

SAFE_BUILTINS = {
    "__import__": __import__,
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "isinstance": isinstance, "len": len, "list": list, "map": map,
    "max": max, "min": min, "range": range, "reversed": reversed,
    "round": round, "set": set, "sorted": sorted, "str": str, "sum": sum,
    "tuple": tuple, "zip": zip, "print": print,
    "True": True, "False": False, "None": None,
}


@contextmanager
def _build_tmp_cwd():
    """Run generated scripts from the ignored build scratch directory."""
    BUILD_TMP_DIR.mkdir(parents=True, exist_ok=True)
    original = Path.cwd()
    os.chdir(BUILD_TMP_DIR)
    try:
        yield
    finally:
        os.chdir(original)


def strip_code_fences(text: str) -> str:
    """Strip a leading/trailing ```lang ... ``` fence if present."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def render_vegalite_to_png(spec: str | dict, *, scale: float = 2.0) -> bytes:
    """Parse a Vega-Lite v5 spec (str or dict) and rasterize to PNG."""
    spec_obj = json.loads(spec) if isinstance(spec, str) else spec
    return vlc.vegalite_to_png(spec_obj, scale=scale)


_FONT_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"
_FONT_FALLBACK = "/System/Library/Fonts/Helvetica.ttc"


def _font(size: int, *, bold: bool = False):
    from PIL import ImageFont
    for path in (_FONT_PATH, _FONT_FALLBACK):
        try:
            return ImageFont.truetype(path, size, index=1 if bold else 0)
        except Exception:
            continue
    return ImageFont.load_default()


def render_slide_to_png(slide: str | dict) -> bytes:
    """Compose an executive slide PNG from Sage's slide schema.

    Schema (all top-level keys optional except `chart_spec`):
      {
        "headline":    "Q4 revenue hit $31.0M, +21.6% YoY",
        "subhead":     "Software the engine; margin slipping 4pp YTD",
        "kpi_tiles":   [{"label": "Q4 Revenue", "value": "$31.0M",
                         "delta": "+21.6% YoY"}, ...],
        "footnote":    "Source: finance close, 2026-01-15.",
        "chart_spec":  { ... Vega-Lite v5 spec ... }
      }
    """
    import io
    from PIL import Image as PILImage, ImageDraw

    if isinstance(slide, str):
        slide = json.loads(slide)
    chart_spec = slide["chart_spec"]
    if isinstance(chart_spec, dict) and "title" in chart_spec:
        chart_spec = {k: v for k, v in chart_spec.items() if k != "title"}
    chart_png = render_vegalite_to_png(chart_spec, scale=2.0)
    chart_img = PILImage.open(io.BytesIO(chart_png)).convert("RGB")

    headline = (slide.get("headline") or "").strip()
    subhead = (slide.get("subhead") or "").strip()
    kpis = slide.get("kpi_tiles") or []
    footnote = (slide.get("footnote") or "").strip()

    W = 1200
    pad = 36
    cw = W - 2 * pad
    scale = cw / chart_img.width
    ch = int(chart_img.height * scale)
    chart_scaled = chart_img.resize((cw, ch), PILImage.LANCZOS)

    headline_h = 44 if headline else 0
    subhead_h = 28 if subhead else 0
    head_gap = 14 if (headline or subhead) else 0
    kpi_h = 108 if kpis else 0
    kpi_gap = 20 if kpis else 0
    footnote_h = 26 if footnote else 0
    footnote_gap = 12 if footnote else 0

    H = (pad + headline_h + subhead_h + head_gap + kpi_h + kpi_gap
         + ch + footnote_gap + footnote_h + pad)
    canvas = PILImage.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)

    y = pad
    if headline:
        draw.text((pad, y), headline, fill="#1a1a1a", font=_font(30, bold=True))
        y += headline_h
    if subhead:
        draw.text((pad, y), subhead, fill="#6a6a6a", font=_font(17))
        y += subhead_h
    if headline or subhead:
        y += head_gap

    if kpis:
        n = len(kpis)
        gap = 16
        tile_w = (cw - gap * (n - 1)) // n
        for i, tile in enumerate(kpis[:6]):
            x = pad + i * (tile_w + gap)
            draw.rectangle([x, y, x + tile_w, y + kpi_h],
                           fill="#f6f8fa", outline="#d8dee4")
            label = (tile.get("label") or "").upper()
            value = str(tile.get("value") or "")
            delta = str(tile.get("delta") or "")
            if delta.startswith("+"):
                delta_color = "#1f7a3a"
            elif delta.startswith(("-", "−")):
                delta_color = "#c43c3c"
            else:
                delta_color = "#555555"
            draw.text((x + 16, y + 14), label, fill="#888888",
                      font=_font(11, bold=True))
            draw.text((x + 16, y + 36), value, fill="#1a1a1a",
                      font=_font(30, bold=True))
            if delta:
                draw.text((x + 16, y + 78), delta, fill=delta_color,
                          font=_font(14, bold=True))
        y += kpi_h + kpi_gap

    canvas.paste(chart_scaled, (pad, y))
    y += ch
    if footnote:
        y += footnote_gap
        draw.text((pad, y), footnote, fill="#999999", font=_font(12))

    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def render_python_to_png(
    code: str, *, figsize: tuple[float, float] = (8, 5), dpi: int = 144
) -> bytes:
    """Exec `code` and return PNG bytes.

    Two supported shapes (open-ended baseline may emit either):
    1. The code defines `render(ax)`, call it on a fresh fig/ax.
    2. Top-level script that builds a figure via pyplot, capture the
       current figure after exec. `plt.show` and any `savefig` calls
       are neutered so the script doesn't pop windows or write to disk.
    """
    from matplotlib.figure import Figure

    with _PYTHON_RENDER_LOCK:
        sns.set_theme(style="whitegrid", context="talk", font_scale=0.85,
                      palette="colorblind")

        sandbox: dict[str, object] = {
            "__builtins__": SAFE_BUILTINS,
            "plt": plt, "np": np, "math": math, "matplotlib": matplotlib,
            "sns": sns, "pd": pd,
        }
        code = textwrap.dedent(code)
        has_render = (
            re.search(r"^\s*def\s+render\s*\(", code, re.MULTILINE) is not None
        )

        orig_show = plt.show
        orig_plt_savefig = plt.savefig
        orig_fig_savefig = Figure.savefig
        plt.show = lambda *a, **kw: None  # type: ignore[assignment]
        plt.savefig = lambda *a, **kw: None  # type: ignore[assignment]
        Figure.savefig = lambda self, *a, **kw: None  # type: ignore[assignment]
        plt.close("all")
        try:
            with _build_tmp_cwd():
                if has_render:
                    exec(code, sandbox)
                    render_fn = sandbox.get("render")
                    if not callable(render_fn):
                        raise ValueError("`render` was defined but is not callable")
                    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
                    try:
                        render_fn(ax)
                        buf = io.BytesIO()
                        orig_fig_savefig(fig, buf, format="png", bbox_inches="tight")
                        return buf.getvalue()
                    finally:
                        plt.close(fig)
                exec(code, sandbox)
                fig = plt.gcf()
                if not fig.get_axes():
                    raise ValueError("Top-level script produced no axes")
                buf = io.BytesIO()
                orig_fig_savefig(fig, buf, format="png", bbox_inches="tight")
                plt.close(fig)
                return buf.getvalue()
        finally:
            plt.show = orig_show  # type: ignore[assignment]
            plt.savefig = orig_plt_savefig  # type: ignore[assignment]
            Figure.savefig = orig_fig_savefig  # type: ignore[assignment]


def _looks_like_vegalite(obj: object) -> bool:
    if not isinstance(obj, dict):
        return False
    schema = obj.get("$schema", "")
    if isinstance(schema, str) and "vega-lite" in schema:
        return True
    return any(k in obj for k in ("mark", "layer", "facet", "concat",
                                  "hconcat", "vconcat", "repeat"))


def _try_vegalite(text: str, errs: list[str]) -> bytes | None:
    try:
        obj = json.loads(text)
    except Exception as e:
        errs.append(f"vegalite: not JSON ({e.__class__.__name__})")
        return None
    if not _looks_like_vegalite(obj):
        errs.append("vegalite: JSON did not look like a Vega-Lite spec")
        return None
    try:
        return render_vegalite_to_png(obj)
    except Exception as e:
        errs.append(f"vegalite: render failed ({e.__class__.__name__}: {e})")
        return None


def _try_python(code: str, errs: list[str]) -> bytes | None:
    try:
        return render_python_to_png(code)
    except Exception as e:
        errs.append(f"python: {e.__class__.__name__}: {str(e)[:200]}")
        return None


def _placeholder_png(message: str) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 5), dpi=144)
    ax.text(0.5, 0.5, message, ha="center", va="center",
            fontsize=11, color="#888", wrap=True, transform=ax.transAxes)
    ax.set_axis_off()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_freeform_to_png(text: str) -> tuple[bytes, str | None]:
    """Detect format of `text` (open-ended LLM output) and render to PNG.

    Returns `(png_bytes, error)` where `error` is None on success and
    otherwise a human-readable string listing every render attempt that
    failed plus the first line of the offending text. The placeholder
    PNG embeds the same message so it shows up visibly in the HTML.
    """
    text = text.strip()
    errs: list[str] = []

    if text.startswith("{"):
        png = _try_vegalite(text, errs)
        if png:
            return png, None

    blocks = FENCE_RE.findall(text)
    if not blocks and not text.startswith("{"):
        errs.append("no fenced code block found and text does not look like JSON")
    for lang, body in blocks:
        if lang.lower() in ("vega-lite", "vega", "vegalite", "json"):
            png = _try_vegalite(body, errs)
            if png:
                return png, None
    for lang, body in blocks:
        if lang.lower() in ("python", "py", ""):
            png = _try_python(body, errs)
            if png:
                return png, None

    png = _try_python(text, errs)
    if png:
        return png, None

    first_line = text.splitlines()[0] if text else "(empty)"
    reason = "; ".join(errs) if errs else "no renderable content"
    msg = f"Unrenderable output.\n\n{reason}\n\nFirst line:\n{first_line[:200]}"
    return _placeholder_png(msg), reason
