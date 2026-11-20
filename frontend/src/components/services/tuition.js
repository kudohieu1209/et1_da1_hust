export function semesterSummaries(records = []) {
  return [...records].sort((a, b) => String(b.semester ?? '').localeCompare(String(a.semester ?? ''), 'en', { numeric: true }));
}

function calendarDay(year, month, day) {
  const value = new Date(Date.UTC(year, month - 1, day));
  return value.getUTCFullYear() === year && value.getUTCMonth() === month - 1 && value.getUTCDate() === day
    ? value.getTime() / 86400000
    : NaN;
}

export function dueInfo(deadline, today = new Date()) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(deadline ?? '');
  if (!match) return { daysLeft: null, state: 'unknown' };
  const [, year, month, day] = match.map(Number);
  const daysLeft = calendarDay(year, month, day) - calendarDay(today.getFullYear(), today.getMonth() + 1, today.getDate());
  if (!Number.isFinite(daysLeft)) return { daysLeft: null, state: 'unknown' };
  if (daysLeft < 0) return { daysLeft, state: 'overdue' };
  return { daysLeft, state: daysLeft <= 14 ? 'soon' : 'ok' };
}

export function checkCharge({ unit_fee, fee_credits, coefficient, amount }) {
  const factor = coefficient == null || (typeof coefficient === 'string' && !coefficient.trim()) ? 1 : coefficient;
  if (![unit_fee, fee_credits, factor].every(Number.isFinite)) {
    return { expected: null, diff: null, ok: null };
  }
  const expected = unit_fee * fee_credits * factor;
  if (!Number.isFinite(amount)) return { expected, diff: null, ok: null };
  const diff = amount - expected;
  return { expected, diff, ok: Math.abs(diff) <= 1000 };
}

export function chargeTotals(charges = []) {
  return charges.reduce(({ credits, amount }, row) => ({
    credits: credits != null && Number.isFinite(row.fee_credits) ? credits + row.fee_credits : null,
    amount: amount != null && Number.isFinite(row.amount) ? amount + row.amount : null,
  }), { credits: 0, amount: 0 });
}
