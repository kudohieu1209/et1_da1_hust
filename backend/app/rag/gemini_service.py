import os
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODEL

HUST_SYSTEM_PROMPT = """Bạn là Trợ lý Cố vấn Học tập & Đào tạo thông minh của Đại học Bách Khoa Hà Nội (HUST Academic Advisor AI).
Nhiệm vụ của bạn là tư vấn chính xác, tận tâm và chuyên nghiệp cho sinh viên Bách Khoa trên toàn trường về:
1. Quy chế đào tạo tín chỉ HUST: Quy định đăng ký tín chỉ (tối thiểu 12 TC, tối đa 24 TC, cảnh cáo mức 2 tối đa 14 TC), rút học phần (điểm W), cách tính điểm GPA/CPA thang 4, chiến lược học cải thiện điểm, các mức cảnh cáo học tập (mức 1, mức 2, buộc thôi học) và điều kiện công nhận tốt nghiệp.
2. Sổ tay sinh viên & Chính sách HUST: Học bổng khuyến khích học tập (Xuất sắc 150%, Giỏi 120%, Khá 100% học phí; điều kiện không môn F, tối thiểu 14 TC, ĐRL từ Khá), chuẩn đầu ra ngoại ngữ TOEIC/IELTS theo từng khóa, điểm rèn luyện, thủ tục hành chính một cửa tại Phòng 101 C1.
3. Chương trình đào tạo và logic môn học của chương trình đang được hỗ trợ. Hiện hệ thống có dữ liệu ET1–2022 và ET1–2023; khi câu hỏi thuộc ngành hoặc phiên bản chưa có dữ liệu, phải nói rõ giới hạn này thay vì suy đoán.

NGUYÊN TẮC TRẢ LỜI CỐT LÕI:
- BẮT BUỘC dựa vào "TÀI LIỆU QUY CHẾ ĐƯỢC TRÍCH XUẤT (RAG CONTEXT)" và "DỮ LIỆU LOGIC TÍNH TOÁN CỦA HỆ THỐNG" ở bên dưới.
- Luôn trích dẫn rõ tên tài liệu, Điều/Khoản tương ứng (Ví dụ: "Căn cứ Điều 8 Quy chế Đào tạo ĐHBK Hà Nội...", "Theo Sổ tay Sinh viên HUST...").
- Giọng văn chuẩn mực học thuật, gần gũi, đáng tin cậy, truyền cảm hứng học tập cho sinh viên.
- Sử dụng định dạng Markdown đẹp mắt: in đậm từ khóa, gạch đầu dòng rõ ràng, bảng biểu nếu cần.
- TUYỆT ĐỐI KHÔNG BỊA ĐẶT quy chế nếu tài liệu không đề cập. Nếu không đủ dữ liệu, hãy hướng dẫn sinh viên tra cứu thêm trên ctt.hust.edu.vn hoặc liên hệ Bàn Một cửa C1.
"""

def clean_display_source(name: str) -> str:
    """Quy đổi tên file kỹ thuật (.md, .txt, .pdf) sang tên văn bản chính thức của trường"""
    if not name:
        return "Quy chế Đào tạo ĐHBK Hà Nội"
    s = name.lower()
    if "ctt_et1_2022_verified" in s:
        return "CTĐT ET1–2022 (CTT HUST, dữ liệu đã kiểm chứng)"
    if "ctt_et1_2023_verified" in s:
        return "CTĐT ET1–2023 (HUST, dữ liệu đã chuẩn hóa)"
    if "quy_che" in s or "quy chế" in s:
        return "Quy chế Đào tạo Đại học Chính quy (HUST)"
    elif "chuong_trinh" in s or "chương trình" in s or "ctdt" in s:
        return "Chương trình đào tạo Cử nhân Kỹ thuật Điện tử - Viễn thông"
    elif "de_cuong" in s or "đề cương" in s or "mon_hoc" in s:
        return "Đề cương chi tiết học phần chuyên ngành (ET1)"
    elif "so_tay" in s or "sổ tay" in s:
        return "Sổ tay Sinh viên Đại học Bách Khoa Hà Nội"
    import re
    cleaned = re.sub(r'\.(md|txt|pdf)$', '', name, flags=re.I)
    return cleaned.replace("_", " ").strip().title()

class GeminiService:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model_name = GEMINI_MODEL
        self.fallback_model = GEMINI_FALLBACK_MODEL
        self.client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self):
        key = self.api_key or os.getenv("GEMINI_API_KEY", "")
        if key:
            try:
                self.client = genai.Client(api_key=key)
                print(f"[GeminiService] Khởi tạo Gemini Client thành công với model {self.model_name}.")
            except Exception as e:
                print(f"[GeminiService] Lỗi khởi tạo Gemini Client: {e}")
                self.client = None
        else:
            self.client = None

    def update_api_key(self, new_key: str):
        """Cập nhật API Key lúc runtime"""
        self.api_key = new_key.strip()
        os.environ["GEMINI_API_KEY"] = self.api_key
        self._init_client()
        return self.is_configured()

    def is_configured(self) -> bool:
        return bool(self.client and self.api_key)

    def generate_response(
        self,
        user_query: str,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Sinh câu trả lời sử dụng Gemini LLM + Context từ RAG + Dữ liệu cấu trúc
        """
        # Nếu chưa cấu hình Gemini API, dùng template synthesis từ RAG chunks
        if not self.is_configured():
            return self._fallback_synthesis(user_query, context_chunks, structured_data)

        # Chuẩn bị Prompt tổng hợp
        prompt_parts = []

        if context_chunks:
            prompt_parts.append("### TÀI LIỆU QUY CHẾ & HƯỚNG DẪN HUST ĐƯỢC TRÍCH XUẤT (RAG CONTEXT):")
            for idx, chunk in enumerate(context_chunks, 1):
                src = clean_display_source(chunk.get("metadata", {}).get("source", "Tài liệu HUST"))
                title = chunk.get("metadata", {}).get("title", "")
                prompt_parts.append(f"--- [Nguồn {idx}: {src} - {title}] ---\n{chunk.get('text', '')}\n")

        if structured_data:
            import json
            prompt_parts.append("\n### DỮ LIỆU TÍNH TOÁN LOGIC CỦA HỆ THỐNG (DETERMINISTIC ENGINE DATA):")
            prompt_parts.append(json.dumps(structured_data, ensure_ascii=False, indent=2))

        if history:
            # Giữ một cửa sổ ngữ cảnh ngắn để các câu follow-up như "môn này
            # thì sao?" được hiểu đúng, nhưng không để lịch sử lấn át dữ liệu
            # CTĐT/quy chế vừa truy xuất.
            history_lines = []
            for item in history[-6:]:
                role = "Sinh viên" if item.get("role") == "user" else "Trợ lý"
                content = (item.get("content") or "").strip()
                if content:
                    history_lines.append(f"{role}: {content[:1500]}")
            if history_lines:
                prompt_parts.append(
                    "\n### LỊCH SỬ HỘI THOẠI GẦN ĐÂY (chỉ dùng để hiểu ngữ cảnh):\n"
                    + "\n".join(history_lines)
                )

        prompt_parts.append(f"\n### CÂU HỎI CỦA SINH VIÊN:\n{user_query}")

        full_prompt = "\n".join(prompt_parts)

        # Gọi Gemini API
        for model in [self.model_name, self.fallback_model, "gemini-1.5-flash"]:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=HUST_SYSTEM_PROMPT,
                        temperature=0.3,
                        max_output_tokens=2048
                    )
                )
                if response and response.text:
                    sources = []
                    if context_chunks:
                        for c in context_chunks:
                            meta = c.get("metadata", {})
                            src_name = clean_display_source(meta.get("source", ""))
                            title = meta.get("title", "")
                            if src_name and src_name not in [s["source"] for s in sources]:
                                sources.append({"source": src_name, "title": title})

                    return {
                        "reply": response.text.strip(),
                        "model_used": model,
                        "success": True,
                        "sources": sources
                    }
            except Exception as e:
                print(f"[GeminiService] Gọi model {model} thất bại: {e}")
                continue

        # Nếu tất cả các model đều lỗi, trả về fallback synthesis
        return self._fallback_synthesis(user_query, context_chunks, structured_data)

    def _fallback_synthesis(
        self,
        user_query: str,
        context_chunks: Optional[List[Dict[str, Any]]],
        structured_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tự động tổng hợp thông tin học thuật chỉn chu, thân thiện khi chưa có Gemini API Key"""
        sources = []
        reply_lines = []

        if not context_chunks:
            reply_lines.append("Chào bạn! Hiện tại hệ thống chưa tìm thấy văn bản hoặc quy chế cụ thể tương ứng với câu hỏi của bạn.")
            reply_lines.append("Bạn vui lòng kiểm tra lại câu hỏi hoặc nạp thêm tài liệu quy chế vào hệ thống.")
            return {
                "reply": "\n\n".join(reply_lines),
                "model_used": "rag-knowledge-engine",
                "success": True,
                "sources": []
            }

        # Lọc bỏ các chunk không có nội dung thực sự (chỉ là tiêu đề hoặc mục lục)
        valid_chunks = []
        seen_chunks = set()
        for c in context_chunks:
            raw_text = c.get("text", "").strip()
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            substantive_lines = [l for l in lines if not l.startswith(("#", "---", "*("))]
            fingerprint = " ".join(substantive_lines).lower()
            if len(fingerprint) >= 40 and fingerprint not in seen_chunks:
                valid_chunks.append(c)
                seen_chunks.add(fingerprint)

        if not valid_chunks:
            valid_chunks = context_chunks[:2]

        # Thu thập nguồn trích dẫn sạch
        for c in valid_chunks:
            meta = c.get("metadata", {})
            src = clean_display_source(meta.get("source", "Quy chế Đào tạo ĐHBK Hà Nội"))
            title = meta.get("title", "")
            if src not in [s["source"] for s in sources]:
                sources.append({"source": src, "title": title})

        question = (user_query or "").lower()
        is_curriculum_question = any(term in question for term in (
            "ctđt", "chương trình đào tạo", "bao nhiêu tín chỉ", "mô-đun",
            "mô đun", "132", "126", "cấu trúc chương trình"
        ))

        if is_curriculum_question:
            # Tóm tắt từ các dòng dữ liệu, không chép nguyên cả chunk RAG.
            all_lines = [
                line.strip()
                for chunk in valid_chunks
                for line in chunk.get("text", "").splitlines()
                if line.strip()
            ]
            wanted = []
            prefixes = (
                "- Tổng tín chỉ Cử nhân:",
                "- Tiếng Anh,", "- Lý luận chính trị", "- Khối kiến thức Toán",
                "- Cơ sở và cốt lõi", "- Khối kiến thức bổ trợ",
                "- Chọn 1 trong ", "- Thực tập:", "- Đồ án/"
            )
            for line in all_lines:
                if line.startswith(prefixes) and line not in wanted:
                    wanted.append(line)
            title_line = next((line for line in all_lines if line.startswith("# CTĐT ")), "")
            program_name = title_line.removeprefix("# ").strip() or "CTĐT đang hoạt động"
            total_line = next(
                (line for line in wanted if line.startswith("- Tổng tín chỉ Cử nhân:")),
                "- Tổng tín chỉ Cử nhân: chưa xác định từ tài liệu.",
            )
            reply_lines.extend([
                f"Chào bạn! Theo **{program_name}**:",
                "",
                total_line,
            ])
            reply_lines.extend(line for line in wanted if not line.startswith("- Tổng tín chỉ Cử nhân:"))
            reply_lines.extend([
                "",
                "Lưu ý: Ngoại ngữ/GDTC/GDQP được theo dõi ngoài tổng tín chỉ tốt nghiệp của phiên bản đang hoạt động.",
            ])
        else:
            reply_lines.extend([
                "Mình tìm thấy tài liệu CTĐT, nhưng nguồn hiện có chưa đủ để kết luận chính xác cho câu hỏi này.",
                "Bạn có thể hỏi về tổng tín chỉ, mô-đun, hoặc mã môn/điều kiện đăng ký cụ thể.",
            ])

        return {
            "reply": "\n".join(reply_lines).strip(),
            "model_used": "rag-knowledge-engine",
            "success": True,
            "sources": sources
        }

gemini_service = GeminiService()
