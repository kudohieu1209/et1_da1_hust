import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ACADEMIC_YEARS,
  academicYearFor,
  weekOf,
  dateOf,
  parseWeeks,
  parseClock,
  sessionLabel,
  parseExamDate,
  buildMonthGrid,
  eventsByDay,
  formatDateKey,
  parseLocalDate,
} from './calendar.js';

test('ACADEMIC_YEARS and academicYearFor identify verified and provisional years', () => {
  assert.equal(ACADEMIC_YEARS.length, 2);
  assert.equal(ACADEMIC_YEARS[0].id, '2026-2027');
  assert.equal(ACADEMIC_YEARS[0].provisional, false);
  assert.equal(ACADEMIC_YEARS[1].id, '2027-2028');
  assert.equal(ACADEMIC_YEARS[1].provisional, true);

  const y1 = academicYearFor('2026-11-20');
  assert.equal(y1?.id, '2026-2027');
  assert.equal(y1?.provisional, false);

  const y2 = academicYearFor('2027-09-01');
  assert.equal(y2?.id, '2027-2028');
  assert.equal(y2?.provisional, true);

  assert.equal(academicYearFor('2025-01-01'), null);
});

test('weekOf returns correct week number and academic year', () => {
  assert.deepEqual(weekOf('2026-11-20'), { yearId: '2026-2027', week: 12, provisional: false });
  assert.deepEqual(weekOf(new Date(2026, 10, 20)), { yearId: '2026-2027', week: 12, provisional: false });
  assert.deepEqual(weekOf('2026-08-31'), { yearId: '2026-2027', week: 1, provisional: false });
  assert.deepEqual(weekOf('2027-01-25'), { yearId: '2026-2027', week: 22, provisional: false });
  assert.equal(weekOf('2026-08-30'), null);
});

test('dateOf converts year, week, and day-of-week to local Date', () => {
  const d1 = dateOf('2026-2027', 12, 6);
  assert.equal(formatDateKey(d1), '2026-11-20');

  const d2 = dateOf('2026-2027', 1, 8);
  assert.equal(formatDateKey(d2), '2026-09-06');
});

test('parseWeeks handles expected formats and rejects invalid strings', () => {
  assert.deepEqual(Array.from(parseWeeks('1-16')).sort((a, b) => a - b), Array.from({ length: 16 }, (_, i) => i + 1));
  assert.deepEqual(
    Array.from(parseWeeks('2-9,11-18')).sort((a, b) => a - b),
    [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18],
  );
  assert.deepEqual(Array.from(parseWeeks('2, 4, 6')).sort((a, b) => a - b), [2, 4, 6]);
  assert.deepEqual(
    Array.from(parseWeeks('1-8;10-17')).sort((a, b) => a - b),
    [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17],
  );
  assert.deepEqual(
    Array.from(parseWeeks('Tuần 2-9, 11-18')).sort((a, b) => a - b),
    [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18],
  );

  assert.equal(parseWeeks(''), null);
  assert.equal(parseWeeks('   '), null);
  assert.equal(parseWeeks(null), null);
  assert.equal(parseWeeks('không rõ'), null);
  assert.equal(parseWeeks('9-2'), null);
  assert.equal(parseWeeks('tuần abc'), null);
});

test('parseClock handles valid time ranges and rejects invalid hours/minutes', () => {
  assert.deepEqual(parseClock('12:30 - 14:55'), { start: '12:30', end: '14:55' });
  assert.deepEqual(parseClock('12h30-14h55'), { start: '12:30', end: '14:55' });
  assert.deepEqual(parseClock('1230-1455'), { start: '12:30', end: '14:55' });

  assert.equal(parseClock('25:00-26:00'), null);
  assert.equal(parseClock('12:65-14:00'), null);
  assert.equal(parseClock('random-text'), null);
  assert.equal(parseClock(''), null);
  assert.equal(parseClock(null), null);
});

test('sessionLabel returns Sáng, Chiều, Tối according to start hour', () => {
  assert.equal(sessionLabel('07:30'), 'Sáng');
  assert.equal(sessionLabel('11:55'), 'Sáng');
  assert.equal(sessionLabel('12:00'), 'Chiều');
  assert.equal(sessionLabel('14:55'), 'Chiều');
  assert.equal(sessionLabel('17:59'), 'Chiều');
  assert.equal(sessionLabel('18:00'), 'Tối');
  assert.equal(sessionLabel('20:00'), 'Tối');
  assert.equal(sessionLabel(''), '');
  assert.equal(sessionLabel(null), '');
});

test('parseExamDate parses dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd and rejects non-existent dates', () => {
  assert.equal(parseExamDate('08/01/2027'), '2027-01-08');
  assert.equal(parseExamDate('8-1-2027'), '2027-01-08');
  assert.equal(parseExamDate('2027-01-08'), '2027-01-08');

  assert.equal(parseExamDate('31/02/2027'), null);
  assert.equal(parseExamDate('invalid'), null);
  assert.equal(parseExamDate(''), null);
  assert.equal(parseExamDate(null), null);
});

test('buildMonthGrid returns 42 cells starting on Monday', () => {
  const grid = buildMonthGrid(2026, 10); // November 2026
  assert.equal(grid.length, 42);
  assert.equal(grid[0].key, '2026-10-26'); // Monday Oct 26, 2026
  assert.equal(grid[0].inMonth, false);

  const nov1 = grid.find((c) => c.key === '2026-11-01');
  assert.ok(nov1);
  assert.equal(nov1.inMonth, true);

  const nov30 = grid.find((c) => c.key === '2026-11-30');
  assert.ok(nov30);
  assert.equal(nov30.inMonth, true);

  assert.equal(grid[41].key, '2026-12-06'); // Sunday Dec 6, 2026
});

test('eventsByDay organizes classes and exams correctly', () => {
  const records = [
    {
      course_code: 'PH3330',
      course_name: 'Vật lý điện tử',
      class_code: '173759',
      day_of_week: 6, // Thứ 6
      start_period: 1,
      end_period: 3,
      time_str: '12:30 - 14:55',
      room: 'D9-502',
      weeks: '2-9,11-18',
    },
    {
      course_code: 'ET2030',
      course_name: 'Kỹ thuật lập trình',
      class_code: '123456',
      day_of_week: 6,
      start_period: 4,
      end_period: 6,
      time_str: '15:05 - 17:30',
      room: 'D3-201',
      weeks: '1-16',
    },
    {
      course_code: 'INVALID01',
      course_name: 'Lớp lỗi tuần',
      class_code: '999999',
      day_of_week: 2,
      weeks: 'chưa xếp tuần',
    },
  ];

  const exams = [
    {
      course_code: 'PH3330',
      course_name: 'Vật lý điện tử',
      class_code: '173759',
      exam_date: '08/01/2027',
      exam_time: '07:30',
      room: 'D9-502',
    },
  ];

  const map = eventsByDay(records, exams, '2026-10-01', '2027-01-31');

  // Week 12 Friday is 2026-11-20
  const nov20 = map.get('2026-11-20');
  assert.ok(nov20);
  assert.equal(nov20.length, 2);
  assert.equal(nov20[0].record.course_code, 'PH3330'); // 12:30
  assert.equal(nov20[1].record.course_code, 'ET2030'); // 15:05

  // Week 10 Friday is 2026-11-06 (PH3330 has weeks 2-9,11-18 so it should NOT be here)
  const nov06 = map.get('2026-11-06');
  assert.ok(nov06);
  assert.equal(nov06.some((ev) => ev.record.course_code === 'PH3330'), false);
  assert.equal(nov06.some((ev) => ev.record.course_code === 'ET2030'), true);

  // Exam on 2027-01-08
  const jan08 = map.get('2027-01-08');
  assert.ok(jan08);
  const examEv = jan08.find((ev) => ev.type === 'exam');
  assert.ok(examEv);
  assert.equal(examEv.record.course_code, 'PH3330');

  // Unplaced classes
  assert.equal(map.unplaced.length, 1);
  assert.equal(map.unplaced[0].course_code, 'INVALID01');
});

test('timezone consistency across local midnight calculations', () => {
  const d = parseLocalDate('2026-11-20');
  assert.equal(formatDateKey(d), '2026-11-20');
  assert.equal(d.getFullYear(), 2026);
  assert.equal(d.getMonth(), 10);
  assert.equal(d.getDate(), 20);

  const weekInfo = weekOf('2026-11-20');
  assert.equal(weekInfo.week, 12);
  const back = dateOf(weekInfo.yearId, weekInfo.week, 6);
  assert.equal(formatDateKey(back), '2026-11-20');
});
