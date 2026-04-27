import { motion } from "framer-motion";
import type { ResearcherPersona } from "@/lib/api";
import { Sparkles, Loader2 } from "lucide-react";

interface Props {
  persona: ResearcherPersona | null;
  loading?: boolean;
  onGenerate?: () => void;
  onShare?: () => void;
}

export default function PersonaShowcase({ persona, loading, onGenerate, onShare }: Props) {
  if (!persona) {
    return (
      <div className="flex items-center justify-between rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-200 text-slate-600">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-800">研究者人格</div>
            <div className="text-xs text-gray-500">生成你的研究者人格</div>
          </div>
        </div>
        <button
          onClick={onGenerate}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
          {loading ? "计算中…" : "生成"}
        </button>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm"
      style={{
        backgroundImage: `linear-gradient(180deg, ${persona.color_from}10 0%, ${persona.color_to}05 100%)`,
      }}
    >
      <div className="flex flex-col items-center gap-3 p-4 text-center">
        {/* Illustration */}
        <button
          onClick={onShare}
          className="rounded-2xl p-2 transition hover:scale-105"
          style={{
            background: `linear-gradient(135deg, ${persona.color_from}15, ${persona.color_to}20)`,
          }}
          title="点击导出分享卡片"
        >
          <img
            src={`/static/personas/${persona.persona_code}.png`}
            alt={persona.name_zh}
            width={160}
            height={160}
            style={{ width: 160, height: 160, objectFit: "contain" }}
          />
        </button>

        {/* Name + code */}
        <div className="flex items-center gap-2 flex-wrap justify-center">
          <span className="text-xl">{persona.emoji}</span>
          <h3 className="text-lg font-bold text-gray-900 tracking-wide">{persona.name_zh}</h3>
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-bold font-mono tracking-wider"
            style={{
              background: persona.color_from + "20",
              color: persona.color_from,
            }}
          >
            {persona.persona_code}
          </span>
        </div>

        {/* Tagline */}
        {persona.tagline && (
          <p className="text-xs italic text-gray-600 px-2">"{persona.tagline}"</p>
        )}

        {/* Traits */}
        <div className="flex flex-wrap justify-center gap-1">
          {persona.traits.map((t) => (
            <span
              key={t}
              className="rounded-full px-2 py-0.5 text-[10px] font-medium"
              style={{
                background: persona.color_from + "12",
                color: persona.color_from,
                border: `1px solid ${persona.color_from}30`,
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
