import { useState } from 'react';
import { NEW_COURSE_GRADES } from './planner';

function UpcomingGroupHeader({ title, count, codes, onBatchGrade, onClearBatch, t }) {
  const [selectedGrade, setSelectedGrade] = useState('B');

  return (
    <div className="improve-group-header">
      <h3 className="improve-group-title">
        {title} <span className="improve-count">{count}</span>
      </h3>
      {codes.length > 0 && (
        <div className="improve-group-actions" role="group" aria-label={t(`Thao tác nhóm ${title}`, `Batch actions for ${title}`)}>
          <div className="improve-batch-select-wrap">
            <span className="improve-batch-label">{t('Đặt cả nhóm =', 'Set all =')}</span>
            <select
              className="improve-select"
              aria-label={t(`Chọn điểm cho cả nhóm ${title}`, `Select grade for ${title}`)}
              value={selectedGrade}
              onChange={e => setSelectedGrade(e.target.value)}
            >
              {NEW_COURSE_GRADES.map(g => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
            <button
              type="button"
              className="improve-button improve-button--sm"
              onClick={() => onBatchGrade(codes, selectedGrade)}
            >
              {t('Áp dụng', 'Apply')}
            </button>
          </div>
          <button
            type="button"
            className="improve-button improve-button--sm"
            onClick={() => onClearBatch(codes)}
          >
            {t('Bỏ chọn nhóm', 'Clear group')}
          </button>
        </div>
      )}
    </div>
  );
}

function UpcomingRow({ course, grade, customCredit, onGradeChange, onCreditChange, t }) {
  const creditsKnown = course.credits_known && course.credits != null && course.credits > 0;
  const currentCredit = creditsKnown ? course.credits : (customCredit ?? '');

  return (
    <li className="improve-course improve-course--upcoming">
      <div className="improve-course-info">
        <span className="improve-grade improve-grade--upcoming" aria-hidden="true">
          {grade || '—'}
        </span>
        <div>
          <div className="improve-course-name">
            <strong>{course.code}</strong> · {course.name}
          </div>
          <div className="improve-course-meta">
            {creditsKnown ? (
              <span>{course.credits} {t('tín chỉ', 'credits')}</span>
            ) : (
              <span className="improve-custom-credit-wrap">
                <label htmlFor={`credit-${course.code}`}>
                  {t('Số TC:', 'Credits:')}
                </label>
                <input
                  id={`credit-${course.code}`}
                  type="number"
                  min="1"
                  max="10"
                  step="1"
                  className="improve-credit-input"
                  placeholder="TC"
                  value={currentCredit}
                  onChange={e => onCreditChange(course.code, e.target.value ? Number(e.target.value) : '')}
                />
                <em className="improve-unknown-note">{t('(Chưa có trong CTĐT)', '(Not in curriculum)')}</em>
              </span>
            )}
            {course.is_compulsory && (
              <span className="improve-tag improve-tag--compulsory">
                {t('Bắt buộc', 'Compulsory')}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="improve-course-targets">
        <div
          className="improve-controls"
          role="group"
          aria-label={t(`Điểm dự kiến cho ${course.code}`, `Expected grade for ${course.code}`)}
        >
          {NEW_COURSE_GRADES.map(g => (
            <button
              key={g}
              type="button"
              className="improve-button improve-grade-button"
              aria-pressed={grade === g}
              onClick={() => onGradeChange(course.code, grade === g ? null : g)}
            >
              {g}
            </button>
          ))}
        </div>
      </div>
    </li>
  );
}

export default function UpcomingCourses({
  upcomingCourses = [],
  upcomingGrades = {},
  customCredits = {},
  onGradeChange,
  onCustomCreditChange,
  onBatchGrade,
  onClearBatch,
  onOpenImport,
  t,
}) {
  const currentTermCourses = upcomingCourses.filter(c => c.source === 'current_term');
  const curriculumCourses = upcomingCourses.filter(c => c.source === 'curriculum');
  const compulsory = curriculumCourses.filter(c => c.is_compulsory);
  const electives = curriculumCourses.filter(c => !c.is_compulsory);

  // Group compulsory by suggested_semester
  const semesterMap = new Map();
  for (const course of compulsory) {
    const sem = course.suggested_semester ?? 99;
    if (!semesterMap.has(sem)) semesterMap.set(sem, []);
    semesterMap.get(sem).push(course);
  }
  const sortedSemesters = Array.from(semesterMap.keys()).sort((a, b) => a - b);

  return (
    <div className="improve-upcoming-section">
      {/* 1. Nhóm Kỳ này theo TKB */}
      <section className="improve-upcoming-group" aria-labelledby="upcoming-term-title">
        <UpcomingGroupHeader
          title={t('Kỳ này (theo thời khóa biểu)', 'Current term (from timetable)')}
          count={currentTermCourses.length}
          codes={currentTermCourses.map(c => c.code)}
          onBatchGrade={onBatchGrade}
          onClearBatch={onClearBatch}
          t={t}
        />
        {currentTermCourses.length > 0 ? (
          <ul className="improve-course-list">
            {currentTermCourses.map(course => (
              <UpcomingRow
                key={course.code}
                course={course}
                grade={upcomingGrades[course.code]}
                customCredit={customCredits[course.code]}
                onGradeChange={onGradeChange}
                onCreditChange={onCustomCreditChange}
                t={t}
              />
            ))}
          </ul>
        ) : (
          <div className="improve-state improve-panel">
            <p>{t('Chưa có dữ liệu thời khóa biểu kỳ này.', 'No timetable synced for current term.')}</p>
            {onOpenImport && (
              <button
                type="button"
                className="improve-button improve-primary"
                onClick={onOpenImport}
              >
                {t('Nhập / đồng bộ dữ liệu', 'Sync or import data')}
              </button>
            )}
          </div>
        )}
      </section>

      {/* 2. Nhóm Theo CTĐT */}
      <section className="improve-upcoming-group" aria-labelledby="upcoming-curriculum-title">
        <h3 id="upcoming-curriculum-title" className="improve-super-title">
          {t('Theo CTĐT', 'From curriculum')}
        </h3>

        {sortedSemesters.map(sem => {
          const courses = semesterMap.get(sem) || [];
          const title = sem === 99
            ? t('Chưa xếp kỳ gợi ý', 'Other / unassigned')
            : t(`Kỳ gợi ý ${sem}`, `Suggested semester ${sem}`);
          return (
            <div key={sem} className="improve-subgroup">
              <UpcomingGroupHeader
                title={title}
                count={courses.length}
                codes={courses.map(c => c.code)}
                onBatchGrade={onBatchGrade}
                onClearBatch={onClearBatch}
                t={t}
              />
              <ul className="improve-course-list">
                {courses.map(course => (
                  <UpcomingRow
                    key={course.code}
                    course={course}
                    grade={upcomingGrades[course.code]}
                    customCredit={customCredits[course.code]}
                    onGradeChange={onGradeChange}
                    onCreditChange={onCustomCreditChange}
                    t={t}
                  />
                ))}
              </ul>
            </div>
          );
        })}

        {electives.length > 0 && (
          <details className="improve-electives-details">
            <summary className="improve-electives-summary">
              <strong>{t(`Học phần tự chọn (${electives.length})`, `Elective courses (${electives.length})`)}</strong>
            </summary>
            <p className="improve-note">
              {t('Chỉ chọn số môn bạn định học.', 'Only select the courses you plan to take.')}
            </p>
            <UpcomingGroupHeader
              title={t('Học phần tự chọn', 'Electives')}
              count={electives.length}
              codes={electives.map(c => c.code)}
              onBatchGrade={onBatchGrade}
              onClearBatch={onClearBatch}
              t={t}
            />
            <ul className="improve-course-list">
              {electives.map(course => (
                <UpcomingRow
                  key={course.code}
                  course={course}
                  grade={upcomingGrades[course.code]}
                  customCredit={customCredits[course.code]}
                  onGradeChange={onGradeChange}
                  onCreditChange={onCustomCreditChange}
                  t={t}
                />
              ))}
            </ul>
          </details>
        )}
      </section>
    </div>
  );
}
