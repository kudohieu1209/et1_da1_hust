import React, { useState, useEffect, useRef } from 'react';
import { 
  X, Moon, Sun, Globe, User, BookOpen, Database, Settings as SettingsIcon, 
  Check, RotateCcw, ShieldCheck, Sparkles, RefreshCw, Key, ExternalLink, 
  LogIn, Camera, Upload, Trash2, Save, UserCheck, CheckCircle2 
} from 'lucide-react';

export default function SettingsModal({ 
  isOpen, 
  onClose, 
  theme, 
  setTheme, 
  language, 
  setLanguage,
  studentProfile,
  setStudentProfile,
  auditData,
  setAuditData,
  onResetChat,
  onOpenAuthModal,
  onShowToast
}) {
  const [activeTab, setActiveTab] = useState('general');
  const [ragStatus, setRagStatus] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);

  const fileInputRef = useRef(null);
  const studentInfo = studentProfile?.info || {};

  const [formName, setFormName] = useState(studentInfo.student_name || 'Mai Duy Hiếu');
  const [formStudentId, setFormStudentId] = useState(studentInfo.student_id || '20220001');
  const [formClass, setFormClass] = useState(studentInfo.class_name || 'Điện tử 02 - K67');
  const [formProgram, setFormProgram] = useState(studentInfo.program_name || 'Kỹ thuật Điện tử - Viễn thông 2022');
  const [formProgramId, setFormProgramId] = useState(studentInfo.program_id || '1654');
  const [formCurriculumVersion, setFormCurriculumVersion] = useState(studentInfo.curriculum_version || '2022');
  const [formAvatarUrl, setFormAvatarUrl] = useState(studentInfo.avatar_url || '');
  const [formAvatarEmoji, setFormAvatarEmoji] = useState(studentInfo.avatar_emoji || '');
  const [formAvatarGradient, setFormAvatarGradient] = useState(studentInfo.avatar_gradient || 'linear-gradient(135deg, #6366f1, #38bdf8)');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);

  useEffect(() => {
    if (studentProfile?.info) {
      const info = studentProfile.info;
      setFormName(info.student_name || 'Mai Duy Hiếu');
      setFormStudentId(info.student_id || '20220001');
      setFormClass(info.class_name || 'Điện tử 02 - K67');
      setFormProgram(info.program_name || 'Kỹ thuật Điện tử - Viễn thông 2022');
      setFormProgramId(info.program_id || '1654');
      setFormCurriculumVersion(info.curriculum_version || '2022');
      setFormAvatarUrl(info.avatar_url || '');
      setFormAvatarEmoji(info.avatar_emoji || '');
      setFormAvatarGradient(info.avatar_gradient || 'linear-gradient(135deg, #6366f1, #38bdf8)');
    }
  }, [studentProfile, isOpen]);

  const avatarGradients = [
    { id: 'indigo', name: 'Lam tím', value: 'linear-gradient(135deg, #6366f1, #38bdf8)' },
    { id: 'hust', name: 'Đỏ Bách Khoa', value: 'linear-gradient(135deg, #c8102e, #990000)' },
    { id: 'emerald', name: 'Lục bảo', value: 'linear-gradient(135deg, #10b981, #06b6d4)' },
    { id: 'purple', name: 'Tím Cyber', value: 'linear-gradient(135deg, #8b5cf6, #ec4899)' },
    { id: 'amber', name: 'Cam hổ phách', value: 'linear-gradient(135deg, #f59e0b, #ef4444)' },
    { id: 'midnight', name: 'Đêm sâu', value: 'linear-gradient(135deg, #334155, #0f172a)' }
  ];

  const handleAvatarFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      alert(language === 'vi' ? 'Vui lòng chọn ảnh dung lượng dưới 2MB' : 'Please select an image under 2MB');
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      setFormAvatarUrl(event.target.result);
      setFormAvatarEmoji('');
    };
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async (e) => {
    if (e) e.preventDefault();
    setIsSavingProfile(true);
    try {
      const payload = {
        student_name: formName.trim(),
        student_id: formStudentId.trim(),
        class_name: formClass.trim(),
        program_name: formProgram.trim(),
        program_id: formProgramId.trim(),
        curriculum_version: formCurriculumVersion.trim(),
        avatar_url: formAvatarUrl,
        avatar_emoji: formAvatarEmoji,
        avatar_gradient: formAvatarGradient
      };
      const res = await fetch('http://localhost:8000/api/student/profile/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        if (setStudentProfile && data.profile) {
          setStudentProfile(data.profile);
        }
        if (setAuditData && data.audit) {
          setAuditData(data.audit);
        }
        setProfileSaved(true);
        if (onShowToast) {
          onShowToast(language === 'vi' ? 'Đã lưu thông tin hồ sơ thành công!' : 'Profile updated successfully!');
        }
        setTimeout(() => setProfileSaved(false), 2500);
      } else {
        const error = await res.json();
        onShowToast?.(error.detail || 'Không tìm thấy CTĐT phù hợp với hồ sơ.');
      }
    } catch (err) {
      console.error('Lỗi cập nhật profile:', err);
    } finally {
      setIsSavingProfile(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchRagStatus();
    }
  }, [isOpen]);

  const fetchRagStatus = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/rag/status');
      if (res.ok) {
        const data = await res.json();
        setRagStatus(data);
      }
    } catch (e) {
      console.warn('Lỗi lấy RAG status:', e);
    }
  };

  const handleSyncKnowledge = async () => {
    setIsSyncing(true);
    try {
      const res = await fetch('http://localhost:8000/api/rag/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true })
      });
      if (res.ok) {
        await fetchRagStatus();
      }
    } catch (e) {
      console.error('Lỗi sync RAG:', e);
    } finally {
      setIsSyncing(false);
    }
  };

  if (!isOpen) return null;

  const cpa = auditData?.cpa ?? 0;
  const accumulatedCredits = auditData?.total_credits_accumulated ?? 0;
  const requiredCredits = auditData?.total_credits_required ?? 0;

  return (
    <div className="apple-modal-backdrop" onClick={onClose} style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="apple-modal-window" onClick={e => e.stopPropagation()} style={{
        width: '100%',
        maxWidth: '680px',
        background: 'var(--bg-surface)',
        borderRadius: '18px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SettingsIcon size={18} color="#c8102e" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
              {language === 'vi' ? 'Cài đặt' : 'Settings'}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body: Left Tab Nav & Right Content */}
        <div style={{ display: 'flex', minHeight: '380px' }}>
          {/* Sub-nav Left */}
          <div style={{
            width: '200px',
            borderRight: '1px solid var(--border-subtle)',
            padding: '12px 10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            background: 'var(--sidebar-footer-bg)'
          }}>
            <button
              onClick={() => setActiveTab('general')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: 'none',
                background: activeTab === 'general' ? 'var(--sidebar-hover)' : 'transparent',
                color: activeTab === 'general' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'general' ? '700' : '500',
                fontSize: '0.85rem',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <SettingsIcon size={16} />
              <span>{language === 'vi' ? 'Chung' : 'General'}</span>
            </button>

            <button
              onClick={() => setActiveTab('profile')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: 'none',
                background: activeTab === 'profile' ? 'var(--sidebar-hover)' : 'transparent',
                color: activeTab === 'profile' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'profile' ? '700' : '500',
                fontSize: '0.85rem',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <User size={16} />
              <span>{language === 'vi' ? 'Tài khoản & Hồ sơ' : 'Account & Profile'}</span>
            </button>

            <button
              onClick={() => setActiveTab('system')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: 'none',
                background: activeTab === 'system' ? 'var(--sidebar-hover)' : 'transparent',
                color: activeTab === 'system' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'system' ? '700' : '500',
                fontSize: '0.85rem',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <Database size={16} />
              <span>{language === 'vi' ? 'Hệ thống CTĐT' : 'Curriculum System'}</span>
            </button>

            <button
              onClick={() => setActiveTab('rag')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: 'none',
                background: activeTab === 'rag' ? 'var(--sidebar-hover)' : 'transparent',
                color: activeTab === 'rag' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'rag' ? '700' : '500',
                fontSize: '0.85rem',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <BookOpen size={16} />
              <span>{language === 'vi' ? 'Tri thức & Quy chế' : 'Regulations & Knowledge'}</span>
            </button>
          </div>

          {/* Right Content Panel */}
          <div style={{ flex: 1, padding: '24px 28px', overflowY: 'auto' }}>
            {/* TAB 1: GENERAL (Theme & Language) */}
            {activeTab === 'general' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
                {/* Theme Setting */}
                <div>
                  <label style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
                    {language === 'vi' ? 'Chủ đề giao diện' : 'Theme'}
                  </label>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                    {language === 'vi' ? 'Tùy chỉnh chế độ hiển thị màu sắc của ứng dụng.' : 'Choose your preferred visual theme.'}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <button
                      onClick={() => setTheme('dark')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        padding: '12px',
                        borderRadius: '10px',
                        border: theme === 'dark' ? '2px solid #c8102e' : '1px solid var(--border-subtle)',
                        background: theme === 'dark' ? 'rgba(200, 16, 46, 0.12)' : 'var(--bg-card)',
                        color: theme === 'dark' ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: '700',
                        fontSize: '0.85rem',
                        cursor: 'pointer'
                      }}
                    >
                      <Moon size={16} color={theme === 'dark' ? '#c8102e' : 'inherit'} />
                      <span>{language === 'vi' ? 'Tối' : 'Dark'}</span>
                      {theme === 'dark' && <Check size={14} color="#c8102e" />}
                    </button>

                    <button
                      onClick={() => setTheme('light')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        padding: '12px',
                        borderRadius: '10px',
                        border: theme === 'light' ? '2px solid #c8102e' : '1px solid var(--border-subtle)',
                        background: theme === 'light' ? 'rgba(200, 16, 46, 0.12)' : 'var(--bg-card)',
                        color: theme === 'light' ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: '700',
                        fontSize: '0.85rem',
                        cursor: 'pointer'
                      }}
                    >
                      <Sun size={16} color={theme === 'light' ? '#f59e0b' : 'inherit'} />
                      <span>{language === 'vi' ? 'Sáng' : 'Light'}</span>
                      {theme === 'light' && <Check size={14} color="#c8102e" />}
                    </button>
                  </div>
                </div>

                <div style={{ height: '1px', background: 'var(--border-subtle)' }} />

                {/* Language Setting */}
                <div>
                  <label style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
                    {language === 'vi' ? 'Ngôn ngữ' : 'Language'}
                  </label>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                    {language === 'vi' ? 'Chọn ngôn ngữ hiển thị giao diện và hội thoại.' : 'Select application language.'}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <button
                      onClick={() => setLanguage('vi')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        padding: '12px',
                        borderRadius: '10px',
                        border: language === 'vi' ? '2px solid #0284c7' : '1px solid var(--border-subtle)',
                        background: language === 'vi' ? 'rgba(14, 165, 233, 0.12)' : 'var(--bg-card)',
                        color: language === 'vi' ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: '700',
                        fontSize: '0.85rem',
                        cursor: 'pointer'
                      }}
                    >
                      <Globe size={16} color="#0284c7" />
                      <span>Tiếng Việt</span>
                      {language === 'vi' && <Check size={14} color="#0284c7" />}
                    </button>

                    <button
                      onClick={() => setLanguage('en')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        padding: '12px',
                        borderRadius: '10px',
                        border: language === 'en' ? '2px solid #0284c7' : '1px solid var(--border-subtle)',
                        background: language === 'en' ? 'rgba(14, 165, 233, 0.12)' : 'var(--bg-card)',
                        color: language === 'en' ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: '700',
                        fontSize: '0.85rem',
                        cursor: 'pointer'
                      }}
                    >
                      <Globe size={16} color="#0284c7" />
                      <span>English</span>
                      {language === 'en' && <Check size={14} color="#0284c7" />}
                    </button>
                  </div>
                </div>

                <div style={{ height: '1px', background: 'var(--border-subtle)' }} />

                {/* Account & Login Section */}
                <div>
                  <label style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
                    {language === 'vi' ? 'Tài khoản người dùng' : 'User Account'}
                  </label>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between', 
                    padding: '12px 14px', 
                    borderRadius: '10px', 
                    background: 'var(--bg-card)', 
                    border: '1px solid var(--border-subtle)' 
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #6366f1, #38bdf8)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontWeight: '700',
                        fontSize: '0.88rem'
                      }}>
                        {(studentInfo.student_name || 'H').charAt(0)}
                      </div>
                      <div>
                        <div style={{ fontSize: '0.86rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                          {studentInfo.student_name || 'Nguyễn Văn Hiếu'}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          MSSV: {studentInfo.student_id || '20220001'}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        onClose();
                        if (onOpenAuthModal) onOpenAuthModal();
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '7px 14px',
                        borderRadius: '8px',
                        border: '1px solid rgba(200, 16, 46, 0.35)',
                        background: 'rgba(200, 16, 46, 0.08)',
                        color: '#c8102e',
                        fontSize: '0.82rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(200, 16, 46, 0.15)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'rgba(200, 16, 46, 0.08)'}
                    >
                      <LogIn size={15} />
                      <span>{language === 'vi' ? 'Đăng nhập / Đổi tài khoản' : 'Login / Switch Account'}</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: STUDENT PROFILE & EDIT */}
            {activeTab === 'profile' && (
              <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                <div>
                  <h4 style={{ fontSize: '0.98rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 4px' }}>
                    {language === 'vi' ? 'Hồ sơ Sinh viên' : 'Student Profile'}
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                    {language === 'vi' 
                      ? 'Chỉnh sửa ảnh đại diện, họ tên, lớp và thông tin đào tạo của bạn.' 
                      : 'Customize your avatar, full name, cohort class, and academic details.'}
                  </p>
                </div>

                {/* 1. Avatar Customization Section */}
                <div style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px'
                }}>
                  <div style={{ fontSize: '0.84rem', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Camera size={15} color="#c8102e" />
                    <span>{language === 'vi' ? 'Ảnh đại diện' : 'Profile Avatar'}</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                    {/* Live Avatar Preview */}
                    <div style={{
                      width: '64px',
                      height: '64px',
                      borderRadius: '50%',
                      background: formAvatarGradient,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      fontWeight: '800',
                      fontSize: formAvatarEmoji ? '1.8rem' : '1.5rem',
                      overflow: 'hidden',
                      boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
                      border: '2px solid rgba(255,255,255,0.2)',
                      flexShrink: 0
                    }}>
                      {formAvatarUrl ? (
                        <img src={formAvatarUrl} alt="Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      ) : (
                        formAvatarEmoji || (formName || 'H').charAt(0)
                      )}
                    </div>

                    {/* Upload / Remove Actions */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <input 
                        type="file" 
                        ref={fileInputRef} 
                        accept="image/*" 
                        onChange={handleAvatarFileUpload} 
                        style={{ display: 'none' }} 
                      />
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '7px 14px',
                            borderRadius: '8px',
                            border: '1px solid var(--border-subtle)',
                            background: 'var(--bg-surface)',
                            color: 'var(--text-primary)',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer'
                          }}
                        >
                          <Upload size={14} />
                          <span>{language === 'vi' ? 'Tải ảnh lên' : 'Upload photo'}</span>
                        </button>

                        {formAvatarUrl && (
                          <button
                            type="button"
                            onClick={() => {
                              setFormAvatarUrl('');
                            }}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '7px 12px',
                              borderRadius: '8px',
                              border: '1px solid rgba(244, 63, 94, 0.3)',
                              background: 'rgba(244, 63, 94, 0.08)',
                              color: 'var(--danger)',
                              fontSize: '0.8rem',
                              fontWeight: '600',
                              cursor: 'pointer'
                            }}
                          >
                            <Trash2 size={13} />
                            <span>{language === 'vi' ? 'Dùng chữ cái đầu' : 'Use initials'}</span>
                          </button>
                        )}
                      </div>
                      <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                        {language === 'vi' ? 'Hỗ trợ định dạng JPG, PNG (dung lượng tối đa 2MB).' : 'Supports JPG, PNG (max 2MB).'}
                      </span>
                    </div>
                  </div>

                  {/* Preset Gradients Picker */}
                  <div>
                    <div style={{ fontSize: '0.76rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                      {language === 'vi' ? 'Màu nền gradient:' : 'Background gradient:'}
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {avatarGradients.map((g) => (
                        <button
                          key={g.id}
                          type="button"
                          onClick={() => setFormAvatarGradient(g.value)}
                          title={g.name}
                          style={{
                            width: '26px',
                            height: '26px',
                            borderRadius: '50%',
                            background: g.value,
                            border: formAvatarGradient === g.value ? '2px solid #fff' : '2px solid transparent',
                            outline: formAvatarGradient === g.value ? '2px solid #c8102e' : 'none',
                            cursor: 'pointer',
                            boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* 2. Personal & Academic Fields */}
                <div style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px'
                }}>
                  <div style={{ fontSize: '0.84rem', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <User size={15} color="#0284c7" />
                    <span>{language === 'vi' ? 'Thông tin cá nhân & Đào tạo' : 'Personal & Academic Details'}</span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                        {language === 'vi' ? 'Họ và tên sinh viên' : 'Full name'}
                      </label>
                      <input 
                        type="text"
                        value={formName}
                        onChange={e => setFormName(e.target.value)}
                        placeholder="VD: Mai Duy Hiếu"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-surface)',
                          color: 'var(--text-primary)',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                        {language === 'vi' ? 'Mã số sinh viên (MSSV)' : 'Student ID'}
                      </label>
                      <input 
                        type="text"
                        value={formStudentId}
                        onChange={e => setFormStudentId(e.target.value)}
                        placeholder="VD: 20220001"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-surface)',
                          color: 'var(--text-primary)',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                        {language === 'vi' ? 'Lớp sinh viên / Khóa' : 'Class / Cohort'}
                      </label>
                      <input 
                        type="text"
                        value={formClass}
                        onChange={e => setFormClass(e.target.value)}
                        placeholder="VD: Điện tử 02 - K67"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-surface)',
                          color: 'var(--text-primary)',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                        {language === 'vi' ? 'Mã chương trình (CTĐT)' : 'Program Code'}
                      </label>
                      <input 
                        type="text"
                        value={formProgramId}
                        onChange={e => setFormProgramId(e.target.value)}
                        placeholder="VD: 1654"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-surface)',
                          color: 'var(--text-primary)',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                        {language === 'vi' ? 'Phiên bản CTĐT' : 'Curriculum Version'}
                      </label>
                      <input
                        type="text"
                        value={formCurriculumVersion}
                        onChange={e => setFormCurriculumVersion(e.target.value)}
                        placeholder="VD: 2022"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-surface)',
                          color: 'var(--text-primary)',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                      {language === 'vi' ? 'Chương trình đào tạo' : 'Program Name'}
                    </label>
                    <input 
                      type="text"
                      value={formProgram}
                      onChange={e => setFormProgram(e.target.value)}
                      placeholder="VD: Kỹ thuật Điện tử - Viễn thông 2022"
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid var(--border-subtle)',
                        background: 'var(--bg-surface)',
                        color: 'var(--text-primary)',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>
                </div>

                {/* 3. Readonly Academic Highlights */}
                <div style={{
                  background: 'rgba(200, 16, 46, 0.05)',
                  border: '1px solid rgba(200, 16, 46, 0.2)',
                  borderRadius: '12px',
                  padding: '12px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.82rem',
                  flexWrap: 'wrap',
                  gap: '8px'
                }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>CPA tích lũy: </span>
                    <strong style={{ color: '#f59e0b' }}>{cpa.toFixed(2)}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Tín chỉ: </span>
                    <strong style={{ color: 'var(--success)' }}>{accumulatedCredits} / {requiredCredits} TC</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Cảnh báo: </span>
                    <strong style={{ color: '#0284c7' }}>M0 (Bình thường)</strong>
                  </div>
                </div>

                {/* 4. Action Buttons */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '4px' }}>
                  <button
                    type="submit"
                    disabled={isSavingProfile}
                    style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      padding: '11px 18px',
                      borderRadius: '10px',
                      border: 'none',
                      background: profileSaved ? '#16a34a' : 'linear-gradient(135deg, #c8102e, #a855f7)',
                      color: '#fff',
                      fontWeight: '700',
                      fontSize: '0.86rem',
                      cursor: isSavingProfile ? 'not-allowed' : 'pointer',
                      boxShadow: '0 2px 10px rgba(200, 16, 46, 0.3)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {profileSaved ? <Check size={16} /> : <Save size={16} />}
                    <span>
                      {profileSaved 
                        ? (language === 'vi' ? 'Đã lưu thành công!' : 'Saved successfully!') 
                        : (isSavingProfile 
                            ? (language === 'vi' ? 'Đang lưu...' : 'Saving...') 
                            : (language === 'vi' ? 'Lưu thay đổi hồ sơ' : 'Save Profile Changes'))}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      if (onOpenAuthModal) onOpenAuthModal();
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '11px 16px',
                      borderRadius: '10px',
                      border: '1px solid rgba(200, 16, 46, 0.35)',
                      background: 'rgba(200, 16, 46, 0.08)',
                      color: '#c8102e',
                      fontSize: '0.82rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      whiteSpace: 'nowrap'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(200, 16, 46, 0.15)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(200, 16, 46, 0.08)'}
                  >
                    <LogIn size={15} />
                    <span>{language === 'vi' ? 'Đổi tài khoản' : 'Switch Account'}</span>
                  </button>
                </div>
              </form>
            )}

            {/* TAB 3: ACADEMIC SYSTEM & DATA */}
            {activeTab === 'system' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{
                  background: 'rgba(200, 16, 46, 0.08)',
                  border: '1px solid rgba(200, 16, 46, 0.25)',
                  borderRadius: '12px',
                  padding: '14px',
                  fontSize: '0.84rem',
                  lineHeight: '1.5'
                }}>
                  <div style={{ fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ShieldCheck size={16} color="#c8102e" />
                    Cơ sở dữ liệu Đào tạo Bách Khoa
                  </div>
                  <div style={{ color: 'var(--text-secondary)' }}>
                    Phạm vi dữ liệu thử nghiệm hiện tại gồm <strong>117 học phần</strong> của một chương trình đào tạo và <strong>446 quy tắc tiên quyết</strong> được chuẩn hóa từ cổng đào tạo CTT Bách Khoa.
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button
                    onClick={() => {
                      if (onResetChat) onResetChat();
                      onClose();
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.84rem',
                      cursor: 'pointer'
                    }}
                  >
                    <RotateCcw size={15} color="#0284c7" />
                    <span>{language === 'vi' ? 'Làm mới phiên trò chuyện' : 'Reset Chat'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* TAB 4: AI & RAG KNOWLEDGE BASE */}
            {/* TAB 4: KNOWLEDGE BASE & REGULATIONS */}
            {activeTab === 'rag' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 6px' }}>
                    {language === 'vi' ? 'Cơ sở Tri thức & Động cơ Cố vấn HUST' : 'HUST Knowledge Base & Advisor Engine'}
                  </h4>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: 0 }}>
                    {language === 'vi' 
                      ? 'Hệ thống tự động tra cứu và đối chiếu các văn bản quy chế, chương trình đào tạo và đề cương chi tiết chính thức của Đại học Bách Khoa Hà Nội.' 
                      : 'The system automatically retrieves and cross-references official HUST regulations, curricula, and syllabi.'}
                  </p>
                </div>

                {/* AI Engine Status Card (Server-managed, no user key needed) */}
                <div style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '10px',
                      background: 'rgba(200, 16, 46, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#c8102e',
                      flexShrink: 0
                    }}>
                      <Sparkles size={20} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        Động cơ AI Cố vấn Học tập HUST
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        Xử lý trực tiếp từ máy chủ hệ thống • Tự động cá nhân hóa theo tiến độ sinh viên
                      </div>
                    </div>
                  </div>

                  <span style={{
                    fontSize: '0.75rem',
                    color: '#16a34a',
                    background: 'rgba(22, 163, 74, 0.12)',
                    border: '1px solid rgba(22, 163, 74, 0.25)',
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    flexShrink: 0
                  }}>
                    <Check size={13} /> Sẵn sàng hoạt động
                  </span>
                </div>

                {/* Official Documents & Vector Database Status */}
                <div style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <BookOpen size={16} color="#c8102e" />
                      <span style={{ fontSize: '0.86rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        Các Văn bản Quy chế Đào tạo Đang Áp dụng
                      </span>
                    </div>
                    <button
                      onClick={handleSyncKnowledge}
                      disabled={isSyncing}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-subtle)',
                        background: 'var(--bg-surface)',
                        color: 'var(--text-secondary)',
                        fontSize: '0.76rem',
                        fontWeight: '600',
                        cursor: isSyncing ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <RefreshCw size={12} className={isSyncing ? 'spin' : ''} />
                      {isSyncing ? 'Đang cập nhật...' : 'Đồng bộ lại'}
                    </button>
                  </div>

                  {/* 3 Official Documents List - Clean names, no .md */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px'
                    }}>
                      <span style={{ color: '#c8102e', fontSize: '1rem', marginTop: '1px' }}>📜</span>
                      <div>
                        <div style={{ fontSize: '0.84rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                          Quy chế Đào tạo Đại học Chính quy (ĐHBK Hà Nội)
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Quy định đăng ký tín chỉ (12-24 TC), GPA/CPA, học cải thiện điểm, cảnh cáo mức 1-2, điều kiện nhận ĐATN & xét tốt nghiệp.
                        </div>
                      </div>
                    </div>

                    <div style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px'
                    }}>
                      <span style={{ color: '#0284c7', fontSize: '1rem', marginTop: '1px' }}>📘</span>
                      <div>
                        <div style={{ fontSize: '0.84rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                          Chương trình đào tạo Cử nhân Kỹ thuật Điện tử - Viễn thông (ET1)
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Hỗ trợ ET1–2022 (126 TC, 6 mô-đun) và ET1–2023 (132 TC, 5 mô-đun); Ngoại ngữ/GDTC/GDQP được theo dõi ngoài tổng tín chỉ tốt nghiệp.
                        </div>
                      </div>
                    </div>

                    <div style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px'
                    }}>
                      <span style={{ color: '#16a34a', fontSize: '1rem', marginTop: '1px' }}>🔬</span>
                      <div>
                        <div style={{ fontSize: '0.84rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                          Đề cương chi tiết học phần chuyên ngành (ET1)
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Nội dung học phần, bài tập lớn, phần mềm & công cụ thực hành (Cadence, Synopsys, Vivado, Keil C...), cơ hội nghề nghiệp.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Architecture Note */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(200, 16, 46, 0.08), rgba(2, 132, 199, 0.08))',
                  border: '1px solid rgba(200, 16, 46, 0.2)',
                  borderRadius: '12px',
                  padding: '14px',
                  fontSize: '0.8rem',
                  lineHeight: '1.5',
                  color: 'var(--text-secondary)'
                }}>
                  <strong style={{ color: 'var(--text-primary)' }}>🎓 Cơ chế Tư vấn & Cố vấn Đào tạo:</strong> Khi sinh viên hỏi quy chế đào tạo hoặc đề cương môn học, hệ thống tự động trích xuất các điều khoản chính xác từ văn bản HUST; đồng thời kết hợp kiểm tra tự động điều kiện tiên quyết và tính toán CPA theo bảng điểm cá nhân để đưa ra lời khuyên chuẩn xác nhất.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
