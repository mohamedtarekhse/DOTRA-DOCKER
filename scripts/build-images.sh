#!/usr/bin/env bash
set -euo pipefail

# Build all ACUSEEK service images from per-service Dockerfiles.
# Run this ONCE on the server (or before deploying via Coolify).
# Afterwards, reference the prebuilt images in docker-compose.coolify.yml.
#
# Usage:  bash scripts/build-images.sh

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"
PREFIX="acuseek"

build() {
  local svc="$1"
  local ctx="$2"
  local dockerfile="${3:-Dockerfile}"
  local image="${PREFIX}-${svc}:${TAG}"
  echo "==> Building ${image} from ${ctx}/${dockerfile}"
  docker build -t "$image" -f "${REPO}/${ctx}/${dockerfile}" "${REPO}/${ctx}"
}

build api              services/api              Dockerfile
build ai-engine        services/ai-engine        Dockerfile
build lpr-listener     services/lpr-listener     Dockerfile
build stream-processor services/stream-processor Dockerfile
build dashboard        services/dashboard        Dockerfile
build postgres         services/postgres         Dockerfile
build redis            services/redis            Dockerfile
build mosquitto        services/mosquitto        Dockerfile
build nginx            services/nginx            Dockerfile

echo ""
echo "Done. All images tagged as ${PREFIX}-*:${TAG}."
echo "celery-worker shares the api image (same Dockerfile)."
echo "Deploy with:  docker compose -f docker-compose.coolify.yml up -d"
