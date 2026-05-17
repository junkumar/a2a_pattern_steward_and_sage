"""Steward: runs the Layer 2 viz comparison.

For each scenario, produces two PNGs side by side in one HTML page:

  - Sage: Steward calls the Sage MCP server, which applies a
    proprietary guidance before asking Claude to render. Sage
    internally emits a Vega-Lite v5 JSON spec and rasterizes it.

  - Baseline: Steward calls Claude directly with an open-ended
    prompt that imposes no library or language constraint. Whatever the
    model returns (Vega-Lite JSON, Python with matplotlib, etc.) is
    rasterized by the freeform dispatcher.

Same model, same data, same question on both sides. The only variable is
whether Sage's proprietary guidance is applied behind the MCP boundary.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from claude_cli import claude_complete  # noqa: E402

SERVER_SCRIPT = HERE / "server.py"
SCENARIOS_DIR = HERE.parent.parent / "scenarios"
OUTPUT_DIR = HERE.parent.parent / "output"
DEBUG_DIR = HERE.parent.parent / "output" / "debug"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

BASELINE_SYSTEM = (
    "You are a data visualization assistant with full access to a shell "
    "and a working directory. Given a dataset and a question, choose any "
    "tool, library, or language you prefer, run it yourself, and write "
    "the resulting chart to the PNG filename given in the user message, "
    "in the current working directory. Use the Bash tool (e.g. invoke "
    "python with matplotlib, R, gnuplot, whatever you like). The only "
    "requirement is that that file exists when you finish. "
    "No commentary."
)
BASELINE_TOOLS = "Bash,Read,Write"


async def sage(data: dict, question: str) -> bytes:
    """Run the request through the Sage MCP server and return PNG bytes."""
    env = get_default_environment()
    if m := os.environ.get("CLAUDE_MODEL"):
        env["CLAUDE_MODEL"] = m
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "generate_visualization",
                arguments={
                    "req": {
                        "data": data,
                        "question": question
                    }
                },
            )
            for block in result.content:
                if getattr(block, "type", None) == "image":
                    return base64.b64decode(block.data)
            for block in result.content:
                txt = getattr(block, "text", None)
                if txt:
                    print(f"[sage error block] {txt[:2000]}", file=sys.stderr)
    raise RuntimeError("Sage returned no image content")


def baseline(data: dict, question: str, name: str) -> tuple[bytes, str | None]:
    """Steward asks Claude (with tools) to render a chart itself.

    Claude runs in a scratch directory with Bash/Read/Write tools enabled
    and is asked to write `chart.png` there. The transcript is saved to
    `output/debug/<name>.baseline.txt` for inspection. Returns
    `(png_bytes, error)`; `error` is non-None if no PNG was produced.
    """
    import tempfile
    # Scenario-specific filename so that even if concurrent `claude -p`
    # baselines somehow share working state (a stray `cd` in claude's
    # shell snapshot, a cached shell session), one scenario's chart can't
    # be mistaken for another's at read time.
    chart_name = f"{name}_chart.png"
    user_message = (
        f"Question:\n{question}\n\n"
        f"Dataset (JSON):\n{json.dumps(data, indent=2)}\n\n"
        "Produce the chart that best answers the question. Write the "
        f"final image to `{chart_name}` in the current working directory. "
        "Do not write anywhere else."
    )
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    debug_path = DEBUG_DIR / f"{name}.baseline.txt"
    with tempfile.TemporaryDirectory(prefix=f"baseline-{name}-") as scratch:
        transcript = claude_complete(
            system=BASELINE_SYSTEM, user=user_message, model=MODEL,
            tools=BASELINE_TOOLS, cwd=scratch,
        )
        debug_path.write_text(transcript)
        png_path = Path(scratch) / chart_name
        if not png_path.exists():
            return _placeholder_png(
                f"Baseline did not produce {chart_name}. Transcript saved to "
                f"output/debug/{name}.baseline.txt"
            ), f"baseline did not write {chart_name}"
        return png_path.read_bytes(), None


def _placeholder_png(message: str) -> bytes:
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5), dpi=144)
    ax.text(0.5, 0.5, message, ha="center", va="center",
            fontsize=11, color="#888", wrap=True, transform=ax.transAxes)
    ax.set_axis_off()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem auto;
        max-width: 1200px; color: #222; padding: 0 1rem; }}
.question {{ background: #f5f5f5; padding: 1rem; border-left: 4px solid #999;
          margin: 1rem 0; }}
.metadata {{ background: #f6f8fa; padding: 0.75rem 1rem; margin: 1rem 0;
             border: 1px solid #d8dee4; }}
.metadata p {{ margin: 0.25rem 0; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
.col {{ border: 1px solid #ddd; padding: 1rem; background: white; }}
.col h2 {{ margin-top: 0; font-size: 1rem; color: #555; }}
img {{ max-width: 100%; height: auto; display: block; }}
.note {{ color: #666; font-size: 0.85rem; margin-top: 1rem; }}
</style></head><body>
<h1>{title}</h1>
<div class="metadata">
  <p><strong>Data:</strong> {data_summary}</p>
  <p><strong>Visualization risk:</strong> {visualization_risk}</p>
</div>
<div class="question"><strong>Question:</strong> {question}</div>
<div class="grid">
  <div class="col"><h2>Baseline</h2>
    <img src="data:image/png;base64,{baseline_b64}" alt="baseline"></div>
  <div class="col"><h2>Sage</h2>
    <img src="data:image/png;base64,{sage_b64}" alt="sage"></div>
</div>
<p class="note">Same Claude model on both sides. Sage's proprietary
guidance is applied behind the boundary; the baseline receives
no library or language constraint.</p>
</body></html>
"""


async def run_scenario(name: str) -> Path:
    scenario_path = SCENARIOS_DIR / f"{name}.json"
    ex = json.loads(scenario_path.read_text())
    title = ex.get("title", name)
    data_summary = ex.get("data_summary", "")
    visualization_risk = ex.get("visualization_risk", "")
    question = ex["question"]
    data = ex["data"]

    print(f"[{name}] calling Sage over MCP + baseline (concurrent)...")
    sage_result, base_result = await asyncio.gather(
        sage(data, question),
        asyncio.to_thread(baseline, data, question, name),
        return_exceptions=True,
    )
    failures = []
    if isinstance(sage_result, Exception):
        failures.append(f"Sage: {sage_result}")
    if isinstance(base_result, Exception):
        failures.append(f"baseline: {base_result}")
    if failures:
        raise RuntimeError("; ".join(failures))
    sage_png = sage_result
    baseline_png, baseline_err = base_result
    if baseline_err:
        print(
            f"[{name}] WARN: baseline output unrenderable: {baseline_err}. "
            f"Raw output saved to output/debug/{name}.baseline.txt",
            file=sys.stderr,
        )
    OUTPUT_DIR.mkdir(exist_ok=True)
    html_path = OUTPUT_DIR / f"{name}.html"
    html_path.write_text(
        HTML_TEMPLATE.format(
            title=title,
            data_summary=data_summary,
            visualization_risk=visualization_risk,
            question=question,
            sage_b64=base64.b64encode(sage_png).decode(),
            baseline_b64=base64.b64encode(baseline_png).decode(),
        )
    )
    print(f"[{name}] wrote {html_path}")
    return html_path


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", nargs="?", default="all",
                        help="scenario name (file stem in scenarios/) or 'all'")
    parser.add_argument("--strict", action="store_true",
                        help="exit nonzero if any requested scenario fails")
    args = parser.parse_args()

    if args.scenario == "all":
        names = [p.stem for p in sorted(SCENARIOS_DIR.glob("*.json"))]
        if not names:
            raise SystemExit(f"no scenarios found in {SCENARIOS_DIR}")
    else:
        names = [args.scenario]

    async def _safe(n: str) -> str | None:
        try:
            await run_scenario(n)
            return None
        except Exception as e:
            print(f"[{n}] FAILED: {e}", file=sys.stderr)
            return f"{n}: {e}"

    failures = [f for f in await asyncio.gather(*(_safe(n) for n in names)) if f]
    if failures and args.strict:
        msg = "\n".join(f"  - {f}" for f in failures)
        raise SystemExit(f"scenario generation failed:\n{msg}")


if __name__ == "__main__":
    asyncio.run(main())
