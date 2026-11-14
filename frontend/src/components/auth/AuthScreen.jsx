import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, ArrowRight, BookOpen, Eye, EyeOff, GraduationCap, Loader2, LockKeyhole, MessageSquare, UserRound } from 'lucide-react';
import BrandLogo from '../BrandLogo';
import ProgramsTab from '../ProgramsTab';
import SchoolConnect from './SchoolConnect';
import { apiFetch, apiUrl, readError } from '../../api';
import './auth.css';

const FALLBACK_PROGRAMS = [{ code: 'ET1', name: 'Điện tử và Viễn thông', cohorts: ['K67', 'K68'] }];
const EMPTY_REGISTER = { student_id: '', student_name: '', class_name: '', program_code: 'ET1', password: '', confirm: '' };

function PasswordInput({ id, value, onChange, autoComplete, disabled }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="auth-password">
      <input id={id} className="auth-input" type={visible ? 'text' : 'password'} value={value} onChange={onChange}
        autoComplete={autoComplete} required maxLength={256} disabled={disabled} />
      <button type="button" className="auth-password__toggle" onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'} aria-pressed={visible}>
        {visible ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </div>
  );
}

export default function AuthScreen({ onAuthenticated, notice, language = 'vi' }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [mode, setMode] = useState('local');
  const [login, setLogin] = useState({ student_id: '', password: '' });
  const [register, setRegister] = useState(EMPTY_REGISTER);
  const [programs, setPrograms] = useState(FALLBACK_PROGRAMS);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [schoolCommitting, setSchoolCommitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(apiUrl('/api/programs?supported_only=true'));
        if (!res.ok) return;
        const data = await res.json();
        const loaded = (data.programs || []).map((p) => ({
          code: p.admission_code, name: p.name, cohorts: p.supported_cohorts || [],
        })).sort((a, b) => a.code.localeCompare(b.code));
        if (!cancelled && loaded.length) setPrograms(loaded);
      } catch { /* Retain the supported fallback; the server validates the program. */ }
    })();
    return () => { cancelled = true; };
  }, []);

  const switchMode = (next) => {
    setMode(next);
    setError('');
    setLogin((current) => ({ ...current, password: '' }));
    setRegister((current) => ({ ...current, password: '', confirm: '' }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const isRegister = mode === 'register';
    const form = isRegister ? register : login;
    if (!/^[0-9]{8}$/.test(form.student_id.trim())) {
      setError(t('MSSV gồm đúng 8 chữ số.', 'Student ID must contain 8 digits.'));
      return;
    }
    if (isRegister && (register.password.length < 8 || register.password !== register.confirm)) {
      setError(t('Mật khẩu cần ít nhất 8 ký tự và hai lần nhập phải khớp.', 'Use at least 8 characters and matching passwords.'));
      return;
    }
    setSubmitting(true);
    try {
      const { confirm: _confirm, ...registration } = register;
      const res = await apiFetch(apiUrl(isRegister ? '/api/auth/register' : '/api/auth/login'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isRegister ? { ...registration, student_id: register.student_id.trim() }
          : { student_id: login.student_id.trim(), password: login.password }),
      });
      if (!res.ok) {
        setError(await readError(res, t('Chưa thể đăng nhập. Vui lòng thử lại.', 'Unable to sign in. Please try again.')));
        return;
      }
      const account = await res.json();
      setLogin((current) => ({ ...current, password: '' }));
      setRegister((current) => ({ ...current, password: '', confirm: '' }));
      onAuthenticated(account);
    } catch {
      setError(t('Chưa kết nối được máy chủ. Hãy kiểm tra backend đang chạy.', 'Cannot reach the server. Check that the backend is running.'));
    } finally { setSubmitting(false); }
  };

  if (mode === 'browse') return (
    <main className="program-public">
      <button type="button" className="auth-back" onClick={() => switchMode('local')}><ArrowLeft size={16} />{t('Quay lại đăng nhập', 'Back to sign in')}</button>
      <ProgramsTab />
    </main>
  );

  const selectedProgram = programs.find((p) => p.code === register.program_code) || programs[0];
  const setRegisterField = (key) => (e) => setRegister({ ...register, [key]: e.target.value });

  return (
    <main className="auth-screen">
      <div className="auth-layout">
        <section className="auth-story" aria-label="HUST Advisor">
          <a className="auth-brand" href="/" aria-label="HUST Advisor">
            <BrandLogo size={48} decorative />
            <span>HUST<span className="auth-brand__light">Advisor</span><small>{t('NGƯỜI BẠN ĐỒNG HÀNH HỌC TẬP', 'YOUR ACADEMIC COMPANION')}</small></span>
          </a>
          <div className="auth-story__body">
            <span className="auth-eyebrow"><span />{t('HIỂU MÌNH. HIỂU LỘ TRÌNH.', 'YOUR PROGRESS. YOUR PATH.')}</span>
            <h1>{t('Mỗi học kỳ,', 'Every semester,')}<br /><span>{t('một bước tiến.', 'a step forward.')}</span></h1>
            <p className="auth-story__description">{t(
              'Từ bảng điểm đến kế hoạch học tập — một nơi để hiểu tiến độ, chọn môn phù hợp và chủ động với hành trình tại Bách khoa.',
              'From your transcript to your next semester — understand your progress, choose your courses and shape your journey at HUST.',
            )}</p>
            <div className="auth-benefits">
              {[
                [GraduationCap, t('Hồ sơ học tập của bạn', 'Your academic profile'), t('Điểm số, tín chỉ và tiến độ trong một góc nhìn.', 'Grades, credits and progress, all in one place.')],
                [BookOpen, t('Lộ trình đúng chương trình', 'A plan for your degree'), t('Đối chiếu học phần và điều kiện tốt nghiệp.', 'Understand your courses and graduation requirements.')],
                [MessageSquare, t('Có thắc mắc, có người bạn', 'Questions meet guidance'), t('Hỏi về môn học, học kỳ và những bước tiếp theo.', 'Ask about courses, semesters and what comes next.')],
              ].map(([Icon, title, detail]) => (
                <div className="auth-benefit" key={title}><span className="auth-benefit__icon"><Icon size={19} /></span><div><h2>{title}</h2><p>{detail}</p></div></div>
              ))}
            </div>
          </div>
          <p className="auth-story__footer"><span className="auth-story__rule" />{t('Dành cho sinh viên Đại học Bách khoa Hà Nội', 'Made for students of Hanoi University of Science and Technology')}</p>
        </section>

        <section className="auth-card" aria-labelledby="auth-title">
          <header className="auth-card__header">
            <h2 id="auth-title">{mode === 'register' ? t('Tạo tài khoản demo', 'Create a demo account') : t('Chào bạn trở lại', 'Welcome back')}</h2>
            {mode === 'register' && <p>{t('Dùng để nhập bảng điểm và lưu kế hoạch học tập.', 'Import your grades and save your academic plans.')}</p>}
          </header>

          <div className="auth-tabs" role="tablist" aria-label={t('Cách đăng nhập', 'Sign-in method')}
            onKeyDown={(e) => {
              if (submitting || schoolCommitting || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
              e.preventDefault();
              const advisor = e.key === 'Home' || e.key === 'ArrowLeft' || (e.key !== 'End' && mode === 'school');
              switchMode(advisor ? 'local' : 'school');
              e.currentTarget.querySelector(advisor ? '#advisor-tab' : '#school-tab')?.focus();
            }}>
            <button type="button" role="tab" id="advisor-tab" aria-controls="auth-panel" aria-selected={mode !== 'school'}
              className={mode !== 'school' ? 'is-active' : ''} tabIndex={mode !== 'school' ? 0 : -1} disabled={submitting || schoolCommitting} onClick={() => switchMode('local')}><UserRound size={15} />{t('Tài khoản demo', 'Demo account')}</button>
            <button type="button" role="tab" id="school-tab" aria-controls="auth-panel" aria-selected={mode === 'school'}
              className={mode === 'school' ? 'is-active' : ''} tabIndex={mode === 'school' ? 0 : -1} disabled={submitting || schoolCommitting} onClick={() => switchMode('school')}><GraduationCap size={16} />{t('Tài khoản trường', 'HUST account')}</button>
          </div>

          {notice && !error && <div className="auth-notice" role="status">{notice}</div>}
          {error && <div className="auth-error" role="alert"><AlertCircle size={16} /><span>{error}</span></div>}

          <div id="auth-panel" role="tabpanel" aria-labelledby={mode !== 'school' ? 'advisor-tab' : 'school-tab'}>
            {mode === 'school' ? (
              <SchoolConnect programs={programs} onConnected={onAuthenticated} onCommittingChange={setSchoolCommitting} language={language} />
            ) : (
              <form className="auth-form" onSubmit={submit}>
                {mode === 'register' && <button type="button" className="auth-back" onClick={() => switchMode('local')}><ArrowLeft size={15} />{t('Về đăng nhập demo', 'Back to demo sign in')}</button>}
                {mode === 'local' && <p className="auth-form__hint"><LockKeyhole size={16} />{t('Dùng mật khẩu bạn đã tạo cho tài khoản demo.', 'Use the password you created for your demo account.')}</p>}
                <label className="auth-field" htmlFor="advisor-student-id"><span>{t('Mã số sinh viên', 'Student ID')}</span>
                  <input id="advisor-student-id" className="auth-input" inputMode="numeric" autoComplete="username" placeholder="Ví dụ: 20231234"
                    maxLength={8} pattern="[0-9]{8}" value={mode === 'register' ? register.student_id : login.student_id} disabled={submitting} required
                    onChange={mode === 'register' ? setRegisterField('student_id') : (e) => setLogin({ ...login, student_id: e.target.value })} />
                </label>
                {mode === 'register' && <>
                  <label className="auth-field" htmlFor="advisor-full-name"><span>{t('Họ và tên', 'Full name')}</span><input id="advisor-full-name" className="auth-input" autoComplete="name"
                    value={register.student_name} onChange={setRegisterField('student_name')} maxLength={80} disabled={submitting} required /></label>
                  <label className="auth-field" htmlFor="advisor-class"><span>{t('Lớp và khóa', 'Class and cohort')}</span><input id="advisor-class" className="auth-input" placeholder="Điện tử 02 - K68"
                    value={register.class_name} onChange={setRegisterField('class_name')} maxLength={60} disabled={submitting} required /><small>{t('Ví dụ: Điện tử 02 - K68.', 'For example: Electronics 02 - K68.')}</small></label>
                  <label className="auth-field" htmlFor="advisor-program"><span>{t('Chương trình đào tạo', 'Degree program')}</span>
                    <select id="advisor-program" className="auth-input" value={register.program_code} onChange={setRegisterField('program_code')} disabled={submitting}>
                      {programs.map((p) => <option key={p.code} value={p.code}>{p.code} — {p.name}</option>)}
                    </select><small>{t('Khóa hỗ trợ: ', 'Supported cohorts: ')}{selectedProgram?.cohorts?.join(', ') || '—'}</small>
                  </label>
                </>}
                <div className="auth-field"><label htmlFor="advisor-password">{t('Mật khẩu', 'Password')}</label>
                  <PasswordInput id="advisor-password" value={mode === 'register' ? register.password : login.password} disabled={submitting}
                    onChange={mode === 'register' ? setRegisterField('password') : (e) => setLogin({ ...login, password: e.target.value })}
                    autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
                  {mode === 'register' && <small>{t('Tối thiểu 8 ký tự; tránh mật khẩu phổ biến hoặc chứa MSSV.', 'At least 8 characters. Avoid common passwords or your student ID.')}</small>}
                </div>
                {mode === 'register' && <div className="auth-field"><label htmlFor="advisor-confirm">{t('Nhập lại mật khẩu', 'Confirm password')}</label>
                  <PasswordInput id="advisor-confirm" value={register.confirm} onChange={setRegisterField('confirm')} autoComplete="new-password" disabled={submitting} /></div>}
                <button type="submit" className="auth-submit" disabled={submitting}>{submitting ? <Loader2 size={17} className="spin" /> : <ArrowRight size={17} />}
                  {submitting ? t('Đang xử lý…', 'Please wait…') : mode === 'register' ? t('Tạo tài khoản', 'Create account') : t('Vào không gian học tập', 'Open my workspace')}</button>
                <p className="auth-switch">{mode === 'register' ? t('Đã có tài khoản?', 'Already have an account?') : t('Chưa có tài khoản demo?', 'New to demo account?')}{' '}
                  <button type="button" disabled={submitting} onClick={() => switchMode(mode === 'register' ? 'local' : 'register')}>{mode === 'register' ? t('Đăng nhập', 'Sign in') : t('Tạo tài khoản', 'Create an account')}</button></p>
              </form>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
