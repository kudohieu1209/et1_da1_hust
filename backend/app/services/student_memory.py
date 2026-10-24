"""Explicit student preferences; no automatic extraction from conversations."""
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.schemas import AdvisingMemoryUpdate
from app.services.mongo_client import get_mongo_database


class StudentMemoryRepository:
    def __init__(self, database):
        self.collection = database["student_memory"]

    def get(self, student_id):
        document = self.collection.find_one({"_id": str(student_id)}, {"_id": 0})
        return document or {**AdvisingMemoryUpdate().model_dump(), "updated_at": None}

    def save(self, student_id, preferences, curriculum):
        document = {
            **preferences.model_dump(),
            "program_code": curriculum["program_code"],
            "curriculum_version": curriculum["curriculum_version"],
            "source": "student_settings",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.collection.replace_one({"_id": str(student_id)}, document, upsert=True)
        return document

    def delete(self, student_id):
        self.collection.delete_one({"_id": str(student_id)})

    def for_advising(self, student_id, curriculum, tracks):
        memory = self.get(student_id)
        if not memory.get("enabled") or any(
            memory.get(key) != curriculum[key] for key in ("program_code", "curriculum_version")
        ):
            return {}
        if memory.get("target_track") and memory["target_track"] not in {track["id"] for track in tracks}:
            return {}
        # Revalidate stored records as well as HTTP payloads.
        try:
            return AdvisingMemoryUpdate.model_validate({
                key: memory[key] for key in AdvisingMemoryUpdate.model_fields if key in memory
            }).model_dump()
        except ValidationError:
            return {}


student_memory = StudentMemoryRepository(get_mongo_database())
