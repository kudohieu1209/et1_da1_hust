from typing import Any, Dict, List

from app.core.hust_rules import (
    CREDIT_LIMITS,
    GRADE_TO_SCALE4,
    MIN_GRADUATION_CPA,
    assess_academic_warning,
    get_academic_classification,
    parse_grade_from_line,
)
from app.services.data_loader import data_loader


class StudentService:
    def get_profile(self) -> Dict[str, Any]:
        return data_loader.get_student_profile()

    @staticmethod
    def _credits_for_codes(codes, course_map) -> float:
        return sum(float(course_map[code].get("credits", 0)) for code in set(codes) if code in course_map)

    def _audit_graduation_components(self, passed_codes: set[str]) -> List[Dict[str, Any]]:
        groups = {group["id"]: group for group in data_loader.get_groups()}
        course_map = {course["code"]: course for course in data_loader.get_all_courses()}
        results = []

        def group_progress(group_id: str, required: float) -> Dict[str, Any]:
            group = groups[group_id]
            completed_codes = sorted(set(group["course_codes"]) & passed_codes)
            raw_credits = self._credits_for_codes(completed_codes, course_map)
            earned = min(float(required), raw_credits)
            return {
                "group_id": group_id,
                "name": group["name"],
                "required_credits": required,
                "earned_credits": earned,
                "remaining_credits": max(0.0, float(required) - earned),
                "is_complete": earned >= float(required),
                "completed_course_codes": completed_codes,
                "course_codes": list(group["course_codes"]),
            }

        for component in data_loader.get_graduation_path().get("components", []):
            if component["type"] == "GROUP_CREDITS":
                results.append({"type": "GROUP_CREDITS", **group_progress(
                    component["group_id"], component["required_credits"]
                )})
                continue

            if component["type"] == "ONE_OF_GROUPS":
                options = [
                    group_progress(option["group_id"], option["required_credits"])
                    for option in component["options"]
                ]
                best = max(options, key=lambda item: (item["earned_credits"], -item["remaining_credits"]))
                results.append({
                    "type": "ONE_OF_GROUPS",
                    "name": "Một trong các mô-đun tự chọn",
                    "required_credits": component["required_credits"],
                    "earned_credits": best["earned_credits"],
                    "remaining_credits": best["remaining_credits"],
                    "is_complete": any(option["is_complete"] for option in options),
                    "best_option_group_id": best["group_id"],
                    "options": options,
                })
        return results

    def audit_degree(self) -> Dict[str, Any]:
        """Audit the active student against their exact curriculum version."""
        profile = data_loader.get_student_profile()
        info = profile.get("info", {})
        transcript = profile.get("transcript", [])
        passed_courses = profile.get("passed_courses", [])
        failed_courses = profile.get("failed_courses", [])
        passed_codes = {course["code"] for course in passed_courses}
        course_map = {course["code"]: course for course in data_loader.get_all_courses()}

        # Một học phần học nhiều lần chỉ tính điểm lần cao nhất (QĐ 5445,
        # "Điểm lần cao nhất được công nhận là điểm chính thức của học phần").
        best_by_code: Dict[str, Dict[str, float]] = {}
        for item in transcript:
            credits = float(item.get("credits", 0.0))
            letter = item.get("letter_grade", "")
            scale4 = float(item.get("numeric_grade", GRADE_TO_SCALE4.get(letter, 0.0)))
            if item["code"].startswith("PE") or credits <= 0:
                continue
            best = best_by_code.get(item["code"])
            if best is None or scale4 > best["scale4"]:
                best_by_code[item["code"]] = {"scale4": scale4, "credits": credits}
        total_grade_points = sum(v["scale4"] * v["credits"] for v in best_by_code.values())
        cpa_credits = sum(v["credits"] for v in best_by_code.values())
        cpa = round(total_grade_points / cpa_credits, 2) if cpa_credits else 0.0

        warning = assess_academic_warning(profile)
        warning_level = warning["level"]
        limit_info = CREDIT_LIMITS.get(warning_level, CREDIT_LIMITS[0])

        path = data_loader.get_graduation_path()
        program = data_loader.get_program()
        required_credits = float(path["total_required_credits"])
        group_audit = self._audit_graduation_components(passed_codes)

        path_group_ids = set()
        mandatory_group_ids = set()
        groups = {group["id"]: group for group in data_loader.get_groups()}
        for component in path["components"]:
            if component["type"] == "GROUP_CREDITS":
                group_id = component["group_id"]
                path_group_ids.add(group_id)
                if float(groups[group_id]["catalog_credits"]) <= float(component["required_credits"]):
                    mandatory_group_ids.add(group_id)
            else:
                path_group_ids.update(option["group_id"] for option in component["options"])

        degree_course_codes = {
            code
            for group_id in path_group_ids
            for code in groups[group_id]["course_codes"]
        }
        total_accumulated_credits = self._credits_for_codes(
            passed_codes & degree_course_codes, course_map
        )

        unlearned_compulsory = []
        unlearned_elective = []
        for course in data_loader.get_all_courses():
            if course["code"] in passed_codes or course["code"] not in degree_course_codes:
                continue
            item = {
                "code": course["code"],
                "name": course["name"],
                "credits": course.get("credits", 0.0),
                "suggested_semester": course.get("suggested_semester"),
                "category": course.get("category", ""),
            }
            is_mandatory = bool(set(course.get("group_ids", [])) & mandatory_group_ids)
            if course.get("is_compulsory") or is_mandatory:
                unlearned_compulsory.append(item)
            elif float(course.get("credits", 0)) > 0:
                unlearned_elective.append(item)
        sort_key = lambda item: (item.get("suggested_semester") or 99, item["code"])
        unlearned_compulsory.sort(key=sort_key)
        unlearned_elective.sort(key=sort_key)

        completion_rate = min(100.0, round(total_accumulated_credits / required_credits * 100, 1))
        classification = get_academic_classification(cpa)
        remaining_credits = max(0.0, required_credits - total_accumulated_credits)
        # Học phần F của CTĐT nằm trong số TC còn lại; khi học lại, điểm mới
        # thay điểm F chứ không cộng thêm TC vào mẫu số CPA.
        failed_degree_credits = sum(
            v["credits"]
            for code, v in best_by_code.items()
            if v["scale4"] == 0 and code in degree_course_codes
        )
        final_cpa_credits = cpa_credits - failed_degree_credits + remaining_credits
        points_needed_for_kha = 2.50 * final_cpa_credits - total_grade_points
        gpa_needed_for_kha = max(0.0, round(points_needed_for_kha / remaining_credits, 2)) if remaining_credits else 0.0

        pending_reqs = []
        for component in group_audit:
            if not component["is_complete"]:
                pending_reqs.append(
                    f"{component['name']}: còn thiếu {component['remaining_credits']:.1f} tín chỉ"
                )
        if cpa < MIN_GRADUATION_CPA:
            pending_reqs.append(f"CPA cần đạt tối thiểu {MIN_GRADUATION_CPA:.1f} (hiện tại: {cpa})")

        non_credit_groups = [
            {
                "group_id": group["id"],
                "name": group["name"],
                "course_codes": group["course_codes"],
                "note": "Yêu cầu không tính vào tổng tín chỉ; cần đối chiếu quy định chuẩn đầu ra.",
            }
            for group in data_loader.get_groups()
            if group.get("source_group_code") in {"220", "230", "240"}
        ]
        if non_credit_groups:
            pending_reqs.append(
                "Chưa xác minh các yêu cầu không tính tín chỉ: GDTC, GDQP và Tiếng Anh"
            )

        return {
            "student_info": info,
            "curriculum": {
                **program,
                "graduation_path_id": path["id"],
                "graduation_formula": path["raw_expression"],
                "source_file": data_loader.get_curriculum().get("_dataset_file"),
            },
            "cpa": cpa,
            "academic_classification": classification,
            "target_kha_advice": {
                "gpa_needed_remaining": gpa_needed_for_kha,
                "remaining_credits": remaining_credits,
                "is_achievable": gpa_needed_for_kha <= 4.0,
            },
            "warning_level": warning_level,
            "warning_description": limit_info["desc"],
            "warning_basis": warning["basis"],
            "debt_credits": warning["debt_credits"],
            "credit_limit": limit_info,
            "total_credits_accumulated": total_accumulated_credits,
            "total_credits_required": required_credits,
            "completion_percentage": completion_rate,
            "passed_count": len(passed_courses),
            "failed_count": len(failed_courses),
            "unlearned_compulsory_courses": unlearned_compulsory,
            "unlearned_elective_courses": unlearned_elective,
            "graduation_group_audit": group_audit,
            "non_credit_requirements": non_credit_groups,
            "graduation_ready": not pending_reqs,
            "pending_requirements": pending_reqs,
        }

    def list_profiles(self) -> List[Dict[str, Any]]:
        return data_loader.list_available_profiles()

    def switch_student(self, student_id: str) -> Dict[str, Any]:
        data_loader.load_student_profile(student_id)
        return {
            "status": "success",
            "active_student_id": student_id,
            "profile": self.get_profile(),
            "audit": self.audit_degree(),
        }

    def import_transcript(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Import a personal transcript from copied CTT text or course objects."""
        import re

        student_id = data.get("student_id", "custom").strip()
        student_name = data.get("student_name", "Sinh viên Tự nhập").strip()
        class_name = data.get("class_name", "Điện tử 01 - K67").strip()
        raw_text = data.get("raw_text", "")
        transcript = []

        source_items = []
        skipped = []
        if raw_text:
            for line in raw_text.splitlines():
                code_match = re.search(r"\b([A-Z]{2,3}\d{4}[A-Z]?)\b", line.upper())
                if code_match:
                    source_items.append({
                        "code": code_match.group(1),
                        "letter_grade": parse_grade_from_line(line[code_match.end():]),
                        "_line": line.strip(),
                    })
        else:
            source_items = data.get("courses", [])

        for item in source_items:
            code = (item.get("code") or "").upper()
            if not code:
                continue
            letter = (item.get("letter_grade") or "").strip().upper()
            if letter not in GRADE_TO_SCALE4:
                # Dòng chưa có điểm (đang học, R, I...) không được tự gán điểm.
                skipped.append(item.get("_line") or code)
                continue
            course = data_loader.get_course(code)
            transcript.append({
                "code": code,
                "name": item.get("name") or (course.get("name") if course else f"Học phần {code}"),
                "credits": float(item.get("credits") or (course.get("credits", 3.0) if course else 3.0)),
                "letter_grade": letter,
                "numeric_grade": GRADE_TO_SCALE4.get(letter, 0.0),
                "is_passed": letter != "F",
            })

        if not transcript:
            raise ValueError(
                "Không đọc được học phần nào có điểm chữ hợp lệ (A+, A, B+, B, C+, C, D+, D, F)."
            )

        custom_profile = {
            "info": {
                "program_id": data.get("program_id", "1654"),
                "program_code": data.get("program_code", "ET1"),
                "curriculum_version": str(data.get("curriculum_version", "2022")),
                "program_name": "Kỹ thuật Điện tử - Viễn thông",
                "student_id": student_id,
                "student_name": student_name,
                "class_name": class_name,
                "badge": "Tự nhập CTT",
                "persona": f"Hồ sơ cá nhân của {student_name} ({student_id})",
                # Mức cảnh báo học tập hiển thị trên CTT (0-3), nếu sinh viên nhập.
                "warning_level": data.get("warning_level"),
            },
            "total_courses_completed": sum(item["is_passed"] for item in transcript),
            "passed_courses": [item for item in transcript if item["is_passed"]],
            "failed_courses": [item for item in transcript if not item["is_passed"]],
            "transcript": transcript,
        }
        data_loader.save_custom_profile(custom_profile)
        return {
            "status": "success",
            "message": f"Đã nạp thành công bảng điểm gồm {len(transcript)} môn học!"
            + (f" Bỏ qua {len(skipped)} dòng chưa có điểm chữ." if skipped else ""),
            "skipped_lines": skipped,
            "profile": custom_profile,
            "audit": self.audit_degree(),
        }

    def update_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        profile = data_loader.update_profile_info(payload)
        return {
            "status": "success",
            "message": "Cập nhật thông tin hồ sơ thành công!",
            "profile": profile,
            "audit": self.audit_degree(),
        }


student_service = StudentService()
