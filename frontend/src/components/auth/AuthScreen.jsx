import React, { useEffect, useState } from 'react';
import { AlertCircle, Eye, EyeOff, Loader2, LogIn, UserPlus } from 'lucide-react';
import BrandLogo from '../BrandLogo';
import { apiFetch, apiUrl, readError } from '../../api';
import './auth.css';

const MIN_PASSWORD_LENGTH = 8;

// Danh sách dự phòng khi chưa tải được /api/programs: ET1 là CTĐT đã đối chiếu thủ công.
const FALLBACK_PROGRAMS = [{ code: 'ET1', name: 'Điện tử và Viễn thông', cohorts: ['K67', 'K68'] }];

const EMPTY_REGISTER = {
  student_id: '',
  student_name: '',
  class_name: '',
  program_code: FALLBACK_PROGRAMS[0].code,
  password: '',
  confirm: '',
};

function PasswordInput({ id, value, onChange, autoComplete, placeholder }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="auth-password">
      <input
        id={id}
        className="auth-input"
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        placeholder={placeholder}
        required
      />
      <button
        type="button"
        className="auth-password__toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

/**
 * Màn hình toàn trang khi chưa đăng nhập. Thành công thì backend đặt cookie
 * phiên (HttpOnly) và trả về thông tin tài khoản cho onAuthenticated.
 */
export default function AuthScreen({ onAuthenticated, notice, language = 'vi' }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [mode, setMode] = useState('login');
  const [login, setLogin] = useState({ student_id: '', password: '' });
  const [register, setRegister] = useState(EMPTY_REGISTER);
  const [programs, setPrograms] = useState(FALLBACK_PROGRAMS);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(apiUrl('/api/programs?supported_only=true'));
        if (!res.ok) return;
        const data = await res.json();
        const loaded = (data.programs || [])
          .map((p) => ({ code: p.admission_code, name: p.name, cohorts: p.supported_cohorts || [] }))
          .sort((a, b) => a.code.localeCompare(b.code));
        if (!cancelled && loaded.length) setPrograms(loaded);
      } catch {
        // Giữ danh sách dự phòng; backend vẫn kiểm tra lại khi đăng ký.
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const selectedProgram = programs.find((p) => p.code === register.program_code) || programs[0];
  const cohortHint = selectedProgram?.cohorts?.join(', ') || '—';

  const switchMode = (next) => {
    setMode(next);
    setError('');
  };

  const submit = async (path, body, fallback) => {
    setSubmitting(true);
    setError('');
    try {
      const res = await apiFetch(apiUrl(path), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setError(await readError(res, fallback));
        return;
      }
      onAuthenticated(await res.json());
    } catch {
      setError(t('Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy.', 'Cannot reach the server.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogin = (e) => {
    e.preventDefault();
    submit(
      '/api/auth/login',
      { student_id: login.student_id.trim(), password: login.password },
      t('Đăng nhập không thành công.', 'Login failed.'),
    );
  };

  const handleRegister = (e) => {
    e.preventDefault();
    if (!/^[0-9]{8}$/.test(register.student_id.trim())) {
      setError(t('MSSV gồm đúng 8 chữ số.', 'Student ID must be 8 digits.'));
      return;
    }
    if (!/\bK\d{2}\b/i.test(register.class_name)) {
      setError(t('Tên lớp cần có khóa, ví dụ: Điện tử 02 - K67.', 'Class must include the cohort, e.g. K67.'));
      return;
    }
    if (register.password.length < MIN_PASSWORD_LENGTH) {
      setError(t(`Mật khẩu cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự.`, `Password needs ${MIN_PASSWORD_LENGTH}+ characters.`));
      return;
    }
    if (register.password !== register.confirm) {
      setError(t('Mật khẩu nhập lại không khớp.', 'Passwords do not match.'));
      return;
    }
    const { confirm: _confirm, ...body } = register;
    submit(
      '/api/auth/register',
      { ...body, student_id: body.student_id.trim() },
      t('Đăng ký không thành công.', 'Registration failed.'),
    );
  };

  const setLoginField = (key) => (e) => setLogin({ ...login, [key]: e.target.value });
  const setRegisterField = (key) => (e) => setRegister({ ...register, [key]: e.target.value });

  return (
    <main className="auth-screen">
      <div className="auth-card">
        <header className="auth-card__header">
          <BrandLogo size={56} />
          <h1>HUST Advisor</h1>
          <p>{t('Tư vấn học tập cho sinh viên Bách Khoa', 'Academic advising for HUST students')}</p>
        </header>

        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'is-active' : ''}
            onClick={() => switchMode('login')}
          >
            {t('Đăng nhập', 'Log in')}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'is-active' : ''}
            onClick={() => switchMode('register')}
          >
            {t('Đăng ký', 'Sign up')}
          </button>
        </div>

        {notice && !error && <div className="auth-notice" role="status">{notice}</div>}
        {error && (
          <div className="auth-error" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {mode === 'login' ? (
          <form className="auth-form" onSubmit={handleLogin}>
            <label className="auth-field">
              <span>{t('Mã số sinh viên', 'Student ID')}</span>
              <input
                className="auth-input"
                inputMode="numeric"
                autoComplete="username"
                placeholder="20220001"
                value={login.student_id}
                onChange={setLoginField('student_id')}
                required
                autoFocus
              />
            </label>
            <div className="auth-field">
              <label htmlFor="login-password">{t('Mật khẩu', 'Password')}</label>
              <PasswordInput
                id="login-password"
                value={login.password}
                onChange={setLoginField('password')}
                autoComplete="current-password"
              />
            </div>
            <button type="submit" className="auth-submit" disabled={submitting}>
              {submitting ? <Loader2 size={16} className="spin" /> : <LogIn size={16} />}
              <span>{submitting ? t('Đang đăng nhập…', 'Logging in…') : t('Đăng nhập', 'Log in')}</span>
            </button>
            <p className="auth-switch">
              {t('Chưa có tài khoản?', 'No account yet?')}{' '}
              <button type="button" onClick={() => switchMode('register')}>{t('Đăng ký', 'Sign up')}</button>
            </p>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleRegister}>
            <div className="auth-row">
              <label className="auth-field">
                <span>{t('Mã số sinh viên', 'Student ID')}</span>
                <input
                  className="auth-input"
                  inputMode="numeric"
                  autoComplete="username"
                  placeholder="20231234"
                  maxLength={8}
                  value={register.student_id}
                  onChange={setRegisterField('student_id')}
                  required
                  autoFocus
                />
              </label>
              <label className="auth-field">
                <span>{t('Lớp', 'Class')}</span>
                <input
                  className="auth-input"
                  placeholder="Điện tử 02 - K68"
                  value={register.class_name}
                  onChange={setRegisterField('class_name')}
                  required
                />
              </label>
            </div>
            <label className="auth-field">
              <span>{t('Họ và tên', 'Full name')}</span>
              <input
                className="auth-input"
                autoComplete="name"
                placeholder="Nguyễn Văn A"
                value={register.student_name}
                onChange={setRegisterField('student_name')}
                required
              />
            </label>
            <label className="auth-field">
              <span>{t('Chương trình đào tạo', 'Program')}</span>
              <select className="auth-input" value={register.program_code} onChange={setRegisterField('program_code')}>
                {programs.map((p) => (
                  <option key={p.code} value={p.code}>{p.code} – {p.name}</option>
                ))}
              </select>
              <small>{t(`Khóa được hỗ trợ: ${cohortHint}.`, `Supported cohorts: ${cohortHint}.`)}</small>
            </label>
            <div className="auth-row">
              <div className="auth-field">
                <label htmlFor="register-password">{t('Mật khẩu', 'Password')}</label>
                <PasswordInput
                  id="register-password"
                  value={register.password}
                  onChange={setRegisterField('password')}
                  autoComplete="new-password"
                  placeholder={t(`Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`, `${MIN_PASSWORD_LENGTH}+ characters`)}
                />
              </div>
              <div className="auth-field">
                <label htmlFor="register-confirm">{t('Nhập lại mật khẩu', 'Confirm password')}</label>
                <PasswordInput
                  id="register-confirm"
                  value={register.confirm}
                  onChange={setRegisterField('confirm')}
                  autoComplete="new-password"
                />
              </div>
            </div>
            <button type="submit" className="auth-submit" disabled={submitting}>
              {submitting ? <Loader2 size={16} className="spin" /> : <UserPlus size={16} />}
              <span>{submitting ? t('Đang tạo tài khoản…', 'Creating account…') : t('Tạo tài khoản', 'Create account')}</span>
            </button>
            <p className="auth-switch">
              {t('Đã có tài khoản?', 'Already registered?')}{' '}
              <button type="button" onClick={() => switchMode('login')}>{t('Đăng nhập', 'Log in')}</button>
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
