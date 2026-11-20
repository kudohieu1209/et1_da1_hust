"""Phân tích học phần học lại và mô phỏng cải thiện CPA theo QĐ 5445."""
from itertools import chain
from typing import Any, Dict, Optional

from app.core.hust_rules import (
    ACADEMIC_CLASSIFICATIONS,
    GRADE_TO_SCALE4,
    HONORS_RETAKE_RATIO,
    best_attempts,
    cpa_from_attempts,
    get_academic_classification,
)


class CourseImprovementEngine:
    TARGET_GRADES = ("C", "C+", "B", "B+", "A")

    def analyze_improvements(
        self, profile: Dict[str, Any], required_credits: Optional[float] = None
    ) -> Dict[str, Any]:
        transcript = profile.get("transcript", [])
        best = best_attempts(transcript)
        cpa, _, cpa_credits = cpa_from_attempts(best)
        if not transcript:
            cpa = float(profile.get("info", {}).get("cpa") or 0.0)

        candidates = []
        for code, attempt in best.items():
            scale4 = attempt["scale4"]
            if scale4 >= 4.0:
                continue

            letter = attempt["letter"]
            credits = attempt["credits"]
            if letter == "F":
                category = "retake"
                priority = "HIGH"
                reason = "Điểm F, bắt buộc học lại để tích lũy tín chỉ."
            else:
                category = "improve_low" if letter in {"D", "D+"} else "improve"
                priority = "HIGH" if category == "improve_low" and credits >= 3 else "MEDIUM"
                reason = f"Học phần {credits:g} tín chỉ, có thể học lại để cải thiện điểm {letter}."

            projections = {}
            for grade in self.TARGET_GRADES:
                target = GRADE_TO_SCALE4[grade]
                if target > scale4:
                    # Điểm F đã nằm trong mẫu số CPA, nên chỉ thay điểm chất lượng.
                    delta = (target - scale4) * credits / cpa_credits
                    projections[grade] = {
                        "delta_cpa": round(delta, 3),
                        "new_cpa": round(min(4.0, cpa + delta), 2),
                    }

            candidates.append({
                "code": code,
                "name": attempt["name"],
                "credits": credits,
                "current_letter_grade": letter,
                "current_numeric_grade": scale4,
                "is_failed": category == "retake",
                "category": category,
                "priority": priority,
                "reason": reason,
                "projections": projections,
                "efficiency_score": projections.get("B", {}).get("delta_cpa", 0.0),
                "max_delta_cpa": projections["A"]["delta_cpa"],
            })

        category_order = {"retake": 0, "improve_low": 1, "improve": 2}
        candidates.sort(key=lambda course: (category_order[course["category"]], -course["max_delta_cpa"]))

        failed_attempts = (item for item in transcript if item.get("letter_grade") == "F")
        failed_by_code: Dict[str, float] = {}
        for item in chain(profile.get("failed_courses", []), failed_attempts):
            if code := item.get("code"):
                credits = float(item.get("credits") or 0.0)
                failed_by_code[code] = max(failed_by_code.get(code, 0.0), credits)
        retake_credits = sum(failed_by_code.values())
        basis_credits = cpa_credits if required_credits is None else float(required_credits)
        threshold_credits = round(basis_credits * HONORS_RETAKE_RATIO, 2)

        classification = get_academic_classification(cpa)
        summary = (
            f"Hiện tại CPA của bạn là {cpa:.2f} ({classification['rank']}). "
            f"Có {len(candidates)} môn học có thể cải thiện hoặc học lại để nâng CPA."
            if transcript else "Chưa có đủ dữ liệu bảng điểm để phân tích môn cải thiện."
        )
        return {
            "current_cpa": cpa,
            "current_classification": classification,
            "total_credits": cpa_credits,
            "cpa_credits": cpa_credits,
            "has_transcript": bool(transcript),
            "total_candidates": len(candidates),
            "improve_candidates": candidates,
            "summary": summary,
            "honors_rule": {
                "retake_credits": retake_credits,
                "basis_credits": basis_credits,
                "threshold_credits": threshold_credits,
                "exceeds": retake_credits > threshold_credits,
                "basis_source": "transcript" if required_credits is None else "program",
            },
            "classification_ladder": ACADEMIC_CLASSIFICATIONS,
        }


course_improvement_engine = CourseImprovementEngine()
