#!/usr/bin/env bash
# Deploy the Bastion Console showcase to a Hugging Face Space.
#
# Prereqs (one-time):
#   1. Create a free account at huggingface.co
#   2. Create the Space: huggingface.co/new-space
#        Name: bastion-console · SDK: Docker · Blank template · Public
#   3. Create a WRITE token: huggingface.co/settings/tokens
#      (git will ask for it as the password; username = your HF username)
#
# Usage:
#   bash deploy/hf-space/deploy.sh https://huggingface.co/spaces/<user>/bastion-console

set -euo pipefail

SPACE_URL="${1:?usage: deploy.sh <space git url>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"

echo "→ cloning Space repo…"
git clone "$SPACE_URL" "$TMP/space"

echo "→ assembling showcase bundle…"
rm -rf "$TMP/space/router" "$TMP/space/dashboard"
cp -R "$ROOT/router" "$ROOT/dashboard" "$TMP/space/"
cp "$ROOT/requirements.txt" "$TMP/space/"
cp "$ROOT/deploy/hf-space/Dockerfile" "$TMP/space/Dockerfile"
cp "$ROOT/deploy/hf-space/README-space.md" "$TMP/space/README.md"

cd "$TMP/space"
git add -A
git commit -m "Deploy Bastion Console showcase" || echo "(nothing new to commit)"
git push

echo
echo "✅ Pushed. The Space builds in ~2–4 minutes. Your demo URL:"
echo "   ${SPACE_URL%.git}"
