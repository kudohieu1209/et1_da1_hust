import React, { useState } from 'react';
import { Loader2, LogOut } from 'lucide-react';
import { apiFetch, apiUrl, readError } from '../../api';

const MIN_PASSWORD_LENGTH = 8;
const EMPTY = { current: '', next: '', confirm: '' };

/** Tab "Tài khoản": đổi mật khẩu và đăng xuất. */
export default function AccountSecurity({ account, language, onPasswordChanged, onLogout }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState({ state: 'idle', message: '' });
  const isSaving = status.state === 'saving';

  const setField = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (form.next.length < MIN_PASSWORD_LENGTH) {
      setStatus({ state: 'error', message: t(`Mật khẩu mới cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự.`, `New password needs ${MIN_PASSWORD_LENGTH}+ characters.`) });
      return;
    }
    if (form.next !== form.confirm) {
      setStatus({ state: 'error', message: t('Mật khẩu nhập lại không khớp.', 'Passwords do not match.') });
      return;
    }
    setStatus({ state: 'saving', message: '' });
    try {
      const response = await apiFetch(apiUrl('/api/auth/password'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: form.current, new_password: form.next }),
      });
      if (!response.ok) {
        setStatus({ state: 'error', message: await readError(response, t('Không đổi được mật khẩu.', 'Could not change password.')) });
        return;
      }
      setForm(EMPTY);
      // Backend thu hồi mọi phiên (kể cả phiên này) sau khi đổi mật khẩu.
      onPasswordChanged?.();
    } catch {
      setStatus({ state: 'error', message: t('Không kết nối được máy chủ.', 'Could not reach the server.') });
    }
  };

  return (
    <>
      <section className="settings-section">
        <h3>{t('Tài khoản', 'Account')}</h3>
        <dl className="settings-readonly">
          <dt>MSSV</dt>
          <dd>{account?.student_id || '—'}</dd>
          {account?.is_demo && (
            <>
              <dt>{t('Loại', 'Type')}</dt>
              <dd>{t('Tài khoản demo', 'Demo account')}</dd>
            </>
          )}
        </dl>
      </section>

      <form className="settings-section" onSubmit={handleSubmit}>
        <h3>{t('Đổi mật khẩu', 'Change password')}</h3>
        <p className="settings-hint">
          {t('Sau khi đổi, mọi thiết bị đều bị đăng xuất và bạn cần đăng nhập lại.', 'All devices are signed out after the change.')}
        </p>
        <div className="settings-field">
          <label htmlFor="password-current">{t('Mật khẩu hiện tại', 'Current password')}</label>
          <input id="password-current" type="password" className="settings-input" autoComplete="current-password" value={form.current} onChange={setField('current')} required />
        </div>
        <div className="settings-field">
          <label htmlFor="password-new">{t('Mật khẩu mới', 'New password')}</label>
          <input id="password-new" type="password" className="settings-input" autoComplete="new-password" value={form.next} onChange={setField('next')} required />
        </div>
        <div className="settings-field">
          <label htmlFor="password-confirm">{t('Nhập lại mật khẩu mới', 'Confirm new password')}</label>
          <input id="password-confirm" type="password" className="settings-input" autoComplete="new-password" value={form.confirm} onChange={setField('confirm')} required />
        </div>
        <div className="settings-actions">
          {status.message && (
            <span className={`settings-status${status.state === 'error' ? ' is-error' : ''}`} role="status">
              {status.message}
            </span>
          )}
          <button type="submit" className="settings-button settings-button--primary" disabled={isSaving}>
            {isSaving && <Loader2 size={15} className="spin" aria-hidden="true" />}
            {isSaving ? t('Đang đổi…', 'Saving…') : t('Đổi mật khẩu', 'Change password')}
          </button>
        </div>
      </form>

      <section className="settings-section">
        <h3>{t('Đăng xuất', 'Log out')}</h3>
        <div className="settings-actions" style={{ justifyContent: 'flex-start' }}>
          <button type="button" className="settings-button" onClick={onLogout}>
            <LogOut size={15} aria-hidden="true" />
            {t('Đăng xuất khỏi thiết bị này', 'Log out of this device')}
          </button>
        </div>
      </section>
    </>
  );
}
