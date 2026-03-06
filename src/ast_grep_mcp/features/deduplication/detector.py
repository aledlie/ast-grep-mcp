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

from ...constants import DeduplicationDefaults, DetectorDefaults, DisplayDefaults, FormattingDefaults, IndentationDefaults, StreamDefaults
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
_MANDATORY_ENV_EXCLUDE_PATTERNS = ["site-packages", ".venv", "venv", "virtualenv"]


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
        """Initialize the duplication detector."""
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

    def _build_exclude_patterns(self, exclude_patterns: Optional[List[str]]) -> List[str]:
        """Merge user-supplied and mandatory exclusion patterns."""
        result = ["site-packages", "node_modules", ".venv", "venv", "vendor"] if exclude_patterns is None else list(exclude_patterns)
        for pattern in _MANDATORY_ENV_EXCLUDE_PATTERNS:
            if pattern not in result:
                result.append(pattern)
        return result

    def _run_detection(
        self,
        project_folder: str,
        construct_type: str,
        min_similarity: float,
        min_lines: int,
        max_constructs: int,
        exclude_patterns: List[str],
        start_time: float,
    ) -> Dict[str, Any]:
        """Inner detection logic, separated from tracking/error handling."""
        self._validate_parameters(min_similarity, min_lines, max_constructs)
        pattern = self._get_construct_pattern(construct_type)
        all_matches = self._find_constructs(project_folder, pattern, max_constructs, exclude_patterns)

        if not all_matches:
            return self._empty_result(construct_type, time.time() - start_time)

        duplication_groups = self.group_duplicates(all_matches, min_similarity, min_lines)
        suggestions = self.generate_refactoring_suggestions(duplication_groups, construct_type)
        stats = self._calculate_statistics(all_matches, duplication_groups, suggestions)
        return self._format_result(all_matches, duplication_groups, suggestions, stats, time.time() - start_time)

    def find_duplication(
        self,
        project_folder: str,
        construct_type: str = "function_definition",
        min_similarity: float = DeduplicationDefaults.MIN_SIMILARITY,
        min_lines: int = DeduplicationDefaults.MIN_LINES,
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
        exclude_patterns = self._build_exclude_patterns(exclude_patterns)

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

        with track_operation(
            "find_duplication", OperationType.FIND_DUPLICATION, metadata={"language": self.language, "construct_type": construct_type}
        ) as tracker:
            return self._tracked_detection(project_folder, construct_type, min_similarity, min_lines, max_constructs, exclude_patterns, start_time, tracker)

    def _tracked_detection(
        self,
        project_folder: str,
        construct_type: str,
        min_similarity: float,
        min_lines: int,
        max_constructs: int,
        exclude_patterns: List[str],
        start_time: float,
        tracker: Any,
    ) -> Dict[str, Any]:
        """Run detection inside a tracking context with error logging."""
        try:
            result = self._run_detection(project_folder, construct_type, min_similarity, min_lines, max_constructs, exclude_patterns, start_time)
            summary = result.get("summary", {})
            tracker.lines_analyzed = summary.get("total_constructs", 0)
            tracker.matches_found = summary.get("duplicate_groups", 0)
            self.logger.info(
                "find_duplication_completed",
                execution_time_seconds=round(time.time() - start_time, FormattingDefaults.ROUNDING_PRECISION),
                duplicate_groups=tracker.matches_found,
                status="success",
            )
            return result
        except Exception as e:
            self.logger.error(
                "find_duplication_failed",
                execution_time_seconds=round(time.time() - start_time, FormattingDefaults.ROUNDING_PRECISION),
                error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
                status="failed",
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

    _JS_TS_PATTERNS: Dict[str, str] = {
        "function_definition": "const $NAME = $$$",
        "arrow_function": "const $NAME = ($$$) => $$$",
        "traditional_function": "function $NAME($$$) { $$$ }",
        "method_definition": "$NAME($$$) { $$$ }",
    }
    _C_LIKE_PATTERNS: Dict[str, str] = {
        "function_definition": "$TYPE $NAME($$$) { $$$ }",
        "method_definition": "$TYPE $NAME($$$) { $$$ }",
    }
    _DEFAULT_PATTERNS: Dict[str, str] = {
        "function_definition": "def $NAME($$$)",
        "class_definition": "class $NAME",
        "method_definition": "def $NAME($$$)",
    }
    _JS_TS_LANGS = frozenset(["javascript", "typescript", "jsx", "tsx"])
    _C_LIKE_LANGS = frozenset(["java", "csharp", "cpp", "c"])

    def _get_construct_pattern(self, construct_type: str) -> str:
        """Get ast-grep pattern for the construct type and language."""
        lang = self.language.lower()
        patterns = dict(self._DEFAULT_PATTERNS)

        if lang in self._JS_TS_LANGS:
            js_pattern = self._JS_TS_PATTERNS.get(construct_type, "const $NAME = $$$")
            patterns[construct_type] = js_pattern
        elif lang in self._C_LIKE_LANGS:
            patterns.update(self._C_LIKE_PATTERNS)

        return patterns.get(construct_type, patterns["function_definition"])

    def _apply_exclude_patterns(self, all_matches: List[Dict[str, Any]], exclude_patterns: List[str]) -> List[Dict[str, Any]]:
        """Filter matches by excluded path patterns, logging if any were removed."""
        if not exclude_patterns:
            return all_matches
        before = len(all_matches)
        filtered = [m for m in all_matches if not any(p in m.get("file", "") for p in exclude_patterns)]
        if before > len(filtered):
            self.logger.info("excluded_matches", total_before=before, total_after=len(filtered), excluded_count=before - len(filtered))
        return filtered

    def _find_constructs(self, project_folder: str, pattern: str, max_constructs: int, exclude_patterns: List[str]) -> List[Dict[str, Any]]:
        """Find all constructs matching the pattern."""
        args = ["--pattern", pattern, "--lang", self.language]
        self.logger.info("searching_constructs", pattern=pattern, language=self.language)

        stream_limit = max_constructs if max_constructs > 0 else 0
        all_matches = list(
            stream_ast_grep_results(
                "run",
                args + ["--json=stream", project_folder],
                max_results=stream_limit,
                progress_interval=StreamDefaults.PROGRESS_INTERVAL,
            )
        )

        all_matches = self._apply_exclude_patterns(all_matches, exclude_patterns)

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
            return self._hybrid.estimate_similarity(code1, code2)
        if self.similarity_mode == "minhash":
            return self._minhash.estimate_similarity(code1, code2)
        return self.calculate_similarity_precise(code1, code2)

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
                normalized_line = " " * min(indent_count, IndentationDefaults.SPACES_PER_LEVEL) + line.lstrip()
                lines.append(normalized_line)
        return "\n".join(lines)

    def group_duplicates(self, matches: List[Dict[str, Any]], min_similarity: float, min_lines: int) -> List[List[Dict[str, Any]]]:
        """Group similar code constructs together."""
        if not matches:
            return []

        filtered_matches = [m for m in matches if len(m.get("text", "").split("\n")) >= min_lines]

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
            hash_val = self._calculate_structure_hash(match.get("text", ""))
            buckets.setdefault(hash_val, []).append(match)
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

    def _collect_similar_items(
        self, anchor: Dict[str, Any], candidates: List[Dict[str, Any]], candidate_indices: List[int], used: set, min_similarity: float
    ) -> List[int]:
        """Return indices (into candidates) that are similar to anchor and not yet used."""
        matches = []
        for offset, item in enumerate(candidates):
            j = candidate_indices[offset]
            if j in used:
                continue
            if self.calculate_similarity(anchor.get("text", ""), item.get("text", "")) >= min_similarity:
                matches.append(offset)
        return matches

    def _find_similar_in_bucket(self, bucket: List[Dict[str, Any]], min_similarity: float) -> List[List[Dict[str, Any]]]:
        """Find similar items within a bucket."""
        groups = []
        used: set = set()

        for i, item1 in enumerate(bucket):
            if i in used:
                continue
            used.add(i)
            rest = bucket[i + 1 :]
            rest_indices = list(range(i + 1, len(bucket)))
            similar_offsets = self._collect_similar_items(item1, rest, rest_indices, used, min_similarity)
            if not similar_offsets:
                continue
            group = [item1]
            for offset in similar_offsets:
                j = rest_indices[offset]
                used.add(j)
                group.append(rest[offset])
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
                item_to_groups.setdefault(key, []).append(idx)
        return item_to_groups

    def _add_unique_items(self, target: List[Dict[str, Any]], source: List[Dict[str, Any]]) -> None:
        """Add unique items from source to target."""
        for item in source:
            if not any(self._items_equal(item, existing) for existing in target):
                target.append(item)

    def _connected_group_indices(self, current_idx: int, groups: List[List[Dict[str, Any]]], item_to_groups: Dict[str, List[int]], used_groups: set[int]) -> List[int]:
        """Return group indices connected to current_idx that haven't been visited."""
        candidates: List[int] = []
        for item in groups[current_idx]:
            candidates.extend(item_to_groups.get(self._get_item_key(item), []))
        return [ci for ci in candidates if ci not in used_groups]

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
        for connected_idx in self._connected_group_indices(current_idx, groups, item_to_groups, used_groups):
            to_merge.append(connected_idx)
            used_groups.add(connected_idx)
            self._add_unique_items(merged_group, groups[connected_idx])

    def _expand_connected_group(
        self, start_idx: int, groups: List[List[Dict[str, Any]]], item_to_groups: Dict[str, List[int]], used_groups: set
    ) -> List[Dict[str, Any]]:
        """BFS-expand all groups connected to start_idx, returning merged items."""
        merged_group = groups[start_idx].copy()
        to_merge = [start_idx]
        while to_merge:
            current_idx = to_merge.pop()
            self._process_group_connections(current_idx, groups, item_to_groups, used_groups, to_merge, merged_group)
        return merged_group

    def _merge_overlapping_groups(self, groups: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """Merge groups that share common members."""
        if not groups:
            return []
        item_to_groups = self._build_item_to_groups_map(groups)
        merged = []
        used_groups: set = set()
        for idx in range(len(groups)):
            if idx in used_groups:
                continue
            used_groups.add(idx)
            merged.append(self._expand_connected_group(idx, groups, item_to_groups, used_groups))
        return merged

    def _items_equal(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Check if two match items are the same."""
        return item1.get("file") == item2.get("file") and item1.get("range", {}).get("start", {}).get("line") == item2.get("range", {}).get(
            "start", {}
        ).get("line")

    def _group_locations(self, group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract file/line location entries from a group."""
        return [{"file": item.get("file", ""), "line": item.get("range", {}).get("start", {}).get("line", 0) + 1} for item in group]

    def _build_suggestion(self, idx: int, group: List[Dict[str, Any]], construct_type: str) -> Dict[str, Any]:
        """Build a single refactoring suggestion for a duplication group."""
        lines = len(group[0].get("text", "").split("\n"))
        total_lines = lines * len(group)
        return {
            "group_id": idx + 1,
            "duplicate_count": len(group),
            "lines_per_duplicate": lines,
            "total_duplicated_lines": total_lines,
            "potential_line_savings": total_lines - lines,
            "refactoring_strategy": self._determine_refactoring_strategy(group, construct_type),
            "locations": self._group_locations(group),
        }

    def generate_refactoring_suggestions(self, duplication_groups: List[List[Dict[str, Any]]], construct_type: str) -> List[Dict[str, Any]]:
        """Generate refactoring suggestions for duplication groups."""
        return [self._build_suggestion(idx, group, construct_type) for idx, group in enumerate(duplication_groups) if len(group) >= 2]

    def _determine_refactoring_strategy(self, group: List[Dict[str, Any]], construct_type: str) -> Dict[str, str]:
        """Determine the best refactoring strategy for a duplication group."""
        # Analyze the code to determine strategy
        first_text = group[0].get("text", "")
        line_count = len(first_text.split("\n"))

        # Simple heuristics for strategy selection
        if construct_type == "function_definition":
            if line_count < DetectorDefaults.UTILITY_FUNCTION_LINE_THRESHOLD:
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
                "analysis_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
            "duplication_groups": [],
            "refactoring_suggestions": [],
            "message": f"No {construct_type} instances found in the project",
        }

    def _format_group_instances(self, group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format match instances within a duplication group."""
        instances = []
        for match in group:
            start_line = match.get("range", {}).get("start", {}).get("line", 0) + 1
            end_line = match.get("range", {}).get("end", {}).get("line", 0) + 1
            instances.append({
                "file": match.get("file", ""),
                "lines": f"{start_line}-{end_line}",
                "code_preview": match.get("text", "")[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            })
        return instances

    def _format_group(self, idx: int, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format a single duplication group for output."""
        similarity = (
            round(self.calculate_similarity(group[0].get("text", ""), group[1].get("text", "")), FormattingDefaults.ROUNDING_PRECISION)
            if len(group) >= 2
            else 1.0
        )
        return {"group_id": idx + 1, "similarity_score": similarity, "instances": self._format_group_instances(group)}

    def _format_result(
        self,
        all_matches: List[Dict[str, Any]],
        duplication_groups: List[List[Dict[str, Any]]],
        suggestions: List[Dict[str, Any]],
        stats: Dict[str, Any],
        execution_time: float,
    ) -> Dict[str, Any]:
        """Format the final result."""
        formatted_groups = [self._format_group(idx, group) for idx, group in enumerate(duplication_groups)]
        return {
            "summary": {**stats, "analysis_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION)},
            "duplication_groups": formatted_groups,
            "refactoring_suggestions": suggestions,
            "message": f"Found {stats['duplicate_groups']} duplication group(s) with potential to save {stats['potential_line_savings']} lines",
        }
