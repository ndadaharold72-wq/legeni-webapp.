pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    environment {
        IMAGE = 'ndada/legeni-webapp'
        KUBECONFIG = ''
        CI_NETWORK = "legeni-ci-${BUILD_NUMBER}"
        TEST_CONTAINER = "legeni-ci-app-${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout et version') {
            steps {
                checkout scm
                script {
                    env.APP_VERSION = readFile('VERSION').trim()
                    if (!(env.APP_VERSION ==~ /[0-9]+\.[0-9]+\.[0-9]+/)) {
                        error('VERSION doit respecter le format X.Y.Z')
                    }
                    env.IMAGE_TAG = "${env.APP_VERSION}-${env.BUILD_NUMBER}"
                    echo "Version de release : ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Tests et build de validation') {
            steps {
                sh '''
                    set -eu
                    docker build --target test \
                      --build-arg APP_VERSION="$IMAGE_TAG" \
                      -t "legeni-webapp-test:${BUILD_NUMBER}" .
                '''
            }
        }

        stage('Contrôle Dockerfile - Hadolint') {
            steps {
                sh '''
                    set -eu
                    docker run --rm -i hadolint/hadolint:v2.12.0 \
                      hadolint - < Dockerfile
                '''
            }
        }

        stage('Build image versionnée') {
            steps {
                sh '''
                    set -eu
                    docker build \
                      --build-arg APP_VERSION="$IMAGE_TAG" \
                      --tag "$IMAGE:$IMAGE_TAG" .
                    docker image inspect "$IMAGE:$IMAGE_TAG" >/dev/null
                '''
            }
        }

        stage('Scan sécurité - Trivy') {
            steps {
                sh '''
                    set -eu
                    docker run --rm \
                      -v /run/docker.sock:/var/run/docker.sock \
                      aquasec/trivy:0.58.2 \
                      image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed \
                      --scanners vuln "$IMAGE:$IMAGE_TAG"
                '''
            }
        }

        stage('Test d’acceptation') {
            steps {
                sh '''
                    set -eu
                    docker network create "$CI_NETWORK"
                    docker run -d --name "$TEST_CONTAINER" \
                      --network "$CI_NETWORK" \
                      -e APP_ENV=ci \
                      "$IMAGE:$IMAGE_TAG"

                    docker run --rm --network "$CI_NETWORK" \
                      curlimages/curl:8.11.1 \
                      -fsS --retry 15 --retry-connrefused --retry-delay 2 \
                      "http://$TEST_CONTAINER:5000/health"

                    docker run --rm --network "$CI_NETWORK" \
                      curlimages/curl:8.11.1 \
                      -fsS "http://$TEST_CONTAINER:5000/api/info" \
                      | grep -F "\\"version\\":\\"$IMAGE_TAG\\""
                '''
            }
        }

        stage('Push Docker Hub') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub',
                    usernameVariable: 'DH_USER',
                    passwordVariable: 'DH_TOKEN'
                )]) {
                    sh '''
                        set +x
                        printf '%s' "$DH_TOKEN" |
                          docker login -u "$DH_USER" --password-stdin
                        docker push "$IMAGE:$IMAGE_TAG"
                        docker logout
                    '''
                }
            }
        }

        stage('Déploiement staging') {
            when { branch 'main' }
            steps {
                withCredentials([
                    file(credentialsId: 'kubeconfig', variable: 'KCFG'),
                    string(credentialsId: 'ansible-vault-pass', variable: 'VAULT_PASS')
                ]) {
                    sh '''
                        set -eu
                        export KUBECONFIG="$KCFG"
                        printf '%s' "$VAULT_PASS" > .vault-pass-ci
                        chmod 600 .vault-pass-ci
                        cd ansible
                        ansible-playbook deploy.yml \
                          --vault-password-file ../.vault-pass-ci \
                          -e target_env=staging \
                          -e app_image="$IMAGE" \
                          -e app_version="$IMAGE_TAG"
                    '''
                }
            }
        }

        stage('Approbation avant production') {
            when { branch 'main' }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    input message: "Staging validé. Déployer ${IMAGE}:${IMAGE_TAG} en production ?",
                          ok: 'Approuver production'
                }
            }
        }

        stage('Déploiement production') {
            when { branch 'main' }
            steps {
                withCredentials([
                    file(credentialsId: 'kubeconfig', variable: 'KCFG'),
                    string(credentialsId: 'ansible-vault-pass', variable: 'VAULT_PASS')
                ]) {
                    sh '''
                        set -eu
                        export KUBECONFIG="$KCFG"
                        printf '%s' "$VAULT_PASS" > .vault-pass-ci
                        chmod 600 .vault-pass-ci
                        cd ansible
                        ansible-playbook deploy.yml \
                          --vault-password-file ../.vault-pass-ci \
                          -e target_env=prod \
                          -e app_image="$IMAGE" \
                          -e app_version="$IMAGE_TAG"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
                docker network rm "$CI_NETWORK" >/dev/null 2>&1 || true
                rm -f .vault-pass-ci
            '''
        }
        success {
            echo 'Pipeline terminé sans erreur.'
        }
        failure {
            echo 'Pipeline en échec : consulter les journaux ; vérifier le rollback Kubernetes.'
        }
    }
}
