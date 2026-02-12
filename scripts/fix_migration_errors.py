#!/usr/bin/env python3
"""Fix syntax errors from migration script."""

import re
from pathlib import Path

from ast_grep_mcp.utils.console_logger import console


def fix_file(filepath: Path) -> bool:
    """Fix orphaned import statement closing in a file."""

    with open(filepath, "r") as f:
        lines = f.readlines()

    fixed = False
    new_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        # Check for orphaned closing parenthesis pattern after import statements
        if i < len(lines) - 1:
            next_line = lines[i + 1]
            # Pattern: valid import statement followed by orphaned items/closing paren
            if (
                line.strip().startswith("from ast_grep_mcp.")
                and "import" in line
                and next_line.strip()
                and (
                    next_line.strip()[0] in [",", ")"]
                    or (
                        not next_line.strip().startswith("from")
                        and not next_line.strip().startswith("import")
                        and not next_line.strip().startswith("#")
                        and not next_line.strip().startswith("class")
                        and not next_line.strip().startswith("def")
                        and not next_line.strip().startswith("@")
                        and not next_line.strip().startswith('"""')
                        and not next_line.strip().startswith("'''")
                        and not next_line.startswith(" " * 0)  # Not top-level
                        and re.match(r"^\s+[a-zA-Z_]", next_line)
                    )
                )
            ):  # Indented identifier
                # Look ahead to find the closing paren
                j = i + 1
                while j < len(lines) and lines[j].strip() and lines[j].strip() != ")":
                    j += 1
                    if lines[j].strip().startswith(("from", "import", "class", "def", "@", "#")):
                        break

                # Skip the orphaned lines
                if j < len(lines) and lines[j].strip() == ")":
                    console.log(f"  Fixing {filepath.name}: Removing orphaned lines {i + 2} to {j + 1}")
                    new_lines.append(line)
                    # Skip to after the closing paren
                    for _k in range(i + 1, j + 1):
                        skip_next = False  # Will be handled by advancing i
                    i = j
                    fixed = True
                    continue

        new_lines.append(line)

    if fixed:
        with open(filepath, "w") as f:
            f.writelines(new_lines)

    return fixed


def main():
    """Fix all files with syntax errors."""
    test_files = [
        "tests/unit/test_duplication.py",
        "tests/unit/test_coverage_detection.py",
        "tests/unit/test_import_management.py",
        "tests/unit/test_parameter_extraction.py",
        "tests/unit/test_enhanced_suggestions.py",
        "tests/unit/test_function_generation.py",
        "tests/unit/test_standards_enforcement.py",
        "tests/unit/test_dependency_analysis.py",
        "tests/unit/test_linting_rules.py",
        "tests/unit/test_diff_preview.py",
        "tests/unit/test_complexity.py",
        "tests/unit/test_code_smells.py",
        "tests/unit/test_ast_diff.py",
        "tests/unit/test_variation_classification.py",
        "tests/unit/test_impact_analysis.py",
        "tests/unit/test_enhanced_reporting.py",
        "tests/unit/test_call_site.py",
    ]

    console.log("Fixing migration syntax errors...")
    fixed_count = 0

    for filepath in test_files:
        path = Path(filepath)
        if not path.exists():
            console.log(f"  Skipping {filepath} - not found")
            continue

        console.log(f"\nProcessing {filepath}")
        if fix_file(path):
            fixed_count += 1

    console.success(f"\n✓ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
