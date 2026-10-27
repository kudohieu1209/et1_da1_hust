import unittest

from app.services.curriculum_repository import curriculum_repository
from app.services.program_catalog import program_catalog


class ProgramCatalogTests(unittest.TestCase):
    def test_official_catalog_is_loaded(self):
        programs = program_catalog.list()
        self.assertGreaterEqual(len(programs), 60)
        et1 = program_catalog.get("ET1")
        self.assertIsNotNone(et1)
        self.assertEqual(et1["name"], "Điện tử và Viễn thông")
        self.assertEqual(et1["curriculum_source_status"], "ok")
        self.assertIn("seee.hust.edu.vn", et1["curriculum_source_url"])
        self.assertTrue(et1["curriculum_candidate_available"])
        self.assertEqual(et1["curriculum_candidates"][0]["candidate_id"], "ET1-2023")

    def test_support_status_does_not_claim_unloaded_curricula(self):
        supported = program_catalog.list(supported_only=True)
        loaded = {item["program_code"] for item in curriculum_repository.list_programs()}
        self.assertIn("ET1", loaded)
        self.assertEqual(sorted(item["admission_code"] for item in supported), sorted(loaded))
        self.assertEqual(program_catalog.list(search="ET1")[0]["curriculum_versions"], ["2022", "2023"])
        self.assertEqual(program_catalog.get("ET1")["supported_cohorts"], ["K67", "K68"])
        self.assertEqual(program_catalog.get("BF1")["supported_cohorts"], ["K68", "K69"])
        self.assertFalse(program_catalog.get("ET-E4")["curriculum_supported"])
        self.assertTrue(program_catalog.get("ET-E4")["curriculum_candidate_available"])


if __name__ == "__main__":
    unittest.main()
