"""Data models for code quality standards and linting rules."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RuleValidationError(Exception):
    """Raised when a linting rule validation fails."""
    pass


class RuleStorageError(Exception):
    """Raised when saving/loading rules fails."""
    pass


@dataclass
class LintingRule:
    """Represents a custom linting rule.

    Attributes:
        id: Unique identifier (e.g., 'no-console-log')
        message: Error message to display
        note: Additional context or explanation
        severity: 'error', 'warning', or 'info'
        language: Target language
        pattern: ast-grep pattern
        fix: Optional suggested fix
        fixDescription: Optional description of the fix
        metadata: Additional rule metadata
        tags: Optional tags for categorization
    """
    id: str
    message: str
    note: str
    severity: str
    language: str
    pattern: str
    fix: Optional[str] = None
    fixDescription: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to YAML-compatible dictionary."""
        yaml_dict: Dict[str, Any] = {
            'id': self.id,
            'message': self.message,
            'note': self.note,
            'severity': self.severity,
            'language': self.language,
        }

        # Add rule configuration
        rule_config: Dict[str, Any] = {
            'pattern': self.pattern
        }
        yaml_dict['rule'] = rule_config

        # Add optional fields
        if self.fix:
            yaml_dict['fix'] = self.fix
        if self.fixDescription:
            yaml_dict['fixDescription'] = self.fixDescription
        if self.metadata:
            yaml_dict['metadata'] = self.metadata
        if self.tags:
            yaml_dict['tags'] = self.tags

        return yaml_dict


@dataclass
class RuleTemplate:
    """Pre-built rule template.

    Attributes:
        id: Template identifier
        name: Human-readable name
        description: What the rule checks for
        pattern: ast-grep pattern
        message: Error message template
        severity: Default severity level
        languages: Supported languages
        category: Rule category
        fix: Optional fix pattern
        note: Additional context
    """
    id: str
    name: str
    description: str
    pattern: str
    message: str
    severity: str
    languages: List[str]
    category: str
    fix: Optional[str] = None
    note: Optional[str] = None


@dataclass
class RuleValidationResult:
    """Result of rule validation.

    Attributes:
        valid: Whether the rule is valid
        errors: List of validation errors
        warnings: List of validation warnings
        pattern_valid: Whether the pattern is valid ast-grep syntax
        id_valid: Whether the ID follows naming conventions
        severity_valid: Whether the severity is valid
        language_valid: Whether the language is supported
    """
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    pattern_valid: bool = True
    id_valid: bool = True
    severity_valid: bool = True
    language_valid: bool = True

    def add_error(self, error: str) -> None:
        """Add an error and mark as invalid."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning (doesn't affect validity)."""
        self.warnings.append(warning)


@dataclass
class RuleViolation:
    """Single violation of a linting rule.

    Attributes:
        rule_id: ID of the violated rule
        file_path: Path to file with violation
        line_number: Line number of violation
        column_number: Column number of violation
        message: Violation message
        severity: Violation severity
        code_snippet: The violating code
        suggested_fix: Optional suggested fix
        context_before: Lines before violation
        context_after: Lines after violation
    """
    rule_id: str
    file_path: str
    line_number: int
    column_number: int
    message: str
    severity: str
    code_snippet: str
    suggested_fix: Optional[str] = None
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)

    def format_display(self) -> str:
        """Format violation for display."""
        lines = [
            f"{self.file_path}:{self.line_number}:{self.column_number}",
            f"  {self.severity.upper()}: {self.message}",
            f"  {self.line_number} | {self.code_snippet}"
        ]
        if self.suggested_fix:
            lines.append(f"  Fix: {self.suggested_fix}")
        return '\n'.join(lines)


@dataclass
class RuleSet:
    """Collection of linting rules with metadata.

    Attributes:
        name: Rule set name
        description: Rule set description
        rules: List of rules in the set
        enabled: Whether the rule set is enabled
        languages: Supported languages
        version: Rule set version
        author: Rule set author
    """
    name: str
    description: str
    rules: List[LintingRule]
    enabled: bool = True
    languages: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: Optional[str] = None


@dataclass
class EnforcementResult:
    """Complete results from standards enforcement scan.

    Attributes:
        violations: List of all violations found
        total_violations: Total count of violations
        violations_by_severity: Count by severity
        violations_by_rule: Count by rule ID
        violations_by_file: Count by file
        files_scanned: Number of files scanned
        rules_applied: Number of rules applied
        scan_duration_ms: Scan duration in milliseconds
    """
    violations: List[RuleViolation]
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations_by_rule: Dict[str, int]
    violations_by_file: Dict[str, int]
    files_scanned: int
    rules_applied: int
    scan_duration_ms: float


@dataclass
class RuleExecutionContext:
    """Context for executing rules (internal use).

    Attributes:
        project_folder: Root folder of project
        language: Language being checked
        rules: Rules to execute
        exclude_patterns: Patterns to exclude
        include_patterns: Patterns to include
        max_violations: Maximum violations to report
        auto_fix: Whether to auto-fix violations
    """
    project_folder: str
    language: str
    rules: List[LintingRule]
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    max_violations: int = 100
    auto_fix: bool = False