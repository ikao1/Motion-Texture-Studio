#!/usr/bin/env bash
# pfa-repos.sh -- one-glance inventory of the PFA class repos (GitHub + local).
# Usage: bash tools/pfa-repos.sh
set -u
ROOT="$HOME/Desktop"

echo "=== GitHub (account: ikao1) ==="
if command -v gh >/dev/null 2>&1; then
  gh repo list ikao1 --limit 100 2>/dev/null || echo "gh failed (run: gh auth login)"
else
  echo "gh not installed"
fi

echo
echo "=== Local folders under $ROOT (pfa* and Midterm*) ==="
for d in "$ROOT"/pfa* "$ROOT"/Midterm-Proposal; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  if git -C "$d" rev-parse --git-dir >/dev/null 2>&1; then
    remote=$(git -C "$d" remote get-url origin 2>/dev/null || echo "-")
    dirty=$(git -C "$d" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    printf "%-22s git   origin=%s   uncommitted=%s\n" "$name" "$remote" "$dirty"
  else
    printf "%-22s no-git\n" "$name"
  fi
done
