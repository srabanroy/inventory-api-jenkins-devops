#!/usr/bin/env sh
set -eu

base_url=${1:-http://127.0.0.1:8000}
api_key=${2:-}
expected_version=${3:-}

if [ -z "$api_key" ]; then
  printf 'An API key is required for the deployed CRUD smoke test.\n' >&2
  exit 2
fi

dashboard=$(curl --fail --silent --show-error "$base_url/")
printf '%s\n' "$dashboard" | grep -q 'Inventory workspace'

health=$(curl --fail --silent --show-error "$base_url/health")
printf '%s\n' "$health" | grep -q '"status":"ok"'

metrics=$(curl --fail --silent --show-error "$base_url/metrics")
printf '%s\n' "$metrics" | grep -q 'inventory_readiness 1.0'

if [ -n "$expected_version" ]; then
  version=$(curl --fail --silent --show-error "$base_url/version")
  printf '%s\n' "$version" | grep -q "\"version\":\"$expected_version\""
fi

# Exercise the deployed service end to end rather than checking process health alone.
sku="SMOKE-$(date +%s)-$$"
created=$(curl --fail --silent --show-error \
  -X POST \
  -H "X-API-Key: $api_key" \
  -H 'Content-Type: application/json' \
  -d "{\"sku\":\"$sku\",\"name\":\"Pipeline smoke item\",\"quantity\":2}" \
  "$base_url/api/items")
item_id=$(printf '%s' "$created" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')

listed=$(curl --fail --silent --show-error -H "X-API-Key: $api_key" "$base_url/api/items")
printf '%s\n' "$listed" | grep -q "$sku"

updated=$(curl --fail --silent --show-error \
  -X PUT \
  -H "X-API-Key: $api_key" \
  -H 'Content-Type: application/json' \
  -d "{\"sku\":\"$sku\",\"name\":\"Pipeline smoke item\",\"quantity\":3}" \
  "$base_url/api/items/$item_id")
printf '%s\n' "$updated" | grep -q '"quantity":3'

deleted=$(curl --fail --silent --show-error \
  -X DELETE \
  -H "X-API-Key: $api_key" \
  "$base_url/api/items/$item_id")
printf '%s\n' "$deleted" | grep -q '"status":"deleted"'

printf 'Dashboard, health, metrics, version and CRUD smoke tests passed for %s\n' "$base_url"
