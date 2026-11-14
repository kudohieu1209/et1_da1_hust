import { useEffect, useState } from 'react';
import { apiFetch, apiUrl, readError } from './api';

export function useSchoolServices(version) {
  const [sections, setSections] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    (async () => {
      try {
        const res = await apiFetch(apiUrl('/api/student/school-services'), { signal: controller.signal });
        if (!res.ok) throw new Error(await readError(res, 'Chưa tải được dữ liệu đã đồng bộ.'));
        const data = await res.json();
        if (active) setSections(data.sections || {});
      } catch (err) { if (active) setError(err.message); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; controller.abort(); };
  }, [version, revision]);
  return { sections, loading, error, reload: () => setRevision((v) => v + 1) };
}

export const display = (value) => value == null || value === '' ? '—' : String(value);
export const money = (value) => typeof value === 'number' && Number.isFinite(value) ? `${new Intl.NumberFormat('vi-VN').format(value)} đ` : 'Chưa có dữ liệu';
export const certificateLabel = (value) => ({ completed: 'Đã hoàn thành', incomplete: 'Chưa hoàn thành', unverified: 'Chưa xác minh' }[value] || 'Chưa xác minh');

