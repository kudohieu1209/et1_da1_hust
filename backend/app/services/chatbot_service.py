import re
import os
import unicodedata
from typing import Dict, List, Any, Optional
from app.services.data_loader import data_loader
from app.services.student_service import student_service
from app.engine.rule_engine import rule_engine
from app.engine.graph_engine import graph_engine
from app.engine.recommender import course_recommender
from app.core.config import GEMINI_API_KEY, OPENAI_API_KEY
from app.rag.rag_engine import rag_engine
from app.rag.gemini_service import gemini_service
from app.services.conversation_context import previous_focus, resolve_followup

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

# Câu xã giao: không cần tra tài liệu, chỉ cần đáp lại tự nhiên. Thứ tự quan
# trọng: "chúc ngủ ngon" phải rơi vào goodnight trước wish.
SMALL_TALK_PATTERNS = [
    ("goodnight", r"ngủ(\s+\w+){0,2}\s+ngon|good\s*night|(?<!\w)gn(?!\w)|đi\s+ngủ"),
    ("thanks", r"cảm\s+ơn|cám\s+ơn|thank|(?<!\w)(tks|thx)(?!\w)"),
    ("bye", r"tạm\s+biệt|(?<!\w)(bye|bai)(?!\w)|hẹn\s+gặp\s+lại"),
    ("wish", r"(?<!\w)chúc(?!\w)"),
    ("howareyou", r"(khỏe|khoẻ)\s+không|dạo\s+này\s+(thế\s+nào|sao)"),
    ("feeling", r"(?<!\w)(buồn|mệt|chán|stress|căng\s+thẳng|áp\s+lực|lo\s+lắng|cô\s+đơn|nản)(?!\w)"),
    ("compliment", r"(giỏi|hay|tuyệt|xịn|đỉnh|thông\s+minh)\s+(quá|thế|vậy|ghê)|tuyệt\s+vời|good\s+job"),
    ("ack", r"^(ok|oke|okay|okela|uk|ừ|ừm|vâng|dạ|được\s+rồi|(ha)+|(hi)+|(he)+|k+)$"),
]
# Cảm ơn/chúc/tạm biệt vẫn là xã giao dù nhắc tới chuyện học ("chúc mình qua
# đồ án"); các nhóm còn lại chỉ tính khi câu không có nội dung học vụ.
STRONG_SMALL_TALK = {"goodnight", "thanks", "bye", "wish", "ack"}
# Câu hỏi hoặc lời nhờ kèm theo ("cảm ơn, vậy học phí bao nhiêu?") thì phải trả lời nội dung.
QUESTION_OR_REQUEST = re.compile(
    r"\?|(?<!\w)(gì|sao|bao\s+nhiêu|nào|không|chưa|giúp|cho\s+mình|cho\s+em|gợi\s+ý|kiểm\s+tra|xem|tra|hỏi)(?!\w)"
)
ACADEMIC_KEYWORDS = [
    "điều kiện", "tiên quyết", "song hành", "học trước", "đăng ký", "đăng kí",
    "học phần", "môn học", "tín chỉ", "quy chế", "quy định",
    "cảnh báo", "cảnh cáo", "buộc thôi học", "học bổng", "học phí",
    "tốt nghiệp", "đồ án", "thực tập", "cpa", "gpa", "tiến độ",
    "tích lũy", "bảng điểm", "trượt", "tạch", "nếu rớt", "học lại",
    "kỳ tới", "kỳ sau", "định hướng", "chuyên sâu", "đề cương", "ngành",
]
# Dấu hiệu câu hỏi có thể nằm trong tài liệu trường, dùng khi không gọi được LLM.
HUST_TOPIC_KEYWORDS = ACADEMIC_KEYWORDS + [
    "học", "môn", "điểm", "thi", "lịch", "học kỳ", "kỳ học", "lớp", "trường", "hust",
    "bách khoa", "sinh viên", "giảng viên", "viện", "khoa", "ký túc", "kí túc",
    "ktx", "miễn giảm", "chương trình", "ctđt", "ngoại ngữ", "tiếng anh", "bảo lưu",
]

SMALL_TALK_REPLIES = {
    "goodnight": "Chúc bạn ngủ thật ngon nhé! 🌙 Nghỉ ngơi đủ giấc thì mai học mới hiệu quả. Khi cần xem tiến độ hay chọn môn, cứ quay lại tìm mình.",
    "thanks": "Không có gì đâu! 😊 Cần kiểm tra điều kiện môn, xem tiến độ hay tra quy chế thì bạn cứ hỏi mình nhé.",
    "bye": "Tạm biệt bạn! 👋 Chúc bạn học tốt, hẹn gặp lại.",
    "wish": "Chúc bạn học tập thật tốt, thi đâu qua đó và giữ CPA thật đẹp nhé! 😊 Cần gì cứ nhắn mình.",
    "howareyou": "Mình vẫn ổn và luôn sẵn sàng hỗ trợ bạn! 😊 Hôm nay bạn muốn xem tiến độ học tập, kiểm tra điều kiện môn hay gợi ý môn kỳ tới?",
    "feeling": "Nghe có vẻ bạn đang hơi mệt. Học ở Bách Khoa áp lực là chuyện thường, bạn nhớ nghỉ ngơi một chút và chia sẻ với bạn bè, người thân hoặc cố vấn học tập nhé. Nếu đang lo về điểm hay tiến độ, mình có thể cùng bạn xem bảng điểm và lên kế hoạch cho kỳ tới.",
    "compliment": "Cảm ơn bạn đã khen! 😄 Có gì cần tra cứu thêm thì bạn cứ hỏi mình nhé.",
    "ack": "Ok bạn! Cần gì thêm cứ nhắn mình nhé.",
}
OFF_TOPIC_REPLY = (
    "Câu này nằm ngoài phạm vi tài liệu mình đang có nên mình chưa trả lời được. 🙏\n\n"
    "Mình chuyên hỗ trợ sinh viên Bách Khoa về:\n"
    "- **Điều kiện đăng ký môn** (ví dụ: *Điều kiện học ET3300?*)\n"
    "- **Gợi ý môn kỳ tới** theo định hướng chuyên ngành\n"
    "- **Tiến độ học tập, CPA** và các môn còn thiếu\n"
    "- **Quy chế đào tạo, học phí, học bổng** theo văn bản của trường"
)
SMALL_TALK_SUGGESTIONS = [
    "Xem tiến độ học tập",
    "Gợi ý môn học kỳ tới",
    "Điều kiện nhận Đồ án tốt nghiệp",
]


def _contains_keyword(text: str, keywords: List[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", text) for kw in keywords)


def detect_small_talk(text: str, detected_codes: Optional[List[str]] = None) -> Optional[str]:
    """Trả về loại câu xã giao (goodnight, thanks, ...) hoặc None nếu cần trả lời nội dung."""
    if detected_codes:
        return None
    lowered = unicodedata.normalize("NFC", text or "").strip().lower()
    if not lowered:
        return None
    cleaned = " ".join(re.sub(r"[\.,!~:;\-_]+", " ", lowered).split())
    has_academic = _contains_keyword(lowered, ACADEMIC_KEYWORDS)
    asks_something = bool(QUESTION_OR_REQUEST.search(lowered))
    for category, pattern in SMALL_TALK_PATTERNS:
        if not re.search(pattern, cleaned):
            continue
        if category in STRONG_SMALL_TALK:
            if not asks_something:
                return category
        elif not has_academic:
            return category
    return None


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
            if self._has_any(msg_lower, [alias]):
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

    @staticmethod
    def _has_any(text: str, keywords: List[str]) -> bool:
        """Khớp từ khóa theo ranh giới từ.

        So khớp chuỗi con làm "hướng" khớp "hướng dẫn" và "ic" khớp "logic",
        khiến câu hỏi bị định tuyến sai Agent.
        """
        return any(
            re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text)
            for keyword in keywords
        )

    @staticmethod
    def _is_greeting_or_intro(text: str, detected_codes: Optional[List[str]] = None) -> bool:
        """Nhận diện các câu chào hỏi, hỏi thông tin/danh tính trợ lý, hoặc yêu cầu giới thiệu bản thân.
        
        Không bắt các câu có chứa mã môn học hoặc câu hỏi học thuật có nội dung thực sự.
        """
        if detected_codes:
            return False

        msg_clean = unicodedata.normalize("NFC", text or "").strip().lower()
        if not msg_clean:
            return False

        # Các từ khóa nội dung học thuật/quy chế thực sự -> không phải câu chào thuần túy
        substantive_keywords = [
            "điều kiện", "tiên quyết", "song hành", "học trước", "đăng ký",
            "học phần", "môn học", "tín chỉ", "quy chế", "quy định",
            "cảnh báo", "cảnh cáo", "buộc thôi học", "học bổng", "học phí",
            "tốt nghiệp", "đồ án", "thực tập", "cpa", "gpa", "tiến độ",
            "tích lũy", "bảng điểm", "trượt", "tạch", "nếu rớt", "học lại",
            "kỳ tới", "kỳ sau", "định hướng", "chuyên sâu", "đề cương", "ngành"
        ]
        if any(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", msg_clean) for kw in substantive_keywords):
            return False

        # Chuẩn hóa khoảng trắng và dấu câu
        cleaned = re.sub(r"[\.,!~:;\-_]+", " ", msg_clean)
        cleaned = " ".join(cleaned.split())

        # 1. Chào hỏi đơn thuần (kèm hậu tố thân mật: nha, nhé, ơi, ạ, ...)
        # vd: "chào", "chào bạn", "xin chào", "xin chào!", "chào bot", "hello", "hi bạn", "alo"
        greeting_pattern = r"^(xin\s+)?chào(\s+(bạn|cậu|bot|ad|admin|mọi người|trợ lý|cố vấn))?(\s+(ạ|ơi|nha|nhé|nhá|nè|ha|nhỉ))?$"
        hello_pattern = r"^(hello|hi|hey|alo|halo)(\s+(bạn|cậu|bot|ad|admin))?(\s+(ạ|ơi|nha|nhé|nhá|nè|ha|nhỉ))?$"
        if re.fullmatch(greeting_pattern, cleaned) or re.fullmatch(hello_pattern, cleaned):
            return True

        # 2. Câu hỏi danh tính trợ lý (bạn là ai, bạn là ?, bạn là gì, tên bạn là gì)
        # vd: "bạn là ?", "bạn là ai", "bạn là ai thế?", "bạn là ai vậy", "bạn tên là gì"
        identity_pattern = r"^((xin\s+)?chào\s+(bạn\s+|bot\s+|ad\s+)?)?((bạn|cậu|mày)\s+là\s*(ai|\?|gì)|(bạn|cậu)\s+tên\s+(là\s+)?gì|tên\s+(của\s+)?(bạn|cậu)\s+là\s+gì)(\s+(thế|vậy|đấy|nhỉ|đó|ạ|hả|nhở))?\??$"
        if re.match(identity_pattern, msg_clean) or re.match(identity_pattern, cleaned):
            return True

        # 3. Yêu cầu giới thiệu bản thân
        # vd: "giới thiệu bản thân đi", "giới thiệu về bản thân", "bạn giới thiệu về bản thân bạn đi", "tự giới thiệu"
        intro_pattern = r"(giới\s+thiệu\s+(chút\s+)?(về\s+)?(bản\s+thân|bạn|mình)|tự\s+giới\s+thiệu)"
        if re.search(intro_pattern, cleaned):
            return True

        # 4. Câu hỏi năng lực / menu trợ giúp
        # vd: "bạn có thể làm gì", "bạn giúp được gì", "bạn làm được gì", "menu", "help"
        capability_pattern = r"^((xin\s+)?chào\s+(bạn\s+|bot\s+)?)?(bạn|bot)\s+((có\s+thể\s+)?(làm|giúp|hỗ\s+trợ)(\s+được)?\s+(gì|những\s+gì)|chức\s+năng\s+gì)"
        if re.search(capability_pattern, cleaned):
            return True

        if cleaned in {"menu", "help", "trợ giúp", "hướng dẫn", "bắt đầu"}:
            return True

        return False

    def process_message(self, message: str, history: Optional[List[Dict[str, Any]]] = None, *, preferences=None) -> Dict[str, Any]:
        history = (history or [])[-12:]
        message = unicodedata.normalize("NFC", message or "").strip()
        focus = previous_focus(history, self._detect_courses, self._is_repeat_request)
        if self._is_repeat_request(message):
            message = focus.get("topic_query") or self._last_substantive_user_message(history, message) or message
        effective, clarification = resolve_followup(message, focus, self._detect_courses)
        if clarification:
            return {
                "reply": clarification, "intent": "CONTEXT_CLARIFICATION", "sources": [],
                "suggested_actions": focus.get("course_codes", []), "model_used": "rule-based",
                "data_context": {"conversation_context": focus},
            }
        # Structured context is for reference resolution only; LLM history stays text.
        text_history = [{"role": item["role"], "content": item["content"]} for item in history
                        if item.get("role") in {"user", "assistant"}]
        result = self._process_message(effective, text_history, preferences=preferences)
        if result.get("intent") not in {"SMALL_TALK", "GENERAL_GREETING", "OUT_OF_SCOPE"}:
            focus = {"course_codes": self._detect_courses(effective), "topic_query": effective[:1200]}
        context = dict(result.get("data_context") or {})
        context["conversation_context"] = focus
        result["data_context"] = context
        return result

    def _process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None, *, preferences=None) -> Dict[str, Any]:
        """
        Xử lý tin nhắn của sinh viên theo kiến trúc Hybrid Agent:
        1. Phân loại Intent (Simulation, Recommendation, Degree Audit, Course Eligibility)
        2. Nếu là câu hỏi quy chế, chính sách, thủ tục, học bổng -> Kích hoạt RAG Engine + Gemini LLM
        3. Tổng hợp câu trả lời tự nhiên, chính xác kèm trích dẫn văn bản quy chế HUST.
        """
        # Một số câu follow-up chỉ có ý nghĩa khi đọc cùng lịch sử, ví dụ
        # "trả lời lại đi bạn". Dùng câu hỏi gần nhất có nội dung để chạy lại
        # đúng Agent (course check/RAG/audit), thay vì trả lời fallback chung.
        # Bộ gõ "Unicode tổ hợp" gửi chữ dạng NFD; đưa về NFC để khớp từ khóa.
        effective_message = unicodedata.normalize("NFC", message or "").strip()
        if self._is_repeat_request(effective_message):
            previous_question = self._last_substantive_user_message(history, effective_message)
            if previous_question:
                effective_message = previous_question

        msg_lower = effective_message.lower()
        detected_codes = self._detect_courses(effective_message)

        # 0. Câu xã giao (chúc ngủ ngon, cảm ơn, tạm biệt...) không đi tra tài liệu.
        small_talk = detect_small_talk(effective_message, detected_codes)
        if small_talk:
            return self._handle_small_talk(effective_message, small_talk, history)

        # 1. Xử lý câu hỏi mô phỏng trượt môn (What-if simulation)
        if self._has_any(msg_lower, ["trượt", "tạch", "nếu rớt", "học lại", "không qua", "ảnh hưởng"]):
            if detected_codes:
                return self._handle_simulation(detected_codes[0])

        # 2. Câu nói có "kỳ tới" nhưng nêu rõ môn và hỏi
        # "cần gì/học trước" là kiểm tra điều kiện, không phải gợi ý môn.
        course_condition_terms = [
            "học được không", "đăng ký được", "cùng lúc",
            "đồng thời", "tiên quyết", "song hành", "cần môn", "cần học",
            "học trước", "cần những gì", "cần những môn", "môn gì trước", "cần gì",
        ]
        if detected_codes and (self._has_any(msg_lower, course_condition_terms) or re.search(
            r"(?:học|đăng k[ýí]).*\b(?:được|chưa)\b", msg_lower
        )):
            return self._handle_course_check(detected_codes, effective_message)

        if re.search(r"(?:điểm|ký hiệu)\s+[abcdfrwi](?:\+)?\b", msg_lower) or re.search(
            r"(?:xếp|trình độ|sinh viên).*(?:năm thứ|năm [1-6])", msg_lower
        ):
            return self._handle_rag_query(effective_message, history)
        # Personal progress takes precedence over generic credit-policy keywords.
        if self._has_any(msg_lower, ["còn thiếu", "bảng điểm"]) or (
            "tiến độ" in msg_lower and "chậm tiến độ" not in msg_lower
        ):
            return self._handle_audit()
        if re.search(r"chuyển.*(?:chương trình|ngành)", msg_lower):
            return self._handle_rag_query(effective_message, history)

        # 3. Xử lý câu hỏi đề xuất môn học / gợi ý kỳ tới / định hướng chuyên sâu
        if self._has_any(msg_lower, ["nên học", "nên đăng ký", "gợi ý", "tư vấn môn", "kỳ tới", "kỳ sau", "kỳ 7", "kỳ 8", "chọn môn", "định hướng", "theo hướng", "chọn hướng", "hướng nào", "hướng chuyên"]):
            target_track = None
            if self._has_any(msg_lower, ["vi mạch", "bán dẫn", "ic", "vlsi"]):
                target_track = "IC_DESIGN"
            elif self._has_any(msg_lower, ["nhúng", "embedded", "iot"]):
                target_track = "EMBEDDED_IOT"
            elif self._has_any(msg_lower, ["viễn thông", "telecom", "5g", "truyền thông"]):
                target_track = "TELECOM_NETWORK"
            elif self._has_any(msg_lower, ["y sinh", "biomedical"]):
                target_track = "BIOMEDICAL"

            memory = preferences or {}
            remembered_track = memory.get("target_track") if target_track is None else None
            explicit_credits = re.search(r"\b([1-9]\d?)\s*(?:tín chỉ|tc)\b", msg_lower)
            max_credits = int(explicit_credits[1]) if explicit_credits else memory.get("max_credits")
            # Explicit chat choices take priority over the saved default.
            return self._handle_recommendation(
                target_track or remembered_track, max_credits=max_credits,
                memory_used={key: memory[key] for key in ("max_credits", "target_cpa")
                             if memory.get(key) is not None and not (key == "max_credits" and explicit_credits)}
                            | ({"target_track": remembered_track} if remembered_track else {}),
            )

        # 4. Ưu tiên RAG nếu câu hỏi hỏi về Đề cương chi tiết môn học / Nội dung môn / Phần mềm, công cụ, tool thực hành
        is_syllabus_query = self._has_any(msg_lower, [
            "nội dung", "học gì", "học những gì", "đề cương", "phần mềm", 
            "công cụ", "tool", "thực hành gì", "kiến thức", "giáo trình", 
            "tài liệu", "dạy gì", "mô tả môn"
        ])

        # 5. Ưu tiên RAG nếu câu hỏi hỏi về văn bản quy chế / quy định / tín chỉ / cảnh cáo / tốt nghiệp / học cải thiện
        is_explicit_regulation = self._has_any(msg_lower, [
            "quy chế", "quy định", "tối thiểu", "tối đa", "bao nhiêu tín chỉ", "giới hạn tín chỉ",
            "học bổng", "cảnh cáo", "cảnh báo học tập", "buộc thôi học", "rút học phần", "điểm w", "thủ tục", 
            "chuẩn ngoại ngữ", "chuẩn tiếng anh", "toeic", "ielts", "vstep", "học phí", 
            "bảo lưu", "chính sách", "nhận đồ án", "làm đồ án tốt nghiệp", "xét tốt nghiệp", 
            "điều kiện tốt nghiệp", "cải thiện điểm", "học lại", "thang điểm", "điều 1", "điều 2",
            "điều 3", "điều 4", "điều 5", "điều 6", "điều 7", "điều 8", "điều 9", "điều 10"
        ])
        if is_syllabus_query or is_explicit_regulation:
            return self._handle_rag_query(effective_message, history, detected_codes=detected_codes if is_syllabus_query else None)

        # 6. Xử lý câu hỏi về tiến độ học tập cá nhân / Degree Audit / CPA / Bằng Khá / Cải thiện điểm
        if self._has_any(msg_lower, ["tiến độ", "còn thiếu", "tích lũy", "cpa", "gpa", "bảng điểm", "bằng khá", "bằng giỏi", "nợ môn", "kéo điểm", "cải thiện"]):
            return self._handle_audit()

        # 7. Xử lý kiểm tra môn học cụ thể (điều kiện đăng ký, học được không, môn X cần gì)
        is_course_question = self._has_any(msg_lower, ["điều kiện", "học được không", "được không", "đăng ký được", "cùng lúc", "đồng thời", "tiên quyết", "song hành", "môn"])
        if detected_codes and (is_course_question or len(detected_codes) >= 2 or re.search(r'\b[A-Z]{2,3}\s*\d{4}[A-Z]?\b', message.upper())):
            return self._handle_course_check(detected_codes, effective_message)

        # 8. Câu hỏi chào hỏi thông thường / giới thiệu bản thân
        if self._is_greeting_or_intro(effective_message, detected_codes):
            return self._handle_general_query(message)

        # 9. RAG (Retrieval-Augmented Generation) cho các câu hỏi tổng quát về CTĐT và Quy chế
        result = self._handle_rag_query(effective_message, history)
        # Không có LLM thì RAG chỉ chép lại các đoạn tài liệu gần nhất; với câu
        # không dính tới chuyện học/trường, các đoạn đó vô nghĩa với người hỏi.
        if result.get("model_used") == "rag-knowledge-engine" and not _contains_keyword(msg_lower, HUST_TOPIC_KEYWORDS):
            return {
                "reply": OFF_TOPIC_REPLY,
                "intent": "OUT_OF_SCOPE",
                "suggested_actions": SMALL_TALK_SUGGESTIONS,
                "sources": [],
                "model_used": "rule-based",
            }
        return result

    def _handle_small_talk(
        self, message: str, category: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        reply = gemini_service.small_talk(message, history)
        return {
            "reply": reply or SMALL_TALK_REPLIES[category],
            "intent": "SMALL_TALK",
            "suggested_actions": SMALL_TALK_SUGGESTIONS,
            "sources": [],
            "model_used": gemini_service.model_name if reply else "rule-based",
        }

    def _handle_rag_query(self, message: str, history: Optional[List[Dict[str, str]]] = None, detected_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Truy vấn kiến thức CTĐT và Quy chế đào tạo HUST qua RAG + Gemini LLM.
        Nếu sinh viên hỏi về một môn cụ thể, kết hợp thêm kiểm tra điều kiện cá nhân.
        """
        try:
            rag_res = rag_engine.query(message, k=4, history=history)
        except Exception as e:
            # Lỗi kho vector (vd. chỉ mục ChromaDB hỏng) không được làm sập
            # /api/chat: phản hồi 500 thiếu header CORS khiến trình duyệt báo
            # nhầm là mất kết nối backend.
            print(f"[ChatbotService] RAG không khả dụng: {e!r}")
            return self._rag_unavailable_reply()
        reply = rag_res["reply"]

        # Nếu hỏi về môn học cụ thể, đối chiếu thêm với tiến độ sinh viên
        if detected_codes:
            try:
                code = detected_codes[0]
                student_profile = data_loader.get_student_profile()
                check_res = rule_engine.check_eligibility(code, student_profile)
                c_name = check_res.get("course_name", "")
                profile_id = student_profile.get("info", {}).get("student_id")
                header = f"Đối chiếu hồ sơ cá nhân (MSSV {profile_id})" if profile_id else "Đối chiếu hồ sơ cá nhân"

                if check_res["status"] == "ALREADY_PASSED":
                    elig_note = f"\n\n---\n👤 **{header}:**\n⭐ Bạn đã hoàn thành môn học này ({code} - {c_name})."
                elif check_res["is_eligible"]:
                    elig_note = f"\n\n---\n👤 **{header}:**\n✅ **Bạn đã ĐỦ ĐIỀU KIỆN** để đăng ký học môn `{code}` ({c_name}) trong kỳ tới!"
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
                    elig_note = f"\n\n---\n👤 **{header}:**\n⚠️ **Hiện tại bạn CHƯA ĐỦ ĐIỀU KIỆN** đăng ký môn `{code}`: {reason_text}."
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
    def _rag_unavailable_reply() -> Dict[str, Any]:
        return {
            "reply": (
                "⚠️ Kho tài liệu quy chế đang gặp sự cố nên mình chưa tra cứu được câu này. "
                "Bạn thử lại sau ít phút, hoặc xem trực tiếp trên ctt.hust.edu.vn.\n\n"
                "Các chức năng dựa trên CTĐT vẫn dùng bình thường: kiểm tra điều kiện học phần, "
                "gợi ý môn kỳ tới và rà soát tiến độ học tập."
            ),
            "intent": "RAG_HUST_KNOWLEDGE",
            "suggested_actions": [
                "Xem tiến độ học tập",
                "Gợi ý môn học kỳ tới",
                "Điều kiện môn Mạng máy tính",
            ],
            "sources": [],
            "model_used": "rag-unavailable",
            "data_context": {"retrieved_chunks": [], "context_chunks_count": 0},
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
            if is_concurrent_question:
                # Kết luận suy ra từ kết quả Rule Engine của chính hồ sơ này,
                # không viết cứng cho từng cặp môn.
                blocked = [r["course_code"] for r in results if not r["is_eligible"]]
                if blocked:
                    reply_lines.append(
                        f"👉 **Kết luận: CHƯA ĐĂNG KÝ ĐƯỢC cùng kỳ** — đang bị chặn: {', '.join(blocked)}.\n"
                    )
                else:
                    reply_lines.append(
                        "👉 **Kết luận: ĐƯỢC PHÉP đăng ký các môn này trong cùng một học kỳ** "
                        "(đã tính cả điều kiện song hành giữa các môn).\n"
                    )
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

    def _handle_recommendation(self, target_track: Optional[str], *, max_credits=None, memory_used=None) -> Dict[str, Any]:
        rec = course_recommender.recommend(target_track=target_track, max_credits=max_credits)
        if memory_used:
            rec["memory_used"] = memory_used
        courses = rec["recommended_courses"]
        
        reply_lines = [
            f"📋 **Đề xuất kế hoạch chọn môn học kỳ tới ({rec['track_name']}):**\n",
            f"💡 *{rec['advice_note']}*\n",
            f"**Tổng số tín chỉ đề xuất:** `{rec['total_credits_suggested']}` / `{rec['max_allowed_credits']}` TC\n"
        ]

        if memory_used:
            reply_lines.append("🧠 Đã dùng mục tiêu bạn lưu trong **Cài đặt → Ghi nhớ học tập**. Hạn mức vẫn được kiểm tra theo hồ sơ hiện tại.\n")
            if memory_used.get("target_cpa") is not None:
                reply_lines.append(f"🎯 Mục tiêu CPA đã lưu: **{memory_used['target_cpa']:.2f}/4.0**. Danh sách này chưa mô phỏng điểm để đạt mục tiêu CPA.\n")

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
            f"- **Tình trạng học tập:** {audit['warning_description']} ({'Hạn mức kế hoạch tạm thời' if audit['credit_limit'].get('is_provisional') else 'Giới hạn đăng ký'}: {audit['credit_limit']['max']} TC/kỳ chính)",
            f"  - *Căn cứ:* {audit.get('warning_basis', '')}",
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
            reply_lines.append(f"- Điểm CPA hiện tại là **{audit['cpa']}** (loại {classification.get('rank', 'Trung bình')}). Trong {kha_advice.get('remaining_credits', 0):g} TC còn lại:")
            if not kha_advice.get("remaining_credits"):
                reply_lines.append("  - Đã đủ khối lượng tín chỉ; cần xem phương án **học cải thiện điểm** để nâng CPA. Không còn tín chỉ mới để phân bổ GPA mục tiêu.")
            elif kha_advice.get("is_achievable"):
                reply_lines.append(f"  - Nếu chỉ học môn mới: Cần đạt GPA trung bình ~**{kha_advice.get('gpa_needed_remaining')}** cho phần còn lại.")
            else:
                reply_lines.append("  - Chỉ học các môn mới thì **không đủ** để đạt CPA 2.50 (cần GPA > 4.0).")
            reply_lines.append("  - Có thể xem thêm phương án học cải thiện các môn điểm thấp; số môn và mức điểm cần đạt phải tính theo bảng điểm cụ thể.")

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
