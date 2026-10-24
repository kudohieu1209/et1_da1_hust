import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { apiFetch, apiUrl } from '../../api';

async function getJson(path) {
  const response = await apiFetch(apiUrl(path));
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

/**
 * Tab "Giới thiệu": số liệu thật lấy từ backend (CTĐT đang dùng, kho tài liệu
 * RAG, mô hình ngôn ngữ, nơi lưu dữ liệu) thay cho các con số viết cứng.
 */
export default function AboutPanel({ language }) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [data, setData] = useState({ curriculum: null, rag: null, server: null });
  const [errors, setErrors] = useState({});
  const [reindex, setReindex] = useState({ state: 'idle', message: '' });

  const load = useCallback(async () => {
    const [curriculum, rag, server] = await Promise.allSettled([
      getJson('/api/courses/curriculum'),
      getJson('/api/rag/status'),
      getJson('/api/system'),
    ]);
    setData({
      curriculum: curriculum.status === 'fulfilled' ? curriculum.value : null,
      rag: rag.status === 'fulfilled' ? rag.value : null,
      server: server.status === 'fulfilled' ? server.value : null,
    });
    setErrors({
      curriculum: curriculum.status === 'rejected',
      rag: rag.status === 'rejected',
      server: server.status === 'rejected',
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleReindex = async () => {
    setReindex({ state: 'running', message: '' });
    try {
      const response = await apiFetch(apiUrl('/api/rag/sync?force=true'), { method: 'POST' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      setReindex({
        state: 'done',
        message: t(`Đã lập chỉ mục lại: ${result.total_chunks ?? '?'} đoạn.`, `Re-indexed: ${result.total_chunks ?? '?'} chunks.`),
      });
      load();
    } catch {
      setReindex({ state: 'error', message: t('Lập chỉ mục lại thất bại.', 'Re-indexing failed.') });
    }
  };

  const unavailable = <dd className="settings-status is-error">{t('Không tải được', 'Unavailable')}</dd>;
  const loading = <dd>…</dd>;
  const program = data.curriculum?.program;
  const rag = data.rag;

  return (
    <div>
      <section className="settings-section">
        <h3>HUST Course Advisor</h3>
        <p className="settings-hint">
          {t(
            'Trợ lý tư vấn học tập: kiểm tra điều kiện học phần và rà soát tiến độ bằng luật xác định theo CTĐT, tra cứu quy chế, học phí, học bổng bằng RAG có trích dẫn nguồn.',
            'Academic advisor: deterministic course-condition checks and degree audit from the curriculum, plus cited RAG answers on regulations, tuition and scholarships.',
          )}
        </p>
      </section>

      <section className="settings-section">
        <h3>{t('Dữ liệu đang dùng', 'Data in use')}</h3>
        <dl className="settings-readonly">
          <dt>{t('CTĐT', 'Program')}</dt>
          {errors.curriculum ? unavailable : program ? (
            <dd>
              {program.name} ({program.program_code} · {program.curriculum_version}) — {program.total_required_credits} TC
            </dd>
          ) : loading}

          <dt>{t('Kho tài liệu', 'Documents')}</dt>
          {errors.rag ? unavailable : rag ? (
            <dd>
              {t(
                `${rag.total_documents} văn bản đã kiểm chứng, ${rag.vector_store?.total_chunks ?? 0} đoạn`,
                `${rag.total_documents} verified documents, ${rag.vector_store?.total_chunks ?? 0} chunks`,
              )}
            </dd>
          ) : loading}

          <dt>{t('Mô hình', 'Model')}</dt>
          {errors.rag ? unavailable : rag ? (
            <dd>
              {rag.gemini?.configured
                ? `Gemini (${rag.gemini.model})`
                : t('Trích dẫn cục bộ (chưa cấu hình Gemini)', 'Local citations (Gemini not configured)')}
            </dd>
          ) : loading}

          <dt>{t('Lưu trữ', 'Storage')}</dt>
          {errors.server ? unavailable : data.server ? <dd>{data.server.storage ?? '—'}</dd> : loading}
        </dl>
        {rag?.vector_store?.indexed_sources?.length > 0 && (
          <p className="settings-hint" style={{ marginTop: 10 }}>
            {rag.vector_store.indexed_sources.join(' · ')}
          </p>
        )}
      </section>

      <details className="settings-advanced">
        <summary>{t('Nâng cao (dành cho quản trị)', 'Advanced (administrators)')}</summary>
        <p className="settings-hint">
          {t(
            'Chỉ cần khi thêm hoặc sửa văn bản trong data/documents. Việc này tính lại toàn bộ vector và có thể mất vài phút.',
            'Only needed after adding or editing files in data/documents. Recomputes every vector and may take a few minutes.',
          )}
        </p>
        <div className="settings-actions" style={{ justifyContent: 'flex-start', marginTop: 0 }}>
          <button type="button" className="settings-button" onClick={handleReindex} disabled={reindex.state === 'running'}>
            {reindex.state === 'running' ? (
              <Loader2 size={15} className="spin" aria-hidden="true" />
            ) : (
              <RefreshCw size={15} aria-hidden="true" />
            )}
            {t('Lập chỉ mục lại tài liệu', 'Re-index documents')}
          </button>
          {reindex.message && (
            <span className={`settings-status${reindex.state === 'error' ? ' is-error' : ''}`} role="status">
              {reindex.message}
            </span>
          )}
        </div>
      </details>
    </div>
  );
}
