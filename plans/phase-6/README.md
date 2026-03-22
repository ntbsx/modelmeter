# Phase 6: Multi-Agent Support (Claude Code Integration)

## Objective

Extend ModelMeter to read and display usage data from Claude Code alongside OpenCode, treating each as a peer "coding agent" source. Users see unified analytics across both agents while retaining the ability to identify which agent produced the data.

## Scope Summary

Phase 6 covers:
- Repository Protocol abstraction and factory pattern for pluggable data readers
- JSONL-based data reader for Claude Code session files (`~/.claude/projects/`)
- Auto-detection of both OpenCode (SQLite) and Claude Code (JSONL) local data
- Agent identity field on sources (`opencode`, `claudecode`)
- Full analytics parity: summary, daily, models, providers, projects, date insights, sessions
- Live monitoring of Claude Code sessions via file mtime polling
- Doctor/health check extension for multi-agent detection
- Frontend agent identity display on source and session cards

## Plan Set

1. [27-repository-protocol-and-factory.md](27-repository-protocol-and-factory.md) (pending)
2. [28-claudecode-jsonl-reader.md](28-claudecode-jsonl-reader.md) (pending)
3. [29-auto-detection-and-agent-identity.md](29-auto-detection-and-agent-identity.md) (pending)
4. [30-analytics-multi-repo-integration.md](30-analytics-multi-repo-integration.md) (pending)
5. [31-live-monitoring-claudecode.md](31-live-monitoring-claudecode.md) (pending)
6. [32-frontend-agent-identity.md](32-frontend-agent-identity.md) (pending)

## Execution Order

- `27` first — protocol extraction and factory; foundation for everything else
- `28` after `27` — JSONL reader implementing the protocol
- `29` after `28` — auto-detection, settings, doctor, agent field
- `30` after `29` — federation integration, analytics refactor to use protocol
- `31` after `30` — live monitoring for Claude Code sessions
- `32` after `31` — frontend changes to display agent identity

## Phase Exit Criteria

- [ ] UsageRepository Protocol defined; SQLiteUsageRepository satisfies it
- [ ] JsonlUsageRepository reads Claude Code JSONL data with full method coverage
- [ ] Auto-detection discovers both OpenCode and Claude Code data on startup
- [ ] Agent identity field on sources; API responses include agent metadata
- [ ] All analytics endpoints include Claude Code data when present
- [ ] Live monitoring shows active Claude Code sessions alongside OpenCode sessions
- [ ] Doctor reports multi-agent detection status
- [ ] Frontend displays agent identity on source cards and session cards
- [ ] All existing tests pass; new tests cover JSONL reader, auto-detection, and federation
- [ ] OpenAPI artifacts regenerated for any schema changes

## Validation Baseline

- `uv run pytest` (all tests)
- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
- `make gen-types` (if API schema changes)
- `npm run --prefix web check:types`
- `make release-check`
