# Parcours Jenkins 3.5 à 3.8 – application fil rouge

## Jenkinsfile à sélectionner

| TP | Script Path Jenkins | Fonctionnalités |
|---|---|---|
| 3.5 | `Jenkinsfile.tp35` | Tests, build, test d'acceptance et push Docker Hub |
| 3.6 | `Jenkinsfile.multibranch` | Tags par branche, push limite a `main` |
| 3.7 | `Jenkinsfile.qualite` | Tests paralleles, rapports JUnit/couverture/flake8, gate 100 %, Hadolint et Trivy |
| 3.8 | `Jenkinsfile.cd` | Staging, validation humaine sur `main`, production et rollback smoke-test |

Le `Jenkinsfile` principal du depot est conserve pour le pipeline CI/CD Kubernetes/Ansible. Les quatre fichiers TP se selectionnent individuellement comme Script Path. Le stage de test du Dockerfile impose desormais 100 % de couverture.

## Credentials à créer dans Jenkins

- `dockerhub` : **Username with password** ; le mot de passe est un jeton Docker Hub.
- `redis-password-staging` : **Secret text** avec un mot de passe aléatoire.
- `redis-password-prod` : **Secret text** différent de celui de staging.
- Pour la découverte GitHub multibranch et les statuts de PR, créer un credential GitHub avec les droits nécessaires au dépôt et l'utiliser dans la source GitHub du job.

Ne placez aucun jeton ou mot de passe dans les fichiers du dépôt. Les valeurs Redis sont injectées par Jenkins au moment du déploiement.

## Pré-requis Jenkins

L'image `TP_jenkins/jenkins-docker` fournit le client Docker, Compose v2 et les plugins `docker-workflow`, `junit`, `coverage`, `warnings-ng`, `github-branch-source`, `credentials-binding` et `ws-cleanup`. Le conteneur Jenkins doit avoir accès au socket Docker de l'hôte. Les contrôles du TP 3.7 téléchargent les images `python:3.12-slim`, Hadolint et Trivy.

Pour TP 3.6, configurer le job **Multibranch Pipeline** avec la source GitHub, découverte des branches et des pull requests, puis le webhook `/github-webhook/`. Pour les webhooks reçus depuis GitHub, Jenkins doit être joignable depuis Internet.

Pour TP 3.8, les ports 8081 (staging) et 8082 (production) doivent être libres sur l'hôte Docker. Le pipeline déploie aussi les branches de fonctionnalité en staging, comme indiqué dans le sujet, mais seuls les builds `main` peuvent demander l'approbation production.

## Couverture

Des tests ciblent les routes, compteurs mémoire/Redis, valeurs d'environnement et point d'entrée Flask. Le pipeline qualité échoue sous 100 % de couverture mesurée sur `app.py`.

Vérification locale effectuée avec Docker : `14 passed`, couverture `app.py` = **100 % (55/55 statements)**, Flake8 OK, Hadolint OK, test HTTP `/health` et page d'accueil OK, Trivy = **0 vulnérabilité HIGH/CRITICAL corrigeable** après mise à jour de `zlib1g` et `--ignore-unfixed`. Le pipeline Jenkins reste à exécuter après activation de l’accès navigateur à localhost:8080.
