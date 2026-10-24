import os
import hashlib
import json
import re
from pathlib import Path
from typing import List, Dict, Any

from app.core.config import DOCUMENTS_DIR

UNVERIFIED_MARKER = "RAG_STATUS: UNVERIFIED"

class DocumentChunk:
    def __init__(self, text: str, metadata: Dict[str, Any]):
        self.text = text
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "metadata": self.metadata
        }

def format_document_display_name(filename: str) -> str:
    """Quy đổi tên file kỹ thuật (.md, .txt, .pdf) sang tên văn bản chính thức của trường"""
    name_map = {
        "ctt_et1_2022_verified.md": "CTĐT ET1–2022 (CTT HUST, dữ liệu đã kiểm chứng)",
        "ctt_et1_2023_verified.md": "CTĐT ET1–2023 (HUST, dữ liệu đã chuẩn hóa)",
        "quy_che_dao_tao_2025_verified.md": "Quy chế đào tạo HUST 2025 (QĐ 5445/QĐ-ĐHBK)",
        "so_tay_sinh_vien_2026_verified.md": "Sổ tay sinh viên HUST 2026",
        "hoc_phi_2025_2026_verified.md": "Quyết định học phí HUST 2025-2026",
        "quy_che_dao_tao_dai_hoc_hust.md": "Quy chế Đào tạo Đại học Chính quy (HUST)",
        "chuong_trinh_dao_tao_et1.md": "Chương trình đào tạo Cử nhân Kỹ thuật Điện tử - Viễn thông",
        "de_cuong_chi_tiet_mon_hoc_et1.md": "Đề cương chi tiết học phần chuyên ngành (ET1)",
        "so_tay_sinh_vien_2026.pdf": "Sổ tay Sinh viên Đại học Bách Khoa Hà Nội",
    }
    if filename in name_map:
        return name_map[filename]
    stem = Path(filename).stem
    return stem.replace("_", " ").strip().title()

class DocumentLoader:
    def __init__(self, doc_dir: Path = DOCUMENTS_DIR):
        self.doc_dir = Path(doc_dir)
        self.doc_dir.mkdir(parents=True, exist_ok=True)

    def get_document_files(self) -> List[Path]:
        """Return only documents explicitly allowed into the trusted RAG index."""
        files = []
        for ext in ["*.md", "*.txt", "*.pdf"]:
            for path in self.doc_dir.glob(ext):
                if self._document_metadata(path).get("rag_status", "").upper() != "VERIFIED":
                    continue
                files.append(path)
        return sorted(files)

    def _document_metadata(self, path: Path) -> Dict[str, str]:
        if path.suffix.lower() in {".md", ".txt"}:
            text = self._read_text_file(path)
            if UNVERIFIED_MARKER in text[:500]:
                return {}
            return self._parse_front_matter(text)[0]
        # PDFs require an explicit approval sidecar; a filename is not approval.
        try:
            metadata = json.loads(path.with_suffix(path.suffix + ".metadata.json").read_text(encoding="utf-8"))
            return metadata if isinstance(metadata, dict) else {}
        except (OSError, ValueError):
            return {}

    def calculate_file_hash(self, file_path: Path) -> str:
        """Tính MD5 hash của file để nhận diện thay đổi"""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _read_text_file(self, file_path: Path) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _parse_front_matter(text: str) -> tuple[Dict[str, str], str]:
        """Read the small YAML-like metadata block used by verified documents."""
        metadata: Dict[str, str] = {}
        text = text.lstrip("\ufeff")
        if not text.startswith("---\n"):
            return metadata, text
        end = text.find("\n---\n", 4)
        if end == -1:
            return metadata, text
        for line in text[4:end].splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
        return metadata, text[end + 5:].lstrip()

    def _read_pdf_file(self, file_path: Path) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- [Trang {i+1}] ---\n" + text)
            return "\n\n".join(pages_text)
        except Exception as e:
            print(f"[DocumentLoader] Lỗi đọc file PDF {file_path.name}: {e}")
            return ""

    def _split_text_into_chunks(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """
        Phân đoạn văn bản (Smart Chunking):
        Ưu tiên ngắt theo đoạn văn (\n\n) hoặc dấu chấm câu, bảo toàn trọn vẹn ý nghĩa của Điều khoản.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue

            p_len = len(p_clean)
            if current_length + p_len > chunk_size and current_chunk:
                # Đóng chunk hiện tại
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)
                
                # Giữ lại một phần đoạn trước cho overlap
                if len(current_chunk) > 1 and len(current_chunk[-1]) <= overlap:
                    current_chunk = [current_chunk[-1], p_clean]
                    current_length = len(current_chunk[0]) + p_len
                else:
                    current_chunk = [p_clean]
                    current_length = p_len
            else:
                current_chunk.append(p_clean)
                current_length += p_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        # Nếu có đoạn nào quá lớn vượt quá 1.5 chunk_size, chia nhỏ tiếp theo dòng
        refined_chunks = []
        for c in chunks:
            if len(c) > chunk_size * 1.5:
                sub_lines = c.split("\n")
                sub_c = []
                sub_len = 0
                for line in sub_lines:
                    if sub_len + len(line) > chunk_size and sub_c:
                        refined_chunks.append("\n".join(sub_c))
                        sub_c = [line]
                        sub_len = len(line)
                    else:
                        sub_c.append(line)
                        sub_len += len(line)
                if sub_c:
                    refined_chunks.append("\n".join(sub_c))
            else:
                refined_chunks.append(c)

        return [rc.strip() for rc in refined_chunks if rc.strip()]

    def _structured_chunks(self, text: str, document_type: str = "") -> List[tuple[str, Dict[str, Any]]]:
        """Keep page, article and section context when splitting legal clauses/tables."""
        result = []
        buffer = []
        page = 0
        article = ""
        section = ""
        clause = ""
        education_level = "general"
        awaiting_chapter_title = False
        in_contents = False

        def flush():
            if not buffer:
                return
            content = "\n".join(buffer).strip()
            context = "\n".join(dict.fromkeys(value for value in (article, section, clause) if value))
            for part in self._split_text_into_chunks(content, chunk_size=1400, overlap=150):
                if section == "Nguồn và truy vết" or part.startswith((
                    "> Trạng thái:", "Bản trích xuất", "Trích các trang PDF", "Dữ liệu danh tính",
                )):
                    continue
                if len(re.sub(r"\s+", " ", part).strip()) < 20:
                    continue
                result.append((f"{context}\n\n{part}".strip(), {
                    "page": page, "article": article, "section": section, "clause": clause,
                    "education_level": education_level,
                }))
            buffer.clear()

        for line in text.splitlines():
            stripped = line.strip()
            page_match = re.match(r"(?:## Trang PDF |--- \[Trang )(\d+)", stripped)
            if page_match:
                flush()
                page = int(page_match.group(1))
                section = ""
                if document_type and document_type != "academic_regulation":
                    article = ""
                    clause = ""
                in_contents = False
                continue
            if stripped == "MỤC LỤC":
                flush()
                in_contents = True
            if in_contents or re.search(r"\.{4,}", stripped):
                continue
            if re.fullmatch(r"CHƯƠNG\s+[IVXLCDM]+", stripped):
                flush()
                article = section = clause = ""
                awaiting_chapter_title = True
                continue
            if awaiting_chapter_title and stripped:
                education_level = next((level for title, level in (
                    ("ĐÀO TẠO ĐẠI HỌC", "undergraduate"), ("ĐÀO TẠO KỸ SƯ", "engineer"),
                    ("ĐÀO TẠO THẠC SĨ", "master"), ("ĐÀO TẠO TIẾN SĨ", "doctorate"),
                ) if title in stripped.upper()), "general")
                awaiting_chapter_title = False
                continue
            article_match = re.match(r"Điều\s+\d+[.:]\s+.+", stripped)
            if article_match and not re.search(r"\.{3,}", stripped):
                flush()
                article = stripped
                section = ""
                clause = ""
                continue
            if re.match(r"#{1,6}\s", stripped):
                flush()
                section = stripped.lstrip("# ")
                clause = ""
                continue
            # Do not mix independent clauses or module alternatives in a chunk.
            if re.match(r"\d+[.)]\s+", stripped):
                flush()
                clause = stripped
            elif re.match(r"[a-zđ]\)\s+", stripped):
                # A point inherits the full lead-in of its numbered clause,
                # including PDF line wraps (e.g. "giảm một mức" on the next line).
                if buffer and re.match(r"\d+[.)]\s+", buffer[0].strip()):
                    clause = "\n".join(buffer).strip()
                flush()
            elif re.match(r"- Mô-đun \d+:", stripped):
                flush()
            buffer.append(line)
        flush()
        return result

    def load_all_chunks(self) -> List[DocumentChunk]:
        """Nạp toàn bộ tài liệu và chia thành các chunks kèm metadata sạch sẽ"""
        files = self.get_document_files()
        all_chunks = []

        for file_path in files:
            ext = file_path.suffix.lower()
            if ext in [".md", ".txt"]:
                raw_text = self._read_text_file(file_path)
            elif ext == ".pdf":
                raw_text = self._read_pdf_file(file_path)
            else:
                continue

            if not raw_text.strip():
                continue

            file_hash = self.calculate_file_hash(file_path)
            _, content_text = self._parse_front_matter(raw_text)
            document_metadata = self._document_metadata(file_path)
            chunks = self._structured_chunks(content_text, document_metadata.get("document_type", ""))

            # Lấy tiêu đề từ dòng đầu tiên nếu là markdown (# Tiêu đề)
            first_line = content_text.strip().split("\n")[0].replace("#", "").strip()
            title = first_line if first_line else format_document_display_name(file_path.name)

            valid_idx = 0
            for chunk_text, location in chunks:
                cleaned_chunk = chunk_text.strip()
                # Bỏ qua các chunk chỉ chứa tiêu đề thuần túy hoặc quá ngắn (< 60 ký tự) không mang thông tin
                lines = [line.strip() for line in cleaned_chunk.splitlines() if line.strip()]
                non_header_lines = [l for l in lines if not l.startswith(("#", "---", "*("))]
                if not non_header_lines or len(" ".join(non_header_lines)) < 40:
                    continue

                chunk_title = location.get("article") or location.get("section") or title
                if ext == ".pdf":
                    match_page = re.search(r'---\s*\[Trang\s*(\d+)\]\s*---', cleaned_chunk)
                    if match_page:
                        chunk_title = f"{format_document_display_name(file_path.name)} (Trang {match_page.group(1)})"
                    else:
                        chunk_title = format_document_display_name(file_path.name)

                chunk = DocumentChunk(
                    text=cleaned_chunk,
                    metadata={
                        "source": format_document_display_name(file_path.name),
                        "file_name": file_path.name,
                        "title": chunk_title,
                        "chunk_index": valid_idx,
                        "total_chunks": len(chunks),
                        "file_hash": file_hash,
                        "file_type": ext.replace(".", ""),
                        "document_type": document_metadata.get("document_type", "general"),
                        "effective_period": document_metadata.get("effective_period", ""),
                        "source_url": document_metadata.get("source_url", ""),
                        **location,
                    }
                )
                all_chunks.append(chunk)
                valid_idx += 1

        print(f"[DocumentLoader] Đã tải {len(files)} tài liệu và tạo {len(all_chunks)} chunks thông tin chất lượng.")
        return all_chunks

document_loader = DocumentLoader()
