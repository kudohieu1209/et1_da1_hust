export const TARGET_GRADES = ['C', 'C+', 'B', 'B+', 'A'];
export const NEW_COURSE_GRADES = ['A', 'B+', 'B', 'C+', 'C', 'D+', 'D'];

export const SCALE4 = {
  A: 4.0,
  'B+': 3.5,
  B: 3.0,
  'C+': 2.5,
  C: 2.0,
  'D+': 1.5,
  D: 1.0,
  F: 0.0,
};

export const roundCpa = value => Math.round((value + Number.EPSILON) * 100) / 100;

export function pointGain(course, grade) {
  return (SCALE4[grade] - course.current_numeric_grade) * course.credits;
}

export function courseGain(course, grade, base) {
  const denominator = typeof base === 'number' ? base : (base?.credits || 0);
  if (denominator <= 0 || !SCALE4[grade]) return 0;
  return pointGain(course, grade) / denominator;
}

export function requiredAverage({ targetCpa, currentPoints, currentCredits, newCredits }) {
  if (!newCredits || newCredits <= 0) return null;
  const needed = (targetCpa * (currentCredits + newCredits) - currentPoints) / newCredits;
  if (needed <= 0) return 0;
  return Math.ceil(needed * 100 - 1e-9) / 100;
}

export function simulate(base, candidates = [], targets = {}, upcoming = [], upcomingGrades = {}) {
  let totalPoints = 0;
  let totalCredits = 0;

  if (typeof base === 'number') {
    totalCredits = Number(arguments[1] || 0);
    totalPoints = base * totalCredits;
    candidates = arguments[2] || [];
    targets = arguments[3] || {};
    upcoming = arguments[4] || [];
    upcomingGrades = arguments[5] || {};
  } else if (base && typeof base === 'object') {
    totalCredits = Number(base.credits || 0);
    totalPoints = base.points != null
      ? Number(base.points)
      : (base.cpa != null ? Number(base.cpa) * totalCredits : 0);
  }

  let retakePoints = 0;
  let retakeCredits = 0;
  let retakeCount = 0;

  for (const course of (candidates || [])) {
    const grade = targets?.[course.code];
    if (!grade || !course.projections?.[grade]) continue;
    retakePoints += pointGain(course, grade);
    retakeCredits += course.credits;
    retakeCount += 1;
  }

  let newPoints = 0;
  let newCredits = 0;
  let newCount = 0;

  for (const course of (upcoming || [])) {
    const grade = upcomingGrades?.[course.code];
    if (!grade || !SCALE4[grade]) continue;
    const cr = course.credits ?? course.custom_credits;
    if (cr == null || cr <= 0) continue;
    newPoints += SCALE4[grade] * cr;
    newCredits += cr;
    newCount += 1;
  }

  const initialBaseCpa = totalCredits > 0 ? totalPoints / totalCredits : 0;
  const finalNumerator = totalPoints + retakePoints + newPoints;
  const finalDenominator = totalCredits + newCredits;
  const simulatedCpa = finalDenominator > 0 ? finalNumerator / finalDenominator : 0;
  const cpa = roundCpa(simulatedCpa);
  const delta = roundCpa(simulatedCpa - initialBaseCpa);

  return {
    cpa,
    delta,
    retakeCredits,
    newCredits,
    count: retakeCount + newCount,
    credits: retakeCredits + newCredits,
  };
}

export function rankFor(cpa, ladder) {
  return ladder.reduce((rank, step) =>
    step.min_cpa <= cpa && (!rank || step.min_cpa > rank.min_cpa) ? step : rank, null);
}

export function nextRank(cpa, ladder) {
  return ladder.reduce((rank, step) =>
    step.min_cpa > cpa && (!rank || step.min_cpa < rank.min_cpa) ? step : rank, null);
}

export function planForTarget({
  base,
  baseCpa,
  cpaCredits,
  candidates = [],
  targetCpa,
  assumedGrade = 'B',
  newCourses = [],
  newGrade = 'B',
}) {
  const totalBaseCredits = base?.credits ?? (cpaCredits ?? 0);
  const totalBasePoints = base?.points ?? (baseCpa != null ? baseCpa * totalBaseCredits : 0);

  let newCredits = 0;
  let newPoints = 0;
  const resolvedNewGrade = newGrade || 'B';
  const newScale = SCALE4[resolvedNewGrade] ?? 3.0;

  for (const course of newCourses) {
    const cr = course.credits ?? course.custom_credits;
    if (cr == null || cr <= 0) continue;
    newCredits += cr;
    newPoints += newScale * cr;
  }

  const D = totalBaseCredits + newCredits;
  const P = totalBasePoints + newPoints;

  const eligible = candidates.filter(course => course.projections?.[assumedGrade]);
  const requiredF = eligible.filter(course => course.category === 'retake');
  const requiredFPoints = requiredF.reduce((total, course) => total + pointGain(course, assumedGrade), 0);

  const gpaNeededForNew = requiredAverage({
    targetCpa,
    currentPoints: totalBasePoints + requiredFPoints,
    currentCredits: totalBaseCredits,
    newCredits,
  });

  if (D > 0 && P + 1e-9 >= targetCpa * D) {
    return {
      achievable: true,
      courses: [],
      credits: 0,
      cpa: roundCpa(P / D),
      maxCpa: roundCpa(P / D),
      gpaNeededForNew,
      newCredits,
    };
  }

  const maxRetakePoints = eligible.reduce((total, course) => total + pointGain(course, assumedGrade), 0);
  const maxCpa = D > 0 ? roundCpa((P + maxRetakePoints) / D) : roundCpa(targetCpa);

  if (D <= 0 || P + maxRetakePoints + 1e-9 < targetCpa * D) {
    return {
      achievable: false,
      courses: [],
      credits: 0,
      cpa: D > 0 ? roundCpa(P / D) : 0,
      maxCpa,
      gpaNeededForNew,
      newCredits,
    };
  }

  const optional = eligible.filter(course => course.category !== 'retake');
  let selected = requiredF;
  let addedPoints = requiredFPoints;

  if (P + requiredFPoints + 1e-9 < targetCpa * D) {
    const neededFromOptional = targetCpa * D - P - requiredFPoints;
    const budget = optional.reduce((total, course) => total + Math.ceil(course.credits), 0);
    const dp = Array(budget + 1).fill(null);
    dp[0] = { points: 0, courses: [] };
    for (const course of optional) {
      const cost = Math.ceil(course.credits);
      const gain = pointGain(course, assumedGrade);
      for (let cr = budget; cr >= cost; cr -= 1) {
        const previous = dp[cr - cost];
        if (!previous) continue;
        const pts = previous.points + gain;
        if (!dp[cr] || pts > dp[cr].points) {
          dp[cr] = { points: pts, courses: [...previous.courses, course] };
        }
      }
    }
    const best = dp.find(option => option && option.points + 1e-9 >= neededFromOptional);
    if (!best) {
      return {
        achievable: false,
        courses: [],
        credits: 0,
        cpa: D > 0 ? roundCpa(P / D) : 0,
        maxCpa,
        gpaNeededForNew,
        newCredits,
      };
    }
    selected = [...requiredF, ...best.courses];
    addedPoints += best.points;
  }

  return {
    achievable: true,
    courses: selected.map(({ code }) => ({ code, grade: assumedGrade })),
    credits: selected.reduce((total, course) => total + course.credits, 0),
    cpa: D > 0 ? roundCpa((P + addedPoints) / D) : roundCpa(targetCpa),
    maxCpa,
    gpaNeededForNew,
    newCredits,
  };
}
