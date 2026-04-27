import { forwardRef } from "react";
import type { AnnualPoemData, UserProfile } from "@/lib/api";

interface Props {
  poem: AnnualPoemData;
  user: UserProfile;
}

const THEMES: Record<string, { from: string; to: string; accent: string; seal: string }> = {
  indigo: { from: "#1e1b4b", to: "#4338ca", accent: "#a5b4fc", seal: "#eef2ff" },
  amber: { from: "#451a03", to: "#b45309", accent: "#fcd34d", seal: "#fffbeb" },
  emerald: { from: "#064e3b", to: "#047857", accent: "#6ee7b7", seal: "#ecfdf5" },
  rose: { from: "#4c1d24", to: "#be185d", accent: "#fda4af", seal: "#fff1f2" },
};

const AnnualPoemCard = forwardRef<HTMLDivElement, Props>(({ poem, user }, ref) => {
  const theme = THEMES[poem.theme] ?? THEMES.indigo;
  return (
    <div
      ref={ref}
      style={{
        width: 460,
        fontFamily: "'Source Han Serif', 'Noto Serif SC', 'Songti SC', 'PingFang SC', serif",
        background: `linear-gradient(160deg, ${theme.from}, ${theme.to})`,
        color: "#fff",
        borderRadius: 20,
        padding: "48px 40px",
        position: "relative",
        overflow: "hidden",
        boxShadow: "0 10px 40px rgba(0,0,0,0.25)",
      }}
    >
      {/* Decorative vertical strip */}
      <div
        style={{
          position: "absolute",
          left: 24,
          top: 48,
          bottom: 48,
          width: 1,
          background: `linear-gradient(to bottom, ${theme.accent}00, ${theme.accent}66, ${theme.accent}00)`,
        }}
      />

      {/* Subtle year watermark */}
      <div
        style={{
          position: "absolute",
          right: -20,
          top: -40,
          fontSize: 260,
          fontWeight: 700,
          opacity: 0.07,
          lineHeight: 1,
          color: theme.accent,
          letterSpacing: -8,
          fontFamily: "'Playfair Display', Georgia, serif",
        }}
      >
        {poem.year}
      </div>

      {/* Header */}
      <div style={{ position: "relative", textAlign: "center", marginBottom: 28 }}>
        <div style={{ fontSize: 11, letterSpacing: 6, color: theme.accent, opacity: 0.85 }}>
          IMPACTHUB · 年度诗篇
        </div>
        <div style={{ marginTop: 10, fontSize: 34, fontWeight: 600, letterSpacing: 6 }}>
          {poem.year}
        </div>
        {poem.title && (
          <div style={{ marginTop: 8, fontSize: 14, opacity: 0.8, letterSpacing: 2 }}>
            {poem.title}
          </div>
        )}
      </div>

      {/* Verses */}
      <div style={{ position: "relative", textAlign: "center", marginBottom: 32 }}>
        {poem.verses.map((v, i) => {
          const isFrame = i === 0 || i === poem.verses.length - 1;
          // Adaptive font size: more verses → smaller
          const size = poem.verses.length <= 6 ? 17 : poem.verses.length <= 10 ? 15 : 14;
          return (
            <div
              key={i}
              style={{
                fontSize: size,
                lineHeight: 1.9,
                letterSpacing: 1.2,
                color: isFrame ? theme.accent : "#fff",
                opacity: isFrame ? 0.92 : 1,
                fontWeight: isFrame ? 500 : 400,
              }}
            >
              {v}
            </div>
          );
        })}
      </div>

      {/* Highlights */}
      {poem.highlights.length > 0 && (
        <div
          style={{
            position: "relative",
            display: "flex",
            justifyContent: "space-around",
            gap: 10,
            paddingTop: 20,
            borderTop: `1px solid ${theme.accent}33`,
            marginBottom: 16,
            flexWrap: "wrap",
          }}
        >
          {poem.highlights.slice(0, 4).map((h, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: theme.accent,
                  letterSpacing: 0.5,
                }}
              >
                {h.value}
              </div>
              <div style={{ fontSize: 10, opacity: 0.65, marginTop: 2, letterSpacing: 1 }}>
                {h.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer: seal with researcher name */}
      <div
        style={{
          position: "relative",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 24,
          fontSize: 11,
          opacity: 0.7,
          letterSpacing: 1.5,
        }}
      >
        <span>— {user.name || user.github_username || "研究者"} —</span>
        <span style={{ fontFamily: "monospace" }}>
          {new Date().toISOString().slice(0, 10).replace(/-/g, ".")}
        </span>
      </div>
    </div>
  );
});

AnnualPoemCard.displayName = "AnnualPoemCard";

export default AnnualPoemCard;
