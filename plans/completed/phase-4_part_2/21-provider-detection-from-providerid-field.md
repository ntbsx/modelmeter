# 21. Provider Detection from providerID Field

**Status:** Planned  
**Priority:** High  
**Dependencies:** None (standalone fix)

## Problem Statement

ModelMeter currently **ignores the `providerID` field** in OpenCode message JSON and only uses pattern-based detection from model ID strings. This causes significant misattribution:

- **~700 messages** from **GitHub Copilot** are incorrectly attributed to OpenAI/Anthropic
- **~2,569 messages** from **OpenCode** proxy are marked as "unknown" provider

### Example Data from Investigation

Query results from database show the issue:

```
Model                     Provider (actual)    Count    Provider (detected)
gpt-5.3-codex             github-copilot       253      → openai (WRONG)
claude-sonnet-4.5         github-copilot       126      → anthropic (WRONG)
gpt-5.4                   github-copilot       39       → openai (WRONG)
minimax-m2.5-free         opencode             1687     → unknown (WRONG)
mimo-v2-flash-free        opencode             311      → unknown (WRONG)
big-pickle                opencode             281      → unknown (WRONG)
trinity-large-preview     opencode             276      → unknown (WRONG)
nemotron-3-super-free     opencode             14       → unknown (WRONG)
```

## Root Cause Analysis

### Current Code Path

1. `get_providers()` calls `repository.fetch_model_usage_detail(days=days)`
2. Repository extracts `model_id` from JSON but **not** `providerID`
3. Analytics calls `provider_from_model_id(model_id)` (line 709 in analytics.py)
4. This function only does string pattern matching:
   ```python
   heuristic_prefixes = (
       ("gpt-", "openai"),
       ("claude-", "anthropic"),
       ("gemini-", "google"),
       # ... missing github-copilot and opencode
   )
   ```

### Message Data Structure

OpenCode stores messages with this structure:
```json
{
  "role": "assistant",
  "modelID": "gpt-5.3-codex",
  "providerID": "github-copilot",  // ← IGNORED by ModelMeter
  "tokens": { ... }
}
```

The `providerID` field contains authoritative provider information but is not being read.

## Goals

1. Extract `providerID` from message JSON in all data repository queries
2. Update provider detection logic to prioritize `providerID` over pattern matching
3. Correctly attribute usage to **github-copilot** and **opencode** providers
4. Maintain backwards compatibility with messages lacking `providerID`
5. Add tests to prevent regression

## Implementation Plan

### Phase 1: Extract providerID from Messages

**File:** `src/modelmeter/data/sqlite_usage_repository.py`

**Methods to Update:**

All methods that extract `model_id` need to also extract `provider_id`:

1. **`fetch_model_usage_detail()`** (line ~250)
2. **`fetch_daily_model_usage()`** (line ~277)
3. **`fetch_model_detail()`** (line ~320)
4. **`fetch_daily_model_detail()`** (line ~365)
5. **`fetch_project_model_breakdown()`** (line ~405)
6. **`fetch_project_session_detail()`** (line ~453)
7. **`fetch_project_daily_usage()`** (line ~539)
8. **`fetch_live_model_usage()`** (line ~650)

**Example Change:**

Current code (line 254-258):
```python
COALESCE(
    json_extract(data, '$.modelID'),
    json_extract(data, '$.model.modelID'),
    'unknown'
) AS model_id,
```

Add after `model_id`:
```python
COALESCE(
    json_extract(data, '$.providerID'),
    json_extract(data, '$.model.providerID'),
    NULL
) AS provider_id,
```

**Note:** Use `NULL` as default for `provider_id` (not `'unknown'`) to distinguish "not provided" from "explicitly unknown".

### Phase 2: Update Provider Detection Logic

**File:** `src/modelmeter/core/providers.py`

**Create New Function:**

```python
def provider_from_model_id_and_provider_field(
    model_id: str,
    provider_id: str | None = None,
) -> str:
    """
    Resolve provider label from model_id and optional providerID field.
    
    Priority:
    1. Use providerID from message data if available and valid
    2. Fall back to heuristic pattern matching on model_id
    
    Args:
        model_id: Model identifier string (e.g., "gpt-4o", "claude-3-opus")
        provider_id: Optional providerID from message JSON
        
    Returns:
        Normalized provider name (e.g., "openai", "github-copilot", "opencode")
    """
    # Normalize providerID if present
    if provider_id:
        normalized = provider_id.strip().lower()
        # Accept any non-empty, non-"unknown" providerID
        if normalized and normalized != "unknown":
            return normalized
    
    # Fall back to existing pattern-based detection
    return provider_from_model_id(model_id)
```

**Why New Function?**
- Keeps backwards compatibility for code that only has model_id
- Explicit naming shows we're using both fields
- Easier to test and reason about
- Clear migration path

### Phase 3: Update Analytics to Use provider_id

**File:** `src/modelmeter/core/analytics.py`

**Locations to Update:**

1. **`get_providers()`** (line ~709):
   ```python
   # Current:
   provider = provider_from_model_id(model_id)
   
   # New:
   provider = provider_from_model_id_and_provider_field(
       model_id=model_id,
       provider_id=row.get("provider_id"),  # May be None
   )
   ```

2. **`get_models()`** (line ~439+):
   - Similar change when filtering by provider
   - Ensure provider detection uses new function

3. **`get_model_detail()`** (line ~839):
   ```python
   # Current:
   provider=provider_from_model_id(model_id)
   
   # New:
   provider=provider_from_model_id_and_provider_field(
       model_id=model_id,
       provider_id=row.get("provider_id") if row else None,
   )
   ```

4. **`get_projects()`** (line ~850+):
   - Update provider attribution in project breakdowns

5. **`get_project_detail()`** (line ~950+):
   - Update provider detection in session details

6. **Live monitoring** (`src/modelmeter/core/live.py`):
   - Update `get_live_snapshot()` to use new function

**Import Statement:**
```python
from modelmeter.core.providers import (
    provider_from_model_id,
    provider_from_model_id_and_provider_field,  # Add this
)
```

### Phase 4: Add Tests

**File:** `tests/test_providers.py` (create new or add to existing)

**Test Cases:**

```python
import pytest
from modelmeter.core.providers import (
    provider_from_model_id,
    provider_from_model_id_and_provider_field,
)


class TestProviderDetection:
    """Test provider detection from model_id and providerID field."""
    
    def test_provider_from_providerid_field_github_copilot(self):
        """GitHub Copilot models should be detected from providerID."""
        assert provider_from_model_id_and_provider_field(
            "gpt-5.3-codex", "github-copilot"
        ) == "github-copilot"
        
        assert provider_from_model_id_and_provider_field(
            "claude-sonnet-4.5", "github-copilot"
        ) == "github-copilot"
        
        assert provider_from_model_id_and_provider_field(
            "gpt-5.4", "GitHub-Copilot"  # Case insensitive
        ) == "github-copilot"
    
    def test_provider_from_providerid_field_opencode(self):
        """OpenCode proxied models should be detected from providerID."""
        assert provider_from_model_id_and_provider_field(
            "minimax-m2.5-free", "opencode"
        ) == "opencode"
        
        assert provider_from_model_id_and_provider_field(
            "big-pickle", "opencode"
        ) == "opencode"
        
        assert provider_from_model_id_and_provider_field(
            "mimo-v2-flash-free", "OpenCode"  # Case insensitive
        ) == "opencode"
    
    def test_fallback_to_pattern_matching_when_no_providerid(self):
        """Should fall back to pattern matching when providerID is None."""
        # OpenAI models
        assert provider_from_model_id_and_provider_field(
            "gpt-4o", None
        ) == "openai"
        
        assert provider_from_model_id_and_provider_field(
            "gpt-4o-mini", None
        ) == "openai"
        
        # Anthropic models
        assert provider_from_model_id_and_provider_field(
            "claude-3-opus", None
        ) == "anthropic"
        
        # Google models
        assert provider_from_model_id_and_provider_field(
            "gemini-pro", None
        ) == "google"
    
    def test_fallback_when_providerid_is_unknown(self):
        """Should fall back to pattern matching when providerID is 'unknown'."""
        assert provider_from_model_id_and_provider_field(
            "gpt-4o", "unknown"
        ) == "openai"
        
        assert provider_from_model_id_and_provider_field(
            "claude-3-opus", "unknown"
        ) == "anthropic"
    
    def test_providerid_takes_precedence_over_pattern(self):
        """providerID should take precedence even when pattern matches."""
        # Model ID suggests OpenAI, but providerID says GitHub Copilot
        assert provider_from_model_id_and_provider_field(
            "gpt-5.3-codex", "github-copilot"
        ) == "github-copilot"
        
        # Model ID suggests Anthropic, but providerID says GitHub Copilot
        assert provider_from_model_id_and_provider_field(
            "claude-sonnet-4.5", "github-copilot"
        ) == "github-copilot"
    
    def test_unknown_model_without_providerid(self):
        """Unknown models without providerID should return 'unknown'."""
        assert provider_from_model_id_and_provider_field(
            "random-model-123", None
        ) == "unknown"
        
        assert provider_from_model_id_and_provider_field(
            "big-pickle", None
        ) == "unknown"
    
    def test_empty_and_whitespace_providerid(self):
        """Empty or whitespace providerID should fall back to pattern."""
        assert provider_from_model_id_and_provider_field(
            "gpt-4o", ""
        ) == "openai"
        
        assert provider_from_model_id_and_provider_field(
            "gpt-4o", "   "
        ) == "openai"
    
    def test_backwards_compatibility(self):
        """Original function should still work for existing code."""
        assert provider_from_model_id("gpt-4o") == "openai"
        assert provider_from_model_id("claude-3-opus") == "anthropic"
        assert provider_from_model_id("gemini-pro") == "google"
        assert provider_from_model_id("unknown-model") == "unknown"


class TestProviderIntegration:
    """Integration tests with actual database queries."""
    
    @pytest.fixture
    def repository(self, tmp_path):
        """Create test SQLite database with sample data."""
        # Implementation would create a test DB with sample messages
        # including both model_id and provider_id fields
        pass
    
    def test_providers_endpoint_includes_github_copilot(self, repository):
        """Providers list should include github-copilot."""
        # Test that get_providers() correctly attributes
        # GitHub Copilot models when providerID is present
        pass
    
    def test_providers_endpoint_includes_opencode(self, repository):
        """Providers list should include opencode."""
        # Test that get_providers() correctly attributes
        # OpenCode models when providerID is present
        pass
```

**Run Tests:**
```bash
uv run pytest tests/test_providers.py -v
```

### Phase 5: Update OpenAPI Schema (if needed)

**Check if response schemas change:**
```bash
make gen-types
```

If provider names in responses change (e.g., new providers appear), the OpenAPI schema will capture this automatically. Frontend types will be regenerated.

### Phase 6: Manual Verification

**Test Commands:**

1. **Check providers list:**
   ```bash
   uv run modelmeter providers --days 90
   ```
   
   Expected output should now include:
   ```
   Provider        Models  Sessions  Total Tokens    Cost
   github-copilot  6       ~700      ...            ...
   opencode        5       2,569     ...            ...
   openai          3       2,200     ...            ...
   anthropic       3       1,300     ...            ...
   google          6       3,400     ...            ...
   ```

2. **Check specific models:**
   ```bash
   uv run modelmeter models --days 90 | grep -E "github-copilot|opencode"
   ```

3. **Web UI verification:**
   ```bash
   make dev
   ```
   Navigate to `/providers` and verify:
   - "GitHub Copilot" appears as a provider
   - "OpenCode" appears as a provider
   - Usage counts match CLI output

4. **Verify no regression:**
   ```bash
   # OpenAI models should still work
   uv run modelmeter models --provider openai
   
   # Anthropic models should still work
   uv run modelmeter models --provider anthropic
   ```

## Expected Results

### Before Fix

```
Provider     Models  Sessions  Interactions
openai       5       ~2,900    ...  ← Includes GitHub Copilot models
anthropic    4       ~1,500    ...  ← Includes GitHub Copilot models
google       6       3,400     ...
unknown      5       2,569     ...  ← All OpenCode models
```

### After Fix

```
Provider        Models  Sessions  Interactions
openai          3       2,200     ...  ← Copilot separated out
anthropic       3       1,300     ...  ← Copilot separated out
google          6       3,400     ...
github-copilot  6       ~700      ...  ← NEW! Properly attributed
opencode        5       2,569     ...  ← NEW! Properly attributed
```

## File Manifest

### Modified Files

1. **`src/modelmeter/data/sqlite_usage_repository.py`** (~50 lines changed)
   - Add `provider_id` extraction in 8 fetch methods
   - All methods that extract `model_id` updated

2. **`src/modelmeter/core/providers.py`** (~25 lines added)
   - New function: `provider_from_model_id_and_provider_field()`
   - Keep existing `provider_from_model_id()` for compatibility

3. **`src/modelmeter/core/analytics.py`** (~30 lines changed)
   - Update `get_providers()` to use new provider function
   - Update `get_models()` to use new provider function
   - Update `get_model_detail()` to use new provider function
   - Update `get_projects()` to use new provider function
   - Update `get_project_detail()` to use new provider function
   - Add import for new function

4. **`src/modelmeter/core/live.py`** (~10 lines changed)
   - Update `get_live_snapshot()` to use new provider function

### New Files

5. **`tests/test_providers.py`** (~150 lines)
   - Unit tests for provider detection logic
   - Integration tests with repository queries
   - Regression tests for existing providers

## Acceptance Criteria

### Must Have

- [ ] `provider_id` extracted from message JSON in all repository fetch methods
- [ ] `provider_from_model_id_and_provider_field()` function created
- [ ] Provider detection prioritizes `providerID` field over pattern matching
- [ ] All analytics functions use new provider detection
- [ ] Tests cover GitHub Copilot and OpenCode detection
- [ ] Tests cover fallback to pattern matching
- [ ] Tests cover edge cases (empty, whitespace, "unknown")
- [ ] CLI shows "github-copilot" and "opencode" in providers list
- [ ] Web UI shows "GitHub Copilot" and "OpenCode" in providers page
- [ ] Existing providers (OpenAI, Anthropic, Google) still work correctly

### Should Have

- [ ] Integration tests with actual database queries
- [ ] Backwards compatibility verified for messages without `providerID`
- [ ] OpenAPI schema regenerated if needed
- [ ] Documentation updated to explain provider detection logic

### Nice to Have

- [ ] Migration guide for users with existing data
- [ ] Analytics on how many messages have `providerID` field
- [ ] Logging when provider detection falls back to pattern matching

## Success Metrics

- **Accuracy**: GitHub Copilot and OpenCode models correctly attributed (0% misattribution)
- **Coverage**: All messages with `providerID` field use that value
- **Compatibility**: Existing model pattern detection still works for messages without `providerID`
- **Tests**: 100% test coverage for new provider detection logic
- **User Impact**: Users see correct provider attribution in CLI and web UI

## Migration Notes

### Data Migration

**Not required.** This is a read-only change to how ModelMeter interprets existing data. No database modifications needed.

### Rollback Plan

If issues arise:
1. Revert changes to `analytics.py` and `live.py` to use old `provider_from_model_id()`
2. Keep repository changes (extracting `provider_id` is harmless even if unused)
3. New function remains available for future use

## Related Issues

### Database Coverage Analysis

From investigation, the following model/provider combinations exist:

**GitHub Copilot (701 total messages):**
- gpt-5.3-codex: 253
- claude-sonnet-4.5: 126
- gpt-5.4: 39
- claude-opus-4.5: 8
- gpt-5-mini: 7
- gpt-4o: 1
- gpt-5: 2
- gpt-5.2: 1

**OpenCode (2,569 total messages):**
- minimax-m2.5-free: 1,687
- mimo-v2-flash-free: 311
- big-pickle: 281
- trinity-large-preview-free: 276
- nemotron-3-super-free: 14

This represents **~20% of all assistant messages** in the test database being misattributed.

## Related Plans

- **03-analytics-engine.md**: Core analytics implementation
- **17-provider-analytics.md**: Provider-level analytics (this fixes data accuracy)
- **20-source-status-banner-and-loading-states.md**: Frontend UX improvements (discovered during investigation)

## Estimated Effort

- **Phase 1** (Data extraction): 1 hour
  - Update 8 repository methods
  - Test queries return provider_id

- **Phase 2** (Provider detection logic): 0.5 hours
  - Create new function
  - Handle edge cases

- **Phase 3** (Analytics updates): 1 hour
  - Update 5 analytics functions
  - Update live monitoring

- **Phase 4** (Tests): 1 hour
  - Unit tests for provider detection
  - Integration tests
  - Regression tests

- **Phase 5-6** (Verification): 0.5 hours
  - Regenerate types if needed
  - Manual CLI testing
  - Web UI verification

**Total: ~4 hours**

## Notes

This issue was discovered while investigating source status banners. The root cause is straightforward: ModelMeter reads `modelID` from message JSON but ignores `providerID`, relying instead on fragile string pattern matching.

The fix is clean and low-risk:
1. Extract additional field from existing data
2. Prefer explicit field over heuristic
3. Maintain backwards compatibility for old messages
4. Add comprehensive tests

No database schema changes, no migrations, no breaking changes.
