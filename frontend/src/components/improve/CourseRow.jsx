import { TARGET_GRADES } from './planner';

export default function CourseRow({ course, categoryLabel, target, onTargetChange, t }) {
  const projection = course.projections[target];

  return (
    <li className={`improve-course improve-course--${course.category}`}>
      <div className="improve-course-info">
        <span className="improve-grade" aria-label={t(
          `Điểm hiện tại ${course.current_letter_grade}`,
          `Current grade ${course.current_letter_grade}`,
        )}>{course.current_letter_grade}</span>
        <div>
          <div className="improve-course-name"><strong>{course.code}</strong> · {course.name}</div>
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
        <span className={projection ? 'improve-gain' : 'improve-course-max'}>
          {projection
            ? t(`+${projection.delta_cpa.toFixed(3)} CPA`, `+${projection.delta_cpa.toFixed(3)} CPA`)
            : t(`tối đa +${course.max_delta_cpa.toFixed(3)}`, `up to +${course.max_delta_cpa.toFixed(3)}`)}
        </span>
      </div>
    </li>
  );
}
