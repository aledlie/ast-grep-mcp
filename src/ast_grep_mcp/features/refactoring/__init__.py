"""Refactoring assistants for intelligent code transformations.

This module provides tools for automated refactoring operations including:
- Function extraction with parameter detection
- Symbol renaming across codebases
- Code style conversions
- Conditional logic simplification
- Batch refactoring operations
"""

from .analyzer import CodeSelectionAnalyzer
from .extractor import FunctionExtractor
from .renamer import SymbolRenamer
from .rename_coordinator import RenameCoordinator

__all__ = [
    "CodeSelectionAnalyzer",
    "FunctionExtractor",
    "SymbolRenamer",
    "RenameCoordinator",
]
