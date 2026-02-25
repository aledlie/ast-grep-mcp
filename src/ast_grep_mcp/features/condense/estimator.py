"""Non-destructive estimation of condensation reduction ratios.

Runs extraction patterns in dry-run mode to estimate token/byte reduction
without modifying any files.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ...constants import CondenseDefaults, CondenseFileRouting
from ...core.logging import get_logger
from .strategies import STRATEGY_REDUCTION_RATIOS as _STRATEGY_REDUCTION

logger = get_logger("condense.estimator")

_MAX_REDUCTION_CANDIDATES = 10


def estimate_condensation_impl(
    path: str,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimate reduction ratios for a path without modifying files.

    Args:
        path: Directory or file path to analyze.
        language: Optional language filter (e.g. "python", "typescript").

    Returns:
        Dict with total_files, total_lines, total_bytes, estimated_condensed_bytes
        per strategy, estimated_tokens per strategy, and top_reduction_candidates.
    """
    root = Path(path)
    if not root.exists():
        return {"error": f"Path does not exist: {path}", "total_files": 0}

    files = _collect_files(root, language)

    total_bytes = 0
    total_lines = 0
    file_stats: List[Dict[str, Any]] = []

    for fp in files:
        try:
            raw = fp.read_bytes()
        except OSError:
            continue
        size = len(raw)
        if size > CondenseDefaults.MAX_FILE_SIZE_BYTES:
            continue
        lines = raw.count(b"\n") + 1
        total_bytes += size
        total_lines += lines
        file_stats.append({"file": str(fp), "lines": lines, "bytes": size})

    estimated_condensed_bytes: Dict[str, int] = {}
    estimated_tokens: Dict[str, int] = {}
    for strategy, ratio in _STRATEGY_REDUCTION.items():
        condensed = int(total_bytes * (1.0 - ratio))
        estimated_condensed_bytes[strategy] = condensed
        estimated_tokens[strategy] = int(condensed * CondenseDefaults.AVG_TOKENS_PER_BYTE)

    top_candidates = _rank_reduction_candidates(file_stats)

    logger.info(
        "estimate_complete",
        total_files=len(file_stats),
        total_bytes=total_bytes,
        path=path,
    )

    return {
        "total_files": len(file_stats),
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "estimated_condensed_bytes": estimated_condensed_bytes,
        "estimated_tokens": estimated_tokens,
        "top_reduction_candidates": top_candidates,
    }


def _collect_files(root: Path, language: Optional[str]) -> List[Path]:
    """Collect code files under root, filtered by language if given."""
    ext_filter: Optional[frozenset[str]] = None
    if language:
        ext_filter = _language_to_extensions(language)

    files: List[Path] = []
    exclude: set[str] = set(CondenseFileRouting.EXCLUDE_PATTERNS)

    for fp in root.rglob("*"):
        if not fp.is_file():
            continue
        rel = fp.relative_to(root)
        if _is_excluded(rel, exclude):
            continue
        suffix = fp.suffix.lower()
        if suffix in CondenseFileRouting.IMAGE_EXTENSIONS:
            continue
        if ext_filter is not None and suffix not in ext_filter:
            continue
        if ext_filter is None and suffix not in CondenseFileRouting.CODE_EXTENSIONS:
            continue
        files.append(fp)
        if len(files) >= CondenseDefaults.MAX_FILES_PER_RUN:
            logger.warning("max_files_reached", limit=CondenseDefaults.MAX_FILES_PER_RUN, path=str(root))
            break

    return files


def _is_excluded(rel: Path, exclude_patterns: set[str]) -> bool:
    """Check if a relative path matches any exclusion pattern or skip directory."""
    skip_dirs = {"dist", "build", "node_modules", "__pycache__", ".git", ".venv", "venv"}
    parts = rel.parts
    if any(p in skip_dirs for p in parts):
        return True
    return any(rel.match(pattern) for pattern in exclude_patterns)


def _language_to_extensions(language: str) -> frozenset:
    """Map a language name to its file extensions."""
    mapping: Dict[str, frozenset[str]] = {
        "python": frozenset({".py"}),
        "typescript": frozenset({".ts", ".tsx"}),
        "javascript": frozenset({".js", ".jsx"}),
        "rust": frozenset({".rs"}),
        "go": frozenset({".go"}),
        "java": frozenset({".java"}),
        "ruby": frozenset({".rb"}),
        "php": frozenset({".php"}),
        "swift": frozenset({".swift"}),
        "kotlin": frozenset({".kt"}),
        "csharp": frozenset({".cs"}),
        "cpp": frozenset({".cpp", ".cc", ".cxx", ".h", ".hpp"}),
        "c": frozenset({".c", ".h"}),
    }
    return mapping.get(language.lower(), CondenseFileRouting.CODE_EXTENSIONS)


def _rank_reduction_candidates(
    file_stats: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return top files by line count as reduction candidates."""
    if not file_stats:
        return []
    total_lines = sum(s["lines"] for s in file_stats) or 1
    sorted_files = sorted(file_stats, key=lambda s: s["lines"], reverse=True)
    top = sorted_files[:_MAX_REDUCTION_CANDIDATES]
    return [
        {
            "file": s["file"],
            "lines": s["lines"],
            "reducible_pct": round(s["lines"] / total_lines * 100, 1),
        }
        for s in top
    ]
