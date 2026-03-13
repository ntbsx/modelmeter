# Contributor and Release Runbook

This runbook provides the standard workflow for feature delivery, release prep, and rollback.

## Feature Branch Workflow

1. Sync with `main` and create a feature branch.
2. Implement changes with focused commits.
3. Run local checks before opening MR:

```bash
make version-check
make contract-policy-check
npm run --prefix web lint
npm run --prefix web check:types
make typecheck
make test
```

4. If changing API contracts, ensure:
- `web/openapi.json` updated
- `web/src/generated/api.ts` updated
- `web/src/generated/openapi.sha256` updated
- canonical version intent documented in MR template

## Release Preparation

1. Stamp version and sync frontend:

```bash
make version-stamp
```

2. Run release gate:

```bash
make release-check
```

3. Commit release changes and create annotated tag:

```bash
git tag -a "v$(uv run python -c \"import tomllib, pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])\")" -m "Release"
git push --tags
```

4. CI release jobs will:
- build wheel/sdist with bundled web assets
- publish package files to GitLab generic package registry
- create/update GitLab release links for wheel/sdist assets

## Install Verification (Post-Release)

Run install from release metadata:

```bash
curl -fsSL https://gitlab.com/ntbsdev/modelmeter/-/raw/main/scripts/install.sh | bash -s -- --version <YYYY.M.D>
modelmeter --version
```

Confirm service:

```bash
modelmeter serve --host 127.0.0.1 --port 18080 --no-access-log
```

## Rollback Guidance

If a release is broken:

1. Stop adoption by updating release notes with warning.
2. Create a new corrective release tag (preferred) rather than deleting tags.
3. If installer pulls latest, recommend users pin last known good version.
4. Patch main, re-run `make release-check`, publish follow-up release.

Avoid force-pushing or rewriting release history.
