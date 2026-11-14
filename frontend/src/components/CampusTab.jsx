import React, { useState, useEffect } from 'react';
import { 
  Search, 
  ExternalLink, 
  Navigation, 
  Compass
} from 'lucide-react';
import { apiFetch, apiUrl } from '../api';

const CATEGORY_NAMES = {
  all: 'Tất cả địa điểm',
  giang_duong: 'Giảng đường & Tòa nhà',
  tien_ich: 'Tiện ích & Dịch vụ'
};

export default function CampusTab({ language = 'vi', initialSearch = '' }) {
  const [locations, setLocations] = useState([]);
  const [search, setSearch] = useState(initialSearch);
  const [category, setCategory] = useState('all');
  const [loading, setLoading] = useState(true);

  const t = (vi, en) => (language === 'vi' ? vi : en);

  useEffect(() => {
    let cancelled = false;
    async function loadLocations() {
      setLoading(true);
      try {
        const res = await apiFetch(apiUrl('/api/student/campus-locations'));
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setLocations(data.locations || []);
        }
      } catch (err) {
        console.error('Lỗi tải bản đồ:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadLocations();
    return () => { cancelled = true; };
  }, []);

  const filteredLocations = locations.filter(loc => {
    const matchCat = category === 'all' || loc.category === category;
    if (!matchCat) return false;
    if (!search.trim()) return true;

    const q = search.toLowerCase().trim();
    const name = (loc.name || '').toLowerCase();
    const code = (loc.code || '').toLowerCase();
    return name.includes(q) || code.includes(q);
  });

  return (
    <div style={{ padding: '20px 24px 60px', maxWidth: 960, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(213, 19, 42, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
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
            <Compass size={22} color="var(--brand-accent)" />
            <h2 style={{ fontSize: '1.35rem', fontWeight: 650, margin: 0, color: 'var(--text-primary)' }}>
              {t('Bản đồ & Định vị Giảng đường Bách Khoa', 'HUST Campus Map & Classroom Finder')}
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: 540, lineHeight: 1.5 }}>
            {t(
              'Tra cứu vị trí chính xác của hơn 60 tòa nhà, giảng đường D3, D5, C1, B1, Thư viện Tạ Quang Bửu, cổng trường và tiện ích sinh viên HUST kèm dẫn đường Google Maps.',
              'Search exact coordinates for 60+ buildings, lecture halls, TQB library, gates, and campus utilities with direct Google Maps navigation.'
            )}
          </p>
        </div>

        <a
          href="https://www.google.com/maps/search/Đại+học+Bách+khoa+Hà+Nội"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 18px',
            borderRadius: 12,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--brand-accent)',
            textDecoration: 'none',
            fontSize: '0.82rem',
            fontWeight: 600
          }}
        >
          <Navigation size={15} /> {t('Mở Google Maps toàn trường', 'Open Google Maps')}
        </a>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'var(--bg-surface)',
          padding: '8px 16px',
          borderRadius: 12,
          border: '1px solid var(--border-subtle)',
          flex: '1 1 300px'
        }}>
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('Tìm kiếm toà nhà, giảng đường (D3, D5, C1, Thư viện...)...', 'Search building, room (D3, D5, C1, Library...)...')}
            style={{
              border: 'none',
              background: 'transparent',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.86rem',
              width: '100%'
            }}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Categories */}
        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'giang_duong', 'tien_ich'].map(cat => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategory(cat)}
              style={{
                padding: '8px 14px',
                borderRadius: 10,
                border: category === cat ? '1px solid var(--brand-accent)' : '1px solid var(--border-subtle)',
                background: category === cat ? 'rgba(213, 19, 42, 0.1)' : 'var(--bg-surface)',
                color: category === cat ? 'var(--brand-accent)' : 'var(--text-secondary)',
                fontSize: '0.78rem',
                fontWeight: category === cat ? 600 : 450,
                cursor: 'pointer'
              }}
            >
              {CATEGORY_NAMES[cat]}
            </button>
          ))}
        </div>
      </div>

      {/* Results Count */}
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        {t(`Hiển thị ${filteredLocations.length} địa điểm`, `Showing ${filteredLocations.length} locations`)}
      </div>

      {/* Grid of Locations */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
          {t('Đang tải dữ liệu bản đồ...', 'Loading campus map...')}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
          {filteredLocations.map((loc, idx) => {
            const isGiangDuong = loc.category === 'giang_duong';
            return (
              <div
                key={loc.code || loc.name || idx}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 14,
                  padding: '16px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: 12,
                  transition: 'transform 0.15s ease, border-color 0.15s ease'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ fontWeight: 650, fontSize: '0.94rem', color: 'var(--text-primary)' }}>
                      {loc.name}
                    </div>
                    {loc.code && (
                      <span style={{
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: 6,
                        background: isGiangDuong ? 'rgba(59, 130, 246, 0.12)' : 'rgba(16, 185, 129, 0.12)',
                        color: isGiangDuong ? '#3b82f6' : '#10b981'
                      }}>
                        {loc.code}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    {isGiangDuong ? 'Khu giảng đường / Tòa nhà' : 'Tiện ích / Dịch vụ sinh viên'}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 10 }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {loc.center?.lat?.toFixed(4)}, {loc.center?.lng?.toFixed(4)}
                  </span>
                  <a
                    href={loc.google_maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      color: 'var(--brand-accent)',
                      textDecoration: 'none'
                    }}
                  >
                    <Navigation size={12} /> {t('Chỉ đường', 'Directions')} <ExternalLink size={10} />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
