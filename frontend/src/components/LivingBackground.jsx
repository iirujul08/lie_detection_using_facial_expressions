import { useEffect, useRef } from "react";

export default function LivingBackground({ theme }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let animId;
    let time = 0;

    let w = (canvas.width = window.innerWidth);
    let h = (canvas.height = window.innerHeight);

    const handleResize = () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    };

    window.addEventListener("resize", handleResize);

    const render = () => {
      time += 0.003; // Very slow, calm organic drift

      const isDark = theme === "dark";

      // Base background color
      ctx.fillStyle = isDark ? "#0e0d0c" : "#f7f4ef";
      ctx.fillRect(0, 0, w, h);

      // Soft ambient warm light gradient blobs drifting continuously
      const g1X = w * 0.4 + Math.cos(time * 0.5) * (w * 0.15);
      const g1Y = h * 0.3 + Math.sin(time * 0.4) * (h * 0.15);
      const g1Radius = Math.max(w, h) * 0.5;

      const g1 = ctx.createRadialGradient(g1X, g1Y, 0, g1X, g1Y, g1Radius);
      if (isDark) {
        g1.addColorStop(0, "rgba(55, 48, 40, 0.25)");
        g1.addColorStop(1, "transparent");
      } else {
        g1.addColorStop(0, "rgba(235, 226, 213, 0.7)");
        g1.addColorStop(1, "transparent");
      }
      ctx.fillStyle = g1;
      ctx.fillRect(0, 0, w, h);

      const g2X = w * 0.7 + Math.sin(time * 0.6) * (w * 0.18);
      const g2Y = h * 0.7 + Math.cos(time * 0.5) * (h * 0.18);
      const g2Radius = Math.max(w, h) * 0.45;

      const g2 = ctx.createRadialGradient(g2X, g2Y, 0, g2X, g2Y, g2Radius);
      if (isDark) {
        g2.addColorStop(0, "rgba(35, 30, 26, 0.3)");
        g2.addColorStop(1, "transparent");
      } else {
        g2.addColorStop(0, "rgba(225, 214, 198, 0.6)");
        g2.addColorStop(1, "transparent");
      }
      ctx.fillStyle = g2;
      ctx.fillRect(0, 0, w, h);

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animId);
    };
  }, [theme]);

  return (
    <>
      <canvas
        ref={canvasRef}
        style={{
          position: "fixed",
          inset: 0,
          width: "100vw",
          height: "100vh",
          pointerEvents: "none",
          zIndex: 0,
          transition: "background-color 0.5s ease",
        }}
      />
      {/* Subtle Editorial Grain Overlay */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          zIndex: 1,
          opacity: 0.035,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
    </>
  );
}
