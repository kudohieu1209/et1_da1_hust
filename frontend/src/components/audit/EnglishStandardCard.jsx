import React, { useEffect, useId, useState } from 'react';
import { apiFetch, apiUrl, readError } from '../../api';
import { display } from '../../schoolData';
import ResponsiveTable from '../services/ResponsiveTable';
import './english-standard.css';

function Requirements({ data, t }) {
  if (!data.rule) {
    const cohort = data.cohort ? `K${data.cohort}` : null;
    return <p>{cohort ? t(`Kho tài liệu chưa có quy định ngoại ngữ cho khóa ${cohort}.`, `No foreign language regulations for cohort ${cohort} are available in the document library.`)
      : t('Kho tài liệu chưa có quy định ngoại ngữ cho khóa chưa xác định.', 'No foreign language regulations are available for an unidentified cohort.')}
    {' '}{t('Trạng thái trên lấy từ CTT; hãy đối chiếu quy định hiện hành của trường.', 'The status above comes from CTT. Check the university’s current regulations.')}</p>;
  }
  const required = data.required;
  const graduation = required?.graduation;
  const tracks = {
    standard: t('CTĐT chuẩn', 'Standard program'),
    talent: t('CTĐT tài năng', 'Talent program'),
    elitech: 'ELITECH',
  };
  const table = data.track === 'elitech' ? '4.2' : '3.2';
  return (
    <div className="english-standard-section">
      <h4>{t('Yêu cầu với khóa của bạn', 'Requirements for your cohort')} · K{data.cohort}</h4>
      <p className="english-standard-source">{t('Quyết định', 'Decision')} {data.rule.decision}</p>
      {required ? <>
        <p>{t('Chuẩn tốt nghiệp', 'Graduation requirement')} · {tracks[data.track]}
          {graduation.level != null && <> · <strong>{t(`Tối thiểu Bậc ${graduation.level}`, `Level ${graduation.level} or above`)}</strong></>}
        </p>
        {graduation.note && <p>{graduation.note}</p>}
        <blockquote className="english-standard-source">“{graduation.quote}” <cite>· {t('Bảng', 'Table')} {table} · {graduation.source}</cite></blockquote>
        {required.registration_by_semester.length > 0 && <details>
          <summary>{t('Yêu cầu đăng ký theo kỳ', 'Registration requirements by semester')} · {t('Bảng', 'Table')} {table}</summary>
          <ResponsiveTable rows={required.registration_by_semester} columns={[
            ['semesters', t('Học kỳ', 'Semester'), (semesters) => semesters.join('–')],
            ['courses', t('Yêu cầu', 'Requirement'), (courses, row) => row.placement_table
              ? t(`Xếp lớp theo Bảng ${row.placement_table}`, `Placement according to Table ${row.placement_table}`)
              : t(`Học song hành ${courses.join(', ')} nếu chưa học hoặc chưa được miễn theo quy định.`,
                `Take ${courses.join(', ')} concurrently if still required under the regulations.`)],
          ]} />
        </details>}
      </> : <p>{t('Chưa xác định yêu cầu tiếng Anh cho CTĐT của bạn từ hồ sơ. Hãy đối chiếu văn bản theo CTĐT.',
        'Your profile does not specify an applicable English requirement. Check the decision for your program.')}</p>}
    </div>
  );
}

export default function EnglishStandardCard({ language = 'vi', onSync, refreshKey }) {
  const heading = useId();
  const [state, setState] = useState({ loading: true });
  const t = (vi, en) => language === 'en' ? en : vi;
  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true }));
    (async () => {
      try {
        const response = await apiFetch(apiUrl('/api/student/english-standard'), { signal: controller.signal });
        if (!response.ok) throw new Error(await readError(response, 'Chưa tải được chuẩn tiếng Anh.'));
        const data = await response.json();
        if (!controller.signal.aborted) setState({ data, loading: false });
      } catch (error) {
        if (!controller.signal.aborted) setState({ error: error.message, loading: false });
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  const { data, error, loading } = state;
  const status = data?.ctt_status;
  const latest = data?.latest;
  const skills = [
    ['listening', t('Nghe', 'Listening')], ['reading', t('Đọc', 'Reading')],
    ['speaking', t('Nói', 'Speaking')], ['writing', t('Viết', 'Writing')],
  ];
  const skillsSummary = skills.filter(([key]) => latest?.[key] != null)
    .map(([key, label]) => `${label} ${latest[key]}`).join(' · ');
  const badge = status === 'completed' ? ['success', t('Đã đạt', 'Met')]
    : status === 'incomplete' ? ['danger', t('Chưa đạt', 'Unmet')]
      : ['warning', t('Chưa xác minh', 'Unverified')];

  return (
    <section className="school-data-card english-standard-card" aria-labelledby={heading}>
      <header>
        <h3 id={heading}>{t('Chuẩn tiếng Anh', 'English standard')}</h3>
        {data && <span className={`badge badge-${badge[0]}`}>CTT · {badge[1]}</span>}
      </header>
      {loading && <p role="status">{t('Đang tải dữ liệu CTT…', 'Loading CTT data…')}</p>}
      {error && !loading && <p className="school-data-error" role="alert">{t(error, 'Unable to load the English standard.')}</p>}
      {data && <>
        {latest ? <div className="english-standard-section">
          <p>{t('Điểm mới nhất', 'Latest score')} · <strong>{display(latest.score ?? skillsSummary)}</strong></p>
          <p>{display(latest.test_date)} · {display(latest.certificate_type)}</p>
          {data.estimated_level && <p>{t(`≈ Bậc ${data.estimated_level} theo Bảng 2.1`, `≈ Level ${data.estimated_level} under Table 2.1`)}</p>}
        </div> : <p>{t('Chưa có điểm thi từ CTT.', 'No test scores from CTT yet.')}</p>}
        <Requirements data={data} t={t} />
        {data.history.length > 0 && <details className="english-standard-history">
          <summary>{t('Lịch sử thi', 'Test history')} ({data.history.length})</summary>
          <ResponsiveTable rows={data.history} columns={[
            ['test_date', t('Ngày thi', 'Test date'), (date) => date ? <time dateTime={date}>{date}</time> : display(date)],
            ['certificate_type', t('Loại bài thi', 'Test type')],
            ...skills, ['score', t('Tổng điểm', 'Total')],
          ]} />
        </details>}
        {data.notes.map((note) => <p key={note} className="english-standard-source">{note}</p>)}
        {!data.has_data && onSync && <button className="school-data-secondary" type="button" onClick={onSync}>{t('Đồng bộ CTT', 'Sync CTT')}</button>}
      </>}
    </section>
  );
}
