from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import write_official_json
from mmos.kernel.events import now_iso

SCHEMA_VERSION = "7.4.0"

QUESTION_HINT_RE = re.compile(r"(?:问题\s*[一二三四五六七八九十0-9]+|第\s*[一二三四五六七八九十0-9]+\s*问|Q\s*[0-9]+)")


def build_evidence_index(case_dir: Path, question_id: str | None = None, max_block_chars: int = 700) -> dict[str, Any]:
    """Build source-grounded evidence blocks from corpus, problem graph and data manifest.

    This is intentionally deterministic. Every later semantic claim must cite one or more
    evidence_id values generated here.
    """
    case_dir = Path(case_dir).resolve()
    corpus = _read_corpus(case_dir)
    graph = read_json(case_dir / "workspace" / "problem_graph.json", {}) or {}
    questions = graph.get("questions", []) or []
    if question_id:
        questions = [q for q in questions if q.get("question_id") == question_id]
    if not questions:
        questions = [{"question_id": question_id or "Q0", "title": "unparsed_problem", "source_excerpt": corpus[:max_block_chars]}]

    blocks: list[dict[str, Any]] = []
    counters: dict[str, int] = {}

    def add_block(qid: str, text: str, source_file: str = "workspace/problem_corpus.md", source_type: str = "problem_statement", meta: dict | None = None):
        text = _clean_text(text)
        if not text:
            return
        counters[qid] = counters.get(qid, 0) + 1
        evid = f"EVID-{qid}-{counters[qid]:04d}"
        blocks.append({
            "evidence_id": evid,
            "question_id": qid,
            "source_file": source_file,
            "source_type": source_type,
            "text": text[:max_block_chars],
            "char_count": len(text),
            "metadata": meta or {},
        })

    for q in questions:
        qid = q.get("question_id") or q.get("id") or "Q0"
        title = q.get("title") or ""
        excerpt = q.get("source_excerpt") or q.get("text") or ""
        if excerpt:
            add_block(qid, f"{title}\n{excerpt}", source_type="problem_question_excerpt")
        else:
            slice_text = _best_question_slice(corpus, qid, title)
            add_block(qid, f"{title}\n{slice_text}", source_type="problem_question_slice")

    # Global evidence for statements before/after parsed questions. Useful when the parser is incomplete.
    if corpus:
        add_block("GLOBAL", corpus[:max_block_chars], source_type="problem_corpus_global")

    # Attachments and data manifests are evidence too: they often define variables, units and sampling.
    manifest = read_json(case_dir / "data" / "manifest" / "data_manifest.json", {}) or {}
    manifest_items = manifest.get("files") or manifest.get("items") or []
    for idx, item in enumerate(manifest_items[:100], 1):
        qid = question_id or "GLOBAL"
        name = item.get("path") or item.get("filename") or item.get("name") or f"attachment_{idx}"
        summary = item.get("summary") or item.get("description") or item.get("schema") or ""
        add_block(qid, f"Attachment: {name}\n{summary}", source_file=str(name), source_type="data_manifest_item", meta={"manifest_index": idx})

    out = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "status": "passed" if blocks else "warning",
        "evidence_blocks": blocks,
        "block_count": len(blocks),
        "note": "Every formal problem-understanding claim should cite one or more evidence_id values from this file.",
    }
    out_path = write_official_json(case_dir, "workspace/problem_understanding/evidence_index.json", out)
    return out


def _read_corpus(case_dir: Path) -> str:
    corpus_path = case_dir / "workspace" / "problem_corpus.md"
    if corpus_path.exists():
        return corpus_path.read_text(encoding="utf-8", errors="ignore")
    parts = []
    raw = case_dir / "data" / "raw"
    if raw.exists():
        for f in sorted(raw.glob("*")):
            if f.suffix.lower() in {".txt", ".md", ".csv", ".tsv"}:
                parts.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n\n".join(parts)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _best_question_slice(corpus: str, qid: str, title: str) -> str:
    if not corpus:
        return ""
    # Prefer title hits.
    if title:
        i = corpus.find(title)
        if i >= 0:
            return corpus[i:i + 1200]
    # Prefer qid hits such as Q1.
    i = corpus.lower().find(str(qid).lower())
    if i >= 0:
        return corpus[i:i + 1200]
    # Generic fallback: take the first question-like block.
    m = QUESTION_HINT_RE.search(corpus)
    if m:
        return corpus[m.start():m.start() + 1200]
    return corpus[:1200]
