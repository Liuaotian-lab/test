from __future__ import annotations

from mmos.kernel.paths import OSPaths

from . import commands_common
from .commands_common import print_json
from .dispatch import _exit_code_from_payload
from .parser import build_parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    osp = OSPaths.discover()
    try:
        args.fn(args, osp)
    except ValueError as e:
        print_json({'status': 'failed', 'error': str(e)})
        return 2
    return _exit_code_from_payload(
        commands_common._LAST_EMITTED_JSON,
        strict_warnings=getattr(args, 'strict_warnings_exit', False),
    )


__all__ = ["build_parser", "main"]
