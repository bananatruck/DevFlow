"""SQLModel database tables with full traceability.

Tables:
- User: GitHub authenticated users
- Run: Agent runs with status tracking
- RunStep: Individual workflow steps
- ToolCall: Every tool invocation with request/response
- Artifact: Generated content (plans, checklists, diffs, summaries)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from sqlalchemy import Column, Text, Index
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    pass


# =============================================================================
# User Model
# =============================================================================

class User(SQLModel, table=True):
    """GitHub authenticated user."""
    
    __tablename__ = "users"
    
    id: int | None = Field(default=None, primary_key=True)
    github_id: str = Field(unique=True, index=True, description="GitHub user ID")
    github_username: str = Field(index=True, description="GitHub username")
    email: str | None = Field(default=None, description="Email from GitHub")
    avatar_url: str | None = Field(default=None, description="GitHub avatar URL")
    access_token_hash: str | None = Field(default=None, description="Hashed GitHub access token")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
    
    # Relationships
    runs: list["Run"] = Relationship(back_populates="user")


# =============================================================================
# Run Model
# =============================================================================

class Run(SQLModel, table=True):
    """An agent run instance."""
    
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_user_created", "user_id", "created_at"),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(unique=True, index=True, description="UUID for the run")
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Request
    repo_path: str = Field(description="Local path to repository")
    feature_request: str = Field(sa_column=Column(Text), description="User's feature request")
    base_branch: str = Field(default="main")
    
    # Status
    status: str = Field(default="queued", index=True)  # Use RunStatus enum values
    current_step: str | None = Field(default=None)  # Use StepName enum values
    progress: float = Field(default=0.0, description="0-1 progress indicator")
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    
    # Model info
    model_primary: str = Field(default="deepseek-chat")
    model_fallback: str | None = Field(default="moonshot-v1-32k")
    
    # Metrics
    total_tokens_used: int = Field(default=0)
    total_tool_calls: int = Field(default=0)
    retry_count: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(default=None)
    ended_at: datetime | None = Field(default=None)
    
    # Success tracking
    success: bool | None = Field(default=None)
    
    # Relationships
    user: User | None = Relationship(back_populates="runs")
    steps: list["RunStep"] = Relationship(back_populates="run")
    tool_calls: list["ToolCall"] = Relationship(back_populates="run")
    artifacts: list["Artifact"] = Relationship(back_populates="run")


# =============================================================================
# RunStep Model
# =============================================================================

class RunStep(SQLModel, table=True):
    """Individual workflow step within a run."""
    
    __tablename__ = "run_steps"
    __table_args__ = (
        Index("ix_run_steps_run_step", "run_id", "step_name"),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.run_id", index=True)
    
    step_name: str = Field(index=True)  # PLAN, CHECKLIST, EXECUTE, VALIDATE, SUMMARY
    step_order: int = Field(default=0, description="Order in the workflow")
    status: str = Field(default="pending")  # pending, running, completed, failed, skipped
    
    # Model used for this step
    model_used: str | None = Field(default=None)
    
    # Metrics
    tokens_used: int = Field(default=0)
    latency_ms: int | None = Field(default=None)
    retry_count: int = Field(default=0)
    
    # Error info
    error_code: str | None = Field(default=None)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    
    # Timestamps
    started_at: datetime | None = Field(default=None)
    ended_at: datetime | None = Field(default=None)
    
    # Relationships
    run: Run | None = Relationship(back_populates="steps")


# =============================================================================
# ToolCall Model
# =============================================================================

class ToolCall(SQLModel, table=True):
    """Log of every tool invocation for audit and debugging."""
    
    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_run_tool", "run_id", "tool_name"),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.run_id", index=True)
    step_name: str = Field(index=True)
    
    tool_name: str = Field(index=True, description="Name of the tool called")
    
    # Request/Response (stored as JSON strings)
    request_json: str = Field(sa_column=Column(Text), description="Tool input as JSON")
    response_json: str | None = Field(default=None, sa_column=Column(Text), description="Tool output as JSON")
    
    # Result
    ok: bool | None = Field(default=None)
    error_code: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
    retryable: bool = Field(default=False)
    
    # Metrics
    latency_ms: int | None = Field(default=None)
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    run: Run | None = Relationship(back_populates="tool_calls")


# =============================================================================
# Artifact Model
# =============================================================================

class Artifact(SQLModel, table=True):
    """Generated content from runs (plans, checklists, diffs, summaries)."""
    
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifacts_run_type", "run_id", "artifact_type"),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.run_id", index=True)
    
    artifact_type: str = Field(index=True)  # plan_md, checklist_md, diff, test_log, summary_md
    
    # Content (stored as text, could be moved to blob storage for large files)
    content: str = Field(sa_column=Column(Text), description="Artifact content")
    content_hash: str | None = Field(default=None, description="SHA256 of content for deduplication")
    
    # Metadata
    version: int = Field(default=1, description="Version number for updates")
    size_bytes: int | None = Field(default=None)
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    run: Run | None = Relationship(back_populates="artifacts")


# =============================================================================
# LLM Call Log (for debugging and cost tracking)
# =============================================================================

class LLMCallLog(SQLModel, table=True):
    """Log of every LLM API call for debugging and cost analysis."""
    
    __tablename__ = "llm_call_logs"
    
    id: int | None = Field(default=None, primary_key=True)
    run_id: str | None = Field(default=None, index=True)
    step_name: str | None = Field(default=None)
    
    # Provider info
    provider: str = Field(index=True)  # deepseek, kimi
    model: str = Field(description="Model name used")
    
    # Request (stored for replay/debugging)
    messages_json: str = Field(sa_column=Column(Text), description="Input messages as JSON")
    
    # Response
    response_content: str | None = Field(default=None, sa_column=Column(Text))
    tool_calls_json: str | None = Field(default=None, sa_column=Column(Text))
    finish_reason: str | None = Field(default=None)
    
    # Raw response (for debugging)
    raw_response_json: str | None = Field(default=None, sa_column=Column(Text))
    
    # Token usage
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    
    # Metrics
    latency_ms: int | None = Field(default=None)
    success: bool = Field(default=True)
    error_message: str | None = Field(default=None)
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
