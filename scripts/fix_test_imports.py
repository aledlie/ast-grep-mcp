#!/usr/bin/env python3
"""
Automated script to fix test file imports after Phase 10 refactoring.

This script updates all test files to use the new modular import structure
instead of importing from main.py.

Usage:
    uv run python scripts/fix_test_imports.py [--dry-run] [--file TEST_FILE]

Examples:
    # Dry run (preview changes)
    uv run python scripts/fix_test_imports.py --dry-run

    # Fix all test files
    uv run python scripts/fix_test_imports.py

    # Fix specific file
    uv run python scripts/fix_test_imports.py --file tests/unit/test_alignment.py
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
import sys

# Import mapping: old import -> new import
IMPORT_MAPPINGS = {
    # Core Executor
    "run_ast_grep": "from ast_grep_mcp.core.executor import run_ast_grep",
    "run_command": "from ast_grep_mcp.core.executor import run_command",
    "stream_ast_grep_results": "from ast_grep_mcp.core.executor import stream_ast_grep_results",

    # Search/Find (service implementations)
    "find_code": "from ast_grep_mcp.features.search.service import find_code_impl as find_code",
    "find_code_by_rule": "from ast_grep_mcp.features.search.service import find_code_by_rule_impl as find_code_by_rule",
    "dump_syntax_tree": "from ast_grep_mcp.features.search.service import dump_syntax_tree_impl as dump_syntax_tree",

    # Formatters
    "format_matches_as_text": "from ast_grep_mcp.utils.formatters import format_matches_as_text",
    "format_diff_with_colors": "from ast_grep_mcp.utils.formatters import format_diff_with_colors",
    "format_python_code": "from ast_grep_mcp.utils.formatters import format_python_code",
    "format_typescript_code": "from ast_grep_mcp.utils.formatters import format_typescript_code",

    # Templates
    "PYTHON_FUNCTION_TEMPLATE": "from ast_grep_mcp.utils.templates import PYTHON_FUNCTION_TEMPLATE",
    "TYPESCRIPT_FUNCTION_TEMPLATE": "from ast_grep_mcp.utils.templates import TYPESCRIPT_FUNCTION_TEMPLATE",
    "format_python_function": "from ast_grep_mcp.utils.templates import format_python_function",

    # Data Models
    "AlignmentResult": "from ast_grep_mcp.models.deduplication import AlignmentResult",
    "AlignmentSegment": "from ast_grep_mcp.models.deduplication import AlignmentSegment",
    "DiffTree": "from ast_grep_mcp.models.deduplication import DiffTree",
    "DiffTreeNode": "from ast_grep_mcp.models.deduplication import DiffTreeNode",
    "VariationCategory": "from ast_grep_mcp.models.deduplication import VariationCategory",
    "FunctionTemplate": "from ast_grep_mcp.models.deduplication import FunctionTemplate",
    "ParameterInfo": "from ast_grep_mcp.models.deduplication import ParameterInfo",
    "FileDiff": "from ast_grep_mcp.models.deduplication import FileDiff",
    "DiffPreview": "from ast_grep_mcp.models.deduplication import DiffPreview",

    # Configuration & Exceptions
    "ConfigurationError": "from ast_grep_mcp.core.exceptions import ConfigurationError",
    "InvalidYAMLError": "from ast_grep_mcp.core.exceptions import InvalidYAMLError",
    "CustomLanguageConfig": "from ast_grep_mcp.models.config import CustomLanguageConfig",

    # Cache
    "QueryCache": "from ast_grep_mcp.core.cache import QueryCache",

    # Complexity
    "calculate_cyclomatic_complexity": "from ast_grep_mcp.features.complexity.analyzer import calculate_cyclomatic_complexity",
    "calculate_cognitive_complexity": "from ast_grep_mcp.features.complexity.analyzer import calculate_cognitive_complexity",
    "analyze_file_complexity": "from ast_grep_mcp.features.complexity.analyzer import analyze_file_complexity",
    "ComplexityMetrics": "from ast_grep_mcp.features.complexity.metrics import ComplexityMetrics",

    # Code Quality
    "create_linting_rule": "from ast_grep_mcp.features.quality.rules import create_linting_rule",
    "RULE_TEMPLATES": "from ast_grep_mcp.features.quality.rules import RULE_TEMPLATES",

    # Code Smells (private functions)
    "_count_function_parameters": "from ast_grep_mcp.features.quality.smells import _count_function_parameters",
    "_find_magic_numbers": "from ast_grep_mcp.features.quality.smells import _find_magic_numbers",
    "_extract_classes_from_file": "from ast_grep_mcp.features.quality.smells import _extract_classes_from_file",

    # Schema.org
    "SchemaOrgClient": "from ast_grep_mcp.features.schema.client import SchemaOrgClient",
    "get_schema_org_client": "from ast_grep_mcp.features.schema.client import get_schema_org_client",

    # Deduplication - Coverage
    "has_test_coverage": "from ast_grep_mcp.features.deduplication.coverage import has_test_coverage",
    "get_test_coverage_for_files": "from ast_grep_mcp.features.deduplication.coverage import get_test_coverage_for_files",
    "find_test_file_patterns": "from ast_grep_mcp.features.deduplication.coverage import find_test_file_patterns",

    # Deduplication - Impact
    "analyze_deduplication_impact": "from ast_grep_mcp.features.deduplication.impact import analyze_deduplication_impact",

    # Deduplication - Reporting
    "create_enhanced_duplication_response": "from ast_grep_mcp.features.deduplication.reporting import create_enhanced_duplication_response",
    "generate_before_after_example": "from ast_grep_mcp.features.deduplication.reporting import generate_before_after_example",
    "visualize_complexity": "from ast_grep_mcp.features.deduplication.reporting import visualize_complexity",
}

# Functions that became class methods (need special handling)
CLASS_BASED_IMPORTS = {
    # DuplicationDetector
    "group_duplicates": ("ast_grep_mcp.features.deduplication.detector", "DuplicationDetector"),

    # PatternAnalyzer
    "classify_variation": ("ast_grep_mcp.features.deduplication.analyzer", "PatternAnalyzer"),
    "align_code_blocks": ("ast_grep_mcp.features.deduplication.analyzer", "PatternAnalyzer"),
    "analyze_duplicate_variations": ("ast_grep_mcp.features.deduplication.analyzer", "PatternAnalyzer"),
    "identify_varying_literals": ("ast_grep_mcp.features.deduplication.analyzer", "PatternAnalyzer"),

    # CodeGenerator
    "extract_function_template": ("ast_grep_mcp.features.deduplication.generator", "CodeGenerator"),
    "generate_parameterized_function": ("ast_grep_mcp.features.deduplication.generator", "CodeGenerator"),
    "render_python_function": ("ast_grep_mcp.features.deduplication.generator", "CodeGenerator"),
    "generate_replacement_call": ("ast_grep_mcp.features.deduplication.generator", "CodeGenerator"),
    "detect_import_insertion_point": ("ast_grep_mcp.features.deduplication.generator", "CodeGenerator"),
    "detect_return_value": ("ast_grep_mcp.features.deduplication.generator", "CodeGenerator"),

    # DuplicationRanker
    "calculate_deduplication_score": ("ast_grep_mcp.features.deduplication.ranker", "DuplicationRanker"),
    "rank_deduplication_candidates": ("ast_grep_mcp.features.deduplication.ranker", "DuplicationRanker"),
    "calculate_refactoring_complexity": ("ast_grep_mcp.features.deduplication.ranker", "DuplicationRanker"),

    # RecommendationEngine
    "generate_deduplication_recommendation": ("ast_grep_mcp.features.deduplication.recommendations", "RecommendationEngine"),
}


def parse_imports_from_main(content: str) -> Tuple[Set[str], List[Tuple[int, str]]]:
    """
    Parse all imports from main.py in the file.

    Returns:
        Tuple of (set of imported names, list of (line_number, full_line))
    """
    imported_names = set()
    import_lines = []

    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Match: from main import ...
        match = re.match(r'^from main import (.+)$', line.strip())
        if match:
            imports_str = match.group(1)
            # Handle parenthesized imports
            if '(' in imports_str:
                # Multi-line import, need to find closing paren
                full_import = imports_str
                j = i + 1
                while ')' not in full_import and j < len(lines):
                    full_import += ' ' + lines[j].strip()
                    j += 1
                imports_str = full_import

            # Extract import names
            imports_str = imports_str.replace('(', '').replace(')', '').strip()
            for name in imports_str.split(','):
                name = name.strip()
                if name:
                    imported_names.add(name)

            import_lines.append((i, line))

    return imported_names, import_lines


def generate_new_imports(imported_names: Set[str]) -> Tuple[List[str], List[str], Dict[str, str], Set[str]]:
    """
    Generate new import statements for the given names.

    Returns:
        Tuple of:
        - List of new import lines (simple imports)
        - List of class imports needed
        - Dict of function name -> fixture name (for class methods)
        - Set of unmapped names (remain in main.py)
    """
    new_imports = []
    class_imports = set()
    fixture_mappings = {}
    unmapped = set()

    # Group imports by module
    import_groups: Dict[str, List[str]] = {}

    for name in imported_names:
        if name in IMPORT_MAPPINGS:
            # Simple import mapping
            import_line = IMPORT_MAPPINGS[name]
            module = import_line.split(' import ')[0].replace('from ', '')
            if module not in import_groups:
                import_groups[module] = []
            import_item = import_line.split(' import ')[1]
            import_groups[module].append(import_item)

        elif name in CLASS_BASED_IMPORTS:
            # Class-based import (needs fixture)
            module, class_name = CLASS_BASED_IMPORTS[name]
            class_imports.add(f"from {module} import {class_name}")

            # Generate fixture name
            fixture_name = ''.join(['_' + c.lower() if c.isupper() else c for c in class_name]).lstrip('_')
            fixture_mappings[name] = fixture_name

        else:
            # Not yet migrated, remains in main.py
            unmapped.add(name)

    # Generate grouped import statements
    for module, items in sorted(import_groups.items()):
        # Remove duplicates and sort
        unique_items = sorted(set(items))
        if len(unique_items) == 1:
            new_imports.append(f"from {module} import {unique_items[0]}")
        else:
            new_imports.append(f"from {module} import (")
            for item in unique_items:
                new_imports.append(f"    {item},")
            new_imports.append(")")

    # Add import for unmapped items (still in main.py)
    if unmapped:
        sorted_unmapped = sorted(unmapped)
        if len(sorted_unmapped) == 1:
            new_imports.append(f"from main import {sorted_unmapped[0]}")
        else:
            new_imports.append("from main import (")
            for item in sorted_unmapped:
                new_imports.append(f"    {item},")
            new_imports.append(")")

    return new_imports, sorted(class_imports), fixture_mappings, unmapped


def update_function_calls(content: str, fixture_mappings: Dict[str, str]) -> str:
    """
    Update function calls to use fixture instances for class methods.

    For functions that became class methods, replace:
        result = function_name(args)
    with:
        result = fixture_name.function_name(args)
    """
    if not fixture_mappings:
        return content

    lines = content.split('\n')
    updated_lines = []

    for line in lines:
        updated_line = line
        for func_name, fixture_name in fixture_mappings.items():
            # Match function calls: function_name(
            # But not: self.function_name( or fixture.function_name(
            pattern = r'\b' + re.escape(func_name) + r'\('
            if re.search(pattern, line) and not re.search(r'(self\.|[a-z_]+\.)' + re.escape(func_name) + r'\(', line):
                updated_line = re.sub(
                    r'\b' + re.escape(func_name) + r'\(',
                    f'{fixture_name}.{func_name}(',
                    updated_line
                )
        updated_lines.append(updated_line)

    return '\n'.join(updated_lines)


def add_fixtures_to_test_functions(content: str, fixture_mappings: Dict[str, str]) -> str:
    """
    Add fixture parameters to test functions that use class methods.

    Updates function signatures like:
        def test_something():
    to:
        def test_something(duplication_detector, pattern_analyzer):
    """
    if not fixture_mappings:
        return content

    # Get unique fixture names used in this file
    used_fixtures = set(fixture_mappings.values())

    lines = content.split('\n')
    updated_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Match test function definition
        test_match = re.match(r'^(\s*)def (test_\w+)\(([^)]*)\):', line)
        if test_match:
            indent, func_name, current_params = test_match.groups()

            # Check if this test uses any of the fixtures
            # Look ahead in the function body to see if fixtures are used
            test_body_start = i + 1
            test_body = []
            j = test_body_start
            while j < len(lines):
                next_line = lines[j]
                # Stop at next function definition or class definition
                if re.match(r'^(def |class )', next_line):
                    break
                test_body.append(next_line)
                j += 1

            test_body_str = '\n'.join(test_body)

            # Check which fixtures are used in this test
            needed_fixtures = []
            for fixture in sorted(used_fixtures):
                if f'{fixture}.' in test_body_str:
                    needed_fixtures.append(fixture)

            if needed_fixtures:
                # Add fixtures to parameters
                if current_params.strip():
                    # Has existing params
                    new_params = f"{current_params.strip()}, {', '.join(needed_fixtures)}"
                else:
                    # No existing params
                    new_params = ', '.join(needed_fixtures)

                updated_line = f"{indent}def {func_name}({new_params}):"
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

        i += 1

    return '\n'.join(updated_lines)


def fix_test_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Fix imports in a single test file.

    Returns:
        Tuple of (success, message)
    """
    try:
        content = file_path.read_text()

        # Parse current imports from main
        imported_names, import_lines = parse_imports_from_main(content)

        if not imported_names:
            return True, "No imports from main.py found"

        # Generate new imports
        new_imports, class_imports, fixture_mappings, unmapped = generate_new_imports(imported_names)

        if not new_imports and not class_imports:
            return False, f"All imports unmapped: {', '.join(sorted(imported_names))}"

        # Remove old import lines
        lines = content.split('\n')
        lines_to_remove = set(line_num for line_num, _ in import_lines)

        # Find insertion point (after other imports)
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_index = i + 1

        # Build new content
        new_lines = []
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                new_lines.append(line)
            elif i == min(lines_to_remove):
                # Insert new imports at first removed line
                new_lines.extend(new_imports)
                if class_imports:
                    new_lines.append("")
                    new_lines.extend(class_imports)

        new_content = '\n'.join(new_lines)

        # Update function calls for class methods
        if fixture_mappings:
            new_content = update_function_calls(new_content, fixture_mappings)
            new_content = add_fixtures_to_test_functions(new_content, fixture_mappings)

        if dry_run:
            print(f"\n{'='*80}")
            print(f"File: {file_path}")
            print(f"{'='*80}")
            print(f"Imported from main: {', '.join(sorted(imported_names))}")
            print(f"\nNew imports:")
            for imp in new_imports:
                print(f"  {imp}")
            if class_imports:
                print(f"\nClass imports (need fixtures):")
                for imp in class_imports:
                    print(f"  {imp}")
            if fixture_mappings:
                print(f"\nFixture mappings:")
                for func, fixture in sorted(fixture_mappings.items()):
                    print(f"  {func}() -> {fixture}.{func}()")
            if unmapped:
                print(f"\n⚠️  Unmapped (still in main.py): {', '.join(sorted(unmapped))}")
            return True, "Dry run - no changes made"

        # Write updated content
        file_path.write_text(new_content)

        msg_parts = [f"Fixed {len(imported_names)} imports"]
        if fixture_mappings:
            msg_parts.append(f"{len(fixture_mappings)} class methods")
        if unmapped:
            msg_parts.append(f"⚠️ {len(unmapped)} unmapped")
        return True, ", ".join(msg_parts)

    except Exception as e:
        return False, f"Error: {e}"


def update_conftest(dry_run: bool = False) -> Tuple[bool, str]:
    """
    Add fixture definitions to tests/conftest.py if they don't exist.
    """
    conftest_path = Path("tests/conftest.py")

    fixture_code = '''
# Fixtures for class-based deduplication components
@pytest.fixture
def duplication_detector():
    """Provide DuplicationDetector instance."""
    from ast_grep_mcp.features.deduplication.detector import DuplicationDetector
    from ast_grep_mcp.core.executor import run_ast_grep
    return DuplicationDetector(run_ast_grep)


@pytest.fixture
def pattern_analyzer():
    """Provide PatternAnalyzer instance."""
    from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
    from ast_grep_mcp.core.executor import run_ast_grep
    return PatternAnalyzer(run_ast_grep)


@pytest.fixture
def code_generator():
    """Provide CodeGenerator instance."""
    from ast_grep_mcp.features.deduplication.generator import CodeGenerator
    return CodeGenerator()


@pytest.fixture
def duplication_ranker():
    """Provide DuplicationRanker instance."""
    from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker
    return DuplicationRanker()


@pytest.fixture
def recommendation_engine():
    """Provide RecommendationEngine instance."""
    from ast_grep_mcp.features.deduplication.recommendations import RecommendationEngine
    return RecommendationEngine()
'''

    try:
        if not conftest_path.exists():
            if dry_run:
                print(f"\nWould create {conftest_path} with fixtures")
                return True, "Dry run - would create conftest.py"

            conftest_path.write_text(f"import pytest\n{fixture_code}")
            return True, "Created conftest.py with fixtures"

        content = conftest_path.read_text()

        # Check if fixtures already exist
        if "def duplication_detector" in content:
            return True, "Fixtures already exist in conftest.py"

        if dry_run:
            print(f"\nWould add fixtures to {conftest_path}")
            return True, "Dry run - would add fixtures"

        # Append fixtures
        content += "\n" + fixture_code
        conftest_path.write_text(content)

        return True, "Added fixtures to conftest.py"

    except Exception as e:
        return False, f"Error updating conftest.py: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Fix test file imports after Phase 10 refactoring"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Fix specific test file instead of all files"
    )
    parser.add_argument(
        "--skip-conftest",
        action="store_true",
        help="Skip updating conftest.py"
    )

    args = parser.parse_args()

    # Determine which files to process
    if args.file:
        test_files = [args.file]
    else:
        test_files = sorted(Path("tests/unit").glob("test_*.py"))

    print(f"{'='*80}")
    print(f"Test Import Fixer - Phase 11A")
    print(f"{'='*80}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY CHANGES'}")
    print(f"Files to process: {len(test_files)}")
    print()

    # Update conftest.py first
    if not args.skip_conftest:
        success, message = update_conftest(args.dry_run)
        status = "✓" if success else "✗"
        print(f"{status} conftest.py: {message}")
        print()

    # Process test files
    results = []
    for file_path in test_files:
        success, message = fix_test_file(file_path, args.dry_run)
        results.append((file_path, success, message))

        status = "✓" if success else "✗"
        print(f"{status} {file_path.name}: {message}")

    # Summary
    print()
    print(f"{'='*80}")
    print("Summary")
    print(f"{'='*80}")

    successful = sum(1 for _, success, _ in results if success)
    failed = len(results) - successful

    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed files:")
        for file_path, success, message in results:
            if not success:
                print(f"  - {file_path.name}: {message}")

    if args.dry_run:
        print("\n⚠️  This was a dry run. Use without --dry-run to apply changes.")
        return 0

    if failed == 0:
        print("\n✓ All imports fixed successfully!")
        print("\nNext steps:")
        print("  1. Run tests: uv run pytest tests/unit/ -v")
        print("  2. Check for any remaining issues")
        print("  3. Commit changes: git add tests/ && git commit -m 'fix: update test imports (Phase 11A)'")
        return 0
    else:
        print("\n✗ Some files failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
