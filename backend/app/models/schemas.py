from typing import Annotated, List, Literal, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Ảnh đại diện đã được frontend thu về ~256px; giới hạn này chặn ảnh gốc nhiều
# MB bị lưu vào hồ sơ (và bị gửi lại trong mọi phản hồi audit).
MAX_AVATAR_DATA_URL_LENGTH = 300_000
AVATAR_DATA_URL_PATTERN = r"^(data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+)?$"
AVATAR_GRADIENT_PATTERN = r"^linear-gradient\(135deg, #[0-9a-fA-F]{6}, #[0-9a-fA-F]{6}\)$"


class TranscriptImportRequest(BaseModel):
    """Bảng điểm copy từ CTT. MSSV/tên/lớp lấy từ tài khoản đăng nhập; các
    trường đó nếu client còn gửi kèm sẽ bị bỏ qua (không ghi đè danh tính)."""

    model_config = ConfigDict(extra="ignore")

    raw_text: str = Field(..., min_length=1, max_length=100_000)
    warning_level: Optional[int] = Field(None, ge=0, le=3)
    course_credit_overrides: Dict[str, Annotated[float, Field(ge=0, allow_inf_nan=False)]] = Field(default_factory=dict)
    non_credit_status: Dict[str, Literal["completed", "incomplete", "unverified"]] = Field(default_factory=dict)


class ProfileDisplayUpdate(BaseModel):
    """Các trường hiển thị sinh viên được tự sửa trong Cài đặt.

    MSSV, lớp, CTĐT quyết định kết quả rà soát nên không nằm ở đây: chúng chỉ
    đến từ hồ sơ hoặc bảng điểm nhập từ CTT. Trường lạ bị từ chối (422).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    student_name: Optional[str] = Field(None, min_length=1, max_length=80)
    avatar_url: Optional[str] = Field(
        None, max_length=MAX_AVATAR_DATA_URL_LENGTH, pattern=AVATAR_DATA_URL_PATTERN
    )
    avatar_emoji: Optional[str] = Field(None, max_length=8)
    avatar_gradient: Optional[str] = Field(None, pattern=AVATAR_GRADIENT_PATTERN)

    @field_validator("student_name")
    @classmethod
    def _collapse_inner_spaces(cls, value: Optional[str]) -> Optional[str]:
        return " ".join(value.split()) if value is not None else value

class CourseConditionItem(BaseModel):
    code: str
    type: str # PREREQUISITE | COREQUISITE | PRIOR

class CourseRule(BaseModel):
    code: str
    name: str
    suggested_semester: Optional[int] = None
    credits: float = 0.0
    is_compulsory: bool = False
    category: Optional[str] = ""
    raw_condition: Optional[str] = ""
    condition_tree: List[List[CourseConditionItem]] = []
    flat_prerequisites: List[str] = []
    flat_prior_courses: List[str] = []
    flat_corequisites: List[str] = []
    min_credits_accumulated: int = 0

class StudentGradeItem(BaseModel):
    code: str
    name: str
    credits: float
    letter_grade: str
    numeric_grade: float
    is_passed: bool

class StudentProfile(BaseModel):
    info: Dict[str, str]
    total_courses_completed: int
    passed_courses: List[StudentGradeItem]
    failed_courses: List[StudentGradeItem]
    transcript: List[StudentGradeItem]

class CheckEligibilityRequest(BaseModel):
    course_code: str
    simulated_passed_codes: Optional[List[str]] = None


class AdvisingMemoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    target_track: Optional[str] = Field(None, pattern=r"^MOD[1-6]$")
    max_credits: Optional[int] = Field(None, ge=1, le=30, strict=True)
    target_cpa: Optional[float] = Field(None, ge=0, le=4, allow_inf_nan=False)

class CheckEligibilityResponse(BaseModel):
    course_code: str
    course_name: str
    is_eligible: bool
    status: str # ELIGIBLE | BLOCKED | ALREADY_PASSED | NOT_FOUND
    reasons: List[str] = []
    missing_prerequisites: List[str] = []
    missing_prior_courses: List[str] = []
    # Khi điều kiện có phép OR, mỗi nhánh được giữ riêng để UI/chatbot không
    # diễn giải nhầm danh sách hợp (A hoặc B) thành bắt buộc học cả A và B.
    missing_alternative_branches: List[Dict[str, Any]] = []
    satisfied_branch: Optional[List[Dict[str, str]]] = None

class DegreeAuditResponse(BaseModel):
    student_info: Dict[str, Any]
    curriculum: Dict[str, Any]
    cpa: float
    warning_level: Optional[int]
    warning_status: str = "unverified"
    warning_description: str
    warning_basis: str = ""
    debt_credits: float = 0.0
    credit_limit: Dict[str, Any]
    total_credits_accumulated: float
    total_credits_required: float
    completion_percentage: float
    passed_count: int
    failed_count: int
    unlearned_compulsory_courses: List[Dict[str, Any]]
    unlearned_elective_courses: List[Dict[str, Any]]
    graduation_group_audit: List[Dict[str, Any]] = []
    non_credit_requirements: List[Dict[str, Any]] = []
    academic_classification: Optional[Dict[str, Any]] = None
    target_kha_advice: Optional[Dict[str, Any]] = None
    graduation_ready: bool
    graduation_status: str = "unverified"
    pending_requirements: List[str]

class RecommendationRequest(BaseModel):
    target_track: Optional[str] = None  # MOD1 ... MOD6
    max_credits: Optional[int] = 20
    is_summer_term: Optional[bool] = False

class RecommendedCourseItem(BaseModel):
    code: str
    name: str
    credits: float
    suggested_semester: Optional[int]
    is_compulsory: bool
    category: str
    priority_reason: str
    prerequisite_summary: str

class RecommendationResponse(BaseModel):
    target_track: Optional[str]
    track_name: Optional[str]
    total_credits_suggested: float
    max_allowed_credits: int
    recommended_courses: List[RecommendedCourseItem]
    advice_note: str

class ImpactSimulationRequest(BaseModel):
    failed_course_code: str

class ImpactSimulationResponse(BaseModel):
    failed_course_code: str
    failed_course_name: str
    direct_blocked_courses: List[Dict[str, Any]]
    direct_at_risk_courses: List[Dict[str, Any]] = []
    indirect_blocked_courses: List[Dict[str, Any]]
    total_blocked: int
    severity: str # HIGH | MEDIUM | LOW
    analysis: str

class ChatMessage(BaseModel):
    role: str # user | assistant
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: Optional[List[ChatMessage]] = []
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: Optional[str] = None
    intent: Optional[str] = None
    suggested_actions: Optional[List[str]] = []
    data_context: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, str]]] = []
    model_used: Optional[str] = None

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None
