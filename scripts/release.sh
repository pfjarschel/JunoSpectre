#!/usr/bin/env bash
# Bump the project version, commit, tag and (optionally) push.
#
# Usage: scripts/release.sh <patch|minor|major> [-y] [--dry-run] [--no-push]
#
# Reads VERSION (MAJOR.MINOR.PATCH), shows what the bump would do and asks for
# confirmation. On confirmation it writes VERSION, commits, and creates an
# annotated tag "v<version>". It then asks whether to push the branch and the
# tag to "origin".
#
#   -y         answer "yes" to every question (create and push automatically)
#   --dry-run  show the bump information and exit without changing anything
#   --no-push  never push (and don't ask)
set -euo pipefail

usage() {
    echo "Usage: $(basename "$0") <patch|minor|major> [-y] [--dry-run] [--no-push]" >&2
    exit 1
}

BUMP=""
ASSUME_YES=0
DRY_RUN=0
PUSH=1
for arg in "$@"; do
    case "$arg" in
        patch|minor|major) BUMP="$arg" ;;
        -y|--yes) ASSUME_YES=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --no-push) PUSH=0 ;;
        *) usage ;;
    esac
done
[[ -z "$BUMP" ]] && usage

# confirm "question" -> returns 0 for yes. Defaults to "no" on empty input.
confirm() {
    if [[ $ASSUME_YES -eq 1 ]]; then
        echo "$1 [y/N] y (auto)"
        return 0
    fi
    local reply
    read -r -p "$1 [y/N] " reply || return 1
    [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

[[ -f VERSION ]] || { echo "VERSION file not found." >&2; exit 1; }
CURRENT="$(tr -d '[:space:]' < VERSION)"
if ! [[ "$CURRENT" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo "VERSION must look like MAJOR.MINOR.PATCH, got '$CURRENT'." >&2
    exit 1
fi
MAJOR="${BASH_REMATCH[1]}"; MINOR="${BASH_REMATCH[2]}"; PATCH="${BASH_REMATCH[3]}"

case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac
NEW="$MAJOR.$MINOR.$PATCH"
TAG="v$NEW"

BRANCH="$(git branch --show-current)"
[[ -n "$BRANCH" ]] || { echo "Detached HEAD; check out a branch first." >&2; exit 1; }

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    echo "Tag $TAG already exists." >&2
    exit 1
fi

# Refuse to release with uncommitted changes so the tag only contains committed work
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Working tree has uncommitted changes to tracked files; commit or stash them first." >&2
    exit 1
fi

# ---- Bump information -------------------------------------------------------
LAST_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"
if [[ -n "$LAST_TAG" ]]; then
    RANGE="$LAST_TAG..HEAD"
    SINCE="since $LAST_TAG"
else
    RANGE="HEAD"
    SINCE="(no previous tag)"
fi
COMMIT_COUNT="$(git rev-list --count "$RANGE")"

echo "=============================================="
echo " Release summary"
echo "=============================================="
echo " Bump type     : $BUMP"
echo " Version       : $CURRENT -> $NEW"
echo " New tag       : $TAG"
echo " Branch        : $BRANCH"
echo " Remote        : $(git remote get-url origin 2>/dev/null || echo 'none')"
echo " Previous tag  : ${LAST_TAG:-none}"
echo " Commits       : $COMMIT_COUNT $SINCE"
if [[ "$COMMIT_COUNT" -gt 0 ]]; then
    echo "----------------------------------------------"
    git log --oneline --max-count=15 "$RANGE" | sed 's/^/  /'
    if [[ "$COMMIT_COUNT" -gt 15 ]]; then
        echo "  ... and $((COMMIT_COUNT - 15)) more"
    fi
fi
echo "=============================================="

if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] No changes made."
    exit 0
fi

# ---- Create ------------------------------------------------------------------
if ! confirm "Update VERSION to $NEW, commit and create tag $TAG?"; then
    echo "Aborted. Nothing was changed."
    exit 0
fi

printf '%s\n' "$NEW" > VERSION
git add VERSION
git commit -m "Release $TAG"
git tag -a "$TAG" -m "Release $TAG"
echo "Created commit and tag $TAG locally."

# ---- Push --------------------------------------------------------------------
if [[ $PUSH -eq 0 ]]; then
    echo "Not pushing (--no-push). Push later with: git push origin $BRANCH $TAG"
    exit 0
fi

if confirm "Push branch '$BRANCH' and tag $TAG to origin?"; then
    git push origin "$BRANCH"
    git push origin "$TAG"
    echo "Pushed $BRANCH and $TAG to origin."
else
    echo "Not pushed. Push later with: git push origin $BRANCH $TAG"
fi
