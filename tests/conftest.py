import json
import logging
import os
import re
import uuid
from pathlib import Path

import pytest

from clients.api_client import APIClient
from config.settings import get_settings


def _safe_name(nodeid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid)


def _load_transfer_dataset(env: str, dataset_file: str):
    data_root = Path(__file__).resolve().parent / "data"
    dataset_path = data_root / env / dataset_file
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError(f"Dataset must be a list of test cases: {dataset_path}")

    return dataset


def pytest_generate_tests(metafunc):
    if "dataset_case" not in metafunc.fixturenames:
        return

    env = os.getenv("ENV", "dev")
    dataset_file = os.getenv("DATASET", "transfers_dataset.json")
    dataset = _load_transfer_dataset(env=env, dataset_file=dataset_file)
    case_ids = [case.get("name", f"case_{idx}") for idx, case in enumerate(dataset)]
    metafunc.parametrize("dataset_case", dataset, ids=case_ids)


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def ensure_artifacts(settings):
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.allure_results_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def correlation_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def test_logger(request, settings, correlation_id):
    logger_name = f"api_test.{_safe_name(request.node.nodeid)}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    logfile = settings.logs_dir / f"{_safe_name(request.node.nodeid)}.log"
    handler = logging.FileHandler(logfile, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s correlation_id=%(correlation_id)s %(message)s"
    )
    handler.setFormatter(formatter)

    class CorrelationFilter(logging.Filter):
        def filter(self, record):
            record.correlation_id = correlation_id
            return True

    handler.addFilter(CorrelationFilter())
    logger.addHandler(handler)

    logger.info("test_started")
    yield logger
    logger.info("test_finished")

    handler.close()
    logger.removeHandler(handler)


@pytest.fixture
def api_client(settings, correlation_id, test_logger):
    return APIClient(
        base_url=settings.base_url,
        timeout=settings.request_timeout,
        logger=test_logger,
        correlation_id=correlation_id,
    )
