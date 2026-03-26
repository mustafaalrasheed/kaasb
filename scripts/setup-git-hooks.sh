#!/usr/bin/env bash
# =============================================================================
# Kaasb — Developer Git Hooks Setup
# Run once after cloning: bash scripts/setup-git-hooks.sh
# =============================================================================
set -euo pipefail

echo "Setting up Kaasb developer tools..."

# ---- Commit message template ----
git config commit.template .gitmessage
echo "✓ Commit message template set (.gitmessage)"

# ---- pre-commit ----
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
fi

pre-commit install                     # hooks on git commit
pre-commit install --hook-type commit-msg  # hooks on commit message

echo "✓ pre-commit hooks installed"

# ---- Initialize detect-secrets baseline (if not exists) ----
if [ ! -f .secrets.baseline ]; then
    echo "Creating detect-secrets baseline..."
    pip install detect-secrets
    detect-secrets scan \
        --exclude-files ".*\.example$" \
        --exclude-files ".*test.*" \
        > .secrets.baseline
    echo "✓ .secrets.baseline created — commit this file"
else
    echo "✓ .secrets.baseline already exists"
fi

echo ""
echo "============================================================"
echo "  Developer setup complete!"
echo "============================================================"
echo ""
echo "  pre-commit hooks: active on every 'git commit'"
echo "  Commit template:  shown on 'git commit' (no -m flag)"
echo "  Secrets scan:     blocks accidental secret commits"
echo ""
echo "  Useful commands:"
echo "    pre-commit run --all-files    # Run all hooks now"
echo "    pre-commit autoupdate         # Update hook versions"
echo "    git commit                    # Opens commit template"
echo ""
echo "  Branch strategy:"
echo "    main     — production only (PRs required, CI must pass)"
echo "    develop  — integration branch (PRs from feature branches)"
echo "    feature/description — your work branches"
echo ""
echo "  Create develop branch (first time only):"
echo "    git checkout -b develop && git push -u origin develop"
echo ""
