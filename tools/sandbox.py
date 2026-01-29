"""Sandbox execution.

Responsibilities:
- Run commands (tests/lint/build) in an isolated Docker container
- Capture stdout/stderr and return structured results
- Prevent agent from executing untrusted code on the host

Design:
- separate image/container with mounted working directory (read/write controlled)
"""

from __future__ import annotations

from typing import List, Dict, Any


def run_in_sandbox(commands: List[str], workdir: str) -> Dict[str, Any]:
    """Execute commands in sandbox (placeholder)."""
    # TODO: Implement docker execution and log capture
    return {"ok": True, "stdout": "", "stderr": "", "exit_code": 0}
