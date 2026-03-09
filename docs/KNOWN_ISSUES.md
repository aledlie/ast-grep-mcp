# Known Issues

## changelog_generator.py

### ~~`from_version` / `to_version` resolution asymmetry~~ (Resolved)

`_get_commit_range` now uses `_resolve_version_ref` for both `from_version` and `to_version`. Invalid `from_version` falls back to HEAD via `_resolve_version_ref` instead of passing the raw string.

### ~~Missing unit tests for extracted helpers~~ (Resolved)

Unit tests for `_resolve_version_ref`, `_get_first_commit`, `_find_previous_tag`, and `_get_commit_range` were added in `tests/unit/test_documentation.py::TestChangelogHelpers`.

### ~~No `cwd` validation in `_run_git_command`~~ (Resolved)

`_run_git_command` now validates `project_folder` with `os.path.isdir()` before passing as `cwd` to `subprocess.run`. Returns `(False, "Directory not found: ...")` for non-existent paths.

### ~~Empty string sentinel for missing refs~~ (Resolved)

`_get_first_commit` now returns `str | None` instead of `""`. `_find_previous_tag` also returns `str | None`. `_get_commit_range` uses `or ""` to coalesce `None` for downstream compatibility with `_get_commits`.
