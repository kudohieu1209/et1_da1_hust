import React, { useEffect, useState } from 'react';
import { apiFetch, apiUrl, readError } from '../../api';

const EMPTY = { enabled: false, target_track: '', max_credits: '', target_cpa: '' };
const toForm = (data) => Object.fromEntries(Object.keys(EMPTY).map((key) => [key, data[key] ?? EMPTY[key]]));

export default function AdvisingMemory({ language }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [form, setForm] = useState(EMPTY);
  const [tracks, setTracks] = useState([]);
  const [status, setStatus] = useState({ state: 'loading', message: '' });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      setStatus({ state: 'loading', message: '' });
      try {
        const [memory, trackResponse] = await Promise.all([
          apiFetch(apiUrl('/api/student/memory'), { signal: controller.signal }),
          apiFetch(apiUrl('/api/student/tracks'), { signal: controller.signal }),
        ]);
        if (!memory.ok || !trackResponse.ok) throw new Error();
        const [saved, available] = await Promise.all([memory.json(), trackResponse.json()]);
        if (controller.signal.aborted) return;
        setForm(toForm(saved));
        setTracks(available.tracks);
        setStatus({ state: 'idle', message: '' });
      } catch {
        if (!controller.signal.aborted) setStatus({ state: 'load-error', message: 'Không tải được ghi nhớ. / Could not load preferences.' });
      }
    };
    load();
    return () => controller.abort();
  }, [retry]);

  const save = async (event) => {
    event.preventDefault();
    setStatus({ state: 'saving', message: '' });
    try {
      const response = await apiFetch(apiUrl('/api/student/memory'), {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: form.enabled,
          target_track: form.target_track || null,
          max_credits: form.max_credits === '' ? null : Number(form.max_credits),
          target_cpa: form.target_cpa === '' ? null : Number(form.target_cpa),
        }),
      });
      if (!response.ok) throw new Error(await readError(response, t('Không lưu được ghi nhớ.', 'Could not save preferences.')));
      setForm(toForm(await response.json()));
      setStatus({ state: 'idle', message: t('Đã lưu mục tiêu học tập.', 'Study goals saved.') });
    } catch (error) {
      setStatus({ state: 'error', message: error.message });
    }
  };

  const clear = async () => {
    setStatus({ state: 'saving', message: '' });
    try {
      const response = await apiFetch(apiUrl('/api/student/memory'), { method: 'DELETE' });
      if (!response.ok) throw new Error();
      setForm(EMPTY);
      setStatus({ state: 'idle', message: t('Đã xóa ghi nhớ. Các gợi ý mới sẽ dùng hồ sơ hiện tại.', 'Preferences deleted. New recommendations use your current profile.') });
    } catch {
      setStatus({ state: 'error', message: t('Không xóa được ghi nhớ. Hãy thử lại.', 'Could not delete preferences. Try again.') });
    }
  };

  if (status.state === 'loading') return <p role="status">{t('Đang tải ghi nhớ…', 'Loading preferences…')}</p>;
  if (status.state === 'load-error') return <div><p role="alert">{status.message}</p><button type="button" className="settings-button" onClick={() => setRetry(retry + 1)}>{t('Thử lại', 'Retry')}</button></div>;
  const saving = status.state === 'saving';
  const setField = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  return (
    <form className="settings-section" onSubmit={save}>
      <h3>{t('Ghi nhớ học tập', 'Study preferences')}</h3>
      <p className="settings-hint">{t('Bạn chọn những mục tiêu trợ lý được dùng trong các lần gợi ý môn sau, kể cả đoạn chat mới. Bạn có thể sửa hoặc xóa bất cứ lúc nào.', 'Choose goals for future course recommendations, including new chats. Edit or delete them at any time.')}</p>
      <fieldset className="memory-fields" disabled={saving}>
        <label className="memory-toggle"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} />{t('Dùng mục tiêu đã lưu để tư vấn', 'Use saved goals for advice')}</label>
        <div className="settings-field">
          <label htmlFor="memory-track">{t('Định hướng ưu tiên', 'Preferred track')}</label>
          <select id="memory-track" className="settings-input" value={form.target_track} onChange={setField('target_track')}>
            <option value="">{t('Chưa chọn', 'Not selected')}</option>
            {form.target_track && !tracks.some((track) => track.id === form.target_track) && <option value={form.target_track}>{t('Mô-đun cũ — hãy chọn lại', 'Previous track — select again')}</option>}
            {tracks.map((track) => <option key={track.id} value={track.id}>{track.name}</option>)}
          </select>
        </div>
        <div className="settings-field">
          <label htmlFor="memory-credits">{t('Số tín chỉ tối đa mong muốn mỗi kỳ', 'Preferred maximum credits per term')}</label>
          <input id="memory-credits" type="number" min="1" max="30" step="1" className="settings-input" value={form.max_credits} onChange={setField('max_credits')} placeholder={t('Theo mặc định', 'Use default')} />
        </div>
        <div className="settings-field">
          <label htmlFor="memory-cpa">{t('Mục tiêu CPA (thang 4)', 'Target CPA (4-point scale)')}</label>
          <input id="memory-cpa" type="number" min="0" max="4" step="0.01" className="settings-input" value={form.target_cpa} onChange={setField('target_cpa')} placeholder={t('Chưa đặt mục tiêu', 'No target yet')} />
        </div>
        <p className="settings-hint">{t('Lựa chọn trong câu hỏi hiện tại được ưu tiên. Số tín chỉ vẫn chịu giới hạn học vụ. Mục tiêu CPA được ghi nhận; tính năng mô phỏng điểm sẽ được bổ sung sau.', 'Your current question takes priority. Academic credit limits still apply. CPA goals are saved; grade simulation will follow.')}</p>
        <div className="settings-actions">
          <button type="button" className="settings-button" onClick={clear}>{t('Xóa ghi nhớ', 'Delete preferences')}</button>
          <button type="submit" className="settings-button settings-button--primary">{saving ? t('Đang lưu…', 'Saving…') : t('Lưu mục tiêu', 'Save goals')}</button>
        </div>
      </fieldset>
      {status.message && <p className={`settings-status${status.state === 'error' ? ' is-error' : ''}`} role="status">{status.message}</p>}
    </form>
  );
}
