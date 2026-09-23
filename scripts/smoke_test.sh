#!/usr/bin/env sh
set -eu

base_url=${1:-http://127.0.0.1:8000}

health=$(curl --fail --silent --show-error "$base_url/health")
printf '%s\n' "$health" | grep -q '"status":"ok"'

metrics=$(curl --fail --silent --show-error "$base_url/metrics")
printf '%s\n' "$metrics" | grep -q 'inventory_readiness 1.0'

printf 'Smoke test passed for %s\n' "$base_url"

