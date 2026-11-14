import React, { useState } from 'react';
import { RefreshCw, ExternalLink } from 'lucide-react';
import { display } from '../schoolData';
import './SchoolDataPanel.css';

export function SchoolSectionState({ section, onSync, title }) {
  const status = section?.status || 'not_synced';
  const labels = { synced: 'Đã đồng bộ', empty: 'CTT không có bản ghi', partial: 'Đã lấy được một phần', stale: 'Dữ liệu lần trước', error: 'Chưa cập nhật được', unavailable: 'Chưa nhận diện được dữ liệu', not_synced: 'Chưa đồng bộ' };
  const stamp = section?.synced_at && new Date(section.synced_at);
  const source = section?.source_url?.startsWith('https://ctt-sis.hust.edu.vn/') ? section.source_url : null;
  return <div className={`school-data-status school-data-status--${status}`} role="status">
    <div>{title && <span>{title}</span>}<strong>{section?.source_type === 'imported_pdf' ? 'Nhập PDF đã xác nhận' : section?.source_type === 'coursework' ? 'Đã đối chiếu học phần' : labels[status] || labels.not_synced}</strong>
      {stamp && !Number.isNaN(stamp.getTime()) && <span>{new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Bangkok' }).format(stamp)}</span>}</div>
    <p>{section?.message || (status === 'not_synced' ? 'Hãy kết nối lại tài khoản trường để lấy mục này.' : '')}</p>
    <div className="school-data-status__actions">{source && <a href={source} target="_blank" rel="noreferrer">Nguồn CTT <ExternalLink size={12} /></a>}
      {onSync && <button type="button" onClick={onSync}><RefreshCw size={13} />Đồng bộ từ trường</button>}</div>
  </div>;
}

export function DataTable({ columns, rows, empty = 'Chưa có dữ liệu đã đồng bộ để hiển thị.' }) {
  if (!rows?.length) return <p className="school-data-empty">{empty}</p>;
  return <div className="school-data-table-wrap"><table className="school-data-table"><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={i}>{columns.map(([key, , renderer]) => <td key={key}>{renderer ? renderer(row[key], row) : display(row[key])}</td>)}</tr>)}</tbody></table></div>;
}

function RawTable({ table }) {
  const [limit, setLimit] = useState(100);
  return <div className="school-data-raw"><div className="school-data-table-wrap"><table className="school-data-table"><thead><tr>{table.headers.map((label, i) => <th key={i}>{label}</th>)}</tr></thead>
    <tbody>{table.rows.slice(0, limit).map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{display(cell)}</td>)}</tr>)}</tbody></table></div>
    {table.rows.length > limit && <button className="school-data-secondary" type="button" onClick={() => setLimit((n) => n + 100)}>Xem thêm ({limit}/{table.rows.length} dòng)</button>}</div>;
}

export function RawSchoolTables({ section, collapsed = false }) {
  if (!section?.tables?.length) return null;
  return <details className="school-data-source" open={!collapsed && !section.records?.length && !section.charges?.length && !section.payments?.length}><summary>Đối chiếu bảng gốc CTT ({section.tables.length})</summary>
    {section.tables.map((table, i) => <RawTable key={`${table.id}-${i}`} table={table} />)}</details>;
}

export function SchoolDataHeader({ title, subtitle, onSync }) {
  return <header className="school-data-header"><div><h2>{title}</h2><p>{subtitle}</p></div>
    {onSync && <button type="button" className="school-data-secondary" onClick={onSync}><RefreshCw size={15} />Đồng bộ CTT</button>}</header>;
}
