from datetime import datetime, timezone

import allure
import pytest


REQUIRED_RESPONSE_FIELDS = {
    "transfer_id",
    "status",
    "exchange_rate",
    "fees",
}


def _assert_transfer_response_schema(response_json, expected_status: str):
    assert REQUIRED_RESPONSE_FIELDS.issubset(response_json.keys())
    assert response_json["status"] == expected_status
    assert isinstance(response_json["transfer_id"], str)
    assert response_json["transfer_id"]
    assert isinstance(response_json["exchange_rate"], str)
    assert isinstance(response_json["fees"], str)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _build_payload(
    *,
    from_account: str = "ACC1001",
    to_account: str = "ACC2001",
    amount: str = "10.00",
    currency: str = "USD",
    description: str,
    scheduled_date: str,
    recurring_enabled: bool = False,
    recurring_frequency: str = "weekly",
    recurring_end_date: str | None = None,
):
    recurring = {
        "enabled": recurring_enabled,
        "frequency": recurring_frequency,
    }
    if recurring_end_date is not None:
        recurring["end_date"] = recurring_end_date

    return {
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
        "currency": currency,
        "description": description,
        "scheduled_date": scheduled_date,
        "recurring": recurring,
    }


@allure.title("1. Create immediate transfer with sufficient balance")
def test_create_immediate_transfer_with_sufficient_balance(api_client):
    payload = _build_payload(
        amount="49.99",
        description="Rent Feb",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 201
    response_json = response.json()
    assert response_json["status"] in {"completed", "pending"}
    assert "transfer_id" in response_json
    assert "fees" in response_json
    assert "estimated_completion" in response_json


@allure.title("2. Reject transfer when sender has insufficient funds")
def test_reject_transfer_with_insufficient_funds(api_client):
    payload = _build_payload(
        from_account="ACC1002",
        amount="49.99",
        description="Groceries",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 402
    response_json = response.json()
    _assert_transfer_response_schema(response_json, expected_status="failed")
    assert response_json.get("estimated_completion") in {None, ""}


@allure.title("3. Reject transfer to non-existent recipient account")
def test_reject_transfer_to_non_existent_recipient(api_client):
    payload = _build_payload(
        to_account="ACC9999",
        amount="20.00",
        description="Gift",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 404
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("4. Reject transfer from non-existent sender account")
def test_reject_transfer_from_non_existent_sender(api_client):
    payload = _build_payload(
        from_account="ACC9998",
        amount="20.00",
        description="Test",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 404
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("5. Reject transfer when sender and recipient match")
def test_reject_transfer_when_sender_and_recipient_match(api_client):
    payload = _build_payload(
        from_account="ACC1001",
        to_account="ACC1001",
        amount="10.00",
        description="Self transfer",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 400
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("6. Reject transfer from account user does not own")
def test_reject_transfer_from_account_user_does_not_own(api_client):
    payload = _build_payload(
        from_account="ACC3001",
        amount="10.00",
        description="Unauthorized",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 403
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("7. Prevent duplicate transfer on repeated request")
def test_prevent_duplicate_transfer_on_repeated_request(api_client):
    payload = _build_payload(
        amount="15.00",
        description="Lunch",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    first_response = api_client.post_transfer(payload)
    second_response = api_client.post_transfer(payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    assert first_body["transfer_id"] == second_body["transfer_id"]
    assert first_body["status"] in {"completed", "pending"}
    assert second_body["status"] in {"pending", "failed"}


@allure.title("8. Create scheduled transfer for a future date")
def test_create_scheduled_transfer_for_future_date(api_client):
    payload = _build_payload(
        amount="25.00",
        description="Electricity bill",
        scheduled_date="2026-03-05T10:00:00Z",
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 201
    response_json = response.json()
    _assert_transfer_response_schema(response_json, expected_status="pending")
    assert response_json.get("estimated_completion")


@allure.title("9. Reject scheduled transfer with past scheduled date")
def test_reject_scheduled_transfer_with_past_date(api_client):
    payload = _build_payload(
        amount="25.00",
        description="Past schedule",
        scheduled_date="2025-01-01T10:00:00Z",
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 400
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("10. Create daily recurring transfer with valid end date")
def test_create_daily_recurring_transfer_with_valid_end_date(api_client):
    payload = _build_payload(
        amount="5.00",
        description="Daily savings",
        scheduled_date="2026-03-01T08:00:00Z",
        recurring_enabled=True,
        recurring_frequency="daily",
        recurring_end_date="2026-03-10T08:00:00Z",
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 201
    response_json = response.json()
    _assert_transfer_response_schema(response_json, expected_status="pending")
    assert response_json.get("estimated_completion")


@allure.title("11. Reject recurring transfer when end date is missing")
def test_reject_recurring_transfer_when_end_date_missing(api_client):
    payload = _build_payload(
        amount="5.00",
        description="Recurring missing end",
        scheduled_date=_iso_now(),
        recurring_enabled=True,
        recurring_frequency="weekly",
        recurring_end_date=None,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 400
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("12. Reject recurring transfer when end date is before start")
def test_reject_recurring_transfer_when_end_before_start(api_client):
    payload = _build_payload(
        amount="5.00",
        description="Recurring wrong end",
        scheduled_date="2026-03-10T08:00:00Z",
        recurring_enabled=True,
        recurring_frequency="monthly",
        recurring_end_date="2026-03-01T08:00:00Z",
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 400
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("13. Reject recurring transfer with invalid frequency value")
def test_reject_recurring_transfer_with_invalid_frequency(api_client):
    payload = _build_payload(
        amount="5.00",
        description="Recurring invalid frequency",
        scheduled_date=_iso_now(),
        recurring_enabled=True,
        recurring_frequency="yearly",
        recurring_end_date="2026-04-01T08:00:00Z",
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 400
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("14. Apply FX rate and fees for cross-currency transfer")
def test_apply_fx_rate_and_fees_for_cross_currency_transfer(api_client):
    payload = _build_payload(
        from_account="ACCXAF01",
        to_account="ACCUSD01",
        amount="100.00",
        currency="USD",
        description="USD purchase",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 201
    response_json = response.json()
    assert response_json["status"] in {"completed", "pending"}
    assert response_json.get("exchange_rate") not in {None, ""}
    assert response_json.get("fees") not in {None, ""}


@allure.title("15. Reject transfer when FX rate is unavailable")
def test_reject_transfer_when_fx_rate_unavailable(api_client):
    payload = _build_payload(
        from_account="ACCXAF01",
        to_account="ACCUSD01",
        amount="100.00",
        currency="USD",
        description="FX unavailable",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 503
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("16. Reject transfer amount that exceeds transaction limit")
def test_reject_transfer_exceeding_transaction_limit(api_client):
    payload = _build_payload(
        amount="1500.00",
        description="Large payment",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 422
    _assert_transfer_response_schema(response.json(), expected_status="failed")


@allure.title("17. Reject transfer when daily cumulative limit exceeded")
def test_reject_transfer_when_daily_cumulative_limit_exceeded(api_client):
    first_payload = _build_payload(
        amount="150.00",
        description="Daily limit step 1",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )
    second_payload = _build_payload(
        amount="60.00",
        description="Daily limit step 2",
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    first_response = api_client.post_transfer(first_payload)
    second_response = api_client.post_transfer(second_payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 429
    assert first_response.json()["status"] in {"completed", "pending"}
    assert second_response.json()["status"] == "failed"


@pytest.mark.parametrize(
    ("amount", "description"),
    [
        ("0.00", "Invalid amount zero"),
        ("-10.00", "Invalid amount negative"),
    ],
)
@allure.title("18. Reject transfer with negative or zero amount")
def test_reject_transfer_with_negative_or_zero_amount(
    api_client,
    amount: str,
    description: str,
):
    payload = _build_payload(
        amount=amount,
        description=description,
        scheduled_date=_iso_now(),
        recurring_enabled=False,
    )

    response = api_client.post_transfer(payload)

    assert response.status_code == 400
    _assert_transfer_response_schema(response.json(), expected_status="failed")
