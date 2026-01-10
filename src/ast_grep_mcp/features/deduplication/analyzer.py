"""
Pattern analysis module for deduplication.

This module provides functionality for analyzing code patterns,
identifying variations, and classifying differences between duplicate code blocks.
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from ...core.logging import get_logger
from ...models.deduplication import VariationCategory, VariationSeverity


class PatternAnalyzer:
    """Analyzes patterns and variations in duplicate code."""

    def __init__(self) -> None:
        """Initialize the pattern analyzer."""
        self.logger = get_logger("deduplication.analyzer")

    def identify_varying_literals(self, code1: str, code2: str, language: str = "python") -> List[Dict[str, Any]]:
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
                    varying_literals.append(
                        {
                            "position": pos[0] + 1,  # 1-based line number
                            "column": pos[1],
                            "value1": lit1["value"],
                            "value2": lit2["value"],
                            "literal_type": literal_type,
                        }
                    )

        # Sort by position
        varying_literals.sort(key=lambda x: (x["position"], x.get("column", 0)))

        self.logger.info(
            "varying_literals_found",
            count=len(varying_literals),
            by_type={t: len([v for v in varying_literals if v["literal_type"] == t]) for t in ["string", "number", "boolean"]},
        )

        return varying_literals

    def _extract_literals_with_ast_grep(self, code: str, literal_type: str, language: str) -> List[Dict[str, Any]]:
        """Extract literals from code using ast-grep."""
        literals: List[Dict[str, Any]] = []

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
            "c": ".c",
        }
        ext = ext_map.get(language, ".py")

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Define ast-grep rules for literal types
            if literal_type == "number":
                rule = {"rule": {"any": [{"kind": "integer"}, {"kind": "float"}, {"kind": "number"}]}}
            elif literal_type == "string":
                rule = {"rule": {"any": [{"kind": "string"}, {"kind": "string_literal"}]}}
            elif literal_type == "boolean":
                rule = {"rule": {"any": [{"kind": "true"}, {"kind": "false"}, {"kind": "none"}, {"kind": "null"}]}}
            else:
                return literals

            rule_yaml = yaml.dump(rule)

            result = subprocess.run(
                ["ast-grep", "scan", "--rule", "-", "--json", temp_path], input=rule_yaml, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    matches = json.loads(result.stdout)
                    for match in matches:
                        line = match.get("range", {}).get("start", {}).get("line", 0)
                        col = match.get("range", {}).get("start", {}).get("column", 0)
                        text = match.get("text", "")
                        literals.append({"line": line, "column": col, "value": text, "type": literal_type})
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

    def analyze_duplicate_group_literals(self, group: List[Dict[str, Any]], language: str = "python") -> Dict[str, Any]:
        """
        Analyze a group of duplicates to find all varying literals.

        Args:
            group: List of duplicate code matches
            language: Programming language

        Returns:
            Analysis results with variations and suggestions
        """
        if len(group) < 2:
            return {"total_variations": 0, "variations": [], "suggested_parameters": []}

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
            variation = {"position": {"line": line, "column": col}, "type": lit_type, "values": values, "unique_count": len(set(values))}
            formatted_variations.append(variation)

            # Suggest parameter name
            param_name = self._suggest_parameter_name(lit_type, values[0])
            if param_name and param_name not in suggested_parameters:
                suggested_parameters.append(param_name)

        return {
            "total_variations": len(formatted_variations),
            "variations": formatted_variations,
            "suggested_parameters": suggested_parameters,
        }

    def classify_variation(self, variation_type: str, old_value: str, new_value: str, context: Optional[str] = None) -> Dict[str, Any]:
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
            "complexity": complexity,
        }

    def classify_variations(self, variations: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "parameter_suggestions": [],
            }

        classifications = []
        total_complexity = 0
        parameterizable_count = 0
        param_suggestions = []

        for var in variations:
            classification = self.classify_variation(
                var.get("type", "unknown"), var.get("old_value", ""), var.get("new_value", ""), var.get("context")
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
            "parameter_suggestions": param_suggestions[:5],  # Top 5 suggestions
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
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
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
            "->",
            ":",
            "Optional[",
            "List[",
            "Dict[",
            "Tuple[",
            "Set[",
            "Union[",
            "Any",
            "int",
            "str",
            "float",
            "bool",
            "None",
            "<",
            ">",  # Generics in other languages
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

    def _score_literal_variation(self) -> tuple[int, str]:
        """Score literal category variation."""
        return 1, "Simple value substitution"

    def _score_identifier_variation(self, severity: str) -> tuple[int, str]:
        """Score identifier category variation."""
        if severity == VariationSeverity.LOW:
            return 1, "Simple identifier rename"
        return 2, "Identifier with semantic differences"

    def _score_expression_variation(self, severity: str) -> tuple[int, str]:
        """Score expression category variation."""
        if severity == VariationSeverity.LOW:
            return 3, "Minor expression variation"
        if severity == VariationSeverity.MEDIUM:
            return 4, "Different operations or function calls"
        return 4, "Significant expression restructuring"

    def _score_type_variation(self, severity: str) -> tuple[int, str]:
        """Score type category variation."""
        if severity == VariationSeverity.LOW:
            return 4, "Simple type substitution"
        if severity == VariationSeverity.MEDIUM:
            return 5, "Generic type variation"
        return 6, "Complex type system changes"

    def _score_logic_variation(self, severity: str, old_value: str, new_value: str) -> tuple[int, str]:
        """Score logic category variation."""
        if "inserted" in str(old_value) or "deleted" in str(new_value):
            return 7, "Added or removed logic branches"
        if severity == VariationSeverity.HIGH:
            return 7, "Significant control flow differences"
        return 5, "Conditional logic variation"

    def _get_complexity_level(self, score: int) -> str:
        """Get complexity level from score."""
        if score <= 2:
            return "trivial"
        if score <= 4:
            return "moderate"
        return "complex"

    def _calculate_variation_complexity(self, category: str, severity: str, old_value: str, new_value: str) -> Dict[str, Any]:
        """
        Calculate complexity score for a variation.

        Scores range from 1-7:
        - 1: Trivial (literal substitution)
        - 2-3: Simple (identifier/expression)
        - 4-5: Moderate (type/complex expression)
        - 6-7: Complex (logic/structure)
        """
        # Use a mapping to handle category scoring
        scorers: Dict[str, Callable[[], Tuple[int, str]]] = {
            VariationCategory.LITERAL: lambda: self._score_literal_variation(),
            VariationCategory.IDENTIFIER: lambda: self._score_identifier_variation(severity),
            VariationCategory.EXPRESSION: lambda: self._score_expression_variation(severity),
            VariationCategory.TYPE: lambda: self._score_type_variation(severity),
            VariationCategory.LOGIC: lambda: self._score_logic_variation(severity, old_value, new_value),
        }

        # Get score and reasoning for the category
        scorer = scorers.get(category)
        if scorer:
            score, reasoning = scorer()
        else:
            score, reasoning = 3, "Unknown variation type"

        # Determine complexity level
        level = self._get_complexity_level(score)

        return {"score": score, "level": level, "reasoning": reasoning}

    def detect_conditional_variations(self, code1: str, code2: str, language: str = "python") -> List[Dict[str, Any]]:
        """
        Detect variations in conditional statements between two code blocks.

        Analyzes if/else conditions, comparison operators, and conditional values
        to identify differences that could be parameterized.

        Args:
            code1: First code snippet
            code2: Second code snippet
            language: Programming language (default: python)

        Returns:
            List of conditional variations with details about the differences
        """
        self.logger.info("detecting_conditional_variations", language=language)

        variations: List[Dict[str, Any]] = []

        # Extract conditionals from both code blocks using ast-grep
        conditionals1 = self._extract_conditionals(code1, language)
        conditionals2 = self._extract_conditionals(code2, language)

        # Compare conditionals by position
        max_len = max(len(conditionals1), len(conditionals2))

        for i in range(max_len):
            cond1 = conditionals1[i] if i < len(conditionals1) else None
            cond2 = conditionals2[i] if i < len(conditionals2) else None

            if cond1 and cond2:
                # Both exist - check for differences
                if cond1["text"] != cond2["text"]:
                    variation = {
                        "position": i + 1,
                        "type": "modified",
                        "condition1": cond1["text"],
                        "condition2": cond2["text"],
                        "line1": cond1.get("line", 0),
                        "line2": cond2.get("line", 0),
                    }
                    # Analyze the specific variation
                    variation["details"] = self._analyze_conditional_difference(
                        cond1["text"], cond2["text"], language
                    )
                    variations.append(variation)
            elif cond1:
                # Only in first code block
                variations.append({
                    "position": i + 1,
                    "type": "removed",
                    "condition1": cond1["text"],
                    "condition2": None,
                    "line1": cond1.get("line", 0),
                })
            elif cond2:
                # Only in second code block
                variations.append({
                    "position": i + 1,
                    "type": "added",
                    "condition1": None,
                    "condition2": cond2["text"],
                    "line2": cond2.get("line", 0),
                })

        self.logger.info(
            "conditional_variations_found",
            count=len(variations),
            by_type={
                "modified": len([v for v in variations if v["type"] == "modified"]),
                "added": len([v for v in variations if v["type"] == "added"]),
                "removed": len([v for v in variations if v["type"] == "removed"]),
            },
        )

        return variations

    def _extract_conditionals(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Extract conditional statements from code using ast-grep."""
        conditionals: List[Dict[str, Any]] = []

        # Language file extensions
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
        }
        ext = ext_map.get(language, ".py")

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Define ast-grep rule for conditionals based on language
            if language == "python":
                rule = {"rule": {"any": [
                    {"kind": "if_statement"},
                    {"kind": "elif_clause"},
                    {"kind": "comparison_operator"},
                ]}}
            else:
                # JavaScript/TypeScript/Java
                rule = {"rule": {"any": [
                    {"kind": "if_statement"},
                    {"kind": "binary_expression"},
                    {"kind": "ternary_expression"},
                ]}}

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
                        text = match.get("text", "")
                        kind = match.get("kind", "unknown")
                        conditionals.append({
                            "line": line,
                            "text": text.strip(),
                            "kind": kind,
                        })
                except json.JSONDecodeError:
                    self.logger.warning("conditional_parse_error", language=language)

        except subprocess.TimeoutExpired:
            self.logger.warning("conditional_extraction_timeout", language=language)
        except FileNotFoundError:
            # ast-grep not installed - fall back to regex
            conditionals = self._extract_conditionals_regex(code, language)
        except Exception as e:
            self.logger.error("conditional_extraction_error", error=str(e))
            # Fall back to regex extraction
            conditionals = self._extract_conditionals_regex(code, language)
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        return conditionals

    def _extract_conditionals_regex(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Fallback regex-based extraction for conditionals."""
        import re
        conditionals: List[Dict[str, Any]] = []

        # Pattern for if/elif conditions
        if language == "python":
            pattern = r'(?:if|elif)\s+(.+?):'
        else:
            pattern = r'(?:if|else\s+if)\s*\((.+?)\)'

        for i, line in enumerate(code.split('\n'), 1):
            match = re.search(pattern, line)
            if match:
                conditionals.append({
                    "line": i,
                    "text": match.group(0).strip(),
                    "kind": "if_statement",
                })

        return conditionals

    def _get_language_extension(self, language: str) -> str:
        """Get file extension for a programming language."""
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
        }
        return ext_map.get(language, ".py")

    def _get_call_rule(self, language: str) -> Dict[str, Any]:
        """Get ast-grep rule for call expressions based on language."""
        if language == "python":
            return {"rule": {"kind": "call"}}
        return {"rule": {"kind": "call_expression"}}

    def _find_nested_call_in_matches(
        self, matches: List[Dict[str, Any]], identifier: str
    ) -> Optional[Dict[str, Any]]:
        """Find nested function call containing identifier in ast-grep matches."""
        for match in matches:
            text = match.get("text", "")
            if identifier not in text:
                continue
            nesting_depth = self._calculate_call_nesting_depth(text, identifier)
            if nesting_depth > 1:
                return {
                    "identifier": identifier,
                    "nesting_depth": nesting_depth,
                    "call_expression": text,
                    "line": match.get("range", {}).get("start", {}).get("line", 0) + 1,
                }
        return None

    def _run_ast_grep_for_calls(
        self, temp_path: str, language: str, identifier: str
    ) -> Optional[Dict[str, Any]]:
        """Run ast-grep to find nested function calls."""
        rule = self._get_call_rule(language)
        rule_yaml = yaml.dump(rule)

        result = subprocess.run(
            ["ast-grep", "scan", "--rule", "-", "--json", temp_path],
            input=rule_yaml,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        try:
            matches = json.loads(result.stdout)
            return self._find_nested_call_in_matches(matches, identifier)
        except json.JSONDecodeError:
            self.logger.warning("nested_call_parse_error", language=language)
            return None

    def detect_nested_function_call(
        self, code: str, identifier: str, language: str = "python"
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if an identifier is used within nested function calls.

        Args:
            code: Source code to analyze
            identifier: The identifier to look for
            language: Programming language

        Returns:
            Dict with nesting info if found, None otherwise
        """
        self.logger.info("detecting_nested_function_call", identifier=identifier, language=language)

        ext = self._get_language_extension(language)

        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            return self._run_ast_grep_for_calls(temp_path, language, identifier)
        except subprocess.TimeoutExpired:
            self.logger.warning("nested_call_detection_timeout", language=language)
        except FileNotFoundError:
            return self._detect_nested_call_regex(code, identifier)
        except Exception as e:
            self.logger.error("nested_call_detection_error", error=str(e))
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        return None

    def _calculate_call_nesting_depth(self, expression: str, identifier: str) -> int:
        """Calculate the nesting depth of function calls around an identifier."""
        # Count opening parentheses before the identifier
        idx = expression.find(identifier)
        if idx == -1:
            return 0

        depth = 0
        max_depth = 0
        for i, char in enumerate(expression[:idx]):
            if char == '(':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == ')':
                depth -= 1

        return max_depth

    def _detect_nested_call_regex(self, code: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Fallback regex-based detection for nested function calls."""
        import re

        # Pattern for nested function calls: func(func(...identifier...))
        # Look for identifier within parentheses that are inside other parentheses
        pattern = r'(\w+)\s*\(\s*(\w+)\s*\([^)]*' + re.escape(identifier) + r'[^)]*\)'

        for i, line in enumerate(code.split('\n'), 1):
            match = re.search(pattern, line)
            if match:
                return {
                    "identifier": identifier,
                    "nesting_depth": 2,
                    "call_expression": match.group(0),
                    "line": i,
                    "outer_function": match.group(1),
                    "inner_function": match.group(2),
                }

        return None

    def _analyze_conditional_difference(
        self, cond1: str, cond2: str, language: str
    ) -> Dict[str, Any]:
        """Analyze the specific differences between two conditional expressions."""
        import re

        details: Dict[str, Any] = {
            "operator_changed": False,
            "value_changed": False,
            "variable_changed": False,
            "comparison_values": {},
        }

        # Extract comparison operators
        operators = [">=", "<=", "!=", "==", ">", "<", "in", "not in", "is not", "is"]
        op1 = op2 = None

        for op in operators:
            if op in cond1:
                op1 = op
                break
        for op in operators:
            if op in cond2:
                op2 = op
                break

        if op1 and op2 and op1 != op2:
            details["operator_changed"] = True
            details["operators"] = {"from": op1, "to": op2}

        # Extract numeric values
        nums1 = re.findall(r'\b\d+(?:\.\d+)?\b', cond1)
        nums2 = re.findall(r'\b\d+(?:\.\d+)?\b', cond2)

        if nums1 != nums2:
            details["value_changed"] = True
            details["comparison_values"] = {
                "from": nums1,
                "to": nums2,
            }

        # Extract identifiers (simple check)
        # Remove operators and numbers to find variable names
        for op in operators:
            cond1 = cond1.replace(op, " ")
            cond2 = cond2.replace(op, " ")

        vars1 = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', cond1)) - {"if", "elif", "else"}
        vars2 = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', cond2)) - {"if", "elif", "else"}

        if vars1 != vars2:
            details["variable_changed"] = True
            details["variables"] = {
                "from": list(vars1),
                "to": list(vars2),
            }

        return details


# Standalone function for backward compatibility
def detect_conditional_variations(code1: str, code2: str, language: str = "python") -> List[Dict[str, Any]]:
    """
    Detect variations in conditional statements between two code blocks.

    This is a convenience function that creates a PatternAnalyzer instance
    and calls its detect_conditional_variations method.

    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Programming language (default: python)

    Returns:
        List of conditional variations with details about the differences
    """
    analyzer = PatternAnalyzer()
    return analyzer.detect_conditional_variations(code1, code2, language)


def _detect_nested_function_call(
    code: str, identifier: str, language: str = "python"
) -> Optional[Dict[str, Any]]:
    """
    Detect if an identifier is used within nested function calls.

    This is a convenience function that creates a PatternAnalyzer instance
    and calls its detect_nested_function_call method.

    Args:
        code: Source code to analyze
        identifier: The identifier to look for
        language: Programming language (default: python)

    Returns:
        Dict with nesting info if found, None otherwise
    """
    analyzer = PatternAnalyzer()
    return analyzer.detect_nested_function_call(code, identifier, language)


def classify_variations(code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
    """
    Classify variations between two code snippets.

    Compares two code blocks and identifies the types and severity of
    differences between them.

    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Programming language (default: python)

    Returns:
        Dictionary containing:
        - severity: Overall severity level (low, medium, high)
        - variations: List of specific variations found
        - parameterizable: Whether differences can be parameterized
        - suggested_refactoring: Recommended refactoring approach
    """
    analyzer = PatternAnalyzer()

    # Find variations between the code snippets
    variations = []

    # Identify varying literals
    literal_variations = analyzer.identify_varying_literals(code1, code2, language)
    for lit_var in literal_variations:
        variations.append({
            "type": "literal",
            "old_value": lit_var.get("value1", ""),
            "new_value": lit_var.get("value2", ""),
            "context": lit_var.get("context", ""),
        })

    # Identify conditional variations
    cond_variations = analyzer.detect_conditional_variations(code1, code2, language)
    for cond_var in cond_variations:
        variations.append({
            "type": "conditional",
            "old_value": cond_var.get("condition1", ""),
            "new_value": cond_var.get("condition2", ""),
            "context": f"line {cond_var.get('line1', 0)}",
        })

    # Identify varying identifiers
    identifier_variations = identify_varying_identifiers(code1, code2, language)
    for ident_var in identifier_variations:
        variations.append({
            "type": "identifier",
            "old_value": ident_var.get("identifier1", ""),
            "new_value": ident_var.get("identifier2", ""),
            "context": ident_var.get("context", ""),
        })

    # Classify all variations
    if variations:
        classification = analyzer.classify_variations(variations)
        # Determine overall severity based on variation types
        high_count = sum(1 for v in classification.get("classifications", [])
                        if v.get("severity") == VariationSeverity.HIGH)
        medium_count = sum(1 for v in classification.get("classifications", [])
                          if v.get("severity") == VariationSeverity.MEDIUM)

        if high_count > 0:
            overall_severity = VariationSeverity.HIGH
        elif medium_count > len(variations) // 2:
            overall_severity = VariationSeverity.MEDIUM
        else:
            overall_severity = VariationSeverity.LOW

        return {
            "severity": overall_severity,
            "variations": variations,
            "parameterizable": classification.get("parameterizable_count", 0) > 0,
            "suggested_refactoring": "extract_function" if overall_severity != VariationSeverity.HIGH else "manual_review",
            "complexity_score": classification.get("complexity_score", 0),
            "parameter_suggestions": classification.get("parameter_suggestions", []),
        }

    # No variations found - code is identical or nearly identical
    return {
        "severity": VariationSeverity.LOW,
        "variations": [],
        "parameterizable": True,
        "suggested_refactoring": "extract_function",
        "complexity_score": 0,
        "parameter_suggestions": [],
    }


def identify_varying_identifiers(code1: str, code2: str, language: str = "python") -> List[Dict[str, Any]]:
    """
    Identify identifiers that vary between two code snippets.

    Compares identifier usage in two code blocks to find names that
    differ but serve similar purposes (e.g., 'user_id' vs 'order_id').

    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Programming language (default: python)

    Returns:
        List of varying identifier pairs with context
    """
    varying_identifiers: List[Dict[str, Any]] = []

    # Extract identifiers from both code blocks
    identifiers1 = _extract_identifiers_from_code(code1, language)
    identifiers2 = _extract_identifiers_from_code(code2, language)

    # Compare identifiers by position/context
    # Find identifiers that appear in similar positions but with different names
    for pos, ident1 in identifiers1.items():
        if pos in identifiers2:
            ident2 = identifiers2[pos]
            if ident1["name"] != ident2["name"]:
                varying_identifiers.append({
                    "identifier1": ident1["name"],
                    "identifier2": ident2["name"],
                    "position": pos,
                    "context": ident1.get("context", ""),
                    "usage_type": ident1.get("usage_type", "unknown"),
                })

    return varying_identifiers


def _extract_identifiers_from_code(code: str, language: str) -> Dict[int, Dict[str, Any]]:
    """
    Extract identifiers from code with position information.

    Args:
        code: Source code to analyze
        language: Programming language

    Returns:
        Dictionary mapping position to identifier info
    """
    identifiers: Dict[int, Dict[str, Any]] = {}

    # Simple regex-based extraction for common patterns
    # This handles most common identifier patterns across languages
    import re

    # Pattern for identifiers (variable names, function names, etc.)
    identifier_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'

    # Keywords to exclude (common across languages)
    keywords = {
        "python": {"def", "class", "if", "else", "elif", "for", "while", "return",
                   "import", "from", "as", "try", "except", "finally", "with",
                   "lambda", "yield", "raise", "pass", "break", "continue",
                   "and", "or", "not", "in", "is", "None", "True", "False",
                   "async", "await", "global", "nonlocal", "assert"},
        "javascript": {"function", "const", "let", "var", "if", "else", "for",
                       "while", "return", "import", "export", "from", "class",
                       "new", "this", "try", "catch", "finally", "throw",
                       "async", "await", "true", "false", "null", "undefined"},
        "typescript": {"function", "const", "let", "var", "if", "else", "for",
                       "while", "return", "import", "export", "from", "class",
                       "new", "this", "try", "catch", "finally", "throw",
                       "async", "await", "true", "false", "null", "undefined",
                       "interface", "type", "enum", "implements", "extends"},
    }

    excluded = keywords.get(language, keywords["python"])

    for idx, match in enumerate(re.finditer(identifier_pattern, code)):
        name = match.group(1)
        if name not in excluded and not name.isupper():  # Exclude constants
            # Get surrounding context
            start = max(0, match.start() - 20)
            end = min(len(code), match.end() + 20)
            context = code[start:end].strip()

            # Determine usage type based on context
            usage_type = "variable"
            if "def " in context or "function " in context:
                usage_type = "function"
            elif "class " in context:
                usage_type = "class"
            elif "(" in context[context.find(name):context.find(name)+len(name)+2]:
                usage_type = "function_call"

            identifiers[idx] = {
                "name": name,
                "position": match.start(),
                "context": context,
                "usage_type": usage_type,
            }

    return identifiers
