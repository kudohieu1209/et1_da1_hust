"""Read-only repository for versioned curriculum datasets.

The file name is deliberately not part of the lookup contract. A curriculum is
identified by the program metadata contained in the validated JSON itself.
Lookup keys are (program_code, entry year of the cohort): K67 entered in 2022,
K68 in 2023, ... A dataset that lists ``applies_to_cohorts`` serves exactly
those cohorts; otherwise its curriculum_version is taken as the entry year.
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
            data["_dataset_file"] = str(path)
            for year in self._entry_years(data, version, path):
                key = (code, year)
                if key in curricula:
                    raise ValueError(f"Trùng curriculum {code} cho năm nhập học {year}: {path}")
                curricula[key] = data
            aliases[str(program.get("program_id", "")).upper()] = code
            aliases[code] = code
        self._curricula = curricula
        self._program_id_aliases = aliases

    @property
    def available_keys(self) -> list[Tuple[str, str]]:
        return sorted(self._curricula)

    def list_programs(self) -> list[Dict[str, Any]]:
        unique = {id(data): data for data in self._curricula.values()}
        return [dict(data["program"]) for data in unique.values()]

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
        if not program:
            program = self.infer_program_code(str(info.get("class_name", ""))) or ""
        stored_version = str(info.get("curriculum_version") or "")
        entry_year = self._infer_version(info)
        if not program:
            raise CurriculumNotFoundError("Hồ sơ sinh viên thiếu program_code/program_id.")
        if not (entry_year or stored_version):
            raise CurriculumNotFoundError(
                "Không xác định được phiên bản CTĐT từ hồ sơ sinh viên."
            )
        curriculum = self.get(program, entry_year or stored_version)
        actual_version = str(curriculum["program"]["curriculum_version"])
        if entry_year and stored_version and stored_version != actual_version:
            # A cohort must not silently use a different curriculum snapshot
            # just because an old profile contains a stale explicit version.
            raise CurriculumNotFoundError(
                f"Hồ sơ {info.get('student_id', '')} thuộc khóa {entry_year} "
                f"nhưng đang trỏ tới CTĐT {stored_version}."
            )
        return curriculum

    @staticmethod
    def infer_program_code(class_name: str) -> Optional[str]:
        """Tự động suy luận mã CTĐT (program_code) từ tên lớp của sinh viên."""
        if not class_name:
            return None
        import unicodedata
        for code in ["BF-E19", "TE-EP", "BF1", "BF2", "ED2", "EE1", "EE2", "ET1", "ET2", "EV1", "EV2", "FL2", "FL3", "ME1", "MS1"]:
            if re.search(rf"\b{re.escape(code)}\b", class_name, re.I):
                return code
        folded = unicodedata.normalize("NFD", class_name.lower().replace("đ", "d"))
        folded = " ".join("".join(c for c in folded if not unicodedata.combining(c)).split()).strip(" :")
        if "pfiev" in folded or "hang khong" in folded:
            return "TE-EP"
        if "co dien tu" in folded:
            return "ME1"
        if "y sinh" in folded:
            return "ET2"
        if "dien tu" in folded or "vien thong" in folded or "dtvt" in folded:
            return "ET1"
        if ("sinh hoc" in folded or "bf" in folded) and ("tien tien" in folded or "elitech" in folded or "e19" in folded):
            return "BF-E19"
        if "sinh hoc" in folded:
            return "BF1"
        if "thuc pham" in folded:
            return "BF2"
        if "giao duc" in folded:
            return "ED2"
        if "tu dong" in folded or "dieu khien" in folded or "tdh" in folded:
            return "EE2"
        if "ky thuat dien" in folded or "he thong dien" in folded or "dien luc" in folded or re.search(r"\bdien\s+\d", folded):
            return "EE1"
        if "tai nguyen" in folded:
            return "EV2"
        if "moi truong" in folded:
            return "EV1"
        if "tieng trung" in folded:
            return "FL3"
        if "tieng anh" in folded or "anh van" in folded:
            return "FL2"
        if "vat lieu" in folded:
            return "MS1"
        return None

    def supports_profile(self, profile: Dict[str, Any]) -> bool:
        try:
            self.resolve_profile(profile)
            return True
        except CurriculumNotFoundError:
            return False

    @staticmethod
    def _entry_years(data: Dict[str, Any], version: str, path: Path) -> list[str]:
        years = []
        for cohort in data.get("applies_to_cohorts") or []:
            match = re.fullmatch(r"K(\d{2})", str(cohort).strip().upper())
            if not match:
                raise ValueError(f"Khóa áp dụng không hợp lệ {cohort!r}: {path}")
            years.append(str(1955 + int(match.group(1))))
        return sorted(set(years)) or [version]

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
