import React from 'react';
import { useSchoolServices } from '../../schoolData';
import ResponsiveTable from '../services/ResponsiveTable';
import './english-standard.css';

export default function NonCreditEvidence({ language = 'vi', refreshKey }) {
  const { sections, loading } = useSchoolServices(refreshKey);
  const coursework = sections.certificates?.coursework ?? {};
  const t = (vi, en) => language === 'en' ? en : vi;
  const groups = [['220', t('GDTC', 'Physical education')], ['230', t('GDQP', 'National defense')]]
    .filter(([key]) => coursework[key]);
  if (loading || !groups.length) return null;
  return (
    <details className="school-data-card english-standard-card">
      <summary>{t('Căn cứ GDTC/GDQP', 'PE and national defense evidence')}</summary>
      {groups.map(([key, label]) => {
        const evidence = coursework[key];
        return <section className="english-standard-section" key={key}>
          <h4>{t(`Căn cứ ${label}`, `${label} evidence`)}</h4>
          <p>{evidence.passed_count}/{evidence.required_count} {t('học phần đạt', 'courses passed')} · {t('Nhóm', 'Group')} {evidence.source_group_code}</p>
          <ResponsiveTable rows={evidence.records} empty={t('Chưa có học phần để đối chiếu.', 'No coursework evidence available.')} columns={[
            ['course_code', t('Mã HP', 'Code')], ['course_name', t('Học phần', 'Course')],
            ['letter_grade', t('Điểm chữ', 'Grade')],
            ['is_passed', t('Kết quả', 'Result'), (passed) => passed ? t('Đạt', 'Passed') : t('Chưa ghi nhận đạt', 'Pass not recorded')],
          ]} />
          <p className="english-standard-source">{evidence.note}</p>
        </section>;
      })}
    </details>
  );
}
