# Inventory API Jenkins DevOps Pipeline

This project implements the seven assessed Jenkins stages for SIT223/SIT753 Task 7.3HD: Build, Test, Code Quality, Security, Deploy, Release, and Monitoring.

The application is a small Flask inventory service with API-key authentication, SQLite persistence, CRUD endpoints, health checks, and Prometheus metrics. Its scope is intentionally compact so the pipeline evidence remains easy to explain in a ten-minute demonstration.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
pytest -q --cov=inventory_api --cov-report=term-missing --cov-fail-under=90
ruff check src tests
bandit -q -r src -ll
python -m build --wheel --no-isolation
```

Start the API locally:

```bash
export INVENTORY_API_KEY=change-this-local-key
flask --app inventory_api:create_app run --host 127.0.0.1 --port 8000
```

Example request:

```bash
curl -H 'X-API-Key: change-this-local-key' http://127.0.0.1:8000/api/items
```

## Container deployment

Start staging and its monitoring stack:

```bash
docker build -t inventory-api:local .
IMAGE_TAG=local docker compose -f deploy/docker-compose.staging.yml up -d
./scripts/smoke_test.sh http://127.0.0.1:8081
```

Prometheus is exposed at `http://127.0.0.1:9090` and Alertmanager at `http://127.0.0.1:9093`. The local alert sink logs received alerts so the monitoring stage is demonstrable without an external account.

## Jenkins setup

1. Push this directory to a Git repository.
2. In Jenkins, create a **Pipeline from SCM** job and point it to the repository.
3. Set the script path to `Jenkinsfile`.
4. Ensure the Jenkins agent has Python 3.11 or later, Docker, and Docker Compose.
5. Run the pipeline. The default incident-test parameter stops the staging service briefly, verifies that Prometheus fires `InventoryApiDown`, and restores the service.

The release stage runs on the `main` branch and in a local single-branch Jenkins job. It tags the verified image with the version in `VERSION`, creates `release-manifest.json`, and deploys the production Compose definition on port 8082. The demonstration pipeline generates an ephemeral API key for each deployment; use a Jenkins credential and a registry credential before publishing outside the local host.

## Project structure

```text
src/inventory_api/           Application and database code
tests/unit/                  Focused validation tests
tests/integration/           API and persistence tests
deploy/                      Staging and production Compose definitions
monitoring/                  Prometheus, Alertmanager, and alert rules
scripts/                     Smoke, release, and incident-test automation
Jenkinsfile                  Seven-stage declarative pipeline
```

## Security decisions

- SQL statements use parameters rather than string interpolation.
- Production startup fails when `INVENTORY_API_KEY` is absent.
- The container runs as an unprivileged user.
- Bandit scans application code and `pip-audit` checks third-party packages.
- Secrets are supplied through environment variables and are not committed.
