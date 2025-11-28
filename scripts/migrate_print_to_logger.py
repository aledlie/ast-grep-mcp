#!/usr/bin/env python3
"""Migrate console.blank() statements to console logger.

This script automatically migrates console.blank() statements to use the
console logger abstraction, providing better control and consistency.

Usage:
    # Dry run (preview changes)
    python scripts/migrate_print_to_logger.py --dry-run

    # Migrate specific directory
    python scripts/migrate_print_to_logger.py --path scripts/

    # Migrate all files
    python scripts/migrate_print_to_logger.py --all

    # Migrate with backup
    python scripts/migrate_print_to_logger.py --backup
"""
from ast_grep_mcp.utils.console_logger import console

import argparse
import ast
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class PrintStatement:
    """Represents a console.blank() statement to migrate."""

    file_path: str
    line_number: int
    column: int
    original_code: str
    suggested_replacement: str
    print_type: str  # 'simple', 'formatted', 'json', 'separator', 'error'


class PrintMigrator:
    """Migrates console.blank() statements to console logger calls."""

    def __init__(self, dry_run: bool = True, backup: bool = False):
        """Initialize migrator.

        Args:
            dry_run: If True, only preview changes without applying
            backup: If True, create backup before modifying files
        """
        self.dry_run = dry_run
        self.backup = backup

    def analyze_print_call(self, code: str) -> str:
        """Analyze console.blank() call and determine appropriate logger method.

        Args:
            code: The console.blank() statement code

        Returns:
            Type of print statement: 'simple', 'json', 'separator', 'error', etc.
        """
        # Check for JSON output
        if 'json.dumps' in code or 'asdict' in code:
            return 'json'

        # Check for separator lines
        if re.search(r'print\(["\']([=\-_*])\1+["\']\)', code):
            return 'separator'

        # Check for error output ( or 'error' in string)
        if '' in code or 'error' in code.lower():
            return 'error'

        # Check for formatted strings
        if code.startswith('console.log(f"') or code.startswith("console.log(f'"):
            return 'formatted'

        # Default to simple
        return 'simple'

    def migrate_print_statement(self, code: str, print_type: str) -> str:
        """Convert console.blank() statement to console logger call.

        Args:
            code: Original console.blank() statement
            print_type: Type of print statement

        Returns:
            Migrated code using console logger
        """
        # Extract the content between console.log( and )
        # Handle nested parentheses
        match = re.match(r'print\((.*)\)$', code.strip(), re.DOTALL)
        if not match:
            # Fallback: return original if we can't parse
            return code

        content = match.group(1)

        # Remove if present
        content = re.sub(r',?\s*file=sys\.stderr', '', content)

        # Handle different types
        if print_type == 'json':
            # Extract json.dumps(...) call
            if 'json.dumps' in content:
                # Replace json.dumps with console.json
                json_match = re.search(r'json\.dumps\((.*?)(,\s*indent=\d+)?\)', content)
                if json_match:
                    data = json_match.group(1)
                    return f'console.json({data})'
            return f'console.log({content})'

        elif print_type == 'separator':
            # Extract separator character and length
            sep_match = re.search(r'["\']([=\-_*])\1*["\']', content)
            if sep_match:
                char = sep_match.group(1)
                length = len(re.search(r'["\']([=\-_*]+)["\']', content).group(1))
                return f'console.separator("{char}", {length})'
            return f'console.log({content})'

        elif print_type == 'error':
            return f'console.error({content})'

        elif print_type == 'formatted':
            return f'console.log({content})'

        else:  # simple
            return f'console.log({content})'

    def find_print_statements(self, file_path: Path) -> List[PrintStatement]:
        """Find all console.blank() statements in a file.

        Args:
            file_path: Path to Python file

        Returns:
            List of PrintStatement objects
        """
        statements = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Use regex to find print statements (simple approach)
            for line_num, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue

                # Find console.log( statements
                for match in re.finditer(r'\bprint\s*\(', line):
                    # Extract full print statement (may span multiple lines)
                    start_col = match.start()
                    original_code = self._extract_print_call(lines, line_num - 1, start_col)

                    if original_code:
                        print_type = self.analyze_print_call(original_code)
                        replacement = self.migrate_print_statement(original_code, print_type)

                        statements.append(PrintStatement(
                            file_path=str(file_path),
                            line_number=line_num,
                            column=start_col,
                            original_code=original_code,
                            suggested_replacement=replacement,
                            print_type=print_type
                        ))

        except Exception as e:
            console.log(f"Error analyzing {file_path}: {e}")

        return statements

    def _extract_print_call(self, lines: List[str], start_line: int, start_col: int) -> str:
        """Extract complete console.blank() call that may span multiple lines.

        Args:
            lines: All lines in the file
            start_line: Line number where console.log( starts (0-indexed)
            start_col: Column where console.log( starts

        Returns:
            Complete console.blank() statement as string
        """
        # Simple extraction - find matching closing parenthesis
        line = lines[start_line][start_col:]
        depth = 0
        in_string = False
        string_char = None
        escaped = False
        result = []

        for i, char in enumerate(line):
            if escaped:
                escaped = False
                result.append(char)
                continue

            if char == '\\':
                escaped = True
                result.append(char)
                continue

            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                result.append(char)
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                result.append(char)
            elif char == '(' and not in_string:
                depth += 1
                result.append(char)
            elif char == ')' and not in_string:
                depth -= 1
                result.append(char)
                if depth == 0:
                    return ''.join(result)
            else:
                result.append(char)

        # If we didn't find closing paren on same line, it might span multiple lines
        # For simplicity, return what we have
        return ''.join(result) if result else None

    def migrate_file(self, file_path: Path) -> Tuple[int, List[str]]:
        """Migrate all console.blank() statements in a file.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (number of migrations, list of changes)
        """
        statements = self.find_print_statements(file_path)
        if not statements:
            return 0, []

        changes = []

        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # Create backup if requested
        if self.backup and not self.dry_run:
            backup_path = file_path.with_suffix('.py.bak')
            shutil.copy(file_path, backup_path)
            changes.append(f"Created backup: {backup_path}")

        # Check if file already has console import
        has_import = False
        import_line_index = -1

        for i, line in enumerate(lines):
                has_import = True
                break
            if line.startswith('import ') or line.startswith('from '):
                import_line_index = i

        # Replace print statements (in reverse order to maintain line numbers)
        for stmt in reversed(statements):
            line_idx = stmt.line_number - 1
            line = lines[line_idx]

            # Replace the print statement
            new_line = line.replace(stmt.original_code, stmt.suggested_replacement)
            lines[line_idx] = new_line

            changes.append(
                f"Line {stmt.line_number}: {stmt.original_code.strip()} -> "
                f"{stmt.suggested_replacement.strip()}"
            )

        # Add import if not present
        if not has_import:
            if import_line_index >= 0:
                # Add after last import
                lines.insert(import_line_index + 1, self.import_statement)
            else:
                # Add at top after docstring/shebang
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('#!'):
                        insert_idx = i + 1
                    elif line.strip().startswith('"""') or line.strip().startswith("'''"):
                        # Find end of docstring
                        quote = '"""' if '"""' in line else "'''"
                        if line.count(quote) >= 2:
                            insert_idx = i + 1
                            break
                        else:
                            for j in range(i + 1, len(lines)):
                                if quote in lines[j]:
                                    insert_idx = j + 1
                                    break
                        break

                lines.insert(insert_idx, self.import_statement)
                lines.insert(insert_idx + 1, '')  # Blank line

            changes.append(f"Added import: {self.import_statement}")

        # Write updated content
        if not self.dry_run:
            new_content = '\n'.join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        return len(statements), changes

    def migrate_directory(self, directory: Path, pattern: str = '**/*.py') -> Dict[str, any]:
        """Migrate all Python files in a directory.

        Args:
            directory: Directory to scan
            pattern: Glob pattern for files to process

        Returns:
            Dictionary with migration statistics
        """
        results = {
            'files_processed': 0,
            'files_modified': 0,
            'total_migrations': 0,
            'changes_by_file': {}
        }

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                results['files_processed'] += 1

                count, changes = self.migrate_file(file_path)

                if count > 0:
                    results['files_modified'] += 1
                    results['total_migrations'] += count
                    results['changes_by_file'][str(file_path)] = {
                        'migrations': count,
                        'changes': changes
                    }

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate console.blank() statements to console logger'
    )
    parser.add_argument(
        '--path',
        type=str,
        help='Path to file or directory to migrate'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Migrate all scripts and tests'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup files before modifying'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    migrator = PrintMigrator(dry_run=args.dry_run, backup=args.backup)

    # Determine what to migrate
    if args.path:
        path = Path(args.path)
        if not path.is_absolute():
            path = project_root / path
    elif args.all:
        path = project_root
    else:
        # Default: scripts and tests
        path = project_root

    # Run migration
    if path.is_file():
        count, changes = migrator.migrate_file(path)
        results = {
            'files_processed': 1,
            'files_modified': 1 if count > 0 else 0,
            'total_migrations': count,
            'changes_by_file': {str(path): {'migrations': count, 'changes': changes}}
        }
    else:
        results = migrator.migrate_directory(path)

    # Output results
    if args.json:
        console.json(results)
    else:
        mode = "DRY RUN - " if args.dry_run else ""
        console.log(f"\n{mode}Print Statement Migration Results")
        console.log("=" * 70)
        console.log(f"Files processed: {results['files_processed']}")
        console.log(f"Files modified: {results['files_modified']}")
        console.log(f"Total migrations: {results['total_migrations']}")

        if results['changes_by_file']:
            console.log("\nChanges by file:")
            for file_path, file_results in results['changes_by_file'].items():
                console.log(f"\n{Path(file_path).name}: {file_results['migrations']} migrations")
                for change in file_results['changes'][:5]:  # Show first 5
                    console.log(f"  - {change}")
                if len(file_results['changes']) > 5:
                    console.log(f"  ... and {len(file_results['changes']) - 5} more")

        if args.dry_run:
            console.log("\n⚠ This was a dry run. No files were modified.")
            console.log("Run without --dry-run to apply changes.")


if __name__ == '__main__':
    main()
