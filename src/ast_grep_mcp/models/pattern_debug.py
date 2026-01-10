"""Models for pattern debugging functionality.

This module provides dataclasses for pattern debugging results,
including AST comparison, metavariable validation, and suggestions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IssueSeverity(Enum):
    """Severity level for pattern issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(Enum):
    """Category of pattern issue."""

    METAVARIABLE = "metavariable"
    SYNTAX = "syntax"
    STRUCTURE = "structure"
    RELATIONAL = "relational"
    BEST_PRACTICE = "best_practice"


@dataclass
class PatternIssue:
    """An issue found in a pattern.

    Attributes:
        severity: How severe the issue is (error, warning, info)
        category: Category of the issue
        message: Description of the issue
        suggestion: How to fix the issue
        location: Where in the pattern the issue occurs (if applicable)
    """

    severity: IssueSeverity
    category: IssueCategory
    message: str
    suggestion: str
    location: Optional[str] = None


@dataclass
class MetavariableInfo:
    """Information about a metavariable in a pattern.

    Attributes:
        name: The metavariable name (e.g., $NAME, $$$ARGS)
        type: Type of metavariable (single, multi, non_capturing, unnamed)
        valid: Whether the metavariable syntax is valid
        occurrences: Number of times it appears in the pattern
        issue: Any issue with this metavariable
    """

    name: str
    type: str  # "single", "multi", "non_capturing", "unnamed"
    valid: bool
    occurrences: int = 1
    issue: Optional[str] = None


@dataclass
class AstComparison:
    """Comparison between pattern AST and code AST.

    Attributes:
        pattern_root_kind: Root node kind in pattern AST
        code_root_kind: Root node kind in code AST
        kinds_match: Whether the root kinds match
        pattern_structure: Simplified pattern AST structure
        code_structure: Simplified code AST structure
        structural_differences: List of structural differences found
    """

    pattern_root_kind: Optional[str]
    code_root_kind: Optional[str]
    kinds_match: bool
    pattern_structure: str
    code_structure: str
    structural_differences: List[str] = field(default_factory=list)


@dataclass
class MatchAttempt:
    """Result of attempting to match pattern against code.

    Attributes:
        matched: Whether any matches were found
        match_count: Number of matches found
        matches: List of match details
        partial_matches: Potential partial matches (for debugging)
    """

    matched: bool
    match_count: int = 0
    matches: List[Dict[str, Any]] = field(default_factory=list)
    partial_matches: List[str] = field(default_factory=list)


@dataclass
class PatternDebugResult:
    """Complete result of pattern debugging.

    Attributes:
        pattern: The original pattern
        code: The code being matched against
        language: The language used
        pattern_valid: Whether the pattern is syntactically valid
        pattern_ast: The pattern's AST structure
        code_ast: The code's AST structure
        ast_comparison: Comparison between pattern and code ASTs
        metavariables: Information about metavariables in the pattern
        issues: List of issues found
        suggestions: Prioritized list of fix suggestions
        match_attempt: Result of attempting to match
        execution_time_ms: Time taken to debug in milliseconds
    """

    pattern: str
    code: str
    language: str
    pattern_valid: bool
    pattern_ast: str
    code_ast: str
    ast_comparison: AstComparison
    metavariables: List[MetavariableInfo]
    issues: List[PatternIssue]
    suggestions: List[str]
    match_attempt: MatchAttempt
    execution_time_ms: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern": self.pattern,
            "code": self.code,
            "language": self.language,
            "pattern_valid": self.pattern_valid,
            "pattern_ast": self.pattern_ast,
            "code_ast": self.code_ast,
            "ast_comparison": {
                "pattern_root_kind": self.ast_comparison.pattern_root_kind,
                "code_root_kind": self.ast_comparison.code_root_kind,
                "kinds_match": self.ast_comparison.kinds_match,
                "pattern_structure": self.ast_comparison.pattern_structure,
                "code_structure": self.ast_comparison.code_structure,
                "structural_differences": self.ast_comparison.structural_differences,
            },
            "metavariables": [
                {
                    "name": mv.name,
                    "type": mv.type,
                    "valid": mv.valid,
                    "occurrences": mv.occurrences,
                    "issue": mv.issue,
                }
                for mv in self.metavariables
            ],
            "issues": [
                {
                    "severity": issue.severity.value,
                    "category": issue.category.value,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "location": issue.location,
                }
                for issue in self.issues
            ],
            "suggestions": self.suggestions,
            "match_attempt": {
                "matched": self.match_attempt.matched,
                "match_count": self.match_attempt.match_count,
                "matches": self.match_attempt.matches,
                "partial_matches": self.match_attempt.partial_matches,
            },
            "execution_time_ms": self.execution_time_ms,
        }
