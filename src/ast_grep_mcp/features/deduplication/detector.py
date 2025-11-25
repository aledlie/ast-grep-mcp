"""
Duplication detection module.

This module provides the core functionality for detecting duplicate code
in a codebase using ast-grep pattern matching and similarity analysis.
"""

import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from ...core.logging import get_logger
from ...core.executor import stream_ast_grep_results


class DuplicationDetector:
    """Core duplication detection functionality."""

    def __init__(self, language: str = "python"):
        """Initialize the duplication detector.

        Args:
            language: Programming language to analyze
        """
        self.language = language
        self.logger = get_logger("deduplication.detector")

    def find_duplication(
        self,
        project_folder: str,
        construct_type: str = "function_definition",
        min_similarity: float = 0.8,
        min_lines: int = 5,
        max_constructs: int = 1000,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect duplicate code in a project.

        Args:
            project_folder: Absolute path to the project folder
            construct_type: Type of construct to check ('function_definition', 'class_definition', 'method_definition')
            min_similarity: Minimum similarity threshold (0.0-1.0)
            min_lines: Minimum number of lines to consider
            max_constructs: Maximum number of constructs to analyze (0 for unlimited)
            exclude_patterns: Path patterns to exclude from analysis

        Returns:
            Dict containing duplication analysis results
        """
        start_time = time.time()

        if exclude_patterns is None:
            exclude_patterns = ["site-packages", "node_modules", ".venv", "venv", "vendor"]

        self.logger.info(
            "find_duplication_started",
            project_folder=project_folder,
            language=self.language,
            construct_type=construct_type,
            min_similarity=min_similarity,
            min_lines=min_lines,
            max_constructs=max_constructs,
            exclude_patterns=exclude_patterns
        )

        try:
            # Validate parameters
            self._validate_parameters(min_similarity, min_lines, max_constructs)

            # Get pattern for the construct type
            pattern = self._get_construct_pattern(construct_type)

            # Find all instances of the construct
            all_matches = self._find_constructs(
                project_folder,
                pattern,
                max_constructs,
                exclude_patterns
            )

            if not all_matches:
                execution_time = time.time() - start_time
                return self._empty_result(construct_type, execution_time)

            # Group duplicates by similarity
            duplication_groups = self.group_duplicates(all_matches, min_similarity, min_lines)

            # Generate refactoring suggestions
            suggestions = self.generate_refactoring_suggestions(
                duplication_groups,
                construct_type
            )

            # Calculate statistics
            stats = self._calculate_statistics(all_matches, duplication_groups, suggestions)

            execution_time = time.time() - start_time
            self.logger.info(
                "find_duplication_completed",
                execution_time_seconds=round(execution_time, 3),
                total_constructs=len(all_matches),
                duplicate_groups=len(duplication_groups),
                status="success"
            )

            return self._format_result(
                all_matches,
                duplication_groups,
                suggestions,
                stats,
                execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                "find_duplication_failed",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            raise

    def _validate_parameters(self, min_similarity: float, min_lines: int, max_constructs: int):
        """Validate input parameters."""
        if min_similarity < 0.0 or min_similarity > 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0")
        if min_lines < 1:
            raise ValueError("min_lines must be at least 1")
        if max_constructs < 0:
            raise ValueError("max_constructs must be 0 (unlimited) or positive")

    def _get_construct_pattern(self, construct_type: str) -> str:
        """Get ast-grep pattern for the construct type and language."""
        construct_patterns = {
            "function_definition": "def $NAME($$$)",  # Python/general
            "class_definition": "class $NAME",
            "method_definition": "def $NAME($$$)"
        }

        # Language-specific patterns
        if self.language.lower() in ["javascript", "typescript", "jsx", "tsx"]:
            construct_patterns["function_definition"] = "function $NAME($$$) { $$$ }"
            construct_patterns["method_definition"] = "$NAME($$$) { $$$ }"
        elif self.language.lower() in ["java", "csharp", "cpp", "c"]:
            construct_patterns["function_definition"] = "$TYPE $NAME($$$) { $$$ }"
            construct_patterns["method_definition"] = "$TYPE $NAME($$$) { $$$ }"

        return construct_patterns.get(construct_type, construct_patterns["function_definition"])

    def _find_constructs(
        self,
        project_folder: str,
        pattern: str,
        max_constructs: int,
        exclude_patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """Find all constructs matching the pattern."""
        args = ["--pattern", pattern, "--lang", self.language]

        self.logger.info(
            "searching_constructs",
            pattern=pattern,
            language=self.language
        )

        # Use streaming to get matches
        stream_limit = max_constructs if max_constructs > 0 else 0
        all_matches = list(stream_ast_grep_results(
            "run",
            args + ["--json=stream", project_folder],
            max_results=stream_limit,
            progress_interval=100
        ))

        # Filter out excluded paths
        if exclude_patterns:
            matches_before = len(all_matches)
            all_matches = [
                match for match in all_matches
                if not any(pattern in match.get('file', '') for pattern in exclude_patterns)
            ]
            if matches_before > len(all_matches):
                self.logger.info(
                    "excluded_matches",
                    total_before=matches_before,
                    total_after=len(all_matches),
                    excluded_count=matches_before - len(all_matches)
                )

        # Log if we hit the limit
        if max_constructs > 0 and len(all_matches) >= max_constructs:
            self.logger.info(
                "construct_limit_reached",
                total_found=len(all_matches),
                max_constructs=max_constructs
            )

        return all_matches

    def calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code snippets using normalized sequence matching."""
        if not code1 or not code2:
            return 0.0

        # Normalize whitespace for comparison
        norm1 = self._normalize_code(code1)
        norm2 = self._normalize_code(code2)

        # Use SequenceMatcher for similarity
        matcher = SequenceMatcher(None, norm1, norm2)
        return matcher.ratio()

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison by removing extra whitespace and comments."""
        lines = []
        for line in code.split('\n'):
            # Strip trailing whitespace
            line = line.rstrip()
            # Skip empty lines
            if line:
                # Normalize indentation to single spaces
                indent_count = len(line) - len(line.lstrip())
                normalized_line = ' ' * min(indent_count, 4) + line.lstrip()
                lines.append(normalized_line)
        return '\n'.join(lines)

    def group_duplicates(
        self,
        matches: List[Dict[str, Any]],
        min_similarity: float,
        min_lines: int
    ) -> List[List[Dict[str, Any]]]:
        """Group similar code constructs together."""
        if not matches:
            return []

        # Filter by minimum line count
        filtered_matches = []
        for match in matches:
            text = match.get('text', '')
            line_count = len(text.split('\n'))
            if line_count >= min_lines:
                filtered_matches.append(match)

        if not filtered_matches:
            return []

        # Use hash-based bucketing for initial grouping (optimization)
        buckets = self._create_hash_buckets(filtered_matches)

        # Find similar items within each bucket
        groups = []
        for bucket in buckets.values():
            bucket_groups = self._find_similar_in_bucket(bucket, min_similarity)
            groups.extend(bucket_groups)

        # Merge groups that share members
        merged_groups = self._merge_overlapping_groups(groups)

        # Filter out single-item groups
        return [group for group in merged_groups if len(group) > 1]

    def _create_hash_buckets(self, matches: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Create hash buckets for initial grouping (reduces O(n²) comparisons)."""
        buckets: Dict[int, List[Dict[str, Any]]] = {}

        for match in matches:
            text = match.get('text', '')
            # Create a simple hash based on code structure
            hash_val = self._calculate_structure_hash(text)

            if hash_val not in buckets:
                buckets[hash_val] = []
            buckets[hash_val].append(match)

        return buckets

    def _calculate_structure_hash(self, code: str) -> int:
        """Calculate a hash based on code structure for bucketing."""
        # Simple hash based on number of lines and key tokens
        lines = code.split('\n')
        line_count = len(lines)

        # Count some structural elements
        keywords = ['def', 'class', 'if', 'for', 'while', 'return', 'function', 'var', 'let', 'const']
        keyword_count = sum(1 for line in lines for kw in keywords if kw in line)

        # Create a simple hash that groups similar structures
        return (line_count // 5) * 1000 + keyword_count

    def _find_similar_in_bucket(
        self,
        bucket: List[Dict[str, Any]],
        min_similarity: float
    ) -> List[List[Dict[str, Any]]]:
        """Find similar items within a bucket."""
        groups = []
        used = set()

        for i, item1 in enumerate(bucket):
            if i in used:
                continue

            group = [item1]
            used.add(i)

            for j, item2 in enumerate(bucket[i+1:], i+1):
                if j in used:
                    continue

                similarity = self.calculate_similarity(
                    item1.get('text', ''),
                    item2.get('text', '')
                )

                if similarity >= min_similarity:
                    group.append(item2)
                    used.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _merge_overlapping_groups(self, groups: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """Merge groups that share common members."""
        if not groups:
            return []

        # Create a mapping of items to group indices
        item_to_groups: Dict[str, List[int]] = {}

        for idx, group in enumerate(groups):
            for item in group:
                # Use file + line as unique identifier
                key = f"{item.get('file', '')}:{item.get('range', {}).get('start', {}).get('line', 0)}"
                if key not in item_to_groups:
                    item_to_groups[key] = []
                item_to_groups[key].append(idx)

        # Merge groups that share items
        merged = []
        used_groups = set()

        for idx, group in enumerate(groups):
            if idx in used_groups:
                continue

            merged_group = group.copy()
            used_groups.add(idx)

            # Find all connected groups
            to_merge = [idx]
            while to_merge:
                current_idx = to_merge.pop()
                for item in groups[current_idx]:
                    key = f"{item.get('file', '')}:{item.get('range', {}).get('start', {}).get('line', 0)}"
                    for connected_idx in item_to_groups.get(key, []):
                        if connected_idx not in used_groups:
                            to_merge.append(connected_idx)
                            used_groups.add(connected_idx)
                            # Add unique items from connected group
                            for connected_item in groups[connected_idx]:
                                if not any(
                                    self._items_equal(connected_item, existing)
                                    for existing in merged_group
                                ):
                                    merged_group.append(connected_item)

            merged.append(merged_group)

        return merged

    def _items_equal(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Check if two match items are the same."""
        return (
            item1.get('file') == item2.get('file') and
            item1.get('range', {}).get('start', {}).get('line') ==
            item2.get('range', {}).get('start', {}).get('line')
        )

    def generate_refactoring_suggestions(
        self,
        duplication_groups: List[List[Dict[str, Any]]],
        construct_type: str
    ) -> List[Dict[str, Any]]:
        """Generate refactoring suggestions for duplication groups."""
        suggestions = []

        for idx, group in enumerate(duplication_groups):
            if len(group) < 2:
                continue

            # Calculate metrics for the group
            first_item = group[0]
            text = first_item.get('text', '')
            lines = len(text.split('\n'))

            total_lines = lines * len(group)
            potential_savings = total_lines - lines  # Keep one instance

            # Determine refactoring strategy
            strategy = self._determine_refactoring_strategy(group, construct_type)

            suggestions.append({
                "group_id": idx + 1,
                "duplicate_count": len(group),
                "lines_per_duplicate": lines,
                "total_duplicated_lines": total_lines,
                "potential_line_savings": potential_savings,
                "refactoring_strategy": strategy,
                "locations": [
                    {
                        "file": item.get('file', ''),
                        "line": item.get('range', {}).get('start', {}).get('line', 0) + 1
                    }
                    for item in group
                ]
            })

        return suggestions

    def _determine_refactoring_strategy(
        self,
        group: List[Dict[str, Any]],
        construct_type: str
    ) -> Dict[str, str]:
        """Determine the best refactoring strategy for a duplication group."""
        # Analyze the code to determine strategy
        first_text = group[0].get('text', '')
        line_count = len(first_text.split('\n'))

        # Simple heuristics for strategy selection
        if construct_type == "function_definition":
            if line_count < 10:
                return {
                    "type": "extract_utility_function",
                    "description": "Extract duplicated logic into a shared utility function"
                }
            else:
                return {
                    "type": "extract_module",
                    "description": "Extract duplicated logic into a separate module"
                }
        elif construct_type == "class_definition":
            return {
                "type": "extract_base_class",
                "description": "Extract common functionality into a base class"
            }
        else:  # method_definition
            return {
                "type": "extract_method",
                "description": "Extract duplicated method to a parent class or mixin"
            }

    def _calculate_statistics(
        self,
        all_matches: List[Dict[str, Any]],
        duplication_groups: List[List[Dict[str, Any]]],
        suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate summary statistics."""
        total_duplicated_lines = sum(s["total_duplicated_lines"] for s in suggestions)
        potential_savings = sum(s["potential_line_savings"] for s in suggestions)

        return {
            "total_constructs": len(all_matches),
            "duplicate_groups": len(duplication_groups),
            "total_duplicated_lines": total_duplicated_lines,
            "potential_line_savings": potential_savings
        }

    def _empty_result(self, construct_type: str, execution_time: float) -> Dict[str, Any]:
        """Return empty result when no constructs found."""
        return {
            "summary": {
                "total_constructs": 0,
                "duplicate_groups": 0,
                "total_duplicated_lines": 0,
                "potential_line_savings": 0,
                "analysis_time_seconds": round(execution_time, 3)
            },
            "duplication_groups": [],
            "refactoring_suggestions": [],
            "message": f"No {construct_type} instances found in the project"
        }

    def _format_result(
        self,
        all_matches: List[Dict[str, Any]],
        duplication_groups: List[List[Dict[str, Any]]],
        suggestions: List[Dict[str, Any]],
        stats: Dict[str, Any],
        execution_time: float
    ) -> Dict[str, Any]:
        """Format the final result."""
        # Format duplication groups for output
        formatted_groups = []
        for idx, group in enumerate(duplication_groups):
            instances = []
            for match in group:
                file_path = match.get('file', '')
                start_line = match.get('range', {}).get('start', {}).get('line', 0) + 1
                end_line = match.get('range', {}).get('end', {}).get('line', 0) + 1
                instances.append({
                    "file": file_path,
                    "lines": f"{start_line}-{end_line}",
                    "code_preview": match.get('text', '')[:200]  # First 200 chars
                })

            formatted_groups.append({
                "group_id": idx + 1,
                "similarity_score": round(
                    self.calculate_similarity(
                        group[0].get('text', ''),
                        group[1].get('text', '')
                    ),
                    3
                ) if len(group) >= 2 else 1.0,
                "instances": instances
            })

        return {
            "summary": {
                **stats,
                "analysis_time_seconds": round(execution_time, 3)
            },
            "duplication_groups": formatted_groups,
            "refactoring_suggestions": suggestions,
            "message": f"Found {stats['duplicate_groups']} duplication group(s) with potential to save {stats['potential_line_savings']} lines of code"
        }