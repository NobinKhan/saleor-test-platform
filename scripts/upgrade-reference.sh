#!/usr/bin/env bash
# Upgrade golden reference corpus for a new Saleor version.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
COMPOSE=(docker compose -f "${ROOT}/docker-compose.yml")

if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <saleor-version>"
  echo "Example: $0 3.24.0"
  exit 1
fi

echo "==> Saleor reference upgrade: ${VERSION}"
echo ""
echo "1. Pin docker-compose.yml:"
echo "   ghcr.io/saleor/saleor:${VERSION}"
echo ""
read -r -p "Have you updated docker-compose.yml? [y/N] " confirm
if [[ "${confirm,,}" != "y" ]]; then
  echo "Aborting — update docker-compose.yml first, then re-run."
  exit 1
fi

cd "$ROOT"
just fresh
just corpus-diff || true
just patch-corpus --apply-diff || just record-reference
"${COMPOSE[@]}" exec harness-backend \
  python -m app.scripts.migrate_semantic_profiles --version "$VERSION"
just verify-corpus --min-probes 400 --version "$VERSION"
just baseline

echo ""
echo "==> Done. Update env:"
echo "   GOLDEN_CORPUS_VERSION=${VERSION}"
echo "   REFERENCE_BASELINE_VERSION=<dashboard tag when available>"
echo "Commit reference/corpora/saleor-${VERSION}/ and registry.json"
