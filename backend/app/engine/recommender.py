from typing import Dict, List, Set, Any, Optional
from app.services.data_loader import data_loader
from app.engine.rule_engine import rule_engine
from app.core.hust_rules import assess_academic_warning, credit_limits_for_warning


LEGACY_TRACK_ALIASES = {
    "EMBEDDED_IOT": "MOD1",
    "TELECOM_NETWORK": "MOD2",
    "BIOMEDICAL": "MOD3",
    "IC_DESIGN": "MOD6",
}

class CourseRecommender:
    def __init__(self):
        pass

    def recommend(
        self,
        student_profile: Optional[Dict[str, Any]] = None,
        target_track: Optional[str] = None,
        max_credits: Optional[int] = 20,
        is_summer: bool = False
    ) -> Dict[str, Any]:
        """
        Thuật toán đề xuất môn học thông minh theo thứ tự ưu tiên:
        1. Ưu tiên 1: Môn nợ / Môn trượt (nếu có)
        2. Ưu tiên 2: Môn bắt buộc chưa học của kỳ hiện tại / kỳ kế tiếp
        3. Ưu tiên 3: Môn tự chọn định hướng chuyên ngành (theo track mà SV chọn)
        4. Giới hạn số tín chỉ tối đa theo mức cảnh cáo học tập
        """
        if student_profile is None:
            student_profile = data_loader.get_student_profile()

        passed_codes = set(c["code"] for c in student_profile.get("passed_courses", []))
        failed_codes = set(c["code"] for c in student_profile.get("failed_courses", []))

        # Hạn mức tín chỉ theo mức cảnh báo học tập (Điều 19 QĐ 5445)
        warning = assess_academic_warning(student_profile)
        limit_info = credit_limits_for_warning(warning)
        allowed_max = limit_info["summer_max"] if is_summer else limit_info["max"]
        target_max_credits = min(max_credits or 20, allowed_max)

        all_courses = data_loader.get_all_courses()
        unlearned_courses = [c for c in all_courses if c["code"] not in passed_codes]

        recommended_items = []
        current_credits = 0.0
        selected_codes = set()

        # Track info
        normalized_track = LEGACY_TRACK_ALIASES.get(target_track, target_track)
        tracks = {track["id"]: track for track in data_loader.get_module_tracks()}
        track_info = tracks.get(normalized_track) if normalized_track else None
        if target_track and not track_info:
            raise ValueError(
                f"Mô-đun {target_track} không tồn tại trong CTĐT đang chọn. "
                f"Giá trị hợp lệ: {', '.join(tracks)}"
            )
        track_core_set = set(track_info["core_courses"]) if track_info else set()

        # Nhóm 1: Môn nợ (Failed courses)
        for code in sorted(failed_codes):
            if code not in passed_codes and code not in selected_codes:
                c = data_loader.get_course(code)
                if not c:
                    continue
                c_credits = c.get("credits", 0.0)
                if current_credits + c_credits <= target_max_credits:
                    elig = rule_engine.check_eligibility(code, student_profile)
                    if elig["is_eligible"]:
                        recommended_items.append({
                            "code": code,
                            "name": c["name"],
                            "credits": c_credits,
                            "suggested_semester": c.get("suggested_semester"),
                            "is_compulsory": c.get("is_compulsory", False),
                            "category": c.get("category", ""),
                            "priority_reason": "Ưu tiên 1: Học lại môn chưa đạt để gỡ nợ và cải thiện CPA",
                            "prerequisite_summary": "Đủ điều kiện đăng ký lại"
                        })
                        current_credits += c_credits
                        selected_codes.add(code)

        # Nhóm 2: Môn bắt buộc chưa học (Sắp xếp theo kỳ gợi ý từ thấp đến cao)
        compulsory_unlearned = [
            c for c in unlearned_courses 
            if c.get("is_compulsory") and c["code"] not in selected_codes
        ]
        compulsory_unlearned.sort(key=lambda x: (x.get("suggested_semester") or 99, x["code"]))

        for c in compulsory_unlearned:
            code = c["code"]
            c_credits = c.get("credits", 0.0)
            if current_credits + c_credits <= target_max_credits:
                # Kiểm tra điều kiện (tính cả các môn đã chọn cùng kỳ này)
                elig = rule_engine.check_eligibility(
                    code, 
                    student_profile, 
                    concurrent_codes=list(selected_codes)
                )
                if elig["is_eligible"] and elig["status"] != "ALREADY_PASSED":
                    rule_info = data_loader.get_rule(code)
                    cond_str = rule_info.get("raw_condition", "") if rule_info else ""
                    recommended_items.append({
                        "code": code,
                        "name": c["name"],
                        "credits": c_credits,
                        "suggested_semester": c.get("suggested_semester"),
                        "is_compulsory": True,
                        "category": c.get("category", "Bắt buộc"),
                        "priority_reason": f"Ưu tiên 2: Môn bắt buộc thuộc khung kỳ {c.get('suggested_semester', 'tiếp theo')}",
                        "prerequisite_summary": f"Đủ điều kiện (ĐK gốc: '{cond_str}')" if cond_str else "Không ràng buộc"
                    })
                    current_credits += c_credits
                    selected_codes.add(code)

        # Nhóm 3: Môn tự chọn theo định hướng chuyên ngành (Track)
        if track_info:
            completed_track_credits = sum(
                float(data_loader.get_course(code).get("credits", 0))
                for code in passed_codes & track_core_set
                if data_loader.get_course(code)
            )
            selected_track_credits = 0.0
            track_courses = [
                c for c in unlearned_courses 
                if c["code"] in track_core_set and c["code"] not in selected_codes
            ]
            for c in track_courses:
                code = c["code"]
                c_credits = c.get("credits", 0.0)
                if current_credits + c_credits <= target_max_credits:
                    elig = rule_engine.check_eligibility(
                        code, 
                        student_profile, 
                        concurrent_codes=list(selected_codes)
                    )
                    if elig["is_eligible"] and elig["status"] != "ALREADY_PASSED":
                        recommended_items.append({
                            "code": code,
                            "name": c["name"],
                            "credits": c_credits,
                            "suggested_semester": c.get("suggested_semester"),
                            "is_compulsory": False,
                            "category": f"Tự chọn - {track_info['name']}",
                            "priority_reason": f"Ưu tiên 3: Tự chọn cốt lõi theo định hướng {track_info['name']}",
                            "prerequisite_summary": "Đủ điều kiện đăng ký"
                        })
                        current_credits += c_credits
                        selected_track_credits += c_credits
                        selected_codes.add(code)
                        if completed_track_credits + selected_track_credits >= float(track_info["required_credits"]):
                            break

        # Nhóm 4: Môn tự chọn chung / môn khác nếu còn chỉ tiêu tín chỉ
        if current_credits < target_max_credits:
            other_electives = [
                c for c in unlearned_courses 
                if not c.get("is_compulsory") and c["code"] not in selected_codes and not c["code"].startswith("PE")
            ]
            other_electives.sort(key=lambda x: (x.get("suggested_semester") or 99, x["code"]))
            for c in other_electives:
                code = c["code"]
                c_credits = c.get("credits", 0.0)
                if current_credits + c_credits <= target_max_credits:
                    elig = rule_engine.check_eligibility(
                        code, 
                        student_profile, 
                        concurrent_codes=list(selected_codes)
                    )
                    if elig["is_eligible"] and elig["status"] != "ALREADY_PASSED":
                        recommended_items.append({
                            "code": code,
                            "name": c["name"],
                            "credits": c_credits,
                            "suggested_semester": c.get("suggested_semester"),
                            "is_compulsory": False,
                            "category": c.get("category", "Tự chọn"),
                            "priority_reason": "Ưu tiên 4: Môn tự chọn bổ sung kiến thức tích lũy",
                            "prerequisite_summary": "Đủ điều kiện đăng ký"
                        })
                        current_credits += c_credits
                        selected_codes.add(code)

        advice_note = (
            f"Hệ thống đã đề xuất {len(recommended_items)} môn học với tổng cộng {current_credits:.1f} tín chỉ "
            f"(hạn mức lập kế hoạch {target_max_credits} TC). "
        )
        if limit_info["is_provisional"]:
            advice_note += "Chưa xác định mức cảnh báo; tạm giới hạn kế hoạch ở 14 TC/kỳ chính. Hãy đối chiếu CTT trước khi đăng ký. "
        if track_info:
            advice_note += f"Ưu tiên theo định hướng: {track_info['name']}."
        else:
            advice_note += (
                f"Bạn có thể chọn một trong {len(tracks)} mô-đun chính thức "
                "để lọc môn tự chọn."
            )

        return {
            "target_track": normalized_track,
            "track_name": track_info["name"] if track_info else "Mặc định (Chung)",
            "total_credits_suggested": current_credits,
            "max_allowed_credits": target_max_credits,
            "recommended_courses": recommended_items,
            "advice_note": advice_note
        }

# Singleton instance
course_recommender = CourseRecommender()
