# Context Pack: CLI

## Purpose

CLI command registration and dispatch.

## Current structure

- `mmos/cli/main.py`: runtime entrypoint.
- `mmos/cli/parser.py`: argparse command registration.
- `mmos/cli/commands_*.py`: grouped command handlers.
- `mmos/cli/commands_common.py`: shared imports, JSON output helper and small render helpers.
- `scripts/mmtool.py`: compatibility wrapper.

## Inputs

Command-line arguments.

## Outputs

JSON payloads printed to stdout through `print_json`.

## Public APIs

- `mmos.cli.main(argv=None)`
- `mmos.cli.build_parser()`

## Tests

```bash
python -m mmos.cli --help
python scripts/mmtool.py --help
python -m pytest -q tests/test_cli_contract.py
```

## Rules

- Keep old command names stable.
- Handler functions should stay thin and call workflow/domain modules.
- Do not add heavy business logic to `parser.py`.
