"""Orphan code detection service.

This module provides functionality to detect orphan files and functions
in a codebase using dependency graph analysis and verification.
"""

import ast
import fnmatch
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.orphan import (
    DependencyEdge,
    DependencyGraph,
    OrphanAnalysisConfig,
    OrphanAnalysisResult,
    OrphanFile,
    OrphanFunction,
    VerificationStatus,
)


class OrphanDetector:
    """Detects orphan files and functions in a codebase."""

    def __init__(self, config: Optional[OrphanAnalysisConfig] = None) -> None:
        """Initialize the detector with optional configuration."""
        self.config = config or OrphanAnalysisConfig()
        self.logger = get_logger("orphan_detector")

    def analyze(self, project_folder: str) -> OrphanAnalysisResult:
        """Analyze a project for orphan code.

        Args:
            project_folder: Path to the project root

        Returns:
            OrphanAnalysisResult with detected orphans
        """
        start_time = time.time()
        base_path = Path(project_folder)

        self.logger.info("orphan_analysis_started", project=project_folder)

        # Phase 1: Build dependency graph
        graph = self._build_dependency_graph(base_path)

        # Phase 2: Identify entry points
        self._identify_entry_points(base_path, graph)

        # Phase 3: Find orphan files
        orphan_files = self._find_orphan_files(base_path, graph)

        # Phase 4: Verify orphans with grep
        if self.config.verify_with_grep:
            orphan_files = self._verify_orphans_with_grep(base_path, orphan_files)

        # Phase 5: Analyze function-level orphans (optional)
        orphan_functions: List[OrphanFunction] = []
        total_functions = 0
        if self.config.analyze_functions:
            orphan_functions, total_functions = self._find_orphan_functions(
                base_path, graph
            )

        elapsed_ms = int((time.time() - start_time) * 1000)

        result = OrphanAnalysisResult(
            orphan_files=orphan_files,
            orphan_functions=orphan_functions,
            total_files_analyzed=len(graph.files),
            total_functions_analyzed=total_functions,
            dependency_graph=graph,
            analysis_time_ms=elapsed_ms,
            config=self.config,
        )

        self.logger.info(
            "orphan_analysis_complete",
            orphan_files=len(orphan_files),
            orphan_functions=len(orphan_functions),
            total_files=len(graph.files),
            elapsed_ms=elapsed_ms,
        )

        return result

    def _build_dependency_graph(self, base_path: Path) -> DependencyGraph:
        """Build the import dependency graph for the project."""
        graph = DependencyGraph()

        # Collect all source files
        for pattern in self.config.include_patterns:
            # Handle glob patterns properly - extract just the file pattern
            # **/*.py -> *.py, src/**/*.py -> *.py
            if "**/" in pattern:
                glob_pattern = pattern.split("**/")[-1]
            else:
                glob_pattern = pattern

            for file_path in base_path.rglob(glob_pattern):
                if self._should_exclude(file_path, base_path):
                    continue
                if not file_path.is_file():
                    continue

                rel_path = str(file_path.relative_to(base_path))
                graph.files.add(rel_path)

                # Extract imports based on file type
                if file_path.suffix == ".py":
                    self._extract_python_imports(file_path, rel_path, base_path, graph)
                elif file_path.suffix in (".ts", ".js", ".tsx", ".jsx"):
                    self._extract_js_imports(file_path, rel_path, base_path, graph)

        self.logger.debug("dependency_graph_built", files=len(graph.files), edges=len(graph.edges))
        return graph

    def _should_exclude(self, file_path: Path, base_path: Path) -> bool:
        """Check if a file should be excluded from analysis."""
        rel_path = str(file_path.relative_to(base_path))
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern.lstrip("**/")):
                return True
            if fnmatch.fnmatch(str(file_path), pattern):
                return True
            # Check path parts
            for part in file_path.parts:
                if fnmatch.fnmatch(part, pattern.replace("**/", "").replace("/**", "")):
                    return True
        return False

    def _extract_python_imports(
        self, file_path: Path, rel_path: str, base_path: Path, graph: DependencyGraph
    ) -> None:
        """Extract imports from a Python file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception as e:
            self.logger.debug("parse_failed", file=rel_path, error=str(e))
            return

        external_imports: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self._process_import_node(node, rel_path, base_path, graph, external_imports)
            elif isinstance(node, ast.ImportFrom):
                self._process_import_from_node(
                    node, file_path, rel_path, base_path, graph, external_imports
                )

        if external_imports:
            graph.external_imports[rel_path] = external_imports

    def _process_import_node(
        self,
        node: ast.Import,
        rel_path: str,
        base_path: Path,
        graph: DependencyGraph,
        external_imports: Set[str],
    ) -> None:
        """Process an ast.Import node."""
        for alias in node.names:
            target = self._resolve_python_import(alias.name, base_path)
            if target and target in graph.files:
                graph.edges.append(
                    DependencyEdge(
                        source=rel_path,
                        target=target,
                        import_type="absolute",
                        import_statement=f"import {alias.name}",
                    )
                )
            else:
                external_imports.add(alias.name.split(".")[0])

    def _process_import_from_node(
        self,
        node: ast.ImportFrom,
        file_path: Path,
        rel_path: str,
        base_path: Path,
        graph: DependencyGraph,
        external_imports: Set[str],
    ) -> None:
        """Process an ast.ImportFrom node."""
        if not node.module:
            return

        # Resolve import target
        if node.level > 0:
            target = self._resolve_relative_import(file_path, node.module, node.level, base_path)
        else:
            target = self._resolve_python_import(node.module, base_path)

        if target and target in graph.files:
            graph.edges.append(
                DependencyEdge(
                    source=rel_path,
                    target=target,
                    import_type="relative" if node.level > 0 else "absolute",
                    import_statement=f"from {node.module} import ...",
                )
            )
        elif node.module:
            external_imports.add(node.module.split(".")[0])

    def _resolve_python_import(
        self, module_name: str, base_path: Path
    ) -> Optional[str]:
        """Resolve a Python module name to a file path."""
        parts = module_name.split(".")

        # Try as package (directory with __init__.py)
        pkg_path = base_path / "/".join(parts) / "__init__.py"
        if pkg_path.exists():
            return str(pkg_path.relative_to(base_path))

        # Try as module file directly
        mod_path = base_path / "/".join(parts[:-1]) / f"{parts[-1]}.py" if len(parts) > 1 else base_path / f"{parts[0]}.py"
        if mod_path.exists():
            return str(mod_path.relative_to(base_path))

        # Try with src/ prefix
        for prefix in ["src/", ""]:
            pkg_path = base_path / prefix / "/".join(parts) / "__init__.py"
            if pkg_path.exists():
                return str(pkg_path.relative_to(base_path))

            mod_path = base_path / prefix / "/".join(parts)
            mod_path = mod_path.with_suffix(".py")
            if mod_path.exists():
                return str(mod_path.relative_to(base_path))

        return None

    def _resolve_relative_import(
        self, file_path: Path, module: str, level: int, base_path: Path
    ) -> Optional[str]:
        """Resolve a relative Python import."""
        # Go up 'level' directories from the current file
        current_dir = file_path.parent
        for _ in range(level - 1):
            current_dir = current_dir.parent

        # Resolve the module path
        parts = module.split(".") if module else []

        # Try as module file
        if parts:
            mod_path = current_dir / "/".join(parts[:-1]) / f"{parts[-1]}.py" if len(parts) > 1 else current_dir / f"{parts[0]}.py"
            if mod_path.exists():
                return str(mod_path.relative_to(base_path))

            # Try as package
            pkg_path = current_dir / "/".join(parts) / "__init__.py"
            if pkg_path.exists():
                return str(pkg_path.relative_to(base_path))

        return None

    def _extract_js_imports(
        self, file_path: Path, rel_path: str, base_path: Path, graph: DependencyGraph
    ) -> None:
        """Extract imports from a JavaScript/TypeScript file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.debug("read_failed", file=rel_path, error=str(e))
            return

        external_imports: Set[str] = set()

        # Match ES6 imports: import X from 'path' or import { X } from 'path'
        import_pattern = r"import\s+(?:[\w\s{},*]+\s+from\s+)?['\"]([^'\"]+)['\"]"

        # Match require: require('path')
        require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"

        for pattern in [import_pattern, require_pattern]:
            self._process_js_pattern_matches(
                pattern, content, file_path, rel_path, base_path, graph, external_imports
            )

        if external_imports:
            graph.external_imports[rel_path] = external_imports

    def _process_js_pattern_matches(
        self,
        pattern: str,
        content: str,
        file_path: Path,
        rel_path: str,
        base_path: Path,
        graph: DependencyGraph,
        external_imports: Set[str],
    ) -> None:
        """Process all matches of a JS import pattern."""
        for match in re.finditer(pattern, content):
            import_path = match.group(1)
            self._process_single_js_import(
                import_path, match.group(0), file_path, rel_path, base_path, graph, external_imports
            )

    def _process_single_js_import(
        self,
        import_path: str,
        import_statement: str,
        file_path: Path,
        rel_path: str,
        base_path: Path,
        graph: DependencyGraph,
        external_imports: Set[str],
    ) -> None:
        """Process a single JS import path."""
        if not import_path.startswith("."):
            external_imports.add(import_path.split("/")[0])
            return

        target = self._resolve_js_relative_import(file_path, import_path, base_path)
        if target and target in graph.files:
            graph.edges.append(
                DependencyEdge(
                    source=rel_path,
                    target=target,
                    import_type="relative",
                    import_statement=import_statement,
                )
            )

    def _resolve_js_relative_import(
        self, file_path: Path, import_path: str, base_path: Path
    ) -> Optional[str]:
        """Resolve a relative JavaScript/TypeScript import."""
        current_dir = file_path.parent
        target_path = (current_dir / import_path).resolve()

        # Try various extensions
        extensions = [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]

        for ext in extensions:
            test_path = Path(str(target_path) + ext)
            if test_path.exists():
                try:
                    return str(test_path.relative_to(base_path))
                except ValueError:
                    continue

        # Try without extension (might already have it)
        if target_path.exists():
            try:
                return str(target_path.relative_to(base_path))
            except ValueError:
                pass

        return None

    def _identify_entry_points(self, base_path: Path, graph: DependencyGraph) -> None:
        """Identify entry point files in the project."""
        for file_path in graph.files:
            full_path = base_path / file_path

            # Check against entry point patterns
            for pattern in self.config.entry_point_patterns:
                if fnmatch.fnmatch(file_path, pattern.lstrip("**/")):
                    graph.entry_points.add(file_path)
                    break
                if fnmatch.fnmatch(full_path.name, pattern.lstrip("**/").split("/")[-1]):
                    graph.entry_points.add(file_path)
                    break

            # __init__.py files are always entry points (they can be imported as packages)
            if full_path.name == "__init__.py":
                graph.entry_points.add(file_path)

        self.logger.debug("entry_points_identified", count=len(graph.entry_points))

    def _find_orphan_files(
        self, base_path: Path, graph: DependencyGraph
    ) -> List[OrphanFile]:
        """Find files with no incoming imports."""
        orphans: List[OrphanFile] = []

        for file_path in graph.files:
            # Skip entry points
            if file_path in graph.entry_points:
                continue

            # Skip __init__.py files
            if Path(file_path).name == "__init__.py":
                continue

            # Check for importers
            importers = graph.get_importers(file_path)

            if not importers:
                full_path = base_path / file_path
                lines = len(full_path.read_text(encoding="utf-8").split("\n"))

                language = "python" if file_path.endswith(".py") else "typescript"
                if file_path.endswith(".js"):
                    language = "javascript"

                orphan = OrphanFile(
                    file_path=file_path,
                    absolute_path=str(full_path),
                    lines=lines,
                    language=language,
                    status=VerificationStatus.LIKELY,
                    reason="No direct imports found",
                )
                orphans.append(orphan)

        return orphans

    def _verify_orphans_with_grep(
        self, base_path: Path, orphans: List[OrphanFile]
    ) -> List[OrphanFile]:
        """Verify orphan candidates using grep for string references."""
        verified_orphans: List[OrphanFile] = []

        for orphan in orphans:
            module_basename = Path(orphan.file_path).stem

            # Search for string references to this module
            try:
                result = subprocess.run(
                    ["grep", "-r", "-l", module_basename, str(base_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                references = [
                    line
                    for line in result.stdout.strip().split("\n")
                    if line and not line.endswith(orphan.file_path)
                ]

                if not references:
                    orphan.status = VerificationStatus.CONFIRMED
                    orphan.reason = "No imports or string references found"
                    verified_orphans.append(orphan)
                else:
                    # Has some references, mark as uncertain
                    orphan.status = VerificationStatus.UNCERTAIN
                    orphan.reason = f"Found {len(references)} possible string references"
                    orphan.importers = references[:5]  # Store top 5
                    verified_orphans.append(orphan)

            except subprocess.TimeoutExpired:
                orphan.status = VerificationStatus.UNCERTAIN
                orphan.reason = "Verification timed out"
                verified_orphans.append(orphan)
            except Exception as e:
                self.logger.debug("grep_failed", file=orphan.file_path, error=str(e))
                verified_orphans.append(orphan)

        return verified_orphans

    def _find_orphan_functions(
        self, base_path: Path, graph: DependencyGraph
    ) -> Tuple[List[OrphanFunction], int]:
        """Find functions with no call sites."""
        orphan_functions: List[OrphanFunction] = []
        total_functions = 0

        for file_path in graph.files:
            if not file_path.endswith(".py"):
                continue

            full_path = base_path / file_path
            functions, file_orphans = self._analyze_python_functions(
                full_path, file_path, base_path
            )
            total_functions += functions
            orphan_functions.extend(file_orphans)

        return orphan_functions, total_functions

    def _analyze_python_functions(
        self, file_path: Path, rel_path: str, base_path: Path
    ) -> Tuple[int, List[OrphanFunction]]:
        """Analyze Python file for orphan functions."""
        orphans: List[OrphanFunction] = []
        function_count = 0

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            return 0, []

        # Collect all function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1

                # Skip special methods
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue

                # Skip test functions
                if node.name.startswith("test_"):
                    continue

                is_private = node.name.startswith("_")

                # Check if function is called anywhere in the codebase
                if not self._is_function_called(node.name, base_path, rel_path):
                    orphan = OrphanFunction(
                        name=node.name,
                        file_path=rel_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        status=VerificationStatus.LIKELY,
                        reason="No call sites found in codebase",
                        is_private=is_private,
                    )
                    orphans.append(orphan)

        return function_count, orphans

    def _is_function_called(
        self, func_name: str, base_path: Path, source_file: str
    ) -> bool:
        """Check if a function is called anywhere in the codebase."""
        # Use grep to search for function calls
        try:
            # Search for function name followed by opening paren
            pattern = rf"{func_name}\s*\("

            result = subprocess.run(
                ["grep", "-r", "-E", pattern, str(base_path / "src")],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Filter out the definition itself and comments
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Skip the source file itself (definition)
                if source_file in line:
                    continue
                # Skip comments
                if line.strip().startswith("#"):
                    continue
                # Found a call site
                return True

            return False

        except Exception:
            # On error, assume it might be called
            return True


def detect_orphans_impl(
    project_folder: str,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    analyze_functions: bool = True,
    verify_with_grep: bool = True,
) -> Dict[str, Any]:
    """Detect orphan files and functions in a project.

    Args:
        project_folder: Path to the project root
        include_patterns: Glob patterns for files to analyze
        exclude_patterns: Glob patterns for files to exclude
        analyze_functions: Whether to analyze function-level orphans
        verify_with_grep: Whether to verify findings with grep

    Returns:
        Dictionary with orphan analysis results
    """
    config = OrphanAnalysisConfig(
        analyze_functions=analyze_functions,
        verify_with_grep=verify_with_grep,
    )

    if include_patterns:
        config.include_patterns = include_patterns
    if exclude_patterns:
        config.exclude_patterns = exclude_patterns

    detector = OrphanDetector(config)
    result = detector.analyze(project_folder)

    return result.to_dict()
