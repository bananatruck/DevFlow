"""LangGraph state machine definition.

Responsibilities:
- Define the agent loop: Ingest -> Plan -> Checklist -> Execute -> Validate -> Retry/Escalate -> Summarize
- Provide a single `run_agent()` entrypoint used by the API + CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AgentRunResult:
    """Final artifacts from an agent run."""
    run_id: str
    plan_markdown: str
    checklist_markdown: str
    summary_markdown: str
    raw_events: list[dict[str, Any]]


async def run_agent(request: Dict[str, Any]) -> AgentRunResult:
    """Execute one agent run.

    NOTE: This is a placeholder stub. The real implementation will:
    - Build a LangGraph workflow
    - Call planner/executor tools
    - Persist logs in Postgres
    - Return artifacts for UI/CLI
    """
    return AgentRunResult(
        run_id="stub-run-id",
        plan_markdown="(PLAN.md will be generated here)",
        checklist_markdown="(Checklist will be generated here)",
        summary_markdown="(Summary will be generated here)",
        raw_events=[],
    )
