"""Persist a server-verified CTT snapshot only after all validation succeeds."""
import copy
import re
import secrets
import threading
from datetime import datetime, timezone

from app.auth.passwords import hash_password
from app.auth.store import UserExistsError
from app.services.curriculum_repository import curriculum_repository
from app.services.data_loader import data_loader
from app.services.school_portal import SchoolPortalError, SchoolSnapshot

_link_lock = threading.RLock()


def complete_school_login(auth_service, snapshot: SchoolSnapshot, program_code: str,
                          expected_student_id: str | None = None) -> tuple[str, dict]:
    student_id = snapshot.info.get("student_id", "")
    if not re.fullmatch(r"[0-9]{8}", student_id) or not snapshot.info.get("student_name"):
        raise SchoolPortalError("Chưa xác minh được danh tính sinh viên từ CTT.")
    if expected_student_id and expected_student_id != student_id:
        raise SchoolPortalError("MSSV CTT khác tài khoản đang đăng nhập. Chưa thay đổi hồ sơ.")
    if not snapshot.transcript:
        raise SchoolPortalError("Không có bảng điểm hợp lệ để đồng bộ.")
    with _link_lock:
        user = auth_service.get_user(student_id)
        if user and (user.get("is_admin") or user.get("is_demo")):
            raise SchoolPortalError("MSSV này đang được dành cho tài khoản quản trị hoặc demo. Chưa liên kết CTT.")
        key = auth_service.profiles.find_key(student_id)
        existing = auth_service.profiles.get(key) if key else None
        if existing and existing.get("info", {}).get("student_id") != student_id:
            raise SchoolPortalError("MSSV của hồ sơ hiện có không khớp. Chưa thay đổi dữ liệu.")
        profile = copy.deepcopy(existing) if existing else {"info": {}, "non_credit_status": {}}
        info = profile.setdefault("info", {})
        info.update({k: v for k, v in snapshot.info.items() if k in {"student_id", "student_name", "class_name", "email"}})
        # Entry year comes from the school's class or verified student ID, never a made-up class.
        if not info.get("curriculum_version") and not re.search(r"\bK\d{2}\b", info.get("class_name", ""), re.I):
            info["curriculum_version"] = student_id[:4]
        # Tự động nhận diện CTĐT từ tên lớp (ví dụ: Điện tử -> ET1, Cơ điện tử -> ME1)
        detected_program = curriculum_repository.infer_program_code(info.get("class_name", ""))
        entry_year = curriculum_repository._infer_version(info) or info.get("curriculum_version") or student_id[:4]
        if detected_program and (detected_program, str(entry_year)) in curriculum_repository._curricula:
            info["program_code"] = detected_program
        else:
            info.setdefault("program_code", program_code)
        curriculum = curriculum_repository.resolve_profile(profile)
        program = curriculum["program"]
        info.update({"program_code": program["program_code"], "program_id": program.get("program_id", program["program_code"]),
                     "program_name": program.get("name", ""), "curriculum_version": str(program["curriculum_version"])})
        profile.update({
            "transcript": copy.deepcopy(snapshot.transcript),
            "passed_courses": [copy.deepcopy(c) for c in snapshot.transcript if c["is_passed"]],
            "failed_courses": [copy.deepcopy(c) for c in snapshot.transcript if not c["is_passed"]],
            "total_courses_completed": sum(c["is_passed"] for c in snapshot.transcript),
            "semesters": copy.deepcopy(snapshot.semesters),
            "school_sync": {"source": "ctt-sis.hust.edu.vn", "synced_at": datetime.now(timezone.utc).isoformat(),
                            "course_count": len(snapshot.transcript)},
        })
        saved_services = profile.setdefault("school_services", {})
        for kind, incoming in snapshot.services.items():
            previous = saved_services.get(kind)
            if incoming.get("status") in {"error", "unavailable"} and previous and previous.get("status") in {"synced", "empty", "partial", "stale"}:
                saved_services[kind] = {**previous, "status": "stale", "last_attempt_at": incoming.get("synced_at"),
                                        "message": incoming.get("message") or "Chưa cập nhật được; đang hiển thị lần đồng bộ trước."}
            else:
                saved_services[kind] = copy.deepcopy(incoming)
        warning = snapshot.services.get("warning", {})
        if warning.get("status") == "synced" and warning.get("warning_level") is not None:
            info["warning_level"] = warning["warning_level"]
            info["warning_source"] = "ctt"
        certificates = snapshot.services.get("certificates", {})
        for key, status in certificates.get("requirements", {}).items():
            if key in {"220", "230", "240"} and status in {"completed", "incomplete"}:
                profile.setdefault("non_credit_status", {})[key] = status
                profile.setdefault("non_credit_sources", {})[key] = {"source": "ctt", "synced_at": certificates.get("synced_at")}
        profile["school_sync"]["sections"] = {kind: section.get("status") for kind, section in saved_services.items()}
        created_user = False
        if user is None:
            try:
                # No school password is requested or stored, including as a reusable local password.
                auth_service.store.create_user({"student_id": student_id, "password_hash": hash_password(secrets.token_urlsafe(48)),
                                                "auth_provider": "ctt", "created_at": auth_service.clock()})
                created_user = True
            except UserExistsError:
                raise SchoolPortalError("Tài khoản vừa được tạo ở một phiên khác. Vui lòng kết nối lại.") from None
        try:
            data_loader.save_profile_for(student_id, profile)
        except Exception:
            if created_user:
                auth_service.store.delete_user(student_id)
            raise
        auth_service.store.record_successful_login(student_id, auth_service.clock())
        return auth_service._start_session(student_id), profile["school_sync"]
