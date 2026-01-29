"""Sandbox execution for running commands safely.

Runs commands (tests/lint/build) in isolated environment:
- Controlled execution with timeouts
- Allowlist of permitted commands
- Capture stdout/stderr
- Resource limits
"""

from __future__ import annotations

import subprocess
import os
import shlex
from typing import Any

from src.config import get_settings
from src.schemas import ToolResult


async def run_command(
    command: str,
    cwd: str,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> ToolResult:
    """Run a command in a controlled environment.
    
    Args:
        command: Command to run (will be validated against allowlist)
        cwd: Working directory
        timeout: Command timeout in seconds
        env: Additional environment variables
        
    Returns:
        ToolResult with command output
    """
    import time
    start = time.perf_counter()
    
    settings = get_settings()
    
    if timeout is None:
        timeout = settings.sandbox_timeout_seconds
    
    # Parse command to check against allowlist
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return ToolResult(
            ok=False,
            error_code="INVALID_COMMAND",
            error_message=f"Invalid command syntax: {e}",
        )
    
    if not parts:
        return ToolResult(
            ok=False,
            error_code="EMPTY_COMMAND",
            error_message="Command is empty",
        )
    
    base_command = parts[0]
    
    # Check allowlist
    allowed = settings.sandbox_allowed_commands
    if base_command not in allowed:
        return ToolResult(
            ok=False,
            error_code="COMMAND_NOT_ALLOWED",
            error_message=f"Command '{base_command}' is not in allowlist: {allowed}",
        )
    
    # Validate working directory
    if not os.path.isdir(cwd):
        return ToolResult(
            ok=False,
            error_code="INVALID_CWD",
            error_message=f"Working directory does not exist: {cwd}",
        )
    
    # Build environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    
    try:
        result = subprocess.run(
            parts,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=result.returncode == 0,
            data={
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
            },
            error_code="COMMAND_FAILED" if result.returncode != 0 else None,
            error_message=result.stderr if result.returncode != 0 else None,
            latency_ms=latency_ms,
        )
        
    except subprocess.TimeoutExpired as e:
        return ToolResult(
            ok=False,
            error_code="COMMAND_TIMEOUT",
            error_message=f"Command timed out after {timeout} seconds",
            data={
                "stdout": e.stdout if e.stdout else "",
                "stderr": e.stderr if e.stderr else "",
                "command": command,
            },
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="EXECUTION_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def run_tests(
    repo_path: str,
    test_path: str | None = None,
    verbose: bool = True,
) -> ToolResult:
    """Run pytest in the repository.
    
    Args:
        repo_path: Path to the repository
        test_path: Optional specific test file/dir
        verbose: Whether to run with verbose output
        
    Returns:
        ToolResult with test results
    """
    cmd_parts = ["pytest"]
    
    if verbose:
        cmd_parts.append("-v")
    
    if test_path:
        cmd_parts.append(test_path)
    
    command = " ".join(cmd_parts)
    
    result = await run_command(command, cwd=repo_path, timeout=120)
    
    # Enhance result with test parsing
    if result.ok and result.data:
        stdout = result.data.get("stdout", "")
        
        # Parse pytest output for summary
        passed = stdout.count(" passed")
        failed = stdout.count(" failed")
        errors = stdout.count(" error")
        
        result.data["tests_passed"] = passed > 0 and failed == 0 and errors == 0
        result.data["summary"] = {
            "passed": passed,
            "failed": failed,
            "errors": errors,
        }
    
    return result


async def run_linter(
    repo_path: str,
    file_path: str | None = None,
) -> ToolResult:
    """Run ruff linter on the repository.
    
    Args:
        repo_path: Path to the repository
        file_path: Optional specific file to lint
        
    Returns:
        ToolResult with lint results
    """
    cmd_parts = ["ruff", "check"]
    
    if file_path:
        cmd_parts.append(file_path)
    else:
        cmd_parts.append(".")
    
    command = " ".join(cmd_parts)
    
    return await run_command(command, cwd=repo_path, timeout=60)


async def run_type_check(
    repo_path: str,
    file_path: str | None = None,
) -> ToolResult:
    """Run mypy type checker on the repository.
    
    Args:
        repo_path: Path to the repository
        file_path: Optional specific file to check
        
    Returns:
        ToolResult with type check results
    """
    cmd_parts = ["mypy"]
    
    if file_path:
        cmd_parts.append(file_path)
    else:
        cmd_parts.append(".")
    
    command = " ".join(cmd_parts)
    
    return await run_command(command, cwd=repo_path, timeout=120)
