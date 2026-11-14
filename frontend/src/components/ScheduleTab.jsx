import { useSchoolServices, display } from '../schoolData';
import React, { useRef, useState } from 'react';
import { apiFetch, apiUrl, readError } from '../api';
import { SchoolDataHeader, SchoolSectionState, RawSchoolTables, DataTable } from './SchoolDataPanel';

const DAYS = { 2: 'Thứ Hai', 3: 'Thứ Ba', 4: 'Thứ Tư', 5: 'Thứ Năm', 6: 'Thứ Sáu', 7: 'Thứ Bảy', 8: 'Chủ Nhật' };

export default function ScheduleTab({ syncVersion, onOpenImport }) {
  const { sections, loading, error, reload } = useSchoolServices(syncVersion);
  const [tab, setTab] = useState('timetable');
  const [preview, setPreview] = useState([]);
  const [checked, setChecked] = useState(new Set());
  const [fileError, setFileError] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef(null);
  const main = sections.timetable;
  const temporary = sections.temporary_timetable;
  const classes = [...(main?.records || []), ...(temporary?.records || [])];
  const selected = sections[tab];

  const readPdf = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileError('');
    setPreview([]);
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const response = await apiFetch(apiUrl('/api/student/exams/preview'), { method: 'POST', body: form });
      if (!response.ok) throw new Error(await readError(response, 'Không đọc được PDF lịch thi.'));
      const data = await response.json();
      setPreview(data.records || []);
      setChecked(new Set());
    } catch (err) { setFileError(err.message); }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = ''; }
  };
  const saveExams = async () => {
    if (!checked.size) return;
    setFileError('');
    setUploading(true);
    try {
      const response = await apiFetch(apiUrl('/api/student/exams/import'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exams: preview.filter((_, i) => checked.has(i)) }),
      });
      if (!response.ok) throw new Error(await readError(response, 'Không lưu được lịch thi.'));
      setPreview([]);
      setChecked(new Set());
      reload();
    } catch (err) { setFileError(err.message); }
    finally { setUploading(false); }
  };
  return <div className="school-data-page">
    <SchoolDataHeader title="Thời khóa biểu & Lịch thi" subtitle="Dữ liệu CTT đã đồng bộ và lịch thi PDF do bạn xác nhận." onSync={onOpenImport} />
    <nav className="school-data-tabs" aria-label="Lịch học và lịch thi">
      <button type="button" className={tab === 'timetable' ? 'is-active' : ''} aria-pressed={tab === 'timetable'} onClick={() => setTab('timetable')}>Thời khóa biểu</button>
      <button type="button" className={tab === 'exams' ? 'is-active' : ''} aria-pressed={tab === 'exams'} onClick={() => setTab('exams')}>Lịch thi</button>
    </nav>
    {error && <p className="school-data-error" role="alert">{error}</p>}
    {loading ? <p className="school-data-empty" role="status">Đang tải lịch đã đồng bộ…</p> : <>
      <SchoolSectionState section={selected} onSync={onOpenImport} title={tab === 'exams' ? 'Lịch thi' : 'Lịch chính thức'} />
      {tab === 'timetable' ? <>
        <SchoolSectionState section={temporary} onSync={onOpenImport} title="Lịch tạm thời" />
        {!classes.length && <p className="school-data-empty">Chưa có lớp đã chuẩn hóa. Nếu CTT đã trả về bảng, bạn có thể xem bảng dữ liệu bên dưới.</p>}
        <div className="school-data-grid">{Object.entries(DAYS).filter(([day]) => classes.some((row) => Number(row.day_of_week) === Number(day))).map(([day, label]) =>
          <section className="school-data-card" key={day}><h3>{label}</h3>{classes.filter((row) => Number(row.day_of_week) === Number(day)).sort((a, b) => a.start_period - b.start_period).map((row, i) =>
            <article className="school-data-class" key={row.id || i}><strong>{row.course_code} · {display(row.course_name)}</strong>
              <span>{row.time_str || 'Tiết ' + row.start_period + '–' + row.end_period} · {display(row.room)}</span>
              <span>Lớp {display(row.class_code)} · Tuần {display(row.weeks)}</span>
              {row.lecturer && <span>{row.lecturer}</span>}{row.is_temp && <span className="school-data-badge">Lớp tạm thời</span>}
            </article>)}</section>)}</div>
        <RawSchoolTables section={main} /><RawSchoolTables section={temporary} />
      </> : <>
        <DataTable rows={sections.exams?.records || []} columns={[[ 'course_code', 'Mã HP' ], ['course_name', 'Học phần'], ['class_code', 'Mã lớp'], ['exam_date', 'Ngày thi'], ['exam_time', 'Giờ / ca'], ['room', 'Phòng'], ['exam_type', 'Hình thức'], ['student_index', 'SBD']]} />
        <RawSchoolTables section={sections.exams} />
        <section className="school-data-card school-data-file"><h3>Nhập PDF lịch thi</h3>
          <p>Nếu CTT không có trang lịch thi, chọn PDF có lớp văn bản do trường cung cấp. Bạn sẽ chọn đúng lớp và ca thi trước khi lưu. PDF ảnh quét cần được chuyển sang văn bản trước.</p>
          <input ref={fileInput} type="file" accept=".pdf,application/pdf" aria-label="Chọn PDF lịch thi" onChange={readPdf} disabled={uploading} />
          {uploading && <p role="status">Đang xử lý…</p>}
          {fileError && <p className="school-data-error" role="alert">{fileError}</p>}
          {!!preview.length && <><p>Đọc được {preview.length} ca thi. Chọn các ca thuộc lịch của bạn:</p>
            <DataTable rows={preview.map((row, i) => ({ ...row, selected: i }))} columns={[
              ['selected', 'Chọn', (i) => <input type="checkbox" aria-label={'Chọn ca thi ' + (i + 1)} checked={checked.has(i)} onChange={() => setChecked((current) => { const next = new Set(current); if (next.has(i)) next.delete(i); else next.add(i); return next; })} />],
              ['course_code', 'Mã HP'], ['course_name', 'Học phần'], ['class_code', 'Mã lớp'], ['exam_date', 'Ngày'], ['exam_time', 'Giờ / ca'], ['room', 'Phòng'],
            ]} />
            <button type="button" className="school-data-secondary" disabled={uploading || !checked.size} onClick={saveExams}>Xác nhận và lưu {checked.size} ca thi đã chọn</button>
          </>}
        </section>
      </>}
    </>}
  </div>;
}
