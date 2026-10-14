import React, { useState, useEffect } from 'react';
import { 
  X, 
  Users, 
  UserCheck, 
  UploadCloud, 
  CheckCircle2, 
  Loader2
} from 'lucide-react';
import { apiUrl } from '../api';

export default function ProfileModal({ 
  isOpen, 
  onClose, 
  currentStudentId, 
  onProfileSwitched,
  initialTab = 'demo',
  studentProfile = null,
  language = 'vi' 
}) {
  const [activeTab, setActiveTab] = useState(initialTab); // 'demo' | 'import'
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [switchingId, setSwitchingId] = useState(null);

  // Form state for custom import
  const [importId, setImportId] = useState(studentProfile?.info?.student_id || '20228888');
  const [importName, setImportName] = useState(studentProfile?.info?.student_name || 'Nguyễn Hoàng Nam');
  const [importClass, setImportClass] = useState(studentProfile?.info?.class_name || 'Điện tử 01 - K67');
  const [importText, setImportText] = useState('');
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      if (studentProfile?.info) {
        setImportId(studentProfile.info.student_id || '');
        setImportName(studentProfile.info.student_name || '');
        setImportClass(studentProfile.info.class_name || '');
      }
      fetchProfiles();
    }
  }, [isOpen, initialTab, studentProfile]);

  const fetchProfiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/student/profiles'));
      if (res.ok) {
        const data = await res.json();
        setProfiles(data);
      }
    } catch (err) {
      console.error('Lỗi nạp danh sách hồ sơ:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitch = async (studentId) => {
    setSwitchingId(studentId);
    try {
      const res = await fetch(apiUrl('/api/student/switch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId })
      });
      if (res.ok) {
        const data = await res.json();
        if (onProfileSwitched) {
          onProfileSwitched(data);
        }
        await fetchProfiles();
        setTimeout(() => {
          onClose();
        }, 300);
      }
    } catch (err) {
      console.error('Lỗi chuyển hồ sơ:', err);
    } finally {
      setSwitchingId(null);
    }
  };

  const handleFillSample = () => {
    setImportId('20228888');
    setImportName('Nguyễn Hoàng Nam');
    setImportClass('Điện tử 01 - K67');
    setImportText(
`MI1111  Giải tích I                 4   A
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
ET3260  Kỹ thuật phần mềm ứng dụng 2   A`
    );
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    if (!importText.trim()) {
      alert(language === 'vi' ? 'Vui lòng dán nội dung bảng điểm từ CTT!' : 'Please paste transcript text from CTT!');
      return;
    }
    setImporting(true);
    setImportMessage(null);
    try {
      const res = await fetch(apiUrl('/api/student/import'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: importId,
          student_name: importName,
          class_name: importClass,
          raw_text: importText
        })
      });
      if (res.ok) {
        const data = await res.json();
        setImportMessage({ type: 'success', text: data.message || 'Nhập bảng điểm thành công!' });
        if (onProfileSwitched) {
          onProfileSwitched(data);
        }
        await fetchProfiles();
        setTimeout(() => {
          onClose();
        }, 800);
      } else {
        setImportMessage({ type: 'error', text: 'Có lỗi xảy ra khi nạp bảng điểm.' });
      }
    } catch (err) {
      console.error('Lỗi import bảng điểm:', err);
      setImportMessage({ type: 'error', text: 'Không thể kết nối Backend.' });
    } finally {
      setImporting(false);
    }
  };

  if (!isOpen) return null;

  const getBadgeColor = (badge) => {
    switch (badge) {
      case 'Pilot Benchmark': return { bg: 'rgba(213, 19, 42, 0.15)', text: 'var(--danger)', border: 'rgba(213, 19, 42, 0.3)' };
      case 'Học lực Giỏi': return { bg: 'rgba(16, 185, 129, 0.15)', text: 'var(--success)', border: 'rgba(16, 185, 129, 0.3)' };
      case 'Cảnh báo Mức 2': return { bg: 'rgba(239, 68, 68, 0.15)', text: 'var(--danger)', border: 'rgba(239, 68, 68, 0.3)' };
      case 'Sinh viên K68': return { bg: 'rgba(213, 19, 42, 0.15)', text: 'var(--brand-accent)', border: 'rgba(213, 19, 42, 0.3)' };
      default: return { bg: 'rgba(246, 196, 0, 0.15)', text: 'var(--gold-ink)', border: 'rgba(246, 196, 0, 0.3)' };
    }
  };

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
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '18px',
        width: '100%',
        maxWidth: '680px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-card)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'var(--brand-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              <Users size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
                {language === 'vi' ? 'Quản lý Hồ sơ Sinh viên' : 'Student Profile Manager'}
              </h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0, marginTop: '2px' }}>
                {language === 'vi' 
                  ? 'Chuyển đổi hồ sơ mẫu hoặc nhập bảng điểm cá nhân từ CTT' 
                  : 'Switch demo student profiles or import your personal CTT transcript'}
              </p>
            </div>
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
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-subtle)',
          padding: '0 24px',
          background: 'var(--bg-surface)'
        }}>
          <button
            onClick={() => setActiveTab('demo')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'demo' ? '2px solid var(--hust-red)' : '2px solid transparent',
              color: activeTab === 'demo' ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: activeTab === 'demo' ? '600' : '400',
              fontSize: '0.88rem',
              cursor: 'pointer'
            }}
          >
            <UserCheck size={16} color={activeTab === 'demo' ? 'var(--brand-accent)' : 'currentColor'} />
            {language === 'vi' ? 'Hồ sơ Sinh viên Mẫu' : 'Demo Benchmark Profiles'}
          </button>

          <button
            onClick={() => setActiveTab('import')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'import' ? '2px solid var(--hust-red)' : '2px solid transparent',
              color: activeTab === 'import' ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: activeTab === 'import' ? '600' : '400',
              fontSize: '0.88rem',
              cursor: 'pointer'
            }}
          >
            <UploadCloud size={16} color={activeTab === 'import' ? 'var(--brand-accent)' : 'currentColor'} />
            {language === 'vi' ? 'Nhập bảng điểm CTT' : 'Import CTT Transcript'}
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'demo' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '0 0 4px' }}>
                {language === 'vi'
                  ? 'Chọn một hồ sơ mẫu bên dưới để trải nghiệm tư vấn cá nhân hóa theo từng trường hợp sinh viên:'
                  : 'Select a sample profile below to test personalized degree audit and advising:'}
              </p>

              {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '30px' }}>
                  <Loader2 size={28} className="spin" color="var(--brand-accent)" />
                </div>
              ) : (
                profiles.map((p) => {
                  const isActive = p.is_active || p.student_id === currentStudentId;
                  const isSwitching = switchingId === p.student_id;
                  const badgeStyle = getBadgeColor(p.badge);

                  return (
                    <div
                      key={p.student_id}
                      onClick={() => !isActive && !isSwitching && handleSwitch(p.student_id)}
                      style={{
                        padding: '14px 16px',
                        borderRadius: '12px',
                        background: isActive ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                        border: isActive ? '2px solid var(--hust-red)' : '1px solid var(--border-subtle)',
                        cursor: isActive ? 'default' : 'pointer',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '14px'
                      }}
                      onMouseEnter={e => {
                        if (!isActive) e.currentTarget.style.borderColor = 'rgba(213, 19, 42, 0.4)';
                      }}
                      onMouseLeave={e => {
                        if (!isActive) e.currentTarget.style.borderColor = 'var(--border-subtle)';
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{
                            fontSize: '0.92rem',
                            fontWeight: '700',
                            color: 'var(--text-primary)'
                          }}>
                            {p.name}
                          </span>
                          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            • MSSV: {p.student_id} ({p.class_name})
                          </span>
                          <span style={{
                            fontSize: '0.68rem',
                            fontWeight: '700',
                            padding: '2px 8px',
                            borderRadius: '12px',
                            background: badgeStyle.bg,
                            color: badgeStyle.text,
                            border: `1px solid ${badgeStyle.border}`
                          }}>
                            {p.badge}
                          </span>
                        </div>

                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                          {p.persona}
                        </div>

                        {/* Stats chips */}
                        <div style={{ display: 'flex', gap: '10px', fontSize: '0.74rem' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border-subtle)'
                          }}>
                            CPA: <strong style={{ color: 'var(--warning)' }}>{p.cpa.toFixed(2)}</strong>
                          </span>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border-subtle)'
                          }}>
                            Tích lũy: <strong style={{ color: 'var(--success)' }}>{p.accumulated_credits} TC</strong>
                          </span>
                        </div>
                      </div>

                      <div>
                        {isActive ? (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            color: 'var(--success)',
                            fontSize: '0.8rem',
                            fontWeight: '600'
                          }}>
                            <CheckCircle2 size={18} />
                            <span>Đang dùng</span>
                          </div>
                        ) : isSwitching ? (
                          <Loader2 size={18} className="spin" color="var(--brand-accent)" />
                        ) : (
                          <button
                            style={{
                              padding: '6px 14px',
                              borderRadius: '8px',
                              background: 'var(--bg-surface)',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--text-primary)',
                              fontSize: '0.8rem',
                              fontWeight: '600',
                              cursor: 'pointer'
                            }}
                          >
                            Chọn
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {activeTab === 'import' && (
            <form onSubmit={handleImportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{
                background: 'rgba(213, 19, 42, 0.08)',
                border: '1px solid rgba(213, 19, 42, 0.25)',
                borderRadius: '10px',
                padding: '12px 14px',
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
                lineHeight: 1.45
              }}>
                💡 <strong>Hướng dẫn:</strong> Đăng nhập vào <code>ctt.hust.edu.vn</code>, vào mục <em>Bảng điểm cá nhân</em>, quét chọn các dòng mã môn và điểm chữ (ví dụ <code>MI1111 A</code>, <code>ET2040 B+</code>), copy và dán trực tiếp vào ô bên dưới. AI sẽ tự động phân tích tiến độ học tập và tư vấn riêng cho bạn!
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    MSSV:
                  </label>
                  <input
                    type="text"
                    value={importId}
                    onChange={(e) => setImportId(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.84rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Họ và tên:
                  </label>
                  <input
                    type="text"
                    value={importName}
                    onChange={(e) => setImportName(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.84rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Lớp / Khóa:
                  </label>
                  <input
                    type="text"
                    value={importClass}
                    onChange={(e) => setImportClass(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.84rem'
                    }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-primary)', fontWeight: '600' }}>
                    Văn bản bảng điểm copy từ CTT Bách Khoa:
                  </label>
                  <button
                    type="button"
                    onClick={handleFillSample}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--brand-accent)',
                      fontSize: '0.76rem',
                      cursor: 'pointer',
                      textDecoration: 'underline'
                    }}
                  >
                    Điền bảng điểm mẫu
                  </button>
                </div>
                <textarea
                  rows={8}
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder="Dán các dòng bảng điểm từ CTT vào đây... (Ví dụ: MI1111 4 A hoặc ET2040 3 B+)"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    fontSize: '0.82rem',
                    fontFamily: 'monospace',
                    lineHeight: 1.4,
                    resize: 'vertical'
                  }}
                />
              </div>

              {importMessage && (
                <div style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  background: importMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: importMessage.type === 'success' ? 'var(--success)' : 'var(--danger)',
                  border: `1px solid ${importMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
                }}>
                  {importMessage.text}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
                <button
                  type="button"
                  onClick={onClose}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'transparent',
                    color: 'var(--text-muted)',
                    fontSize: '0.84rem',
                    cursor: 'pointer'
                  }}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={importing}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 18px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--brand-gradient)',
                    color: '#fff',
                    fontSize: '0.84rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px rgba(213, 19, 42, 0.3)'
                  }}
                >
                  {importing ? <Loader2 size={16} className="spin" /> : <UploadCloud size={16} />}
                  <span>{importing ? 'Đang phân tích...' : 'Phân tích & Tải vào hệ thống'}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
