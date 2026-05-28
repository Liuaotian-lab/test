#!/usr/bin/env bash
set -euo pipefail
python -c "from pathlib import Path; from mmos.feedback.selftest import run_self_test; r=run_self_test(Path('.').resolve(), case_id='fixture_smoke_complete_fixture', budget='fast'); assert r['status']=='passed', r; assert r['duration_sec'] < 120, r['duration_sec']; print('smoke_complete passed in', r['duration_sec'], 'sec')"
rm -rf cases/fixture_smoke_complete_fixture
