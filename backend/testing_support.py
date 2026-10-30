"""Synthetic profiles and isolated MongoDB fixtures for tests only.

Never reads personal transcripts or connects to a real database.
"""
import json
from pathlib import Path


def sample_profiles():
    directory = Path(__file__).resolve().parent.parent / "data" / "processed" / "curricula"
    profiles = {}
    for key, student_id, version, name, warning in (
        ("20220001", "20220001", "2022", "Sinh viên demo K67", 0),
        ("20231890", "20231890", "2023", "Sinh viên demo K68", 0),
        ("20223123", "20223123", "2022", "Sinh viên demo học lực giỏi", 0),
        ("20224567", "20224567", "2022", "Sinh viên demo cảnh báo", 2),
        ("custom", "20228888", "2022", "Sinh viên demo nhập tay", 0),
    ):
        data = json.loads((directory / f"et1_{version}.json").read_text(encoding="utf-8"))
        transcript = [{"code": course["code"], "name": course["name"], "credits": course["credits"],
                       "letter_grade": "B", "numeric_grade": 3.0, "is_passed": True}
                      for course in data["courses"] if 0 < (course.get("suggested_semester") or 99) <= 6]
        profiles[key] = {
            "info": {"student_id": student_id, "student_name": name, "program_code": "ET1",
                     "curriculum_version": version, "class_name": "Điện tử - K67" if version == "2022" else "Điện tử - K68",
                     "warning_level": warning},
            "transcript": transcript, "passed_courses": transcript, "failed_courses": [],
            "total_courses_completed": len(transcript), "fixture_kind": "synthetic_not_a_real_transcript",
        }
    return profiles


def isolated_database(seed=False):
    import mongomock
    database = mongomock.MongoClient()["advisor_test"]
    if seed:
        for key, profile in sample_profiles().items():
            database["student_profiles"].insert_one({"_id": key, "student_id": profile["info"]["student_id"], "profile": profile})
    return database
