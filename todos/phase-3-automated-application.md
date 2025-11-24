# Phase 3: Automated Application Tool TODOs

**Status: COMPLETED**
**Completed Date: 2025-11-23**

## 3.1 Tool Skeleton
- [x] Create `apply_deduplication` function signature
- [x] Add to MCP tool registry
- [x] Define input/output schema
- [x] Add logging instrumentation
- [x] Add Sentry error tracking
- [x] Basic integration test

## 3.2 Backup Integration
- [x] Identify backup directory location
- [x] Create backup metadata structure
- [x] Copy files before modification
- [x] Return backup_id to caller
- [x] Integration test with rollback

## 3.3 Multi-File Orchestration
- [x] Plan file modification order
- [x] Handle extracted function file creation
- [x] Update all duplicate location files
- [x] Ensure atomicity (all or nothing)
- [x] Handle failure scenarios (partial rollback)
- [x] Integration tests for multi-file changes

## 3.4 Diff Preview Generator
- [x] Generate unified diff for each file
- [x] Format diffs for readability
- [x] Include context lines
- [x] Return structured diff data
- [x] Unit tests for diff generation

## 3.5 Syntax Validation Pipeline
- [x] Validate before applying changes
- [x] Validate after applying changes
- [x] Rollback on validation failure
- [x] Detailed error reporting
- [x] Integration tests for validation

## 3.6 Rollback Mechanism
- [x] Leverage existing `rollback_rewrite` tool
- [x] Ensure backup format compatibility
- [x] Add deduplication-specific metadata
- [x] Integration test rollback flow

## Summary

- **27/27 tasks completed**
- **90 tests written** (39 diff preview, 24 unit, 15 validation, 12 rollback)
- New helper functions: `_plan_file_modification_order`, `_generate_import_for_extracted_function`, `_add_import_to_content`
- Backup functions: `create_deduplication_backup`, `get_file_hash`, `verify_backup_integrity`
- All tests passing
