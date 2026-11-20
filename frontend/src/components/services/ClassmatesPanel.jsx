import React, { useState } from 'react';
import ResponsiveTable from './ResponsiveTable';
import { compareClassmates } from './classmates';

export default function ClassmatesPanel({ section, t }) {
  const [query, setQuery] = useState('');
  const normalized = query.trim().toLocaleLowerCase('vi');
  const rows = (section?.records ?? []).filter((row) =>
    [row.student_id, row.student_name, row.class_name].some((value) => String(value ?? '').toLocaleLowerCase('vi').includes(normalized))
  ).sort(compareClassmates);
  const stamp = section?.synced_at && new Date(section.synced_at);
  const time = stamp && Number.isFinite(stamp.getTime())
    ? new Intl.DateTimeFormat(t('vi-VN', 'en-GB'), { dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Bangkok' }).format(stamp)
    : null;
  const searchLabel = t('Tìm bạn cùng lớp trong dữ liệu đã đồng bộ', 'Search synced classmates');
  return (
    <section className="services-stack" aria-label={t('Bạn cùng lớp', 'Classmates')}>
      <p className="school-data-provenance">
        {time ? <>{t('Lấy từ CTT lúc', 'Synced from CTT at')} <time dateTime={section.synced_at}>{time}</time>.</> : t('Chưa có thời điểm đồng bộ từ CTT.', 'No CTT sync time available.')}
        {' '}{t('Chỉ bạn xem được danh sách này.', 'Only you can see this list.')}
      </p>
      <div className="services-search">
        <input className="school-data-search" type="search" aria-label={searchLabel}
          placeholder={t('Tìm theo MSSV, họ tên hoặc lớp', 'Search by student ID, name or class')}
          value={query} onChange={(event) => setQuery(event.target.value)} />
        <p className="school-data-provenance" role="status">
          {rows.length} {normalized ? t('kết quả', rows.length === 1 ? 'result' : 'results') : t('sinh viên', rows.length === 1 ? 'student' : 'students')}
        </p>
      </div>
      <ResponsiveTable rows={rows}
        empty={normalized ? t('Không tìm thấy sinh viên phù hợp.', 'No matching students.') : t('Chưa có danh sách lớp từ CTT.', 'No class roster from CTT yet.')}
        columns={[[ 'student_id', t('MSSV', 'Student ID') ], ['student_name', t('Họ và tên', 'Full name')], ['class_name', t('Lớp', 'Class')]]} />
    </section>
  );
}
