# Steward and Sage: Agent Collaboration Across Trust Boundary

A small runnable example of agent collaboration when neither agent can reveal
everything it knows.

Here "agent-to-agent" (a2a) means two agents collaborating across a trust
boundary: different organizations, teams, security zones, or systems with
different disclosure rules.

**Steward** is the data-side agent and holds sensitive data, deciding
what crosses the boundary. **Sage** is the guidance-side agent and
holds proprietary reasoning, including prompts, design rules, and
playbooks. They collaborate through a typed MCP tool surface. Steward
sends only the scoped data and question for this request. Sage returns
the result, not its private implementation.

Each agent can reason locally, but the cross-boundary exchange is typed
rather than free-form chat.

```
┌─────────────┐         MCP          ┌─────────────────┐
│   Steward   │  ───── request ───►  │      Sage       │
│ (data side) │  ◄──── result  ────  │ (guidance side) │
└─────────────┘                      └─────────────────┘
   knows the                            knows the
   sensitive data                       proprietary guidance
```

Steward can minimize disclosure by choosing the scoped data and question
that cross the boundary. Sage can apply proprietary judgment without
handing over the system prompt, catalog, or chart strategy. The exchange
remains typed and inspectable.

This repo is a worked example of one useful shape for agent
cooperation. It does not aim to prove a security model or define a
new agent protocol.

The central design choice is the typed boundary. Too narrow, and Sage
cannot do useful work. Too wide, and the disclosure logic leaks back
across. This demo picks one minimal shape: `data` + `question`. The
`data` payload is a flexible illustration whereas a production version would be much more structured.

The core surface is intentionally small:

```python
class VisualizationRequest(BaseModel):
    data: dict[str, Any]
    question: str

@mcp.tool()
def generate_visualization(req: VisualizationRequest) -> Image:
    ...
```

This repo uses data visualization as the demonstration domain because
the result is easy to inspect: the same data and question can produce two
charts that can be compared side by side. The pattern is broader than
charting. Any workflow where one side holds sensitive inputs and the
other side holds specialized guidance can use the same shape.

The visualization comparison is time-sensitive. It is only evidence
against the current generation of Claude, GPT, and similar baseline
models. As those models improve, the baseline will likely get stronger
and this particular chart-quality comparison may go stale quickly. The
boundary pattern is the durable claim; the chart-quality delta is a
current-model demonstration.

Snapshot context for the checked-in comparison:

- Generation date and model are included in the results output.
- Model used during development: `claude-opus-4-7` through Claude Code CLI.
- Scenario count: 6.
- Same model, same data, and same question on both paths.
- **See the side-by-side results: [output/RESULTS.md](output/RESULTS.md).**

How to read the comparison:

- Check whether each chart answers the stated question.
- Check whether it foregrounds the listed visualization challenge.
- Treat the image quality difference as a dated model snapshot, not a benchmark.


## Two demos

### `demos/01_minimal/`

Smallest faithful end-to-end implementation: one MCP server, one MCP
client, one tool, one round-trip. Read it first to see the wire shape.

### `demos/02_viz_comparison/`

Steward sends a dataset and a question to Sage. Sage uses its proprietary
guidance to return a rendered chart. The checked-in comparison includes
six scenarios and compares two paths:

The Sage path calls Claude with proprietary guidance, design rules, and
a chart-strategy library, then returns a rendered PNG.

The baseline path calls Claude directly without Sage's proprietary
guidance.

**A snapshot of the generated result, the comparison, is in [output/RESULTS.md](output/RESULTS.md).**
Both paths use the same model. The variable is whether Sage's proprietary
guidance is applied behind the MCP boundary.

## Stack

- The project uses Python 3.12.
- `mcp` is the MCP Python SDK, used by both server and client.
- Claude Code CLI provides model calls for the Layer 2 rerun path.

## Run

Create a virtual environment and install the Python dependencies:

```sh
python3.12 -m venv venv
./venv/bin/python -m pip install -e .
```

Run the minimal MCP boundary demo:

```sh
./venv/bin/python demos/01_minimal/client.py
```

Rendered comparison outputs are checked in under `output/`. Start with
`output/RESULTS.md` for the comparison view; the per-scenario PNGs live
under `output/img/`.

To regenerate the Layer 2 visualization comparison, install and
authenticate Claude Code so the `claude` command works, then run:

```sh
./venv/bin/python demos/02_viz_comparison/client.py all
```

You can set `CLAUDE_MODEL` to choose a different Claude Code model.

## Repo layout

- **`demos/01_minimal/`**: Core transport layer (1 tool, no LLM).
- **`demos/02_viz_comparison/`**: The Sage vs. Baseline agentic demo.
- **`scenarios/`**: The data and questions Steward sends to Sage.

## A companion sketch

These are two of a few small sketches I am working through on questions in agent architecture. They share a thread: firm intelligence and vendor or specialist guidance should not sit in the same agent. [The Right Agent for the Right Job](https://github.com/junkumar/right-agent-right-job) argues that case. This repo takes the split as given and asks what the boundary between the two should look like, with a typed MCP surface in a different domain (data visualization). Neither is a system anyone is running.

## Industry Context

Early multi-agent frameworks gave every agent access to a shared context window holding everything any agent knew. Enterprise deployments will likely restrict each agent to only the fields a typed schema declares, with disclosure decided at the boundary rather than inside the prompt. Wrapping an agent inside an MCP server with a declared tool signature makes that decision programmatic. Additionally, using MCP primitives directly keeps the implementation small enough to read in one sitting and inspect with standard tooling.

## About

Built by [Nandu Jayakumar](https://www.linkedin.com/in/junkumar/). My background is 20+ years of building data systems, inside enterprises and on the vendor side shipping to them, at Meta, Oracle, Visa, and Yahoo. The data domain in these sketches reflects where I have spent most of my career. The enterprise framing reflects years of shipping software that had to survive inside real organizations. This is one of a few small runnable sketches I've built in Apr 2026 while thinking through agent architecture patterns that I believe are important.
