from __future__ import annotations

from .commands_common import print_json


def cmd_workflow_state(args, osp):
    from mmos.workflows.state_machine import case_state_report
    print_json(case_state_report(osp.case_dir(args.case)))


def cmd_workflow_transition(args, osp):
    from mmos.workflows.state_machine import transition_case_state
    print_json(transition_case_state(osp.case_dir(args.case), step=args.step, status=args.status))


def cmd_agent_policy_init(args, osp):
    from mmos.agents.policy import ensure_policy
    print_json({"status": "passed", "policy": ensure_policy(osp.case_dir(args.case))})


def cmd_agent_runtime_report(args, osp):
    from mmos.agents.runtime import create_agent_run_report, latest_agent_run_report
    if args.latest:
        print_json(latest_agent_run_report(osp.case_dir(args.case)))
    else:
        print_json(create_agent_run_report(osp.case_dir(args.case), task_id=args.task_id, agent_role=args.role, context_files=args.context_file or [], candidate_outputs=args.candidate_output or [], commands_run=args.command or []))


def cmd_agent_budget_check(args, osp):
    from mmos.agents.budget import evaluate_budget
    usage = {"context_files": args.context_files, "tool_calls": args.tool_calls, "search_queries": args.search_queries, "runtime_seconds": args.runtime_seconds, "candidate_outputs": args.candidate_outputs}
    print_json(evaluate_budget(usage))


def cmd_mcp_permission_check(args, osp):
    from mmos.adapters.mcp.permissions import evaluate_mcp_call
    print_json(evaluate_mcp_call(osp.case_dir(args.case), tool=args.tool, target=args.target, mode=args.mode))
