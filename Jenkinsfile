pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    parameters {
        booleanParam(
            name: 'RUN_INCIDENT_TEST',
            defaultValue: true,
            description: 'Stop staging briefly and verify that Prometheus fires InventoryApiDown'
        )
    }

    environment {
        VENV = '.venv'
        IMAGE_REPOSITORY = 'inventory-api'
        IMAGE_TAG = "${BUILD_NUMBER}"
        STAGING_PROJECT = 'inventory-staging'
        PRODUCTION_PROJECT = 'inventory-production'
        STAGING_URL = 'http://127.0.0.1:8081'
        PROMETHEUS_URL = 'http://127.0.0.1:9090'
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                script {
                    def repositoryUrl = scm.userRemoteConfigs[0].url
                    if (repositoryUrl.startsWith('file:')) {
                        withEnv(["REPOSITORY_URL=${repositoryUrl}"]) {
                            sh 'git clone --branch main "$REPOSITORY_URL" .'
                        }
                    } else {
                        checkout scm
                    }
                    env.GIT_COMMIT = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                    env.BRANCH_NAME = sh(
                        script: 'git branch --show-current',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Build') {
            steps {
                sh '''
                    set -eu
                    python3 -m venv "$VENV"
                    "$VENV/bin/python" -m pip install --upgrade pip
                    "$VENV/bin/python" -m pip install -r requirements-dev.txt
                    "$VENV/bin/python" -m pip install -e .
                    "$VENV/bin/python" -m build --wheel --no-isolation
                    docker build \
                        --label "org.opencontainers.image.revision=$GIT_COMMIT" \
                        --label "org.opencontainers.image.version=$BUILD_NUMBER" \
                        -t "$IMAGE_REPOSITORY:$IMAGE_TAG" .
                '''
                archiveArtifacts artifacts: 'dist/*.whl', fingerprint: true
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -eu
                    "$VENV/bin/pytest" -q \
                        --junitxml=test-results.xml \
                        --cov=inventory_api \
                        --cov-branch \
                        --cov-report=term-missing \
                        --cov-report=xml:coverage.xml \
                        --cov-fail-under=90
                '''
            }
            post {
                always {
                    junit allowEmptyResults: false, testResults: 'test-results.xml'
                    archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Code Quality') {
            steps {
                sh '''
                    set -eu
                    "$VENV/bin/ruff" check src tests --output-format=full
                    "$VENV/bin/ruff" format --check src tests
                '''
            }
        }

        stage('Security') {
            steps {
                sh '''
                    set -eu
                    "$VENV/bin/bandit" -q -r src -ll -f json -o bandit-report.json
                    "$VENV/bin/pip-audit" -r requirements.txt --format=json --output=pip-audit-report.json
                '''
                archiveArtifacts artifacts: '*-report.json', fingerprint: true
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    set -eu
                    DEMO_KEY=$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')
                    IMAGE_REPOSITORY="$IMAGE_REPOSITORY" IMAGE_TAG="$IMAGE_TAG" \
                    INVENTORY_API_KEY="$DEMO_KEY" \
                    docker compose --project-name "$STAGING_PROJECT" \
                        -f deploy/docker-compose.staging.yml up -d --wait
                    ./scripts/smoke_test.sh "$STAGING_URL"
                '''
            }
        }

        stage('Release') {
            when {
                expression {
                    return env.BRANCH_NAME == null || env.BRANCH_NAME == 'main'
                }
            }
            steps {
                sh '''
                    set -eu
                    APP_VERSION=$(tr -d '[:space:]' < VERSION)
                    "$VENV/bin/python" scripts/create_release_manifest.py \
                        --version "$APP_VERSION" \
                        --build-number "$BUILD_NUMBER" \
                        --commit "$GIT_COMMIT" \
                        --image "$IMAGE_REPOSITORY:$APP_VERSION"
                    docker tag "$IMAGE_REPOSITORY:$IMAGE_TAG" "$IMAGE_REPOSITORY:$APP_VERSION"
                    DEMO_KEY=$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')
                    IMAGE_REPOSITORY="$IMAGE_REPOSITORY" APP_VERSION="$APP_VERSION" \
                    INVENTORY_API_KEY="$DEMO_KEY" \
                    docker compose --project-name "$PRODUCTION_PROJECT" \
                        -f deploy/docker-compose.production.yml up -d --wait
                    ./scripts/smoke_test.sh http://127.0.0.1:8082
                '''
                archiveArtifacts artifacts: 'release-manifest.json', fingerprint: true
            }
        }

        stage('Monitoring') {
            steps {
                sh '''
                    set -eu
                    docker compose --project-name "$STAGING_PROJECT" \
                        -f deploy/docker-compose.staging.yml exec -T prometheus \
                        promtool check rules /etc/prometheus/alerts.yml
                    ./scripts/monitoring_check.sh "$PROMETHEUS_URL"
                '''
                script {
                    if (params.RUN_INCIDENT_TEST) {
                        sh './scripts/simulate_incident.sh "$STAGING_PROJECT" "$PROMETHEUS_URL"'
                    }
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker compose --project-name "$STAGING_PROJECT" \
                    -f deploy/docker-compose.staging.yml logs --no-color > staging-compose.log 2>&1 || true
            '''
            archiveArtifacts artifacts: 'staging-compose.log', allowEmptyArchive: true
        }
    }
}
