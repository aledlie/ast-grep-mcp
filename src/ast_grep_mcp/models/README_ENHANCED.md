# models

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "models",
  "description": "Directory containing 9 code files with 97 classes and 1 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "97 class definitions",
    "1 function definitions"
  ]
}
</script>

## Overview

This directory contains 9 code file(s) with extracted schemas.

## Files and Schemas

### `complexity.py` (python)

**Classes:**
- `ComplexityMetrics` - Line 10
  - Immutable metrics container for a single function.
- `FunctionComplexity` - Line 21
  - Complete analysis result for one function.
- `ComplexityThresholds` - Line 34
  - Configurable thresholds with sensible defaults.

**Functions:**
- `get_complexity_level(score) -> str` - Line 43

**Key Imports:** `ast_grep_mcp.constants`, `dataclasses`, `typing`

### `config.py` (python)

**Classes:**
- `CustomLanguageConfig` (extends: BaseModel) - Line 8
  - Configuration for a custom language in sgconfig.yaml.
  - Methods: validate_extensions
- `AstGrepConfig` (extends: BaseModel) - Line 29
  - Pydantic model for validating sgconfig.yaml structure.
  - Methods: validate_dirs, validate_custom_languages

**Key Imports:** `pydantic`, `typing`

### `cross_language.py` (python)

**Classes:**
- `ConversionStyle` (extends: Enum) - Line 16
  - Code conversion style options.
- `BindingStyle` (extends: Enum) - Line 24
  - API binding generation style.
- `RefactoringType` (extends: Enum) - Line 32
  - Cross-language refactoring types.
- `SemanticPattern` - Line 46
  - A semantic pattern that can match across languages.
- `MultiLanguageMatch` - Line 61
  - A match found in multi-language search.
- `MultiLanguageSearchResult` - Line 82
  - Result of multi-language search operation.
- `PatternExample` - Line 110
  - An example of a pattern in a specific language.
- `PatternEquivalence` - Line 127
  - Equivalent patterns across multiple languages.
- `PatternEquivalenceResult` - Line 150
  - Result of pattern equivalence lookup.
- `TypeMapping` - Line 176
  - Type mapping between languages.
- `ConversionWarning` - Line 193
  - Warning generated during code conversion.
- `ConvertedCode` - Line 210
  - Result of code conversion.
- `ConversionResult` - Line 237
  - Complete result of language conversion operation.
- `PolyglotChange` - Line 261
  - A change in a specific language during polyglot refactoring.
- `PolyglotRefactoringPlan` - Line 282
  - Plan for polyglot refactoring.
- `PolyglotRefactoringResult` - Line 305
  - Result of polyglot refactoring operation.
- `ApiEndpoint` - Line 333
  - An API endpoint parsed from specification.
- `GeneratedBinding` - Line 360
  - A generated API client binding.
- `BindingGenerationResult` - Line 381
  - Result of API binding generation.

**Key Imports:** `dataclasses`, `enum`, `typing`

### `deduplication.py` (python)

**Classes:**
- `VariationCategory` - Line 7
  - Categories for classifying variations between duplicate code blocks.
- `VariationSeverity` - Line 17
  - Severity levels for variations.
- `AlignmentSegment` - Line 26
  - Represents a segment in the alignment between two code blocks.
  - Methods: __post_init__
- `AlignmentResult` - Line 45
  - Result of aligning two code blocks for comparison.
- `DiffTreeNode` - Line 57
  - A node in a hierarchical diff tree structure.
  - Methods: __post_init__, add_child, get_all_nodes, find_by_type, get_depth (+1 more)
- `DiffTree` - Line 104
  - Hierarchical representation of code differences.
  - Methods: get_statistics, serialize_for_display
- `FunctionTemplate` - Line 166
  - Template for generating extracted functions from duplicate code.
  - Methods: __post_init__, format_params, format_decorators, format_return_type, generate
- `ParameterType` - Line 274
  - Represents an inferred type for an extracted parameter.
  - Methods: __init__, _get_type_map, get_type_annotation, __str__
- `ParameterInfo` - Line 340
  - Represents a parameter for code generation with type information.
  - Methods: __init__, to_signature
- `FileDiff` - Line 387
  - Represents a diff for a single file.
- `DiffPreview` - Line 412
  - Container for multi-file diff preview.
  - Methods: to_dict, get_file_diff
- `EnhancedDuplicationCandidate` - Line 460
  - Enhanced duplication candidate with full reporting details.
  - Methods: to_summary

**Key Imports:** `dataclasses`, `typing`

### `documentation.py` (python)

**Classes:**
- `DocstringStyle` (extends: Enum) - Line 8
  - Supported docstring styles.
- `ChangeType` (extends: Enum) - Line 19
  - Type of change in changelog.
- `ParameterInfo` - Line 31
  - Information about a function parameter.
- `FunctionSignature` - Line 48
  - Parsed function signature information.
- `GeneratedDocstring` - Line 77
  - A generated docstring for a function.
- `DocstringGenerationResult` - Line 102
  - Result of docstring generation for a project.
- `ProjectInfo` - Line 132
  - Analyzed project information.
- `ReadmeSection` - Line 161
  - A generated README section.
- `ReadmeGenerationResult` - Line 178
  - Result of README section generation.
- `RouteParameter` - Line 200
  - API route parameter.
- `RouteResponse` - Line 221
  - API route response schema.
- `ApiRoute` - Line 240
  - Parsed API route information.
- `ApiDocsResult` - Line 269
  - Result of API documentation generation.
- `CommitInfo` - Line 293
  - Parsed git commit information.
- `ChangelogEntry` - Line 326
  - A single changelog entry.
- `ChangelogVersion` - Line 349
  - Changelog entries for a specific version.
- `ChangelogResult` - Line 366
  - Result of changelog generation.
- `DocSyncIssue` - Line 390
  - An issue found during documentation sync.
- `DocSyncResult` - Line 413
  - Result of documentation sync check.

**Key Imports:** `dataclasses`, `enum`, `typing`

### `orphan.py` (python)

**Classes:**
- `OrphanType` (extends: str, Enum) - Line 12
  - Type of orphan artifact.
- `VerificationStatus` (extends: str, Enum) - Line 21
  - Verification status for orphan detection.
- `OrphanFile` - Line 31
  - Represents an orphan file (not imported anywhere).
  - Methods: to_dict
- `OrphanFunction` - Line 68
  - Represents an orphan function (defined but never called).
  - Methods: lines, to_dict
- `DependencyEdge` - Line 115
  - Represents a dependency between two files.
- `DependencyGraph` - Line 132
  - Represents the import dependency graph.
  - Methods: get_importers, get_imports, is_reachable_from_entry
- `OrphanAnalysisConfig` - Line 175
  - Configuration for orphan analysis.
- `OrphanAnalysisResult` - Line 223
  - Result of orphan code analysis.
  - Methods: total_orphan_lines, orphan_file_count, orphan_function_count, to_dict

**Key Imports:** `dataclasses`, `enum`, `typing`

### `refactoring.py` (python)

**Classes:**
- `VariableType` (extends: Enum) - Line 8
  - Classification of variables in code selection.
- `RefactoringType` (extends: Enum) - Line 18
  - Types of refactoring operations.
- `VariableInfo` - Line 29
  - Information about a variable in code selection.
- `CodeSelection` - Line 42
  - Represents a selection of code for refactoring.
  - Methods: get_variables_by_type
- `FunctionSignature` - Line 65
  - Generated function signature.
  - Methods: to_python_signature, to_typescript_signature
- `ExtractFunctionResult` - Line 95
  - Result of extract function operation.
- `ScopeInfo` - Line 110
  - Information about a scope in the code.
- `SymbolReference` - Line 122
  - Reference to a symbol in code.
- `RenameSymbolResult` - Line 137
  - Result of rename symbol operation.
- `StyleConversion` - Line 153
  - Configuration for style conversion.
- `ConversionResult` - Line 165
  - Result of code style conversion.
- `SimplificationResult` - Line 179
  - Result of conditional simplification.
- `RefactoringStep` - Line 193
  - Single step in batch refactoring.
- `BatchRefactoringResult` - Line 203
  - Result of batch refactoring operation.

**Key Imports:** `dataclasses`, `enum`, `typing`

### `schema_enhancement.py` (python)

**Classes:**
- `EnhancementPriority` (extends: Enum) - Line 8
  - Priority levels for Schema.org enhancements.
- `EnhancementCategory` (extends: Enum) - Line 24
  - Categories of schema enhancement issues.
- `PropertyEnhancement` - Line 41
  - Enhancement suggestion for a missing property.
- `EntityEnhancement` - Line 62
  - Enhancement suggestions for a single entity.
- `MissingEntitySuggestion` - Line 83
  - Suggestion for a missing entity type in the graph.
- `GraphEnhancementResult` - Line 102
  - Complete result of entity graph enhancement analysis.

**Key Imports:** `dataclasses`, `enum`, `typing`

### `standards.py` (python)

**Classes:**
- `RuleValidationError` (extends: Exception) - Line 7
  - Raised when a linting rule validation fails.
- `RuleStorageError` (extends: Exception) - Line 13
  - Raised when saving/loading rules fails.
- `LintingRule` - Line 20
  - Represents a custom linting rule.
  - Methods: to_yaml_dict
- `RuleTemplate` - Line 75
  - Pre-built rule template.
- `RuleValidationResult` - Line 106
  - Result of rule validation.
- `RuleViolation` - Line 121
  - Single violation of a linting rule.
- `RuleSet` - Line 152
  - Collection of linting rules with metadata.
- `EnforcementResult` - Line 169
  - Complete results from standards enforcement scan.
- `RuleExecutionContext` - Line 194
  - Context for executing rules (internal use).
- `FixResult` - Line 222
  - Result of applying a single fix to a violation.
- `FixValidation` - Line 247
  - Result of validating a proposed fix.
- `FixBatchResult` - Line 266
  - Result of applying multiple fixes.
- `SecurityIssue` - Line 298
  - Represents a detected security vulnerability.
- `SecurityScanResult` - Line 335
  - Result from security vulnerability scan.

**Key Imports:** `dataclasses`, `typing`

---
*Generated by Enhanced Schema Generator with schema.org markup*