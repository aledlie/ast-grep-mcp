"""
Code generation module for deduplication refactoring.

This module provides functionality for generating refactored code,
including function extraction, parameter inference, and import generation.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ...core.logging import get_logger
from ...models.deduplication import FunctionTemplate
from ...utils.formatters import format_generated_code


class CodeGenerator:
    """Generates refactored code for deduplication."""

    def __init__(self, language: str = "python"):
        """Initialize the code generator.

        Args:
            language: Programming language for code generation
        """
        self.language = language
        self.logger = get_logger("deduplication.generator")

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

        # Use template system for Python
        if self.language == "python":
            # Convert parameter dicts to tuples for FunctionTemplate
            param_tuples = [
                (p["name"], p.get("type"))
                for p in parameters
            ]

            # Create and use template
            template = FunctionTemplate(
                name=function_name,
                parameters=param_tuples,
                body=body,
                return_type=return_type,
                docstring=docstring
            )

            function_code = template.generate()

        elif self.language in ["javascript", "typescript"]:
            # Use render function for JS/TS
            param_list = self._format_js_parameters(parameters)
            type_annotation = f": {return_type}" if return_type and self.language == "typescript" else ""

            function_code = f"function {function_name}({param_list}){type_annotation} {{\n"

            if docstring:
                function_code += f"    // {docstring}\n"

            # Indent body
            indented_body = "\n".join(f"    {line}" for line in body.split("\n"))
            function_code += indented_body + "\n}"

        elif self.language == "java":
            # Java method generation
            param_list = ", ".join(
                f"{p.get('type', 'Object')} {p['name']}"
                for p in parameters
            )
            return_annotation = return_type if return_type else "void"

            function_code = f"public {return_annotation} {function_name}({param_list}) {{\n"

            if docstring:
                function_code += f"    // {docstring}\n"

            # Indent body
            indented_body = "\n".join(f"    {line}" for line in body.split("\n"))
            function_code += indented_body + "\n}"

        else:
            # Generic function format
            param_list = ", ".join(p["name"] for p in parameters)
            function_code = f"function {function_name}({param_list}) {{\n"
            function_code += body + "\n}"

        # Format the generated code before returning
        try:
            function_code = format_generated_code(function_code, self.language)
            self.logger.info(
                "formatted_generated_function",
                function_name=function_name,
                language=self.language
            )
        except Exception as e:
            # If formatting fails, return unformatted code
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

    def _infer_parameter_type(self, variation: Dict[str, Any]) -> Optional[str]:
        """Infer parameter type from variation."""
        category = variation.get("category", "")
        value = variation.get("old_value", "")

        if self.language == "python":
            if category == "literal":
                if variation.get("literal_type") == "string":
                    return "str"
                elif variation.get("literal_type") == "number":
                    return "int" if "." not in value else "float"
                elif variation.get("literal_type") == "boolean":
                    return "bool"
            elif category == "identifier":
                return "Any"  # Will be refined based on usage
            elif category == "type":
                return value  # Use the actual type

        elif self.language == "typescript":
            if category == "literal":
                if variation.get("literal_type") == "string":
                    return "string"
                elif variation.get("literal_type") == "number":
                    return "number"
                elif variation.get("literal_type") == "boolean":
                    return "boolean"
            elif category == "identifier":
                return "any"

        return None

    def _find_external_dependencies(self, code: str) -> List[str]:
        """Find external dependencies that should be parameters."""
        dependencies = []

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
        def process_conditional(match: re.Match[str]) -> str:
            condition_type = match.group(1)  # 'if' or 'unless'
            var_name = match.group(2)
            content = match.group(3)

            var_value = variables.get(var_name, "")
            is_truthy = var_value and var_value.lower() not in ("false", "0", "")

            if condition_type == "if":
                return content if is_truthy else ""
            else:  # unless
                return "" if is_truthy else content

        # Process {{#if var}}...{{/if}} and {{#unless var}}...{{/unless}}
        result = re.sub(
            r'\{\{#(if|unless)\s+(\w+)\}\}(.*?)\{\{/\1\}\}',
            process_conditional,
            result,
            flags=re.DOTALL
        )

        # Process loops {{#each items}}{{.}}{{/each}}
        def process_each(match: re.Match[str]) -> str:
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

        result = re.sub(
            r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}',
            process_each,
            result,
            flags=re.DOTALL
        )

        # Process simple variables {{var}}
        def substitute_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name not in variables:
                if strict:
                    raise ValueError(f"Missing required variable: {var_name}")
                return ""
            return variables[var_name]

        result = re.sub(r'\{\{(\w+)\}\}', substitute_var, result)

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

        i = 0
        in_docstring = False
        docstring_quotes = None

        # Skip module docstring
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue

            # Check for docstring
            if line.startswith('"""') or line.startswith("'''"):
                if not in_docstring:
                    docstring_quotes = line[:3]
                    in_docstring = True
                    if line.count(docstring_quotes) >= 2:
                        in_docstring = False
                        i += 1
                        break
                elif docstring_quotes in line:
                    in_docstring = False
                    i += 1
                    break
                i += 1
                continue

            if in_docstring:
                i += 1
                continue

            break

        # Skip comments
        while i < len(lines) and lines[i].strip().startswith("#"):
            i += 1

        # Skip existing imports
        last_import = i
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("import ") or line.startswith("from "):
                last_import = i + 1
            elif line and not line.startswith("#"):
                break
            i += 1

        return last_import + 1

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
