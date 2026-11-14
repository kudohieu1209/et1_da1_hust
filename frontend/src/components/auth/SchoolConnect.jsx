import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Check, CheckCircle2, ExternalLink, Loader2, ShieldCheck } from 'lucide-react';
import { apiFetch, apiUrl, readError } from '../../api';
import './school-connect.css';
import { Capacitor } from '@capacitor/core';

const BUSY = new Set(['opening', 'waiting', 'syncing', 'saving']);

export default function SchoolConnect({ _programs = [], defaultProgram = 'ET1', onConnected, onCommittingChange, language = 'vi' }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const usbMode = Capacitor.isNativePlatform() && ['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.protocol === 'http:';
  const [program] = useState(defaultProgram);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [available, setAvailable] = useState(null);
  const [retryAfter, setRetryAfter] = useState(0);
  const connection = useRef({ generation: 0, attempt: null, timer: null, mounted: false, running: false });
  const onConnectedRef = useRef(onConnected);
  onConnectedRef.current = onConnected;

  useEffect(() => {
    if (retryAfter <= 0) return;
    const timer = setTimeout(() => setRetryAfter((value) => Math.max(0, value - 1)), 1000);
    return () => clearTimeout(timer);
  }, [retryAfter]);

  useEffect(() => {
    onCommittingChange?.(status === 'saving');
    return () => onCommittingChange?.(false);
  }, [status, onCommittingChange]);

  const abandon = (id) => apiFetch(apiUrl(`/api/auth/ctt/${id}`), { method: 'DELETE', keepalive: true }).catch(() => {});

  useEffect(() => {
    const state = connection.current;
    state.mounted = true;
    let cancelled = false;
    apiFetch(apiUrl('/api/auth/ctt/capabilities'))
      .then(async (res) => {
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!cancelled) setAvailable(data.available);
      })
      .catch(() => { if (!cancelled) setAvailable(null); });
    return () => {
      cancelled = true;
      state.mounted = false;
      state.generation += 1;
      clearTimeout(state.timer);
      if (state.attempt) abandon(state.attempt);
      state.attempt = null;
    };
  }, []);

  const start = async () => {
    const state = connection.current;
    if (state.running || retryAfter > 0) return;
    state.running = true; // Guard repeated clicks before React renders disabled.
    const generation = ++state.generation;
    const active = () => state.mounted && state.generation === generation;
    setError('');
    setStatus('opening');
    const request = async (path, options) => {
      const response = await apiFetch(apiUrl(path), { ...options, signal: AbortSignal.timeout(45000) });
      if (!response.ok) {
        const requestError = new Error(await readError(response, t('Không kết nối được CTT. Vui lòng thử lại.', 'School connection failed. Please try again.')));
        if (response.status === 429) requestError.retryAfter = Math.min(300, Math.max(1, Number(response.headers.get('Retry-After')) || 15));
        throw requestError;
      }
      return response.json();
    };
    const fail = (err) => {
      if (!active()) return;
      if (state.attempt) abandon(state.attempt);
      state.attempt = null;
      state.running = false;
      setStatus('error');
      setRetryAfter(err.retryAfter || 0);
      setError(err.message || t('Không kết nối được máy chủ.', 'Cannot reach the server.'));
    };
    try {
      const data = await request('/api/auth/ctt/start', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ program_code: program }),
      });
      if (!active()) { abandon(data.attempt_id); return; }
      state.attempt = data.attempt_id;
      const poll = async () => {
        if (!active()) return;
        try {
          const result = await request(`/api/auth/ctt/${data.attempt_id}/status`);
          if (!active()) return;
          if (result.status === 'error') throw new Error(result.error);
          if (result.status === 'ready') {
            setStatus('saving');
            const account = await request(`/api/auth/ctt/${data.attempt_id}/finish`, { method: 'POST' });
            state.attempt = null;
            state.running = false;
            if (!active()) return;
            setStatus('success');
            onConnectedRef.current?.(account);
            return;
          }
          setStatus(result.status);
          state.timer = setTimeout(poll, 1100);
        } catch (err) { fail(err); }
      };
      await poll();
    } catch (err) { fail(err); }
  };

  const cancel = () => {
    const state = connection.current;
    state.generation += 1;
    clearTimeout(state.timer);
    if (state.attempt) abandon(state.attempt);
    state.attempt = null;
    state.running = false;
    setStatus('idle');
    setError('');
  };

  const busy = BUSY.has(status);
  const progress = { opening: 0, waiting: 1, syncing: 2, saving: 2, success: 3 }[status] ?? -1;
  const statusText = {
    opening: t('Đang mở cửa sổ đăng nhập…', 'Opening the sign-in window…'),
    waiting: usbMode ? t('Hoàn tất đăng nhập trong cửa sổ CTT trên PC đang nối USB. Sau đó trở lại app này.', 'Finish signing in in the CTT window on the connected PC, then return to this app.') : t('Hoàn tất đăng nhập trong cửa sổ CTT vừa mở.', 'Finish signing in in the CTT window.'),
    syncing: t('Đang xác minh MSSV và đồng bộ dữ liệu CTT…', 'Verifying your identity and syncing CTT data…'),
    saving: t('Đang lưu hồ sơ học tập của bạn…', 'Saving your academic profile…'),
    success: t('Đã kết nối và đồng bộ bảng điểm.', 'Connected and transcript synced.'),
  }[status];

  return (
    <div className="school-connect">
      <div className="school-connect__portal">
        <span className="school-connect__portal-icon"><ShieldCheck size={22} /></span>
        <div><strong>{t('Cổng đào tạo HUST', 'HUST student portal')}</strong><span>ctt-sis.hust.edu.vn <ArrowUpRight size={12} /></span></div>
        <span className="school-connect__badge">{t('Trang trường', 'Official portal')}</span>
      </div>

      <ol className="school-connect__steps" aria-label={t('Các bước kết nối', 'Connection steps')}>
        {[
          [t('Mở trang trường', 'Open the portal'), usbMode ? t('Cửa sổ đăng nhập mở trên PC đang nối USB.', 'The sign-in window opens on the connected PC.') : t('Một cửa sổ trình duyệt riêng trên PC này.', 'A separate browser window on this PC.')],
          [t('Bạn tự đăng nhập', 'Sign in yourself'), t('Nhập tài khoản, CAPTCHA hoặc xác thực Office 365.', 'Enter your account, CAPTCHA or Office 365 verification.')],
          [t('Nhận hồ sơ và bảng điểm', 'Sync your profile and grades'), t('Trở lại đây, ứng dụng sẽ tự hoàn tất.', 'Return here. We will finish automatically.')],
        ].map(([title, detail], i) => (
          <li key={title} className={progress > i ? 'is-done' : progress === i ? 'is-current' : ''}>
            <span className="school-connect__step-number">{progress > i ? <Check size={13} /> : i + 1}</span>
            <div><strong>{title}</strong><span>{detail}</span></div>
          </li>
        ))}
      </ol>

      {available === false && <div className="school-connect__notice">{t(
        'Kết nối trực tiếp hiện dùng trên PC chạy HUST Advisor. Bạn có thể dùng tài khoản Advisor và nhập bảng điểm khi mở web từ thiết bị khác.',
        'Direct connection is available on the PC running HUST Advisor. On other devices, use an Advisor account and import your transcript.',
      )}</div>}
      {error && <div className="school-connect__error" role="alert">{error}</div>}
      {statusText && <div className="school-connect__status" role="status" aria-live="polite">
        {status === 'success' ? <CheckCircle2 size={17} /> : <Loader2 size={17} className="spin" />}<span>{statusText}</span>
      </div>}

      <button type="button" className="auth-submit school-connect__submit" onClick={start} disabled={busy || retryAfter > 0 || available === false || status === 'success'}>
        {busy ? <Loader2 size={17} className="spin" /> : <ExternalLink size={17} />}
        {retryAfter > 0 ? t(`Thử lại sau ${retryAfter} giây`, `Try again in ${retryAfter}s`) : busy ? t('Đang kết nối với trường', 'Connecting to HUST') : t(status === 'error' ? 'Thử kết nối lại' : 'Tiếp tục với tài khoản trường', status === 'error' ? 'Try again' : 'Continue with HUST')}
      </button>
      {busy && status !== 'saving' && <button type="button" className="school-connect__cancel" onClick={cancel}>{t('Hủy kết nối', 'Cancel connection')}</button>}
      <p className="school-connect__privacy"><ShieldCheck size={14} />{t('HUST Advisor không nhận hoặc lưu mật khẩu trường.', 'HUST Advisor never receives or stores your school password.')}</p>
    </div>
  );
}
