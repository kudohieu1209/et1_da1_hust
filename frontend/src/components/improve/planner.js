export const TARGET_GRADES = ['C', 'C+', 'B', 'B+', 'A'];

const SCALE4 = { C: 2, 'C+': 2.5, B: 3, 'B+': 3.5, A: 4 };
const roundCpa = value => Math.round((value + Number.EPSILON) * 100) / 100;
const capCpa = (baseCpa, addedPoints, cpaCredits) =>
  Math.min(4, baseCpa + (cpaCredits > 0 ? addedPoints / cpaCredits : 0));

function pointGain(course, grade) {
  return (SCALE4[grade] - course.current_numeric_grade) * course.credits;
}

export function simulate(baseCpa, cpaCredits, candidates, targets) {
  let addedPoints = 0;
  let credits = 0;
  let count = 0;

  for (const course of candidates) {
    const grade = targets[course.code];
    if (!course.projections[grade]) continue;
    addedPoints += pointGain(course, grade);
    credits += course.credits;
    count += 1;
  }

  const cpa = roundCpa(capCpa(baseCpa, addedPoints, cpaCredits));
  return { cpa, delta: roundCpa(cpa - baseCpa), credits, count };
}

export function rankFor(cpa, ladder) {
  return ladder.reduce((rank, step) =>
    step.min_cpa <= cpa && (!rank || step.min_cpa > rank.min_cpa) ? step : rank, null);
}

export function nextRank(cpa, ladder) {
  return ladder.reduce((rank, step) =>
    step.min_cpa > cpa && (!rank || step.min_cpa < rank.min_cpa) ? step : rank, null);
}

export function planForTarget({ baseCpa, cpaCredits, candidates, targetCpa, assumedGrade }) {
  if (targetCpa <= baseCpa) {
    return { achievable: true, courses: [], credits: 0, cpa: baseCpa, maxCpa: baseCpa };
  }

  const eligible = candidates.filter(course => course.projections[assumedGrade]);
  const maxPoints = eligible.reduce((total, course) => total + pointGain(course, assumedGrade), 0);
  const maxCpa = roundCpa(capCpa(baseCpa, maxPoints, cpaCredits));
  const need = (targetCpa - baseCpa) * cpaCredits;
  const meetsGoal = points => points + 1e-9 >= need;
  if (cpaCredits <= 0 || !meetsGoal(maxPoints)) {
    return { achievable: false, courses: [], credits: 0, cpa: baseCpa, maxCpa };
  }

  const required = eligible.filter(course => course.category === 'retake');
  const optional = eligible.filter(course => course.category !== 'retake');
  const requiredPoints = required.reduce((total, course) => total + pointGain(course, assumedGrade), 0);
  let selected = required;
  let addedPoints = requiredPoints;

  if (!meetsGoal(requiredPoints)) {
    const budget = optional.reduce((total, course) => total + Math.ceil(course.credits), 0);
    const dp = Array(budget + 1).fill(null);
    dp[0] = { points: 0, courses: [] };
    for (const course of optional) {
      const cost = Math.ceil(course.credits);
      const gain = pointGain(course, assumedGrade);
      // Walk backwards so each course can be picked at most once.
      for (let credits = budget; credits >= cost; credits -= 1) {
        const previous = dp[credits - cost];
        if (!previous) continue;
        const points = previous.points + gain;
        if (!dp[credits] || points > dp[credits].points) {
          dp[credits] = { points, courses: [...previous.courses, course] };
        }
      }
    }
    const best = dp.find(option => option && meetsGoal(requiredPoints + option.points));
    selected = [...required, ...best.courses];
    addedPoints += best.points;
  }

  return {
    achievable: true,
    courses: selected.map(({ code }) => ({ code, grade: assumedGrade })),
    credits: selected.reduce((total, course) => total + course.credits, 0),
    cpa: roundCpa(capCpa(baseCpa, addedPoints, cpaCredits)),
    maxCpa,
  };
}
