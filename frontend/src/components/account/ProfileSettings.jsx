import React, { useEffect, useRef, useState } from 'react';
import { Camera, Loader2, RotateCcw, Upload } from 'lucide-react';
import { apiFetch, apiUrl } from '../../api';
import Avatar from './Avatar';
import { ACCEPTED_AVATAR_TYPES, resizeAvatar } from './imageResize';
import { AVATAR_GRADIENTS, buildStudentSummary, getInitials, programLabel } from './studentSummary';

/** Chuỗi lỗi đọc được từ phản hồi FastAPI (detail dạng chuỗi hoặc danh sách lỗi Pydantic). */
async function readErrorDetail(response, fallback) {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join('; ');
  } catch {
    // Phản hồi không phải JSON: dùng thông báo mặc định.
  }
  return fallback;
}

/**
 * Tab "Hồ sơ": chỉ sửa tên hiển thị và ảnh đại diện. MSSV/lớp/CTĐT đến từ hồ
 * sơ hoặc bảng điểm nên chỉ hiển thị, kèm lối tắt sang "Nhập lại bảng điểm".
 */
export default function ProfileSettings({ studentProfile, auditData, language, onProfileUpdated, onImportTranscript, onShowToast }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const summary = buildStudentSummary(studentProfile, auditData);
  const [name, setName] = useState(summary.name);
  const [avatar, setAvatar] = useState(summary.avatar);
  const [status, setStatus] = useState({ state: 'idle', message: '' });
  const fileInputRef = useRef(null);

  useEffect(() => {
    const fresh = buildStudentSummary(studentProfile, auditData);
    setName(fresh.name);
    setAvatar(fresh.avatar);
    setStatus({ state: 'idle', message: '' });
    // Chỉ đặt lại form khi đổi sang hồ sơ khác hoặc hồ sơ vừa được lưu.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentProfile]);

  const changes = {};
  const trimmedName = name.trim().replace(/\s+/g, ' ');
  if (trimmedName !== summary.name) changes.student_name = trimmedName;
  if (avatar.url !== summary.avatar.url) changes.avatar_url = avatar.url;
  if (avatar.emoji !== summary.avatar.emoji) changes.avatar_emoji = avatar.emoji;
  if (avatar.gradient !== summary.avatar.gradient) changes.avatar_gradient = avatar.gradient;
  const isDirty = Object.keys(changes).length > 0;
  const isSaving = status.state === 'saving';

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    try {
      const url = await resizeAvatar(file);
      setAvatar((current) => ({ ...current, url, emoji: '' }));
      setStatus({ state: 'idle', message: '' });
    } catch (error) {
      const message =
        error.message === 'type'
          ? t('Chỉ nhận ảnh PNG, JPEG hoặc WebP.', 'Only PNG, JPEG or WebP images are supported.')
          : error.message === 'size'
            ? t('Ảnh quá lớn (tối đa 10MB).', 'Image is too large (max 10MB).')
            : t('Không đọc được ảnh này.', 'This image could not be read.');
      setStatus({ state: 'error', message });
    }
  };

  const handleSave = async (event) => {
    event.preventDefault();
    if (!trimmedName) {
      setStatus({ state: 'error', message: t('Tên hiển thị không được để trống.', 'Display name cannot be empty.') });
      return;
    }
    setStatus({ state: 'saving', message: '' });
    try {
      const response = await apiFetch(apiUrl('/api/student/profile/update'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(changes),
      });
      if (!response.ok) {
        const message = await readErrorDetail(response, t('Không lưu được hồ sơ.', 'Could not save the profile.'));
        setStatus({ state: 'error', message });
        return;
      }
      onProfileUpdated?.(await response.json());
      onShowToast?.(t('Đã lưu hồ sơ', 'Profile saved'));
    } catch {
      setStatus({ state: 'error', message: t('Không kết nối được máy chủ.', 'Could not reach the server.') });
    }
  };

  const program = programLabel(summary);

  return (
    <form onSubmit={handleSave}>
      <section className="settings-section">
        <h3>{t('Ảnh đại diện', 'Avatar')}</h3>
        <p className="settings-hint">
          {t('Ảnh được cắt vuông và thu về 256px trước khi lưu.', 'Images are cropped square and resized to 256px before saving.')}
        </p>
        <div className="settings-avatar-row">
          <Avatar avatar={avatar} initial={getInitials(trimmedName)} size={64} />
          <div>
            <div className="settings-avatar-actions">
              <button type="button" className="settings-button" onClick={() => fileInputRef.current?.click()}>
                <Camera size={15} aria-hidden="true" />
                {t('Tải ảnh lên', 'Upload photo')}
              </button>
              {(avatar.url || avatar.emoji) && (
                <button
                  type="button"
                  className="settings-button"
                  onClick={() => setAvatar((current) => ({ ...current, url: '', emoji: '' }))}
                >
                  <RotateCcw size={15} aria-hidden="true" />
                  {t('Dùng chữ cái đầu', 'Use initial')}
                </button>
              )}
            </div>
            {!avatar.url && (
              <div className="settings-swatches" role="radiogroup" aria-label={t('Màu nền', 'Background colour')}>
                {AVATAR_GRADIENTS.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    role="radio"
                    aria-checked={avatar.gradient === option.value}
                    aria-label={t(option.vi, option.en)}
                    title={t(option.vi, option.en)}
                    className="settings-swatch"
                    style={{ background: option.value }}
                    onClick={() => setAvatar((current) => ({ ...current, gradient: option.value }))}
                  />
                ))}
              </div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_AVATAR_TYPES.join(',')}
            hidden
            onChange={handleFile}
          />
        </div>
      </section>

      <section className="settings-section">
        <div className="settings-field">
          <label htmlFor="settings-display-name">{t('Tên hiển thị', 'Display name')}</label>
          <input
            id="settings-display-name"
            className="settings-input"
            value={name}
            maxLength={80}
            autoComplete="name"
            onChange={(event) => setName(event.target.value)}
          />
        </div>
      </section>

      <section className="settings-section">
        <h3>{t('Thông tin đào tạo', 'Academic record')}</h3>
        <p className="settings-hint">
          {t(
            'Lấy từ tài khoản và bảng điểm nên không sửa tay ở đây. Muốn cập nhật tiến độ, hãy nhập lại bảng điểm.',
            'Comes from your account and transcript, so it cannot be edited here. Re-import the transcript to update it.',
          )}
        </p>
        <dl className="settings-readonly">
          <dt>MSSV</dt>
          <dd>{summary.studentId || '—'}</dd>
          <dt>{t('Lớp', 'Class')}</dt>
          <dd>{summary.className || '—'}</dd>
          <dt>{t('CTĐT', 'Program')}</dt>
          <dd>{[summary.programName, program && `(${program})`].filter(Boolean).join(' ') || '—'}</dd>
        </dl>
        <div className="settings-actions" style={{ justifyContent: 'flex-start', marginTop: 10 }}>
          <button type="button" className="settings-button" onClick={onImportTranscript}>
            <Upload size={15} aria-hidden="true" />
            {t('Nhập lại bảng điểm', 'Re-import transcript')}
          </button>
        </div>
      </section>

      <div className="settings-actions">
        {status.message && (
          <span className={`settings-status${status.state === 'error' ? ' is-error' : ''}`} role="status">
            {status.message}
          </span>
        )}
        <button type="submit" className="settings-button settings-button--primary" disabled={!isDirty || isSaving}>
          {isSaving && <Loader2 size={15} className="spin" aria-hidden="true" />}
          {isSaving ? t('Đang lưu…', 'Saving…') : t('Lưu thay đổi', 'Save changes')}
        </button>
      </div>
    </form>
  );
}
