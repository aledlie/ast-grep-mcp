"""Shared constants across the ast-grep-mcp codebase.

This module centralizes magic numbers and configuration values
to improve maintainability and reduce code duplication.
"""
import os


class ComplexityDefaults:
    """Default thresholds for complexity analysis."""

    CYCLOMATIC_THRESHOLD = 10
    COGNITIVE_THRESHOLD = 15
    NESTING_THRESHOLD = 4
    LENGTH_THRESHOLD = 50


class ParallelProcessing:
    """Parallel processing configuration."""

    DEFAULT_WORKERS = 4
    MAX_WORKERS = 16

    @staticmethod
    def get_optimal_workers(max_threads: int = 0) -> int:
        """Calculate optimal worker count based on CPU cores.

        Args:
            max_threads: Maximum threads to use (0 = auto-detect)

        Returns:
            Optimal number of worker threads (1 to MAX_WORKERS)
        """
        if max_threads > 0:
            return min(max_threads, ParallelProcessing.MAX_WORKERS)

        cpu_count = os.cpu_count() or 4
        # Reserve 1 core for system, cap at MAX_WORKERS
        return max(1, min(cpu_count - 1, ParallelProcessing.MAX_WORKERS))


class CacheDefaults:
    """Cache configuration defaults."""

    TTL_SECONDS = 3600  # 1 hour
    MAX_SIZE_MB = 100
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
    DEFAULT_CACHE_SIZE = 100  # Number of cached items


class FilePatterns:
    """Common file patterns for analysis."""

    DEFAULT_EXCLUDE = [
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/venv/**",
        "**/.venv/**",
        "**/site-packages/**",
        "**/dist/**",
        "**/build/**",
        "**/.git/**",
        "**/coverage/**",
    ]

    TEST_EXCLUDE = [
        "**/test*/**",
        "**/*test*",
        "**/tests/**",
        "**/*_test.py",
        "**/test_*.py",
    ]


class StreamDefaults:
    """Defaults for streaming operations."""

    DEFAULT_TIMEOUT_MS = 120000  # 2 minutes
    MAX_TIMEOUT_MS = 600000  # 10 minutes
    PROGRESS_INTERVAL = 100  # Log progress every N matches


class ValidationDefaults:
    """Defaults for validation operations."""

    MAX_FILE_SIZE_MB = 10  # Skip files larger than this
    SYNTAX_CHECK_TIMEOUT_SECONDS = 5


class DeduplicationDefaults:
    """Defaults for deduplication analysis."""

    MIN_SIMILARITY = 0.8  # Minimum similarity threshold (0-1)
    MIN_LINES = 5  # Minimum lines to consider for duplication

    # Scoring weights (must sum to 1.0)
    SAVINGS_WEIGHT = 0.40
    COMPLEXITY_WEIGHT = 0.20
    RISK_WEIGHT = 0.25
    EFFORT_WEIGHT = 0.15


class SecurityScanDefaults:
    """Defaults for security scanning."""

    MAX_ISSUES = 100  # Maximum issues to return
    DEFAULT_SEVERITY_THRESHOLD = "low"  # Minimum severity to report

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5


class CodeQualityDefaults:
    """Defaults for code quality analysis."""

    # Code smell thresholds
    LONG_FUNCTION_LINES = 50
    PARAMETER_COUNT = 5
    NESTING_DEPTH = 4
    CLASS_LINES = 300
    CLASS_METHODS = 20

    # Magic numbers to ignore
    ALLOWED_MAGIC_NUMBERS = {0, 1, -1, 2, 10, 100, 1000}


class LoggingDefaults:
    """Logging configuration defaults."""

    DEFAULT_LEVEL = "INFO"
    MAX_LOG_SIZE_MB = 10
    BACKUP_COUNT = 5  # Number of log files to keep


# Language-specific extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "java": [".java"],
    "kotlin": [".kt", ".kts"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "php": [".php"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
    "csharp": [".cs"],
    "swift": [".swift"],
}

# Schema.org constants
SCHEMA_ORG_BASE_URL = "https://schema.org"
SCHEMA_ORG_CONTEXT = "https://schema.org"

# HTTP constants
DEFAULT_USER_AGENT = "ast-grep-mcp/1.0"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1
