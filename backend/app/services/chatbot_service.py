import re
import os
from typing import Dict, List, Any, Optional
from app.services.data_loader import data_loader
from app.services.student_service import student_service
from app.engine.rule_engine import rule_engine
from app.engine.graph_engine import graph_engine
from app.engine.recommender import course_recommender
from app.core.config import GEMINI_API_KEY, OPENAI_API_KEY
from app.rag.rag_engine import rag_engine

# Bảng từ đồng nghĩa / tên gọi phổ biến của sinh viên Bách Khoa
COURSE_ALIASES = {
    # Chuyên ngành & Mô-đun
    "mạng máy tính": "ET4230",
    "mạng mt": "ET4230",
    "cơ sở truyền số liệu": "ET4070",
    "truyền số liệu": "ET4070",
    "kỹ thuật vi xử lý": "ET3300",
    "vi xử lý": "ET3300",
    "vxl": "ET3300",
    "điện tử số": "ET3220",
    "dts": "ET3220",
    "điện tử tương tự 1": "ET3230",
    "điện tử tương tự i": "ET3230",
    "điện tử tương tự 2": "ET3241",
    "điện tử tương tự ii": "ET3241",
    "cấu kiện điện tử": "ET2040",
    "cấu kiện": "ET2040",
    "lý thuyết mạch": "ET2050",
    "tín hiệu và hệ thống": "ET2060",
    "trường điện từ": "ET3210",
    "xử lý tín hiệu số": "ET4020",
    "xlths": "ET4020",
    "dsp": "ET4020",
    "hệ điều hành": "ET4291",
    "hdh": "ET4291",
    "hệ thống nhúng": "ET4361",
    "ht nhúng": "ET4361",
    "thiết kế vi mạch": "ET4340",
    "thiết kế vlsi": "ET4340",
    "vlsi": "ET4340",
    "ic tương tự": "ET4033",
    "thiết kế ic tương tự": "ET4033",
    "kiểm chứng vi mạch": "ET4356",
    "cơ sở công nghệ vi điện tử": "ET4358",
    "vi điện tử": "ET4358",
    "thông tin vô tuyến": "ET3180",
    "anten và truyền sóng": "ET3280",
    "anten": "ET3280",
    "thực tập kỹ thuật": "ET3270",
    "ttkt": "ET3270",
    "đồ án 1": "ET3290",
    "đồ án 2": "ET4010",
    "đồ án thiết kế 1": "ET3290",
    "đồ án thiết kế 2": "ET4010",
    "đồ án thiết kế i": "ET3290",
    "đồ án thiết kế ii": "ET4010",
    "đatk 1": "ET3290",
    "đatk 2": "ET4010",
    "đồ án tốt nghiệp": "ET4900",
    "đatn": "ET4900",
    "tốt nghiệp cử nhân": "ET4900",
    "lý thuyết mật mã": "ET3310",
    "mật mã": "ET3310",
    "hệ thống viễn thông": "ET4250",
    "tư duy công nghệ": "ET3262",
    "quản trị học đại cương": "EM1010",
    "quản trị học": "EM1010",
    "văn hóa kinh doanh": "EM1180",
    "tinh thần khởi nghiệp": "EM1180",
    "kỹ thuật phần mềm ứng dụng": "ET3260",
    "phần mềm ứng dụng": "ET3260",
    "kỹ thuật lập trình": "IT3040",
    "tin học đại cương": "IT1110",
    "pháp luật đại cương": "EM1170",
    "pldc": "EM1170",
    "giải tích 1": "MI1111",
    "giải tích i": "MI1111",
    "giải tích 2": "MI1121",
    "giải tích ii": "MI1121",
    "giải tích 3": "MI1131",
    "giải tích iii": "MI1131",
    "đại số": "MI1141",
    "xác suất thống kê": "MI2020",
    "phương pháp tính": "MI2010",
    "vật lý 1": "PH1111",
    "vật lý 2": "PH1122",
    "vật lý điện tử": "PH3330",
    "triết học": "SSH1111",
    "kinh tế chính trị": "SSH1121",
    "chủ nghĩa xã hội": "SSH1131",
    "lịch sử đảng": "SSH1141",
    "tư tưởng hồ chí minh": "SSH1151",
    "cơ sở điện sinh học": "ET4100",
    "điện sinh học": "ET4100",
    "cảm biến y sinh": "ET4110",
    "cảm biến và kt đo lường y sinh": "ET4110",
    "thiết bị điện tử y sinh 1": "ET4120",
    "giải phẫu và sinh lý học": "ET4450",
    "giải phẫu": "ET4450",
    "mạch xử lý tín hiệu y sinh": "ET4471",
    "công nghệ chẩn đoán hình ảnh 1": "ET4480",
    "chẩn đoán hình ảnh": "ET4480",
    "truyền số liệu và chuyển tiếp điện văn": "ET4130",
    "định vị và dẫn đường điện tử": "ET4140"
}

class ChatbotService:
    def __init__(self):
        self.gemini_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.openai_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")

    @staticmethod
    def _is_repeat_request(message: str) -> bool:
        """Nhận diện các câu ngắn yêu cầu trả lời lại câu hỏi trước.

        Các câu như ``trả lời lại đi bạn`` không chứa mã/tên học phần nên nếu
        đưa thẳng vào bộ phân loại sẽ bị chuyển sang RAG tổng quát. Khi có
        lịch sử hội thoại, ta dùng câu hỏi trước làm truy vấn thực tế.
        """
        normalized = re.sub(r"\s+", " ", (message or "").strip().lower())
        if not normalized:
            return False
        repeat_phrases = (
            "trả lời lại",
            "nói lại",
            "giải thích lại",
            "nhắc lại",
            "trình bày lại",
            "tóm tắt lại",
            "làm rõ lại",
            "mình chưa hiểu",
            "mình chưa rõ",
            "chưa hiểu",
            "chưa rõ",
        )
        return any(phrase in normalized for phrase in repeat_phrases)

    @classmethod
    def _last_substantive_user_message(
        cls,
        history: Optional[List[Dict[str, str]]],
        current_message: str,
    ) -> Optional[str]:
        """Lấy câu hỏi có nội dung gần nhất, bỏ qua các yêu cầu lặp lại."""
        if not history:
            return None
        current_normalized = re.sub(r"\s+", " ", (current_message or "").strip().lower())
        for item in reversed(history):
            if item.get("role") != "user":
                continue
            candidate = (item.get("content") or "").strip()
            candidate_normalized = re.sub(r"\s+", " ", candidate.lower())
            if not candidate_normalized or candidate_normalized == current_normalized:
                continue
            if cls._is_repeat_request(candidate):
                continue
            return candidate
        return None

    def _detect_courses(self, message: str) -> List[str]:
        """
        Nhận diện thông minh tất cả các môn học được nhắc tới:
        1. Mã học phần chuẩn (ET4230, ET 4230, MI1111,...)
        2. Tên tiếng Việt thông dụng & Từ viết tắt sinh viên
        3. Tên đầy đủ từ danh mục 117 môn CTĐT
        """
        msg_clean = message.upper()
        # Chuẩn hóa khoảng trắng trong mã học phần (ET 4230 -> ET4230)
        msg_clean = re.sub(r'\b([A-Z]{2,3})\s+(\d{4}[A-Z]?)\b', r'\1\2', msg_clean)
        
        detected = []
        # 1. Regex tìm mã HP
        raw_codes = re.findall(r'\b([A-Z]{2,3}\d{4}[A-Z]?)\b', msg_clean)
        for c in raw_codes:
            if c not in detected:
                detected.append(c)

        msg_lower = message.lower()

        # 2. Trường hợp đặc biệt: Đồ án 1 và 2 cùng lúc
        if re.search(r'đồ án\s*(?:thiết kế\s*)?1\s*(?:và|&|,|\+)\s*(?:đồ án\s*)?2', msg_lower) or "đatk 1 và 2" in msg_lower or "đa 1 và 2" in msg_lower:
            if "ET3290" not in detected:
                detected.append("ET3290")
            if "ET4010" not in detected:
                detected.append("ET4010")

        # 3. Tra cứu theo Alias sinh viên
        for alias, code in sorted(COURSE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            if alias in msg_lower:
                if code not in detected:
                    detected.append(code)

        # 4. Tra cứu theo tên môn chuẩn trong hệ thống
        all_courses = data_loader.get_all_courses()
        for c in sorted(all_courses, key=lambda x: len(x['name']), reverse=True):
            c_name = c['name'].strip().lower()
            if len(c_name) >= 5 and c_name in msg_lower:
                if c['code'] not in detected:
                    detected.append(c['code'])

        return detected

    def process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Xử lý tin nhắn của sinh viên theo kiến trúc Hybrid Agent:
        1. Phân loại Intent (Simulation, Recommendation, Degree Audit, Course Eligibility)
        2. Nếu là câu hỏi quy chế, chính sách, thủ tục, học bổng -> Kích hoạt RAG Engine + Gemini LLM
        3. Tổng hợp câu trả lời tự nhiên, chính xác kèm trích dẫn văn bản quy chế HUST.
        """
        # Một số câu follow-up chỉ có ý nghĩa khi đọc cùng lịch sử, ví dụ
        # "trả lời lại đi bạn". Dùng câu hỏi gần nhất có nội dung để chạy lại
        # đúng Agent (course check/RAG/audit), thay vì trả lời fallback chung.
        effective_message = (message or "").strip()
        if self._is_repeat_request(effective_message):
            previous_question = self._last_substantive_user_message(history, effective_message)
            if previous_question:
                effective_message = previous_question

        msg_lower = effective_message.lower()
        detected_codes = self._detect_courses(effective_message)

        # 1. Xử lý câu hỏi mô phỏng trượt môn (What-if simulation)
        if any(k in msg_lower for k in ["trượt", "tạch", "nếu rớt", "học lại", "không qua", "ảnh hưởng"]):
            if detected_codes:
                return self._handle_simulation(detected_codes[0])

        # 2. Xử lý câu hỏi đề xuất môn học / gợi ý kỳ tới / định hướng chuyên sâu
        if any(k in msg_lower for k in ["nên học", "nên đăng ký", "gợi ý", "tư vấn môn", "kỳ tới", "kỳ sau", "kỳ 7", "kỳ 8", "chọn môn", "hướng", "định hướng"]):
            target_track = None
            if any(k in msg_lower for k in ["vi mạch", "bán dẫn", "ic", "vlsi"]):
                target_track = "IC_DESIGN"
            elif any(k in msg_lower for k in ["nhúng", "embedded", "iot"]):
                target_track = "EMBEDDED_IOT"
            elif any(k in msg_lower for k in ["viễn thông", "telecom", "5g", "truyền thông"]):
                target_track = "TELECOM_NETWORK"
            elif any(k in msg_lower for k in ["y sinh", "biomedical"]):
                target_track = "BIOMEDICAL"

            return self._handle_recommendation(target_track)

        # 3. Ưu tiên RAG nếu câu hỏi hỏi về Đề cương chi tiết môn học / Nội dung môn / Phần mềm, công cụ, tool thực hành
        is_syllabus_query = any(k in msg_lower for k in [
            "nội dung", "học gì", "học những gì", "đề cương", "phần mềm", 
            "công cụ", "tool", "thực hành gì", "kiến thức", "giáo trình", 
            "tài liệu", "dạy gì", "làm gì", "mô tả môn"
        ])

        # 4. Ưu tiên RAG nếu câu hỏi hỏi về văn bản quy chế / quy định / tín chỉ / cảnh cáo / tốt nghiệp / học cải thiện
        is_explicit_regulation = any(k in msg_lower for k in [
            "quy chế", "quy định", "tối thiểu", "tối đa", "bao nhiêu tín chỉ", "giới hạn tín chỉ",
            "học bổng", "cảnh cáo", "buộc thôi học", "rút học phần", "điểm w", "thủ tục", 
            "chuẩn ngoại ngữ", "chuẩn tiếng anh", "toeic", "ielts", "vstep", "học phí", 
            "bảo lưu", "chính sách", "nhận đồ án", "làm đồ án tốt nghiệp", "xét tốt nghiệp", 
            "điều kiện tốt nghiệp", "cải thiện điểm", "học lại", "thang điểm", "điều 1", "điều 2",
            "điều 3", "điều 4", "điều 5", "điều 6", "điều 7", "điều 8", "điều 9", "điều 10"
        ])
        if is_syllabus_query or is_explicit_regulation:
            return self._handle_rag_query(effective_message, history, detected_codes=detected_codes if is_syllabus_query else None)

        # 5. Xử lý câu hỏi về tiến độ học tập cá nhân / Degree Audit / CPA / Bằng Khá / Cải thiện điểm
        if any(k in msg_lower for k in ["tiến độ", "còn thiếu", "tích lũy", "cpa", "gpa", "bảng điểm", "bằng khá", "bằng giỏi", "nợ môn", "kéo điểm", "cải thiện"]):
            return self._handle_audit()

        # 6. Xử lý kiểm tra môn học cụ thể (điều kiện đăng ký, học được không, môn X cần gì)
        is_course_question = any(k in msg_lower for k in ["điều kiện", "học được không", "được không", "đăng ký được", "cùng lúc", "đồng thời", "tiên quyết", "song hành", "môn"])
        if detected_codes and (is_course_question or len(detected_codes) >= 2 or re.search(r'\b[A-Z]{2,3}\s*\d{4}[A-Z]?\b', message.upper())):
            return self._handle_course_check(detected_codes, effective_message)

        # 7. Câu hỏi chào hỏi thông thường
        if any(msg_lower.strip() == k for k in ["chào", "chào bạn", "hello", "hi", "alo", "menu", "help", "bạn là ai"]):
            return self._handle_general_query(message)

        # 8. RAG (Retrieval-Augmented Generation) cho các câu hỏi tổng quát về CTĐT và Quy chế
        return self._handle_rag_query(effective_message, history)

    def _handle_rag_query(self, message: str, history: Optional[List[Dict[str, str]]] = None, detected_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Truy vấn kiến thức CTĐT và Quy chế đào tạo HUST qua RAG + Gemini LLM.
        Nếu sinh viên hỏi về một môn cụ thể, kết hợp thêm kiểm tra điều kiện cá nhân.
        """
        rag_res = rag_engine.query(message, k=4, history=history)
        reply = rag_res["reply"]

        # Nếu hỏi về môn học cụ thể, đối chiếu thêm với tiến độ sinh viên
        if detected_codes:
            try:
                code = detected_codes[0]
                student_profile = data_loader.get_student_profile()
                check_res = rule_engine.check_eligibility(code, student_profile)
                c_name = check_res.get("course_name", "")
                
                if check_res["status"] == "ALREADY_PASSED":
                    elig_note = f"\n\n---\n👤 **Đối chiếu hồ sơ cá nhân (MSSV {student_profile.get('info', {}).get('student_id', '20220001')}):**\n⭐ Bạn đã hoàn thành môn học này ({code} - {c_name})."
                elif check_res["is_eligible"]:
                    elig_note = f"\n\n---\n👤 **Đối chiếu hồ sơ cá nhân (MSSV {student_profile.get('info', {}).get('student_id', '20220001')}):**\n✅ **Bạn đã ĐỦ ĐIỀU KIỆN** để đăng ký học môn `{code}` ({c_name}) trong kỳ tới!"
                else:
                    alternatives = check_res.get("missing_alternative_branches", [])
                    if alternatives:
                        options = self._format_alternative_options(alternatives)
                        reason_text = (
                            "chưa thỏa mãn phương án nào; chỉ cần hoàn thành một trong các lựa chọn: "
                            f"{options}. Không cần đáp ứng đồng thời các phương án"
                        )
                    else:
                        reason_text = "; ".join(check_res.get("reasons", []))
                    elig_note = f"\n\n---\n👤 **Đối chiếu hồ sơ cá nhân (MSSV {student_profile.get('info', {}).get('student_id', '20220001')}):**\n⚠️ **Hiện tại bạn CHƯA ĐỦ ĐIỀU KIỆN** đăng ký môn `{code}`: {reason_text}."
                reply += elig_note
            except Exception as e:
                print(f"[ChatbotService] Lỗi đối chiếu điều kiện môn học: {e}")

        suggested = [
            "Giới hạn số tín chỉ đăng ký kỳ chính & hè",
            "Điều kiện nhận Đồ án tốt nghiệp (Điều 9)",
            "Gợi ý chọn môn theo hướng Thiết kế Vi mạch",
            "Làm sao để kéo điểm CPA lên bằng Khá?"
        ]

        return {
            "reply": reply,
            "intent": "RAG_HUST_KNOWLEDGE",
            "suggested_actions": suggested,
            "sources": rag_res.get("sources", []),
            "model_used": rag_res.get("model_used", "rag-local"),
            "data_context": {
                "retrieved_chunks": rag_res.get("retrieved_chunks", []),
                "context_chunks_count": rag_res.get("context_chunks_count", 0)
            }
        }

    @staticmethod
    def _course_module_labels(course: Dict[str, Any]) -> List[str]:
        """Lấy các mô-đun chính thức mà học phần thuộc về.

        Một học phần tự chọn có thể xuất hiện trong nhiều nhóm mô-đun (ví dụ
        ET4230 thuộc Mô đun 1, 2 và 5). Không suy diễn từ chuỗi category đã
        gộp; dùng group_ids của CTĐT đã chuẩn hóa để hiển thị chính xác.
        """
        return [item["name"] for item in data_loader.get_course_modules(course)]

    @staticmethod
    def _format_condition_item(item: Dict[str, Any]) -> str:
        code = item.get("code", "")
        relation = item.get("type", "PRIOR")
        relation_label = {
            "PREREQUISITE": "tiên quyết (phải qua môn)",
            "COREQUISITE": "song hành (có thể học cùng kỳ)",
            "PRIOR": "học trước (đã từng học)",
        }.get(relation, "điều kiện")
        course_label = ChatbotService._format_course_reference(code)
        return f"{course_label} - *{relation_label}*"

    @staticmethod
    def _format_course_reference(code: str, bold: bool = False) -> str:
        """Định dạng mã/tên môn mà không để lọt tên rỗng ra giao diện."""
        course = data_loader.get_course(code) or {}
        name = course.get("name", "")
        code_markup = f"**{code}**" if bold else f"`{code}`"
        if name:
            return f"{code_markup} ({name})"
        # Một số điều kiện CTT tham chiếu học phần ngoài catalog của phiên bản
        # đang hoạt động. Không tự đoán tên và không hiển thị ngoặc rỗng.
        program = data_loader.get_program()
        label = f"CTĐT {program.get('program_code', '')}–{program.get('curriculum_version', '')}".rstrip("–")
        return f"{code_markup} (*chưa có tên trong danh mục {label}*)"

    @staticmethod
    def _format_alternative_options(branches: List[Dict[str, Any]]) -> str:
        options = []
        for idx, branch in enumerate(branches, 1):
            branch_items = []
            for key in ("missing_prerequisites", "missing_prior_courses", "missing_corequisites"):
                for item in branch.get(key, []):
                    branch_items.append(ChatbotService._format_course_reference(item, bold=True))
            options.append(f"Phương án {idx}: " + (" và ".join(branch_items) if branch_items else "đã đạt"))
        return " **hoặc** ".join(options)

    def _handle_course_check(self, codes: List[str], raw_msg: str) -> Dict[str, Any]:
        student_profile = data_loader.get_student_profile()
        results = []
        is_concurrent_question = ("cùng lúc" in raw_msg.lower() or "đồng thời" in raw_msg.lower()) and len(codes) >= 2

        for code in codes:
            concurrent = [c for c in codes if c != code] if is_concurrent_question else None
            res = rule_engine.check_eligibility(code, student_profile, concurrent_codes=concurrent)
            results.append(res)

        reply_lines = []
        # Case đặc biệt: Đồ án 1 và 2 cùng lúc
        if is_concurrent_question and set(codes) == {"ET3290", "ET4010"}:
            reply_lines.append("🎓 **Về việc đăng ký Đồ án thiết kế I (ET3290) và Đồ án thiết kế II (ET4010) cùng lúc:**\n")
            reply_lines.append("👉 **Kết luận: Hoàn toàn ĐƯỢC PHÉP bạn nhé!**\n")
            reply_lines.append("Chi tiết quy định trên hệ thống CTT Bách Khoa:")
            reply_lines.append("- Môn **ET4010 (Đồ án thiết kế II)**: Cột HP điều kiện là **RỖNG** (không có tiên quyết).")
            reply_lines.append("- Môn **ET3290 (Đồ án thiết kế I)**: Chỉ yêu cầu điều kiện song hành `=`: `ET3260=` (học song hành với Kỹ thuật phần mềm ứng dụng).")
            reply_lines.append("- Vì vậy bạn hoàn toàn có thể đăng ký cả 2 đồ án này trong cùng một học kỳ.")
            
            return {
                "reply": "\n".join(reply_lines),
                "intent": "COURSE_ELIGIBILITY_CHECK",
                "suggested_actions": [
                    "Gợi ý môn học kỳ tiếp theo",
                    "Xem tiến độ học tập Degree Audit",
                    "Kiểm tra môn khác"
                ],
                "data_context": {"check_results": results}
            }

        # Kiểm tra chi tiết từng môn
        if len(codes) == 1:
            r = results[0]
            code = r["course_code"]
            student_id = student_profile.get("info", {}).get("student_id", data_loader.current_student_id)
            c_info = data_loader.get_course(code) or {}
            rule = data_loader.get_rule(code) or {}
            raw_cond = rule.get("raw_condition", "")
            c_name = r["course_name"]
            credits = c_info.get("credits", rule.get("credits", 0.0))
            category = c_info.get("category", "Chuyên ngành")
            module_labels = self._course_module_labels(c_info)
            semester = c_info.get("suggested_semester", "Kỳ 7 hoặc 8")

            status_header = "✅ **ĐỦ ĐIỀU KIỆN ĐĂNG KÝ**" if r["is_eligible"] else "❌ **CHƯA ĐỦ ĐIỀU KIỆN (BỊ CHẶN)**"
            if r["status"] == "ALREADY_PASSED":
                status_header = "⭐ **ĐÃ HOÀN THÀNH MÔN HỌC**"

            reply_lines.append(f"🔍 **Thông tin & Điều kiện đăng ký môn {code} - {c_name}:**\n")
            reply_lines.append(f"{status_header}\n")
            reply_lines.append("📋 **Thông tin học phần:**")
            reply_lines.append(f"- **Mã HP:** `{code}` | **Số tín chỉ:** `{credits}` TC")
            if module_labels:
                reply_lines.append(f"- **Mô-đun thuộc CTĐT:** {', '.join(module_labels)}")
                if len(module_labels) > 1:
                    module_count = len(data_loader.get_module_tracks())
                    reply_lines.append(
                        f"- **Cách tính mô-đun:** CTĐT yêu cầu chọn **1 trong {module_count} mô-đun**; "
                        "môn này là học phần dùng chung trong các mô-đun được liệt kê."
                    )
            else:
                reply_lines.append(f"- **Khối kiến thức:** {category}")
            if semester:
                reply_lines.append(f"- **Học kỳ gợi ý trong CTĐT:** Kỳ {semester}")

            reply_lines.append("\n🔒 **Ràng buộc điều kiện trên hệ thống CTT Bách Khoa:**")
            if not raw_cond:
                reply_lines.append("- **Điều kiện CTT:** Không có ràng buộc điều kiện (Môn mở tự do).")
            else:
                reply_lines.append(f"- **Công thức điều kiện trên CTT:** `{raw_cond}`")
                # Diễn giải điều kiện
                condition_branches = rule.get("condition_tree", [])
                if len(condition_branches) > 1:
                    part_descs = []
                    for idx, branch in enumerate(condition_branches, 1):
                        requirements = [self._format_condition_item(item) for item in branch]
                        part_descs.append(
                            f"  + **Phương án {idx}:** " +
                            (" và ".join(requirements) if requirements else "không có ràng buộc")
                        )
                    reply_lines.append(
                        "- **Cách đọc điều kiện:** Dấu `/` nghĩa là **HOẶC**. Bạn chỉ cần đáp ứng "
                        "**một phương án** dưới đây; các môn trong cùng một phương án phải đáp ứng đồng thời:\n"
                        + "\n".join(part_descs)
                    )
                elif condition_branches:
                    requirements = [self._format_condition_item(item) for item in condition_branches[0]]
                    if len(requirements) > 1:
                        reply_lines.append(
                            "- **Ý nghĩa dấu `,` (VÀ):** Cần thỏa mãn đồng thời tất cả các môn:\n"
                            + "\n".join(f"  + {item}" for item in requirements)
                        )
                    elif requirements:
                        reply_lines.append(f"- **Yêu cầu:** {requirements[0]}")
                else:
                    reply_lines.append("- **Yêu cầu:** Không có điều kiện ràng buộc.")

            reply_lines.append(f"\n👤 **Đối chiếu với tiến độ học tập cá nhân (MSSV {student_id}):**")
            if r.get("missing_alternative_branches"):
                # Các phương án đã được giải thích ở trên; tại phần hồ sơ chỉ nêu
                # kết luận một lần để không tạo cảm giác cả hai môn đều bắt buộc.
                for reason in r["reasons"][:2]:
                    reply_lines.append(f"- {reason}")
                reply_lines.append(
                    "- Hiện tại bạn chưa thỏa mãn **bất kỳ phương án nào**; chỉ cần chọn và hoàn thành **một** phương án."
                )
            else:
                for reason in r["reasons"]:
                    reply_lines.append(f"- {reason}")

            if not r["is_eligible"]:
                reply_lines.append("\n💡 **Lời khuyên đăng ký:**")
                alternative_branches = r.get("missing_alternative_branches", [])
                if alternative_branches:
                    common_items = []
                    for item in r.get("missing_prerequisites", []):
                        common_items.append(self._format_course_reference(item, bold=True))
                    for item in r.get("missing_prior_courses", []):
                        common_items.append(self._format_course_reference(item, bold=True))
                    if common_items:
                        reply_lines.append(
                            f"- Mọi phương án đều yêu cầu bạn thỏa mãn: {', '.join(common_items)}."
                        )

                    reply_lines.append(
                        f"- Bạn chưa đạt phương án nào. Chỉ cần hoàn thành **một** lựa chọn: "
                        + self._format_alternative_options(alternative_branches)
                        + ". Không cần đáp ứng đồng thời các phương án còn lại."
                    )
                elif r.get("missing_prior_courses"):
                    prior_codes = r["missing_prior_courses"]
                    prior_names = [self._format_course_reference(c, bold=True) for c in prior_codes]
                    reply_lines.append(f"- Để mở khóa môn {code}, trong kỳ tới bạn nên ưu tiên đăng ký môn học trước: {', '.join(prior_names)}.")
                elif r.get("missing_prerequisites"):
                    prereq_codes = r["missing_prerequisites"]
                    prereq_names = [self._format_course_reference(c, bold=True) for c in prereq_codes]
                    reply_lines.append(f"- Bạn cần hoàn thành đạt điểm môn tiên quyết {', '.join(prereq_names)} trước.")

        else:
            # Nhiều môn cùng lúc
            reply_lines.append(f"🔍 **Kết quả kiểm tra điều kiện học phần cho {len(codes)} môn ({', '.join(codes)}):**\n")
            for r in results:
                status_icon = "✅" if r["is_eligible"] else "❌"
                status_text = "Đủ điều kiện" if r["is_eligible"] else "Đang bị chặn"
                if r["status"] == "ALREADY_PASSED":
                    status_icon = "⭐"
                    status_text = "Đã hoàn thành"

                reply_lines.append(f"### {status_icon} Môn **{r['course_code']}** - {r['course_name']} ({status_text})")
                for reason in r["reasons"]:
                    reply_lines.append(f"- {reason}")
                reply_lines.append("")

        return {
            "reply": "\n".join(reply_lines),
            "intent": "COURSE_ELIGIBILITY_CHECK",
            "suggested_actions": [
                "Gợi ý danh sách môn nên học kỳ tới",
                "Xem tiến độ học tập Degree Audit",
                "Tư vấn môn khác"
            ],
            "data_context": {"check_results": results}
        }

    def _handle_recommendation(self, target_track: Optional[str]) -> Dict[str, Any]:
        rec = course_recommender.recommend(target_track=target_track)
        courses = rec["recommended_courses"]
        
        reply_lines = [
            f"📋 **Đề xuất kế hoạch chọn môn học kỳ tới ({rec['track_name']}):**\n",
            f"💡 *{rec['advice_note']}*\n",
            f"**Tổng số tín chỉ đề xuất:** `{rec['total_credits_suggested']}` / `{rec['max_allowed_credits']}` TC\n"
        ]

        for idx, c in enumerate(courses, 1):
            comp_badge = "[Bắt buộc]" if c["is_compulsory"] else "[Tự chọn]"
            reply_lines.append(f"{idx}. **{c['code']}** - {c['name']} ({c['credits']} TC) {comp_badge}")
            reply_lines.append(f"   - *Lý do:* {c['priority_reason']}")
            reply_lines.append(f"   - *Điều kiện:* {c['prerequisite_summary']}")

        reply_lines.append("\n👉 Bạn có thể đổi định hướng chuyên sâu khác bằng cách nhắn: *'Tư vấn hướng Vi mạch'*, *'Tư vấn hướng Nhúng'*, hoặc *'Tư vấn hướng Viễn thông'*.")

        return {
            "reply": "\n".join(reply_lines),
            "intent": "COURSE_RECOMMENDATION",
            "suggested_actions": [
                "Xem theo hướng Thiết kế Vi mạch",
                "Xem theo hướng Hệ thống nhúng",
                "Xem theo hướng Mạng & Viễn thông",
                "Kiểm tra tiến độ tốt nghiệp"
            ],
            "data_context": rec
        }

    def _handle_audit(self) -> Dict[str, Any]:
        audit = student_service.audit_degree()
        info = audit["student_info"]
        classification = audit.get("academic_classification", {})
        kha_advice = audit.get("target_kha_advice", {})
        
        reply_lines = [
            f"📊 **Báo cáo Tiến độ Học tập (Degree Audit) - {info.get('student_name', 'Sinh viên')} ({info.get('student_id', '')}):**\n",
            f"- **Chương trình:** {info.get('program_name', 'Chương trình đang hoạt động')}",
            f"- **Điểm CPA hiện tại:** `{audit['cpa']:.2f}` / 4.0",
            f"- **Xếp loại học lực hiện tại:** **{classification.get('rank', 'Trung bình')}** ({classification.get('desc', 'Đạt chuẩn tốt nghiệp')})",
            f"- **Tình trạng học tập:** {audit['warning_description']} (Giới hạn đăng ký: {audit['credit_limit']['max']} TC/kỳ)",
            f"- **Tín chỉ tích lũy:** `{audit['total_credits_accumulated']:.1f}` / `{audit['total_credits_required']}` TC (**{audit['completion_percentage']}%** hoàn thành)",
            f"- **Số môn đã qua:** {audit['passed_count']} môn | **Số môn chưa đạt:** {audit['failed_count']} môn\n",
            "📌 **Các môn bắt buộc cốt lõi còn lại cần hoàn thành:**"
        ]

        for c in audit["unlearned_compulsory_courses"][:6]:
            reply_lines.append(f"  - **{c['code']}** - {c['name']} ({c['credits']} TC - Kỳ gợi ý: {c.get('suggested_semester', 'N/A')})")

        if audit["pending_requirements"]:
            reply_lines.append("\n⚠️ **Điều kiện cần hoàn thiện để xét tốt nghiệp:**")
            for req in audit["pending_requirements"]:
                reply_lines.append(f"  - {req}")

        if audit['cpa'] < 2.50 and kha_advice:
            reply_lines.append(f"\n🎯 **Mục tiêu tốt nghiệp bằng KHÁ (CPA ≥ 2.50):**")
            reply_lines.append(f"- Điểm CPA hiện tại là **{audit['cpa']}** (loại Trung bình). Để nâng lên loại Khá, trong {kha_advice.get('remaining_credits', 21)} TC còn lại:")
            reply_lines.append(f"  - Nếu chỉ học môn mới: Cần đạt GPA trung bình ~**{kha_advice.get('gpa_needed_remaining', 3.71)}** (toàn bộ A/B+).")
            reply_lines.append(f"  - **Giải pháp dễ hơn nhiều:** Đăng ký học **cải thiện điểm** 1 - 2 môn điểm D/D+ (Giải tích, Đại số, Vật lý, Điện tử số...) để nâng điểm kéo CPA lên ≥ 2.50!")

        return {
            "reply": "\n".join(reply_lines),
            "intent": "DEGREE_AUDIT",
            "suggested_actions": [
                "Gợi ý môn học kỳ tiếp theo",
                "Kiểm tra môn Mạng máy tính",
                "Kiểm tra Đồ án 1 và 2",
                "Tư vấn định hướng chuyên ngành"
            ],
            "data_context": audit
        }

    def _handle_simulation(self, course_code: str) -> Dict[str, Any]:
        sim = graph_engine.get_impact_analysis(course_code)
        
        reply_lines = [
            f"⚠️ **Phân tích Rủi ro & Tác động nếu không đạt môn {sim['failed_course_code']} ({sim['failed_course_name']}):**\n",
            f"Mức độ ảnh hưởng: **{sim['severity']}**\n",
            sim["analysis"],
            ""
        ]

        if sim["direct_blocked_courses"]:
            reply_lines.append("🚫 **Các môn sẽ bị CHẶN TRỰC TIẾP không thể đăng ký ngay kỳ sau:**")
            for c in sim["direct_blocked_courses"]:
                reply_lines.append(f"  - **{c['code']}** - {c['name']} ({c['credits']} TC)")

        if sim["indirect_blocked_courses"]:
            reply_lines.append("\n⏳ **Các môn bị ảnh hưởng dây chuyền tiếp theo:**")
            for c in sim["indirect_blocked_courses"][:5]:
                reply_lines.append(f"  - **{c['code']}** - {c['name']}")

        return {
            "reply": "\n".join(reply_lines),
            "intent": "IMPACT_SIMULATION",
            "suggested_actions": [
                "Gợi ý lộ trình khắc phục",
                "Kiểm tra môn khác",
                "Xem tiến độ học tập"
            ],
            "data_context": sim
        }

    def _handle_general_query(self, message: str) -> Dict[str, Any]:
        reply = (
            "👋 Chào bạn! Mình là Trợ lý AI tư vấn học tập của Đại học Bách Khoa Hà Nội.\n\n"
            "Mình có thể hỗ trợ bạn:\n"
            "1. **Kiểm tra điều kiện đăng ký:** Nhắn tên hoặc mã môn học bất kỳ (ví dụ: *'điều kiện môn học Mạng máy tính'*, *'Mình học được ET4010 và ET3290 cùng lúc không?'*).\n"
            "2. **Đề xuất chọn môn kỳ tiếp theo:** Nhắn *'Gợi ý môn kỳ tới'* hoặc kèm định hướng (Vi mạch, Nhúng, Viễn thông, Y sinh).\n"
            "3. **Kiểm tra tiến độ tốt nghiệp (Degree Audit):** Nhắn *'Tiến độ học tập'* để xem số tín tích lũy, CPA và các môn còn nợ.\n"
            "\n"
            "Bạn muốn tra cứu nội dung nào trước?"
        )
        return {
            "reply": reply,
            "intent": "GENERAL_GREETING",
            "suggested_actions": [
                "Điều kiện môn học Mạng máy tính",
                "Kiểm tra Đồ án 1 và Đồ án 2",
                "Gợi ý môn học kỳ tới",
                "Xem tiến độ tốt nghiệp"
            ]
        }

# Singleton instance
chatbot_service = ChatbotService()
