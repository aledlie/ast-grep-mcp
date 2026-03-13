#!/usr/bin/env python3
"""Run detect_orphans against a target directory and print full orphan file details."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TARGET = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "code" / "jobs")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/orphans_detail.json")

from ast_grep_mcp.features.quality.tools import detect_orphans_tool

print(f"Running detect_orphans against {TARGET} ...")
r = detect_orphans_tool(project_folder=TARGET)

with open(OUT, "w") as f:
    json.dump(r, f, indent=2, default=str)

files = r.get("orphan_files", [])
funcs = r.get("orphan_functions", [])
summary = r.get("summary", {})

print(f"\nSummary: {summary}")
print(f"\n{'='*80}")
print(f"ORPHAN FILES ({len(files)})")
print(f"{'='*80}")

# Group by directory
from collections import defaultdict

by_dir: dict[str, list] = defaultdict(list)
for of in files:
    fp = of.get("file_path", "")
    parent = str(Path(fp).parent)
    by_dir[parent].append(of)

for d in sorted(by_dir):
    items = sorted(by_dir[d], key=lambda x: x.get("file_path", ""))
    total_lines = sum(x.get("lines", 0) for x in items)
    print(f"\n  {d}/ ({len(items)} files, {total_lines} lines)")
    for of in items:
        fp = Path(of.get("file_path", "")).name
        lines = of.get("lines", 0)
        status = of.get("status", "")
        print(f"    {lines:>5} lines  {status:<12}  {fp}")

print(f"\n{'='*80}")
print(f"ORPHAN FUNCTIONS ({len(funcs)})")
print(f"{'='*80}")

by_file: dict[str, list] = defaultdict(list)
for fn in funcs:
    fp = fn.get("file", "")
    by_file[fp].append(fn)

for fp in sorted(by_file):
    items = sorted(by_file[fp], key=lambda x: x.get("line", 0))
    print(f"\n  {fp} ({len(items)} orphan functions)")
    for fn in items:
        name = fn.get("name", "?")
        line = fn.get("line", 0)
        print(f"    L{line:<5}  {name}")

print(f"\nFull results: {OUT}")
