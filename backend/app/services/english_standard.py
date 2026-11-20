"""Show official CTT evidence separately from published English requirements."""

import re
from math import isfinite

from app.services.ctt_sections import fold
from app.services.curriculum_repository import cohort_from_class_name

K70 = "quy_dinh_ngoai_ngu_k70_verified.md"
K71 = "quy_dinh_ngoai_ngu_k71_verified.md"


def _evidence(filename, lines, quote):
    return {"source": f"{filename}:{lines}", "quote": quote}


def _conversion(filename, level, lines, quote, *, placement=None, skills=None, note=None):
    return {"level": level, "placement": placement, "skills": skills, "note": note,
            **_evidence(filename, lines, quote)}


def _graduation(filename, lines, quote, level, note=None):
    return {"level": level, "note": note, **_evidence(filename, lines, quote)}


def _registration(filename, lines, quote, semesters, *, placement_table=None, courses=()):
    return {"semesters": semesters, "placement_table": placement_table, "courses": courses,
            **_evidence(filename, lines, quote)}


ENGLISH_RULES = (
    {
        "decision": "10728/QĐ-ĐHBK",
        "applies_from_cohort": 70,
        "applies_to_cohort": 70,
        "source_file": K70,
        **_evidence(K70, "422-422", "Yêu cầu trình độ tiếng Anh theo học kỳ và chuẩn ngoại ngữ đầu ra khi xét tốt nghiệp"),
        "conversion_table": (
            # Skill ranges are ordered listening, reading, speaking, writing.
            _conversion(K70, "1", "315-316", "60÷105 60÷110 50÷80 30÷60",
                        placement=(120, 220), skills=((60, 105), (60, 110), (50, 80), (30, 60))),
            _conversion(K70, "2.1", "318-319", "110÷165 115÷170 90 70÷80",
                        placement=(225, 340), skills=((110, 165), (115, 170), (90, 90), (70, 80))),
            _conversion(K70, "2.2", "321-322", "170÷215 175÷215 100 90÷100",
                        placement=(345, 435), skills=((170, 215), (175, 215), (100, 100), (90, 100))),
            _conversion(K70, "2.3", "322-327", "220÷270 220÷270 110 110",
                        placement=(440, 545), skills=((220, 270), (220, 270), (110, 110), (110, 110))),
            _conversion(K70, "3.1", "329-331", "275÷310 275÷310 120 120",
                        placement=(550, 620), skills=((275, 310), (275, 310), (120, 120), (120, 120))),
            _conversion(K70, "3.2", "332-335", "315÷395 315÷380 130÷150 130÷140",
                        placement=(625, 780), skills=((315, 395), (315, 380), (130, 150), (130, 140))),
            _conversion(K70, "4", "334-339", "400÷485 385÷450 160÷170 150÷170",
                        placement=(785, 940), skills=((400, 485), (385, 450), (160, 170), (150, 170))),
            _conversion(K70, "5", "336-346", "490÷495 455÷495 180÷200 180÷200",
                        placement=(945, 990), skills=((490, 495), (455, 495), (180, 200), (180, 200))),
            _conversion(K70, "6", "348-349", "Bậc 6", note="Bảng 2.1 không có mức TOEIC cho bậc này."),
        ),
        "graduation": {
            "standard": _graduation(K70, "438-441", "Đạt chứng chỉ trình độ tối thiểu Bậc 3", 3),
            "talent": _graduation(K70, "443-445", "Được quy định bằng văn bản riêng", None,
                                  "Chuẩn tốt nghiệp của CTĐT tài năng được quy định bằng văn bản riêng."),
            "elitech": _graduation(K70, "507-519", "Đạt chứng chỉ trình độ tối thiểu Bậc 4", 4),
        },
        "registration_by_semester": {
            "standard": (
                _registration(K70, "426-427", "Được xếp lớp học theo quy định tại Bảng 3.1", (1, 2), placement_table="3.1"),
                _registration(K70, "429-430", "đăng ký học song hành học phần FL1133", (3,), courses=("FL1133",)),
                _registration(K70, "432-433", "đăng ký học song hành học phần FL1134", (4,), courses=("FL1134",)),
                _registration(K70, "435-436", "đăng ký học song hành học phần FL1135", (5,), courses=("FL1135",)),
            ),
            "elitech": (
                _registration(K70, "512-513", "Được xếp lớp học theo quy định tại Bảng 4.1", (1, 2), placement_table="4.1"),
                _registration(K70, "515-516", "{FL1231, FL1232, FL1233, FL1234}", (3,),
                              courses=("FL1231", "FL1232", "FL1233", "FL1234")),
            ),
        },
    },
    {
        "decision": "10828/QĐ-ĐHBK",
        "applies_from_cohort": 71,
        "applies_to_cohort": None,
        "source_file": K71,
        **_evidence(K71, "467-467", "Yêu cầu trình độ tiếng Anh theo học kỳ và chuẩn ngoại ngữ đầu ra khi xét tốt nghiệp"),
        # K71 Bảng 2.1 has only a four-skill TOEIC column. The signed PDF
        # resolves cells whose text is shifted or dropped in the extraction.
        "conversion_table": (
            _conversion(K71, "1.1", "341-344", "60÷80 60÷80 50÷60 30÷40",
                        skills=((60, 80), (60, 80), (50, 60), (30, 40))),
            _conversion(K71, "1.2", "342-349", "85÷110 70÷80 50÷60",
                        skills=((85, 105), (85, 110), (70, 80), (50, 60))),
            _conversion(K71, "2.1", "351-352", "110÷165 115÷170 90 70÷80",
                        skills=((110, 165), (115, 170), (90, 90), (70, 80))),
            _conversion(K71, "2.2", "354-355", "170÷215 175÷215 100 90÷100",
                        skills=((170, 215), (175, 215), (100, 100), (90, 100))),
            _conversion(K71, "2.3", "357-358", "220÷270 220÷270 110 110",
                        skills=((220, 270), (220, 270), (110, 110), (110, 110))),
            _conversion(K71, "3.1", "360-361", "275÷330 275÷330 120÷130 120÷130",
                        skills=((275, 330), (275, 330), (120, 130), (120, 130))),
            _conversion(K71, "3.2", "361-367", "335÷395 335÷380",
                        skills=((335, 395), (335, 380), (140, 150), (140, 140))),
            _conversion(K71, "4", "362-369", "400÷485 385÷450",
                        skills=((400, 485), (385, 450), (160, 170), (150, 170))),
            _conversion(K71, "5", "363-374", "490÷495 455÷495",
                        skills=((490, 495), (455, 495), (180, 200), (180, 200))),
            _conversion(K71, "6", "399-400", "Bậc 6", note="Bảng 2.1 không có mức TOEIC cho bậc này."),
        ),
        "graduation": {
            "standard": _graduation(K71, "477-481", "3 trở lên theo Bảng 2.1, Phụ lục II", 3),
            "talent": _graduation(K71, "483-488", "Bậc 4 trở lên theo Bảng 2.1 - Phụ lục II", 4,
                                  "Đồng thời phải đạt chuẩn ngoại ngữ CTĐT kỹ sư, thạc sĩ tài năng STEM do Bộ GD&ĐT ban hành."),
            "elitech": _graduation(K71, "552-564", "Có chứng chỉ tiếng Anh được quy đổi tương đương từ Bậc 4 trở lên", 4),
        },
        "registration_by_semester": {
            "standard": (
                _registration(K71, "470-471", "Được xếp lớp học theo quy định tại Bảng 3.1", (1, 2), placement_table="3.1"),
                _registration(K71, "472-474", "đăng ký học song hành học phần FL1133", (3,), courses=("FL1133",)),
                _registration(K71, "474-476", "đăng ký học song hành học phần FL1134", (4,), courses=("FL1134",)),
                _registration(K71, "476-478", "đăng ký học song hành học phần FL1135", (5,), courses=("FL1135",)),
            ),
            "elitech": (
                _registration(K71, "557-558", "Được xếp lớp học theo quy định tại Bảng 4.1", (1, 2), placement_table="4.1"),
                _registration(K71, "560-561", "{FL1231, FL1232, FL1233, FL1234}", (3,),
                              courses=("FL1231", "FL1232", "FL1233", "FL1234")),
            ),
        },
    },
)

STANDARD_PROGRAMS = frozenset({"BF1", "BF2", "ED2", "EE1", "EE2", "ET1", "ET2",
                               "EV1", "EV2", "ME1", "MS1"})
ENGLISH_ELITECH_PROGRAMS = frozenset({"BF-E19"})
OTHER_PROGRAMS = frozenset({"FL1", "FL2", "FL3", "FL4", "TE-EP", "EE-EP"})


def cohort_from_profile(profile):
    return cohort_from_class_name(str(profile.get("info", {}).get("class_name") or ""))


def rule_for(cohort):
    if cohort is None:
        return None
    return next((rule for rule in ENGLISH_RULES if cohort >= rule["applies_from_cohort"]
                 and (rule["applies_to_cohort"] is None or cohort <= rule["applies_to_cohort"])), None)


def program_track(profile):
    info = profile.get("info", {})
    program = str(info.get("program_code") or info.get("program_id") or "").strip().upper()
    name = fold(info.get("program_name") or "")
    if program in OTHER_PROGRAMS or any(term in name for term in ("troy", "pfiev", "viet phap", "ngon ngu")):
        return "unknown"
    if "tai nang" in name:
        cohort = cohort_from_profile(profile)
        return "talent" if "tich hop" in name or (cohort is not None and cohort <= 70) else "unknown"
    if program in ENGLISH_ELITECH_PROGRAMS:
        return "elitech"
    if program in STANDARD_PROGRAMS:
        return "standard"
    return "unknown"


def _by_test_date(records):
    return sorted(records, key=lambda row: row.get("test_date") or "", reverse=True)


def latest_score(records):
    dated = [row for row in records if row.get("test_date")]
    if dated:
        return max(dated, key=lambda row: row["test_date"])
    return records[0] if len(records) == 1 else None


def estimate_level(record, rule):
    if not record or not rule:
        return None
    kind = fold(record.get("certificate_type") or "")
    if not re.search(r"\btoeic\b", kind) or any(term in kind for term in ("home edition", "at home")):
        return None
    scores = [record.get(skill) for skill in ("listening", "reading", "speaking", "writing")]

    def valid(score):
        return type(score) in (int, float) and isfinite(score)

    rows = rule["conversion_table"]
    if "placement" in kind and all(valid(score) for score in scores[:2]) and scores[2:] == [None, None]:
        total = sum(scores[:2])
        return next((row["level"] for row in rows if row["placement"]
                     and row["placement"][0] <= total <= row["placement"][1]), None)
    if "placement" in kind or not all(valid(score) for score in scores):
        return None
    levels = [
        next((row["level"] for row in rows if row["skills"]
              and row["skills"][idx][0] <= score <= row["skills"][idx][1]), None)
        for idx, score in enumerate(scores)
    ]
    return min(levels, key=float) if all(levels) else None


def english_standard(profile, sections):
    cohort = cohort_from_profile(profile)
    track = program_track(profile)
    rule = rule_for(cohort)
    history = _by_test_date(sections.get("english", {}).get("records", []))
    latest = latest_score(history)
    estimated_level = estimate_level(latest, rule)
    status = sections.get("certificates", {}).get("requirements", {}).get("240")
    if status not in {"completed", "incomplete"}:
        status = "unverified"
    required = None
    if rule and track in rule["graduation"]:
        required = {
            "graduation": rule["graduation"][track],
            "registration_by_semester": rule["registration_by_semester"].get(
                "standard" if track == "talent" else track, ()),
        }
    notes = []
    if rule:
        notes.append("Bảng quy đổi QĐ 10828 áp dụng cho chứng chỉ cấp kể từ ngày quyết định có hiệu lực. "
                     "Với K70 trở về trước, lấy mức cao hơn giữa hai quy định nếu kết quả khác nhau.")
        if latest and "placement" in fold(latest.get("certificate_type") or ""):
            notes.append("TOEIC Placement chỉ dùng để xếp lớp và xét miễn học, không dùng để xét chuẩn đầu ra.")
        if estimated_level:
            notes.append("Bậc hiển thị là ước tính theo bảng của khóa. CTT cung cấp ngày thi; ngày cấp "
                         "và hiệu lực của chứng chỉ cần được đối chiếu khi xét chính thức.")
    return {
        "cohort": cohort, "track": track, "ctt_status": status, "latest": latest,
        "estimated_level": estimated_level, "rule": rule, "required": required,
        "history": history, "notes": notes, "has_data": bool(history or status != "unverified"),
    }
