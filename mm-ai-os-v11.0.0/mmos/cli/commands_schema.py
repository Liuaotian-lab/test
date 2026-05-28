from __future__ import annotations

from .commands_common import print_json
from mmos.core.schema import list_schemas, validate_json_file, schema_path


def cmd_schema_list(args, osp):
    schemas = list_schemas(osp.root)
    print_json({
        "status": "passed",
        "schema_count": len(schemas),
        "schemas": schemas,
    })


def cmd_schema_validate(args, osp):
    result = validate_json_file(args.file, args.schema, root=osp.root)
    payload = result.to_dict()
    payload["schema_path"] = str(schema_path(args.schema, osp.root).relative_to(osp.root))
    print_json(payload)
