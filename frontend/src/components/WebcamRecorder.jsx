import { useRef, useState, useEffect, useCallback } from "react";

export default function WebcamRecorder({ clipSeconds = 4, onCapture, disabled, theme = "light" }) {
  const videoRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const [status, setStatus] = useState("idle"); // idle | ready | recording | processing
  const [secondsLeft, setSecondsLeft] = useState(clipSeconds);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        mediaStreamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setStatus("ready");
      } catch (err) {
        setError("Camera access restricted: " + err.message);
      }
    }
    initCamera();
    return () => {
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // Subtle Refined Facial Landmark Overlay
  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let animId;
    let time = 0;

    const BASE_LANDMARKS = [
      // Left eye
      { x: 0.38, y: 0.42 }, { x: 0.41, y: 0.40 }, { x: 0.44, y: 0.42 }, { x: 0.41, y: 0.44 },
      // Right eye
      { x: 0.56, y: 0.42 }, { x: 0.59, y: 0.40 }, { x: 0.62, y: 0.42 }, { x: 0.59, y: 0.44 },
      // Brows
      { x: 0.36, y: 0.36 }, { x: 0.41, y: 0.34 }, { x: 0.45, y: 0.36 },
      { x: 0.55, y: 0.36 }, { x: 0.59, y: 0.34 }, { x: 0.64, y: 0.36 },
      // Nose
      { x: 0.50, y: 0.42 }, { x: 0.50, y: 0.48 }, { x: 0.47, y: 0.54 }, { x: 0.50, y: 0.56 }, { x: 0.53, y: 0.54 },
      // Mouth
      { x: 0.42, y: 0.66 }, { x: 0.46, y: 0.64 }, { x: 0.50, y: 0.65 }, { x: 0.54, y: 0.64 }, { x: 0.58, y: 0.66 },
      { x: 0.54, y: 0.70 }, { x: 0.50, y: 0.71 }, { x: 0.46, y: 0.70 },
      // Jaw
      { x: 0.34, y: 0.58 }, { x: 0.38, y: 0.70 }, { x: 0.45, y: 0.78 }, { x: 0.50, y: 0.81 }, { x: 0.55, y: 0.78 }, { x: 0.62, y: 0.70 }, { x: 0.66, y: 0.58 }
    ];

    const renderLandmarks = () => {
      time += 0.02;
      const w = (canvas.width = canvas.clientWidth || 560);
      const h = (canvas.height = canvas.clientHeight || 420);

      ctx.clearRect(0, 0, w, h);

      if (status === "ready" || status === "recording") {
        const isRec = status === "recording";
        const isDark = theme === "dark";
        const dotColor = isRec
          ? "rgba(225, 60, 60, 0.85)"
          : isDark
          ? "rgba(240, 236, 230, 0.65)"
          : "rgba(25, 23, 22, 0.65)";
        const lineAlpha = isRec ? 0.25 : 0.12;

        const swayX = Math.sin(time * 0.7) * 4;
        const swayY = Math.cos(time * 0.5) * 3;

        const points = BASE_LANDMARKS.map((pt) => ({
          x: pt.x * w + swayX + Math.sin(time * 2 + pt.x * 8) * 1.2,
          y: pt.y * h + swayY + Math.cos(time * 2 + pt.y * 8) * 1.2,
        }));

        // Draw delicate connecting lines
        ctx.strokeStyle = isRec ? "rgba(225, 60, 60, 0.3)" : isDark ? `rgba(240, 236, 230, ${lineAlpha})` : `rgba(25, 23, 22, ${lineAlpha})`;
        ctx.lineWidth = 0.6;

        for (let i = 0; i < points.length; i++) {
          for (let j = i + 1; j < points.length; j++) {
            const dx = points[i].x - points[j].x;
            const dy = points[i].y - points[j].y;
            if (Math.sqrt(dx * dx + dy * dy) < w * 0.11) {
              ctx.beginPath();
              ctx.moveTo(points[i].x, points[i].y);
              ctx.lineTo(points[j].x, points[j].y);
              ctx.stroke();
            }
          }
        }

        // Draw micro keypoint dots
        points.forEach((p) => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
          ctx.fillStyle = dotColor;
          ctx.fill();
        });
      }

      animId = requestAnimationFrame(renderLandmarks);
    };

    renderLandmarks();

    return () => cancelAnimationFrame(animId);
  }, [status, theme]);

  const startRecording = useCallback(() => {
    if (!mediaStreamRef.current) return;
    chunksRef.current = [];
    const recorder = new MediaRecorder(mediaStreamRef.current, {
      mimeType: "video/webm",
    });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      setStatus("processing");
      Promise.resolve(onCapture(blob)).finally(() => {
        setStatus("ready");
        setSecondsLeft(clipSeconds);
      });
    };
    mediaRecorderRef.current = recorder;
    recorder.start();
    setStatus("recording");
    setSecondsLeft(clipSeconds);

    const tick = setInterval(() => {
      setSecondsLeft((s) => (s > 1 ? s - 1 : s));
    }, 1000);

    setTimeout(() => {
      clearInterval(tick);
      if (recorder.state === "recording") recorder.stop();
    }, clipSeconds * 1000);
  }, [clipSeconds, onCapture]);

  if (error) {
    return (
      <div
        style={{
          padding: 14,
          borderRadius: 12,
          background: "rgba(225, 60, 60, 0.1)",
          border: "1px solid var(--red)",
          color: "var(--red)",
          fontFamily: "var(--font-mono)",
          fontSize: 12,
        }}
      >
        ⚠️ {error}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
      <div className="video-hairline-frame">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: theme === "dark" ? "contrast(1.05) brightness(0.95)" : "contrast(1.02) brightness(1.02)",
          }}
        />

        <canvas
          ref={overlayCanvasRef}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
            zIndex: 4,
          }}
        />

        {/* Corner hairline ticks */}
        <div className="hud-hairline-corner tl" />
        <div className="hud-hairline-corner tr" />
        <div className="hud-hairline-corner bl" />
        <div className="hud-hairline-corner br" />

        {/* Subtle scanline */}
        {(status === "ready" || status === "recording") && <div className="editorial-scanline" />}

        {/* Status indicator */}
        <div
          className="mono"
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "5px 12px",
            borderRadius: 20,
            background: "var(--surface)",
            backdropFilter: "blur(12px)",
            border: "1px solid var(--line-strong)",
            fontSize: 11,
            fontWeight: 500,
            color: "var(--text)",
            zIndex: 10,
          }}
        >
          <span className={`live-dot${status === "recording" ? " recording" : ""}`} />
          {status === "recording" ? `RECORDING · ${secondsLeft}s` : status === "ready" ? "LIVE STREAM" : "LOADING FEED..."}
        </div>
      </div>

      {/* Action Button */}
      <div style={{ marginTop: 20, width: "100%", maxWidth: 580 }}>
        <button
          className="primary"
          onClick={startRecording}
          disabled={disabled || status === "recording" || status === "processing" || status === "idle"}
          style={{
            width: "100%",
            padding: "14px 24px",
            fontSize: 14,
          }}
        >
          {status === "recording" ? (
            `Recording (${secondsLeft}s)...`
          ) : status === "processing" ? (
            "Processing clip..."
          ) : status === "idle" ? (
            "Connecting camera..."
          ) : (
            `Capture ${clipSeconds}s Clip`
          )}
        </button>
      </div>
    </div>
  );
}
