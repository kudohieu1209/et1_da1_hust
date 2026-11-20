import React, { useState } from 'react';
import { AcademicMilestone, TranscriptEmptyState } from './StudentState';
import {
  CheckCircle2,
  AlertTriangle,
  GraduationCap,
  ArrowRight,
  ShieldCheck,
  Clock,
  Sparkles,
  Layers,
  Calendar,
  Upload,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import './AuditTab.css';

const COMPULSORY_PREVIEW_COUNT = 8;

export default function AuditTab({
  auditData,
  onNavigateTab,
  onOpenImport,
  hasTranscript,
  language = 'vi'
}) {
  const [showAllCompulsory, setShowAllCompulsory] = useState(false);

  if (!auditData) {
    return (
      <div className="audit-loading">
        <div style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '8px' }}>Đang tải báo cáo tiến độ học tập...</div>
        <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Vui lòng đợi giây lát trong khi hệ thống đồng bộ dữ liệu CTĐT Bách Khoa.</div>
      </div>
    );
  }

  const {
    student_info = {},
    curriculum = {},
    cpa = 0,
    warning_level = null,
    warning_description = 'Chưa xác định mức cảnh báo',
    warning_basis = '',
    credit_limit = {},
    total_credits_accumulated = 0,
    total_credits_required = 0,
    completion_percentage = 0,
    passed_count = 0,
    failed_count = 0,
    academic_classification = { rank: 'Trung bình', color: 'var(--warning)', desc: '2.00 ≤ CPA < 2.50' },
    target_kha_advice = null,
    unlearned_compulsory_courses = [],
    unlearned_elective_courses = [],
    graduation_group_audit = [],
    non_credit_requirements = [],
    graduation_ready = false,
    graduation_status = 'unverified'
  } = auditData;

  const hasAnyTranscriptData = hasTranscript ?? (passed_count + failed_count > 0);

  const classificationTone = !hasAnyTranscriptData
    ? 'indigo'
    : ['Xuất sắc', 'Giỏi', 'Khá'].includes(academic_classification.rank)
      ? 'success'
      : ['Yếu', 'Kém'].includes(academic_classification.rank) ? 'danger' : 'warning';
  const classificationColor = !hasAnyTranscriptData ? 'var(--text-primary)' : `var(--${classificationTone})`;
  const classificationLabel = !hasAnyTranscriptData ? 'Chưa xếp loại' : `Loại ${academic_classification.rank}`;
  const warningTone = warning_level == null || warning_level > 0 ? 'warning' : 'success';
  const requirementLabels = { completed: 'Đã hoàn thành (theo khai báo)', incomplete: 'Chưa hoàn thành', unverified: 'Chưa xác minh' };

  const remaining_credits = Math.max(0, total_credits_required - total_credits_accumulated);
  const compulsory_credits_missing = unlearned_compulsory_courses.reduce((sum, c) => sum + (c.credits || 0), 0);
  const elective_credits_missing = Math.max(0, remaining_credits - compulsory_credits_missing);
  const moduleRequirement = graduation_group_audit.find(item => item.type === 'ONE_OF_GROUPS');
  const moduleCount = moduleRequirement?.options?.length || 0;
  const maxCreditsPerSemester = Number(credit_limit.max || 24);
  const theoreticalMinSemesters = remaining_credits > 0
    ? Math.ceil(remaining_credits / Math.max(1, maxCreditsPerSemester))
    : 0;

  const displayedCompulsory = showAllCompulsory
    ? unlearned_compulsory_courses
    : unlearned_compulsory_courses.slice(0, COMPULSORY_PREVIEW_COUNT);
  const hiddenCompulsoryCount = Math.max(0, unlearned_compulsory_courses.length - COMPULSORY_PREVIEW_COUNT);

  // SVG Circular progress
  const radius = 38;
  const strokeWidth = 7;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (completion_percentage / 100) * circumference;

  return (
    <div className="audit-page">
      {hasAnyTranscriptData === false && (
        <TranscriptEmptyState onImport={onOpenImport} language={language} />
      )}
      <AcademicMilestone auditData={auditData} language={language} />

      {/* 1. Header */}
      <div className="audit-header">
        <div>
          <div className="audit-header__meta">
            <span className="badge badge-hust">{curriculum.program_code || 'CTĐT'} • {curriculum.curriculum_version || '—'}</span>
            <span className="audit-header__source">Nguồn CTĐT đã chuẩn hóa</span>
          </div>
          <h2>Tiến độ Học tập & Chuẩn Tốt nghiệp</h2>
          <p className="audit-header__subtitle">
            Ngành {curriculum.name || student_info.program_name || '—'} ({curriculum.program_code || '—'}) • Sinh viên:{' '}
            <strong style={{ color: 'var(--text-primary)' }}>{student_info.student_name || '—'}</strong> (MSSV: {student_info.student_id || '—'})
          </p>
        </div>

        <div className="audit-header__actions">
          <div className="gemini-pill audit-header__pill">
            <span>Đã qua <strong style={{ color: 'var(--success)' }}>{passed_count}</strong> môn</span>
            <span>•</span>
            <span>Nợ <strong style={{ color: failed_count > 0 ? 'var(--danger)' : 'var(--text-primary)' }}>{failed_count}</strong> môn</span>
          </div>
          {onOpenImport && (
            <button
              type="button"
              onClick={onOpenImport}
              className="btn-primary gemini-pill audit-header__import-btn"
            >
              <Upload size={15} />
              <span>{hasAnyTranscriptData ? 'Cập nhật bảng điểm' : 'Nhập bảng điểm'}</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. Top 4 Metric Bento Cards (1 -> 2x2 -> 4x1) */}
      <div className="audit-kpi-grid">
        {/* Card 1: Credit Progress */}
        <div className="glass-panel audit-kpi-card">
          <div className="audit-kpi-card__top">
            <span className="audit-kpi-card__label">TIẾN ĐỘ TÍN CHỈ</span>
            <span className="badge badge-success audit-kpi-card__badge">
              {completion_percentage >= 90 ? 'Gần cán đích' : 'Đang tích lũy'}
            </span>
          </div>

          <div className="audit-kpi-ring-row">
            <div style={{ position: 'relative', width: '90px', height: '90px', flexShrink: 0 }}>
              <svg viewBox="0 0 96 96" style={{ transform: 'rotate(-90deg)', width: '90px', height: '90px', overflow: 'visible' }}>
                <circle
                  cx="48"
                  cy="48"
                  r={radius}
                  stroke="var(--border-subtle)"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                />
                <circle
                  cx="48"
                  cy="48"
                  r={radius}
                  stroke="url(#hustProgressGradient)"
                  strokeWidth={strokeWidth}
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                  style={{ transition: 'stroke-dashoffset 1.4s var(--ease-apple)' }}
                />
                <defs>
                  <linearGradient id="hustProgressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="var(--hust-red)" />
                    <stop offset="100%" stopColor="var(--brand-gold)" />
                  </linearGradient>
                </defs>
              </svg>
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <span style={{ fontSize: '1.08rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                  {completion_percentage}%
                </span>
              </div>
            </div>

            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '1.22rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                {total_credits_accumulated} / {total_credits_required}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Tín chỉ tích lũy
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--brand-accent)', fontWeight: '600', marginTop: '4px' }}>
                Còn thiếu {remaining_credits.toFixed(1)} TC
              </div>
            </div>
          </div>

          <div className="audit-kpi-footer">
            Đã hoàn thành {completion_percentage}% khối lượng CTĐT
          </div>
        </div>

        {/* Card 2: CPA Status */}
        <div className="glass-panel audit-kpi-card">
          <div className="audit-kpi-card__top">
            <span className="audit-kpi-card__label">CPA HIỆN TẠI</span>
            <span className={`badge badge-${classificationTone} audit-kpi-card__badge`} style={{ fontWeight: '700' }}>
              {classificationLabel}
            </span>
          </div>

          <div>
            <div style={{
              fontSize: '2.05rem',
              fontWeight: '800',
              color: classificationColor,
              lineHeight: '1.1'
            }}>
              {hasAnyTranscriptData ? cpa.toFixed(2) : '—'}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {hasAnyTranscriptData ? `Thang điểm 4.0 • ${academic_classification.desc}` : 'Chưa có dữ liệu điểm để xếp loại'}
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', marginBottom: '4px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Chuẩn Bằng Khá (≥ 2.50)</span>
              <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{cpa.toFixed(2)} / 2.50</span>
            </div>
            <div className="audit-progress-track" style={{ height: '6px' }}>
              <div
                className="audit-progress-fill"
                style={{
                  width: `${Math.min(100, (cpa / 2.5) * 100)}%`,
                  background: cpa >= 2.5 ? 'var(--success)' : 'var(--warning)'
                }}
              />
            </div>
          </div>
        </div>

        {/* Card 3: Academic Standing */}
        <div className="glass-panel audit-kpi-card">
          <div className="audit-kpi-card__top">
            <span className="audit-kpi-card__label">CẢNH BÁO HỌC TẬP</span>
            <span className={`badge badge-${warningTone} audit-kpi-card__badge`}>
              {warning_level == null ? 'Chưa xác định' : `Mức ${warning_level}`}
            </span>
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={22} color={`var(--${warningTone})`} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '1.16rem', fontWeight: '700', color: `var(--${warningTone})`, lineHeight: 1.25 }}>
                {warning_description}
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
              {warning_basis || 'Hãy đối chiếu mức cảnh báo hiện tại trên CTT.'}
            </div>
          </div>

          <div className="audit-kpi-pill-footer">
            {credit_limit.is_provisional ? 'Hạn mức tạm' : 'Hạn mức ĐK'}: <strong style={{ color: 'var(--text-primary)' }}>Tối đa {credit_limit.max || 14} TC</strong>/kỳ
          </div>
        </div>

        {/* Card 4: Graduation Overview */}
        <div className="glass-panel audit-kpi-card">
          <div className="audit-kpi-card__top">
            <span className="audit-kpi-card__label">XÉT TỐT NGHIỆP</span>
            <span className={graduation_ready ? 'badge badge-success audit-kpi-card__badge' : 'badge badge-warning audit-kpi-card__badge'}>
              {graduation_ready ? 'Đạt hồ sơ' : graduation_status === 'unverified' ? 'Chưa xác minh' : 'Đang hoàn thiện'}
            </span>
          </div>

          <div>
            <div style={{ fontSize: '1.02rem', fontWeight: '700', color: 'var(--text-primary)' }}>
              Đã qua <span style={{ color: 'var(--success)' }}>{passed_count} môn</span> • <span style={{ color: failed_count > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>Nợ {failed_count} môn</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
              Còn <strong style={{ color: 'var(--text-primary)' }}>{unlearned_compulsory_courses.length} môn bắt buộc</strong> ({compulsory_credits_missing.toFixed(0)} TC) và các nhóm tín chỉ chưa đủ.
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: 'var(--brand-accent)',
            fontWeight: '600'
          }}>
            <Calendar size={14} style={{ flexShrink: 0 }} />
            <span>{credit_limit.is_provisional ? 'Dự kiến' : 'Ít nhất'} {theoreticalMinSemesters} học kỳ {credit_limit.is_provisional ? 'theo hạn mức tạm' : 'theo giới hạn tín chỉ'}</span>
          </div>
        </div>
      </div>

      {/* 3. Smart Advisor Banner */}
      {hasAnyTranscriptData && cpa < 2.5 && target_kha_advice && (
        <div style={{
          padding: '15px 18px',
          borderRadius: 'var(--radius-lg)',
          background: 'rgba(213, 19, 42, 0.08)',
          border: '1px solid rgba(213, 19, 42, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px',
          flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', flex: '1 1 420px', minWidth: 0 }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: 'rgba(213, 19, 42, 0.15)',
              color: 'var(--brand-accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <Sparkles size={18} />
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span>Mục tiêu CPA ≥ 2.50</span>
                <span className="badge badge-indigo" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>Khuyến nghị</span>
              </div>
              <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.45', margin: '4px 0 0' }}>
                {target_kha_advice.remaining_credits === 0 ? (
                  <>Bạn đã đủ khối lượng tín chỉ nhưng CPA hiện tại là <strong>{cpa.toFixed(2)}</strong>. Cần xem phương án học cải thiện để đạt CPA 2.50.</>
                ) : target_kha_advice.is_achievable ? (
                  <>Với CPA hiện tại <strong>{cpa.toFixed(2)}</strong>, GPA trung bình cần đạt cho {target_kha_advice.remaining_credits} TC còn lại là <strong>{target_kha_advice.gpa_needed_remaining}</strong>.</>
                ) : (
                  <>Chỉ hoàn thành {target_kha_advice.remaining_credits} TC còn lại chưa đủ đạt CPA 2.50 vì GPA cần đạt vượt 4.0. Cần xem thêm phương án học cải thiện.</>
                )}
                {' '}Ước tính dựa trên bảng điểm đã nhập; số môn và mức điểm cải thiện cần được tính riêng.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab('improve')}
            className="btn-primary gemini-pill"
            style={{ fontSize: '0.8rem', padding: '8px 16px', borderRadius: 'var(--radius-full)', flexShrink: 0 }}
          >
            <span>Tính phương án cải thiện</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* 4. Balanced 2-Column Overview: Graduation Formula Groups vs Graduation Checklist + Forecast */}
      <div className="audit-overview-grid">
        {/* Left: Credit groups from the versioned graduation formula */}
        <div className="glass-panel audit-panel">
          <div className="audit-panel__head">
            <div className="audit-panel__head-text">
              <h3 className="audit-panel__title">Tiến độ theo nhóm trong công thức tốt nghiệp</h3>
              <span className="audit-panel__subtitle" style={{ wordBreak: 'break-word' }}>{curriculum.graduation_formula || 'Chưa có công thức CTĐT'}</span>
            </div>
            <span className="badge badge-indigo" style={{ flexShrink: 0 }}>{graduation_group_audit.length} thành phần</span>
          </div>

          <div className="audit-groups-grid">
            {graduation_group_audit.map((group, index) => {
              const required = Number(group.required_credits || 0);
              const earned = Number(group.earned_credits || 0);
              const pct = required > 0 ? Math.min(100, Math.round((earned / required) * 100)) : (group.is_complete ? 100 : 0);
              const hasOptions = Boolean(group.options && group.options.length > 0);
              return (
                <div
                  key={group.group_id || `choice-${index}`}
                  className={`audit-group-card${hasOptions ? ' audit-group-card--wide' : ''}`}
                >
                  <div className="audit-group-card__row">
                    <strong className="audit-group-card__name">{group.name}</strong>
                    <span
                      className="audit-group-card__credits"
                      style={{ color: group.is_complete ? 'var(--success)' : 'var(--warning)' }}
                    >
                      {earned}/{required} TC
                    </span>
                  </div>
                  <div className="audit-progress-track">
                    <div
                      className="audit-progress-fill"
                      style={{
                        width: `${pct}%`,
                        background: group.is_complete ? 'var(--success)' : 'var(--warning)'
                      }}
                    />
                  </div>
                  {hasOptions && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '2px' }}>
                      {group.options.map((option, optionIndex) => (
                        <span key={option.group_id} className={option.is_complete ? 'badge badge-success' : 'badge badge-indigo'} style={{ fontSize: '0.68rem' }}>
                          Mô-đun {optionIndex + 1}: {option.earned_credits}/{option.required_credits}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Graduation Checklist & Forecast */}
        <div className="audit-right-stack">
          <div className="glass-panel audit-panel">
            <div className="audit-panel__head">
              <div className="audit-panel__title-wrap">
                <div className="audit-panel__icon" style={{ background: 'var(--hust-red-glow)', color: 'var(--brand-accent)' }}>
                  <GraduationCap size={19} />
                </div>
                <div>
                  <h3 className="audit-panel__title">Tiêu chuẩn xét tốt nghiệp</h3>
                  <span className="audit-panel__subtitle">Quy chế Đào tạo ĐH Bách Khoa Hà Nội</span>
                </div>
              </div>
              <span className="badge badge-hust" style={{ flexShrink: 0 }}>HUST Criteria</span>
            </div>

            <div className="audit-checklist">
              {/* Item 1: Credits */}
              <div
                className="audit-check-item audit-check-item--stacked"
                style={{
                  background: total_credits_accumulated >= total_credits_required ? 'rgba(16, 185, 129, 0.06)' : 'rgba(245, 158, 11, 0.06)',
                  border: total_credits_accumulated >= total_credits_required ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                  <div className="audit-check-item__body">
                    {total_credits_accumulated >= total_credits_required ? (
                      <CheckCircle2 size={18} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    ) : (
                      <Clock size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    )}
                    <div>
                      <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.88rem' }}>
                        Tích lũy tối thiểu {total_credits_required} Tín chỉ
                      </div>
                      <div style={{ fontSize: '0.79rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        Hiện tại: <strong style={{ color: 'var(--text-primary)' }}>{total_credits_accumulated} / {total_credits_required} TC</strong> ({completion_percentage}%)
                      </div>
                    </div>
                  </div>
                  <span className={total_credits_accumulated >= total_credits_required ? 'badge badge-success' : 'badge badge-warning'} style={{ fontSize: '0.7rem', flexShrink: 0 }}>
                    {total_credits_accumulated >= total_credits_required ? 'Đạt' : `Thiếu ${remaining_credits.toFixed(1)} TC`}
                  </span>
                </div>
                <div className="audit-progress-track" style={{ height: '6px', marginTop: '10px' }}>
                  <div
                    className="audit-progress-fill"
                    style={{
                      width: `${Math.min(100, completion_percentage)}%`,
                      background: total_credits_accumulated >= total_credits_required ? 'var(--success)' : 'var(--warning)'
                    }}
                  />
                </div>
              </div>

              {/* Item 2: Compulsory courses */}
              <div
                className="audit-check-item"
                style={{
                  background: unlearned_compulsory_courses.length === 0 ? 'rgba(16, 185, 129, 0.06)' : 'rgba(245, 158, 11, 0.06)',
                  border: unlearned_compulsory_courses.length === 0 ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)'
                }}
              >
                <div className="audit-check-item__body">
                  {unlearned_compulsory_courses.length === 0 ? (
                    <CheckCircle2 size={18} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  ) : (
                    <AlertTriangle size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  )}
                  <div>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.88rem' }}>
                      Hoàn thành toàn bộ môn bắt buộc
                    </div>
                    <div style={{ fontSize: '0.79rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {unlearned_compulsory_courses.length === 0 ? (
                        'Đã hoàn thành 100% học phần bắt buộc.'
                      ) : (
                        <span>Còn <strong style={{ color: 'var(--text-primary)' }}>{unlearned_compulsory_courses.length} môn bắt buộc</strong> ({compulsory_credits_missing.toFixed(1)} TC).</span>
                      )}
                    </div>
                  </div>
                </div>
                <span className={unlearned_compulsory_courses.length === 0 ? 'badge badge-success' : 'badge badge-warning'} style={{ fontSize: '0.7rem', flexShrink: 0 }}>
                  {unlearned_compulsory_courses.length === 0 ? 'Đạt' : `Còn ${unlearned_compulsory_courses.length} môn`}
                </span>
              </div>

              {/* Item 3: CPA >= 2.00 */}
              <div
                className="audit-check-item"
                style={{
                  background: cpa >= 2.0 ? 'rgba(16, 185, 129, 0.06)' : 'rgba(244, 63, 94, 0.06)',
                  border: cpa >= 2.0 ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(244, 63, 94, 0.25)'
                }}
              >
                <div className="audit-check-item__body">
                  <CheckCircle2 size={18} color={cpa >= 2.0 ? 'var(--success)' : 'var(--danger)'} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.88rem' }}>
                      Điểm trung bình tích lũy CPA ≥ 2.00
                    </div>
                    <div style={{ fontSize: '0.79rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Hiện tại: <strong style={{ color: cpa >= 2.0 ? 'var(--success)' : 'var(--danger)' }}>CPA {cpa.toFixed(2)}</strong>{' '}
                      {cpa >= 2.0 ? '(Đạt chuẩn học lực cử nhân).' : '(Chưa đạt mức tối thiểu 2.00).'}
                    </div>
                  </div>
                </div>
                <span className={cpa >= 2.0 ? 'badge badge-success' : 'badge badge-danger'} style={{ fontSize: '0.7rem', flexShrink: 0 }}>
                  {cpa >= 2.0 ? 'Đạt chuẩn' : 'Chưa đạt'}
                </span>
              </div>

              {/* Item 4: Non-credit requirements */}
              <div
                className="audit-check-item"
                style={{
                  background: 'rgba(245, 158, 11, 0.06)',
                  border: '1px solid rgba(245, 158, 11, 0.25)'
                }}
              >
                <div className="audit-check-item__body">
                  <AlertTriangle size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.88rem' }}>
                      GDTC, GDQP & Chuẩn tiếng Anh
                    </div>
                    <div style={{ fontSize: '0.79rem', color: 'var(--text-secondary)', marginTop: '3px', lineHeight: 1.45 }}>
                      {non_credit_requirements.map((item) => (
                        <div key={item.group_id}>
                          {item.name}:{' '}
                          {item.source === 'coursework'
                            ? `${item.status === 'completed' ? 'Đã hoàn thành học phần' : item.status === 'incomplete' ? 'Chưa đủ học phần' : 'Chưa có đủ điểm'} (${item.coursework?.passed_count || 0}/${item.coursework?.required_count || 0})`
                            : item.status === 'completed' && item.source === 'ctt'
                              ? 'Đã hoàn thành (đồng bộ CTT)'
                              : requirementLabels[item.status] || 'Chưa xác minh'}
                        </div>
                      ))}
                      <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>Đối chiếu hồ sơ chính thức; cập nhật khi nhập bảng điểm.</div>
                    </div>
                  </div>
                </div>
                <span className="badge badge-warning" style={{ fontSize: '0.7rem', flexShrink: 0 }}>
                  {non_credit_requirements.length > 0 && non_credit_requirements.every((item) => item.status === 'completed') ? 'Đã ghi nhận' : 'Cần đối chiếu'}
                </span>
              </div>
            </div>
          </div>

          {/* Graduation Roadmap Forecast Box */}
          <div className="glass-panel audit-forecast-box">
            <div className="audit-panel__icon" style={{ width: '38px', height: '38px', background: 'var(--hust-red-glow)', color: 'var(--brand-accent)' }}>
              <Calendar size={19} />
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                Dự báo Kế hoạch Tốt nghiệp
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '3px', lineHeight: '1.45' }}>
                Còn {remaining_credits.toFixed(1)} TC, {credit_limit.is_provisional ? 'hạn mức kế hoạch tạm thời' : 'hạn mức đăng ký'} {maxCreditsPerSemester} TC/kỳ.{' '}
                {credit_limit.is_provisional ? 'Nếu giữ hạn mức này, dự kiến' : 'Về mặt khối lượng, cần ít nhất'}{' '}
                <strong>{theoreticalMinSemesters} học kỳ</strong>; thời gian thực tế còn phụ thuộc điều kiện học phần và lịch mở lớp.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Full-Width Bottom Section: Compulsory Courses (2-col grid) + Elective Summary */}
      <div className="glass-panel audit-panel">
        <div className="audit-panel__head">
          <div className="audit-panel__title-wrap">
            <div className="audit-panel__icon" style={{ background: 'var(--warning-bg)', color: 'var(--warning)' }}>
              <AlertTriangle size={18} />
            </div>
            <div>
              <h3 className="audit-panel__title">
                Môn Bắt buộc Cốt lõi Còn lại ({unlearned_compulsory_courses.length})
              </h3>
              <span className="audit-panel__subtitle">
                Tổng cộng: {compulsory_credits_missing.toFixed(1)} Tín chỉ
              </span>
            </div>
          </div>
          <span className="badge badge-warning" style={{ flexShrink: 0 }}>Cần ưu tiên</span>
        </div>

        {unlearned_compulsory_courses.length === 0 ? (
          <div style={{
            padding: '22px',
            textAlign: 'center',
            color: 'var(--success)',
            background: 'var(--success-bg)',
            borderRadius: 'var(--radius-md)'
          }}>
            🎉 Chúc mừng! Bạn đã hoàn thành 100% các học phần bắt buộc trong CTĐT!
          </div>
        ) : (
          <>
            <div className="audit-course-grid">
              {displayedCompulsory.map((course) => (
                <div key={course.code} className="audit-course-card">
                  <div className="audit-course-card__info">
                    <div className="audit-course-card__title-row">
                      <span className="audit-course-code">{course.code}</span>
                      <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                        {course.name || 'Chưa có tên học phần'}
                      </strong>
                      {course.suggested_semester && (
                        <span className="badge badge-indigo" style={{ fontSize: '0.67rem', padding: '2px 8px' }}>
                          Kỳ {course.suggested_semester}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                      {course.category || 'Học phần bắt buộc trong công thức tốt nghiệp'}
                    </div>
                  </div>
                  <span className="badge badge-indigo" style={{ fontWeight: '700', flexShrink: 0 }}>{course.credits || 0} TC</span>
                </div>
              ))}
            </div>
            {hiddenCompulsoryCount > 0 && (
              <button
                type="button"
                className="audit-course-toggle"
                onClick={() => setShowAllCompulsory((prev) => !prev)}
              >
                {showAllCompulsory ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                <span>
                  {showAllCompulsory
                    ? 'Thu gọn danh sách'
                    : `Xem tất cả ${unlearned_compulsory_courses.length} môn (+${hiddenCompulsoryCount} môn nữa)`}
                </span>
              </button>
            )}
          </>
        )}
      </div>

      {/* 6. Elective Credits Summary Card */}
      <div className="glass-panel audit-panel">
        <div className="audit-panel__head" style={{ marginBottom: '10px' }}>
          <div className="audit-panel__title-wrap">
            <div className="audit-panel__icon" style={{ background: 'rgba(213, 19, 42, 0.12)', color: 'var(--brand-accent)' }}>
              <Layers size={18} />
            </div>
            <div>
              <h3 className="audit-panel__title">Tín chỉ Tự chọn Định hướng Còn thiếu</h3>
              <span className="audit-panel__subtitle">
                Cần tích lũy thêm: {elective_credits_missing.toFixed(1)} Tín chỉ
              </span>
            </div>
          </div>
          <span className="badge badge-indigo" style={{ flexShrink: 0 }}>{elective_credits_missing.toFixed(0)} TC</span>
        </div>

        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
          Bạn cần hoàn thành đúng các nhóm trong công thức tốt nghiệp{moduleCount ? `, trong đó chọn một trong ${moduleCount} mô-đun` : ''} và tích lũy đủ <strong>{total_credits_required} tín chỉ</strong>.
        </p>

        <div className="audit-elective-footer">
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {unlearned_elective_courses.length} môn tự chọn khả dụng trong CTĐT
          </span>
          <button
            type="button"
            onClick={() => onNavigateTab('chat')}
            className="btn-primary gemini-pill"
            style={{
              fontSize: '0.82rem',
              padding: '8px 18px',
              borderRadius: 'var(--radius-full)'
            }}
          >
            <span>Hỏi trợ lý chọn môn</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
