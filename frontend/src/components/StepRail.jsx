const STEPS = [
  { key: "baseline", label: "Baseline Calibration" },
  { key: "questions", label: "Deviation Analysis" },
];

export default function StepRail({ current }) {
  const currentIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 16,
        padding: "6px 18px",
        borderRadius: 30,
        background: "var(--surface)",
        backdropFilter: "blur(16px)",
        border: "1px solid var(--line-strong)",
      }}
    >
      {STEPS.map((step, i) => {
        const isDone = i < currentIndex;
        const isActive = i === currentIndex;

        return (
          <div key={step.key} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              className="mono"
              style={{
                fontSize: 11,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? "var(--text)" : isDone ? "var(--text-soft)" : "var(--text-faint)",
                letterSpacing: "0.04em",
              }}
            >
              0{i + 1} {step.label}
            </span>

            {i < STEPS.length - 1 && (
              <span style={{ fontSize: 10, color: "var(--text-faint)" }}>—</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
