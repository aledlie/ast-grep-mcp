"""Unit tests for Phase 4.4: Impact Analysis for Deduplication.

Tests for:
- analyze_deduplication_impact
- _extract_function_names_from_code
- _find_external_call_sites
- _find_import_references
- _estimate_lines_changed
- _assess_breaking_change_risk
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ast_grep_mcp.features.deduplication.impact import analyze_deduplication_impact
from main import (
    _assess_breaking_change_risk,
    _estimate_lines_changed,
    _extract_function_names_from_code,
    _find_external_call_sites,
    _find_import_references,
)


class TestExtractFunctionNamesFromCode:
    """Tests for _extract_function_names_from_code function."""

    def test_python_function_extraction(self):
        """Test extracting function names from Python code."""
        code = '''
def process_data(items):
    return [x * 2 for x in items]

def validate_input(data):
    return data is not None
'''
        names = _extract_function_names_from_code(code, "python")
        assert "process_data" in names
        assert "validate_input" in names

    def test_python_class_extraction(self):
        """Test extracting class names from Python code."""
        code = '''
class DataProcessor:
    def __init__(self):
        pass

class ResultHandler:
    pass
'''
        names = _extract_function_names_from_code(code, "python")
        assert "DataProcessor" in names
        assert "ResultHandler" in names

    def test_javascript_function_extraction(self):
        """Test extracting function names from JavaScript code."""
        code = '''
function fetchData(url) {
    return fetch(url);
}

const processItems = (items) => {
    return items.map(x => x * 2);
};
'''
        names = _extract_function_names_from_code(code, "javascript")
        assert "fetchData" in names

    def test_typescript_method_extraction(self):
        """Test extracting method names from TypeScript code."""
        code = '''
class Service {
    getData(id: string) {
        return this.repository.find(id);
    }

    saveData(data: any) {
        return this.repository.save(data);
    }
}
'''
        names = _extract_function_names_from_code(code, "typescript")
        # Methods are extracted, class name may or may not be depending on pattern
        assert "getData" in names or "saveData" in names

    def test_java_method_extraction(self):
        """Test extracting method names from Java code."""
        code = '''
public class UserService {
    public User findUser(String id) {
        return repository.findById(id);
    }

    private void validateUser(User user) {
        // validation logic
    }
}
'''
        names = _extract_function_names_from_code(code, "java")
        assert "UserService" in names
        assert "findUser" in names or "validateUser" in names

    def test_go_function_extraction(self):
        """Test extracting function names from Go code."""
        code = '''
func ProcessData(items []int) []int {
    result := make([]int, len(items))
    return result
}

func (s *Service) HandleRequest(req Request) Response {
    return Response{}
}
'''
        names = _extract_function_names_from_code(code, "go")
        assert "ProcessData" in names
        assert "HandleRequest" in names

    def test_rust_function_extraction(self):
        """Test extracting function names from Rust code."""
        code = '''
fn process_data(items: Vec<i32>) -> Vec<i32> {
    items.iter().map(|x| x * 2).collect()
}

struct DataProcessor {
    items: Vec<i32>,
}
'''
        names = _extract_function_names_from_code(code, "rust")
        assert "process_data" in names
        assert "DataProcessor" in names

    def test_empty_code(self):
        """Test with empty code."""
        names = _extract_function_names_from_code("", "python")
        assert names == []

    def test_filters_common_words(self):
        """Test that common words are filtered out."""
        code = '''
def get():
    pass

def main():
    pass

def process_data():
    pass
'''
        names = _extract_function_names_from_code(code, "python")
        assert "main" not in names
        assert "get" not in names
        assert "process_data" in names


class TestFindExternalCallSites:
    """Tests for _find_external_call_sites function."""

    @patch('main.run_ast_grep')
    def test_finds_call_sites(self, mock_run):
        """Test finding external call sites."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "file": "/project/caller.py",
                "range": {"start": {"line": 10, "column": 4}},
                "text": "process_data(items)"
            }
        ])
        mock_run.return_value = mock_result

        call_sites = _find_external_call_sites(
            function_names=["process_data"],
            project_root="/project",
            language="python",
            exclude_files=["/project/original.py"]
        )

        assert len(call_sites) == 1
        assert call_sites[0]["file"] == "/project/caller.py"
        assert call_sites[0]["line"] == 11  # 0-indexed + 1
        assert call_sites[0]["function_called"] == "process_data"
        assert call_sites[0]["type"] == "function_call"

    @patch('main.run_ast_grep')
    def test_excludes_duplicate_files(self, mock_run):
        """Test that files containing duplicates are excluded."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "file": "/project/original.py",  # Should be excluded
                "range": {"start": {"line": 5, "column": 0}},
                "text": "process_data(items)"
            }
        ])
        mock_run.return_value = mock_result

        call_sites = _find_external_call_sites(
            function_names=["process_data"],
            project_root="/project",
            language="python",
            exclude_files=["/project/original.py"]
        )

        assert len(call_sites) == 0

    @patch('main.run_ast_grep')
    def test_handles_no_matches(self, mock_run):
        """Test handling no matches found."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        call_sites = _find_external_call_sites(
            function_names=["process_data"],
            project_root="/project",
            language="python",
            exclude_files=[]
        )

        assert call_sites == []

    def test_empty_function_names(self):
        """Test with empty function names list."""
        call_sites = _find_external_call_sites(
            function_names=[],
            project_root="/project",
            language="python",
            exclude_files=[]
        )

        assert call_sites == []


class TestFindImportReferences:
    """Tests for _find_import_references function."""

    @patch('main.run_ast_grep')
    def test_finds_python_imports(self, mock_run):
        """Test finding Python import references."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "file": "/project/consumer.py",
                "range": {"start": {"line": 1, "column": 0}},
                "text": "from utils import process_data"
            }
        ])
        mock_run.return_value = mock_result

        import_refs = _find_import_references(
            function_names=["process_data"],
            project_root="/project",
            language="python",
            exclude_files=["/project/utils.py"]
        )

        # Multiple patterns may match the same import
        assert len(import_refs) >= 1
        assert import_refs[0]["file"] == "/project/consumer.py"
        assert import_refs[0]["imported_name"] == "process_data"
        assert import_refs[0]["type"] == "import"

    @patch('main.run_ast_grep')
    def test_finds_javascript_imports(self, mock_run):
        """Test finding JavaScript import references."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "file": "/project/consumer.js",
                "range": {"start": {"line": 0, "column": 0}},
                "text": "import { fetchData } from './utils'"
            }
        ])
        mock_run.return_value = mock_result

        import_refs = _find_import_references(
            function_names=["fetchData"],
            project_root="/project",
            language="javascript",
            exclude_files=[]
        )

        # Multiple patterns may match the same import
        assert len(import_refs) >= 1
        assert import_refs[0]["imported_name"] == "fetchData"

    def test_empty_function_names(self):
        """Test with empty function names list."""
        import_refs = _find_import_references(
            function_names=[],
            project_root="/project",
            language="python",
            exclude_files=[]
        )

        assert import_refs == []


class TestEstimeLinesChanged:
    """Tests for _estimate_lines_changed function."""

    def test_basic_estimate(self):
        """Test basic lines changed estimation."""
        result = _estimate_lines_changed(
            duplicate_count=3,
            lines_per_duplicate=10,
            external_call_sites=0
        )

        # Deletions: (3-1) * 10 = 20
        assert result["deletions"] == 20

        # Additions should include extracted function, imports, replacement calls
        assert result["additions"] > 0
        assert "net_change" in result
        assert "breakdown" in result

    def test_with_external_call_sites(self):
        """Test estimation with external call sites."""
        result = _estimate_lines_changed(
            duplicate_count=2,
            lines_per_duplicate=5,
            external_call_sites=3
        )

        # Should include updates for external calls
        assert result["breakdown"]["external_call_updates"] == 3

    def test_breakdown_structure(self):
        """Test that breakdown has all expected fields."""
        result = _estimate_lines_changed(
            duplicate_count=2,
            lines_per_duplicate=10,
            external_call_sites=1
        )

        breakdown = result["breakdown"]
        assert "extracted_function" in breakdown
        assert "new_imports" in breakdown
        assert "replacement_calls" in breakdown
        assert "external_call_updates" in breakdown

    def test_net_change_calculation(self):
        """Test that net change is calculated correctly."""
        result = _estimate_lines_changed(
            duplicate_count=5,
            lines_per_duplicate=20,
            external_call_sites=0
        )

        expected_net = result["additions"] - result["deletions"]
        assert result["net_change"] == expected_net


class TestAssessBreakingChangeRisk:
    """Tests for _assess_breaking_change_risk function."""

    def test_low_risk_no_external_refs(self):
        """Test low risk when no external references exist."""
        result = _assess_breaking_change_risk(
            function_names=["_private_func"],
            files_in_group=["/project/src/module.py"],
            external_call_sites=[],
            project_root="/project",
            language="python"
        )

        assert result["level"] == "low"
        assert result["score"] <= 1

    def test_medium_risk_external_calls(self):
        """Test medium risk with external call sites."""
        external_refs = [
            {"type": "function_call", "file": "/project/other.py"},
            {"type": "function_call", "file": "/project/another.py"}
        ]

        result = _assess_breaking_change_risk(
            function_names=["process_data"],
            files_in_group=["/project/src/module.py"],
            external_call_sites=external_refs,
            project_root="/project",
            language="python"
        )

        # Should be medium or higher due to external refs and public name
        assert result["level"] in ("medium", "high")
        assert len(result["factors"]) > 0

    def test_high_risk_public_api(self):
        """Test high risk for public API functions."""
        external_refs = [
            {"type": "function_call", "file": "/project/other.py"},
            {"type": "import", "file": "/project/consumer.py"}
        ]

        result = _assess_breaking_change_risk(
            function_names=["PublicFunction"],
            files_in_group=[
                "/project/src/module1.py",
                "/project/lib/module2.py"
            ],
            external_call_sites=external_refs,
            project_root="/project",
            language="python"
        )

        # Should have risk factors
        assert len(result["factors"]) > 0
        assert len(result["recommendations"]) > 0

    def test_reduced_risk_for_test_files(self):
        """Test that test files reduce risk score."""
        result = _assess_breaking_change_risk(
            function_names=["test_helper"],
            files_in_group=[
                "/project/tests/test_module.py",
                "/project/tests/test_other.py"
            ],
            external_call_sites=[],
            project_root="/project",
            language="python"
        )

        # Should have a factor about test files
        test_factor = any("test" in f.lower() for f in result["factors"])
        assert test_factor or result["level"] == "low"

    def test_high_risk_init_files(self):
        """Test high risk for __init__.py files."""
        result = _assess_breaking_change_risk(
            function_names=["exported_func"],
            files_in_group=["/project/package/__init__.py"],
            external_call_sites=[],
            project_root="/project",
            language="python"
        )

        # Should have high risk due to module export
        has_export_factor = any("export" in f.lower() for f in result["factors"])
        assert has_export_factor

    def test_cross_module_risk(self):
        """Test risk factor for cross-module duplicates."""
        result = _assess_breaking_change_risk(
            function_names=["shared_func"],
            files_in_group=[
                "/project/module_a/file.py",
                "/project/module_b/file.py",
                "/project/module_c/file.py"
            ],
            external_call_sites=[],
            project_root="/project",
            language="python"
        )

        # Should mention cross-module
        has_cross_module = any("module" in f.lower() or "director" in f.lower()
                              for f in result["factors"])
        assert has_cross_module

    def test_recommendations_present(self):
        """Test that recommendations are always provided."""
        result = _assess_breaking_change_risk(
            function_names=["any_func"],
            files_in_group=["/project/file.py"],
            external_call_sites=[],
            project_root="/project",
            language="python"
        )

        assert "recommendations" in result
        assert len(result["recommendations"]) > 0


class TestAnalyzeDeduplicationImpact:
    """Tests for the main analyze_deduplication_impact function."""

    @patch('main._find_external_call_sites')
    @patch('main._find_import_references')
    def test_basic_impact_analysis(self, mock_imports, mock_calls):
        """Test basic impact analysis."""
        mock_calls.return_value = []
        mock_imports.return_value = []

        duplicate_group = {
            "locations": [
                "/project/src/file1.py:10-20",
                "/project/src/file2.py:5-15"
            ],
            "sample_code": "def process_data(items):\n    return [x * 2 for x in items]",
            "duplicate_count": 2,
            "lines_per_duplicate": 10
        }

        result = analyze_deduplication_impact(
            duplicate_group=duplicate_group,
            project_root="/project",
            language="python"
        )

        assert "files_affected" in result
        assert "lines_changed" in result
        assert "external_call_sites" in result
        assert "breaking_change_risk" in result

    @patch('main._find_external_call_sites')
    @patch('main._find_import_references')
    def test_files_affected_count(self, mock_imports, mock_calls):
        """Test that files_affected count is correct."""
        mock_calls.return_value = [
            {"file": "/project/caller1.py", "type": "function_call"},
            {"file": "/project/caller2.py", "type": "function_call"}
        ]
        mock_imports.return_value = []

        duplicate_group = {
            "locations": [
                "/project/src/file1.py:10-20",
                "/project/src/file2.py:5-15"
            ],
            "sample_code": "def process_data():\n    pass",
            "duplicate_count": 2,
            "lines_per_duplicate": 5
        }

        result = analyze_deduplication_impact(
            duplicate_group=duplicate_group,
            project_root="/project",
            language="python"
        )

        # 2 files in group + 2 external files
        assert result["files_affected"] == 4

    @patch('main._find_external_call_sites')
    @patch('main._find_import_references')
    def test_empty_locations(self, mock_imports, mock_calls):
        """Test handling of empty locations."""
        mock_calls.return_value = []
        mock_imports.return_value = []

        duplicate_group = {
            "locations": [],
            "sample_code": "",
            "duplicate_count": 0,
            "lines_per_duplicate": 0
        }

        result = analyze_deduplication_impact(
            duplicate_group=duplicate_group,
            project_root="/project",
            language="python"
        )

        assert result["files_affected"] == 0
        assert result["external_call_sites"] == []

    @patch('main._find_external_call_sites')
    @patch('main._find_import_references')
    def test_combines_call_sites_and_imports(self, mock_imports, mock_calls):
        """Test that call sites and imports are combined."""
        mock_calls.return_value = [
            {"file": "/project/caller.py", "type": "function_call"}
        ]
        mock_imports.return_value = [
            {"file": "/project/importer.py", "type": "import"}
        ]

        duplicate_group = {
            "locations": ["/project/src/file.py:1-10"],
            "sample_code": "def process():\n    pass",
            "duplicate_count": 1,
            "lines_per_duplicate": 5
        }

        result = analyze_deduplication_impact(
            duplicate_group=duplicate_group,
            project_root="/project",
            language="python"
        )

        # Should have both call site and import
        assert len(result["external_call_sites"]) == 2
        types = {ref["type"] for ref in result["external_call_sites"]}
        assert "function_call" in types
        assert "import" in types


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    @patch('main.run_ast_grep')
    def test_real_world_python_scenario(self, mock_run):
        """Test a realistic Python deduplication scenario."""
        # Mock ast-grep returning some call sites
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "file": "/project/services/user_service.py",
                "range": {"start": {"line": 25, "column": 8}},
                "text": "validate_email(email)"
            },
            {
                "file": "/project/api/handlers.py",
                "range": {"start": {"line": 42, "column": 12}},
                "text": "validate_email(user_email)"
            }
        ])
        mock_run.return_value = mock_result

        duplicate_group = {
            "locations": [
                "/project/utils/validators.py:10-25",
                "/project/helpers/validation.py:5-20"
            ],
            "sample_code": '''def validate_email(email):
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))''',
            "duplicate_count": 2,
            "lines_per_duplicate": 5
        }

        result = analyze_deduplication_impact(
            duplicate_group=duplicate_group,
            project_root="/project",
            language="python"
        )

        # Should identify external call sites
        assert result["files_affected"] >= 2
        assert result["breaking_change_risk"]["level"] in ("low", "medium", "high")
        assert len(result["breaking_change_risk"]["recommendations"]) > 0

    @patch('main.run_ast_grep')
    def test_typescript_component_scenario(self, mock_run):
        """Test a TypeScript component deduplication scenario."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        duplicate_group = {
            "locations": [
                "/project/src/components/UserCard.tsx:15-45",
                "/project/src/components/ProfileCard.tsx:20-50"
            ],
            "sample_code": '''function formatDate(date: Date): string {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}''',
            "duplicate_count": 2,
            "lines_per_duplicate": 6
        }

        result = analyze_deduplication_impact(
            duplicate_group=duplicate_group,
            project_root="/project",
            language="typescript"
        )

        assert "files_affected" in result
        assert result["lines_changed"]["deletions"] == 6  # (2-1) * 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
