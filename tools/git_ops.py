"""Git operations.

Responsibilities:
- clone repo to working directory
- create branch
- commit changes
- push branch
- open PR (optional later)

Security:
- restrict allowed commands and sanitize inputs
"""

from __future__ import annotations

from typing import Optional


def clone_repo(repo_url: str, dest: str) -> str:
    """Clone repository into dest (placeholder)."""
    # TODO: Implement using subprocess with safe allowlist
    return dest
