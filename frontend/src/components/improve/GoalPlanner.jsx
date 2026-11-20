import { Target } from 'lucide-react';
import { planForTarget } from './planner';

const NEW_SCOPE_OPTIONS = [
  { id: 'none', labelVi: 'Không tính', labelEn: 'None' },
  { id: 'term', labelVi: 'Môn kỳ này', labelEn: 'Current term' },
  { id: 'program', labelVi: 'Học hết CTĐT', labelEn: 'Entire curriculum' },
];

const NEW_GRADE_OPTIONS = ['C+', 'B', 'B+', 'A'];

export default function GoalPlanner({
  base,
  baseCpa,
  cpaCredits,
  candidates = [],
  upcomingCourses = [],
  customCredits = {},
  programProjection = null,
  ladder = [],
  rankLabel,
  goal = {},
  onGoalChange,
  onApply,
  t,
}) {
  const hasTerm = upcomingCourses.some(c => c.source === 'current_term');
  const scope = goal.scope ?? (hasTerm ? 'term' : 'none');
  const newGrade = goal.newGrade ?? 'B';
  const retakeGrade = goal.grade ?? 'B+';

  let newCourses = [];
  let undefinedElectiveCredits = 0;

  if (scope === 'term') {
    newCourses = upcomingCourses
      .filter(c => c.source === 'current_term')
      .map(c => ({
        ...c,
        credits: (c.credits_known && c.credits != null && c.credits > 0)
          ? c.credits
          : (customCredits[c.code] ?? null),
      }));
  } else if (scope === 'program') {
    const compulsory = upcomingCourses
      .filter(c => c.source === 'curriculum' && c.is_compulsory)
      .map(c => ({
        ...c,
        credits: (c.credits_known && c.credits != null && c.credits > 0)
          ? c.credits
          : (customCredits[c.code] ?? null),
      }));

    const compulsoryCredits = compulsory.reduce((sum, c) => sum + (c.credits || 0), 0);
    const finalCpaCredits = programProjection?.final_cpa_credits;

    newCourses = [...compulsory];

    if (finalCpaCredits != null) {
      const currentDenom = base?.credits ?? cpaCredits ?? 0;
      const targetNewCredits = Math.max(0, finalCpaCredits - currentDenom);
      if (compulsoryCredits < targetNewCredits) {
        undefinedElectiveCredits = Math.round((targetNewCredits - compulsoryCredits) * 10) / 10;
        if (undefinedElectiveCredits > 0) {
          newCourses.push({
            code: '__UNDEFINED_ELECTIVES__',
            name: t('Học phần tự chọn chưa xác định', 'Undefined elective courses'),
            credits: undefinedElectiveCredits,
            is_compulsory: false,
          });
        }
      }
    }
  }

  const targetCpa = Number(goal.cpa);
  const validCpa = goal.cpa !== '' && targetCpa >= baseCpa && targetCpa <= 4
    && Math.abs(targetCpa * 100 - Math.round(targetCpa * 100)) < 1e-9;

  const plan = validCpa
    ? planForTarget({
        base,
        baseCpa,
        cpaCredits,
        candidates,
        targetCpa,
        assumedGrade: retakeGrade,
        newCourses,
        newGrade,
      })
    : null;

  let gpaNeededForNew = null;
  if (validCpa) {
    if (scope === 'program' && programProjection?.remaining_credits > 0 && programProjection?.final_cpa_credits > 0) {
      const remCredits = programProjection.remaining_credits;
      const finalCredits = programProjection.final_cpa_credits;
      const curPts = base?.points ?? (baseCpa * (base?.credits ?? cpaCredits));
      const needed = (targetCpa * finalCredits - curPts) / remCredits;
      gpaNeededForNew = Math.ceil(Math.max(0, needed) * 100 - 1e-9) / 100;
    } else if (plan?.gpaNeededForNew != null) {
      gpaNeededForNew = plan.gpaNeededForNew;
    }
  }

  const presets = ladder.filter(rank => rank.min_cpa >= 2).sort((a, b) => a.min_cpa - b.min_cpa);
  const names = new Map(candidates.map(c => [c.code, c.name]));

  function handleApply() {
    if (!plan) return;
    const retakeMap = Object.fromEntries(plan.courses.map(({ code, grade }) => [code, grade]));
    const upcomingMap = {};
    if (scope !== 'none') {
      for (const c of newCourses) {
        if (c.code !== '__UNDEFINED_ELECTIVES__') {
          upcomingMap[c.code] = newGrade;
        }
      }
    }
    onApply(retakeMap, upcomingMap);
  }

  return (
    <section className="improve-panel improve-goal" aria-labelledby="improve-goal-title">
      <h3 id="improve-goal-title">
        <Target size={18} aria-hidden="true" /> {t('Đặt CPA mục tiêu', 'Set a CPA goal')}
      </h3>
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
            value={goal.cpa ?? ''}
            onChange={event => onGoalChange({ ...goal, cpa: event.target.value })}
          />
        </div>

        <div className="improve-goal-field">
          <label htmlFor="improve-expected-grade">{t('Điểm dự kiến khi học lại', 'Expected retake grade')}</label>
          <select
            id="improve-expected-grade"
            value={retakeGrade}
            onChange={event => onGoalChange({ ...goal, grade: event.target.value })}
          >
            {['B', 'B+', 'A'].map(grade => (
              <option key={grade} value={grade}>{grade}</option>
            ))}
          </select>
        </div>

        <div className="improve-goal-field">
          <label htmlFor="improve-new-scope">{t('Phạm vi môn mới', 'Upcoming course scope')}</label>
          <select
            id="improve-new-scope"
            value={scope}
            onChange={event => onGoalChange({ ...goal, scope: event.target.value })}
          >
            {NEW_SCOPE_OPTIONS.map(opt => (
              <option key={opt.id} value={opt.id}>
                {t(opt.labelVi, opt.labelEn)}
              </option>
            ))}
          </select>
        </div>

        <div className="improve-goal-field">
          <label htmlFor="improve-new-grade">{t('Điểm dự kiến môn mới', 'Expected new course grade')}</label>
          <select
            id="improve-new-grade"
            value={newGrade}
            disabled={scope === 'none'}
            onChange={event => onGoalChange({ ...goal, newGrade: event.target.value })}
          >
            {NEW_GRADE_OPTIONS.map(grade => (
              <option key={grade} value={grade}>{grade}</option>
            ))}
          </select>
        </div>
      </div>

      {scope === 'program' && undefinedElectiveCredits > 0 && (
        <p className="improve-note">
          {t(
            `Phạm vi gồm toàn bộ môn bắt buộc chưa học và ${undefinedElectiveCredits} TC tự chọn chưa xác định để khớp tổng tín chỉ CTĐT.`,
            `Scope includes all unlearned compulsory courses and ${undefinedElectiveCredits} undefined elective credits.`,
          )}
        </p>
      )}

      {goal.cpa !== '' && !validCpa && (
        <p className="improve-goal-feedback" role="status">
          {t(
            `Nhập CPA từ ${baseCpa.toFixed(2)} đến 4.00, tối đa hai chữ số thập phân.`,
            `Enter a CPA from ${baseCpa.toFixed(2)} to 4.00 with up to two decimal places.`,
          )}
        </p>
      )}

      {plan && (
        <div className="improve-goal-result">
          {gpaNeededForNew != null && (
            <p className="improve-goal-gpa-needed" role="status">
              {gpaNeededForNew > 4.0 ? (
                <span className="improve-loss">
                  {t(
                    'Không đạt được chỉ với môn mới (cần GPA > 4.00). Cần học lại hoặc cải thiện thêm các môn đã có điểm.',
                    'Cannot achieve goal with new courses alone (requires GPA > 4.00). Retakes are necessary.',
                  )}
                </span>
              ) : (
                <span>
                  {t(
                    `Các môn sắp học cần trung bình ${gpaNeededForNew.toFixed(2)} để đạt mục tiêu nếu không học cải thiện.`,
                    `Upcoming courses need an average of ${gpaNeededForNew.toFixed(2)} to achieve goal without retakes.`,
                  )}
                </span>
              )}
            </p>
          )}

          {!plan.achievable ? (
            <p role="status">
              {t(
                `Chưa thể đạt mục tiêu. CPA tối đa khi tất cả môn đủ điều kiện lên ${retakeGrade} (và môn mới đạt ${newGrade}) là ${plan.maxCpa.toFixed(2)}.`,
                `Goal out of reach. Maximum CPA attainable is ${plan.maxCpa.toFixed(2)}.`,
              )}
            </p>
          ) : plan.courses.length === 0 ? (
            <>
              <p role="status">
                {scope !== 'none' && newCourses.length > 0
                  ? t(
                      `Mục tiêu đạt được khi các môn mới đạt ${newGrade} mà không cần học lại môn nào.`,
                      `Goal achievable if new courses achieve ${newGrade} without extra retakes.`,
                    )
                  : t(
                      'CPA hiện tại đã đạt mục tiêu này.',
                      'Your current CPA already meets this goal.',
                    )}
              </p>
              {scope !== 'none' && newCourses.length > 0 && (
                <button
                  type="button"
                  className="improve-button improve-primary"
                  onClick={handleApply}
                >
                  {t('Áp dụng phương án môn mới', 'Apply new courses plan')}
                </button>
              )}
            </>
          ) : (
            <>
              <p role="status">
                <strong>
                  {t(
                    `${plan.courses.length} môn học lại · ${plan.credits} tín chỉ · CPA dự kiến ${plan.cpa.toFixed(2)}`,
                    `${plan.courses.length} retake courses · ${plan.credits} credits · projected CPA ${plan.cpa.toFixed(2)}`,
                  )}
                </strong>
              </p>
              <ul className="improve-plan-courses">
                {plan.courses.map(({ code, grade }) => (
                  <li key={code}>
                    {code} · {names.get(code)} <strong>→ {grade}</strong>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="improve-button improve-primary"
                onClick={handleApply}
              >
                {t('Áp dụng phương án', 'Apply plan')}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
