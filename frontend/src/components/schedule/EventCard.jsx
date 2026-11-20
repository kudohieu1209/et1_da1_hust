import React from 'react';
import { Code2, MapPin, CalendarDays, User, Clock, Hash, FileText } from 'lucide-react';
import { sessionLabel } from './calendar';

function formatSessionInfo(record, start, end) {
  const parts = [];
  const session = sessionLabel(start);
  const dayMap = { 2: 'Thứ 2', 3: 'Thứ 3', 4: 'Thứ 4', 5: 'Thứ 5', 6: 'Thứ 6', 7: 'Thứ 7', 8: 'Chủ Nhật' };
  const day = dayMap[Number(record.day_of_week)];
  const daySession = [session, day].filter(Boolean).join(' ');
  if (daySession) parts.push(daySession);

  if (record.start_period != null && record.end_period != null) {
    parts.push(`Tiết ${record.start_period} - ${record.end_period}`);
  } else if (record.start_period != null) {
    parts.push(`Tiết ${record.start_period}`);
  }

  const clockText = record.time_str || (start && end ? `${start} - ${end}` : (start || ''));
  let combined = parts.join(', ');
  if (clockText) {
    combined = combined ? `${combined} [${clockText}]` : `[${clockText}]`;
  }
  return combined;
}

export default function EventCard({ event }) {
  const { type, week, start, end, record } = event;

  if (type === 'exam') {
    return (
      <article className="schedule-card schedule-card--exam">
        <div className="schedule-card__time">
          <span className="schedule-card__start">{start || 'Ca thi'}</span>
          {end && <span className="schedule-card__end">{end}</span>}
        </div>
        <div className="schedule-card__divider schedule-card__divider--exam" />
        <div className="schedule-card__content">
          <div className="schedule-card__header">
            <h4 className="schedule-card__title">
              {record.course_code ? `${record.course_code} - ${record.course_name || 'Môn thi'}` : (record.course_name || 'Lịch thi')}
            </h4>
            <span className="schedule-badge schedule-badge--exam">Lịch thi</span>
          </div>
          <div className="schedule-card__details">
            {record.class_code && (
              <div className="schedule-card__row">
                <Hash size={14} className="schedule-card__icon" />
                <span>Mã lớp: {record.class_code}</span>
              </div>
            )}
            {record.room && (
              <div className="schedule-card__row">
                <MapPin size={14} className="schedule-card__icon" />
                <span>Phòng {record.room}</span>
              </div>
            )}
            {record.exam_time && (
              <div className="schedule-card__row">
                <Clock size={14} className="schedule-card__icon" />
                <span>Ca / giờ: {record.exam_time}</span>
              </div>
            )}
            {record.exam_type && (
              <div className="schedule-card__row">
                <FileText size={14} className="schedule-card__icon" />
                <span>Hình thức: {record.exam_type}</span>
              </div>
            )}
            {record.student_index && (
              <div className="schedule-card__row">
                <Hash size={14} className="schedule-card__icon" />
                <span>SBD: {record.student_index}</span>
              </div>
            )}
          </div>
        </div>
      </article>
    );
  }

  // Type === 'class'
  const sessionText = formatSessionInfo(record, start, end);

  return (
    <article className="schedule-card schedule-card--class">
      <div className="schedule-card__time">
        {start ? (
          <>
            <span className="schedule-card__start">{start}</span>
            {end && <span className="schedule-card__end">{end}</span>}
          </>
        ) : record.start_period != null ? (
          <>
            <span className="schedule-card__start">Tiết {record.start_period}</span>
            {record.end_period != null && <span className="schedule-card__end">Tiết {record.end_period}</span>}
          </>
        ) : (
          <span className="schedule-card__start">—</span>
        )}
      </div>
      <div className="schedule-card__divider" />
      <div className="schedule-card__content">
        <div className="schedule-card__header">
          <h4 className="schedule-card__title">
            {record.class_code} - {record.course_name}
          </h4>
          {record.is_temp && <span className="schedule-badge schedule-badge--temp">Lớp tạm thời</span>}
        </div>
        <div className="schedule-card__details">
          {record.course_code && (
            <div className="schedule-card__row">
              <Code2 size={14} className="schedule-card__icon" />
              <span>Mã HP: {record.course_code}</span>
            </div>
          )}
          {record.room && (
            <div className="schedule-card__row">
              <MapPin size={14} className="schedule-card__icon" />
              <span>Phòng {record.room}</span>
            </div>
          )}
          {sessionText && (
            <div className="schedule-card__row">
              <CalendarDays size={14} className="schedule-card__icon" />
              <span>{sessionText}</span>
            </div>
          )}
          {week != null && (
            <div className="schedule-card__row">
              <CalendarDays size={14} className="schedule-card__icon" />
              <span>Tuần {week}</span>
            </div>
          )}
          {record.lecturer && (
            <div className="schedule-card__row">
              <User size={14} className="schedule-card__icon" />
              <span>Giảng viên: {record.lecturer}</span>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
