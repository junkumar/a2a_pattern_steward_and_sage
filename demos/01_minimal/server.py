"""Minimal MCP server: one tool that renders an ASCII bar chart.

This layer demonstrates the *transport* only: one typed tool exposed
over MCP. There's no LLM on either side yet, so this isn't agent-to-agent
in any meaningful sense; it's a client calling a typed service. The
larger demo (`demos/02_viz_comparison/`) puts reasoning on both sides
and uses the same boundary.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sage-minimal")


@mcp.tool()
def render_bar_chart(values: list[float], label: str) -> str:
    """Render an ASCII bar chart of `values` with `label` as a title."""
    if not values:
        return f"{label}\n(no data)"
    peak = max(values) or 1.0
    width = 30
    lines = [label, "-" * len(label)]
    for i, v in enumerate(values):
        bar = "█" * max(1, int(round(v / peak * width)))
        lines.append(f"{i:>3} | {bar} {v:g}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
