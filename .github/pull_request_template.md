## Summary

<!-- What does this PR do? One paragraph. Link to issue if applicable. -->
Closes #

## Type of Change

<!-- Check all that apply -->
- [ ] `feat` — New feature
- [ ] `fix` — Bug fix
- [ ] `refactor` — Code refactor (no behavior change)
- [ ] `perf` — Performance improvement
- [ ] `test` — Add/update tests
- [ ] `docs` — Documentation only
- [ ] `chore` — Build, CI, config, dependency update
- [ ] `hotfix` — Production critical fix

## Changes Made

<!-- Bullet list of what changed and why -->
-
-

## Database Changes

- [ ] No database changes
- [ ] New migration added — run `alembic upgrade head` after merge
- [ ] Migration is reversible (`downgrade` implemented)
- [ ] Schema change is backwards-compatible

## Testing

- [ ] Existing tests pass (`pytest backend/`)
- [ ] New tests added for new code paths
- [ ] Manually tested in local Docker stack
- [ ] API tested via `test_api.py` or Postman

## Security Checklist

- [ ] No secrets, passwords, or API keys added to code
- [ ] Input validated at API boundary (Pydantic schemas)
- [ ] Auth/permission checks in place for new endpoints
- [ ] No SQL injection vectors (SQLAlchemy ORM only, no raw f-strings)
- [ ] `pip-audit` passes (no new vulnerable dependencies)

## Frontend Changes

- [ ] No frontend changes
- [ ] `npm run lint` passes
- [ ] `tsc --noEmit` passes
- [ ] Responsive layout tested (mobile + desktop)

## Deployment Notes

<!-- Anything the deployer needs to know: new env vars, migration order, manual steps -->

## Screenshots / Recordings

<!-- For UI changes, paste a screenshot or screen recording here -->
