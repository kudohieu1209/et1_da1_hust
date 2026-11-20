/**
 * Academic year definitions and calendar calculations for HUST schedule.
 * All date arithmetic is performed in local time.
 */

export const ACADEMIC_YEARS = [
  { id: '2026-2027', week1Monday: '2026-08-31', source: 'ke_hoach_nam_hoc_2026_2027_verified.md', provisional: false },
  { id: '2027-2028', week1Monday: '2027-08-23', source: 'ke_hoach_nam_hoc_2026_2027_verified.md', provisional: true },
];

/**
 * Parses a Date object or YYYY-MM-DD string into a local midnight Date.
 */
export function parseLocalDate(val) {
  if (val instanceof Date) {
    if (Number.isNaN(val.getTime())) return null;
    return new Date(val.getFullYear(), val.getMonth(), val.getDate());
  }
  if (typeof val === 'string') {
    const m = val.trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) {
      const year = Number(m[1]);
      const month = Number(m[2]) - 1;
      const day = Number(m[3]);
      const d = new Date(year, month, day);
      if (d.getFullYear() === year && d.getMonth() === month && d.getDate() === day) {
        return d;
      }
    }
  }
  return null;
}

/**
 * Formats a Date object into YYYY-MM-DD local date string without toISOString() timezone shift.
 */
export function formatDateKey(d) {
  if (!d || Number.isNaN(d.getTime())) return '';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Returns the academic year object covering the given date, or null if outside known years.
 * The last year in ACADEMIC_YEARS extends at most 52 weeks (52 * 7 days).
 */
export function academicYearFor(date) {
  const target = parseLocalDate(date);
  if (!target) return null;

  for (let i = 0; i < ACADEMIC_YEARS.length; i++) {
    const current = ACADEMIC_YEARS[i];
    const start = parseLocalDate(current.week1Monday);
    let nextStart;
    if (i < ACADEMIC_YEARS.length - 1) {
      nextStart = parseLocalDate(ACADEMIC_YEARS[i + 1].week1Monday);
    } else {
      nextStart = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 52 * 7);
    }
    if (target >= start && target < nextStart) {
      return current;
    }
  }
  return null;
}

/**
 * Returns { yearId, week, provisional } or null.
 */
export function weekOf(date) {
  const target = parseLocalDate(date);
  if (!target) return null;

  const year = academicYearFor(target);
  if (!year) return null;

  const start = parseLocalDate(year.week1Monday);
  const diffDays = Math.round((target.getTime() - start.getTime()) / 86400000);
  if (diffDays < 0) return null;

  const week = Math.floor(diffDays / 7) + 1;
  return { yearId: year.id, week, provisional: year.provisional };
}

/**
 * Returns local Date for the given week and day of week.
 * dayOfWeek follows CTT standard: 2 = Thứ Hai ... 7 = Thứ Bảy, 8 = Chủ Nhật.
 */
export function dateOf(yearId, week, dayOfWeek) {
  const year = ACADEMIC_YEARS.find((y) => y.id === yearId);
  if (!year) return null;

  const dayNum = Number(dayOfWeek);
  if (dayNum < 2 || dayNum > 8) return null;
  if (typeof week !== 'number' || week < 1) return null;

  const start = parseLocalDate(year.week1Monday);
  const totalDaysOffset = (week - 1) * 7 + (dayNum - 2);
  return new Date(start.getFullYear(), start.getMonth(), start.getDate() + totalDaysOffset);
}

/**
 * Parses CTT weeks string like "1-16", "2-9,11-18", "2, 4, 6", "1-8;10-17".
 * Returns Set<number> of week numbers, or null if invalid or unparseable.
 */
export function parseWeeks(text) {
  if (text == null) return null;
  let str = String(text).trim();
  if (!str) return null;

  str = str.replace(/^(?:tuần|tuan)\s*/i, '').trim();
  if (!str) return null;

  const parts = str.split(/[,;]+/).map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return null;

  const result = new Set();
  for (const part of parts) {
    if (/^\d+$/.test(part)) {
      const num = Number(part);
      if (num < 1 || num > 60) return null;
      result.add(num);
    } else {
      const match = part.match(/^(\d+)\s*[-–—]\s*(\d+)$/);
      if (!match) return null;
      const start = Number(match[1]);
      const end = Number(match[2]);
      if (start < 1 || end > 60 || start >= end) return null;
      for (let w = start; w <= end; w++) {
        result.add(w);
      }
    }
  }

  return result.size > 0 ? result : null;
}

/**
 * Parses clock range like "12:30 - 14:55", "12h30-14h55", "1230-1455".
 * Returns { start: '12:30', end: '14:55' } or null.
 */
export function parseClock(timeStr) {
  if (timeStr == null) return null;
  const str = String(timeStr).trim();
  if (!str) return null;

  const parts = str.split(/\s*[-–—]\s*/);
  if (parts.length !== 2) return null;

  function parseTimePart(s) {
    const raw = s.trim();
    let m = raw.match(/^(\d{1,2}):(\d{2})$/);
    if (m) {
      const h = Number(m[1]);
      const min = Number(m[2]);
      if (h >= 0 && h <= 23 && min >= 0 && min <= 59) {
        return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
      }
      return null;
    }
    m = raw.match(/^(\d{1,2})h(\d{2})$/i);
    if (m) {
      const h = Number(m[1]);
      const min = Number(m[2]);
      if (h >= 0 && h <= 23 && min >= 0 && min <= 59) {
        return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
      }
      return null;
    }
    m = raw.match(/^(\d{2})(\d{2})$/);
    if (m) {
      const h = Number(m[1]);
      const min = Number(m[2]);
      if (h >= 0 && h <= 23 && min >= 0 && min <= 59) {
        return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
      }
      return null;
    }
    return null;
  }

  const start = parseTimePart(parts[0]);
  const end = parseTimePart(parts[1]);
  if (!start || !end) return null;

  return { start, end };
}

/**
 * Returns 'Sáng' if start < 12:00, 'Chiều' if start < 18:00, otherwise 'Tối'.
 * If no valid start time, returns ''.
 */
export function sessionLabel(start) {
  if (!start || typeof start !== 'string') return '';
  const m = start.match(/^(\d{1,2}):/);
  if (!m) return '';
  const hour = Number(m[1]);
  if (hour < 12) return 'Sáng';
  if (hour < 18) return 'Chiều';
  return 'Tối';
}

/**
 * Parses exam date like dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd.
 * Returns date key 'YYYY-MM-DD' or null.
 */
export function parseExamDate(text) {
  if (text == null) return null;
  const s = String(text).trim();
  if (!s) return null;

  let y, m, d;
  let match = s.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/);
  if (match) {
    d = Number(match[1]);
    m = Number(match[2]);
    y = Number(match[3]);
  } else {
    match = s.match(/^(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})$/);
    if (match) {
      y = Number(match[1]);
      m = Number(match[2]);
      d = Number(match[3]);
    } else {
      return null;
    }
  }

  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  const dateObj = new Date(y, m - 1, d);
  if (dateObj.getFullYear() !== y || dateObj.getMonth() !== (m - 1) || dateObj.getDate() !== d) {
    return null;
  }

  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

/**
 * Builds 6 rows x 7 columns grid for given year and month (0-indexed).
 * Week starts on Monday. Returns 42 cells.
 */
export function buildMonthGrid(year, month) {
  const firstDay = new Date(year, month, 1);
  const daysBefore = (firstDay.getDay() + 6) % 7;
  const startDate = new Date(year, month, 1 - daysBefore);
  const todayKey = formatDateKey(new Date());

  const grid = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate() + i);
    const key = formatDateKey(d);
    grid.push({
      key,
      date: d,
      inMonth: d.getMonth() === month && d.getFullYear() === year,
      isToday: key === todayKey,
    });
  }
  return grid;
}

/**
 * Groups classes and exams by date key 'YYYY-MM-DD' within [rangeStart, rangeEnd].
 * Returns a Map<key, Event[]> with an unplaced array property.
 */
export function eventsByDay(records, exams, rangeStart, rangeEnd) {
  const map = new Map();
  const unplaced = [];

  const startKey = rangeStart ? (typeof rangeStart === 'string' ? rangeStart : formatDateKey(rangeStart)) : null;
  const endKey = rangeEnd ? (typeof rangeEnd === 'string' ? rangeEnd : formatDateKey(rangeEnd)) : null;

  function addEvent(key, ev) {
    if ((!startKey || key >= startKey) && (!endKey || key <= endKey)) {
      let list = map.get(key);
      if (!list) {
        list = [];
        map.set(key, list);
      }
      list.push(ev);
    }
  }

  for (const record of records || []) {
    const parsedWeeks = parseWeeks(record.weeks);
    const dayOfWeek = Number(record.day_of_week);
    if (!parsedWeeks || !dayOfWeek || dayOfWeek < 2 || dayOfWeek > 8) {
      unplaced.push(record);
      continue;
    }

    const clock = parseClock(record.time_str);
    const start = clock ? clock.start : null;
    const end = clock ? clock.end : null;
    let sortKey = start;
    if (!sortKey) {
      sortKey = record.start_period != null ? `P${String(record.start_period).padStart(2, '0')}` : 'ZZ';
    }

    for (const week of parsedWeeks) {
      for (const year of ACADEMIC_YEARS) {
        const d = dateOf(year.id, week, dayOfWeek);
        if (!d) continue;
        const key = formatDateKey(d);
        const yCover = academicYearFor(d);
        if (!yCover || yCover.id !== year.id) continue;

        addEvent(key, {
          type: 'class',
          key,
          week,
          start,
          end,
          sortKey,
          record,
        });
      }
    }
  }

  for (const exam of exams || []) {
    const examKey = parseExamDate(exam.exam_date);
    if (!examKey) continue;

    const clock = parseClock(exam.exam_time);
    const start = clock ? clock.start : (exam.exam_time || '');
    const end = clock ? clock.end : '';
    const sortKey = clock ? clock.start : (exam.exam_time || '99:99');

    addEvent(examKey, {
      type: 'exam',
      key: examKey,
      week: null,
      start,
      end,
      sortKey,
      record: exam,
    });
  }

  for (const list of map.values()) {
    list.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  }

  map.unplaced = unplaced;
  return map;
}
