const BUCKET_STYLE = {
  Low: { color: "var(--text)", label: "Low Risk", bg: "rgba(100, 200, 120, 0.1)" },
  Medium: { color: "var(--amber)", label: "Moderate Risk", bg: "rgba(225, 150, 40, 0.1)" },
  High: { color: "var(--red)", label: "High Risk", bg: "rgba(230, 92, 92, 0.1)" },
};

export default function Meter({
  meter,
  bucket,
  deception_probability,
  baseline_deviation,
  risk_score,
  risk_level,
  warnings,
  disclaimer,
}) {
  const effectiveRiskLevel = risk_level || bucket || "Low";
  const style = BUCKET_STYLE[effectiveRiskLevel] || BUCKET_STYLE.Low;
  const score = risk_score ?? meter ?? 0;
  const clampedScore = Math.min(100, Math.max(0, score));

  const probPercent =
    deception_probability !== undefined
      ? (deception_probability * 100).toFixed(1) + "%"
      : "N/A";

  const devPercent =
    baseline_deviation !== undefined
      ? (baseline_deviation * 100).toFixed(1) + "%"
      : "N/A";

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Risk Badge Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: style.color,
            background: style.bg,
            padding: "3px 10px",
            borderRadius: 12,
            border: `1px solid ${style.color}`,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {style.label}
        </span>
        <span className="mono" style={{ fontSize: 18, fontWeight: 700, color: style.color }}>
          {clampedScore.toFixed(1)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div
        style={{
          position: "relative",
          height: 6,
          borderRadius: 3,
          background: "var(--line)",
          overflow: "hidden",
        }}
      >
        <div
          className="meter-fill"
          style={{
            width: `${clampedScore}%`,
            height: "100%",
            background: style.color,
            borderRadius: 3,
          }}
        />
      </div>

      {/* Detailed Metrics Pill Breakdown Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          marginTop: 2,
        }}
      >
        <div
          style={{
            padding: "8px 10px",
            borderRadius: 8,
            background: "var(--bg-raised)",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ fontSize: 10, color: "var(--text-faint)", textTransform: "uppercase" }}>
            ML Deception Prob
          </div>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
            {probPercent}
          </div>
        </div>

        <div
          style={{
            padding: "8px 10px",
            borderRadius: 8,
            background: "var(--bg-raised)",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ fontSize: 10, color: "var(--text-faint)", textTransform: "uppercase" }}>
            Baseline AU Drift
          </div>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
            {devPercent}
          </div>
        </div>
      </div>

      {/* Disclaimer Box */}
      <div
        style={{
          padding: "8px 10px",
          borderRadius: 8,
          background: "var(--surface)",
          border: "1px solid var(--line)",
          fontSize: 10.5,
          lineHeight: 1.4,
          color: "var(--text-soft)",
        }}
      >
        ⚖️ <strong>Disclaimer:</strong>{" "}
        {disclaimer ||
          "Biometric signal risk estimate relative to baseline calibration. Not proof of lying."}
      </div>

      {/* Warnings */}
      {warnings?.length > 0 && (
        <div style={{ marginTop: 2, display: "flex", flexDirection: "column", gap: 4 }}>
          {warnings.map((w, i) => (
            <p key={i} className="mono" style={{ fontSize: 10.5, color: "var(--amber)" }}>
              ⚠️ {w}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
