# Known Issues

## changelog_generator.py

### `from_version` / `to_version` resolution asymmetry

**Severity:** Medium
**File:** `src/ast_grep_mcp/features/documentation/changelog_generator.py`
**Function:** `_get_commit_range`

`_resolve_version_ref` (v-prefix tag, bare ref, HEAD fallback) is only used for `to_version`. The `from_version` path only tries the v-prefix tag and falls back to the raw string — no bare-ref validation, no HEAD fallback. An invalid `from_version` is silently passed to `git log`, which fails downstream.

**Fix:** Replace the `from_version` branch in `_get_commit_range` with `from_ref = _resolve_version_ref(project_folder, from_version)`. Accepts a behavior delta: invalid `from_version` falls back to HEAD instead of passing the raw string.

### ~~Missing unit tests for extracted helpers~~ (Resolved)

Unit tests for `_resolve_version_ref`, `_get_first_commit`, `_find_previous_tag`, and `_get_commit_range` were added in `tests/unit/test_documentation.py::TestChangelogHelpers`.

### ~~No `cwd` validation in `_run_git_command`~~ (Resolved)

`_run_git_command` now validates `project_folder` with `os.path.isdir()` before passing as `cwd` to `subprocess.run`. Returns `(False, "Directory not found: ...")` for non-existent paths.

### ~~Empty string sentinel for missing refs~~ (Resolved)

`_get_first_commit` now returns `str | None` instead of `""`. `_find_previous_tag` also returns `str | None`. `_get_commit_range` uses `or ""` to coalesce `None` for downstream compatibility with `_get_commits`.
