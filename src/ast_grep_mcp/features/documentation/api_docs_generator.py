"""API documentation generation service.

This module provides functionality for generating API documentation
from route definitions across different web frameworks.
"""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.documentation import (
    ApiDocsResult,
    ApiRoute,
    RouteParameter,
    RouteResponse,
)

logger = get_logger(__name__)


# =============================================================================
# Framework Detection
# =============================================================================

# JS API frameworks: (dep_key, framework_name)
_JS_API_FRAMEWORKS: List[Tuple[str, str]] = [
    ('express', 'express'),
    ('fastify', 'fastify'),
    ('@nestjs/core', 'nestjs'),
    ('koa', 'koa'),
    ('hono', 'hono'),
]

# Python API frameworks: (pattern, framework_name) - order matters (first match wins)
_PYTHON_API_FRAMEWORKS: List[Tuple[str, str]] = [
    ('fastapi', 'fastapi'),
    ('flask', 'flask'),
    ('django', 'django'),
    ('starlette', 'starlette'),
]


def _detect_js_api_framework(project_folder: str) -> Optional[str]:
    """Detect JavaScript API framework from package.json.

    Args:
        project_folder: Project root

    Returns:
        Framework name or None
    """
    package_json = os.path.join(project_folder, 'package.json')
    if not os.path.exists(package_json):
        return None

    try:
        with open(package_json, 'r') as f:
            data = json.load(f)
        deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
    except (json.JSONDecodeError, OSError):
        return None

    for dep_key, framework_name in _JS_API_FRAMEWORKS:
        if dep_key in deps:
            return framework_name
    return None


def _detect_python_api_framework(project_folder: str) -> Optional[str]:
    """Detect Python API framework from dependency files.

    Args:
        project_folder: Project root

    Returns:
        Framework name or None
    """
    deps_content = ""
    for filename in ['requirements.txt', 'pyproject.toml']:
        filepath = os.path.join(project_folder, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    deps_content += f.read().lower()
            except OSError:
                pass

    if not deps_content:
        return None

    for pattern, framework_name in _PYTHON_API_FRAMEWORKS:
        if pattern in deps_content:
            return framework_name
    return None


def _detect_framework(project_folder: str, language: str) -> Optional[str]:
    """Detect web framework used in the project.

    Args:
        project_folder: Project root
        language: Primary language

    Returns:
        Framework name or None
    """
    # Check JS frameworks first
    js_framework = _detect_js_api_framework(project_folder)
    if js_framework:
        return js_framework

    # Then check Python frameworks
    return _detect_python_api_framework(project_folder)


# =============================================================================
# Route Parsers
# =============================================================================

class ExpressRouteParser:
    """Parse Express.js routes."""

    def parse_file(self, file_path: str) -> List[ApiRoute]:
        """Parse routes from an Express file."""
        routes = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # Pattern for app.get/post/etc. or router.get/post/etc.
        # Matches: app.get('/path', handler), router.post('/path', ...)
        route_pattern = re.compile(
            r'(?:app|router)\.(get|post|put|delete|patch|options|head)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]'
        )

        for i, line in enumerate(lines):
            match = route_pattern.search(line)
            if match:
                method = match.group(1).upper()
                path = match.group(2)

                # Try to find handler name
                handler_match = re.search(r',\s*(\w+)\s*\)', line)
                handler_name = handler_match.group(1) if handler_match else 'anonymous'

                # Extract path parameters
                params = self._extract_path_params(path)

                route = ApiRoute(
                    path=path,
                    method=method,
                    handler_name=handler_name,
                    file_path=file_path,
                    line_number=i + 1,
                    parameters=params,
                )
                routes.append(route)

        return routes

    def _extract_path_params(self, path: str) -> List[RouteParameter]:
        """Extract path parameters from route path."""
        params = []
        # Match :param syntax
        for match in re.finditer(r':(\w+)', path):
            params.append(RouteParameter(
                name=match.group(1),
                location='path',
                required=True,
            ))
        return params


class FastAPIRouteParser:
    """Parse FastAPI routes."""

    def parse_file(self, file_path: str) -> List[ApiRoute]:
        """Parse routes from a FastAPI file."""
        routes = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # Pattern for @app.get/post/etc. or @router.get/post/etc.
        decorator_pattern = re.compile(
            r'@(?:app|router)\.(get|post|put|delete|patch|options|head)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]'
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            match = decorator_pattern.search(line)

            if match:
                method = match.group(1).upper()
                path = match.group(2)

                # Look for function definition on next line(s)
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('def ') and not lines[j].strip().startswith('async def '):
                    j += 1

                handler_name = 'unknown'
                params: List[RouteParameter] = []

                if j < len(lines):
                    func_line = lines[j]
                    # Extract function name
                    name_match = re.search(r'(?:async\s+)?def\s+(\w+)', func_line)
                    if name_match:
                        handler_name = name_match.group(1)

                    # Extract parameters
                    params = self._extract_params(func_line)

                # Add path params
                path_params = self._extract_path_params(path)

                route = ApiRoute(
                    path=path,
                    method=method,
                    handler_name=handler_name,
                    file_path=file_path,
                    line_number=i + 1,
                    parameters=path_params + params,
                )
                routes.append(route)

            i += 1

        return routes

    def _extract_path_params(self, path: str) -> List[RouteParameter]:
        """Extract path parameters from route path."""
        params = []
        # Match {param} syntax
        for match in re.finditer(r'\{(\w+)\}', path):
            params.append(RouteParameter(
                name=match.group(1),
                location='path',
                required=True,
            ))
        return params

    def _extract_params(self, func_line: str) -> List[RouteParameter]:
        """Extract query/body parameters from function signature."""
        params = []

        # Find params section
        param_match = re.search(r'\((.*)\)', func_line)
        if not param_match:
            return params

        params_str = param_match.group(1)

        # Parse each parameter
        for part in params_str.split(','):
            part = part.strip()
            if not part or part in ('self', 'cls'):
                continue

            # Check for Query/Body annotations
            if 'Query' in part:
                name_match = re.match(r'(\w+)\s*:', part)
                if name_match:
                    params.append(RouteParameter(
                        name=name_match.group(1),
                        location='query',
                        required='...' not in part,
                    ))
            elif 'Body' in part:
                name_match = re.match(r'(\w+)\s*:', part)
                if name_match:
                    params.append(RouteParameter(
                        name=name_match.group(1),
                        location='body',
                        required='...' not in part,
                    ))

        return params


class FlaskRouteParser:
    """Parse Flask routes."""

    def parse_file(self, file_path: str) -> List[ApiRoute]:
        """Parse routes from a Flask file."""
        routes = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # Pattern for @app.route or @blueprint.route
        decorator_pattern = re.compile(
            r'@(?:\w+)\.route\s*\(\s*[\'"`]([^\'"`]+)[\'"`](?:.*methods\s*=\s*\[([^\]]+)\])?'
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            match = decorator_pattern.search(line)

            if match:
                path = match.group(1)
                methods_str = match.group(2)

                # Parse methods
                if methods_str:
                    methods = [m.strip().strip('\'"') for m in methods_str.split(',')]
                else:
                    methods = ['GET']

                # Look for function definition
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('def '):
                    j += 1

                handler_name = 'unknown'
                if j < len(lines):
                    func_line = lines[j]
                    name_match = re.search(r'def\s+(\w+)', func_line)
                    if name_match:
                        handler_name = name_match.group(1)

                # Extract path parameters
                path_params = self._extract_path_params(path)

                # Create route for each method
                for method in methods:
                    route = ApiRoute(
                        path=path,
                        method=method.upper(),
                        handler_name=handler_name,
                        file_path=file_path,
                        line_number=i + 1,
                        parameters=path_params,
                    )
                    routes.append(route)

            i += 1

        return routes

    def _extract_path_params(self, path: str) -> List[RouteParameter]:
        """Extract path parameters from route path."""
        params = []
        # Match <param> or <type:param> syntax
        for match in re.finditer(r'<(?:(\w+):)?(\w+)>', path):
            type_hint = match.group(1)
            name = match.group(2)
            params.append(RouteParameter(
                name=name,
                location='path',
                type_hint=type_hint,
                required=True,
            ))
        return params


# =============================================================================
# Documentation Generators
# =============================================================================

def _generate_markdown_docs(routes: List[ApiRoute], framework: str) -> str:
    """Generate Markdown API documentation.

    Args:
        routes: List of parsed routes
        framework: Framework name

    Returns:
        Markdown string
    """
    lines = ['# API Documentation', '']
    lines.append(f'Generated from {framework} routes.')
    lines.append('')

    # Group routes by path prefix
    route_groups: Dict[str, List[ApiRoute]] = {}
    for route in routes:
        # Get first path segment as group
        parts = route.path.strip('/').split('/')
        group = parts[0] if parts else 'root'
        if group not in route_groups:
            route_groups[group] = []
        route_groups[group].append(route)

    # Generate documentation for each group
    for group, group_routes in sorted(route_groups.items()):
        lines.append(f'## {group.title()} Endpoints')
        lines.append('')

        for route in sorted(group_routes, key=lambda r: (r.path, r.method)):
            lines.append(f'### `{route.method}` {route.path}')
            lines.append('')

            if route.description:
                lines.append(route.description)
                lines.append('')

            # Handler info
            lines.append(f'**Handler:** `{route.handler_name}` ({route.file_path}:{route.line_number})')
            lines.append('')

            # Parameters
            if route.parameters:
                lines.append('**Parameters:**')
                lines.append('')
                lines.append('| Name | Location | Type | Required | Description |')
                lines.append('|------|----------|------|----------|-------------|')
                for param in route.parameters:
                    required = 'Yes' if param.required else 'No'
                    type_hint = param.type_hint or 'string'
                    desc = param.description or '-'
                    lines.append(f'| `{param.name}` | {param.location} | {type_hint} | {required} | {desc} |')
                lines.append('')

            # Responses (default)
            if not route.responses:
                lines.append('**Responses:**')
                lines.append('')
                lines.append('| Status | Description |')
                lines.append('|--------|-------------|')
                lines.append('| 200 | Success |')
                lines.append('| 400 | Bad Request |')
                lines.append('| 404 | Not Found |')
                lines.append('| 500 | Internal Server Error |')
                lines.append('')

            lines.append('---')
            lines.append('')

    return '\n'.join(lines)


def _build_openapi_param(param: RouteParameter) -> Dict[str, Any]:
    """Build OpenAPI parameter object.

    Args:
        param: Route parameter

    Returns:
        OpenAPI parameter object
    """
    param_obj: Dict[str, Any] = {
        'name': param.name,
        'in': param.location if param.location != 'body' else 'query',
        'required': param.required,
        'schema': {'type': param.type_hint or 'string'},
    }
    if param.description:
        param_obj['description'] = param.description
    return param_obj


def _build_openapi_request_body(body_params: List[RouteParameter]) -> Dict[str, Any]:
    """Build OpenAPI request body object.

    Args:
        body_params: Body parameters

    Returns:
        OpenAPI requestBody object
    """
    properties = {p.name: {'type': p.type_hint or 'string'} for p in body_params}
    return {
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': properties,
                }
            }
        }
    }


def _build_openapi_operation(route: ApiRoute) -> Dict[str, Any]:
    """Build OpenAPI operation object for a route.

    Args:
        route: API route

    Returns:
        OpenAPI operation object
    """
    method = route.method.lower()
    operation: Dict[str, Any] = {
        'operationId': route.handler_name,
        'summary': route.description or f'{route.method} {route.path}',
        'responses': {'200': {'description': 'Successful response'}},
    }

    # Add parameters
    parameters = [_build_openapi_param(p) for p in route.parameters]
    if parameters:
        operation['parameters'] = parameters

    # Add request body for POST/PUT/PATCH
    if method in ('post', 'put', 'patch'):
        body_params = [p for p in route.parameters if p.location == 'body']
        if body_params:
            operation['requestBody'] = _build_openapi_request_body(body_params)

    return operation


def _generate_openapi_spec(routes: List[ApiRoute], project_name: str = "API") -> Dict[str, Any]:
    """Generate OpenAPI 3.0 specification.

    Args:
        routes: List of parsed routes
        project_name: Project name for the spec

    Returns:
        OpenAPI spec as dictionary
    """
    spec: Dict[str, Any] = {
        'openapi': '3.0.0',
        'info': {'title': project_name, 'version': '1.0.0'},
        'paths': {},
    }

    for route in routes:
        if route.path not in spec['paths']:
            spec['paths'][route.path] = {}
        spec['paths'][route.path][route.method.lower()] = _build_openapi_operation(route)

    return spec


# =============================================================================
# Main Generator
# =============================================================================

def _find_route_files(project_folder: str, language: str, framework: str) -> List[str]:
    """Find files likely to contain route definitions.

    Args:
        project_folder: Project root
        language: Primary language
        framework: Framework name

    Returns:
        List of file paths
    """
    route_files = []

    # Common patterns for route files
    route_patterns = {
        'express': ['routes', 'router', 'api', 'controllers'],
        'fastapi': ['routes', 'router', 'api', 'endpoints', 'views'],
        'flask': ['routes', 'views', 'api', 'blueprints'],
        'fastify': ['routes', 'router', 'api'],
        'nestjs': ['controller', 'routes'],
    }

    patterns = route_patterns.get(framework, ['routes', 'api', 'controllers'])

    # File extensions
    extensions = {
        'python': ['.py'],
        'typescript': ['.ts'],
        'javascript': ['.js'],
    }

    exts = extensions.get(language, ['.py', '.js', '.ts'])

    # Walk directory
    for root, dirs, files in os.walk(project_folder):
        # Skip common non-source directories
        if any(skip in root for skip in ['node_modules', '.git', 'venv', '__pycache__', 'dist', 'build']):
            continue

        for file in files:
            # Check extension
            if not any(file.endswith(ext) for ext in exts):
                continue

            # Check if file/path matches route patterns
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_folder).lower()

            if any(pattern in rel_path for pattern in patterns):
                route_files.append(full_path)
            elif any(pattern in file.lower() for pattern in patterns):
                route_files.append(full_path)

    return route_files


def generate_api_docs_impl(
    project_folder: str,
    language: str,
    framework: Optional[str] = None,
    output_format: str = "markdown",
    include_examples: bool = True,
) -> ApiDocsResult:
    """Generate API documentation from route definitions.

    Args:
        project_folder: Root folder of the project
        language: Programming language
        framework: Framework name (or None for auto-detect)
        output_format: Output format ('markdown', 'openapi', 'both')
        include_examples: Whether to include request/response examples

    Returns:
        ApiDocsResult with generated documentation
    """
    start_time = time.time()

    logger.info(
        "generate_api_docs_started",
        project_folder=project_folder,
        language=language,
        framework=framework,
        output_format=output_format,
    )

    # Detect framework if not specified
    if not framework:
        framework = _detect_framework(project_folder, language)

    if not framework:
        logger.warning("no_framework_detected")
        return ApiDocsResult(
            routes=[],
            markdown="# API Documentation\n\nNo web framework detected.",
            framework=None,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

    # Select parser based on framework
    parsers = {
        'express': ExpressRouteParser(),
        'fastapi': FastAPIRouteParser(),
        'flask': FlaskRouteParser(),
        'fastify': ExpressRouteParser(),  # Similar syntax
        'starlette': FastAPIRouteParser(),  # Similar syntax
    }

    parser = parsers.get(framework)
    if not parser:
        logger.warning("unsupported_framework", framework=framework)
        return ApiDocsResult(
            routes=[],
            markdown=f"# API Documentation\n\nFramework '{framework}' is not yet supported.",
            framework=framework,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

    # Find route files
    route_files = _find_route_files(project_folder, language, framework)

    # Parse all route files
    all_routes: List[ApiRoute] = []
    for file_path in route_files:
        try:
            routes = parser.parse_file(file_path)
            all_routes.extend(routes)
        except Exception as e:
            logger.warning("file_parse_error", file=file_path, error=str(e))
            sentry_sdk.capture_exception(e)

    # Generate documentation
    markdown = _generate_markdown_docs(all_routes, framework)

    openapi_spec = None
    if output_format in ('openapi', 'both'):
        project_name = os.path.basename(project_folder)
        openapi_spec = _generate_openapi_spec(all_routes, project_name)

    execution_time = int((time.time() - start_time) * 1000)

    logger.info(
        "generate_api_docs_completed",
        routes_found=len(all_routes),
        framework=framework,
        execution_time_ms=execution_time,
    )

    return ApiDocsResult(
        routes=all_routes,
        markdown=markdown,
        openapi_spec=openapi_spec,
        framework=framework,
        execution_time_ms=execution_time,
    )
