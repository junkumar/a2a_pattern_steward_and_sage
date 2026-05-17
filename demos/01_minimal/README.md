# Layer 1: minimal MCP boundary

This is the smallest version of the pattern: one MCP server, one MCP
client, one typed tool, and one round trip.

There are no LLM calls in this layer. This keeps the wire shape easy to
inspect before Layer 2 adds agent reasoning.

## What this demo is doing

- `server.py` exposes a typed MCP tool.
- `client.py` starts the server over stdio, calls the tool, and prints the
  result.

The boundary is visible here: the client sends only the fields the tool
accepts, and the server returns only the declared result.
That is the core pattern Layer 2 builds on.

## Run

```sh
./venv/bin/python demos/01_minimal/client.py
```
