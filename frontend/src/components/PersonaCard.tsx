import { forwardRef } from "react";
import type { ResearcherPersona, UserProfile, Stats } from "@/lib/api";
import PersonaAvatar from "./PersonaAvatar";

interface Props {
  persona: ResearcherPersona;
  user: UserProfile;
  stats: Stats;
}

const AXIS_LABELS: [string, string, string][] = [
  ["output_depth", "多产", "深耕"],
  ["ecosystem", "理论", "建设"],
  ["seniority", "新锐", "资深"],
  ["collaboration", "独行", "协作"],
];

const PersonaCard = forwardRef<HTMLDivElement, Props>(({ persona, user, stats }, ref) => {
  const score = (key: string) => Math.round((persona.dimension_scores[key] ?? 0.5) * 100);

  return (
    <div
      ref={ref}
      style={{
        width: 420,
        fontFamily: "'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
        background: `linear-gradient(135deg, ${persona.color_from}, ${persona.color_to})`,
        borderRadius: 24,
        padding: 32,
        color: "#fff",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Decorative circles */}
      <div
        style={{
          position: "absolute",
          top: -40,
          right: -40,
          width: 160,
          height: 160,
          borderRadius: "50%",
          background: "rgba(255,255,255,0.08)",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: -30,
          left: -30,
          width: 120,
          height: 120,
          borderRadius: "50%",
          background: "rgba(255,255,255,0.06)",
        }}
      />

      {/* Persona avatar + name */}
      <div style={{ textAlign: "center", position: "relative" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 8 }}>
          <PersonaAvatar
            code={persona.persona_code}
            emoji={persona.emoji}
            colorFrom={persona.color_from}
            colorTo={persona.color_to}
            size={180}
          />
        </div>
        <div style={{ fontSize: 28, fontWeight: 800, marginTop: 4, letterSpacing: 2 }}>
          {persona.name_zh}
        </div>
        <div
          style={{
            display: "inline-block",
            marginTop: 8,
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: 4,
            padding: "4px 16px",
            borderRadius: 999,
            background: "rgba(255,255,255,0.2)",
            fontFamily: "'JetBrains Mono', 'SF Mono', Consolas, monospace",
          }}
        >
          {persona.persona_code}
        </div>
        <div style={{ fontSize: 13, opacity: 0.7, marginTop: 6, fontWeight: 500, letterSpacing: 1 }}>
          {persona.name_en}
        </div>
        {persona.tagline && (
          <div
            style={{
              fontSize: 13,
              fontStyle: "italic",
              marginTop: 12,
              opacity: 0.9,
              letterSpacing: 0.5,
            }}
          >
            "{persona.tagline}"
          </div>
        )}
        <div
          style={{
            fontSize: 11,
            opacity: 0.6,
            marginTop: 12,
            lineHeight: 1.6,
            maxWidth: 320,
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          {persona.description}
        </div>
      </div>

      {/* Dimension bars: center-anchored, fills toward the leaning side */}
      <div style={{ marginTop: 28, position: "relative" }}>
        {AXIS_LABELS.map(([key, labelLow, labelHigh]) => {
          const pct = score(key);              // 0-100
          const leansRight = pct >= 50;
          const strength = Math.abs(pct - 50) * 2; // 0-100 distance from center
          const dominantLabel = leansRight ? labelHigh : labelLow;
          return (
            <div key={key} style={{ marginBottom: 14 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  marginBottom: 4,
                }}
              >
                <span style={{ opacity: leansRight ? 0.35 : 1, fontWeight: leansRight ? 400 : 600 }}>
                  {labelLow}
                </span>
                <span style={{ opacity: 0.6, fontSize: 10, fontWeight: 700 }}>
                  {strength.toFixed(0)}% {dominantLabel}
                </span>
                <span style={{ opacity: leansRight ? 1 : 0.35, fontWeight: leansRight ? 600 : 400 }}>
                  {labelHigh}
                </span>
              </div>
              <div
                style={{
                  height: 8,
                  borderRadius: 4,
                  background: "rgba(255,255,255,0.15)",
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* center tick */}
                <div
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: 0,
                    bottom: 0,
                    width: 1,
                    background: "rgba(255,255,255,0.35)",
                  }}
                />
                {/* filled segment from center to the leaning side */}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    bottom: 0,
                    left: leansRight ? "50%" : `${50 - strength / 2}%`,
                    width: `${strength / 2}%`,
                    background: "rgba(255,255,255,0.8)",
                    borderRadius: 2,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Traits */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 6,
          justifyContent: "center",
          marginTop: 20,
        }}
      >
        {persona.traits.map((t) => (
          <span
            key={t}
            style={{
              fontSize: 10,
              padding: "3px 10px",
              borderRadius: 20,
              background: "rgba(255,255,255,0.15)",
              fontWeight: 600,
            }}
          >
            {t}
          </span>
        ))}
      </div>

      {/* User info */}
      <div
        style={{
          marginTop: 24,
          paddingTop: 16,
          borderTop: "1px solid rgba(255,255,255,0.15)",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url.includes("githubusercontent.com")
              ? `/api/proxy/image?url=${encodeURIComponent(user.avatar_url)}`
              : user.avatar_url}
            alt=""
            style={{ width: 36, height: 36, borderRadius: 10, border: "2px solid rgba(255,255,255,0.2)" }}
            crossOrigin="anonymous"
          />
        ) : (
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "rgba(255,255,255,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              fontWeight: 700,
            }}
          >
            {(user.name || "?")[0]}
          </div>
        )}
        <div>
          <div style={{ fontSize: 14, fontWeight: 700 }}>{user.name || "研究者"}</div>
          <div style={{ fontSize: 10, opacity: 0.5 }}>
            {stats.paper_count} 论文 &middot; h-index {stats.h_index} &middot; {stats.total_citations} 引用
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          marginTop: 16,
          textAlign: "center",
          fontSize: 9,
          opacity: 0.35,
          letterSpacing: 1,
        }}
      >
        ImpactHub &middot; 研究者人格画像
      </div>
    </div>
  );
});

PersonaCard.displayName = "PersonaCard";

export default PersonaCard;
