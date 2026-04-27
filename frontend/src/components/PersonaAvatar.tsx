import { useState, type CSSProperties } from "react";

interface Props {
  code: string;
  emoji: string;
  colorFrom: string;
  colorTo: string;
  size?: number;
  style?: CSSProperties;
}

/**
 * Persona avatar. Tries to load an AI-generated PNG from /static/personas/{code}.png
 * first (real MBTI-style character). If the image fails to load, falls back to the
 * procedural SVG scene below.
 */
export default function PersonaAvatar({
  code, emoji, colorFrom, colorTo, size = 200, style,
}: Props) {
  const [pngError, setPngError] = useState(false);
  const pngUrl = `/static/personas/${code}.png`;

  if (!pngError) {
    return (
      <img
        src={pngUrl}
        alt={code}
        width={size}
        height={size}
        onError={() => setPngError(true)}
        style={{
          width: size,
          height: size,
          objectFit: "contain",
          borderRadius: Math.round(size * 0.15),
          background: `linear-gradient(135deg, ${colorFrom}25, ${colorTo}25)`,
          ...style,
        }}
      />
    );
  }

  // Fallback: procedural SVG
  const id = `persona-grad-${code}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 240 240"
      xmlns="http://www.w3.org/2000/svg"
      style={style}
    >
      <defs>
        <radialGradient id={id} cx="30%" cy="30%" r="90%">
          <stop offset="0%" stopColor={colorFrom} />
          <stop offset="100%" stopColor={colorTo} />
        </radialGradient>
      </defs>
      {/* Background circle */}
      <circle cx="120" cy="120" r="118" fill={`url(#${id})`} />
      <circle cx="120" cy="120" r="118" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="2" />

      {/* Scene layer per persona */}
      <g opacity="0.85">{renderScene(code)}</g>

      {/* Big emoji centered */}
      <text
        x="120"
        y="148"
        fontSize="84"
        textAnchor="middle"
        style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.2))" }}
      >
        {emoji}
      </text>

      {/* Code chip bottom */}
      <rect x="76" y="200" width="88" height="24" rx="12" fill="rgba(0,0,0,0.25)" />
      <text
        x="120"
        y="217"
        fontSize="13"
        fontWeight="700"
        textAnchor="middle"
        fill="#fff"
        style={{ fontFamily: "'JetBrains Mono', 'SF Mono', monospace", letterSpacing: 2 }}
      >
        {code}
      </text>
    </svg>
  );
}

/* ── Per-persona decorative scenes ─────────────────────────────────────── */

const W = "rgba(255,255,255,0.18)";   // light decoration
const W2 = "rgba(255,255,255,0.35)";  // highlight

function renderScene(code: string) {
  switch (code) {
    case "GOAT": // 老神仙 — mountain range + sun
      return (
        <>
          <circle cx="180" cy="60" r="18" fill={W2} />
          <path d="M 10 200 L 70 100 L 110 150 L 160 80 L 230 200 Z" fill={W} />
          <path d="M 65 105 L 70 100 L 78 110 L 65 105 Z" fill="rgba(255,255,255,0.5)" />
          <path d="M 155 85 L 160 80 L 169 93 L 155 85 Z" fill="rgba(255,255,255,0.5)" />
        </>
      );
    case "PI": // 组里老大 — crown + 5 subordinate dots
      return (
        <>
          <path d="M 60 50 L 80 80 L 100 40 L 120 80 L 140 40 L 160 80 L 180 50 L 175 95 L 65 95 Z" fill={W} />
          <circle cx="55" cy="200" r="5" fill={W2} />
          <circle cx="85" cy="210" r="5" fill={W2} />
          <circle cx="120" cy="215" r="5" fill={W2} />
          <circle cx="155" cy="210" r="5" fill={W2} />
          <circle cx="185" cy="200" r="5" fill={W2} />
          <line x1="55" y1="200" x2="120" y2="170" stroke={W} strokeWidth="1" />
          <line x1="185" y1="200" x2="120" y2="170" stroke={W} strokeWidth="1" />
        </>
      );
    case "WOLF": // 独狼 — moon + pine trees
      return (
        <>
          <circle cx="60" cy="70" r="20" fill={W2} />
          <circle cx="68" cy="65" r="20" fill={`url(#persona-grad-${code})`} />
          <path d="M 30 190 L 50 130 L 70 190 Z" fill={W} />
          <path d="M 180 200 L 200 140 L 220 200 Z" fill={W} />
          <path d="M 150 205 L 165 160 L 180 205 Z" fill={W} opacity="0.7" />
        </>
      );
    case "VIRAL": // 开源新贵 — rocket trail of sparkles
      return (
        <>
          {[25, 50, 80, 115, 155, 195].map((x, i) => (
            <g key={i} transform={`translate(${x}, ${40 + i * 15})`}>
              <path d="M 0 -8 L 3 -3 L 8 0 L 3 3 L 0 8 L -3 3 L -8 0 L -3 -3 Z" fill={W2} />
            </g>
          ))}
          <path d="M 20 220 Q 80 180 140 100" stroke={W} strokeWidth="3" fill="none" strokeLinecap="round" />
        </>
      );
    case "QED": // 理论大神 — floating math symbols
      return (
        <>
          <text x="40" y="80" fontSize="28" fill={W2} fontFamily="serif" fontStyle="italic">∃</text>
          <text x="180" y="90" fontSize="28" fill={W2} fontFamily="serif" fontStyle="italic">∀</text>
          <text x="30" y="200" fontSize="26" fill={W2} fontFamily="serif" fontStyle="italic">∑</text>
          <text x="195" y="200" fontSize="26" fill={W2} fontFamily="serif" fontStyle="italic">∞</text>
          <text x="115" y="55" fontSize="22" fill={W} fontFamily="serif">Q.E.D.</text>
        </>
      );
    case "SENSEI": // 学派掌门 — scroll lines + seal
      return (
        <>
          <rect x="30" y="50" width="180" height="20" rx="10" fill={W} />
          <rect x="45" y="80" width="150" height="4" fill={W} />
          <rect x="45" y="95" width="130" height="4" fill={W} />
          <rect x="45" y="110" width="150" height="4" fill={W} />
          <rect x="30" y="160" width="180" height="20" rx="10" fill={W} />
          <rect x="180" y="195" width="30" height="30" rx="4" fill="rgba(220,38,38,0.55)" />
          <text x="195" y="215" fontSize="16" fill="#fff" textAnchor="middle" fontWeight="700">印</text>
        </>
      );
    case "MONK": // 苦行僧 — concentric lotus petals
      return (
        <>
          {[80, 60, 40].map((r, i) => (
            <circle
              key={i}
              cx="120"
              cy="120"
              r={r}
              fill="none"
              stroke={W}
              strokeWidth="1"
              strokeDasharray="3 4"
              opacity={0.5 - i * 0.1}
            />
          ))}
          {[0, 60, 120, 180, 240, 300].map((deg) => (
            <ellipse
              key={deg}
              cx="120"
              cy="50"
              rx="8"
              ry="24"
              fill={W}
              transform={`rotate(${deg} 120 120)`}
            />
          ))}
        </>
      );
    case "HYPE": // 学术新贵 — sunburst rays
      return (
        <>
          {Array.from({ length: 12 }).map((_, i) => {
            const deg = i * 30;
            return (
              <rect
                key={i}
                x="117"
                y="10"
                width="6"
                height="36"
                fill={W2}
                transform={`rotate(${deg} 120 120)`}
              />
            );
          })}
          {/* sparkles */}
          {[[50,60],[190,80],[200,180],[40,170]].map(([x,y],i)=>(
            <path key={i} d={`M ${x} ${y-6} L ${x+2} ${y-2} L ${x+6} ${y} L ${x+2} ${y+2} L ${x} ${y+6} L ${x-2} ${y+2} L ${x-6} ${y} L ${x-2} ${y-2} Z`} fill={W2} />
          ))}
        </>
      );
    case "NINJA": // 一人成军 — shuriken + diagonal lines
      return (
        <>
          <g transform="translate(50, 55)" opacity="0.6">
            <path d="M 0 -14 L 4 -4 L 14 0 L 4 4 L 0 14 L -4 4 L -14 0 L -4 -4 Z" fill={W2} />
          </g>
          <g transform="translate(190, 180)" opacity="0.6">
            <path d="M 0 -12 L 3 -3 L 12 0 L 3 3 L 0 12 L -3 3 L -12 0 L -3 -3 Z" fill={W2} />
          </g>
          <line x1="20" y1="120" x2="60" y2="110" stroke={W} strokeWidth="2" strokeLinecap="round" />
          <line x1="220" y1="120" x2="180" y2="110" stroke={W} strokeWidth="2" strokeLinecap="round" />
          <line x1="30" y1="200" x2="80" y2="170" stroke={W} strokeWidth="1.5" strokeLinecap="round" />
        </>
      );
    case "BDFL": // 造轮大师 — globe grid
      return (
        <>
          <circle cx="120" cy="120" r="90" fill="none" stroke={W2} strokeWidth="2" />
          <ellipse cx="120" cy="120" rx="90" ry="30" fill="none" stroke={W} strokeWidth="1" />
          <ellipse cx="120" cy="120" rx="30" ry="90" fill="none" stroke={W} strokeWidth="1" />
          <ellipse cx="120" cy="120" rx="90" ry="55" fill="none" stroke={W} strokeWidth="1" />
          <ellipse cx="120" cy="120" rx="55" ry="90" fill="none" stroke={W} strokeWidth="1" />
        </>
      );
    case "JUAN": // 卷王 — flame + paper stacks
      return (
        <>
          {/* paper stack behind */}
          {[0, 8, 16, 24].map((o, i) => (
            <rect
              key={i}
              x={40 + i * 3}
              y={150 + o}
              width="60"
              height="8"
              rx="2"
              fill={W}
              opacity={0.5 - i * 0.1}
            />
          ))}
          {[0, 8, 16, 24].map((o, i) => (
            <rect
              key={`r-${i}`}
              x={140 - i * 3}
              y={150 + o}
              width="60"
              height="8"
              rx="2"
              fill={W}
              opacity={0.5 - i * 0.1}
            />
          ))}
          {/* flame */}
          <path
            d="M 120 50 Q 100 90 110 120 Q 90 110 95 75 Q 80 100 85 135 Q 100 120 105 95 Q 115 110 120 50 Z M 120 50 Q 140 90 130 120 Q 150 110 145 75 Q 160 100 155 135 Q 140 120 135 95 Q 125 110 120 50 Z"
            fill={W2}
          />
        </>
      );
    case "MILL": // 论文工厂 — smoke stacks + paper flow
      return (
        <>
          <rect x="40" y="130" width="160" height="80" fill={W} />
          <rect x="60" y="90" width="20" height="50" fill={W} />
          <rect x="110" y="70" width="20" height="70" fill={W} />
          <rect x="160" y="90" width="20" height="50" fill={W} />
          {/* smoke puffs */}
          <circle cx="70" cy="80" r="10" fill={W2} />
          <circle cx="80" cy="60" r="12" fill={W2} opacity="0.7" />
          <circle cx="120" cy="55" r="10" fill={W2} />
          <circle cx="135" cy="35" r="12" fill={W2} opacity="0.7" />
          <circle cx="170" cy="80" r="10" fill={W2} />
        </>
      );
    default:
      return null;
  }
}
