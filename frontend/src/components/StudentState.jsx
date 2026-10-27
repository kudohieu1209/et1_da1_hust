import './StudentState.css';
import useMascot from '../useMascot';

export default function StudentState({ variant, title, description, actionLabel, onAction, compact = false, role = 'status' }) {
  const { mascot } = useMascot();
  const image = mascot.states[variant];
  return (
    <div className={`student-state student-state--${variant}${compact ? ' student-state--compact' : ''}`} role={role}>
      {image && <img className="student-state__image" src={image} alt="" loading="lazy" decoding="async" width="160" height="160" />}
      <div className="student-state__content">
        <h3>{title}</h3>
        <p>{description}</p>
        {onAction && actionLabel && <button type="button" className="btn-primary" onClick={onAction}>{actionLabel}</button>}
      </div>
    </div>
  );
}

export function TranscriptEmptyState({ onImport, language = 'vi', compact = false }) {
  const vi = language === 'vi';
  return <StudentState variant="transcript" compact={compact}
    title={vi ? 'Bắt đầu với bảng điểm của bạn' : 'Start with your transcript'}
    description={vi ? 'Dán bảng điểm từ CTT để xem CPA, tiến độ tích lũy và gợi ý môn phù hợp với bạn.' : 'Paste your CTT transcript to see your CPA, credit progress and course suggestions.'}
    actionLabel={vi ? 'Nhập bảng điểm' : 'Import transcript'} onAction={onImport} />;
}

export function AcademicMilestone({ auditData, language = 'vi' }) {
  const required = auditData?.total_credits_required;
  const accumulated = auditData?.total_credits_accumulated;
  if (!(required > 0 && accumulated >= required)) return null;
  const vi = language === 'vi';
  return <StudentState variant="achievement"
    title={vi ? 'Bạn đã đạt mốc tín chỉ của chương trình!' : 'You reached the credit milestone!'}
    description={vi ? `Đã tích lũy ${accumulated}/${required} tín chỉ. Hãy tiếp tục đối chiếu các nhóm học phần, CPA và chuẩn đầu ra bên dưới; đây chưa phải xác nhận tốt nghiệp.` : `You have earned ${accumulated}/${required} credits. Check the course groups, CPA and other requirements below; this does not confirm graduation.`} />;
}
