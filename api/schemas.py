"""Pydantic request/response schemas.

Responsibilities:
- Validate incoming requests for agent runs
- Validate tool I/O payloads (function calling)
- Ensure stable, typed API contract
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Start a new agent run."""
    repo_url: str = Field(..., description="Git repository URL to operate on")
    feature_request: str = Field(..., description="Natural language feature request")
    base_branch: str = Field(default="main")
    model_profile: str = Field(default="default", description="Which model routing policy to use")


class RunStatus(BaseModel):
    run_id: str
    state: str
    message: Optional[str] = None


class RunArtifacts(BaseModel):
    run_id: str
    plan_markdown: str
    checklist_markdown: str
    summary_markdown: str
    raw_events: List[Dict[str, Any]] = []
