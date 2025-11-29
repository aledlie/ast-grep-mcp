"""Docstring generation service.

This module provides functionality for auto-generating docstrings
from function signatures and names across multiple languages.
"""
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.documentation import (
    DocstringGenerationResult,
    DocstringStyle,
    FunctionSignature,
    GeneratedDocstring,
    ParameterInfo,
)

logger = get_logger(__name__)


# =============================================================================
# Name Inference Utilities
# =============================================================================

def _split_camel_case(name: str) -> List[str]:
    """Split camelCase or PascalCase into words.

    Args:
        name: camelCase or PascalCase string

    Returns:
        List of words
    """
    # Insert space before uppercase letters following lowercase
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    # Insert space before uppercase letters followed by lowercase (for acronyms)
    result = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', result)
    return result.split()


def _split_snake_case(name: str) -> List[str]:
    """Split snake_case into words.

    Args:
        name: snake_case string

    Returns:
        List of words
    """
    return name.split('_')


def _infer_description_from_name(name: str) -> str:
    """Infer a description from a function name.

    Uses common naming patterns to generate meaningful descriptions.

    Args:
        name: Function name

    Returns:
        Inferred description
    """
    # Split name into words
    if '_' in name:
        words = _split_snake_case(name)
    else:
        words = _split_camel_case(name)

    words = [w.lower() for w in words if w]

    if not words:
        return "Perform operation."

    # Common prefixes and their meanings
    prefix_meanings = {
        'get': 'Get',
        'set': 'Set',
        'is': 'Check if',
        'has': 'Check if has',
        'can': 'Check if can',
        'should': 'Determine if should',
        'will': 'Determine if will',
        'create': 'Create',
        'make': 'Create',
        'build': 'Build',
        'generate': 'Generate',
        'compute': 'Compute',
        'calculate': 'Calculate',
        'find': 'Find',
        'search': 'Search for',
        'fetch': 'Fetch',
        'load': 'Load',
        'save': 'Save',
        'store': 'Store',
        'write': 'Write',
        'read': 'Read',
        'parse': 'Parse',
        'format': 'Format',
        'convert': 'Convert',
        'transform': 'Transform',
        'validate': 'Validate',
        'check': 'Check',
        'verify': 'Verify',
        'process': 'Process',
        'handle': 'Handle',
        'update': 'Update',
        'delete': 'Delete',
        'remove': 'Remove',
        'add': 'Add',
        'insert': 'Insert',
        'append': 'Append',
        'init': 'Initialize',
        'initialize': 'Initialize',
        'setup': 'Set up',
        'configure': 'Configure',
        'render': 'Render',
        'display': 'Display',
        'show': 'Show',
        'hide': 'Hide',
        'enable': 'Enable',
        'disable': 'Disable',
        'start': 'Start',
        'stop': 'Stop',
        'begin': 'Begin',
        'end': 'End',
        'open': 'Open',
        'close': 'Close',
        'connect': 'Connect to',
        'disconnect': 'Disconnect from',
        'send': 'Send',
        'receive': 'Receive',
        'emit': 'Emit',
        'dispatch': 'Dispatch',
        'trigger': 'Trigger',
        'fire': 'Fire',
        'on': 'Handle',
        'do': 'Perform',
        'run': 'Run',
        'execute': 'Execute',
        'apply': 'Apply',
        'merge': 'Merge',
        'split': 'Split',
        'join': 'Join',
        'sort': 'Sort',
        'filter': 'Filter',
        'map': 'Map',
        'reduce': 'Reduce',
        'extract': 'Extract',
        'export': 'Export',
        'import': 'Import',
    }

    first_word = words[0]
    rest_words = words[1:]

    if first_word in prefix_meanings:
        verb = prefix_meanings[first_word]
        if rest_words:
            noun = ' '.join(rest_words)
            # Add article if appropriate
            if first_word in ('get', 'find', 'fetch', 'load', 'read', 'create', 'make', 'build', 'generate'):
                return f"{verb} the {noun}."
            return f"{verb} {noun}."
        return f"{verb}."

    # Default: capitalize and make sentence
    description = ' '.join(words)
    return f"{description.capitalize()}."


# Configuration for parameter name inference
_COMMON_PARAMS: Dict[str, str] = {
    'self': 'The instance', 'cls': 'The class', 'args': 'Positional arguments',
    'kwargs': 'Keyword arguments', 'path': 'The file or directory path',
    'file_path': 'Path to the file', 'dir_path': 'Path to the directory',
    'folder': 'The folder path', 'directory': 'The directory path',
    'name': 'The name', 'value': 'The value', 'key': 'The key',
    'data': 'The data', 'content': 'The content', 'text': 'The text content',
    'message': 'The message', 'config': 'Configuration settings',
    'options': 'Options dictionary', 'settings': 'Settings dictionary',
    'params': 'Parameters dictionary', 'callback': 'Callback function',
    'handler': 'Handler function', 'func': 'The function', 'fn': 'The function',
    'items': 'List of items', 'elements': 'List of elements',
    'values': 'List of values', 'result': 'The result', 'response': 'The response',
    'request': 'The request', 'req': 'The request', 'res': 'The response',
    'ctx': 'The context', 'context': 'The context', 'index': 'The index',
    'idx': 'The index', 'i': 'The index', 'j': 'Secondary index',
    'k': 'Tertiary index', 'n': 'The count or number', 'count': 'The count',
    'size': 'The size', 'length': 'The length', 'width': 'The width',
    'height': 'The height', 'x': 'The x coordinate', 'y': 'The y coordinate',
    'z': 'The z coordinate', 'start': 'The start value', 'end': 'The end value',
    'begin': 'The beginning value', 'limit': 'The limit', 'offset': 'The offset',
    'timeout': 'Timeout in seconds', 'delay': 'Delay in milliseconds',
    'interval': 'Interval duration', 'id': 'The unique identifier',
    'user_id': 'The user identifier', 'user': 'The user object',
    'username': 'The username', 'password': 'The password',
    'email': 'The email address', 'url': 'The URL', 'uri': 'The URI',
    'host': 'The host address', 'port': 'The port number',
    'language': 'The programming language', 'lang': 'The language code',
    'locale': 'The locale', 'format': 'The format string', 'pattern': 'The pattern',
    'regex': 'The regular expression', 'template': 'The template',
    'style': 'The style', 'mode': 'The mode', 'type': 'The type',
    'kind': 'The kind', 'level': 'The level', 'severity': 'The severity level',
    'priority': 'The priority', 'status': 'The status', 'state': 'The state',
    'flag': 'Boolean flag', 'enabled': 'Whether enabled',
    'disabled': 'Whether disabled', 'active': 'Whether active',
    'visible': 'Whether visible', 'hidden': 'Whether hidden',
    'readonly': 'Whether read-only', 'required': 'Whether required',
    'optional': 'Whether optional', 'force': 'Whether to force the operation',
    'recursive': 'Whether to process recursively',
    'verbose': 'Whether to output verbose information',
    'debug': 'Whether in debug mode', 'quiet': 'Whether to suppress output',
    'silent': 'Whether to be silent', 'dry_run': 'Whether to perform a dry run only',
    'overwrite': 'Whether to overwrite existing', 'append': 'Whether to append',
    'include': 'Items to include', 'exclude': 'Items to exclude',
    'filter': 'Filter function or criteria', 'sort': 'Sort criteria',
    'order': 'Sort order', 'ascending': 'Whether ascending order',
    'descending': 'Whether descending order', 'reverse': 'Whether to reverse',
    'max': 'Maximum value', 'min': 'Minimum value', 'default': 'Default value',
    'fallback': 'Fallback value', 'encoding': 'Character encoding',
    'charset': 'Character set', 'separator': 'The separator',
    'delimiter': 'The delimiter', 'prefix': 'The prefix', 'suffix': 'The suffix',
    'header': 'The header', 'footer': 'The footer', 'title': 'The title',
    'label': 'The label', 'description': 'The description', 'error': 'The error',
    'exception': 'The exception', 'logger': 'The logger instance', 'log': 'The log',
}

# Suffix patterns: (suffix, template) - template uses {base} placeholder
_SUFFIX_PATTERNS: List[Tuple[str, str]] = [
    ('_id', 'The {base} identifier'),
    ('_name', 'The {base} name'),
    ('_path', 'Path to the {base}'),
    ('_file', 'The {base} file'),
    ('_directory', 'The {base} directory'),
    ('_dir', 'The {base} directory'),
    ('_list', 'List of {base}'),
    ('_array', 'List of {base}'),
    ('_dict', 'Dictionary of {base}'),
    ('_map', 'Dictionary of {base}'),
    ('_count', 'Number of {base}'),
    ('_num', 'Number of {base}'),
    ('_callback', 'Callback for {base}'),
    ('_handler', 'Callback for {base}'),
    ('_config', 'Configuration for {base}'),
    ('_options', 'Configuration for {base}'),
]

# Prefix patterns: (prefix, template) - template uses {rest} placeholder
_PREFIX_PATTERNS: List[Tuple[str, str]] = [
    ('is_', 'Whether {rest}'),
    ('has_', 'Whether {rest}'),
    ('can_', 'Whether {rest}'),
    ('num_', 'Number of {rest}'),
    ('n_', 'Number of {rest}'),
    ('max_', 'Maximum {rest}'),
    ('min_', 'Minimum {rest}'),
]


def _check_suffix_pattern(name: str) -> Optional[str]:
    """Check if name matches a suffix pattern."""
    for suffix, template in _SUFFIX_PATTERNS:
        if name.endswith(suffix):
            base = name[:-len(suffix)].replace('_', ' ')
            return template.format(base=base)
    return None


def _check_prefix_pattern(name: str) -> Optional[str]:
    """Check if name matches a prefix pattern."""
    for prefix, template in _PREFIX_PATTERNS:
        if name.startswith(prefix):
            rest = name[len(prefix):].replace('_', ' ')
            return template.format(rest=rest)
    return None


def _infer_parameter_description(param: ParameterInfo, function_context: str = "") -> str:
    """Infer a description for a parameter.

    Args:
        param: Parameter information
        function_context: Optional function name for context

    Returns:
        Inferred description
    """
    name = param.name.lower()

    # Check exact match first
    if name in _COMMON_PARAMS:
        return _COMMON_PARAMS[name]

    # Check suffix patterns
    suffix_result = _check_suffix_pattern(name)
    if suffix_result:
        return suffix_result

    # Check prefix patterns
    prefix_result = _check_prefix_pattern(name)
    if prefix_result:
        return prefix_result

    # Default: use parameter name as description
    readable = param.name.replace('_', ' ')
    return f"The {readable}"


# Return description patterns based on function prefix
_RETURN_PREFIX_HANDLERS: Dict[str, str] = {
    'get': 'The {rest}', 'fetch': 'The {rest}', 'load': 'The {rest}',
    'read': 'The {rest}', 'find': 'The {rest}', 'search': 'The {rest}',
    'create': 'The created {rest}', 'make': 'The created {rest}',
    'build': 'The created {rest}', 'generate': 'The created {rest}',
    'calculate': 'The calculated {rest}', 'compute': 'The calculated {rest}',
    'count': 'The number of {rest}',
}

_BOOLEAN_PREFIXES = frozenset({'is', 'has', 'can', 'should', 'will'})

# Return type to description mapping
_RETURN_TYPE_DESCRIPTIONS: Dict[str, str] = {
    'list': 'List of results', 'array': 'List of results',
    'dict': 'Dictionary with results', 'bool': 'True if successful, False otherwise',
    'str': 'The resulting string', 'int': 'The resulting integer',
    'float': 'The resulting number',
}


def _get_return_from_type(return_type: str) -> str:
    """Get return description from type annotation."""
    type_lower = return_type.lower()
    for key, desc in _RETURN_TYPE_DESCRIPTIONS.items():
        if key in type_lower:
            return desc
    return f"The {return_type}"


def _infer_return_description(return_type: Optional[str], function_name: str) -> str:
    """Infer return value description.

    Args:
        return_type: Return type annotation
        function_name: Function name for context

    Returns:
        Inferred return description
    """
    # Get function words
    words = _split_snake_case(function_name) if '_' in function_name else _split_camel_case(function_name)
    words = [w.lower() for w in words if w]
    if not words:
        return "The result"

    first_word = words[0]
    rest = ' '.join(words[1:]) if len(words) > 1 else ''

    # Handle boolean prefixes
    if first_word in _BOOLEAN_PREFIXES:
        return f"True if {rest}, False otherwise" if rest else "Boolean result"

    # Handle other prefixes with configuration
    if first_word in _RETURN_PREFIX_HANDLERS:
        template = _RETURN_PREFIX_HANDLERS[first_word]
        if rest:
            return template.format(rest=rest)
        if return_type:
            return template.format(rest=return_type.lower())
        return template.format(rest='result')

    # Default based on return type
    if return_type:
        return _get_return_from_type(return_type)

    return "The result"


# =============================================================================
# Function Signature Parser
# =============================================================================

class FunctionSignatureParser:
    """Parse function signatures from source code."""

    def __init__(self, language: str) -> None:
        """Initialize parser for specific language.

        Args:
            language: Programming language
        """
        self.language = language

    def parse_file(self, file_path: str) -> List[FunctionSignature]:
        """Parse all function signatures from a file.

        Args:
            file_path: Path to source file

        Returns:
            List of parsed function signatures
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if self.language == "python":
            return self._parse_python_functions(content, file_path)
        elif self.language in ("typescript", "javascript"):
            return self._parse_js_ts_functions(content, file_path)
        elif self.language == "java":
            return self._parse_java_functions(content, file_path)

        return []

    def _parse_python_functions(self, content: str, file_path: str) -> List[FunctionSignature]:
        """Parse Python function signatures."""
        functions = []
        lines = content.split('\n')

        # Pattern for function definitions
        func_pattern = re.compile(
            r'^(\s*)(async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?\s*:'
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.match(line)

            if match:
                indent, is_async, name, params_str, return_type = match.groups()
                start_line = i + 1

                # Check if this is a method (indented)
                is_method = bool(indent)

                # Get decorators (lines before function def)
                decorators = []
                j = i - 1
                while j >= 0 and lines[j].strip().startswith('@'):
                    decorator = lines[j].strip()[1:].split('(')[0]
                    decorators.insert(0, decorator)
                    j -= 1

                # Parse parameters
                parameters = self._parse_python_params(params_str)

                # Find existing docstring
                existing_docstring = self._find_python_docstring(lines, i + 1)

                # Find end of function (next function or dedent)
                end_line = self._find_python_function_end(lines, i, indent)

                func = FunctionSignature(
                    name=name,
                    parameters=parameters,
                    return_type=return_type.strip() if return_type else None,
                    is_async=bool(is_async),
                    is_method=is_method,
                    decorators=decorators,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    existing_docstring=existing_docstring,
                )
                functions.append(func)

            i += 1

        return functions

    def _parse_python_params(self, params_str: str) -> List[ParameterInfo]:
        """Parse Python function parameters."""
        params = []
        if not params_str.strip():
            return params

        # Handle multi-line and nested brackets
        params_str = re.sub(r'\s+', ' ', params_str)

        # Split by comma (careful with nested brackets)
        parts = []
        depth = 0
        current = []

        for char in params_str:
            if char in '([{':
                depth += 1
                current.append(char)
            elif char in ')]}':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current).strip())

        for part in parts:
            if not part:
                continue

            # Parse parameter
            param = self._parse_single_python_param(part)
            if param:
                params.append(param)

        return params

    def _parse_single_python_param(self, part: str) -> Optional[ParameterInfo]:
        """Parse a single Python parameter."""
        # Handle *args, **kwargs
        if part.startswith('**'):
            return ParameterInfo(name=part[2:], type_hint='Dict[str, Any]')
        if part.startswith('*'):
            return ParameterInfo(name=part[1:], type_hint='Tuple[Any, ...]')

        # Split by default value
        if '=' in part:
            name_type, default = part.rsplit('=', 1)
            default = default.strip()
        else:
            name_type = part
            default = None

        # Split by type hint
        if ':' in name_type:
            name, type_hint = name_type.split(':', 1)
            name = name.strip()
            type_hint = type_hint.strip()
        else:
            name = name_type.strip()
            type_hint = None

        if not name:
            return None

        return ParameterInfo(
            name=name,
            type_hint=type_hint,
            default_value=default,
        )

    def _find_python_docstring(self, lines: List[str], func_line: int) -> Optional[str]:
        """Find existing docstring after function definition."""
        # Look at the line(s) after the function def
        if func_line >= len(lines):
            return None

        next_idx = func_line
        # Skip to next non-empty line
        while next_idx < len(lines) and not lines[next_idx].strip():
            next_idx += 1

        if next_idx >= len(lines):
            return None

        next_line = lines[next_idx].strip()

        # Check for docstring start
        if next_line.startswith('"""') or next_line.startswith("'''"):
            quote = next_line[:3]
            if next_line.endswith(quote) and len(next_line) > 6:
                # Single-line docstring
                return next_line[3:-3]

            # Multi-line docstring
            docstring_lines = [next_line[3:]]
            next_idx += 1
            while next_idx < len(lines):
                line = lines[next_idx]
                if quote in line:
                    docstring_lines.append(line[:line.index(quote)])
                    break
                docstring_lines.append(line)
                next_idx += 1

            return '\n'.join(docstring_lines).strip()

        return None

    def _find_python_function_end(self, lines: List[str], start: int, indent: str) -> int:
        """Find the end line of a Python function."""
        indent_len = len(indent)
        i = start + 1

        while i < len(lines):
            line = lines[i]
            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Check indentation
            current_indent = len(line) - len(line.lstrip())

            # If we hit a line with same or less indentation, function ended
            if current_indent <= indent_len and line.strip():
                return i

            i += 1

        return len(lines)

    def _parse_js_ts_functions(self, content: str, file_path: str) -> List[FunctionSignature]:
        """Parse JavaScript/TypeScript function signatures."""
        functions = []
        lines = content.split('\n')

        # Patterns for different function styles
        patterns = [
            # async function name(params): ReturnType
            re.compile(r'^\s*(export\s+)?(async\s+)?function\s+(\w+)\s*\((.*?)\)(?:\s*:\s*(.+?))?\s*\{'),
            # const name = (params): ReturnType =>
            re.compile(r'^\s*(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\((.*?)\)(?:\s*:\s*(.+?))?\s*=>'),
            # class method: name(params): ReturnType
            re.compile(r'^\s*(async\s+)?(\w+)\s*\((.*?)\)(?:\s*:\s*(.+?))?\s*\{'),
        ]

        for i, line in enumerate(lines):
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    groups = match.groups()

                    # Parse based on pattern type
                    if len(groups) == 5:  # Regular function
                        _, is_async, name, params_str, return_type = groups
                    elif len(groups) == 6:  # Arrow function
                        _, _, name, is_async, params_str, return_type = groups
                    else:  # Method
                        is_async, name, params_str, return_type = groups

                    if name in ('if', 'for', 'while', 'switch', 'catch'):
                        continue

                    parameters = self._parse_js_ts_params(params_str or '')

                    func = FunctionSignature(
                        name=name,
                        parameters=parameters,
                        return_type=return_type.strip() if return_type else None,
                        is_async=bool(is_async),
                        is_method=False,
                        file_path=file_path,
                        start_line=i + 1,
                        end_line=i + 1,
                    )
                    functions.append(func)
                    break

        return functions

    def _parse_js_ts_params(self, params_str: str) -> List[ParameterInfo]:
        """Parse JavaScript/TypeScript function parameters."""
        params = []
        if not params_str.strip():
            return params

        # Split by comma (simple version)
        parts = params_str.split(',')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Handle default values
            if '=' in part:
                name_type, default = part.split('=', 1)
                default = default.strip()
            else:
                name_type = part
                default = None

            # Handle type annotations
            if ':' in name_type:
                name, type_hint = name_type.split(':', 1)
                name = name.strip().lstrip('...')  # Handle rest params
                type_hint = type_hint.strip()
            else:
                name = name_type.strip().lstrip('...')
                type_hint = None

            if name:
                params.append(ParameterInfo(
                    name=name,
                    type_hint=type_hint,
                    default_value=default,
                ))

        return params

    def _parse_java_functions(self, content: str, file_path: str) -> List[FunctionSignature]:
        """Parse Java method signatures."""
        functions = []
        lines = content.split('\n')

        # Pattern for Java methods
        pattern = re.compile(
            r'^\s*(public|private|protected)?\s*(static\s+)?([\w<>,\s]+)\s+(\w+)\s*\((.*?)\)\s*(throws\s+[\w,\s]+)?\s*\{'
        )

        for i, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                _, _, return_type, name, params_str, _ = match.groups()

                # Skip constructors and control statements
                if name in ('if', 'for', 'while', 'switch', 'catch', 'try'):
                    continue

                parameters = self._parse_java_params(params_str or '')

                func = FunctionSignature(
                    name=name,
                    parameters=parameters,
                    return_type=return_type.strip() if return_type else None,
                    is_method=True,
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=i + 1,
                )
                functions.append(func)

        return functions

    def _parse_java_params(self, params_str: str) -> List[ParameterInfo]:
        """Parse Java method parameters."""
        params = []
        if not params_str.strip():
            return params

        # Split by comma
        parts = params_str.split(',')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Java params are: Type name or final Type name
            parts_split = part.split()
            if len(parts_split) >= 2:
                name = parts_split[-1]
                type_hint = ' '.join(parts_split[:-1])
                params.append(ParameterInfo(name=name, type_hint=type_hint))

        return params


# =============================================================================
# Docstring Templates
# =============================================================================

def _generate_google_docstring(func: FunctionSignature) -> str:
    """Generate Google-style docstring."""
    lines = []

    # Description
    description = _infer_description_from_name(func.name)
    lines.append(f'"""{description}')

    # Add Args section if there are parameters
    non_self_params = [p for p in func.parameters if p.name not in ('self', 'cls')]
    if non_self_params:
        lines.append('')
        lines.append('Args:')
        for param in non_self_params:
            desc = _infer_parameter_description(param, func.name)
            if param.type_hint:
                lines.append(f'    {param.name} ({param.type_hint}): {desc}')
            else:
                lines.append(f'    {param.name}: {desc}')

    # Add Returns section if there's a return type and it's not None/void
    if func.return_type and func.return_type.lower() not in ('none', 'void'):
        lines.append('')
        lines.append('Returns:')
        return_desc = _infer_return_description(func.return_type, func.name)
        lines.append(f'    {func.return_type}: {return_desc}')

    lines.append('"""')
    return '\n'.join(lines)


def _generate_numpy_docstring(func: FunctionSignature) -> str:
    """Generate NumPy-style docstring."""
    lines = []

    # Description
    description = _infer_description_from_name(func.name)
    lines.append(f'"""')
    lines.append(description)

    # Add Parameters section
    non_self_params = [p for p in func.parameters if p.name not in ('self', 'cls')]
    if non_self_params:
        lines.append('')
        lines.append('Parameters')
        lines.append('----------')
        for param in non_self_params:
            desc = _infer_parameter_description(param, func.name)
            type_str = param.type_hint or 'any'
            lines.append(f'{param.name} : {type_str}')
            lines.append(f'    {desc}')

    # Add Returns section
    if func.return_type and func.return_type.lower() not in ('none', 'void'):
        lines.append('')
        lines.append('Returns')
        lines.append('-------')
        return_desc = _infer_return_description(func.return_type, func.name)
        lines.append(f'{func.return_type}')
        lines.append(f'    {return_desc}')

    lines.append('"""')
    return '\n'.join(lines)


def _generate_sphinx_docstring(func: FunctionSignature) -> str:
    """Generate Sphinx-style docstring."""
    lines = []

    # Description
    description = _infer_description_from_name(func.name)
    lines.append(f'"""{description}')

    # Add :param: entries
    non_self_params = [p for p in func.parameters if p.name not in ('self', 'cls')]
    if non_self_params:
        lines.append('')
        for param in non_self_params:
            desc = _infer_parameter_description(param, func.name)
            if param.type_hint:
                lines.append(f':param {param.name}: {desc}')
                lines.append(f':type {param.name}: {param.type_hint}')
            else:
                lines.append(f':param {param.name}: {desc}')

    # Add :return:
    if func.return_type and func.return_type.lower() not in ('none', 'void'):
        lines.append('')
        return_desc = _infer_return_description(func.return_type, func.name)
        lines.append(f':return: {return_desc}')
        lines.append(f':rtype: {func.return_type}')

    lines.append('"""')
    return '\n'.join(lines)


def _generate_jsdoc(func: FunctionSignature) -> str:
    """Generate JSDoc-style documentation."""
    lines = ['/**']

    # Description
    description = _infer_description_from_name(func.name)
    lines.append(f' * {description}')

    # Add @param entries
    if func.parameters:
        lines.append(' *')
        for param in func.parameters:
            desc = _infer_parameter_description(param, func.name)
            type_str = param.type_hint or '*'
            if param.default_value is not None:
                lines.append(f' * @param {{{type_str}}} [{param.name}={param.default_value}] - {desc}')
            else:
                lines.append(f' * @param {{{type_str}}} {param.name} - {desc}')

    # Add @returns
    if func.return_type and func.return_type.lower() not in ('void', 'undefined'):
        lines.append(' *')
        return_desc = _infer_return_description(func.return_type, func.name)
        lines.append(f' * @returns {{{func.return_type}}} {return_desc}')

    # Add @async if applicable
    if func.is_async:
        lines.append(' * @async')

    lines.append(' */')
    return '\n'.join(lines)


def _generate_javadoc(func: FunctionSignature) -> str:
    """Generate Javadoc-style documentation."""
    lines = ['/**']

    # Description
    description = _infer_description_from_name(func.name)
    lines.append(f' * {description}')

    # Add @param entries
    if func.parameters:
        lines.append(' *')
        for param in func.parameters:
            desc = _infer_parameter_description(param, func.name)
            lines.append(f' * @param {param.name} {desc}')

    # Add @return
    if func.return_type and func.return_type.lower() not in ('void'):
        lines.append(' *')
        return_desc = _infer_return_description(func.return_type, func.name)
        lines.append(f' * @return {return_desc}')

    lines.append(' */')
    return '\n'.join(lines)


# =============================================================================
# Main Generator
# =============================================================================

def _detect_project_style(project_folder: str, language: str) -> DocstringStyle:
    """Auto-detect docstring style from existing code.

    Args:
        project_folder: Project root
        language: Programming language

    Returns:
        Detected style or default for language
    """
    # Check existing docstrings in the project
    style_counts = {style: 0 for style in DocstringStyle}

    # Default styles by language
    defaults = {
        'python': DocstringStyle.GOOGLE,
        'typescript': DocstringStyle.JSDOC,
        'javascript': DocstringStyle.JSDOC,
        'java': DocstringStyle.JAVADOC,
    }

    # Could implement scanning here - for now return default
    return defaults.get(language, DocstringStyle.GOOGLE)


def _generate_docstring_for_function(
    func: FunctionSignature,
    style: DocstringStyle,
    language: str,
) -> GeneratedDocstring:
    """Generate docstring for a single function.

    Args:
        func: Function signature
        style: Docstring style
        language: Programming language

    Returns:
        Generated docstring
    """
    # Select generator based on style
    generators = {
        DocstringStyle.GOOGLE: _generate_google_docstring,
        DocstringStyle.NUMPY: _generate_numpy_docstring,
        DocstringStyle.SPHINX: _generate_sphinx_docstring,
        DocstringStyle.JSDOC: _generate_jsdoc,
        DocstringStyle.JAVADOC: _generate_javadoc,
    }

    generator = generators.get(style, _generate_google_docstring)
    docstring = generator(func)

    return GeneratedDocstring(
        function_name=func.name,
        file_path=func.file_path,
        line_number=func.start_line,
        docstring=docstring,
        style=style,
        confidence=0.8,  # Basic inference confidence
        inferred_description=True,
    )


def _should_skip_function(func: FunctionSignature, skip_private: bool = True) -> Tuple[bool, str]:
    """Check if function should be skipped.

    Args:
        func: Function signature
        skip_private: Whether to skip private functions

    Returns:
        Tuple of (should_skip, reason)
    """
    # Skip private functions if requested
    if skip_private and func.name.startswith('_') and not func.name.startswith('__'):
        return True, "private function"

    # Skip dunder methods except __init__
    if func.name.startswith('__') and func.name.endswith('__') and func.name != '__init__':
        return True, "dunder method"

    return False, ""


def _apply_docstring_to_file(
    file_path: str,
    docstrings: List[GeneratedDocstring],
    language: str,
) -> bool:
    """Apply generated docstrings to a file.

    Args:
        file_path: Path to file
        docstrings: Docstrings to apply (sorted by line number descending)
        language: Programming language

    Returns:
        True if file was modified
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Sort by line number descending to avoid line number shifts
    sorted_docstrings = sorted(docstrings, key=lambda d: d.line_number, reverse=True)

    modified = False
    for doc in sorted_docstrings:
        line_idx = doc.line_number - 1
        if line_idx < len(lines):
            # Find indentation
            func_line = lines[line_idx]
            indent = len(func_line) - len(func_line.lstrip())
            indent_str = func_line[:indent]

            # For Python, add indent to each line of docstring
            if language == "python":
                # Add extra indent for docstring inside function
                body_indent = indent_str + "    "
                docstring_lines = doc.docstring.split('\n')
                indented_lines = [body_indent + line if line else line for line in docstring_lines]
                formatted_docstring = '\n'.join(indented_lines) + '\n'

                # Insert after function definition
                insert_idx = line_idx + 1
                lines.insert(insert_idx, formatted_docstring)
            else:
                # For JS/Java, add docstring before function
                body_indent = indent_str
                docstring_lines = doc.docstring.split('\n')
                indented_lines = [body_indent + line if line else line for line in docstring_lines]
                formatted_docstring = '\n'.join(indented_lines) + '\n'

                lines.insert(line_idx, formatted_docstring)

            modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    return modified


def generate_docstrings_impl(
    project_folder: str,
    file_pattern: str,
    language: str,
    style: str = "auto",
    overwrite_existing: bool = False,
    dry_run: bool = True,
    skip_private: bool = True,
) -> DocstringGenerationResult:
    """Generate docstrings for undocumented functions.

    Args:
        project_folder: Root folder of the project
        file_pattern: Glob pattern for files to process (e.g., "**/*.py")
        language: Programming language
        style: Docstring style (google, numpy, sphinx, jsdoc, javadoc, auto)
        overwrite_existing: Whether to overwrite existing docstrings
        dry_run: If True, only preview without applying
        skip_private: Whether to skip private functions

    Returns:
        DocstringGenerationResult with generated docstrings
    """
    start_time = time.time()

    logger.info(
        "generate_docstrings_started",
        project_folder=project_folder,
        file_pattern=file_pattern,
        language=language,
        style=style,
        dry_run=dry_run,
    )

    # Determine style
    if style == "auto":
        doc_style = _detect_project_style(project_folder, language)
    else:
        doc_style = DocstringStyle(style)

    # Find files matching pattern
    import glob
    pattern_path = os.path.join(project_folder, file_pattern)
    files = glob.glob(pattern_path, recursive=True)

    parser = FunctionSignatureParser(language)

    total_functions = 0
    functions_documented = 0
    functions_generated = 0
    functions_skipped = 0
    all_docstrings: List[GeneratedDocstring] = []
    files_modified: List[str] = []

    # Group docstrings by file for batch application
    docstrings_by_file: Dict[str, List[GeneratedDocstring]] = {}

    for file_path in files:
        try:
            functions = parser.parse_file(file_path)
            total_functions += len(functions)

            for func in functions:
                # Check if should skip
                should_skip, reason = _should_skip_function(func, skip_private)
                if should_skip:
                    functions_skipped += 1
                    continue

                # Check existing docstring
                if func.existing_docstring and not overwrite_existing:
                    functions_documented += 1
                    continue

                # Generate docstring
                docstring = _generate_docstring_for_function(func, doc_style, language)
                all_docstrings.append(docstring)
                functions_generated += 1

                # Group by file
                if file_path not in docstrings_by_file:
                    docstrings_by_file[file_path] = []
                docstrings_by_file[file_path].append(docstring)

        except Exception as e:
            logger.warning("file_parse_error", file=file_path, error=str(e))
            sentry_sdk.capture_exception(e)
            continue

    # Apply docstrings if not dry run
    if not dry_run:
        for file_path, docstrings in docstrings_by_file.items():
            try:
                if _apply_docstring_to_file(file_path, docstrings, language):
                    files_modified.append(file_path)
            except Exception as e:
                logger.error("file_write_error", file=file_path, error=str(e))
                sentry_sdk.capture_exception(e)

    execution_time = int((time.time() - start_time) * 1000)

    logger.info(
        "generate_docstrings_completed",
        total_functions=total_functions,
        functions_generated=functions_generated,
        functions_documented=functions_documented,
        functions_skipped=functions_skipped,
        files_modified=len(files_modified),
        execution_time_ms=execution_time,
    )

    return DocstringGenerationResult(
        total_functions=total_functions,
        functions_documented=functions_documented,
        functions_generated=functions_generated,
        functions_skipped=functions_skipped,
        docstrings=all_docstrings,
        files_modified=files_modified,
        dry_run=dry_run,
        execution_time_ms=execution_time,
    )
