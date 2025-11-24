"""Unit tests for complexity scoring functions.

Tests calculate_refactoring_complexity and get_complexity_level functions
for accurate complexity assessment of code duplication refactoring.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import calculate_refactoring_complexity, get_complexity_level


class TestGetComplexityLevel:
    """Tests for get_complexity_level function."""

    def test_low_complexity_threshold_lower(self):
        """Score of 1 should be low complexity."""
        result = get_complexity_level(1.0)
        assert result['level'] == 'low'
        assert 'Simple refactoring' in result['description']

    def test_low_complexity_threshold_upper(self):
        """Score of 3.0 should be low complexity (boundary)."""
        result = get_complexity_level(3.0)
        assert result['level'] == 'low'

    def test_medium_complexity_threshold_lower(self):
        """Score of 3.1 should be medium complexity."""
        result = get_complexity_level(3.1)
        assert result['level'] == 'medium'
        assert 'Moderate refactoring' in result['description']

    def test_medium_complexity_threshold_upper(self):
        """Score of 6.0 should be medium complexity (boundary)."""
        result = get_complexity_level(6.0)
        assert result['level'] == 'medium'

    def test_high_complexity_threshold_lower(self):
        """Score of 6.1 should be high complexity."""
        result = get_complexity_level(6.1)
        assert result['level'] == 'high'
        assert 'Complex refactoring' in result['description']

    def test_high_complexity_threshold_upper(self):
        """Score of 10 should be high complexity."""
        result = get_complexity_level(10.0)
        assert result['level'] == 'high'

    def test_description_contains_guidance(self):
        """All levels should provide actionable descriptions."""
        low = get_complexity_level(2.0)
        assert 'minimal parameters' in low['description']

        medium = get_complexity_level(5.0)
        assert 'testing' in medium['description']

        high = get_complexity_level(8.0)
        assert 'incremental approach' in high['description']


class TestCalculateRefactoringComplexity:
    """Tests for calculate_refactoring_complexity function."""

    def test_minimal_complexity(self):
        """Empty/minimal input should return lowest score."""
        result = calculate_refactoring_complexity({})
        assert result['score'] == 1.0
        assert result['level'] == 'low'
        assert result['raw_score'] == 0

    def test_simple_refactoring_low_complexity(self):
        """Simple literal change should score low (1-3)."""
        result = calculate_refactoring_complexity({
            'parameter_count': 1,
            'line_count': 5,
            'nesting_depth': 1
        })
        # 1*1.5 + 5*0.1 + 1*1.5 = 3.5 raw -> ~2.05 scaled
        assert result['score'] <= 3.0
        assert result['level'] == 'low'

    def test_moderate_refactoring_medium_complexity(self):
        """Multiple params with some logic should score medium (3-6)."""
        result = calculate_refactoring_complexity({
            'parameter_count': 3,
            'control_flow_branches': 2,
            'line_count': 20,
            'nesting_depth': 2,
            'import_count': 2
        })
        # 3*1.5 + 2*2.5 + 20*0.1 + 2*1.5 + 2*1.0 = 4.5+5+2+3+2 = 16.5 raw
        # scaled = 1 + (16.5/30)*9 = 5.95
        assert 3.0 < result['score'] <= 6.0
        assert result['level'] == 'medium'

    def test_complex_refactoring_high_complexity(self):
        """Cross-file with complex logic should score high (7-10)."""
        result = calculate_refactoring_complexity({
            'parameter_count': 5,
            'parameter_type_complexity': 2,
            'control_flow_branches': 5,
            'import_count': 4,
            'cross_file_dependency': 1,
            'line_count': 50,
            'nesting_depth': 4,
            'return_complexity': 2
        })
        # 5*1.5 + 2*1.0 + 5*2.5 + 4*1.0 + 1*2.0 + 50*0.1 + 4*1.5 + 2*1.0
        # = 7.5 + 2 + 12.5 + 4 + 2 + 5 + 6 + 2 = 41 raw -> capped at 10
        assert result['score'] >= 7.0
        assert result['level'] == 'high'

    def test_parameter_count_contribution(self):
        """Parameter count should contribute with weight 1.5."""
        result = calculate_refactoring_complexity({'parameter_count': 4})
        assert result['breakdown']['parameter_count'] == 6.0  # 4 * 1.5

    def test_parameter_type_complexity_contribution(self):
        """Parameter type complexity should contribute with weight 1.0."""
        result = calculate_refactoring_complexity({'parameter_type_complexity': 2})
        assert result['breakdown']['parameter_type_complexity'] == 2.0

    def test_control_flow_branches_contribution(self):
        """Control flow branches should contribute with weight 2.5."""
        result = calculate_refactoring_complexity({'control_flow_branches': 3})
        assert result['breakdown']['control_flow_branches'] == 7.5  # 3 * 2.5

    def test_import_count_contribution(self):
        """Import count should contribute with weight 1.0."""
        result = calculate_refactoring_complexity({'import_count': 5})
        assert result['breakdown']['import_count'] == 5.0

    def test_cross_file_dependency_contribution(self):
        """Cross-file dependency should contribute with weight 2.0."""
        result = calculate_refactoring_complexity({'cross_file_dependency': 1})
        assert result['breakdown']['cross_file_dependency'] == 2.0

    def test_line_count_contribution_capped(self):
        """Line count should be capped at 50 with weight 0.1."""
        result = calculate_refactoring_complexity({'line_count': 100})
        assert result['breakdown']['line_count'] == 5.0  # min(100, 50) * 0.1

    def test_line_count_contribution_under_cap(self):
        """Line count under cap should use actual value."""
        result = calculate_refactoring_complexity({'line_count': 30})
        assert result['breakdown']['line_count'] == 3.0  # 30 * 0.1

    def test_nesting_depth_contribution(self):
        """Nesting depth should contribute with weight 1.5."""
        result = calculate_refactoring_complexity({'nesting_depth': 3})
        assert result['breakdown']['nesting_depth'] == 4.5  # 3 * 1.5

    def test_return_complexity_contribution(self):
        """Return complexity should contribute with weight 1.0."""
        result = calculate_refactoring_complexity({'return_complexity': 2})
        assert result['breakdown']['return_complexity'] == 2.0

    def test_scaling_minimum_bound(self):
        """Score should be at least 1.0."""
        result = calculate_refactoring_complexity({})
        assert result['score'] >= 1.0

    def test_scaling_maximum_bound(self):
        """Score should be at most 10.0."""
        result = calculate_refactoring_complexity({
            'parameter_count': 100,
            'control_flow_branches': 100,
            'nesting_depth': 100
        })
        assert result['score'] == 10.0

    def test_raw_score_calculation(self):
        """Raw score should be sum of all weighted factors."""
        result = calculate_refactoring_complexity({
            'parameter_count': 2,
            'control_flow_branches': 1,
            'line_count': 10
        })
        expected_raw = 2*1.5 + 1*2.5 + 10*0.1  # 3 + 2.5 + 1 = 6.5
        assert result['raw_score'] == 6.5

    def test_score_rounding(self):
        """Score should be rounded to 1 decimal place."""
        result = calculate_refactoring_complexity({
            'parameter_count': 1,
            'line_count': 7
        })
        # 1*1.5 + 7*0.1 = 2.2 raw -> 1 + (2.2/30)*9 = 1.66
        assert str(result['score']).count('.') <= 1
        if '.' in str(result['score']):
            decimal_places = len(str(result['score']).split('.')[1])
            assert decimal_places <= 1

    def test_result_structure(self):
        """Result should contain all required keys."""
        result = calculate_refactoring_complexity({'parameter_count': 1})
        assert 'score' in result
        assert 'level' in result
        assert 'description' in result
        assert 'breakdown' in result
        assert 'raw_score' in result

    def test_breakdown_contains_all_factors(self):
        """Breakdown should contain all 8 factors."""
        result = calculate_refactoring_complexity({})
        expected_factors = [
            'parameter_count',
            'parameter_type_complexity',
            'control_flow_branches',
            'import_count',
            'cross_file_dependency',
            'line_count',
            'nesting_depth',
            'return_complexity'
        ]
        for factor in expected_factors:
            assert factor in result['breakdown']

    def test_level_matches_score_low(self):
        """Level should match score thresholds for low."""
        result = calculate_refactoring_complexity({'line_count': 5})
        if result['score'] <= 3.0:
            assert result['level'] == 'low'

    def test_level_matches_score_medium(self):
        """Level should match score thresholds for medium."""
        result = calculate_refactoring_complexity({
            'parameter_count': 3,
            'control_flow_branches': 2
        })
        if 3.0 < result['score'] <= 6.0:
            assert result['level'] == 'medium'

    def test_level_matches_score_high(self):
        """Level should match score thresholds for high."""
        result = calculate_refactoring_complexity({
            'parameter_count': 5,
            'control_flow_branches': 5,
            'cross_file_dependency': 1,
            'nesting_depth': 4
        })
        if result['score'] > 6.0:
            assert result['level'] == 'high'


class TestComplexityEdgeCases:
    """Edge case tests for complexity scoring."""

    def test_zero_values(self):
        """All zero values should return minimum score."""
        result = calculate_refactoring_complexity({
            'parameter_count': 0,
            'parameter_type_complexity': 0,
            'control_flow_branches': 0,
            'import_count': 0,
            'cross_file_dependency': 0,
            'line_count': 0,
            'nesting_depth': 0,
            'return_complexity': 0
        })
        assert result['score'] == 1.0
        assert result['raw_score'] == 0

    def test_negative_values_treated_as_provided(self):
        """Negative values should be used as-is (no validation)."""
        result = calculate_refactoring_complexity({
            'parameter_count': -1
        })
        assert result['breakdown']['parameter_count'] == -1.5

    def test_float_values(self):
        """Float values should be accepted."""
        result = calculate_refactoring_complexity({
            'parameter_count': 2.5
        })
        assert result['breakdown']['parameter_count'] == 3.75  # 2.5 * 1.5

    def test_missing_keys_use_defaults(self):
        """Missing keys should default to 0."""
        result = calculate_refactoring_complexity({
            'parameter_count': 2
        })
        assert result['breakdown']['import_count'] == 0
        assert result['breakdown']['nesting_depth'] == 0

    def test_extra_keys_ignored(self):
        """Extra keys in input should be ignored."""
        result = calculate_refactoring_complexity({
            'parameter_count': 1,
            'unknown_factor': 100
        })
        assert 'unknown_factor' not in result['breakdown']
        assert result['score'] < 2.0  # Only parameter_count contributes


class TestComplexityBoundaries:
    """Boundary value tests for complexity thresholds."""

    def test_boundary_low_to_medium(self):
        """Test exact boundary between low and medium (3.0)."""
        # Score of exactly 3.0 should be low
        low_result = get_complexity_level(3.0)
        assert low_result['level'] == 'low'

        # Score just above 3.0 should be medium
        medium_result = get_complexity_level(3.01)
        assert medium_result['level'] == 'medium'

    def test_boundary_medium_to_high(self):
        """Test exact boundary between medium and high (6.0)."""
        # Score of exactly 6.0 should be medium
        medium_result = get_complexity_level(6.0)
        assert medium_result['level'] == 'medium'

        # Score just above 6.0 should be high
        high_result = get_complexity_level(6.01)
        assert high_result['level'] == 'high'

    def test_raw_score_30_gives_max(self):
        """Raw score of 30 should give scaled score of 10."""
        # Create input that gives exactly raw_score = 30
        # Using control_flow_branches: 30/2.5 = 12
        result = calculate_refactoring_complexity({
            'control_flow_branches': 12  # 12 * 2.5 = 30
        })
        assert result['score'] == 10.0

    def test_raw_score_above_30_capped(self):
        """Raw score above 30 should still give scaled score of 10."""
        result = calculate_refactoring_complexity({
            'control_flow_branches': 20  # 20 * 2.5 = 50
        })
        assert result['score'] == 10.0
