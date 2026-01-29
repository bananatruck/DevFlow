"""Repository analysis tools with AST parsing.

These tools provide the agent with structured access to repository content:
- repo_map: Generate file tree with AST summaries
- read_file: Read file content with optional context
- search_repo: Fast text search using ripgrep
- write_file: Safe file writing within repo bounds
"""

from __future__ import annotations

import os
import subprocess
import hashlib
from pathlib import Path
from typing import Any

from src.schemas import ToolResult


# Maximum file size to read (1MB)
MAX_FILE_SIZE = 1024 * 1024


def _is_safe_path(repo_path: str, file_path: str) -> bool:
    """Check if file_path is safely within repo_path."""
    repo_abs = os.path.abspath(repo_path)
    file_abs = os.path.abspath(os.path.join(repo_path, file_path))
    return file_abs.startswith(repo_abs)


async def repo_map(
    repo_path: str,
    max_depth: int = 4,
    include_ast_summary: bool = True,
    ignore_patterns: list[str] | None = None,
) -> ToolResult:
    """Generate repository structure with optional AST summaries.
    
    Args:
        repo_path: Path to the repository
        max_depth: Maximum directory depth to traverse
        include_ast_summary: Include function/class signatures
        ignore_patterns: Patterns to ignore (default: common ignores)
        
    Returns:
        ToolResult with file tree and key file summaries
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(repo_path):
        return ToolResult(
            ok=False,
            error_code="INVALID_PATH",
            error_message=f"Repository path does not exist: {repo_path}",
        )
    
    if ignore_patterns is None:
        ignore_patterns = [
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            ".next", "dist", "build", ".pytest_cache", ".mypy_cache",
            "*.pyc", "*.pyo", ".DS_Store", "*.egg-info"
        ]
    
    tree: dict[str, Any] = {"type": "directory", "name": os.path.basename(repo_path), "children": []}
    key_files: list[dict[str, Any]] = []
    
    def should_ignore(name: str) -> bool:
        for pattern in ignore_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False
    
    def build_tree(path: str, current_depth: int) -> list[dict[str, Any]]:
        if current_depth > max_depth:
            return []
        
        items = []
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return []
        
        for entry in entries:
            if should_ignore(entry):
                continue
            
            full_path = os.path.join(path, entry)
            rel_path = os.path.relpath(full_path, repo_path)
            
            if os.path.isdir(full_path):
                children = build_tree(full_path, current_depth + 1)
                if children or current_depth < 2:  # Always show top-level dirs
                    items.append({
                        "type": "directory",
                        "name": entry,
                        "path": rel_path,
                        "children": children,
                    })
            else:
                file_info: dict[str, Any] = {
                    "type": "file",
                    "name": entry,
                    "path": rel_path,
                }
                
                # Get file size
                try:
                    file_info["size"] = os.path.getsize(full_path)
                except OSError:
                    file_info["size"] = 0
                
                items.append(file_info)
                
                # Add to key files if it's a code file
                if _is_code_file(entry) and file_info["size"] < MAX_FILE_SIZE:
                    key_files.append({
                        "path": rel_path,
                        "size": file_info["size"],
                    })
        
        return items
    
    tree["children"] = build_tree(repo_path, 0)
    
    # Generate AST summaries for key files
    ast_summaries: dict[str, list[str]] = {}
    if include_ast_summary:
        for key_file in key_files[:50]:  # Limit to 50 files
            summary = await _get_ast_summary(
                os.path.join(repo_path, key_file["path"])
            )
            if summary:
                ast_summaries[key_file["path"]] = summary
    
    latency_ms = int((time.perf_counter() - start) * 1000)
    
    return ToolResult(
        ok=True,
        data={
            "tree": tree,
            "key_files": key_files[:50],
            "ast_summaries": ast_summaries,
            "total_files": len(key_files),
        },
        latency_ms=latency_ms,
    )


def _is_code_file(filename: str) -> bool:
    """Check if file is a code file we should analyze."""
    code_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
        ".java", ".c", ".cpp", ".h", ".hpp", ".rb", ".php",
        ".swift", ".kt", ".scala", ".vue", ".svelte",
    }
    return any(filename.endswith(ext) for ext in code_extensions)


async def _get_ast_summary(file_path: str) -> list[str]:
    """Extract function/class signatures using tree-sitter or regex fallback."""
    if not os.path.exists(file_path):
        return []
    
    # Try tree-sitter first
    if file_path.endswith(".py"):
        return await _get_python_ast_summary(file_path)
    
    # Fallback to simple regex-based extraction
    return _get_regex_summary(file_path)


async def _get_python_ast_summary(file_path: str) -> list[str]:
    """Extract Python function/class signatures using AST."""
    import ast
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        
        tree = ast.parse(source)
        signatures = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = ", ".join(arg.arg for arg in node.args.args)
                sig = f"def {node.name}({args})"
                signatures.append(sig)
            elif isinstance(node, ast.AsyncFunctionDef):
                args = ", ".join(arg.arg for arg in node.args.args)
                sig = f"async def {node.name}({args})"
                signatures.append(sig)
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(
                    getattr(base, "id", getattr(base, "attr", ""))
                    for base in node.bases
                )
                sig = f"class {node.name}({bases})" if bases else f"class {node.name}"
                signatures.append(sig)
        
        return signatures[:20]  # Limit signatures per file
        
    except Exception:
        return []


def _get_regex_summary(file_path: str) -> list[str]:
    """Simple regex-based extraction for non-Python files."""
    import re
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(50000)  # First 50KB only
        
        signatures = []
        
        # JavaScript/TypeScript function patterns
        patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            r"(?:export\s+)?class\s+(\w+)",
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            signatures.extend(matches[:10])
        
        return signatures[:20]
        
    except Exception:
        return []


async def read_file(
    repo_path: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> ToolResult:
    """Read file content with optional line range.
    
    Args:
        repo_path: Repository root path
        file_path: Relative path within repo
        start_line: Optional start line (1-indexed)
        end_line: Optional end line (1-indexed, inclusive)
        
    Returns:
        ToolResult with file content
    """
    import time
    start = time.perf_counter()
    
    if not _is_safe_path(repo_path, file_path):
        return ToolResult(
            ok=False,
            error_code="PATH_ESCAPE",
            error_message="File path attempts to escape repository",
        )
    
    full_path = os.path.join(repo_path, file_path)
    
    if not os.path.exists(full_path):
        return ToolResult(
            ok=False,
            error_code="FILE_NOT_FOUND",
            error_message=f"File not found: {file_path}",
            retryable=False,
        )
    
    if not os.path.isfile(full_path):
        return ToolResult(
            ok=False,
            error_code="NOT_A_FILE",
            error_message=f"Path is not a file: {file_path}",
        )
    
    file_size = os.path.getsize(full_path)
    if file_size > MAX_FILE_SIZE:
        return ToolResult(
            ok=False,
            error_code="FILE_TOO_LARGE",
            error_message=f"File too large ({file_size} bytes, max {MAX_FILE_SIZE})",
        )
    
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Apply line range if specified
        if start_line is not None:
            start_idx = max(0, start_line - 1)
        else:
            start_idx = 0
        
        if end_line is not None:
            end_idx = min(len(lines), end_line)
        else:
            end_idx = len(lines)
        
        selected_lines = lines[start_idx:end_idx]
        content = "".join(selected_lines)
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "content": content,
                "path": file_path,
                "total_lines": total_lines,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "size": file_size,
            },
            latency_ms=latency_ms,
        )
        
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="READ_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def search_repo(
    repo_path: str,
    query: str,
    file_pattern: str | None = None,
    max_results: int = 50,
) -> ToolResult:
    """Search repository using ripgrep or fallback to grep.
    
    Args:
        repo_path: Repository root path
        query: Search query (regex supported)
        file_pattern: Optional file pattern (e.g., "*.py")
        max_results: Maximum number of results
        
    Returns:
        ToolResult with search results
    """
    import time
    start = time.perf_counter()
    
    if not os.path.isdir(repo_path):
        return ToolResult(
            ok=False,
            error_code="INVALID_PATH",
            error_message=f"Repository path does not exist: {repo_path}",
        )
    
    # Try ripgrep first, fall back to grep
    cmd = ["rg", "--json", "-m", str(max_results)]
    
    if file_pattern:
        cmd.extend(["-g", file_pattern])
    
    cmd.append(query)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Parse ripgrep JSON output
        import json
        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    matches.append({
                        "path": match_data.get("path", {}).get("text", ""),
                        "line_number": match_data.get("line_number", 0),
                        "line_content": match_data.get("lines", {}).get("text", "").strip(),
                    })
            except json.JSONDecodeError:
                continue
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "matches": matches[:max_results],
                "total_matches": len(matches),
                "query": query,
            },
            latency_ms=latency_ms,
        )
        
    except FileNotFoundError:
        # Ripgrep not installed, fall back to grep
        return await _search_with_grep(repo_path, query, file_pattern, max_results)
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            error_code="SEARCH_TIMEOUT",
            error_message="Search timed out after 30 seconds",
            retryable=True,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="SEARCH_ERROR",
            error_message=str(e),
            retryable=True,
        )


async def _search_with_grep(
    repo_path: str,
    query: str,
    file_pattern: str | None,
    max_results: int,
) -> ToolResult:
    """Fallback search using grep."""
    import time
    start = time.perf_counter()
    
    cmd = ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.ts", query, "."]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        matches = []
        for line in result.stdout.strip().split("\n")[:max_results]:
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                matches.append({
                    "path": parts[0].lstrip("./"),
                    "line_number": int(parts[1]) if parts[1].isdigit() else 0,
                    "line_content": parts[2].strip(),
                })
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "matches": matches,
                "total_matches": len(matches),
                "query": query,
            },
            latency_ms=latency_ms,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="GREP_ERROR",
            error_message=str(e),
        )


async def write_file(
    repo_path: str,
    file_path: str,
    content: str,
    create_dirs: bool = True,
) -> ToolResult:
    """Write content to a file within the repository.
    
    Args:
        repo_path: Repository root path
        file_path: Relative path within repo
        content: File content to write
        create_dirs: Create parent directories if needed
        
    Returns:
        ToolResult with write status
    """
    import time
    start = time.perf_counter()
    
    if not _is_safe_path(repo_path, file_path):
        return ToolResult(
            ok=False,
            error_code="PATH_ESCAPE",
            error_message="File path attempts to escape repository",
        )
    
    full_path = os.path.join(repo_path, file_path)
    
    # Check if file exists (for diff)
    original_content = None
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                original_content = f.read()
        except Exception:
            pass
    
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ToolResult(
            ok=True,
            data={
                "path": file_path,
                "size": len(content),
                "hash": content_hash,
                "created": original_content is None,
                "modified": original_content is not None,
            },
            latency_ms=latency_ms,
            artifacts=[full_path],
        )
        
    except Exception as e:
        return ToolResult(
            ok=False,
            error_code="WRITE_ERROR",
            error_message=str(e),
            retryable=True,
        )
