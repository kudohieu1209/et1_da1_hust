import React, { useState, useEffect } from 'react';
import { Search, Filter, CheckCircle2, Lock, Unlock, BookOpen, X, ArrowRight, Info, AlertCircle } from 'lucide-react';

export default function RoadmapTab({ studentProfile, onSelectCourse }) {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('ALL'); // ALL | PASSED | ELIGIBLE | BLOCKED
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [courseDetail, setCourseDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const passedCodes = new Set((studentProfile?.passed_courses || []).map(c => c.code));
  const learnedCodes = new Set([
    ...(studentProfile?.passed_courses || []).map(c => c.code),
    ...(studentProfile?.failed_courses || []).map(c => c.code)
  ]);

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/courses');
      const data = await res.json();
      setCourses(data.courses || []);
    } catch (err) {
      console.error('Lỗi nạp môn học:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCourse = async (course) => {
    setSelectedCourse(course);
    setLoadingDetail(true);
    try {
      const res = await fetch(`http://localhost:8000/api/courses/${course.code}`);
      const data = await res.json();
      setCourseDetail(data);
    } catch (err) {
      console.error('Lỗi nạp chi tiết môn:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Group courses by semester (Kỳ 1 -> Kỳ 8, và Kỳ Khác)
  const semesters = [1, 2, 3, 4, 5, 6, 7, 8];

  const getCourseStatus = (c) => {
    if (passedCodes.has(c.code)) return 'PASSED';
    const branches = c.condition_tree || [];
    if (branches.length === 0) return 'ELIGIBLE';
    const branchSatisfied = branch => branch.every(item => {
      if (item.type === 'PREREQUISITE') return passedCodes.has(item.code);
      return learnedCodes.has(item.code); // PRIOR/COREQUISITE: đã từng học
    });
    return branches.some(branchSatisfied) ? 'ELIGIBLE' : 'BLOCKED';
  };

  const conditionItemText = (item) => {
    const course = courses.find(c => c.code === item.code);
    const relation = item.type === 'PREREQUISITE'
      ? 'tiên quyết (phải qua môn)'
      : item.type === 'COREQUISITE'
        ? 'song hành'
        : 'học trước';
    return `${item.code}${course?.name ? ` - ${course.name}` : ''} (${relation})`;
  };

  const filteredCourses = courses.filter(c => {
    // Ignore physical education PE in main tree view unless searched
    if (c.code.startsWith('PE') && !searchQuery) return false;

    const status = getCourseStatus(c);
    if (filterStatus === 'PASSED' && status !== 'PASSED') return false;
    if (filterStatus === 'ELIGIBLE' && status !== 'ELIGIBLE') return false;
    if (filterStatus === 'BLOCKED' && status !== 'BLOCKED') return false;

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return c.code.toLowerCase().includes(q) || c.name.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Controls Bar: Search & Status Filters */}
      <div className="glass-panel" style={{
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        {/* Search */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'rgba(255, 255, 255, 0.05)',
          padding: '8px 14px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          minWidth: '280px'
        }}>
          <Search size={18} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Tìm theo mã hoặc tên môn (ET3290, Giải tích...)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              width: '100%'
            }}
          />
        </div>

        {/* Status Filter Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setFilterStatus('ALL')}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              border: filterStatus === 'ALL' ? '1px solid var(--indigo)' : '1px solid var(--border-subtle)',
              background: filterStatus === 'ALL' ? 'var(--indigo-glow)' : 'rgba(255, 255, 255, 0.04)',
              color: filterStatus === 'ALL' ? '#fff' : 'var(--text-secondary)',
              fontSize: '0.84rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Tất cả ({courses.length})
          </button>
          <button
            onClick={() => setFilterStatus('PASSED')}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              border: filterStatus === 'PASSED' ? '1px solid var(--success)' : '1px solid var(--border-subtle)',
              background: filterStatus === 'PASSED' ? 'var(--success-bg)' : 'rgba(255, 255, 255, 0.04)',
              color: filterStatus === 'PASSED' ? 'var(--success)' : 'var(--text-secondary)',
              fontSize: '0.84rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Đã qua ({courses.filter(c => passedCodes.has(c.code)).length})
          </button>
          <button
            onClick={() => setFilterStatus('ELIGIBLE')}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              border: filterStatus === 'ELIGIBLE' ? '1px solid var(--sky)' : '1px solid var(--border-subtle)',
              background: filterStatus === 'ELIGIBLE' ? 'rgba(14, 165, 233, 0.15)' : 'rgba(255, 255, 255, 0.04)',
              color: filterStatus === 'ELIGIBLE' ? '#38bdf8' : 'var(--text-secondary)',
              fontSize: '0.84rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Đang mở khóa
          </button>
          <button
            onClick={() => setFilterStatus('BLOCKED')}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              border: filterStatus === 'BLOCKED' ? '1px solid var(--danger)' : '1px solid var(--border-subtle)',
              background: filterStatus === 'BLOCKED' ? 'var(--danger-bg)' : 'rgba(255, 255, 255, 0.04)',
              color: filterStatus === 'BLOCKED' ? '#fda4af' : 'var(--text-secondary)',
              fontSize: '0.84rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Bị chặn điều kiện
          </button>
        </div>
      </div>

      {/* Roadmap Grid by Semester */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
          Đang tải cây lộ trình môn học...
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
          alignItems: 'start'
        }}>
          {semesters.map(sem => {
            const semCourses = filteredCourses.filter(c => c.suggested_semester === sem);
            if (semCourses.length === 0 && searchQuery) return null;

            return (
              <div
                key={sem}
                className="glass-panel"
                style={{
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                {/* Column Header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingBottom: '10px',
                  borderBottom: '1px solid var(--border-subtle)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '6px',
                      background: sem <= 4 ? 'rgba(99, 102, 241, 0.2)' : 'rgba(200, 16, 46, 0.2)',
                      color: sem <= 4 ? '#818cf8' : '#fda4af',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: '800',
                      fontSize: '0.82rem'
                    }}>
                      {sem}
                    </div>
                    <span style={{ fontWeight: '700', fontSize: '0.98rem', color: 'var(--text-primary)' }}>
                      Học kỳ {sem}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {semCourses.length} môn
                  </span>
                </div>

                {/* Course Cards inside Semester */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {semCourses.map(c => {
                    const status = getCourseStatus(c);
                    let borderColor = 'var(--border-subtle)';
                    let statusBadge = null;

                    if (status === 'PASSED') {
                      borderColor = 'rgba(16, 185, 129, 0.3)';
                      statusBadge = <span className="badge badge-success" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>Đã qua</span>;
                    } else if (status === 'BLOCKED') {
                      borderColor = 'rgba(244, 63, 94, 0.3)';
                      statusBadge = <span className="badge badge-danger" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>Bị chặn</span>;
                    } else {
                      borderColor = 'rgba(14, 165, 233, 0.3)';
                      statusBadge = <span className="badge badge-indigo" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>Mở khóa</span>;
                    }

                    return (
                      <div
                        key={c.code}
                        onClick={() => handleOpenCourse(c)}
                        style={{
                          background: 'var(--bg-card)',
                          border: `1px solid ${borderColor}`,
                          borderRadius: 'var(--radius-md)',
                          padding: '10px 12px',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.background = 'var(--bg-card-hover)';
                          e.currentTarget.style.transform = 'translateY(-1px)';
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.background = 'var(--bg-card)';
                          e.currentTarget.style.transform = 'translateY(0)';
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                          <span style={{ fontWeight: '700', fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                            {c.code}
                          </span>
                          {statusBadge}
                        </div>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.3' }}>
                          {c.name}
                        </div>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginTop: '6px',
                          fontSize: '0.72rem',
                          color: 'var(--text-muted)'
                        }}>
                          <span>{c.credits} TC • {c.is_compulsory ? 'Bắt buộc' : 'Tự chọn'}</span>
                          {c.raw_condition && (
                            <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>
                              ĐK: {c.raw_condition.length > 12 ? c.raw_condition.slice(0, 12) + '...' : c.raw_condition}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Course Detail Modal */}
      {selectedCourse && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{
            maxWidth: '620px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '28px',
            position: 'relative'
          }}>
            <button
              onClick={() => { setSelectedCourse(null); setCourseDetail(null); }}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: 'rgba(255, 255, 255, 0.08)',
                border: 'none',
                borderRadius: '50%',
                width: '34px',
                height: '34px',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={18} />
            </button>

            {/* Modal Content */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="badge badge-hust">{selectedCourse.code}</span>
              <span className={passedCodes.has(selectedCourse.code) ? "badge badge-success" : "badge badge-indigo"}>
                {passedCodes.has(selectedCourse.code) ? "Đã qua môn" : "Chưa học"}
              </span>
            </div>

            <h2 style={{ fontSize: '1.4rem', color: 'var(--text-primary)', margin: '10px 0 6px' }}>
              {selectedCourse.name}
            </h2>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {selectedCourse.modules?.length > 0
                ? <>Mô-đun thuộc CTĐT: {selectedCourse.modules.map(m => m.name).join(', ')}</>
                : <>Khối kiến thức: {selectedCourse.category || 'Cơ sở ngành'}</>}
              {' '}• Số tín chỉ: <strong>{selectedCourse.credits} TC</strong> • Kỳ gợi ý: Kỳ {selectedCourse.suggested_semester || 'N/A'}
            </p>

            {/* Condition Section */}
            <div style={{
              marginTop: '20px',
              padding: '16px',
              background: 'var(--bg-card-hover)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)'
            }}>
              <h4 style={{ fontSize: '0.92rem', color: 'var(--indigo)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Info size={16} />
                Điều kiện đăng ký chính thức trên CTT HUST:
              </h4>

              {selectedCourse.raw_condition ? (
                <div>
                  <div style={{
                    fontFamily: 'monospace',
                    background: 'rgba(0, 0, 0, 0.06)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    color: 'var(--success)',
                    fontWeight: '700',
                    fontSize: '0.9rem',
                    marginBottom: '10px'
                  }}>
                    {selectedCourse.raw_condition}
                  </div>

                  <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {(selectedCourse.condition_tree || []).length > 1 ? (
                      <>
                        <div>🔀 <strong>Phép HOẶC (/):</strong> chỉ cần đáp ứng một phương án; các môn trong cùng phương án phải đáp ứng đồng thời.</div>
                        {selectedCourse.condition_tree.map((branch, index) => (
                          <div key={index} style={{ paddingLeft: '12px' }}>
                            <strong>Phương án {index + 1}:</strong> {branch.map(conditionItemText).join(' và ')}
                          </div>
                        ))}
                      </>
                    ) : (selectedCourse.condition_tree?.[0] || []).length > 1 ? (
                      <div>
                        🔗 <strong>Phép VÀ (,):</strong> cần thỏa mãn đồng thời: {selectedCourse.condition_tree[0].map(conditionItemText).join(' và ')}
                      </div>
                    ) : selectedCourse.condition_tree?.[0]?.[0] ? (
                      <div>📖 <strong>Điều kiện:</strong> {conditionItemText(selectedCourse.condition_tree[0][0])}</div>
                    ) : null}
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                  ✅ Môn học này <strong>hoàn toàn không có ràng buộc điều kiện</strong>. Sinh viên được phép đăng ký tự do theo khung CTĐT!
                </p>
              )}
            </div>

            {/* Unlocks Next Courses */}
            {courseDetail?.unlocks_courses && courseDetail.unlocks_courses.length > 0 && (
              <div style={{ marginTop: '20px' }}>
                <h4 style={{ fontSize: '0.92rem', color: '#f8fafc', marginBottom: '10px' }}>
                  🔓 Môn này là điều kiện để mở khóa các môn tiếp theo:
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {courseDetail.unlocks_courses.map(u => (
                    <span key={u.code} className="badge badge-indigo" style={{ padding: '6px 12px' }}>
                      {u.code} - {u.name} ({u.type === 'PREREQUISITE' ? 'Tiên quyết' : 'Học trước'})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
