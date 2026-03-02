import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    env: str
    base_url: str
    dataset_file: str
    request_timeout: int
    artifacts_dir: Path
    logs_dir: Path
    allure_results_dir: Path
    data_dir: Path

    @property
    def dataset_path(self) -> Path:
        return self.data_dir / self.env / self.dataset_file


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = os.getenv("ENV", "dev")
    base_url = os.getenv("BASE_URL", "http://mockserver:1080")
    dataset_file = os.getenv("DATASET", "transfers_dataset.json")
    request_timeout = int(os.getenv("REQUEST_TIMEOUT", "15"))

    artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", "/artifacts"))
    tests_root = Path(__file__).resolve().parents[1]

    return Settings(
        env=env,
        base_url=base_url.rstrip("/"),
        dataset_file=dataset_file,
        request_timeout=request_timeout,
        artifacts_dir=artifacts_dir,
        logs_dir=artifacts_dir / "logs",
        allure_results_dir=artifacts_dir / "allure-results",
        data_dir=tests_root / "data",
    )
