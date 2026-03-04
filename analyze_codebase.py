#!/usr/bin/env python3
"""
Comprehensive codebase analysis using all MCP tools.
This script analyzes the ast-grep-mcp codebase for:
- Code complexity issues
- Code smells
- Duplication opportunities
- Security vulnerabilities
- Code quality standards
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ast_grep_mcp.constants import DeduplicationDefaults, FilePatterns, FormattingDefaults, SemanticVolumeDefaults
from ast_grep_mcp.features.complexity.analyzer import analyze_file_complexity
from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool, detect_code_smells_tool
from ast_grep_mcp.features.deduplication.tools import analyze_deduplication_candidates_tool, find_duplication_tool
from ast_grep_mcp.features.quality.security_scanner import detect_security_issues_impl
from ast_grep_mcp.features.quality.tools import apply_standards_fixes_tool, enforce_standards_tool, generate_quality_report_tool
from ast_grep_mcp.models.complexity import ComplexityThresholds

DEFAULT_PROJECT_FOLDER = "src/ast_grep_mcp"
DEFAULT_LANGUAGE = "python"
EXCLUDE_PATTERNS = FilePatterns.DEFAULT_EXCLUDE + FilePatterns.TEST_EXCLUDE + FilePatterns.MINIFIED_EXCLUDE
TOP_FILES_COUNT = 5
LANGUAGE_EXTENSIONS = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "java": "java",
    "rust": "rs",
    "go": "go",
    "ruby": "rb",
    "cpp": "cpp",
    "c": "c",
}


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * FormattingDefaults.WIDE_SECTION_WIDTH}")
    print(f" {title}")
    print("=" * FormattingDefaults.WIDE_SECTION_WIDTH)


def _discover_source_files(project_folder: str, language: str) -> list[Path]:
    """Discover source files in the project folder by language."""
    ext = LANGUAGE_EXTENSIONS.get(language, language)
    glob_pattern = f"*.{ext}"
    folder = Path(project_folder)
    if not folder.is_dir():
        return []
    # Derive dir names from glob patterns like "**/node_modules/**" -> "node_modules"
    exclude_dirs = {p.strip("**/") for p in FilePatterns.DEFAULT_EXCLUDE}
    # Derive suffixes from glob patterns like "**/*.min.js" -> ".min.js"
    exclude_suffixes = {p.removeprefix("**/").removeprefix("*") for p in FilePatterns.MINIFIED_EXCLUDE}
    return [
        f for f in sorted(folder.rglob(glob_pattern))
        if not any(part in exclude_dirs for part in f.parts)
        and not any(str(f).endswith(s) for s in exclude_suffixes)
    ]


def analyze_individual_files(project_folder: str, language: str):
    """Analyze the top most complex files individually."""
    print_section("PHASE 1: Individual File Complexity Analysis")

    source_files = _discover_source_files(project_folder, language)
    if not source_files:
        print(f"\nNo {language} source files found in {project_folder}")
        return

    # First pass: score each file by max cognitive complexity
    thresholds = ComplexityThresholds()
    file_scores: list[tuple[str, int]] = []
    for f in source_files:
        try:
            functions = analyze_file_complexity(str(f), language, thresholds)
            max_cog = max((fn.metrics.cognitive for fn in functions), default=0)
            file_scores.append((str(f), max_cog))
        except Exception:
            continue

    # Take the top N files by worst cognitive complexity
    top_files = [path for path, _ in sorted(file_scores, key=lambda x: x[1], reverse=True)[:TOP_FILES_COUNT]]

    print(f"\nAnalyzing top {len(top_files)} most complex files out of {len(source_files)} total:")

    for file_path in top_files:
        print(f"\n--- {file_path} ---")
        try:
            functions = analyze_file_complexity(file_path, language, thresholds)
            critical = [
                f for f in functions
                if f.metrics.cyclomatic > thresholds.cyclomatic or f.metrics.cognitive > thresholds.cognitive
            ]

            print(f"Total functions: {len(functions)}")
            print(f"Critical functions: {len(critical)}")

            if critical:
                print("\nWorst offenders:")
                for func in sorted(critical, key=lambda x: x.metrics.cognitive, reverse=True)[:3]:
                    print(f"  - {func.function_name} (line {func.start_line})")
                    print(
                        f"    Cyclomatic: {func.metrics.cyclomatic}, Cognitive: {func.metrics.cognitive}, "
                        f"Nesting: {func.metrics.nesting_depth}, Lines: {func.metrics.lines}"
                    )
        except Exception as e:
            print(f"  Exception: {e}")


def analyze_project_complexity(project_folder: str, language: str):
    """Run project-wide complexity analysis."""
    print_section("PHASE 2: Project-Wide Complexity Analysis")

    try:
        result = analyze_complexity_tool(
            project_folder=project_folder,
            language=language,
            include_patterns=[f"**/*.{LANGUAGE_EXTENSIONS.get(language, language)}"],
            exclude_patterns=EXCLUDE_PATTERNS,
            store_results=False,
            include_trends=False,
        )

        if result.get("success"):
            summary = result.get("summary", {})
            print(f"\nTotal functions analyzed: {summary.get('total_functions', 0)}")
            print(f"Functions exceeding thresholds: {summary.get('exceeding_thresholds', 0)}")
            print(f"Percentage over threshold: {summary.get('percentage_exceeding', 0):.1f}%")
            print(f"\nAverage cyclomatic complexity: {summary.get('average_cyclomatic', 0):.2f}")
            print(f"Average cognitive complexity: {summary.get('average_cognitive', 0):.2f}")
            print(f"Average nesting depth: {summary.get('average_nesting', 0):.2f}")
            print(f"Average function length: {summary.get('average_length', 0):.1f} lines")

            exceeding = result.get("exceeding_functions", [])
            if exceeding:
                print("\nTop 10 most complex functions by cognitive complexity:")
                for i, func in enumerate(sorted(exceeding, key=lambda x: x.get("cognitive", 0), reverse=True)[:10], 1):
                    print(f"  {i}. {func['file']}:{func['name']} (line {func['start_line']})")
                    print(
                        f"     Cyclomatic: {func['cyclomatic']}, Cognitive: {func['cognitive']}, "
                        f"Nesting: {func['nesting_depth']}, Lines: {func['length']}"
                    )
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during project complexity analysis: {e}")
        import traceback

        traceback.print_exc()


def detect_code_smells(project_folder: str, language: str):
    """Run code smell detection."""
    print_section("PHASE 3: Code Smell Detection")

    try:
        result = detect_code_smells_tool(
            project_folder=project_folder,
            language=language,
            include_patterns=[f"**/*.{LANGUAGE_EXTENSIONS.get(language, language)}"],
            exclude_patterns=EXCLUDE_PATTERNS,
        )

        if result.get("success"):
            summary = result.get("summary", {})
            print(f"\nTotal files analyzed: {summary.get('total_files', 0)}")
            print(f"Files with smells: {summary.get('files_with_smells', 0)}")
            print(f"Total smells found: {summary.get('total_smells', 0)}")

            by_severity = summary.get("by_severity", {})
            print("\nBy severity:")
            print(f"  High: {by_severity.get('high', 0)}")
            print(f"  Medium: {by_severity.get('medium', 0)}")
            print(f"  Low: {by_severity.get('low', 0)}")

            smells = result.get("smells", [])
            if smells:
                print("\nTop 10 code smells:")
                for smell in smells[:10]:
                    print(f"  - [{smell.get('severity', 'unknown').upper()}] {smell.get('type', 'unknown')}")
                    print(f"    File: {smell.get('file', 'unknown')}:{smell.get('line', '?')}")
                    print(f"    {smell.get('message', 'No message')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during code smell detection: {e}")
        import traceback

        traceback.print_exc()


def detect_security_issues(project_folder: str, language: str):
    """Run security vulnerability scanning."""
    print_section("PHASE 4: Security Vulnerability Scanning")

    try:
        result = detect_security_issues_impl(
            project_folder=project_folder,
            language=language,
        )

        summary = result.summary
        print(f"\nTotal files scanned: {summary.get('total_files', 0)}")
        print(f"Total issues found: {summary.get('total_issues', 0)}")

        by_severity = summary.get("by_severity", {})
        print("\nBy severity:")
        print(f"  Critical: {by_severity.get('critical', 0)}")
        print(f"  High: {by_severity.get('high', 0)}")
        print(f"  Medium: {by_severity.get('medium', 0)}")
        print(f"  Low: {by_severity.get('low', 0)}")

        by_category = summary.get("by_category", {})
        if by_category:
            print("\nBy category:")
            for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                print(f"  {category}: {count}")

        if result.issues:
            print("\nTop 10 security issues:")
            for issue in result.issues[:10]:
                print(f"  - [{issue.severity.upper()}] {issue.issue_type}")
                print(f"    File: {issue.file}:{issue.line}")
                print(f"    {issue.description}")
    except Exception as e:
        print(f"Exception during security scanning: {e}")
        import traceback

        traceback.print_exc()


def analyze_duplication(project_folder: str, language: str):
    """Analyze code duplication opportunities."""
    print_section("PHASE 5: Code Duplication Analysis")

    try:
        find_result = find_duplication_tool(
            project_folder=project_folder,
            language=language,
            min_similarity=DeduplicationDefaults.MIN_SIMILARITY,
            min_lines=10,
            exclude_patterns=EXCLUDE_PATTERNS,
        )

        groups = find_result.get("groups", [])
        if not groups:
            print("\nNo duplication groups found.")
            return

        result = analyze_deduplication_candidates_tool(
            project_path=project_folder,
            language=language,
            min_similarity=DeduplicationDefaults.MIN_SIMILARITY,
            min_lines=10,
            exclude_patterns=EXCLUDE_PATTERNS,
        )

        if result.get("success"):
            summary = result.get("summary", {})
            print(f"\nTotal files analyzed: {summary.get('total_files', 0)}")
            print(f"Duplication groups found: {summary.get('total_groups', 0)}")
            print(f"Total duplicated instances: {summary.get('total_instances', 0)}")

            if summary.get("total_groups", 0) > 0:
                print(f"Average group size: {summary.get('average_group_size', 0):.1f} instances")
                print(f"Average similarity: {summary.get('average_similarity', 0):.1%}")
                print(f"Estimated LOC savings: {summary.get('estimated_loc_savings', 0)}")

            dedup_groups = result.get("groups", [])
            if dedup_groups:
                print(f"\nTop {SemanticVolumeDefaults.TOP_RESULTS_LIMIT} duplication groups by potential savings:")
                for i, group in enumerate(dedup_groups[: SemanticVolumeDefaults.TOP_RESULTS_LIMIT], 1):
                    print(f"  {i}. Group with {group.get('instance_count', 0)} instances ({group.get('similarity', 0):.1%} similar)")
                    print(f"     Potential LOC savings: {group.get('potential_loc_savings', 0)} lines")
                    instances = group.get("instances", [])
                    if instances:
                        print("     Locations:")
                        for inst in instances[:3]:
                            print(f"       - {inst.get('file', 'unknown')}:{inst.get('start_line', '?')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during duplication analysis: {e}")
        import traceback

        traceback.print_exc()


def generate_summary_report(project_folder: str, language: str, apply_fixes: bool = False):
    """Generate comprehensive quality report and optionally apply fixes."""
    print_section("PHASE 6: Generate Comprehensive Quality Report")

    try:
        # First run enforcement to get the result needed by the report generator
        enforcement_result = enforce_standards_tool(
            project_folder=project_folder,
            language=language,
            include_patterns=[f"**/*.{LANGUAGE_EXTENSIONS.get(language, language)}"],
            exclude_patterns=EXCLUDE_PATTERNS,
        )

        result = generate_quality_report_tool(
            enforcement_result=enforcement_result,
            project_name="ast-grep-mcp",
            output_format="markdown",
            save_to_file="QUALITY_REPORT.md",
        )

        if result.get("success"):
            print("\nQuality report generated successfully!")
            report_path = result.get("file_path")
            if report_path:
                print(f"Report saved to: {report_path}")

            report_content = result.get("report", "")
            if report_content:
                print("\nReport Summary:")
                lines = report_content.split("\n")
                in_summary = False
                for line in lines[: SemanticVolumeDefaults.SUMMARY_PREVIEW_LIMIT]:
                    if "## Summary" in line or "## Executive Summary" in line:
                        in_summary = True
                    if in_summary:
                        print(line)
                        if line.startswith("##") and "Summary" not in line:
                            break
        else:
            print(f"Error: {result.get('error')}")

        # Apply fixes if requested
        if apply_fixes:
            _apply_fixes(enforcement_result, language, project_folder=project_folder)

    except Exception as e:
        print(f"Exception during report generation: {e}")
        import traceback

        traceback.print_exc()


def _run_tsc_check(project_folder: str) -> bool:
    """Run tsc --noEmit to verify no type errors after fixes.

    Args:
        project_folder: Path to the project folder

    Returns:
        True if tsc passes (or is not available), False if errors found
    """
    tsconfig = Path(project_folder) / "tsconfig.json"
    if not tsconfig.exists():
        return True

    print("\nRunning tsc --noEmit to verify fixes...")
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=project_folder,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print("tsc --noEmit: PASSED (no type errors)")
            return True

        error_lines = result.stdout.strip().splitlines() if result.stdout else []
        error_count = sum(1 for line in error_lines if ": error TS" in line)
        print(f"tsc --noEmit: FAILED ({error_count} type errors)")
        # Show bounded error preview
        for line in error_lines[: SemanticVolumeDefaults.DETAIL_RESULTS_LIMIT]:
            if ": error TS" in line:
                print(f"  {line}")
        if error_count > SemanticVolumeDefaults.DETAIL_RESULTS_LIMIT:
            print(f"  ... and {error_count - SemanticVolumeDefaults.DETAIL_RESULTS_LIMIT} more errors")
        return False
    except FileNotFoundError:
        print("tsc not found, skipping type check")
        return True
    except subprocess.TimeoutExpired:
        print("tsc --noEmit timed out after 120s, skipping")
        return True


def _is_cli_entry_point(file_path: str) -> bool:
    """Check if a file is a CLI entry point (has if __name__ == '__main__')."""
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        return '__name__' in content and "'__main__'" in content or '"__main__"' in content
    except (OSError, UnicodeDecodeError):
        return False


# Rules that delete lines rather than replacing them — dangerous for CLI entry points.
# Directory/file-name patterns (scripts/, bin/, cli/, *_runner.py, etc.) are handled
# by each rule's exclude_files in rules.py.  This filter catches the remaining case:
# files containing `if __name__ == '__main__'` which can't be expressed as a glob.
_DESTRUCTIVE_RULES = {"no-print-production", "no-console-log", "no-system-out"}


def _filter_destructive_violations(violations: list[dict]) -> tuple[list[dict], int]:
    """Filter out removal-rule violations targeting CLI entry points.

    Skips violations from _DESTRUCTIVE_RULES when the target file contains
    ``if __name__ == '__main__'``, indicating intentional user-facing output.
    Directory and filename-based exclusions are handled at detection time by
    each rule's ``exclude_files`` patterns.

    Returns:
        Tuple of (filtered_violations, skipped_count)
    """
    filtered = []
    skipped = 0
    cli_cache: dict[str, bool] = {}

    for v in violations:
        rule_id = v.get("rule_id", "")
        file_path = v.get("file", "")

        if rule_id in _DESTRUCTIVE_RULES:
            if file_path not in cli_cache:
                cli_cache[file_path] = _is_cli_entry_point(file_path)
            if cli_cache[file_path]:
                skipped += 1
                continue

        filtered.append(v)

    return filtered, skipped


def _apply_fixes(enforcement_result: dict, language: str, project_folder: str = ""):
    """Apply automatic standards fixes from enforcement violations."""
    print_section("PHASE 7: Apply Standards Fixes")

    violations = enforcement_result.get("violations", [])
    if not violations:
        print("\nNo violations to fix.")
        return

    # Filter out destructive fixes targeting CLI scripts and test runners
    violations, skipped = _filter_destructive_violations(violations)
    if skipped:
        print(f"\nSkipped {skipped} violations in CLI/test files (removal rules would delete intentional output)")
    if not violations:
        print("No remaining violations to fix after filtering.")
        return

    try:
        # Dry run first
        dry_result = apply_standards_fixes_tool(
            violations=violations,
            language=language,
            fix_types=["safe"],
            dry_run=True,
            create_backup=True,
        )

        summary = dry_result.get("summary", {})
        fixable = summary.get("total_violations", 0)
        safe_count = sum(1 for r in dry_result.get("results", []) if r.get("fix_type") == "safe")
        print(f"\nDry run: {safe_count} of {fixable} violations can be auto-fixed (safe fixes only)")

        if safe_count == 0:
            print("No auto-fixable violations found.")
            return

        # Apply fixes
        fix_result = apply_standards_fixes_tool(
            violations=violations,
            language=language,
            fix_types=["safe"],
            dry_run=False,
            create_backup=True,
        )

        fix_summary = fix_result.get("summary", {})
        print(f"\nFixed: {fix_summary.get('fixes_successful', 0)} violations")
        print(f"Failed: {fix_summary.get('fixes_failed', 0)}")
        print(f"Files modified: {fix_summary.get('files_modified', 0)}")
        backup_id = fix_result.get("backup_id")
        if backup_id:
            print(f"Backup ID: {backup_id}")

        # Post-fix type check for TypeScript
        if language == "typescript" and project_folder:
            if not _run_tsc_check(project_folder):
                print(f"\nWARNING: Type errors detected after fixes. Backup available: {backup_id}")
                print("Review errors above and restore from backup if needed.")

    except Exception as e:
        print(f"Exception during fix application: {e}")
        import traceback

        traceback.print_exc()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Comprehensive codebase analysis using MCP tools."
    )
    parser.add_argument(
        "project_folder",
        nargs="?",
        default=DEFAULT_PROJECT_FOLDER,
        help=f"Path to the project folder to analyze (default: {DEFAULT_PROJECT_FOLDER})",
    )
    parser.add_argument(
        "-l", "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Source language (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe auto-fixes for standards violations",
    )
    return parser.parse_args()


def main():
    """Run all analyses."""
    args = parse_args()
    project_folder = args.project_folder
    language = args.language

    folder = Path(project_folder)
    if not folder.is_dir():
        print(f"Error: '{project_folder}' is not a valid directory")
        sys.exit(1)

    print("=" * FormattingDefaults.WIDE_SECTION_WIDTH)
    print(f" COMPREHENSIVE CODEBASE ANALYSIS - {project_folder}")
    print("=" * FormattingDefaults.WIDE_SECTION_WIDTH)
    print(f"\nTarget: {project_folder} ({language})")
    print("This analysis uses MCP tools to evaluate code quality,")
    print("complexity, security, and duplication opportunities.\n")

    analyze_individual_files(project_folder, language)
    analyze_project_complexity(project_folder, language)
    detect_code_smells(project_folder, language)
    detect_security_issues(project_folder, language)
    analyze_duplication(project_folder, language)
    generate_summary_report(project_folder, language, apply_fixes=args.fix)

    print_section("ANALYSIS COMPLETE")
    print("\nAll phases completed. Review the output above and QUALITY_REPORT.md")
    print("for detailed findings and recommendations.")


if __name__ == "__main__":
    main()
