#!/usr/bin/env python3
"""Smart console.blank() to console logger migration.

Intelligently converts console.blank() statements based on context:
- Error messages -> console.error()
- JSON output -> console.json()
- Separators -> console.separator()
- Empty lines -> console.blank()
- Regular output -> console.log()
"""
from ast_grep_mcp.utils.console_logger import console

import re
from pathlib import Path
from typing import List, Tuple


def smart_replace_print(line: str) -> Tuple[str, bool]:
    """Smart replacement of console.blank() with appropriate console method.

    Args:
        line: Line containing console.blank() statement

    Returns:
        Tuple of (replaced_line, was_modified)
    """
    original = line
    modified = False

    # Skip if already using console
    if 'console.' in line:
        return line, False

    # Pattern 1: print() with no arguments -> console.blank()
    if re.search(r'\bprint\(\s*\)', line):
        line = re.sub(r'\bprint\(\s*\)', 'console.blank()', line)
        modified = True

    # Pattern 2: Separator lines (=, -, *, _)
    elif re.search(r'print\(["\']([=\-_*])\1{5,}["\']\)', line):
        match = re.search(r'print\(["\']([=\-_*]+)["\']\)', line)
        if match:
            char = match.group(1)[0]
            length = len(match.group(1))
            line = re.sub(
                r'print\(["\']([=\-_*]+)["\']\)',
                f'console.separator("{char}", {length})',
                line
            )
            modified = True

    # Pattern 3: JSON output
    elif 'json.dumps' in line and 'print(' in line:
        # Extract json.dumps content
        match = re.search(r'print\(json\.dumps\((.*?)(,\s*indent=\d+)?\)\)', line)
        if match:
            data = match.group(1)
            line = re.sub(
                r'print\(json\.dumps\((.*?)(,\s*indent=\d+)?\)\)',
                rf'console.json(\1)',
                line
            )
            modified = True

    # Pattern 4: Error messages ( or "error" in text)
    elif '' in line:
        # Remove file=sys.stderr and use console.error
        content = re.sub(r',?\s*file=sys\.stderr', '', line)
        content = re.sub(r'\bprint\((.*)\)', r'console.error(\1)', content)
        line = content
        modified = True

    elif any(word in line.lower() for word in ['error:', 'failed', 'failure']):
        line = re.sub(r'\bprint\(', 'console.error(', line)
        modified = True

    # Pattern 5: Success/completion messages
    elif any(word in line.lower() for word in ['success', 'complete', 'done', '✓']):
        line = re.sub(r'\bprint\(', 'console.success(', line)
        modified = True

    # Pattern 6: Warning messages
    elif any(word in line.lower() for word in ['warning:', 'warn:']):
        line = re.sub(r'\bprint\(', 'console.warning(', line)
        modified = True

    # Pattern 7: Debug/verbose messages
    elif any(word in line.lower() for word in ['debug:', '[debug]']):
        line = re.sub(r'\bprint\(', 'console.debug(', line)
        modified = True

    # Pattern 8: Default to console.log()
    elif 'console.log(' in line:
        line = re.sub(r'\bprint\(', 'console.log(', line)
        modified = True

    return line, modified


def add_console_import(lines: List[str]) -> List[str]:
    """Add console import if not present.

    Args:
        lines: File lines

    Returns:
        Modified lines with import added
    """

    # Check if already imported
    for line in lines:
        if import_stmt in line:
            return lines

    # Find where to insert import
    insert_idx = 0

    # Skip shebang
    if lines and lines[0].startswith('#!'):
        insert_idx = 1

    # Skip module docstring
    in_docstring = False
    for i in range(insert_idx, min(insert_idx + 20, len(lines))):
        line = lines[i].strip()
        if line.startswith('"""') or line.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                # Check if docstring closes on same line
                quote = '"""' if '"""' in line else "'''"
                if line.count(quote) >= 2:
                    insert_idx = i + 1
                    in_docstring = False
            else:
                insert_idx = i + 1
                break
        elif in_docstring:
            continue
        elif line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1

    # Insert import and blank line
    lines.insert(insert_idx, import_stmt)
    if insert_idx < len(lines) and lines[insert_idx + 1].strip():
        lines.insert(insert_idx + 1, '')

    return lines


def migrate_file(file_path: Path, dry_run: bool = True) -> Tuple[int, List[str]]:
    """Migrate print statements in a file.

    Args:
        file_path: Path to file
        dry_run: If True, don't modify files

    Returns:
        Tuple of (migrations_count, changes_list)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified_lines = []
    changes = []
    migrations = 0

    for i, line in enumerate(lines, 1):
        new_line, was_modified = smart_replace_print(line)
        modified_lines.append(new_line)

        if was_modified:
            migrations += 1
            changes.append(f"Line {i}: {line.strip()} -> {new_line.strip()}")

    if migrations > 0:
        # Add import
        modified_lines_stripped = [l.rstrip('\n') for l in modified_lines]
        modified_lines_stripped = add_console_import(modified_lines_stripped)

        if not dry_run:
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(modified_lines_stripped))
                if modified_lines_stripped and not modified_lines_stripped[-1].endswith('\n'):
                    f.write('\n')

    return migrations, changes


def migrate_directory(dir_path: Path, pattern: str = '**/*.py', dry_run: bool = True):
    """Migrate all files in directory.

    Args:
        dir_path: Directory path
        pattern: Glob pattern
        dry_run: Preview mode
    """
    results = {
        'total_files': 0,
        'modified_files': 0,
        'total_migrations': 0,
        'files': {}
    }

    for file_path in sorted(dir_path.glob(pattern)):
        if file_path.is_file() and '__pycache__' not in str(file_path):
            results['total_files'] += 1
            migrations, changes = migrate_file(file_path, dry_run=dry_run)

            if migrations > 0:
                results['modified_files'] += 1
                results['total_migrations'] += migrations
                results['files'][str(file_path)] = {
                    'migrations': migrations,
                    'changes': changes[:10]  # First 10 changes
                }

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Smart console.blank() to console migration')
    parser.add_argument('--path', help='File or directory to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')
    parser.add_argument('--scripts', action='store_true', help='Migrate scripts/')
    parser.add_argument('--tests', action='store_true', help='Migrate tests/')
    parser.add_argument('--all', action='store_true', help='Migrate all')

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    if args.path:
        path = Path(args.path)
        if not path.is_absolute():
            path = project_root / path

        if path.is_file():
            migrations, changes = migrate_file(path, dry_run=args.dry_run)
            console.log(f"\n{'[DRY RUN] ' if args.dry_run else ''}Migrated {path.name}")
            console.log(f"Migrations: {migrations}")
            for change in changes[:15]:
                console.log(f"  {change}")
        else:
            results = migrate_directory(path, dry_run=args.dry_run)
            console.log(f"\n{'[DRY RUN] ' if args.dry_run else ''}Migration Results")
            console.log("=" * 70)
            console.log(f"Total files: {results['total_files']}")
            console.log(f"Modified files: {results['modified_files']}")
            console.log(f"Total migrations: {results['total_migrations']}")

    elif args.scripts:
        results = migrate_directory(project_root / 'scripts', dry_run=args.dry_run)
        console.log(f"\n{'[DRY RUN] ' if args.dry_run else ''}Scripts Migration")
        console.log("=" * 70)
        console.log(f"Files processed: {results['total_files']}")
        console.log(f"Files modified: {results['modified_files']}")
        console.log(f"Total migrations: {results['total_migrations']}")

        if results['files']:
            console.log("\nTop modified files:")
            for path, info in sorted(
                results['files'].items(),
                key=lambda x: x[1]['migrations'],
                reverse=True
            )[:5]:
                console.log(f"\n{Path(path).name}: {info['migrations']} migrations")
                for change in info['changes'][:3]:
                    console.log(f"  {change}")

    elif args.tests:
        results = migrate_directory(project_root / 'tests', dry_run=args.dry_run)
        console.log(f"\n{'[DRY RUN] ' if args.dry_run else ''}Tests Migration")
        console.log("=" * 70)
        console.log(f"Files processed: {results['total_files']}")
        console.log(f"Files modified: {results['modified_files']}")
        console.log(f"Total migrations: {results['total_migrations']}")

    elif args.all:
        console.log("\n" + "=" * 70)
        console.log("MIGRATING ALL FILES")
        console.log("=" * 70)

        # Scripts
        console.log("\n1. SCRIPTS")
        scripts_results = migrate_directory(project_root / 'scripts', dry_run=args.dry_run)
        console.log(f"   Migrated: {scripts_results['modified_files']}/{scripts_results['total_files']} files")
        console.log(f"   Changes: {scripts_results['total_migrations']}")

        # Tests
        console.log("\n2. TESTS")
        tests_results = migrate_directory(project_root / 'tests', dry_run=args.dry_run)
        console.log(f"   Migrated: {tests_results['modified_files']}/{tests_results['total_files']} files")
        console.log(f"   Changes: {tests_results['total_migrations']}")

        # Root level scripts
        console.log("\n3. ROOT SCRIPTS")
        root_results = migrate_directory(
            project_root,
            pattern='*.py',
            dry_run=args.dry_run
        )
        console.log(f"   Migrated: {root_results['modified_files']}/{root_results['total_files']} files")
        console.log(f"   Changes: {root_results['total_migrations']}")

        # Summary
        total_migrations = (
            scripts_results['total_migrations'] +
            tests_results['total_migrations'] +
            root_results['total_migrations']
        )
        console.log("\n" + "=" * 70)
        print(f"TOTAL: {total_migrations} console.blank() statements migrated")
        console.log("=" * 70)

        if args.dry_run:
            console.log("\n⚠ DRY RUN - No files were modified")
            console.log("Run without --dry-run to apply changes")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
