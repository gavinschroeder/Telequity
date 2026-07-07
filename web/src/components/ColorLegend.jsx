/**
 * Color-scheme key for the equity-index maps. Shows the exact value cutoffs and
 * what each color signifies, so viewers can read severity at a glance.
 */
export default function ColorLegend({ legend }) {
  if (!legend) return null;
  return (
    <div className="legend-bar" role="group" aria-label="Color scale">
      {legend.caption && <span className="legend-caption">{legend.caption}</span>}
      <div className="legend-items">
        {legend.tiers.map((t) => (
          <span className="legend-item" key={t.range}>
            <span className="legend-swatch" style={{ background: t.color }} />
            <span className="legend-range">{t.range}</span>
            <span className="legend-label">{t.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
