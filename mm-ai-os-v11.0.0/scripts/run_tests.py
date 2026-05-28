#!/usr/bin/env python3
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(cmd: list[str], timeout: int = 180) -> int:
    print("$", " ".join(cmd), flush=True)
    env = os.environ.copy()
    if "pytest" in cmd:
        # Keep local CI deterministic and avoid third-party plugin shutdown hooks.
        env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    try:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "stdout.txt"
            err_path = Path(td) / "stderr.txt"
            with out_path.open("w", encoding="utf-8") as out, err_path.open("w", encoding="utf-8") as err:
                proc = subprocess.run(cmd, cwd=str(ROOT), timeout=timeout, env=env, text=True, stdout=out, stderr=err)
            stdout = out_path.read_text(encoding="utf-8", errors="replace")
            stderr = err_path.read_text(encoding="utf-8", errors="replace")
        def _print_limited(text: str, label: str) -> None:
            if not text:
                return
            limit = 5000
            if len(text) > limit:
                print(text[:limit], end="" if text[:limit].endswith("\n") else "\n", flush=True)
                print(f"... [{label} truncated: {len(text) - limit} chars omitted]", flush=True)
            else:
                print(text, end="" if text.endswith("\n") else "\n", flush=True)

        _print_limited(stdout, "stdout")
        _print_limited(stderr, "stderr")
        return proc.returncode
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout}s: {' '.join(cmd)}", flush=True)
        return 124


def exec_run(cmd: list[str]) -> None:
    """Replace the current process with a test command.

    This avoids pytest shutdown hangs observed when pytest is launched as a
    nested subprocess from this local CI driver on Python 3.13.
    """
    print("$", " ".join(cmd), flush=True)
    env = os.environ.copy()
    if "pytest" in cmd:
        env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    os.execvpe(cmd[0], cmd, env)


def pure_dev_checks() -> int:
    print("$ internal pure dev checks", flush=True)
    from mmos.kernel.paths import OSPaths
    from mmos.contracts.manager import ensure_case_scaffold
    from mmos.kernel.jsonio import write_json
    from mmos.problem_signature.extractor import extract_problem_signature
    from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search

    # Path safety
    osp = OSPaths.discover()
    for bad in ['../evil', '../../tmp/x', 'case/evil', 'case..evil']:
        try:
            osp.case_dir(bad)
        except ValueError:
            pass
        else:
            print(f"path safety failed for {bad}")
            return 1

    # Purity contract
    for rel in ['legacy', 'examples', 'dev_tools', 'mmos/capability_router', 'mmos/capability_planning', 'tests/legacy']:
        if (ROOT / rel).exists():
            print(f"pure distribution must not include {rel}")
            return 1

    # Signature + academic-search bootstrap
    with tempfile.TemporaryDirectory() as td:
        case_dir = Path(td) / 'case_thermal'
        ensure_case_scaffold(case_dir)
        (case_dir / 'workspace' / 'problem_corpus.md').write_text('问题1：建立炉温曲线模型，考虑温度、时间和传送带速度，并优化工艺参数。', encoding='utf-8')
        write_json(case_dir / 'workspace' / 'problem_graph.json', {'questions': [{'question_id':'Q1','title':'炉温曲线优化','source_excerpt':'建立炉温曲线模型，优化传送带速度。'}]})
        sig = extract_problem_signature(case_dir)
        q1 = sig['questions']['Q1']
        if q1['domain_family']['primary'] != 'physical_process.thermal_process':
            print('signature bootstrap failed')
            return 1
        search = orchestrate_academic_search(case_dir, strict=False)
        if search['status'] != 'passed' or search['searches'][0]['total_queries'] <= 0:
            print('academic-search bootstrap failed')
            return 1
    print('pure dev checks passed', flush=True)
    return 0


def schema_checks() -> int:
    print("$ internal schema checks", flush=True)
    from mmos.core.schema import list_schemas, validate_json_file

    required = {
        "problem_understanding/final_problem_signature",
        "academic_research/search_results",
        "method_plan/method_plan",
        "agents/task_card",
        "gates/gate_result",
        "workflow/step_result",
        "artifacts/artifact_promotion",
    }
    schemas = set(list_schemas(ROOT))
    missing = sorted(required - schemas)
    if missing:
        print(f"missing schemas: {missing}", flush=True)
        return 1
    fixtures = [
        ("problem_understanding/final_problem_signature", ROOT / "tests/fixtures/schemas/problem_understanding/valid_final_problem_signature.json", True),
        ("problem_understanding/final_problem_signature", ROOT / "tests/fixtures/schemas/problem_understanding/invalid_final_problem_signature.json", False),
        ("academic_research/search_results", ROOT / "tests/fixtures/schemas/academic_research/valid_search_results.json", True),
        ("academic_research/search_results", ROOT / "tests/fixtures/schemas/academic_research/invalid_search_results.json", False),
        ("method_plan/method_plan", ROOT / "tests/fixtures/schemas/method_plan/valid_method_plan.json", True),
        ("gates/gate_result", ROOT / "tests/fixtures/schemas/gates/valid_gate_result.json", True),
    ]
    for schema_name, path, should_pass in fixtures:
        result = validate_json_file(path, schema_name, root=ROOT)
        if should_pass and result.status != "passed":
            print(f"schema fixture should pass but failed: {schema_name} {path} {result.errors}", flush=True)
            return 1
        if not should_pass and result.status != "failed":
            print(f"schema fixture should fail but passed: {schema_name} {path}", flush=True)
            return 1
    print("schema checks passed", flush=True)
    return 0



def _run_json(cmd: list[str], timeout: int = 240) -> dict:
    import json
    print("$", " ".join(cmd), flush=True)
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "stdout.json"
        err_path = Path(td) / "stderr.txt"
        with out_path.open("w", encoding="utf-8") as out, err_path.open("w", encoding="utf-8") as err:
            proc = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=out, stderr=err, timeout=timeout)
        stdout = out_path.read_text(encoding="utf-8", errors="replace")
        stderr = err_path.read_text(encoding="utf-8", errors="replace")
    if stdout:
        print(stdout, flush=True)
    if stderr:
        print(stderr, flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed with {proc.returncode}: {' '.join(cmd)}")
    return json.loads(stdout)


def synthetic_e2e_checks() -> int:
    print("$ synthetic e2e checks", flush=True)
    try:
        result = _run_json([sys.executable, '-m', 'mmos.cli', 'synthetic-e2e-run', 'synthetic_thermal_minimal_run_tests', '--force'])
    except Exception as exc:
        print(f"synthetic e2e failed: {exc}", flush=True)
        return 1
    if result.get("status") != "passed":
        print(f"synthetic e2e failed: {result}", flush=True)
        return 1
    case_dir = ROOT / "cases" / "synthetic_thermal_minimal_run_tests"
    if not (case_dir / "package" / "package_manifest.json").exists() or not (case_dir / "final_outputs" / "final_gate_check.json").exists():
        print("synthetic e2e missing package manifest or final gate", flush=True)
        return 1
    print("synthetic e2e checks passed", flush=True)
    return 0


def golden_checks() -> int:
    print("$ golden checks", flush=True)
    import json
    expected = ROOT / "tests" / "fixtures" / "synthetic_cases" / "thermal_optimization_minimal" / "expected"
    try:
        result = _run_json([sys.executable, '-m', 'mmos.cli', 'synthetic-e2e-run', 'synthetic_thermal_minimal', '--force'])
        if result.get("status") != "passed":
            print(f"golden pipeline failed: {result}", flush=True)
            return 1
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            _run_json([sys.executable, '-m', 'mmos.cli', 'synthetic-write-golden', 'synthetic_thermal_minimal', '--destination', str(out)])
            for name in ["problem_graph.golden.json", "search_plan.golden.json", "method_plan.golden.json", "package_manifest.golden.json"]:
                actual = json.loads((out / name).read_text(encoding="utf-8"))
                exp = json.loads((expected / name).read_text(encoding="utf-8"))
                if actual != exp:
                    print(f"golden mismatch: {name}", flush=True)
                    return 1
    except Exception as exc:
        print(f"golden checks failed: {exc}", flush=True)
        return 1
    print("golden checks passed", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tier', choices=['smoke', 'schema', 'unit', 'integration', 'e2e', 'golden', 'dev', 'release', 'all'], default='smoke')
    args = ap.parse_args()

    # Test-heavy tiers are delegated directly to pytest so the local CI driver
    # does not keep a parent Python process around while pytest spawns its own
    # subprocesses. Smoke/schema/dev/release keep the deterministic preflight.
    if args.tier == 'unit':
        exec_run([sys.executable, '-m', 'pytest', '-q', '--ignore=tests/e2e', '--ignore=tests/golden'])
    if args.tier == 'integration':
        exec_run([sys.executable, '-m', 'pytest', '-q', 'tests/test_academic_research_bootstrap.py', 'tests/test_artifact_governance.py', 'tests/test_problem_understanding_engine.py', 'tests/test_search_plan_gate.py'])
    if args.tier == 'e2e':
        exec_run([sys.executable, '-m', 'pytest', '-q', 'tests/e2e'])
    if args.tier == 'golden':
        exec_run([sys.executable, '-m', 'pytest', '-q', 'tests/golden'])
    if args.tier == 'all':
        exec_run([sys.executable, '-m', 'pytest', '-vv'])

    commands = [
        ([sys.executable, '-m', 'compileall', '-q', 'mmos', 'scripts', 'tests'], 180),
        ([sys.executable, 'scripts/check_version_consistency.py'], 60),
    ]
    # Keep the smoke CLI probe compact. Full --help compatibility is covered by
    # pytest tests and can be run manually; printing the very large command list
    # repeatedly can destabilize nested CI subprocesses on Python 3.13.
    if args.tier not in {'unit', 'integration', 'all', 'schema'}:
        commands.append(([sys.executable, '-m', 'mmos.cli', 'schema-list'], 60))
    if args.tier == 'release':
        commands.append(([sys.executable, 'setup_verify.py'], 180))

    for cmd, timeout in commands:
        rc = run(cmd, timeout=timeout)
        if rc:
            return rc

    if args.tier == 'schema':
        rc = schema_checks()
        if rc:
            return rc

    if args.tier == 'dev':
        rc = pure_dev_checks()
        if rc:
            return rc
        # Optional script-level regressions that do not require historical cases.
        for cmd in ([sys.executable, 'tests/academic_research_engine_checks.py'], [sys.executable, 'tests/chart_digitizer_checks.py']):
            rc = run(list(cmd), timeout=180)
            if rc:
                return rc
    return 0


if __name__ == '__main__':
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)
