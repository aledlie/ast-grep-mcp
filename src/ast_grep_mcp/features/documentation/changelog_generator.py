"""Changelog generation service.

This module provides functionality for generating changelogs
from git commits using conventional commit format.
"""
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.documentation import (
    ChangelogEntry,
    ChangelogResult,
    ChangelogVersion,
    ChangeType,
    CommitInfo,
)

logger = get_logger(__name__)


# =============================================================================
# Git Operations
# =============================================================================

def _run_git_command(project_folder: str, args: List[str]) -> Tuple[bool, str]:
    """Run a git command and return output.

    Args:
        project_folder: Project root
        args: Git command arguments

    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=project_folder,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "Git not found"


def _get_commit_range(
    project_folder: str,
    from_version: Optional[str],
    to_version: str,
) -> Tuple[str, str]:
    """Determine commit range for changelog.

    Args:
        project_folder: Project root
        from_version: Starting version (tag or commit)
        to_version: Ending version (tag, commit, or HEAD)

    Returns:
        Tuple of (from_ref, to_ref)
    """
    # Get to_ref
    if to_version.upper() == 'HEAD':
        to_ref = 'HEAD'
    else:
        # Check if it's a tag
        success, _ = _run_git_command(project_folder, ['rev-parse', f'v{to_version}'])
        if success:
            to_ref = f'v{to_version}'
        else:
            success, _ = _run_git_command(project_folder, ['rev-parse', to_version])
            if success:
                to_ref = to_version
            else:
                to_ref = 'HEAD'

    # Get from_ref
    if from_version:
        # Check if it's a tag
        success, _ = _run_git_command(project_folder, ['rev-parse', f'v{from_version}'])
        if success:
            from_ref = f'v{from_version}'
        else:
            from_ref = from_version
    else:
        # Get the first commit or most recent tag
        success, tags = _run_git_command(project_folder, ['tag', '--sort=-version:refname', '-l', 'v*'])
        if success and tags:
            tag_list = tags.split('\n')
            # Skip current version tag if it's to_ref
            for tag in tag_list:
                if tag and tag != to_ref:
                    from_ref = tag
                    break
            else:
                # No previous tag, get first commit
                success, first_commit = _run_git_command(project_folder, ['rev-list', '--max-parents=0', 'HEAD'])
                from_ref = first_commit if success else ''
        else:
            # No tags, get first commit
            success, first_commit = _run_git_command(project_folder, ['rev-list', '--max-parents=0', 'HEAD'])
            from_ref = first_commit if success else ''

    return from_ref, to_ref


def _get_commits(
    project_folder: str,
    from_ref: str,
    to_ref: str,
) -> List[CommitInfo]:
    """Get commits in range.

    Args:
        project_folder: Project root
        from_ref: Starting reference
        to_ref: Ending reference

    Returns:
        List of CommitInfo objects
    """
    commits = []

    # Format: hash|full_hash|author|email|date|subject|body
    log_format = '%h|%H|%an|%ae|%aI|%s|%b'
    separator = '---COMMIT---'

    if from_ref:
        range_arg = f'{from_ref}..{to_ref}'
    else:
        range_arg = to_ref

    success, output = _run_git_command(
        project_folder,
        ['log', range_arg, f'--format={log_format}{separator}']
    )

    if not success:
        logger.warning("git_log_failed", output=output)
        return commits

    # Parse commits
    for commit_str in output.split(separator):
        commit_str = commit_str.strip()
        if not commit_str:
            continue

        parts = commit_str.split('|', 6)
        if len(parts) < 6:
            continue

        hash_short, hash_full, author, email, date, subject = parts[:6]
        body = parts[6] if len(parts) > 6 else ''

        # Parse conventional commit format
        parsed = _parse_conventional_commit(subject, body)

        commit = CommitInfo(
            hash=hash_short,
            full_hash=hash_full,
            message=subject,
            body=body,
            author=author,
            author_email=email,
            date=date,
            change_type=parsed.get('type'),
            scope=parsed.get('scope'),
            is_breaking=parsed.get('is_breaking', False),
            issues=parsed.get('issues', []),
            prs=parsed.get('prs', []),
        )
        commits.append(commit)

    return commits


def _parse_conventional_commit(subject: str, body: str) -> Dict[str, Any]:
    """Parse conventional commit format.

    Format: type(scope)!: description

    Args:
        subject: Commit subject line
        body: Commit body

    Returns:
        Dict with type, scope, is_breaking, issues, prs
    """
    result: Dict[str, Any] = {
        'type': None,
        'scope': None,
        'is_breaking': False,
        'issues': [],
        'prs': [],
    }

    # Parse type(scope)!: pattern
    pattern = re.compile(r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$')
    match = pattern.match(subject)

    if match:
        result['type'] = match.group(1).lower()
        result['scope'] = match.group(2)
        result['is_breaking'] = bool(match.group(3))

    # Check for BREAKING CHANGE in body
    if 'BREAKING CHANGE' in body or 'BREAKING-CHANGE' in body:
        result['is_breaking'] = True

    # Extract issue references
    issue_pattern = re.compile(r'#(\d+)')
    all_text = subject + ' ' + body
    result['issues'] = list(set(issue_pattern.findall(all_text)))

    # Extract PR references (common formats)
    pr_pattern = re.compile(r'(?:pull request|pr|merge request|mr)\s*#?(\d+)', re.IGNORECASE)
    result['prs'] = list(set(pr_pattern.findall(all_text)))

    return result


# =============================================================================
# Changelog Formatting
# =============================================================================

def _map_commit_type_to_change_type(commit_type: Optional[str]) -> ChangeType:
    """Map conventional commit type to changelog change type.

    Args:
        commit_type: Conventional commit type (feat, fix, etc.)

    Returns:
        ChangeType enum
    """
    type_map = {
        'feat': ChangeType.ADDED,
        'feature': ChangeType.ADDED,
        'add': ChangeType.ADDED,
        'fix': ChangeType.FIXED,
        'bugfix': ChangeType.FIXED,
        'bug': ChangeType.FIXED,
        'docs': ChangeType.CHANGED,
        'doc': ChangeType.CHANGED,
        'style': ChangeType.CHANGED,
        'refactor': ChangeType.CHANGED,
        'perf': ChangeType.CHANGED,
        'test': ChangeType.CHANGED,
        'chore': ChangeType.CHANGED,
        'build': ChangeType.CHANGED,
        'ci': ChangeType.CHANGED,
        'deprecate': ChangeType.DEPRECATED,
        'deprecated': ChangeType.DEPRECATED,
        'remove': ChangeType.REMOVED,
        'removed': ChangeType.REMOVED,
        'delete': ChangeType.REMOVED,
        'security': ChangeType.SECURITY,
        'sec': ChangeType.SECURITY,
    }

    if commit_type:
        return type_map.get(commit_type.lower(), ChangeType.CHANGED)

    return ChangeType.CHANGED


def _group_commits_by_version(
    commits: List[CommitInfo],
    project_folder: str,
    to_version: str,
) -> List[ChangelogVersion]:
    """Group commits into versions.

    Args:
        commits: List of commits
        project_folder: Project root
        to_version: Target version

    Returns:
        List of ChangelogVersion objects
    """
    # For now, create a single version for all commits
    # A more sophisticated implementation would detect tags and group by them

    if not commits:
        return []

    # Determine version info
    if to_version.upper() == 'HEAD':
        version_str = 'Unreleased'
        date_str = datetime.now().strftime('%Y-%m-%d')
        is_unreleased = True
    else:
        version_str = to_version
        # Try to get tag date
        success, tag_date = _run_git_command(
            project_folder,
            ['log', '-1', '--format=%aI', f'v{to_version}']
        )
        if success and tag_date:
            date_str = tag_date[:10]  # YYYY-MM-DD
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')
        is_unreleased = False

    # Group entries by change type
    entries: Dict[ChangeType, List[ChangelogEntry]] = {}

    for commit in commits:
        change_type = _map_commit_type_to_change_type(commit.change_type)

        # If breaking change, might want to categorize differently
        if commit.is_breaking:
            # Keep track but don't change category
            pass

        entry = ChangelogEntry(
            change_type=change_type,
            description=commit.message,
            commit_hash=commit.hash,
            scope=commit.scope,
            is_breaking=commit.is_breaking,
            issues=commit.issues,
            prs=commit.prs,
        )

        if change_type not in entries:
            entries[change_type] = []
        entries[change_type].append(entry)

    return [ChangelogVersion(
        version=version_str,
        date=date_str,
        entries=entries,
        is_unreleased=is_unreleased,
    )]


def _format_keepachangelog(versions: List[ChangelogVersion], project_name: str = "") -> str:
    """Format changelog in Keep a Changelog format.

    Args:
        versions: List of versions with entries
        project_name: Project name for header

    Returns:
        Markdown string
    """
    lines = ['# Changelog', '']
    lines.append('All notable changes to this project will be documented in this file.')
    lines.append('')
    lines.append('The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),')
    lines.append('and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).')
    lines.append('')

    # Order of sections
    section_order = [
        ChangeType.ADDED,
        ChangeType.CHANGED,
        ChangeType.DEPRECATED,
        ChangeType.REMOVED,
        ChangeType.FIXED,
        ChangeType.SECURITY,
    ]

    for version in versions:
        # Version header
        if version.is_unreleased:
            lines.append('## [Unreleased]')
        else:
            lines.append(f'## [{version.version}] - {version.date}')
        lines.append('')

        # Sections
        for change_type in section_order:
            if change_type not in version.entries:
                continue

            entries = version.entries[change_type]
            if not entries:
                continue

            lines.append(f'### {change_type.value}')
            lines.append('')

            for entry in entries:
                # Format entry
                msg = entry.description

                # Remove conventional commit prefix if present
                msg = re.sub(r'^(\w+)(?:\([^)]+\))?!?:\s*', '', msg)

                # Add scope if present
                if entry.scope:
                    msg = f'**{entry.scope}:** {msg}'

                # Mark breaking changes
                if entry.is_breaking:
                    msg = f'**BREAKING:** {msg}'

                # Add references
                refs = []
                if entry.issues:
                    refs.extend([f'#{i}' for i in entry.issues])
                if entry.prs:
                    refs.extend([f'PR #{p}' for p in entry.prs])
                if entry.commit_hash:
                    refs.append(f'({entry.commit_hash})')

                if refs:
                    msg = f'{msg} {" ".join(refs)}'

                lines.append(f'- {msg}')

            lines.append('')

    return '\n'.join(lines)


def _format_conventional(versions: List[ChangelogVersion], project_name: str = "") -> str:
    """Format changelog in Conventional Changelog format.

    Args:
        versions: List of versions with entries
        project_name: Project name for header

    Returns:
        Markdown string
    """
    lines = [f'# {project_name or "Project"} Changelog', '']

    for version in versions:
        # Version header
        if version.is_unreleased:
            lines.append('## Unreleased')
        else:
            lines.append(f'## {version.version} ({version.date})')
        lines.append('')

        # Group by scope within type
        for change_type in [ChangeType.ADDED, ChangeType.FIXED, ChangeType.CHANGED, ChangeType.REMOVED, ChangeType.SECURITY]:
            if change_type not in version.entries:
                continue

            entries = version.entries[change_type]
            if not entries:
                continue

            type_name = {
                ChangeType.ADDED: 'Features',
                ChangeType.FIXED: 'Bug Fixes',
                ChangeType.CHANGED: 'Changes',
                ChangeType.REMOVED: 'Removed',
                ChangeType.SECURITY: 'Security',
            }.get(change_type, 'Other')

            lines.append(f'### {type_name}')
            lines.append('')

            # Group by scope
            by_scope: Dict[str, List[ChangelogEntry]] = {}
            for entry in entries:
                scope = entry.scope or 'general'
                if scope not in by_scope:
                    by_scope[scope] = []
                by_scope[scope].append(entry)

            for scope, scope_entries in sorted(by_scope.items()):
                if len(by_scope) > 1:
                    lines.append(f'* **{scope}**')
                    for entry in scope_entries:
                        msg = re.sub(r'^(\w+)(?:\([^)]+\))?!?:\s*', '', entry.description)
                        commit_ref = f' ({entry.commit_hash})' if entry.commit_hash else ''
                        lines.append(f'  * {msg}{commit_ref}')
                else:
                    for entry in scope_entries:
                        msg = re.sub(r'^(\w+)(?:\([^)]+\))?!?:\s*', '', entry.description)
                        commit_ref = f' ({entry.commit_hash})' if entry.commit_hash else ''
                        if entry.is_breaking:
                            msg = f'**BREAKING:** {msg}'
                        lines.append(f'* {msg}{commit_ref}')

            lines.append('')

    return '\n'.join(lines)


# =============================================================================
# Main Generator
# =============================================================================

def generate_changelog_impl(
    project_folder: str,
    from_version: Optional[str] = None,
    to_version: str = "HEAD",
    changelog_format: str = "keepachangelog",
    group_by: str = "type",
) -> ChangelogResult:
    """Generate changelog from git commits.

    Args:
        project_folder: Root folder of the project
        from_version: Starting version (tag or None for last tag)
        to_version: Ending version (tag or HEAD)
        changelog_format: Output format ('keepachangelog', 'conventional', 'json')
        group_by: How to group entries ('type', 'scope')

    Returns:
        ChangelogResult with generated changelog
    """
    start_time = time.time()

    logger.info(
        "generate_changelog_started",
        project_folder=project_folder,
        from_version=from_version,
        to_version=to_version,
        format=changelog_format,
    )

    # Check if git repo
    success, _ = _run_git_command(project_folder, ['rev-parse', '--git-dir'])
    if not success:
        logger.warning("not_a_git_repository")
        return ChangelogResult(
            versions=[],
            markdown="# Changelog\n\nNot a git repository.",
            commits_processed=0,
            commits_skipped=0,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

    # Determine commit range
    from_ref, to_ref = _get_commit_range(project_folder, from_version, to_version)

    # Get commits
    commits = _get_commits(project_folder, from_ref, to_ref)

    # Count commits with/without conventional format
    commits_processed = len(commits)
    commits_skipped = sum(1 for c in commits if not c.change_type)

    # Group into versions
    versions = _group_commits_by_version(commits, project_folder, to_version)

    # Format output
    project_name = os.path.basename(project_folder)

    if changelog_format == 'keepachangelog':
        markdown = _format_keepachangelog(versions, project_name)
    elif changelog_format == 'conventional':
        markdown = _format_conventional(versions, project_name)
    else:  # json format handled by tool layer
        markdown = _format_keepachangelog(versions, project_name)

    execution_time = int((time.time() - start_time) * 1000)

    logger.info(
        "generate_changelog_completed",
        commits_processed=commits_processed,
        commits_skipped=commits_skipped,
        versions=len(versions),
        execution_time_ms=execution_time,
    )

    return ChangelogResult(
        versions=versions,
        markdown=markdown,
        commits_processed=commits_processed,
        commits_skipped=commits_skipped,
        execution_time_ms=execution_time,
    )
