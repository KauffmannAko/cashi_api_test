import json
import logging
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from locust import HttpUser, between, events, task

LOGGER = logging.getLogger("performance.locust")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)

TRANSFER_PATH = os.getenv("TRANSFER_PATH", "/api/v1/transfers")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
RESPONSE_TIME_THRESHOLD_MS = int(os.getenv("RESPONSE_TIME_THRESHOLD_MS", "2000"))
P95_THRESHOLD_MS = int(os.getenv("P95_THRESHOLD_MS", "2000"))
FAILURE_RATE_THRESHOLD = float(os.getenv("FAILURE_RATE_THRESHOLD", "0.01"))
TEST_DATA_FILE = os.getenv("TEST_DATA_FILE", "test_data.json")


def _load_test_data(file_name: str) -> dict:
    candidates = [
        Path(file_name),
        Path(__file__).resolve().parent / file_name,
        Path("/workspace/performance") / file_name,
    ]

    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as file_pointer:
                return json.load(file_pointer)

    raise FileNotFoundError(f"Unable to locate test data file: {file_name}")


TEST_DATA = _load_test_data(TEST_DATA_FILE)
ACCOUNTS = TEST_DATA.get("accounts", [])
CURRENCIES = TEST_DATA.get("currencies", ["USD"])
DESCRIPTIONS = TEST_DATA.get("descriptions", ["Performance transfer"])

if len(ACCOUNTS) < 2:
    raise ValueError("test_data.json must include at least 2 account identifiers")


@events.request.add_listener
def request_observer(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    **kwargs,
):
    correlation_id = (context or {}).get("correlation_id", "n/a")
    if exception is None:
        LOGGER.info(
            "SUCCESS request=%s name=%s correlation_id=%s response_time_ms=%.2f bytes=%s",
            request_type,
            name,
            correlation_id,
            response_time,
            response_length,
        )
    else:
        LOGGER.error(
            "FAILURE request=%s name=%s correlation_id=%s response_time_ms=%.2f reason=%s",
            request_type,
            name,
            correlation_id,
            response_time,
            exception,
        )


@events.quitting.add_listener
def validate_global_sla(environment, **kwargs):
    total = environment.stats.total
    p95 = total.get_response_time_percentile(0.95) or 0
    fail_ratio = total.fail_ratio or 0

    LOGGER.info(
        "GLOBAL_SLA total_requests=%s total_failures=%s p95_ms=%.2f fail_ratio=%.4f",
        total.num_requests,
        total.num_failures,
        p95,
        fail_ratio,
    )

    if p95 > P95_THRESHOLD_MS:
        LOGGER.error(
            "P95 threshold breach: observed=%.2fms threshold=%sms",
            p95,
            P95_THRESHOLD_MS,
        )
        environment.process_exit_code = 1

    if fail_ratio >= FAILURE_RATE_THRESHOLD:
        LOGGER.error(
            "Failure-rate threshold breach: observed=%.4f threshold=%.4f",
            fail_ratio,
            FAILURE_RATE_THRESHOLD,
        )
        environment.process_exit_code = 1


class TransferUser(HttpUser):
    wait_time = between(0.5, 2.0)
    host = os.getenv("BASE_URL", "http://mockserver:1080")

    def _headers(self, correlation_id: str) -> dict:
        headers = {
            "Content-Type": "application/json",
            "X-Correlation-ID": correlation_id,
        }
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
        return headers

    @staticmethod
    def _pick_accounts() -> tuple[str, str]:
        from_account, to_account = random.sample(ACCOUNTS, 2)
        return from_account, to_account

    @staticmethod
    def _payload(recurring_enabled: bool, scheduled: bool = False) -> dict:
        from_account, to_account = TransferUser._pick_accounts()
        now = datetime.now(timezone.utc)
        scheduled_date = (now + timedelta(hours=2)).isoformat() if scheduled else now.isoformat()
        end_date = (now + timedelta(days=30)).isoformat()

        recurring = {
            "enabled": recurring_enabled,
            "frequency": random.choice(["daily", "weekly", "monthly"]),
            "end_date": end_date,
        }

        return {
            "from_account": from_account,
            "to_account": to_account,
            "amount": str(round(random.uniform(10, 100), 2)),
            "currency": random.choice(CURRENCIES),
            "description": random.choice(DESCRIPTIONS),
            "scheduled_date": scheduled_date,
            "recurring": recurring,
        }

    def _submit_transfer(self, payload: dict, scenario_name: str):
        correlation_id = str(uuid.uuid4())
        with self.client.post(
            TRANSFER_PATH,
            json=payload,
            name="POST /api/v1/transfers",
            headers=self._headers(correlation_id),
            catch_response=True,
            context={"correlation_id": correlation_id, "scenario": scenario_name},
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"Unexpected status code: {response.status_code}")
                return

            try:
                body = response.json()
            except ValueError:
                response.failure("Response is not valid JSON")
                return

            if "transfer_id" not in body:
                response.failure("Missing transfer_id in response")
                return

            if response.elapsed.total_seconds() * 1000 > RESPONSE_TIME_THRESHOLD_MS:
                response.failure(
                    f"Response time exceeded {RESPONSE_TIME_THRESHOLD_MS}ms: "
                    f"{response.elapsed.total_seconds() * 1000:.2f}ms"
                )
                return

            response.success()

    @task(70)
    def immediate_transfer(self):
        payload = self._payload(recurring_enabled=False, scheduled=False)
        self._submit_transfer(payload, scenario_name="immediate_transfer")

    @task(30)
    def scheduled_transfer(self):
        payload = self._payload(recurring_enabled=False, scheduled=True)
        self._submit_transfer(payload, scenario_name="scheduled_transfer")
