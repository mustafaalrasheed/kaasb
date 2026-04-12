# Flagged Items for Review

No hardcoded secrets were found. All API keys, passwords, and tokens are correctly loaded from environment variables.

## Hardcoded Values Requiring Future Action

### USD_TO_IQD Exchange Rate
- **File**: `backend/app/services/qi_card_client.py` line 60
- **Value**: `USD_TO_IQD = 1310.0`
- **Risk**: Low — this is not a secret, but a stale value if the IQD/USD rate shifts significantly.
- **Action**: Replace with a live rate API call or a configurable env var (`USD_TO_IQD_RATE`) before scaling to high transaction volumes.

## Scan Results

| Check | Result |
|-------|--------|
| Hardcoded API keys in Python | None found |
| Hardcoded passwords in Python | None found |
| Hardcoded tokens in YAML/shell scripts | None found — shell scripts reference `$ENV_VAR` correctly |
| `.env` files tracked in git | None — only `.example` files tracked |
| AI attribution in code | None — `robots.ts` bot-blocking user agents (GPTBot, CCBot) are legitimate |
| Ruff lint (F401/F841) | All checks passed |
| TODO/FIXME in Python | None |
| TODO/FIXME in TypeScript | None |
| Debug `console.log` | One `console.error` in `error.tsx` (legitimate error boundary) |
| Debug `print()` in Python | None |
