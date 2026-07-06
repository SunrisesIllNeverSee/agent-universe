#!/bin/bash
# lanes.sh — cross-repo currency probe (READ-ONLY, flags nothing dangerous).
#
# Answers ONE question: "are we current across all lanes?" — every repo, every
# registry, in one glance. Computes nothing proprietary and CHANGES nothing.
#
# CONFIG: Edit the LANES array below to match your repos. Each lane is:
#   "name|path|expected-branch|registry|package-name"
# where registry is "npm" or "pypi" or "none".
#
# Usage: bash scripts/lanes.sh            (fetches remotes; add --no-fetch to skip)

set +e

NO_FETCH=0
[ "$1" = "--no-fetch" ] && NO_FETCH=1

# ─── CONFIG: edit these for your project ─────────────────────────────────────
# Format: "name|path|expected-branch|registry|package-name"
_REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANES=(
  "agent-universe|$_REPO_ROOT|main|pypi|civitae-mcp"
  # Add related repos here:
  # "personal-command|$HOME/Desktop/personal-command|main|none|"
  # "command-engine|$HOME/Desktop/command-engine|main|npm|"
  # "moses-governance|$HOME/Desktop/moses-governance|main|none|"
)
# ─────────────────────────────────────────────────────────────────────────────

bold(){ printf '\033[1m%s\033[0m\n' "$1"; }
dim(){ printf '\033[2m%s\033[0m\n' "$1"; }

git_lane(){
  local name="$1" dir="$2" want_branch="$3" registry="$4" pkg="$5"
  if [ ! -d "$dir/.git" ]; then printf '  %-13s \033[2mMISSING (%s)\033[0m\n' "$name" "$dir"; return; fi
  [ "$NO_FETCH" = 0 ] && git -C "$dir" fetch --quiet 2>/dev/null
  local ver head branch ahead behind dirty
  ver=$(node -p "require('$dir/package.json').version" 2>/dev/null || echo "—")
  branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
  head=$(git -C "$dir" log -1 --format='%h %cd' --date=short 2>/dev/null)
  ahead=$(git -C "$dir" rev-list --count @{u}..HEAD 2>/dev/null || echo "?")
  behind=$(git -C "$dir" rev-list --count HEAD..@{u} 2>/dev/null || echo "?")
  dirty=$(git -C "$dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  local warn=""
  [ "$branch" != "$want_branch" ] && warn="$warn ⚠branch(want $want_branch)"
  [ "$ahead" != "0" ] && [ "$ahead" != "?" ] && warn="$warn ⚠${ahead}-unpushed"
  [ "$behind" != "0" ] && [ "$behind" != "?" ] && warn="$warn ⚠${behind}-behind"
  [ "$dirty" != "0" ] && warn="$warn ⚠${dirty}-dirty"
  [ -z "$warn" ] && warn=" ✓ clean+synced"
  printf '  %-13s v%-8s %-20s %s\n' "$name" "$ver" "$branch @ $head" "$warn"
  # Stash version for registry compare
  [ -n "$pkg" ] && eval "VER_${name//-/_}='$ver'"
}

reg_lane(){
  local label="$1" localver="$2" pub="$3"
  local mark="≠ MISMATCH"
  [ "$localver" = "$pub" ] && mark="✓ matches local"
  [ "$pub" = "—" ] && mark="⚠ registry unreachable"
  printf '  %-13s published %-8s  (local %-8s) %s\n' "$label" "$pub" "$localver" "$mark"
}

bold "── Lanes currency probe ───────────────────────────────────"
dim  "   $(date -u '+%Y-%m-%d %H:%M UTC')$([ "$NO_FETCH" = 1 ] && echo '  (--no-fetch)')"
echo

bold "GIT LANES"
for lane in "${LANES[@]}"; do
  IFS='|' read -r name dir branch registry pkg <<< "$lane"
  git_lane "$name" "$dir" "$branch" "$registry" "$pkg"
done
echo

# Collect registries
HAS_REG=0
for lane in "${LANES[@]}"; do
  IFS='|' read -r name dir branch registry pkg <<< "$lane"
  if [ "$registry" = "npm" ] && [ -n "$pkg" ]; then
    [ "$HAS_REG" = 0 ] && bold "REGISTRIES (published truth vs local package.json)" && HAS_REG=1
    pub=$(npm view "$pkg" version 2>/dev/null || echo "—")
    localvar="VER_${name//-/_}"
    reg_lane "npm $pkg" "${!localvar:-—}" "$pub"
  elif [ "$registry" = "pypi" ] && [ -n "$pkg" ]; then
    [ "$HAS_REG" = 0 ] && bold "REGISTRIES (published truth vs local package.json)" && HAS_REG=1
    pub=$(curl -s --max-time 8 "https://pypi.org/pypi/$pkg/json" 2>/dev/null | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{process.stdout.write(JSON.parse(d).info.version)}catch{process.stdout.write('—')}})" 2>/dev/null || echo "—")
    localvar="VER_${name//-/_}"
    reg_lane "PyPI $pkg" "${!localvar:-—}" "$pub"
  fi
done
[ "$HAS_REG" = 1 ] && echo

dim "Read the marks; nothing was changed. ≠ = committed-but-unpublished OR a reverted version bump."
