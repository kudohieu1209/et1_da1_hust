import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_vietnamese(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để tìm kiếm không dấu / có dấu tương thích."""
    text = unicodedata.normalize("NFD", text.lower())
    text = re.sub(r"[\u0300-\u036f]", "", text)
    return text.replace("đ", "d").strip()


class CampusService:
    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            # e:\Vibe\et1_da1_hust\data\campus_locations.json
            repo_root = Path(__file__).resolve().parents[3]
            data_path = repo_root / "data" / "campus_locations.json"
        self.data_path = data_path
        self._locations: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8-sig") as f:
                self._locations = json.load(f)
        else:
            self._locations = []

    def get_all_locations(self) -> List[Dict[str, Any]]:
        return self._locations

    def find_location(self, query: str) -> Optional[Dict[str, Any]]:
        """Tìm địa điểm theo tên hoặc mã tòa nhà (D3, D5, C1, B1, Tạ Quang Bửu...)."""
        if not query or not query.strip():
            return None

        q_norm = _normalize_vietnamese(query)
        q_raw = query.strip().upper()

        # 1. Tìm khớp mã chính xác trước (VD "D3", "C1", "B1")
        for loc in self._locations:
            code = (loc.get("code") or "").upper().strip()
            if code and code == q_raw:
                return loc

        # 2. Tìm tên khớp chính xác hoặc bắt đầu bằng
        for loc in self._locations:
            name_norm = _normalize_vietnamese(loc.get("name", ""))
            if q_norm == name_norm:
                return loc

        # 3. Tìm tên chứa chuỗi tìm kiếm hoặc chuỗi tìm kiếm chứa tên tòa nhà
        matches = []
        for loc in self._locations:
            name_norm = _normalize_vietnamese(loc.get("name", ""))
            code = (loc.get("code") or "").upper().strip()
            if not name_norm:
                continue
            if (
                q_norm in name_norm
                or (len(name_norm) >= 3 and name_norm in q_norm)
                or (code and code in q_raw)
                or ("ta quang buu" in q_norm and code == "TVTQB")
                or ("thu vien" in q_norm and code == "TVTQB")
            ):
                matches.append(loc)

        return matches[0] if matches else None

    def format_direction_reply(self, loc: Dict[str, Any]) -> str:
        """Định dạng câu trả lời chỉ đường thân thiện kèm link Google Maps."""
        name = loc.get("name", "")
        code = loc.get("code")
        code_str = f" (Mã tòa: {code})" if code and code != name else ""
        maps_url = loc.get("google_maps_url", "")
        center = loc.get("center", {})
        lat = center.get("lat")
        lng = center.get("lng")

        reply = (
            f"📍 **Vị trí trong khuôn viên Bách Khoa:** **{name}**{code_str}\n"
            f"- **Tọa độ GPS:** `{lat}, {lng}`\n"
            f"- **Chỉ đường Google Maps:** [Bấm vào đây để mở chỉ đường]({maps_url})\n\n"
            f"*Gợi ý:* Bạn có thể mở link trên để xem định vị trực tiếp và dẫn đường từ vị trí hiện tại của bạn đến {name}."
        )
        return reply


campus_service = CampusService()
