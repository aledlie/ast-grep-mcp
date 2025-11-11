#!/usr/bin/env python3
"""
Command-line script to run the find_duplication tool.

Usage:
    python scripts/find_duplication.py /path/to/project --language python
    python scripts/find_duplication.py /path/to/project --language javascript --construct-type class_definition
    python scripts/find_duplication.py /path/to/project --language python --min-similarity 0.9 --min-lines 10
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import main
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs):
        pass


def mock_field(**kwargs):
    return kwargs.get("default")


# Mock the imports
sys.modules['mcp.server.fastmcp'] = type(sys)('mcp.server.fastmcp')
sys.modules['mcp.server.fastmcp'].FastMCP = MockFastMCP

sys.modules['pydantic'] = type(sys)('pydantic')
sys.modules['pydantic'].Field = mock_field
sys.modules['pydantic'].BaseModel = object
sys.modules['pydantic'].ConfigDict = dict
sys.modules['pydantic'].field_validator = lambda *args, **kwargs: lambda f: f

# Now import main
import main

# Register the tools
main.register_mcp_tools()

# Get the tool function
find_duplication = main.mcp.tools.get("find_duplication")


def format_summary(summary):
    """Format the summary section"""
    print("\n" + "=" * 80)
    print("DUPLICATION ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Total constructs analyzed:    {summary['total_constructs']}")
    print(f"Duplicate groups found:       {summary['duplicate_groups']}")
    print(f"Total duplicated lines:       {summary['total_duplicated_lines']}")
    print(f"Potential line savings:       {summary['potential_line_savings']}")
    print(f"Analysis time:                {summary['analysis_time_seconds']:.3f}s")
    print("=" * 80)


def format_duplication_groups(groups):
    """Format duplication groups"""
    if not groups:
        return

    print("\n" + "-" * 80)
    print("DUPLICATION GROUPS")
    print("-" * 80)

    for group in groups:
        print(f"\n📦 Group {group['group_id']} (Similarity: {group['similarity_score']:.1%})")
        print(f"   Found {len(group['instances'])} duplicate instances:")
        for instance in group['instances']:
            print(f"   • {instance['file']}:{instance['lines']}")
            if instance['code_preview']:
                preview = instance['code_preview'][:100].replace('\n', ' ')
                print(f"     Preview: {preview}...")


def format_refactoring_suggestions(suggestions):
    """Format refactoring suggestions"""
    if not suggestions:
        return

    print("\n" + "-" * 80)
    print("REFACTORING SUGGESTIONS")
    print("-" * 80)

    for suggestion in suggestions:
        print(f"\n💡 Suggestion #{suggestion['group_id']}: {suggestion['type']}")
        print(f"   {suggestion['description']}")
        print(f"   Duplicates: {suggestion['duplicate_count']} instances")
        print(f"   Lines per instance: {suggestion['lines_per_duplicate']}")
        print(f"   Total duplicated: {suggestion['total_duplicated_lines']} lines")
        print(f"\n   Locations:")
        for loc in suggestion['locations']:
            print(f"   • {loc}")
        print(f"\n   Recommendation:")
        print(f"   {suggestion['suggestion']}")


def main_cli():
    """Main CLI entry point"""
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

    args = parser.parse_args()

    # Validate project folder
    if not os.path.isabs(args.project_folder):
        print(f"Error: Project folder must be an absolute path: {args.project_folder}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.project_folder):
        print(f"Error: Project folder does not exist: {args.project_folder}", file=sys.stderr)
        sys.exit(1)

    # Validate similarity threshold
    if not 0.0 <= args.min_similarity <= 1.0:
        print(f"Error: min-similarity must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    # Validate min lines
    if args.min_lines < 1:
        print(f"Error: min-lines must be at least 1", file=sys.stderr)
        sys.exit(1)

    # Validate max constructs
    if args.max_constructs < 0:
        print(f"Error: max-constructs must be 0 (unlimited) or positive", file=sys.stderr)
        sys.exit(1)

    # Show analysis parameters
    if not args.json:
        print(f"Analyzing: {args.project_folder}")
        print(f"Language: {args.language}")
        print(f"Construct type: {args.construct_type}")
        print(f"Min similarity: {args.min_similarity:.1%}")
        print(f"Min lines: {args.min_lines}")
        if args.max_constructs > 0:
            print(f"Max constructs: {args.max_constructs}")
        else:
            print(f"Max constructs: unlimited")
        if args.exclude_patterns:
            print(f"Excluding patterns: {', '.join(args.exclude_patterns)}")
        print("\nSearching for duplicates...")

    try:
        # Call the find_duplication tool
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
            print(json.dumps(result, indent=2))
        else:
            # Format and display results
            format_summary(result['summary'])
            format_duplication_groups(result['duplication_groups'])
            format_refactoring_suggestions(result['refactoring_suggestions'])

            # Print message
            if result.get('message'):
                print(f"\n{result['message']}")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if not args.json:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
