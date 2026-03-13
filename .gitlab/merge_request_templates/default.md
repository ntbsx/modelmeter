## Summary

- Describe the user-visible change and intent.

## Version Impact

- [ ] Patch (bugfix/internal)
- [ ] Minor (backward-compatible feature)
- [ ] Major (breaking behavior/contract)

Version notes:

- Canonical version update needed? (`pyproject.toml`, `web/package.json`)
- CalVer target (if bumping): `YYYY.M.D`

## API Contract Impact

- [ ] No API contract change
- [ ] Backward-compatible API change
- [ ] Breaking API change

If API changed, describe what changed and why.

## Verification

- [ ] `make version-check`
- [ ] `npm run --prefix web lint`
- [ ] `npm run --prefix web check:types`
- [ ] `make typecheck`
- [ ] `make test`
- [ ] `make release-check` (recommended before merge)

## Generated/Artifact Updates

- [ ] OpenAPI snapshot updated (`web/openapi.json`)
- [ ] TS API types/hash updated (`web/src/generated/*`)
- [ ] No generated artifacts changed

## Risk and Rollout

- Risk level: Low / Medium / High
- Rollback strategy:

## Checklist

- [ ] Updated docs (`README.md`, `AGENTS.md`, or plans) if workflow changed
- [ ] Added/updated tests for behavior changes
