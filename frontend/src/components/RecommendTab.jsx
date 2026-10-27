import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Wifi, Radio, HeartPulse, CheckCircle, Sparkles, Sliders } from 'lucide-react';
import { apiFetch, apiUrl, readError } from '../api';

const RECOMMEND_DEBOUNCE_MS = 300;

const TRACK_VISUALS = [
  { icon: Radio, color: 'var(--brand-accent)', bg: 'rgba(213, 19, 42, 0.08)' },
  { icon: Wifi, color: 'var(--gold-ink)', bg: 'rgba(246, 196, 0, 0.08)' },
  { icon: HeartPulse, color: 'var(--brand-accent)', bg: 'rgba(213, 19, 42, 0.08)' },
  { icon: Radio, color: 'var(--brand-accent)', bg: 'rgba(213, 19, 42, 0.08)' },
  { icon: Wifi, color: 'var(--gold-ink)', bg: 'rgba(246, 196, 0, 0.08)' },
  { icon: Cpu, color: 'var(--gold-ink)', bg: 'var(--gold-soft)' }
];

export default function RecommendTab() {
  const [selectedTrack, setSelectedTrack] = useState('MOD1');
  const [tracks, setTracks] = useState([]);
  const [maxCredits, setMaxCredits] = useState(20);
  const [isSummer, setIsSummer] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch(apiUrl('/api/student/tracks'))
      .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`)))
      .then(data => {
        const loaded = (data.tracks || []).map((track, index) => ({
          ...track,
          title: track.name,
          sub: `${track.required_credits} TC bắt buộc trong ${track.catalog_credits} TC danh mục`,
          ...TRACK_VISUALS[index % TRACK_VISUALS.length]
        }));
        setTracks(loaded);
        if (loaded.length) {
          setSelectedTrack(current => loaded.some(track => track.id === current) ? current : loaded[0].id);
        }
      })
      .catch(err => console.error('Lỗi tải danh sách mô-đun:', err));
  }, []);

  const fetchRecommendation = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const res = await apiFetch(apiUrl('/api/student/recommend'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_track: selectedTrack,
          max_credits: maxCredits,
          is_summer_term: isSummer
        }),
        signal
      });
      if (!res.ok) {
        setRecommendation(null);
        setError(await readError(res, 'Không tải được gợi ý môn học.'));
        return;
      }
      setRecommendation(await res.json());
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Lỗi gợi ý môn:', err);
      setRecommendation(null);
      setError('Không kết nối được máy chủ để lấy gợi ý môn học.');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [selectedTrack, maxCredits, isSummer]);

  useEffect(() => {
    const controller = new AbortController();
    // Chờ người dùng thả thanh trượt rồi mới gọi, và hủy yêu cầu cũ khi tham số đổi.
    const timer = setTimeout(() => fetchRecommendation(controller.signal), RECOMMEND_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [fetchRecommendation]);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Step 1: Choose Specialization Track */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', color: 'var(--text-primary)' }}>
              Bước 1: Chọn định hướng chuyên môn
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Chọn một trong các mô-đun của chương trình đào tạo đang được hỗ trợ; mỗi mô-đun yêu cầu tối thiểu 15 tín chỉ.
            </p>
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '14px'
        }}>
          {tracks.map(t => {
            const Icon = t.icon;
            const isSelected = selectedTrack === t.id;
            return (
              <div
                key={t.id}
                onClick={() => setSelectedTrack(t.id)}
                style={{
                  background: isSelected ? t.bg : 'var(--bg-card)',
                  border: isSelected ? '2px solid var(--hust-red)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '18px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? `0 6px 24px rgba(0, 0, 0, 0.1)` : 'var(--shadow-sm)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    background: isSelected ? 'var(--hust-red)' : t.bg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: isSelected ? '#fff' : t.color
                  }}>
                    <Icon size={22} />
                  </div>
                  {isSelected && <CheckCircle size={20} color={t.color} />}
                </div>

                <h3 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', marginTop: '14px' }}>
                  {t.title}
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {t.sub}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Step 2: Set Credit Limits */}
      <div className="glass-panel" style={{
        padding: '18px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <Sliders size={20} color="var(--brand-accent)" />
          <div>
            <span style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              Số tín chỉ tối đa muốn đăng ký: <strong style={{ color: 'var(--brand-accent)', fontSize: '1.15rem' }}>{maxCredits} TC</strong>
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>
              Quy chế HUST: Tối đa 24 TC (Kỳ chính) / 8 TC (Kỳ hè)
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <input
            type="range"
            min="12"
            max="24"
            step="1"
            value={maxCredits}
            onChange={(e) => setMaxCredits(parseInt(e.target.value))}
            style={{ width: '180px', cursor: 'pointer', accentColor: 'var(--hust-red)' }}
          />

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            <input
              type="checkbox"
              checked={isSummer}
              onChange={(e) => setIsSummer(e.target.checked)}
              style={{ accentColor: 'var(--hust-red)', width: '16px', height: '16px' }}
            />
            Đăng ký kỳ hè
          </label>
        </div>
      </div>

      {/* Step 3: Recommended Courses Output */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={20} color="var(--brand-accent)" />
              <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>
                Danh sách Môn học Tối ưu Được Đề xuất
              </h3>
            </div>
            {recommendation && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {recommendation.advice_note}
              </p>
            )}
          </div>

          {recommendation && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="badge badge-success" style={{ fontSize: '0.9rem', padding: '6px 14px' }}>
                Tổng: {recommendation.total_credits_suggested} / {recommendation.max_allowed_credits} TC
              </span>
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Đang tính toán ma trận môn học tối ưu...
          </div>
        ) : error ? (
          <div role="alert" style={{ padding: '30px', textAlign: 'center', color: 'var(--danger)' }}>
            {error}
          </div>
        ) : recommendation?.recommended_courses?.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {recommendation.recommended_courses.map((c, idx) => (
              <div
                key={c.code}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '16px 20px',
                  background: 'var(--bg-card-hover)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    background: 'rgba(213, 19, 42, 0.15)',
                    color: 'var(--brand-accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: '700',
                    fontSize: '0.9rem'
                  }}>
                    {idx + 1}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <strong style={{ color: 'var(--brand-accent)', fontSize: '1.05rem' }}>{c.code}</strong>
                      <span style={{ fontSize: '0.98rem', color: 'var(--text-primary)', fontWeight: '600' }}>{c.name}</span>
                      <span className={c.is_compulsory ? "badge badge-hust" : "badge badge-indigo"}>
                        {c.is_compulsory ? "Bắt buộc" : "Tự chọn"}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      {c.priority_reason} • <span style={{ color: 'var(--brand-accent)' }}>{c.prerequisite_summary}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <span style={{ fontSize: '1.1rem', fontWeight: '800', color: 'var(--success)' }}>
                    {c.credits} TC
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Không có môn học nào cần đề xuất hoặc bạn đã hoàn thành hết các môn!
          </div>
        )}
      </div>
    </div>
  );
}
