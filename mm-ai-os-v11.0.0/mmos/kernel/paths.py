from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import shutil


@dataclass(frozen=True)
class OSPaths:
    root: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> 'OSPaths':
        start = Path(start or Path.cwd()).resolve()
        for p in [start, *start.parents]:
            if (p / 'scripts' / 'mmtool.py').exists() and (p / 'mmos').exists():
                return cls(p)
        return cls(start)

    def case_dir(self, case_id: str) -> Path:
        return resolve_case_id(self.root, case_id)

    def template_dir(self, *parts: str) -> Path:
        return (self.root / 'templates' / Path(*parts)).resolve()

    # v7.0: capability_dir removed. Use search_templates_dir() instead.
    # def capability_dir(self) -> Path: ...  # DELETED in v7.0

    def search_templates_dir(self) -> Path:
        return (self.root / 'templates' / 'search_templates').resolve()

    def schema_dir(self) -> Path:
        return (self.root / 'schemas').resolve()


CASE_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$')


def resolve_case_id(root: Path, case_id: str) -> Path:
    """Resolve a case id below <root>/cases with strict traversal protection."""
    if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id) or '..' in case_id:
        raise ValueError(
            'invalid case id: use only letters, digits, underscore, dash and dot; '
            'path separators and traversal are forbidden'
        )
    cases_root = (Path(root).resolve() / 'cases').resolve()
    target = (cases_root / case_id).resolve()
    try:
        target.relative_to(cases_root)
    except ValueError as exc:
        raise ValueError(f'case path escapes cases directory: {target}') from exc
    return target


def resolve_case_path(case_dir: Path, *parts: str) -> Path:
    base = Path(case_dir).resolve()
    target = (base / Path(*parts)).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError(f'path escapes case directory: {target}') from exc
    return target


def copytree_merge(src: Path, dst: Path) -> None:
    src, dst = Path(src), Path(dst)
    for item in src.rglob('*'):
        rel = item.relative_to(src)
        out = dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)
