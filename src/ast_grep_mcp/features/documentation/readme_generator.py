"""README generation service.

This module provides functionality for auto-generating README.md sections
from code structure analysis.
"""

import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple, cast

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.documentation import (
    ProjectInfo,
    ReadmeGenerationResult,
    ReadmeSection,
)

logger = get_logger(__name__)


# =============================================================================
# Project Analyzers
# =============================================================================


def _parse_json_metadata(file_path: str) -> Tuple[str, str]:
    """Parse name and version from JSON file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data.get("name", ""), data.get("version", "")
    except (json.JSONDecodeError, OSError):
        return "", ""


def _parse_toml_metadata(file_path: str) -> Tuple[str, str]:
    """Parse name and version from TOML-like file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        return (name_match.group(1) if name_match else "", version_match.group(1) if version_match else "")
    except OSError:
        return "", ""


def _parse_go_mod(file_path: str) -> Tuple[str, str]:
    """Parse module name from go.mod."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
        module_match = re.search(r"module\s+(\S+)", content)
        return module_match.group(1) if module_match else "", ""
    except OSError:
        return "", ""


def _detect_js_package_manager(project_folder: str) -> str:
    """Detect JavaScript package manager from lock files."""
    if os.path.exists(os.path.join(project_folder, "yarn.lock")):
        return "yarn"
    if os.path.exists(os.path.join(project_folder, "pnpm-lock.yaml")):
        return "pnpm"
    return "npm"


def _detect_python_package_manager(project_folder: str) -> str:
    """Detect Python package manager from lock files."""
    if os.path.exists(os.path.join(project_folder, "uv.lock")):
        return "uv"
    if os.path.exists(os.path.join(project_folder, "poetry.lock")):
        return "poetry"
    return "pip"


def _detect_package_manager(project_folder: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Detect package manager and project metadata.

    Args:
        project_folder: Project root

    Returns:
        Tuple of (package_manager, project_name, version)
    """
    # Check for package.json (npm/yarn/pnpm)
    package_json = os.path.join(project_folder, "package.json")
    if os.path.exists(package_json):
        name, version = _parse_json_metadata(package_json)
        pm = _detect_js_package_manager(project_folder)
        return pm, name, version

    # Check for pyproject.toml (Python)
    pyproject = os.path.join(project_folder, "pyproject.toml")
    if os.path.exists(pyproject):
        name, version = _parse_toml_metadata(pyproject)
        pm = _detect_python_package_manager(project_folder)
        return pm, name, version

    # Check for setup.py (Python)
    setup_py = os.path.join(project_folder, "setup.py")
    if os.path.exists(setup_py):
        name, version = _parse_toml_metadata(setup_py)
        return "pip", name, version

    # Check for requirements.txt (Python)
    if os.path.exists(os.path.join(project_folder, "requirements.txt")):
        return "pip", "", ""

    # Check for Cargo.toml (Rust)
    cargo = os.path.join(project_folder, "Cargo.toml")
    if os.path.exists(cargo):
        name, version = _parse_toml_metadata(cargo)
        return "cargo", name, version

    # Check for go.mod (Go)
    go_mod = os.path.join(project_folder, "go.mod")
    if os.path.exists(go_mod):
        name, _ = _parse_go_mod(go_mod)
        return "go", name, ""

    return None, "", ""


def _detect_language(project_folder: str) -> str:
    """Detect primary programming language.

    Args:
        project_folder: Project root

    Returns:
        Primary language string
    """
    extensions: dict[str, int] = {}

    for root, _, files in os.walk(project_folder):
        # Skip common non-source directories
        if any(skip in root for skip in ["node_modules", ".git", "venv", "__pycache__", "dist", "build"]):
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                extensions[ext] += 1
            else:
                extensions[ext] = 1

    # Map extensions to languages
    lang_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".java": "java",
        ".rs": "rust",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".swift": "swift",
        ".kt": "kotlin",
    }

    # Find language with most files
    lang_counts: Dict[str, int] = {}
    for ext, count in extensions.items():
        lang = lang_map.get(ext)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + count

    if lang_counts:
        return max(lang_counts, key=lambda k: lang_counts[k])

    return "unknown"


# JS framework detection: (dep_key, framework_name)
_JS_FRAMEWORKS: List[Tuple[str, str]] = [
    ("react", "React"),
    ("next", "Next.js"),
    ("vue", "Vue.js"),
    ("angular", "Angular"),
    ("@angular/core", "Angular"),
    ("express", "Express"),
    ("fastify", "Fastify"),
    ("nestjs", "NestJS"),
    ("@nestjs/core", "NestJS"),
    ("electron", "Electron"),
]

# Python framework detection: (pattern, framework_name)
_PYTHON_FRAMEWORKS: List[Tuple[str, str]] = [
    ("django", "Django"),
    ("flask", "Flask"),
    ("fastapi", "FastAPI"),
    ("pytest", "pytest"),
    ("sqlalchemy", "SQLAlchemy"),
    ("pydantic", "Pydantic"),
]


def _detect_js_frameworks(project_folder: str) -> List[str]:
    """Detect JavaScript frameworks from package.json.

    Args:
        project_folder: Project root

    Returns:
        List of detected framework names
    """
    package_json = os.path.join(project_folder, "package.json")
    if not os.path.exists(package_json):
        return []

    try:
        with open(package_json, "r") as f:
            data = json.load(f)
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    except (json.JSONDecodeError, OSError):
        return []

    frameworks = []
    seen = set()  # Avoid duplicates like Angular appearing twice
    for dep_key, framework_name in _JS_FRAMEWORKS:
        if dep_key in deps and framework_name not in seen:
            frameworks.append(framework_name)
            seen.add(framework_name)
    return frameworks


def _get_python_deps_content(project_folder: str) -> str:
    """Read Python dependency files content.

    Args:
        project_folder: Project root

    Returns:
        Combined lowercase content of dependency files
    """
    deps_content = ""
    files = ["requirements.txt", "pyproject.toml"]

    for filename in files:
        filepath = os.path.join(project_folder, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    deps_content += f.read().lower()
            except OSError:
                pass
    return deps_content


def _detect_python_frameworks(project_folder: str) -> List[str]:
    """Detect Python frameworks from requirements.txt and pyproject.toml.

    Args:
        project_folder: Project root

    Returns:
        List of detected framework names
    """
    deps_content = _get_python_deps_content(project_folder)
    if not deps_content:
        return []

    return [name for pattern, name in _PYTHON_FRAMEWORKS if pattern in deps_content]


def _detect_frameworks(project_folder: str, language: str) -> List[str]:
    """Detect frameworks used in the project.

    Args:
        project_folder: Project root
        language: Primary language

    Returns:
        List of detected frameworks
    """
    frameworks = _detect_js_frameworks(project_folder)
    frameworks.extend(_detect_python_frameworks(project_folder))
    return frameworks


def _find_entry_points(project_folder: str, language: str) -> List[str]:
    """Find main entry point files.

    Args:
        project_folder: Project root
        language: Primary language

    Returns:
        List of entry point file paths
    """
    entry_points = []

    # Common entry point names
    common_names = {
        "python": ["main.py", "app.py", "__main__.py", "cli.py", "run.py"],
        "typescript": ["index.ts", "main.ts", "app.ts", "server.ts"],
        "javascript": ["index.js", "main.js", "app.js", "server.js"],
        "java": ["Main.java", "App.java", "Application.java"],
        "rust": ["main.rs", "lib.rs"],
        "go": ["main.go", "cmd/main.go"],
    }

    candidates = common_names.get(language, [])

    for candidate in candidates:
        full_path = os.path.join(project_folder, candidate)
        if os.path.exists(full_path):
            entry_points.append(candidate)
        # Check in src directory
        src_path = os.path.join(project_folder, "src", candidate)
        if os.path.exists(src_path):
            entry_points.append(os.path.join("src", candidate))

    return entry_points


def _analyze_project(project_folder: str, language: str) -> ProjectInfo:
    """Analyze project structure and metadata.

    Args:
        project_folder: Project root
        language: Primary language (can be 'auto')

    Returns:
        ProjectInfo with analyzed data
    """
    # Detect language if auto
    if language == "auto" or not language:
        language = _detect_language(project_folder)

    # Detect package manager and metadata
    package_manager, name, version = _detect_package_manager(project_folder)

    # Use folder name if no name found
    if not name:
        name = os.path.basename(project_folder)

    # Detect frameworks
    frameworks = _detect_frameworks(project_folder, language)

    # Find entry points
    entry_points = _find_entry_points(project_folder, language)

    # Check for tests
    has_tests = any(
        [
            os.path.exists(os.path.join(project_folder, "tests")),
            os.path.exists(os.path.join(project_folder, "test")),
            os.path.exists(os.path.join(project_folder, "__tests__")),
            os.path.exists(os.path.join(project_folder, "spec")),
        ]
    )

    # Check for docs
    has_docs = any(
        [
            os.path.exists(os.path.join(project_folder, "docs")),
            os.path.exists(os.path.join(project_folder, "documentation")),
        ]
    )

    # Get description from package files
    description = _get_project_description(project_folder)

    # Get main dependencies
    dependencies = _get_main_dependencies(project_folder, language)

    return ProjectInfo(
        name=name,
        version=version or None,
        description=description,
        language=language,
        package_manager=package_manager,
        entry_points=entry_points,
        frameworks=frameworks,
        has_tests=has_tests,
        has_docs=has_docs,
        dependencies=dependencies,
    )


def _get_project_description(project_folder: str) -> Optional[str]:
    """Get project description from package files.

    Args:
        project_folder: Project root

    Returns:
        Description string or None
    """
    # Check package.json
    package_json = os.path.join(project_folder, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, "r") as f:
                data = json.load(f)
            if data.get("description"):
                return cast(str, data["description"])
        except (json.JSONDecodeError, OSError):
            pass

    # Check pyproject.toml
    pyproject = os.path.join(project_folder, "pyproject.toml")
    if os.path.exists(pyproject):
        try:
            with open(pyproject, "r") as f:
                content = f.read()
            desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            if desc_match:
                return desc_match.group(1)
        except OSError:
            pass

    return None


def _get_js_dependencies(project_folder: str, max_deps: int = 10) -> List[str]:
    """Get JavaScript dependencies from package.json.

    Args:
        project_folder: Project root
        max_deps: Maximum dependencies to return

    Returns:
        List of dependency names
    """
    package_json = os.path.join(project_folder, "package.json")
    if not os.path.exists(package_json):
        return []

    try:
        with open(package_json, "r") as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        return list(deps.keys())[:max_deps]
    except (json.JSONDecodeError, OSError):
        return []


def _get_python_dependencies(project_folder: str, max_deps: int = 10) -> List[str]:
    """Get Python dependencies from requirements.txt.

    Args:
        project_folder: Project root
        max_deps: Maximum dependencies to return

    Returns:
        List of dependency names
    """
    requirements = os.path.join(project_folder, "requirements.txt")
    if not os.path.exists(requirements):
        return []

    dependencies = []
    try:
        with open(requirements, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                pkg = re.split(r"[<>=!~\[]", line)[0].strip()
                if pkg:
                    dependencies.append(pkg)
                if len(dependencies) >= max_deps:
                    break
    except OSError:
        pass

    return dependencies


def _get_main_dependencies(project_folder: str, language: str) -> List[str]:
    """Get main project dependencies.

    Args:
        project_folder: Project root
        language: Primary language

    Returns:
        List of main dependency names
    """
    dependencies = _get_js_dependencies(project_folder)
    dependencies.extend(_get_python_dependencies(project_folder, max_deps=10 - len(dependencies)))
    return dependencies


# =============================================================================
# Section Generators
# =============================================================================


def _generate_installation_section(info: ProjectInfo) -> ReadmeSection:
    """Generate installation instructions section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with installation content
    """
    lines = []

    if info.package_manager:
        pm_commands = {
            "npm": f"npm install {info.name}",
            "yarn": f"yarn add {info.name}",
            "pnpm": f"pnpm add {info.name}",
            "pip": f"pip install {info.name}",
            "uv": f"uv add {info.name}",
            "poetry": f"poetry add {info.name}",
            "cargo": f"cargo add {info.name}",
            "go": f"go get {info.name}",
        }

        cmd = pm_commands.get(info.package_manager, "")
        if cmd:
            lines.append("```bash")
            lines.append(cmd)
            lines.append("```")
        else:
            lines.append(f"Install using {info.package_manager}.")

        # Add from source instructions
        lines.append("")
        lines.append("### From Source")
        lines.append("")
        lines.append("```bash")
        lines.append(f"git clone https://github.com/your-username/{info.name}.git")
        lines.append(f"cd {info.name}")

        if info.package_manager == "npm":
            lines.append("npm install")
        elif info.package_manager == "yarn":
            lines.append("yarn install")
        elif info.package_manager == "pnpm":
            lines.append("pnpm install")
        elif info.package_manager in ("pip", "uv"):
            lines.append("uv sync  # or pip install -e .")
        elif info.package_manager == "poetry":
            lines.append("poetry install")
        elif info.package_manager == "cargo":
            lines.append("cargo build --release")
        elif info.package_manager == "go":
            lines.append("go build")

        lines.append("```")
    else:
        lines.append("Clone the repository and install dependencies:")
        lines.append("")
        lines.append("```bash")
        lines.append(f"git clone https://github.com/your-username/{info.name}.git")
        lines.append(f"cd {info.name}")
        lines.append("# Install dependencies")
        lines.append("```")

    return ReadmeSection(
        section_type="installation",
        title="Installation",
        content="\n".join(lines),
        order=10,
    )


def _generate_usage_section(info: ProjectInfo) -> ReadmeSection:
    """Generate usage examples section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with usage content
    """
    lines = []

    # Add basic usage based on language
    if info.language == "python":
        lines.append("```python")
        lines.append(f"from {info.name.replace('-', '_')} import main")
        lines.append("")
        lines.append("# Example usage")
        lines.append("result = main()")
        lines.append("```")
    elif info.language in ("typescript", "javascript"):
        lines.append("```javascript")
        lines.append(f'import {{ main }} from "{info.name}";')
        lines.append("")
        lines.append("// Example usage")
        lines.append("const result = main();")
        lines.append("```")
    elif info.language == "java":
        lines.append("```java")
        lines.append(f"import com.example.{info.name.replace('-', '')}.Main;")
        lines.append("")
        lines.append("// Example usage")
        lines.append("Main.run();")
        lines.append("```")
    elif info.language == "rust":
        lines.append("```rust")
        lines.append(f"use {info.name.replace('-', '_')}::*;")
        lines.append("")
        lines.append("fn main() {")
        lines.append("    // Example usage")
        lines.append("}")
        lines.append("```")
    elif info.language == "go":
        lines.append("```go")
        lines.append(f'import "{info.name}"')
        lines.append("")
        lines.append("func main() {")
        lines.append("    // Example usage")
        lines.append("}")
        lines.append("```")
    else:
        lines.append("See examples below.")

    # Add CLI usage if entry points suggest CLI
    if any("cli" in ep.lower() or "main" in ep.lower() for ep in info.entry_points):
        lines.append("")
        lines.append("### Command Line")
        lines.append("")
        lines.append("```bash")

        if info.package_manager in ("npm", "yarn", "pnpm"):
            lines.append(f"npx {info.name} --help")
        elif info.package_manager in ("pip", "uv", "poetry"):
            lines.append(f"{info.name.replace('-', '_')} --help")
        else:
            lines.append(f"./{info.name} --help")

        lines.append("```")

    return ReadmeSection(
        section_type="usage",
        title="Usage",
        content="\n".join(lines),
        order=20,
    )


def _generate_features_section(info: ProjectInfo) -> ReadmeSection:
    """Generate features list section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with features content
    """
    lines = []

    # Generate generic features based on detected frameworks
    if info.frameworks:
        lines.append(f"Built with {', '.join(info.frameworks)}.")
        lines.append("")

    lines.append("- Feature 1: Description")
    lines.append("- Feature 2: Description")
    lines.append("- Feature 3: Description")

    if info.has_tests:
        lines.append("- Comprehensive test suite")

    if info.has_docs:
        lines.append("- Full documentation")

    return ReadmeSection(
        section_type="features",
        title="Features",
        content="\n".join(lines),
        order=5,
    )


def _generate_api_section(info: ProjectInfo) -> ReadmeSection:
    """Generate API reference section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with API content
    """
    lines = []

    lines.append("### Core Functions")
    lines.append("")
    lines.append("| Function | Description |")
    lines.append("|----------|-------------|")
    lines.append("| `main()` | Main entry point |")
    lines.append("| `configure()` | Configure settings |")
    lines.append("")
    lines.append("See the [full API documentation](docs/api.md) for details.")

    return ReadmeSection(
        section_type="api",
        title="API Reference",
        content="\n".join(lines),
        order=30,
    )


def _generate_structure_section(info: ProjectInfo) -> ReadmeSection:
    """Generate project structure section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with structure content
    """
    lines = ["```"]

    # Generate basic structure
    lines.append(f"{info.name}/")

    if info.language == "python":
        lines.append("├── src/")
        lines.append(f"│   └── {info.name.replace('-', '_')}/")
        lines.append("│       ├── __init__.py")
        lines.append("│       └── main.py")
        if info.has_tests:
            lines.append("├── tests/")
            lines.append("│   └── test_main.py")
        lines.append("├── pyproject.toml")
        lines.append("└── README.md")
    elif info.language in ("typescript", "javascript"):
        lines.append("├── src/")
        lines.append("│   ├── index.ts")
        lines.append("│   └── lib/")
        if info.has_tests:
            lines.append("├── tests/")
            lines.append("│   └── index.test.ts")
        lines.append("├── package.json")
        lines.append("├── tsconfig.json")
        lines.append("└── README.md")
    else:
        lines.append("├── src/")
        lines.append("│   └── main.*")
        if info.has_tests:
            lines.append("├── tests/")
        lines.append("└── README.md")

    lines.append("```")

    return ReadmeSection(
        section_type="structure",
        title="Project Structure",
        content="\n".join(lines),
        order=40,
    )


def _generate_contributing_section(info: ProjectInfo) -> ReadmeSection:
    """Generate contributing section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with contributing content
    """
    lines = []

    lines.append("Contributions are welcome! Please follow these steps:")
    lines.append("")
    lines.append("1. Fork the repository")
    lines.append("2. Create a feature branch (`git checkout -b feature/amazing-feature`)")
    lines.append('3. Commit your changes (`git commit -m "Add amazing feature"`)')
    lines.append("4. Push to the branch (`git push origin feature/amazing-feature`)")
    lines.append("5. Open a Pull Request")
    lines.append("")
    lines.append("### Development Setup")
    lines.append("")

    if info.package_manager == "npm":
        lines.append("```bash")
        lines.append("npm install")
        lines.append("npm run test")
        lines.append("```")
    elif info.package_manager in ("pip", "uv"):
        lines.append("```bash")
        lines.append("uv sync")
        lines.append("uv run pytest")
        lines.append("```")
    elif info.package_manager == "poetry":
        lines.append("```bash")
        lines.append("poetry install")
        lines.append("poetry run pytest")
        lines.append("```")
    elif info.package_manager == "cargo":
        lines.append("```bash")
        lines.append("cargo build")
        lines.append("cargo test")
        lines.append("```")
    else:
        lines.append("```bash")
        lines.append("# Install dependencies")
        lines.append("# Run tests")
        lines.append("```")

    return ReadmeSection(
        section_type="contributing",
        title="Contributing",
        content="\n".join(lines),
        order=50,
    )


def _generate_license_section(info: ProjectInfo) -> ReadmeSection:
    """Generate license section.

    Args:
        info: Project information

    Returns:
        ReadmeSection with license content
    """
    return ReadmeSection(
        section_type="license",
        title="License",
        content="This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.",
        order=60,
    )


def _generate_header(info: ProjectInfo) -> str:
    """Generate README header with title and badges.

    Args:
        info: Project information

    Returns:
        Header markdown string
    """
    lines = []

    # Title
    lines.append(f"# {info.name}")
    lines.append("")

    # Badges
    badges = []
    if info.version:
        badges.append(f"![Version](https://img.shields.io/badge/version-{info.version}-blue)")

    if info.language:
        lang_colors = {
            "python": "3776AB",
            "typescript": "3178C6",
            "javascript": "F7DF1E",
            "java": "ED8B00",
            "rust": "DEA584",
            "go": "00ADD8",
        }
        color = lang_colors.get(info.language, "gray")
        badges.append(f"![Language](https://img.shields.io/badge/{info.language}-{color})")

    if badges:
        lines.append(" ".join(badges))
        lines.append("")

    # Description
    if info.description:
        lines.append(info.description)
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Main Generator
# =============================================================================


def generate_readme_sections_impl(
    project_folder: str,
    language: str = "auto",
    sections: Optional[List[str]] = None,
    include_examples: bool = True,
) -> ReadmeGenerationResult:
    """Generate README.md sections from code analysis.

    Args:
        project_folder: Root folder of the project
        language: Programming language (or 'auto' for detection)
        sections: Which sections to generate (or ['all'])
        include_examples: Whether to include code examples

    Returns:
        ReadmeGenerationResult with generated sections
    """
    start_time = time.time()

    if sections is None:
        sections = ["all"]

    logger.info(
        "generate_readme_started",
        project_folder=project_folder,
        language=language,
        sections=sections,
    )

    # Analyze project
    info = _analyze_project(project_folder, language)

    # Section generators
    generators = {
        "installation": _generate_installation_section,
        "usage": _generate_usage_section,
        "features": _generate_features_section,
        "api": _generate_api_section,
        "structure": _generate_structure_section,
        "contributing": _generate_contributing_section,
        "license": _generate_license_section,
    }

    # Generate requested sections
    generated_sections = []

    if "all" in sections:
        sections_to_generate = list(generators.keys())
    else:
        sections_to_generate = [s for s in sections if s in generators]

    for section_type in sections_to_generate:
        try:
            generator = generators[section_type]
            section = generator(info)
            generated_sections.append(section)
        except Exception as e:
            logger.warning("section_generation_error", section=section_type, error=str(e))
            sentry_sdk.capture_exception(e)

    # Sort sections by order
    generated_sections.sort(key=lambda s: s.order)

    # Generate full README
    full_readme_parts = [_generate_header(info)]

    # Table of contents
    toc_lines = ["## Table of Contents", ""]
    for section in generated_sections:
        anchor = section.title.lower().replace(" ", "-")
        toc_lines.append(f"- [{section.title}](#{anchor})")
    toc_lines.append("")
    full_readme_parts.append("\n".join(toc_lines))

    # Add sections
    for section in generated_sections:
        full_readme_parts.append(f"## {section.title}")
        full_readme_parts.append("")
        full_readme_parts.append(section.content)
        full_readme_parts.append("")

    full_readme = "\n".join(full_readme_parts)

    execution_time = int((time.time() - start_time) * 1000)

    logger.info(
        "generate_readme_completed",
        sections_generated=len(generated_sections),
        execution_time_ms=execution_time,
    )

    return ReadmeGenerationResult(
        project_info=info,
        sections=generated_sections,
        full_readme=full_readme,
        execution_time_ms=execution_time,
    )
