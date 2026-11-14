"""Kiểm thử bộ tích hợp nâng cấp kiến trúc iLoveBK:
1. CTT DevExpress Parser & Scraper Service
2. Course Improvement Engine (Tính toán cải thiện CPA)
3. Campus Locations & GIS Navigation Service
4. Student Service & Chatbot Intent Routing
"""

import unittest
from pathlib import Path

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


class TestIlovebkIntegrations(unittest.TestCase):
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
        self.assertGreaterEqual(len(candidates), 2)

        # Môn F phải có priority HIGH
        f_course = next(c for c in candidates if c["code"] == "ET2050")
        self.assertEqual(f_course["priority"], "HIGH")
        self.assertTrue(f_course["is_failed"])

        # Phải tính toán được delta CPA cho mục tiêu B
        proj = f_course["projections"]["B"]
        self.assertGreater(proj["delta_cpa"], 0)
        self.assertGreater(proj["new_cpa"], 2.20)

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


if __name__ == "__main__":
    unittest.main()

