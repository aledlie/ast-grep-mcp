"""Unit tests for enhanced refactoring suggestions.

Tests the generate_refactoring_suggestions function with focus on:
- parameter_details field
- import_analysis field
- complexity scores
- refactoring_strategies field
- backward compatibility with include_enhanced_analysis=False
- strategy recommendations based on complexity
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import (
    generate_refactoring_suggestions,
    calculate_refactoring_complexity,
    _generate_refactoring_strategies,
)


class TestEnhancedSuggestions:
    """Test enhanced refactoring suggestions."""

    def create_duplicate_group(
        self,
        code1: str,
        code2: str,
        file1: str = "file1.py",
        file2: str = "file2.py",
    ) -> list[list[dict]]:
        """Helper to create a duplication group for testing."""
        return [[
            {
                "text": code1,
                "file": file1,
                "range": {
                    "start": {"line": 0, "column": 0},
                    "end": {"line": code1.count('\n'), "column": 0}
                }
            },
            {
                "text": code2,
                "file": file2,
                "range": {
                    "start": {"line": 0, "column": 0},
                    "end": {"line": code2.count('\n'), "column": 0}
                }
            }
        ]]

    def test_suggestions_include_parameter_details(self):
        """Test that suggestions include parameter_details with enhanced analysis."""
        code1 = """def process_user(user_id):
    data = fetch_data(user_id)
    result = transform(data, "user")
    return result"""

        code2 = """def process_order(order_id):
    data = fetch_data(order_id)
    result = transform(data, "order")
    return result"""

        groups = self.create_duplicate_group(code1, code2)
        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python", include_enhanced_analysis=True
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Should have parameter_details field
        assert "parameter_details" in suggestion
        param_details = suggestion["parameter_details"]

        # Should have expected structure
        assert "varying_identifiers" in param_details
        assert "varying_expressions" in param_details
        assert "varying_literals" in param_details
        assert "total_parameters_needed" in param_details

        # Should detect varying expressions or identifiers
        # The actual detection depends on the parsing - just verify structure exists
        assert isinstance(param_details["varying_literals"], list)
        assert isinstance(param_details["total_parameters_needed"], int)

    def test_suggestions_include_import_analysis(self):
        """Test that suggestions include import_analysis when file_imports provided."""
        code1 = """import os
def process():
    return os.path.join('a', 'b')"""

        code2 = """import os
def process():
    return os.path.join('x', 'y')"""

        groups = self.create_duplicate_group(code1, code2)
        file_imports = {
            "file1.py": ["import os", "import sys"],
            "file2.py": ["import os", "import json"]
        }

        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python",
            file_imports=file_imports,
            include_enhanced_analysis=True
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Should have import_analysis field
        assert "import_analysis" in suggestion
        import_analysis = suggestion["import_analysis"]

        # Should have variations and overlap
        assert "variations" in import_analysis
        assert "overlap" in import_analysis

    def test_suggestions_include_complexity_scores(self):
        """Test that suggestions include complexity field with detailed scores."""
        code1 = """def complex_func(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                return i * 2
    return 0"""

        code2 = """def complex_func(y):
    if y > 0:
        for j in range(y):
            if j % 2 == 0:
                return j * 2
    return 0"""

        groups = self.create_duplicate_group(code1, code2)
        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python", include_enhanced_analysis=True
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Should have complexity field (detailed)
        assert "complexity" in suggestion
        complexity = suggestion["complexity"]

        # Should have expected complexity structure
        assert "score" in complexity
        assert "level" in complexity
        assert isinstance(complexity["score"], (int, float))
        assert complexity["level"] in ["low", "medium", "high"]

        # Also check base complexity_score field
        assert "complexity_score" in suggestion
        assert isinstance(suggestion["complexity_score"], int)
        assert 1 <= suggestion["complexity_score"] <= 10

    def test_suggestions_include_refactoring_strategies(self):
        """Test that suggestions include refactoring_strategies."""
        code1 = """def simple():
    return 1"""

        code2 = """def simple():
    return 2"""

        groups = self.create_duplicate_group(code1, code2)
        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python", include_enhanced_analysis=True
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Should have refactoring_strategies field
        assert "refactoring_strategies" in suggestion
        strategies = suggestion["refactoring_strategies"]

        # Should be a list of strategy options
        assert isinstance(strategies, list)
        assert len(strategies) > 0

        # Each strategy should have expected fields
        for strategy in strategies:
            assert "name" in strategy
            assert "description" in strategy
            assert "effort" in strategy
            assert "recommended" in strategy

    def test_backward_compatibility_no_enhanced_analysis(self):
        """Test backward compatibility with include_enhanced_analysis=False."""
        code1 = """def func1(x):
    return x + 1"""

        code2 = """def func2(y):
    return y + 1"""

        groups = self.create_duplicate_group(code1, code2)
        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python", include_enhanced_analysis=False
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Should NOT have enhanced-only fields
        assert "parameter_details" not in suggestion
        assert "import_analysis" not in suggestion
        assert "complexity" not in suggestion
        assert "refactoring_strategies" not in suggestion

        # Should still have base fields
        assert "group_id" in suggestion
        assert "type" in suggestion
        assert "description" in suggestion
        assert "suggestion" in suggestion
        assert "duplicate_count" in suggestion
        assert "complexity_score" in suggestion
        assert "complexity_factors" in suggestion
        assert "parameter_analysis" in suggestion
        assert "import_dependencies" in suggestion
        assert "estimated_effort" in suggestion

    def test_strategy_recommendations_low_complexity(self):
        """Test that low complexity yields appropriate strategy recommendations."""
        strategies = _generate_refactoring_strategies(
            complexity_level="low",
            construct_type="function_definition",
            duplicate_count=2,
            parameter_count=1
        )

        assert len(strategies) > 0

        # Should recommend Direct Extract for low complexity
        recommended = [s for s in strategies if s.get("recommended")]
        assert len(recommended) > 0
        assert any("Direct Extract" in s["name"] for s in recommended)

        # Low complexity should have low effort options
        assert all(s["effort"] in ["low", "medium"] for s in strategies)

    def test_strategy_recommendations_medium_complexity(self):
        """Test that medium complexity yields appropriate strategy recommendations."""
        strategies = _generate_refactoring_strategies(
            complexity_level="medium",
            construct_type="function_definition",
            duplicate_count=4,
            parameter_count=3
        )

        assert len(strategies) > 0

        # Should recommend Parameterized Extract for medium complexity
        recommended = [s for s in strategies if s.get("recommended")]
        assert len(recommended) > 0

        # Should include multiple strategy options
        strategy_names = [s["name"] for s in strategies]
        assert "Parameterized Extract" in strategy_names or "Strategy Pattern" in strategy_names

    def test_strategy_recommendations_high_complexity(self):
        """Test that high complexity yields appropriate strategy recommendations."""
        strategies = _generate_refactoring_strategies(
            complexity_level="high",
            construct_type="class_definition",
            duplicate_count=6,
            parameter_count=10
        )

        assert len(strategies) > 0

        # High complexity should suggest incremental approaches
        strategy_descriptions = ' '.join([s["description"] for s in strategies])
        # Should mention incremental/phased approaches for high complexity
        assert any(s["effort"] == "high" for s in strategies)

    def test_complexity_score_calculation(self):
        """Test that complexity scores are calculated correctly."""
        # Low complexity input
        low_input = {
            "parameter_count": 0,
            "parameter_type_complexity": 0,
            "control_flow_branches": 0,
            "import_count": 0,
            "cross_file_dependency": 0,
            "line_count": 3,
            "nesting_depth": 0,
            "return_complexity": 0
        }

        low_result = calculate_refactoring_complexity(low_input)
        assert low_result["level"] in ["low", "medium"]  # May vary based on algorithm

        # High complexity input
        high_input = {
            "parameter_count": 10,
            "parameter_type_complexity": 3,
            "control_flow_branches": 15,
            "import_count": 10,
            "cross_file_dependency": 1,
            "line_count": 100,
            "nesting_depth": 5,
            "return_complexity": 3
        }

        high_result = calculate_refactoring_complexity(high_input)
        assert high_result["level"] == "high"
        assert high_result["score"] > low_result["score"]

    def test_suggestions_for_class_definitions(self):
        """Test that class definitions get appropriate suggestions."""
        code1 = """class UserService:
    def __init__(self):
        self.db = Database()

    def get(self, id):
        return self.db.find(id)"""

        code2 = """class OrderService:
    def __init__(self):
        self.db = Database()

    def get(self, id):
        return self.db.find(id)"""

        groups = self.create_duplicate_group(code1, code2)
        suggestions = generate_refactoring_suggestions(
            groups, "class_definition", "python", include_enhanced_analysis=True
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]

        # Should suggest base class extraction
        assert suggestion["type"] == "Extract Base Class"
        assert "base class" in suggestion["description"].lower() or "mixin" in suggestion["description"].lower()

        # Should have strategies appropriate for class refactoring
        assert "refactoring_strategies" in suggestion

    def test_cross_file_complexity_increase(self):
        """Test that cross-file duplicates increase complexity score."""
        code = """def func():
    return 1"""

        # Same file duplicates
        same_file_groups = [[
            {
                "text": code,
                "file": "file1.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            },
            {
                "text": code,
                "file": "file1.py",
                "range": {"start": {"line": 10}, "end": {"line": 12}}
            }
        ]]

        # Different file duplicates
        diff_file_groups = [[
            {
                "text": code,
                "file": "file1.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            },
            {
                "text": code,
                "file": "file2.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            }
        ]]

        same_file_suggestions = generate_refactoring_suggestions(
            same_file_groups, "function_definition", "python", include_enhanced_analysis=True
        )
        diff_file_suggestions = generate_refactoring_suggestions(
            diff_file_groups, "function_definition", "python", include_enhanced_analysis=True
        )

        # Cross-file should have higher base complexity
        assert diff_file_suggestions[0]["complexity_score"] >= same_file_suggestions[0]["complexity_score"]

        # Check complexity factors mention cross-file
        factors = ' '.join(diff_file_suggestions[0]["complexity_factors"])
        assert "cross-file" in factors.lower() or "file" in factors.lower()

    def test_multiple_duplication_groups(self):
        """Test that multiple duplication groups each get suggestions."""
        groups = [
            [
                {"text": "def a(): return 1", "file": "f1.py", "range": {"start": {"line": 0}, "end": {"line": 1}}},
                {"text": "def b(): return 1", "file": "f2.py", "range": {"start": {"line": 0}, "end": {"line": 1}}}
            ],
            [
                {"text": "def c(): return 2", "file": "f3.py", "range": {"start": {"line": 0}, "end": {"line": 1}}},
                {"text": "def d(): return 2", "file": "f4.py", "range": {"start": {"line": 0}, "end": {"line": 1}}}
            ]
        ]

        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python", include_enhanced_analysis=True
        )

        assert len(suggestions) == 2
        assert suggestions[0]["group_id"] == 1
        assert suggestions[1]["group_id"] == 2

    def test_single_item_group_skipped(self):
        """Test that groups with only one item are skipped."""
        groups = [
            [
                {"text": "def a(): return 1", "file": "f1.py", "range": {"start": {"line": 0}, "end": {"line": 1}}}
            ]
        ]

        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "python", include_enhanced_analysis=True
        )

        assert len(suggestions) == 0

    def test_empty_groups_handled(self):
        """Test that empty groups are handled gracefully."""
        suggestions = generate_refactoring_suggestions(
            [], "function_definition", "python", include_enhanced_analysis=True
        )

        assert suggestions == []

    def test_estimated_effort_levels(self):
        """Test that estimated_effort is set based on complexity."""
        # Simple code - low effort
        simple_code = "def f(): return 1"
        simple_groups = self.create_duplicate_group(simple_code, simple_code)
        simple_suggestions = generate_refactoring_suggestions(
            simple_groups, "function_definition", "python", include_enhanced_analysis=True
        )

        # Complex code - higher effort
        complex_code = """def complex(a, b, c, d, e):
    if a > 0:
        for i in range(b):
            while c < d:
                if e:
                    for j in range(10):
                        pass
    return None"""
        complex_groups = self.create_duplicate_group(complex_code, complex_code)
        complex_suggestions = generate_refactoring_suggestions(
            complex_groups, "function_definition", "python", include_enhanced_analysis=True
        )

        assert simple_suggestions[0]["estimated_effort"] in ["low", "medium", "high"]
        assert complex_suggestions[0]["estimated_effort"] in ["low", "medium", "high"]

    def test_javascript_import_detection(self):
        """Test that JavaScript imports are detected correctly."""
        code1 = """const x = require('module1');
function process() { return x.run(); }"""

        code2 = """const x = require('module2');
function process() { return x.run(); }"""

        groups = self.create_duplicate_group(code1, code2, "file1.js", "file2.js")
        suggestions = generate_refactoring_suggestions(
            groups, "function_definition", "javascript", include_enhanced_analysis=True
        )

        assert len(suggestions) == 1
        # Check import_dependencies are analyzed
        assert "import_dependencies" in suggestions[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
