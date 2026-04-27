import { motion } from "framer-motion";
import type { CapabilityData, CapabilityDirectionProfile } from "@/lib/api";
import { Loader2, RefreshCw, Sparkles, Quote } from "lucide-react";

interface Props {
  data: CapabilityData | null;
  loading?: boolean;
  onRefresh?: () => void;
}

export default function CapabilityCard({ data, loading, onRefresh }: Props) {
  if (!data) {
    return (
      <div className="flex items-center justify-between rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-200 text-slate-600">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-800">能力画像</div>
            <div className="text-xs text-gray-500">各方向角色 × 成果立体画像</div>
          </div>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
          {loading ? "分析中…" : "生成"}
        </button>
      </div>
    );
  }

  const profiles = data.profiles || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl border border-gray-200 bg-white shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">能力画像</div>
          {data.primary_direction && (
            <div className="mt-0.5 flex items-center gap-1.5 text-sm">
              <span className="text-base">{data.primary_role_emoji}</span>
              <span className="font-bold text-gray-900">{data.primary_direction}</span>
              <span className="text-gray-400">的</span>
              <span
                className="font-semibold"
                style={{ color: data.primary_role_color }}
              >
                {data.primary_role_zh}
              </span>
            </div>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1 text-[10px] text-gray-500 transition hover:bg-gray-50 disabled:opacity-50"
          title="重新分析"
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
        </button>
      </div>

      {data.rationale && (
        <div className="px-4 py-2.5 text-xs italic text-gray-600 leading-relaxed border-b border-gray-100">
          "{data.rationale}"
        </div>
      )}

      {/* Per-direction profiles */}
      <div className="divide-y divide-gray-100">
        {profiles.map((p, i) => (
          <DirectionRow key={i} profile={p} />
        ))}
      </div>
    </motion.div>
  );
}

function DirectionRow({ profile }: { profile: CapabilityDirectionProfile }) {
  const scorePct = Math.round(profile.score * 100);
  const weightPct = Math.round(profile.weight * 100);

  return (
    <div className="px-4 py-3">
      {/* Direction + role row */}
      <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base">{profile.role_emoji}</span>
          <span className="text-sm font-semibold text-gray-900 truncate">
            {profile.direction_zh || profile.direction_en}
          </span>
          <span
            className="rounded-full px-1.5 py-0.5 text-[10px] font-mono font-bold"
            style={{ background: profile.role_color + "20", color: profile.role_color }}
          >
            {profile.role_en}
          </span>
        </div>
        <span className="text-[10px] text-gray-400 font-mono shrink-0">
          占比 {weightPct}%
        </span>
      </div>

      {/* Weight bar */}
      <div className="h-1 rounded-full bg-gray-100 mb-2 overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${scorePct}%`, background: profile.role_color }}
        />
      </div>

      {/* Achievements */}
      {profile.achievements && (
        <div className="text-xs text-gray-600 leading-relaxed mb-1.5">
          {profile.achievements}
        </div>
      )}

      {/* Representative works */}
      {profile.representative_works.length > 0 && (
        <ul className="space-y-0.5">
          {profile.representative_works.slice(0, 3).map((w, i) => (
            <li key={i} className="flex items-start gap-1 text-[11px] text-gray-500">
              <Quote className="mt-0.5 h-2.5 w-2.5 shrink-0 text-gray-400" />
              <div className="flex-1 min-w-0">
                <span className="text-gray-700">{w.title}</span>
                {w.year && <span className="text-gray-400 ml-1">({w.year})</span>}
                {w.citing_count > 0 && (
                  <span className="text-gray-400 ml-1">· 引用 {w.citing_count}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
