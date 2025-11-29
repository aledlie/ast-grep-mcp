"""Documentation sync checker service.

This module provides functionality for keeping documentation
synchronized with code changes.
"""
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.documentation import (
    DocSyncIssue,
    DocSyncResult,
    FunctionSignature,
    ParameterInfo,
)
from .docstring_generator import FunctionSignatureParser

logger = get_logger(__name__)


# =============================================================================
# Docstring Analysis
# =============================================================================

def _extract_python_docstring_params(docstring: str) -> List[str]:
    """Extract parameter names from Python docstrings.

    Supports Google, NumPy, and Sphinx styles.

    Args:
        docstring: Docstring content

    Returns:
        List of parameter names
    """
    params = []

    # Google style: Args:
    args_match = re.search(r'Args:\s*\n((?:\s+\w+.*\n?)+)', docstring)
    if args_match:
        for line in args_match.group(1).split('\n'):
            param_match = re.match(r'\s+(\w+)(?:\s*\(|\s*:)', line)
            if param_match:
                params.append(param_match.group(1))

    # NumPy style: Parameters
    params_match = re.search(r'Parameters\s*\n-+\s*\n((?:.*\n?)+?)(?:\n\w|\Z)', docstring)
    if params_match:
        for line in params_match.group(1).split('\n'):
            param_match = re.match(r'(\w+)\s*:', line)
            if param_match:
                params.append(param_match.group(1))

    # Sphinx style: :param name:
    for match in re.finditer(r':param\s+(\w+):', docstring):
        params.append(match.group(1))

    return params


def _extract_js_docstring_params(docstring: str) -> List[str]:
    """Extract parameter names from JSDoc/Javadoc docstrings.

    Args:
        docstring: Docstring content

    Returns:
        List of parameter names
    """
    return [m.group(1) for m in re.finditer(r'@param\s+(?:\{[^}]+\}\s+)?(\w+)', docstring)]


def _extract_docstring_params(docstring: str, language: str) -> List[str]:
    """Extract documented parameter names from a docstring.

    Args:
        docstring: Docstring content
        language: Programming language

    Returns:
        List of documented parameter names
    """
    if language == "python":
        return _extract_python_docstring_params(docstring)
    elif language in ("typescript", "javascript", "java"):
        return _extract_js_docstring_params(docstring)
    return []


def _extract_docstring_return(docstring: str, language: str) -> bool:
    """Check if docstring documents a return value.

    Args:
        docstring: Docstring content
        language: Programming language

    Returns:
        True if return is documented
    """
    if language == "python":
        # Google style: Returns:
        if re.search(r'Returns:\s*\n', docstring):
            return True
        # NumPy style: Returns
        if re.search(r'Returns\s*\n-+', docstring):
            return True
        # Sphinx style: :return: or :returns:
        if re.search(r':returns?:', docstring):
            return True

    elif language in ("typescript", "javascript"):
        # JSDoc style: @returns or @return
        if re.search(r'@returns?\s', docstring):
            return True

    elif language == "java":
        # Javadoc style: @return
        if re.search(r'@return\s', docstring):
            return True

    return False


def _check_docstring_sync(
    func: FunctionSignature,
    language: str,
) -> List[DocSyncIssue]:
    """Check if a function's docstring is in sync with its signature.

    Args:
        func: Function signature
        language: Programming language

    Returns:
        List of issues found
    """
    issues = []

    if not func.existing_docstring:
        # No docstring - this is an "undocumented" issue
        issues.append(DocSyncIssue(
            issue_type='undocumented',
            file_path=func.file_path,
            line_number=func.start_line,
            function_name=func.name,
            description=f"Function '{func.name}' is missing documentation",
            severity='warning',
        ))
        return issues

    # Extract documented params
    doc_params = set(_extract_docstring_params(func.existing_docstring, language))

    # Get actual params (excluding self/cls)
    actual_params = set(
        p.name for p in func.parameters
        if p.name not in ('self', 'cls')
    )

    # Check for missing params in docstring
    missing_in_doc = actual_params - doc_params
    for param in missing_in_doc:
        issues.append(DocSyncIssue(
            issue_type='mismatch',
            file_path=func.file_path,
            line_number=func.start_line,
            function_name=func.name,
            description=f"Parameter '{param}' is not documented",
            suggested_fix=f"Add documentation for parameter '{param}'",
            severity='info',
        ))

    # Check for documented params that don't exist
    extra_in_doc = doc_params - actual_params
    for param in extra_in_doc:
        issues.append(DocSyncIssue(
            issue_type='stale',
            file_path=func.file_path,
            line_number=func.start_line,
            function_name=func.name,
            description=f"Documented parameter '{param}' does not exist in function signature",
            suggested_fix=f"Remove documentation for parameter '{param}'",
            severity='warning',
        ))

    # Check return documentation
    has_return = func.return_type and func.return_type.lower() not in ('none', 'void')
    doc_has_return = _extract_docstring_return(func.existing_docstring, language)

    if has_return and not doc_has_return:
        issues.append(DocSyncIssue(
            issue_type='mismatch',
            file_path=func.file_path,
            line_number=func.start_line,
            function_name=func.name,
            description=f"Return value of type '{func.return_type}' is not documented",
            suggested_fix="Add return value documentation",
            severity='info',
        ))

    if not has_return and doc_has_return:
        issues.append(DocSyncIssue(
            issue_type='stale',
            file_path=func.file_path,
            line_number=func.start_line,
            function_name=func.name,
            description="Documented return value but function has no return type",
            suggested_fix="Remove return value documentation or add return type annotation",
            severity='info',
        ))

    return issues


# =============================================================================
# Link Checking
# =============================================================================

def _check_markdown_links(file_path: str, project_folder: str) -> List[DocSyncIssue]:
    """Check for broken links in markdown files.

    Args:
        file_path: Path to markdown file
        project_folder: Project root

    Returns:
        List of broken link issues
    """
    issues = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except OSError:
        return issues

    # Pattern for markdown links: [text](url)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    for i, line in enumerate(lines):
        for match in link_pattern.finditer(line):
            text = match.group(1)
            url = match.group(2)

            # Skip external URLs
            if url.startswith(('http://', 'https://', 'mailto:')):
                continue

            # Skip anchors
            if url.startswith('#'):
                continue

            # Check relative file paths
            if url.startswith('/'):
                full_path = os.path.join(project_folder, url[1:])
            else:
                base_dir = os.path.dirname(file_path)
                full_path = os.path.normpath(os.path.join(base_dir, url.split('#')[0]))

            if not os.path.exists(full_path):
                issues.append(DocSyncIssue(
                    issue_type='broken_link',
                    file_path=file_path,
                    line_number=i + 1,
                    description=f"Broken link to '{url}'",
                    suggested_fix=f"Update or remove link to '{url}'",
                    severity='warning',
                ))

    return issues


# =============================================================================
# Main Sync Check
# =============================================================================

def _find_source_files(
    project_folder: str,
    language: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
) -> List[str]:
    """Find source files to check.

    Args:
        project_folder: Project root
        language: Programming language
        include_patterns: Glob patterns to include
        exclude_patterns: Glob patterns to exclude

    Returns:
        List of file paths
    """
    import glob

    files = []

    # Default patterns by language
    if not include_patterns or include_patterns == ['all']:
        default_patterns = {
            'python': ['**/*.py'],
            'typescript': ['**/*.ts', '**/*.tsx'],
            'javascript': ['**/*.js', '**/*.jsx'],
            'java': ['**/*.java'],
        }
        include_patterns = default_patterns.get(language, ['**/*'])

    # Default excludes
    if not exclude_patterns:
        exclude_patterns = [
            '**/node_modules/**',
            '**/__pycache__/**',
            '**/venv/**',
            '**/.venv/**',
            '**/dist/**',
            '**/build/**',
            '**/.git/**',
        ]

    # Find files matching include patterns
    for pattern in include_patterns:
        full_pattern = os.path.join(project_folder, pattern)
        matched = glob.glob(full_pattern, recursive=True)
        files.extend(matched)

    # Remove duplicates
    files = list(set(files))

    # Filter out excluded patterns
    def is_excluded(path: str) -> bool:
        rel_path = os.path.relpath(path, project_folder)
        for pattern in exclude_patterns:
            # Simple pattern matching
            pattern_clean = pattern.replace('**/', '').replace('/**', '')
            if pattern_clean in rel_path:
                return True
        return False

    files = [f for f in files if not is_excluded(f)]

    return files


def _find_markdown_files(project_folder: str) -> List[str]:
    """Find markdown documentation files.

    Args:
        project_folder: Project root

    Returns:
        List of markdown file paths
    """
    import glob

    patterns = ['**/*.md', '**/*.markdown']
    files = []

    for pattern in patterns:
        full_pattern = os.path.join(project_folder, pattern)
        matched = glob.glob(full_pattern, recursive=True)
        files.extend(matched)

    # Exclude node_modules, etc.
    exclude_dirs = ['node_modules', '.git', 'venv', '.venv']
    files = [f for f in files if not any(d in f for d in exclude_dirs)]

    return list(set(files))


def _check_function_docstring(
    func: FunctionSignature,
    language: str,
) -> Tuple[List[DocSyncIssue], bool, bool, Optional[Dict[str, Any]]]:
    """Check a single function's docstring.

    Args:
        func: Function signature
        language: Programming language

    Returns:
        Tuple of (issues, is_documented, is_stale, suggestion)
    """
    # Skip private functions (single underscore prefix)
    if func.name.startswith('_') and not func.name.startswith('__'):
        return [], False, False, None

    issues = _check_docstring_sync(func, language)
    is_documented = bool(func.existing_docstring)
    is_stale = is_documented and any(i.issue_type == 'stale' for i in issues)

    suggestion = None
    if not func.existing_docstring:
        suggestion = {
            'file': func.file_path,
            'line': func.start_line,
            'function': func.name,
            'action': 'add_docstring',
        }

    return issues, is_documented, is_stale, suggestion


def _check_docstrings_in_files(
    project_folder: str,
    language: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
) -> Tuple[List[DocSyncIssue], int, int, int, int, List[Dict[str, Any]]]:
    """Check docstrings across source files.

    Returns:
        Tuple of (issues, total, documented, undocumented, stale, suggestions)
    """
    source_files = _find_source_files(project_folder, language, include_patterns, exclude_patterns)
    parser = FunctionSignatureParser(language)

    all_issues: List[DocSyncIssue] = []
    total_functions = 0
    documented_functions = 0
    undocumented_functions = 0
    stale_docstrings = 0
    suggestions: List[Dict[str, Any]] = []

    for file_path in source_files:
        try:
            functions = parser.parse_file(file_path)
            total_functions += len(functions)

            for func in functions:
                issues, is_documented, is_stale, suggestion = _check_function_docstring(func, language)
                all_issues.extend(issues)

                if is_documented:
                    documented_functions += 1
                    if is_stale:
                        stale_docstrings += 1
                elif suggestion:  # Only count non-private undocumented functions
                    undocumented_functions += 1
                    suggestions.append(suggestion)

        except Exception as e:
            logger.warning("file_parse_error", file=file_path, error=str(e))
            sentry_sdk.capture_exception(e)

    return all_issues, total_functions, documented_functions, undocumented_functions, stale_docstrings, suggestions


def _check_markdown_link_issues(project_folder: str) -> List[DocSyncIssue]:
    """Check all markdown files for broken links.

    Args:
        project_folder: Project root

    Returns:
        List of broken link issues
    """
    all_issues: List[DocSyncIssue] = []
    md_files = _find_markdown_files(project_folder)

    for file_path in md_files:
        try:
            link_issues = _check_markdown_links(file_path, project_folder)
            all_issues.extend(link_issues)
        except Exception as e:
            logger.warning("link_check_error", file=file_path, error=str(e))
            sentry_sdk.capture_exception(e)

    return all_issues


def sync_documentation_impl(
    project_folder: str,
    language: str,
    doc_types: List[str] = None,
    check_only: bool = True,
    include_patterns: List[str] = None,
    exclude_patterns: List[str] = None,
) -> DocSyncResult:
    """Synchronize documentation with code.

    Args:
        project_folder: Root folder of the project
        language: Programming language
        doc_types: Types to check ('docstrings', 'links', 'all')
        check_only: If True, only check without making changes
        include_patterns: File patterns to include
        exclude_patterns: File patterns to exclude

    Returns:
        DocSyncResult with sync status
    """
    start_time = time.time()

    doc_types = doc_types or ['all']
    include_patterns = include_patterns or ['all']
    exclude_patterns = exclude_patterns or []

    logger.info(
        "sync_documentation_started",
        project_folder=project_folder,
        language=language,
        doc_types=doc_types,
        check_only=check_only,
    )

    all_issues: List[DocSyncIssue] = []
    total_functions = 0
    documented_functions = 0
    undocumented_functions = 0
    stale_docstrings = 0
    suggestions: List[Dict[str, Any]] = []

    # Check docstrings
    if 'all' in doc_types or 'docstrings' in doc_types:
        issues, total, documented, undocumented, stale, suggs = _check_docstrings_in_files(
            project_folder, language, include_patterns, exclude_patterns
        )
        all_issues.extend(issues)
        total_functions = total
        documented_functions = documented
        undocumented_functions = undocumented
        stale_docstrings = stale
        suggestions = suggs

    # Check markdown links
    if 'all' in doc_types or 'links' in doc_types:
        all_issues.extend(_check_markdown_link_issues(project_folder))

    # Sort issues by severity
    severity_order = {'error': 0, 'warning': 1, 'info': 2}
    all_issues.sort(key=lambda i: (severity_order.get(i.severity, 3), i.file_path, i.line_number))

    execution_time = int((time.time() - start_time) * 1000)

    logger.info(
        "sync_documentation_completed",
        total_functions=total_functions,
        documented=documented_functions,
        undocumented=undocumented_functions,
        stale=stale_docstrings,
        issues_found=len(all_issues),
        execution_time_ms=execution_time,
    )

    return DocSyncResult(
        total_functions=total_functions,
        documented_functions=documented_functions,
        undocumented_functions=undocumented_functions,
        stale_docstrings=stale_docstrings,
        issues=all_issues,
        suggestions=suggestions,
        files_updated=[],
        check_only=check_only,
        execution_time_ms=execution_time,
    )
