#!/usr/bin/env sh
set -eu

prometheus_url=${1:-http://127.0.0.1:9090}

ready=$(curl --fail --silent --show-error "$prometheus_url/-/ready")
printf '%s\n' "$ready" | grep -q 'Prometheus Server is Ready'

targets=$(curl --fail --silent --show-error "$prometheus_url/api/v1/targets")
printf '%s\n' "$targets" | grep -q 'inventory-api'
printf '%s\n' "$targets" | grep -q '"health":"up"'

rules=$(curl --fail --silent --show-error "$prometheus_url/api/v1/rules")
printf '%s\n' "$rules" | grep -q 'InventoryApiDown'
printf '%s\n' "$rules" | grep -q 'InventoryApiHighErrorRate'

printf 'Monitoring checks passed for %s\n' "$prometheus_url"

