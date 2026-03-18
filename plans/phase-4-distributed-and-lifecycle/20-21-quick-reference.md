# Plans 20 & 21: Quick Reference

Created: 2026-03-18

## Overview

Two new plans created during investigation of source switching UX:

### Plan 20: Source Status Banner and Loading States
**File:** `phase-4-distributed-and-lifecycle/20-source-status-banner-and-loading-states.md`  
**Priority:** High  
**Effort:** ~4-5 hours  

**Problem:** No visual feedback when switching between data sources (local/remote). Users see empty screens without knowing if data is loading, if source is down, or if there's just no data.

**Solution:**
- Create `SourceStatusBanner` component with 5 variants (loading, warning, error, info, success)
- Create `useSourceLabels` hook to map source IDs to friendly names
- Integrate banner into 7 pages (Overview, Providers, Models, Projects, ProjectDetail, ModelDetail, Live)
- Add source scope indicator in page headers
- Dim old data during refetch with pulse animation
- Inline health check without leaving page

**Key Features:**
- Show loading state immediately on source switch
- Display partial failures ("2 of 3 sources failed")
- Show first failure inline, rest expandable
- Inline health check button
- ModelDetail page gets source scope support (frontend only, backend returns 501)

**Files:**
- New: `SourceStatusBanner.tsx` (~200 lines), `useSourceLabels.ts` (~60 lines)
- Modified: 7 page files (~15-25 lines each)

---

### Plan 21: Provider Detection from providerID Field
**File:** `phase-4-distributed-and-lifecycle/21-provider-detection-from-providerid-field.md`  
**Priority:** High  
**Effort:** ~4 hours  

**Problem:** ModelMeter ignores the `providerID` field in OpenCode message JSON, causing massive misattribution:
- **~700 messages** from GitHub Copilot → wrongly attributed to OpenAI/Anthropic
- **~2,569 messages** from OpenCode proxy → marked as "unknown"

**Root Cause:** Code only reads `modelID` and does pattern matching (`gpt-*` → openai, `claude-*` → anthropic). Never reads the `providerID` field that contains correct information.

**Solution:**
1. Extract `provider_id` from JSON in 8 repository methods
2. Create `provider_from_model_id_and_provider_field()` function
3. Prioritize `providerID` field over pattern matching
4. Update 5 analytics functions to use new detection
5. Add comprehensive tests

**Impact After Fix:**
```
Before:
- openai: 5 models, ~2,900 sessions (includes Copilot)
- unknown: 5 models, 2,569 sessions (all OpenCode)

After:
- openai: 3 models, 2,200 sessions (Copilot separated)
- github-copilot: 6 models, ~700 sessions (NEW!)
- opencode: 5 models, 2,569 sessions (NEW!)
```

**Files:**
- Modified: `sqlite_usage_repository.py` (~50 lines), `providers.py` (+25 lines), `analytics.py` (~30 lines), `live.py` (~10 lines)
- New: `test_providers.py` (~150 lines)

---

## Which to Tackle First?

**Recommendation:** Plan 21 (Provider Detection)

**Why:**
1. **Data accuracy issue** - 20% of messages misattributed
2. **Cleaner implementation** - Backend only, no UI complexity
3. **Faster** - 4 hours vs 5 hours
4. **No dependencies** - Standalone fix
5. **Immediate value** - Users see correct provider attribution right away

Plan 20 is pure UX improvement, Plan 21 fixes data correctness.

---

## Quick Start Commands

### For Plan 20 (Source Status Banner):
```bash
# Read the full plan
cat plans/phase-4-distributed-and-lifecycle/20-source-status-banner-and-loading-states.md

# Start with Phase 1: Create component
# File: web/src/components/SourceStatusBanner.tsx

# Then Phase 2: Create hook
# File: web/src/hooks/useSourceLabels.ts

# Test in browser
make dev
```

### For Plan 21 (Provider Detection):
```bash
# Read the full plan
cat plans/phase-4-distributed-and-lifecycle/21-provider-detection-from-providerid-field.md

# Start with Phase 1: Update repository
# File: src/modelmeter/data/sqlite_usage_repository.py
# Add provider_id extraction in 8 methods

# Verify current state
uv run python -c "
import sqlite3
from pathlib import Path
db = sqlite3.connect(Path.home() / '.local/share/opencode/opencode.db')
cursor = db.execute('''
    SELECT json_extract(data, '$.providerID') as provider, COUNT(*) 
    FROM message 
    WHERE json_extract(data, '$.providerID') IN ('github-copilot', 'opencode')
    GROUP BY provider
''')
for row in cursor: print(row)
"

# Expected: Shows ~700 github-copilot, ~2,569 opencode messages
```

---

## Testing Notes

### Plan 20 Testing:
- Switch between "This Server" ↔ "All Sources" ↔ specific remote
- Simulate remote source down (stop remote server)
- Check all 7 pages show banner correctly
- Verify health check works inline

### Plan 21 Testing:
```bash
# After implementation
uv run pytest tests/test_providers.py -v
uv run modelmeter providers --days 90  # Should show github-copilot, opencode
make dev  # Check /providers page in web UI
```

---

## Documentation

Both plans are fully documented with:
- Problem statement and root cause analysis
- Step-by-step implementation phases
- File manifest (what to create/modify)
- Acceptance criteria
- Testing strategy
- Expected results before/after
- Effort estimates

Plans are self-contained and can be implemented independently.
