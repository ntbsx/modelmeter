# 32. Frontend Agent Identity

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display agent identity (OpenCode vs Claude Code) on source cards, live session panels, and health status in the web frontend.

**Architecture:** Minimal frontend changes since the API abstraction handles data merging. The main visual addition is agent badges on existing UI components. Uses the `agent` field from API responses.

**Tech Stack:** React, TypeScript, Tailwind v4

**Dependencies:** Plans 27-31

---

### Task 1: Regenerate OpenAPI types

**Files:**
- Modify: `web/openapi.json`
- Modify: `web/src/generated/api.ts`
- Modify: `web/src/generated/openapi.sha256`

- [ ] **Step 1: Regenerate types from backend**

Run: `make gen-types`

This captures all API changes from Plans 29-31 (agents_detected in health, agent field on sources, etc.)

- [ ] **Step 2: Verify types are correct**

Run: `npm run --prefix web check:types`

- [ ] **Step 3: Commit**

```bash
git add web/openapi.json web/src/generated/
git commit -m "chore: regenerate OpenAPI types for agent identity fields"
```

---

### Task 2: Create AgentBadge component

**Files:**
- Create: `web/src/components/AgentBadge.tsx`

- [ ] **Step 1: Create the component**

A small badge component that displays the agent name with distinct styling:

```tsx
interface AgentBadgeProps {
  agent: string | null | undefined;
  size?: "sm" | "md";
}

export function AgentBadge({ agent, size = "sm" }: AgentBadgeProps) {
  if (!agent) return null;

  const label = agent === "claudecode" ? "Claude Code" : agent === "opencode" ? "OpenCode" : agent;
  const colorClass =
    agent === "claudecode"
      ? "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300"
      : agent === "opencode"
        ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
        : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";

  const sizeClass = size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2 py-1";

  return (
    <span className={`inline-flex items-center rounded font-medium ${colorClass} ${sizeClass}`}>
      {label}
    </span>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/AgentBadge.tsx
git commit -m "feat: add AgentBadge component for agent identity display"
```

---

### Task 3: Add agent badge to Sources page cards

**Files:**
- Modify: `web/src/pages/Sources.tsx` (or wherever source cards are rendered)

- [ ] **Step 1: Import and use AgentBadge**

On each source card, display the `agent` field from the source config:

```tsx
import { AgentBadge } from "../components/AgentBadge";

// In source card JSX:
<AgentBadge agent={source.agent} />
```

- [ ] **Step 2: Run frontend tests**

Run: `npm run --prefix web test -- --run`

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Sources.tsx
git commit -m "feat: show agent badge on source cards"
```

---

### Task 4: Add agent identity to live session panels

**Files:**
- Modify: `web/src/pages/Live.tsx` (or the live session panel component)

- [ ] **Step 1: Display agent identity on session panels**

If the live session data includes agent information (from the session metadata), display an `AgentBadge` on each session panel header.

Note: The agent identity for live sessions comes from knowing which repository the session was queried from. This may need a small API extension to include `agent` in the `LiveActiveSession` response model.

- [ ] **Step 2: Check if LiveActiveSession needs agent field**

If not already added by Plan 31, add `agent: str | None = None` to `LiveActiveSession` in `src/modelmeter/core/models.py` and populate it in the live endpoint.

- [ ] **Step 3: Run frontend tests**

Run: `npm run --prefix web test -- --run`

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/Live.tsx web/src/components/
git commit -m "feat: show agent identity on live session panels"
```

---

### Task 5: Display detected agents in health/settings area

**Files:**
- Modify: `web/src/App.tsx` or `web/src/components/Header.tsx` (wherever health status is displayed)

- [ ] **Step 1: Show detected agents from /health endpoint**

The `/health` endpoint now returns `agents_detected: ["opencode", "claudecode"]`. Display this somewhere appropriate — perhaps in the header area or a status indicator.

- [ ] **Step 2: Run frontend build**

Run: `npm run --prefix web build`

- [ ] **Step 3: Commit**

```bash
git add web/src/
git commit -m "feat: display detected agents from health endpoint"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run all frontend tests**

Run: `npm run --prefix web test -- --run`

- [ ] **Step 2: Run frontend build**

Run: `npm run --prefix web build`

- [ ] **Step 3: Run full backend test suite**

Run: `uv run pytest tests/ -v`

- [ ] **Step 4: Run release check**

Run: `make release-check`

- [ ] **Step 5: Commit any remaining changes**

---

## Verification

```bash
npm run --prefix web test -- --run
npm run --prefix web build
uv run pytest tests/ -v
make release-check
```
