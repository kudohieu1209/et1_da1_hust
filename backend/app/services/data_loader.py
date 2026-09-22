import json
import re
from typing import Any, Dict, List, Optional

from app.core.config import RAW_CONDITIONS_FILE, STUDENT_PROFILE_FILE, STUDENTS_DIR
from app.services.curriculum_repository import (
    CurriculumNotFoundError,
    curriculum_repository,
)


class DataLoader:
    """Compatibility facade backed by a versioned curriculum dataset."""

    def __init__(self):
        self.courses: Dict[str, Dict[str, Any]] = {}
        self.aux_courses: Dict[str, Dict[str, Any]] = {}
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.student_profile: Dict[str, Any] = {}
        self.curriculum: Dict[str, Any] = {}
        self.current_student_id = "20220001"
        self.reload()

    @staticmethod
    def _read_json(path):
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def reload(self):
        curriculum_repository.reload()

        self.aux_courses = {}
        if RAW_CONDITIONS_FILE.exists():
            for course in self._read_json(RAW_CONDITIONS_FILE):
                self.aux_courses[course["code"]] = {
                    "code": course["code"],
                    "name": course["name"],
                    "credits": float(course.get("credits", 0) or 0),
                }

        student_file = STUDENTS_DIR / f"{self.current_student_id}.json"
        if not student_file.exists():
            student_file = STUDENT_PROFILE_FILE
        if not student_file.exists():
            raise FileNotFoundError(f"Không tìm thấy hồ sơ sinh viên: {student_file}")

        profile = self._read_json(student_file)
        curriculum = curriculum_repository.resolve_profile(profile)
        self._activate(profile, curriculum, self.current_student_id)

    def _activate(
        self,
        profile: Dict[str, Any],
        curriculum: Dict[str, Any],
        student_id: str,
    ) -> None:
        self.student_profile = profile
        self.curriculum = curriculum
        self.current_student_id = student_id
        self.courses = {course["code"]: dict(course) for course in curriculum["courses"]}
        self.rules = {}
        for course in self.courses.values():
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
            self.rules[course["code"]] = {
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
        program = curriculum["program"]
        print(
            f"[INFO] DataLoader: {program['program_code']}-{program['curriculum_version']}, "
            f"{len(self.courses)} môn, {len(curriculum['groups'])} nhóm, "
            f"SV {profile.get('info', {}).get('student_name', 'N/A')}"
        )

    def load_student_profile(self, student_id: str) -> Dict[str, Any]:
        """Activate a profile only when its exact verified curriculum exists."""
        target_path = STUDENTS_DIR / f"{student_id}.json"
        if not target_path.exists():
            raise FileNotFoundError(f"Không tìm thấy hồ sơ sinh viên {student_id}")
        profile = self._read_json(target_path)
        curriculum = curriculum_repository.resolve_profile(profile)
        self._activate(profile, curriculum, student_id)
        return self.student_profile

    def list_available_profiles(self) -> List[Dict[str, Any]]:
        profiles = []
        if not STUDENTS_DIR.exists():
            return profiles
        for path in sorted(STUDENTS_DIR.glob("*.json")):
            try:
                data = self._read_json(path)
                info = data.get("info", {})
                total_points = cpa_credits = accumulated = 0.0
                for item in data.get("transcript", []):
                    credits = float(item.get("credits", 0.0))
                    if not item["code"].startswith("PE") and credits > 0:
                        if item.get("is_passed", True):
                            accumulated += credits
                        total_points += float(item.get("numeric_grade", 0.0)) * credits
                        cpa_credits += credits
                try:
                    resolved = curriculum_repository.resolve_profile(data)["program"]
                    supported = True
                    curriculum_version = resolved["curriculum_version"]
                except CurriculumNotFoundError:
                    supported = False
                    curriculum_version = curriculum_repository._infer_version(info)
                profiles.append({
                    "id": path.stem,
                    "student_id": info.get("student_id", path.stem),
                    "name": info.get("student_name", "Sinh viên Demo"),
                    "class_name": info.get("class_name", ""),
                    "badge": info.get("badge", "Demo"),
                    "persona": info.get("persona", "Hồ sơ sinh viên HUST"),
                    "cpa": round(total_points / cpa_credits, 2) if cpa_credits else 0.0,
                    "accumulated_credits": accumulated,
                    "is_active": path.stem == self.current_student_id,
                    "curriculum_version": curriculum_version,
                    "curriculum_supported": supported,
                })
            except Exception as exc:
                print(f"[WARN] Lỗi đọc profile {path}: {exc}")
        return profiles

    def save_custom_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        # Resolve before writing so an unsupported profile cannot silently replace
        # the active, working profile.
        curriculum = curriculum_repository.resolve_profile(profile_data)
        STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
        custom_path = STUDENTS_DIR / "custom.json"
        with custom_path.open("w", encoding="utf-8") as stream:
            json.dump(profile_data, stream, ensure_ascii=False, indent=2)
        self._activate(profile_data, curriculum, "custom")
        return self.student_profile

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

    def update_profile_info(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        candidate = json.loads(json.dumps(self.student_profile))
        candidate.setdefault("info", {})
        for key, value in updates.items():
            if value is not None:
                candidate["info"][key] = value
        curriculum = curriculum_repository.resolve_profile(candidate)

        target_path = STUDENTS_DIR / f"{self.current_student_id}.json"
        if not target_path.exists():
            target_path = STUDENTS_DIR / "custom.json"
        STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8") as stream:
            json.dump(candidate, stream, ensure_ascii=False, indent=2)
        self._activate(candidate, curriculum, self.current_student_id)
        return self.student_profile


data_loader = DataLoader()
