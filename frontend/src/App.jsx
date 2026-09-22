import { useState, useEffect } from "react";
import LivingBackground from "./components/LivingBackground.jsx";
import WebcamRecorder from "./components/WebcamRecorder.jsx";
import Meter from "./components/Meter.jsx";
import StepRail from "./components/StepRail.jsx";
import { createSession, uploadBaselineClip, finalizeBaseline, scoreQuestion } from "./api.js";

const BASELINE_PROMPTS = [
  "What city are you in right now?",
  "What's today's date?",
  "Read aloud: The weather today is sunny and warm.",
];

const STAGE = { SETUP: "setup", BASELINE: "baseline", QUESTIONS: "questions" };

export default function App() {
  const [theme, setTheme] = useState("dark"); // 'dark' | 'light' default
  const [stage, setStage] = useState(STAGE.SETUP);
  const [sessionId, setSessionId] = useState(null);
  const [baselineIndex, setBaselineIndex] = useState(0);
  const [baselineWarnings, setBaselineWarnings] = useState([]);
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [copiedSession, setCopiedSession] = useState(false);

  // Sync theme attribute on <html> element
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "light" ? "dark" : "light"));
  }

  async function handleStart() {
    setError(null);
    try {
      const { session_id } = await createSession();
      setSessionId(session_id);
      setStage(STAGE.BASELINE);
    } catch (e) {
      setError(e.message + " -- is backend running on localhost:8000?");
    }
  }

  async function handleBaselineCapture(blob) {
    setError(null);
    try {
      await uploadBaselineClip(sessionId, blob);
      if (baselineIndex + 1 < BASELINE_PROMPTS.length) {
        setBaselineIndex(baselineIndex + 1);
      } else {
        const fin = await finalizeBaseline(sessionId);
        setBaselineWarnings(fin.warnings || []);
        setStage(STAGE.QUESTIONS);
      }
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleQuestionCapture(blob) {
    setError(null);
    if (!question.trim()) {
      setError("Please enter a question before capturing.");
      return;
    }
    try {
      const result = await scoreQuestion(sessionId, question, blob);
      setResults((prev) => [{ question, ...result, timestamp: new Date().toLocaleTimeString() }, ...prev]);
      setQuestion("");
    } catch (e) {
      setError(e.message);
    }
  }

  function handleCopySession() {
    if (!sessionId) return;
    navigator.clipboard.writeText(sessionId);
    setCopiedSession(true);
    setTimeout(() => setCopiedSession(false), 2000);
  }

  function handleResetSession() {
    setStage(STAGE.SETUP);
    setSessionId(null);
    setBaselineIndex(0);
    setBaselineWarnings([]);
    setQuestion("");
    setResults([]);
    setError(null);
  }

  return (
    <>
      {/* Calm Living Motion Background */}
      <LivingBackground theme={theme} />

      {/* Top Header Dock */}
      <header
        style={{
          position: "fixed",
          top: 24,
          left: 32,
          right: 32,
          zIndex: 50,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pointerEvents: "auto",
        }}
      >
        <div />

        {stage !== STAGE.SETUP && (
          <div style={{ position: "absolute", left: "50%", transform: "translateX(-50%)" }}>
            <StepRail current={stage === STAGE.BASELINE ? "baseline" : "questions"} />
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {sessionId && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "4px 12px",
                borderRadius: 20,
                background: "var(--surface)",
                border: "1px solid var(--line)",
                fontSize: 11,
              }}
              className="mono"
            >
              <span>ID: {sessionId.slice(0, 8)}...</span>
              <button onClick={handleCopySession} style={{ padding: "2px 6px", fontSize: 10 }}>
                {copiedSession ? "Copied" : "Copy"}
              </button>
              <button onClick={handleResetSession} style={{ padding: "2px 6px", fontSize: 10 }}>
                Reset
              </button>
            </div>
          )}

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            style={{
              padding: "6px 14px",
              fontSize: 12,
              borderRadius: 30,
            }}
          >
            {theme === "light" ? "🌙 Dark Mode" : "☀️ Light Mode"}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main
        style={{
          position: "relative",
          zIndex: 10,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "100px 24px 120px",
        }}
      >
        {error && (
          <div
            style={{
              position: "fixed",
              top: 80,
              left: "50%",
              transform: "translateX(-50%)",
              zIndex: 60,
              padding: "8px 18px",
              borderRadius: 20,
              background: "var(--surface)",
              border: "1px solid var(--red)",
              color: "var(--red)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {/* SETUP STAGE: Clean Editorial Introduction */}
        {stage === STAGE.SETUP && (
          <div style={{ textAlign: "center", maxWidth: 520 }} className="card-appear">
            {/* 3D Dual-Sided Twisting Biometric Face Asset (Female Front / Male Back) */}
            <div style={{ marginBottom: 28 }}>
              <div className="flip-logo-container">
                <div className="flip-logo-inner">
                  <div className="flip-logo-front">
                    <img src="/biometric_face_female.png" alt="Female Biometric Face" />
                  </div>
                  <div className="flip-logo-back">
                    <img src="/biometric_face_male.png" alt="Male Biometric Face" />
                  </div>
                </div>
              </div>
            </div>

            <h1 style={{ fontSize: 36, lineHeight: 1.15, marginBottom: 12, fontWeight: 600 }}>
              Facial Deviation Console
            </h1>

            <p style={{ fontSize: 14, color: "var(--text-soft)", lineHeight: 1.6, marginBottom: 32 }}>
              Quantifies personal micro-expression drift relative to a calibrated baseline.
              A scientific signal drift indicator — not a truth verdict.
            </p>

            <button className="primary" onClick={handleStart} style={{ padding: "14px 32px", fontSize: 14 }}>
              Start Session Calibration
            </button>
          </div>
        )}

        {/* BASELINE & QUESTIONS STAGE: Centerpiece Live Video Viewport */}
        {(stage === STAGE.BASELINE || stage === STAGE.QUESTIONS) && (
          <div
            style={{
              width: "100%",
              maxWidth: 580,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
            className="card-appear"
          >
            {stage === STAGE.BASELINE && (
              <div
                style={{
                  textAlign: "center",
                  marginBottom: 18,
                }}
              >
                <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)", letterSpacing: "0.06em" }}>
                  SAMPLE {baselineIndex + 1} OF {BASELINE_PROMPTS.length}
                </span>
                <h2 style={{ fontSize: 18, marginTop: 4 }}>"{BASELINE_PROMPTS[baselineIndex]}"</h2>
              </div>
            )}

            <WebcamRecorder
              theme={theme}
              onCapture={stage === STAGE.BASELINE ? handleBaselineCapture : handleQuestionCapture}
            />
          </div>
        )}

        {/* QUESTIONS PHASE: Bottom Floating Input Station */}
        {stage === STAGE.QUESTIONS && (
          <div
            style={{
              position: "fixed",
              bottom: 28,
              left: "50%",
              transform: "translateX(-50%)",
              zIndex: 50,
              width: "90%",
              maxWidth: 580,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "6px 6px 6px 16px",
              borderRadius: 40,
              background: "var(--surface)",
              backdropFilter: "blur(20px)",
              border: "1px solid var(--line-strong)",
              boxShadow: "var(--shadow-subtle)",
            }}
          >
            <input
              type="text"
              placeholder="Type question being asked..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                boxShadow: "none",
                padding: "8px 0",
              }}
            />
            <button
              className="primary"
              onClick={() => {
                if (!question.trim()) setError("Please enter a question first.");
              }}
              style={{
                padding: "10px 18px",
                fontSize: 12,
                whiteSpace: "nowrap",
              }}
            >
              Set Question
            </button>
          </div>
        )}
      </main>

      {/* Side Telemetry Drawer */}
      {stage === STAGE.QUESTIONS && (
        <aside
          style={{
            position: "fixed",
            top: 90,
            right: 28,
            bottom: 90,
            width: 300,
            zIndex: 40,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 12,
            pointerEvents: "auto",
          }}
        >
          <div
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              background: "var(--surface)",
              backdropFilter: "blur(16px)",
              border: "1px solid var(--line)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--text-soft)" }}>
              EVALUATION LOGS ({results.length})
            </span>
          </div>

          {baselineWarnings.length > 0 && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                background: "rgba(225, 150, 40, 0.1)",
                border: "1px solid var(--amber)",
                color: "var(--amber)",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
              }}
            >
              ⚠️ {baselineWarnings.join(" ")}
            </div>
          )}

          {results.length === 0 ? (
            <div
              style={{
                padding: "20px 14px",
                borderRadius: 12,
                background: "var(--surface)",
                border: "1px dashed var(--line)",
                textAlign: "center",
              }}
            >
              <p className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
                Awaiting target question evaluation...
              </p>
            </div>
          ) : (
            results.map((r, i) => (
              <div
                key={`${r.question}-${i}`}
                className="card-appear"
                style={{
                  padding: "14px",
                  borderRadius: 12,
                  background: "var(--surface)",
                  backdropFilter: "blur(16px)",
                  border: "1px solid var(--line)",
                  boxShadow: "var(--shadow-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{r.question}</span>
                  {r.timestamp && (
                    <span className="mono" style={{ fontSize: 10, color: "var(--text-faint)" }}>
                      {r.timestamp}
                    </span>
                  )}
                </div>
                <Meter meter={r.meter} bucket={r.bucket} warnings={r.warnings} />
              </div>
            ))
          )}
        </aside>
      )}
    </>
  );
}

