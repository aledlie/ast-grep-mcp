"""
Pattern analysis module for deduplication.

This module provides functionality for analyzing code patterns,
identifying variations, and classifying differences between duplicate code blocks.
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import yaml

from ...core.logging import get_logger
from ...models.deduplication import VariationCategory, VariationSeverity


class PatternAnalyzer:
    """Analyzes patterns and variations in duplicate code."""

    def __init__(self):
        """Initialize the pattern analyzer."""
        self.logger = get_logger("deduplication.analyzer")

    def identify_varying_literals(
        self,
        code1: str,
        code2: str,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Identify varying literal values between two similar code blocks.

        Args:
            code1: First code snippet
            code2: Second code snippet
            language: Programming language

        Returns:
            List of varying literals with positions and values
        """
        self.logger.info("identifying_varying_literals", language=language)

        varying_literals = []

        # Extract literals from both code blocks
        for literal_type in ["string", "number", "boolean"]:
            literals1 = self._extract_literals_with_ast_grep(code1, literal_type, language)
            literals2 = self._extract_literals_with_ast_grep(code2, literal_type, language)

            # Match literals by position
            pos_map1 = {(lit["line"], lit["column"]): lit for lit in literals1}
            pos_map2 = {(lit["line"], lit["column"]): lit for lit in literals2}

            # Compare literals at same positions
            all_positions = set(pos_map1.keys()) | set(pos_map2.keys())
            for pos in sorted(all_positions):
                lit1 = pos_map1.get(pos)
                lit2 = pos_map2.get(pos)

                if lit1 and lit2 and lit1["value"] != lit2["value"]:
                    varying_literals.append({
                        "position": pos[0] + 1,  # 1-based line number
                        "column": pos[1],
                        "value1": lit1["value"],
                        "value2": lit2["value"],
                        "literal_type": literal_type
                    })

        # Sort by position
        varying_literals.sort(key=lambda x: (x["position"], x.get("column", 0)))

        self.logger.info(
            "varying_literals_found",
            count=len(varying_literals),
            by_type={
                t: len([v for v in varying_literals if v["literal_type"] == t])
                for t in ["string", "number", "boolean"]
            }
        )

        return varying_literals

    def _extract_literals_with_ast_grep(
        self,
        code: str,
        literal_type: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Extract literals from code using ast-grep."""
        literals = []

        # Language file extensions
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "jsx": ".jsx",
            "tsx": ".tsx",
            "java": ".java",
            "csharp": ".cs",
            "cpp": ".cpp",
            "c": ".c"
        }
        ext = ext_map.get(language, ".py")

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Define ast-grep rules for literal types
            if literal_type == "number":
                rule = {
                    "rule": {
                        "any": [
                            {"kind": "integer"},
                            {"kind": "float"},
                            {"kind": "number"}
                        ]
                    }
                }
            elif literal_type == "string":
                rule = {
                    "rule": {
                        "any": [
                            {"kind": "string"},
                            {"kind": "string_literal"}
                        ]
                    }
                }
            elif literal_type == "boolean":
                rule = {
                    "rule": {
                        "any": [
                            {"kind": "true"},
                            {"kind": "false"},
                            {"kind": "none"},
                            {"kind": "null"}
                        ]
                    }
                }
            else:
                return literals

            rule_yaml = yaml.dump(rule)

            result = subprocess.run(
                ["ast-grep", "scan", "--rule", "-", "--json", temp_path],
                input=rule_yaml,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    matches = json.loads(result.stdout)
                    for match in matches:
                        line = match.get("range", {}).get("start", {}).get("line", 0)
                        col = match.get("range", {}).get("start", {}).get("column", 0)
                        text = match.get("text", "")
                        literals.append({
                            "line": line,
                            "column": col,
                            "value": text,
                            "type": literal_type
                        })
                except json.JSONDecodeError:
                    self.logger.warning("literal_parse_error", literal_type=literal_type)

        except subprocess.TimeoutExpired:
            self.logger.warning("literal_extraction_timeout", literal_type=literal_type)
        except Exception as e:
            self.logger.error("literal_extraction_error", error=str(e), literal_type=literal_type)
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        return literals

    def analyze_duplicate_group_literals(
        self,
        group: List[Dict[str, Any]],
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Analyze a group of duplicates to find all varying literals.

        Args:
            group: List of duplicate code matches
            language: Programming language

        Returns:
            Analysis results with variations and suggestions
        """
        if len(group) < 2:
            return {
                "total_variations": 0,
                "variations": [],
                "suggested_parameters": []
            }

        # Compare first item against all others
        base_code = group[0].get("text", "")
        all_variations = {}  # (line, col, type) -> [values]

        for item in group[1:]:
            code = item.get("text", "")
            if code == base_code:
                continue

            variations = self.identify_varying_literals(base_code, code, language)
            for var in variations:
                key = (var["position"], var.get("column", 0), var["literal_type"])
                if key not in all_variations:
                    all_variations[key] = [var["value1"]]
                if var["value2"] not in all_variations[key]:
                    all_variations[key].append(var["value2"])

        # Format variations
        formatted_variations = []
        suggested_parameters = []

        for (line, col, lit_type), values in sorted(all_variations.items()):
            variation = {
                "position": {"line": line, "column": col},
                "type": lit_type,
                "values": values,
                "unique_count": len(set(values))
            }
            formatted_variations.append(variation)

            # Suggest parameter name
            param_name = self._suggest_parameter_name(lit_type, values[0])
            if param_name and param_name not in suggested_parameters:
                suggested_parameters.append(param_name)

        return {
            "total_variations": len(formatted_variations),
            "variations": formatted_variations,
            "suggested_parameters": suggested_parameters
        }

    def classify_variation(
        self,
        variation_type: str,
        old_value: str,
        new_value: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify a single variation between duplicate code blocks.

        Args:
            variation_type: Type hint from detector
            old_value: Original value
            new_value: New value
            context: Optional surrounding context

        Returns:
            Classification with category, severity, and metadata
        """
        category = self._determine_category(variation_type, old_value, new_value)
        severity = self._determine_severity(category, old_value, new_value)
        complexity = self._calculate_variation_complexity(category, severity, old_value, new_value)

        return {
            "category": category,
            "severity": severity,
            "old_value": old_value,
            "new_value": new_value,
            "context": context,
            "parameterizable": severity in [VariationSeverity.LOW, VariationSeverity.MEDIUM],
            "suggested_param_name": self._suggest_parameter_name(category, old_value),
            "complexity": complexity
        }

    def classify_variations(
        self,
        variations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Classify multiple variations and determine overall complexity.

        Args:
            variations: List of variations to classify

        Returns:
            Overall classification with complexity metrics
        """
        if not variations:
            return {
                "total_variations": 0,
                "complexity_score": 0,
                "refactoring_difficulty": "trivial",
                "classifications": [],
                "parameterizable_count": 0,
                "parameter_suggestions": []
            }

        classifications = []
        total_complexity = 0
        parameterizable_count = 0
        param_suggestions = []

        for var in variations:
            classification = self.classify_variation(
                var.get("type", "unknown"),
                var.get("old_value", ""),
                var.get("new_value", ""),
                var.get("context")
            )
            classifications.append(classification)

            # Aggregate metrics
            total_complexity += classification["complexity"]["score"]
            if classification["parameterizable"]:
                parameterizable_count += 1
            if classification["suggested_param_name"]:
                if classification["suggested_param_name"] not in param_suggestions:
                    param_suggestions.append(classification["suggested_param_name"])

        # Calculate overall complexity
        avg_complexity = total_complexity / len(variations) if variations else 0

        # Determine refactoring difficulty
        if avg_complexity <= 2:
            difficulty = "trivial"
        elif avg_complexity <= 3:
            difficulty = "simple"
        elif avg_complexity <= 4:
            difficulty = "moderate"
        elif avg_complexity <= 5:
            difficulty = "complex"
        else:
            difficulty = "very_complex"

        return {
            "total_variations": len(variations),
            "complexity_score": round(avg_complexity, 2),
            "refactoring_difficulty": difficulty,
            "classifications": classifications,
            "parameterizable_count": parameterizable_count,
            "parameter_suggestions": param_suggestions[:5]  # Top 5 suggestions
        }

    def _determine_category(self, variation_type: str, old_value: str, new_value: str) -> str:
        """Determine the category of a variation."""
        variation_type_lower = variation_type.lower()

        # Direct mapping from detector hints
        if variation_type_lower in ["literal", "string", "number", "boolean"]:
            return VariationCategory.LITERAL

        if variation_type_lower in ["identifier", "name", "variable", "function", "class"]:
            return VariationCategory.IDENTIFIER

        if variation_type_lower in ["type", "annotation", "type_hint"]:
            return VariationCategory.TYPE

        if variation_type_lower in ["expression", "operator", "call"]:
            return VariationCategory.EXPRESSION

        if variation_type_lower in ["logic", "control", "flow", "condition"]:
            return VariationCategory.LOGIC

        # Content-based inference
        return self._infer_category_from_content(old_value, new_value)

    def _infer_category_from_content(self, old_value: str, new_value: str) -> str:
        """Infer category from content when type hint is unavailable."""
        # Check for literal patterns
        if self._is_literal(old_value) and self._is_literal(new_value):
            return VariationCategory.LITERAL

        # Check for type annotations
        if self._is_type_annotation(old_value) or self._is_type_annotation(new_value):
            return VariationCategory.TYPE

        # Check for control flow keywords
        control_keywords = {"if", "else", "elif", "for", "while", "switch", "case", "try", "catch", "except"}
        if any(kw in old_value.lower() or kw in new_value.lower() for kw in control_keywords):
            return VariationCategory.LOGIC

        # Check for expression patterns
        expression_indicators = ["(", ")", "+", "-", "*", "/", "==", "!=", "&&", "||", "and", "or"]
        if any(ind in old_value or ind in new_value for ind in expression_indicators):
            return VariationCategory.EXPRESSION

        # Default to identifier
        return VariationCategory.IDENTIFIER

    def _is_literal(self, value: str) -> bool:
        """Check if a value appears to be a literal."""
        value = value.strip()

        # String literals
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return True

        # Numeric literals
        try:
            float(value)
            return True
        except ValueError:
            pass

        # Boolean literals
        if value.lower() in ["true", "false", "none", "null", "nil"]:
            return True

        return False

    def _is_type_annotation(self, value: str) -> bool:
        """Check if a value appears to be a type annotation."""
        type_indicators = [
            "->", ":", "Optional[", "List[", "Dict[", "Tuple[", "Set[",
            "Union[", "Any", "int", "str", "float", "bool", "None",
            "<", ">",  # Generics in other languages
        ]
        return any(ind in value for ind in type_indicators)

    def _determine_severity(self, category: str, old_value: str, new_value: str) -> str:
        """Determine the severity of a variation."""
        # Literal variations are typically easy
        if category == VariationCategory.LITERAL:
            return VariationSeverity.LOW

        # Identifier variations depend on scope
        if category == VariationCategory.IDENTIFIER:
            old_words = len(old_value.split("_")) + len(old_value.split())
            new_words = len(new_value.split("_")) + len(new_value.split())
            if abs(old_words - new_words) > 2:
                return VariationSeverity.MEDIUM
            return VariationSeverity.LOW

        # Type variations require careful handling
        if category == VariationCategory.TYPE:
            if "[" in old_value or "[" in new_value:
                return VariationSeverity.MEDIUM
            return VariationSeverity.LOW

        # Expression variations need analysis
        if category == VariationCategory.EXPRESSION:
            if "(" in old_value and "(" in new_value:
                return VariationSeverity.HIGH if old_value.split("(")[0] != new_value.split("(")[0] else VariationSeverity.MEDIUM
            return VariationSeverity.MEDIUM

        # Logic variations are complex
        if category == VariationCategory.LOGIC:
            return VariationSeverity.HIGH

        return VariationSeverity.MEDIUM

    def _suggest_parameter_name(self, category: str, value: str) -> Optional[str]:
        """Suggest a parameter name for a variation."""
        if category == VariationCategory.LITERAL:
            if any(kw in value.lower() for kw in ["url", "path", "file"]):
                return "target_path"
            if any(kw in value.lower() for kw in ["name", "id", "key"]):
                return "identifier"
            if any(char.isdigit() for char in value):
                return "value"
            return "text_value"

        if category == VariationCategory.IDENTIFIER:
            return "name"

        if category == VariationCategory.TYPE:
            return "type_param"

        if category == VariationCategory.EXPRESSION:
            return "expression"

        if category == VariationCategory.LOGIC:
            return None  # Logic variations typically can't be parameterized simply

        return None

    def _calculate_variation_complexity(
        self,
        category: str,
        severity: str,
        old_value: str,
        new_value: str
    ) -> Dict[str, Any]:
        """
        Calculate complexity score for a variation.

        Scores range from 1-7:
        - 1: Trivial (literal substitution)
        - 2-3: Simple (identifier/expression)
        - 4-5: Moderate (type/complex expression)
        - 6-7: Complex (logic/structure)
        """
        score = 1
        reasoning = ""

        if category == VariationCategory.LITERAL:
            score = 1
            reasoning = "Simple value substitution"

        elif category == VariationCategory.IDENTIFIER:
            if severity == VariationSeverity.LOW:
                score = 1
                reasoning = "Simple identifier rename"
            else:
                score = 2
                reasoning = "Identifier with semantic differences"

        elif category == VariationCategory.EXPRESSION:
            if severity == VariationSeverity.LOW:
                score = 3
                reasoning = "Minor expression variation"
            elif severity == VariationSeverity.MEDIUM:
                score = 4
                reasoning = "Different operations or function calls"
            else:
                score = 4
                reasoning = "Significant expression restructuring"

        elif category == VariationCategory.TYPE:
            if severity == VariationSeverity.LOW:
                score = 4
                reasoning = "Simple type substitution"
            elif severity == VariationSeverity.MEDIUM:
                score = 5
                reasoning = "Generic type variation"
            else:
                score = 6
                reasoning = "Complex type system changes"

        elif category == VariationCategory.LOGIC:
            if "inserted" in str(old_value) or "deleted" in str(new_value):
                score = 7
                reasoning = "Added or removed logic branches"
            elif severity == VariationSeverity.HIGH:
                score = 7
                reasoning = "Significant control flow differences"
            else:
                score = 5
                reasoning = "Conditional logic variation"

        else:
            score = 3
            reasoning = "Unknown variation type"

        # Determine complexity level
        if score <= 2:
            level = "trivial"
        elif score <= 4:
            level = "moderate"
        else:
            level = "complex"

        return {
            "score": score,
            "level": level,
            "reasoning": reasoning
        }
