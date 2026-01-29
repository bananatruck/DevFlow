"""Git operations tooling.

Provides safe git operations within repositories:
- git_status: Get current repo status
- git_create_branch: Create and checkout a new branch
- git_commit: Stage and commit changes
- git_diff: Get diff of changes
"""

from __future__ import annotations

import subprocess
import os
from typing import Any

from src.schemas import ToolResult


async def git_status(repo_path: str) -> ToolResult:
    """Get git status of the repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        ToolResult with status information
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return ToolResult(
            ok=False,
            error_code="NOT_A_GIT_REPO",
            error_message="Directory is not a git repository",
        )
    
    try:
        # Get branch name
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        current_branch = branch_result.stdout.strip()
        
        # Get status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        # Parse status
        changes = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
        }
        
        for line in status_result.stdout.strip().split("\n"):
            if not line:
                continue
            code = line[:2]
            file_path = line[3:]
            
            if code[0] == "M" or code[1] == "M":
                changes["modified"].append(file_path)
            elif code[0] == "A":
                changes["added"].append(file_path)
            elif code[0] == "D":
                changes["deleted"].append(file_path)
            elif code[0] == "?" and code[1] == "?":
                changes["untracked"].append(file_path)
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "branch": current_branch,
                "changes": changes,
                "is_clean": len(status_result.stdout.strip()) == 0,
            },
            latency_ms=latency_ms,
        )
        
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            error_code="GIT_TIMEOUT",
            error_message="Git command timed out",
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="GIT_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def git_create_branch(
    repo_path: str,
    branch_name: str,
    checkout: bool = True,
) -> ToolResult:
    """Create a new git branch.
    
    Args:
        repo_path: Path to the repository
        branch_name: Name of the branch to create
        checkout: Whether to checkout the new branch
        
    Returns:
        ToolResult with branch information
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return ToolResult(
            ok=False,
            error_code="NOT_A_GIT_REPO",
            error_message="Directory is not a git repository",
        )
    
    # Sanitize branch name
    safe_name = branch_name.replace(" ", "-").replace("/", "-")
    if safe_name != branch_name:
        branch_name = safe_name
    
    try:
        if checkout:
            cmd = ["git", "checkout", "-b", branch_name]
        else:
            cmd = ["git", "branch", branch_name]
        
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            return ToolResult(
                ok=False,
                error_code="BRANCH_CREATE_FAILED",
                error_message=result.stderr.strip(),
            )
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "branch": branch_name,
                "checked_out": checkout,
            },
            latency_ms=latency_ms,
        )
        
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            error_code="GIT_TIMEOUT",
            error_message="Git command timed out",
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="GIT_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def git_commit(
    repo_path: str,
    message: str,
    add_all: bool = True,
) -> ToolResult:
    """Stage and commit changes.
    
    Args:
        repo_path: Path to the repository
        message: Commit message
        add_all: Whether to add all changes before committing
        
    Returns:
        ToolResult with commit information
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return ToolResult(
            ok=False,
            error_code="NOT_A_GIT_REPO",
            error_message="Directory is not a git repository",
        )
    
    try:
        # Stage changes
        if add_all:
            add_result = subprocess.run(
                ["git", "add", "-A"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if add_result.returncode != 0:
                return ToolResult(
                    ok=False,
                    error_code="GIT_ADD_FAILED",
                    error_message=add_result.stderr.strip(),
                )
        
        # Commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if commit_result.returncode != 0:
            # Check if there's nothing to commit
            if "nothing to commit" in commit_result.stdout:
                return ToolResult(
                    ok=True,
                    data={
                        "committed": False,
                        "message": "Nothing to commit",
                    },
                )
            return ToolResult(
                ok=False,
                error_code="GIT_COMMIT_FAILED",
                error_message=commit_result.stderr.strip(),
            )
        
        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit_hash = hash_result.stdout.strip()[:8]
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "committed": True,
                "hash": commit_hash,
                "message": message,
            },
            latency_ms=latency_ms,
        )
        
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            error_code="GIT_TIMEOUT",
            error_message="Git command timed out",
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="GIT_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def git_diff(
    repo_path: str,
    staged: bool = False,
    file_path: str | None = None,
) -> ToolResult:
    """Get diff of changes in the repository.
    
    Args:
        repo_path: Path to the repository
        staged: Whether to show staged changes only
        file_path: Optional specific file to diff
        
    Returns:
        ToolResult with diff content
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return ToolResult(
            ok=False,
            error_code="NOT_A_GIT_REPO",
            error_message="Directory is not a git repository",
        )
    
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if file_path:
            cmd.append("--")
            cmd.append(file_path)
        
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        diff_content = result.stdout
        
        # Parse diff stats
        stats_result = subprocess.run(
            cmd + ["--stat"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "diff": diff_content,
                "stats": stats_result.stdout.strip(),
                "has_changes": len(diff_content.strip()) > 0,
            },
            latency_ms=latency_ms,
        )
        
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            error_code="GIT_TIMEOUT",
            error_message="Git command timed out",
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="GIT_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def git_log(
    repo_path: str,
    max_commits: int = 10,
) -> ToolResult:
    """Get recent git commits.
    
    Args:
        repo_path: Path to the repository
        max_commits: Maximum number of commits to return
        
    Returns:
        ToolResult with commit history
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return ToolResult(
            ok=False,
            error_code="NOT_A_GIT_REPO",
            error_message="Directory is not a git repository",
        )
    
    try:
        result = subprocess.run(
            [
                "git", "log",
                f"-{max_commits}",
                "--format=%H|%s|%an|%ad",
                "--date=short",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                })
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "commits": commits,
                "count": len(commits),
            },
            latency_ms=latency_ms,
        )
        
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            error_code="GIT_TIMEOUT",
            error_message="Git command timed out",
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="GIT_ERROR",
            error_message=str(e),
            retryable=True,
        )
