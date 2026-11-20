import { TARGET_GRADES, courseGain } from './planner';

export default function CourseRow({ course, categoryLabel, target, onTargetChange, base, t }) {
  const gain = target ? courseGain(course, target, base) : 0;
  const maxGain = course.projections?.A ? courseGain(course, 'A', base) : (course.max_delta_cpa || 0);

  return (
    <li className={`improve-course improve-course--${course.category}`}>
      <div className="improve-course-info">
        <span className="improve-grade" aria-label={t(
          `Điểm hiện tại ${course.current_letter_grade}`,
          `Current grade ${course.current_letter_grade}`,
        )}>{course.current_letter_grade}</span>
        <div>
          <div className="improve-course-name">
            <strong>{course.code}</strong> · {course.name}
            {course.in_current_term && (
              <span className="improve-tag improve-tag--term">
                {t('Đang học lại kỳ này', 'Retaking this term')}
              </span>
            )}
          </div>
          <div className="improve-course-meta">
            {course.credits} {t('tín chỉ', 'credits')} · {categoryLabel}
          </div>
        </div>
      </div>
      <div className="improve-course-targets">
        <div className="improve-controls" role="group" aria-label={t(
          `Điểm mục tiêu cho ${course.code}`, `Target grade for ${course.code}`,
        )}>
          {TARGET_GRADES.filter(grade => course.projections[grade]).map(grade => (
            <button
              key={grade}
              type="button"
              className="improve-button improve-grade-button"
              aria-pressed={target === grade}
              onClick={() => onTargetChange(course.code, target === grade ? null : grade)}
            >{grade}</button>
          ))}
        </div>
        <span className={target ? 'improve-gain' : 'improve-course-max'}>
          {target
            ? t(`+${gain.toFixed(3)} CPA`, `+${gain.toFixed(3)} CPA`)
            : t(`tối đa +${maxGain.toFixed(3)}`, `up to +${maxGain.toFixed(3)}`)}
        </span>
      </div>
    </li>
  );
}
