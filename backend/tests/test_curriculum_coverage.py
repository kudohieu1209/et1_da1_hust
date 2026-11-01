import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.engine.recommender import course_recommender
from app.engine.rule_engine import rule_engine
from app.services.curriculum_repository import curriculum_repository
from app.services.data_loader import data_loader, _build_state
from app.services.program_catalog import program_catalog
from app.services.student_service import student_service


class CurriculumCoverageTests(unittest.TestCase):
    def test_every_admission_program_has_public_source_access(self):
        client = TestClient(app)
        programs = client.get("/api/programs").json()["programs"]
        self.assertEqual(len(programs), 68)
        for program in programs:
            with self.subTest(code=program["admission_code"]):
                self.assertTrue(program["reference_available"])
                response = client.get(f"/api/programs/{program['admission_code']}/curricula")
                self.assertEqual(response.status_code, 200)
                records = response.json()["curricula"]
                self.assertTrue(records)
                for record in records:
                    self.assertEqual(record["program_code"], program["admission_code"])
                    self.assertIn(record["usage"], {"reference", "audit_and_reference"})
                    self.assertNotIn("C:\\Users", str(record))

    def test_unconfirmed_source_remains_readable_without_claiming_audit(self):
        records = program_catalog.get_curricula("IT1")
        self.assertTrue(any(record["course_count"] for record in records))
        self.assertTrue(all(not record["audit_available"] for record in records))
        self.assertTrue(all(record["scope_note"] for record in records))
        self.assertEqual(TestClient(app).get("/api/programs/UNKNOWN/curricula").status_code, 404)

    def test_manual_et1_2022_snapshot_is_included_in_lookup(self):
        records = program_catalog.get_curricula("ET1")
        self.assertEqual({r["curriculum_version"] for r in records if r["audit_available"]}, {"2022", "2023"})

    def test_cohort_derived_version_is_linked_to_its_normalized_snapshot(self):
        records = program_catalog.get_curricula("BF-E19")
        original = next(r for r in records if r["id"] == "BF-E19-2023")
        self.assertTrue(original["audit_available"])
        self.assertEqual(original["curriculum_version"], "2023")

    def test_reviewed_curricula_resolve_to_their_supported_cohorts(self):
        for code, cohort, total in (("BF2", "K70", 132), ("ME1", "K70", 132),
                                    ("EV1", "K70", 132), ("EV2", "K70", 132),
                                    ("MS1", "K68", 132), ("FL3", "K70", 136)):
            with self.subTest(code=code):
                curriculum = curriculum_repository.resolve_profile({"info": {
                    "program_code": code, "class_name": f"Lớp - {cohort}"}})
                self.assertEqual(curriculum["program"]["total_required_credits"], total)
                self.assertTrue(any(s["kind"] == "OFFICIAL_SOURCE_REVIEW" for s in curriculum["sources"]))

    def test_missing_ctt_conditions_are_unknown_and_never_recommended(self):
        curriculum = curriculum_repository.get("ME1", "2025")
        profile = {"info": {"warning_level": 0}, "transcript": [], "passed_courses": [], "failed_courses": []}
        token = data_loader.enter_scope(_build_state(profile, curriculum, "synthetic-review"))
        try:
            unknown = [c["code"] for c in curriculum["courses"]
                       if c.get("registration_condition_verified") is False]
            self.assertTrue(unknown)
            for code in unknown:
                result = rule_engine.check_eligibility(code)
                self.assertEqual(result["status"], "UNVERIFIED")
                self.assertFalse(result["is_eligible"])
            recommended = {c["code"] for c in course_recommender.recommend()["recommended_courses"]}
            self.assertFalse(recommended & set(unknown))
        finally:
            data_loader.exit_scope(token)

    def test_two_selection_layers_are_audited_as_one_legal_bundle(self):
        for code, year, required in (("MS1", "2023", 26), ("FL3", "2025", 25)):
            curriculum = curriculum_repository.get(code, year)
            profile = {"info": {}, "transcript": [], "passed_courses": [], "failed_courses": []}
            token = data_loader.enter_scope(_build_state(profile, curriculum, "synthetic-bundles"))
            try:
                tracks = data_loader.get_module_tracks()
                self.assertEqual(len(tracks), 6)
                self.assertEqual({t["required_credits"] for t in tracks}, {required})
                chosen = tracks[0]
                completed = set(chosen["core_courses"])
                audit = student_service._audit_graduation_components(completed)
                choice = next(c for c in audit if c["type"] == "ONE_OF_GROUPS")
                self.assertEqual(choice["earned_credits"], required)
                self.assertTrue(choice["is_complete"])
                # Passing every alternative must not multiply graduation credits.
                all_completed = {c["code"] for c in curriculum["courses"]}
                total = sum(c["earned_credits"] for c in student_service._audit_graduation_components(all_completed))
                self.assertEqual(total, curriculum["program"]["total_required_credits"])
                self.assertFalse(any(g["id"] in {t["group_id"] for t in tracks}
                                     for g in student_service._non_credit_groups()))
            finally:
                data_loader.exit_scope(token)


if __name__ == "__main__":
    unittest.main()
