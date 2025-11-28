#!/usr/bin/env python3
"""
Command-line script to run the find_duplication tool.

Usage:
    python scripts/find_duplication.py /path/to/project --language python
    python scripts/find_duplication.py /path/to/project --language javascript --construct-type class_definition
    python scripts/find_duplication.py /path/to/project --language python --min-similarity 0.9 --min-lines 10
    python scripts/find_duplication.py /path/to/project --language python --analyze  # Use ranked analysis
    python scripts/find_duplication.py /path/to/project --language python --detailed  # Show diff previews
"""
from ast_grep_mcp.utils.console_logger import console

import argparse
import difflib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

# Add parent directory to path to import main
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, Callable[..., Any]] = {}

    def tool(self, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs: Any) -> None:
        pass


def mock_field(**kwargs: Any) -> Any:
    return kwargs.get("default")


# Mock only MCP imports - don't mock pydantic as it breaks sentry_sdk
sys.modules['mcp.server.fastmcp'] = type(sys)('mcp.server.fastmcp')
sys.modules['mcp.server.fastmcp'].FastMCP = MockFastMCP  # type: ignore

# Now import main
import main  # noqa: E402

# Register the tools
main.register_mcp_tools()

# Get the tool functions
find_duplication = main.mcp.tools.get("find_duplication")  # type: ignore
analyze_deduplication_candidates = main.mcp.tools.get("analyze_deduplication_candidates")  # type: ignore


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


class ColorPrinter:
    """Helper for colored terminal output."""

    def __init__(self, use_color: bool = True):
        self.use_color = use_color

    def colorize(self, text: str, *codes: str) -> str:
        if not self.use_color:
            return text
        return "".join(codes) + text + Colors.RESET

    def bold(self, text: str) -> str:
        return self.colorize(text, Colors.BOLD)

    def red(self, text: str) -> str:
        return self.colorize(text, Colors.RED)

    def green(self, text: str) -> str:
        return self.colorize(text, Colors.GREEN)

    def yellow(self, text: str) -> str:
        return self.colorize(text, Colors.YELLOW)

    def blue(self, text: str) -> str:
        return self.colorize(text, Colors.BLUE)

    def cyan(self, text: str) -> str:
        return self.colorize(text, Colors.CYAN)

    def magenta(self, text: str) -> str:
        return self.colorize(text, Colors.MAGENTA)

    def dim(self, text: str) -> str:
        return self.colorize(text, Colors.DIM)


# Global color printer (initialized in main)
cp = ColorPrinter(use_color=True)


def format_complexity_bar(score: float, width: int = 20) -> str:
    """Create a visual bar representation of a complexity score."""
    filled = int(score * width)
    empty = width - filled

    # Color based on score
    if score >= 0.7:
        bar_color = Colors.GREEN if cp.use_color else ""
    elif score >= 0.4:
        bar_color = Colors.YELLOW if cp.use_color else ""
    else:
        bar_color = Colors.RED if cp.use_color else ""

    reset = Colors.RESET if cp.use_color else ""
    bar = bar_color + "█" * filled + reset + "░" * empty
    return f"[{bar}] {score:.1%}"


def format_priority_level(score: float) -> str:
    """Format priority level with color based on score."""
    if score >= 0.7:
        label = "HIGH"
        return cp.red(cp.bold(f"[{label}]"))
    elif score >= 0.4:
        label = "MEDIUM"
        return cp.yellow(f"[{label}]")
    else:
        label = "LOW"
        return cp.green(f"[{label}]")


def generate_diff_preview(instances: List[Dict[str, Any]], max_lines: int = 15) -> str:
    """Generate a colored diff preview between instances."""
    if len(instances) < 2:
        return ""

    # Get first two instances for comparison
    code1 = instances[0].get('code_preview', '') or instances[0].get('code', '')
    code2 = instances[1].get('code_preview', '') or instances[1].get('code', '')

    if not code1 or not code2:
        return ""

    lines1 = code1.split('\n')[:max_lines]
    lines2 = code2.split('\n')[:max_lines]

    diff = list(difflib.unified_diff(
        lines1, lines2,
        fromfile=instances[0].get('file', 'file1'),
        tofile=instances[1].get('file', 'file2'),
        lineterm=''
    ))

    if not diff:
        return cp.dim("  (identical code)")

    result = []
    for line in diff[:max_lines + 4]:  # Include header + context
        if line.startswith('+++') or line.startswith('---'):
            result.append(cp.bold(line))
        elif line.startswith('+'):
            result.append(cp.green(line))
        elif line.startswith('-'):
            result.append(cp.red(line))
        elif line.startswith('@@'):
            result.append(cp.cyan(line))
        else:
            result.append(line)

    if len(diff) > max_lines + 4:
        result.append(cp.dim(f"  ... ({len(diff) - max_lines - 4} more lines)"))

    return '\n'.join(result)


def format_summary(summary: Dict[str, Any]) -> None:
    """Format the summary section"""
    console.log("\n" + "=" * 80)
    console.log(cp.bold("DUPLICATION ANALYSIS SUMMARY"))
    console.log("=" * 80)
    console.log(f"Total constructs analyzed:    {summary['total_constructs']}")
    console.log(f"Duplicate groups found:       {cp.yellow(str(summary['duplicate_groups']))}")
    console.log(f"Total duplicated lines:       {summary['total_duplicated_lines']}")
    console.log(f"Potential line savings:       {cp.green(str(summary['potential_line_savings']))}")
    console.log(f"Analysis time:                {summary['analysis_time_seconds']:.3f}s")
    console.log("=" * 80)


def format_duplication_groups(groups: List[Dict[str, Any]], detailed: bool = False) -> None:
    """Format duplication groups"""
    if not groups:
        return

    console.log("\n" + "-" * 80)
    console.log(cp.bold("DUPLICATION GROUPS"))
    console.log("-" * 80)

    for group in groups:
        group_id = group['group_id']
        similarity = group['similarity_score']
        console.log(f"\n{cp.cyan('Group ' + str(group_id))} (Similarity: {cp.yellow(f'{similarity:.1%}')})")
        console.log(f"   Found {len(group['instances'])} duplicate instances:")
        for instance in group['instances']:
            console.log(f"   {cp.dim('-')} {instance['file']}:{instance['lines']}")
            if instance['code_preview'] and not detailed:
                preview = instance['code_preview'][:100].replace('\n', ' ')
                console.log(f"     {cp.dim('Preview:')} {preview}...")

        if detailed and len(group['instances']) >= 2:
            console.log(f"\n   {cp.bold('Diff Preview:')}")
            diff = generate_diff_preview(group['instances'])
            if diff:
                for line in diff.split('\n'):
                    console.log(f"   {line}")


def format_refactoring_suggestions(suggestions: List[Dict[str, Any]]) -> None:
    """Format refactoring suggestions"""
    if not suggestions:
        return

    console.log("\n" + "-" * 80)
    console.log(cp.bold("REFACTORING SUGGESTIONS"))
    console.log("-" * 80)

    for suggestion in suggestions:
        console.log(f"\n{cp.yellow('Suggestion #' + str(suggestion['group_id']))}: {suggestion['type']}")
        console.log(f"   {suggestion['description']}")
        console.log(f"   Duplicates: {suggestion['duplicate_count']} instances")
        console.log(f"   Lines per instance: {suggestion['lines_per_duplicate']}")
        console.log(f"   Total duplicated: {cp.green(str(suggestion['total_duplicated_lines']))} lines")
        console.log("\n   Locations:")
        for loc in suggestion['locations']:
            console.log(f"   {cp.dim('-')} {loc}")
        console.log("\n   Recommendation:")
        console.log(f"   {suggestion['suggestion']}")


def format_analyze_results(result: Dict[str, Any], detailed: bool = False) -> None:
    """Format results from analyze_deduplication_candidates tool."""
    metadata = result.get('analysis_metadata', {})
    candidates = result.get('candidates', [])

    # Summary header
    console.log("\n" + "=" * 80)
    console.log(cp.bold("DEDUPLICATION CANDIDATE ANALYSIS"))
    console.log("=" * 80)
    console.log(f"Project:                      {metadata.get('project_path', 'N/A')}")
    console.log(f"Language:                     {metadata.get('language', 'N/A')}")
    console.log(f"Total constructs analyzed:    {metadata.get('total_constructs_analyzed', 0)}")
    console.log(f"Candidate groups found:       {cp.yellow(str(result.get('total_groups', 0)))}")
    console.log(f"Total potential savings:      {cp.green(str(result.get('total_savings_potential', 0)))} lines")
    console.log(f"Analysis time:                {metadata.get('analysis_time_seconds', 0):.3f}s")
    console.log("=" * 80)

    if not candidates:
        console.log(f"\n{cp.green('No duplication candidates found.')}")
        return

    # Ranked candidates
    console.log(f"\n{cp.bold('RANKED CANDIDATES')} (highest priority first)")
    console.log("-" * 80)

    for candidate in candidates:
        rank = candidate.get('rank', '?')
        priority = candidate.get('priority_score', 0)
        similarity = candidate.get('similarity_score', 0)
        instances = candidate.get('instance_count', 0)
        savings = candidate.get('potential_savings', 0)
        avg_lines = candidate.get('avg_lines_per_instance', 0)

        # Header with rank and priority
        console.log(f"\n{cp.bold(f'#{rank}')} {format_priority_level(priority)} Group {candidate.get('group_id', '?')}")

        # Metrics
        console.log(f"   Priority Score: {format_complexity_bar(priority)}")
        console.log(f"   Similarity:     {similarity:.1%}")
        console.log(f"   Instances:      {instances}")
        console.log(f"   Lines/Instance: {avg_lines}")
        console.log(f"   Savings:        {cp.green(str(savings))} lines")

        # Files affected
        files = candidate.get('files_affected', [])
        if files:
            console.log(f"\n   {cp.cyan('Files Affected:')}")
            for f in files[:5]:  # Limit display
                console.log(f"   {cp.dim('-')} {f}")
            if len(files) > 5:
                console.log(f"   {cp.dim(f'... and {len(files) - 5} more')}")

        # Instances with locations
        candidate_instances = candidate.get('instances', [])
        if candidate_instances:
            console.log(f"\n   {cp.cyan('Instances:')}")
            for inst in candidate_instances[:5]:
                file_path = inst.get('file', '')
                start = inst.get('start_line', 0)
                end = inst.get('end_line', 0)
                console.log(f"   {cp.dim('-')} {file_path}:{start}-{end}")
            if len(candidate_instances) > 5:
                console.log(f"   {cp.dim(f'... and {len(candidate_instances) - 5} more')}")

        # Recommendation
        rec = candidate.get('recommendation', '')
        if rec:
            console.log(f"\n   {cp.yellow('Recommendation:')}")
            # Wrap long recommendations
            words = rec.split()
            line = "   "
            for word in words:
                if len(line) + len(word) > 75:
                    console.log(line)
                    line = "   " + word
                else:
                    line += " " + word if line.strip() else word
            if line.strip():
                console.log(line)

        # Detailed diff preview
        if detailed and candidate_instances and len(candidate_instances) >= 2:
            console.log(f"\n   {cp.bold('Diff Preview:')}")
            diff = generate_diff_preview(candidate_instances)
            if diff:
                for line in diff.split('\n'):
                    console.log(f"   {line}")

    # Summary message
    if result.get('message'):
        console.log(f"\n{result['message']}")


def main_cli() -> None:
    """Main CLI entry point"""
    global cp

    parser = argparse.ArgumentParser(
        description="Detect duplicate code in a project using ast-grep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Python functions
  python scripts/find_duplication.py /path/to/project --language python

  # Analyze JavaScript classes with strict similarity
  python scripts/find_duplication.py /path/to/project --language javascript \\
      --construct-type class_definition --min-similarity 0.9

  # Analyze Python methods, ignore small functions
  python scripts/find_duplication.py /path/to/project --language python \\
      --construct-type method_definition --min-lines 10

  # Use ranked analysis with recommendations
  python scripts/find_duplication.py /path/to/project --language python --analyze

  # Show detailed output with diff previews
  python scripts/find_duplication.py /path/to/project --language python --detailed

  # Combine analysis and detailed output
  python scripts/find_duplication.py /path/to/project --language python --analyze --detailed

  # Disable colors for piping to file
  python scripts/find_duplication.py /path/to/project --language python --no-color > report.txt

  # Output as JSON
  python scripts/find_duplication.py /path/to/project --language python --json
        """
    )

    parser.add_argument(
        "project_folder",
        help="Absolute path to the project folder to analyze"
    )

    parser.add_argument(
        "--language", "-l",
        required=True,
        help="Programming language (e.g., python, javascript, typescript, java, go)"
    )

    parser.add_argument(
        "--construct-type", "-c",
        default="function_definition",
        choices=["function_definition", "class_definition", "method_definition"],
        help="Type of code construct to analyze (default: function_definition)"
    )

    parser.add_argument(
        "--min-similarity", "-s",
        type=float,
        default=0.8,
        help="Minimum similarity threshold 0.0-1.0 (default: 0.8)"
    )

    parser.add_argument(
        "--min-lines", "-m",
        type=int,
        default=5,
        help="Minimum lines to consider for duplication (default: 5)"
    )

    parser.add_argument(
        "--max-constructs", "-x",
        type=int,
        default=1000,
        help="Maximum constructs to analyze for performance (0=unlimited, default: 1000)"
    )

    parser.add_argument(
        "--exclude-patterns", "-e",
        nargs="*",
        default=["site-packages", "node_modules", ".venv", "venv", "vendor"],
        help="Path patterns to exclude (e.g., library code). Default: site-packages node_modules .venv venv vendor"
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON instead of formatted text"
    )

    parser.add_argument(
        "--analyze", "-a",
        action="store_true",
        help="Use analyze_deduplication_candidates for ranked results with recommendations"
    )

    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Show detailed output including diff previews for duplicate groups"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        default=100,
        help="Maximum candidates to return when using --analyze (default: 100)"
    )

    parser.add_argument(
        "--include-test-coverage",
        action="store_true",
        default=True,
        help="Include test coverage in analysis (only with --analyze)"
    )

    args = parser.parse_args()

    # Initialize color printer
    use_color = not args.no_color and sys.stdout.isatty() and not args.json
    cp = ColorPrinter(use_color=use_color)

    # Validate project folder
    if not os.path.isabs(args.project_folder):
        console.error(f"Error: Project folder must be an absolute path: {args.project_folder}")
        sys.exit(1)

    if not os.path.isdir(args.project_folder):
        console.error(f"Error: Project folder does not exist: {args.project_folder}")
        sys.exit(1)

    # Validate similarity threshold
    if not 0.0 <= args.min_similarity <= 1.0:
        console.error("Error: min-similarity must be between 0.0 and 1.0")
        sys.exit(1)

    # Validate min lines
    if args.min_lines < 1:
        console.error("Error: min-lines must be at least 1")
        sys.exit(1)

    # Validate max constructs
    if args.max_constructs < 0:
        console.error("Error: max-constructs must be 0 (unlimited) or positive")
        sys.exit(1)

    # Show analysis parameters
    if not args.json:
        console.log(f"Analyzing: {args.project_folder}")
        console.log(f"Language: {args.language}")
        if not args.analyze:
            console.log(f"Construct type: {args.construct_type}")
        console.log(f"Min similarity: {args.min_similarity:.1%}")
        console.log(f"Min lines: {args.min_lines}")
        if args.max_constructs > 0:
            console.log(f"Max constructs: {args.max_constructs}")
        else:
            console.log("Max constructs: unlimited")
        if args.exclude_patterns:
            console.log(f"Excluding patterns: {', '.join(args.exclude_patterns)}")
        if args.analyze:
            console.log(f"Mode: {cp.cyan('Ranked Analysis')}")
        if args.detailed:
            console.log(f"Output: {cp.cyan('Detailed with diff previews')}")
        console.log("\nSearching for duplicates...")

    try:
        if args.analyze:
            # Use analyze_deduplication_candidates tool
            if analyze_deduplication_candidates is None:
                console.error("Error: analyze_deduplication_candidates tool not available")
                sys.exit(1)

            result = analyze_deduplication_candidates(
                project_path=args.project_folder,
                language=args.language,
                min_similarity=args.min_similarity,
                min_lines=args.min_lines,
                max_candidates=args.max_candidates,
                include_test_coverage=args.include_test_coverage,
                exclude_patterns=args.exclude_patterns
            )

            if args.json:
                console.json(result)
            else:
                format_analyze_results(result, detailed=args.detailed)
        else:
            # Use original find_duplication tool
            result = find_duplication(
                project_folder=args.project_folder,
                language=args.language,
                construct_type=args.construct_type,
                min_similarity=args.min_similarity,
                min_lines=args.min_lines,
                max_constructs=args.max_constructs,
                exclude_patterns=args.exclude_patterns
            )

            if args.json:
                # Output as JSON
                console.json(result)
            else:
                # Format and display results
                format_summary(result['summary'])
                format_duplication_groups(result['duplication_groups'], detailed=args.detailed)
                format_refactoring_suggestions(result['refactoring_suggestions'])

                # Print message
                if result.get('message'):
                    console.log(f"\n{result['message']}")

    except Exception as e:
        console.error(f"\nError: {e}")
        if not args.json:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
