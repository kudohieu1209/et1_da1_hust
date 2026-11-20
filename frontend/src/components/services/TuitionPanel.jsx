import React, { useState } from 'react';
import { display, money } from '../../schoolData';
import ResponsiveTable from './ResponsiveTable';
import { chargeTotals, checkCharge, dueInfo, semesterSummaries } from './tuition';

function TuitionSummary({ records, t, formatMoney }) {
  const [semester, setSemester] = useState(null);
  const selected = records.find((row) => row.semester === semester) ?? records[0];
  if (!selected) return null;
  const { state, daysLeft } = dueInfo(selected.deadline);
  const dueLabel = state === 'unknown' ? t('Chưa có hạn', 'No due date')
    : state === 'overdue' ? t(`Quá hạn ${-daysLeft} ngày`, `${-daysLeft} days overdue`)
      : daysLeft === 0 ? t('Đến hạn hôm nay', 'Due today')
        : t(`Còn ${daysLeft} ngày`, `${daysLeft} days left`);
  const summary = [
    ['tuition_fee', t('Phải nộp', 'Total due')],
    ['paid', t('Đã nộp', 'Paid')],
    ['debt', t('Còn nợ', 'Outstanding')],
  ];

  return (
    <section className="school-data-card services-stack">
      <div className="services-section-heading">
        <h3>{t('Tóm tắt học phí theo kỳ', 'Tuition summary by semester')}</h3>
        <label>{t('Học kỳ', 'Semester')}{' '}
          <select className="services-select" value={selected.semester ?? ''} onChange={(event) => setSemester(event.target.value)}>
            {records.map((row, index) => <option key={index} value={row.semester ?? ''}>{display(row.semester)}</option>)}
          </select>
        </label>
      </div>
      <dl className="services-summary">
        {summary.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{formatMoney(selected[key])}</dd></div>)}
        <div>
          <dt>{t('Hạn nộp', 'Due date')}</dt>
          {state !== 'unknown' && <dd><time dateTime={selected.deadline}>{selected.deadline}</time></dd>}
          <dd className={`services-due services-due--${state}`}>{dueLabel}</dd>
        </div>
      </dl>
      <p className="services-note">{t('Trạng thái CTT', 'CTT status')} · {display(selected.status)}</p>
      {selected.debt > 0 && ['soon', 'overdue'].includes(state) && (
        <p className={`services-reminder services-due--${state}`} role="status">
          {t('Học phí còn nợ', 'Outstanding tuition')} {formatMoney(selected.debt)} · {dueLabel}
        </p>
      )}
    </section>
  );
}

export default function TuitionPanel({ section, t }) {
  const records = semesterSummaries(section?.records ?? []);
  const charges = section?.charges ?? [];
  const payments = section?.payments ?? [];
  const totals = chargeTotals(charges);
  const formatMoney = (value) => Number.isFinite(value) ? money(value) : t('Chưa có dữ liệu', 'Unavailable');
  const totalDifference = records.length === 1 && totals.amount != null && Number.isFinite(records[0].tuition_fee)
    ? Math.round((totals.amount - records[0].tuition_fee) * 100) / 100
    : null;
  const chargeColumns = [
    ['course_code', t('Mã HP', 'Code')],
    ['course_name', t('Học phần', 'Course')],
    ['unit_fee', t('Đơn giá / TC', 'Fee per credit'), formatMoney],
    ['fee_credits', t('TC học phí', 'Fee credits')],
    ['coefficient', t('Hệ số', 'Multiplier')],
    ['amount', t('Tổng tiền', 'Amount'), (value, row) => {
      const { diff, ok } = checkCharge(row);
      if (ok !== false) return formatMoney(value);
      const difference = formatMoney(Math.abs(diff));
      return <>{formatMoney(value)} <span className="services-charge-badge">
        {t(`Lệch ${difference} so với đơn giá × TC × hệ số`, `${difference} difference from fee × credits × multiplier`)}
      </span></>;
    }],
    ['registration_status', t('Trạng thái đăng ký', 'Registration status')],
    ['registration_type', t('Loại đăng ký', 'Registration type')],
    ['notes', t('Ghi chú', 'Notes')],
  ];
  return (
    <>
      <TuitionSummary records={records} t={t} formatMoney={formatMoney} />
      {charges.length > 0 && (
        <section className="school-data-card services-stack">
          <h3>{t('Học phí theo học phần (theo CTT)', 'Tuition by course (from CTT)')}</h3>
          <p className="services-note">
            {t('Tổng tín chỉ học phí', 'Total fee credits')} · <strong>{display(totals.credits)}</strong>
            {' / '}{t('Tổng tiền', 'Total amount')} · <strong>{formatMoney(totals.amount)}</strong>
          </p>
          {totalDifference != null && totalDifference !== 0 && <p className="services-note">
            {t(`Tổng theo học phần lệch ${formatMoney(Math.abs(totalDifference))} so với số phải nộp kỳ ${records[0].semester}.`,
              `Course charges differ from the amount due for semester ${records[0].semester} by ${formatMoney(Math.abs(totalDifference))}.`)}
          </p>}
          <ResponsiveTable columns={chargeColumns} rows={charges} />
        </section>
      )}
      {payments.length > 0 && (
        <section className="school-data-card services-stack">
          <h3>{t('Các khoản thu theo CTT', 'Payments listed by CTT')}</h3>
          <ResponsiveTable cards rows={payments} columns={[
            ['label', t('Loại tiền', 'Payment type')], ['amount', t('Số tiền', 'Amount'), formatMoney],
            ['coefficient', t('Hệ số đóng', 'Multiplier')], ['actual_amount', t('Thực đóng', 'Actual payment'), formatMoney],
            ['updated_at', t('Ngày cập nhật', 'Updated')], ['notes', t('Ghi chú', 'Notes')],
          ]} />
          <p className="services-note">{t('Giữ nguyên tên khoản thu của CTT. Các khoản này chưa đủ để xác định số tiền còn nợ.',
            'Payment labels are shown as supplied by CTT. These payments alone cannot determine the outstanding balance.')}</p>
        </section>
      )}
      {!records.length && !charges.length && !payments.length && !section?.tables?.length &&
        <p className="school-data-empty">{t('Chưa có bảng học phí từ CTT để hiển thị.', 'No CTT tuition data to display.')}</p>}
    </>
  );
}
