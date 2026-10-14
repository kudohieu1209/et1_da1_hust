import React from 'react';
import BrandLogo from './BrandLogo';
import { Sparkles, CheckCircle2, Award } from 'lucide-react';

export default function Header({ studentProfile, auditData, activeTab, setActiveTab }) {
  const studentInfo = studentProfile?.info || {};
  const cpa = auditData?.cpa ?? 0;
  const accumulatedCredits = auditData?.total_credits_accumulated ?? 0;
  const requiredCredits = auditData?.total_credits_required ?? 0;
  const completionPercentage = auditData?.completion_percentage ?? 0;
  const curriculum = auditData?.curriculum || {};

  const navItems = [
    { id: 'chat', label: 'Trợ lý AI', icon: Sparkles },
    { id: 'audit', label: 'Tiến độ học tập', icon: Award },
    { id: 'recommend', label: 'Gợi ý chọn môn', icon: CheckCircle2 },
  ];

  return (
    <header style={{
      borderBottom: '1px solid var(--border-subtle)',
      background: 'var(--bg-surface)',
      backdropFilter: 'blur(20px)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        {/* Logo & Major */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <BrandLogo size={46} decorative />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                HUST Advisor
              </h1>
              <span className="badge badge-hust">
                {curriculum.program_code || '—'} • {curriculum.curriculum_version || 'chưa chọn CTĐT'}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginLeft: '6px' }}>
                <span className="pulse-dot"></span>
                <span style={{ fontSize: '0.75rem', color: 'var(--success)', fontWeight: '600' }}>AI Online</span>
              </div>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Hệ thống Tư vấn Môn học & Quản lý Tiến độ Đào tạo Bách Khoa
            </p>
          </div>
        </div>

        {/* Student Profile Snapshot */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '8px 16px'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                {studentInfo.student_name || 'Mai Duy Hiếu'}
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                ({studentInfo.student_id || '20220001'})
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '2px', fontSize: '0.78rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                CPA: <strong style={{ color: 'var(--brand-accent)' }}>{cpa.toFixed(2)}</strong>
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>•</span>
              <span style={{ color: 'var(--text-secondary)' }}>
                Tích lũy: <strong style={{ color: 'var(--success)' }}>{accumulatedCredits}/{requiredCredits} TC</strong> ({completionPercentage}%)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '0 24px',
        display: 'flex',
        gap: '4px',
        overflowX: 'auto'
      }}>
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                background: 'transparent',
                border: 'none',
                borderBottom: isActive ? '3px solid var(--hust-red)' : '3px solid transparent',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: isActive ? '700' : '500',
                fontSize: '0.92rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap'
              }}
            >
              <Icon size={17} color={isActive ? 'var(--brand-accent)' : 'var(--text-muted)'} />
              {item.label}
            </button>
          );
        })}
      </div>
    </header>
  );
}
