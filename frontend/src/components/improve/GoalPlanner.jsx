import { Target } from 'lucide-react';
import { planForTarget } from './planner';

export default function GoalPlanner({ baseCpa, cpaCredits, candidates, ladder, rankLabel, goal, onGoalChange, onApply, t }) {
  const targetCpa = Number(goal.cpa);
  const validCpa = goal.cpa !== '' && targetCpa >= baseCpa && targetCpa <= 4
    && Math.abs(targetCpa * 100 - Math.round(targetCpa * 100)) < 1e-9;
  const plan = validCpa
    ? planForTarget({ baseCpa, cpaCredits, candidates, targetCpa, assumedGrade: goal.grade })
    : null;
  const presets = ladder.filter(rank => rank.min_cpa >= 2).sort((a, b) => a.min_cpa - b.min_cpa);
  const names = new Map(candidates.map(course => [course.code, course.name]));

  return (
    <section className="improve-panel improve-goal" aria-labelledby="improve-goal-title">
      <h3 id="improve-goal-title"><Target size={18} aria-hidden="true" /> {t('Đặt CPA mục tiêu', 'Set a CPA goal')}</h3>
      <div className="improve-controls" role="group" aria-label={t('Mốc CPA', 'CPA milestones')}>
        {presets.map(rank => (
          <button
            key={rank.rank}
            type="button"
            className="improve-button"
            disabled={rank.min_cpa < baseCpa}
            aria-pressed={goal.cpa !== '' && targetCpa === rank.min_cpa}
            onClick={() => onGoalChange({ ...goal, cpa: rank.min_cpa.toFixed(2) })}
          >
            {rank.min_cpa.toFixed(2)} · {rankLabel(rank)}
          </button>
        ))}
      </div>
      <div className="improve-goal-fields">
        <div className="improve-goal-field">
          <label htmlFor="improve-target-cpa">{t('CPA mục tiêu', 'Target CPA')}</label>
          <input
            id="improve-target-cpa"
            type="number"
            inputMode="decimal"
            min={baseCpa}
            max={4}
            step="0.01"
            placeholder={baseCpa.toFixed(2)}
            aria-invalid={goal.cpa !== '' && !validCpa}
            value={goal.cpa}
            onChange={event => onGoalChange({ ...goal, cpa: event.target.value })}
          />
        </div>
        <div className="improve-goal-field">
          <label htmlFor="improve-expected-grade">{t('Điểm dự kiến khi học lại', 'Expected retake grade')}</label>
          <select id="improve-expected-grade" value={goal.grade} onChange={event => onGoalChange({ ...goal, grade: event.target.value })}>
            {['B', 'B+', 'A'].map(grade => <option key={grade}>{grade}</option>)}
          </select>
        </div>
      </div>
      {goal.cpa !== '' && !validCpa && <p className="improve-goal-feedback" role="status">
        {t(
          `Nhập CPA từ ${baseCpa.toFixed(2)} đến 4.00, tối đa hai chữ số thập phân.`,
          `Enter a CPA from ${baseCpa.toFixed(2)} to 4.00 with up to two decimal places.`,
        )}
      </p>}
      {plan && (
        <div className="improve-goal-result">
          {!plan.achievable ? (
            <p role="status">{t(
              `Chưa thể đạt mục tiêu. CPA tối đa khi tất cả môn đủ điều kiện lên ${goal.grade} là ${plan.maxCpa.toFixed(2)}.`,
              `Goal out of reach. The maximum CPA if every eligible course improves to ${goal.grade} is ${plan.maxCpa.toFixed(2)}.`,
            )}</p>
          ) : plan.courses.length === 0 ? (
            <p role="status">{t('CPA hiện tại đã đạt mục tiêu này.', 'Your current CPA already meets this goal.')}</p>
          ) : (
            <>
              <p role="status"><strong>{t(
                `${plan.courses.length} môn · ${plan.credits} tín chỉ · CPA dự kiến ${plan.cpa.toFixed(2)}`,
                `${plan.courses.length} courses · ${plan.credits} credits · projected CPA ${plan.cpa.toFixed(2)}`,
              )}</strong></p>
              <ul className="improve-plan-courses">
                {plan.courses.map(({ code, grade }) => (
                  <li key={code}>{code} · {names.get(code)} <strong>→ {grade}</strong></li>
                ))}
              </ul>
              <button type="button" className="improve-button improve-primary" onClick={() => onApply(plan.courses)}>
                {t('Áp dụng phương án', 'Apply plan')}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
