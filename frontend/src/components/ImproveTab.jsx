import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  RotateCcw
} from 'lucide-react';
import { apiFetch, apiUrl } from '../api';

const MILESTONES = [
  { min: 2.0, max: 2.49, rank: 'Trung bình', color: '#f59e0b', next: 2.50, nextRank: 'Khá' },
  { min: 2.50, max: 3.19, rank: 'Khá', color: '#3b82f6', next: 3.20, nextRank: 'Giỏi' },
  { min: 3.20, max: 3.59, rank: 'Giỏi', color: '#10b981', next: 3.60, nextRank: 'Xuất sắc' },
  { min: 3.60, max: 4.0, rank: 'Xuất sắc', color: '#8b5cf6', next: null, nextRank: null },
];

export default function ImproveTab({ language = 'vi' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // targets: { [course_code]: target_grade (e.g. 'A', 'B+', 'B', 'C') }
  const [selectedTargets, setSelectedTargets] = useState({});

  const t = (vi, en) => (language === 'vi' ? vi : en);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch(apiUrl('/api/student/improve-courses'));
        if (!res.ok) throw new Error('Không thể tải dữ liệu phân tích cải thiện điểm.');
        const result = await res.json();
        if (!cancelled) {
          setData(result);
          // Mặc định chọn mục tiêu B cho tất cả các môn
          const initial = {};
          result.improve_candidates?.forEach(c => {
            if (c.projections?.B) initial[c.code] = 'B';
            else if (c.projections?.C) initial[c.code] = 'C';
          });
          setSelectedTargets(initial);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadData();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 12 }}>
        <div className="spin" style={{ width: 32, height: 32, border: '3px solid var(--border-subtle)', borderTopColor: 'var(--brand-accent)', borderRadius: '50%' }} />
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{t('Đang phân tích bảng điểm & mô phỏng CPA...', 'Analyzing transcript & simulating CPA...')}</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)' }}>
        <AlertTriangle size={36} color="#f59e0b" style={{ margin: '0 auto 12px' }} />
        <p>{error || t('Chưa có dữ liệu phân tích.', 'No analysis data available.')}</p>
      </div>
    );
  }

  const currentCpa = data.current_cpa || 0;
  const candidates = data.improve_candidates || [];

  // Tính CPA mô phỏng dựa trên các mục tiêu đã chọn
  let simulatedGain = 0;
  candidates.forEach(c => {
    const target = selectedTargets[c.code];
    if (target && c.projections?.[target]) {
      simulatedGain += c.projections[target].delta_cpa;
    }
  });

  const simulatedCpa = Math.min(4.0, Math.round((currentCpa + simulatedGain) * 100) / 100);
  const currentMilestone = MILESTONES.find(m => currentCpa >= m.min && currentCpa <= m.max) || MILESTONES[0];
  const simulatedMilestone = MILESTONES.find(m => simulatedCpa >= m.min && simulatedCpa <= m.max) || MILESTONES[0];

  const resetAll = () => setSelectedTargets({});
  const setAllTarget = (grade) => {
    const next = {};
    candidates.forEach(c => {
      if (c.projections?.[grade]) next[c.code] = grade;
    });
    setSelectedTargets(next);
  };

  return (
    <div style={{ padding: '20px 24px 60px', maxWidth: 960, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(213, 19, 42, 0.08) 0%, rgba(59, 130, 246, 0.08) 100%)',
        borderRadius: 20,
        padding: '24px 28px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 20
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <TrendingUp size={22} color="var(--brand-accent)" />
            <h2 style={{ fontSize: '1.35rem', fontWeight: 650, margin: 0, color: 'var(--text-primary)' }}>
              {t('Tính toán & Mô phỏng Học cải thiện điểm', 'CPA Improvement & Retake Simulator')}
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: 540, lineHeight: 1.5 }}>
            {t(
              'Quy chế Bách Khoa: Điểm F bắt buộc học lại; Điểm D/D+ được phép học cải thiện để nâng CPA. Hệ thống tự động tính mức tăng điểm thực tế theo số tín chỉ.',
              'HUST Academic Rules: Grade F must be retaken; D/D+ can be improved to boost CPA. The engine computes actual CPA gain weighted by credit count.'
            )}
          </p>
        </div>

        {/* Milestone Badge */}
        <div style={{
          background: 'var(--bg-surface)',
          padding: '16px 20px',
          borderRadius: 16,
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          gap: 20,
          alignItems: 'center'
        }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('CPA Hiện tại', 'Current CPA')}</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentCpa.toFixed(2)}
              <span style={{ fontSize: '0.78rem', fontWeight: 550, color: currentMilestone.color, marginLeft: 8 }}>({currentMilestone.rank})</span>
            </div>
          </div>
          <div style={{ width: 1, height: 36, background: 'var(--border-subtle)' }} />
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--brand-accent)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>{t('CPA Sau cải thiện', 'Simulated CPA')}</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--brand-accent)' }}>
              {simulatedCpa.toFixed(2)}
              <span style={{ fontSize: '0.78rem', fontWeight: 550, color: simulatedMilestone.color, marginLeft: 6 }}>
                ({simulatedMilestone.rank})
              </span>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#10b981', marginLeft: 6 }}>
                (+{simulatedGain.toFixed(2)})
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Target Presets & Actions */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{t('Chọn nhanh tất cả mục tiêu:', 'Quick set all targets:')}</span>
          {['B', 'B+', 'A'].map(grade => (
            <button
              key={grade}
              type="button"
              onClick={() => setAllTarget(grade)}
              style={{
                padding: '4px 10px',
                borderRadius: 8,
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Lên điểm {grade}
            </button>
          ))}
          <button
            type="button"
            onClick={resetAll}
            style={{
              padding: '4px 10px',
              borderRadius: 8,
              border: 'none',
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4
            }}
          >
            <RotateCcw size={12} /> {t('Đặt lại', 'Reset')}
          </button>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {t(`Tìm thấy ${candidates.length} môn có thể cải thiện / học lại`, `Found ${candidates.length} improvable courses`)}
        </div>
      </div>

      {/* Candidates List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {candidates.map((course) => {
          const currentTarget = selectedTargets[course.code] || null;
          const currentProjection = currentTarget ? course.projections?.[currentTarget] : null;

          return (
            <div
              key={course.code}
              style={{
                background: 'var(--bg-surface)',
                border: course.is_failed ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid var(--border-subtle)',
                borderRadius: 16,
                padding: '16px 20px',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 16,
                transition: 'border-color 0.15s ease'
              }}
            >
              {/* Course Info */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 260 }}>
                <div style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  background: course.is_failed ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                  color: course.is_failed ? '#ef4444' : '#f59e0b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '1rem',
                  flexShrink: 0
                }}>
                  {course.current_letter_grade}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 650, fontSize: '0.92rem', color: 'var(--text-primary)' }}>{course.code} — {course.name}</span>
                    {course.is_failed && (
                      <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: 4, background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontWeight: 600 }}>
                        {t('Nợ đọng (F)', 'Failed')}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                    {course.credits} {t('tín chỉ', 'credits')} • {course.reason}
                  </div>
                </div>
              </div>

              {/* Target Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginRight: 4 }}>{t('Mục tiêu:', 'Target:')}</span>
                {['C', 'B', 'B+', 'A'].map(grade => {
                  const available = !!course.projections?.[grade];
                  const isSelected = currentTarget === grade;
                  if (!available) return null;

                  return (
                    <button
                      key={grade}
                      type="button"
                      onClick={() => setSelectedTargets(prev => ({ ...prev, [course.code]: isSelected ? null : grade }))}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 8,
                        border: isSelected ? '1px solid var(--brand-accent)' : '1px solid var(--border-subtle)',
                        background: isSelected ? 'rgba(213, 19, 42, 0.12)' : 'var(--bg-card)',
                        color: isSelected ? 'var(--brand-accent)' : 'var(--text-secondary)',
                        fontWeight: isSelected ? 700 : 500,
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {grade}
                    </button>
                  );
                })}
              </div>

              {/* Impact readout */}
              <div style={{ minWidth: 100, textAlign: 'right' }}>
                {currentProjection ? (
                  <div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t('Tăng CPA:', 'CPA Gain:')}</span>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#10b981' }}>
                      +{currentProjection.delta_cpa.toFixed(3)}
                    </div>
                  </div>
                ) : (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    {t('Chưa chọn', 'Not selected')}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
