import assert from 'node:assert/strict';
import test from 'node:test';
import { chargeTotals, checkCharge, dueInfo, semesterSummaries } from './tuition.js';
import { compareClassmates } from './classmates.js';

test('dueInfo compares local calendar dates and validates deadlines', () => {
  const today = new Date(2026, 10, 20, 23, 40);
  assert.deepEqual(dueInfo('2026-11-19', today), { daysLeft: -1, state: 'overdue' });
  assert.deepEqual(dueInfo('2026-11-20', today), { daysLeft: 0, state: 'soon' });
  assert.deepEqual(dueInfo('2026-12-04', today), { daysLeft: 14, state: 'soon' });
  assert.deepEqual(dueInfo('2026-12-05', today), { daysLeft: 15, state: 'ok' });
  assert.deepEqual(dueInfo(null, today), { daysLeft: null, state: 'unknown' });
  assert.deepEqual(dueInfo('2026-02-30', today), { daysLeft: null, state: 'unknown' });
});

test('checkCharge allows a 1000 VND difference and handles missing amounts', () => {
  const row = { unit_fee: 400000, fee_credits: 3, coefficient: 1.5, amount: 1800000 };
  assert.deepEqual(checkCharge(row), { expected: 1800000, diff: 0, ok: true });
  assert.equal(checkCharge({ ...row, amount: 1799000 }).ok, true);
  assert.equal(checkCharge({ ...row, amount: 1801001 }).ok, false);
  assert.equal(checkCharge({ ...row, fee_credits: null }).ok, null);
  assert.deepEqual(checkCharge({ ...row, amount: null }), { expected: 1800000, diff: null, ok: null });
  assert.deepEqual(checkCharge({ ...row, coefficient: '', amount: 1200000 }), { expected: 1200000, diff: 0, ok: true });
});

test('semesterSummaries sorts without modifying the original list', () => {
  const records = ['2025.2', '2026.1', '2025.3'].map((semester) => ({ semester }));
  assert.deepEqual(semesterSummaries(records).map((row) => row.semester), ['2026.1', '2025.3', '2025.2']);
  assert.equal(records[0].semester, '2025.2');
});

test('chargeTotals preserves a zero and avoids reporting incomplete sums as totals', () => {
  assert.deepEqual(chargeTotals([{ fee_credits: 2, amount: 0 }, { fee_credits: 3, amount: 600000 }]), { credits: 5, amount: 600000 });
  assert.deepEqual(chargeTotals([{ fee_credits: 3, amount: null }]), { credits: 3, amount: null });
});

test('classmates sort by Vietnamese given name and then by family and middle names', () => {
  const names = ['Bùi Bình', 'Nguyễn Anh', 'Lê Anh', 'Nguyễn Ánh', 'Hồ Đạt', 'Vũ Duy'];
  const sorted = names.map((student_name) => ({ student_name })).sort(compareClassmates);
  assert.deepEqual(sorted.map((row) => row.student_name), ['Lê Anh', 'Nguyễn Anh', 'Nguyễn Ánh', 'Bùi Bình', 'Vũ Duy', 'Hồ Đạt']);
});
