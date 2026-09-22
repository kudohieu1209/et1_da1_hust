from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = DATA_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_curriculum import build_curriculum, parse_condition
from build_hust_curriculum_candidates import build_candidates
from discover_hust_curriculum_sources import extract_curriculum_link
from extract_hust_curriculum_tables import _summary_hp_tc, parse_generic_table
from extract_hust_curriculum_pdfs import parse_course_list
from download_hust_curriculum_sources import _attachment_links
from validate_curriculum import validate_curriculum


class CurriculumPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = build_curriculum(
            DATA_DIR / "raw" / "et1_curiculum.html",
            DATA_DIR / "raw" / "ctt_et_conditions.json",
            "ET1",
        )
        cls.groups = {item["id"]: item for item in cls.data["groups"]}
        cls.courses = {item["code"]: item for item in cls.data["courses"]}
        cls.bachelor = next(
            item for item in cls.data["graduation_paths"] if item["id"] == "bachelor"
        )

    def test_program_identity_and_total_are_read_from_ctt(self) -> None:
        self.assertEqual("1654", self.data["program"]["program_id"])
        self.assertEqual("ET1", self.data["program"]["program_code"])
        self.assertEqual("2022", self.data["program"]["curriculum_version"])
        self.assertEqual(126, self.data["program"]["total_required_credits"])

    def test_bachelor_credit_formula(self) -> None:
        scalar = {
            item["group_id"]: item["required_credits"]
            for item in self.bachelor["components"]
            if item["type"] == "GROUP_CREDITS"
        }
        self.assertEqual(
            {
                "group_210": 13,
                "group_250": 32,
                "group_300": 52,
                "group_320": 6,
                "group_360": 2,
                "group_7": 6,
            },
            scalar,
        )

    def test_six_modules_are_alternatives(self) -> None:
        choice = next(
            item for item in self.bachelor["components"] if item["type"] == "ONE_OF_GROUPS"
        )
        self.assertEqual(15, choice["required_credits"])
        self.assertEqual(
            [f"group_{code}" for code in range(400, 406)],
            [item["group_id"] for item in choice["options"]],
        )
        self.assertEqual(16, self.groups["group_404"]["catalog_credits"])

    def test_english_is_non_credit(self) -> None:
        english = self.groups["group_240"]
        self.assertEqual("Tiếng Anh", english["name"])
        self.assertEqual(0, english["catalog_credits"])
        self.assertFalse(english["counts_toward_degree_credits"])
        self.assertEqual(["FL1131", "FL1132"], english["course_codes"])

    def test_known_course_values_come_from_ctt(self) -> None:
        self.assertEqual(3, self.courses["ET2040"]["credits"])
        self.assertEqual(2, self.courses["ET3260"]["credits"])
        self.assertEqual(
            ["group_400", "group_401", "group_403", "group_404"],
            self.courses["ET3310"]["group_ids"],
        )

    def test_condition_parser_preserves_or_and_semantics(self) -> None:
        parsed = parse_condition("ET2040!/ET2042!")
        self.assertEqual(2, len(parsed["any_of"]))
        self.assertEqual(
            {"course_code": "ET2040", "relation": "PREREQUISITE"},
            parsed["any_of"][0]["all_of"][0],
        )
        parsed = parse_condition("ET3290,ET4010=")
        self.assertEqual(2, len(parsed["any_of"][0]["all_of"]))
        self.assertEqual("COREQUISITE", parsed["any_of"][0]["all_of"][1]["relation"])

    def test_output_does_not_copy_student_identity(self) -> None:
        serialized = json.dumps(self.data, ensure_ascii=False)
        self.assertNotIn("20220001", serialized)
        self.assertNotIn("Mai Duy Hiếu", serialized)
        self.assertFalse(self.data["sources"][0]["personal_data_included_in_output"])

    def test_validator_accepts_generated_dataset(self) -> None:
        errors, _warnings = validate_curriculum(self.data, project_dir=DATA_DIR.parent)
        self.assertEqual([], errors)

    def test_curriculum_source_link_is_taken_from_curriculum_tab(self) -> None:
        html = """
        <section id="tab_2">
          <a href="#contents">Mục lục</a>
          <a href="https://faculty.example.edu/et1">XEM TẠI ĐÂY</a>
        </section>
        """
        self.assertEqual(
            "https://faculty.example.edu/et1",
            extract_curriculum_link(html, "https://ts.hust.edu.vn/program/et1"),
        )

    def test_curriculum_source_manifest_covers_catalog(self) -> None:
        manifest = json.loads(
            (DATA_DIR / "raw" / "hust_program_curriculum_sources.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(68, manifest["count"])
        self.assertEqual(68, manifest["with_source_link"])
        self.assertEqual(68, len(manifest["records"]))

    def test_public_html_candidate_keeps_et1_separate_from_verified_2022(self) -> None:
        extraction = json.loads(
            (DATA_DIR / "raw" / "hust_curriculum_extractions.json").read_text(
                encoding="utf-8"
            )
        )
        et1 = next(item for item in extraction["records"] if item["admission_code"] == "ET1")
        self.assertEqual("2023", et1["curriculum_version"])
        self.assertEqual(132, et1["total_credits_published"])
        self.assertEqual(79, len(et1["courses"]))
        self.assertNotEqual("processed/curricula/et1_2022.json", et1["file"])

    def test_public_summary_keeps_catalog_and_required_credits_separate(self) -> None:
        self.assertEqual((34, 87), _summary_hp_tc("34 HP · 87 TC"))
        extraction = json.loads(
            (DATA_DIR / "raw" / "hust_curriculum_extractions.json").read_text(
                encoding="utf-8"
            )
        )
        et16 = next(item for item in extraction["records"] if item["admission_code"] == "ET-E16")
        core = next(item for item in et16["groups"] if item["id"] == "group_khoi_2")
        self.assertEqual(87, core["published_catalog_credits"])
        self.assertEqual(22, core["required_credits"])

    def test_generic_html_table_is_extracted_conservatively(self) -> None:
        html = """
        <table><tr><th>Mã</th><th>Tên</th><th>Tín chỉ</th></tr>
        <tr><td>ET1000</td><td>Nhập môn</td><td>3(2-1-0-6)</td></tr>
        <tr><td>ET1001</td><td>Mạch điện</td><td>4</td></tr>
        <tr><td>ET1002</td><td>Tín hiệu</td><td>3(3-0-0-6)</td></tr></table>
        """
        parsed = parse_generic_table(html)
        self.assertEqual(["ET1000", "ET1001", "ET1002"], [item["code"] for item in parsed])
        self.assertEqual([3, 4, 3], [item["credits"] for item in parsed])

    def test_pdf_course_list_keeps_module_groups(self) -> None:
        section = """
        Danh mục học phần
        Lý luận chính trị + Pháp luật đại cương                 13
        1 SSH1111 Triết học Mác - Lênin 3(3-0-0-6) 3
        Mô đun 1: Hệ thống nhúng                                  16
        2 ET4210 Hệ nhúng 3(3-0-1-6) 3
        3 ET4735 IoT và ứng dụng 2(2-1-0-4) 2
        """
        groups, courses, warnings = parse_course_list(section)
        self.assertFalse(warnings)
        self.assertEqual(["SSH1111", "ET4210", "ET4735"], [item["code"] for item in courses])
        module = next(group for group in groups if group["kind"] == "module")
        self.assertEqual(["ET4210", "ET4735"], module["course_codes"])

    def test_downloaded_it1_pdf_has_version_and_course_list(self) -> None:
        extraction = json.loads(
            (DATA_DIR / "raw" / "hust_curriculum_pdf_extractions.json").read_text(
                encoding="utf-8"
            )
        )
        it1 = next(item for item in extraction["records"] if item["admission_code"] == "IT1")
        self.assertEqual("2017", it1["curriculum_version"])
        self.assertEqual(136, it1["total_credits_published"])
        self.assertIn("IT3940", {course["code"] for course in it1["courses"]})

    def test_attachment_discovery_resolves_relative_curriculum_files(self) -> None:
        html = '<a href="/files/CTDT-IT1.pdf">CTĐT</a><a href="/logo.png">logo</a>'
        self.assertEqual(
            ["https://faculty.example.edu/files/CTDT-IT1.pdf"],
            _attachment_links(html, "https://faculty.example.edu/dao-tao/it1"),
        )

    def test_candidates_record_the_explicit_et1_2023_approval(self) -> None:
        candidates = build_candidates(
            DATA_DIR / "raw" / "hust_curriculum_extractions.json",
            DATA_DIR / "raw" / "ctt_course_catalog_all.json",
        )
        self.assertEqual("hust-curriculum-candidates.v1", candidates["schema_version"])
        # The public-source inventory grows as retired faculty URLs are
        # replaced.  This assertion protects the original coverage without
        # making the approval test fail whenever more curricula are recovered.
        self.assertGreaterEqual(candidates["count"], 14)
        et1 = next(item for item in candidates["records"] if item["candidate_id"] == "ET1-2023")
        self.assertFalse(et1["quality"]["rule_engine_eligible"])
        self.assertIn("normalization_not_validated", et1["quality"]["review_reasons"])
        self.assertTrue(et1["quality"]["automatic_checks_passed"])
        self.assertEqual("approved", et1["activation"]["status"])
        self.assertTrue(et1["activation"]["rule_engine_eligible"])
        self.assertEqual(1, candidates["rule_engine_loaded"])
        self.assertEqual(79, et1["quality"]["ctt_course_rows_matched"])
        self.assertEqual(132, et1["quality"]["derived_one_module_total"])
        it1 = next(item for item in candidates["records"] if item["candidate_id"] == "IT1-2017")
        self.assertEqual("PUBLIC_HUST_CURRICULUM_PDF", it1["sources"][0]["kind"])


if __name__ == "__main__":
    unittest.main()
