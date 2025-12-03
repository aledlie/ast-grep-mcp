"""Pattern equivalence lookup implementation.

This module provides functionality to find equivalent patterns
across programming languages.
"""

import time
from typing import Any, Dict, List, Optional

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.cross_language.pattern_database import (
    PATTERN_CATEGORIES,
    PATTERN_DATABASE,
)
from ast_grep_mcp.models.cross_language import (
    SUPPORTED_LANGUAGES,
    PatternEquivalence,
    PatternEquivalenceResult,
    PatternExample,
)

logger = get_logger(__name__)


def _create_pattern_equivalence(
    pattern_id: str,
    pattern_data: Dict[str, Any],
    target_languages: Optional[List[str]] = None,
) -> PatternEquivalence:
    """Create a PatternEquivalence from database entry.

    Args:
        pattern_id: Pattern identifier
        pattern_data: Pattern data from database
        target_languages: Optional filter for target languages

    Returns:
        PatternEquivalence object
    """
    examples = []
    examples_data = pattern_data.get("examples", {})

    for lang, ex_data in examples_data.items():
        if target_languages and lang not in target_languages:
            continue

        if isinstance(ex_data, dict):
            examples.append(
                PatternExample(
                    language=lang,
                    code=ex_data.get("code", ""),
                    description=ex_data.get("description", ""),
                    notes=ex_data.get("notes", []),
                )
            )
        elif isinstance(ex_data, str):
            examples.append(
                PatternExample(
                    language=lang,
                    code=ex_data,
                    description="",
                    notes=[],
                )
            )

    # Build complexity comparison
    complexity_comparison = {}
    for ex in examples:
        lines = len(ex.code.strip().split("\n"))
        if lines <= 2:
            complexity_comparison[ex.language] = "simple"
        elif lines <= 5:
            complexity_comparison[ex.language] = "moderate"
        else:
            complexity_comparison[ex.language] = "complex"

    return PatternEquivalence(
        pattern_id=pattern_id,
        concept=pattern_data.get("concept", ""),
        category=pattern_data.get("category", ""),
        description=pattern_data.get("description", ""),
        examples=examples,
        related_patterns=pattern_data.get("related_patterns", []),
        complexity_comparison=complexity_comparison,
    )


def _fuzzy_match_pattern(query: str) -> List[str]:
    """Find pattern IDs that match a fuzzy query.

    Args:
        query: Search query

    Returns:
        List of matching pattern IDs
    """
    query_lower = query.lower()
    matches = []

    # Direct concept matching
    for pattern_id, pattern_data in PATTERN_DATABASE.items():
        concept = pattern_data.get("concept", "").lower()
        description = pattern_data.get("description", "").lower()

        # Check for match in concept, description, or pattern_id
        if query_lower in concept or query_lower in description or query_lower in pattern_id.lower():
            matches.append(pattern_id)

    # If no matches, try word-by-word matching
    if not matches:
        query_words = query_lower.split()
        for pattern_id, pattern_data in PATTERN_DATABASE.items():
            concept = pattern_data.get("concept", "").lower()
            description = pattern_data.get("description", "").lower()
            searchable = f"{concept} {description} {pattern_id}".lower()

            # Check if any query word matches
            for word in query_words:
                if len(word) > 2 and word in searchable:
                    matches.append(pattern_id)
                    break

    return list(set(matches))


def _get_suggestions(
    found_patterns: List[str],
    category: Optional[str] = None,
) -> List[str]:
    """Get pattern suggestions based on found patterns.

    Args:
        found_patterns: List of found pattern IDs
        category: Optional category filter

    Returns:
        List of suggestion strings
    """
    suggestions = []

    # Suggest related patterns
    related = set()
    for pattern_id in found_patterns:
        pattern = PATTERN_DATABASE.get(pattern_id, {})
        related.update(pattern.get("related_patterns", []))

    for rel_id in related:
        if rel_id not in found_patterns and rel_id in PATTERN_DATABASE:
            rel_pattern = PATTERN_DATABASE[rel_id]
            suggestions.append(f"Related: {rel_id} - {rel_pattern.get('concept', '')}")

    # Suggest category exploration
    if category:
        category_patterns = [pid for pid, p in PATTERN_DATABASE.items() if p.get("category") == category and pid not in found_patterns]
        if category_patterns[:3]:
            suggestions.append(f"More in '{category}': {', '.join(category_patterns[:3])}")

    # Suggest categories to explore
    if not category and len(found_patterns) < 3:
        suggestions.append(f"Try searching by category: {', '.join(PATTERN_CATEGORIES[:4])}")

    return suggestions[:5]  # Limit suggestions


def find_language_equivalents_impl(
    pattern_description: str,
    source_language: Optional[str] = None,
    target_languages: Optional[List[str]] = None,
) -> PatternEquivalenceResult:
    """Find equivalent patterns across languages.

    Args:
        pattern_description: Description of the pattern to find
        source_language: Optional source language to highlight
        target_languages: List of target languages to include

    Returns:
        PatternEquivalenceResult with found equivalences
    """
    start_time = time.time()

    # Validate source language
    if source_language and source_language not in SUPPORTED_LANGUAGES:
        logger.warning(
            "unsupported_source_language",
            language=source_language,
            supported=SUPPORTED_LANGUAGES,
        )

    # Default target languages
    if not target_languages:
        target_languages = ["python", "typescript", "javascript", "java", "go", "rust"]

    # Filter to supported languages
    target_languages = [lang for lang in target_languages if lang in SUPPORTED_LANGUAGES]

    # Find matching patterns
    pattern_ids = _fuzzy_match_pattern(pattern_description)

    logger.info(
        "pattern_search_results",
        query=pattern_description,
        found_count=len(pattern_ids),
    )

    # Build equivalences
    equivalences = []
    for pattern_id in pattern_ids:
        pattern_data = PATTERN_DATABASE.get(pattern_id)
        if pattern_data:
            equiv = _create_pattern_equivalence(
                pattern_id,
                pattern_data,
                target_languages,
            )
            equivalences.append(equiv)

    # Get suggestions
    categories = list(set(PATTERN_DATABASE.get(pid, {}).get("category") for pid in pattern_ids))
    suggestions = _get_suggestions(
        pattern_ids,
        categories[0] if categories else None,
    )

    execution_time = int((time.time() - start_time) * 1000)

    return PatternEquivalenceResult(
        pattern_description=pattern_description,
        source_language=source_language,
        target_languages=target_languages,
        equivalences=equivalences,
        suggestions=suggestions,
        execution_time_ms=execution_time,
    )


def list_pattern_categories() -> List[Dict[str, Any]]:
    """List all available pattern categories with counts.

    Returns:
        List of category information dictionaries
    """
    category_counts: Dict[str, int] = {}
    category_examples: Dict[str, List[str]] = {}

    for pattern_id, pattern_data in PATTERN_DATABASE.items():
        category = pattern_data.get("category", "uncategorized")
        category_counts[category] = category_counts.get(category, 0) + 1

        if category not in category_examples:
            category_examples[category] = []
        if len(category_examples[category]) < 3:
            category_examples[category].append(pattern_id)

    return [
        {
            "category": cat,
            "count": count,
            "examples": category_examples.get(cat, []),
        }
        for cat, count in sorted(category_counts.items())
    ]


def get_pattern_details(pattern_id: str) -> Optional[PatternEquivalence]:
    """Get detailed information about a specific pattern.

    Args:
        pattern_id: Pattern identifier

    Returns:
        PatternEquivalence object or None if not found
    """
    pattern_data = PATTERN_DATABASE.get(pattern_id)
    if not pattern_data:
        return None

    return _create_pattern_equivalence(pattern_id, pattern_data)
