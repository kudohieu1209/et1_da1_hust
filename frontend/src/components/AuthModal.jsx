import React, { useState, useEffect } from 'react';
import { 
  X, 
  LogIn, 
  UserPlus, 
  Sparkles, 
  Lock, 
  User, 
  GraduationCap, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  Zap
} from 'lucide-react';

export default function AuthModal({ 
  isOpen, 
  onClose, 
  onAuthSuccess, 
  language = 'vi' 
}) {
  const [activeTab, setActiveTab] = useState('login'); // 'login' | 'register'
  
  // Login form
  const [loginId, setLoginId] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // Register form
  const [regId, setRegId] = useState('');
  const [regName, setRegName] = useState('');
  const [regClass, setRegClass] = useState('Điện tử 01 - K68');
  const [regProgram, setRegProgram] = useState('Kỹ thuật Điện tử - Viễn thông');
  const [regPass, setRegPass] = useState('');
  const [regError, setRegError] = useState('');
  const [regSuccess, setRegSuccess] = useState('');
  const [regLoading, setRegLoading] = useState(false);

  // Demo accounts
  const [demoAccounts, setDemoAccounts] = useState([]);

  useEffect(() => {
    if (isOpen) {
      fetchDemoAccounts();
      setLoginError('');
      setRegError('');
      setRegSuccess('');
    }
  }, [isOpen]);

  const fetchDemoAccounts = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/auth/demo-accounts');
      if (res.ok) {
        const data = await res.json();
        setDemoAccounts(data.demo_accounts || []);
      }
    } catch (err) {
      console.error('Lỗi nạp demo accounts:', err);
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: loginId,
          password: loginPass
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem('hust_advisor_user', JSON.stringify(data.user));
        if (onAuthSuccess) {
          onAuthSuccess(data.user);
        }
        onClose();
      } else {
        setLoginError(data.detail || data.message || 'MSSV hoặc mật khẩu không chính xác!');
      }
    } catch (err) {
      setLoginError('Lỗi kết nối Backend. Vui lòng kiểm tra lại!');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegError('');
    setRegSuccess('');
    setRegLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: regId,
          student_name: regName,
          class_name: regClass,
          program_name: regProgram,
          password: regPass
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setRegSuccess(data.message);
        localStorage.setItem('hust_advisor_user', JSON.stringify(data.user));
        setTimeout(() => {
          if (onAuthSuccess) {
            onAuthSuccess(data.user);
          }
          onClose();
        }, 600);
      } else {
        setRegError(data.detail || data.message || 'Đăng ký không thành công!');
      }
    } catch (err) {
      setRegError('Lỗi kết nối Backend.');
    } finally {
      setRegLoading(false);
    }
  };

  const handleQuickDemoLogin = async (acc) => {
    setLoginId(acc.student_id);
    setLoginPass(acc.default_password || '123456');
    setLoginLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: acc.student_id,
          password: acc.default_password || '123456'
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem('hust_advisor_user', JSON.stringify(data.user));
        if (onAuthSuccess) {
          onAuthSuccess(data.user);
        }
        onClose();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoginLoading(false);
    }
  };

  if (!isOpen) return null;

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
      zIndex: 1100,
      padding: '20px'
    }}>
      <div className="apple-modal-window" onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '18px',
        width: '100%',
        maxWidth: '520px',
        maxHeight: '92vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header */}
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
              background: 'linear-gradient(135deg, #c8102e, #850014)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: '900'
            }}>
              BK
            </div>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
                {language === 'vi' ? 'Tài khoản Sinh viên Bách Khoa' : 'HUST Student Account'}
              </h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                HUST Academic Advisor & Degree Audit Engine
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

        {/* Tab switch */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-subtle)',
          padding: '0 24px',
          background: 'var(--bg-surface)'
        }}>
          <button
            onClick={() => setActiveTab('login')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '12px 18px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'login' ? '2px solid #c8102e' : '2px solid transparent',
              color: activeTab === 'login' ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: activeTab === 'login' ? '600' : '400',
              fontSize: '0.88rem',
              cursor: 'pointer'
            }}
          >
            <LogIn size={16} color={activeTab === 'login' ? '#c8102e' : 'currentColor'} />
            <span>{language === 'vi' ? 'Đăng nhập' : 'Login'}</span>
          </button>

          <button
            onClick={() => setActiveTab('register')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '12px 18px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'register' ? '2px solid #c8102e' : '2px solid transparent',
              color: activeTab === 'register' ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: activeTab === 'register' ? '600' : '400',
              fontSize: '0.88rem',
              cursor: 'pointer'
            }}
          >
            <UserPlus size={16} color={activeTab === 'register' ? '#c8102e' : 'currentColor'} />
            <span>{language === 'vi' ? 'Đăng ký tài khoản mới' : 'Register New'}</span>
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'login' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <form onSubmit={handleLoginSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Mã số sinh viên (MSSV):
                  </label>
                  <input
                    type="text"
                    placeholder="Ví dụ: 20220001"
                    value={loginId}
                    onChange={(e) => setLoginId(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '9px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Mật khẩu:
                  </label>
                  <input
                    type="password"
                    placeholder="Nhập mật khẩu..."
                    value={loginPass}
                    onChange={(e) => setLoginPass(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '9px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                {loginError && (
                  <div style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#ef4444',
                    fontSize: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <AlertCircle size={15} />
                    <span>{loginError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loginLoading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, #c8102e, #990000)',
                    color: '#fff',
                    fontWeight: '600',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    marginTop: '4px',
                    boxShadow: '0 2px 8px rgba(200, 16, 46, 0.3)'
                  }}
                >
                  {loginLoading ? <Loader2 size={16} className="spin" /> : <LogIn size={16} />}
                  <span>{loginLoading ? 'Đang đăng nhập...' : 'Đăng nhập'}</span>
                </button>
              </form>

              {/* Quick Demo Login Section */}
              <div style={{ marginTop: '10px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
                <div style={{ 
                  fontSize: '0.78rem', 
                  color: 'var(--text-muted)', 
                  fontWeight: '600', 
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px'
                }}>
                  <Zap size={14} color="#f59e0b" />
                  <span>Đăng nhập nhanh tài khoản Demo (1-Click để kiểm thử):</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {demoAccounts.map(acc => (
                    <button
                      key={acc.student_id}
                      type="button"
                      onClick={() => handleQuickDemoLogin(acc)}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '8px',
                        border: '1px solid var(--border-subtle)',
                        background: 'var(--bg-card)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '2px',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = 'rgba(200, 16, 46, 0.4)';
                        e.currentTarget.style.background = 'var(--sidebar-hover)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'var(--border-subtle)';
                        e.currentTarget.style.background = 'var(--bg-card)';
                      }}
                    >
                      <div style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {acc.student_name}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#c8102e' }}>
                        {acc.badge} • {acc.student_id}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'register' && (
            <form onSubmit={handleRegisterSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{
                background: 'rgba(56, 189, 248, 0.08)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                borderRadius: '8px',
                padding: '10px 12px',
                fontSize: '0.78rem',
                color: 'var(--text-primary)',
                lineHeight: 1.4
              }}>
                💡 <strong>Lưu ý:</strong> Khi bạn tạo tài khoản mới, hệ thống sẽ khởi tạo bảng điểm <strong>trống hoàn toàn</strong>. Sau đó bạn chỉ cần dán bảng điểm CTT của mình vào là AI sẽ tự động phân tích và tư vấn!
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Mã số sinh viên (MSSV):
                </label>
                <input
                  type="text"
                  placeholder="Ví dụ: 20231234"
                  value={regId}
                  onChange={(e) => setRegId(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    fontSize: '0.88rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Họ và tên sinh viên:
                </label>
                <input
                  type="text"
                  placeholder="Ví dụ: Nguyễn Văn A"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    fontSize: '0.88rem'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Lớp / Khóa:
                  </label>
                  <input
                    type="text"
                    value={regClass}
                    onChange={(e) => setRegClass(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Mật khẩu:
                  </label>
                  <input
                    type="password"
                    placeholder="Tạo mật khẩu..."
                    value={regPass}
                    onChange={(e) => setRegPass(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>
              </div>

              {regError && (
                <div style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#ef4444',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <AlertCircle size={15} />
                  <span>{regError}</span>
                </div>
              )}

              {regSuccess && (
                <div style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  color: '#10b981',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <CheckCircle2 size={15} />
                  <span>{regSuccess}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={regLoading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px 16px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #c8102e, #990000)',
                  color: '#fff',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  marginTop: '6px',
                  boxShadow: '0 2px 8px rgba(200, 16, 46, 0.3)'
                }}
              >
                {regLoading ? <Loader2 size={16} className="spin" /> : <UserPlus size={16} />}
                <span>{regLoading ? 'Đang tạo tài khoản...' : 'Tạo tài khoản & Đăng nhập'}</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
