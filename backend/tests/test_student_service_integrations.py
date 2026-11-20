"""Kiểm thử tích hợp các dịch vụ sinh viên:
1. CTT DevExpress Parser & Scraper Service
2. Course Improvement Engine (Tính toán cải thiện CPA)
3. Campus Locations & GIS Navigation Service
4. Student Service & Chatbot Intent Routing
"""

import unittest
from unittest.mock import patch

from app.core.hust_rules import GRADE_TO_SCALE4
from app.engine.improve_engine import course_improvement_engine
from app.services.campus_service import campus_service
from app.services.chatbot_service import chatbot_service
from app.services.ctt_service import ctt_parser
from app.services.data_loader import data_loader
from app.services.student_service import student_service


MOCK_DEVEXPRESS_HTML = """
<html>
<body>
<table id="ctl00_ctl00_contentPane_MainPanel_MainContent_gvResults_DXMainTable" class="dxgvTable">
    <tr class="dxgvGroupRow">
        <td colspan="8">Học kỳ: 2023.1 - GPA: 2.80 - CPA: 2.80</td>
    </tr>
    <tr class="dxgvDataRow">
        <td class="dxgv">1</td>
        <td class="dxgv">ET2030</td>
        <td class="dxgv">Kỹ thuật lập trình</td>
        <td class="dxgv">3.0</td>
        <td class="dxgv">7.0</td>
        <td class="dxgv">8.0</td>
        <td class="dxgv">B</td>
    </tr>
    <tr class="dxgvDataRow">
        <td class="dxgv">2</td>
        <td class="dxgv">ET3220</td>
        <td class="dxgv">Điện tử số</td>
        <td class="dxgv">3.0</td>
        <td class="dxgv">4.0</td>
        <td class="dxgv">4.5</td>
        <td class="dxgv">D</td>
    </tr>
    <tr class="dxgvDataRow">
        <td class="dxgv">3</td>
        <td class="dxgv">ET2050</td>
        <td class="dxgv">Lý thuyết mạch</td>
        <td class="dxgv">3.0</td>
        <td class="dxgv">3.0</td>
        <td class="dxgv">3.5</td>
        <td class="dxgv">F</td>
    </tr>
</table>
</body>
</html>
"""


def _course(code, grade, credits=3.0):
    return {
        "code": code, "name": code, "credits": credits, "letter_grade": grade,
        "numeric_grade": GRADE_TO_SCALE4[grade], "is_passed": grade != "F",
    }


class TestStudentServiceIntegrations(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")

    def test_devexpress_parser_extracts_courses_and_grades(self):
        result = ctt_parser.parse_transcript_html(MOCK_DEVEXPRESS_HTML)
        transcript = result.get("transcript", [])
        self.assertEqual(len(transcript), 3)

        et2030 = next((c for c in transcript if c["code"] == "ET2030"), None)
        self.assertIsNotNone(et2030)
        self.assertEqual(et2030["credits"], 3.0)
        self.assertEqual(et2030["letter_grade"], "B")
        self.assertEqual(et2030["semester"], "2023.1")
        self.assertTrue(et2030["is_passed"])

        et2050 = next((c for c in transcript if c["code"] == "ET2050"), None)
        self.assertIsNotNone(et2050)
        self.assertEqual(et2050["letter_grade"], "F")
        self.assertFalse(et2050["is_passed"])

    def test_course_improvement_engine_identifies_f_and_d_courses(self):
        profile = {
            "info": {"cpa": 2.20},
            "passed_courses": [
                {"code": "ET3220", "name": "Điện tử số", "credits": 3.0, "letter_grade": "D", "numeric_grade": 1.0},
                {"code": "ET2030", "name": "Kỹ thuật lập trình", "credits": 3.0, "letter_grade": "B", "numeric_grade": 3.0},
            ],
            "failed_courses": [
                {"code": "ET2050", "name": "Lý thuyết mạch", "credits": 3.0, "letter_grade": "F", "numeric_grade": 0.0},
            ],
            "transcript": [
                {"code": "ET3220", "name": "Điện tử số", "credits": 3.0, "letter_grade": "D", "numeric_grade": 1.0},
                {"code": "ET2030", "name": "Kỹ thuật lập trình", "credits": 3.0, "letter_grade": "B", "numeric_grade": 3.0},
                {"code": "ET2050", "name": "Lý thuyết mạch", "credits": 3.0, "letter_grade": "F", "numeric_grade": 0.0},
            ]
        }
        res = course_improvement_engine.analyze_improvements(profile)
        candidates = res.get("improve_candidates", [])
        self.assertEqual([course["category"] for course in candidates], ["retake", "improve_low", "improve"])

        # Môn F phải có priority HIGH
        f_course = next(c for c in candidates if c["code"] == "ET2050")
        self.assertEqual(f_course["priority"], "HIGH")
        self.assertTrue(f_course["is_failed"])

        # Phải tính toán được delta CPA cho mục tiêu B
        proj = f_course["projections"]["B"]
        self.assertEqual(proj, {"delta_cpa": 1.0, "new_cpa": 2.33})

    def test_passing_retake_is_an_optional_improvement(self):
        failed = _course("ET2050", "F")
        passed = _course("ET2050", "D")
        result = course_improvement_engine.analyze_improvements({
            "transcript": [failed, passed], "failed_courses": [failed],
        })
        course, = result["improve_candidates"]
        self.assertFalse(course["is_failed"])
        self.assertEqual(course["category"], "improve_low")
        self.assertEqual(course["current_letter_grade"], "D")

    def test_c_course_can_improve_and_a_is_excluded(self):
        result = course_improvement_engine.analyze_improvements({
            "transcript": [_course("ET2050", "C"), _course("ET2030", "A")],
        })
        course, = result["improve_candidates"]
        self.assertEqual(course["code"], "ET2050")
        self.assertEqual(course["category"], "improve")
        self.assertEqual(set(course["projections"]), {"C+", "B", "B+", "A"})

    def test_improvement_cpa_matches_degree_audit_with_repeats_and_pe(self):
        failed = _course("ET2050", "F")
        passed = [_course("ET2050", "D"), _course("ET2030", "B", 4), _course("PE1015", "A", 2)]
        profile = {
            "info": {"cpa": 3.99}, "failed_courses": [failed],
            "transcript": [failed, *passed], "passed_courses": passed,
        }
        with patch.object(data_loader, "get_student_profile", return_value=profile):
            audit = student_service.audit_degree()
            analysis = student_service.get_course_improvements()
        self.assertEqual(analysis["current_cpa"], audit["cpa"])
        self.assertEqual(analysis["current_cpa"], 2.14)
        self.assertEqual(analysis["cpa_credits"], 7.0)

    def test_honors_counts_each_failed_course_once_even_after_passing(self):
        recovered = _course("ET2050", "F")
        failed = _course("ET2030", "F")
        legacy = _course("ET3220", "F", 1)
        profile = {
            "failed_courses": [recovered, legacy],
            "transcript": [recovered, recovered, _course("ET2050", "D"), failed],
        }
        for required, threshold, exceeds in [(120, 6, True), (140, 7, False), (160, 8, False)]:
            with self.subTest(threshold=threshold):
                analysis = course_improvement_engine.analyze_improvements(profile, required)
                self.assertEqual(analysis["honors_rule"], {
                    "retake_credits": 7.0, "basis_credits": required, "threshold_credits": threshold,
                    "exceeds": exceeds, "basis_source": "program",
                })

    def test_honors_falls_back_to_transcript_credits_without_graduation_path(self):
        profile = {"transcript": [_course("ET2050", "F"), _course("ET2030", "B")]}
        with patch.object(student_service, "get_profile", return_value=profile), \
             patch.object(data_loader, "get_graduation_path", side_effect=LookupError):
            rule = student_service.get_course_improvements()["honors_rule"]
        self.assertEqual(rule["basis_source"], "transcript")
        self.assertEqual(rule["threshold_credits"], 0.30)

    def test_empty_transcript_uses_reported_cpa_without_candidates(self):
        result = course_improvement_engine.analyze_improvements({
            "info": {"cpa": 2.5}, "transcript": [], "failed_courses": [_course("ET2050", "F")],
        })
        self.assertFalse(result["has_transcript"])
        self.assertEqual(result["current_cpa"], 2.5)
        self.assertEqual(result["total_candidates"], 0)
        self.assertEqual(result["improve_candidates"], [])

    def test_campus_service_finds_buildings_and_generates_links(self):
        # Tìm tòa D3
        loc_d3 = campus_service.find_location("D3")
        self.assertIsNotNone(loc_d3)
        self.assertEqual(loc_d3.get("code"), "D3")
        self.assertIn("google.com/maps", loc_d3.get("google_maps_url", ""))

        # Tìm Thư viện Tạ Quang Bửu
        loc_lib = campus_service.find_location("Thư viện Tạ Quang Bửu")
        self.assertIsNotNone(loc_lib)
        self.assertIn("Tạ Quang Bửu", loc_lib.get("name", ""))

        reply = campus_service.format_direction_reply(loc_d3)
        self.assertIn("D3", reply)
        self.assertIn("http", reply)

    def test_chatbot_handles_campus_map_intent(self):
        res = chatbot_service.process_message("Nhà D3 ở đâu vậy bot?")
        self.assertEqual(res.get("intent"), "CAMPUS_NAVIGATION")
        self.assertIn("D3", res.get("reply", ""))
        self.assertIn("Google Maps", res.get("reply", ""))

    def test_chatbot_handles_course_improvement_intent(self):
        res = chatbot_service.process_message("Em nên học lại môn nào để cải thiện CPA?")
        self.assertEqual(res.get("intent"), "COURSE_IMPROVEMENT")
        self.assertIn("CPA", res.get("reply", ""))

    def test_chatbot_congratulates_student_with_only_c_and_b(self):
        profile = {"transcript": [_course("ET2050", "C"), _course("ET2030", "B")]}
        with patch.object(student_service, "get_profile", return_value=profile):
            result = chatbot_service.process_message("nên học cải thiện môn nào")
        self.assertEqual(result["intent"], "COURSE_IMPROVEMENT")
        self.assertIn("Chúc mừng", result["reply"])
        self.assertIn("Cải thiện điểm CPA", result["reply"])
        self.assertNotIn("ET2050", result["reply"])
        self.assertEqual(result["data_context"]["total_candidates"], 0)


if __name__ == "__main__":
    unittest.main()

