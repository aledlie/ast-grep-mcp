"""
Code generation module for deduplication refactoring.

This module provides functionality for generating refactored code,
including function extraction, parameter inference, and import generation.
"""

import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

from ...core.logging import get_logger


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

        # template = self.templates.get_function_template(self.language)  # TODO: Implement templates

        # Format parameters
        if self.language == "python":
            param_list = self._format_python_parameters(parameters)
            return_annotation = f" -> {return_type}" if return_type else ""

            function_code = f"def {function_name}({param_list}){return_annotation}:\n"

            if docstring:
                function_code += f'    """{docstring}"""\n'

            # Indent body
            indented_body = "\n".join(f"    {line}" for line in body.split("\n"))
            function_code += indented_body

        elif self.language in ["javascript", "typescript"]:
            param_list = self._format_js_parameters(parameters)
            type_annotation = f": {return_type}" if return_type and self.language == "typescript" else ""

            function_code = f"function {function_name}({param_list}){type_annotation} {{\n"

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

        return function_code  # TODO: Add code formatting

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
            module_code.append(f'"""')
            module_code.append(f'{module_name} - Extracted common functionality')
            module_code.append(f'"""')
            module_code.append('')

        elif self.language in ["javascript", "typescript"]:
            module_code.append(f'/**')
            module_code.append(f' * {module_name} - Extracted common functionality')
            module_code.append(f' */')
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