import React, { useEffect, useRef, useState } from 'react';
import { Camera, Loader2, RotateCcw, Upload } from 'lucide-react';
import { apiFetch, apiUrl } from '../../api';
import Avatar from './Avatar';
import { ACCEPTED_AVATAR_TYPES, resizeAvatar } from './imageResize';
import { AVATAR_GRADIENTS, buildStudentSummary, getInitials } from './studentSummary';

const DEFAULT_PROGRAMS = [
  { code: 'ET1', name: 'Kỹ thuật Điện tử - Viễn thông' },
  { code: 'ET2', name: 'Kỹ thuật Y sinh' },
  { code: 'EE1', name: 'Kỹ thuật điện' },
  { code: 'EE2', name: 'Kỹ thuật Điều khiển - Tự động hóa' },
  { code: 'ME1', name: 'Kỹ thuật Cơ điện tử' },
  { code: 'BF1', name: 'Kỹ thuật Sinh học' },
  { code: 'BF2', name: 'Kỹ thuật Thực phẩm' },
  { code: 'BF-E19', name: 'Kỹ thuật sinh học (Chương trình tiên tiến)' },
  { code: 'EV1', name: 'Kỹ thuật Môi trường' },
  { code: 'EV2', name: 'Quản lý Tài nguyên và Môi trường' },
  { code: 'ED2', name: 'Công nghệ giáo dục' },
  { code: 'FL2', name: 'Tiếng Anh Chuyên nghiệp Quốc tế' },
  { code: 'FL3', name: 'Tiếng Trung Khoa học và Công nghệ' },
  { code: 'MS1', name: 'Kỹ thuật Vật liệu' },
  { code: 'TE-EP', name: 'Cơ khí hàng không (Chương trình Việt - Pháp PFIEV)' },
];

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
  const [programCode, setProgramCode] = useState(summary.programCode || 'ET1');
  const [availablePrograms, setAvailablePrograms] = useState([]);
  const [status, setStatus] = useState({ state: 'idle', message: '' });
  const fileInputRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch(apiUrl('/api/programs?supported_only=true'))
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data?.programs?.length) {
          setAvailablePrograms(data.programs);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const fresh = buildStudentSummary(studentProfile, auditData);
    setName(fresh.name);
    setAvatar(fresh.avatar);
    setProgramCode(fresh.programCode || 'ET1');
    setStatus({ state: 'idle', message: '' });
    // Chỉ đặt lại form khi đổi sang hồ sơ khác hoặc hồ sơ vừa được lưu.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentProfile, auditData]);

  const changes = {};
  const trimmedName = name.trim().replace(/\s+/g, ' ');
  if (trimmedName !== summary.name) changes.student_name = trimmedName;
  if (avatar.url !== summary.avatar.url) changes.avatar_url = avatar.url;
  if (avatar.emoji !== summary.avatar.emoji) changes.avatar_emoji = avatar.emoji;
  if (avatar.gradient !== summary.avatar.gradient) changes.avatar_gradient = avatar.gradient;
  if (programCode && programCode !== summary.programCode) changes.program_code = programCode;
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
            'Lớp và bảng điểm đồng bộ từ CTT. Bạn có thể đổi CTĐT bên dưới nếu học song bằng hoặc chương trình đặc biệt.',
            'Class and transcript are synced from CTT. You can change your program below if taking a dual or special degree.',
          )}
        </p>
        <dl className="settings-readonly">
          <dt>MSSV</dt>
          <dd>{summary.studentId || '—'}</dd>
          <dt>{t('Lớp', 'Class')}</dt>
          <dd>{summary.className || '—'}</dd>
          <dt>{t('Khóa', 'Cohort')}</dt>
          <dd>{summary.curriculumVersion ? `K${parseInt(summary.curriculumVersion, 10) - 1955} (${summary.curriculumVersion})` : '—'}</dd>
        </dl>

        <div className="settings-field" style={{ marginTop: 14 }}>
          <label htmlFor="settings-program-select">{t('Chương trình đào tạo (CTĐT)', 'Curriculum program')}</label>
          <select
            id="settings-program-select"
            className="settings-input"
            value={programCode}
            onChange={(event) => setProgramCode(event.target.value)}
          >
            {(availablePrograms.length > 0
              ? availablePrograms.map((p) => ({ code: p.admission_code || p.code, name: p.name }))
              : DEFAULT_PROGRAMS
            ).map((prog) => (
              <option key={prog.code} value={prog.code}>
                {prog.code} - {prog.name}
              </option>
            ))}
          </select>
          <p className="settings-hint" style={{ marginTop: 4 }}>
            {t(
              'Hệ thống tự nhận diện CTĐT theo lớp khi đăng nhập trường. Nếu học song bằng, chọn chương trình bạn muốn rà soát.',
              'Automatically detected from your class name upon sign in. If pursuing dual degrees, select your target program here.',
            )}
          </p>
        </div>

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
