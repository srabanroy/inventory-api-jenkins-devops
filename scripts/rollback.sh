#!/usr/bin/env sh
set -eu

target_version=${1:?Usage: rollback.sh VERSION BASE_URL API_KEY}
base_url=${2:-http://127.0.0.1:8082}
api_key=${3:?An API key is required}
image_repository=${IMAGE_REPOSITORY:-inventory-api}
project_name=${PRODUCTION_PROJECT:-inventory-production}
compose_file=deploy/docker-compose.production.yml

# Refuse an unavailable target instead of silently rebuilding a different artefact.
docker image inspect "$image_repository:$target_version" >/dev/null

IMAGE_REPOSITORY="$image_repository" \
APP_VERSION="$target_version" \
INVENTORY_API_KEY="$api_key" \
docker compose --project-name "$project_name" -f "$compose_file" up -d --wait

./scripts/smoke_test.sh "$base_url" "$api_key" "$target_version"
printf 'Rollback deployment verified: %s:%s\n' "$image_repository" "$target_version" | tee rollback-evidence.txt
