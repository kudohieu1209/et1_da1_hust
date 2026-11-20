import { ArrowRight, RotateCcw } from 'lucide-react';
import { nextRank, rankFor } from './planner';

export default function CpaSummary({ baseCpa, simulation, ladder, rankLabel, onReset, t }) {
  const current = rankFor(baseCpa, ladder);
  const simulated = rankFor(simulation.cpa, ladder);
  const next = nextRank(simulation.cpa, ladder);

  return (
    <section className="improve-summary" aria-label={t('Tổng quan CPA', 'CPA overview')}>
      <div className="improve-summary-scores" aria-live="polite" aria-atomic="true">
        {[
          { label: t('CPA hiện tại', 'Current CPA'), value: baseCpa, rank: current, id: 'current-cpa' },
          { label: t('CPA mô phỏng', 'Simulated CPA'), value: simulation.cpa, rank: simulated, id: 'simulated-cpa' },
        ].map(({ label, value, rank, id }, index) => (
          <div key={id} className="improve-score">
            {index === 1 && <ArrowRight className="improve-score-arrow" size={18} aria-hidden="true" />}
            <span className="improve-score-label">{label}</span>
            <div className="improve-score-value">
              <strong data-testid={id}>{value.toFixed(2)}</strong>
              {index === 1 && <span className="improve-gain">+{simulation.delta.toFixed(2)}</span>}
            </div>
            {rank && (
              <span className="improve-rank" style={{ '--improve-rank-color': rank.color }}>
                {rankLabel(rank)}
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="improve-summary-details">
        {next && (
          <div className="improve-progress">
            <span id="improve-progress-label">
              {t(
                `Còn thiếu ${(next.min_cpa - simulation.cpa).toFixed(2)} để lên ${rankLabel(next)}`,
                `${(next.min_cpa - simulation.cpa).toFixed(2)} to reach ${rankLabel(next)}`,
              )}
            </span>
            <progress
              aria-labelledby="improve-progress-label"
              value={simulation.cpa - simulated.min_cpa}
              max={next.min_cpa - simulated.min_cpa}
            />
          </div>
        )}
        <div className="improve-selection">
          <span data-testid="improve-selection">{t(
            `Đã chọn ${simulation.count} môn · ${simulation.credits} tín chỉ`,
            `${simulation.count} selected · ${simulation.credits} credits`,
          )}</span>
          <button type="button" className="improve-button improve-reset" onClick={onReset} disabled={!simulation.count}>
            <RotateCcw size={14} aria-hidden="true" />
            {t('Bỏ chọn tất cả', 'Clear selection')}
          </button>
        </div>
      </div>
    </section>
  );
}
