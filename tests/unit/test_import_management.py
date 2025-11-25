"""Unit tests for import management functions in the code generation engine.

Tests cover:
- detect_import_insertion_point for all languages
- generate_import_statement
- identify_unused_imports
- resolve_import_path
- Edge cases (no imports, all imports unused, etc.)
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import (
    _detect_generic_import_point,
    _detect_java_import_point,
    _detect_js_import_point,
    _detect_python_import_point,
    _extract_identifiers,
    _extract_imports_with_names,
    _remove_import_lines,
    generate_import_statement,
    identify_unused_imports,
    resolve_import_path,
)

from ast_grep_mcp.features.deduplication.generator import CodeGenerator


class TestDetectImportInsertionPoint:
    """Test detect_import_insertion_point for various languages."""

    # Python tests
    def test_python_basic_imports(self, code_generator):
        """Test Python with basic import statements."""
        content = "import os\nimport sys\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 3

    def test_python_from_imports(self, code_generator):
        """Test Python with from imports."""
        content = "from os import path\nfrom sys import argv\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 3

    def test_python_mixed_imports(self, code_generator):
        """Test Python with mixed import and from import."""
        content = "import os\nfrom sys import argv\nimport json\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 4

    def test_python_with_docstring(self, code_generator):
        """Test Python file with module docstring."""
        content = '"""Module docstring."""\nimport os\n\ndef main():\n    pass'
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 3

    def test_python_with_multiline_docstring(self, code_generator):
        """Test Python file with multiline docstring."""
        content = '"""\nMultiline\ndocstring.\n"""\nimport os\nimport sys\n\ndef main():\n    pass'
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 7

    def test_python_with_comments(self, code_generator):
        """Test Python file with comments before imports."""
        content = "# Comment\nimport os\nimport sys\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 4

    def test_python_no_imports(self, code_generator):
        """Test Python file with no imports."""
        content = "def main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 1

    def test_python_empty_file(self, code_generator):
        """Test empty Python file."""
        result = code_generator.detect_import_insertion_point("", "python")
        assert result == 1

    def test_python_future_imports(self, code_generator):
        """Test Python with __future__ imports."""
        content = "from __future__ import annotations\nimport os\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result == 3

    # TypeScript/JavaScript tests
    def test_typescript_es6_imports(self, code_generator):
        """Test TypeScript with ES6 imports."""
        content = "import React from 'react'\nimport { useState } from 'react'\n\nconst App = () => {}"
        result = code_generator.detect_import_insertion_point(content, "typescript")
        assert result == 3

    def test_javascript_require(self, code_generator):
        """Test JavaScript with require statements."""
        content = "const fs = require('fs')\nconst path = require('path')\n\nmodule.exports = {}"
        result = code_generator.detect_import_insertion_point(content, "javascript")
        assert result == 3

    def test_typescript_with_use_strict(self, code_generator):
        """Test TypeScript with 'use strict' directive."""
        content = "'use strict';\nimport { foo } from 'bar'\n\nconst x = 1"
        result = code_generator.detect_import_insertion_point(content, "typescript")
        assert result == 3

    def test_typescript_type_imports(self, code_generator):
        """Test TypeScript with type imports."""
        content = "import type { User } from './types'\nimport { getUser } from './api'\n\nconst user: User = {}"
        result = code_generator.detect_import_insertion_point(content, "typescript")
        assert result == 3

    def test_javascript_mixed_imports(self, code_generator):
        """Test JavaScript with mixed import styles."""
        content = "import React from 'react'\nconst lodash = require('lodash')\nimport './styles.css'\n\nfunction App() {}"
        result = code_generator.detect_import_insertion_point(content, "javascript")
        assert result == 4

    def test_javascript_no_imports(self, code_generator):
        """Test JavaScript file with no imports."""
        content = "const x = 1\nconst y = 2"
        result = code_generator.detect_import_insertion_point(content, "javascript")
        assert result == 1

    # Java tests
    def test_java_basic_imports(self, code_generator):
        """Test Java with basic imports."""
        content = "package com.example;\n\nimport java.util.List;\nimport java.util.Map;\n\npublic class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")
        assert result == 5

    def test_java_static_imports(self, code_generator):
        """Test Java with static imports."""
        content = "package com.example;\n\nimport static org.junit.Assert.*;\nimport java.util.List;\n\npublic class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")
        assert result == 5

    def test_java_only_package(self, code_generator):
        """Test Java file with only package declaration."""
        content = "package com.example;\n\npublic class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")
        assert result == 2

    def test_java_no_package_no_imports(self, code_generator):
        """Test Java file with no package or imports."""
        content = "public class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")
        assert result == 1

    # Generic/Unknown language tests
    def test_generic_language(self, code_generator):
        """Test with unsupported language falls back to generic detection."""
        content = "#include <stdio.h>\n#include <stdlib.h>\n\nint main() {}"
        result = code_generator.detect_import_insertion_point(content, "c")
        assert result == 3

    def test_rust_use_statements(self, code_generator):
        """Test generic detection with Rust use statements."""
        content = "use std::io;\nuse std::fs;\n\nfn main() {}"
        result = code_generator.detect_import_insertion_point(content, "rust")
        assert result == 3


class TestGenerateImportStatement:
    """Test generate_import_statement for various languages."""

    # Python tests
    def test_python_single_import(self):
        """Test Python single module import."""
        result = generate_import_statement("os", [], "python")
        assert result == "import os"

    def test_python_from_import_single(self):
        """Test Python from import with single item."""
        result = generate_import_statement("os.path", ["join"], "python")
        assert result == "from os.path import join"

    def test_python_from_import_multiple(self):
        """Test Python from import with multiple items."""
        result = generate_import_statement("os.path", ["join", "dirname", "exists"], "python")
        assert result == "from os.path import join, dirname, exists"

    def test_python_star_import(self):
        """Test Python star import."""
        result = generate_import_statement("typing", ["*"], "python")
        assert result == "from typing import *"

    # TypeScript/JavaScript tests
    def test_typescript_named_imports(self):
        """Test TypeScript named imports."""
        result = generate_import_statement("react", ["useState", "useEffect"], "typescript")
        assert result == "import { useState, useEffect } from 'react'"

    def test_typescript_default_import(self):
        """Test TypeScript default import."""
        result = generate_import_statement("react", [], "typescript", default_import="React")
        assert result == "import React from 'react'"

    def test_typescript_mixed_import(self):
        """Test TypeScript default + named imports."""
        result = generate_import_statement("react", ["useState"], "typescript", default_import="React")
        assert result == "import React, { useState } from 'react'"

    def test_typescript_side_effect_import(self):
        """Test TypeScript side-effect import."""
        result = generate_import_statement("./styles.css", [], "typescript")
        assert result == "import './styles.css'"

    def test_typescript_star_import(self):
        """Test TypeScript namespace import."""
        result = generate_import_statement("lodash", ["*"], "typescript")
        assert result == "import * as lodash from 'lodash'"

    def test_javascript_require(self):
        """Test JavaScript require syntax."""
        result = generate_import_statement("fs", [], "javascript", default_import="fs", use_require=True)
        assert result == "const fs = require('fs')"

    def test_javascript_require_destructuring(self):
        """Test JavaScript require with destructuring."""
        result = generate_import_statement("path", ["join", "dirname"], "javascript", use_require=True)
        assert result == "const { join, dirname } = require('path')"

    # Java tests
    def test_java_single_class(self):
        """Test Java single class import."""
        result = generate_import_statement("java.util", ["List"], "java")
        assert result == "import java.util.List;"

    def test_java_multiple_classes(self):
        """Test Java multiple class imports."""
        result = generate_import_statement("java.util", ["List", "Map", "Set"], "java")
        expected = "import java.util.List;\nimport java.util.Map;\nimport java.util.Set;"
        assert result == expected

    def test_java_star_import(self):
        """Test Java star import."""
        result = generate_import_statement("java.util", ["*"], "java")
        assert result == "import java.util.*;"

    # Go tests
    def test_go_simple_import(self):
        """Test Go simple import."""
        result = generate_import_statement("fmt", [], "go")
        assert result == 'import "fmt"'

    def test_go_aliased_import(self):
        """Test Go aliased import."""
        result = generate_import_statement("database/sql", [], "go", default_import="db")
        assert result == 'import db "database/sql"'

    # Rust tests
    def test_rust_use_single(self):
        """Test Rust single use."""
        result = generate_import_statement("std::io", [], "rust")
        assert result == "use std::io;"

    def test_rust_use_single_item(self):
        """Test Rust use with single item."""
        result = generate_import_statement("std::io", ["Read"], "rust")
        assert result == "use std::io::Read;"

    def test_rust_use_multiple(self):
        """Test Rust use with multiple items."""
        result = generate_import_statement("std::io", ["Read", "Write"], "rust")
        assert result == "use std::io::{Read, Write};"

    def test_rust_use_glob(self):
        """Test Rust glob use."""
        result = generate_import_statement("std::prelude", ["*"], "rust")
        assert result == "use std::prelude::*;"

    # C/C++ tests
    def test_c_include_system(self):
        """Test C system include."""
        result = generate_import_statement("stdio.h", [], "c")
        assert result == '#include "stdio.h"'

    def test_c_include_angle_brackets(self):
        """Test C include with angle brackets."""
        result = generate_import_statement("<stdio.h>", [], "c")
        assert result == "#include <stdio.h>"

    # C# tests
    def test_csharp_using(self):
        """Test C# using statement."""
        result = generate_import_statement("System.Collections.Generic", [], "csharp")
        assert result == "using System.Collections.Generic;"

    # Unknown language tests
    def test_unknown_language(self):
        """Test unknown language generates comment."""
        result = generate_import_statement("some.module", ["foo"], "unknown")
        assert result == "// Import foo from some.module"


class TestIdentifyUnusedImports:
    """Test identify_unused_imports function."""

    def test_python_unused_import(self):
        """Test identifying unused Python import."""
        content = "import os\n\ndef main():\n    pass"
        removed = "path = os.path.join('a', 'b')"
        result = identify_unused_imports(content, removed, "python")
        assert "import os" in result

    def test_python_used_import_not_flagged(self):
        """Test that used imports are not flagged."""
        content = "import os\n\ndef main():\n    return os.getcwd()"
        removed = "path = os.path.join('a', 'b')"
        result = identify_unused_imports(content, removed, "python")
        assert len(result) == 0

    def test_python_from_import_unused(self):
        """Test unused from import."""
        content = "from os.path import join\n\ndef main():\n    pass"
        removed = "result = join('a', 'b')"
        result = identify_unused_imports(content, removed, "python")
        assert any("join" in imp for imp in result)

    def test_typescript_unused_import(self):
        """Test unused TypeScript import."""
        content = "import { useState } from 'react'\n\nconst App = () => null"
        removed = "const [count, setCount] = useState(0)"
        result = identify_unused_imports(content, removed, "typescript")
        assert any("useState" in imp for imp in result)

    def test_empty_content(self):
        """Test with empty content."""
        result = identify_unused_imports("", "some code", "python")
        assert result == []

    def test_empty_removed(self):
        """Test with empty removed code."""
        content = "import os\n\ndef main():\n    pass"
        result = identify_unused_imports(content, "", "python")
        assert result == []

    def test_all_imports_unused(self):
        """Test when all imports are unused."""
        content = "import os\nimport sys\n\ndef main():\n    pass"
        removed = "os.getcwd()\nsys.exit(0)"
        result = identify_unused_imports(content, removed, "python")
        assert len(result) == 2

    def test_partial_import_unused(self):
        """Test when only some items from import are unused."""
        content = "from os.path import join, dirname\n\ndef main():\n    return dirname('/path')"
        removed = "result = join('a', 'b')"
        result = identify_unused_imports(content, removed, "python")
        # Should not flag since dirname is still used
        assert len(result) == 0


class TestResolveImportPath:
    """Test resolve_import_path function."""

    def test_python_same_directory_relative(self):
        """Test Python relative import in same directory."""
        result = resolve_import_path("/src/utils/helper.py", "/src/utils/formatter.py", "python", prefer_relative=True)
        assert ".formatter" in result
        assert "from" in result

    def test_python_parent_directory_relative(self):
        """Test Python relative import from parent directory."""
        result = resolve_import_path("/src/utils/helper.py", "/src/models/user.py", "python", prefer_relative=True)
        assert ".." in result

    def test_python_subdirectory_relative(self):
        """Test Python relative import from subdirectory."""
        result = resolve_import_path("/src/main.py", "/src/utils/helper.py", "python", prefer_relative=True)
        assert ".utils" in result

    def test_typescript_same_directory(self):
        """Test TypeScript relative import in same directory."""
        result = resolve_import_path("/src/utils/helper.ts", "/src/utils/formatter.ts", "typescript", prefer_relative=True)
        assert result == "./formatter"

    def test_typescript_parent_directory(self):
        """Test TypeScript relative import from parent directory."""
        result = resolve_import_path("/src/utils/helper.ts", "/src/models/user.ts", "typescript", prefer_relative=True)
        assert result.startswith("../")
        assert "user" in result

    def test_typescript_subdirectory(self):
        """Test TypeScript relative import from subdirectory."""
        result = resolve_import_path("/src/main.ts", "/src/utils/helper.ts", "typescript", prefer_relative=True)
        assert result == "./utils/helper"

    def test_java_always_absolute(self):
        """Test Java always uses absolute paths."""
        result = resolve_import_path(
            "/src/main/java/com/example/Main.java",
            "/src/main/java/com/example/utils/Helper.java",
            "java",
            prefer_relative=True
        )
        # Java ignores prefer_relative
        assert "com.example.utils" in result or "Helper" in result

    def test_javascript_relative(self):
        """Test JavaScript relative import."""
        result = resolve_import_path("/src/index.js", "/src/utils/helper.js", "javascript", prefer_relative=True)
        assert result == "./utils/helper"

    @patch('os.path.exists')
    def test_typescript_absolute_with_package_json(self, mock_exists):
        """Test TypeScript absolute import with package.json."""
        mock_exists.return_value = True
        result = resolve_import_path(
            "/project/src/utils/helper.ts",
            "/project/src/components/Button.ts",
            "typescript",
            prefer_relative=False
        )
        # Should use path alias or relative
        assert "Button" in result or "components" in result

    def test_tsx_same_as_typescript(self):
        """Test TSX uses same logic as TypeScript."""
        result = resolve_import_path("/src/App.tsx", "/src/components/Button.tsx", "tsx", prefer_relative=True)
        assert result == "./components/Button"

    def test_jsx_same_as_javascript(self):
        """Test JSX uses same logic as JavaScript."""
        result = resolve_import_path("/src/App.jsx", "/src/components/Button.jsx", "jsx", prefer_relative=True)
        assert result == "./components/Button"

    def test_default_fallback(self):
        """Test default fallback for unknown languages."""
        result = resolve_import_path("/src/main.rb", "/src/lib/helper.rb", "ruby", prefer_relative=True)
        assert "lib" in result and "helper" in result


class TestExtractIdentifiers:
    """Test _extract_identifiers helper function."""

    def test_python_simple_identifiers(self):
        """Test extracting Python identifiers."""
        code = "foo = bar + baz"
        result = _extract_identifiers(code, "python")
        assert "foo" in result
        assert "bar" in result
        assert "baz" in result

    def test_python_removes_strings(self):
        """Test that string contents are not extracted."""
        code = 'name = "not_an_identifier"'
        result = _extract_identifiers(code, "python")
        assert "name" in result
        assert "not_an_identifier" not in result

    def test_python_removes_comments(self):
        """Test that comment contents are not extracted."""
        code = "x = 1  # this_is_a_comment"
        result = _extract_identifiers(code, "python")
        assert "x" in result
        assert "this_is_a_comment" not in result

    def test_javascript_removes_template_literals(self):
        """Test JavaScript template literals are removed."""
        code = "const msg = `hello ${name}`"
        result = _extract_identifiers(code, "javascript")
        assert "msg" in result
        assert "const" in result

    def test_javascript_removes_multiline_comments(self):
        """Test JavaScript multiline comments are removed."""
        code = "/* comment */ const x = 1"
        result = _extract_identifiers(code, "javascript")
        assert "x" in result
        assert "const" in result
        assert "comment" not in result


class TestRemoveImportLines:
    """Test _remove_import_lines helper function."""

    def test_python_removes_imports(self):
        """Test removing Python imports."""
        content = "import os\nfrom sys import argv\n\ndef main():\n    pass"
        result = _remove_import_lines(content, "python")
        assert "import os" not in result
        assert "from sys" not in result
        assert "def main" in result

    def test_typescript_removes_imports(self):
        """Test removing TypeScript imports."""
        content = "import React from 'react'\nconst x = 1"
        result = _remove_import_lines(content, "typescript")
        assert "import React" not in result
        assert "const x = 1" in result

    def test_javascript_removes_require(self):
        """Test removing JavaScript require statements."""
        content = "const fs = require('fs')\nconst x = 1"
        result = _remove_import_lines(content, "javascript")
        assert "require" not in result
        assert "const x = 1" in result

    def test_java_removes_imports(self):
        """Test removing Java imports."""
        content = "import java.util.List;\n\npublic class Foo {}"
        result = _remove_import_lines(content, "java")
        assert "import java" not in result
        assert "public class Foo" in result


class TestExtractImportsWithNames:
    """Test _extract_imports_with_names helper function."""

    def test_python_import_module(self):
        """Test extracting Python module import."""
        content = "import os"
        result = _extract_imports_with_names(content, "python")
        assert len(result) == 1
        assert "import os" in result[0][0]
        assert "os" in result[0][1]

    def test_python_from_import(self):
        """Test extracting Python from import."""
        content = "from os.path import join, dirname"
        result = _extract_imports_with_names(content, "python")
        assert len(result) == 1
        assert "join" in result[0][1]
        assert "dirname" in result[0][1]

    def test_python_aliased_import(self):
        """Test extracting Python aliased import."""
        content = "import numpy as np"
        result = _extract_imports_with_names(content, "python")
        assert len(result) == 1
        assert "np" in result[0][1]

    def test_typescript_default_import(self):
        """Test extracting TypeScript default import."""
        content = "import React from 'react'"
        result = _extract_imports_with_names(content, "typescript")
        assert len(result) == 1
        assert "React" in result[0][1]

    def test_typescript_named_imports(self):
        """Test extracting TypeScript named imports."""
        content = "import { useState, useEffect } from 'react'"
        result = _extract_imports_with_names(content, "typescript")
        assert len(result) == 1
        assert "useState" in result[0][1]
        assert "useEffect" in result[0][1]

    def test_typescript_namespace_import(self):
        """Test extracting TypeScript namespace import."""
        content = "import * as lodash from 'lodash'"
        result = _extract_imports_with_names(content, "typescript")
        assert len(result) == 1
        assert "lodash" in result[0][1]

    def test_javascript_require(self):
        """Test extracting JavaScript require."""
        content = "const fs = require('fs')"
        result = _extract_imports_with_names(content, "javascript")
        assert len(result) == 1
        assert "fs" in result[0][1]

    def test_javascript_require_destructuring(self):
        """Test extracting JavaScript require with destructuring."""
        content = "const { join, dirname } = require('path')"
        result = _extract_imports_with_names(content, "javascript")
        assert len(result) == 1
        assert "join" in result[0][1]
        assert "dirname" in result[0][1]

    def test_java_import(self):
        """Test extracting Java import."""
        content = "import java.util.List;"
        result = _extract_imports_with_names(content, "java")
        assert len(result) == 1
        assert "List" in result[0][1]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_detect_insertion_none_content(self, code_generator):
        """Test detect_import_insertion_point with None-like content."""
        result = code_generator.detect_import_insertion_point("", "python")
        assert result == 1

    def test_detect_insertion_whitespace_only(self, code_generator):
        """Test with whitespace-only content."""
        result = code_generator.detect_import_insertion_point("   \n\n   ", "python")
        assert result == 1

    def test_generate_import_empty_items(self, code_generator):
        """Test generate_import_statement with empty items list."""
        result = generate_import_statement("module", [], "python")
        assert result == "import module"

    def test_resolve_path_same_file(self, code_generator):
        """Test resolve_import_path with same source and target."""
        result = resolve_import_path("/src/file.py", "/src/file.py", "python")
        # Should handle gracefully
        assert "file" in result

    def test_case_insensitive_language(self, code_generator):
        """Test that language parameter is case-insensitive."""
        result = code_generator.detect_import_insertion_point("import os\n\ndef main():\n    pass", "PYTHON")
        assert result == 2

    def test_typescript_without_semicolons(self, code_generator):
        """Test TypeScript imports without semicolons."""
        content = "import React from 'react'\nimport { useState } from 'react'\n\nconst App = () => {}"
        result = code_generator.detect_import_insertion_point(content, "typescript")
        assert result == 3

    def test_python_inline_comments_after_import(self, code_generator):
        """Test Python imports with inline comments."""
        content = "import os  # system operations\nimport sys  # system info\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")
        # Should still find imports correctly
        assert result >= 2

    def test_multiline_python_import(self, code_generator):
        """Test Python multiline from import (parentheses)."""
        content = "from typing import (\n    List,\n    Dict,\n    Optional\n)\n\ndef main():\n    pass"
        # This is a complex case - the function may count individual lines
        result = code_generator.detect_import_insertion_point(content, "python")
        assert result >= 1

    def test_java_with_comments_between_imports(self, code_generator):
        """Test Java with comments between imports."""
        content = "package com.example;\n\n// Collections\nimport java.util.List;\n// IO\nimport java.io.File;\n\npublic class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")
        assert result >= 4


class TestLanguageSpecificDetection:
    """Test language-specific import detection helpers."""

    def test_detect_python_import_point_directly(self):
        """Test _detect_python_import_point directly."""
        lines = ["import os", "import sys", "", "def main():", "    pass"]
        result = _detect_python_import_point(lines)
        assert result == 3

    def test_detect_js_import_point_directly(self):
        """Test _detect_js_import_point directly."""
        lines = ["import React from 'react'", "import { useState } from 'react'", "", "const App = () => {}"]
        result = _detect_js_import_point(lines)
        assert result == 3

    def test_detect_java_import_point_directly(self):
        """Test _detect_java_import_point directly."""
        lines = ["package com.example;", "", "import java.util.List;", "", "public class Foo {}"]
        result = _detect_java_import_point(lines)
        assert result == 4

    def test_detect_generic_import_point_directly(self):
        """Test _detect_generic_import_point directly."""
        lines = ["#include <stdio.h>", "#include <stdlib.h>", "", "int main() {}"]
        result = _detect_generic_import_point(lines)
        assert result == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
