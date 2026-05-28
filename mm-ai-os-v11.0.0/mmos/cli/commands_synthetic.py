from __future__ import annotations

from .commands_common import *


def cmd_synthetic_install(args, osp):
    from mmos.synthetic.thermal_case import install_synthetic_raw
    print_json(install_synthetic_raw(osp.case_dir(args.case), overwrite=args.overwrite))


def cmd_synthetic_search_inject(args, osp):
    from mmos.synthetic.thermal_case import inject_synthetic_search_results
    print_json(inject_synthetic_search_results(osp.case_dir(args.case), question_id=args.question))


def cmd_synthetic_solution_inject(args, osp):
    from mmos.synthetic.thermal_case import inject_synthetic_solution
    print_json(inject_synthetic_solution(osp.case_dir(args.case), question_id=args.question))


def cmd_synthetic_write_golden(args, osp):
    from pathlib import Path
    from mmos.synthetic.thermal_case import write_golden_snapshot
    print_json(write_golden_snapshot(osp.case_dir(args.case), Path(args.destination)))



def cmd_synthetic_e2e_run(args, osp):
    from mmos.synthetic.thermal_case import run_synthetic_e2e
    print_json(run_synthetic_e2e(osp.case_dir(args.case), force=args.force))
