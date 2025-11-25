"""
Deduplication feature module.

This module provides comprehensive code deduplication detection and refactoring
capabilities for the ast-grep MCP server.
"""

from .detector import DuplicationDetector
from .analyzer import PatternAnalyzer, VariationCategory, VariationSeverity
from .generator import CodeGenerator
from .ranker import DuplicationRanker

__all__ = [
    # Core classes
    "DuplicationDetector",
    "PatternAnalyzer",
    "CodeGenerator",
    "DuplicationRanker",

    # Constants
    "VariationCategory",
    "VariationSeverity",
]

# Version info
__version__ = "1.0.0"