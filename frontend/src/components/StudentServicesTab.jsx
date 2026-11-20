import React, { useState } from 'react';
import { useSchoolServices } from '../schoolData';
import { SchoolDataHeader, SchoolSectionState, RawSchoolTables } from './SchoolDataPanel';
import ClassmatesPanel from './services/ClassmatesPanel';
import TuitionPanel from './services/TuitionPanel';
import './services/services.css';

export default function StudentServicesTab({ syncVersion, onOpenImport, language = 'vi' }) {
  const { sections, loading, error } = useSchoolServices(syncVersion);
  const [tab, setTab] = useState('tuition');
  const t = (vi, en) => language === 'en' ? en : vi;
  const tabs = { tuition: t('Học phí', 'Tuition'), classmates: t('Bạn cùng lớp', 'Classmates') };
  const selected = sections[tab];
  return (
    <div className="school-data-page services-page">
      <SchoolDataHeader title={t('Thông tin sinh viên từ CTT', 'Student services from CTT')}
        subtitle={t('Xem học phí và danh sách bạn cùng lớp.', 'View your tuition and class roster.')} onSync={onOpenImport} />
      <nav className="school-data-tabs" aria-label={t('Thông tin sinh viên', 'Student services')}>
        {Object.entries(tabs).map(([key, label]) => (
          <button type="button" key={key} className={tab === key ? 'is-active' : ''} aria-pressed={tab === key}
            onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>
      <p className="school-data-provenance">
        {t('Chuẩn tiếng Anh, GDTC/GDQP và cảnh báo học tập đã chuyển sang tab Tiến độ.',
          'English requirements, PE and national defense coursework, and academic warnings are now in Degree Audit.')}
      </p>
      {error && <p className="school-data-error" role="alert">{t(error, 'Unable to load synced school data.')}</p>}
      {loading ? <p className="school-data-empty" role="status">{t('Đang tải dữ liệu đã đồng bộ…', 'Loading synced data…')}</p> : <>
        <SchoolSectionState section={selected} onSync={onOpenImport} title={tabs[tab]} />
        {tab === 'tuition' ? <TuitionPanel section={selected} t={t} /> : <ClassmatesPanel section={selected} t={t} />}
        <RawSchoolTables section={selected} collapsed />
      </>}
    </div>
  );
}
