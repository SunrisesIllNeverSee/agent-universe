#!/usr/bin/env bash
# Vercel "Ignored Build Step" (vercel.json ignoreCommand; runs from the repo root).
# Exit 0 = skip the build. Exit 1 = run the build.
#
# The Python backend deploys to Railway; Vercel only serves the static frontend
# plus the root files it reads: vercel.json, middleware.js (and the
# scripts/edge/ module it imports) and .vercelignore.
#
# Preview (every branch but main): skip by default to cut build cost. Put
# [preview] in the commit message to get a preview link for that push.
#
# Everything else (production, or Vercel did not say): build when Vercel-relevant
# files changed since the last deployed commit. When in doubt, build.
set -u

# Skip only a git-branch preview: a deploy with no branch (CLI) always builds.
ref="${VERCEL_GIT_COMMIT_REF:-}"
if [ "${VERCEL_ENV:-}" = "preview" ] && [ -n "$ref" ] && [ "$ref" != "main" ]; then
  case "${VERCEL_GIT_COMMIT_MESSAGE:-}" in
    *"[preview]"*)
      echo "[preview] in commit message: building preview"
      exit 1
      ;;
  esac
  echo "Skipping preview build. Add [preview] to the commit message to get one."
  exit 0
fi

# Compare against the last deployed commit when Vercel provides it, so a
# multi-commit push is judged on all its commits, not only the newest one.
base="${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}"
if git diff --quiet "$base" HEAD -- frontend vercel.json middleware.js scripts/edge .vercelignore; then
  echo "No Vercel-relevant files changed since $base: skipping build"
  exit 0
fi
# Files changed, or git could not tell (exit 128): build.
exit 1
