#!/usr/bin/env python3
"""Remove orphaned import lines from migration."""

import re
import subprocess
import sys
from pathlib import Path
from ast_grep_mcp.utils.console_logger import console


def find_orphaned_imports(lines):
    """Find lines that are orphaned from old import blocks."""

    orphaned_ranges = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Look for patterns that suggest orphaned imports:
        # 1. Lines that look like import items but aren't part of a from...import
        # 2. Closing parens with nothing before them
        # 3. Import names at wrong indentation

        if i > 0:
            prev_line = lines[i - 1].strip()

            # Pattern 1: Orphaned closing paren after complete import
            if line == ')' and prev_line.endswith(')'):
                orphaned_ranges.append((i, i + 1))
                i += 1
                continue

            # Pattern 2: Indented identifiers after complete import statement
            if (not line.startswith(('from', 'import', '#', '"""', "'''", 'class', 'def', '@')) and
                line and
                lines[i].startswith('    ') and  # Indented
                '(' not in line and
                '=' not in line and
                'def ' not in line and
                'class ' not in line and
                prev_line.endswith(')')):  # Previous line ended an import

                # This might be an orphaned import item
                # Look ahead to find the end
                start = i
                while i < len(lines):
                    curr = lines[i].strip()
                    if curr == ')':
                        orphaned_ranges.append((start, i + 1))
                        break
                    elif curr.startswith(('from', 'import', 'class', 'def', '@', '"""', "'''")):
                        # Hit next statement, end here
                        orphaned_ranges.append((start, i))
                        break
                    elif not curr or curr.startswith('#'):
                        # Empty line or comment, end here
                        orphaned_ranges.append((start, i))
                        break
                    i += 1
                continue

        i += 1

    return orphaned_ranges


def remove_orphaned_lines(filepath: Path):
    """Remove orphaned import lines from file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    orphaned = find_orphaned_imports(lines)

    if not orphaned:
        return False

    console.log(f"\n  Fixing {filepath.name}:")
    new_lines = []
    skip_until = -1

    for i, line in enumerate(lines):
        if i < skip_until:
            continue

        # Check if this line is in an orphaned range
        is_orphaned = False
        for start, end in orphaned:
            if start <= i < end:
                is_orphaned = True
                skip_until = end
                console.log(f"    Removing lines {start + 1}-{end}: {repr(lines[start].strip()[:50])}")
                break

        if not is_orphaned:
            new_lines.append(line)

    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    return True


def check_syntax(filepath: Path):
    """Check if file has valid Python syntax."""
    result = subprocess.run(
        [sys.executable, '-m', 'py_compile', str(filepath)],
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stderr


def main():
    """Fix all test files with orphaned imports."""
    error_files = [
        'tests/unit/test_duplication.py',
        'tests/unit/test_coverage_detection.py',
        'tests/unit/test_import_management.py',
        'tests/unit/test_parameter_extraction.py',
        'tests/unit/test_enhanced_suggestions.py',
        'tests/unit/test_function_generation.py',
        'tests/unit/test_standards_enforcement.py',
        'tests/unit/test_dependency_analysis.py',
        'tests/unit/test_linting_rules.py',
        'tests/unit/test_diff_preview.py',
        'tests/unit/test_complexity.py',
        'tests/unit/test_code_smells.py',
        'tests/unit/test_ast_diff.py',
        'tests/unit/test_variation_classification.py',
        'tests/unit/test_impact_analysis.py',
        'tests/unit/test_enhanced_reporting.py',
        'tests/unit/test_call_site.py',
    ]

    console.log("=" * 80)
    console.log("Fixing orphaned import lines from migration")
    console.log("=" * 80)

    fixed_count = 0
    failed = []

    for filepath_str in error_files:
        filepath = Path(filepath_str)
        if not filepath.exists():
            console.log(f"\n  Skipping {filepath} - not found")
            continue

        # Check syntax before
        valid_before, error_before = check_syntax(filepath)

        if valid_before:
            console.log(f"\n  Skipping {filepath.name} - already valid")
            continue

        # Try to fix
        if remove_orphaned_lines(filepath):
            # Check syntax after
            valid_after, error_after = check_syntax(filepath)

            if valid_after:
                console.success(f"    ✓ Fixed!")
                fixed_count += 1
            else:
                console.log(f"    ✗ Still has errors:")
                console.log(f"      {error_after.strip()}")
                failed.append(filepath_str)
        else:
            console.log(f"\n  No orphaned imports found in {filepath.name}")
            console.error(f"    Original error: {error_before.strip()}")
            failed.append(filepath_str)

    console.log("\n" + "=" * 80)
    console.log(f"Results: {fixed_count} files fixed")

    if failed:
        console.error(f"\n{len(failed)} files still have errors:")
        for f in failed:
            console.log(f"  - {f}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
