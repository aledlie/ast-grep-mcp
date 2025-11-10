#!/usr/bin/env python3
"""Update tests to use stream_ast_grep_results instead of run_ast_grep for find_code functions"""

import re

def update_test_file():
    with open('tests/test_unit.py', 'r') as f:
        content = f.read()

    # Define the classes that need updating
    classes_to_update = [
        'TestFindCode',
        'TestFindCodeByRule',
        'TestFindCodeEdgeCases',
        'TestFindCodeByRuleEdgeCases'
    ]

    # Track if we're inside a class that needs updating
    lines = content.split('\n')
    new_lines = []
    current_class = None

    for i, line in enumerate(lines):
        # Check if we're entering a class
        class_match = re.match(r'^class (\w+):', line)
        if class_match:
            current_class = class_match.group(1)

        # Check if we're leaving a class (new class or end of file)
        if line and not line.startswith(' ') and not line.startswith('\t') and current_class:
            if not line.startswith('class'):
                current_class = None

        # Update lines in classes that need it
        if current_class in classes_to_update:
            # Replace @patch decorator
            line = line.replace('@patch("main.run_ast_grep")', '@patch("main.stream_ast_grep_results")')

            # Replace mock_run with mock_stream in function signatures
            line = re.sub(r'def test_\w+\(self, mock_run\)', lambda m: m.group(0).replace('mock_run', 'mock_stream'), line)

            # Replace mock_run.return_value = mock_result with iterator pattern
            if 'mock_run.return_value = mock_result' in line:
                indent = line[:len(line) - len(line.lstrip())]
                # We need to look ahead to see if there's a mock_matches variable
                # For now, just mark it for manual review
                pass

            # Replace mock_result.stdout with direct mock_matches
            if 'mock_result = Mock()' in line:
                # Skip this line - we'll use mock_matches directly
                continue

            # Replace setting stdout
            if 'mock_result.stdout = ' in line and 'json.dumps' in line:
                # Extract the mock_matches part
                match = re.search(r'mock_result\.stdout = json\.dumps\((\[.*?\])\)', line)
                if match:
                    # This is tricky, skip for now
                    pass

        new_lines.append(line)

    # Simpler approach: use sed-like replacements for specific patterns
    result = '\n'.join(new_lines)

    # Now do targeted replacements
    # For find_code and find_code_by_rule tests specifically
    result = re.sub(
        r'(@patch\("main\.run_ast_grep"\))\s+def (test_\w+)\(self, mock_run\):',
        r'@patch("main.stream_ast_grep_results")\n    def \2(self, mock_stream):',
        result
    )

    with open('tests/test_unit.py', 'w') as f:
        f.write(result)

    print("Updated test file - manual review needed for mock_result patterns")

if __name__ == '__main__':
    update_test_file()
