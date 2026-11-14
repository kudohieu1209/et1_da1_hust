import { useSchoolServices, display, money, certificateLabel } from '../schoolData';
import React, { useState } from 'react';
import { SchoolDataHeader, SchoolSectionState, RawSchoolTables, DataTable } from './SchoolDataPanel';

export default function StudentServicesTab({ syncVersion, onOpenImport }) {
  const { sections, loading, error } = useSchoolServices(syncVersion);
  const [tab, setTab] = useState('english');
  const [query, setQuery] = useState('');
  const selected = sections[tab];
  const records = selected?.records || [];
  const certificates = sections.certificates?.requirements || {};
  const coursework = sections.certificates?.coursework || {};
  const classmates = records.filter((row) => !query || [row.student_id, row.student_name, row.class_name].some((value) => String(value || '').toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi'))));
  const debts = (sections.tuition?.records || []).map((row) => row.debt);
  const totalDebt = debts.length && debts.every((n) => typeof n === 'number') ? debts.reduce((a, b) => a + b, 0) : null;
  return <div className="school-data-page">
    <SchoolDataHeader title="Thông tin sinh viên từ CTT" subtitle="Điểm tiếng Anh, học phí, danh sách lớp và trạng thái học vụ của tài khoản đang đăng nhập." onSync={onOpenImport} />
    <nav className="school-data-tabs" aria-label="Thông tin sinh viên">
      {[['english', 'Tiếng Anh'], ['tuition', 'Học phí'], ['classmates', 'Bạn cùng lớp'], ['certificates', 'Học vụ & Chứng chỉ']].map(([key, label]) =>
        <button type="button" key={key} className={tab === key ? 'is-active' : ''} aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}
    </nav>
    {error && <p className="school-data-error" role="alert">{error}</p>}
    {loading ? <p className="school-data-empty" role="status">Đang tải dữ liệu đã đồng bộ…</p> : <>
      <SchoolSectionState section={selected} onSync={onOpenImport} title={{ english: 'Tiếng Anh', tuition: 'Học phí', classmates: 'Danh sách lớp', certificates: 'GDTC / GDQP & chuẩn tiếng Anh' }[tab]} />
      {tab === 'english' && <>
        <div className="school-data-metric"><span>Chuẩn đầu ra tiếng Anh trên hồ sơ CTT</span><strong>{certificateLabel(certificates['240'])}</strong><span>Điểm thi và trạng thái chuẩn đầu ra được hiển thị riêng theo dữ liệu trường.</span></div>
        <DataTable rows={records} columns={[[ 'test_date', 'Ngày thi' ], ['certificate_type', 'Loại / kỳ thi'], ['listening', 'Điểm nghe'], ['reading', 'Điểm đọc'], ['writing', 'Điểm viết'], ['speaking', 'Điểm nói'], ['score', 'Tổng điểm']]} />
      </>}
      {tab === 'tuition' && <>
        {totalDebt != null && <div className="school-data-metric"><span>Tổng khoản còn nợ trong các kỳ đã đọc được</span><strong>{money(totalDebt)}</strong></div>}
        {!!records.length && <DataTable rows={records} columns={[[ 'semester', 'Học kỳ' ], ['tuition_fee', 'Phải nộp', money], ['paid', 'Đã nộp', money], ['debt', 'Còn nợ', money], ['deadline', 'Hạn nộp'], ['status', 'Trạng thái']]} />}
        {!!selected?.charges?.length && <section className="school-data-card"><h3>Học phí theo học phần</h3><DataTable rows={selected.charges} columns={[
          ['course_code', 'Mã HP'], ['course_name', 'Học phần'], ['unit_fee', 'Số tiền / TC', money], ['fee_credits', 'TC học phí'], ['coefficient', 'Hệ số'], ['amount', 'Tổng tiền', money], ['registration_status', 'Trạng thái đăng ký'], ['registration_type', 'Loại đăng ký'], ['notes', 'Ghi chú'],
        ]} /></section>}
        {!!selected?.payments?.length && <section className="school-data-card"><h3>Các khoản thu theo CTT</h3><DataTable rows={selected.payments} columns={[
          ['label', 'Loại tiền'], ['amount', 'Số tiền', money], ['coefficient', 'Hệ số đóng'], ['actual_amount', 'Thực đóng', money], ['updated_at', 'Ngày cập nhật'], ['notes', 'Ghi chú'],
        ]} /><p>Giữ nguyên tên khoản thu của CTT. Các khoản này chưa đủ để xác định số tiền còn nợ.</p></section>}
        {!records.length && !selected?.charges?.length && !selected?.payments?.length && !selected?.tables?.length && <p className="school-data-empty">Chưa có bảng học phí từ CTT để hiển thị.</p>}
      </>}
      {tab === 'classmates' && <>
        <input className="school-data-search" aria-label="Tìm bạn cùng lớp trong dữ liệu đã đồng bộ" placeholder="Tìm MSSV hoặc họ tên trong danh sách đã đồng bộ" value={query} onChange={(e) => setQuery(e.target.value)} />
        <DataTable rows={classmates} columns={[[ 'student_id', 'MSSV' ], ['student_name', 'Họ và tên'], ['class_name', 'Lớp'], ['email', 'Email']]} />
      </>}
      {tab === 'certificates' && <>
        <SchoolSectionState section={sections.warning} onSync={onOpenImport} title="Cảnh báo học tập" />
        <div className="school-data-metrics">
          <div className="school-data-metric"><span>Mức cảnh báo học tập do CTT trả về</span><strong>{sections.warning?.warning_level == null ? 'Chưa xác minh' : 'Mức ' + display(sections.warning.warning_level)}</strong></div>
          {[['220', 'GDTC'], ['230', 'GDQP'], ['240', 'Chuẩn tiếng Anh']].map(([key, title]) => {
            const progress = coursework[key];
            return <div className="school-data-metric" key={key}><span>{title}</span><strong>{progress ? ({ completed: 'Đã hoàn thành học phần', incomplete: 'Chưa đủ học phần', unverified: 'Chưa có đủ điểm' }[progress.status]) : certificateLabel(certificates[key])}</strong>
              {progress && <span>{progress.passed_count}/{progress.required_count} học phần đạt · Nhóm {progress.source_group_code}</span>}</div>;
          })}
        </div>
        {['220', '230'].filter((key) => coursework[key]).map((key) => <section className="school-data-card" key={key}>
          <h3>Căn cứ {key === '220' ? 'GDTC' : 'GDQP'}</h3>
          <DataTable rows={coursework[key].records || []} columns={[
            ['course_code', 'Mã HP'], ['course_name', 'Học phần'], ['letter_grade', 'Điểm chữ'], ['is_passed', 'Kết quả', (passed) => passed ? 'Đạt' : 'Chưa ghi nhận đạt'],
          ]} />
          <p>{coursework[key].note}</p>
        </section>)}
        {certificates['240'] !== 'completed' && <p className="school-data-empty">Chuẩn đầu ra tiếng Anh được đối chiếu riêng với thông tin trường; các môn tiếng Anh cơ sở không tự xác nhận chuẩn đầu ra.</p>}
      </>}
      <RawSchoolTables section={selected} collapsed={tab === 'classmates' || tab === 'tuition'} />
    </>}
  </div>;
}
