#!/usr/bin/env bash
# ==================================================================
# update-skills.sh — bump des skills depuis le repo central
#
# À exécuter depuis la racine du projet consommateur :
#
#   ./.agents/update-skills.sh                  # DERNIÈRE version publiée (résolue depuis le remote)
#   SKILLS_TAG=v1.3.0 ./.agents/update-skills.sh   # pin strict sur une version
#   SKILLS_TAG=v1 ./.agents/update-skills.sh       # alias mobile MAJOR (suit les MINOR)
#   PUSH=yes ./.agents/update-skills.sh         # commit + push auto
#   DRY_RUN=yes ./.agents/update-skills.sh      # rien à git, juste sync
#
# Par défaut, le script résout le **dernier tag de version** (vX.Y.Z le plus
# élevé) publié sur le remote — il ne se fie pas à l'alias mobile `v1`, qui
# peut être stale si la release ne l'a pas re-poussé.
#
# Le script :
#   1) résout la dernière version (sauf SKILLS_TAG explicite)
#   2) clone le repo central à ce tag dans un tmp
#   3) synchronise .agents/skills/ (suppression des skills retirés inclus)
#   4) met à jour .agents/update-skills.sh lui-même
#   5) écrit .agents/.skills-version
#   6) git add .agents/ + commit "chore(skills): bump to <tag>"
#   7) (si PUSH=yes) git push
# ==================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────
SKILLS_REPO_URL="${SKILLS_REPO_URL:-git@gitlab.tools.thesmartcrew.com:croo-dev/code-agent-skills-v1.0.git}"
SKILLS_REPO_HTTPS="${SKILLS_REPO_HTTPS:-https://gitlab.tools.thesmartcrew.com/croo-dev/code-agent-skills-v1.0.git}"
# SKILLS_TAG vide = résoudre la dernière version depuis le remote (voir plus bas).
SKILLS_TAG="${SKILLS_TAG:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
PUSH="${PUSH:-no}"
DRY_RUN="${DRY_RUN:-no}"

# ── Détection : on est bien à la racine du projet ─────────────────
if [ ! -d "$PROJECT_ROOT/.agents" ]; then
    echo "ERROR: $PROJECT_ROOT/.agents/ absent. Lance update-skills.sh depuis la racine du projet."
    echo "       Pour une première installation, utilise scripts/install.sh du repo central."
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "ERROR: $PROJECT_ROOT n'est pas un dépôt Git. update-skills.sh suppose un dépôt versionné."
    exit 1
fi

# ── Résolution de la dernière version publiée ─────────────────────
# Si SKILLS_TAG n'est pas fixé explicitement, on interroge le remote et on
# prend le tag de version le plus élevé (vX.Y.Z), en ignorant les alias
# mobiles vX / vX.Y. Évite de rester bloqué sur un alias `v1` stale.
resolve_latest_tag() {
    local url="$1"
    git ls-remote --tags --refs "$url" 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
        | sort -V \
        | tail -1
}

if [ -z "$SKILLS_TAG" ]; then
    echo "[0/7] Résolution de la dernière version publiée…"
    SKILLS_TAG="$(resolve_latest_tag "$SKILLS_REPO_URL")"
    [ -n "$SKILLS_TAG" ] || SKILLS_TAG="$(resolve_latest_tag "$SKILLS_REPO_HTTPS")"
    if [ -z "$SKILLS_TAG" ]; then
        echo "ERROR: impossible de résoudre la dernière version depuis le remote." >&2
        echo "Fixe une version : SKILLS_TAG=v1.7.0 ./.agents/update-skills.sh" >&2
        exit 2
    fi
    echo "       → dernière version : $SKILLS_TAG"
fi

echo "════════════════════════════════════════════════════════════════"
echo "  update-skills"
echo "════════════════════════════════════════════════════════════════"
echo "  Projet     : $PROJECT_ROOT"
echo "  Repo       : $SKILLS_REPO_URL"
echo "  Tag        : $SKILLS_TAG"
echo "  Push auto  : $PUSH"
echo "  Dry-run    : $DRY_RUN"
echo "════════════════════════════════════════════════════════════════"

# ── Version actuelle ──────────────────────────────────────────────
CURRENT_VERSION=$(cat "$PROJECT_ROOT/.agents/.skills-version" 2>/dev/null || echo "unknown")
echo ""
echo "[1/6] Version actuelle des skills : $CURRENT_VERSION"

# ── Clone du repo central ─────────────────────────────────────────
TMPDIR=$(mktemp -d -t skills-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

echo ""
echo "[2/6] Clone de $SKILLS_REPO_URL @ $SKILLS_TAG"

# Essai SSH d'abord, fallback HTTPS
if git clone --depth 1 --branch "$SKILLS_TAG" "$SKILLS_REPO_URL" "$TMPDIR/skills" 2>/dev/null; then
    :
elif git clone --depth 1 --branch "$SKILLS_TAG" "$SKILLS_REPO_HTTPS" "$TMPDIR/skills" 2>/dev/null; then
    :
else
    echo "ERROR: clone échoué (ni SSH ni HTTPS)."
    echo "Vérifie que le tag '$SKILLS_TAG' existe sur $SKILLS_REPO_URL"
    exit 2
fi

NEW_VERSION=$(cd "$TMPDIR/skills" && git describe --tags --always 2>/dev/null || echo "$SKILLS_TAG")
echo "  ✅ cloné — version : $NEW_VERSION"

# ── Synchronisation .agents/skills/ ───────────────────────────────
echo ""
echo "[3/6] Synchronisation .agents/skills/"

SRC_SKILLS="$TMPDIR/skills/.agents/skills"
DST_SKILLS="$PROJECT_ROOT/.agents/skills"

if [ ! -d "$SRC_SKILLS" ]; then
    echo "ERROR: $SRC_SKILLS absent dans le repo central. Tag '$SKILLS_TAG' incompatible ?"
    exit 3
fi

# Skills ajoutés / modifiés
added=0
modified=0
for d in "$SRC_SKILLS/"dx_*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    if [ ! -d "$DST_SKILLS/$name" ]; then
        cp -r "$d" "$DST_SKILLS/"
        added=$((added+1))
    elif ! diff -rq "$d" "$DST_SKILLS/$name" >/dev/null 2>&1; then
        rm -rf "${DST_SKILLS:?}/$name"
        cp -r "$d" "$DST_SKILLS/"
        modified=$((modified+1))
    fi
done

# Skills retirés (présents en local, absents dans le repo central)
removed=0
if [ -d "$DST_SKILLS" ]; then
    for d in "$DST_SKILLS/"dx_*/; do
        [ -d "$d" ] || continue
        name=$(basename "$d")
        if [ ! -d "$SRC_SKILLS/$name" ]; then
            rm -rf "$d"
            removed=$((removed+1))
        fi
    done
fi

echo "  Ajoutés   : $added"
echo "  Modifiés  : $modified"
echo "  Retirés   : $removed"

# ── Mise à jour de update-skills.sh lui-même ──────────────────────
echo ""
echo "[4/6] Mise à jour de .agents/update-skills.sh"

if [ -f "$TMPDIR/skills/scripts/update-skills.sh" ]; then
    if ! cmp -s "$TMPDIR/skills/scripts/update-skills.sh" "$PROJECT_ROOT/.agents/update-skills.sh"; then
        cp "$TMPDIR/skills/scripts/update-skills.sh" "$PROJECT_ROOT/.agents/update-skills.sh"
        chmod +x "$PROJECT_ROOT/.agents/update-skills.sh"
        echo "  ✅ update-skills.sh mis à jour"
    else
        echo "  ↪️  update-skills.sh déjà à jour"
    fi
fi

# ── Version trackée ───────────────────────────────────────────────
echo "$NEW_VERSION" > "$PROJECT_ROOT/.agents/.skills-version"

# ── Audit : skills modifiés à la main détectés ────────────────────
echo ""
echo "[5/6] Audit : modifications locales"

cd "$PROJECT_ROOT"
local_changes=$(git diff --name-only .agents/skills/ 2>/dev/null | grep -v "^.agents/.skills-version$" || true)
if [ -n "$local_changes" ]; then
    n=$(echo "$local_changes" | wc -l)
    echo "  ⚠️  $n fichier(s) modifié(s) localement dans .agents/skills/ avant ce bump :"
    echo "$local_changes" | sed 's|^|     |' | head -10
    echo ""
    echo "  Rappel : modifier un SKILL.md localement est interdit (§ 10.4)."
    echo "  Toute évolution passe par PR sur croo-dev/code-agent-skills-v1.0."
fi

# ── Commit & push ─────────────────────────────────────────────────
echo ""
echo "[6/6] Git commit"

if [ "$DRY_RUN" = "yes" ]; then
    echo "  DRY_RUN=yes → pas de commit. Lance \`git status\` pour voir le diff."
    exit 0
fi

git add .agents/

if git diff --cached --quiet; then
    echo "  Aucun changement à commiter (skills déjà au tag $NEW_VERSION)."
    exit 0
fi

MSG="chore(skills): bump to $NEW_VERSION"
[ "$CURRENT_VERSION" != "unknown" ] && [ "$CURRENT_VERSION" != "$NEW_VERSION" ] \
    && MSG="$MSG (was $CURRENT_VERSION)"

git -c user.email="${GIT_AUTHOR_EMAIL:-update-skills@local}" \
    -c user.name="${GIT_AUTHOR_NAME:-update-skills}" \
    commit -m "$MSG"

echo "  ✅ Commit créé : $MSG"

if [ "$PUSH" = "yes" ]; then
    echo ""
    echo "  git push..."
    git push
    echo "  ✅ pushed"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ update-skills OK — $CURRENT_VERSION → $NEW_VERSION"
echo "════════════════════════════════════════════════════════════════"
