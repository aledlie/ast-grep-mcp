# Phase 3: Automated Application Tool TODOs

## 3.1 Tool Skeleton
- [ ] Create `apply_deduplication` function signature
- [ ] Add to MCP tool registry
- [ ] Define input/output schema
- [ ] Add logging instrumentation
- [ ] Add Sentry error tracking
- [ ] Basic integration test

## 3.2 Backup Integration
- [ ] Identify backup directory location
- [ ] Create backup metadata structure
- [ ] Copy files before modification
- [ ] Return backup_id to caller
- [ ] Integration test with rollback

## 3.3 Multi-File Orchestration
- [ ] Plan file modification order
- [ ] Handle extracted function file creation
- [ ] Update all duplicate location files
- [ ] Ensure atomicity (all or nothing)
- [ ] Handle failure scenarios (partial rollback)
- [ ] Integration tests for multi-file changes

## 3.4 Diff Preview Generator
- [ ] Generate unified diff for each file
- [ ] Format diffs for readability
- [ ] Include context lines
- [ ] Return structured diff data
- [ ] Unit tests for diff generation

## 3.5 Syntax Validation Pipeline
- [ ] Validate before applying changes
- [ ] Validate after applying changes
- [ ] Rollback on validation failure
- [ ] Detailed error reporting
- [ ] Integration tests for validation

## 3.6 Rollback Mechanism
- [ ] Leverage existing `rollback_rewrite` tool
- [ ] Ensure backup format compatibility
- [ ] Add deduplication-specific metadata
- [ ] Integration test rollback flow
