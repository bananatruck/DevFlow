"""LangGraph workflow definition for the 4-step agent.

Graph structure:
START → plan_node → checklist_node → execute_node → summary_node → END
                                         ↓
                                  validate → retry/repair (loop)
                                         ↓
                                  escalate (fallback model)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from src.schemas import (
    Plan,
    Checklist,
    ChecklistItem,
    ExecutionPatch,
    RunSummary,
    ValidationResult,
    FeatureRequest,
    LLMMessage,
    StepName,
    RunStatus,
)
from src.llm.router import get_router
from src.tools.repo import repo_map, read_file, write_file
from src.tools.git_ops import git_create_branch, git_status, git_diff, git_commit
from src.tools.sandbox import run_tests, run_linter
from src.agent.prompts import (
    SYSTEM_PROMPT,
    format_plan_prompt,
    format_checklist_prompt,
    format_execute_prompt,
    format_repair_prompt,
    format_summary_prompt,
)


logger = logging.getLogger(__name__)

# Maximum retries for execution step
MAX_RETRIES = 2


# =============================================================================
# State Definition
# =============================================================================

class AgentState(dict):
    """State for the agent workflow.
    
    Attributes:
        run_id: Unique identifier for this run
        feature_request: The original feature request
        repo_path: Path to the repository
        repo_context: Summarized repository context
        plan: Generated implementation plan
        checklist: Generated implementation checklist
        current_item_index: Current checklist item being executed
        patches: List of file patches made
        validation_results: Results from validation steps
        summary: Final run summary
        current_step: Current workflow step
        retry_count: Number of retries for current item
        errors: List of errors encountered
        status: Current run status
    """
    pass


def initial_state(feature_request: FeatureRequest, run_id: str | None = None) -> AgentState:
    """Create initial agent state."""
    return AgentState(
        run_id=run_id or str(uuid4()),
        feature_request=feature_request,
        repo_path=feature_request.repo_path,
        repo_context="",
        plan=None,
        checklist=None,
        current_item_index=0,
        patches=[],
        validation_results=[],
        summary=None,
        current_step=StepName.PLAN.value,
        retry_count=0,
        errors=[],
        status=RunStatus.PLANNING.value,
        started_at=datetime.utcnow().isoformat(),
    )


# =============================================================================
# Node Functions
# =============================================================================

async def plan_node(state: AgentState) -> AgentState:
    """Generate implementation plan from feature request.
    
    Input: feature_request, repo_path
    Output: plan, repo_context
    """
    logger.info(f"[{state['run_id']}] Starting plan_node")
    
    state["current_step"] = StepName.PLAN.value
    state["status"] = RunStatus.PLANNING.value
    
    # Get repository context
    repo_result = await repo_map(state["repo_path"], max_depth=3)
    if not repo_result.ok:
        state["errors"].append(f"Failed to map repo: {repo_result.error_message}")
        return state
    
    # Build repo context string
    key_files = repo_result.data.get("key_files", [])
    ast_summaries = repo_result.data.get("ast_summaries", {})
    
    context_lines = ["## Key Files"]
    for f in key_files[:20]:
        summary = ast_summaries.get(f["path"], [])
        if summary:
            context_lines.append(f"- `{f['path']}`: {', '.join(summary[:5])}")
        else:
            context_lines.append(f"- `{f['path']}`")
    
    state["repo_context"] = "\n".join(context_lines)
    
    # Generate plan using LLM
    router = get_router()
    
    messages = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=format_plan_prompt(
                feature_request=state["feature_request"].description,
                repo_context=state["repo_context"],
            ),
        ),
    ]
    
    response, provider, model = await router.chat_completion(
        messages=messages,
        step=StepName.PLAN.value,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    
    if not response.content:
        state["errors"].append("Failed to generate plan: empty response")
        return state
    
    # Parse plan from response
    try:
        plan_data = json.loads(response.content)
        state["plan"] = Plan(**plan_data)
        logger.info(f"[{state['run_id']}] Generated plan: {state['plan'].title}")
    except (json.JSONDecodeError, ValueError) as e:
        state["errors"].append(f"Failed to parse plan: {e}")
    
    return state


async def checklist_node(state: AgentState) -> AgentState:
    """Generate implementation checklist from plan.
    
    Input: plan
    Output: checklist
    """
    logger.info(f"[{state['run_id']}] Starting checklist_node")
    
    state["current_step"] = StepName.CHECKLIST.value
    state["status"] = RunStatus.CHECKLIST.value
    
    if not state["plan"]:
        state["errors"].append("No plan available for checklist generation")
        return state
    
    router = get_router()
    
    messages = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=format_checklist_prompt(state["plan"].to_markdown()),
        ),
    ]
    
    response, provider, model = await router.chat_completion(
        messages=messages,
        step=StepName.CHECKLIST.value,
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    
    if not response.content:
        state["errors"].append("Failed to generate checklist: empty response")
        return state
    
    try:
        checklist_data = json.loads(response.content)
        items = [ChecklistItem(**item) for item in checklist_data.get("items", [])]
        state["checklist"] = Checklist(
            items=items,
            test_strategy=checklist_data.get("test_strategy", "Run tests"),
        )
        logger.info(f"[{state['run_id']}] Generated checklist with {len(items)} items")
    except (json.JSONDecodeError, ValueError) as e:
        state["errors"].append(f"Failed to parse checklist: {e}")
    
    return state


async def execute_node(state: AgentState) -> AgentState:
    """Execute checklist items by generating code changes.
    
    Input: checklist, current_item_index
    Output: patches, current_item_index (incremented)
    """
    logger.info(f"[{state['run_id']}] Starting execute_node")
    
    state["current_step"] = StepName.EXECUTE.value
    state["status"] = RunStatus.EXECUTING.value
    
    if not state["checklist"]:
        state["errors"].append("No checklist available for execution")
        return state
    
    items = state["checklist"].items
    current_idx = state["current_item_index"]
    
    if current_idx >= len(items):
        logger.info(f"[{state['run_id']}] All items executed")
        return state
    
    item = items[current_idx]
    logger.info(f"[{state['run_id']}] Executing item {current_idx + 1}/{len(items)}: {item.description}")
    
    # Get current file content if modifying
    file_content = ""
    if item.file_path and item.action == "modify":
        file_result = await read_file(state["repo_path"], item.file_path)
        if file_result.ok:
            file_content = file_result.data.get("content", "")
    
    router = get_router()
    
    messages = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=format_execute_prompt(
                checklist_item=json.dumps(item.model_dump()),
                file_content=file_content or "(new file)",
                repo_context=state["repo_context"],
            ),
        ),
    ]
    
    response, provider, model = await router.chat_completion(
        messages=messages,
        step=StepName.EXECUTE.value,
        model_type="reasoning",  # Use reasoning model for code
        temperature=0.3,  # Lower temperature for code
        response_format={"type": "json_object"},
    )
    
    if not response.content:
        state["errors"].append(f"Failed to execute item {item.id}: empty response")
        state["retry_count"] += 1
        return state
    
    try:
        exec_data = json.loads(response.content)
        file_path = exec_data.get("file_path", item.file_path)
        new_content = exec_data.get("new_content", "")
        
        if file_path and new_content:
            # Write the file
            write_result = await write_file(state["repo_path"], file_path, new_content)
            
            if write_result.ok:
                patch = ExecutionPatch(
                    file_path=file_path,
                    original_content=file_content if file_content else None,
                    new_content=new_content,
                    checklist_item_id=item.id,
                )
                state["patches"].append(patch)
                item.completed = True
                state["current_item_index"] = current_idx + 1
                state["retry_count"] = 0
                logger.info(f"[{state['run_id']}] Successfully wrote {file_path}")
            else:
                state["errors"].append(f"Failed to write file: {write_result.error_message}")
                state["retry_count"] += 1
        else:
            state["current_item_index"] = current_idx + 1
            
    except (json.JSONDecodeError, ValueError) as e:
        state["errors"].append(f"Failed to parse execution result: {e}")
        state["retry_count"] += 1
    
    return state


async def validate_node(state: AgentState) -> AgentState:
    """Validate changes by running tests and linting.
    
    Input: patches
    Output: validation_results
    """
    logger.info(f"[{state['run_id']}] Starting validate_node")
    
    state["current_step"] = StepName.VALIDATE.value
    state["status"] = RunStatus.VALIDATING.value
    
    checks = {}
    errors = []
    
    # Run linter
    lint_result = await run_linter(state["repo_path"])
    checks["lint"] = lint_result.ok
    if not lint_result.ok:
        errors.append(f"Lint failed: {lint_result.error_message}")
    
    # Run tests
    test_result = await run_tests(state["repo_path"])
    checks["tests"] = test_result.ok
    test_output = test_result.data.get("stdout", "") if test_result.data else ""
    if not test_result.ok:
        errors.append(f"Tests failed: {test_result.error_message}")
    
    validation = ValidationResult(
        passed=all(checks.values()),
        checks=checks,
        errors=errors,
        test_output=test_output,
    )
    
    state["validation_results"].append(validation)
    
    logger.info(f"[{state['run_id']}] Validation: {'PASSED' if validation.passed else 'FAILED'}")
    
    return state


async def summary_node(state: AgentState) -> AgentState:
    """Generate final run summary.
    
    Input: feature_request, patches, validation_results
    Output: summary
    """
    logger.info(f"[{state['run_id']}] Starting summary_node")
    
    state["current_step"] = StepName.SUMMARY.value
    state["status"] = RunStatus.SUMMARIZING.value
    
    # Get diff
    diff_result = await git_diff(state["repo_path"])
    diff_content = diff_result.data.get("diff", "") if diff_result.ok else ""
    
    # Build changes summary
    changes = []
    for patch in state["patches"]:
        changes.append(f"- Modified `{patch.file_path}`")
    
    # Get test results summary
    test_passed = all(v.passed for v in state["validation_results"])
    test_summary = "All tests passed" if test_passed else "Some tests failed"
    
    router = get_router()
    
    messages = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=format_summary_prompt(
                feature_request=state["feature_request"].description,
                changes="\n".join(changes) + f"\n\n### Diff\n```diff\n{diff_content[:5000]}\n```",
                test_results=test_summary,
            ),
        ),
    ]
    
    response, provider, model = await router.chat_completion(
        messages=messages,
        step=StepName.SUMMARY.value,
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    
    if response.content:
        try:
            summary_data = json.loads(response.content)
            state["summary"] = RunSummary(
                title=summary_data.get("title", "Changes"),
                description=summary_data.get("description", ""),
                changes_made=summary_data.get("changes_made", []),
                files_changed=[p.file_path for p in state["patches"]],
                tests_passed=test_passed,
                verification_steps=summary_data.get("verification_steps", []),
                risk_notes=summary_data.get("risk_notes", []),
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse summary: {e}")
    
    state["status"] = RunStatus.COMPLETED.value
    state["ended_at"] = datetime.utcnow().isoformat()
    
    return state


# =============================================================================
# Routing Functions
# =============================================================================

def should_continue_execution(state: AgentState) -> Literal["execute", "validate", "summary"]:
    """Determine next step after execution."""
    if not state["checklist"]:
        return "summary"
    
    if state["current_item_index"] < len(state["checklist"].items):
        return "execute"
    
    return "validate"


def should_retry_or_continue(state: AgentState) -> Literal["execute", "summary"]:
    """Determine if we should retry or continue after validation."""
    # If validation passed or max retries reached, go to summary
    if state["validation_results"]:
        last_validation = state["validation_results"][-1]
        if last_validation.passed:
            return "summary"
    
    if state["retry_count"] >= MAX_RETRIES:
        return "summary"
    
    # Otherwise continue execution
    return "execute"


# =============================================================================
# Workflow Builder
# =============================================================================

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("checklist", checklist_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("summary", summary_node)
    
    # Set entry point
    workflow.set_entry_point("plan")
    
    # Add edges
    workflow.add_edge("plan", "checklist")
    workflow.add_edge("checklist", "execute")
    
    # Conditional edge after execute
    workflow.add_conditional_edges(
        "execute",
        should_continue_execution,
        {
            "execute": "execute",
            "validate": "validate",
            "summary": "summary",
        },
    )
    
    # Conditional edge after validate
    workflow.add_conditional_edges(
        "validate",
        should_retry_or_continue,
        {
            "execute": "execute",
            "summary": "summary",
        },
    )
    
    # Summary goes to end
    workflow.add_edge("summary", END)
    
    return workflow


# Compiled workflow
agent_workflow = build_workflow().compile()


# =============================================================================
# Public API
# =============================================================================

async def run_agent(feature_request: FeatureRequest, run_id: str | None = None) -> AgentState:
    """Execute the full agent workflow.
    
    Args:
        feature_request: The feature to implement
        run_id: Optional run ID (generated if not provided)
        
    Returns:
        Final agent state with all artifacts
    """
    state = initial_state(feature_request, run_id)
    
    logger.info(f"Starting agent run {state['run_id']}")
    
    # Create branch for changes
    branch_name = f"devflow/{state['run_id'][:8]}"
    await git_create_branch(state["repo_path"], branch_name)
    
    # Run workflow
    async for step_state in agent_workflow.astream(state):
        # Update state from step
        if isinstance(step_state, dict):
            for key, value in step_state.items():
                if isinstance(value, dict):
                    state.update(value)
    
    # Commit changes if any
    if state["patches"]:
        commit_msg = f"feat: {state['plan'].title if state['plan'] else 'DevFlow changes'}"
        await git_commit(state["repo_path"], commit_msg)
    
    logger.info(f"Agent run {state['run_id']} completed with status {state['status']}")
    
    return state
