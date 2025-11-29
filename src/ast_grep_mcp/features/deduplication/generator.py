"""
Code generation module for deduplication refactoring.

This module provides functionality for generating refactored code,
including function extraction, parameter inference, and import generation.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Callable

from ...core.logging import get_logger
from ...models.deduplication import FunctionTemplate
from ...utils.formatters import format_generated_code


# Language-specific configuration for function generation
FUNCTION_GENERATORS: Dict[str, Callable] = {}

# Language-specific configuration for type inference
TYPE_INFERENCE_CONFIG: Dict[str, Dict[str, Dict[str, str]]] = {
    "python": {
        "literal": {
            "string": "str",
            "number_int": "int",
            "number_float": "float",
            "boolean": "bool"
        },
        "identifier": {"default": "Any"},
        "type": {"use_value": True}
    },
    "typescript": {
        "literal": {
            "string": "string",
            "number": "number",
            "boolean": "boolean"
        },
        "identifier": {"default": "any"},
        "type": {"use_value": False}
    }
}


class CodeGenerator:
    """Generates refactored code for deduplication."""

    def __init__(self, language: str = "python") -> None:
        """Initialize the code generator.

        Args:
            language: Programming language for code generation
        """
        self.language = language
        self.logger = get_logger("deduplication.generator")

    def _generate_python_function(
        self,
        function_name: str,
        parameters: List[Dict[str, str]],
        body: str,
        return_type: Optional[str],
        docstring: Optional[str]
    ) -> str:
        """Generate Python function using template system."""
        param_tuples = [(p["name"], p.get("type")) for p in parameters]
        template = FunctionTemplate(
            name=function_name,
            parameters=param_tuples,
            body=body,
            return_type=return_type,
            docstring=docstring
        )
        return template.generate()

    def _generate_js_ts_function(
        self,
        function_name: str,
        parameters: List[Dict[str, str]],
        body: str,
        return_type: Optional[str],
        docstring: Optional[str]
    ) -> str:
        """Generate JavaScript/TypeScript function."""
        param_list = self._format_js_parameters(parameters)
        type_annotation = f": {return_type}" if return_type and self.language == "typescript" else ""

        function_code = f"function {function_name}({param_list}){type_annotation} {{\n"
        if docstring:
            function_code += f"    // {docstring}\n"

        indented_body = "\n".join(f"    {line}" for line in body.split("\n"))
        function_code += indented_body + "\n}"
        return function_code

    def _generate_java_function(
        self,
        function_name: str,
        parameters: List[Dict[str, str]],
        body: str,
        return_type: Optional[str],
        docstring: Optional[str]
    ) -> str:
        """Generate Java method."""
        param_list = ", ".join(f"{p.get('type', 'Object')} {p['name']}" for p in parameters)
        return_annotation = return_type if return_type else "void"

        function_code = f"public {return_annotation} {function_name}({param_list}) {{\n"
        if docstring:
            function_code += f"    // {docstring}\n"

        indented_body = "\n".join(f"    {line}" for line in body.split("\n"))
        function_code += indented_body + "\n}"
        return function_code

    def _generate_generic_function(
        self,
        function_name: str,
        parameters: List[Dict[str, str]],
        body: str,
        **kwargs
    ) -> str:
        """Generate generic function format."""
        param_list = ", ".join(p["name"] for p in parameters)
        return f"function {function_name}({param_list}) {{\n{body}\n}}"

    def generate_extracted_function(
        self,
        function_name: str,
        parameters: List[Dict[str, str]],
        body: str,
        return_type: Optional[str] = None,
        docstring: Optional[str] = None
    ) -> str:
        """
        Generate an extracted function from duplicated code.

        Args:
            function_name: Name of the extracted function
            parameters: List of parameter dicts with 'name' and optionally 'type'
            body: Function body code
            return_type: Optional return type annotation
            docstring: Optional function documentation

        Returns:
            Generated function code
        """
        self.logger.info(
            "generating_extracted_function",
            function_name=function_name,
            param_count=len(parameters),
            language=self.language
        )

        # Language-specific generators map
        generators = {
            "python": self._generate_python_function,
            "javascript": self._generate_js_ts_function,
            "typescript": self._generate_js_ts_function,
            "java": self._generate_java_function
        }

        # Get the appropriate generator or use generic
        generator = generators.get(self.language, self._generate_generic_function)
        function_code = generator(function_name, parameters, body, return_type, docstring)

        # Format the generated code
        return self._format_generated_code(function_code, function_name)

    def _format_generated_code(self, function_code: str, function_name: str) -> str:
        """Format generated code with error handling."""
        try:
            formatted_code = format_generated_code(function_code, self.language)
            self.logger.info(
                "formatted_generated_function",
                function_name=function_name,
                language=self.language
            )
            return formatted_code
        except Exception as e:
            self.logger.warning(
                "formatting_failed",
                function_name=function_name,
                language=self.language,
                error=str(e)
            )
            return function_code

    def generate_function_call(
        self,
        function_name: str,
        arguments: List[str],
        assign_to: Optional[str] = None
    ) -> str:
        """
        Generate a function call to replace duplicated code.

        Args:
            function_name: Name of the function to call
            arguments: List of argument values
            assign_to: Optional variable to assign result to

        Returns:
            Generated function call code
        """
        call = f"{function_name}({', '.join(arguments)})"

        if assign_to:
            if self.language in ["javascript", "typescript"]:
                return f"const {assign_to} = {call};"
            elif self.language == "python":
                return f"{assign_to} = {call}"
            else:
                return f"{assign_to} = {call};"

        return call if self.language == "python" else f"{call};"

    def generate_import_statement(
        self,
        module_path: str,
        import_names: List[str],
        is_relative: bool = False
    ) -> str:
        """
        Generate an import statement for the extracted function.

        Args:
            module_path: Module or file path to import from
            import_names: Names to import
            is_relative: Whether to use relative import

        Returns:
            Generated import statement
        """
        if self.language == "python":
            if is_relative:
                prefix = "." if module_path else ""
                return f"from {prefix}{module_path} import {', '.join(import_names)}"
            else:
                if module_path:
                    return f"from {module_path} import {', '.join(import_names)}"
                else:
                    return f"import {', '.join(import_names)}"

        elif self.language in ["javascript", "typescript"]:
            names = "{" + ", ".join(import_names) + "}"
            extension = ".js" if self.language == "javascript" else ""
            path = f"./{module_path}" if is_relative else module_path
            return f"import {names} from '{path}{extension}';"

        elif self.language == "java":
            return f"import {module_path}.{import_names[0]};"

        else:
            return f"// Import {', '.join(import_names)} from {module_path}"

    def infer_function_parameters(
        self,
        code_variations: List[Dict[str, Any]],
        base_code: str
    ) -> List[Dict[str, str]]:
        """
        Infer function parameters from code variations.

        Args:
            code_variations: List of code variations
            base_code: Base code to analyze

        Returns:
            List of inferred parameters
        """
        parameters = []
        seen_names = set()

        # Extract unique varying values
        for variation in code_variations:
            param_name = variation.get("suggested_param_name")
            if param_name and param_name not in seen_names:
                param_type = self._infer_parameter_type(variation)
                parameters.append({
                    "name": param_name,
                    "type": param_type
                })
                seen_names.add(param_name)

        # Add any identifiers that appear to be external dependencies
        external_deps = self._find_external_dependencies(base_code)
        for dep in external_deps:
            if dep not in seen_names:
                parameters.append({
                    "name": dep,
                    "type": "Any"  # Type will be inferred from usage
                })
                seen_names.add(dep)

        return parameters

    def _format_python_parameters(self, parameters: List[Dict[str, str]]) -> str:
        """Format parameters for Python function signature."""
        formatted = []
        for param in parameters:
            if "type" in param and param["type"]:
                formatted.append(f"{param['name']}: {param['type']}")
            else:
                formatted.append(param["name"])
        return ", ".join(formatted)

    def _format_js_parameters(self, parameters: List[Dict[str, str]]) -> str:
        """Format parameters for JavaScript/TypeScript function signature."""
        if self.language == "typescript":
            formatted = []
            for param in parameters:
                if "type" in param and param["type"]:
                    formatted.append(f"{param['name']}: {param['type']}")
                else:
                    formatted.append(param["name"])
            return ", ".join(formatted)
        else:
            return ", ".join(p["name"] for p in parameters)

    def _get_literal_type(self, literal_type: str, value: str, lang_config: Dict) -> Optional[str]:
        """Get type mapping for literal values."""
        if literal_type == "string":
            return lang_config.get("string")
        elif literal_type == "number":
            # For Python, distinguish int from float
            if self.language == "python" and "." not in value:
                return lang_config.get("number_int", "int")
            elif self.language == "python":
                return lang_config.get("number_float", "float")
            else:
                return lang_config.get("number")
        elif literal_type == "boolean":
            return lang_config.get("boolean")
        return None

    def _infer_parameter_type(self, variation: Dict[str, Any]) -> Optional[str]:
        """Infer parameter type from variation."""
        category = variation.get("category", "")
        value = variation.get("old_value", "")

        # Get language configuration
        lang_config = TYPE_INFERENCE_CONFIG.get(self.language, {})
        if not lang_config:
            return None

        # Get category configuration
        category_config = lang_config.get(category, {})
        if not category_config:
            return None

        # Handle different categories
        if category == "literal":
            literal_type = variation.get("literal_type", "")
            return self._get_literal_type(literal_type, value, category_config)
        elif category == "identifier":
            return category_config.get("default")
        elif category == "type":
            # Use value directly for type category if configured
            if category_config.get("use_value"):
                return str(value) if value else None
            return None

        return None

    def _find_external_dependencies(self, code: str) -> List[str]:
        """Find external dependencies that should be parameters."""
        dependencies: List[str] = []

        # Simple heuristic: find identifiers that look like they come from outside
        # This is language-specific and simplified
        if self.language == "python":
            # Look for common patterns like self.x, module.function, etc.
            patterns = [
                r'\bself\.(\w+)',  # Class attributes
                r'(?<!\.)(\w+)\(',  # Function calls (not methods)
            ]
            for pattern in patterns:
                matches = re.findall(pattern, code)
                dependencies.extend(m for m in matches if m not in ['print', 'len', 'range', 'str', 'int'])

        return list(set(dependencies))[:5]  # Limit to top 5

    def generate_module_structure(
        self,
        module_name: str,
        functions: List[Dict[str, str]],
        imports: Optional[List[str]] = None
    ) -> str:
        """
        Generate a complete module with extracted functions.

        Args:
            module_name: Name of the module
            functions: List of function definitions
            imports: Optional list of import statements

        Returns:
            Complete module code
        """
        module_code = []

        # Add module docstring
        if self.language == "python":
            module_code.append('"""')
            module_code.append(f'{module_name} - Extracted common functionality')
            module_code.append('"""')
            module_code.append('')

        elif self.language in ["javascript", "typescript"]:
            module_code.append('/**')
            module_code.append(f' * {module_name} - Extracted common functionality')
            module_code.append(' */')
            module_code.append('')

        # Add imports
        if imports:
            for imp in imports:
                module_code.append(imp)
            module_code.append('')

        # Add functions
        for func in functions:
            module_code.append(func.get("code", ""))
            module_code.append('')

        # Add exports for JS/TS
        if self.language in ["javascript", "typescript"]:
            export_names = [f.get("name", "") for f in functions]
            if export_names:
                module_code.append(f"export {{ {', '.join(export_names)} }};")

        return "\n".join(module_code)

    def validate_generated_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate generated code for syntax errors.

        Args:
            code: Generated code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.language == "python":
            try:
                compile(code, "<string>", "exec")
                return True, None
            except SyntaxError as e:
                return False, str(e)

        elif self.language in ["javascript", "typescript"]:
            # Would need external tool like eslint or tsc
            # For now, basic validation
            if code.count("{") != code.count("}"):
                return False, "Mismatched braces"
            if code.count("(") != code.count(")"):
                return False, "Mismatched parentheses"
            return True, None

        # Default: assume valid
        return True, None

    def render_python_function(
        self,
        name: str,
        params: str,
        body: str,
        return_type: Optional[str] = None,
        docstring: Optional[str] = None,
        decorators: Optional[List[str]] = None
    ) -> str:
        """
        Render a Python function from components.

        Args:
            name: Function name
            params: Formatted parameter string
            body: Function body code
            return_type: Optional return type annotation
            docstring: Optional function docstring
            decorators: Optional list of decorator strings

        Returns:
            Complete Python function code
        """
        lines = []

        # Add decorators
        if decorators:
            for decorator in decorators:
                lines.append(f"@{decorator}")

        # Add function signature
        return_annotation = f" -> {return_type}" if return_type else ""
        lines.append(f"def {name}({params}){return_annotation}:")

        # Add docstring
        if docstring:
            if "\n" in docstring:
                lines.append(f'    """{docstring}"""')
            else:
                lines.append(f'    """{docstring}"""')

        # Add body (strip existing indentation and re-indent)
        body_lines = body.split("\n")
        for line in body_lines:
            stripped = line.lstrip()
            if stripped:
                # Preserve relative indentation
                original_indent = len(line) - len(stripped)
                relative_indent = original_indent - (len(body_lines[0]) - len(body_lines[0].lstrip()))
                indent = "    " + " " * max(0, relative_indent)
                lines.append(indent + stripped)
            else:
                lines.append("")

        return "\n".join(lines)

    def _process_conditional(self, match: re.Match[str], variables: Dict[str, str]) -> str:
        """Process conditional template blocks."""
        condition_type = match.group(1)  # 'if' or 'unless'
        var_name = match.group(2)
        content = match.group(3)

        var_value = variables.get(var_name, "")
        is_truthy = var_value and var_value.lower() not in ("false", "0", "")

        if condition_type == "if":
            return content if is_truthy else ""
        return "" if is_truthy else content  # unless

    def _process_each_loop(self, match: re.Match[str], variables: Dict[str, str], strict: bool) -> str:
        """Process each loop template blocks."""
        var_name = match.group(1)
        loop_content = match.group(2)

        if var_name not in variables:
            if strict:
                raise ValueError(f"Missing list variable: {var_name}")
            return ""

        items = variables[var_name].split(",") if variables[var_name] else []
        result = "".join(loop_content.replace("{{.}}", item.strip()) for item in items)

        # Remove trailing space if the loop content ends with a space
        if loop_content.endswith(" ") and result.endswith(" "):
            result = result.rstrip()
        return result

    def _substitute_simple_variable(self, match: re.Match[str], variables: Dict[str, str], strict: bool) -> str:
        """Substitute simple template variable."""
        var_name = match.group(1)
        if var_name not in variables:
            if strict:
                raise ValueError(f"Missing required variable: {var_name}")
            return ""
        return variables[var_name]

    def substitute_template_variables(
        self,
        template: str,
        variables: Dict[str, str],
        strict: bool = False
    ) -> str:
        """
        Substitute template variables in a string template.

        Supports:
        - Simple variables: {{name}}
        - Conditionals: {{#if var}}...{{/if}}, {{#unless var}}...{{/unless}}
        - Loops: {{#each items}}{{.}}{{/each}}

        Args:
            template: Template string with {{variable}} placeholders
            variables: Dictionary of variable values
            strict: If True, raise error on missing variables

        Returns:
            Template with variables substituted

        Raises:
            ValueError: If strict=True and required variable is missing
        """
        result = template

        # Process conditionals (if/unless)
        result = re.sub(
            r'\{\{#(if|unless)\s+(\w+)\}\}(.*?)\{\{/\1\}\}',
            lambda m: self._process_conditional(m, variables),
            result,
            flags=re.DOTALL
        )

        # Process loops {{#each items}}{{.}}{{/each}}
        result = re.sub(
            r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}',
            lambda m: self._process_each_loop(m, variables, strict),
            result,
            flags=re.DOTALL
        )

        # Process simple variables {{var}}
        result = re.sub(
            r'\{\{(\w+)\}\}',
            lambda m: self._substitute_simple_variable(m, variables, strict),
            result
        )

        return result

    def preserve_call_site_indentation(self, original_code: str, replacement: str) -> str:
        """
        Preserve the indentation from the original code when replacing it.

        Args:
            original_code: Original code with indentation
            replacement: Replacement code to indent

        Returns:
            Replacement code with original indentation preserved
        """
        if not original_code or not replacement:
            return replacement

        # Extract indentation from original
        indent = ""
        for char in original_code:
            if char in " \t":
                indent += char
            else:
                break

        # Apply indentation to replacement
        if "\n" in replacement:
            lines = replacement.split("\n")
            indented_lines = [indent + line if line.strip() else "" for line in lines]
            return "\n".join(indented_lines)
        else:
            return indent + replacement

    def detect_import_insertion_point(self, content: str, language: str) -> int:
        """
        Detect where to insert import statements in a file.

        Args:
            content: File content
            language: Programming language

        Returns:
            Line number (1-indexed) where imports should be inserted
        """
        lines = content.split("\n")

        if language == "python":
            return self._detect_python_import_point(lines)
        elif language in ["javascript", "typescript"]:
            return self._detect_js_import_point(lines)
        elif language == "java":
            return self._detect_java_import_point(lines)
        else:
            # Generic: after first line
            return 1

    def _detect_python_import_point(self, lines: List[str]) -> int:
        """Find import insertion point for Python files."""
        # Handle empty file
        if not lines or (len(lines) == 1 and not lines[0].strip()):
            return 1

        # Skip module docstring (if present)
        position = self._skip_python_module_docstring(lines, start=0)

        # Skip top-level comments
        position = self._skip_python_comments(lines, start=position)

        # Find end of existing imports
        last_import_line = self._find_last_import_line(lines, start=position)

        return last_import_line + 1

    def _skip_python_module_docstring(self, lines: List[str], start: int) -> int:
        """Skip module-level docstring and return position after it.

        Args:
            lines: List of file lines
            start: Starting position

        Returns:
            Position after docstring (or start if no docstring found)
        """
        position = start
        in_docstring = False
        docstring_quotes = None

        while position < len(lines):
            line = lines[position].strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                position += 1
                continue

            # Check for docstring start/end
            if line.startswith('"""') or line.startswith("'''"):
                quotes = line[:3]

                if not in_docstring:
                    # Starting a docstring
                    docstring_quotes = quotes
                    in_docstring = True

                    # Check if docstring closes on same line
                    if line.count(quotes) >= 2:
                        return position + 1

                elif docstring_quotes and quotes == docstring_quotes:
                    # Closing the docstring
                    return position + 1

                position += 1
                continue

            # If we're in a docstring, keep skipping
            if in_docstring:
                position += 1
                continue

            # Found non-docstring content
            break

        return position

    def _skip_python_comments(self, lines: List[str], start: int) -> int:
        """Skip comment lines and return position after comments.

        Args:
            lines: List of file lines
            start: Starting position

        Returns:
            Position after comments
        """
        position = start
        while position < len(lines) and lines[position].strip().startswith("#"):
            position += 1
        return position

    def _find_last_import_line(self, lines: List[str], start: int) -> int:
        """Find the last import statement line.

        Args:
            lines: List of file lines
            start: Starting position

        Returns:
            Position of last import (or start if no imports found)
        """
        position = start
        last_import = start

        while position < len(lines):
            line = lines[position].strip()

            # Track import statements
            if self._is_import_line(line):
                last_import = position + 1
            # Stop at first non-import, non-comment, non-empty line
            elif line and not line.startswith("#"):
                break

            position += 1

        return last_import

    def _is_import_line(self, line: str) -> bool:
        """Check if line is an import statement.

        Args:
            line: Stripped line to check

        Returns:
            True if line is an import statement
        """
        return line.startswith("import ") or line.startswith("from ")

    def _detect_js_import_point(self, lines: List[str]) -> int:
        """Find import insertion point for JavaScript/TypeScript files."""
        i = 0

        # Skip 'use strict' directive
        while i < len(lines):
            line = lines[i].strip()
            if line in ('"use strict";', "'use strict';"):
                i += 1
                # Skip blank line after directive
                if i < len(lines) and not lines[i].strip():
                    i += 1
                break
            if line:
                break
            i += 1

        # Skip existing imports
        last_import = i
        while i < len(lines):
            line = lines[i].strip()
            if (line.startswith("import ") or
                line.startswith("const ") and "require(" in line or
                line.startswith("var ") and "require(" in line):
                last_import = i + 1
            elif line and not line.startswith("//"):
                break
            i += 1

        return last_import + 1

    def _detect_java_import_point(self, lines: List[str]) -> int:
        """Find import insertion point for Java files."""
        i = 0

        # Skip package declaration
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("package "):
                i += 1
                # Skip blank lines after package
                while i < len(lines) and not lines[i].strip():
                    i += 1
                break
            if line and not line.startswith("//"):
                break
            i += 1

        # Skip existing imports
        last_import = i
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("import "):
                last_import = i + 1
            elif line and not line.startswith("//"):
                break
            i += 1

        return last_import + 1
