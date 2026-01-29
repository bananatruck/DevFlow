"""SQLModel tables.

Suggested tables:
- runs: run_id, timestamps, repo_url, request, state, model profile
- run_events: tool calls, validation errors, retries (for audit + evaluation)
- artifacts: plan/checklist/summary blobs
- embeddings_workflows: dataset items embeddings (pgvector)
- embeddings_repo: code chunk embeddings (pgvector)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    repo_url: str
    feature_request: str
    state: str = Field(default="queued")
    created_at: datetime = Field(default_factory=datetime.utcnow)
