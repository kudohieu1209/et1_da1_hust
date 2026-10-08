import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  GraduationCap,
  ArrowRight,
  ShieldCheck,
  Clock,
  Sparkles,
  Layers,
  Calendar
} from 'lucide-react';

export default function AuditTab({ 
  auditData, 
  onNavigateTab, 
  onOpenImport, 
  onOpenProfileModal
}) {
  if (!auditData) {
    return (
      <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '60px 20px' }}>
        <div style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '8px' }}>Đang tải báo cáo tiến độ học tập...</div>
        <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Vui lòng đợi giây lát trong khi hệ thống đồng bộ dữ liệu CTĐT Bách Khoa.</div>
      </div>
    );
  }

  const {
    student_info = {},
    curriculum = {},
    cpa = 0,
    warning_level = 0,
    warning_description = 'Bình thường',
    credit_limit = {},
    total_credits_accumulated = 0,
    total_credits_required = 0,
    completion_percentage = 0,
    passed_count = 0,
    failed_count = 0,
    academic_classification = { rank: 'Trung bình', color: '#f59e0b', desc: '2.00 ≤ CPA < 2.50' },
    target_kha_advice = null,
    unlearned_compulsory_courses = [],
    unlearned_elective_courses = [],
    graduation_group_audit = [],
    non_credit_requirements = [],
    graduation_ready = false
  } = auditData;

  const remaining_credits = Math.max(0, total_credits_required - total_credits_accumulated);
  const compulsory_credits_missing = unlearned_compulsory_courses.reduce((sum, c) => sum + (c.credits || 0), 0);
  const elective_credits_missing = Math.max(0, remaining_credits - compulsory_credits_missing);
  const moduleRequirement = graduation_group_audit.find(item => item.type === 'ONE_OF_GROUPS');
  const moduleCount = moduleRequirement?.options?.length || 0;
  const maxCreditsPerSemester = Number(credit_limit.max || 24);
  const theoreticalMinSemesters = remaining_credits > 0
    ? Math.ceil(remaining_credits / Math.max(1, maxCreditsPerSemester))
    : 0;

  // SVG Circular progress
  const radius = 38;
  const strokeWidth = 7;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (completion_percentage / 100) * circumference;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', paddingBottom: '32px' }}>
      {/* If Fresh Account with 0 courses */}
      {passed_count === 0 && (
        <div style={{
          padding: '16px 20px',
          borderRadius: '14px',
          background: 'linear-gradient(135deg, rgba(200, 16, 46, 0.08), rgba(56, 189, 248, 0.08))',
          border: '1px solid rgba(200, 16, 46, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertTriangle size={24} color="#f59e0b" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '0.94rem' }}>
                Hồ sơ sinh viên chưa có môn học nào hoàn thành (0 / {total_credits_required} tín chỉ)
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Bạn có thể sao chép bảng điểm từ trang ctt.hust.edu.vn và dán vào đây để hệ thống tự động tính CPA, số tín chỉ tích lũy và kiểm tra điều kiện tốt nghiệp.
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {onOpenImport && (
              <button
                onClick={onOpenImport}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 14px',
                  borderRadius: '8px',
                  background: 'var(--accent-red)',
                  color: '#fff',
                  border: 'none',
                  fontWeight: '600',
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                <span>+ Dán bảng điểm CTT</span>
              </button>
            )}
            {onOpenProfileModal && (
              <button
                onClick={onOpenProfileModal}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                <span>Chọn hồ sơ mẫu</span>
              </button>
            )}
          </div>
        </div>
      )}
      {/* 1. Standardized Page Header */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span className="badge badge-hust">{curriculum.program_code || 'CTĐT'} • {curriculum.curriculum_version || '—'}</span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Nguồn CTĐT đã chuẩn hóa</span>
          </div>
          <h2 style={{ fontSize: '1.55rem', color: 'var(--text-primary)', margin: 0 }}>
            Tiến độ Học tập & Chuẩn Tốt nghiệp
          </h2>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Ngành {curriculum.name || student_info.program_name || '—'} ({curriculum.program_code || '—'}) • Sinh viên: <strong style={{ color: 'var(--text-primary)' }}>{student_info.student_name || '—'}</strong> (MSSV: {student_info.student_id || '—'})
          </p>
        </div>

        {/* Quick status pills on top right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div style={{
            padding: '6px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.82rem'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>Tích lũy: </span>
            <strong style={{ color: 'var(--text-primary)' }}>{total_credits_accumulated}/{total_credits_required} TC</strong>
          </div>
          <div style={{
            padding: '6px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.82rem'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>CPA: </span>
            <strong style={{ color: academic_classification.color || 'var(--warning)' }}>{cpa.toFixed(2)}</strong>
          </div>
        </div>
      </div>

      {/* 2. Top 4 Metric Bento Cards (Uniform Height & Balanced Whitespace) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '16px'
      }}>
        {/* Card 1: Credit Progress */}
        <div className="glass-panel" style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '175px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '700', letterSpacing: '0.04em' }}>
              TIẾN ĐỘ TÍN CHỈ
            </span>
            <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
              Gần cán đích
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', margin: '8px 0' }}>
            <div style={{ position: 'relative', width: '96px', height: '96px', flexShrink: 0 }}>
              <svg viewBox="0 0 96 96" style={{ transform: 'rotate(-90deg)', width: '96px', height: '96px', overflow: 'visible' }}>
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
                    <stop offset="0%" stopColor="#c8102e" />
                    <stop offset="100%" stopColor="#f43f5e" />
                  </linearGradient>
                </defs>
              </svg>
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <span style={{ fontSize: '1.15rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                  {completion_percentage}%
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                {total_credits_accumulated} / {total_credits_required}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Tín chỉ tích lũy
              </div>
              <div style={{ fontSize: '0.78rem', color: '#c8102e', fontWeight: '600', marginTop: '4px' }}>
                Còn thiếu {remaining_credits.toFixed(1)} TC
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Đã hoàn thành {completion_percentage}% khối lượng CTĐT
          </div>
        </div>

        {/* Card 2: CPA Status */}
        <div className="glass-panel" style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '175px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '700', letterSpacing: '0.04em' }}>
              ĐIỂM CPA HIỆN TẠI
            </span>
            <span className="badge" style={{
              background: `${academic_classification.color}1a`,
              color: academic_classification.color,
              border: `1px solid ${academic_classification.color}40`,
              fontSize: '0.7rem',
              fontWeight: '700'
            }}>
              Loại {academic_classification.rank}
            </span>
          </div>

          <div style={{ margin: '6px 0' }}>
            <div style={{
              fontSize: '2.1rem',
              fontWeight: '800',
              color: academic_classification.color || 'var(--warning)',
              lineHeight: '1.1'
            }}>
              {cpa.toFixed(2)}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Thang điểm 4.0 • {academic_classification.desc}
            </div>
          </div>

          {/* Mini Progress bar towards CPA 2.50 (Bằng Khá) */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', marginBottom: '4px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Chuẩn Bằng Khá (≥ 2.50)</span>
              <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{cpa.toFixed(2)} / 2.50</span>
            </div>
            <div style={{ width: '100%', height: '5px', background: 'var(--border-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{
                width: `${Math.min(100, (cpa / 2.5) * 100)}%`,
                height: '100%',
                background: cpa >= 2.5 ? 'var(--success)' : 'var(--warning)',
                borderRadius: '3px'
              }} />
            </div>
          </div>
        </div>

        {/* Card 3: Academic Standing */}
        <div className="glass-panel" style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '175px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '700', letterSpacing: '0.04em' }}>
              CẢNH BÁO HỌC TẬP
            </span>
            <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
              Mức {warning_level}
            </span>
          </div>

          <div style={{ margin: '6px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={24} color="var(--success)" />
              <span style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--success)' }}>
                {warning_description}
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Hồ sơ học tập an toàn, không có nguy cơ xử lý học vụ.
            </div>
          </div>

          <div style={{
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            padding: '6px 10px',
            background: 'var(--bg-surface)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)'
          }}>
            Hạn mức đăng ký: <strong style={{ color: 'var(--text-primary)' }}>Tối đa {credit_limit.max || 24} TC</strong> / kỳ chính
          </div>
        </div>

        {/* Card 4: Graduation Overview */}
        <div className="glass-panel" style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '175px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '700', letterSpacing: '0.04em' }}>
              XÉT TỐT NGHIỆP
            </span>
            <span className={graduation_ready ? "badge badge-success" : "badge badge-warning"} style={{ fontSize: '0.7rem' }}>
              {graduation_ready ? "Đủ điều kiện" : "Đang hoàn thiện"}
            </span>
          </div>

          <div style={{ margin: '6px 0' }}>
            <div style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)' }}>
              Đã qua <span style={{ color: 'var(--success)' }}>{passed_count} môn</span> • <span style={{ color: failed_count > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>Nợ {failed_count} môn</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Còn <strong style={{ color: 'var(--text-primary)' }}>{unlearned_compulsory_courses.length} môn bắt buộc</strong> ({compulsory_credits_missing.toFixed(0)} TC) và các nhóm tín chỉ chưa đủ.
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: 'var(--indigo)',
            fontWeight: '600'
          }}>
            <Calendar size={14} />
            <span>Ít nhất {theoreticalMinSemesters} học kỳ theo giới hạn tín chỉ</span>
          </div>
        </div>
      </div>

      {/* Credit groups from the versioned graduation formula */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '14px', flexWrap: 'wrap' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', margin: 0 }}>
              Tiến độ theo nhóm trong công thức tốt nghiệp
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              {curriculum.graduation_formula || 'Chưa có công thức CTĐT'}
            </p>
          </div>
          <span className="badge badge-indigo">{graduation_group_audit.length} thành phần</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '10px' }}>
          {graduation_group_audit.map((group, index) => (
            <div key={group.group_id || `choice-${index}`} style={{ padding: '12px', border: '1px solid var(--border-subtle)', borderRadius: '10px', background: 'var(--bg-surface)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                <strong style={{ color: 'var(--text-primary)', fontSize: '0.82rem' }}>{group.name}</strong>
                <span style={{ color: group.is_complete ? 'var(--success)' : 'var(--warning)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>
                  {group.earned_credits}/{group.required_credits} TC
                </span>
              </div>
              {group.options && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '9px' }}>
                  {group.options.map((option, optionIndex) => (
                    <span key={option.group_id} className={option.is_complete ? 'badge badge-success' : 'badge badge-indigo'} style={{ fontSize: '0.66rem' }}>
                      Mô-đun {optionIndex + 1}: {option.earned_credits}/{option.required_credits}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 3. AI Smart Advisor Banner (Horizontal Full-Width Banner) */}
      {cpa < 2.5 && target_kha_advice && (
        <div style={{
          padding: '16px 20px',
          borderRadius: 'var(--radius-lg)',
          background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(99, 102, 241, 0.08) 100%)',
          border: '1px solid rgba(14, 165, 233, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', flex: '1 1 500px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'rgba(14, 165, 233, 0.15)',
              color: '#0284c7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <Sparkles size={20} />
            </div>
            <div>
              <div style={{ fontSize: '0.92rem', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>Chiến lược Nâng hạng Bằng Khá (CPA ≥ 2.50) từ AI Advisor</span>
                <span className="badge badge-indigo" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>Khuyến nghị</span>
              </div>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.45', margin: 0 }}>
                Để nâng mức tốt nghiệp từ <strong>Trung bình ({cpa.toFixed(2)})</strong> lên <strong>Khá (≥ 2.50)</strong>, bạn cần đạt GPA trung bình ~<strong style={{ color: '#0284c7' }}>{target_kha_advice.gpa_needed_remaining}</strong> trong {target_kha_advice.remaining_credits} TC còn lại. 
                <span style={{ color: 'var(--text-primary)', fontWeight: '500' }}> Phương án tối ưu: </span> 
                Đăng ký học <strong>cải thiện 2 - 3 môn điểm C/D</strong> ở các kỳ tới để giảm tải áp lực GPA môn mới xuống mức an toàn (~3.0 - 3.2).
              </p>
            </div>
          </div>

        </div>
      )}

      {/* 4. Main 2-Column Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
        gap: '20px'
      }}>
        {/* Left Column: Breakdown of remaining credits */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Section 4A: Missing Compulsory Courses */}
          <div className="glass-panel" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'var(--warning-bg)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--warning)'
                }}>
                  <AlertTriangle size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', margin: 0 }}>
                    Môn Bắt buộc Cốt lõi Còn lại ({unlearned_compulsory_courses.length})
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Tổng cộng: {compulsory_credits_missing.toFixed(1)} Tín chỉ
                  </span>
                </div>
              </div>
              <span className="badge badge-warning">Cần ưu tiên</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {unlearned_compulsory_courses.length === 0 ? (
                <div style={{
                  padding: '24px',
                  textAlign: 'center',
                  color: 'var(--success)',
                  background: 'var(--success-bg)',
                  borderRadius: 'var(--radius-md)'
                }}>
                  🎉 Chúc mừng! Bạn đã hoàn thành 100% các học phần bắt buộc trong CTĐT!
                </div>
              ) : unlearned_compulsory_courses.map((course) => (
                  <div key={course.code} style={{
                    padding: '14px 16px',
                    background: 'var(--bg-card-hover)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{
                          fontWeight: '800',
                          color: '#0284c7',
                          fontFamily: 'monospace',
                          fontSize: '1rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: 'rgba(2, 132, 199, 0.1)'
                        }}>
                          {course.code}
                        </span>
                        <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                          {course.name || 'Chưa có tên học phần'}
                        </strong>
                        {course.suggested_semester && (
                          <span className="badge badge-indigo" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                            Kỳ gợi ý {course.suggested_semester}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                        {course.category || 'Học phần bắt buộc trong công thức tốt nghiệp'}
                      </div>
                    </div>
                    <span className="badge badge-indigo" style={{ fontWeight: '700' }}>{course.credits || 0} TC</span>
                  </div>
              ))}
            </div>
          </div>

          {/* Section 4B: Elective Credits Explanation */}
          <div className="glass-panel" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'rgba(99, 102, 241, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--indigo)'
                }}>
                  <Layers size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', margin: 0 }}>
                    Tín chỉ Tự chọn Định hướng Còn thiếu
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Cần tích lũy thêm: {elective_credits_missing.toFixed(1)} Tín chỉ
                  </span>
                </div>
              </div>
              <span className="badge badge-indigo">{elective_credits_missing.toFixed(0)} TC</span>
            </div>

            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
              Bạn cần hoàn thành đúng các nhóm trong công thức tốt nghiệp{moduleCount ? `, trong đó chọn một trong ${moduleCount} mô-đun` : ''} và tích lũy đủ <strong>{total_credits_required} tín chỉ</strong>.
            </p>

            <div style={{
              marginTop: '16px',
              paddingTop: '14px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px'
            }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {unlearned_elective_courses.length} môn tự chọn khả dụng trong CTĐT
              </span>
              <button
                onClick={() => onNavigateTab('recommend')}
                className="btn-primary"
                style={{
                  fontSize: '0.82rem',
                  padding: '7px 14px',
                  borderRadius: '8px'
                }}
              >
                <span>Xem Gợi ý chọn môn</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Graduation Checklist & Criteria */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-panel" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'var(--hust-red-glow)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--hust-red)'
                }}>
                  <GraduationCap size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', margin: 0 }}>
                    Tiêu chuẩn xét tốt nghiệp theo chương trình đào tạo
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Quy chế Đào tạo Đại học Bách Khoa Hà Nội
                  </span>
                </div>
              </div>
              <span className="badge badge-hust">HUST Criteria</span>
            </div>

            {/* Checklist Items with Proper Semantic Icons & Visual Styles */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Item 1: Credits requirement (Pending) */}
              <div style={{
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                background: total_credits_accumulated >= total_credits_required ? 'rgba(16, 185, 129, 0.06)' : 'rgba(245, 158, 11, 0.06)',
                border: total_credits_accumulated >= total_credits_required ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    {total_credits_accumulated >= total_credits_required ? (
                      <CheckCircle2 size={18} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    ) : (
                      <Clock size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    )}
                    <div>
                      <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                        Tích lũy tối thiểu {total_credits_required} Tín chỉ
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        Hiện tại: <strong style={{ color: 'var(--text-primary)' }}>{total_credits_accumulated} / {total_credits_required} TC</strong> ({completion_percentage}%)
                      </div>
                    </div>
                  </div>
                  <span className={total_credits_accumulated >= total_credits_required ? "badge badge-success" : "badge badge-warning"} style={{ fontSize: '0.7rem' }}>
                    {total_credits_accumulated >= total_credits_required ? "Đạt" : `Thiếu ${remaining_credits.toFixed(1)} TC`}
                  </span>
                </div>
                {/* Progress bar inside */}
                <div style={{ width: '100%', height: '5px', background: 'var(--border-subtle)', borderRadius: '3px', marginTop: '10px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, completion_percentage)}%`,
                    height: '100%',
                    background: total_credits_accumulated >= total_credits_required ? 'var(--success)' : 'var(--warning)',
                    borderRadius: '3px'
                  }} />
                </div>
              </div>

              {/* Item 2: Compulsory courses (Pending) */}
              <div style={{
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                background: unlearned_compulsory_courses.length === 0 ? 'rgba(16, 185, 129, 0.06)' : 'rgba(245, 158, 11, 0.06)',
                border: unlearned_compulsory_courses.length === 0 ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  {unlearned_compulsory_courses.length === 0 ? (
                    <CheckCircle2 size={18} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  ) : (
                    <AlertTriangle size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  )}
                  <div>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                      Hoàn thành toàn bộ môn bắt buộc trong CTĐT
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {unlearned_compulsory_courses.length === 0 ? (
                        'Đã hoàn thành 100% học phần bắt buộc.'
                      ) : (
                        <span>Còn <strong style={{ color: 'var(--text-primary)' }}>{unlearned_compulsory_courses.length} môn bắt buộc</strong> ({compulsory_credits_missing.toFixed(1)} TC).</span>
                      )}
                    </div>
                  </div>
                </div>
                <span className={unlearned_compulsory_courses.length === 0 ? "badge badge-success" : "badge badge-warning"} style={{ fontSize: '0.7rem' }}>
                  {unlearned_compulsory_courses.length === 0 ? "Đạt" : `Còn ${unlearned_compulsory_courses.length} môn`}
                </span>
              </div>

              {/* Item 3: CPA requirement (Passed) */}
              <div style={{
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                background: cpa >= 2.0 ? 'rgba(16, 185, 129, 0.06)' : 'rgba(244, 63, 94, 0.06)',
                border: cpa >= 2.0 ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(244, 63, 94, 0.25)',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <CheckCircle2 size={18} color={cpa >= 2.0 ? 'var(--success)' : 'var(--danger)'} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                      Điểm trung bình tích lũy CPA ≥ 2.00
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Hiện tại: <strong style={{ color: 'var(--success)' }}>CPA {cpa.toFixed(2)}</strong> (Đạt chuẩn học lực cử nhân Bách Khoa).
                    </div>
                  </div>
                </div>
                <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                  Đạt chuẩn
                </span>
              </div>

              {/* Item 4: non-credit requirements need separate evidence */}
              <div style={{
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(245, 158, 11, 0.06)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <AlertTriangle size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                      Chứng chỉ GDTC, GDQP & Chuẩn tiếng Anh
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {non_credit_requirements.length} nhóm không tính tín chỉ; cần đối chiếu chứng chỉ/chuẩn đầu ra trong hồ sơ chính thức.
                    </div>
                  </div>
                </div>
                <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                  Chưa xác minh
                </span>
              </div>
            </div>
          </div>

          {/* Graduation Roadmap Forecast Box */}
          <div className="glass-panel" style={{
            padding: '18px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            background: 'var(--bg-card)'
          }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'var(--hust-red-glow)',
              color: 'var(--hust-red)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <Calendar size={20} />
            </div>
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                Dự báo Kế hoạch Tốt nghiệp
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px', lineHeight: '1.4' }}>
                Còn {remaining_credits.toFixed(1)} TC, hạn mức hiện tại {maxCreditsPerSemester} TC/kỳ. Về mặt khối lượng, cần ít nhất <strong>{theoreticalMinSemesters} học kỳ</strong>; thời gian thực tế còn phụ thuộc điều kiện học phần và lịch mở lớp.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
