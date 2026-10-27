from typing import Dict, List, Set, Tuple, Optional, Any
from app.services.data_loader import data_loader

class RuleEngine:
    def __init__(self):
        pass

    @staticmethod
    def _course_label(code: str) -> str:
        course = data_loader.get_course(code)
        name = course.get("name", "") if course else ""
        if name:
            return f"{code} ({name})"
        program = data_loader.get_program()
        label = f"CTĐT {program.get('program_code', '')}–{program.get('curriculum_version', '')}".rstrip("–")
        return f"{code} (chưa có tên trong danh mục {label})"

    def check_eligibility(
        self,
        course_code: str,
        student_profile: Optional[Dict[str, Any]] = None,
        simulated_passed_codes: Optional[List[str]] = None,
        concurrent_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Kiểm tra tính hợp lệ khi đăng ký môn học theo đúng cú pháp điều kiện HUST:
        - Tiên quyết (!): Bắt buộc đã qua môn (điểm >= D)
        - Học trước: Bắt buộc đã từng học / có điểm
        - Song hành (=): Đã học hoặc đăng ký cùng kỳ này (concurrent_codes)
        - Phép HOẶC (/): Chỉ cần thoả mãn 1 phương án điều kiện
        - Phép VÀ (,): Thoả mãn tất cả môn trong cùng phương án
        - Tín chỉ tích lũy tối thiểu (ví dụ: Đồ án 1: 90 TC, Đồ án TN: 120 TC)
        """
        if student_profile is None:
            student_profile = data_loader.get_student_profile()

        course = data_loader.get_course(course_code)
        rule = data_loader.get_rule(course_code)

        if not course and not rule:
            return {
                "course_code": course_code,
                "course_name": course_code,
                "is_eligible": False,
                "status": "NOT_FOUND",
                "reasons": [f"Không tìm thấy môn học {course_code} trong chương trình đào tạo của bạn."],
                "missing_prerequisites": [],
                "missing_prior_courses": [],
                "missing_alternative_branches": []
            }

        course_name = (rule.get("name") if rule else None) or (course.get("name") if course else course_code)

        # Tập hợp mã môn đã qua và đã học
        passed_codes: Set[str] = set()
        learned_codes: Set[str] = set()
        total_credits_accumulated: float = 0.0

        if simulated_passed_codes is not None:
            passed_codes = set(simulated_passed_codes)
            learned_codes = set(simulated_passed_codes)
            # Ước tính tín chỉ tích lũy từ simulated_passed_codes
            for c_code in passed_codes:
                c_item = data_loader.get_course(c_code)
                if c_item:
                    total_credits_accumulated += c_item.get("credits", 0.0)
        else:
            for item in student_profile.get("passed_courses", []):
                passed_codes.add(item["code"])
                learned_codes.add(item["code"])
                total_credits_accumulated += float(item.get("credits", 0.0))

            for item in student_profile.get("failed_courses", []):
                learned_codes.add(item["code"])

        concurrent_set = set(concurrent_codes or [])

        # 1. Kiểm tra nếu sinh viên đã qua môn này rồi
        if course_code in passed_codes:
            return {
                "course_code": course_code,
                "course_name": course_name,
                "is_eligible": True,
                "status": "ALREADY_PASSED",
                "reasons": [f"Bạn đã hoàn thành môn {course_code} - {course_name} (Điểm đạt). Bạn có thể đăng ký lại nếu muốn học cải thiện điểm."],
                "missing_prerequisites": [],
                "missing_prior_courses": [],
                "missing_alternative_branches": []
            }

        # 2. Kiểm tra tín chỉ tích lũy tối thiểu (ví dụ Đồ án tốt nghiệp 120 TC, Đồ án 1: 90 TC)
        min_credits = rule.get("min_credits_accumulated", 0) if rule else 0
        if min_credits > 0 and total_credits_accumulated < min_credits:
            return {
                "course_code": course_code,
                "course_name": course_name,
                "is_eligible": False,
                "status": "BLOCKED",
                "reasons": [
                    f"Chưa đủ điều kiện số tín chỉ tích lũy tối thiểu: Yêu cầu {min_credits} TC, hiện tại bạn mới tích lũy được {total_credits_accumulated:.1f} TC."
                ],
                "missing_prerequisites": [],
                "missing_prior_courses": [],
                "missing_alternative_branches": []
            }

        # 3. Đánh giá cây điều kiện (condition_tree)
        condition_tree = rule.get("condition_tree", []) if rule else []

        # Nếu không có điều kiện nào -> ĐỦ ĐIỀU KIỆN
        if not condition_tree or len(condition_tree) == 0:
            return {
                "course_code": course_code,
                "course_name": course_name,
                "is_eligible": True,
                "status": "ELIGIBLE",
                "reasons": [f"Môn {course_code} không có điều kiện ràng buộc. Bạn hoàn toàn đủ điều kiện đăng ký."],
                "missing_prerequisites": [],
                "missing_prior_courses": [],
                "missing_alternative_branches": []
            }

        # Duyệt qua các nhánh OR (chỉ cần 1 nhánh thoả mãn là ĐỦ ĐIỀU KIỆN)
        satisfied_branch = None
        branch_failures = []

        for branch_idx, branch in enumerate(condition_tree):
            branch_ok = True
            branch_missing_prereqs = []
            branch_missing_priors = []
            branch_missing_cores = []

            for item in branch:
                req_code = item["code"]
                req_type = item["type"]

                if req_type == "PREREQUISITE":
                    # Bắt buộc đã qua môn
                    if req_code not in passed_codes:
                        branch_ok = False
                        branch_missing_prereqs.append(req_code)
                elif req_type == "COREQUISITE":
                    # Đã học, đã qua, hoặc đăng ký cùng kỳ
                    if req_code not in learned_codes and req_code not in concurrent_set:
                        branch_ok = False
                        branch_missing_cores.append(req_code)
                else: # PRIOR (Học trước)
                    # Bắt buộc đã từng học / có điểm
                    if req_code not in learned_codes:
                        branch_ok = False
                        branch_missing_priors.append(req_code)

            if branch_ok:
                satisfied_branch = branch
                break
            else:
                branch_failures.append({
                    "branch_idx": branch_idx,
                    "missing_prereqs": branch_missing_prereqs,
                    "missing_priors": branch_missing_priors,
                    "missing_cores": branch_missing_cores
                })

        # Nếu có ít nhất 1 nhánh thoả mãn
        if satisfied_branch is not None:
            req_descs = []
            for item in satisfied_branch:
                c_item = data_loader.get_course(item["code"])
                c_name = c_item.get("name", item["code"]) if c_item else item["code"]
                kind = "tiên quyết" if item["type"] == "PREREQUISITE" else ("song hành" if item["type"] == "COREQUISITE" else "học trước")
                req_descs.append(f"{item['code']} ({c_name} - {kind})")

            return {
                "course_code": course_code,
                "course_name": course_name,
                "is_eligible": True,
                "status": "ELIGIBLE",
                "reasons": [
                    f"Đủ điều kiện đăng ký môn {course_code} - {course_name}.",
                    f"Đã thỏa mãn phương án điều kiện: {', '.join(req_descs)}." if req_descs else "Không có ràng buộc ngăn cản."
                ],
                "missing_prerequisites": [],
                "missing_prior_courses": [],
                "missing_alternative_branches": [],
                "satisfied_branch": satisfied_branch
            }

        # Nếu tất cả các nhánh đều không thoả mãn -> BỊ CHẶN
        has_alternatives = len(branch_failures) > 1
        if has_alternatives:
            reasons = [
                f"Chưa đủ điều kiện đăng ký môn {course_code} - {course_name}.",
                "Điều kiện có phép HOẶC (`/`): chỉ cần thỏa mãn một phương án, không cần hoàn thành tất cả các môn ở các phương án."
            ]
        else:
            reasons = [f"Chưa đủ điều kiện đăng ký môn {course_code} - {course_name}."]

        for f_info in branch_failures:
            f_parts = []
            if f_info["missing_prereqs"]:
                names = [self._course_label(c) for c in f_info["missing_prereqs"]]
                f_parts.append(f"Thiếu môn tiên quyết: {', '.join(names)}")
            if f_info["missing_priors"]:
                names = [self._course_label(c) for c in f_info["missing_priors"]]
                f_parts.append(f"Chưa học môn học trước: {', '.join(names)}")
            if f_info["missing_cores"]:
                names = [self._course_label(c) for c in f_info["missing_cores"]]
                f_parts.append(f"Chưa đăng ký môn song hành: {', '.join(names)}")
            if f_parts:
                prefix = f"Phương án {f_info['branch_idx'] + 1} chưa đạt: " if has_alternatives else ""
                reasons.append(prefix + " | ".join(f_parts))

        # Với OR, danh sách thiếu của từng nhánh phải được giữ nguyên. Không
        # trả union (ET3200 + ET4070), vì union dễ bị hiểu thành AND. Các
        # trường missing_* ở cấp cao nhất chỉ phản ánh yêu cầu chung của mọi
        # nhánh; với một nhánh duy nhất chúng vẫn giữ nguyên hành vi cũ.
        def common_missing(key: str) -> Set[str]:
            values = [set(item[key]) for item in branch_failures]
            if not values:
                return set()
            if len(values) == 1:
                return values[0]
            return set.intersection(*values)

        missing_alternative_branches = [
            {
                "branch_idx": item["branch_idx"],
                "missing_prerequisites": sorted(item["missing_prereqs"]),
                "missing_prior_courses": sorted(item["missing_priors"]),
                "missing_corequisites": sorted(item["missing_cores"]),
            }
            for item in branch_failures
        ] if has_alternatives else []

        return {
            "course_code": course_code,
            "course_name": course_name,
            "is_eligible": False,
            "status": "BLOCKED",
            "reasons": reasons,
            "missing_prerequisites": sorted(common_missing("missing_prereqs")),
            "missing_prior_courses": sorted(common_missing("missing_priors")),
            "missing_alternative_branches": missing_alternative_branches,
        }

# Singleton instance
rule_engine = RuleEngine()
