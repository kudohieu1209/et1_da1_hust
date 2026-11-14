import React, { useState, useEffect } from 'react';
import { 
  Star, 
  Plus, 
  Search
} from 'lucide-react';
import { apiFetch, apiUrl } from '../api';

export default function CourseReviewsTab({ language = 'vi' }) {
  const [reviews, setReviews] = useState([]);
  const [courseFilter, setCourseFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // New review form
  const [newReview, setNewReview] = useState({
    course_code: 'ET3210',
    rating: 5,
    difficulty: 'Trung bình',
    attendance: 'Có điểm danh',
    comment: ''
  });

  const t = (vi, en) => (language === 'vi' ? vi : en);

  const fetchReviews = async (code) => {
    setLoading(true);
    try {
      const url = code 
        ? apiUrl(`/api/student/reviews?course_code=${encodeURIComponent(code.trim().toUpperCase())}`)
        : apiUrl('/api/student/reviews');
      const res = await apiFetch(url);
      if (res.ok) {
        const data = await res.json();
        setReviews(data);
      }
    } catch (err) {
      console.error('Error fetching reviews:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews('');
  }, []);

  const handleFilterSubmit = (e) => {
    e.preventDefault();
    fetchReviews(courseFilter);
  };

  const handleCreateReview = async (e) => {
    e.preventDefault();
    if (!newReview.comment.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch(
        apiUrl(`/api/student/reviews?course_code=${encodeURIComponent(newReview.course_code.trim().toUpperCase())}`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newReview)
        }
      );
      if (res.ok) {
        setIsFormOpen(false);
        setNewReview({ course_code: '', rating: 5, difficulty: 'Trung bình', attendance: 'Có điểm danh', comment: '' });
        fetchReviews(courseFilter);
      }
    } catch (err) {
      console.error('Error creating review:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '20px 24px 60px', maxWidth: 960, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(213, 19, 42, 0.08) 0%, rgba(245, 158, 11, 0.08) 100%)',
        borderRadius: 20,
        padding: '24px 28px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Star size={22} color="#f59e0b" fill="#f59e0b" />
            <h2 style={{ fontSize: '1.35rem', fontWeight: 650, margin: 0, color: 'var(--text-primary)' }}>
              {t('Đánh giá & Review Môn học HUST', 'Course Reviews & Community Insights')}
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: 540, lineHeight: 1.5 }}>
            {t(
              'Tổng hợp kinh nghiệm học tập, độ khó đề thi, tình hình điểm danh và lời khuyên ôn tập thực tế từ các thế hệ sinh viên Bách Khoa.',
              'Real reviews from HUST students covering difficulty, exam tips, attendance policies, and professor insights.'
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsFormOpen(!isFormOpen)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 18px',
            borderRadius: 12,
            background: 'var(--brand-accent)',
            border: 'none',
            color: '#fff',
            fontSize: '0.84rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <Plus size={16} /> {t('Viết đánh giá môn học', 'Write a Review')}
        </button>
      </div>

      {/* Review Submission Form Modal / Box */}
      {isFormOpen && (
        <form
          onSubmit={handleCreateReview}
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 18,
            padding: '20px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            boxShadow: '0 8px 30px rgba(0,0,0,0.1)'
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 650, color: 'var(--text-primary)' }}>
            {t('Chia sẻ kinh nghiệm môn học', 'Share Your Course Experience')}
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
            <div>
              <label style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Mã học phần *
              </label>
              <input
                type="text"
                required
                value={newReview.course_code}
                onChange={e => setNewReview({ ...newReview, course_code: e.target.value.toUpperCase() })}
                placeholder="Ví dụ: MI1111, ET3210..."
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Đánh giá sao (1 - 5)
              </label>
              <select
                value={newReview.rating}
                onChange={e => setNewReview({ ...newReview, rating: Number(e.target.value) })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem'
                }}
              >
                <option value={5}>⭐⭐⭐⭐⭐ (5 sao - Rất tốt / Rất đáng học)</option>
                <option value={4}>⭐⭐⭐⭐ (4 sao - Tốt)</option>
                <option value={3}>⭐⭐⭐ (3 sao - Bình thường)</option>
                <option value={2}>⭐⭐ (2 sao - Khá áp lực)</option>
                <option value={1}>⭐ (1 sao - Rất gắt / Khó qua)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Độ khó môn học
              </label>
              <select
                value={newReview.difficulty}
                onChange={e => setNewReview({ ...newReview, difficulty: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem'
                }}
              >
                <option value="Dễ">Dễ thở</option>
                <option value="Trung bình">Trung bình</option>
                <option value="Khó">Khó</option>
                <option value="Rất khó">Rất khó (Cần cày nhiều)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Điểm danh
              </label>
              <select
                value={newReview.attendance}
                onChange={e => setNewReview({ ...newReview, attendance: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem'
                }}
              >
                <option value="Có điểm danh">Có điểm danh đều</option>
                <option value="Thỉnh thoảng">Thỉnh thoảng điểm danh</option>
                <option value="Không điểm danh">Không điểm danh</option>
              </select>
            </div>
          </div>

          <div>
            <label style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Nhận xét, kinh nghiệm học & lời khuyên ôn thi *
            </label>
            <textarea
              required
              rows={3}
              value={newReview.comment}
              onChange={e => setNewReview({ ...newReview, comment: e.target.value })}
              placeholder="Chia sẻ cách tính điểm giữa kỳ/cuối kỳ, đề thi hay vào dạng nào, tài liệu nào nên ôn..."
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
                resize: 'vertical'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button
              type="button"
              onClick={() => setIsFormOpen(false)}
              style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: '8px 20px',
                borderRadius: 8,
                border: 'none',
                background: 'var(--brand-accent)',
                color: '#fff',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {submitting ? 'Đang gửi...' : 'Đăng đánh giá'}
            </button>
          </div>
        </form>
      )}

      {/* Filter bar */}
      <form onSubmit={handleFilterSubmit} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'var(--bg-surface)',
          padding: '8px 14px',
          borderRadius: 12,
          border: '1px solid var(--border-subtle)',
          flex: '1 1 260px'
        }}>
          <Search size={15} color="var(--text-muted)" />
          <input
            type="text"
            value={courseFilter}
            onChange={e => setCourseFilter(e.target.value)}
            placeholder="Lọc theo mã môn (MI1111, ET3210, IT1110...)"
            style={{
              border: 'none',
              background: 'transparent',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              width: '100%'
            }}
          />
        </div>
        <button
          type="submit"
          style={{
            padding: '8px 16px',
            borderRadius: 12,
            background: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.82rem',
            cursor: 'pointer'
          }}
        >
          Lọc
        </button>
        {courseFilter && (
          <button
            type="button"
            onClick={() => { setCourseFilter(''); fetchReviews(''); }}
            style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem' }}
          >
            Xóa lọc
          </button>
        )}
      </form>

      {/* Reviews List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
          {t('Đang tải danh sách đánh giá...', 'Loading reviews...')}
        </div>
      ) : reviews.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
          {t('Chưa có đánh giá nào cho môn học này. Hãy là người đầu tiên chia sẻ!', 'No reviews yet for this course.')}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {reviews.map(rev => (
            <div
              key={rev.id}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 16,
                padding: '18px 20px',
                display: 'flex',
                flexDirection: 'column',
                gap: 10
              }}
            >
              {/* Header */}
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontWeight: 700, fontSize: '0.98rem', color: 'var(--brand-accent)' }}>
                    {rev.course_code}
                  </span>
                  {rev.course_name && (
                    <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      — {rev.course_name}
                    </span>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 2, marginLeft: 6 }}>
                    {[1, 2, 3, 4, 5].map(star => (
                      <Star
                        key={star}
                        size={14}
                        color="#f59e0b"
                        fill={star <= rev.rating ? '#f59e0b' : 'transparent'}
                      />
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: 6,
                    background: rev.difficulty === 'Rất khó' ? 'rgba(239, 68, 68, 0.12)' : rev.difficulty === 'Khó' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)',
                    color: rev.difficulty === 'Rất khó' ? '#ef4444' : rev.difficulty === 'Khó' ? '#f59e0b' : '#10b981',
                    fontWeight: 600
                  }}>
                    {rev.difficulty}
                  </span>
                  <span style={{
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: 6,
                    background: 'var(--bg-card)',
                    color: 'var(--text-secondary)'
                  }}>
                    {rev.attendance}
                  </span>
                </div>
              </div>

              {/* Comment text */}
              <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {rev.comment}
              </p>

              {/* Footer */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 8, fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                <span>Người viết: <strong>{rev.author}</strong></span>
                <span>{new Date(rev.created_at).toLocaleDateString('vi-VN')}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
