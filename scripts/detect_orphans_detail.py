#!/usr/bin/env python3
"""Run detect_orphans against a target directory and print a detailed console report."""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TARGET = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "code" / "jobs")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/orphans_detail.json")

from ast_grep_mcp.features.quality.tools import detect_orphans_tool  # noqa: E402

print(f"Running detect_orphans against {TARGET} ...")
r = detect_orphans_tool(project_folder=TARGET)

with open(OUT, "w") as f:
    json.dump(r, f, indent=2, default=str)

files = r.get("orphan_files", [])
funcs = r.get("orphan_functions", [])
summary = r.get("summary", {})

W = 90
THIN = "-" * W
THICK = "=" * W

# -- Status symbols --
STATUS_ICON = {"confirmed": "X", "likely": "!", "uncertain": "?"}

# =====================================================================
# Summary dashboard
# =====================================================================
total_files = summary.get("total_files_analyzed", 0)
total_funcs = summary.get("total_functions_analyzed", 0)
orphan_file_ct = summary.get("orphan_files", 0)
orphan_func_ct = summary.get("orphan_functions", 0)
orphan_lines = summary.get("total_orphan_lines", 0)
elapsed_ms = summary.get("analysis_time_ms", 0)

file_pct = (orphan_file_ct / total_files * 100) if total_files else 0
func_pct = (orphan_func_ct / total_funcs * 100) if total_funcs else 0

print(f"\n{THICK}")
print("  ORPHAN ANALYSIS REPORT")
print(THICK)
print(f"  Target:          {TARGET}")
print(f"  Analysis time:   {elapsed_ms / 1000:.1f}s")
print(THIN)
print(f"  {'Metric':<30} {'Total':>8} {'Orphan':>8} {'%':>7}")
print(f"  {THIN[2:]}")
print(f"  {'Files':<30} {total_files:>8} {orphan_file_ct:>8} {file_pct:>6.1f}%")
print(f"  {'Functions':<30} {total_funcs:>8} {orphan_func_ct:>8} {func_pct:>6.1f}%")
print(f"  {'Orphan lines (total)':<30} {'':>8} {orphan_lines:>8}")
print(THICK)

# =====================================================================
# Orphan files — grouped by directory
# =====================================================================
by_dir: dict[str, list] = defaultdict(list)
for of in files:
    fp = of.get("file_path", "")
    parent = str(Path(fp).parent)
    by_dir[parent].append(of)

print(f"\n  ORPHAN FILES ({orphan_file_ct})")
print(f"  {THIN[2:]}")
print(f"  {'Status':<4} {'Lines':>6}  {'File':<40} {'Reason'}")
print(f"  {THIN[2:]}")

for d in sorted(by_dir):
    items = sorted(by_dir[d], key=lambda x: x.get("file_path", ""))
    dir_lines = sum(x.get("lines", 0) for x in items)
    print(f"\n  {d}/ — {len(items)} file{'s' if len(items) != 1 else ''}, {dir_lines:,} lines")
    for of in items:
        name = Path(of.get("file_path", "")).name
        lines = of.get("lines", 0)
        status = of.get("status", "")
        reason = of.get("reason", "")
        icon = STATUS_ICON.get(status, " ")
        importers = of.get("importers", [])
        print(f"    [{icon}] {lines:>5}  {name:<40} {reason}")
        if importers:
            for imp in importers[:3]:
                print(f"              -> {Path(imp).name}")
            if len(importers) > 3:
                print(f"              ... +{len(importers) - 3} more")

# =====================================================================
# Orphan functions — grouped by file, sorted by line
# =====================================================================
by_file: dict[str, list] = defaultdict(list)
for fn in funcs:
    fp = fn.get("file_path", "")
    by_file[fp].append(fn)

# Pre-compute per-file stats for the directory rollup
dir_func_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "lines": 0, "files": set()})
for fp, items in by_file.items():
    d = str(Path(fp).parent)
    dir_func_stats[d]["count"] += len(items)
    dir_func_stats[d]["lines"] += sum(x.get("lines", 0) for x in items)
    dir_func_stats[d]["files"].add(fp)

print(f"\n{THICK}")
print(f"  ORPHAN FUNCTIONS ({orphan_func_ct})")
print(f"  {THIN[2:]}")
print(f"  {'Status':<4} {'Lines':>5}  {'L#':>5}  {'Name':<40} {'Visibility'}")
print(f"  {THIN[2:]}")

# Group files by directory for section headers
file_by_dir: dict[str, list] = defaultdict(list)
for fp in sorted(by_file):
    d = str(Path(fp).parent)
    file_by_dir[d].append(fp)

for d in sorted(file_by_dir):
    stats = dir_func_stats[d]
    print(f"\n  {d}/ — {stats['count']} orphan func{'s' if stats['count'] != 1 else ''}, {stats['lines']:,} lines")

    for fp in sorted(file_by_dir[d]):
        items = sorted(by_file[fp], key=lambda x: x.get("line_start", 0))
        file_lines = sum(x.get("lines", 0) for x in items)
        print(f"    {Path(fp).name} ({len(items)} funcs, {file_lines} lines)")

        for fn in items:
            name = fn.get("name", "?")
            line_start = fn.get("line_start", 0)
            fn_lines = fn.get("lines", 0)
            status = fn.get("status", "")
            is_private = fn.get("is_private", False)
            icon = STATUS_ICON.get(status, " ")
            vis = "private" if is_private else "public"
            print(f"      [{icon}] {fn_lines:>5}  {line_start:>5}  {name:<40} {vis}")

# =====================================================================
# Severity breakdown
# =====================================================================
status_counts: dict[str, int] = defaultdict(int)
private_count = 0
public_count = 0
for fn in funcs:
    status_counts[fn.get("status", "unknown")] += 1
    if fn.get("is_private", False):
        private_count += 1
    else:
        public_count += 1

file_status_counts: dict[str, int] = defaultdict(int)
for of in files:
    file_status_counts[of.get("status", "unknown")] += 1

print(f"\n{THICK}")
print("  BREAKDOWN")
print(f"  {THIN[2:]}")
print("  File status:     ", end="")
print("  ".join(f"[{STATUS_ICON.get(s, ' ')}] {s}: {c}" for s, c in sorted(file_status_counts.items())))
print("  Function status: ", end="")
print("  ".join(f"[{STATUS_ICON.get(s, ' ')}] {s}: {c}" for s, c in sorted(status_counts.items())))
print(f"  Visibility:       public: {public_count}  private: {private_count}")

# Top files by orphan function count
top_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)[:10]
print("\n  Top files by orphan function count:")
for fp, items in top_files:
    total_lines = sum(x.get("lines", 0) for x in items)
    print(f"    {len(items):>3} funcs  {total_lines:>5} lines  {fp}")

print(f"\n{THICK}")
print("  Legend: [X] confirmed  [!] likely  [?] uncertain")
print(f"  Full JSON: {OUT}")
print(THICK)
