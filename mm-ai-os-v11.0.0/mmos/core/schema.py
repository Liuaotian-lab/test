from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class SchemaValidationResult:
    """Machine-readable result returned by schema validation utilities."""

    status: str
    schema: str
    file: str | None
    error_count: int
    errors: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def schema_root(root: Path | None = None) -> Path:
    root = Path(root or Path.cwd()).resolve()
    for p in [root, *root.parents]:
        if (p / "schemas").exists() and (p / "mmos").exists():
            return (p / "schemas").resolve()
    return (root / "schemas").resolve()


def normalize_schema_name(name: str) -> str:
    name = name.strip().replace("\\", "/")
    if name.startswith("schemas/"):
        name = name[len("schemas/"):]
    if name.endswith(".schema.json"):
        name = name[:-len(".schema.json")]
    elif name.endswith(".json"):
        name = name[:-len(".json")]
    return name.strip("/")


def schema_path(name: str, root: Path | None = None) -> Path:
    base = schema_root(root)
    norm = normalize_schema_name(name)
    candidates = [base / f"{norm}.schema.json", base / f"{norm}.json"]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"schema not found: {name}; searched under {base}")


def list_schemas(root: Path | None = None) -> list[str]:
    base = schema_root(root)
    if not base.exists():
        return []
    out: list[str] = []
    for path in sorted(base.rglob("*.json")):
        rel = path.relative_to(base).as_posix()
        out.append(normalize_schema_name(rel))
    return out


def load_schema(name: str, root: Path | None = None, *, resolve_refs: bool = True) -> dict[str, Any]:
    path = schema_path(name, root)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not resolve_refs:
        return data
    base = schema_root(root)
    return _resolve_local_refs(data, path.parent, base, seen={path.resolve()})


def _resolve_local_refs(obj: Any, current_dir: Path, base: Path, seen: set[Path]) -> Any:
    if isinstance(obj, dict):
        if set(obj.keys()) == {"$ref"} and isinstance(obj.get("$ref"), str):
            ref = obj["$ref"]
            if ref.startswith("#") or "://" in ref:
                return obj
            ref_path = (current_dir / ref).resolve()
            if not ref_path.exists():
                ref_path = schema_path(ref, base.parent)
            if ref_path in seen:
                # Preserve recursive or duplicate references to avoid infinite expansion.
                return {"$ref": ref}
            schema = json.loads(ref_path.read_text(encoding="utf-8"))
            return _resolve_local_refs(schema, ref_path.parent, base, seen | {ref_path})
        return {k: _resolve_local_refs(v, current_dir, base, seen) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_local_refs(v, current_dir, base, seen) for v in obj]
    return obj


def validate_data(data: Any, schema_name: str, root: Path | None = None, file: str | None = None) -> SchemaValidationResult:
    schema = load_schema(schema_name, root)
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        errors.append({
            "path": "/" + "/".join(str(p) for p in err.path),
            "schema_path": "/" + "/".join(str(p) for p in err.schema_path),
            "message": err.message,
            "validator": err.validator,
        })
    return SchemaValidationResult(
        status="passed" if not errors else "failed",
        schema=normalize_schema_name(schema_name),
        file=file,
        error_count=len(errors),
        errors=errors,
    )


def validate_json_file(file_path: Path, schema_name: str, root: Path | None = None) -> SchemaValidationResult:
    path = Path(file_path).resolve()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return validate_data(data, schema_name, root=root, file=str(path))
