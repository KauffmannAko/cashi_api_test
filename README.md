# Payments API Test Automation (Dockerized)

API test framework for `POST /api/v1/transfers` using Python + pytest + Allure + Jenkins + MockServer.

## Stack

- Test framework: `pytest`, `pytest-xdist`, `allure-pytest`
- Runtime: Docker + Docker Compose
- Mocking: MockServer
- Reporting: Allure Docker Service
- CI/CD: Jenkins LTS pipeline (`Jenkinsfile`)

## Repository Structure

```text
.
├── docker-compose.yml
├── .env.dev
├── .env.staging
├── .env.prod
├── README.md
├── Jenkinsfile
├── mockserver
│   ├── expectations
│   │   ├── transfers_success.json
│   │   └── transfers_failed_insufficient_funds.json
│   └── init.sh
├── tests
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── conftest.py
│   ├── config
│   │   ├── settings.py
│   │   └── __init__.py
│   ├── data
│   │   ├── dev
│   │   │   └── transfers_dataset.json
│   │   ├── staging
│   │   │   └── transfers_dataset.json
│   │   └── prod
│   │       └── transfers_dataset.json
│   ├── clients
│   │   ├── api_client.py
│   │   └── __init__.py
│   └── test_transfers_api.py
├── scripts
│   ├── run-tests.sh
│   └── wait-for.sh
└── .gitignore
```

## Quick Start (Default Path)

```bash
docker compose up -d
docker compose --profile manual run --rm tests
```

This starts `mockserver` and `allure` by default, then runs tests in the `tests` container.
Jenkins is opt-in via profile `ci`.

## Environment Switching

Default env is `dev` (`.env.dev`).

```bash
# staging
docker compose --env-file .env.staging run --rm tests

# production
docker compose --env-file .env.prod run --rm tests
```

Config is read from env variables (`ENV`, `BASE_URL`, `DATASET`) through `tests/config/settings.py`.

## Data-Driven Tests

Datasets are stored by environment:

- `tests/data/dev/transfers_dataset.json`
- `tests/data/staging/transfers_dataset.json`
- `tests/data/prod/transfers_dataset.json`

Tests parametrize over dataset cases and validate both positive and negative scenarios.

## Parallel Execution

Parallelization is enabled by `pytest-xdist` in `scripts/run-tests.sh`:

```bash
pytest -n auto --alluredir=/artifacts/allure-results
```

To override:

```bash
docker compose run --rm tests bash -lc "pip install -r /workspace/tests/requirements.txt && pytest -n 4 --alluredir=/artifacts/allure-results"
```

## Reporting and Artifacts

- Allure results: `./artifacts/allure-results`
- Logs: `./artifacts/logs`

Each test writes request/response logs with a unique correlation ID.

## View Results in Allure UI

1. Start required services:

```bash
docker compose up -d mockserver allure
```

2. Run tests (this writes results into `./artifacts/allure-results`):

```bash
docker compose --profile manual run --rm tests
```


3. Open Allure dashboard in browser:

- Latest report: `http://localhost:5050/allure-docker-service/projects/default/reports/latest/index.html`

4. Optional cleanup before a fresh run:

```bash
rm -rf artifacts/allure-results/* artifacts/allure-reports/*
```

Troubleshooting commands:

```bash
docker compose ps
docker compose logs allure --tail=200
```

## Jenkins Local Setup

1. Start Jenkins:

```bash
docker compose --profile ci up -d --build jenkins
```

2. Open `http://localhost:8080`
3. Get initial admin password:

```bash
docker exec -it payments-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

4. Install suggested plugins and add the Allure plugin.
5. Create a Pipeline job pointing to this repo and use `Jenkinsfile`.

Pipeline stages:

- Start dependencies (`mockserver`, `allure`)
- Run tests in container
- Archive artifacts (`artifacts/**/*`)
- Publish Allure results if plugin is available

## Add a New Test

1. Add or extend expectations under `mockserver/expectations`.
2. Add dataset cases under `tests/data/<env>/transfers_dataset.json`.
3. Add tests in `tests/test_transfers_api.py`.
4. Run:

```bash
docker compose run --rm tests
```

## Cleanup

```bash
docker compose down -v
```
## Allure Resut
<img width="1906" height="913" alt="Screenshot from 2026-03-02 02-32-29" src="https://github.com/user-attachments/assets/ef789207-75bd-4325-944d-d45808abc8f4" />

