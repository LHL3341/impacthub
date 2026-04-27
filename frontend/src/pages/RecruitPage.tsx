import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Briefcase, Sparkles, Loader2, Search, Github, ExternalLink,
  Trophy, AlertTriangle, Award, Users, ArrowRight,
} from "lucide-react";
import { api, type RecruitSearchResponse, type RecruitCandidate, type RecruitCriteria } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

const EXAMPLES: { label: string; jd: string }[] = [
  {
    label: "LLM 后训练资深研究员",
    jd: "招聘 LLM 后训练（post-training）方向资深研究员，重点关注 RLHF、DPO、对齐、奖励建模。期望候选人在 NeurIPS/ICML/ICLR 上有多篇一作工作，h-index ≥ 25。如有开源社区贡献（如 trl、Open-RLHF 等）加分。",
  },
  {
    label: "多模态生成方向 PI",
    jd: "为大模型实验室寻找一位多模态生成（diffusion、视频生成、3D 生成）方向的资深 PI 或工业界 director。需要在视觉/多模态有奠基工作，最好有开源代表作（Stable Diffusion 系、Sora 类、SDXL 等）。学术声誉与工程能力都重要。",
  },
  {
    label: "AI 系统/推理优化工程师",
    jd: "招资深 AI 系统工程师，研究方向：大模型推理优化、KV cache、量化、kernel 编写。期望有 vLLM / FlashAttention / TensorRT-LLM / SGLang 等开源项目贡献，GitHub stars 1k+。学术发表是加分项但不强制。",
  },
];

const TIER_META: Record<string, { label: string; bg: string; ring: string; bar: string; text: string }> = {
  perfect: {
    label: "完美匹配",
    bg: "bg-gradient-to-br from-emerald-500 to-teal-600",
    ring: "ring-emerald-200",
    bar: "from-emerald-400 to-teal-500",
    text: "text-emerald-700",
  },
  strong: {
    label: "强匹配",
    bg: "bg-gradient-to-br from-indigo-500 to-blue-600",
    ring: "ring-indigo-200",
    bar: "from-indigo-400 to-blue-500",
    text: "text-indigo-700",
  },
  potential: {
    label: "潜力候选",
    bg: "bg-gradient-to-br from-amber-500 to-orange-600",
    ring: "ring-amber-200",
    bar: "from-amber-400 to-orange-500",
    text: "text-amber-700",
  },
};

const SENIORITY_LABEL: Record<string, string> = {
  senior: "资深",
  mid: "中坚",
  junior: "新锐",
  any: "不限",
};

const DIRECTION_LABEL: Record<string, string> = {
  llm: "LLM/NLP",
  cv: "Computer Vision",
  vlm: "VLM/生成",
  systems: "Systems",
  theory: "Theory",
  rl: "RL",
};

export default function RecruitPage() {
  const [jd, setJd] = useState("");
  const [topK, setTopK] = useState(10);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RecruitSearchResponse | null>(null);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    const trimmed = jd.trim();
    if (!trimmed) {
      setError("请输入岗位需求或人才画像描述");
      return;
    }
    setError("");
    setLoading(true);
    setData(null);
    try {
      const res = await api.recruitSearch(trimmed, topK);
      setData(res);
      if (!res.results.length) {
        setError(res.search_summary || "未匹配到候选人，请放宽条件后重试。");
      }
    } catch {
      setError("搜索服务暂时不可用，请稍后重试。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-6 shadow-sm"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
            <Briefcase className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-gray-900">猎头查询 · AI 人才匹配</h1>
            <p className="text-xs text-gray-500">
              用自然语言描述你要找的人，AI 会从 ImpactHub 数据库里挑出最匹配的学者并解释为什么
            </p>
          </div>
        </div>
      </motion.div>

      {/* Input area */}
      <div className="mb-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500">
          岗位需求 / 人才画像
        </label>
        <textarea
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="例：招聘 LLM 后训练方向资深研究员，重点关注 RLHF、DPO、对齐。期望 NeurIPS/ICML 多篇一作，h-index ≥ 25，开源贡献加分..."
          className="h-32 w-full resize-none rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm leading-relaxed text-gray-900 placeholder-gray-400 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />

        {/* Quick examples */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-gray-400">示例：</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              onClick={() => setJd(ex.jd)}
              className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-600 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
            >
              {ex.label}
            </button>
          ))}
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleSearch}
            disabled={loading || !jd.trim()}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-3 text-sm font-semibold text-white shadow-sm transition hover:shadow-md disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                AI 正在评估候选人…（需要 30-60 秒）
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                开始 AI 搜索
              </>
            )}
          </button>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500">返回</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={loading}
              className="rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs text-gray-700 focus:border-indigo-400 focus:outline-none"
            >
              {[5, 10, 15, 20].map((n) => (
                <option key={n} value={n}>{n} 人</option>
              ))}
            </select>
          </div>
        </div>

        {error && !loading && (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <LoadingState />
      )}

      {/* Results */}
      <AnimatePresence>
        {data && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-4"
          >
            {/* Criteria + summary */}
            <CriteriaPanel criteria={data.criteria} summary={data.search_summary} pool={data.candidate_pool_size} filtered={data.filtered_pool_size} />

            {/* Candidate cards */}
            {data.results.map((c, i) => (
              <CandidateCard key={c.user_id} candidate={c} rank={i + 1} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {!data && !loading && !error && (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-white p-10 text-center text-sm text-gray-400">
          <Sparkles className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p>输入需求后，AI 会先解析你要的画像，再从数据库里逐一评估，最终给出排序+原因。</p>
        </div>
      )}
    </main>
  );
}

// ────────── Loading skeleton ──────────
function LoadingState() {
  const stages = [
    { label: "解析岗位需求", icon: "🔍" },
    { label: "粗筛候选人才池", icon: "📚" },
    { label: "AI 逐一打分排序", icon: "⚖️" },
  ];
  return (
    <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-sm font-medium text-indigo-700">
        <Loader2 className="h-4 w-4 animate-spin" />
        AI 正在分析…
      </div>
      <div className="space-y-2">
        {stages.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.4 }}
            className="flex items-center gap-3 rounded-lg bg-white px-3 py-2 text-sm text-gray-700 shadow-sm"
          >
            <span className="text-lg">{s.icon}</span>
            <span>{s.label}</span>
            <Loader2 className="ml-auto h-3 w-3 animate-spin text-indigo-400" />
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ────────── Criteria chips panel ──────────
function CriteriaPanel({
  criteria, summary, pool, filtered,
}: { criteria: RecruitCriteria; summary: string; pool: number; filtered?: number }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-start gap-2">
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
        <div className="flex-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">AI 解析的画像</div>
          {criteria.intent_summary && (
            <div className="mt-1 text-sm text-gray-800">{criteria.intent_summary}</div>
          )}
        </div>
        <div className="flex items-center gap-1 rounded-full bg-gray-50 px-2.5 py-1 text-[10px] text-gray-500">
          <Users className="h-3 w-3" />
          候选池 {pool}{filtered != null ? ` → 粗筛 ${filtered}` : ""}
        </div>
      </div>

      {summary && (
        <div className="mb-3 rounded-lg bg-indigo-50 px-3 py-2 text-xs italic leading-relaxed text-indigo-800">
          "{summary}"
        </div>
      )}

      <div className="flex flex-wrap gap-1.5 text-[11px]">
        {criteria.research_directions.map((d) => (
          <Chip key={d} color="indigo">方向 · {DIRECTION_LABEL[d] || d}</Chip>
        ))}
        {criteria.seniority !== "any" && (
          <Chip color="purple">资历 · {SENIORITY_LABEL[criteria.seniority]}</Chip>
        )}
        {criteria.min_h_index > 0 && <Chip color="blue">h-index ≥ {criteria.min_h_index}</Chip>}
        {criteria.min_paper_count > 0 && <Chip color="blue">论文 ≥ {criteria.min_paper_count}</Chip>}
        {criteria.min_ccf_a_count > 0 && <Chip color="blue">CCF-A ≥ {criteria.min_ccf_a_count}</Chip>}
        {criteria.min_total_stars > 0 && <Chip color="amber">Stars ≥ {formatNumber(criteria.min_total_stars)}</Chip>}
        {criteria.needs_open_source && <Chip color="amber">需开源贡献</Chip>}
        {criteria.needs_industry_experience && <Chip color="emerald">需工业经验</Chip>}
        {criteria.must_have_keywords.map((k) => (
          <Chip key={`m-${k}`} color="rose">必须 · {k}</Chip>
        ))}
        {criteria.nice_to_have_keywords.map((k) => (
          <Chip key={`n-${k}`} color="sky">加分 · {k}</Chip>
        ))}
        {criteria.honors_preferred.map((k) => (
          <Chip key={`h-${k}`} color="amber">荣誉 · {k}</Chip>
        ))}
        {criteria.exclude_keywords.map((k) => (
          <Chip key={`x-${k}`} color="gray">排除 · {k}</Chip>
        ))}
        <Chip color="gray">排序优先 · {criteria.ranking_priority}</Chip>
      </div>
    </div>
  );
}

function Chip({ children, color }: { children: React.ReactNode; color: string }) {
  const palette: Record<string, string> = {
    indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
    rose: "bg-rose-50 text-rose-700 border-rose-200",
    sky: "bg-sky-50 text-sky-700 border-sky-200",
    gray: "bg-gray-50 text-gray-600 border-gray-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 ${palette[color] || palette.gray}`}>
      {children}
    </span>
  );
}

// ────────── Candidate card ──────────
function CandidateCard({ candidate, rank }: { candidate: RecruitCandidate; rank: number }) {
  const tier = TIER_META[candidate.tier] || TIER_META.potential;
  const u = candidate.user;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.04 }}
      className={`rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md ring-1 ${tier.ring}`}
    >
      <div className="flex items-start gap-4">
        {/* Rank + score column */}
        <div className="flex flex-col items-center gap-2">
          <div className="text-[10px] font-mono text-gray-400">#{rank}</div>
          <div className={`flex h-14 w-14 flex-col items-center justify-center rounded-2xl text-white shadow-sm ${tier.bg}`}>
            <div className="text-lg font-bold leading-none">{candidate.match_score}</div>
            <div className="mt-0.5 text-[8px] uppercase tracking-wider opacity-90">match</div>
          </div>
          <span className={`text-[10px] font-semibold ${tier.text}`}>{tier.label}</span>
        </div>

        {/* Main column */}
        <div className="flex-1 min-w-0">
          {/* Header: name + honors + scholar link */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              {u.avatar_url ? (
                <img
                  src={u.avatar_url}
                  alt={u.name}
                  className="h-12 w-12 shrink-0 rounded-full border border-gray-200 object-cover"
                />
              ) : (
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-600">
                  {(u.name || "?").charAt(0)}
                </div>
              )}
              <div className="min-w-0">
                <Link
                  to={`/profile/${u.id}`}
                  className="block truncate text-base font-bold text-gray-900 hover:text-indigo-600"
                >
                  {u.name}
                </Link>
                {candidate.primary_direction && (
                  <div className="mt-0.5 text-xs text-gray-500 truncate">{candidate.primary_direction}</div>
                )}
                {u.honor_tags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {u.honor_tags.slice(0, 4).map((h) => (
                      <span key={h} className="inline-flex items-center gap-0.5 rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200">
                        <Award className="h-2.5 w-2.5" />
                        {h}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <Link
              to={`/profile/${u.id}`}
              className="shrink-0 inline-flex items-center gap-1 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100"
            >
              查看主页
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {/* Key metrics row */}
          <div className="mt-3 grid grid-cols-4 gap-2 text-center">
            <Metric label="h-index" value={candidate.metrics.h_index} />
            <Metric label="总引用" value={formatNumber(candidate.metrics.total_citations)} />
            <Metric label="CCF-A" value={candidate.metrics.ccf_a_count} />
            <Metric label="GitHub Stars" value={formatNumber(candidate.metrics.total_stars)} />
          </div>

          {/* Fit reasoning */}
          {candidate.fit_reasoning && (
            <div className="mt-3 rounded-lg bg-gradient-to-r from-indigo-50 to-purple-50 px-3 py-2 text-xs leading-relaxed text-gray-800">
              <span className={`mr-1 font-semibold ${tier.text}`}>匹配理由：</span>
              {candidate.fit_reasoning}
            </div>
          )}

          {/* Highlights */}
          {candidate.highlights.length > 0 && (
            <div className="mt-2.5">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">闪光点</div>
              <ul className="space-y-1">
                {candidate.highlights.map((h, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                    <Trophy className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
                    <span>{h}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Concerns */}
          {candidate.concerns.length > 0 && (
            <div className="mt-2.5">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">需要权衡</div>
              <ul className="space-y-1">
                {candidate.concerns.map((c, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-orange-400" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key works */}
          {candidate.key_works.length > 0 && (
            <div className="mt-3 border-t border-gray-100 pt-3">
              <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-400">代表作</div>
              <ul className="space-y-1.5">
                {candidate.key_works.map((w, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs">
                    {w.url ? (
                      <a
                        href={w.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 text-gray-800 hover:text-indigo-600 hover:underline"
                      >
                        {w.title}
                      </a>
                    ) : (
                      <span className="flex-1 text-gray-800">{w.title}</span>
                    )}
                    <span className="shrink-0 text-[10px] text-gray-400 font-mono">
                      {w.year > 0 ? `${w.year}` : ""}
                      {w.venue ? ` · ${w.venue}` : ""}
                      {w.citation_count > 0 ? ` · 引 ${w.citation_count}` : ""}
                      {w.ccf_rank ? ` · CCF-${w.ccf_rank}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Footer links */}
          {(u.github_username || u.homepage || candidate.top_repos.length > 0) && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3 text-[11px]">
              {u.github_username && (
                <a
                  href={`https://github.com/${u.github_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 hover:bg-gray-200"
                >
                  <Github className="h-3 w-3" />
                  {u.github_username}
                </a>
              )}
              {u.homepage && (
                <a
                  href={u.homepage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 hover:bg-gray-200"
                >
                  <ExternalLink className="h-3 w-3" />
                  个人主页
                </a>
              )}
              {candidate.top_repos.slice(0, 2).map((r) => (
                <a
                  key={r.name}
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-amber-700 border border-amber-200 hover:bg-amber-100"
                >
                  ⭐ {r.name} · {formatNumber(r.stars)}
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-gray-50 px-2 py-1.5">
      <div className="text-sm font-bold text-gray-900 tabular-nums">{value}</div>
      <div className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</div>
    </div>
  );
}
