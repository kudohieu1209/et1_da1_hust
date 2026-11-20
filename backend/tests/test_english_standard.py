import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.auth import runtime
from app.core.config import SESSION_COOKIE_NAME
from app.main import app
from app.services.data_loader import data_loader
from app.services.english_standard import (
    ENGLISH_RULES,
    cohort_from_profile,
    english_standard,
    estimate_level,
    latest_score,
    program_track,
    rule_for,
)
from app.services.profile_repository import MongoProfileRepository
from testing_support import isolated_database


def profile(class_name="Điện tử 03 - K71", program_code="ET1", **info):
    return {"info": {"class_name": class_name, "program_code": program_code,
                     "student_id": "20261234", **info}}


def sourced_entries(value):
    if isinstance(value, dict):
        if "source" in value:
            yield value
        for child in value.values():
            yield from sourced_entries(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from sourced_entries(child)


class EnglishStandardTests(unittest.TestCase):
    def test_cohort_from_class_name(self):
        self.assertEqual(cohort_from_profile(profile("Điện tử 03 - K68")), 68)
        self.assertEqual(cohort_from_profile(profile("Điện tử 03 - k71")), 71)
        self.assertIsNone(cohort_from_profile(profile("Điện tử 03", program_name="Điện tử 2026")))
        self.assertIsNone(cohort_from_profile({}))

    def test_rules_use_the_published_cohort_ranges(self):
        self.assertIsNone(rule_for(None))
        self.assertIsNone(rule_for(69))
        self.assertEqual(rule_for(70)["decision"], "10728/QĐ-ĐHBK")
        self.assertEqual(rule_for(71)["decision"], "10828/QĐ-ĐHBK")
        self.assertIs(rule_for(71), rule_for(72))

    def test_placement_cutoffs_are_in_k70_only(self):
        for total, level in [(120, "1"), (220, "1"), (225, "2.1"), (545, "2.3"),
                             (549, None), (550, "3.1"), (785, "4"), (990, "5")]:
            with self.subTest(total=total):
                listening = total // 2
                record = {"certificate_type": "TOEIC Placement", "listening": listening,
                          "reading": total - listening}
                self.assertEqual(estimate_level(record, rule_for(70)), level)
                self.assertIsNone(estimate_level(record, rule_for(71)))

    def test_toeic_uses_the_lowest_of_four_skill_levels(self):
        record = {"certificate_type": "TOEIC 4 kỹ năng", "listening": 400, "reading": 400,
                  "speaking": 130, "writing": 120}
        self.assertEqual(estimate_level(record, rule_for(71)), "3.1")
        self.assertEqual(estimate_level(record, rule_for(70)), "3.1")
        self.assertEqual(estimate_level({**record, "writing": 140, "speaking": 140}, rule_for(71)), "3.2")
        self.assertIsNone(estimate_level({**record, "speaking": None}, rule_for(71)))
        self.assertIsNone(estimate_level({**record, "certificate_type": "Bài thi tổng hợp"}, rule_for(70)))
        self.assertIsNone(estimate_level({"certificate_type": "TOEIC", "score": 990}, rule_for(70)))

    def test_track_and_official_status_stay_separate_from_score(self):
        self.assertEqual(program_track(profile(program_code="BF-E19")), "elitech")
        self.assertEqual(program_track(profile(program_code="ITX", program_name="Tài năng tích hợp Cử nhân – Thạc sĩ")), "talent")
        self.assertEqual(program_track(profile(program_code="ITX", program_name="Chương trình tài năng")), "unknown")
        for code in ["TE-EP", "FL2", "ET-UNKNOWN", ""]:
            self.assertEqual(program_track(profile(program_code=code)), "unknown")
        sections = {"english": {"records": [{"score": 900, "test_date": "2026-10-01"},
                                             {"score": 0, "test_date": "2026-11-01"}]}}
        result = english_standard(profile(), sections)
        self.assertEqual(result["latest"]["score"], 0)
        self.assertEqual(result["ctt_status"], "unverified")
        self.assertEqual(result["required"]["graduation"]["level"], 3)
        self.assertEqual(result["history"][1]["score"], 900)
        self.assertIsNone(english_standard(profile("Điện tử 03 - K67"), sections)["required"])
        self.assertIsNone(latest_score([{"score": 1}, {"score": 2}]))

    def test_all_quotes_are_in_the_cited_lines_of_each_verified_source(self):
        documents = Path(__file__).resolve().parents[2] / "data" / "documents"
        for rule in ENGLISH_RULES:
            lines = (documents / rule["source_file"]).read_text(encoding="utf-8").splitlines()
            entries = list(sourced_entries(rule))
            registration_count = sum(len(rows) for rows in rule["registration_by_semester"].values())
            self.assertEqual(len(entries), 1 + len(rule["conversion_table"]) + len(rule["graduation"]) + registration_count)
            for entry in entries:
                with self.subTest(source=entry["source"]):
                    filename, span = entry["source"].rsplit(":", 1)
                    start, end = map(int, span.split("-"))
                    self.assertEqual(filename, rule["source_file"])
                    self.assertLessEqual(len(entry["quote"].split()), 30)
                    self.assertIn(" ".join(entry["quote"].split()),
                                  " ".join(" ".join(lines[start - 1:end]).split()))


class EnglishStandardApiTests(unittest.TestCase):
    def setUp(self):
        self.profiles = MongoProfileRepository(isolated_database())
        for patcher in (
            mock.patch.object(data_loader, "_profiles", self.profiles),
            mock.patch.object(runtime.auth_service, "resolve_session", return_value="20261234"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app, cookies={SESSION_COOKIE_NAME: "fixture-token"})
        self.addCleanup(self.client.close)
        self.url = "/api/student/english-standard"

    def test_requires_authentication(self):
        with TestClient(app) as client:
            self.assertEqual(client.get(self.url).status_code, 401)

    def test_missing_profile_or_sync_returns_no_data(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["has_data"])
        self.profiles.save("20261234", profile())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["has_data"])
        self.assertEqual(response.json()["cohort"], 71)

    def test_returns_owned_history_and_official_status_without_requiring_a_curriculum(self):
        mine = profile()
        mine["school_services"] = {
            "english": {"records": [{"certificate_type": "TOEIC", "score": 840, "listening": 430,
                                     "reading": 410, "speaking": 150, "writing": 140,
                                     "test_date": "2026-10-15", "unrelated": "hidden"}]},
            "certificates": {"requirements": {"240": "completed"}},
        }
        self.profiles.save("20261234", mine)
        self.profiles.save("20261235", profile(student_id="20261235"))
        response = self.client.get(self.url, headers={"X-Student-ID": "20261235"})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(set(result), {"cohort", "track", "ctt_status", "latest", "estimated_level",
                                       "rule", "required", "history", "notes", "has_data"})
        self.assertTrue(result["has_data"])
        self.assertEqual(result["ctt_status"], "completed")
        self.assertEqual(result["estimated_level"], "3.2")
        self.assertEqual(result["latest"]["score"], 840)
        self.assertNotIn("unrelated", result["history"][0])
        self.assertEqual(result["required"]["graduation"]["level"], 3)
