import React, { useEffect, useMemo, useState } from 'react';
import { apiFetch, apiUrl, readError } from '../api';
import './ProgramsTab.css';

function sourceLink(url) {
  return /^https?:\/\//i.test(url || '') ? url : null;
}

export default function ProgramsTab() {
  const [programs, setPrograms] = useState([]);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState('');
  const [data, setData] = useState(null);
  const [version, setVersion] = useState('');
  const [courseQuery, setCourseQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    apiFetch(apiUrl('/api/programs'), { signal: controller.signal })
      .then(async res => {
        if (!res.ok) throw new Error(await readError(res, 'Không tải được danh mục chương trình.'));
        return res.json();
      })
      .then(result => {
        const list = result.programs || [];
        setPrograms(list);
        setSelected(current => current || list[0]?.admission_code || '');
      })
      .catch(err => { if (err.name !== 'AbortError') { setError(err.message); setLoading(false); } });
    return () => controller.abort();
  }, [retry]);

  useEffect(() => {
    if (!selected) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setData(null);
    setCourseQuery('');
    apiFetch(apiUrl(`/api/programs/${encodeURIComponent(selected)}/curricula`), { signal: controller.signal })
      .then(async res => {
        if (!res.ok) throw new Error(await readError(res, 'Không tải được dữ liệu chương trình.'));
        return res.json();
      })
      .then(result => {
        setData(result);
        setVersion(result.curricula?.[0]?.id || '');
      })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selected, retry]);

  const filtered = useMemo(() => programs.filter(p =>
    `${p.admission_code} ${p.name} ${p.faculty}`.toLocaleLowerCase('vi').includes(query.trim().toLocaleLowerCase('vi'))
  ), [programs, query]);
  const curriculum = data?.curricula?.find(c => c.id === version);
  const matchesCourse = c => `${c.code || ''} ${c.name || ''}`.toLocaleLowerCase('vi')
    .includes(courseQuery.trim().toLocaleLowerCase('vi'));

  return (
    <section className="program-browser">
      <header className="program-browser__header">
        <h2>Tra cứu chương trình đào tạo</h2>
        <p>Toàn bộ {programs.length || '…'} ngành trong danh mục, cùng tài liệu và học phần đã thu thập.</p>
      </header>
      <div className="program-browser__layout">
        <nav className="program-browser__list" aria-label="Danh sách chương trình">
          <label htmlFor="program-search">Tìm ngành</label>
          <input id="program-search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Mã ngành, tên ngành, trường/khoa..." />
          <p className="program-browser__muted">{filtered.length} chương trình</p>
          <div className="program-browser__results">
            {filtered.map(p => (
              <button key={p.admission_code} type="button" aria-pressed={selected === p.admission_code}
                onClick={() => setSelected(p.admission_code)}>
                <strong>{p.admission_code}</strong><span>{p.name}</span>
                <small>{p.curriculum_supported ? 'Có rà soát tiến độ theo khóa' : 'Tra cứu tài liệu và học phần'}</small>
              </button>
            ))}
            {!filtered.length && <p>Không có ngành khớp từ khóa.</p>}
          </div>
        </nav>
        <div className="program-browser__detail" aria-live="polite">
          {error ? <div role="alert"><p>{error}</p><button type="button" onClick={() => setRetry(v => v + 1)}>Thử lại</button></div>
            : loading ? <p>Đang tải dữ liệu...</p>
              : data && <>
                <h3>{data.program.admission_code} — {data.program.name}</h3>
                <p className="program-browser__muted">{data.program.faculty}</p>
                {data.program.supported_cohorts.length > 0 && <p>Khóa có rà soát tiến độ: {data.program.supported_cohorts.join(', ')}.</p>}
                <label htmlFor="curriculum-version">Tài liệu đã thu thập</label>
                <select id="curriculum-version" value={version} onChange={e => { setVersion(e.target.value); setCourseQuery(''); }}>
                  {(data.curricula || []).map(c => <option key={c.id} value={c.id}>
                    {c.id} · {c.course_count} học phần · {c.applies_to_cohorts.join(', ') || 'Nguồn chưa xác định khóa áp dụng'}
                  </option>)}
                </select>
                {curriculum ? <>
                  <p className="program-browser__scope">{curriculum.scope_note || 'Bản này đã có dữ liệu chuẩn hóa để rà soát tiến độ cho các khóa được hỗ trợ.'}</p>
                  <p>Tổng tín chỉ nguồn ghi: <strong>{curriculum.total_credits ?? 'Chưa công bố trong tài liệu này'}</strong></p>
                  {sourceLink(curriculum.source_url) && <a href={curriculum.source_url} target="_blank" rel="noopener noreferrer">Mở nguồn chính thức ↗</a>}
                  <details className="program-browser__notes">
                    <summary>Phạm vi và ghi chú đối chiếu nguồn</summary>
                    {curriculum.graduation_rule && <p>{curriculum.graduation_rule}</p>}
                    <ul>{curriculum.notes.map((note, i) => <li key={i}>{note}</li>)}</ul>
                  </details>
                  <label htmlFor="course-search">Tìm học phần trong tài liệu</label>
                  <input id="course-search" value={courseQuery} onChange={e => setCourseQuery(e.target.value)} placeholder="Mã hoặc tên học phần..." />
                  {curriculum.groups.map((group, i) => {
                    const courses = group.courses.filter(matchesCourse);
                    if (courseQuery && !courses.length) return null;
                    return <section className="program-browser__group" key={i}>
                      <h4>{group.name}</h4>
                      <p className="program-browser__muted">{group.required_credits == null ? 'Nguồn chưa ghi ngưỡng tín chỉ của nhóm.' : `Ngưỡng ghi trong nguồn: ${group.required_credits} TC.`}</p>
                      {courses.length ? <div className="program-browser__table"><table>
                        <thead><tr><th>Mã môn</th><th>Tên học phần</th><th>TC</th><th>Kỳ gợi ý</th></tr></thead>
                        <tbody>{courses.map((c, j) => <tr key={j}>
                          <td>{c.code || 'Chưa ghi mã'}</td><td>{c.name || 'Chưa ghi tên'}</td>
                          <td>{c.credits ?? '—'}</td><td>{c.suggested_semester ?? '—'}</td>
                        </tr>)}</tbody>
                      </table></div> : <p>Chưa có bảng học phần chi tiết trong phần nguồn này.</p>}
                    </section>;
                  })}
                  {courseQuery && !curriculum.groups.some(g => g.courses.some(matchesCourse)) && <p>Không tìm thấy học phần trong tài liệu đang chọn.</p>}
                  {!curriculum.groups.length && <p>Nguồn hiện chỉ có thông tin giới thiệu; chưa công bố bảng học phần để trích xuất.</p>}
                </> : <p>Chưa có tài liệu trích xuất cho ngành này.</p>}
              </>}
        </div>
      </div>
    </section>
  );
}
