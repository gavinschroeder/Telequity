export default function StateCard({ tone = "neutral", title, body, code, spinner }) {
  return (
    <div className="state-wrap">
      <div className={`state-card state-${tone}`}>
        {spinner ? <div className="spinner" aria-hidden="true" /> : <div className={`state-glyph glyph-${tone}`} />}
        <h2>{title}</h2>
        {body && <p>{body}</p>}
        {code && <code className="state-code">{code}</code>}
      </div>
    </div>
  );
}
