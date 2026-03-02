#!/usr/bin/env bash
set -euo pipefail

bash /workspace/scripts/wait-for.sh mockserver 1080 90

pip install --no-cache-dir -r /workspace/tests/requirements.txt

mkdir -p /artifacts/allure-results /artifacts/logs /artifacts/allure-reports

pytest -n auto --alluredir=/artifacts/allure-results /workspace/tests "$@"
