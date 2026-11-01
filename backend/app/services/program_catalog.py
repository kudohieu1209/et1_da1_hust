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
from app.services.curriculum_reference import curriculum_references


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
        self.references = curriculum_references
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
        references = self.references.for_program(admission_code)
        result["reference_available"] = bool(references)
        result["reference_count"] = len(references)
        result["reference_course_count"] = max((r["course_count"] for r in references), default=0)
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

    def get_curricula(self, code: str) -> list[dict[str, Any]]:
        code = code.upper()
        datasets = {str(p["curriculum_version"]): p for p in curriculum_repository.list_programs()
                    if p["program_code"] == code}
        result = []
        for record in self.references.for_program(code):
            version = str(record.get("normalized_version") or record["curriculum_version"] or "")
            result.append({**record, "curriculum_version": version if version in datasets else record["curriculum_version"],
                           "audit_available": version in datasets,
                           "usage": "audit_and_reference" if version in datasets else "reference",
                           "scope_note": None if version in datasets else
                           "Dùng để tra cứu học phần và nguồn gốc. Chưa dùng bản này để xác nhận tiến độ tốt nghiệp cho hồ sơ."})
        represented = {str(row["curriculum_version"]) for row in result if row["audit_available"]}
        # The manually normalized ET1-2022 snapshot is not part of the newer
        # public-extraction folder. Include it rather than hiding an active version.
        for program_code, year in curriculum_repository.available_keys:
            if program_code != code:
                continue
            dataset = curriculum_repository.get(program_code, year)
            version = str(dataset["program"]["curriculum_version"])
            if version in represented:
                continue
            represented.add(version)
            course_map = {c["code"]: c for c in dataset["courses"]}
            result.append({
                "id": f"{code}-{version}", "program_code": code, "name": dataset["program"]["name"],
                "curriculum_version": version, "applies_to_cohorts": dataset.get("applies_to_cohorts") or
                [f"K{int(y) - 1955}" for c, y in curriculum_repository.available_keys
                 if c == code and curriculum_repository.get(c, y)["program"]["curriculum_version"] == version],
                "total_credits": dataset["program"]["total_required_credits"], "source_url": None,
                "course_count": len(course_map), "audit_available": True, "usage": "audit_and_reference",
                "scope_note": None, "graduation_rule": dataset["graduation_paths"][0]["raw_expression"],
                "notes": dataset.get("build_warnings", []),
                "groups": [{"name": g["name"], "required_credits": None,
                            "courses": [course_map[c] for c in g["course_codes"]]} for g in dataset["groups"]],
            })
        return result


program_catalog = ProgramCatalog()
