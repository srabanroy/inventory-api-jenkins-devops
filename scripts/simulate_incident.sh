#!/usr/bin/env sh
set -eu

project_name=${1:-inventory-production}
prometheus_url=${2:-http://127.0.0.1:9090}
monitoring_project=${3:-inventory-monitoring}
production_url=${4:-http://127.0.0.1:8082}
compose_file=deploy/docker-compose.production.yml
monitoring_file=deploy/docker-compose.monitoring.yml
restored=false
incident_started=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Compose resolves required variables even for start/stop operations. This placeholder is never
# applied to a container because the script does not create or recreate the production service.
export INVENTORY_API_KEY=${INVENTORY_API_KEY:-incident-control-only}

restore_service() {
  if [ "$restored" = false ]; then
    docker compose --project-name "$project_name" -f "$compose_file" start inventory-api >/dev/null
    restored=true
  fi
}
trap restore_service EXIT INT TERM

docker compose --project-name "$project_name" -f "$compose_file" stop inventory-api >/dev/null

attempt=1
while [ "$attempt" -le 18 ]; do
  alerts=$(curl --fail --silent --show-error "$prometheus_url/api/v1/alerts")
  if printf '%s' "$alerts" | python3 -c '
import json, sys
data = json.load(sys.stdin)
matches = [a for a in data.get("data", {}).get("alerts", []) if a.get("labels", {}).get("alertname") == "InventoryApiDown"]
raise SystemExit(0 if any(a.get("state") == "firing" for a in matches) else 1)
'; then
    printf 'InventoryApiDown reached the firing state after %s checks.\n' "$attempt"
    break
  fi
  sleep 5
  attempt=$((attempt + 1))
done

if [ "$attempt" -gt 18 ]; then
  printf 'InventoryApiDown did not reach the firing state within 90 seconds.\n' >&2
  exit 1
fi

attempt=1
while [ "$attempt" -le 12 ]; do
  sink_logs=$(docker compose --project-name "$monitoring_project" -f "$monitoring_file" \
    logs --since "$incident_started" --no-color alert-sink)
  if printf '%s\n' "$sink_logs" | grep -q 'InventoryApiDown' && \
     printf '%s\n' "$sink_logs" | grep -q '"status": "firing"'; then
    printf 'Alertmanager delivered the firing notification to the team webhook receiver.\n'
    break
  fi
  sleep 5
  attempt=$((attempt + 1))
done

if [ "$attempt" -gt 12 ]; then
  printf 'Alertmanager did not deliver the firing notification within 60 seconds.\n' >&2
  exit 1
fi

restore_service

attempt=1
while [ "$attempt" -le 18 ]; do
  if curl --fail --silent --show-error "$production_url/health" | grep -q '"status":"ok"'; then
    printf 'Production recovered after %s health checks.\n' "$attempt"
    break
  fi
  sleep 5
  attempt=$((attempt + 1))
done

if [ "$attempt" -gt 18 ]; then
  printf 'Production did not recover within 90 seconds.\n' >&2
  exit 1
fi

attempt=1
while [ "$attempt" -le 18 ]; do
  sink_logs=$(docker compose --project-name "$monitoring_project" -f "$monitoring_file" \
    logs --since "$incident_started" --no-color alert-sink)
  if printf '%s\n' "$sink_logs" | grep -q 'InventoryApiDown' && \
     printf '%s\n' "$sink_logs" | grep -q '"status": "resolved"'; then
    printf 'Incident simulation passed: firing, delivery, recovery and resolution verified.\n'
    exit 0
  fi
  sleep 5
  attempt=$((attempt + 1))
done

printf 'The resolved notification was not delivered within 90 seconds.\n' >&2
exit 1
