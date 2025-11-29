"""Code generation templates and formatting utilities.

This module provides templates and formatting functions for generating
code in various languages (Python, Java, TypeScript, JavaScript).
Used primarily by the duplication detection system for refactoring.
"""

import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional, Tuple

# =============================================================================
# Python Templates
# =============================================================================

PYTHON_CLASS_TEMPLATE: str = '''{decorators}class {name}{bases}:
{docstring}{class_vars}{methods}'''


def format_python_class(
    name: str,
    methods: str,
    decorators: Optional[str] = None,
    bases: Optional[List[str]] = None,
    docstring: Optional[str] = None,
    class_vars: Optional[str] = None,
) -> str:
    """Format a Python class using the template.

    Args:
        name: Class name
        methods: Formatted method definitions (already indented)
        decorators: Optional decorator strings (e.g., "@dataclass\\n")
        bases: Optional list of base classes for inheritance
        docstring: Optional class-level docstring
        class_vars: Optional class variable definitions

    Returns:
        Formatted Python class string
    """
    # Format decorators
    decorator_str = f"{decorators}\n" if decorators else ""

    # Format base classes
    bases_str = f"({', '.join(bases)})" if bases else ""

    # Format docstring with proper indentation
    docstring_str = f'    """{docstring}"""\n\n' if docstring else ""

    # Format class variables with proper indentation
    class_vars_str = f"{class_vars}\n\n" if class_vars else ""

    # Ensure methods are properly indented (4 spaces)
    if methods and not methods.startswith("    "):
        methods = "\n".join(f"    {line}" if line.strip() else line
                          for line in methods.split("\n"))

    return PYTHON_CLASS_TEMPLATE.format(
        decorators=decorator_str,
        name=name,
        bases=bases_str,
        docstring=docstring_str,
        class_vars=class_vars_str,
        methods=methods,
    )


# =============================================================================
# Java Templates
# =============================================================================

JAVA_METHOD_TEMPLATE: str = """{javadoc}{annotations}{modifiers}{type_params}{return_type} {name}({params}){throws} {{
{body}
}}"""


def _try_google_java_format(code: str) -> Optional[str]:
    """Try to format Java code using google-java-format.

    Args:
        code: Java source code to format

    Returns:
        Formatted code if successful, None if tool unavailable or error
    """
    if not shutil.which("google-java-format"):
        return None

    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.java', delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        result = subprocess.run(
            ["google-java-format", temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Clean up temp file
        try:
            os.unlink(temp_path)
        except OSError:
            pass

        if result.returncode == 0:
            return result.stdout

    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    return None


def _process_java_imports(lines: list[str]) -> tuple[list[str], list[str]]:
    """Separate and sort Java import statements.

    Args:
        lines: Raw code lines

    Returns:
        Tuple of (sorted_import_lines, non_import_lines)
    """
    import_lines: list[str] = []
    non_import_lines: list[str] = []
    in_imports = False

    # Separate imports from other code
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import '):
            import_lines.append(stripped)
            in_imports = True
        elif stripped.startswith('package '):
            non_import_lines.append(stripped)
        elif stripped:
            if in_imports and import_lines:
                in_imports = False
            non_import_lines.append(stripped)
        elif not in_imports:
            non_import_lines.append('')

    # Sort imports: java.* first, then javax.*, then others
    def import_sort_key(imp: str) -> tuple[int, str]:
        name = imp.replace('import ', '').replace('static ', '').strip().rstrip(';')
        if name.startswith('java.'):
            return (0, name)
        elif name.startswith('javax.'):
            return (1, name)
        else:
            return (2, name)

    import_lines.sort(key=import_sort_key)

    return import_lines, non_import_lines


def _merge_package_imports_code(
    import_lines: list[str],
    non_import_lines: list[str]
) -> list[str]:
    """Merge package declaration, imports, and code with proper spacing.

    Args:
        import_lines: Sorted import statements
        non_import_lines: Package declaration and code

    Returns:
        Merged lines with proper spacing
    """
    all_lines: list[str] = []
    found_package = False

    for line in non_import_lines:
        if line.startswith('package '):
            all_lines.append(line)
            found_package = True
            if import_lines:
                all_lines.append('')  # Blank line after package
                all_lines.extend(import_lines)
                all_lines.append('')  # Blank line after imports
        else:
            all_lines.append(line)

    if not found_package and import_lines:
        all_lines = import_lines + [''] + all_lines

    return all_lines


def _apply_java_indentation(lines: list[str]) -> str:
    """Apply consistent indentation and brace formatting.

    Args:
        lines: Code lines to format

    Returns:
        Formatted code string with proper indentation
    """
    formatted_lines: list[str] = []
    indent_level = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append('')
            continue

        # Decrease indent for closing braces
        if stripped.startswith('}') or stripped.startswith(')'):
            indent_level = max(0, indent_level - 1)

        # Handle lines that both close and open (e.g., "} else {")
        temp_indent = indent_level
        if stripped.startswith('}') and '{' in stripped:
            temp_indent = max(0, indent_level)

        # Apply indentation (4 spaces)
        formatted_line = '    ' * temp_indent + stripped

        # Ensure space before opening brace
        formatted_line = re.sub(r'(\S)\{', r'\1 {', formatted_line)

        formatted_lines.append(formatted_line)

        # Increase indent for opening braces
        open_braces = stripped.count('{') - stripped.count('}')
        indent_level = max(0, indent_level + open_braces)

    return '\n'.join(formatted_lines)


def format_java_code(code: str) -> str:
    """Format Java code using google-java-format or basic formatting fallback.

    Attempts to use google-java-format for professional formatting. Falls back
    to basic formatting rules if the tool is not available.

    Args:
        code: Java source code string to format

    Returns:
        Formatted Java code string

    Examples:
        >>> format_java_code("public class Foo{int x;}")
        'public class Foo {\\n    int x;\\n}'
    """
    # Try external formatter first
    formatted = _try_google_java_format(code)
    if formatted is not None:
        return formatted

    # Fall back to basic formatting
    lines = code.split('\n')
    import_lines, non_import_lines = _process_java_imports(lines)
    all_lines = _merge_package_imports_code(import_lines, non_import_lines)
    return _apply_java_indentation(all_lines)


def format_java_method(
    name: str,
    params: str,
    body: str,
    return_type: str = "void",
    modifiers: Optional[List[str]] = None,
    annotations: Optional[List[str]] = None,
    type_params: Optional[str] = None,
    throws: Optional[List[str]] = None,
    javadoc: Optional[str] = None,
) -> str:
    """Format a Java method using the template.

    Args:
        name: Method name
        params: Parameter list (e.g., "String name, int age")
        body: Method body (will be indented with 4 spaces)
        return_type: Return type (default: "void")
        modifiers: Optional list of modifiers ["public", "static", "final"]
        annotations: Optional list of annotations ["@Override", "@Deprecated"]
        type_params: Optional type parameters (e.g., "<T extends Comparable<T>>")
        throws: Optional list of exceptions ["IOException", "SQLException"]
        javadoc: Optional Javadoc comment (without /** */)

    Returns:
        Formatted Java method string
    """
    # Format annotations (each on its own line)
    annotations_str = ""
    if annotations:
        annotations_str = "\n".join(annotations) + "\n"

    # Format modifiers (space-separated)
    modifiers_str = ""
    if modifiers:
        modifiers_str = " ".join(modifiers) + " "

    # Format type parameters
    type_params_str = ""
    if type_params:
        type_params_str = type_params + " "

    # Format throws clause
    throws_str = ""
    if throws:
        throws_str = " throws " + ", ".join(throws)

    # Format Javadoc
    javadoc_str = ""
    if javadoc:
        javadoc_lines = javadoc.strip().split("\n")
        javadoc_str = "/**\n"
        for line in javadoc_lines:
            javadoc_str += f" * {line}\n"
        javadoc_str += " */\n"

    # Indent body with 4 spaces
    body_lines = body.strip().split("\n")
    indented_body = "\n".join("    " + line if line.strip() else "" for line in body_lines)

    return JAVA_METHOD_TEMPLATE.format(
        javadoc=javadoc_str,
        annotations=annotations_str,
        modifiers=modifiers_str,
        type_params=type_params_str,
        return_type=return_type,
        name=name,
        params=params,
        throws=throws_str,
        body=indented_body,
    )


# =============================================================================
# TypeScript Templates
# =============================================================================

TYPESCRIPT_CLASS_TEMPLATE: str = """{jsdoc}{export}{abstract}class {name}{type_params}{extends}{implements} {{
{properties}{constructor}{methods}}}
"""

TYPESCRIPT_FUNCTION_TEMPLATE: str = """{jsdoc}{export}function {name}{type_params}({params}){return_type} {{
{body}
}}"""

TYPESCRIPT_ASYNC_FUNCTION_TEMPLATE: str = """{jsdoc}{export}async function {name}{type_params}({params}){return_type} {{
{body}
}}"""

TYPESCRIPT_ARROW_FUNCTION_TEMPLATE: str = """{jsdoc}{export}const {name} = {async}{type_params}({params}){return_type} => {{
{body}
}};"""


def format_typescript_class(
    name: str,
    *,
    export: bool = False,
    abstract: bool = False,
    type_params: Optional[str] = None,
    extends: Optional[str] = None,
    implements: Optional[List[str]] = None,
    jsdoc: Optional[str] = None,
    properties: Optional[List[str]] = None,
    constructor: Optional[str] = None,
    methods: Optional[List[str]] = None,
) -> str:
    """Format a TypeScript class using the template.

    Args:
        name: Class name
        export: Whether to export the class
        abstract: Whether the class is abstract
        type_params: Generic type parameters (e.g., "<T, U>")
        extends: Parent class name
        implements: List of interface names to implement
        jsdoc: JSDoc comment block (without leading newline)
        properties: List of property declarations with indentation
        constructor: Constructor code with indentation
        methods: List of method implementations with indentation

    Returns:
        Formatted TypeScript class code
    """
    return TYPESCRIPT_CLASS_TEMPLATE.format(
        jsdoc=f"{jsdoc}\n" if jsdoc else "",
        export="export " if export else "",
        abstract="abstract " if abstract else "",
        name=name,
        type_params=type_params if type_params else "",
        extends=f" extends {extends}" if extends else "",
        implements=f" implements {', '.join(implements)}" if implements else "",
        properties="\n".join(properties) + "\n\n" if properties else "",
        constructor=constructor + "\n\n" if constructor else "",
        methods="\n\n".join(methods) + "\n" if methods else "",
    )


def _select_typescript_template(use_arrow: bool, is_async: bool) -> str:
    """Select the appropriate TypeScript function template.

    Args:
        use_arrow: Use arrow function syntax
        is_async: Function is async

    Returns:
        Template string
    """
    if use_arrow:
        return TYPESCRIPT_ARROW_FUNCTION_TEMPLATE
    if is_async:
        return TYPESCRIPT_ASYNC_FUNCTION_TEMPLATE
    return TYPESCRIPT_FUNCTION_TEMPLATE


def _format_typescript_params(params: List[Tuple[str, str]]) -> str:
    """Format TypeScript function parameters with types.

    Args:
        params: List of (param_name, param_type) tuples

    Returns:
        Formatted parameters string
    """
    return ", ".join(f"{p[0]}: {p[1]}" for p in params)


def _format_typescript_return_type(return_type: str, is_async: bool) -> str:
    """Format TypeScript return type annotation.

    Args:
        return_type: Return type annotation
        is_async: Whether function is async

    Returns:
        Formatted return type string
    """
    if not return_type:
        return ""

    if is_async and not return_type.startswith("Promise"):
        return f": Promise<{return_type}>"

    return f": {return_type}"


def _indent_function_body(body: str) -> str:
    """Indent function body with 2 spaces (JS/TS convention).

    Args:
        body: Function body to indent

    Returns:
        Indented body string
    """
    return "\n".join(f"  {line}" if line.strip() else line
                     for line in body.split("\n"))


def format_typescript_function(
    name: str,
    params: List[Tuple[str, str]],
    body: str,
    return_type: str = "void",
    export: bool = False,
    is_async: bool = False,
    type_params: Optional[List[str]] = None,
    jsdoc: Optional[str] = None,
    use_arrow: bool = False
) -> str:
    """Generate a TypeScript function from template.

    Args:
        name: Function name
        params: List of (param_name, param_type) tuples
        body: Function body (will be indented)
        return_type: Return type annotation (default "void")
        export: Whether to export the function
        is_async: Whether function is async
        type_params: Optional generic type parameters (e.g., ["T", "U"])
        jsdoc: Optional JSDoc comment block
        use_arrow: Use arrow function syntax instead of declaration

    Returns:
        Formatted TypeScript function string
    """
    # Format placeholders
    export_str = "export " if export else ""
    async_str = "async " if is_async else ""
    type_params_str = f"<{', '.join(type_params)}>" if type_params else ""
    jsdoc_str = f"{jsdoc}\n" if jsdoc else ""

    # Format parameters and return type
    params_str = _format_typescript_params(params)
    return_type_str = _format_typescript_return_type(return_type, is_async)
    indented_body = _indent_function_body(body)

    # Select template
    template = _select_typescript_template(use_arrow, is_async)

    # Format with appropriate template
    format_args = {
        "jsdoc": jsdoc_str,
        "export": export_str,
        "name": name,
        "type_params": type_params_str,
        "params": params_str,
        "return_type": return_type_str,
        "body": indented_body
    }

    # Arrow functions need the async keyword differently
    if use_arrow:
        format_args["async"] = async_str

    return template.format(**format_args)


# =============================================================================
# JavaScript Templates
# =============================================================================

JAVASCRIPT_FUNCTION_TEMPLATE: str = """{jsdoc}{export}function {name}({params}) {{
{body}
}}"""

JAVASCRIPT_ASYNC_FUNCTION_TEMPLATE: str = """{jsdoc}{export}async function {name}({params}) {{
{body}
}}"""

JAVASCRIPT_ARROW_FUNCTION_TEMPLATE: str = """{jsdoc}{export}const {name} = {async}({params}) => {{
{body}
}};"""


def _select_javascript_template(use_arrow: bool, is_async: bool) -> str:
    """Select the appropriate JavaScript function template.

    Args:
        use_arrow: Use arrow function syntax
        is_async: Function is async

    Returns:
        Template string
    """
    if use_arrow:
        return JAVASCRIPT_ARROW_FUNCTION_TEMPLATE
    if is_async:
        return JAVASCRIPT_ASYNC_FUNCTION_TEMPLATE
    return JAVASCRIPT_FUNCTION_TEMPLATE


def _format_javascript_params(params: List[str]) -> str:
    """Format JavaScript function parameters.

    Args:
        params: List of parameter names

    Returns:
        Formatted parameters string
    """
    return ", ".join(params)


def format_javascript_function(
    name: str,
    params: List[str],
    body: str,
    export: bool = False,
    is_async: bool = False,
    jsdoc: Optional[str] = None,
    use_arrow: bool = False
) -> str:
    """Generate a JavaScript function from template.

    Args:
        name: Function name
        params: List of parameter names
        body: Function body (will be indented)
        export: Whether to export the function
        is_async: Whether function is async
        jsdoc: Optional JSDoc comment block
        use_arrow: Use arrow function syntax instead of declaration

    Returns:
        Formatted JavaScript function string
    """
    # Format placeholders
    export_str = "export " if export else ""
    async_str = "async " if is_async else ""
    jsdoc_str = f"{jsdoc}\n" if jsdoc else ""

    # Format parameters and indent body
    params_str = _format_javascript_params(params)
    indented_body = _indent_function_body(body)

    # Select template
    template = _select_javascript_template(use_arrow, is_async)

    # Format with appropriate template
    format_args = {
        "jsdoc": jsdoc_str,
        "export": export_str,
        "name": name,
        "params": params_str,
        "body": indented_body
    }

    # Arrow functions need the async keyword differently
    if use_arrow:
        format_args["async"] = async_str

    return template.format(**format_args)
