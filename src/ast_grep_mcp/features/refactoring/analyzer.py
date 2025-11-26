"""Code selection analyzer for refactoring operations.

This module analyzes selected code regions to determine:
- Variables used and their classification (local, parameter, global)
- Parameters needed for extracted functions
- Return values required
- Scope and dependencies
"""

import re
from typing import Dict, List, Optional, Set, Tuple
import structlog

from ...models.refactoring import (
    CodeSelection,
    VariableInfo,
    VariableType,
)

logger = structlog.get_logger(__name__)


class CodeSelectionAnalyzer:
    """Analyzes code selections for refactoring operations."""

    def __init__(self, language: str):
        """Initialize analyzer for specific language.

        Args:
            language: Programming language (python, typescript, javascript, java)
        """
        self.language = language
        self._variable_patterns = self._get_variable_patterns(language)

    def analyze_selection(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        project_folder: str,
    ) -> CodeSelection:
        """Analyze a code selection for refactoring.

        Args:
            file_path: Path to the file containing selection
            start_line: Starting line of selection (1-indexed)
            end_line: Ending line of selection (1-indexed)
            project_folder: Project root folder

        Returns:
            CodeSelection with analysis results
        """
        logger.info(
            "analyzing_code_selection",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=self.language,
        )

        # Read the selected code
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        selection_lines = lines[start_line - 1:end_line]
        content = ''.join(selection_lines)

        # Detect indentation
        indentation = self._detect_indentation(selection_lines)

        # Create selection object
        selection = CodeSelection(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=self.language,
            content=content,
            indentation=indentation,
        )

        # Analyze variables
        self._analyze_variables(selection, lines, project_folder)

        # Determine parameters and return values
        self._determine_parameters_and_returns(selection)

        # Check for early returns and exceptions
        selection.has_early_returns = self._has_early_returns(content)
        selection.has_exceptions = self._has_exception_handling(content)

        logger.info(
            "code_selection_analyzed",
            variables_found=len(selection.variables),
            parameters_needed=len(selection.parameters_needed),
            return_values=len(selection.return_values),
        )

        return selection

    def _detect_indentation(self, lines: List[str]) -> str:
        """Detect indentation style from code lines.

        Args:
            lines: Lines of code

        Returns:
            Indentation string (spaces or tabs)
        """
        for line in lines:
            if line.strip() and line[0] in (' ', '\t'):
                # Extract leading whitespace
                indent = len(line) - len(line.lstrip())
                return line[:indent]

        return ""  # No indentation detected

    def _analyze_variables(
        self,
        selection: CodeSelection,
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze variables in selection.

        Identifies:
        - Variables read (used)
        - Variables written (assigned)
        - Variable scope (local, parameter, global)

        Args:
            selection: CodeSelection to populate with variable info
            all_lines: All lines in the file (for context)
            project_folder: Project root for ast-grep search
        """
        content = selection.content
        variables: Dict[str, VariableInfo] = {}

        # Find all variable references using ast-grep patterns
        if self.language == "python":
            self._analyze_python_variables(selection, variables, all_lines, project_folder)
        elif self.language in ("typescript", "javascript"):
            self._analyze_js_ts_variables(selection, variables, all_lines, project_folder)
        elif self.language == "java":
            self._analyze_java_variables(selection, variables, all_lines, project_folder)

        selection.variables = list(variables.values())

    def _analyze_python_variables(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze Python variables in selection.

        Uses regex patterns to identify:
        - Assignments (x = ...)
        - Function calls (func(...))
        - Attribute access (obj.attr)
        - Variable references

        Args:
            selection: Code selection
            variables: Dict to populate with variable info
            all_lines: All file lines
            project_folder: Project root
        """
        content = selection.content

        # Find assignments (variables being written)
        assignment_pattern = r'\b(\w+)\s*='
        for match in re.finditer(assignment_pattern, content):
            var_name = match.group(1)
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.LOCAL,  # Default, will refine later
                    first_use_line=selection.start_line,
                    is_written=True,
                )
            else:
                variables[var_name].is_written = True

        # Find variable reads (identifiers not being assigned)
        # Match word boundaries but exclude keywords
        python_keywords = {
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
            'while', 'with', 'yield'
        }

        identifier_pattern = r'\b([a-zA-Z_]\w*)\b'
        for match in re.finditer(identifier_pattern, content):
            var_name = match.group(1)

            # Skip keywords and built-in functions
            if var_name in python_keywords:
                continue

            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,  # Assume parameter until proven otherwise
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

        # Classify variables based on scope analysis
        self._classify_variable_types(selection, variables, all_lines)

    def _analyze_js_ts_variables(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze JavaScript/TypeScript variables in selection.

        Args:
            selection: Code selection
            variables: Dict to populate with variable info
            all_lines: All file lines
            project_folder: Project root
        """
        content = selection.content

        # Find variable declarations and assignments
        # Matches: const x = ..., let y = ..., var z = ..., x = ...
        declaration_pattern = r'\b(?:const|let|var)?\s*(\w+)\s*='
        for match in re.finditer(declaration_pattern, content):
            var_name = match.group(1)
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.LOCAL,
                    first_use_line=selection.start_line,
                    is_written=True,
                )
            else:
                variables[var_name].is_written = True

        # Find variable reads
        js_keywords = {
            'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'enum', 'export',
            'extends', 'false', 'finally', 'for', 'function', 'if', 'import',
            'in', 'instanceof', 'let', 'new', 'null', 'return', 'super', 'switch',
            'this', 'throw', 'true', 'try', 'typeof', 'var', 'void', 'while',
            'with', 'yield', 'async', 'of'
        }

        identifier_pattern = r'\b([a-zA-Z_$]\w*)\b'
        for match in re.finditer(identifier_pattern, content):
            var_name = match.group(1)

            if var_name in js_keywords:
                continue

            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

        self._classify_variable_types(selection, variables, all_lines)

    def _analyze_java_variables(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
        project_folder: str,
    ) -> None:
        """Analyze Java variables in selection.

        Args:
            selection: Code selection
            variables: Dict to populate with variable info
            all_lines: All file lines
            project_folder: Project root
        """
        content = selection.content

        # Find variable declarations and assignments
        # Matches: Type var = ..., var = ...
        declaration_pattern = r'\b(?:\w+\s+)?(\w+)\s*='
        for match in re.finditer(declaration_pattern, content):
            var_name = match.group(1)
            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.LOCAL,
                    first_use_line=selection.start_line,
                    is_written=True,
                )
            else:
                variables[var_name].is_written = True

        # Find variable reads
        java_keywords = {
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
            'char', 'class', 'const', 'continue', 'default', 'do', 'double',
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
            'goto', 'if', 'implements', 'import', 'instanceof', 'int', 'interface',
            'long', 'native', 'new', 'package', 'private', 'protected', 'public',
            'return', 'short', 'static', 'strictfp', 'super', 'switch',
            'synchronized', 'this', 'throw', 'throws', 'transient', 'try', 'void',
            'volatile', 'while', 'true', 'false', 'null'
        }

        identifier_pattern = r'\b([a-zA-Z_]\w*)\b'
        for match in re.finditer(identifier_pattern, content):
            var_name = match.group(1)

            if var_name in java_keywords:
                continue

            if var_name not in variables:
                variables[var_name] = VariableInfo(
                    name=var_name,
                    variable_type=VariableType.PARAMETER,
                    first_use_line=selection.start_line,
                    is_read=True,
                )
            else:
                variables[var_name].is_read = True

        self._classify_variable_types(selection, variables, all_lines)

    def _classify_variable_types(
        self,
        selection: CodeSelection,
        variables: Dict[str, VariableInfo],
        all_lines: List[str],
    ) -> None:
        """Classify variables by type based on scope analysis.

        Updates variable_type in variables dict:
        - LOCAL: Defined within selection, not used outside
        - PARAMETER: Used but not defined in selection
        - MODIFIED: Modified in selection, needs to be returned
        - GLOBAL: Module or global scope
        - CLOSURE: From enclosing function scope

        Args:
            selection: Code selection
            variables: Dict of variables to classify
            all_lines: All file lines for context
        """
        # Get lines before and after selection for context
        before_lines = all_lines[:selection.start_line - 1]
        after_lines = all_lines[selection.end_line:]

        for var_name, var_info in variables.items():
            # Check if variable is defined before selection
            defined_before = any(
                re.search(rf'\b{re.escape(var_name)}\s*=', line)
                for line in before_lines
            )

            # Check if variable is used after selection
            used_after = any(
                re.search(rf'\b{re.escape(var_name)}\b', line)
                for line in after_lines
            )

            # Classify
            if var_info.is_written and not defined_before:
                # Variable is created in selection
                if used_after:
                    var_info.variable_type = VariableType.MODIFIED
                else:
                    var_info.variable_type = VariableType.LOCAL
            elif var_info.is_read and not var_info.is_written:
                # Variable is only read, must come from outside
                if defined_before:
                    var_info.variable_type = VariableType.PARAMETER
                else:
                    # Check if it's a global or built-in
                    var_info.variable_type = VariableType.PARAMETER
            elif var_info.is_written and defined_before and used_after:
                # Variable is modified and used after
                var_info.variable_type = VariableType.MODIFIED

    def _determine_parameters_and_returns(self, selection: CodeSelection) -> None:
        """Determine which variables should be parameters and return values.

        Args:
            selection: Code selection to update
        """
        # Parameters: Variables that need to be passed in
        parameters = selection.get_variables_by_type(VariableType.PARAMETER)
        selection.parameters_needed = [v.name for v in parameters if v.is_read]

        # Return values: Variables that need to be returned
        modified_vars = selection.get_variables_by_type(VariableType.MODIFIED)
        selection.return_values = [v.name for v in modified_vars]

    def _has_early_returns(self, content: str) -> bool:
        """Check if selection contains early return statements.

        Args:
            content: Code content

        Returns:
            True if early returns detected
        """
        return bool(re.search(r'\breturn\b', content))

    def _has_exception_handling(self, content: str) -> bool:
        """Check if selection contains exception handling.

        Args:
            content: Code content

        Returns:
            True if try/except/throw detected
        """
        if self.language == "python":
            return bool(re.search(r'\b(try|except|raise)\b', content))
        elif self.language in ("typescript", "javascript"):
            return bool(re.search(r'\b(try|catch|throw)\b', content))
        elif self.language == "java":
            return bool(re.search(r'\b(try|catch|throw)\b', content))

        return False

    def _get_variable_patterns(self, language: str) -> Dict[str, str]:
        """Get language-specific variable patterns.

        Args:
            language: Programming language

        Returns:
            Dict of ast-grep patterns for variable detection
        """
        patterns = {
            "python": {
                "assignment": "$VAR = $VALUE",
                "variable_ref": "$VAR",
            },
            "typescript": {
                "declaration": "const $VAR = $VALUE",
                "variable_ref": "$VAR",
            },
            "javascript": {
                "declaration": "const $VAR = $VALUE",
                "variable_ref": "$VAR",
            },
            "java": {
                "declaration": "$TYPE $VAR = $VALUE",
                "variable_ref": "$VAR",
            },
        }

        return patterns.get(language, patterns["python"])
