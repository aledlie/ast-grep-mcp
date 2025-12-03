"""Enhanced reporting and visualization for deduplication results."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...utils.formatters import generate_multi_file_diff


@dataclass
class EnhancedDuplicationCandidate:
    """Enhanced duplication candidate with full reporting details.

    Attributes:
        id: Unique identifier for this candidate
        files: List of file paths containing the duplicate
        locations: List of (file, start_line, end_line) tuples
        original_code: The duplicate code snippet
        suggested_function_name: Suggested name for extracted function
        replacement_code: Code to replace each occurrence
        similarity_score: How similar the duplicates are (0-100)
        complexity_score: Complexity rating (1-10)
        before_after: Before/after example dict
        complexity_viz: Complexity visualization dict
        diff_preview: Diff preview for all files
        priority: Priority ranking (higher = more important)
    """

    id: str
    files: List[str]
    locations: List[Tuple[str, int, int]]
    original_code: str
    suggested_function_name: str
    replacement_code: str
    similarity_score: float
    complexity_score: int
    before_after: Dict[str, Any]
    complexity_viz: Dict[str, Any]
    diff_preview: Optional[str]
    priority: int


class DuplicationReporter:
    """Creates enhanced reports for code duplication findings."""

    def format_diff_with_colors(self, diff: str) -> str:
        """Add ANSI color codes to a unified diff for CLI display.

        Args:
            diff: Unified diff string

        Returns:
            Diff string with ANSI color codes:
            - Green for additions (+)
            - Red for deletions (-)
            - Cyan for hunk headers (@@)
            - Yellow for file headers (--- / +++)
        """
        if not diff:
            return diff

        # ANSI color codes
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        CYAN = "\033[36m"
        RESET = "\033[0m"

        colored_lines = []
        for line in diff.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                colored_lines.append(f"{YELLOW}{line}{RESET}")
            elif line.startswith("@@"):
                colored_lines.append(f"{CYAN}{line}{RESET}")
            elif line.startswith("+"):
                colored_lines.append(f"{GREEN}{line}{RESET}")
            elif line.startswith("-"):
                colored_lines.append(f"{RED}{line}{RESET}")
            else:
                colored_lines.append(line)

        return "\n".join(colored_lines)

    def generate_before_after_example(self, original_code: str, replacement_code: str, function_name: str) -> Dict[str, Any]:
        """Generate before/after code examples for a duplication extraction.

        Creates readable code snippets showing the original duplicate code
        and how it looks after extraction into a reusable function.

        Args:
            original_code: The original duplicate code snippet
            replacement_code: The replacement code (function call)
            function_name: Name of the extracted function

        Returns:
            Dictionary containing:
            - before: Original code snippet with context
            - after: Code with extracted function call
            - function_definition: The extracted function's signature
            - explanation: Human-readable explanation of the change
        """
        # Clean up the code snippets
        original_lines = original_code.strip().split("\n")
        replacement_lines = replacement_code.strip().split("\n")

        # Calculate metrics
        original_line_count = len(original_lines)
        replacement_line_count = len(replacement_lines)
        lines_saved = original_line_count - replacement_line_count

        # Format the before section with line numbers
        before_formatted = []
        for i, line in enumerate(original_lines, 1):
            before_formatted.append(f"{i:3d} | {line}")

        # Format the after section with line numbers
        after_formatted = []
        for i, line in enumerate(replacement_lines, 1):
            after_formatted.append(f"{i:3d} | {line}")

        # Generate a simple function signature based on name
        function_definition = f"def {function_name}(...):"

        # Create explanation
        if lines_saved > 0:
            explanation = (
                f"Extracted {original_line_count} lines of duplicate code into "
                f"'{function_name}', reducing to {replacement_line_count} line(s). "
                f"This saves {lines_saved} line(s) per occurrence."
            )
        else:
            explanation = f"Refactored code into '{function_name}' for better reusability and maintainability."

        return {
            "before": "\n".join(before_formatted),
            "after": "\n".join(after_formatted),
            "before_raw": original_code.strip(),
            "after_raw": replacement_code.strip(),
            "function_definition": function_definition,
            "function_name": function_name,
            "original_lines": original_line_count,
            "replacement_lines": replacement_line_count,
            "lines_saved": lines_saved,
            "explanation": explanation,
        }

    def visualize_complexity(self, score: int) -> Dict[str, Any]:
        """Create a visual complexity indicator with recommendations.

        Args:
            score: Complexity score from 1-10

        Returns:
            Dictionary containing:
            - bar: ASCII bar visualization
            - description: Text description (Low/Medium/High)
            - color_code: ANSI color code for CLI
            - recommendations: List of actionable recommendations
            - score: The input score
        """
        # Clamp score to valid range
        score = max(1, min(10, score))

        # Determine description and color based on score
        if score <= 3:
            description = "Low"
            color_code = "\033[32m"  # Green
            recommendations = [
                "Good candidate for quick refactoring",
                "Consider extracting as a simple helper function",
                "Low risk of introducing bugs during extraction",
            ]
        elif score <= 6:
            description = "Medium"
            color_code = "\033[33m"  # Yellow
            recommendations = [
                "Review the code carefully before extraction",
                "Consider adding unit tests before refactoring",
                "May benefit from breaking into smaller pieces",
                "Check for hidden dependencies or side effects",
            ]
        else:
            description = "High"
            color_code = "\033[31m"  # Red
            recommendations = [
                "High complexity - proceed with caution",
                "Strongly recommend comprehensive test coverage first",
                "Consider incremental refactoring in smaller steps",
                "Review for cyclomatic complexity and reduce branches",
                "May need architectural review before extraction",
            ]

        reset_code = "\033[0m"

        # Create ASCII bar visualization
        filled = score
        empty = 10 - score
        bar_plain = f"[{'=' * filled}{' ' * empty}] {score}/10"
        bar_colored = f"{color_code}[{'=' * filled}{' ' * empty}]{reset_code} {score}/10"

        return {
            "score": score,
            "bar": bar_plain,
            "bar_colored": bar_colored,
            "description": description,
            "color_code": color_code,
            "recommendations": recommendations,
            "formatted": f"{description} Complexity ({score}/10): {bar_plain}",
        }

    def create_enhanced_duplication_response(
        self, candidates: List[Dict[str, Any]], include_diffs: bool = True, include_colors: bool = False
    ) -> Dict[str, Any]:
        """Create an enhanced duplication detection response.

        This is the main entry point for Phase 5 enhanced reporting.
        Takes raw duplication candidates and enriches them with:
        - Before/after examples
        - Complexity visualizations
        - Colored diffs (optional)
        - Actionable recommendations

        Args:
            candidates: List of raw duplication candidates with keys:
                - files: List of file paths
                - locations: List of (file, start, end) tuples
                - code: The duplicate code
                - function_name: Suggested function name
                - replacement: Replacement code
                - similarity: Similarity score (0-100)
                - complexity: Complexity score (1-10)
            include_diffs: Whether to generate diff previews
            include_colors: Whether to include ANSI color codes

        Returns:
            Enhanced response dictionary with:
            - candidates: List of EnhancedDuplicationCandidate as dicts
            - summary: Overall summary statistics
            - recommendations: Global recommendations
            - metadata: Response metadata
        """
        enhanced_candidates = []
        total_lines_saveable = 0
        complexity_distribution = {"low": 0, "medium": 0, "high": 0}

        for idx, candidate in enumerate(candidates):
            # Generate before/after example
            before_after = self.generate_before_after_example(
                original_code=candidate.get("code", ""),
                replacement_code=candidate.get("replacement", ""),
                function_name=candidate.get("function_name", f"extracted_function_{idx}"),
            )

            # Generate complexity visualization
            complexity = candidate.get("complexity", 5)
            complexity_viz = self.visualize_complexity(complexity)

            # Track complexity distribution
            if complexity <= 3:
                complexity_distribution["low"] += 1
            elif complexity <= 6:
                complexity_distribution["medium"] += 1
            else:
                complexity_distribution["high"] += 1

            # Generate diff preview if requested
            diff_preview = None
            if include_diffs and "files" in candidate:
                file_changes = []
                original_code = candidate.get("code", "")
                replacement = candidate.get("replacement", "")

                for file_path in candidate.get("files", []):
                    # For demonstration, create a simple diff
                    # In real usage, this would read actual file contents
                    file_changes.append({"file_path": file_path, "original_content": original_code, "new_content": replacement})

                if file_changes:
                    preview = generate_multi_file_diff(file_changes, context_lines=3)
                    diff_text = preview.combined_diff
                    if include_colors:
                        diff_text = self.format_diff_with_colors(diff_text)
                    diff_preview = diff_text

            # Calculate priority based on multiple factors
            occurrences = len(candidate.get("files", []))
            lines = before_after["original_lines"]
            priority = (occurrences * 10) + (lines * 2) - (complexity * 3)

            # Track total saveable lines
            total_lines_saveable += before_after["lines_saved"] * occurrences

            # Get function name with fallback
            function_name = candidate.get("function_name", "") or f"extracted_function_{idx}"

            enhanced_candidate = {
                "id": f"DUP-{idx + 1:03d}",
                "files": candidate.get("files", []),
                "locations": candidate.get("locations", []),
                "original_code": candidate.get("code", ""),
                "suggested_function_name": function_name,
                "replacement_code": candidate.get("replacement", ""),
                "similarity_score": candidate.get("similarity", 100.0),
                "complexity_score": complexity,
                "before_after": before_after,
                "complexity_viz": complexity_viz,
                "diff_preview": diff_preview,
                "priority": priority,
            }

            enhanced_candidates.append(enhanced_candidate)

        # Sort by priority (highest first)
        enhanced_candidates.sort(key=lambda x: x["priority"], reverse=True)

        # Generate global recommendations
        global_recommendations = []

        if complexity_distribution["high"] > 0:
            global_recommendations.append(
                f"Found {complexity_distribution['high']} high-complexity duplicates. Consider adding tests before refactoring these."
            )

        if total_lines_saveable > 50:
            global_recommendations.append(
                f"Potential to save {total_lines_saveable} total lines of code. Prioritize candidates by their priority score."
            )

        if len(enhanced_candidates) > 5:
            global_recommendations.append(
                "Many duplicates found. Consider addressing high-priority items first to maximize impact with minimal effort."
            )

        # Build summary
        summary = {
            "total_candidates": len(enhanced_candidates),
            "total_files_affected": len(set(f for c in candidates for f in c.get("files", []))),
            "total_lines_saveable": total_lines_saveable,
            "complexity_distribution": complexity_distribution,
            "highest_priority_id": enhanced_candidates[0]["id"] if enhanced_candidates else None,
        }

        return {
            "candidates": enhanced_candidates,
            "summary": summary,
            "recommendations": global_recommendations,
            "metadata": {
                "version": "5.0",
                "includes_diffs": include_diffs,
                "includes_colors": include_colors,
                "generated_at": datetime.now().isoformat(),
            },
        }


# Module-level functions for backwards compatibility
_reporter = DuplicationReporter()


def format_diff_with_colors(diff: str) -> str:
    """Add ANSI color codes to a unified diff for CLI display."""
    return _reporter.format_diff_with_colors(diff)


def generate_before_after_example(original_code: str, replacement_code: str, function_name: str) -> Dict[str, Any]:
    """Generate before/after code examples for a duplication extraction."""
    return _reporter.generate_before_after_example(original_code, replacement_code, function_name)


def visualize_complexity(score: int) -> Dict[str, Any]:
    """Create a visual complexity indicator with recommendations."""
    return _reporter.visualize_complexity(score)


def create_enhanced_duplication_response(
    candidates: List[Dict[str, Any]], include_diffs: bool = True, include_colors: bool = False
) -> Dict[str, Any]:
    """Create an enhanced duplication detection response."""
    return _reporter.create_enhanced_duplication_response(candidates, include_diffs, include_colors)
