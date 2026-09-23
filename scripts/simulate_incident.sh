#!/usr/bin/env sh
set -eu

project_name=${1:-inventory-staging}
prometheus_url=${2:-http://127.0.0.1:9090}
compose_file=deploy/docker-compose.staging.yml

restore_service() {
  docker compose --project-name "$project_name" -f "$compose_file" start inventory-api >/dev/null
}
trap restore_service EXIT INT TERM

docker compose --project-name "$project_name" -f "$compose_file" stop inventory-api >/dev/null

attempt=1
while [ "$attempt" -le 12 ]; do
  alerts=$(curl --fail --silent --show-error "$prometheus_url/api/v1/alerts")
  if printf '%s\n' "$alerts" | grep -q 'InventoryApiDown'; then
    printf 'Incident simulation passed: InventoryApiDown fired after %s checks.\n' "$attempt"
    exit 0
  fi
  sleep 5
  attempt=$((attempt + 1))
done

printf 'InventoryApiDown did not fire within 60 seconds.\n' >&2
exit 1

