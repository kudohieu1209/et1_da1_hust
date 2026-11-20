import React from 'react';
import EventCard from './EventCard';

export default function DayAgenda({ selectedDate, events = [] }) {
  const d = selectedDate instanceof Date ? selectedDate : new Date();
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const formattedDate = `${day}/${month}/${year}`;

  const classCount = events.filter((e) => e.type === 'class').length;
  const examCount = events.filter((e) => e.type === 'exam').length;

  let title = `Không có lịch học ngày ${formattedDate}`;
  if (classCount > 0 && examCount > 0) {
    title = `Bạn có ${classCount} lịch học và ${examCount} lịch thi ngày ${formattedDate}`;
  } else if (classCount > 0) {
    title = `Bạn có ${classCount} lịch học ngày ${formattedDate}`;
  } else if (examCount > 0) {
    title = `Bạn có ${examCount} lịch thi ngày ${formattedDate}`;
  }

  return (
    <section className="schedule-agenda" aria-labelledby="schedule-agenda-heading">
      <h3 id="schedule-agenda-heading" className="schedule-agenda__heading">
        {title}
      </h3>
      {events.length === 0 ? (
        <p className="schedule-agenda__empty">Chọn một ngày trên lịch để xem chi tiết lịch học và lịch thi.</p>
      ) : (
        <div className="schedule-agenda__list">
          {events.map((ev, index) => (
            <EventCard
              key={`${ev.type}-${ev.record.class_code || ev.record.course_code || index}-${index}`}
              event={ev}
            />
          ))}
        </div>
      )}
    </section>
  );
}
