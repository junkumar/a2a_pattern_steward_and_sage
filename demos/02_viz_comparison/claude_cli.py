"""Thin wrapper around the `claude -p` CLI.

Lets both Sage and the baseline run through the Claude Code subscription
instead of direct API calls. Same model on both sides; the only variable
is the system prompt.
"""
from __future__ import annotations

import os
import shutil
import subprocess

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

_CLAUDE_BIN = shutil.which("claude") or "claude"


def claude_complete(*, system: str, user: str, model: str = DEFAULT_MODEL,
                    timeout: int = 1800, tools: str | None = None,
                    cwd: str | None = None) -> str:
    """One-shot completion via `claude -p`. Returns stdout.

    `tools=None` disables all tools (text-only completion). Pass a
    comma-separated tool list (e.g. "Bash,Read,Write") to let the
    session run code; permission prompts are bypassed for that case
    since the run is non-interactive.
    """
    cmd = [
        _CLAUDE_BIN, "-p",
        "--model", model,
        "--effort", "low",
        "--system-prompt", system,
        "--output-format", "text",
        "--no-session-persistence",
        "--setting-sources", "",
    ]
    if tools is None:
        cmd.append('--tools=')
    else:
        cmd += [f"--tools={tools}", "--dangerously-skip-permissions"]
    cmd.append(user)
    # Strip API-key env vars so `claude -p` authenticates via the Claude Code
    # subscription (OAuth) rather than falling back to pay-per-token API billing.
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    proc = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL, cwd=cwd, env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (exit {proc.returncode}): {proc.stderr[:2000]}"
        )
    return proc.stdout
