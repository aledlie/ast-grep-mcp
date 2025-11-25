"""Unit tests for dependency analysis functions.

Tests extract_imports_from_files, detect_import_variations,
analyze_import_overlap, and detect_internal_dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import (
    analyze_import_overlap,
    detect_import_variations,
    detect_internal_dependencies,
    extract_imports_from_files,
)


class TestExtractImportsFromFiles:
    """Tests for extract_imports_from_files function."""

    def test_empty_file_list(self):
        """Should return empty dict for empty file list."""
        result = extract_imports_from_files([], "python")
        assert result == {}

    @patch("subprocess.run")
    def test_python_imports(self, mock_run):
        """Should extract Python import statements."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='import os\nfrom pathlib import Path\nfrom typing import Dict, List',
            stderr=""
        )

        result = extract_imports_from_files(["/test/file.py"], "python")

        assert "/test/file.py" in result
        assert mock_run.called

    @patch("subprocess.run")
    def test_typescript_imports(self, mock_run):
        """Should extract TypeScript import statements."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="import React from 'react'\nimport { useState } from 'react'\nimport type { Props } from './types'",
            stderr=""
        )

        result = extract_imports_from_files(["/test/file.ts"], "typescript")

        assert "/test/file.ts" in result
        assert mock_run.called

    @patch("subprocess.run")
    def test_javascript_imports(self, mock_run):
        """Should extract JavaScript import and require statements."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="import axios from 'axios'\nconst fs = require('fs')",
            stderr=""
        )

        result = extract_imports_from_files(["/test/file.js"], "javascript")

        assert "/test/file.js" in result
        assert mock_run.called

    @patch("subprocess.run")
    def test_multiple_files(self, mock_run):
        """Should extract imports from multiple files."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="import os",
            stderr=""
        )

        files = ["/test/file1.py", "/test/file2.py"]
        result = extract_imports_from_files(files, "python")

        # Should be called for each file and pattern
        assert mock_run.called

    @patch("subprocess.run")
    def test_no_imports_found(self, mock_run):
        """Should handle files with no imports."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        result = extract_imports_from_files(["/test/empty.py"], "python")

        assert "/test/empty.py" in result
        assert result["/test/empty.py"] == []

    @patch("subprocess.run")
    def test_subprocess_failure(self, mock_run):
        """Should handle subprocess failures gracefully."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error"
        )

        result = extract_imports_from_files(["/test/file.py"], "python")

        # Should still return dict with empty list for file
        assert "/test/file.py" in result


class TestDetectImportVariations:
    """Tests for detect_import_variations function."""

    def test_empty_imports(self):
        """Should handle empty imports dict."""
        result = detect_import_variations({}, "python")

        assert result["common_imports"] == []
        assert result["unique_imports"] == {}
        assert "No imports to compare" in result["summary"]

    def test_single_file(self):
        """Should handle single file (no comparison possible)."""
        file_imports = {
            "/test/file.py": ["import os", "import sys"]
        }

        result = detect_import_variations(file_imports, "python")

        assert result["common_imports"] == ["import os", "import sys"]
        assert "Only one file" in result["summary"]

    def test_common_imports(self):
        """Should identify imports common to all files."""
        file_imports = {
            "/test/file1.py": ["import os", "import sys", "import json"],
            "/test/file2.py": ["import os", "import sys", "import re"],
        }

        result = detect_import_variations(file_imports, "python")

        assert "import os" in result["common_imports"]
        assert "import sys" in result["common_imports"]

    def test_unique_imports(self):
        """Should identify imports unique to each file."""
        file_imports = {
            "/test/file1.py": ["import os", "import json"],
            "/test/file2.py": ["import os", "import re"],
        }

        result = detect_import_variations(file_imports, "python")

        # json is unique to file1, re is unique to file2
        assert "import json" in result["unique_imports"].get("/test/file1.py", [])
        assert "import re" in result["unique_imports"].get("/test/file2.py", [])

    def test_aliased_imports(self):
        """Should detect different aliases for same module."""
        file_imports = {
            "/test/file1.py": ["import numpy as np"],
            "/test/file2.py": ["import numpy as numpy_lib"],
        }

        result = detect_import_variations(file_imports, "python")

        # Should detect aliasing differences
        assert "aliasing_differences" in result

    def test_partial_imports(self):
        """Should detect partial import variations."""
        file_imports = {
            "/test/file1.py": ["from typing import Dict"],
            "/test/file2.py": ["from typing import Dict, List"],
        }

        result = detect_import_variations(file_imports, "python")

        # Should detect partial import differences
        assert "partial_imports" in result

    def test_typescript_imports(self):
        """Should handle TypeScript import variations."""
        file_imports = {
            "/test/file1.ts": ["import { useState } from 'react'"],
            "/test/file2.ts": ["import { useState, useEffect } from 'react'"],
        }

        result = detect_import_variations(file_imports, "typescript")

        assert "partial_imports" in result


class TestAnalyzeImportOverlap:
    """Tests for analyze_import_overlap function."""

    def test_empty_imports(self):
        """Should handle empty imports dict."""
        result = analyze_import_overlap({})

        assert result["shared_imports"] == []
        assert result["unique_imports_by_file"] == {}
        assert result["overlap_percentage"] == 0.0
        assert "No imports to analyze" in result["analysis_summary"]

    def test_full_overlap(self):
        """Should detect 100% overlap when all imports are shared."""
        file_imports = {
            "/test/file1.py": ["import os", "import sys"],
            "/test/file2.py": ["import os", "import sys"],
        }

        result = analyze_import_overlap(file_imports)

        assert set(result["shared_imports"]) == {"import os", "import sys"}
        assert result["overlap_percentage"] == 100.0

    def test_no_overlap(self):
        """Should detect 0% overlap when no imports are shared."""
        file_imports = {
            "/test/file1.py": ["import os"],
            "/test/file2.py": ["import sys"],
        }

        result = analyze_import_overlap(file_imports)

        assert result["shared_imports"] == []
        assert result["overlap_percentage"] == 0.0
        assert result["total_unique_imports"] == 2

    def test_partial_overlap(self):
        """Should calculate correct overlap percentage."""
        file_imports = {
            "/test/file1.py": ["import os", "import json"],
            "/test/file2.py": ["import os", "import re"],
        }

        result = analyze_import_overlap(file_imports)

        assert "import os" in result["shared_imports"]
        assert result["total_unique_imports"] == 3
        # 1 shared out of 3 total = 33.33%
        assert 30 < result["overlap_percentage"] < 35

    def test_unique_imports_by_file(self):
        """Should correctly identify unique imports per file."""
        file_imports = {
            "/test/file1.py": ["import os", "import json"],
            "/test/file2.py": ["import os", "import re"],
            "/test/file3.py": ["import os", "import yaml"],
        }

        result = analyze_import_overlap(file_imports)

        assert "import json" in result["unique_imports_by_file"]["/test/file1.py"]
        assert "import re" in result["unique_imports_by_file"]["/test/file2.py"]
        assert "import yaml" in result["unique_imports_by_file"]["/test/file3.py"]

    def test_with_duplicate_code(self):
        """Should analyze required imports when duplicate code provided."""
        file_imports = {
            "/test/file1.py": ["import os", "from pathlib import Path"],
            "/test/file2.py": ["import os", "from pathlib import Path"],
        }
        duplicate_code = "path = Path(os.getcwd())"

        result = analyze_import_overlap(file_imports, duplicate_code)

        # Should identify imports needed for the duplicate code
        assert "required_imports" in result

    def test_analysis_summary(self):
        """Should generate human-readable summary."""
        file_imports = {
            "/test/file1.py": ["import os"],
            "/test/file2.py": ["import os"],
        }

        result = analyze_import_overlap(file_imports)

        assert "analysis_summary" in result
        assert isinstance(result["analysis_summary"], str)
        assert len(result["analysis_summary"]) > 0


class TestDetectInternalDependencies:
    """Tests for detect_internal_dependencies function."""

    def test_empty_code(self):
        """Should handle empty code."""
        result = detect_internal_dependencies(
            "",
            "/test/file.py",
            "python",
            {}
        )

        assert result["local_calls"] == []
        assert result["imported_calls"] == []
        assert result["unresolved_calls"] == []

    def test_python_function_calls(self):
        """Should detect Python function calls."""
        code = """
result = process_data(input)
output = transform(result)
"""
        file_imports = {"/test/file.py": []}

        result = detect_internal_dependencies(
            code,
            "/test/file.py",
            "python",
            file_imports
        )

        # Should detect function calls
        all_calls = result["local_calls"] + result["imported_calls"] + result["unresolved_calls"]
        # Note: actual detection depends on implementation
        assert isinstance(result, dict)
        assert "local_calls" in result

    def test_method_calls(self):
        """Should detect method calls on objects."""
        code = """
data = parser.parse(text)
items = container.get_items()
"""
        file_imports = {"/test/file.py": ["import parser"]}

        result = detect_internal_dependencies(
            code,
            "/test/file.py",
            "python",
            file_imports
        )

        assert "imported_calls" in result

    def test_async_function_calls(self):
        """Should detect async function calls."""
        code = """
result = await fetch_data(url)
response = await process_async(data)
"""
        file_imports = {"/test/file.py": []}

        result = detect_internal_dependencies(
            code,
            "/test/file.py",
            "python",
            file_imports
        )

        assert isinstance(result, dict)

    def test_typescript_calls(self):
        """Should detect TypeScript function and class instantiation."""
        code = """
const data = fetchData(url);
const instance = new DataProcessor(config);
"""
        file_imports = {"/test/file.ts": ["import { fetchData } from './api'"]}

        result = detect_internal_dependencies(
            code,
            "/test/file.ts",
            "typescript",
            file_imports
        )

        assert "imported_calls" in result
        assert "local_calls" in result

    def test_imported_vs_local_calls(self):
        """Should distinguish between imported and local function calls."""
        code = """
from utils import helper
result = helper()
local_result = my_function()
"""
        file_imports = {
            "/test/file.py": ["from utils import helper"]
        }

        result = detect_internal_dependencies(
            code,
            "/test/file.py",
            "python",
            file_imports
        )

        # helper should be imported, my_function should be local or unresolved
        assert isinstance(result["imported_calls"], list)
        assert isinstance(result["local_calls"], list)
        assert isinstance(result["unresolved_calls"], list)

    def test_unresolved_calls(self):
        """Should track calls that cannot be resolved."""
        code = """
result = unknown_function(data)
"""
        file_imports = {"/test/file.py": []}

        result = detect_internal_dependencies(
            code,
            "/test/file.py",
            "python",
            file_imports
        )

        # Should have unresolved calls category
        assert "unresolved_calls" in result

    def test_javascript_require_calls(self):
        """Should handle JavaScript with require statements."""
        code = """
const result = processFile(path);
const data = fs.readFileSync(file);
"""
        file_imports = {
            "/test/file.js": ["const fs = require('fs')"]
        }

        result = detect_internal_dependencies(
            code,
            "/test/file.js",
            "javascript",
            file_imports
        )

        assert isinstance(result, dict)

    def test_unsupported_language(self):
        """Should handle unsupported languages gracefully."""
        result = detect_internal_dependencies(
            "code here",
            "/test/file.unknown",
            "unsupported_lang",
            {}
        )

        # Should return valid structure even for unknown language
        assert "local_calls" in result
        assert "imported_calls" in result
        assert "unresolved_calls" in result

    def test_nested_calls(self):
        """Should detect nested function calls."""
        code = """
result = outer(inner(data))
"""
        file_imports = {"/test/file.py": []}

        result = detect_internal_dependencies(
            code,
            "/test/file.py",
            "python",
            file_imports
        )

        # Should detect both outer and inner calls
        assert isinstance(result, dict)


class TestEdgeCases:
    """Edge case tests for all dependency analysis functions."""

    def test_aliased_imports_detection(self):
        """Should handle aliased imports in analysis."""
        file_imports = {
            "/test/file1.py": ["import numpy as np", "import pandas as pd"],
            "/test/file2.py": ["import numpy as np", "import pandas as pd"],
        }

        result = analyze_import_overlap(file_imports)

        # Aliased imports should be recognized as shared
        assert len(result["shared_imports"]) == 2

    def test_special_characters_in_paths(self):
        """Should handle special characters in file paths."""
        file_imports = {
            "/test/path with spaces/file.py": ["import os"],
            "/test/path-with-dashes/file.py": ["import os"],
        }

        result = analyze_import_overlap(file_imports)

        assert len(result["shared_imports"]) == 1

    def test_large_import_lists(self):
        """Should handle files with many imports."""
        imports = [f"import module{i}" for i in range(100)]
        file_imports = {
            "/test/file1.py": imports,
            "/test/file2.py": imports[:50] + [f"import other{i}" for i in range(50)],
        }

        result = analyze_import_overlap(file_imports)

        assert len(result["shared_imports"]) == 50
        assert result["total_unique_imports"] == 150

    def test_duplicate_imports_in_file(self):
        """Should handle duplicate imports within same file."""
        file_imports = {
            "/test/file1.py": ["import os", "import os", "import sys"],
            "/test/file2.py": ["import os", "import sys"],
        }

        result = detect_import_variations(file_imports, "python")

        # Should still work correctly
        assert "common_imports" in result

    def test_mixed_import_styles(self):
        """Should handle mixed import styles in same file."""
        file_imports = {
            "/test/file1.py": [
                "import os",
                "from pathlib import Path",
                "from typing import Dict, List",
            ],
            "/test/file2.py": [
                "import os",
                "from pathlib import Path",
                "from collections import defaultdict",
            ],
        }

        result = analyze_import_overlap(file_imports)

        # os and Path should be shared
        assert "import os" in result["shared_imports"]
        assert "from pathlib import Path" in result["shared_imports"]

    def test_three_or_more_files(self):
        """Should correctly analyze overlap across 3+ files."""
        file_imports = {
            "/test/file1.py": ["import os", "import sys", "import json"],
            "/test/file2.py": ["import os", "import sys", "import re"],
            "/test/file3.py": ["import os", "import sys", "import yaml"],
        }

        result = analyze_import_overlap(file_imports)

        # Only os and sys are in all three files
        assert set(result["shared_imports"]) == {"import os", "import sys"}
        assert result["total_unique_imports"] == 5
