# Known Issues

## changelog_generator.py

### `from_version` / `to_version` resolution asymmetry

**Severity:** Medium
**File:** `src/ast_grep_mcp/features/documentation/changelog_generator.py`
**Lines:** 136-138

`_resolve_version_ref` (v-prefix tag, bare ref, HEAD fallback) is only used for `to_version`. The `from_version` path only tries the v-prefix tag and falls back to the raw string — no bare-ref validation, no HEAD fallback. An invalid `from_version` is silently passed to `git log`, which fails downstream.

**Fix:** Replace lines 136-138 with `from_ref = _resolve_version_ref(project_folder, from_version)`. Accepts a behavior delta: invalid `from_version` falls back to HEAD instead of passing the raw string.

### Missing unit tests for extracted helpers

**Severity:** Medium
**Functions:** `_resolve_version_ref`, `_get_first_commit`, `_find_previous_tag`

These helpers were extracted in commit 8291624 but have no dedicated unit tests. They are independently testable by mocking `_run_git_command`.

### No `cwd` validation in `_run_git_command`

**Severity:** Low
**Lines:** 42-54

`project_folder` is passed as `cwd` to `subprocess.run` without validating the directory exists. A non-existent path raises `FileNotFoundError` which is not caught — the existing `FileNotFoundError` handler only covers the git binary not being found, not an invalid working directory.

### Empty string sentinel for missing refs

**Severity:** Low
**Function:** `_get_first_commit`

Returns `""` on failure, which propagates as `from_ref`. Works because `_get_commits` handles empty `from_ref` (line 166-169), but the implicit contract is fragile. A `str | None` return type with explicit `None` checks would be safer.
