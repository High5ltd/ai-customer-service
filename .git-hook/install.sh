#!/usr/bin/env bash
# Point git to use git-hook/ as the hooks directory.
# Run once after cloning: bash git-hook/install.sh

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)

git -C "$REPO_ROOT" config core.hooksPath git-hook

# Ensure hook files are executable
chmod +x "$REPO_ROOT"/git-hook/pre-commit

echo "Git hooks installed — using git-hook/"
