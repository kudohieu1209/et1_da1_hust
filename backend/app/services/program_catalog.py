"""Read-only catalog of HUST undergraduate programs.

The admissions catalog is useful for selecting/searching a program, but it is
not itself a curriculum.  ``curriculum_supported`` is derived from the
validated JSON files currently loaded by CurriculumRepository. Public HTML/PDF
candidate records are exposed separately as review metadata and never count as
supported curricula.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import PROGRAM_CANDIDATES_FILE, PROGRAM_CATALOG_FILE, PROGRAM_SOURCES_FILE
from app.services.curriculum_repository import curriculum_repository


class ProgramCatalog:
    def __init__(
        self,
        path: Path = PROGRAM_CATALOG_FILE,
        sources_path: Path = PROGRAM_SOURCES_FILE,
        candidates_path: Path = PROGRAM_CANDIDATES_FILE,
    ):
        self.path = Path(path)
        self.sources_path = Path(sources_path)
        self.candidates_path = Path(candidates_path)
        self.source: dict[str, Any] = {}
        self.programs: list[dict[str, Any]] = []
        self.curriculum_sources: dict[str, dict[str, Any]] = {}
        self.curriculum_sources_discovered_at: str | None = None
        self.curriculum_candidates: dict[str, list[dict[str, Any]]] = {}
        self.reload()

    def reload(self) -> None:
        if not self.path.exists():
            self.source = {}
            self.programs = []
            return
        with self.path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
        programs = payload.get("programs", [])
        if not isinstance(programs, list):
            raise ValueError(f"Danh mục chương trình không hợp lệ: {self.path}")
        self.source = dict(payload.get("source", {}))
        self.programs = [dict(item) for item in programs if isinstance(item, dict)]
        self.curriculum_sources = {}
        self.curriculum_sources_discovered_at = None
        if self.sources_path.exists():
            with self.sources_path.open("r", encoding="utf-8") as stream:
                source_payload = json.load(stream)
            self.curriculum_sources_discovered_at = source_payload.get("discovered_at")
            for item in source_payload.get("records", []):
                if isinstance(item, dict) and item.get("admission_code"):
                    self.curriculum_sources[str(item["admission_code"]).upper()] = item
        self.curriculum_candidates = {}
        if self.candidates_path.exists():
            with self.candidates_path.open("r", encoding="utf-8") as stream:
                candidate_payload = json.load(stream)
            for item in candidate_payload.get("records", []):
                if isinstance(item, dict) and item.get("admission_code"):
                    code = str(item["admission_code"]).upper()
                    self.curriculum_candidates.setdefault(code, []).append(item)

    def _with_support_status(self, program: dict[str, Any]) -> dict[str, Any]:
        result = dict(program)
        admission_code = str(result.get("admission_code", "")).upper()
        source_record = self.curriculum_sources.get(admission_code, {})
        source = source_record.get("source") or {}
        result["curriculum_source_url"] = source_record.get("curriculum_source_url")
        result["curriculum_source_status"] = (
            "ok"
            if source.get("http_status", 500) < 400
            else ("error" if source_record.get("error") else "not_checked")
        )
        result["curriculum_source_kind"] = source.get("source_kind")
        result["curriculum_source_table_count"] = source.get("table_count")
        result["curriculum_source_course_code_count"] = source.get("course_code_count")
        if source_record.get("error"):
            result["curriculum_source_error"] = source_record["error"]
        matches = [
            item
            for item in curriculum_repository.list_programs()
            if str(item.get("program_code", "")).upper() == admission_code
        ]
        result["curriculum_supported"] = bool(matches)
        result["curriculum_versions"] = sorted(
            {str(item.get("curriculum_version", "")) for item in matches if item.get("curriculum_version")}
        )
        # Lookup years are cohort entry years: 2022 → K67, 2023 → K68, ...
        result["supported_cohorts"] = sorted(
            f"K{int(year) - 1955}"
            for code, year in curriculum_repository.available_keys
            if code == admission_code and year.isdigit()
        )
        candidates = self.curriculum_candidates.get(admission_code, [])
        result["curriculum_candidates"] = [
            {
                "candidate_id": item.get("candidate_id"),
                "curriculum_version": item.get("curriculum_version"),
                "status": (item.get("activation") or {}).get("status", "needs_review"),
                "course_count": (item.get("quality") or {}).get("course_count"),
                "group_count": (item.get("quality") or {}).get("group_count"),
                "review_reasons": (item.get("quality") or {}).get("review_reasons", []),
            }
            for item in candidates
        ]
        result["curriculum_candidate_available"] = bool(candidates)
        return result

    def list(self, search: str | None = None, supported_only: bool = False) -> list[dict[str, Any]]:
        query = str(search or "").strip().casefold()
        result = []
        for program in self.programs:
            enriched = self._with_support_status(program)
            if supported_only and not enriched["curriculum_supported"]:
                continue
            if query:
                haystack = " ".join(
                    str(enriched.get(key, ""))
                    for key in ("admission_code", "name", "faculty", "language", "slug")
                ).casefold()
                if query not in haystack:
                    continue
            result.append(enriched)
        return result

    def get(self, code: str) -> dict[str, Any] | None:
        normalized = str(code).strip().casefold()
        for program in self.list():
            if str(program.get("admission_code", "")).casefold() == normalized:
                return program
        return None


program_catalog = ProgramCatalog()
