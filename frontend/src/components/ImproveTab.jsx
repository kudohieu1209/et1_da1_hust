import { useEffect, useState } from 'react';
import { AlertTriangle, TrendingUp } from 'lucide-react';
import { apiFetch, apiUrl } from '../api';
import CourseRow from './improve/CourseRow';
import CpaSummary from './improve/CpaSummary';
import GoalPlanner from './improve/GoalPlanner';
import { simulate } from './improve/planner';
import './improve/improve.css';

const ENGLISH_RANKS = {
  'Xuất sắc': 'Outstanding',
  'Giỏi': 'Excellent',
  'Khá': 'Good',
  'Trung bình': 'Average',
  'Yếu': 'Weak',
  'Kém': 'Poor',
};

export default function ImproveTab({ language = 'vi', syncVersion, transcript, onOpenImport }) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('loading');
  const [retry, setRetry] = useState(0);
  const [targets, setTargets] = useState({});
  const [filter, setFilter] = useState('all');
  const [goal, setGoal] = useState({ cpa: '', grade: 'B+' });
  const t = (vi, en) => language === 'vi' ? vi : en;
  const rankLabel = rank => t(rank.rank, ENGLISH_RANKS[rank.rank] ?? rank.rank);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    async function load() {
      try {
        const response = await apiFetch(apiUrl('/api/student/improve-courses'));
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (cancelled) return;

        setData(result);
        setTargets(previous => Object.fromEntries(
          result.improve_candidates
            .filter(course => course.projections[previous[course.code]])
            .map(course => [course.code, previous[course.code]]),
        ));
        setStatus('ready');
      } catch {
        if (!cancelled) setStatus('error');
      }
    }
    load();
    return () => { cancelled = true; };
  }, [syncVersion, transcript, retry]);

  const title = t('Cải thiện điểm CPA', 'Improve your CPA');
  if (status !== 'ready') {
    return (
      <section className="improve-page">
        <h2>{title}</h2>
        {status === 'loading' ? (
          <p className="improve-state" role="status">{t('Đang phân tích bảng điểm…', 'Analyzing transcript…')}</p>
        ) : (
          <div className="improve-state improve-panel">
            <p role="alert">{t('Không tải được dữ liệu cải thiện điểm.', 'Could not load CPA improvement data.')}</p>
            <button type="button" className="improve-button" onClick={() => setRetry(value => value + 1)}>
              {t('Thử lại', 'Retry')}
            </button>
          </div>
        )}
      </section>
    );
  }

  const { current_cpa: baseCpa, cpa_credits: cpaCredits, improve_candidates: candidates,
    classification_ladder: ladder, honors_rule: honors } = data;
  const simulation = simulate(baseCpa, cpaCredits, candidates, targets);
  const honorsRank = ladder.find(rank => rank.rank === 'Giỏi');
  const showHonorsWarning = honors.exceeds && honorsRank
    && Math.max(baseCpa, simulation.cpa) >= honorsRank.min_cpa;
  const groups = [
    { id: 'retake', label: t('Bắt buộc học lại', 'Required retakes'), chip: t('Bắt buộc học lại', 'Required retakes') },
    { id: 'improve_low', label: t('Điểm thấp', 'Low grades'), chip: 'D–D+' },
    { id: 'improve', label: t('Có thể cải thiện', 'Eligible for improvement'), chip: t('C trở lên', 'C or higher') },
  ].map(group => ({ ...group, courses: candidates.filter(course => course.category === group.id) }));
  const filters = [{ id: 'all', chip: t('Tất cả', 'All'), courses: candidates }, ...groups];
  const visibleGroups = groups.filter(group => (filter === 'all' || filter === group.id) && group.courses.length);

  function updateTarget(code, grade) {
    setTargets(previous => {
      const next = { ...previous };
      if (grade) next[code] = grade;
      else delete next[code];
      return next;
    });
  }

  return (
    <section className="improve-page">
      <header className="improve-heading">
        <h2><TrendingUp size={22} aria-hidden="true" /> {title}</h2>
        <p>{t(
          'Điểm F phải học lại. Bạn có thể học lại học phần đã đạt để cải thiện CPA. Điểm cao nhất được công nhận.',
          'Courses with an F require a retake. You can retake passed courses to raise your CPA. The highest grade counts.',
        )}</p>
      </header>
      {!data.has_transcript ? (
        <div className="improve-state improve-panel">
          <p>{t('Nhập bảng điểm để xem các học phần có thể học lại và mô phỏng CPA.', 'Import a transcript to see eligible courses and simulate your CPA.')}</p>
          <button className="improve-button improve-primary" type="button" onClick={onOpenImport}>
            {t('Nhập bảng điểm', 'Import transcript')}
          </button>
        </div>
      ) : (
        <>
          <CpaSummary
            baseCpa={baseCpa}
            simulation={simulation}
            ladder={ladder}
            rankLabel={rankLabel}
            onReset={() => setTargets({})}
            t={t}
          />
          {showHonorsWarning && (
            <aside className="improve-honors">
              <AlertTriangle size={20} aria-hidden="true" />
              <div>
                <h3>{t('Hạng tốt nghiệp có thể giảm một mức', 'Graduation honors may be reduced one level')}</h3>
                <p>{t(
                  `${honors.retake_credits} tín chỉ phải học lại vượt ngưỡng 5% (${honors.threshold_credits} tín chỉ). Theo Điều 15.2a, hạng tốt nghiệp từ Giỏi trở lên giảm một mức. Tín chỉ học cải thiện điểm không tính vào ngưỡng này.`,
                  `${honors.retake_credits} required retake credits exceed the 5% threshold (${honors.threshold_credits} credits). Under Article 15.2a, Excellent or higher graduation honors are reduced by one level. Optional grade improvement credits are excluded.`,
                )}</p>
                {honors.basis_source === 'transcript' && (
                  <p>{t('Ngưỡng đang tạm tính theo tín chỉ trong bảng điểm.', 'The threshold is provisionally based on transcript credits.')}</p>
                )}
              </div>
            </aside>
          )}
          {candidates.length ? (
            <>
              <GoalPlanner
                baseCpa={baseCpa}
                cpaCredits={cpaCredits}
                candidates={candidates}
                ladder={ladder}
                rankLabel={rankLabel}
                goal={goal}
                onGoalChange={setGoal}
                onApply={courses => setTargets(Object.fromEntries(courses.map(({ code, grade }) => [code, grade])))}
                t={t}
              />
              <div className="improve-controls" role="group" aria-label={t('Lọc học phần', 'Filter courses')}>
                {filters.map(item => (
                  <button
                    className="improve-button improve-filter"
                    key={item.id}
                    type="button"
                    aria-pressed={filter === item.id}
                    onClick={() => setFilter(item.id)}
                  >{item.chip} <span className="improve-count">{item.courses.length}</span></button>
                ))}
              </div>
              {visibleGroups.map(group => (
                <section key={group.id} aria-labelledby={`improve-group-${group.id}`}>
                  <h3 className="improve-group-title" id={`improve-group-${group.id}`}>
                    {group.label} <span className="improve-count">{group.courses.length}</span>
                  </h3>
                  <ul className="improve-course-list">
                    {group.courses.map(course => (
                      <CourseRow
                        key={course.code}
                        course={course}
                        categoryLabel={group.label}
                        target={targets[course.code]}
                        onTargetChange={updateTarget}
                        t={t}
                      />
                    ))}
                  </ul>
                </section>
              ))}
              {!visibleGroups.length && <p className="improve-state">{t('Nhóm này chưa có học phần.', 'There are no courses in this group.')}</p>}
            </>
          ) : (
            <p className="improve-state improve-panel">{cpaCredits
              ? t('Tất cả học phần đã đạt A', 'All courses have reached grade A')
              : t('Bảng điểm chưa có học phần tính CPA.', 'The transcript has no courses that count toward CPA.')}
            </p>
          )}
        </>
      )}
    </section>
  );
}
