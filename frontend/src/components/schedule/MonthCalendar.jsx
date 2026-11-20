import React, { useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { buildMonthGrid, formatDateKey } from './calendar';

const DAY_HEADERS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
const DAY_FULL_NAMES = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];

export default function MonthCalendar({
  displayedYear,
  displayedMonth,
  selectedDate,
  onSelectDate,
  onChangeMonth,
  eventsMap = new Map(),
}) {
  const gridRef = useRef(null);
  const selectedKey = formatDateKey(selectedDate);
  const gridCells = buildMonthGrid(displayedYear, displayedMonth);

  const prevMonth = () => {
    if (displayedMonth === 0) {
      onChangeMonth(displayedYear - 1, 11);
    } else {
      onChangeMonth(displayedYear, displayedMonth - 1);
    }
  };

  const nextMonth = () => {
    if (displayedMonth === 11) {
      onChangeMonth(displayedYear + 1, 0);
    } else {
      onChangeMonth(displayedYear, displayedMonth + 1);
    }
  };

  const goToday = () => {
    const today = new Date();
    onSelectDate(today);
    onChangeMonth(today.getFullYear(), today.getMonth());
  };

  const handleKeyDown = (e, cellDate) => {
    let deltaDays = 0;
    let handled = false;

    switch (e.key) {
      case 'ArrowLeft':
        deltaDays = -1;
        handled = true;
        break;
      case 'ArrowRight':
        deltaDays = 1;
        handled = true;
        break;
      case 'ArrowUp':
        deltaDays = -7;
        handled = true;
        break;
      case 'ArrowDown':
        deltaDays = 7;
        handled = true;
        break;
      case 'Home': {
        // Move to Monday of current week
        const dayOfWeek = (cellDate.getDay() + 6) % 7; // 0 for Mon ... 6 for Sun
        deltaDays = -dayOfWeek;
        handled = true;
        break;
      }
      case 'End': {
        // Move to Sunday of current week
        const dayOfWeek = (cellDate.getDay() + 6) % 7;
        deltaDays = 6 - dayOfWeek;
        handled = true;
        break;
      }
      case 'PageUp': {
        e.preventDefault();
        prevMonth();
        const prevMonthDate = new Date(cellDate.getFullYear(), cellDate.getMonth() - 1, cellDate.getDate());
        onSelectDate(prevMonthDate);
        return;
      }
      case 'PageDown': {
        e.preventDefault();
        nextMonth();
        const nextMonthDate = new Date(cellDate.getFullYear(), cellDate.getMonth() + 1, cellDate.getDate());
        onSelectDate(nextMonthDate);
        return;
      }
      default:
        break;
    }

    if (handled) {
      e.preventDefault();
      const newDate = new Date(cellDate.getFullYear(), cellDate.getMonth(), cellDate.getDate() + deltaDays);
      onSelectDate(newDate);
      if (newDate.getMonth() !== displayedMonth || newDate.getFullYear() !== displayedYear) {
        onChangeMonth(newDate.getFullYear(), newDate.getMonth());
      }
    }
  };

  // Focus the selected button when roving
  useEffect(() => {
    if (gridRef.current) {
      const activeBtn = gridRef.current.querySelector('button[aria-selected="true"]');
      if (activeBtn && document.activeElement && gridRef.current.contains(document.activeElement)) {
        activeBtn.focus();
      }
    }
  }, [selectedKey]);

  // Year options: ±2 years around current display year
  const yearOptions = [];
  for (let y = displayedYear - 2; y <= displayedYear + 2; y++) {
    yearOptions.push(y);
  }

  return (
    <div className="schedule-calendar" aria-label="Lịch tháng">
      <div className="schedule-calendar__controls">
        <div className="schedule-calendar__nav">
          <button
            type="button"
            className="schedule-btn-nav"
            onClick={prevMonth}
            aria-label="Tháng trước"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="schedule-calendar__selectors">
            <select
              aria-label="Chọn tháng"
              className="schedule-select"
              value={displayedMonth}
              onChange={(e) => onChangeMonth(displayedYear, Number(e.target.value))}
            >
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i} value={i}>
                  Tháng {i + 1}
                </option>
              ))}
            </select>
            <select
              aria-label="Chọn năm"
              className="schedule-select"
              value={displayedYear}
              onChange={(e) => onChangeMonth(Number(e.target.value), displayedMonth)}
            >
              {yearOptions.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="schedule-btn-nav"
            onClick={nextMonth}
            aria-label="Tháng sau"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <button
          type="button"
          className="schedule-btn-today"
          onClick={goToday}
        >
          Hôm nay
        </button>
      </div>

      <div className="schedule-grid" role="grid" aria-label="Lưới lịch tháng" ref={gridRef}>
        <div className="schedule-grid__header-row" role="row">
          {DAY_HEADERS.map((header, idx) => (
            <div key={idx} className="schedule-grid__col-header" role="columnheader">
              {header}
            </div>
          ))}
        </div>

        <div className="schedule-grid__body">
          {Array.from({ length: 6 }, (_, rowIdx) => (
            <div key={rowIdx} className="schedule-grid__row" role="row">
              {gridCells.slice(rowIdx * 7, (rowIdx + 1) * 7).map((cell) => {
                const isSelected = cell.key === selectedKey;
                const events = eventsMap?.get(cell.key) || [];
                const hasClass = events.some((e) => e.type === 'class');
                const hasExam = events.some((e) => e.type === 'exam');
                const classCount = events.filter((e) => e.type === 'class').length;
                const examCount = events.filter((e) => e.type === 'exam').length;

                const dayName = DAY_FULL_NAMES[cell.date.getDay()];
                const dayStr = `${String(cell.date.getDate()).padStart(2, '0')}/${String(cell.date.getMonth() + 1).padStart(2, '0')}/${cell.date.getFullYear()}`;
                const labelParts = [`${dayName} ${dayStr}`];
                if (classCount > 0) labelParts.push(`${classCount} lịch học`);
                if (examCount > 0) labelParts.push(`${examCount} lịch thi`);
                const ariaLabel = labelParts.join(', ');

                let cellClass = 'schedule-day';
                if (!cell.inMonth) cellClass += ' schedule-day--other-month';
                if (cell.isToday) cellClass += ' schedule-day--today';
                if (isSelected) cellClass += ' schedule-day--selected';

                return (
                  <div key={cell.key} role="gridcell" className="schedule-grid__cell">
                    <button
                      type="button"
                      role="button"
                      className={cellClass}
                      aria-label={ariaLabel}
                      aria-selected={isSelected}
                      tabIndex={isSelected ? 0 : -1}
                      onClick={() => onSelectDate(cell.date)}
                      onKeyDown={(e) => handleKeyDown(e, cell.date)}
                    >
                      <span className="schedule-day__number">{cell.date.getDate()}</span>
                      <span className="schedule-day__dots" aria-hidden="true">
                        {hasClass && <span className="schedule-dot schedule-dot--class" />}
                        {hasExam && <span className="schedule-dot schedule-dot--exam" />}
                      </span>
                    </button>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
