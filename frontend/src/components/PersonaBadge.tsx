import { motion } from "framer-motion";
import type { ResearcherPersona } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface Props {
  persona?: ResearcherPersona | null;
  loading?: boolean;
  onGenerate?: () => void;
}

export default function PersonaBadge({ persona, loading, onGenerate }: Props) {
  if (persona) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold backdrop-blur-sm"
        style={{
          background: `linear-gradient(135deg, ${persona.color_from}40, ${persona.color_to}40)`,
          border: `1px solid ${persona.color_from}50`,
        }}
        title={`${persona.name_zh} — ${persona.tagline || persona.description}`}
      >
        <span className="text-sm">{persona.emoji}</span>
        <span className="text-white/90">{persona.name_zh}</span>
        <span className="text-[10px] text-white/70 font-bold tracking-wider rounded-full bg-white/15 px-1.5 py-0.5 font-mono">
          {persona.persona_code}
        </span>
      </motion.div>
    );
  }

  if (onGenerate) {
    return (
      <button
        onClick={onGenerate}
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-[11px] text-white/50 transition hover:bg-white/15 hover:text-white/70 disabled:opacity-50"
      >
        {loading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <span className="text-sm">🧬</span>
        )}
        {loading ? "计算中..." : "生成研究者人格"}
      </button>
    );
  }

  return null;
}
