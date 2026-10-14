"""Kiểm thử khói cho các engine, chuyển từ script test_backend.py cũ."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.graph_engine import graph_engine
from app.engine.recommender import course_recommender
from app.engine.rule_engine import rule_engine
from app.services.chatbot_service import chatbot_service
from app.services.data_loader import data_loader
from app.services.student_service import student_service


class EngineSmokeTests(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")

    def test_data_loader_has_courses_and_rules(self):
        self.assertGreater(len(data_loader.get_all_courses()), 0)
        self.assertGreater(len(data_loader.get_all_rules()), 0)

    def test_design_projects_one_and_two_can_be_taken_together(self):
        result = rule_engine.check_eligibility("ET4010", concurrent_codes=["ET3290"])
        self.assertTrue(result["is_eligible"])

    def test_failing_component_course_blocks_downstream_chain(self):
        impact = graph_engine.get_impact_analysis("ET2040")
        self.assertGreater(impact["total_blocked"], 0)

    def test_degree_audit_reports_progress_against_curriculum_total(self):
        audit = student_service.audit_degree()
        self.assertEqual(audit["total_credits_required"], 126)
        self.assertGreaterEqual(audit["completion_percentage"], 0)

    def test_recommender_suggests_ic_design_courses(self):
        recommendation = course_recommender.recommend(target_track="IC_DESIGN", max_credits=20)
        self.assertGreater(len(recommendation["recommended_courses"]), 0)

    def test_chatbot_confirms_design_projects_together(self):
        reply = chatbot_service.process_message("Kỳ này mình học đồ án 1 và 2 cùng lúc được không bạn?")
        self.assertIn("ĐƯỢC PHÉP", reply["reply"])

    def test_chatbot_recommends_courses_for_ic_track(self):
        response = chatbot_service.process_message(
            "Mình muốn theo hướng Thiết kế Vi mạch thì kỳ tới nên chọn những môn nào?"
        )
        self.assertEqual(response["intent"], "COURSE_RECOMMENDATION")
        self.assertGreater(len(response["data_context"]["recommended_courses"]), 0)


if __name__ == "__main__":
    unittest.main()
