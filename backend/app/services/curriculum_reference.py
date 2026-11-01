"""Expose every collected curriculum for reading without inventing audit rules."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import CURRICULUM_REFERENCES_DIR, DATA_DIR


class CurriculumReferences:
    def __init__(self, source_dir: Path = CURRICULUM_REFERENCES_DIR,
                 reviewed_dir: Path = DATA_DIR.parent / "raw/reviewed_curricula"):
        self.source_dir = source_dir
        self.reviewed_dir = reviewed_dir
        self.records: dict[str, list[dict[str, Any]]] = {}
        self.reload()

    def reload(self):
        rows = {}
        approval_path = DATA_DIR / "curriculum_approvals.json"
        approvals = json.loads(approval_path.read_text(encoding="utf-8")) if approval_path.exists() else {"approvals": []}
        activations = {a.get("source_candidate_id") or a["candidate_id"]: a["candidate_id"].rsplit("-", 1)[-1]
                       for a in approvals["approvals"] if a.get("status") == "approved"}
        # A source-based resolution replaces the old extraction with the same ID.
        for directory in (self.source_dir, self.reviewed_dir):
            for path in sorted(directory.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                code = str(raw.get("admission_code") or "").upper()
                if not code:
                    continue
                notes = [str(n) for n in raw.get("notes", []) if not re.search(r"[A-Za-z]:\\|appdata", str(n), re.I)]
                groups = [{"name": group.get("name") or "Học phần trong nguồn",
                           "required_credits": group.get("required_credits"),
                           "counts_toward_degree": group.get("counts_toward_degree"),
                           "kind": group.get("kind"), "courses": group.get("courses", [])}
                          for group in raw.get("groups", [])]
                rows[path.stem] = {
                    "id": path.stem, "program_code": code, "name": raw.get("name", code),
                    "curriculum_version": raw.get("curriculum_version"),
                    "normalized_version": activations.get(path.stem),
                    "applies_to_cohorts": raw.get("applies_to_cohorts") or [],
                    "total_credits": raw.get("total_credits"), "source_url": raw.get("source_url"),
                    "source_title": raw.get("source_title"), "retrieved_at": raw.get("retrieved_at"),
                    "graduation_rule": raw.get("graduation_rule"), "groups": groups, "notes": notes,
                    "source_review": raw.get("source_review"),
                    "course_count": len({c.get("code") for g in groups for c in g["courses"] if c.get("code")}),
                }
        records = {}
        for row in rows.values():
            records.setdefault(row["program_code"], []).append(row)
        self.records = records

    def for_program(self, code: str) -> list[dict[str, Any]]:
        return self.records.get(code.upper(), [])


curriculum_references = CurriculumReferences()
