import json
import time
from typing import Any, Dict

import requests


class APIClient:
    def __init__(self, base_url: str, timeout: int, logger, correlation_id: str):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logger
        self.correlation_id = correlation_id
        self.session = requests.Session()

    def post_transfer(self, payload: Dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}/api/v1/transfers"
        headers = {
            "Content-Type": "application/json",
            "X-Correlation-ID": self.correlation_id,
        }

        start = time.perf_counter()
        response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text

        log_record = {
            "correlation_id": self.correlation_id,
            "method": "POST",
            "url": url,
            "request_headers": headers,
            "request_payload": payload,
            "response_status": response.status_code,
            "response_headers": dict(response.headers),
            "response_body": response_body,
            "duration_ms": duration_ms,
        }
        self.logger.info(json.dumps(log_record, default=str))

        return response
