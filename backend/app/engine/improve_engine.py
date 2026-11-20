"""Phân tích học phần học lại và mô phỏng cải thiện CPA theo QĐ 5445."""
from itertools import chain
from typing import Any, Dict, Iterable, List, Optional

from app.core.hust_rules import (
    ACADEMIC_CLASSIFICATIONS,
    GRADE_TO_SCALE4,
    HONORS_RETAKE_RATIO,
    best_attempts,
    cpa_from_attempts,
    get_academic_classification,
)


def build_upcoming(
    current_term: Optional[Iterable[Any]] = None,
    unlearned_compulsory: Optional[List[Dict[str, Any]]] = None,
    unlearned_elective: Optional[List[Dict[str, Any]]] = None,
    course_catalog: Optional[Dict[str, Any]] = None,
    best_attempts_data: Optional[Any] = None,
    current_term_names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Tạo danh sách môn sắp học từ TKB kỳ này và môn chưa học trong CTĐT."""
    if isinstance(best_attempts_data, dict):
        best_codes = set(best_attempts_data.keys())
    elif isinstance(best_attempts_data, list):
        best_codes = set(best_attempts(best_attempts_data).keys())
    elif isinstance(best_attempts_data, set):
        best_codes = set(best_attempts_data)
    else:
        best_codes = set()

    catalog = course_catalog or {}
    term_names = dict(current_term_names or {})
    term_codes: List[str] = []
    if current_term:
        for item in current_term:
            if isinstance(item, str):
                code = item.strip().upper()
            elif isinstance(item, dict):
                code = (item.get("code") or item.get("course_code") or "").strip().upper()
                if item.get("name") or item.get("course_name"):
                    term_names[code] = item.get("name") or item.get("course_name")
            else:
                code = str(item).strip().upper()
            if code and code not in term_codes:
                term_codes.append(code)

    upcoming: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()

    # 1. Current term courses (TKB)
    for code in term_codes:
        if code in best_codes:
            continue
        if code.startswith("PE"):
            continue
        course_info = catalog.get(code)
        if course_info:
            credits_val = course_info.get("credits")
            if credits_val is not None:
                credits_float = float(credits_val)
                if credits_float <= 0:
                    continue
                credits = credits_float
                credits_known = True
            else:
                credits = None
                credits_known = False
            name = course_info.get("name") or term_names.get(code, code)
            suggested_semester = course_info.get("suggested_semester")
            is_compulsory = bool(course_info.get("is_compulsory"))
        else:
            credits = None
            credits_known = False
            name = term_names.get(code, code)
            suggested_semester = None
            is_compulsory = False

        upcoming.append({
            "code": code,
            "name": name,
            "credits": credits,
            "source": "current_term",
            "suggested_semester": suggested_semester,
            "is_compulsory": is_compulsory,
            "credits_known": credits_known,
        })
        seen_codes.add(code)

    # 2. Curriculum courses (CTĐT)
    def add_curriculum_courses(items: Optional[List[Dict[str, Any]]], compulsory: bool):
        if not items:
            return
        for item in items:
            code = (item.get("code") or "").strip().upper()
            if not code or code in seen_codes or code in best_codes:
                continue
            if code.startswith("PE"):
                continue
            credits_val = item.get("credits")
            if credits_val is not None:
                credits_float = float(credits_val)
                if credits_float <= 0:
                    continue
                credits = credits_float
                credits_known = True
            else:
                credits = None
                credits_known = False

            upcoming.append({
                "code": code,
                "name": item.get("name") or code,
                "credits": credits,
                "source": "curriculum",
                "suggested_semester": item.get("suggested_semester"),
                "is_compulsory": compulsory,
                "credits_known": credits_known,
            })
            seen_codes.add(code)

    add_curriculum_courses(unlearned_compulsory, True)
    add_curriculum_courses(unlearned_elective, False)

    return upcoming


class CourseImprovementEngine:
    TARGET_GRADES = ("C", "C+", "B", "B+", "A")

    def analyze_improvements(
        self,
        profile: Dict[str, Any],
        required_credits: Optional[float] = None,
        *,
        current_term_codes: Optional[Iterable[Any]] = None,
        current_term_names: Optional[Dict[str, str]] = None,
        course_catalog: Optional[Dict[str, Any]] = None,
        unlearned_compulsory: Optional[List[Dict[str, Any]]] = None,
        unlearned_elective: Optional[List[Dict[str, Any]]] = None,
        final_cpa_credits: Optional[float] = None,
        remaining_credits: Optional[float] = None,
    ) -> Dict[str, Any]:
        transcript = profile.get("transcript", [])
        best = best_attempts(transcript)
        cpa, total_grade_points, cpa_credits = cpa_from_attempts(best)
        if not transcript:
            cpa = float(profile.get("info", {}).get("cpa") or 0.0)

        term_code_set = set()
        if current_term_codes:
            for item in current_term_codes:
                if isinstance(item, str):
                    term_code_set.add(item.strip().upper())
                elif isinstance(item, dict):
                    c = (item.get("code") or item.get("course_code") or "").strip().upper()
                    if c:
                        term_code_set.add(c)
                else:
                    term_code_set.add(str(item).strip().upper())

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
                "in_current_term": code in term_code_set,
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

        upcoming_courses = build_upcoming(
            current_term=current_term_codes,
            unlearned_compulsory=unlearned_compulsory,
            unlearned_elective=unlearned_elective,
            course_catalog=course_catalog,
            best_attempts_data=best,
            current_term_names=current_term_names,
        )

        cpa_points = float(total_grade_points) if transcript else (cpa * cpa_credits)
        program_projection = (
            {
                "final_cpa_credits": float(final_cpa_credits),
                "remaining_credits": float(remaining_credits),
            }
            if (final_cpa_credits is not None and remaining_credits is not None)
            else None
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
            "cpa_points": cpa_points,
            "upcoming_courses": upcoming_courses,
            "program_projection": program_projection,
        }


course_improvement_engine = CourseImprovementEngine()
