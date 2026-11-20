import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  courseGain,
  nextRank,
  planForTarget,
  rankFor,
  requiredAverage,
  simulate,
} from './planner.js';

const course = (code, credits, numericGrade, category = 'improve') => ({
  code,
  credits,
  category,
  current_numeric_grade: numericGrade,
  projections: { B: { delta_cpa: 0.001 }, 'B+': {}, A: {} },
});

test('simulation starts with the current CPA and no selected courses', () => {
  const courses = [course('ET2050', 4, 0, 'retake')];
  assert.deepEqual(simulate({ points: 45, credits: 20 }, courses, {}), {
    cpa: 2.25, delta: 0, retakeCredits: 0, newCredits: 0, count: 0, credits: 0,
  });
});

test('simulation combines unrounded gains and ignores unavailable targets', () => {
  const courses = [course('ET2050', 4, 0), course('ET2030', 2, 2.5), course('ET1000', 3, 2.5)];
  const result = simulate({ points: 50, credits: 25 }, courses, { ET2050: 'B', ET2030: 'A', ET1000: 'C' });
  assert.equal(result.cpa, 2.6);
  assert.equal(result.delta, 0.6);
  assert.equal(result.retakeCredits, 6);
  assert.equal(result.count, 2);
});

test('simulation handles upcoming courses: higher raises CPA, lower lowers CPA, equal stays same, unknown credits skipped', () => {
  const base = { points: 50, credits: 20 }; // CPA = 2.50
  const upcoming = [
    { code: 'NEW_HIGH', credits: 4 },
    { code: 'NEW_LOW', credits: 4 },
    { code: 'NEW_EQUAL', credits: 4 },
    { code: 'NEW_UNKNOWN', credits: null },
  ];

  // Higher grade (A = 4.0 > 2.50) raises CPA: (50 + 16) / 24 = 2.75
  const resHigh = simulate(base, [], {}, upcoming, { NEW_HIGH: 'A' });
  assert.equal(resHigh.cpa, 2.75);
  assert.equal(resHigh.delta, 0.25);
  assert.equal(resHigh.newCredits, 4);

  // Lower grade (D = 1.0 < 2.50) lowers CPA: (50 + 4) / 24 = 2.25
  const resLow = simulate(base, [], {}, upcoming, { NEW_LOW: 'D' });
  assert.equal(resLow.cpa, 2.25);
  assert.equal(resLow.delta, -0.25);

  // Equal grade (C+ = 2.50 == 2.50) keeps CPA same: (50 + 10) / 24 = 2.50
  const resEqual = simulate(base, [], {}, upcoming, { NEW_EQUAL: 'C+' });
  assert.equal(resEqual.cpa, 2.50);
  assert.equal(resEqual.delta, 0);

  // Unknown credits without custom credit is ignored
  const resUnknown = simulate(base, [], {}, upcoming, { NEW_UNKNOWN: 'A' });
  assert.equal(resUnknown.cpa, 2.50);
  assert.equal(resUnknown.newCredits, 0);
  assert.equal(resUnknown.count, 0);
});

test('courseGain is smaller when denominator includes upcoming courses', () => {
  const retakeCourse = course('ET2050', 3, 1.0); // D -> A: gain = (4.0 - 1.0) * 3 = 9 points
  const gainWithoutNew = courseGain(retakeCourse, 'A', { credits: 20 });
  const gainWithNew = courseGain(retakeCourse, 'A', { credits: 30 }); // 20 + 10 new credits

  assert.equal(gainWithoutNew, 9 / 20); // 0.45
  assert.equal(gainWithNew, 9 / 30); // 0.30
  assert.ok(gainWithNew < gainWithoutNew);
});

test('ranks follow inclusive minimum thresholds without gaps', () => {
  const ladder = [3.6, 3.2, 2.5, 2, 1, 0].map(min_cpa => ({ min_cpa }));
  [
    [0.99, 0, 1], [1, 1, 2], [1.99, 1, 2], [2, 2, 2.5], [2.495, 2, 2.5],
    [2.5, 2.5, 3.2], [3.2, 3.2, 3.6], [3.6, 3.6, null],
  ].forEach(([cpa, current, next]) => {
    assert.equal(rankFor(cpa, ladder).min_cpa, current);
    assert.equal(nextRank(cpa, ladder)?.min_cpa ?? null, next);
  });
});

test('a goal already reached needs no retakes', () => {
  assert.deepEqual(planForTarget({
    base: { points: 62.5, credits: 25 },
    targetCpa: 2.5,
    assumedGrade: 'B',
    candidates: [course('F', 3, 0, 'retake')],
  }), {
    achievable: true,
    courses: [],
    credits: 0,
    cpa: 2.5,
    maxCpa: 2.5,
    gpaNeededForNew: null,
    newCredits: 0,
  });

  assert.deepEqual(planForTarget({
    base: { points: 62.5, credits: 25 },
    targetCpa: 2.5,
    assumedGrade: 'B',
    candidates: [course('C', 3, 2, 'improve')],
  }), {
    achievable: true,
    courses: [],
    credits: 0,
    cpa: 2.5,
    maxCpa: 2.5,
    gpaNeededForNew: null,
    newCredits: 0,
  });
});

test('a feasible plan includes the required F retakes', () => {
  const plan = planForTarget({
    base: { points: 50, credits: 25 }, // CPA 2.0
    targetCpa: 2.1,
    assumedGrade: 'B',
    candidates: [course('F1', 3, 0, 'retake'), course('F2', 2, 0, 'retake'), course('C', 2, 2)],
  });
  assert.deepEqual(plan.courses, [{ code: 'F1', grade: 'B' }, { code: 'F2', grade: 'B' }]);
  assert.equal(plan.credits, 5);
  assert.equal(plan.cpa, 2.6);
});

test('a plan minimizes credits and chooses the greater gain at equal credits', () => {
  const plan = planForTarget({
    base: { points: 40, credits: 20 },
    targetCpa: 2.2,
    assumedGrade: 'B',
    candidates: [course('2', 2, 2), course('3', 3, 2), course('4a', 4, 2), course('4b', 4, 1.5)],
  });
  assert.deepEqual(plan.courses, [{ code: '4b', grade: 'B' }]);
  assert.equal(plan.credits, 4);
  assert.equal(plan.cpa, 2.3);
});

test('fractional credits are rounded up for DP but retain actual gains and cost', () => {
  const plan = planForTarget({
    base: { points: 40, credits: 20 },
    targetCpa: 2.1,
    assumedGrade: 'B',
    candidates: [course('fractional', 1.5, 1.5), course('whole', 2, 2)],
  });
  assert.deepEqual(plan.courses, [{ code: 'fractional', grade: 'B' }]);
  assert.equal(plan.credits, 1.5);
});

test('an unreachable goal becomes reachable with upcoming courses getting grade A', () => {
  const candidates = [course('F', 2, 0, 'retake'), course('D+', 3, 1.5)];
  // Without upcoming courses: max CPA with B is (40 + 6 + 4.5) / 20 = 2.525 -> cannot reach 3.0
  const planWithout = planForTarget({
    base: { points: 40, credits: 20 },
    targetCpa: 3.0,
    assumedGrade: 'B',
    candidates,
    newCourses: [],
  });
  assert.equal(planWithout.achievable, false);

  // With 20 credits of upcoming courses at A (4.0):
  // D = 40. P = 40 + 80 = 120. P/D = 3.0! Reachable!
  const planWith = planForTarget({
    base: { points: 40, credits: 20 },
    targetCpa: 3.0,
    assumedGrade: 'B',
    candidates,
    newCourses: [{ code: 'NEW1', credits: 10 }, { code: 'NEW2', credits: 10 }],
    newGrade: 'A',
  });
  assert.equal(planWith.achievable, true);
});

test('gpaNeededForNew rounds up to 2 decimal places and matches degree audit formula', () => {
  // Demo audit scenario:
  // cpa_credits = 20, points = 45.2, final_cpa_credits = 126, remaining_credits = 106.
  // needed = (2.50 * 126 - 45.2) / 106 = (315 - 45.2) / 106 = 269.8 / 106 = 2.54528...
  // math.ceil(needed * 100 - 1e-9) / 100 = 2.55
  const gpaNeeded = requiredAverage({
    targetCpa: 2.50,
    currentPoints: 45.2,
    currentCredits: 20,
    newCredits: 106,
  });
  assert.equal(gpaNeeded, 2.55);

  const plan = planForTarget({
    base: { points: 45.2, credits: 20 },
    targetCpa: 2.50,
    assumedGrade: 'B',
    candidates: [],
    newCourses: [{ code: 'REMAINING', credits: 106 }],
    newGrade: 'B',
  });
  assert.equal(plan.gpaNeededForNew, 2.55);
  assert.equal(plan.newCredits, 106);
});
