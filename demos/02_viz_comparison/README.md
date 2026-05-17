# Layer 2: viz comparison

Layer 2 adds Claude calls on both sides of the same MCP boundary.
Steward sends a dataset and a question over MCP; Sage applies
proprietary guidance and returns a rendered PNG. The baseline path
runs the same model without Sage's proprietary guidance against the same input.
The public comparison view is `output/RESULTS.md`; each scenario also
writes an HTML page with the two charts side by side.

## What this demo is doing

- `server.py` is Sage, an MCP server. It exposes one tool,
  `generate_visualization(data, question)`. Inside the tool, Sage calls
  Claude with its proprietary guidance, expects a Vega-Lite v5 JSON
  spec back, rasterizes it via `vl-convert`, and returns the PNG.
- `client.py` is Steward. For each scenario:
  1. Spawns the Sage server over stdio MCP, calls the tool, decodes
     the returned image.
  2. Runs the baseline path by calling Claude directly with an
     open-ended prompt that imposes no library or language constraint.
     Whatever the model returns (Vega-Lite JSON, Python with
     matplotlib, etc.) is rasterized by the freeform dispatcher.
  3. Writes `output/<scenario>.html` with both PNGs side by side.
- `render.py` contains rendering helpers. `render_vegalite_to_png`
  handles the Sage path. `render_freeform_to_png` handles the open-ended
  baseline, detects Vega-Lite vs Python, and dispatches accordingly. The
  Python branch execs `def render(ax):` snippets in a small sandbox.
  Demo-grade only; not safe for untrusted code.
- `sage_prompt.py` contains the proprietary guidance, composed from
  named blocks in `prompts/sage_system.md`, the prompt source file.
  Steward never sees this; only the Sage server reads it.
- `../../scenarios/` contains the six JSON inputs used by this demo. Each
  scenario is designed to test visualization judgment: what to encode,
  how to scale it, what to emphasize, and what to leave out. See the
  scenario files for the specific data, question, and visualization risk.

## Run

This demo uses Claude Code through the `claude` command. Install and
authenticate Claude Code first. You can set `CLAUDE_MODEL` to choose a
specific model.

```sh
./venv/bin/python demos/02_viz_comparison/client.py             # runs all
./venv/bin/python demos/02_viz_comparison/client.py consumer_app_engagement
```

Per-scenario output lands in `output/<scenario>.html` as a local build
artifact. The repository tracks `output/RESULTS.md` as the public
comparison view (built from those HTMLs).

## What to look at

Both paths use the same Claude model. The variable is whether Sage's
proprietary guidance is applied behind the MCP boundary. Treat the checked-in
charts as a snapshot from one run, not as a benchmark. The useful question is
whether Sage's private guidance changes the result in a way the scenario makes
visible.

## What crosses the boundary

- Steward sends Sage a scoped JSON dataset and a one-line question. It does
  not send the warehouse, schemas for other tables, or unrelated PII.
- Sage returns Steward a PNG. It does not return the prompt, the
  chart-strategy rationale, or intermediate code.

The typed tool signature names what crosses the boundary on every call,
so the exchange can be inspected without reading either side's internals.
