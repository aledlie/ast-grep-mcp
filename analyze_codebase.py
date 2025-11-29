#!/usr/bin/env python3
"""
Comprehensive codebase analysis using all MCP tools.
This script analyzes the ast-grep-mcp codebase for:
- Code complexity issues
- Code smells
- Duplication opportunities
- Security vulnerabilities
- Code quality standards
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ast_grep_mcp.features.complexity.analyzer import analyze_file_complexity
from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool, detect_code_smells_tool
from ast_grep_mcp.features.quality.security_scanner import detect_security_issues_impl
from ast_grep_mcp.features.quality.tools import generate_quality_report_tool
from ast_grep_mcp.features.deduplication.tools import find_duplication_tool, analyze_deduplication_candidates_tool


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print('='*80)


def analyze_individual_files():
    """Analyze the top 5 most complex files individually."""
    print_section("PHASE 1: Individual File Complexity Analysis")

    files = [
        'src/ast_grep_mcp/features/deduplication/applicator.py',
        'src/ast_grep_mcp/features/complexity/tools.py',
        'src/ast_grep_mcp/features/quality/smells.py',
        'src/ast_grep_mcp/features/deduplication/metrics.py',
        'src/ast_grep_mcp/features/schema/client.py'
    ]

    for file_path in files:
        print(f"\n--- {file_path} ---")
        try:
            result = analyze_file_complexity(file_path, 'python')
            if result.get('success'):
                functions = result.get('functions', [])
                critical = [f for f in functions if
                           f.get('cyclomatic', 0) > 20 or
                           f.get('cognitive', 0) > 30]

                print(f"Total functions: {len(functions)}")
                print(f"Critical functions: {len(critical)}")

                if critical:
                    print("\nWorst offenders:")
                    for func in sorted(critical, key=lambda x: x.get('cognitive', 0), reverse=True)[:3]:
                        print(f"  • {func['name']} (line {func['start_line']})")
                        print(f"    Cyclomatic: {func['cyclomatic']}, Cognitive: {func['cognitive']}, "
                              f"Nesting: {func['nesting_depth']}, Lines: {func['length']}")
            else:
                print(f"  Error: {result.get('error')}")
        except Exception as e:
            print(f"  Exception: {e}")


def analyze_project_complexity():
    """Run project-wide complexity analysis."""
    print_section("PHASE 2: Project-Wide Complexity Analysis")

    try:
        result = analyze_complexity_tool(
            project_folder='src/ast_grep_mcp',
            language='python',
            include_patterns=['**/*.py'],
            exclude_patterns=['**/__pycache__/**', '**/test_*.py', '**/*_test.py'],
            cyclomatic_threshold=20,
            cognitive_threshold=30,
            nesting_threshold=6,
            length_threshold=150,
            store_results=False,
            include_trends=False,
            max_threads=4
        )

        if result.get('success'):
            summary = result.get('summary', {})
            print(f"\nTotal functions analyzed: {summary.get('total_functions', 0)}")
            print(f"Functions exceeding thresholds: {summary.get('exceeding_thresholds', 0)}")
            print(f"Percentage over threshold: {summary.get('percentage_exceeding', 0):.1f}%")
            print(f"\nAverage cyclomatic complexity: {summary.get('average_cyclomatic', 0):.2f}")
            print(f"Average cognitive complexity: {summary.get('average_cognitive', 0):.2f}")
            print(f"Average nesting depth: {summary.get('average_nesting', 0):.2f}")
            print(f"Average function length: {summary.get('average_length', 0):.1f} lines")

            # Show top 10 most complex functions
            exceeding = result.get('exceeding_functions', [])
            if exceeding:
                print(f"\nTop 10 most complex functions by cognitive complexity:")
                for i, func in enumerate(sorted(exceeding,
                                                key=lambda x: x.get('cognitive', 0),
                                                reverse=True)[:10], 1):
                    print(f"  {i}. {func['file']}:{func['name']} (line {func['start_line']})")
                    print(f"     Cyclomatic: {func['cyclomatic']}, Cognitive: {func['cognitive']}, "
                          f"Nesting: {func['nesting_depth']}, Lines: {func['length']}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during project complexity analysis: {e}")
        import traceback
        traceback.print_exc()


def detect_code_smells():
    """Run code smell detection."""
    print_section("PHASE 3: Code Smell Detection")

    try:
        result = detect_code_smells_tool(
            project_folder='src/ast_grep_mcp',
            language='python',
            include_patterns=['**/*.py'],
            exclude_patterns=['**/__pycache__/**', '**/test_*.py'],
            max_threads=4
        )

        if result.get('success'):
            summary = result.get('summary', {})
            print(f"\nTotal files analyzed: {summary.get('total_files', 0)}")
            print(f"Files with smells: {summary.get('files_with_smells', 0)}")
            print(f"Total smells found: {summary.get('total_smells', 0)}")

            by_severity = summary.get('by_severity', {})
            print(f"\nBy severity:")
            print(f"  High: {by_severity.get('high', 0)}")
            print(f"  Medium: {by_severity.get('medium', 0)}")
            print(f"  Low: {by_severity.get('low', 0)}")

            smells = result.get('smells', [])
            if smells:
                print(f"\nTop 10 code smells:")
                for smell in smells[:10]:
                    print(f"  • [{smell.get('severity', 'unknown').upper()}] {smell.get('type', 'unknown')}")
                    print(f"    File: {smell.get('file', 'unknown')}:{smell.get('line', '?')}")
                    print(f"    {smell.get('message', 'No message')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during code smell detection: {e}")
        import traceback
        traceback.print_exc()


def detect_security_issues():
    """Run security vulnerability scanning."""
    print_section("PHASE 4: Security Vulnerability Scanning")

    try:
        result = detect_security_issues_impl(
            project_folder='src/ast_grep_mcp',
            language='python',
            include_patterns=['**/*.py'],
            exclude_patterns=['**/__pycache__/**', '**/test_*.py'],
            max_threads=4
        )

        if result.get('success'):
            summary = result.get('summary', {})
            print(f"\nTotal files scanned: {summary.get('total_files', 0)}")
            print(f"Total issues found: {summary.get('total_issues', 0)}")

            by_severity = summary.get('by_severity', {})
            print(f"\nBy severity:")
            print(f"  Critical: {by_severity.get('critical', 0)}")
            print(f"  High: {by_severity.get('high', 0)}")
            print(f"  Medium: {by_severity.get('medium', 0)}")
            print(f"  Low: {by_severity.get('low', 0)}")

            by_category = summary.get('by_category', {})
            if by_category:
                print(f"\nBy category:")
                for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {category}: {count}")

            issues = result.get('issues', [])
            if issues:
                print(f"\nTop 10 security issues:")
                for issue in issues[:10]:
                    print(f"  • [{issue.get('severity', 'unknown').upper()}] {issue.get('category', 'unknown')}")
                    print(f"    File: {issue.get('file', 'unknown')}:{issue.get('line', '?')}")
                    print(f"    {issue.get('message', 'No message')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during security scanning: {e}")
        import traceback
        traceback.print_exc()


def analyze_duplication():
    """Analyze code duplication opportunities."""
    print_section("PHASE 5: Code Duplication Analysis")

    try:
        # First find duplicates
        find_result = find_duplication_tool(
            project_folder='src/ast_grep_mcp',
            language='python',
            min_similarity=0.8,
            min_lines=10,
            include_patterns=['**/*.py'],
            exclude_patterns=['**/__pycache__/**', '**/test_*.py'],
            max_threads=4
        )

        if not find_result.get('success'):
            print(f"Error finding duplicates: {find_result.get('error')}")
            return

        # Then analyze the candidates
        groups = find_result.get('groups', [])
        if not groups:
            print("\nNo duplication groups found.")
            return

        result = analyze_deduplication_candidates_tool(
            groups=groups,
            language='python',
            max_threads=4
        )

        if result.get('success'):
            summary = result.get('summary', {})
            print(f"\nTotal files analyzed: {summary.get('total_files', 0)}")
            print(f"Duplication groups found: {summary.get('total_groups', 0)}")
            print(f"Total duplicated instances: {summary.get('total_instances', 0)}")

            if summary.get('total_groups', 0) > 0:
                print(f"Average group size: {summary.get('average_group_size', 0):.1f} instances")
                print(f"Average similarity: {summary.get('average_similarity', 0):.1%}")
                print(f"Estimated LOC savings: {summary.get('estimated_loc_savings', 0)}")

            groups = result.get('groups', [])
            if groups:
                print(f"\nTop 5 duplication groups by potential savings:")
                for i, group in enumerate(groups[:5], 1):
                    print(f"  {i}. Group with {group.get('instance_count', 0)} instances "
                          f"({group.get('similarity', 0):.1%} similar)")
                    print(f"     Potential LOC savings: {group.get('potential_loc_savings', 0)} lines")
                    instances = group.get('instances', [])
                    if instances:
                        print(f"     Locations:")
                        for inst in instances[:3]:
                            print(f"       - {inst.get('file', 'unknown')}:{inst.get('start_line', '?')}")
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during duplication analysis: {e}")
        import traceback
        traceback.print_exc()


def generate_summary_report():
    """Generate comprehensive quality report."""
    print_section("PHASE 6: Generate Comprehensive Quality Report")

    try:
        result = generate_quality_report_tool(
            project_folder='src/ast_grep_mcp',
            language='python',
            output_format='markdown',
            include_patterns=['**/*.py'],
            exclude_patterns=['**/__pycache__/**', '**/test_*.py'],
            max_threads=4
        )

        if result.get('success'):
            print("\nQuality report generated successfully!")
            report_content = result.get('report', '')
            if report_content:
                # Save to file
                report_file = Path('QUALITY_REPORT.md')
                report_file.write_text(report_content)
                print(f"Report saved to: {report_file.absolute()}")

                # Show summary
                print("\nReport Summary:")
                lines = report_content.split('\n')
                in_summary = False
                for line in lines[:50]:  # First 50 lines
                    if '## Summary' in line or '## Executive Summary' in line:
                        in_summary = True
                    if in_summary:
                        print(line)
                        if line.startswith('##') and 'Summary' not in line:
                            break
        else:
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"Exception during report generation: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all analyses."""
    print("="*80)
    print(" COMPREHENSIVE CODEBASE ANALYSIS - ast-grep-mcp")
    print("="*80)
    print("\nThis analysis uses all 30 MCP tools to evaluate code quality,")
    print("complexity, security, and duplication opportunities.\n")

    # Run all analysis phases
    analyze_individual_files()
    analyze_project_complexity()
    detect_code_smells()
    detect_security_issues()
    analyze_duplication()
    generate_summary_report()

    print_section("ANALYSIS COMPLETE")
    print("\nAll phases completed. Review the output above and QUALITY_REPORT.md")
    print("for detailed findings and recommendations.")


if __name__ == '__main__':
    main()
