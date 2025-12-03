#!/usr/bin/env python3
"""Fix misplaced console imports."""

from pathlib import Path


def fix_file(file_path: Path) -> bool:
    """Fix misplaced imports in a file.

    Args:
        file_path: Path to file

    Returns:
        True if file was modified
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Find all misplaced imports (not at module level)
    lines = content.split('\n')

    # Remove all console imports first
    filtered_lines = [l for l in lines if console_import not in l]

    # Find correct insertion point (after module docstring and other imports)
    insert_idx = 0

    # Skip shebang
    if filtered_lines and filtered_lines[0].startswith('#!'):
        insert_idx = 1

    # Skip module docstring
    in_docstring = False
    for i in range(insert_idx, min(insert_idx + 50, len(filtered_lines))):
        line = filtered_lines[i].strip()

        if line.startswith('"""') or line.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                quote = '"""' if '"""' in line else "'''"
                if line.count(quote) >= 2:  # Closes on same line
                    insert_idx = i + 1
                    in_docstring = False
            else:
                insert_idx = i + 1
                in_docstring = False
                break
        elif in_docstring:
            continue
        elif line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line and not line.startswith('#'):
            # Hit actual code
            break

    # Insert import at correct location
    if insert_idx < len(filtered_lines) and not filtered_lines[insert_idx].strip():
        # Already has blank line
        filtered_lines.insert(insert_idx, console_import)
    else:
        filtered_lines.insert(insert_idx, console_import)
        filtered_lines.insert(insert_idx + 1, '')

    new_content = '\n'.join(filtered_lines)

    if new_content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True

    return False


def main():
    project_root = Path(__file__).parent.parent

    # Fix all files
    fixed_count = 0
    for dir_path in [project_root / 'scripts', project_root / 'tests', project_root]:
        if dir_path == project_root:
            pattern = '*.py'
        else:
            pattern = '**/*.py'

        for file_path in dir_path.glob(pattern):
            if file_path.is_file() and '__pycache__' not in str(file_path):
                if fix_file(file_path):
                    fixed_count += 1
                    print(f"Fixed: {file_path.name}")

    print(f"\nFixed {fixed_count} files")


if __name__ == '__main__':
    main()
