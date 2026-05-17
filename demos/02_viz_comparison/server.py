"""Sage MCP server: proprietary visualization service.

Exposes one tool, `generate_visualization(data, question)`, that calls
Claude with Sage's proprietary guidance, expects a slide JSON envelope
(headline / subhead / kpi_tiles / footnote / chart_spec) back, and
composes the final PNG (Vega-Lite chart rasterized via vl-convert, then
headline + KPI tiles painted on by PIL). The prompt content never
crosses the MCP boundary; only the PNG returns.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from claude_cli import claude_complete  # noqa: E402
from render import render_slide_to_png, strip_code_fences  # noqa: E402
from sage_prompt import build_system_prompt  # noqa: E402

from pydantic import BaseModel, Field

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

mcp = FastMCP("sage")
_system_prompt = build_system_prompt()


class VisualizationRequest(BaseModel):
    data: dict[str, Any] = Field(description="The minimized dataset for this specific question")
    question: str = Field(description="The business question to answer")


@mcp.tool()
def generate_visualization(req: VisualizationRequest) -> Image:
    """Render the most useful chart for `question` over `data` as PNG."""
    user_message = (
        f"Question:\n{req.question}\n\n"
        f"Dataset (JSON):\n{json.dumps(req.data, indent=2)}\n\n"
        "Return ONLY the slide JSON envelope (headline, optional subhead, "
        "optional kpi_tiles, optional footnote, chart_spec). No commentary."
    )
    text = claude_complete(system=_system_prompt, user=user_message, model=MODEL)
    slide_json = strip_code_fences(text)
    png = render_slide_to_png(slide_json)
    return Image(data=png, format="png")


if __name__ == "__main__":
    mcp.run()
