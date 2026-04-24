# Signup / Registration Audit

Opened 2026-04-25 in response to user ask: *"is the signup works correctly or needs enhancements?"*

Scope: the `/auth/register` POST path end-to-end — FE form → Pydantic schema → `AuthService.register` → auto-login + welcome email → redirect to `/dashboard`. Social login (`POST /auth/social`) and phone OTP are checked at a summary level only.

---

## Verdict

**Works correctly for MVP beta.** No blocking bugs. There are 4 real launch-time gaps and 3 polish items worth considering before opening signups to the public.

---

## What is already right

- Password policy enforced server-side (min 8, upper + digit + special). Client-side hint matches.
- Duplicate email/username checks return a **generic** 409 — deliberate: does not leak which accounts exist (user-enumeration resistance).
- Rate-limited: 3 registrations per IP per 10 min ([security.py:110](../../backend/app/middleware/security.py#L110)).
- Username is normalised server-side (`sanitize_username`) and client-side (strip non-Latin / spaces).
- Password hashing runs off the event loop (`hash_password_async`), so registration doesn't block.
- JWT pair + httpOnly cookies set on successful register ([auth.py:116](../../backend/app/api/v1/endpoints/auth.py#L116)).
- Welcome email is fire-and-forget with its own session — failures don't 500 the registration.
- CSRF-origin checked on `POST /auth/register` (production only).
- Legal + 18+ checkbox required client-side to submit ([register-client.tsx:197-241](../../frontend/src/app/auth/register/register-client.tsx#L197)).

---

## Findings

### P0 — Launch gap

**F1. Legal acceptance is UI-only.** The Terms + Privacy + Acceptable-Use checkbox is validated client-side only. It's not posted to the backend, not stored, and has no timestamp. If a user later disputes a clause, we cannot prove they accepted it at signup. Consumer-protection statutes (Iraqi commercial code; also a question for Legal Track A) typically require a record of consent at the moment of contract formation.

**Fix**: add `terms_accepted_at` + `terms_version` columns on `users`, include them in `UserRegister`, set in `AuthService.register`. Reject registration if the flag is false. One migration, ~20 LoC.

### P1 — Real UX issues

**F2. `is_email_verified=True` hardcoded at signup** ([auth_service.py:115](../../backend/app/services/auth_service.py#L115)). Comment says "Skip email verification for MVP." This means:
- A typo'd email gets an active account that can never receive password-reset mail.
- Fake / disposable emails are trivially registrable — spam exposure on launch.
- Notification emails silently bounce.

**Fix** (two-step, not one PR): (a) keep auto-verify but send a `send_verification_email` on signup so the user can recover if they typo'd; (b) later, require verification before escrow-funding (keep browsing + DM open so onboarding friction stays low).

**F3. Password field has no live strength feedback.** Users learn that "special character required" from a 400 after submit. Known friction point in Arabic-first onboarding — the inline AR hint translates "special character" as "حرف خاص" which is ambiguous (many Arabic typists think punctuation marks in their layout don't count).

**Fix**: live requirements checklist under the password field (✓ 8+ chars, ✓ uppercase, ✓ digit, ✓ symbol). Tailwind-only; no new deps.

**F4. No confirm-password field.** Typos on the only password field land the user with an account they can't log into. They must go through password-reset flow — which won't work because F2 means we probably send mail to a typo'd email.

**Fix**: add `confirmPassword` state; only compare on submit. Plain UI change; no backend work.

### P2 — Polish

**F5. Auto-generated username can be empty.** Line 45 of register-client.tsx: `autoUsername` strips non-Latin characters. An Arabic-only user ("محمد", "علي") gets an empty username field that fails submit with a validation error. At minimum, fall back to email-prefix when the auto-gen is empty.

**F6. Duplicate email vs username conflict not distinguished.** Both return the same 409 + generic message (user-enumeration protection). But when the user types a unique email and hits 409, they cannot tell whether the conflict is username or something else. One way to get both: return `{ "detail": "...", "hints": ["try a different username"] }` on pure username conflict only when the email isn't in the DB (email conflict stays generic). Middle-ground that keeps enumeration protection for the email side.

**F7. Welcome email task is not logged on failure.** `asyncio.create_task(email_service.send_welcome_email(...))` without `.add_done_callback`. If Resend rejects the send, we log nothing. Low severity but makes Sentry alerts harder to triage.

---

## Not a bug (behaves as designed)

- Generic 409 message = intentional user-enumeration resistance.
- Auto-login after registration = MVP choice; future may add email-verify-before-login.
- `primary_role` default = `"freelancer"` on the form — deliberate (the two-sided marketplace needs supply first).
- Social login (`POST /auth/social`) bypasses password rules — the OAuth provider is the trust root.

---

## Recommended launch sequence

If shipping everything: **F1 → F4 → F3 → F5 → F2 (2-step) → F6 → F7**. F1 should happen **before** Legal Track A redlines land, so counsel knows we persist acceptance. F2 is the only multi-PR item.

If shipping one: **F1** (compliance) is the highest-value per line-of-code.
