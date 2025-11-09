#!/usr/bin/env python3
"""
Analyze the tcad-scraper codebase using ast-grep
"""
import json
import subprocess
from typing import Optional

TCAD_PATH = "/Users/alyshialedlie/code/ISPublicSites/tcad-scraper"

def run_ast_grep(command: str, args: list, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run ast-grep command"""
    cmd = ["ast-grep", command] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        input=input_text,
        text=True
    )

def find_code(project_folder: str, pattern: str, language: str, max_results: int = 0) -> str:
    """Find code using pattern"""
    args = ["--pattern", pattern, "--lang", language, "--json", project_folder]
    result = run_ast_grep("run", args)

    if result.returncode != 0:
        return f"Error: {result.stderr}"

    matches = json.loads(result.stdout.strip() or "[]")
    total_matches = len(matches)

    if max_results and total_matches > max_results:
        matches = matches[:max_results]

    if not matches:
        return "No matches found"

    output_blocks = []
    for m in matches:
        file_path = m.get('file', '')
        start_line = m.get('range', {}).get('start', {}).get('line', 0) + 1
        end_line = m.get('range', {}).get('end', {}).get('line', 0) + 1
        match_text = m.get('text', '').rstrip()

        if start_line == end_line:
            header = f"{file_path}:{start_line}"
        else:
            header = f"{file_path}:{start_line}-{end_line}"

        output_blocks.append(f"{header}\n{match_text}")

    header = f"Found {len(matches)} matches"
    if max_results and total_matches > max_results:
        header += f" (showing first {max_results} of {total_matches})"

    return header + ":\n\n" + '\n\n'.join(output_blocks)

def find_code_by_rule(project_folder: str, yaml: str, max_results: int = 0) -> str:
    """Find code using YAML rule"""
    args = ["--inline-rules", yaml, "--json", project_folder]
    result = run_ast_grep("scan", args)

    if result.returncode != 0:
        return f"Error: {result.stderr}"

    matches = json.loads(result.stdout.strip() or "[]")
    total_matches = len(matches)

    if max_results and total_matches > max_results:
        matches = matches[:max_results]

    if not matches:
        return "No matches found"

    output_blocks = []
    for m in matches:
        file_path = m.get('file', '')
        start_line = m.get('range', {}).get('start', {}).get('line', 0) + 1
        end_line = m.get('range', {}).get('end', {}).get('line', 0) + 1
        match_text = m.get('text', '').rstrip()

        if start_line == end_line:
            header = f"{file_path}:{start_line}"
        else:
            header = f"{file_path}:{start_line}-{end_line}"

        output_blocks.append(f"{header}\n{match_text}")

    header = f"Found {len(matches)} matches"
    if max_results and total_matches > max_results:
        header += f" (showing first {max_results} of {total_matches})"

    return header + ":\n\n" + '\n\n'.join(output_blocks)

def analyze_console_logs():
    """Find all console.log statements"""
    print("\n=== Console.log statements ===")
    result = find_code(
        project_folder=TCAD_PATH,
        pattern="console.log($$$ARGS)",
        language="typescript",
        max_results=50
    )
    print(result)

def analyze_todo_comments():
    """Find all TODO/FIXME comments"""
    print("\n=== TODO/FIXME comments ===")
    # Search for TODO comments
    todo_rule = """
id: find-todos
language: typescript
rule:
  any:
    - pattern: "// TODO: $MSG"
    - pattern: "// FIXME: $MSG"
    - pattern: "/* TODO: $MSG */"
    - pattern: "/* FIXME: $MSG */"
"""
    result = find_code_by_rule(
        project_folder=TCAD_PATH,
        yaml=todo_rule,
        max_results=50
    )
    print(result)

def analyze_unused_vars():
    """Find potential unused variables (simplified check)"""
    print("\n=== Unused variable patterns ===")
    # This is a simplified check - ast-grep can't do full data flow analysis
    unused_rule = """
id: unused-vars
language: typescript
rule:
  pattern: "const $VAR = $$$"
  not:
    inside:
      any:
        - pattern: "export const $VAR = $$$"
        - pattern: "export { $$$, $VAR, $$$ }"
"""
    result = find_code_by_rule(
        project_folder=TCAD_PATH,
        yaml=unused_rule,
        max_results=20
    )
    print(result)

def analyze_error_handling():
    """Find try-catch blocks"""
    print("\n=== Error handling (try-catch blocks) ===")
    result = find_code(
        project_folder=TCAD_PATH,
        pattern="try { $$$ } catch ($E) { $$$ }",
        language="typescript",
        max_results=30
    )
    print(result)

def analyze_async_functions():
    """Find async functions"""
    print("\n=== Async functions ===")
    result = find_code(
        project_folder=TCAD_PATH,
        pattern="async function $NAME($$$) { $$$ }",
        language="typescript",
        max_results=20
    )
    print(result)

def analyze_test_files():
    """Find test patterns"""
    print("\n=== Test patterns (describe/it blocks) ===")
    test_rule = """
id: test-blocks
language: typescript
rule:
  any:
    - pattern: "describe($NAME, () => { $$$ })"
    - pattern: "it($NAME, () => { $$$ })"
    - pattern: "test($NAME, () => { $$$ })"
"""
    result = find_code_by_rule(
        project_folder=TCAD_PATH,
        yaml=test_rule,
        max_results=30
    )
    print(result)

def analyze_env_vars():
    """Find environment variable usage"""
    print("\n=== Environment variable usage ===")
    result = find_code(
        project_folder=TCAD_PATH,
        pattern="process.env.$VAR",
        language="typescript",
        max_results=30
    )
    print(result)

def analyze_deprecated_patterns():
    """Find deprecated or old patterns"""
    print("\n=== Deprecated patterns (var declarations) ===")
    result = find_code(
        project_folder=TCAD_PATH,
        pattern="var $VAR = $$$",
        language="typescript",
        max_results=20
    )
    print(result)

if __name__ == "__main__":
    print("=" * 80)
    print("TCAD-SCRAPER CODEBASE ANALYSIS")
    print("=" * 80)

    try:
        analyze_console_logs()
    except Exception as e:
        print(f"Error: {e}")

    try:
        analyze_todo_comments()
    except Exception as e:
        print(f"Error: {e}")

    try:
        analyze_error_handling()
    except Exception as e:
        print(f"Error: {e}")

    try:
        analyze_async_functions()
    except Exception as e:
        print(f"Error: {e}")

    try:
        analyze_test_files()
    except Exception as e:
        print(f"Error: {e}")

    try:
        analyze_env_vars()
    except Exception as e:
        print(f"Error: {e}")

    try:
        analyze_deprecated_patterns()
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
