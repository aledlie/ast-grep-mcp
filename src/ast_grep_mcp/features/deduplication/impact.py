"""Impact analysis for deduplication refactoring."""

import json
import os
import re
import subprocess
from typing import Any, Dict, List

from ...core import run_ast_grep
from ...core.logging import get_logger


class ImpactAnalyzer:
    """Analyzes the impact of applying deduplication to code."""

    def __init__(self) -> None:
        """Initialize the impact analyzer."""
        self.logger = get_logger("deduplication.impact_analysis")

    def analyze_deduplication_impact(
        self,
        duplicate_group: Dict[str, Any],
        project_root: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze the impact of applying deduplication to a duplicate group.

        Uses ast-grep to find external references to the duplicated code and
        assesses breaking change risks.

        Args:
            duplicate_group: A duplication group from find_duplication results containing:
                - locations: List of file:line-range strings
                - sample_code: Representative code sample
                - duplicate_count: Number of instances
                - lines_per_duplicate: Lines in each instance
            project_root: Absolute path to project root
            language: Programming language

        Returns:
            Impact analysis with:
            - files_affected: Number of files that would be modified
            - lines_changed: Dict with additions and deletions estimates
            - external_call_sites: List of locations calling the duplicated code
            - breaking_change_risk: Dict with risk level and factors
        """
        locations = duplicate_group.get("locations", [])
        sample_code = duplicate_group.get("sample_code", "")
        duplicate_count = duplicate_group.get("duplicate_count", 0)
        lines_per_duplicate = duplicate_group.get("lines_per_duplicate", 0)

        # Parse locations to get file paths and line ranges
        files_in_group = []
        for loc in locations:
            if ":" in loc:
                file_path = loc.split(":")[0]
                if file_path not in files_in_group:
                    files_in_group.append(file_path)

        # Extract function/class names from sample code
        function_names = self._extract_function_names_from_code(sample_code, language)

        self.logger.info(
            "impact_analysis_start",
            duplicate_count=duplicate_count,
            files_in_group=len(files_in_group),
            function_names=function_names[:5] if function_names else []
        )

        # Find external call sites using ast-grep
        external_call_sites = self._find_external_call_sites(
            function_names=function_names,
            project_root=project_root,
            language=language,
            exclude_files=files_in_group
        )

        # Find imports of the duplicated code
        import_sites = self._find_import_references(
            function_names=function_names,
            project_root=project_root,
            language=language,
            exclude_files=files_in_group
        )

        # Combine call sites and imports
        all_external_refs = external_call_sites + import_sites

        # Estimate lines changed
        lines_changed = self._estimate_lines_changed(
            duplicate_count=duplicate_count,
            lines_per_duplicate=lines_per_duplicate,
            external_call_sites=len(all_external_refs)
        )

        # Assess breaking change risk
        breaking_change_risk = self._assess_breaking_change_risk(
            function_names=function_names,
            files_in_group=files_in_group,
            external_call_sites=all_external_refs,
            project_root=project_root,
            language=language
        )

        # Calculate files affected
        files_affected = len(files_in_group)
        external_files = set()
        for site in all_external_refs:
            if "file" in site:
                external_files.add(site["file"])
        files_affected += len(external_files)

        result = {
            "files_affected": files_affected,
            "lines_changed": lines_changed,
            "external_call_sites": all_external_refs,
            "breaking_change_risk": breaking_change_risk
        }

        self.logger.info(
            "impact_analysis_complete",
            files_affected=files_affected,
            external_references=len(all_external_refs),
            risk_level=breaking_change_risk.get("level", "unknown")
        )

        return result

    def _extract_function_names_from_code(self, code: str, language: str) -> List[str]:
        """Extract function/method/class names from code sample.

        Args:
            code: Code sample to analyze
            language: Programming language

        Returns:
            List of extracted names
        """
        names: List[str] = []

        if not code:
            return names

        lang = language.lower()

        # Language-specific patterns for extracting names
        if lang == "python":
            # Match: def function_name( or class ClassName
            func_matches = re.findall(r'\bdef\s+(\w+)\s*\(', code)
            class_matches = re.findall(r'\bclass\s+(\w+)', code)
            names.extend(func_matches)
            names.extend(class_matches)

        elif lang in ("javascript", "typescript", "jsx", "tsx"):
            # Match: function name( or const name = or name( { for methods
            func_matches = re.findall(r'\bfunction\s+(\w+)\s*\(', code)
            arrow_matches = re.findall(r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=])*=>', code)
            method_matches = re.findall(r'^\s*(\w+)\s*\([^)]*\)\s*\{', code, re.MULTILINE)
            names.extend(func_matches)
            names.extend(arrow_matches)
            names.extend(method_matches)

        elif lang in ("java", "csharp", "cpp", "c"):
            # Match: returnType methodName( or class ClassName
            method_matches = re.findall(r'\b(?:public|private|protected|static|\w+)\s+(\w+)\s*\([^)]*\)\s*\{', code)
            class_matches = re.findall(r'\bclass\s+(\w+)', code)
            names.extend(method_matches)
            names.extend(class_matches)

        elif lang == "go":
            # Match: func FunctionName( or func (r *Receiver) MethodName(
            func_matches = re.findall(r'\bfunc\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', code)
            names.extend(func_matches)

        elif lang == "rust":
            # Match: fn function_name( or struct StructName
            func_matches = re.findall(r'\bfn\s+(\w+)\s*[<(]', code)
            struct_matches = re.findall(r'\bstruct\s+(\w+)', code)
            names.extend(func_matches)
            names.extend(struct_matches)

        # Deduplicate and filter common words
        filtered_names = []
        seen = set()
        common_words = {"new", "get", "set", "if", "for", "while", "return", "main", "init", "test"}

        for name in names:
            if name and name not in seen and name.lower() not in common_words:
                seen.add(name)
                filtered_names.append(name)

        return filtered_names

    def _find_external_call_sites(
        self,
        function_names: List[str],
        project_root: str,
        language: str,
        exclude_files: List[str]
    ) -> List[Dict[str, Any]]:
        """Find call sites for functions outside the duplicate locations.

        Uses ast-grep to search for function calls.

        Args:
            function_names: Names of functions to search for
            project_root: Project root path
            language: Programming language
            exclude_files: Files to exclude (contain the duplicates)

        Returns:
            List of call site info dicts with file, line, column, context
        """
        call_sites: List[Dict[str, Any]] = []

        if not function_names:
            return call_sites

        for func_name in function_names[:10]:  # Limit to prevent too many searches
            # Build call pattern based on language
            pattern = f"{func_name}($$$)"

            try:
                # Run ast-grep to find call sites
                args = ["--pattern", pattern, "--lang", language, "--json", project_root]
                result = run_ast_grep("run", args)

                if result.returncode == 0 and result.stdout.strip():
                    matches = json.loads(result.stdout)

                    for match in matches:
                        file_path = match.get("file", "")

                        # Skip files containing the duplicates
                        if file_path in exclude_files:
                            continue

                        # Make path absolute if needed
                        if not os.path.isabs(file_path):
                            file_path = os.path.join(project_root, file_path)

                        call_site = {
                            "file": file_path,
                            "line": match.get("range", {}).get("start", {}).get("line", 0) + 1,
                            "column": match.get("range", {}).get("start", {}).get("column", 0),
                            "function_called": func_name,
                            "context": match.get("text", "")[:100],
                            "type": "function_call"
                        }
                        call_sites.append(call_site)

            except (json.JSONDecodeError, subprocess.SubprocessError) as e:
                # Log but continue with other function names
                self.logger.debug("call_site_search_error", function=func_name, error=str(e))
                continue

        return call_sites

    def _find_import_references(
        self,
        function_names: List[str],
        project_root: str,
        language: str,
        exclude_files: List[str]
    ) -> List[Dict[str, Any]]:
        """Find import statements that reference the duplicated code.

        Args:
            function_names: Names to search for in imports
            project_root: Project root path
            language: Programming language
            exclude_files: Files to exclude

        Returns:
            List of import reference info dicts
        """
        import_refs: List[Dict[str, Any]] = []

        if not function_names:
            return import_refs

        lang = language.lower()

        for func_name in function_names[:10]:
            # Build import pattern based on language
            if lang == "python":
                # from module import func_name or import module
                patterns = [
                    f"from $MODULE import {func_name}",
                    f"from $MODULE import $$$, {func_name}, $$$"
                ]
            elif lang in ("javascript", "typescript", "jsx", "tsx"):
                patterns = [
                    f"import {{ {func_name} }} from $MODULE",
                    f"import {{ $$$, {func_name}, $$$ }} from $MODULE"
                ]
            elif lang in ("java",):
                patterns = [f"import $$$$.{func_name}"]
            elif lang == "go":
                # Go imports are package-level, not function-level
                continue
            else:
                continue

            for pattern in patterns:
                try:
                    args = ["--pattern", pattern, "--lang", language, "--json", project_root]
                    result = run_ast_grep("run", args)

                    if result.returncode == 0 and result.stdout.strip():
                        matches = json.loads(result.stdout)

                        for match in matches:
                            file_path = match.get("file", "")

                            if file_path in exclude_files:
                                continue

                            if not os.path.isabs(file_path):
                                file_path = os.path.join(project_root, file_path)

                            import_ref = {
                                "file": file_path,
                                "line": match.get("range", {}).get("start", {}).get("line", 0) + 1,
                                "column": match.get("range", {}).get("start", {}).get("column", 0),
                                "imported_name": func_name,
                                "context": match.get("text", "")[:100],
                                "type": "import"
                            }
                            import_refs.append(import_ref)

                except (json.JSONDecodeError, subprocess.SubprocessError):
                    continue

        return import_refs

    def _estimate_lines_changed(
        self,
        duplicate_count: int,
        lines_per_duplicate: int,
        external_call_sites: int
    ) -> Dict[str, Any]:
        """Estimate the number of lines that would change during deduplication.

        Args:
            duplicate_count: Number of duplicate instances
            lines_per_duplicate: Lines in each duplicate
            external_call_sites: Number of external references

        Returns:
            Dict with additions and deletions estimates
        """
        # Deletions: All duplicate code except one instance
        deletions = (duplicate_count - 1) * lines_per_duplicate

        # Additions:
        # - One extracted function (slightly more lines due to parameterization)
        extracted_function_lines = int(lines_per_duplicate * 1.2)

        # - Import statements for each file (1 line per file)
        import_lines = duplicate_count - 1  # minus the file with the extracted function

        # - Replacement calls (1 line each)
        replacement_calls = duplicate_count

        # - Updates to external call sites (minimal, usually 0 or 1 line each)
        external_updates = external_call_sites

        additions = extracted_function_lines + import_lines + replacement_calls + external_updates

        # Net change
        net_change = additions - deletions

        return {
            "additions": additions,
            "deletions": deletions,
            "net_change": net_change,
            "breakdown": {
                "extracted_function": extracted_function_lines,
                "new_imports": import_lines,
                "replacement_calls": replacement_calls,
                "external_call_updates": external_updates
            }
        }

    def _assess_breaking_change_risk(
        self,
        function_names: List[str],
        files_in_group: List[str],
        external_call_sites: List[Dict[str, Any]],
        project_root: str,
        language: str
    ) -> Dict[str, Any]:
        """Assess the risk of breaking changes from deduplication.

        Args:
            function_names: Names of functions being deduplicated
            files_in_group: Files containing the duplicates
            external_call_sites: External references found
            project_root: Project root path
            language: Programming language

        Returns:
            Risk assessment with level, factors, and recommendations
        """
        risk_factors = []
        risk_score = 0

        # Factor 1: External call sites exist
        if external_call_sites:
            call_count = len([s for s in external_call_sites if s.get("type") == "function_call"])
            import_count = len([s for s in external_call_sites if s.get("type") == "import"])

            if call_count > 0:
                risk_factors.append(f"Found {call_count} external call site(s) that may need updates")
                risk_score += min(call_count, 3)  # Cap at 3

            if import_count > 0:
                risk_factors.append(f"Found {import_count} import statement(s) referencing the code")
                risk_score += min(import_count, 2)  # Cap at 2

        # Factor 2: Check if functions appear to be public API
        for name in function_names:
            # Heuristics for public API
            is_public = False

            # Python: no underscore prefix
            if language.lower() == "python" and not name.startswith("_"):
                is_public = True

            # Java/C#: typically PascalCase for public
            if language.lower() in ("java", "csharp") and name[0].isupper():
                is_public = True

            if is_public:
                risk_factors.append(f"Function '{name}' appears to be public API")
                risk_score += 2
                break  # Only count once

        # Factor 3: Cross-module dependencies
        if len(files_in_group) > 1:
            # Check if files are in different directories (different modules)
            directories = set()
            for file_path in files_in_group:
                directories.add(os.path.dirname(file_path))

            if len(directories) > 1:
                risk_factors.append(f"Duplicates span {len(directories)} different modules/directories")
                risk_score += 2

        # Factor 4: Test files involved
        test_files = [f for f in files_in_group if "test" in f.lower() or "spec" in f.lower()]
        if test_files:
            risk_factors.append(f"{len(test_files)} test file(s) contain duplicates - lower risk")
            risk_score -= 1  # Reduce risk for test-only changes

        # Factor 5: Check for __init__.py or index files (re-exports)
        reexport_files = [f for f in files_in_group
                         if os.path.basename(f) in ("__init__.py", "index.ts", "index.js", "mod.rs")]
        if reexport_files:
            risk_factors.append("Code is in module export file - higher breakage risk")
            risk_score += 3

        # Determine risk level
        if risk_score <= 1:
            level = "low"
            recommendations = [
                "Safe to proceed with standard review",
                "Run tests after applying changes"
            ]
        elif risk_score <= 4:
            level = "medium"
            recommendations = [
                "Review external call sites before applying",
                "Consider updating call sites in the same commit",
                "Run comprehensive test suite after changes"
            ]
        else:
            level = "high"
            recommendations = [
                "Carefully review all external references",
                "Consider deprecating old functions instead of removing",
                "Update external call sites first",
                "May require coordinated changes across modules",
                "Consider feature flag for gradual rollout"
            ]

        return {
            "level": level,
            "score": risk_score,
            "factors": risk_factors,
            "recommendations": recommendations,
            "external_reference_count": len(external_call_sites)
        }


# Module-level function for backwards compatibility
def analyze_deduplication_impact(
    duplicate_group: Dict[str, Any],
    project_root: str,
    language: str
) -> Dict[str, Any]:
    """Analyze the impact of applying deduplication to a duplicate group."""
    analyzer = ImpactAnalyzer()
    return analyzer.analyze_deduplication_impact(duplicate_group, project_root, language)
