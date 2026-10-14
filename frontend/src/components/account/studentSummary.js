// Dữ liệu hiển thị của sinh viên, ghép từ hồ sơ (/api/student/profile) và kết
// quả rà soát (/api/student/audit). Không có giá trị mặc định giả: khi chưa tải
// xong, các trường số là null để giao diện hiện "—" thay vì số sai.

export const DEFAULT_AVATAR_GRADIENT = 'linear-gradient(135deg, #d3132a, #8f1423)';

// Phải khớp AVATAR_GRADIENT_PATTERN của backend (schemas.ProfileDisplayUpdate).
export const AVATAR_GRADIENTS = [
  { id: 'hust', vi: 'Đỏ Bách Khoa', en: 'HUST red', value: DEFAULT_AVATAR_GRADIENT },
  { id: 'burgundy', vi: 'Đỏ trầm', en: 'Burgundy', value: 'linear-gradient(135deg, #a91024, #710619)' },
  { id: 'gold', vi: 'Vàng trầm', en: 'Deep gold', value: 'linear-gradient(135deg, #946b00, #735400)' },
  { id: 'charcoal', vi: 'Xám than', en: 'Charcoal', value: 'linear-gradient(135deg, #525254, #222224)' },
];

const formatCredits = (value) => (Number.isInteger(value) ? String(value) : value.toFixed(1));

/**
 * @param {{ info?: Record<string, any> } | null} profile
 * @param {Record<string, any> | null} audit
 */
export function buildStudentSummary(profile, audit) {
  const info = profile?.info ?? {};
  const curriculum = audit?.curriculum ?? {};
  const name = String(info.student_name ?? '').trim();
  const programCode = curriculum.program_code || info.program_code || info.program_id || '';
  const version = curriculum.curriculum_version || info.curriculum_version || '';
  const accumulated = audit?.total_credits_accumulated;
  const required = audit?.total_credits_required;

  return {
    name,
    initial: (name.charAt(0) || '?').toUpperCase(),
    studentId: info.student_id || '',
    className: info.class_name || '',
    programCode,
    curriculumVersion: version,
    programName: curriculum.name || info.program_name || '',
    cpa: typeof audit?.cpa === 'number' ? audit.cpa : null,
    rank: audit?.academic_classification?.rank || null,
    warningLevel: Number(audit?.warning_level) || 0,
    warningText: audit?.warning_description || '',
    completion: typeof audit?.completion_percentage === 'number' ? audit.completion_percentage : null,
    creditsText:
      typeof accumulated === 'number' && typeof required === 'number'
        ? `${formatCredits(accumulated)}/${formatCredits(required)} TC`
        : null,
    avatar: {
      url: info.avatar_url || '',
      emoji: info.avatar_emoji || '',
      gradient: info.avatar_gradient || DEFAULT_AVATAR_GRADIENT,
    },
  };
}

/** "ET1 · 2022" hoặc chuỗi rỗng khi chưa biết CTĐT. */
export function programLabel(summary) {
  return [summary.programCode, summary.curriculumVersion].filter(Boolean).join(' · ');
}

export function formatCpa(cpa) {
  return typeof cpa === 'number' ? cpa.toFixed(2) : '—';
}
