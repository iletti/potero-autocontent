#!/bin/sh
set -euo pipefail

python -m unittest discover -s tests
POTERO_REQUIRE_API_KEY=false POTERO_REQUIRE_ASSETS=false python scripts/smoke_check.py
