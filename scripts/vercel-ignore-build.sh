#!/usr/bin/env bash
# Vercel "Ignored Build Step" (vercel.json ignoreCommand; runs from the repo root).
# Exit 0 = skip the build. Exit 1 = run the build.
#
# The Python backend deploys to Railway; Vercel only serves the static frontend
# plus the root files it reads: vercel.json, middleware.js (and the
# scripts/edge/ module it imports) and .vercelignore.
#
# Preview (every branch but main): skip by default to cut build cost, unless the
# push changes deploy config (vercel.json, middleware, .vercelignore) or this
# script, so those get a real Vercel build before they reach main. Put
# [preview] in the commit message to force a preview for any push.
#
# Production (and anything else): build when Vercel-relevant files changed
# since the last deployed commit. When in doubt, build.
set -u

watched="frontend vercel.json middleware.js scripts/edge .vercelignore package.json package-lock.json scripts/vercel-ignore-build.sh"
deploy_config="vercel.json middleware.js scripts/edge .vercelignore scripts/vercel-ignore-build.sh"
ref="${VERCEL_GIT_COMMIT_REF:-}"

# No branch (CLI deploy): someone asked for it explicitly, so build.
if [ -z "$ref" ]; then
  echo "No git branch (CLI deploy): building"
  exit 1
fi

if [ "${VERCEL_ENV:-}" = "preview" ] && [ "$ref" != "main" ]; then
  case "${VERCEL_GIT_COMMIT_MESSAGE:-}" in
    *"[preview]"*)
      echo "[preview] in commit message: building preview"
      exit 1
      ;;
  esac
  base="${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}"
  # shellcheck disable=SC2086
  git diff --quiet "$base" HEAD -- $deploy_config
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "Deploy config changed: building preview"
    exit 1
  fi
  [ "$rc" -gt 1 ] && echo "git diff failed (rc=$rc); skipping preview anyway"
  echo "Skipping preview build. Add [preview] to the commit message to get one."
  exit 0
fi

# Production: compare against the last deployed commit. If Vercel does not say
# which one that was, build rather than guess from HEAD^.
base="${VERCEL_GIT_PREVIOUS_SHA:-}"
if [ -z "$base" ]; then
  echo "No previous deployed commit known: building"
  exit 1
fi
# shellcheck disable=SC2086
git diff --quiet "$base" HEAD -- $watched
rc=$?
if [ "$rc" -eq 0 ]; then
  echo "No Vercel-relevant files changed since $base: skipping build"
  exit 0
fi
[ "$rc" -gt 1 ] && echo "git diff failed (rc=$rc): building"
exit 1
