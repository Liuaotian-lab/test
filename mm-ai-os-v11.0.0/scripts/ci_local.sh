#!/usr/bin/env bash
set -euo pipefail

python scripts/check_version_consistency.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -vv
