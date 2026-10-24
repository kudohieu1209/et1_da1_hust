import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, Loader2, UploadCloud, X } from 'lucide-react';
import { apiFetch, apiUrl, readError } from '../api';
import { TranscriptEmptyState } from './StudentState';

const SAMPLE_TRANSCRIPT = `MI1111  Giải tích I                 4   A
MI1121  Giải tích II                3   B+
MI1141  Đại số                      4   B
PH1111  Vật lý đại cương I          3   B+
IT1110  Tin học đại cương           4   A
SSH1111 Triết học Mác - Lênin       3   C+
ET2040  Cấu kiện điện tử            3   B
ET2050  Lý thuyết mạch              3   B+
ET2060  Tín hiệu và hệ thống        3   A
ET3220  Điện tử số                  3   B+
ET3230  Điện tử tương tự I          3   B
ET3300  Kỹ thuật vi xử lý           3   B+
ET3260  Kỹ thuật phần mềm ứng dụng 2   A`;

const fieldStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: '8px',
  border: '1px solid var(--border-subtle)',
  background: 'var(--bg-card)',
  color: 'var(--text-primary)',
  fontSize: '0.82rem',
  fontFamily: 'monospace',
  lineHeight: 1.4,
  resize: 'vertical',
};

/** Nhập bảng điểm copy từ CTT cho tài khoản đang đăng nhập (thay toàn bộ bảng điểm cũ). */
export default function TranscriptImportModal({ isOpen, onClose, onImported, hasTranscript, auditData, language = 'vi' }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [text, setText] = useState('');
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState(null);
  const [unresolved, setUnresolved] = useState([]);
  const [creditOverrides, setCreditOverrides] = useState({});
  const [warningLevel, setWarningLevel] = useState('');
  const [requirementStatuses, setRequirementStatuses] = useState({});
  const wasOpen = useRef(false);

  useEffect(() => {
    if (isOpen && !wasOpen.current) {
      setMessage(null);
      setUnresolved([]);
      setCreditOverrides({});
      setWarningLevel(auditData?.warning_level == null ? '' : String(auditData.warning_level));
      setRequirementStatuses(Object.fromEntries((auditData?.non_credit_requirements || []).map(
        (item) => [item.requirement_id, item.status || 'unverified'],
      )));
    }
    wasOpen.current = isOpen;
  }, [isOpen, auditData]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) {
      setMessage({ type: 'error', text: t('Vui lòng dán nội dung bảng điểm từ CTT.', 'Please paste your CTT transcript.') });
      return;
    }
    setImporting(true);
    setMessage(null);
    try {
      const res = await apiFetch(apiUrl('/api/student/import'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_text: text,
          warning_level: warningLevel === '' ? null : Number(warningLevel),
          course_credit_overrides: Object.fromEntries(Object.entries(creditOverrides)
            .filter(([, value]) => value !== '').map(([code, value]) => [code, Number(value)])),
          non_credit_status: requirementStatuses,
        }),
      });
      if (!res.ok) {
        setMessage({ type: 'error', text: await readError(res, t('Không nạp được bảng điểm.', 'Import failed.')) });
        return;
      }
      const data = await res.json();
      if (data.status === 'needs_confirmation') {
        setUnresolved(data.unresolved_courses || []);
        setMessage({ type: 'error', text: data.message });
        return;
      }
      setMessage({ type: 'success', text: data.message || t('Nhập bảng điểm thành công!', 'Transcript imported!') });
      onImported?.(data);
      setText('');
      if (!data.skipped_lines?.length) setTimeout(onClose, 900);
    } catch {
      setMessage({ type: 'error', text: t('Không kết nối được máy chủ.', 'Cannot reach the server.') });
    } finally {
      setImporting(false);
    }
  };

  return (
    <div
      className="apple-modal-backdrop"
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}
    >
      <div
        className="apple-modal-window"
        role="dialog"
        aria-modal="true"
        aria-labelledby="transcript-import-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '18px',
          width: '100%',
          maxWidth: '640px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-card)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px', background: 'var(--brand-gradient)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
            }}>
              <UploadCloud size={20} />
            </div>
            <div>
              <h2 id="transcript-import-title" style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                {t('Nhập bảng điểm từ CTT', 'Import CTT transcript')}
              </h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                {t('Hệ thống tính lại tiến độ, CPA và gợi ý môn theo bảng điểm này', 'Progress, CPA and suggestions are recalculated')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('Đóng', 'Close')}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px', borderRadius: '6px', display: 'flex' }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '20px 24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {!hasTranscript && !text.trim() && <TranscriptEmptyState compact language={language} />}
          <div style={{
            background: 'var(--brand-soft)',
            border: '1px solid var(--border-hust)',
            borderRadius: '10px',
            padding: '12px 14px',
            fontSize: '0.8rem',
            color: 'var(--text-primary)',
            lineHeight: 1.45,
          }}>
            <strong>{t('Cách làm:', 'How to:')}</strong>{' '}
            {t(
              'Đăng nhập ctt.hust.edu.vn → Bảng điểm cá nhân, quét chọn các dòng có mã học phần và điểm chữ (ví dụ "ET2040 … B+"), copy rồi dán vào ô dưới.',
              'Open ctt.hust.edu.vn → personal transcript, copy the rows with course codes and letter grades, and paste them below.',
            )}
            {hasTranscript && (
              <div style={{ marginTop: '6px', color: 'var(--warning)' }}>
                {t('Bảng điểm mới sẽ thay thế toàn bộ bảng điểm hiện tại.', 'The new transcript replaces the current one.')}
              </div>
            )}
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label htmlFor="transcript-text" style={{ fontSize: '0.78rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                {t('Nội dung bảng điểm', 'Transcript text')}
              </label>
              <button
                type="button"
                onClick={() => { setText(SAMPLE_TRANSCRIPT); setUnresolved([]); setCreditOverrides({}); }}
                style={{ background: 'transparent', border: 'none', color: 'var(--brand-accent)', fontSize: '0.76rem', cursor: 'pointer', textDecoration: 'underline' }}
              >
                {t('Điền bảng điểm mẫu', 'Use sample')}
              </button>
            </div>
            <textarea
              id="transcript-text"
              rows={10}
              value={text}
              onChange={(e) => { setText(e.target.value); setUnresolved([]); setCreditOverrides({}); }}
              placeholder={t('Dán các dòng bảng điểm từ CTT vào đây… (ví dụ: ET2040 Cấu kiện điện tử 3 B+)', 'Paste transcript rows here…')}
              style={fieldStyle}
            />
          </div>

          {unresolved.length > 0 && (
            <fieldset style={{ border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px' }}>
              <legend>{t('Xác nhận học phần ngoài danh mục', 'Confirm courses outside the curriculum')}</legend>
              <p style={{ fontSize: '0.8rem' }}>{t('Đối chiếu mã môn, điểm chữ và nhập số tín chỉ từ CTT. Bảng điểm cũ chưa bị thay đổi.', 'Check codes, grades and credits against CTT. Your previous transcript has not changed.')}</p>
              {[...new Set(unresolved.map((item) => item.code))].map((code) => (
                <label key={code} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '8px' }}>
                  <span style={{ flex: 1, fontSize: '0.8rem' }}>{code} · {unresolved.filter((item) => item.code === code).map((item) => item.letter_grade).join(', ')}</span>
                  <input type="number" min="0" step="0.5" required aria-label={`${code} ${t('số tín chỉ', 'credits')}`}
                    value={creditOverrides[code] ?? ''} style={{ ...fieldStyle, width: '100px' }}
                    onChange={(e) => setCreditOverrides((previous) => ({ ...previous, [code]: e.target.value }))} />
                </label>
              ))}
            </fieldset>
          )}

          <label style={{ fontSize: '0.8rem' }}>
            {t('Mức cảnh báo học tập hiện tại trên CTT', 'Current academic warning level on CTT')}
            <select value={warningLevel} onChange={(e) => setWarningLevel(e.target.value)} style={{ ...fieldStyle, marginTop: '6px' }}>
              <option value="">{t('Chưa có thông tin', 'Unknown')}</option>
              {[0, 1, 2, 3].map((level) => <option key={level} value={level}>{t('Mức', 'Level')} {level}</option>)}
            </select>
          </label>
          {(auditData?.non_credit_requirements || []).map((item) => (
            <label key={item.requirement_id} style={{ fontSize: '0.8rem' }}>
              {item.name} · {t('theo hồ sơ CTT của bạn', 'according to your CTT record')}
              <select value={requirementStatuses[item.requirement_id] || 'unverified'}
                onChange={(e) => setRequirementStatuses((previous) => ({ ...previous, [item.requirement_id]: e.target.value }))}
                style={{ ...fieldStyle, marginTop: '6px' }}>
                <option value="unverified">{t('Chưa xác minh', 'Unverified')}</option>
                <option value="completed">{t('Đã hoàn thành', 'Completed')}</option>
                <option value="incomplete">{t('Chưa hoàn thành', 'Incomplete')}</option>
              </select>
            </label>
          ))}

          {message && (
            <div
              role={message.type === 'error' ? 'alert' : 'status'}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 12px', borderRadius: '6px', fontSize: '0.8rem',
                background: message.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
                color: message.type === 'success' ? 'var(--success)' : 'var(--danger)',
              }}
            >
              {message.type === 'success' && <CheckCircle2 size={15} />}
              <span>{message.text}</span>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-muted)', fontSize: '0.84rem', cursor: 'pointer' }}
            >
              {t('Hủy', 'Cancel')}
            </button>
            <button
              type="submit"
              disabled={importing}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 18px', borderRadius: '8px', border: 'none',
                background: 'var(--brand-gradient)', color: '#fff', fontSize: '0.84rem', fontWeight: 600, cursor: 'pointer',
              }}
            >
              {importing ? <Loader2 size={16} className="spin" /> : <UploadCloud size={16} />}
              <span>{importing ? t('Đang phân tích…', 'Analyzing…') : t('Phân tích & lưu', 'Analyze & save')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
