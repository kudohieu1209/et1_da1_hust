from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = DATA_DIR.parent
SCRIPTS_DIR = DATA_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from import_official_curricula import (
    AUTO_APPROVER,
    AUTO_LABEL,
    CheckFailed,
    build_dataset,
    check_undergraduate,
    drop_conflicts,
    sanitize_source,
)
from validate_curriculum import validate_curriculum


CATALOG = {
    "AA1001": {"code": "AA1001", "name": "Toán A", "credits": 4, "department": "T", "raw_condition": ""},
    "AA1002": {"code": "AA1002", "name": "Toán B", "credits": 4, "department": "T", "raw_condition": "AA1001(!)"},
    "AA2001": {"code": "AA2001", "name": "Cơ sở", "credits": 3, "department": "K", "raw_condition": ""},
    "AA2002": {"code": "AA2002", "name": "Cơ sở 2", "credits": 3, "department": "K", "raw_condition": ""},
    "AA4001": {"code": "AA4001", "name": "Mô-đun A", "credits": 3, "department": "K", "raw_condition": ""},
    "AA4002": {"code": "AA4002", "name": "Mô-đun B", "credits": 3, "department": "K", "raw_condition": ""},
    "PE1010": {"code": "PE1010", "name": "Thể dục", "credits": 0, "department": "GDTC", "raw_condition": ""},
}


def _course(code: str, credits: float | None) -> dict:
    return {"code": code, "name": CATALOG.get(code, {}).get("name", code), "credits": credits,
            "suggested_semester": 1, "compulsory": None}


def _source(**overrides) -> dict:
    raw = {
        "admission_code": "AA1",
        "name": "Ngành thử nghiệm",
        "curriculum_version": "2023",
        "applies_to_cohorts": None,
        "total_credits": 14,
        "source_url": "https://example.hust.edu.vn/ctdt",
        "retrieved_at": "2026-10-27",
        "graduation_rule": None,
        "notes": [],
        "groups": [
            {"name": "Toán", "kind": "block", "required_credits": 8, "counts_toward_degree": True,
             "courses": [_course("AA1001", 4), _course("AA1002", 4)]},
            {"name": "Cơ sở", "kind": "block", "required_credits": 3, "counts_toward_degree": True,
             "courses": [_course("AA2001", 3), _course("AA2002", 3)]},
            {"name": "Giáo dục thể chất", "kind": "block", "required_credits": None,
             "counts_toward_degree": False, "courses": [_course("PE1010", 1), _course("PExxxx", None)]},
            {"name": "Mô đun 1", "kind": "module", "required_credits": 3, "counts_toward_degree": True,
             "courses": [_course("AA4001", 3)]},
            {"name": "Mô đun 2", "kind": "module", "required_credits": 3, "counts_toward_degree": True,
             "courses": [_course("AA4002", 3)]},
        ],
    }
    raw.update(overrides)
    return raw


def _build(raw: dict) -> dict:
    return build_dataset(raw, "data/raw/official_curricula/AA1-2023.json", "0" * 64, CATALOG)


class ImportOfficialCurriculaTest(unittest.TestCase):
    def test_consistent_curriculum_is_normalized(self) -> None:
        data = _build(_source())
        path = data["graduation_paths"][0]
        self.assertEqual(["GROUP_CREDITS", "GROUP_CREDITS", "ONE_OF_GROUPS"],
                         [c["type"] for c in path["components"]])
        self.assertEqual(14, path["total_required_credits"])
        courses = {c["code"]: c for c in data["courses"]}
        self.assertTrue(courses["AA1001"]["is_compulsory"])  # block offers exactly its minimum
        self.assertFalse(courses["AA2001"]["is_compulsory"])  # 3 of 6 TC are electives
        self.assertEqual("AA1001", courses["AA1002"]["registration_condition"]["any_of"][0]["all_of"][0]["course_code"])
        self.assertNotIn("PExxxx", courses)
        self.assertIn(AUTO_LABEL, data["build_warnings"][0])

    def test_sum_of_thresholds_must_equal_published_total(self) -> None:
        with self.assertRaisesRegex(CheckFailed, "khác tổng công bố"):
            _build(_source(total_credits=15))

    def test_missing_total_or_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(CheckFailed, "tổng số TC"):
            _build(_source(total_credits=None))
        with self.assertRaisesRegex(CheckFailed, "phiên bản"):
            _build(_source(curriculum_version=None))

    def test_cohorts_give_lookup_year_when_version_is_missing(self) -> None:
        data = _build(_source(curriculum_version=None, applies_to_cohorts=["K69", "K68"]))
        self.assertEqual("2023", data["program"]["curriculum_version"])
        self.assertEqual(["K68", "K69"], data["applies_to_cohorts"])
        self.assertTrue(any("khóa sớm nhất" in w for w in data["build_warnings"]))

    def test_credit_mismatch_with_ctt_is_rejected(self) -> None:
        raw = _source()
        raw["groups"][0]["courses"][0]["credits"] = 3
        with self.assertRaisesRegex(CheckFailed, "CTT ghi 4 TC"):
            _build(raw)

    def test_modules_with_different_thresholds_are_rejected(self) -> None:
        raw = _source()
        raw["groups"][4]["required_credits"] = 2
        with self.assertRaisesRegex(CheckFailed, "mô-đun"):
            _build(raw)

    def test_too_many_courses_outside_ctt_are_rejected(self) -> None:
        raw = _source()
        raw["groups"][1]["courses"] += [_course("AA2003", 3), _course("AA2004", 3)]
        with self.assertRaisesRegex(CheckFailed, "không có trong danh mục CTT"):
            _build(raw)

    def test_local_extraction_paths_are_removed_from_notes(self) -> None:
        raw = sanitize_source(_source(notes=["Trang 1", "Tệp C:\\Users\\a\\x.pdf", "data/official_curricula_k67_k70/a.pdf"]))
        self.assertEqual(["Trang 1"], raw["notes"])

    def test_programs_outside_the_undergraduate_catalog_are_rejected(self) -> None:
        check_undergraduate(_source(), {"AA1"})
        for code in ("M-AA1", "P-AA1", "E-AA1"):
            with self.assertRaises(CheckFailed):
                check_undergraduate(_source(admission_code=code), {"AA1"})

    def test_two_documents_for_the_same_cohort_are_both_rejected(self) -> None:
        first = _build(_source(applies_to_cohorts=["K68"]))
        second = _build(_source(curriculum_version="2024", applies_to_cohorts=["K68", "K69"]))
        accepted, rejected = {"a": first, "b": second}, {}
        drop_conflicts(accepted, rejected)
        self.assertEqual({}, accepted)
        self.assertEqual({"a", "b"}, set(rejected))

    def test_committed_automatic_datasets_validate_and_are_labelled(self) -> None:
        approvals = json.loads((DATA_DIR / "processed" / "curriculum_approvals.json").read_text(encoding="utf-8"))
        automatic = [a for a in approvals["approvals"] if a["approved_by"] == AUTO_APPROVER]
        for approval in automatic:
            with self.subTest(approval["candidate_id"]):
                self.assertIn(AUTO_LABEL, approval["notes"])
                data = json.loads((PROJECT_DIR / approval["output_file"]).read_text(encoding="utf-8"))
                errors, _ = validate_curriculum(data, PROJECT_DIR)
                self.assertEqual([], errors)
                self.assertIn(AUTO_LABEL, data["build_warnings"][0])


if __name__ == "__main__":
    unittest.main()
