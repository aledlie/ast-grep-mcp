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
        id: Unique rule identifier (e.g., 'no-console-log')
        language: Target language (python, typescript, javascript, java, etc.)
        severity: Severity level ('error', 'warning', or 'info')
        message: Human-readable error message shown when rule is violated
        pattern: ast-grep pattern to match (e.g., 'console.log($$$)')
        note: Optional additional note or explanation
        fix: Optional replacement pattern or fix suggestion
        constraints: Optional additional ast-grep constraints
    """
    id: str
    language: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    pattern: str
    note: Optional[str] = None
    fix: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to ast-grep YAML format.

        Returns:
            Dictionary ready for YAML serialization in ast-grep format
        """
        yaml_dict: Dict[str, Any] = {
            'id': self.id,
            'language': self.language,
            'severity': self.severity,
            'message': self.message,
        }

        # Add rule configuration
        rule_config: Dict[str, Any] = {
            'pattern': self.pattern
        }

        # Add constraints if present
        if self.constraints:
            rule_config.update(self.constraints)

        yaml_dict['rule'] = rule_config

        # Add optional fields
        if self.note:
            yaml_dict['note'] = self.note
        if self.fix:
            yaml_dict['fix'] = self.fix

        return yaml_dict


@dataclass
class RuleTemplate:
    """Pre-built rule template.

    Attributes:
        id: Template identifier
        name: Human-readable name
        description: What the rule checks for
        language: Target language
        severity: Default severity level
        pattern: ast-grep pattern
        message: Error message
        note: Optional additional explanation
        fix: Optional fix suggestion
        category: Rule category (general, security, performance, style)
    """
    id: str
    name: str
    description: str
    language: str
    severity: str
    pattern: str
    message: str
    note: Optional[str] = None
    fix: Optional[str] = None
    category: str = 'general'


@dataclass
class RuleValidationResult:
    """Result of rule validation.

    Attributes:
        is_valid: Whether the rule is valid
        errors: List of error messages (blocking issues)
        warnings: List of warning messages (non-blocking issues)
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RuleViolation:
    """Single violation of a linting rule.

    Attributes:
        file: Absolute path to file containing violation
        line: Line number where violation occurs (1-indexed)
        column: Column number (1-indexed)
        end_line: End line of violation range
        end_column: End column of violation range
        severity: 'error', 'warning', or 'info'
        rule_id: ID of the rule that was violated
        message: Human-readable error message
        code_snippet: Actual code that violated the rule
        fix_suggestion: Optional fix suggestion from rule definition
        meta_vars: Optional metavariables captured by pattern
    """
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    severity: str
    rule_id: str
    message: str
    code_snippet: str
    fix_suggestion: Optional[str] = None
    meta_vars: Optional[Dict[str, str]] = None


@dataclass
class RuleSet:
    """Collection of linting rules with metadata.

    Attributes:
        name: Rule set identifier ('recommended', 'security', etc.)
        description: Human-readable description
        rules: List of LintingRule objects in this set
        priority: Execution priority (higher = run first)
    """
    name: str
    description: str
    rules: List[LintingRule]
    priority: int = 0


@dataclass
class EnforcementResult:
    """Complete results from standards enforcement scan.

    Attributes:
        summary: Summary statistics
        violations: All violations found
        violations_by_file: Violations grouped by file path
        violations_by_severity: Violations grouped by severity level
        violations_by_rule: Violations grouped by rule ID
        rules_executed: List of rule IDs that were executed
        execution_time_ms: Total execution time in milliseconds
        files_scanned: Number of files scanned
    """
    summary: Dict[str, Any]
    violations: List[RuleViolation]
    violations_by_file: Dict[str, List[RuleViolation]]
    violations_by_severity: Dict[str, List[RuleViolation]]
    violations_by_rule: Dict[str, List[RuleViolation]]
    rules_executed: List[str]
    execution_time_ms: int
    files_scanned: int


@dataclass
class RuleExecutionContext:
    """Context for executing rules (internal use).

    Attributes:
        project_folder: Absolute path to project
        language: Target language
        include_patterns: File patterns to include
        exclude_patterns: File patterns to exclude
        max_violations: Stop after this many violations (0 = unlimited)
        max_threads: Number of parallel threads
        logger: Structured logger instance
    """
    project_folder: str
    language: str
    include_patterns: List[str]
    exclude_patterns: List[str]
    max_violations: int
    max_threads: int
    logger: Any  # structlog logger