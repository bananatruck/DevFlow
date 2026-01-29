"""Pydantic schemas for all agent I/O contracts.

These schemas define the strict contracts between:
- API endpoints and clients
- LLM model inputs/outputs
- Tool calls and results
- Database serialization
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class RunStatus(str, Enum):
    """Status of an agent run."""
    QUEUED = "queued"
    PLANNING = "planning"
    CHECKLIST = "checklist"
    EXECUTING = "executing"
    VALIDATING = "validating"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepName(str, Enum):
    """Names of workflow steps."""
    PLAN = "PLAN"
    CHECKLIST = "CHECKLIST"
    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    SUMMARY = "SUMMARY"


class ArtifactType(str, Enum):
    """Types of artifacts produced by runs."""
    PLAN_MD = "plan_md"
    CHECKLIST_MD = "checklist_md"
    DIFF = "diff"
    TEST_LOG = "test_log"
    SUMMARY_MD = "summary_md"


class Complexity(str, Enum):
    """Estimated complexity of a feature."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """Types of actions in a checklist item."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    TEST = "test"
    REFACTOR = "refactor"


# =============================================================================
# Input Schemas
# =============================================================================

class FeatureRequest(BaseModel):
    """Input from user to start an agent run."""
    description: str = Field(..., description="Natural language feature request")
    repo_path: str = Field(..., description="Local path to the repository")
    base_branch: str = Field(default="main", description="Branch to base changes on")
    model_profile: str = Field(default="default", description="Model routing profile to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Add retry limit to webhook processor",
                "repo_path": "/home/user/projects/myapp",
                "base_branch": "main",
                "model_profile": "default"
            }
        }


# =============================================================================
# Plan Schemas
# =============================================================================

class Plan(BaseModel):
    """Output from plan_node - high-level implementation plan."""
    title: str = Field(..., description="Short title for the plan")
    problem_statement: str = Field(..., description="Clear description of what needs to be done")
    proposed_approach: str = Field(..., description="How the problem will be solved")
    affected_files: list[str] = Field(default_factory=list, description="Files expected to change")
    estimated_complexity: Complexity = Field(default=Complexity.MEDIUM)
    risks: list[str] = Field(default_factory=list, description="Potential risks or concerns")
    
    def to_markdown(self) -> str:
        """Render plan as markdown."""
        md = f"# {self.title}\n\n"
        md += f"## Problem Statement\n{self.problem_statement}\n\n"
        md += f"## Proposed Approach\n{self.proposed_approach}\n\n"
        md += f"## Affected Files\n"
        for f in self.affected_files:
            md += f"- `{f}`\n"
        md += f"\n## Estimated Complexity\n{self.estimated_complexity.value}\n"
        if self.risks:
            md += f"\n## Risks\n"
            for r in self.risks:
                md += f"- {r}\n"
        return md


# =============================================================================
# Checklist Schemas
# =============================================================================

class ChecklistItem(BaseModel):
    """Single actionable step in the checklist."""
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    description: str = Field(..., description="What needs to be done")
    file_path: str | None = Field(default=None, description="Target file for this step")
    action: ActionType = Field(..., description="Type of action")
    dependencies: list[str] = Field(default_factory=list, description="IDs of items this depends on")
    completed: bool = Field(default=False)
    

class Checklist(BaseModel):
    """Output from checklist_node - ordered actionable steps."""
    items: list[ChecklistItem] = Field(..., description="Ordered list of steps")
    test_strategy: str = Field(..., description="How to verify the changes work")
    
    def to_markdown(self) -> str:
        """Render checklist as markdown."""
        md = "# Implementation Checklist\n\n"
        for i, item in enumerate(self.items, 1):
            checkbox = "[x]" if item.completed else "[ ]"
            file_str = f" (`{item.file_path}`)" if item.file_path else ""
            md += f"{i}. {checkbox} **{item.action.value.upper()}**{file_str}: {item.description}\n"
        md += f"\n## Test Strategy\n{self.test_strategy}\n"
        return md


# =============================================================================
# Execution Schemas
# =============================================================================

class ExecutionPatch(BaseModel):
    """A single file change produced during execution."""
    file_path: str = Field(..., description="Path to the file")
    original_content: str | None = Field(default=None, description="Original file content (None if new file)")
    new_content: str = Field(..., description="New file content")
    diff: str = Field(default="", description="Unified diff of changes")
    checklist_item_id: str | None = Field(default=None, description="Associated checklist item")


class ValidationResult(BaseModel):
    """Result of validating a patch or execution."""
    passed: bool = Field(..., description="Whether validation passed")
    checks: dict[str, bool] = Field(default_factory=dict, description="Individual check results")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    test_output: str | None = Field(default=None, description="Test runner output")


# =============================================================================
# Summary Schemas
# =============================================================================

class RunSummary(BaseModel):
    """Output from summary_node - PR-ready summary."""
    title: str = Field(..., description="PR title")
    description: str = Field(..., description="PR description")
    changes_made: list[str] = Field(..., description="List of changes made")
    files_changed: list[str] = Field(..., description="List of files modified")
    tests_passed: bool = Field(..., description="Whether tests passed")
    verification_steps: list[str] = Field(..., description="How to verify the changes")
    risk_notes: list[str] = Field(default_factory=list, description="Risk notes for reviewers")
    
    def to_markdown(self) -> str:
        """Render summary as markdown."""
        md = f"# {self.title}\n\n"
        md += f"{self.description}\n\n"
        md += "## Changes Made\n"
        for c in self.changes_made:
            md += f"- {c}\n"
        md += "\n## Files Changed\n"
        for f in self.files_changed:
            md += f"- `{f}`\n"
        md += f"\n## Tests\n{'✅ All tests passed' if self.tests_passed else '❌ Tests failed'}\n"
        md += "\n## Verification Steps\n"
        for i, v in enumerate(self.verification_steps, 1):
            md += f"{i}. {v}\n"
        if self.risk_notes:
            md += "\n## Risk Notes\n"
            for r in self.risk_notes:
                md += f"- ⚠️ {r}\n"
        return md


# =============================================================================
# Tool Schemas
# =============================================================================

class ToolResult(BaseModel):
    """Standard response from any tool call."""
    ok: bool = Field(..., description="Whether the tool call succeeded")
    data: Any | None = Field(default=None, description="Tool-specific response data")
    error_code: str | None = Field(default=None, description="Error code if failed")
    error_message: str | None = Field(default=None, description="Human-readable error message")
    retryable: bool = Field(default=False, description="Whether the error is retryable")
    artifacts: list[str] = Field(default_factory=list, description="Paths to generated artifacts")
    latency_ms: int | None = Field(default=None, description="Time taken in milliseconds")


class ToolCallLog(BaseModel):
    """Log entry for a tool call."""
    tool_name: str
    request: dict[str, Any]
    response: ToolResult
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# API Request/Response Schemas
# =============================================================================

class RunCreateRequest(BaseModel):
    """API request to create a new run."""
    feature_request: str = Field(..., description="Natural language feature request")
    repo_path: str = Field(..., description="Local path to repository")
    base_branch: str = Field(default="main")
    model_profile: str = Field(default="default")


class RunResponse(BaseModel):
    """API response for run status."""
    run_id: str
    status: RunStatus
    current_step: StepName | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="0-1 progress")
    message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class RunArtifactsResponse(BaseModel):
    """API response for run artifacts."""
    run_id: str
    plan_markdown: str | None = None
    checklist_markdown: str | None = None
    summary_markdown: str | None = None
    diff: str | None = None
    raw_events: list[dict[str, Any]] = Field(default_factory=list)


class RunListResponse(BaseModel):
    """API response for listing runs."""
    runs: list[RunResponse]
    total: int
    page: int = 1
    per_page: int = 20


# =============================================================================
# LLM Schemas
# =============================================================================

class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""
    role: Literal["system", "user", "assistant", "tool"] = Field(...)
    content: str = Field(...)
    name: str | None = Field(default=None, description="Name for tool messages")
    tool_calls: list[dict[str, Any]] | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)


class LLMRequest(BaseModel):
    """Request to an LLM provider."""
    messages: list[LLMMessage]
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    tools: list[dict[str, Any]] | None = None
    response_format: dict[str, str] | None = None


class LLMResponse(BaseModel):
    """Response from an LLM provider."""
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None


# =============================================================================
# User/Auth Schemas
# =============================================================================

class UserResponse(BaseModel):
    """API response for user data."""
    id: int
    github_id: str
    github_username: str
    email: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    """API response for auth tokens."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
