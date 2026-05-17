"""Minimal MCP client: connects to the server, calls one tool, prints the result.

Customer side of the transport layer. The client owns the data
(`values`, `label`) and decides what to send. The server's
implementation is opaque from here; we see only the typed surface.
No LLM in this layer; see `demos/02_viz_comparison/` for the
agent-to-agent version.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).parent / "server.py"


async def run() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"server advertises {len(tools.tools)} tool(s):")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")
            print()

            result = await session.call_tool(
                "render_bar_chart",
                arguments={
                    "values": [3, 7, 5, 9, 4, 2],
                    "label": "weekly signups",
                },
            )
            for block in result.content:
                if block.type == "text":
                    print(block.text)


if __name__ == "__main__":
    asyncio.run(run())
