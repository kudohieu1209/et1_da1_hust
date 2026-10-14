import json
import re
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple

from app.core.config import RAW_CONDITIONS_FILE, STUDENT_PROFILE_FILE
from app.services.curriculum_repository import (
    CurriculumNotFoundError,
    curriculum_repository,
)
from app.services.profile_repository import create_profile_repository, is_valid_profile_key

DEFAULT_STUDENT_ID = "20220001"


@dataclass(frozen=True)
class ProfileState:
    """Ảnh chụp hồ sơ sinh viên cùng CTĐT tương ứng.

    Được thay bằng một phép gán duy nhất nên luồng đọc không bao giờ thấy hồ sơ
    của người này đi kèm danh mục môn của CTĐT khác.
    """

    student_id: str
    profile: Dict[str, Any]
    curriculum: Dict[str, Any]
    courses: Dict[str, Dict[str, Any]]
    rules: Dict[str, Dict[str, Any]]


# Hồ sơ riêng của request hiện tại (đặt bởi profile_scope). Mỗi luồng/tác vụ
# có context riêng nên không ảnh hưởng request khác.
_scoped_state: ContextVar[Optional[ProfileState]] = ContextVar("scoped_profile_state", default=None)


def _build_rules(courses: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    rules = {}
    for course in courses.values():
        condition = course.get("registration_condition", {})
        branches = [
            [
                {"code": item["course_code"], "type": item["relation"]}
                for item in branch.get("all_of", [])
            ]
            for branch in condition.get("any_of", [])
        ]
        flat = {"PREREQUISITE": set(), "PRIOR": set(), "COREQUISITE": set()}
        for branch in branches:
            for item in branch:
                flat[item["type"]].add(item["code"])
        rules[course["code"]] = {
            **course,
            "raw_condition": condition.get("raw", ""),
            "condition_tree": branches,
            "flat_prerequisites": sorted(flat["PREREQUISITE"]),
            "flat_prior_courses": sorted(flat["PRIOR"]),
            "flat_corequisites": sorted(flat["COREQUISITE"]),
            "min_credits_accumulated": int(
                condition.get("min_credits_accumulated", 0) or 0
            ),
        }
    return rules


def _build_state(profile: Dict[str, Any], curriculum: Dict[str, Any], student_id: str) -> ProfileState:
    courses = {course["code"]: dict(course) for course in curriculum["courses"]}
    return ProfileState(
        student_id=student_id,
        profile=profile,
        curriculum=curriculum,
        courses=courses,
        rules=_build_rules(courses),
    )


class DataLoader:
    """Compatibility facade backed by a versioned curriculum dataset.

    Hồ sơ "đang hoạt động" (``_state``) dùng chung cho cả tiến trình và chỉ
    được thay khi giữ ``_lock``. Request cần trả lời theo một sinh viên cụ thể
    dùng ``profile_scope``: hồ sơ đó chỉ hiển thị trong context của request ấy.
    """

    def __init__(self, profiles=None):
        # Kho hồ sơ: MongoDB nếu cấu hình MONGODB_URI, ngược lại file cục bộ.
        self._profiles = profiles if profiles is not None else create_profile_repository()
        self.aux_courses: Dict[str, Dict[str, Any]] = {}
        self._state: Optional[ProfileState] = None
        self._lock = threading.RLock()
        self.reload()

    # Giữ tên thuộc tính cũ để engine/service không phải sửa.
    @property
    def _active(self) -> ProfileState:
        return _scoped_state.get() or self._state

    @property
    def student_profile(self) -> Dict[str, Any]:
        return self._active.profile

    @property
    def curriculum(self) -> Dict[str, Any]:
        return self._active.curriculum

    @property
    def courses(self) -> Dict[str, Dict[str, Any]]:
        return self._active.courses

    @property
    def rules(self) -> Dict[str, Dict[str, Any]]:
        return self._active.rules

    @property
    def current_student_id(self) -> str:
        return self._active.student_id

    @staticmethod
    def _read_json(path):
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def reload(self):
        with self._lock:
            self._reload_unlocked()

    def _reload_unlocked(self):
        curriculum_repository.reload()

        aux_courses = {}
        if RAW_CONDITIONS_FILE.exists():
            for course in self._read_json(RAW_CONDITIONS_FILE):
                aux_courses[course["code"]] = {
                    "code": course["code"],
                    "name": course["name"],
                    "credits": float(course.get("credits", 0) or 0),
                }
        self.aux_courses = aux_courses

        student_id = self._state.student_id if self._state else DEFAULT_STUDENT_ID
        profile = self._profiles.get(student_id)
        if profile is None:
            if not STUDENT_PROFILE_FILE.exists():
                raise FileNotFoundError(f"Không tìm thấy hồ sơ sinh viên {student_id}")
            profile = self._read_json(STUDENT_PROFILE_FILE)
        curriculum = curriculum_repository.resolve_profile(profile)
        self._activate(profile, curriculum, student_id)

    def _activate(
        self,
        profile: Dict[str, Any],
        curriculum: Dict[str, Any],
        student_id: str,
    ) -> ProfileState:
        """Đổi hồ sơ đang hoạt động; chỉ gọi khi đang giữ ``_lock``."""
        state = _build_state(profile, curriculum, student_id)
        self._state = state
        program = curriculum["program"]
        print(
            f"[INFO] DataLoader: {program['program_code']}-{program['curriculum_version']}, "
            f"{len(state.courses)} môn, {len(curriculum['groups'])} nhóm, "
            f"SV {profile.get('info', {}).get('student_name', 'N/A')}"
        )
        return state

    def _read_profile(self, student_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Đọc hồ sơ và CTĐT đã kiểm chứng tương ứng, chưa kích hoạt."""
        if not is_valid_profile_key(student_id):
            raise FileNotFoundError(f"Mã hồ sơ không hợp lệ: {student_id!r}")
        profile = self._profiles.get(student_id)
        if profile is None:
            raise FileNotFoundError(f"Không tìm thấy hồ sơ sinh viên {student_id}")
        return profile, curriculum_repository.resolve_profile(profile)

    def load_student_profile(self, student_id: str) -> Dict[str, Any]:
        """Activate a profile only when its exact verified curriculum exists."""
        profile, curriculum = self._read_profile(student_id)
        with self._lock:
            return self._activate(profile, curriculum, student_id).profile

    def find_profile_key(self, student_id: Optional[str]) -> Optional[str]:
        """Tên file hồ sơ (không đuôi) ứng với MSSV, hoặc None nếu không có.

        Hồ sơ nhập tay được lưu dưới khóa "custom" nên ngoài khớp khóa còn so
        với ``info.student_id`` bên trong từng hồ sơ.
        """
        return self._profiles.find_key(str(student_id or "").strip())

    @contextmanager
    def profile_scope(self, student_id: Optional[str]) -> Iterator[None]:
        """Trong khối ``with``, mọi getter trả về hồ sơ của ``student_id``.

        Chỉ context hiện tại thấy hồ sơ này: hồ sơ đang hoạt động không đổi và
        không giữ khóa, nên request khác (kể cả /switch) vẫn chạy song song.
        MSSV không có hồ sơ (vd. "demo") giữ nguyên hồ sơ đang thấy.
        """
        key = self.find_profile_key(student_id)
        if key is None or key == self.current_student_id:
            yield
            return
        token = self.enter_scope(self.load_scope_state(key))
        try:
            yield
        finally:
            self.exit_scope(token)

    # --- Scope theo người đăng nhập --------------------------------------
    # Tách đọc (I/O, chạy trong threadpool) khỏi việc đặt ContextVar (phải
    # chạy trong context của request để endpoint đồng bộ thừa hưởng được).
    @property
    def profiles(self):
        return self._profiles

    def load_scope_state(self, student_id: str) -> ProfileState:
        key = self.find_profile_key(student_id)
        if key is None:
            raise FileNotFoundError(f"Tài khoản {student_id} chưa có hồ sơ học tập.")
        profile, curriculum = self._read_profile(key)
        return _build_state(profile, curriculum, key)

    @staticmethod
    def enter_scope(state: ProfileState) -> Token:
        return _scoped_state.set(state)

    @staticmethod
    def exit_scope(token: Token) -> None:
        _scoped_state.reset(token)

    def save_profile_for(self, student_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Ghi hồ sơ của một sinh viên cụ thể (không phải hồ sơ đang hoạt động).

        Nếu request hiện tại đang ở scope của sinh viên đó thì cập nhật luôn
        scope, để phần còn lại của request (vd. audit) thấy dữ liệu mới.
        """
        key = self.find_profile_key(student_id) or student_id
        curriculum = curriculum_repository.resolve_profile(profile)
        with self._lock:
            self._profiles.save(key, profile)
            state = _build_state(profile, curriculum, key)
            if self._state is not None and self._state.student_id == key:
                self._state = state
        scoped = _scoped_state.get()
        if scoped is not None and scoped.student_id == key:
            _scoped_state.set(state)
        return profile

    def update_profile_info_for(self, student_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        key = self.find_profile_key(student_id)
        current = self._profiles.get(key) if key else None
        if current is None:
            raise FileNotFoundError(f"Tài khoản {student_id} chưa có hồ sơ học tập.")
        candidate = json.loads(json.dumps(current))
        candidate.setdefault("info", {})
        for field, value in updates.items():
            if value is not None:
                candidate["info"][field] = value
        return self.save_profile_for(student_id, candidate)

    def get_course(self, code: str) -> Optional[Dict[str, Any]]:
        return self.courses.get(code) or self.aux_courses.get(code)

    def get_rule(self, code: str) -> Optional[Dict[str, Any]]:
        return self.rules.get(code)

    def get_all_courses(self) -> List[Dict[str, Any]]:
        return list(self.courses.values())

    def get_all_rules(self) -> List[Dict[str, Any]]:
        return list(self.rules.values())

    def get_student_profile(self) -> Dict[str, Any]:
        return self.student_profile

    def get_curriculum(self) -> Dict[str, Any]:
        return self.curriculum

    def get_program(self) -> Dict[str, Any]:
        return self.curriculum["program"]

    def get_graduation_path(self, path_id: str = "bachelor") -> Dict[str, Any]:
        for path in self.curriculum.get("graduation_paths", []):
            if path["id"] == path_id:
                return path
        raise LookupError(f"Curriculum không có lộ trình tốt nghiệp {path_id}")

    def get_groups(self) -> List[Dict[str, Any]]:
        return list(self.curriculum.get("groups", []))

    def get_module_tracks(self) -> List[Dict[str, Any]]:
        """Return the official module alternatives from the graduation formula."""
        groups = {group["id"]: group for group in self.get_groups()}
        component = next(
            (
                item
                for item in self.get_graduation_path().get("components", [])
                if item["type"] == "ONE_OF_GROUPS"
            ),
            None,
        )
        if not component:
            return []

        tracks = []
        for index, option in enumerate(component["options"], 1):
            group = groups[option["group_id"]]
            prefix = f"Mô đun {index}:"
            descriptions = [
                course.get("category", "")[len(prefix):].strip()
                for code in group["course_codes"]
                if (course := self.courses.get(code))
                and course.get("category", "").startswith(prefix)
            ]
            description = max(descriptions, key=len) if descriptions else ""
            description = description.removeprefix("Mô đun:").strip()
            display_name = f"Mô đun {index}"
            if description:
                display_name += f" - {description}"
            tracks.append({
                "id": f"MOD{index}",
                "group_id": group["id"],
                "name": display_name,
                "description": description or group["name"],
                "required_credits": option["required_credits"],
                "catalog_credits": group["catalog_credits"],
                "core_courses": list(group["course_codes"]),
            })
        return tracks

    def get_course_modules(self, course_or_code: Any) -> List[Dict[str, str]]:
        """Return official module memberships for one course.

        Elective courses can belong to several alternatives. Keeping this as a
        structured list avoids parsing the legacy display string
        ``"Mô đun 1,2,5"`` in each consumer.
        """
        course = (
            self.get_course(course_or_code)
            if isinstance(course_or_code, str)
            else (course_or_code or {})
        ) or {}
        groups = {group["id"]: group for group in self.get_groups()}
        modules = []
        for group_id in course.get("group_ids", []):
            group = groups.get(group_id, {})
            name = str(group.get("name", "")).strip()
            match = re.match(r"^Mô đun\s+(\d+)$", name, flags=re.IGNORECASE)
            if match:
                module_id = f"MOD{match.group(1)}"
                if not any(item["id"] == module_id for item in modules):
                    modules.append({"id": module_id, "name": name, "group_id": group_id})
        return modules


data_loader = DataLoader()
