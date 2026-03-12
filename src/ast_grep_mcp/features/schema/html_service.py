"""HTML structured data detection using ast-grep YAML rules.

Detects JSON-LD script tags, microdata attributes, and RDFa properties
in HTML files via ast-grep pattern matching.
"""

import json
import re
from typing import Any, Dict, List, Optional

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.search.service import find_code_by_rule_impl

logger = get_logger("schema.html")

DEFAULT_HTML_GLOBS = ["**/*.html", "**/*.htm"]

# --- YAML Rules ---

RULE_JSONLD_SCRIPTS = """\
id: find-json-ld-scripts
language: html
rule:
  kind: element
  has:
    stopBy: { kind: tag_name }
    kind: tag_name
    pattern: script
  has:
    kind: attribute_value
    regex: application/ld\\+json
"""

RULE_JSONLD_CONTENT = """\
id: extract-json-ld-content
language: html
rule:
  kind: text
  pattern: $JSON_CONTENT
  inside:
    kind: element
    has:
      stopBy: { kind: tag_name }
      kind: tag_name
      pattern: script
    has:
      kind: attribute_value
      regex: application/ld\\+json
"""

RULE_MICRODATA_ATTRS = """\
id: find-microdata-attributes
language: html
rule:
  kind: attribute_name
  regex: ^(itemscope|itemtype|itemprop|itemid|itemref)$
"""

RULE_MICRODATA_ELEMENTS = """\
id: find-microdata-elements
language: html
rule:
  kind: element
  has:
    kind: attribute_name
    regex: ^itemscope$
  has:
    kind: attribute_value
    pattern: $SCHEMA_TYPE
constraints:
  SCHEMA_TYPE:
    regex: schema\\.org
"""

RULE_RDFA_PROPERTIES = """\
id: find-rdfa-properties
language: html
utils:
  in-element:
    inside:
      kind: element
      stopBy: { kind: element }
rule:
  kind: attribute_name
  regex: ^(property|typeof|resource|about|prefix|vocab)$
  matches: in-element
"""

RULE_MISSING_ITEMTYPE = """\
id: microdata-missing-itemprop
language: html
rule:
  kind: element
  has:
    kind: attribute_name
    regex: ^itemscope$
  not:
    has:
      kind: attribute_name
      regex: ^itemtype$
"""

# Regex to extract schema.org type from itemtype attribute value
_SCHEMA_TYPE_RE = re.compile(r"https?://schema\.org/(\w+)")


def _run_rule(project_folder: str, yaml_rule: str) -> List[Dict[str, Any]]:
    """Run an ast-grep YAML rule and return JSON matches."""
    result = find_code_by_rule_impl(project_folder, yaml_rule, output_format="json")
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        matches: List[Dict[str, Any]] = result.get("matches", [])
        return matches
    return []


def _parse_jsonld_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON-LD text, returning None on malformed content."""
    try:
        parsed: Dict[str, Any] = json.loads(text.strip())
        return parsed
    except (json.JSONDecodeError, ValueError):
        return None


def detect_jsonld_in_html(
    project_folder: str,
    file_globs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Find JSON-LD script tags in HTML files and extract their content.

    Args:
        project_folder: Project root path
        file_globs: File patterns to scan (default: **/*.html, **/*.htm)

    Returns:
        Dict with scripts list, parsed content, and error details
    """
    _ = file_globs  # reserved for future glob filtering
    content_matches = _run_rule(project_folder, RULE_JSONLD_CONTENT)

    scripts: List[Dict[str, Any]] = []
    parse_errors: List[Dict[str, Any]] = []

    for match in content_matches:
        file_path = match.get("file", "")
        line = match.get("line", 0)
        text = match.get("text", match.get("code", ""))

        parsed = _parse_jsonld_text(text)
        entry: Dict[str, Any] = {
            "file": file_path,
            "line": line,
            "raw_length": len(text),
        }
        if parsed is not None:
            entry["parsed"] = parsed
            entry["type"] = parsed.get("@type", "unknown")
            scripts.append(entry)
        else:
            entry["error"] = "malformed JSON-LD"
            parse_errors.append(entry)

    return {
        "format": "json-ld",
        "count": len(scripts),
        "scripts": scripts,
        "parse_errors": parse_errors,
    }


def detect_microdata_in_html(
    project_folder: str,
    file_globs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Find microdata attributes in HTML files, mapping to Schema.org types.

    Args:
        project_folder: Project root path
        file_globs: File patterns to scan

    Returns:
        Dict with attributes, typed elements, and validation issues
    """
    _ = file_globs
    attr_matches = _run_rule(project_folder, RULE_MICRODATA_ATTRS)
    element_matches = _run_rule(project_folder, RULE_MICRODATA_ELEMENTS)
    missing_type_matches = _run_rule(project_folder, RULE_MISSING_ITEMTYPE)

    # Extract schema types from element matches
    typed_elements: List[Dict[str, Any]] = []
    for match in element_matches:
        text = match.get("text", match.get("code", ""))
        type_match = _SCHEMA_TYPE_RE.search(text)
        schema_type = type_match.group(1) if type_match else "unknown"
        typed_elements.append({
            "file": match.get("file", ""),
            "line": match.get("line", 0),
            "schema_type": schema_type,
        })

    validation_issues = [
        {
            "file": m.get("file", ""),
            "line": m.get("line", 0),
            "issue": "itemscope without itemtype",
        }
        for m in missing_type_matches
    ]

    return {
        "format": "microdata",
        "attribute_count": len(attr_matches),
        "typed_elements": typed_elements,
        "validation_issues": validation_issues,
    }


def detect_rdfa_in_html(
    project_folder: str,
    file_globs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Find RDFa properties in HTML files.

    Args:
        project_folder: Project root path
        file_globs: File patterns to scan

    Returns:
        Dict with RDFa property matches grouped by attribute type
    """
    _ = file_globs
    matches = _run_rule(project_folder, RULE_RDFA_PROPERTIES)

    by_attribute: Dict[str, int] = {}
    properties: List[Dict[str, Any]] = []
    for match in matches:
        text = match.get("text", match.get("code", "")).strip()
        by_attribute[text] = by_attribute.get(text, 0) + 1
        properties.append({
            "file": match.get("file", ""),
            "line": match.get("line", 0),
            "attribute": text,
        })

    return {
        "format": "rdfa",
        "count": len(properties),
        "by_attribute": by_attribute,
        "properties": properties,
    }


def validate_html_structured_data(
    project_folder: str,
    file_globs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run all HTML structured data detections and produce a validation summary.

    Args:
        project_folder: Project root path
        file_globs: File patterns to scan

    Returns:
        Combined results with validation issues and summary counts
    """
    jsonld = detect_jsonld_in_html(project_folder, file_globs)
    microdata = detect_microdata_in_html(project_folder, file_globs)
    rdfa = detect_rdfa_in_html(project_folder, file_globs)

    all_issues: List[Dict[str, Any]] = []
    all_issues.extend(jsonld.get("parse_errors", []))
    all_issues.extend(microdata.get("validation_issues", []))

    return {
        "json_ld": jsonld,
        "microdata": microdata,
        "rdfa": rdfa,
        "summary": {
            "jsonld_scripts": jsonld["count"],
            "microdata_elements": len(microdata["typed_elements"]),
            "rdfa_properties": rdfa["count"],
            "total_issues": len(all_issues),
        },
        "issues": all_issues,
    }
