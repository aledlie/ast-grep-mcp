# Development Task Management

This directory contains active development tasks and strategic planning documents for the ast-grep MCP server project.

## Directory Structure

```
dev/
├── README.md                    # This file
└── active/                      # Active task directories
    └── [task-name]/            # Individual task workspace
        ├── [task-name]-plan.md      # Comprehensive strategic plan
        ├── [task-name]-context.md   # Context and technical details
        └── [task-name]-tasks.md     # Detailed task checklist
```

## Active Tasks

### ast-grep-mcp-strategic-plan
**Created:** 2025-11-08
**Status:** Planning Complete
**Timeline:** 16 weeks (4 months)
**Effort:** 250-300 developer hours

Strategic plan for evolving the ast-grep MCP server from experimental MVP to production-ready tool.

**Files:**
- `ast-grep-mcp-strategic-plan.md` - Full strategic plan with phases, risks, metrics
- `ast-grep-mcp-context.md` - Technical context, architecture, dependencies
- `ast-grep-mcp-tasks.md` - Detailed task breakdown with checklists

**Key Phases:**
1. Foundation & Quality (Weeks 1-3)
2. Performance & Scalability (Weeks 4-6)
3. Feature Expansion (Weeks 7-10)
4. Developer Experience (Weeks 11-13)
5. Production Readiness (Weeks 14-16)

## Task Management Guidelines

### Creating a New Task
1. Create directory: `dev/active/[task-name]/`
2. Generate three files:
   - `[task-name]-plan.md` - Strategic plan and overview
   - `[task-name]-context.md` - Technical context and decisions
   - `[task-name]-tasks.md` - Actionable checklist
3. Include "Last Updated: YYYY-MM-DD" in each file
4. Update this README with task entry

### Working on a Task
1. Review plan, context, and task files
2. Check off completed subtasks in tasks.md
3. Update "Last Updated" date when making changes
4. Document blockers, issues, and decisions
5. Link to related PRs/commits

### Completing a Task
1. Verify all subtasks completed
2. Update task status in this README
3. Move completed tasks to archive (optional)
4. Document outcomes and lessons learned

### Task File Templates

#### Plan File Structure
- Executive Summary
- Current State Analysis
- Proposed Future State
- Implementation Phases
- Risk Assessment
- Success Metrics
- Required Resources
- Timeline Estimates

#### Context File Structure
- Project Overview
- Architecture Overview
- Key Files and Directories
- Critical Dependencies
- Configuration System
- Data Flow
- Testing Strategy
- Known Issues
- Common Patterns

#### Tasks File Structure
- Tasks grouped by phase/section
- Each task with:
  - Checkbox subtasks
  - Acceptance criteria
  - Effort estimate
  - Dependencies
  - Notes/blockers

## Best Practices

### Documentation
- Keep plans focused on strategy and big picture
- Keep context focused on technical details
- Keep tasks focused on actionable items
- Update "Last Updated" date when making changes
- Link between files when referencing related content

### Task Breakdown
- Tasks should be completable in 1-2 weeks max
- Subtasks should be completable in 1 day or less
- Include clear acceptance criteria
- Note dependencies explicitly
- Estimate effort realistically (S/M/L/XL)

### Progress Tracking
- Update task checklists as work progresses
- Don't batch updates - update incrementally
- Document blockers as soon as they're encountered
- Review progress weekly against timeline
- Adjust estimates based on actual progress

### Context Preservation
- These files survive context resets and conversation boundaries
- Include enough context for future developers to understand
- Document decisions and rationale, not just what
- Link to code locations (file:line format)
- Keep technical debt and TODOs visible

## Task Status Legend

- **Planning** - Task defined, plan in progress
- **Ready** - Plan complete, ready to start implementation
- **In Progress** - Active implementation work
- **Blocked** - Waiting on dependencies or decisions
- **Review** - Implementation complete, in review
- **Complete** - All acceptance criteria met, merged

## Archive

Completed tasks can be moved to `dev/archive/[task-name]/` to keep the active directory clean while preserving history.

---

*This task management system is designed to work with Claude Code and survive context resets. Keep plans, context, and tasks synchronized as work progresses.*
