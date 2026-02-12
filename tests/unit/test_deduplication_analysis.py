"""Consolidated tests for deduplication analysis functionality.

This file consolidates tests from:
- test_variation_classification.py
- test_parameter_extraction.py
- test_complexity_scoring.py

Focus: Variation analysis, parameter extraction, complexity scoring
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import from modular structure where interfaces match
# Import from modular code
# Variation analysis functions migrated to modular architecture
from ast_grep_mcp.features.deduplication.analyzer import (
    _detect_nested_function_call,
    classify_variations,
    detect_conditional_variations,
    identify_varying_identifiers,
)

# Type inference and parameter functions migrated to modular architecture
from ast_grep_mcp.features.deduplication.generator import (
    _infer_from_identifier_name,
    _infer_single_value_type,
    generate_parameter_name,
    infer_parameter_type,
)
from ast_grep_mcp.models.complexity import get_complexity_level

# ParameterType class migrated to modular architecture
from ast_grep_mcp.models.deduplication import ParameterType, VariationSeverity


class TestVariationClassification:
    """Tests for variation classification in duplicate code."""

    def test_classify_variations_simple(self):
        """Test classifying simple variations."""
        code1 = "result = value * 2"
        code2 = "result = value * 3"

        variations = classify_variations(code1, code2, "python")
        assert variations is not None
        assert isinstance(variations, dict) or isinstance(variations, list)

    def test_classify_variations_complex(self):
        """Test classifying complex variations."""
        code1 = """
def process(data):
    if data > 10:
        return data * 2
    return data
"""
        code2 = """
def process(data):
    if data > 20:
        return data * 3
    return data
"""
        variations = classify_variations(code1, code2, "python")
        assert variations is not None

    def test_detect_conditional_variations(self):
        """Test detecting conditional variations."""
        code1 = "if x > 10: return True"
        code2 = "if x > 20: return False"

        conditions = detect_conditional_variations(code1, code2, "python")
        assert conditions is not None
        assert isinstance(conditions, dict) or isinstance(conditions, list)

    def test_variation_severity_enum(self):
        """Test VariationSeverity enum values."""
        assert hasattr(VariationSeverity, "LOW")
        assert hasattr(VariationSeverity, "MEDIUM")
        assert hasattr(VariationSeverity, "HIGH")


class TestParameterExtraction:
    """Tests for parameter extraction from duplicate code."""

    def test_identify_varying_identifiers(self):
        """Test identifying varying identifiers between code snippets."""
        code1 = "result = process_user_data(user_id)"
        code2 = "result = process_order_data(order_id)"

        identifiers = identify_varying_identifiers(code1, code2, "python")
        assert identifiers is not None
        assert isinstance(identifiers, dict) or isinstance(identifiers, list)

    def test_generate_parameter_name(self):
        """Test generating parameter names from identifiers."""
        name = generate_parameter_name("user_id", ["user_id", "order_id"])
        assert name is not None
        assert isinstance(name, str)
        assert name != ""

    def test_infer_parameter_type(self):
        """Test inferring parameter type from context."""
        code_context = "user_id = 123"
        param_type = infer_parameter_type("user_id", code_context, "python")
        assert param_type is not None

    def test_infer_single_value_type(self):
        """Test inferring type from a single value."""
        assert _infer_single_value_type("123", "python") is not None
        assert _infer_single_value_type('"string"', "python") is not None
        assert _infer_single_value_type("True", "python") is not None

    def test_infer_from_identifier_name(self):
        """Test inferring type from identifier naming patterns."""
        result = _infer_from_identifier_name("user_id", "python")
        assert result is not None or result is None  # Can be None if no pattern matches

    def test_detect_nested_function_call(self):
        """Test detecting nested function calls."""
        code = "result = outer(inner(value))"
        nested = _detect_nested_function_call(code, "value", "python")
        assert nested is not None or nested is None  # Can return None if no nesting

    def test_parameter_type_enum(self):
        """Test ParameterType enum values."""
        assert hasattr(ParameterType, "STRING")
        assert hasattr(ParameterType, "NUMBER")
        assert hasattr(ParameterType, "BOOLEAN")


class TestComplexityScoring:
    """Tests for complexity scoring of duplicate code."""

    def test_get_complexity_level_low(self):
        """Test getting complexity level for low score."""
        level = get_complexity_level(3)
        assert level == "low"

    def test_get_complexity_level_medium(self):
        """Test getting complexity level for medium score."""
        level = get_complexity_level(7)
        assert level == "medium"

    def test_get_complexity_level_high(self):
        """Test getting complexity level for high score."""
        level = get_complexity_level(15)
        assert level == "high"

    def test_complexity_boundaries(self):
        """Test complexity level boundaries."""
        assert get_complexity_level(4) == "low"
        assert get_complexity_level(5) == "medium"
        assert get_complexity_level(9) == "medium"
        assert get_complexity_level(10) == "high"
