"""Utilities module for ast-grep MCP server.

This module provides various utility functions for:
- Code generation templates
- Text formatting and display
- String manipulation and similarity
- Configuration validation
"""

# Template utilities
from .templates import (
    # Templates
    PYTHON_CLASS_TEMPLATE,
    JAVA_METHOD_TEMPLATE,
    TYPESCRIPT_CLASS_TEMPLATE,
    TYPESCRIPT_FUNCTION_TEMPLATE,
    TYPESCRIPT_ASYNC_FUNCTION_TEMPLATE,
    TYPESCRIPT_ARROW_FUNCTION_TEMPLATE,
    JAVASCRIPT_FUNCTION_TEMPLATE,
    JAVASCRIPT_ASYNC_FUNCTION_TEMPLATE,
    JAVASCRIPT_ARROW_FUNCTION_TEMPLATE,
    # Python formatting
    format_python_class,
    # Java formatting
    format_java_code,
    format_java_method,
    # TypeScript formatting
    format_typescript_class,
    format_typescript_function,
    # JavaScript formatting
    format_javascript_function,
)

# Formatting utilities
from .formatters import (
    format_matches_as_text,
    format_diff_with_colors,
    generate_before_after_example,
    visualize_complexity,
    generate_file_diff,
    generate_multi_file_diff,
    FileDiff,
    DiffPreview,
)

# Text utilities
from .text import (
    normalize_code,
    calculate_similarity,
)

# Validation utilities
from .validation import (
    validate_config_file,
)

__all__ = [
    # Templates
    "PYTHON_CLASS_TEMPLATE",
    "JAVA_METHOD_TEMPLATE",
    "TYPESCRIPT_CLASS_TEMPLATE",
    "TYPESCRIPT_FUNCTION_TEMPLATE",
    "TYPESCRIPT_ASYNC_FUNCTION_TEMPLATE",
    "TYPESCRIPT_ARROW_FUNCTION_TEMPLATE",
    "JAVASCRIPT_FUNCTION_TEMPLATE",
    "JAVASCRIPT_ASYNC_FUNCTION_TEMPLATE",
    "JAVASCRIPT_ARROW_FUNCTION_TEMPLATE",
    # Template formatting functions
    "format_python_class",
    "format_java_code",
    "format_java_method",
    "format_typescript_class",
    "format_typescript_function",
    "format_javascript_function",
    # Formatters
    "format_matches_as_text",
    "format_diff_with_colors",
    "generate_before_after_example",
    "visualize_complexity",
    "generate_file_diff",
    "generate_multi_file_diff",
    "FileDiff",
    "DiffPreview",
    # Text utilities
    "normalize_code",
    "calculate_similarity",
    # Validation
    "validate_config_file",
]