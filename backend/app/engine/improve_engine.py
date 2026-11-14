"""Thuật toán phân tích và gợi ý học phần cải thiện điểm (Course Improvement Engine)

Áp dụng quy chế đào tạo Đại học Bách khoa Hà Nội (QĐ 5445/QĐ-ĐHBK) và kế thừa
triết lý tính toán tối ưu CPA từ kiến trúc iLoveBK.
"""

from typing import Any, Dict, List, Optional
from app.core.hust_rules import (
    GRADE_TO_SCALE4,
    PASSING_GRADES,
    get_academic_classification,
)


class CourseImprovementEngine:
    """Engine phân tích các môn điểm thấp (D, D+, F) và mô phỏng tác động cải thiện CPA."""

    TARGET_GRADES = ["C", "B", "B+", "A"]

    def analyze_improvements(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Phân tích toàn bộ bảng điểm để tìm ra danh sách môn nên học cải thiện/học lại,

        tính toán mức tăng CPA cụ thể cho từng mục tiêu điểm số.
        """
        transcript = profile.get("transcript", [])
        passed_courses = profile.get("passed_courses", [])
        failed_courses = profile.get("failed_courses", [])
        cpa_current = float(profile.get("info", {}).get("cpa", 0.0) or 0.0)

        # 1. Tính tổng số tín chỉ tính điểm CPA hiện tại
        # Các môn đã học có điểm và số tín chỉ > 0
        total_eval_credits = sum(
            float(c.get("credits", 0.0)) for c in transcript if float(c.get("credits", 0.0)) > 0
        )
        if total_eval_credits <= 0:
            total_eval_credits = sum(float(c.get("credits", 0.0)) for c in passed_courses) + sum(
                float(c.get("credits", 0.0)) for c in failed_courses
            )

        if total_eval_credits <= 0:
            return {
                "current_cpa": cpa_current,
                "current_classification": get_academic_classification(cpa_current),
                "total_credits": 0.0,
                "improve_candidates": [],
                "summary": "Chưa có đủ dữ liệu bảng điểm để phân tích môn cải thiện.",
            }

        # 2. Lọc các môn có thể học lại hoặc học cải thiện
        # Quy chế Bách Khoa: Điểm F bắt buộc học lại; Điểm D, D+ được học cải thiện.
        candidates = []
        seen_codes = set()

        # Quét môn F trước (ưu tiên cao)
        for item in failed_courses:
            code = item.get("code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                candidates.append({**item, "is_failed": True})

        # Quét các môn D, D+ trong passed_courses
        for item in passed_courses:
            code = item.get("code")
            letter = item.get("letter_grade", "").upper()
            if code and code not in seen_codes and letter in {"D", "D+"}:
                seen_codes.add(code)
                candidates.append({**item, "is_failed": False})

        # 3. Tính toán tác động CPA cho từng môn
        analysis_list = []
        for course in candidates:
            code = course.get("code", "")
            name = course.get("name", "")
            credits = float(course.get("credits", 0.0))
            current_letter = course.get("letter_grade", "F").upper()
            current_num = float(course.get("numeric_grade", GRADE_TO_SCALE4.get(current_letter, 0.0)))
            is_failed = course.get("is_failed", False)

            # Mô phỏng nếu đạt điểm target: C (2.0), B (3.0), B+ (3.5), A (4.0)
            projections = {}
            for tgt in self.TARGET_GRADES:
                tgt_num = GRADE_TO_SCALE4[tgt]
                if tgt_num > current_num:
                    delta_pts = (tgt_num - current_num) * credits
                    # Nếu là môn F học lại thì tổng tín chỉ tích lũy tăng thêm `credits`
                    # Đối với môn D/D+ cải thiện thì tổng số tín chỉ giữ nguyên, chỉ thay điểm
                    new_cpa = cpa_current + (delta_pts / total_eval_credits)
                    projections[tgt] = {
                        "new_cpa": round(min(4.0, new_cpa), 2),
                        "delta_cpa": round(delta_pts / total_eval_credits, 3),
                    }

            # Xác định mức độ ưu tiên
            if is_failed:
                priority = "HIGH"
                reason = "Môn nợ đọng (F). Bắt buộc học lại để tích lũy tín chỉ và tránh cảnh báo học tập."
            elif credits >= 3.0:
                priority = "HIGH"
                reason = f"Môn {credits:g} tín chỉ điểm {current_letter}. Kéo CPA rất hiệu quả khi cải thiện lên B/A."
            else:
                priority = "MEDIUM"
                reason = f"Môn {credits:g} tín chỉ điểm {current_letter}. Cải thiện để tối ưu điểm tổng kết."

            # Hiệu quả trên mỗi tín chỉ (với mục tiêu B)
            target_b_delta = projections.get("B", {}).get("delta_cpa", 0.0)

            analysis_list.append({
                "code": code,
                "name": name,
                "credits": credits,
                "current_letter_grade": current_letter,
                "current_numeric_grade": current_num,
                "is_failed": is_failed,
                "priority": priority,
                "reason": reason,
                "projections": projections,
                "efficiency_score": target_b_delta,
            })

        # Sắp xếp: Môn HIGH trước, sau đó theo efficiency_score giảm dần
        priority_weight = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
        analysis_list.sort(
            key=lambda x: (priority_weight.get(x["priority"], 0), x["efficiency_score"]),
            reverse=True
        )

        curr_class = get_academic_classification(cpa_current)

        return {
            "current_cpa": cpa_current,
            "current_classification": curr_class,
            "total_credits": total_eval_credits,
            "total_candidates": len(analysis_list),
            "improve_candidates": analysis_list,
            "summary": (
                f"Hiện tại CPA của bạn là {cpa_current:.2f} ({curr_class.get('rank', 'Trung bình')}). "
                f"Có {len(analysis_list)} môn học có thể cải thiện hoặc học lại để nâng CPA."
            ),
        }


course_improvement_engine = CourseImprovementEngine()
