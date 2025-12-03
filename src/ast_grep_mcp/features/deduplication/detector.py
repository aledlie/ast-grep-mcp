"""
Duplication detection module.

This module provides the core functionality for detecting duplicate code
in a codebase using ast-grep pattern matching and similarity analysis.

Performance optimization (v0.2.0):
- Replaced SequenceMatcher O(n²) with MinHash O(n) for similarity calculation
- Added LSH indexing for scalable candidate retrieval
- Improved structure hash using token pattern fingerprints

Hybrid Pipeline (v0.3.0):
- Two-stage similarity: fast MinHash filter + precise AST verification
- Scientific basis: TACC (ICSE 2023) demonstrates optimal precision/recall
- Configurable thresholds and weights for tuning behavior
"""

import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Literal, Optional

from ...core.executor import stream_ast_grep_results
from ...core.logging import get_logger
from ...core.usage_tracking import OperationType, track_operation
from .similarity import (
    EnhancedStructureHash,
    HybridSimilarity,
    HybridSimilarityConfig,
    HybridSimilarityResult,
    MinHashSimilarity,
    SimilarityConfig,
)

# Type alias for similarity mode selection
SimilarityMode = Literal["minhash", "hybrid", "sequence_matcher"]


class DuplicationDetector:
    """Core duplication detection functionality."""

    def __init__(
        self,
        language: str = "python",
        use_minhash: bool = True,
        similarity_mode: SimilarityMode = "hybrid",
        similarity_config: Optional[SimilarityConfig] = None,
        hybrid_config: Optional[HybridSimilarityConfig] = None,
    ) -> None:
        """Initialize the duplication detector.

        Args:
            language: Programming language to analyze
            use_minhash: Legacy parameter - use similarity_mode instead.
                        If False, overrides similarity_mode to 'sequence_matcher'.
            similarity_mode: Similarity calculation mode:
                - 'hybrid': Two-stage pipeline (recommended) - fast MinHash filter + AST verification
                - 'minhash': Fast MinHash only (O(n)) - good for large codebases
                - 'sequence_matcher': Precise but slow (O(n²)) - for small codebases
            similarity_config: Configuration for MinHash similarity calculation
            hybrid_config: Configuration for hybrid pipeline behavior
        """
        self.language = language
        self.logger = get_logger("deduplication.detector")

        # Handle legacy use_minhash parameter
        if not use_minhash:
            similarity_mode = "sequence_matcher"
        self.similarity_mode = similarity_mode
        self.use_minhash = similarity_mode != "sequence_matcher"

        # Initialize similarity calculators
        self._minhash = MinHashSimilarity(similarity_config)
        self._hybrid = HybridSimilarity(similarity_config, hybrid_config)
        self._structure_hash = EnhancedStructureHash()

        self.logger.info(
            "detector_initialized",
            language=language,
            similarity_mode=similarity_mode,
        )

    def find_duplication(
        self,
        project_folder: str,
        construct_type: str = "function_definition",
        min_similarity: float = 0.8,
        min_lines: int = 5,
        max_constructs: int = 1000,
        exclude_patterns: Optional[List[str]] = None,
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
            exclude_patterns=exclude_patterns,
        )

        # Track usage for cost monitoring
        with track_operation(
            "find_duplication", OperationType.FIND_DUPLICATION, metadata={"language": self.language, "construct_type": construct_type}
        ) as tracker:
            try:
                # Validate parameters
                self._validate_parameters(min_similarity, min_lines, max_constructs)

                # Get pattern for the construct type
                pattern = self._get_construct_pattern(construct_type)

                # Find all instances of the construct
                all_matches = self._find_constructs(project_folder, pattern, max_constructs, exclude_patterns)

                # Update tracker with metrics
                tracker.files_processed = len(set(m.get("file", "") for m in all_matches))
                tracker.lines_analyzed = sum(len(m.get("text", "").split("\n")) for m in all_matches)

                if not all_matches:
                    execution_time = time.time() - start_time
                    return self._empty_result(construct_type, execution_time)

                # Group duplicates by similarity
                duplication_groups = self.group_duplicates(all_matches, min_similarity, min_lines)

                # Generate refactoring suggestions
                suggestions = self.generate_refactoring_suggestions(duplication_groups, construct_type)

                # Calculate statistics
                stats = self._calculate_statistics(all_matches, duplication_groups, suggestions)

                # Update tracker with match count
                tracker.matches_found = len(duplication_groups)

                execution_time = time.time() - start_time
                self.logger.info(
                    "find_duplication_completed",
                    execution_time_seconds=round(execution_time, 3),
                    total_constructs=len(all_matches),
                    duplicate_groups=len(duplication_groups),
                    status="success",
                )

                return self._format_result(all_matches, duplication_groups, suggestions, stats, execution_time)

            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(
                    "find_duplication_failed", execution_time_seconds=round(execution_time, 3), error=str(e)[:200], status="failed"
                )
                raise

    def _validate_parameters(self, min_similarity: float, min_lines: int, max_constructs: int) -> None:
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
            "method_definition": "def $NAME($$$)",
        }

        # Language-specific patterns
        if self.language.lower() in ["javascript", "typescript", "jsx", "tsx"]:
            # For JS/TS, we need to support multiple patterns:
            # 1. Traditional function declarations
            # 2. Arrow functions (const NAME = (...) => {...})
            # 3. Const functions (const NAME = function(...) {...})
            # 4. Object methods

            # Use pattern that matches arrow functions and const functions
            # This is the most common pattern in modern JS/TS
            if construct_type == "function_definition":
                # Match: const NAME = (...) => { ... }
                # Match: const NAME = function(...) { ... }
                construct_patterns["function_definition"] = "const $NAME = $$$"
            elif construct_type == "arrow_function":
                # Specifically for arrow functions
                construct_patterns["arrow_function"] = "const $NAME = ($$$) => $$$"
            elif construct_type == "traditional_function":
                # Traditional function declarations
                construct_patterns["traditional_function"] = "function $NAME($$$) { $$$ }"
            elif construct_type == "method_definition":
                # Object methods: methodName() { ... }
                construct_patterns["method_definition"] = "$NAME($$$) { $$$ }"
            else:
                # Default to const assignments for modern JS/TS
                construct_patterns[construct_type] = "const $NAME = $$$"

        elif self.language.lower() in ["java", "csharp", "cpp", "c"]:
            construct_patterns["function_definition"] = "$TYPE $NAME($$$) { $$$ }"
            construct_patterns["method_definition"] = "$TYPE $NAME($$$) { $$$ }"

        return construct_patterns.get(construct_type, construct_patterns["function_definition"])

    def _find_constructs(self, project_folder: str, pattern: str, max_constructs: int, exclude_patterns: List[str]) -> List[Dict[str, Any]]:
        """Find all constructs matching the pattern."""
        args = ["--pattern", pattern, "--lang", self.language]

        self.logger.info("searching_constructs", pattern=pattern, language=self.language)

        # Use streaming to get matches
        stream_limit = max_constructs if max_constructs > 0 else 0
        all_matches = list(
            stream_ast_grep_results("run", args + ["--json=stream", project_folder], max_results=stream_limit, progress_interval=100)
        )

        # Filter out excluded paths
        if exclude_patterns:
            matches_before = len(all_matches)
            all_matches = [match for match in all_matches if not any(pattern in match.get("file", "") for pattern in exclude_patterns)]
            if matches_before > len(all_matches):
                self.logger.info(
                    "excluded_matches",
                    total_before=matches_before,
                    total_after=len(all_matches),
                    excluded_count=matches_before - len(all_matches),
                )

        # Log if we hit the limit
        if max_constructs > 0 and len(all_matches) >= max_constructs:
            self.logger.info("construct_limit_reached", total_found=len(all_matches), max_constructs=max_constructs)

        return all_matches

    def calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code snippets.

        Uses the configured similarity mode:
        - 'hybrid': Two-stage pipeline (recommended) - fast filter + precise verification
        - 'minhash': Fast MinHash only (O(n)) - good for large codebases
        - 'sequence_matcher': Precise but slow (O(n²)) - for small codebases

        Args:
            code1: First code snippet.
            code2: Second code snippet.

        Returns:
            Similarity score between 0.0 and 1.0.
        """
        if not code1 or not code2:
            return 0.0

        if self.similarity_mode == "hybrid":
            # Two-stage hybrid pipeline - optimal precision/recall
            return self._hybrid.estimate_similarity(code1, code2)
        elif self.similarity_mode == "minhash":
            # Fast MinHash estimation - O(n) complexity
            return self._minhash.estimate_similarity(code1, code2)
        else:
            # Fallback to SequenceMatcher - O(n²) complexity
            norm1 = self._normalize_code(code1)
            norm2 = self._normalize_code(code2)
            matcher = SequenceMatcher(None, norm1, norm2)
            return matcher.ratio()

    def calculate_similarity_detailed(
        self,
        code1: str,
        code2: str,
    ) -> HybridSimilarityResult:
        """Calculate similarity with detailed hybrid pipeline results.

        Returns full details about which stages were executed and
        individual similarity scores from each stage.

        Args:
            code1: First code snippet.
            code2: Second code snippet.

        Returns:
            HybridSimilarityResult with detailed similarity information.
        """
        return self._hybrid.calculate_hybrid_similarity(code1, code2)

    def calculate_similarity_precise(self, code1: str, code2: str) -> float:
        """Calculate precise similarity using SequenceMatcher.

        Use this for final verification of candidates identified by MinHash.

        Args:
            code1: First code snippet.
            code2: Second code snippet.

        Returns:
            Precise similarity score between 0.0 and 1.0.
        """
        if not code1 or not code2:
            return 0.0

        norm1 = self._normalize_code(code1)
        norm2 = self._normalize_code(code2)
        matcher = SequenceMatcher(None, norm1, norm2)
        return matcher.ratio()

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison by removing extra whitespace and comments."""
        lines = []
        for line in code.split("\n"):
            # Strip trailing whitespace
            line = line.rstrip()
            # Skip empty lines
            if line:
                # Normalize indentation to single spaces
                indent_count = len(line) - len(line.lstrip())
                normalized_line = " " * min(indent_count, 4) + line.lstrip()
                lines.append(normalized_line)
        return "\n".join(lines)

    def group_duplicates(self, matches: List[Dict[str, Any]], min_similarity: float, min_lines: int) -> List[List[Dict[str, Any]]]:
        """Group similar code constructs together."""
        if not matches:
            return []

        # Filter by minimum line count
        filtered_matches = []
        for match in matches:
            text = match.get("text", "")
            line_count = len(text.split("\n"))
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
            text = match.get("text", "")
            # Create a simple hash based on code structure
            hash_val = self._calculate_structure_hash(text)

            if hash_val not in buckets:
                buckets[hash_val] = []
            buckets[hash_val].append(match)

        return buckets

    def _calculate_structure_hash(self, code: str) -> int:
        """Calculate a hash based on code structure for bucketing.

        Uses enhanced token pattern fingerprinting for better bucket distribution.
        Groups code by control flow, definitions, returns, and indentation depth.

        Args:
            code: Source code to hash.

        Returns:
            Structure hash integer for bucket assignment.
        """
        return self._structure_hash.calculate(code)

    def _find_similar_in_bucket(self, bucket: List[Dict[str, Any]], min_similarity: float) -> List[List[Dict[str, Any]]]:
        """Find similar items within a bucket."""
        groups = []
        used = set()

        for i, item1 in enumerate(bucket):
            if i in used:
                continue

            group = [item1]
            used.add(i)

            for j, item2 in enumerate(bucket[i + 1 :], i + 1):
                if j in used:
                    continue

                similarity = self.calculate_similarity(item1.get("text", ""), item2.get("text", ""))

                if similarity >= min_similarity:
                    group.append(item2)
                    used.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _get_item_key(self, item: Dict[str, Any]) -> str:
        """Get unique key for an item."""
        file = item.get("file", "")
        line = item.get("range", {}).get("start", {}).get("line", 0)
        return f"{file}:{line}"

    def _build_item_to_groups_map(self, groups: List[List[Dict[str, Any]]]) -> Dict[str, List[int]]:
        """Build mapping from items to group indices."""
        item_to_groups: Dict[str, List[int]] = {}
        for idx, group in enumerate(groups):
            for item in group:
                key = self._get_item_key(item)
                if key not in item_to_groups:
                    item_to_groups[key] = []
                item_to_groups[key].append(idx)
        return item_to_groups

    def _add_unique_items(self, target: List[Dict[str, Any]], source: List[Dict[str, Any]]) -> None:
        """Add unique items from source to target."""
        for item in source:
            if not any(self._items_equal(item, existing) for existing in target):
                target.append(item)

    def _process_group_connections(
        self,
        current_idx: int,
        groups: List[List[Dict[str, Any]]],
        item_to_groups: Dict[str, List[int]],
        used_groups: set[int],
        to_merge: list[int],
        merged_group: list[Dict[str, Any]],
    ) -> None:
        """Process connections for a single group."""
        for item in groups[current_idx]:
            key = self._get_item_key(item)
            for connected_idx in item_to_groups.get(key, []):
                if connected_idx not in used_groups:
                    to_merge.append(connected_idx)
                    used_groups.add(connected_idx)
                    self._add_unique_items(merged_group, groups[connected_idx])

    def _merge_overlapping_groups(self, groups: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """Merge groups that share common members."""
        if not groups:
            return []

        # Build mapping of items to groups
        item_to_groups = self._build_item_to_groups_map(groups)

        # Merge connected groups
        merged = []
        used_groups = set()

        for idx, group in enumerate(groups):
            if idx in used_groups:
                continue

            merged_group = group.copy()
            used_groups.add(idx)

            # Process all connected groups
            to_merge = [idx]
            while to_merge:
                current_idx = to_merge.pop()
                self._process_group_connections(current_idx, groups, item_to_groups, used_groups, to_merge, merged_group)

            merged.append(merged_group)

        return merged

    def _items_equal(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Check if two match items are the same."""
        return item1.get("file") == item2.get("file") and item1.get("range", {}).get("start", {}).get("line") == item2.get("range", {}).get(
            "start", {}
        ).get("line")

    def generate_refactoring_suggestions(self, duplication_groups: List[List[Dict[str, Any]]], construct_type: str) -> List[Dict[str, Any]]:
        """Generate refactoring suggestions for duplication groups."""
        suggestions = []

        for idx, group in enumerate(duplication_groups):
            if len(group) < 2:
                continue

            # Calculate metrics for the group
            first_item = group[0]
            text = first_item.get("text", "")
            lines = len(text.split("\n"))

            total_lines = lines * len(group)
            potential_savings = total_lines - lines  # Keep one instance

            # Determine refactoring strategy
            strategy = self._determine_refactoring_strategy(group, construct_type)

            suggestions.append(
                {
                    "group_id": idx + 1,
                    "duplicate_count": len(group),
                    "lines_per_duplicate": lines,
                    "total_duplicated_lines": total_lines,
                    "potential_line_savings": potential_savings,
                    "refactoring_strategy": strategy,
                    "locations": [
                        {"file": item.get("file", ""), "line": item.get("range", {}).get("start", {}).get("line", 0) + 1} for item in group
                    ],
                }
            )

        return suggestions

    def _determine_refactoring_strategy(self, group: List[Dict[str, Any]], construct_type: str) -> Dict[str, str]:
        """Determine the best refactoring strategy for a duplication group."""
        # Analyze the code to determine strategy
        first_text = group[0].get("text", "")
        line_count = len(first_text.split("\n"))

        # Simple heuristics for strategy selection
        if construct_type == "function_definition":
            if line_count < 10:
                return {"type": "extract_utility_function", "description": "Extract duplicated logic into a shared utility function"}
            else:
                return {"type": "extract_module", "description": "Extract duplicated logic into a separate module"}
        elif construct_type == "class_definition":
            return {"type": "extract_base_class", "description": "Extract common functionality into a base class"}
        else:  # method_definition
            return {"type": "extract_method", "description": "Extract duplicated method to a parent class or mixin"}

    def _calculate_statistics(
        self, all_matches: List[Dict[str, Any]], duplication_groups: List[List[Dict[str, Any]]], suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate summary statistics."""
        total_duplicated_lines = sum(s["total_duplicated_lines"] for s in suggestions)
        potential_savings = sum(s["potential_line_savings"] for s in suggestions)

        return {
            "total_constructs": len(all_matches),
            "duplicate_groups": len(duplication_groups),
            "total_duplicated_lines": total_duplicated_lines,
            "potential_line_savings": potential_savings,
        }

    def _empty_result(self, construct_type: str, execution_time: float) -> Dict[str, Any]:
        """Return empty result when no constructs found."""
        return {
            "summary": {
                "total_constructs": 0,
                "duplicate_groups": 0,
                "total_duplicated_lines": 0,
                "potential_line_savings": 0,
                "analysis_time_seconds": round(execution_time, 3),
            },
            "duplication_groups": [],
            "refactoring_suggestions": [],
            "message": f"No {construct_type} instances found in the project",
        }

    def _format_result(
        self,
        all_matches: List[Dict[str, Any]],
        duplication_groups: List[List[Dict[str, Any]]],
        suggestions: List[Dict[str, Any]],
        stats: Dict[str, Any],
        execution_time: float,
    ) -> Dict[str, Any]:
        """Format the final result."""
        # Format duplication groups for output
        formatted_groups = []
        for idx, group in enumerate(duplication_groups):
            instances = []
            for match in group:
                file_path = match.get("file", "")
                start_line = match.get("range", {}).get("start", {}).get("line", 0) + 1
                end_line = match.get("range", {}).get("end", {}).get("line", 0) + 1
                instances.append(
                    {
                        "file": file_path,
                        "lines": f"{start_line}-{end_line}",
                        "code_preview": match.get("text", "")[:200],  # First 200 chars
                    }
                )

            formatted_groups.append(
                {
                    "group_id": idx + 1,
                    "similarity_score": round(self.calculate_similarity(group[0].get("text", ""), group[1].get("text", "")), 3)
                    if len(group) >= 2
                    else 1.0,
                    "instances": instances,
                }
            )

        return {
            "summary": {**stats, "analysis_time_seconds": round(execution_time, 3)},
            "duplication_groups": formatted_groups,
            "refactoring_suggestions": suggestions,
            "message": (
                f"Found {stats['duplicate_groups']} duplication group(s) "
                f"with potential to save {stats['potential_line_savings']} lines"
            ),
        }
