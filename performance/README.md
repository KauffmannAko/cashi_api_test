# Performance Testing with Locust

This module adds Dockerized Locust performance testing for `POST /api/v1/transfers` without changing the existing functional test workflow.

## Performance Objectives

- Validate up to 10,000 concurrent users (environment-dependent capacity).
- Keep 95th percentile response time below 2 seconds.
- Keep error rate below 1%.
- Detect regressions that can lead to financial risk indicators (duplicate processing, negative balances) through response/error analysis and downstream checks.

## Folder Contents

```text
performance/
├── locustfile.py
├── Dockerfile
├── requirements.txt
├── test_data.json
└── README.md
```

## Workload Model (Ramp-Up Strategy)

- Users (`-u`) and spawn rate (`-r`) are configurable.
- Recommended baseline load: `-u 10000 -r 500 --run-time 5m`.
- Use progressive ramps before max load to avoid synthetic shock masking real bottlenecks.

## Scenarios

1. High-volume immediate transfers
- Random `from_account` and `to_account` from `test_data.json`.
- `amount` randomized from 10 to 100.
- `recurring.enabled=false`.
- SLA checks: response status, `transfer_id` presence, per-request response time threshold.

2. Mixed load
- Implemented with Locust task weights:
  - `70%` immediate transfers
  - `30%` scheduled transfers (future `scheduled_date`)

## Validation and Failure Marking

Each request is executed using `catch_response=True` and marked failed when any condition is not met:

- HTTP status must be `200`.
- Response JSON must contain `transfer_id`.
- Request response time must be below `RESPONSE_TIME_THRESHOLD_MS` (default: `2000`).

Global run validation on quit:

- P95 must be `< P95_THRESHOLD_MS` (default: `2000`).
- Failure ratio must be `< FAILURE_RATE_THRESHOLD` (default: `0.01`).
- Process exits with non-zero code when breached (CI-friendly).

## Metrics Monitored

- Average response time
- P95 response time
- Error percentage
- Requests per second (RPS)

CSV outputs are written to `/artifacts/performance` when headless mode is used with `--csv`.

## Run Modes

### Local Web UI (debug)

```bash
docker compose --profile performance up --build locust
```

Open Locust UI at `http://localhost:8089`.

### Headless CI Mode

```bash
docker compose --profile performance run --rm \
  -e HEADLESS=true \
  -e USERS=10000 \
  -e SPAWN_RATE=500 \
  -e RUN_TIME=5m \
  -e BASE_URL=http://mockserver:1080 \
  -e AUTH_TOKEN=${AUTH_TOKEN} \
  locust
```

Equivalent raw Locust command:

```bash
locust -f locustfile.py --headless -u 10000 -r 500 --run-time 5m --host=http://api
```

## Test Types

1. Load test
- Validate expected peak behavior (`10k` users target).

2. Stress test
- Increase above expected peak until SLA breach to find saturation point.

3. Spike test
- Apply abrupt user increase/decrease and observe recovery behavior.

## Bottleneck Identification Guidance

- If P95 rises with stable CPU, inspect DB contention and lock waits.
- If errors rise before latency, inspect upstream dependency timeouts and thread/connection pools.
- If RPS plateaus while response time increases, inspect queue depth and backpressure handling.
- Correlation IDs are emitted per request to align Locust logs with service logs/APM traces.

## Exit Criteria

- P95 response time `< 2s`
- Error rate `< 1%`
- No negative balances in downstream ledger checks
- No duplicate transaction processing IDs in settlement/reconciliation systems

## Distributed Mode Scaling

For high load generation capacity, run Locust in distributed mode:

1. Start one master container with `--master`.
2. Start multiple worker containers with `--worker --master-host=<master-host>`.
3. Keep target user count/rate in master launch parameters and scale workers based on host CPU/network capacity.

## Example Jenkins Stage Snippet

```groovy
stage('Run Performance Tests') {
  steps {
    sh 'mkdir -p artifacts/performance artifacts/logs'
    sh 'docker compose up -d mockserver'
    sh '''
      docker compose --profile performance run --rm \
        -e HEADLESS=true \
        -e USERS=10000 \
        -e SPAWN_RATE=500 \
        -e RUN_TIME=5m \
        -e BASE_URL=http://mockserver:1080 \
        -e AUTH_TOKEN=$AUTH_TOKEN \
        locust
    '''
  }
  post {
    always {
      sh 'docker compose logs locust > artifacts/logs/locust.log || true'
      archiveArtifacts artifacts: 'artifacts/performance/**/*,artifacts/logs/locust.log', allowEmptyArchive: true
    }
  }
}
```
