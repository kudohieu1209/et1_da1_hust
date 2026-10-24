import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.hust_rules import (
    CREDIT_LIMITS,
    assess_academic_warning,
    parse_grade_from_line,
)
from app.engine.recommender import course_recommender
from app.services.chatbot_service import chatbot_service
from app.services.curriculum_repository import curriculum_repository
from app.services.data_loader import data_loader
from app.services.student_service import student_service


def _course(code, credits, letter, scale4):
    return {
        "code": code,
        "name": code,
        "credits": credits,
        "letter_grade": letter,
        "numeric_grade": scale4,
        "is_passed": letter != "F",
    }


class GradeParsingTests(unittest.TestCase):
    def test_plus_grades_are_not_truncated(self):
        self.assertEqual(parse_grade_from_line("ET3220 Điện tử số 3 B+"), "B+")
        self.assertEqual(parse_grade_from_line("ET4230 Mạng máy tính 3 C+ "), "C+")
        self.assertEqual(parse_grade_from_line("MI1111 Giải tích I 4 8.5 A+"), "A+")

    def test_course_name_letter_is_not_read_as_grade(self):
        self.assertEqual(parse_grade_from_line("IT3040 Ngôn ngữ C 3 A"), "A")

    def test_missing_grade_returns_none_instead_of_default(self):
        self.assertIsNone(parse_grade_from_line("MI1111 Giải tích I 4"))
        self.assertIsNone(parse_grade_from_line("IT3040 Ngôn ngữ C 3"))


class AcademicWarningTests(unittest.TestCase):
    def test_level_one_is_not_credit_limited(self):
        # Điều 19.2 QĐ 5445: chỉ mức 2 trở lên bị hạn chế 8-14 TC.
        self.assertEqual(CREDIT_LIMITS[1]["max"], CREDIT_LIMITS[0]["max"])
        self.assertEqual(CREDIT_LIMITS[2]["max"], 14)
        self.assertEqual(CREDIT_LIMITS[3]["max"], 14)
        self.assertEqual(CREDIT_LIMITS[3]["min"], 8)

    def test_declared_level_takes_priority(self):
        result = assess_academic_warning({"info": {"warning_level": 2}})
        self.assertEqual(result["level"], 2)

    def test_debt_over_24_credits_is_level_three(self):
        failed = [_course(f"ET{1000 + i}", 3.0, "F", 0.0) for i in range(9)]
        result = assess_academic_warning({"info": {}, "failed_courses": failed})
        self.assertEqual(result["debt_credits"], 27.0)
        self.assertEqual(result["level"], 3)

    def test_retaken_failed_course_is_not_debt(self):
        profile = {
            "info": {},
            "failed_courses": [_course("ET2040", 3.0, "F", 0.0)],
            "passed_courses": [_course("ET2040", 3.0, "C", 2.0)],
        }
        self.assertEqual(assess_academic_warning(profile)["debt_credits"], 0.0)

    def test_low_cpa_alone_does_not_trigger_warning(self):
        passed = [_course("ET2040", 3.0, "D", 1.0)]
        result = assess_academic_warning({"info": {}, "passed_courses": passed})
        self.assertIsNone(result["level"])
        self.assertEqual(result["status"], "unverified")


class ActiveProfileTestCase(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")
        self.base_profile = copy.deepcopy(data_loader.get_student_profile())

    def tearDown(self):
        data_loader.load_student_profile("20220001")

    def activate(self, profile):
        curriculum = curriculum_repository.resolve_profile(profile)
        data_loader._activate(profile, curriculum, "20220001")


class AuditTests(ActiveProfileTestCase):
    def _finish_curriculum(self, grade="C", scale4=2.0):
        profile = copy.deepcopy(self.base_profile)
        profile["transcript"] = [_course(c["code"], c["credits"], grade, scale4)
                                 for c in data_loader.get_all_courses()]
        profile["passed_courses"] = profile["transcript"]
        profile["failed_courses"] = []
        profile.pop("non_credit_status", None)
        self.activate(profile)
        return profile

    def test_no_remaining_credits_below_target_requires_improvement(self):
        self._finish_curriculum()
        audit = student_service.audit_degree()
        target = audit["target_kha_advice"]
        self.assertEqual(target["remaining_credits"], 0)
        self.assertIsNone(target["gpa_needed_remaining"])
        self.assertFalse(target["is_achievable"])
        self.assertEqual(target["status"], "requires_grade_improvement")
        reply = chatbot_service._handle_audit()["reply"]
        self.assertNotIn("GPA trung bình ~**0", reply)
        self.assertIn("học cải thiện", reply)

    def test_no_remaining_credits_above_target_is_already_achieved(self):
        self._finish_curriculum("B", 3.0)
        target = student_service.audit_degree()["target_kha_advice"]
        self.assertEqual(target["status"], "already_achieved")
        self.assertTrue(target["is_achievable"])

    def test_extra_electives_do_not_replace_missing_compulsory_credits(self):
        profile = self._finish_curriculum()
        profile["passed_courses"] = [c for c in profile["passed_courses"] if c["code"] != "MI1111"]
        self.activate(profile)
        audit = student_service.audit_degree()
        self.assertLess(audit["total_credits_accumulated"], audit["total_credits_required"])

    def test_non_credit_requirements_distinguish_unknown_and_incomplete(self):
        profile = self._finish_curriculum()
        audit = student_service.audit_degree()
        self.assertFalse(audit["graduation_ready"])
        self.assertEqual(audit["graduation_status"], "unverified")
        profile["non_credit_status"] = {item["requirement_id"]: "completed" for item in audit["non_credit_requirements"]}
        self.activate(profile)
        self.assertTrue(student_service.audit_degree()["graduation_ready"])
        profile["non_credit_status"][next(iter(profile["non_credit_status"]))] = "incomplete"
        self.activate(profile)
        self.assertEqual(student_service.audit_degree()["graduation_status"], "incomplete")

    def test_unknown_warning_uses_provisional_limit_in_audit_and_recommendation(self):
        profile = copy.deepcopy(self.base_profile)
        profile["info"].pop("warning_level", None)
        profile["failed_courses"] = []
        self.activate(profile)
        audit = student_service.audit_degree()
        self.assertIsNone(audit["warning_level"])
        self.assertTrue(audit["credit_limit"]["is_provisional"])
        rec = course_recommender.recommend(max_credits=24)
        self.assertLessEqual(rec["total_credits_suggested"], 14)
        self.assertIn("Chưa xác định", rec["advice_note"])

    def test_cpa_uses_highest_attempt(self):
        profile = copy.deepcopy(self.base_profile)
        profile["transcript"] = [
            _course("ET2040", 3.0, "F", 0.0),
            _course("ET2040", 3.0, "A", 4.0),
            _course("ET2050", 3.0, "B", 3.0),
        ]
        profile["passed_courses"] = [profile["transcript"][1], profile["transcript"][2]]
        profile["failed_courses"] = [profile["transcript"][0]]
        self.activate(profile)
        self.assertEqual(student_service.audit_degree()["cpa"], 3.5)

    def test_recommender_respects_warning_credit_limit(self):
        profile = copy.deepcopy(self.base_profile)
        profile["info"]["warning_level"] = 2
        self.activate(profile)
        rec = course_recommender.recommend(max_credits=24)
        self.assertEqual(rec["max_allowed_credits"], 14)
        self.assertLessEqual(rec["total_credits_suggested"], 14)
        self.assertEqual(student_service.audit_degree()["credit_limit"]["max"], 14)


class ChatRoutingTests(ActiveProfileTestCase):
    def test_huong_dan_is_not_a_recommendation(self):
        result = chatbot_service.process_message("Hướng dẫn mình cách đăng ký học phần trên CTT với")
        self.assertNotEqual(result["intent"], "COURSE_RECOMMENDATION")

    def test_track_keyword_still_routes_to_recommendation(self):
        result = chatbot_service.process_message("Mình muốn theo hướng Thiết kế Vi mạch thì nên học gì")
        self.assertEqual(result["intent"], "COURSE_RECOMMENDATION")

    def test_project_pair_answer_follows_rule_engine(self):
        profile = copy.deepcopy(self.base_profile)
        # Bỏ ET3260 (song hành của ET3290) khỏi hồ sơ: không còn được phép.
        profile["passed_courses"] = [c for c in profile["passed_courses"] if c["code"] != "ET3260"]
        profile["transcript"] = [c for c in profile["transcript"] if c["code"] != "ET3260"]
        self.activate(profile)
        reply = chatbot_service.process_message("Mình học đồ án 1 và 2 cùng lúc được không?")["reply"]
        self.assertIn("CHƯA ĐĂNG KÝ ĐƯỢC", reply)
        self.assertIn("ET3290", reply)

    def test_nfd_input_is_normalized(self):
        import unicodedata

        message = unicodedata.normalize("NFD", "Mình muốn theo hướng Thiết kế Vi mạch")
        result = chatbot_service.process_message(message)
        self.assertEqual(result["intent"], "COURSE_RECOMMENDATION")


if __name__ == "__main__":
    unittest.main()
