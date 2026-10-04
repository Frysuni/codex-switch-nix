#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

repo="${1:-Frysuni/codex-switch-nix}"
visibility="${VISIBILITY:-public}"

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "GitHub CLI (gh) is required" >&2; exit 1; }
command -v nix >/dev/null 2>&1 || { echo "Nix is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required" >&2; exit 1; }

gh auth status >/dev/null

if [ ! -d .git ]; then
  git init -b main
fi

if [ "$(git branch --show-current)" != main ]; then
  echo "Switch to main before publishing." >&2
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  origin="$(git remote get-url origin)"
  case "$origin" in
    "https://github.com/${repo}.git"|"https://github.com/${repo}"|"git@github.com:${repo}.git") ;;
    *) echo "Origin points to a different repository: $origin" >&2; exit 1 ;;
  esac
fi

git add flake.nix package.nix sources.json README.md LICENSE .gitignore bootstrap.sh scripts tests .github
nix flake lock
git add flake.lock
python3 -m unittest discover -s tests -v
python3 scripts/verify.py
./scripts/check.sh
if ! git diff --cached --quiet; then
  git -c user.name="Frysuni" -c user.email="Frysuni@users.noreply.github.com" \
    commit -m "Initial Nix flake for codex-switch"
fi

if gh repo view "$repo" >/dev/null 2>&1; then
  echo "Repository $repo already exists."
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/${repo}.git"
  fi
  git push -u origin main
else
  gh repo create "$repo" "--$visibility" --source=. --remote=origin --push \
    --description "Self-updating Nix flake for xjoker/codex-switch using official release binaries"
fi

echo
printf 'Published: https://github.com/%s\n' "$repo"
echo "GitHub Actions will now check upstream releases every 4 hours and nixpkgs weekly."
