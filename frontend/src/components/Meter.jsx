const BUCKET_STYLE = {
  Low: { color: "var(--text)", label: "Low Drift" },
  Medium: { color: "var(--amber)", label: "Moderate Drift" },
  High: { color: "var(--red)", label: "High Drift" },
};

export default function Meter({ meter, bucket, warnings }) {
  const style = BUCKET_STYLE[bucket] || { color: "var(--text-soft)", label: "Uncalibrated" };
  const clampedMeter = Math.min(100, Math.max(0, meter || 0));

  return (
    <div style={{ width: "100%" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-soft)" }}>
          {style.label}
        </span>
        <span className="mono" style={{ fontSize: 16, fontWeight: 600, color: style.color }}>
          {clampedMeter.toFixed(1)}%
        </span>
      </div>

      <div
        style={{
          position: "relative",
          height: 4,
          borderRadius: 2,
          background: "var(--line)",
          overflow: "hidden",
        }}
      >
        <div
          className="meter-fill"
          style={{
            width: `${clampedMeter}%`,
            height: "100%",
            background: style.color,
            borderRadius: 2,
          }}
        />
      </div>

      {warnings?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {warnings.map((w, i) => (
            <p key={i} className="mono" style={{ fontSize: 11, color: "var(--amber)" }}>
              ⚠️ {w}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
