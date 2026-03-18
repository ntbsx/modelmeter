# 20. Source Status Banner and Loading States

**Status:** Planned  
**Priority:** High  
**Dependencies:** 16-federation-core.md, 19-dashboard-source-management-and-filtering.md

## Problem Statement

When users switch between local and remote data sources in the web UI, there's no visual feedback about:
- Whether the data is still loading
- Whether a remote source is inactive/unreachable
- Partial failures when some sources succeed and others fail
- Empty data vs failed source (different scenarios)

This creates a confusing UX where switching sources shows empty screens without explanation.

## Goals

1. **Loading Indicators**: Show clear loading state when switching between sources
2. **Inactive Source Warnings**: Display when remote sources are unreachable
3. **Partial Failure Visibility**: Show which sources succeeded/failed in federated mode
4. **Dim Effect During Refetch**: Provide visual feedback during data refresh
5. **Source Scope Indicator**: Persistent indicator showing current data source
6. **Inline Health Check**: Allow users to test source connectivity without leaving page

## Current State

### What Works
- ✅ API responses include source metadata: `sources_considered`, `sources_succeeded`, `sources_failed`
- ✅ Sources page shows health status badges (✓ Healthy / ✗ Unreachable)
- ✅ Health check functionality stores results in localStorage
- ✅ `SourceScopePicker` component in header for switching sources
- ✅ Warning banner on ProjectDetail page when using non-local scope

### What's Missing
- ❌ No visibility on data-fetching pages when remote sources fail
- ❌ No indication when queries are loading after source scope changes
- ❌ No banner to show partial failures (e.g., "All Sources" mode where one fails)
- ❌ ModelDetail page doesn't support source scope parameter (frontend doesn't pass it)
- ❌ Live page federation support (backend explicitly blocks non-local sources)

## Design Decisions

Based on user feedback, the following design decisions have been made:

1. **Banner persistence**: Visible when relevant (not dismissible)
2. **Success indicator**: No banner when all sources succeed (clean UI)
3. **Failed source details**: Show first failure inline, rest collapsed
4. **Health check**: Inline health check (no modal, no navigation)
5. **Loading skeleton**: Dim old data + show banner + pulse animation
6. **Source scope indicator**: Add persistent mini-indicator in page header

## Implementation Plan

### Phase 1: Create SourceStatusBanner Component

**File:** `web/src/components/SourceStatusBanner.tsx` (~200 lines)

**Banner Variants:**
- 🔵 **Loading** (blue): "Loading data from [source names]..."
- 🟡 **Partial failure** (amber): "Unable to reach production-server. 2 other sources unavailable."
- 🔴 **Complete failure** (red): "Unable to reach [source name]"
- ⚫ **No data** (gray): "No data available for the selected time range"
- ✅ **No banner** when all sources succeed with data

**Features:**
- Accept props: `isLoading`, `isFetching`, `sourceScope`, `sourcesConsidered`, `sourcesSucceeded`, `sourcesFailed`, `hasData`
- Show different banner variants with appropriate styling
- Include expandable section to show which specific sources failed and why
- Provide inline health check button that triggers `/sources/check` API
- Use similar styling to existing ProjectDetail warning banner

**Component API:**
```tsx
type SourceStatusBannerProps = {
  isLoading: boolean
  isFetching?: boolean
  sourceScope: SourceScopeValue
  sourcesConsidered?: string[]
  sourcesSucceeded?: string[]
  sourcesFailed?: Array<Record<string, string>>
  hasData: boolean
  healthCheckSupport?: boolean  // default true
}
```

**Styling:**
- Loading: `border-blue-200 bg-blue-50 text-blue-800 dark:bg-blue-900/30`
- Warning: `border-amber-200 bg-amber-50 text-amber-800 dark:bg-amber-900/30`
- Error: `border-red-200 bg-red-50 text-red-800 dark:bg-red-900/30`
- Info: `border-gray-200 bg-gray-50 text-gray-700 dark:bg-gray-900/30`

### Phase 2: Create useSourceLabels Hook

**File:** `web/src/hooks/useSourceLabels.ts` (~60 lines)

**Purpose:**
- Fetch source registry from `/sources` API
- Map source IDs to friendly labels
- Provide helper function: `getSourceLabel(sourceId: string): string`
- Return "This Server" for `'local'`, `'self'`, or empty
- Return configured label or fallback to ID for remotes

**Example Usage:**
```tsx
const { getSourceLabel, isLoading } = useSourceLabels()
getSourceLabel('local') // → "This Server"
getSourceLabel('prod-api') // → "Production Server" (if configured)
```

### Phase 3: Add Source Scope Indicator in Page Headers

**Implementation:**
Add a subtle indicator next to page title showing current source scope:
```tsx
<div className="flex items-center gap-2">
  <h1>Overview</h1>
  {sourceScope !== 'self' && (
    <span className="text-xs text-gray-500">
      viewing: {getSourceLabel(sourceScope)}
    </span>
  )}
</div>
```

### Phase 4: Integrate Banner into Data Pages

**Pages to Update:**

1. **Overview** (`web/src/pages/Overview.tsx`)
   - Insert banner between header and stat cards
   - Pass: `loadingSummary || loadingDaily`, summary/daily metadata
   - Has data check: `(summary?.totals.total_tokens ?? 0) > 0`

2. **Providers** (`web/src/pages/Providers.tsx`)
   - Insert banner after header
   - Has data check: `(data?.providers ?? []).length > 0`

3. **Models** (`web/src/pages/Models.tsx`)
   - Insert banner after header
   - Has data check: `(data?.models ?? []).length > 0`

4. **Projects** (`web/src/pages/Projects.tsx`)
   - Insert banner after header
   - Has data check: `(data?.projects ?? []).length > 0`

5. **ProjectDetail** (`web/src/pages/ProjectDetail.tsx`)
   - Replace existing warning banner with `SourceStatusBanner`
   - Keep scope enforcement: `detailScope = 'self'` when `sourceScope !== 'self'`
   - Pass `forceMessage` prop when scope is overridden

6. **Live** (`web/src/pages/Live.tsx`)
   - Add banner to show connection state
   - Keep scope enforcement: `liveScope = 'self'`
   - Pass `forceMessage` when scope is overridden

### Phase 5: Add Source Scope Support to ModelDetail

**Problem:** Frontend doesn't pass `source_scope` to API, even though backend accepts it.

**Files to Modify:** `web/src/pages/ModelDetail.tsx`

**Changes:**
- Import `useSourceScope` hook
- Add `const { sourceScope } = useSourceScope()`
- Update query to pass scope: `queryFn: () => fetchApi(..., { days, source_scope: sourceScope })`
- Update query key: `['model-detail', decodedModelId, days, sourceScope]`
- Add `SourceStatusBanner` after header
- Add scope indicator in page header

**Backend Behavior:**
- API already accepts `source_scope` parameter ✅
- Currently raises `NotImplementedError` for non-local scopes (line 791-792)
- Banner will catch this 501 error and show: "Federated model detail not yet supported"

### Phase 6: Refetch Indicator with Dim Effect

**Implementation:**
When data is refetching after source scope change:
1. Apply opacity to page content: `className="opacity-60 transition-opacity"`
2. Show banner with pulse animation
3. Restore opacity when fetch completes

**Code Pattern:**
```tsx
const { data, isLoading, isFetching } = useQuery(...)
const isRefetching = isFetching && !isLoading

return (
  <>
    <SourceStatusBanner
      isLoading={isLoading}
      isFetching={isRefetching}
      {...otherProps}
    />
    <div className={cn("transition-opacity", isRefetching && "opacity-60")}>
      {/* Page content */}
    </div>
  </>
)
```

## Federation Support Notes

### Current Backend State

Both **ModelDetail** and **Live** endpoints:
- ✅ Accept `source_scope` query parameter
- ✅ Parse `SourceScope` object correctly
- ❌ Raise `NotImplementedError("Federated ... not yet implemented")` for non-local scopes

This means:
1. ✅ API contract is ready for federation
2. ✅ Frontend can start passing `source_scope`
3. ⚠️ Backend will return **501 Not Implemented** for federated queries
4. ✅ Banner will display: "Federated model detail not yet supported" (graceful degradation)

### Future Work (Out of Scope)

Federation for ModelDetail and Live requires:
- **ModelDetail**: Merge model usage data from multiple sources (different sessions, dedupe logic)
- **Live**: Real-time event streams from multiple sources (complex connection pooling, multiplexing)

Both require significant backend work (~3-5 hours each) and should be tracked separately.

## Testing Strategy

### Manual Testing Scenarios

1. **Single local source**:
   - Should not show banner (or show minimal "Viewing This Server")
   
2. **Switch to "All Sources" when remote is healthy**:
   - Brief loading banner
   - Then no banner (or success indicator)
   
3. **Switch to "All Sources" when remote is down**:
   - Show amber "Partial data" banner
   - List failed sources with errors
   
4. **Switch to specific remote source that's down**:
   - Show red "Unable to reach" banner
   - Suggest health check
   
5. **Empty data scenario**:
   - Source succeeds but filters return no results
   - Show gray "No data" message (not error)

### Test Considerations

- Fast source switches (ensure loading states appear)
- Network throttling (slow responses)
- Offline remote source (health check failure)
- Different pages (Overview, Providers, Models, Projects)

## File Manifest

### New Files (2)
- `web/src/components/SourceStatusBanner.tsx` (~200 lines)
- `web/src/hooks/useSourceLabels.ts` (~60 lines)

### Modified Files (7)
- `web/src/pages/Overview.tsx` (~15 lines changed)
- `web/src/pages/Providers.tsx` (~15 lines changed)
- `web/src/pages/Models.tsx` (~15 lines changed)
- `web/src/pages/Projects.tsx` (~15 lines changed)
- `web/src/pages/ProjectDetail.tsx` (~20 lines changed)
- `web/src/pages/Live.tsx` (~20 lines changed)
- `web/src/pages/ModelDetail.tsx` (~25 lines changed) - **New source scope support**

### Unchanged (Backend Ready)
- `src/modelmeter/api/app.py` (already has `source_scope` params)
- `src/modelmeter/core/analytics.py` (returns 501 for federation)
- `src/modelmeter/core/live.py` (returns 501 for federation)

## Acceptance Criteria

### Must Have
- [ ] SourceStatusBanner component created with all variants (loading, warning, error, info)
- [ ] useSourceLabels hook maps source IDs to friendly names
- [ ] Banner integrated into 7 data pages (Overview, Providers, Models, Projects, ProjectDetail, ModelDetail, Live)
- [ ] Source scope indicator visible in page headers
- [ ] Loading state shows immediately on source switch
- [ ] Failed sources display with inline health check button
- [ ] Partial failures show first failure inline with count
- [ ] ModelDetail page passes source_scope to API
- [ ] 501 errors from backend show "Not yet supported" message
- [ ] Refetch state dims old data with pulse animation

### Should Have
- [ ] Health check runs inline without navigation
- [ ] Health check results update banner state
- [ ] Empty data vs failed source show different messages
- [ ] Banner auto-hides when all sources succeed

### Nice to Have
- [ ] Banner animation on state transitions
- [ ] Keyboard shortcuts for source switching
- [ ] Persist last selected source in localStorage

## Success Metrics

- Users can immediately see when data is loading from remote sources
- Users understand when remote sources are unavailable vs empty data
- Users can test source health without leaving the current page
- Reduced confusion when switching between source scopes
- Clear feedback on partial federation failures

## Related Plans

- **16-federation-core.md**: Backend federation implementation
- **19-dashboard-source-management-and-filtering.md**: Source picker and filtering
- **17-provider-analytics.md**: Provider detection (separate issue discovered)

## Notes

During investigation, discovered a separate issue: ModelMeter ignores the `providerID` field in message JSON, causing GitHub Copilot and OpenCode models to be misattributed. This is tracked in plan 21.

## Estimated Effort

- **Phase 1-2** (Core Components): 1.5 hours
- **Phase 3-4** (Integration): 1.5 hours
- **Phase 5** (ModelDetail): 0.5 hours
- **Phase 6-7** (Polish): 0.5 hours
- **Testing**: 1 hour

**Total:** ~4-5 hours
