from datetime import datetime, timezone

import allure


REQUIRED_RESPONSE_FIELDS = {
    "transfer_id",
    "status",
    "exchange_rate",
    "fees",
    "estimated_completion",
}


def _assert_transfer_response_schema(response_json, expected_status: str):
    assert REQUIRED_RESPONSE_FIELDS.issubset(response_json.keys())
    assert response_json["status"] == expected_status
    assert isinstance(response_json["transfer_id"], str)
    assert isinstance(response_json["exchange_rate"], str)
    assert isinstance(response_json["fees"], str)


@allure.title("Create immediate transfer returns completed status")
def test_create_immediate_transfer_returns_completed_status(api_client):
    now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "from_account": "ACC1001", 
        "to_account": "ACC2001",
        "amount": "49.99",
        "currency": "USD",
        "description": "Rent Feb",
        "scheduled_date": now_utc,
        "recurring": {
            "enabled": False,
            "frequency": "monthly",
            "end_date": now_utc,
        },
    }

    with allure.step("Submit transfer request for immediate completion"):
        response = api_client.post_transfer(payload)

    assert response.status_code == 201
    response_json = response.json()
    _assert_transfer_response_schema(response_json, expected_status="completed")


@allure.title("Create transfer fails with insufficient funds")
def test_create_transfer_fails_with_insufficient_funds(api_client):
    now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "from_account": "ACC9999",
        "to_account": "ACC2001",
        "amount": "50000.00",
        "currency": "USD",
        "description": "Insufficient funds test",
        "scheduled_date": now_utc,
        "recurring": {
            "enabled": False,
            "frequency": "monthly",
            "end_date": now_utc,
        },
    }

    with allure.step("Submit transfer request expected to fail"):
        response = api_client.post_transfer(payload)

    assert response.status_code == 402
    response_json = response.json()
    _assert_transfer_response_schema(response_json, expected_status="failed")


def test_transfers_data_driven(api_client, dataset_case):
    response = api_client.post_transfer(dataset_case["payload"])
    assert response.status_code == dataset_case["expected_http_status"]
    response_json = response.json()
    _assert_transfer_response_schema(
        response_json, expected_status=dataset_case["expected_status"]
    )
