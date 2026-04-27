import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type LeaderboardData, type LeaderboardEntry } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Trophy, Sparkles, Loader2 } from "lucide-react";

type TabKey = "total" | "young" | "llm" | "cv" | "vlm" | "systems" | "theory" | "rl";
type MetricKey = "h_index" | "total_citations" | "ccf_a_count" | "total_stars";

const tabs: { key: TabKey; label: string }[] = [
  { key: "total", label: "总榜" },
  { key: "young", label: "年轻学者" },
  { key: "llm", label: "LLM / NLP" },
  { key: "cv", label: "Computer Vision" },
  { key: "vlm", label: "VLM / Generative" },
  { key: "systems", label: "Systems" },
  { key: "theory", label: "Theory" },
  { key: "rl", label: "RL" },
];

const metrics: { key: MetricKey; label: string }[] = [
  { key: "h_index", label: "h-index" },
  { key: "total_citations", label: "总引用" },
  { key: "ccf_a_count", label: "CCF-A" },
  { key: "total_stars", label: "GitHub Stars" },
];

const MEDAL_COLORS: Record<number, string> = {
  1: "bg-gradient-to-br from-amber-400 to-amber-600 text-white",
  2: "bg-gradient-to-br from-slate-300 to-slate-500 text-white",
  3: "bg-gradient-to-br from-orange-400 to-orange-600 text-white",
};

function tabToQuery(tab: TabKey): { type: "total" | "young" | "direction"; direction?: string } {
  if (tab === "total") return { type: "total" };
  if (tab === "young") return { type: "young" };
  return { type: "direction", direction: tab };
}

export default function LeaderboardPage() {
  const [tab, setTab] = useState<TabKey>("total");
  const [metric, setMetric] = useState<MetricKey>("h_index");
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const { type, direction } = tabToQuery(tab);
    api
      .getRankings({ type, direction, metric, limit: 100 })
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [tab, metric]);

  return (
    <main className="mx-auto max-w-5xl px-4 py-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-6 shadow-sm"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 text-white">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">排行榜</h1>
            <p className="text-xs text-gray-500">
              前 10000 名精确排位，之后以百分位呈现，兼顾可比性与审慎度
            </p>
          </div>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="mb-3 flex gap-1.5 overflow-x-auto">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`shrink-0 rounded-full border px-4 py-1.5 text-sm font-medium transition ${
              tab === key
                ? "border-indigo-500 bg-indigo-600 text-white shadow-sm"
                : "border-gray-200 bg-white text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Metric selector */}
      <div className="mb-4 flex items-center gap-2 text-xs">
        <span className="text-gray-400">按指标排序：</span>
        {metrics.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setMetric(key)}
            className={`rounded-full px-2.5 py-0.5 transition ${
              metric === key
                ? "bg-indigo-100 text-indigo-700 font-semibold"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          加载中...
        </div>
      ) : !data || data.entries.length === 0 ? (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-gray-200 bg-gray-50 py-14">
          <Sparkles className="h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-500">榜单暂无数据</p>
          <p className="mt-1 text-xs text-gray-400">种子学者正在批量导入中，稍后刷新页面</p>
        </div>
      ) : (
        <>
          <div className="mb-3 text-xs text-gray-400">
            共 {data.total_count} 位学者
            {data.direction && ` · ${data.direction.toUpperCase()} 方向`}
          </div>
          <div className="space-y-2">
            {data.entries.map((e, i) => (
              <motion.div
                key={e.user.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.015, duration: 0.3 }}
              >
                <LeaderboardRow entry={e} metric={metric} />
              </motion.div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}

function LeaderboardRow({ entry, metric }: { entry: LeaderboardEntry; metric: MetricKey }) {
  const rankDisplay = entry.rank !== null ? (
    <span className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold ${
      MEDAL_COLORS[entry.rank] || "bg-gray-100 text-gray-600"
    }`}>
      {entry.rank}
    </span>
  ) : (
    <span className="flex h-8 min-w-[3rem] items-center justify-center rounded-lg bg-gray-50 px-1.5 text-[11px] font-semibold text-gray-500">
      前 {entry.percentile}%
    </span>
  );

  const primaryMetric = entry.metrics[metric];

  return (
    <Link
      to={`/profile/${entry.user.scholar_id || entry.user.id}`}
      className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm transition hover:border-indigo-300 hover:shadow-md"
    >
      {rankDisplay}

      {entry.user.avatar_url ? (
        <img
          src={entry.user.avatar_url}
          alt=""
          className="h-10 w-10 shrink-0 rounded-full border border-gray-200 object-cover"
        />
      ) : (
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 text-sm font-bold text-indigo-700">
          {(entry.user.name || "?")[0]}
        </div>
      )}

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="truncate text-sm font-semibold text-gray-900">
            {entry.user.name}
          </span>
          {entry.user.research_direction && (
            <span className="shrink-0 rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
              {entry.user.research_direction.toUpperCase()}
            </span>
          )}
          {entry.user.seed_tier && (
            <span className="shrink-0 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
              {entry.user.seed_tier}
            </span>
          )}
          {entry.user.honor_tags.slice(0, 2).map((h) => (
            <span
              key={h}
              className="shrink-0 rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200"
            >
              {h}
            </span>
          ))}
          {entry.user.honor_tags.length > 2 && (
            <span className="shrink-0 text-[10px] text-amber-600">
              +{entry.user.honor_tags.length - 2}
            </span>
          )}
        </div>
        <div className="mt-0.5 flex items-center gap-3 text-[11px] text-gray-500">
          <span>h-index <b className="text-gray-700">{entry.metrics.h_index}</b></span>
          <span>引用 <b className="text-gray-700">{formatNumber(entry.metrics.total_citations)}</b></span>
          <span>论文 <b className="text-gray-700">{entry.metrics.paper_count}</b></span>
          {entry.metrics.ccf_a_count > 0 && (
            <span className="text-red-600">CCF-A <b>{entry.metrics.ccf_a_count}</b></span>
          )}
        </div>
      </div>

      <div className="text-right">
        <div className="text-lg font-bold text-indigo-600 tabular-nums">
          {formatNumber(primaryMetric)}
        </div>
        <div className="text-[10px] text-gray-400">
          {metrics.find((m) => m.key === metric)?.label}
        </div>
      </div>
    </Link>
  );
}

const metricKeys: { key: MetricKey; label: string }[] = [
  { key: "h_index", label: "h-index" },
  { key: "total_citations", label: "总引用" },
  { key: "ccf_a_count", label: "CCF-A" },
  { key: "total_stars", label: "Stars" },
];
// avoid unused warning
void metricKeys;
