"""Kho hồ sơ sinh viên (thông tin + bảng điểm).

Hai cài đặt có cùng giao diện:
- ``MongoProfileRepository``: collection ``student_profiles`` trên MongoDB.
- ``FileProfileRepository``: các file ``students/*.json`` cục bộ (offline).

Khóa hồ sơ là tên file cũ (MSSV hoặc "custom"). Khóa luôn được kiểm tra vì
nó đến từ header/payload và từng được ghép vào đường dẫn file.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pymongo import ASCENDING

from app.core.config import STUDENTS_DIR
from app.services.mongo_client import get_mongo_database

PROFILE_KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,32}")


def is_valid_profile_key(key: Any) -> bool:
    return isinstance(key, str) and PROFILE_KEY_PATTERN.fullmatch(key) is not None


def _require_valid_key(key: Any) -> str:
    if not is_valid_profile_key(key):
        raise ValueError(f"Mã hồ sơ không hợp lệ: {key!r}")
    return key


class FileProfileRepository:
    def __init__(self, directory: Path = STUDENTS_DIR):
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    @staticmethod
    def _read(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not is_valid_profile_key(key) or not self._path(key).exists():
            return None
        return self._read(self._path(key))

    def list(self) -> List[Tuple[str, Dict[str, Any]]]:
        if not self.directory.exists():
            return []
        profiles = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                profiles.append((path.stem, self._read(path)))
            except (OSError, ValueError) as exc:
                print(f"[WARN] Bỏ qua hồ sơ lỗi {path.name}: {exc}")
        return profiles

    def find_key(self, student_id: str) -> Optional[str]:
        if not is_valid_profile_key(student_id):
            return None
        if self._path(student_id).exists():
            return student_id
        for key, profile in self.list():
            if str(profile.get("info", {}).get("student_id", "")) == student_id:
                return key
        return None

    def save(self, key: str, profile: Dict[str, Any]) -> None:
        path = self._path(_require_valid_key(key))
        self.directory.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            json.dump(profile, stream, ensure_ascii=False, indent=2)


class MongoProfileRepository:
    """Mỗi hồ sơ là một document ``{_id: khóa, student_id, profile, updated_at}``.

    ``profile`` giữ nguyên cấu trúc JSON cũ; ``student_id`` được tách ra để
    tra cứu theo MSSV có chỉ mục.
    """

    def __init__(self, database):
        self._collection = database["student_profiles"]
        self._collection.create_index([("student_id", ASCENDING)])

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not is_valid_profile_key(key):
            return None
        document = self._collection.find_one({"_id": key}, {"profile": 1})
        return document["profile"] if document else None

    def list(self) -> List[Tuple[str, Dict[str, Any]]]:
        cursor = self._collection.find({}, {"profile": 1}).sort("_id", ASCENDING)
        return [(document["_id"], document["profile"]) for document in cursor]

    def find_key(self, student_id: str) -> Optional[str]:
        if not is_valid_profile_key(student_id):
            return None
        if self._collection.count_documents({"_id": student_id}, limit=1):
            return student_id
        document = self._collection.find_one({"student_id": student_id}, {"_id": 1}, sort=[("_id", ASCENDING)])
        return document["_id"] if document else None

    def save(self, key: str, profile: Dict[str, Any]) -> None:
        # Vòng JSON giữ dữ liệu y hệt bản file (tuple→list, khóa số→chuỗi).
        normalized = json.loads(json.dumps(profile, ensure_ascii=False))
        self._collection.replace_one(
            {"_id": _require_valid_key(key)},
            {
                "student_id": str(normalized.get("info", {}).get("student_id", "")),
                "profile": normalized,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            upsert=True,
        )


def create_profile_repository():
    database = get_mongo_database()
    if database is not None:
        return MongoProfileRepository(database)
    return FileProfileRepository()
