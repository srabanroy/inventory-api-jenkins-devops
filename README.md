# Inventory API Jenkins DevOps Pipeline

This project implements the seven assessed Jenkins stages for SIT223/SIT753 Task 7.3HD: Build, Test, Code Quality, Security, Deploy, Release, and Monitoring.

The application is a small Flask inventory service with a responsive browser dashboard, API-key authentication, SQLite persistence, CRUD endpoints, health checks, and Prometheus metrics. Its scope is intentionally compact so the pipeline evidence remains easy to explain in a ten-minute demonstration.

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

Open `http://127.0.0.1:8000` and connect with the development key
`change-this-local-key`. The dashboard can list, search, create, edit, and delete inventory
items. It uses plain HTML, CSS, and JavaScript, so it adds no frontend build dependency.

Example request:

```bash
curl -H 'X-API-Key: change-this-local-key' http://127.0.0.1:8000/api/items
```

## Container deployment

Start staging:

```bash
docker build -t inventory-api:local .
IMAGE_TAG=local docker compose -f deploy/docker-compose.staging.yml up -d
./scripts/smoke_test.sh http://127.0.0.1:8081 "$INVENTORY_API_KEY" local
```

The Jenkins pipeline deploys production on `http://127.0.0.1:8082`, then starts a separate
monitoring stack. Prometheus is exposed at `http://127.0.0.1:9090` and Alertmanager at
`http://127.0.0.1:9093`. Prometheus monitors production, while the local team-webhook receiver logs
firing and resolved notifications so alert delivery is demonstrable without an external account.

## Jenkins setup

1. Clone this GitHub repository and confirm that `main` contains `Jenkinsfile`.
2. Ensure the Jenkins agent has Python 3.11 or later, Docker, Docker Compose, Git, and `curl`.
3. In **Manage Jenkins → Credentials**, create a Secret text credential with ID
   `inventory-api-key`. This one masked value is used by staging, production and smoke tests.
4. Create a **Pipeline from SCM** job, select Git, and enter the public GitHub repository URL.
5. Set the branch to `*/main` and the script path to `Jenkinsfile`.
6. Save and choose **Build Now**. SCM polling also checks for changes every five minutes.
7. The default incident test stops production briefly, proves that `InventoryApiDown` fires,
   verifies Alertmanager delivery, restores production and confirms the resolved notification.

The release stage runs only for `main`. It tags the verified image with the version in `VERSION`,
creates `release-manifest.json`, and deploys production on port 8082. Set
`RUN_ROLLBACK_TEST=true` with a previously built `ROLLBACK_VERSION` to deploy that immutable image,
run full smoke checks, and restore the current release. The resulting evidence is archived.

## Project structure

```text
src/inventory_api/           Application, database, templates, and static frontend assets
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

## Technical validation evidence

- `7.3HD_Inventory_DevOps_Execution.ipynb`: locally executed, commented validation notebook.
- `evidence/`: the delivery architecture and authentic successful Jenkins build #6 capture.
