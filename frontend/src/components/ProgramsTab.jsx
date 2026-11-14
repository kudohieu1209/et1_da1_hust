import React, { useEffect, useMemo, useState } from 'react';
import { apiFetch, apiUrl, readError } from '../api';
import { 
  Search, 
  X, 
  BookOpen, 
  GraduationCap, 
  Building, 
  School,
  ExternalLink, 
  FileText, 
  CircleCheck, 
  Info, 
  Layers, 
  Award, 
  ChevronDown, 
  ChevronUp, 
  ArrowUpRight, 
  Sparkles, 
  RotateCcw, 
  FileCheck, 
  Globe,
  FileSpreadsheet
} from 'lucide-react';
import './ProgramsTab.css';

function sourceLink(url) {
  return /^https?:\/\//i.test(url || '') ? url : null;
}

export default function ProgramsTab() {
  const [programs, setPrograms] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all'); // 'all' | 'supported'
  const [selected, setSelected] = useState('');
  const [mobileTab, setMobileTab] = useState('list'); // 'list' | 'detail'
  const [data, setData] = useState(null);
  const [version, setVersion] = useState('');
  const [courseQuery, setCourseQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [isNotesOpen, setIsNotesOpen] = useState(false);

  // Load programs directory
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    apiFetch(apiUrl('/api/programs'), { signal: controller.signal })
      .then(async res => {
        if (!res.ok) throw new Error(await readError(res, 'Không tải được danh mục chương trình.'));
        return res.json();
      })
      .then(result => {
        const list = result.programs || [];
        setPrograms(list);
        setSelected(current => current || list[0]?.admission_code || '');
      })
      .catch(err => { if (err.name !== 'AbortError') { setError(err.message); setLoading(false); } });
    return () => controller.abort();
  }, [retry]);

  // Load curriculum details for selected program
  useEffect(() => {
    if (!selected) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setData(null);
    setCourseQuery('');
    apiFetch(apiUrl(`/api/programs/${encodeURIComponent(selected)}/curricula`), { signal: controller.signal })
      .then(async res => {
        if (!res.ok) throw new Error(await readError(res, 'Không tải được dữ liệu chương trình.'));
        return res.json();
      })
      .then(result => {
        setData(result);
        setVersion(result.curricula?.[0]?.id || '');
      })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selected, retry]);

  // Filter program list
  const filtered = useMemo(() => {
    return programs.filter(p => {
      const matchSearch = `${p.admission_code} ${p.name} ${p.faculty || ''}`
        .toLocaleLowerCase('vi')
        .includes(query.trim().toLocaleLowerCase('vi'));
      
      if (!matchSearch) return false;
      if (selectedFilter === 'supported') {
        return Boolean(p.curriculum_supported || (p.supported_cohorts && p.supported_cohorts.length > 0));
      }
      return true;
    });
  }, [programs, query, selectedFilter]);

  const curriculum = data?.curricula?.find(c => c.id === version);

  const matchesCourse = c => {
    if (!courseQuery.trim()) return true;
    const q = courseQuery.trim().toLocaleLowerCase('vi');
    return (
      (c.code || '').toLocaleLowerCase('vi').includes(q) ||
      (c.name || '').toLocaleLowerCase('vi').includes(q)
    );
  };

  // Count total courses in current curriculum
  const totalCoursesInCurriculum = useMemo(() => {
    if (!curriculum?.groups) return 0;
    return curriculum.groups.reduce((acc, g) => acc + (g.courses?.length || 0), 0);
  }, [curriculum]);

  // Count filtered courses
  const matchingCoursesCount = useMemo(() => {
    if (!curriculum?.groups) return 0;
    return curriculum.groups.reduce((acc, g) => {
      return acc + (g.courses || []).filter(matchesCourse).length;
    }, 0);
  }, [curriculum, courseQuery]);

  return (
    <section className="program-browser">
      {/* Header Banner */}
      <header className="program-browser__header glass-panel">
        <div className="program-browser__header-content">
          <div className="program-browser__title-badge">
            <GraduationCap size={18} color="var(--brand-accent)" />
            <span>CTĐT Toàn Trường Bách Khoa</span>
          </div>
          <h2>Tra cứu chương trình đào tạo</h2>
          <p>
            Khung chương trình đào tạo chính quy, danh mục học phần chuẩn hóa, điều kiện tiên quyết và tài liệu trích xuất từ các Trường/Khoa.
          </p>
        </div>
        <div className="program-browser__header-stats">
          <div className="program-stat-capsule gemini-pill">
            <BookOpen size={15} color="var(--brand-accent)" />
            <span><strong>{programs.length || 68}</strong> Ngành đào tạo</span>
          </div>
          <div className="program-stat-capsule gemini-pill">
            <School size={15} color="var(--brand-gold)" />
            <span><strong>ĐH Bách Khoa</strong> Hà Nội</span>
          </div>
        </div>
      </header>

      {/* Mobile view segmented switch */}
      <div className="program-mobile-switch">
        <button
          type="button"
          className={`program-mobile-switch-btn gemini-pill ${mobileTab === 'list' ? 'is-active' : ''}`}
          onClick={() => setMobileTab('list')}
        >
          <BookOpen size={14} />
          <span>Danh sách ({filtered.length})</span>
        </button>
        <button
          type="button"
          className={`program-mobile-switch-btn gemini-pill ${mobileTab === 'detail' ? 'is-active' : ''}`}
          onClick={() => setMobileTab('detail')}
        >
          <GraduationCap size={14} />
          <span>Chi tiết: {selected || 'CTĐT'}</span>
        </button>
      </div>

      {/* Main 2-Column Layout */}
      <div className="program-browser__layout">
        {/* Left Column: Programs List */}
        <nav className={`program-browser__list glass-panel ${mobileTab === 'detail' ? 'mobile-hidden' : ''}`} aria-label="Danh sách chương trình">
          <div className="program-browser__search-header">
            <label htmlFor="program-search" className="program-browser__search-label">
              <span>Tìm kiếm ngành học</span>
              <span className="program-count-badge gemini-pill">{filtered.length} ngành</span>
            </label>
            
            {/* Search Pill Input */}
            <div className="program-search-bar gemini-pill">
              <Search size={15} color="var(--text-muted)" className="program-search-icon" />
              <input 
                id="program-search" 
                value={query} 
                onChange={e => setQuery(e.target.value)} 
                placeholder="Mã ngành (ET1, IT1...), tên ngành, khoa..." 
              />
              {query && (
                <button 
                  type="button" 
                  onClick={() => setQuery('')} 
                  className="program-search-clear"
                  title="Xóa tìm kiếm"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Quick Filter Segment Chips */}
            <div className="program-filter-tabs">
              <button
                type="button"
                className={`program-filter-tab gemini-pill ${selectedFilter === 'all' ? 'is-active' : ''}`}
                onClick={() => setSelectedFilter('all')}
              >
                Tất cả ({programs.length})
              </button>
              <button
                type="button"
                className={`program-filter-tab gemini-pill ${selectedFilter === 'supported' ? 'is-active' : ''}`}
                onClick={() => setSelectedFilter('supported')}
              >
                <Sparkles size={12} color={selectedFilter === 'supported' ? 'var(--brand-accent)' : 'currentColor'} />
                Có rà soát tiến độ
              </button>
            </div>
          </div>

          {/* Scrollable Results List */}
          <div className="program-browser__results">
            {filtered.map(p => {
              const isSelected = selected === p.admission_code;
              const hasAudit = Boolean(p.curriculum_supported || (p.supported_cohorts && p.supported_cohorts.length > 0));

              return (
                <button 
                  key={p.admission_code} 
                  type="button" 
                  aria-pressed={isSelected}
                  className={`program-card-item ${isSelected ? 'is-active' : ''}`}
                  onClick={() => {
                    setSelected(p.admission_code);
                    setMobileTab('detail');
                  }}
                >
                  <div className="program-card-item__top">
                    <span className="program-code-badge gemini-pill">
                      {p.admission_code}
                    </span>
                    {hasAudit && (
                      <span className="program-audit-pill gemini-pill" title="Hỗ trợ rà soát tiến độ tốt nghiệp tự động">
                        <Sparkles size={11} />
                        <span>Rà soát K67-K69</span>
                      </span>
                    )}
                  </div>
                  
                  <div className="program-card-item__name">
                    {p.name}
                  </div>
                  
                  <div className="program-card-item__faculty">
                    <Building size={12} className="faculty-icon" />
                    <span>{p.faculty || 'Đại học Bách Khoa Hà Nội'}</span>
                  </div>
                </button>
              );
            })}

            {!filtered.length && (
              <div className="program-empty-state">
                <Search size={28} color="var(--text-muted)" />
                <p>Không tìm thấy ngành khớp từ khóa "{query}".</p>
                <button 
                  type="button" 
                  className="btn-secondary gemini-pill"
                  onClick={() => { setQuery(''); setSelectedFilter('all'); }}
                >
                  Đặt lại bộ lọc
                </button>
              </div>
            )}
          </div>
        </nav>

        {/* Right Column: Program Detail */}
        <div className={`program-browser__detail glass-panel ${mobileTab === 'list' ? 'mobile-hidden' : ''}`} aria-live="polite">
          {error ? (
            <div className="program-error-state" role="alert">
              <Info size={28} color="var(--danger)" />
              <p>{error}</p>
              <button type="button" className="btn-primary gemini-pill" onClick={() => setRetry(v => v + 1)}>
                <RotateCcw size={15} />
                <span>Thử lại</span>
              </button>
            </div>
          ) : loading ? (
            <div className="program-loading-state">
              <div className="apple-siri-indicator">
                <span className="apple-siri-dot" />
                <span className="apple-siri-dot" />
                <span className="apple-siri-dot" />
              </div>
              <p>Đang tải cấu trúc chương trình đào tạo...</p>
            </div>
          ) : data && (
            <div className="program-detail-view">
              {/* Mobile Back Button */}
              <button 
                type="button" 
                className="program-mobile-back-btn gemini-pill"
                onClick={() => setMobileTab('list')}
              >
                ← Quay lại danh sách 68 ngành
              </button>

              {/* Program Hero Card */}
              <div className="program-hero-card">
                <div className="program-hero-card__tags">
                  <span className="program-hero-code gemini-pill">
                    {data.program.admission_code}
                  </span>
                  {data.program.language && (
                    <span className="program-hero-badge gemini-pill">
                      <Globe size={13} />
                      <span>{data.program.language}</span>
                    </span>
                  )}
                  {data.program.curriculum_supported && (
                    <span className="program-hero-badge badge-success gemini-pill">
                      <CircleCheck size={13} />
                      <span>Chuẩn hóa rà soát tốt nghiệp</span>
                    </span>
                  )}
                </div>

                <h1 className="program-hero-title">{data.program.name}</h1>
                
                <div className="program-hero-meta">
                  <div className="program-hero-meta__item">
                    <Building size={14} color="var(--text-muted)" />
                    <span>{data.program.faculty}</span>
                  </div>
                  {data.program.supported_cohorts?.length > 0 && (
                    <div className="program-hero-meta__item">
                      <Sparkles size={14} color="var(--brand-accent)" />
                      <span>Khóa áp dụng rà soát: <strong>{data.program.supported_cohorts.join(', ')}</strong></span>
                    </div>
                  )}
                </div>
              </div>

              {/* Curriculum Version Selector Bar */}
              <div className="curriculum-version-toolbar">
                <div className="curriculum-version-select-box">
                  <FileText size={16} color="var(--brand-accent)" className="select-icon" />
                  <div className="select-content">
                    <label htmlFor="curriculum-version" className="select-label">Phiên bản / Tài liệu CTĐT:</label>
                    <select 
                      id="curriculum-version" 
                      value={version} 
                      onChange={e => { setVersion(e.target.value); setCourseQuery(''); }}
                      className="curriculum-select-input"
                    >
                      {(data.curricula || []).map(c => (
                        <option key={c.id} value={c.id}>
                          {c.id} · {c.course_count} học phần · {c.applies_to_cohorts?.join(', ') || 'Áp dụng chung'}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Quick Action Links */}
                <div className="curriculum-actions">
                  {sourceLink(curriculum?.source_url) && (
                    <a 
                      href={curriculum.source_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn-secondary gemini-pill"
                      title="Xem tài liệu gốc từ cổng đào tạo"
                    >
                      <ExternalLink size={14} />
                      <span>Nguồn tài liệu CTT</span>
                    </a>
                  )}
                  {data.program.detail_url && (
                    <a 
                      href={data.program.detail_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn-secondary gemini-pill"
                      title="Xem thông tin tuyển sinh Bách Khoa"
                    >
                      <ArrowUpRight size={14} />
                      <span>Đề án tuyển sinh</span>
                    </a>
                  )}
                </div>
              </div>

              {curriculum ? (
                <>
                  {/* Bento Metrics Overview */}
                  <div className="curriculum-bento-grid">
                    <div className="curriculum-bento-card">
                      <div className="curriculum-bento-icon">
                        <Award size={20} color="var(--brand-accent)" />
                      </div>
                      <div className="curriculum-bento-info">
                        <span className="bento-label">Tổng tín chỉ nguồn ghi</span>
                        <strong className="bento-value">
                          {curriculum.total_credits ? `${curriculum.total_credits} TC` : 'Theo nhóm nguồn'}
                        </strong>
                      </div>
                    </div>

                    <div className="curriculum-bento-card">
                      <div className="curriculum-bento-icon">
                        <BookOpen size={20} color="var(--brand-gold)" />
                      </div>
                      <div className="curriculum-bento-info">
                        <span className="bento-label">Học phần đã trích xuất</span>
                        <strong className="bento-value">{totalCoursesInCurriculum} môn</strong>
                      </div>
                    </div>

                    <div className="curriculum-bento-card">
                      <div className="curriculum-bento-icon">
                        <Layers size={20} color="var(--success)" />
                      </div>
                      <div className="curriculum-bento-info">
                        <span className="bento-label">Khối kiến thức / Nhóm</span>
                        <strong className="bento-value">{curriculum.groups?.length || 0} nhóm</strong>
                      </div>
                    </div>
                  </div>

                  {/* Scope & Verification Notice Callout */}
                  <div className={`program-scope-card ${data.program.curriculum_supported ? 'is-supported' : 'is-reference'}`}>
                    <div className="scope-icon-wrapper">
                      {data.program.curriculum_supported ? (
                        <CircleCheck size={20} color="var(--success)" />
                      ) : (
                        <Info size={20} color="var(--brand-accent)" />
                      )}
                    </div>
                    <div className="scope-text">
                      <strong>Lưu ý phạm vi đối chiếu:</strong>
                      <span>
                        {curriculum.scope_note || 'Dữ liệu học phần dùng để tra cứu mã môn, khối lượng kiến thức và điều kiện tiên quyết.'}
                      </span>
                    </div>
                  </div>

                  {/* Collapsible Source Notes & Graduation Rules */}
                  {(curriculum.graduation_rule || (curriculum.notes && curriculum.notes.length > 0)) && (
                    <div className="program-notes-accordion">
                      <button 
                        type="button" 
                        className="program-notes-trigger"
                        onClick={() => setIsNotesOpen(prev => !prev)}
                      >
                        <div className="trigger-left">
                          <FileCheck size={16} color="var(--brand-accent)" />
                          <span>Quy tắc tốt nghiệp & Ghi chú đối chiếu nguồn ({curriculum.notes?.length || 1})</span>
                        </div>
                        {isNotesOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>

                      {isNotesOpen && (
                        <div className="program-notes-content">
                          {curriculum.graduation_rule && (
                            <div className="graduation-rule-block">
                              <strong>Quy tắc xét công nhận tốt nghiệp:</strong>
                              <p>{curriculum.graduation_rule}</p>
                            </div>
                          )}
                          {curriculum.notes?.length > 0 && (
                            <ul className="notes-list">
                              {curriculum.notes.map((note, i) => (
                                <li key={i}>{note}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* In-Document Course Search Bar */}
                  <div className="course-search-section">
                    <div className="course-search-header">
                      <div className="course-search-title">
                        <FileSpreadsheet size={18} color="var(--brand-accent)" />
                        <h3>Khung chương trình chi tiết theo nhóm môn</h3>
                      </div>
                      <span className="course-search-badge gemini-pill">
                        {courseQuery.trim() ? `Khớp ${matchingCoursesCount}/${totalCoursesInCurriculum} môn` : `Tổng cộng ${totalCoursesInCurriculum} học phần`}
                      </span>
                    </div>

                    <div className="course-search-input-wrapper gemini-pill">
                      <Search size={16} color="var(--text-muted)" />
                      <input 
                        id="course-search" 
                        value={courseQuery} 
                        onChange={e => setCourseQuery(e.target.value)} 
                        placeholder="Lọc nhanh học phần theo mã (SSH1111, MI1110...) hoặc tên môn học..." 
                      />
                      {courseQuery && (
                        <button 
                          type="button" 
                          onClick={() => setCourseQuery('')} 
                          className="course-search-clear"
                          title="Xóa tìm kiếm"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Course Groups & Styled Tables */}
                  <div className="curriculum-groups-container">
                    {curriculum.groups.map((group, i) => {
                      const courses = (group.courses || []).filter(matchesCourse);
                      if (courseQuery && !courses.length) return null;

                      return (
                        <section className="curriculum-group-card" key={i}>
                          <div className="curriculum-group-header">
                            <div className="group-header-left">
                              <span className="group-index-dot" />
                              <h4>{group.name}</h4>
                            </div>
                            <div className="group-header-badges">
                              {group.required_credits != null ? (
                                <span className="badge badge-indigo gemini-pill">
                                  Yêu cầu: {group.required_credits} TC
                                </span>
                              ) : (
                                <span className="badge badge-purple gemini-pill">
                                  Theo khung nhóm
                                </span>
                              )}
                              <span className="badge badge-hust gemini-pill">
                                {courses.length} môn
                              </span>
                            </div>
                          </div>

                          {courses.length ? (
                            <div className="curriculum-table-wrapper">
                              <table className="curriculum-table">
                                <thead>
                                  <tr>
                                    <th style={{ width: '130px' }}>Mã học phần</th>
                                    <th>Tên học phần</th>
                                    <th style={{ width: '80px', textAlign: 'center' }}>Số TC</th>
                                    <th style={{ width: '100px', textAlign: 'center' }}>Kỳ gợi ý</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {courses.map((c, j) => (
                                    <tr key={j}>
                                      <td>
                                        <span className="course-code-pill gemini-pill">
                                          {c.code || '—'}
                                        </span>
                                      </td>
                                      <td>
                                        <div className="course-name-cell">
                                          <span className="course-name-main">{c.name || 'Chưa có tên học phần'}</span>
                                        </div>
                                      </td>
                                      <td style={{ textAlign: 'center' }}>
                                        <span className="course-credits-pill gemini-pill">
                                          {c.credits != null ? `${c.credits} TC` : '—'}
                                        </span>
                                      </td>
                                      <td style={{ textAlign: 'center' }}>
                                        <span className="course-semester-pill gemini-pill">
                                          {c.suggested_semester ? `Kỳ ${c.suggested_semester}` : '—'}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="group-empty-text">Chưa có bảng học phần chi tiết trong phần nguồn này.</p>
                          )}
                        </section>
                      );
                    })}

                    {courseQuery && !curriculum.groups.some(g => (g.courses || []).some(matchesCourse)) && (
                      <div className="course-search-empty">
                        <Search size={28} color="var(--text-muted)" />
                        <p>Không tìm thấy học phần nào khớp với từ khóa "{courseQuery}".</p>
                        <button 
                          type="button" 
                          className="btn-secondary gemini-pill"
                          onClick={() => setCourseQuery('')}
                        >
                          Xóa tìm kiếm
                        </button>
                      </div>
                    )}

                    {!curriculum.groups.length && (
                      <div className="curriculum-empty-groups">
                        <Info size={24} color="var(--text-muted)" />
                        <p>Nguồn hiện chỉ có thông tin giới thiệu; chưa công bố bảng học phần để trích xuất.</p>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="curriculum-no-data">
                  <Info size={24} color="var(--text-muted)" />
                  <p>Chưa có tài liệu trích xuất cho ngành này.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
