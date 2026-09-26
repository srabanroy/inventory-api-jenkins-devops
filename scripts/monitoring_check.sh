#!/usr/bin/env sh
set -eu

prometheus_url=${1:-http://127.0.0.1:9090}
alertmanager_url=${2:-http://127.0.0.1:9093}

attempt=1
while [ "$attempt" -le 12 ]; do
  ready=$(curl --fail --silent --show-error "$prometheus_url/-/ready" 2>/dev/null || true)
  targets=$(curl --fail --silent --show-error "$prometheus_url/api/v1/targets" 2>/dev/null || true)
  rules=$(curl --fail --silent --show-error "$prometheus_url/api/v1/rules" 2>/dev/null || true)
  alertmanager_ready=$(curl --fail --silent --show-error "$alertmanager_url/-/ready" 2>/dev/null || true)

  if printf '%s\n' "$ready" | grep -q 'Prometheus Server is Ready' && \
     printf '%s\n' "$targets" | grep -q 'inventory-api-production' && \
     printf '%s\n' "$targets" | grep -q '"health":"up"' && \
     printf '%s\n' "$rules" | grep -q 'InventoryApiDown' && \
     printf '%s\n' "$rules" | grep -q 'InventoryApiHighErrorRate' && \
     printf '%s\n' "$rules" | grep -q 'InventoryDatabaseNotReady' && \
     printf '%s\n' "$alertmanager_ready" | grep -q 'OK'; then
    printf 'Production target, three rules and Alertmanager checks passed after %s attempt(s).\n' "$attempt"
    exit 0
  fi

  sleep 5
  attempt=$((attempt + 1))
done

printf 'Monitoring stack did not become fully ready within 60 seconds.\n' >&2
exit 1
