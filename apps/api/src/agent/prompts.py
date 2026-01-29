"""Prompt templates for each agent step.

These prompts are engineered for optimal performance with DeepSeek and Kimi models.
Each step has specialized prompts with clear structure and examples.
"""

from __future__ import annotations

# =============================================================================
# System Prompts
# =============================================================================

SYSTEM_PROMPT = """You are DevFlow, an expert software engineer AI assistant. Your role is to:
1. Analyze feature requests and code repositories
2. Create detailed implementation plans
3. Generate high-quality, production-ready code changes
4. Ensure all changes are well-tested and documented

Guidelines:
- Write clean, idiomatic code following the project's existing style
- Prefer minimal, focused changes over large refactors
- Always consider edge cases and error handling
- Include appropriate tests for new functionality
- Provide clear explanations for complex changes

You have access to tools for reading files, searching code, and making changes.
Always verify your understanding before making edits."""


# =============================================================================
# Plan Node Prompts
# =============================================================================

PLAN_PROMPT = """Analyze this feature request and create an implementation plan.

## Feature Request
{feature_request}

## Repository Context
{repo_context}

## Instructions
Create a structured implementation plan with:
1. **Title**: A brief title for this change
2. **Problem Statement**: Clear description of what needs to be done
3. **Proposed Approach**: How you will implement this
4. **Affected Files**: List of files that will be modified or created
5. **Estimated Complexity**: low, medium, or high
6. **Risks**: Any potential issues or concerns

Respond with a JSON object following this schema:
```json
{{
  "title": "string",
  "problem_statement": "string", 
  "proposed_approach": "string",
  "affected_files": ["string"],
  "estimated_complexity": "low|medium|high",
  "risks": ["string"]
}}
```"""


# =============================================================================
# Checklist Node Prompts  
# =============================================================================

CHECKLIST_PROMPT = """Based on this plan, create an ordered checklist of implementation steps.

## Plan
{plan}

## Instructions
Create an ordered checklist where each item is:
1. A single, atomic action (create/modify/delete/test)
2. Specific about which file to change
3. Clear about what the change accomplishes
4. Ordered by dependencies (do prerequisite steps first)

Also include a test strategy explaining how to verify the changes work.

Respond with a JSON object following this schema:
```json
{{
  "items": [
    {{
      "id": "unique_id",
      "description": "What needs to be done",
      "file_path": "path/to/file.py or null",
      "action": "create|modify|delete|test",
      "dependencies": ["id of items this depends on"]
    }}
  ],
  "test_strategy": "How to verify the changes work"
}}
```"""


# =============================================================================
# Execute Node Prompts
# =============================================================================

EXECUTE_PROMPT = """Execute this checklist item by making the required code changes.

## Checklist Item
{checklist_item}

## Current File Content
{file_content}

## Repository Context
{repo_context}

## Instructions
1. Analyze the checklist item carefully
2. Make the minimal changes needed to complete it
3. Ensure the code follows existing style conventions
4. Handle edge cases appropriately

Respond with a JSON object containing the new file content:
```json
{{
  "file_path": "path/to/file.py",
  "new_content": "complete file content with changes",
  "explanation": "Brief explanation of changes made"
}}
```

IMPORTANT: Return the COMPLETE file content, not just the changes."""


EXECUTE_REPAIR_PROMPT = """The previous code change failed validation. Fix the issues.

## Original Checklist Item
{checklist_item}

## Your Previous Attempt
{previous_attempt}

## Validation Errors
{validation_errors}

## Instructions
1. Analyze what went wrong
2. Fix the specific issues mentioned
3. Ensure the fix addresses the root cause

Respond with the corrected file content:
```json
{{
  "file_path": "path/to/file.py",
  "new_content": "corrected complete file content",
  "explanation": "What was fixed and why"
}}
```"""


# =============================================================================
# Summary Node Prompts
# =============================================================================

SUMMARY_PROMPT = """Create a PR-ready summary of the changes made.

## Original Feature Request
{feature_request}

## Changes Made
{changes}

## Test Results
{test_results}

## Instructions
Create a comprehensive summary including:
1. **Title**: PR title (concise, descriptive)
2. **Description**: Overall description of what was done
3. **Changes Made**: Bullet list of specific changes
4. **Files Changed**: List of modified files
5. **Tests Passed**: Whether all tests passed
6. **Verification Steps**: How a reviewer can verify the changes
7. **Risk Notes**: Any concerns for reviewers

Respond with a JSON object:
```json
{{
  "title": "PR title",
  "description": "Overall description",
  "changes_made": ["change 1", "change 2"],
  "files_changed": ["file1.py", "file2.py"],
  "tests_passed": true,
  "verification_steps": ["step 1", "step 2"],
  "risk_notes": ["note 1"]
}}
```"""


# =============================================================================
# Helper Functions
# =============================================================================

def format_plan_prompt(feature_request: str, repo_context: str) -> str:
    """Format the plan prompt with context."""
    return PLAN_PROMPT.format(
        feature_request=feature_request,
        repo_context=repo_context,
    )


def format_checklist_prompt(plan: str) -> str:
    """Format the checklist prompt with plan."""
    return CHECKLIST_PROMPT.format(plan=plan)


def format_execute_prompt(
    checklist_item: str,
    file_content: str,
    repo_context: str,
) -> str:
    """Format the execute prompt with context."""
    return EXECUTE_PROMPT.format(
        checklist_item=checklist_item,
        file_content=file_content,
        repo_context=repo_context,
    )


def format_repair_prompt(
    checklist_item: str,
    previous_attempt: str,
    validation_errors: str,
) -> str:
    """Format the repair prompt for failed validations."""
    return EXECUTE_REPAIR_PROMPT.format(
        checklist_item=checklist_item,
        previous_attempt=previous_attempt,
        validation_errors=validation_errors,
    )


def format_summary_prompt(
    feature_request: str,
    changes: str,
    test_results: str,
) -> str:
    """Format the summary prompt with results."""
    return SUMMARY_PROMPT.format(
        feature_request=feature_request,
        changes=changes,
        test_results=test_results,
    )
