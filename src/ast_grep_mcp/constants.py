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

    # Timeout configuration for parallel operations
    DEFAULT_TIMEOUT_PER_CANDIDATE_SECONDS = 30  # 30 seconds per candidate
    MAX_TIMEOUT_SECONDS = 300  # 5 minutes max total timeout

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
    CACHE_KEY_LENGTH = 16  # Length of truncated SHA256 hash for cache keys


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
    SIGTERM_RETURN_CODE = -15  # Return code for SIGTERM signal


class ValidationDefaults:
    """Defaults for validation operations."""

    MAX_FILE_SIZE_MB = 10  # Skip files larger than this
    SYNTAX_CHECK_TIMEOUT_SECONDS = 5


class FileConstants:
    """Constants for file operations."""

    BYTES_PER_KB = 1024
    BYTES_PER_MB = 1024 * 1024
    BYTES_PER_GB = 1024 * 1024 * 1024
    LINE_PREVIEW_LENGTH = 100  # Maximum characters to show in line preview


class DeduplicationDefaults:
    """Defaults for deduplication analysis."""

    MIN_SIMILARITY = 0.8  # Minimum similarity threshold (0-1)
    MIN_LINES = 5  # Minimum lines to consider for duplication

    # Scoring weights (must sum to 1.0)
    SAVINGS_WEIGHT = 0.40
    COMPLEXITY_WEIGHT = 0.20
    RISK_WEIGHT = 0.25
    EFFORT_WEIGHT = 0.15

    # Regression thresholds for performance benchmarks
    REGRESSION_PATTERN_ANALYSIS = 0.15  # 15% slowdown allowed
    REGRESSION_CODE_GENERATION = 0.10   # 10% slowdown allowed
    REGRESSION_FULL_WORKFLOW = 0.20     # 20% slowdown allowed
    REGRESSION_SCORING = 0.05            # 5% slowdown allowed
    REGRESSION_TEST_COVERAGE = 0.15     # 15% slowdown allowed


class HybridSimilarityDefaults:
    """Defaults for hybrid two-stage similarity pipeline.

    Scientific basis: TACC (Token and AST-based Code Clone detector)
    from ICSE 2023 demonstrates that combining MinHash filtering with
    AST verification yields optimal precision/recall balance.
    """

    # Stage 1: MinHash filter threshold for early exit
    # Code pairs below this threshold skip Stage 2 (AST verification)
    MINHASH_EARLY_EXIT_THRESHOLD = 0.5

    # Stage 2 weights for combining MinHash and AST similarity
    # Must sum to 1.0. AST gets higher weight due to structural precision.
    MINHASH_WEIGHT = 0.4
    AST_WEIGHT = 0.6

    # Minimum token count to use hybrid approach
    # Very short code snippets may not benefit from AST analysis
    MIN_TOKENS_FOR_AST = 10

    # Maximum code length (lines) for AST analysis
    # Very long code may be too expensive for detailed AST comparison
    MAX_LINES_FOR_FULL_AST = 500

    # AST tree edit distance normalization factor
    # Used to convert raw edit distance to 0-1 similarity score
    TREE_EDIT_DISTANCE_NORMALIZATION = 100


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
    MAX_BREADCRUMBS = 50  # Maximum Sentry breadcrumbs to keep


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
