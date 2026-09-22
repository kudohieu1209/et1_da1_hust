import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.graph_engine import graph_engine
from app.engine.recommender import course_recommender
from app.engine.rule_engine import rule_engine
from app.services.chatbot_service import chatbot_service
from app.services.auth_service import auth_service
from app.services.curriculum_repository import (
    CurriculumNotFoundError,
    curriculum_repository,
)
from app.services.data_loader import data_loader
from app.services.student_service import student_service


class VersionedCurriculumTests(unittest.TestCase):
    def setUp(self):
        if data_loader.current_student_id != "20220001":
            data_loader.load_student_profile("20220001")

    def tearDown(self):
        if data_loader.current_student_id != "20220001":
            data_loader.load_student_profile("20220001")

    def test_program_can_be_looked_up_by_code_or_ctt_id(self):
        by_code = curriculum_repository.get("ET1", "2022")
        by_id = curriculum_repository.get("1654", "2022")
        self.assertIs(by_code, by_id)
        self.assertEqual(by_code["program"]["total_required_credits"], 126)

    def test_loader_uses_normalized_courses_not_draft_values(self):
        self.assertEqual(len(data_loader.get_all_courses()), 117)
        self.assertEqual(data_loader.get_course("ET2040")["credits"], 3)
        self.assertEqual(data_loader.get_course("ET3260")["credits"], 2)
        self.assertEqual(
            [item["id"] for item in data_loader.get_course_modules("ET4230")],
            ["MOD1", "MOD2", "MOD5"],
        )

    def test_six_official_module_alternatives_are_exposed(self):
        tracks = data_loader.get_module_tracks()
        self.assertEqual([track["id"] for track in tracks], [f"MOD{i}" for i in range(1, 7)])
        self.assertTrue(all(track["required_credits"] == 15 for track in tracks))
        self.assertEqual(tracks[4]["catalog_credits"], 16)

    def test_audit_uses_curriculum_formula_and_separates_english(self):
        audit = student_service.audit_degree()
        self.assertEqual(audit["curriculum"]["program_code"], "ET1")
        self.assertEqual(audit["curriculum"]["curriculum_version"], "2022")
        self.assertEqual(audit["total_credits_required"], 126)
        one_of = next(
            item for item in audit["graduation_group_audit"]
            if item["type"] == "ONE_OF_GROUPS"
        )
        self.assertEqual(len(one_of["options"]), 6)
        english = next(
            item for item in audit["non_credit_requirements"]
            if item["name"] == "Tiếng Anh"
        )
        self.assertEqual(english["course_codes"], ["FL1131", "FL1132"])

    def test_rule_engine_preserves_or_semantics(self):
        self.assertTrue(
            rule_engine.check_eligibility("ET3210", simulated_passed_codes=["PH1120"])["is_eligible"]
        )
        self.assertTrue(
            rule_engine.check_eligibility("ET3210", simulated_passed_codes=["PH1122"])["is_eligible"]
        )
        self.assertFalse(
            rule_engine.check_eligibility("ET3210", simulated_passed_codes=[])["is_eligible"]
        )

    def test_blocked_or_requirement_keeps_alternatives_separate(self):
        result = rule_engine.check_eligibility("ET4230", simulated_passed_codes=[])
        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["missing_prior_courses"], [])
        self.assertEqual(
            [branch["missing_prior_courses"] for branch in result["missing_alternative_branches"]],
            [["ET3200"], ["ET4070"]],
        )
        self.assertIn("không cần hoàn thành tất cả", " ".join(result["reasons"]))

    def test_repeat_followup_reuses_previous_course_question(self):
        response = chatbot_service.process_message(
            "trả lời lại đi bạn",
            history=[
                {"role": "user", "content": "điều học môn hệ điều hành"},
                {"role": "assistant", "content": "Mình đang kiểm tra môn ET4291."},
            ],
        )
        self.assertEqual(response["intent"], "COURSE_ELIGIBILITY_CHECK")
        self.assertIn("ET4291", response["reply"])
        self.assertIn("Hệ điều hành", response["reply"])
        self.assertNotIn("Nhánh", response["reply"])

    def test_unknown_external_condition_code_is_explained_without_empty_name(self):
        response = chatbot_service.process_message("điều kiện học môn cơ sở truyền số liệu")
        self.assertIn("MI2036", response["reply"])
        self.assertIn("chưa có tên trong danh mục CTĐT ET1–2022", response["reply"])
        self.assertNotIn("MI2036` ()", response["reply"])

    def test_graph_does_not_call_one_or_branch_a_hard_block(self):
        impact = graph_engine.get_impact_analysis("PH1120")
        self.assertNotIn("ET3210", {item["code"] for item in impact["direct_blocked_courses"]})
        self.assertIn("ET3210", {item["code"] for item in impact["direct_at_risk_courses"]})

    def test_k68_profile_resolves_to_et1_2023(self):
        data_loader.load_student_profile("20231890")
        self.assertEqual(data_loader.current_student_id, "20231890")
        self.assertEqual(data_loader.get_program()["curriculum_version"], "2023")
        self.assertEqual(data_loader.get_program()["total_required_credits"], 132)
        self.assertEqual(len(data_loader.get_module_tracks()), 5)

    def test_k68_login_activates_matching_curriculum(self):
        result = auth_service.login({"student_id": "20231890", "password": "123456"})
        self.assertTrue(result["success"])
        self.assertEqual(result["user"]["info"]["curriculum_version"], "2023")
        self.assertEqual(data_loader.get_program()["curriculum_version"], "2023")

    def test_recommender_accepts_official_module_id(self):
        recommendation = course_recommender.recommend(target_track="MOD6", max_credits=20)
        self.assertEqual(recommendation["target_track"], "MOD6")
        self.assertIn("Mô đun 6", recommendation["track_name"])


if __name__ == "__main__":
    unittest.main()
