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
        booleanParam(
            name: 'RUN_ROLLBACK_TEST',
            defaultValue: false,
            description: 'Temporarily deploy ROLLBACK_VERSION, verify it, then restore the current release'
        )
        string(
            name: 'ROLLBACK_VERSION',
            defaultValue: '1.1.0',
            description: 'Previously built semantic version used by the optional rollback verification'
        )
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        VENV = '.venv'
        IMAGE_REPOSITORY = 'inventory-api'
        IMAGE_TAG = "${BUILD_NUMBER}"
        STAGING_PROJECT = 'inventory-staging'
        PRODUCTION_PROJECT = 'inventory-production'
        MONITORING_PROJECT = 'inventory-monitoring'
        STAGING_URL = 'http://127.0.0.1:8081'
        PRODUCTION_URL = 'http://127.0.0.1:8082'
        PROMETHEUS_URL = 'http://127.0.0.1:9090'
        ALERTMANAGER_URL = 'http://127.0.0.1:9093'
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
                    def detectedBranch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
                    env.SOURCE_BRANCH = detectedBranch.replaceFirst(/^origin\//, '')
                    if (!env.SOURCE_BRANCH || env.SOURCE_BRANCH == 'HEAD') {
                        env.SOURCE_BRANCH = sh(
                            script: 'git branch --show-current',
                            returnStdout: true
                        ).trim()
                    }
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
                    "$VENV/bin/python" -m pip freeze > resolved-dependencies.txt
                    "$VENV/bin/python" -m build --wheel --no-isolation
                    docker build \
                        --label "org.opencontainers.image.revision=$GIT_COMMIT" \
                        --label "org.opencontainers.image.version=$BUILD_NUMBER" \
                        -t "$IMAGE_REPOSITORY:$IMAGE_TAG" .
                    docker image inspect "$IMAGE_REPOSITORY:$IMAGE_TAG" > image-metadata.json
                '''
                archiveArtifacts artifacts: 'dist/*.whl,image-metadata.json,resolved-dependencies.txt', fingerprint: true
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
                    "$VENV/bin/ruff" check src tests scripts monitoring --output-format=full
                    "$VENV/bin/ruff" format --check src tests scripts monitoring
                '''
            }
        }

        stage('Security') {
            steps {
                sh '''
                    set -eu
                    "$VENV/bin/bandit" -q -r src scripts monitoring -ll -f json -o bandit-report.json
                    "$VENV/bin/pip-audit" -r requirements.txt --format=json --output=pip-audit-report.json
                '''
                archiveArtifacts artifacts: '*-report.json', fingerprint: true
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([string(credentialsId: 'inventory-api-key', variable: 'INVENTORY_API_KEY')]) {
                    sh '''
                        set -eu
                        IMAGE_REPOSITORY="$IMAGE_REPOSITORY" IMAGE_TAG="$IMAGE_TAG" \
                        INVENTORY_API_KEY="$INVENTORY_API_KEY" \
                        docker compose --project-name "$STAGING_PROJECT" \
                            -f deploy/docker-compose.staging.yml up -d --wait
                        ./scripts/smoke_test.sh "$STAGING_URL" "$INVENTORY_API_KEY" "$IMAGE_TAG"
                    '''
                }
            }
        }

        stage('Release') {
            when {
                expression {
                    return env.SOURCE_BRANCH == 'main'
                }
            }
            steps {
                withCredentials([string(credentialsId: 'inventory-api-key', variable: 'INVENTORY_API_KEY')]) {
                    sh '''
                        set -eu
                        APP_VERSION=$(tr -d '[:space:]' < VERSION)
                        "$VENV/bin/python" scripts/create_release_manifest.py \
                            --version "$APP_VERSION" \
                            --build-number "$BUILD_NUMBER" \
                            --commit "$GIT_COMMIT" \
                            --image "$IMAGE_REPOSITORY:$APP_VERSION"
                        docker tag "$IMAGE_REPOSITORY:$IMAGE_TAG" "$IMAGE_REPOSITORY:$APP_VERSION"
                        IMAGE_REPOSITORY="$IMAGE_REPOSITORY" APP_VERSION="$APP_VERSION" \
                        INVENTORY_API_KEY="$INVENTORY_API_KEY" \
                        docker compose --project-name "$PRODUCTION_PROJECT" \
                            -f deploy/docker-compose.production.yml up -d --wait
                        ./scripts/smoke_test.sh "$PRODUCTION_URL" "$INVENTORY_API_KEY" "$APP_VERSION"
                    '''
                    script {
                        if (params.RUN_ROLLBACK_TEST) {
                            sh '''
                                set -eu
                                APP_VERSION=$(tr -d '[:space:]' < VERSION)
                                ./scripts/rollback.sh "$ROLLBACK_VERSION" "$PRODUCTION_URL" "$INVENTORY_API_KEY"
                                IMAGE_REPOSITORY="$IMAGE_REPOSITORY" APP_VERSION="$APP_VERSION" \
                                INVENTORY_API_KEY="$INVENTORY_API_KEY" \
                                docker compose --project-name "$PRODUCTION_PROJECT" \
                                    -f deploy/docker-compose.production.yml up -d --wait
                                ./scripts/smoke_test.sh "$PRODUCTION_URL" "$INVENTORY_API_KEY" "$APP_VERSION"
                                printf 'Current release restored after rollback verification: %s\n' "$APP_VERSION" \
                                    >> rollback-evidence.txt
                            '''
                        }
                    }
                }
                archiveArtifacts artifacts: 'release-manifest.json', fingerprint: true
                archiveArtifacts artifacts: 'rollback-evidence.txt', allowEmptyArchive: true, fingerprint: true
            }
        }

        stage('Monitoring') {
            steps {
                sh '''
                    set -eu
                    docker compose --project-name "$MONITORING_PROJECT" \
                        -f deploy/docker-compose.monitoring.yml up -d --wait
                    docker compose --project-name "$MONITORING_PROJECT" \
                        -f deploy/docker-compose.monitoring.yml exec -T prometheus \
                        promtool check rules /etc/prometheus/alerts.yml
                    ./scripts/monitoring_check.sh "$PROMETHEUS_URL" "$ALERTMANAGER_URL"
                '''
                script {
                    if (params.RUN_INCIDENT_TEST) {
                        sh './scripts/simulate_incident.sh "$PRODUCTION_PROJECT" "$PROMETHEUS_URL" "$MONITORING_PROJECT" "$PRODUCTION_URL"'
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
                docker compose --project-name "$PRODUCTION_PROJECT" \
                    -f deploy/docker-compose.production.yml logs --no-color > production-compose.log 2>&1 || true
                docker compose --project-name "$MONITORING_PROJECT" \
                    -f deploy/docker-compose.monitoring.yml logs --no-color > monitoring-compose.log 2>&1 || true
            '''
            archiveArtifacts artifacts: '*-compose.log', allowEmptyArchive: true
        }
    }
}
