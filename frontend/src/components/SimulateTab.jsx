import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, ArrowDownRight, RefreshCw, Zap, CheckCircle2 } from 'lucide-react';

export default function SimulateTab() {
  const [selectedCourse, setSelectedCourse] = useState('ET2040');
  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(false);

  const sampleCoreCourses = [
    { code: 'ET2040', name: 'Cấu kiện điện tử (Kỳ 4)' },
    { code: 'ET2050', name: 'Lý thuyết mạch (Kỳ 4)' },
    { code: 'ET2060', name: 'Tín hiệu và hệ thống (Kỳ 4)' },
    { code: 'ET3210', name: 'Trường điện từ (Kỳ 4)' },
    { code: 'ET3220', name: 'Điện tử số (Kỳ 5)' },
    { code: 'ET3230', name: 'Điện tử tương tự I (Kỳ 5)' },
    { code: 'ET3300', name: 'Kỹ thuật vi xử lý (Kỳ 6)' },
    { code: 'ET3260', name: 'Kỹ thuật phần mềm ứng dụng (Kỳ 5)' },
    { code: 'MI1111', name: 'Giải tích I (Kỳ 1)' },
    { code: 'PH1111', name: 'Vật lý đại cương I (Kỳ 1)' }
  ];

  const handleSimulate = async (courseToTest) => {
    const code = courseToTest || selectedCourse;
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/courses/simulate-impact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ failed_course_code: code })
      });
      const data = await res.json();
      setSimulation(data);
    } catch (err) {
      console.error('Lỗi mô phỏng:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Info */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'rgba(244, 63, 94, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--danger)'
          }}>
            <ShieldAlert size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', color: 'var(--text-primary)' }}>
              Mô phỏng Rủi ro Dây chuyền khi Trượt Môn
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Đồ thị môn học Bách Khoa có tính kết nối cao. Hãy chọn 1 môn để kiểm tra nếu không đạt, bạn sẽ bị nghẽn những môn nào tiếp theo.
            </p>
          </div>
        </div>

        {/* Course Selector & Simulate Button */}
        <div style={{ display: 'flex', gap: '14px', marginTop: '20px', flexWrap: 'wrap' }}>
          <select
            value={selectedCourse}
            onChange={(e) => {
              setSelectedCourse(e.target.value);
              handleSimulate(e.target.value);
            }}
            style={{
              flex: 1,
              minWidth: '280px',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-primary)',
              fontSize: '0.95rem',
              outline: 'none'
            }}
          >
            {sampleCoreCourses.map(c => (
              <option key={c.code} value={c.code} style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                {c.code} - {c.name}
              </option>
            ))}
          </select>

          <button
            onClick={() => handleSimulate()}
            disabled={loading}
            className="btn-primary"
            style={{ padding: '12px 24px' }}
          >
            <Zap size={16} />
            <span>{loading ? 'Đang phân tích...' : 'Mô phỏng Tác động'}</span>
          </button>
        </div>
      </div>

      {/* Simulation Results */}
      {simulation && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Severity Banner */}
          <div className="glass-panel" style={{
            padding: '20px 24px',
            borderLeft: simulation.severity === 'HIGH' ? '6px solid var(--danger)' : '6px solid var(--warning)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <span className={simulation.severity === 'HIGH' ? "badge badge-danger" : "badge badge-warning"}>
                  Mức độ ảnh hưởng: {simulation.severity}
                </span>
                <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: '8px' }}>
                  Hậu quả khi trượt môn: {simulation.failed_course_code} - {simulation.failed_course_name}
                </h3>
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: simulation.severity === 'HIGH' ? 'var(--danger)' : 'var(--warning)' }}>
                {simulation.total_blocked} môn bị ảnh hưởng
              </div>
            </div>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', marginTop: '10px', lineHeight: '1.5' }}>
              {simulation.analysis}
            </p>
          </div>

          {/* Direct Blocked Courses */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h4 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color="var(--danger)" />
              Môn bị CHẶN TRỰC TIẾP không thể đăng ký ngay kỳ tiếp theo ({simulation.direct_blocked_courses.length})
            </h4>

            {simulation.direct_blocked_courses.length === 0 ? (
              <p style={{ color: 'var(--text-muted)' }}>Không có môn nào bị chặn trực tiếp.</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                {simulation.direct_blocked_courses.map(c => (
                  <div
                    key={c.code}
                    style={{
                      background: 'var(--danger-bg)',
                      border: '1px solid rgba(220, 38, 38, 0.25)',
                      borderRadius: 'var(--radius-md)',
                      padding: '14px 16px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <strong style={{ color: 'var(--danger)', fontSize: '1rem' }}>{c.code}</strong>
                      <span className="badge badge-danger" style={{ fontSize: '0.72rem' }}>
                        {c.relation === 'PREREQUISITE' ? 'Tiên quyết (!)' : 'Học trước'}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-primary)', fontWeight: '600', fontSize: '0.9rem', marginTop: '6px' }}>
                      {c.name}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      {c.credits} TC • Khung kỳ {c.semester || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Indirect Blocked Courses */}
          {simulation.indirect_blocked_courses.length > 0 && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h4 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ArrowDownRight size={18} color="var(--text-muted)" />
                Chuỗi môn học bị ảnh hưởng gián tiếp ở các kỳ sau ({simulation.indirect_blocked_courses.length})
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {simulation.indirect_blocked_courses.map(c => (
                  <span
                    key={c.code}
                    style={{
                      background: 'var(--bg-card-hover)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-md)',
                      padding: '8px 12px',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem'
                    }}
                  >
                    <strong>{c.code}</strong> - {c.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
