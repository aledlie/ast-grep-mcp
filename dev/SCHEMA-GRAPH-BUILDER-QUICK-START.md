# Schema Graph Builder - Quick Start Guide

**One-command automation for Schema.org entity graph building**

---

## TL;DR

```bash
# Build entity graph for any project
python3 schema-graph-builder.py <directory> <base_url>

# Example: PersonalSite
python3 schema-graph-builder.py ~/code/PersonalSite/schemas-static https://www.aledlie.com

# Example: Fisterra
python3 schema-graph-builder.py ~/code/IntegrityStudioClients/fisterra/test-samples https://fisterra-dance.com
```

---

## What You Get

**4 Files Generated** (in `schema-analysis/` directory):

1. **`unified-entity-graph.json`** - Complete knowledge graph ready for deployment
2. **`entity-graph-analysis.json`** - Relationship statistics and analysis
3. **`entity-id-validation.json`** - @id validation results
4. **`ENTITY-GRAPH-SUMMARY.md`** - Comprehensive documentation

---

## What It Does

1. ✅ **Discovers** all Schema.org JSON files
2. ✅ **Extracts** entities with @type and @id
3. ✅ **Validates** @id values (HTTPS, hash fragments, stability)
4. ✅ **Builds** unified @graph structure
5. ✅ **Analyzes** relationships between entities
6. ✅ **Generates** documentation

---

## Common Commands

### Basic Usage
```bash
python3 schema-graph-builder.py <directory> <base_url>
```

### Custom Output Directory
```bash
python3 schema-graph-builder.py <directory> <base_url> --output-dir <path>
```

### Custom Project Name
```bash
python3 schema-graph-builder.py <directory> <base_url> --name "My Project"
```

### Exclude Additional Files
```bash
python3 schema-graph-builder.py <directory> <base_url> --exclude test.json sample.json
```

### JSON Output (for automation)
```bash
python3 schema-graph-builder.py <directory> <base_url> --json
```

---

## Real-World Examples

### PersonalSite (Jekyll)
```bash
python3 schema-graph-builder.py \
  ~/code/PersonalSite/schemas-static \
  https://www.aledlie.com
```

**Results**:
- 16 entities, 13 types, 33 relationships
- Person (hub), WebSite (hub), Blog, Organizations (2)
- 100% @id validation pass

### Fisterra Dance (Wix)
```bash
python3 schema-graph-builder.py \
  ~/code/IntegrityStudioClients/fisterra/test-samples \
  https://fisterra-dance.com \
  --name "Fisterra Dance"
```

**Results**:
- 22 entities, 17 types, 26 relationships
- Organization, Events, Courses, People (3)
- 100% @id validation pass

---

## Output Example

```
================================================================================
Schema.org Entity Graph Builder
================================================================================
Directory: ~/code/PersonalSite/schemas-static
Base URL: https://www.aledlie.com
Output: ~/code/PersonalSite/schemas-static/schema-analysis

Found 5 Schema.org JSON files:
  - blog-schema.json
  - person-schema.json
  - website-schema.json
  - integrity-studios-schema.json
  - inventoryai-schema.json

================================================================================
Building Entity Graph for Www
================================================================================
Base URL: https://www.aledlie.com
Source files: 5

Processing blog-schema.json...
  Extracted 3 entities
...

Merging duplicate entities...
  16 entities → 16 unique entities

================================================================================
Analyzing Relationships
================================================================================

Total entities: 16

Entities by type:
  Person: 1
  WebSite: 1
  Blog: 1
  Organization: 2
  ...

Total relationships: 33

Relationships by property:
  author: 4
  publisher: 4
  worksFor: 2
  ...

================================================================================
Validating @id Values
================================================================================

✅ 16/16 @id values passed validation

================================================================================
Saving Outputs
================================================================================

✅ Unified entity graph: .../unified-entity-graph.json
✅ Graph analysis: .../entity-graph-analysis.json
✅ Validation results: .../entity-id-validation.json
✅ Documentation: .../ENTITY-GRAPH-SUMMARY.md

================================================================================
Build Complete
================================================================================

📊 Summary:
  - 16 unique entities
  - 13 Schema.org types
  - 33 relationships
  - 16/16 @id values valid

📁 Output directory: .../schema-analysis
```

---

## Next Steps After Building

### 1. Review the Output

```bash
# View the unified graph
cat schema-analysis/unified-entity-graph.json

# View documentation
cat schema-analysis/ENTITY-GRAPH-SUMMARY.md

# Check validation results
cat schema-analysis/entity-id-validation.json | jq
```

### 2. Validate with External Tools

**JSON-LD Validation**:
```bash
python3 -m json.tool schema-analysis/unified-entity-graph.json > /dev/null
```

**Google Rich Results Test**:
- Deploy schema to public URL
- Test at: https://search.google.com/test/rich-results

**Schema.org Validator**:
- Visit: https://validator.schema.org/
- Paste your JSON-LD

### 3. Deploy to Production

**Option A: Static JSON**
```html
<script type="application/ld+json" src="/unified-entity-graph.json"></script>
```

**Option B: Convert to Template**
Use the JSON structure as a template for your platform (Liquid, Jinja2, etc.)

---

## Troubleshooting

### No files found
- Check directory path
- Ensure files have `.json` extension
- Verify files contain `@context` or `@type`

### @id validation warnings
- Add hash fragment: `#entity_type`
- Use HTTPS protocol
- Remove query parameters
- Remove timestamps

### Missing relationships
- Convert inline objects to @id references
- Ensure @id values match exactly (case-sensitive)

---

## Full Documentation

See **SCHEMA-GRAPH-BUILDER-README.md** for:
- Complete feature documentation
- Advanced usage patterns
- Architecture details
- Integration examples
- SEO benefits
- Best practices

---

**Quick Reference**: ~/code/ast-grep-mcp/schema-graph-builder.py
**Full Docs**: ~/code/ast-grep-mcp/SCHEMA-GRAPH-BUILDER-README.md
**Created**: 2025-11-16
