import React from 'react';
import { display } from '../../schoolData';
import './services.css';

export default function ResponsiveTable({ columns, rows, empty = 'Chưa có dữ liệu đã đồng bộ để hiển thị.', cards = false }) {
  if (!rows?.length) return <p className="school-data-empty">{empty}</p>;
  return (
    <div className="services-table-wrap">
      <table className={`services-table${cards ? ' services-table--cards' : ''}`} role="table">
        <thead role="rowgroup"><tr role="row">{columns.map(([key, label]) => <th role="columnheader" scope="col" key={key}>{label}</th>)}</tr></thead>
        <tbody role="rowgroup">
          {rows.map((row, index) => (
            <tr role="row" key={index}>
              {columns.map(([key, label, render]) => (
                <td role="cell" data-label={label} key={key}>
                  <span className="services-cell-label" aria-hidden="true">{label}</span>
                  <span>{render ? render(row[key], row) : display(row[key])}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
