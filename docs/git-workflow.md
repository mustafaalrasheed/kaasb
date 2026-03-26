# Kaasb Git Workflow Guide

## Quick Setup (run once after cloning)

```bash
bash scripts/setup-git-hooks.sh
```

This installs pre-commit hooks, the commit message template, and initialises the
detect-secrets baseline. Takes 30 seconds.

---

## Branch Strategy

```
main ──────────────────────────────────────────► production
  └── develop ──────────────────────────────────► staging
        ├── feature/job-search-filters
        ├── feature/qi-card-refunds
        ├── bugfix/proposal-status-race
        └── hotfix/contract-null-pointer ────────► main (emergency)
```

| Branch | Purpose | Deploy target | Who merges |
|--------|---------|---------------|------------|
| `main` | Production-ready code only | kaasb.com | PR required + CI pass |
| `develop` | Integration branch, daily work | staging.kaasb.com | PR from feature/* |
| `feature/*` | New features and improvements | — | PR to develop |
| `bugfix/*` | Non-critical bug fixes | — | PR to develop |
| `hotfix/*` | Production emergencies only | — | PR to main → cherry-pick to develop |
| `release/*` | Release prep (changelogs, version bumps) | — | PR to main, tag, merge to develop |

### First-time develop branch setup

```bash
git checkout -b develop
git push -u origin develop
```

---

## Daily Workflow

### 1. Start a new task

```bash
# Always branch from develop (not main)
git checkout develop
git pull origin develop
git checkout -b feature/qi-card-partial-refunds
```

### 2. Write code, commit often

Use `git commit` (no `-m`) to open the commit template:

```
feat(payments): add partial refund support for Qi Card gateway

Qi Card gateway returns a transaction_id for partial refunds.
Previously we only supported full refunds. This change adds a
`amount` parameter to the refund endpoint and updates the
escrow service to track partial release amounts.

Closes #142
```

Or use the short form when the change is trivial:

```bash
git commit -m "fix(payments): correct IQD rounding in refund calculation"
git commit -m "test(payments): add partial refund test cases"
git commit -m "docs(api): document refund endpoint parameters"
```

### 3. Push and open PR

```bash
git push -u origin feature/qi-card-partial-refunds
# GitHub will print a PR link — open it
```

Fill in the PR template. For solo development, self-review then merge.

### 4. Merge strategy

- **Feature → develop**: Squash merge (keeps develop history clean)
- **Develop → main** (release): Merge commit (preserves the full release)
- **Hotfix → main**: Merge commit, then cherry-pick to develop

```bash
# After PR merged, clean up local branch
git checkout develop
git pull origin develop
git branch -d feature/qi-card-partial-refunds
```

---

## Commit Convention

Format: `type(scope): short summary`

| Type | When to use | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(jobs): add skills-based job matching` |
| `fix` | Bug fix | `fix(auth): prevent duplicate login events` |
| `perf` | Performance | `perf(db): add index on proposals.freelancer_id` |
| `refactor` | Refactor (no behavior change) | `refactor(contracts): extract payment logic to service` |
| `test` | Tests only | `test(jobs): add pagination edge case tests` |
| `docs` | Documentation | `docs(api): add OpenAPI description for /contracts` |
| `chore` | Build, deps, config | `chore(deps): upgrade stripe to 7.12.0` |
| `ci` | CI/CD changes | `ci: add pip-audit security scan to pipeline` |
| `devops` | Infrastructure | `devops: add alertmanager Telegram notifications` |
| `security` | Security fix | `security(auth): rotate compromised JWT secret` |
| `hotfix` | Production emergency | `hotfix(payments): fix null Qi Card response crash` |
| `revert` | Revert a commit | `revert: feat(jobs): add skills-based job matching` |

**Scopes** (use these consistently):
`auth` · `jobs` · `proposals` · `contracts` · `payments` · `messages` · `users` · `reviews` · `notifications` · `admin` · `db` · `api` · `ui` · `docker` · `nginx` · `ci` · `deps`

---

## Releasing

### Semantic versioning: MAJOR.MINOR.PATCH

- **PATCH** (1.0.X): Bug fixes, security patches — release any time
- **MINOR** (1.X.0): New features, backwards-compatible — release when ready
- **MAJOR** (X.0.0): Breaking changes — plan migration path first

### Release procedure

```bash
# 1. Create release branch from develop
git checkout develop && git pull
git checkout -b release/1.2.0

# 2. Bump version in .env.production.example and package.json
sed -i 's/APP_VERSION=.*/APP_VERSION=1.2.0/' .env.production.example
cd frontend && npm version 1.2.0 --no-git-tag-version && cd ..

# 3. Commit version bump
git commit -m "chore(release): bump version to 1.2.0"

# 4. PR to main → merge (merge commit, not squash)
# After merge:
git checkout main && git pull

# 5. Tag the release
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
# This triggers .github/workflows/release.yml → builds images → creates GitHub Release

# 6. Merge main back to develop (picks up version bump)
git checkout develop
git merge main
git push origin develop
```

### Release checklist

Before tagging:
- [ ] All tests pass in CI on develop
- [ ] `alembic check` shows no pending schema changes
- [ ] New env vars documented in `.env.production.example`
- [ ] Migration is reversible (test `alembic downgrade -1`)
- [ ] Manual backup taken on production
- [ ] Staging deploy verified (push to develop → staging auto-deploys)
- [ ] CHANGELOG reviewed (GitHub Release auto-generates from commits)

---

## Hotfix Workflow (production emergency)

```bash
# Branch from main — NOT develop
git checkout main && git pull
git checkout -b hotfix/contract-null-pointer

# Fix the bug
git commit -m "hotfix(contracts): fix null pointer in PDF generation"

# PR to main → merge immediately (bypass normal review for P0)
# After merge and deploy:

# Cherry-pick to develop so the fix doesn't get lost
git checkout develop && git pull
git cherry-pick <commit-hash>
git push origin develop
```

---

## Undoing Mistakes

### "I committed to main accidentally"

```bash
# Undo last commit, keep changes staged
git reset --soft HEAD~1
# Now move to a feature branch and re-commit
git checkout -b feature/my-work
git commit -m "feat: ..."
```

### "I committed a secret"

```bash
# IMMEDIATELY rotate the secret (assume it's already compromised)
# Then remove it from history with BFG:
brew install bfg  # macOS
# or: https://rtyley.github.io/bfg-repo-cleaner/

bfg --replace-text passwords.txt  # passwords.txt contains the secret
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force-with-lease

# Tell all team members to re-clone
```

### "I need to undo a pushed commit"

```bash
# Safe: creates a new commit that reverts the change
git revert <commit-hash>
git push origin <branch>

# Never: git reset --hard + force push on shared branches
```

### "I deleted a branch by accident"

```bash
# Find the commit hash from reflog
git reflog | grep "checkout: moving from deleted-branch"
git checkout -b deleted-branch <hash>
```

### "I need to unstage files"

```bash
git restore --staged path/to/file   # unstage specific file
git restore --staged .              # unstage everything
```

### "My commit message is wrong (not yet pushed)"

```bash
git commit --amend --no-edit       # keep message, update content
git commit --amend -m "new message"  # change message
# Never amend commits already pushed to shared branches
```

---

## Git Aliases (add to ~/.gitconfig)

```ini
[alias]
    # Short status
    s   = status -sb

    # Pretty log
    lg  = log --oneline --graph --decorate --all -20

    # Current branch name
    br  = rev-parse --abbrev-ref HEAD

    # Switch to develop and pull
    dev = !git checkout develop && git pull origin develop

    # Create feature branch from develop
    feat = "!f() { git checkout develop && git pull && git checkout -b feature/$1; }; f"
    fix  = "!f() { git checkout develop && git pull && git checkout -b bugfix/$1; }; f"
    hot  = "!f() { git checkout main && git pull && git checkout -b hotfix/$1; }; f"

    # Undo last commit (keep changes)
    undo = reset --soft HEAD~1

    # Push current branch to origin
    pub = !git push -u origin $(git rev-parse --abbrev-ref HEAD)

    # Clean merged local branches
    clean-branches = !git branch --merged main | grep -v '\\*\\|main\\|develop' | xargs git branch -d
```

Usage:
```bash
git feat job-search-filters      # creates feature/job-search-filters from develop
git hot contract-null-pointer    # creates hotfix/contract-null-pointer from main
git lg                           # pretty log
git pub                          # push current branch
```

---

## GitHub Repository Settings

Configure these once in GitHub Settings:

### Branch Protection — `main`
- Require a pull request before merging: **on**
- Required status checks: `Backend CI`, `Frontend CI`
- Require branches to be up to date before merging: **on**
- Do not allow bypassing the above settings: **on**
- Allow force pushes: **off**

### Branch Protection — `develop`
- Required status checks: `Backend CI`, `Frontend CI`
- Allow force pushes: **off**

### Required Secrets (Settings → Environments → production)

| Secret | Where to get it |
|--------|-----------------|
| `SERVER_HOST` | Hetzner server IP |
| `SERVER_USER` | `root` |
| `SSH_PRIVATE_KEY` | `cat ~/.ssh/kaasb_deploy` |
| `TELEGRAM_BOT_TOKEN` | BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | Your Telegram chat/group ID |

### Required Secrets (Settings → Environments → staging)

| Secret | Where to get it |
|--------|-----------------|
| `STAGING_HOST` | Staging server IP |
| `STAGING_USER` | `root` |
| `SSH_PRIVATE_KEY` | Same deploy key as production |

---

## VS Code Tips

- **GitLens extension**: Inline blame, history comparison, branch visualization
- **Source Control panel** (Ctrl+Shift+G): Stage hunks, write commits with template
- **Keyboard shortcuts**:
  - `Ctrl+Shift+G` — Open Source Control
  - `Ctrl+\`` `` — Open terminal for git commands
- **Stage individual lines**: In the diff view, select lines → right-click → "Stage Selected Ranges"
- **Resolve merge conflicts**: VS Code shows conflict markers with Accept buttons — use "Accept Incoming" / "Accept Current" / "Accept Both"
