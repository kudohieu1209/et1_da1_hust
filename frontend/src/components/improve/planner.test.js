import assert from 'node:assert/strict';
import { test } from 'node:test';
import { nextRank, planForTarget, rankFor, simulate } from './planner.js';

const course = (code, credits, numericGrade, category = 'improve') => ({
  code,
  credits,
  category,
  current_numeric_grade: numericGrade,
  projections: { B: { delta_cpa: 0.001 }, 'B+': {}, A: {} },
});

test('simulation starts with the current CPA and no selected courses', () => {
  const courses = [course('ET2050', 4, 0, 'retake')];
  assert.deepEqual(simulate(2.25, 20, courses, {}), { cpa: 2.25, delta: 0, credits: 0, count: 0 });
});

test('simulation combines unrounded gains and ignores unavailable targets', () => {
  const courses = [course('ET2050', 4, 0), course('ET2030', 2, 2.5), course('ET1000', 3, 2.5)];
  assert.deepEqual(simulate(2, 25, courses, { ET2050: 'B', ET2030: 'A', ET1000: 'C' }), {
    cpa: 2.6, delta: 0.6, credits: 6, count: 2,
  });
  assert.equal(simulate(3.99, 25, courses, { ET2050: 'B' }).cpa, 4);
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
    baseCpa: 2.5, cpaCredits: 25, targetCpa: 2.5, assumedGrade: 'B',
    candidates: [course('F', 3, 0, 'retake')],
  }), { achievable: true, courses: [], credits: 0, cpa: 2.5, maxCpa: 2.5 });
});

test('a feasible plan includes the required F retakes', () => {
  const plan = planForTarget({
    baseCpa: 2, cpaCredits: 25, targetCpa: 2.1, assumedGrade: 'B',
    candidates: [course('F1', 3, 0, 'retake'), course('F2', 2, 0, 'retake'), course('C', 2, 2)],
  });
  assert.deepEqual(plan.courses, [{ code: 'F1', grade: 'B' }, { code: 'F2', grade: 'B' }]);
  assert.equal(plan.credits, 5);
  assert.equal(plan.cpa, 2.6);
});

test('a plan minimizes credits and chooses the greater gain at equal credits', () => {
  const plan = planForTarget({
    baseCpa: 2, cpaCredits: 20, targetCpa: 2.2, assumedGrade: 'B',
    candidates: [course('2', 2, 2), course('3', 3, 2), course('4a', 4, 2), course('4b', 4, 1.5)],
  });
  assert.deepEqual(plan.courses, [{ code: '4b', grade: 'B' }]);
  assert.equal(plan.credits, 4);
  assert.equal(plan.cpa, 2.3);
});

test('fractional credits are rounded up for DP but retain actual gains and cost', () => {
  const plan = planForTarget({
    baseCpa: 2, cpaCredits: 20, targetCpa: 2.1, assumedGrade: 'B',
    candidates: [course('fractional', 1.5, 1.5), course('whole', 2, 2)],
  });
  assert.deepEqual(plan.courses, [{ code: 'fractional', grade: 'B' }]);
  assert.equal(plan.credits, 1.5);
});

test('an unreachable goal reports the best attainable CPA at the assumed grade', () => {
  const plan = planForTarget({
    baseCpa: 2, cpaCredits: 20, targetCpa: 3.6, assumedGrade: 'B',
    candidates: [course('F', 2, 0, 'retake'), course('D+', 3, 1.5)],
  });
  assert.equal(plan.achievable, false);
  assert.equal(plan.maxCpa, 2.53);
});
