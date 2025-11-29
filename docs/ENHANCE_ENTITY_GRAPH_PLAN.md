# Implementation Plan: `enhance_entity_graph` MCP Tool

> **Status**: Planning Complete
> **Created**: 2025-11-29
> **Estimated Effort**: 18-28 hours (8 phases)

## Executive Summary

Create a new MCP tool `enhance_entity_graph` that analyzes existing Schema.org JSON-LD graphs and suggests enhancements based on schema.org vocabulary, SEO best practices, and Google Rich Results guidelines.

### Problem Statement

The current `build_entity_graph` tool only CREATES graphs from entity definitions - it doesn't analyze existing schemas. During a real-world analysis of the Leora Home Health schema, we had to manually:

1. Identify missing entity types (FAQPage, BreadcrumbList, WebSite)
2. Find missing properties on Organization (contactPoint, aggregateRating, review)
3. Detect missing properties on Services (offers, termsOfService)
4. Add missing properties on Persons (image, description)
5. Enhance BlogPostings (wordCount, timeRequired, dateModified)
6. Complete HowTo guides (totalTime, prepTime, performTime)

This tool automates that entire workflow.

---

## 1. Tool Specification

### Input Parameters

```python
def enhance_entity_graph(
    input_source: str,      # File path or directory path
    input_type: str = "file",  # "file" or "directory"
    output_mode: str = "analysis"  # "analysis", "enhanced", or "diff"
) -> GraphEnhancementResult
```

### Output Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `analysis` | Returns enhancement suggestions with priorities | Review what's missing |
| `enhanced` | Returns complete graph with placeholder values | Quick implementation |
| `diff` | Returns only the additions needed | Merge with existing |

---

## 2. Architecture Design

### New Files to Create

```
src/ast_grep_mcp/
├── models/
│   └── schema_enhancement.py      # Data models (NEW)
└── features/schema/
    ├── enhancement_rules.py       # Priority rules (NEW)
    └── enhancement_service.py     # Core logic (NEW)
```

### Files to Modify

```
src/ast_grep_mcp/
├── features/schema/tools.py       # Add MCP wrapper
└── server/registry.py             # Update tool count

CLAUDE.md                          # Update tool count (37 → 38)
```

---

## 3. Data Models

### `models/schema_enhancement.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class EnhancementPriority(Enum):
    CRITICAL = "critical"  # Required for Google Rich Results
    HIGH = "high"          # Strongly recommended for SEO
    MEDIUM = "medium"      # Improves discoverability
    LOW = "low"            # Nice to have

class EnhancementCategory(Enum):
    MISSING_PROPERTY = "missing_property"
    MISSING_ENTITY = "missing_entity"
    INVALID_ID = "invalid_id"
    BROKEN_REFERENCE = "broken_reference"

@dataclass
class PropertyEnhancement:
    property_name: str
    expected_types: List[str]
    priority: EnhancementPriority
    reason: str
    example_value: Any
    google_rich_result: Optional[str] = None

@dataclass
class EntityEnhancement:
    entity_id: str
    entity_type: str
    existing_properties: List[str]
    suggested_properties: List[PropertyEnhancement]
    validation_issues: List[str] = field(default_factory=list)
    seo_score: float = 0.0

@dataclass
class MissingEntitySuggestion:
    entity_type: str
    priority: EnhancementPriority
    reason: str
    example: Dict[str, Any]
    google_rich_result: Optional[str] = None

@dataclass
class GraphEnhancementResult:
    original_graph: List[Dict[str, Any]]
    entity_enhancements: List[EntityEnhancement]
    missing_entities: List[MissingEntitySuggestion]
    global_issues: List[str] = field(default_factory=list)
    overall_seo_score: float = 0.0
    priority_summary: Dict[str, int] = field(default_factory=dict)
    enhanced_graph: Optional[Dict[str, Any]] = None
    diff: Optional[Dict[str, Any]] = None
    execution_time_ms: int = 0
```

---

## 4. Enhancement Rules

### Property Priorities by Entity Type

```python
PROPERTY_PRIORITIES = {
    "Organization": {
        "aggregateRating": EnhancementPriority.CRITICAL,  # Reviews snippet
        "review": EnhancementPriority.CRITICAL,
        "contactPoint": EnhancementPriority.HIGH,
        "hasOfferCatalog": EnhancementPriority.MEDIUM,
    },
    "Service": {
        "offers": EnhancementPriority.HIGH,
        "termsOfService": EnhancementPriority.MEDIUM,
    },
    "Person": {
        "image": EnhancementPriority.HIGH,
        "description": EnhancementPriority.MEDIUM,
    },
    "BlogPosting": {
        "wordCount": EnhancementPriority.HIGH,
        "timeRequired": EnhancementPriority.HIGH,
        "dateModified": EnhancementPriority.MEDIUM,
    },
    "HowTo": {
        "totalTime": EnhancementPriority.HIGH,
        "prepTime": EnhancementPriority.MEDIUM,
        "performTime": EnhancementPriority.MEDIUM,
    },
    "MedicalWebPage": {
        "medicalAudience": EnhancementPriority.HIGH,
        "reviewedBy": EnhancementPriority.MEDIUM,
    },
}
```

### Google Rich Results Mapping

```python
RICH_RESULTS_MAP = {
    "aggregateRating": ["Organization reviews", "Product reviews"],
    "review": ["Review snippets"],
    "FAQPage": ["FAQ Rich Results"],
    "BreadcrumbList": ["Breadcrumb navigation"],
    "HowTo": ["How-to Rich Results"],
    "Recipe": ["Recipe Rich Results"],
}
```

### Missing Entity Detection Rules

```python
ENTITY_SUGGESTIONS = {
    "has:Organization AND NOT has:FAQPage": {
        "suggest": "FAQPage",
        "priority": EnhancementPriority.HIGH,
        "reason": "FAQ pages enable FAQ Rich Results"
    },
    "has:Organization AND NOT has:WebSite": {
        "suggest": "WebSite",
        "priority": EnhancementPriority.HIGH,
        "reason": "WebSite enables sitelinks searchbox"
    },
    "count:WebPage>1 AND NOT has:BreadcrumbList": {
        "suggest": "BreadcrumbList",
        "priority": EnhancementPriority.MEDIUM,
        "reason": "Improves navigation hierarchy"
    },
    "has:Service AND NOT has:Review": {
        "suggest": "Review",
        "priority": EnhancementPriority.CRITICAL,
        "reason": "Reviews enable rich snippets"
    },
}
```

---

## 5. Core Service Functions

### `enhancement_service.py`

```python
async def analyze_entity_graph(
    graph_data: Dict[str, Any],
    client: SchemaOrgClient
) -> GraphEnhancementResult:
    """Main entry point - orchestrates all analysis phases."""

async def _analyze_entity(
    entity: Dict[str, Any],
    client: SchemaOrgClient
) -> EntityEnhancement:
    """Analyze single entity, compare properties vs schema.org."""

async def _suggest_missing_entities(
    existing_entities: List[Dict[str, Any]],
    client: SchemaOrgClient
) -> List[MissingEntitySuggestion]:
    """Detect missing entity types based on rules."""

def _score_property(
    property_name: str,
    entity_type: str
) -> EnhancementPriority:
    """Score property importance using enhancement_rules."""

def _calculate_seo_score(
    entity: EntityEnhancement
) -> float:
    """Calculate 0-100 SEO completeness score."""

def _generate_enhanced_graph(
    original: List[Dict[str, Any]],
    enhancements: List[EntityEnhancement],
    missing: List[MissingEntitySuggestion]
) -> Dict[str, Any]:
    """Generate enhanced graph with placeholders."""

def _generate_diff(
    original: List[Dict[str, Any]],
    enhanced: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate additions-only diff."""
```

---

## 6. Data Flow

```
Input (file/directory)
        ↓
   Parse JSON-LD
        ↓
┌───────┴───────┐
↓               ↓
Entity          Missing Entity
Analysis        Detection
↓               ↓
For each:       Pattern matching:
- Fetch props   - has:X AND NOT has:Y
- Compare       - count:X > N
- Score         - Suggest entities
- Validate @id
↓               ↓
└───────┬───────┘
        ↓
  Calculate SEO Score
        ↓
  ┌─────┼─────┐
  ↓     ↓     ↓
analysis  enhanced  diff
  ↓     ↓     ↓
Return  Generate  Generate
report  full      additions
        graph     only
```

---

## 7. Implementation Phases

### Phase 1: Data Models (2-3 hours)
- [ ] Create `models/schema_enhancement.py`
- [ ] Create `features/schema/enhancement_rules.py`
- [ ] Write 5 unit tests for models
- **Validation**: `uv run pytest tests/unit/test_schema_enhancement.py -k "test_models"`

### Phase 2: Core Analysis (4-6 hours)
- [ ] Create `features/schema/enhancement_service.py`
- [ ] Implement `_load_graph_from_file()`
- [ ] Implement `_analyze_entity()`
- [ ] Implement `_score_property()`
- [ ] Write 10 unit tests
- **Validation**: `uv run pytest tests/unit/test_schema_enhancement.py -k "test_analysis"`

### Phase 3: Missing Entity Detection (2-3 hours)
- [ ] Implement `_suggest_missing_entities()`
- [ ] Add pattern matching rules
- [ ] Write 5 unit tests
- **Validation**: `uv run pytest tests/unit/test_schema_enhancement.py -k "test_suggestions"`

### Phase 4: SEO Scoring & Validation (2-3 hours)
- [ ] Implement `_calculate_seo_score()`
- [ ] Implement `_validate_references()`
- [ ] Write 5 unit tests
- **Validation**: `uv run pytest tests/unit/test_schema_enhancement.py -k "test_scoring"`

### Phase 5: Output Generation (3-4 hours)
- [ ] Implement `_generate_enhanced_graph()`
- [ ] Implement `_generate_diff()`
- [ ] Write 8 unit tests
- **Validation**: `uv run pytest tests/unit/test_schema_enhancement.py -k "test_output"`

### Phase 6: Integration (2-3 hours)
- [ ] Implement `analyze_entity_graph()` main function
- [ ] Add Sentry integration
- [ ] Write 5 integration tests
- **Validation**: `uv run pytest tests/integration/test_enhance_entity_graph.py`

### Phase 7: MCP Tool Wrapper (1-2 hours)
- [ ] Add `enhance_entity_graph_tool()` to tools.py
- [ ] Add MCP wrapper to `register_schema_tools()`
- [ ] Update registry.py (37 → 38 tools)
- **Validation**: Manual test via Claude Desktop

### Phase 8: Documentation (1-2 hours)
- [ ] Add docstrings
- [ ] Update CLAUDE.md
- [ ] Create test fixtures
- **Validation**: `uv run pytest tests/ -v`

---

## 8. Test Plan

### Unit Tests (33 tests)

| Test Category | Count | File |
|--------------|-------|------|
| Model validation | 5 | test_schema_enhancement.py |
| Entity analysis | 10 | test_schema_enhancement.py |
| Missing entity detection | 5 | test_schema_enhancement.py |
| SEO scoring | 5 | test_schema_enhancement.py |
| Output generation | 8 | test_schema_enhancement.py |

### Integration Tests (5 tests)

| Test | Description |
|------|-------------|
| test_analyze_leora_health | Real-world graph from session |
| test_analyze_simple_org | Minimal Organization graph |
| test_directory_scanning | Multiple files in directory |
| test_all_output_modes | analysis/enhanced/diff |
| test_error_handling | Invalid inputs |

### Test Fixtures

```
tests/fixtures/schema_graphs/
├── leora_health_original.json  # From this session
├── simple_organization.json    # Minimal test case
└── complete_blogposting.json   # Fully populated
```

---

## 9. Example Output

### Analysis Mode

```json
{
  "entity_enhancements": [
    {
      "entity_id": "https://example.com#organization",
      "entity_type": "Organization",
      "existing_properties": ["name", "url", "logo"],
      "suggested_properties": [
        {
          "property_name": "aggregateRating",
          "priority": "critical",
          "reason": "Enables review snippets in Google search",
          "google_rich_result": "Organization reviews",
          "example_value": {
            "@type": "AggregateRating",
            "ratingValue": "4.5",
            "reviewCount": "250"
          }
        }
      ],
      "seo_score": 65.0
    }
  ],
  "missing_entities": [
    {
      "entity_type": "FAQPage",
      "priority": "high",
      "reason": "FAQ pages enable FAQ Rich Results",
      "google_rich_result": "FAQ Rich Results"
    }
  ],
  "overall_seo_score": 68.5,
  "priority_summary": {
    "critical": 2,
    "high": 5,
    "medium": 8,
    "low": 3
  }
}
```

---

## 10. Success Criteria

### Functional
- [x] Analyzes existing JSON-LD graphs
- [x] Identifies missing properties per entity type
- [x] Suggests missing entity types
- [x] Validates @id references
- [x] Scores by SEO impact
- [x] Three output modes (analysis/enhanced/diff)

### Quality
- [ ] 90%+ test coverage
- [ ] All tests passing
- [ ] Zero complexity violations
- [ ] <500ms execution for typical graphs

### Documentation
- [ ] Comprehensive docstrings
- [ ] Updated CLAUDE.md
- [ ] Example usage documented

---

## 11. Related Files

- **Existing schema tools**: `src/ast_grep_mcp/features/schema/tools.py`
- **Schema client**: `src/ast_grep_mcp/features/schema/client.py`
- **Patterns reference**: `PATTERNS.md`
- **Test patterns**: `tests/unit/test_schema_tools.py`

---

## 12. Session Context

This plan was created based on a real-world analysis session where we:

1. Ran `build_entity_graph` on Leora Home Health project
2. Discovered it only creates graphs, doesn't analyze existing ones
3. Manually analyzed `schema-org-markup.json` (27 entities)
4. Created `schema-org-markup-v2.json` (39 entities) with:
   - 3 Reviews + aggregateRating on Organization
   - contactPoint with hours/languages
   - offers on all 5 Services
   - image/description on all 8 Persons
   - wordCount/timeRequired on all 8 BlogPostings
   - totalTime/prepTime/performTime on 3 HowTo guides
   - 10 BreadcrumbList entities
   - Expanded FAQPage (4 → 8 questions)
   - WebSite with SearchAction

The `enhance_entity_graph` tool will automate this entire workflow.
