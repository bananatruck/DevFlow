"""Planner module.

Responsibilities:
- Convert a feature request into a structured plan + checklist
- Use strict schemas for function calling
- Retrieve similar workflows via RAG to guide planning

Models:
- Primary: DeepSeek-V3
- Fallback: Claude Sonnet (after repeated validation failures)
"""

from __future__ import annotations

from typing import Any, Dict


def build_plan(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Return a structured plan object (placeholder)."""
    # TODO: Implement model call + JSON schema validation (Pydantic)
    return {"plan": [], "checklist": []}
