"""Read-only repository for versioned curriculum datasets.

The file name is deliberately not part of the lookup contract. A curriculum is
identified by the program metadata contained in the validated JSON itself.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.core.config import CURRICULA_DIR


class CurriculumNotFoundError(LookupError):
    """Raised when a student profile has no matching, verified curriculum."""


class CurriculumRepository:
    def __init__(self, curricula_dir: Path = CURRICULA_DIR):
        self.curricula_dir = Path(curricula_dir)
        self._curricula: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._program_id_aliases: Dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        curricula: Dict[Tuple[str, str], Dict[str, Any]] = {}
        aliases: Dict[str, str] = {}
        for path in sorted(self.curricula_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
            program = data.get("program", {})
            code = str(program.get("program_code", "")).upper()
            version = str(program.get("curriculum_version", ""))
            if not code or not version or not isinstance(data.get("courses"), list):
                raise ValueError(f"Curriculum không hợp lệ: {path}")
            key = (code, version)
            if key in curricula:
                raise ValueError(f"Trùng curriculum {code}-{version}: {path}")
            data["_dataset_file"] = str(path)
            curricula[key] = data
            aliases[str(program.get("program_id", "")).upper()] = code
            aliases[code] = code
        self._curricula = curricula
        self._program_id_aliases = aliases

    @property
    def available_keys(self) -> list[Tuple[str, str]]:
        return sorted(self._curricula)

    def list_programs(self) -> list[Dict[str, Any]]:
        return [dict(data["program"]) for data in self._curricula.values()]

    def get(self, program: str, version: str) -> Dict[str, Any]:
        code = self._program_id_aliases.get(str(program).upper(), str(program).upper())
        try:
            return self._curricula[(code, str(version))]
        except KeyError as exc:
            available = ", ".join(f"{c}-{v}" for c, v in self.available_keys) or "chưa có"
            raise CurriculumNotFoundError(
                f"Chưa có dữ liệu CTĐT đã kiểm chứng cho {code}-{version}. "
                f"Hiện hỗ trợ: {available}."
            ) from exc

    def resolve_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        info = profile.get("info", {})
        program = str(info.get("program_code") or info.get("program_id") or "").upper()
        version = str(info.get("curriculum_version") or "")
        inferred_version = self._infer_version(info)
        if not version:
            version = inferred_version or ""
        elif inferred_version and version != inferred_version:
            # A cohort must not silently use a different curriculum snapshot
            # just because an old profile contains a stale explicit version.
            raise CurriculumNotFoundError(
                f"Hồ sơ {info.get('student_id', '')} thuộc khóa {inferred_version} "
                f"nhưng đang trỏ tới CTĐT {version}."
            )
        if not program:
            raise CurriculumNotFoundError("Hồ sơ sinh viên thiếu program_code/program_id.")
        if not version:
            raise CurriculumNotFoundError(
                "Không xác định được phiên bản CTĐT từ hồ sơ sinh viên."
            )
        return self.get(program, version)

    def supports_profile(self, profile: Dict[str, Any]) -> bool:
        try:
            self.resolve_profile(profile)
            return True
        except CurriculumNotFoundError:
            return False

    @staticmethod
    def _infer_version(info: Dict[str, Any]) -> Optional[str]:
        class_name = str(info.get("class_name", ""))
        cohort_match = re.search(r"\bK(\d{2})\b", class_name, re.IGNORECASE)
        if cohort_match:
            # K67 entered in 2022, K68 in 2023, ...
            return str(1955 + int(cohort_match.group(1)))

        program_name = str(info.get("program_name", ""))
        year_match = re.search(r"\b(20\d{2})\b", program_name)
        if year_match:
            return year_match.group(1)
        return None


curriculum_repository = CurriculumRepository()
