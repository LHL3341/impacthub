import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { CareerData, CareerStep } from "@/lib/api";
import { GraduationCap, Briefcase, Loader2, RefreshCw, Sparkles, ExternalLink } from "lucide-react";

interface Props {
  userId: string;
  data: CareerData | null;
  onUpdate: (d: CareerData | null) => void;
  onRefresh: () => Promise<void>;
  refreshing: boolean;
  elapsed: number;
}

function fmtRange(step: CareerStep): string {
  const s: string = step.start_year != null ? String(step.start_year) : "?";
  const e: string = step.end_year === null ? "至今" : (step.end_year != null ? String(step.end_year) : "?");
  if (s === "?" && (e === "?" || e === "至今")) return "";
  return `${s}–${e}`;
}

export default function CareerCard({ data, onRefresh, refreshing, elapsed }: Props) {
  const [expanded, setExpanded] = useState(false);
  const sources = data?.sources ?? [];
  const timeline = data?.timeline ?? [];

  // Split into 教育 + 任职 subsections, most recent first
  const sortByYearDesc = (a: CareerStep, b: CareerStep) => {
    // Ongoing entries (end_year === null) sort first, then most recent start_year
    const aEnd = a.end_year ?? 9999;
    const bEnd = b.end_year ?? 9999;
    if (aEnd !== bEnd) return bEnd - aEnd;
    return (b.start_year ?? 0) - (a.start_year ?? 0);
  };
  const education = timeline.filter((s) => s.type === "education").sort(sortByYearDesc);
  const positions = timeline.filter((s) => s.type !== "education").sort(sortByYearDesc);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
            <Briefcase className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">履历</h3>
            <p className="text-xs text-gray-400">
              {data?.refreshed_at
                ? `更新于 ${new Date(data.refreshed_at).toLocaleString("zh-CN")}`
                : "尚未生成履历"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {data?.current && (
            <span className="hidden sm:inline-block max-w-xs truncate rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
              {data.current}
            </span>
          )}
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 transition hover:border-indigo-300 hover:text-indigo-600 disabled:opacity-50"
          >
            {refreshing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : data ? (
              <RefreshCw className="h-3.5 w-3.5" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            {data ? "刷新" : "开始生成"}
          </button>
        </div>
      </div>

      {/* Empty state */}
      {!data && !refreshing && (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-400">
          <Briefcase className="mx-auto mb-2 h-8 w-8 opacity-30" />
          <p>点击「开始生成」由 AI 搜索并整理研究者的教育背景与任职经历</p>
        </div>
      )}

      {/* Progress */}
      {refreshing && (
        <div className="rounded-2xl border border-indigo-100 bg-indigo-50 p-5">
          <div className="mb-2 flex items-center justify-between text-sm text-indigo-700">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              {elapsed < 15
                ? "正在搜索履历来源…"
                : elapsed < 40
                ? "正在核实机构与任期…"
                : elapsed < 80
                ? "正在整理时间线…"
                : "仍在处理中，请耐心等待…"}
            </div>
            <span className="text-xs font-semibold tabular-nums">{elapsed}s</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-indigo-200">
            <div
              className="h-full rounded-full bg-indigo-400 transition-all duration-1000"
              style={{ width: `${Math.min(95, Math.round((elapsed / 90) * 100))}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-[10px] text-indigo-400">
            <span>搜索</span>
            <span>核实</span>
            <span>整理</span>
          </div>
        </div>
      )}

      {/* Education + Positions (split) + Sources */}
      {data && timeline.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          {/* 教育背景 */}
          {education.length > 0 && (
            <Section
              title="教育背景"
              count={education.length}
              icon={<GraduationCap className="h-3.5 w-3.5 text-indigo-500" />}
              steps={education}
              dotClass="bg-indigo-500"
              typeLabel="Education"
              TypeIcon={GraduationCap}
            />
          )}

          {/* 职业经历 */}
          {positions.length > 0 && (
            <div className={education.length > 0 ? "mt-5 pt-5 border-t border-gray-100" : ""}>
              <Section
                title="职业经历"
                count={positions.length}
                icon={<Briefcase className="h-3.5 w-3.5 text-emerald-600" />}
                steps={expanded ? positions : positions.slice(0, 6)}
                dotClass="bg-emerald-500"
                typeLabel="Position"
                TypeIcon={Briefcase}
              />
            </div>
          )}

          {positions.length > 6 && (
            <div className="mt-2">
              <button
                onClick={() => setExpanded((v) => !v)}
                className="text-xs text-indigo-600 hover:text-indigo-700 hover:underline"
              >
                {expanded ? "收起" : `显示全部 ${positions.length} 条任职`}
              </button>
            </div>
          )}

          {sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-400">来源</div>
              <div className="flex flex-wrap gap-1.5">
                {sources.slice(0, 8).map((s, i) => (
                  <a
                    key={i}
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600 transition hover:bg-gray-200 hover:text-gray-900"
                  >
                    <ExternalLink className="h-2.5 w-2.5" />
                    {s.title.length > 28 ? s.title.slice(0, 28) + "…" : s.title}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* No entries after refresh */}
      {data && timeline.length === 0 && (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center text-xs text-gray-400">
          暂无可查证的经历记录，可点击「刷新」重试。
        </div>
      )}
    </div>
  );
}

interface SectionProps {
  title: string;
  count: number;
  icon: React.ReactNode;
  steps: CareerStep[];
  dotClass: string;
  typeLabel: string;
  TypeIcon: React.ComponentType<{ className?: string }>;
}

function Section({ title, count, icon, steps, dotClass, typeLabel, TypeIcon }: SectionProps) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-gray-600">
          {icon}
          {title}
        </h4>
        <span className="text-xs text-gray-400">{count} 条</span>
      </div>
      <div className="relative pl-5">
        <div className="absolute left-1.5 top-2 bottom-2 w-px bg-gradient-to-b from-gray-200 via-gray-200 to-transparent" />
        <AnimatePresence initial={false}>
          {steps.map((step, i) => (
            <motion.div
              key={`${step.start_year}-${step.institution}-${i}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ delay: i * 0.04, duration: 0.25 }}
              className="relative pb-3 last:pb-0"
            >
              <span
                className={`absolute -left-[17px] top-1.5 flex h-3 w-3 items-center justify-center rounded-full ${dotClass} ring-4 ring-white`}
              />
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span className="text-[11px] font-mono text-gray-400 shrink-0">{fmtRange(step)}</span>
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider rounded px-1.5 py-px bg-gray-50 text-gray-500 border border-gray-200">
                  <TypeIcon className="h-2.5 w-2.5" />
                  {typeLabel}
                </span>
                <span className="text-sm font-medium text-gray-900">{step.role || "—"}</span>
                {step.institution && (
                  <span className="text-sm text-gray-600">@ {step.institution}</span>
                )}
              </div>
              {step.advisor && (
                <div className="mt-0.5 text-xs text-gray-500">
                  导师：<span className="text-gray-700">{step.advisor}</span>
                </div>
              )}
              {step.note && <div className="mt-0.5 text-xs text-gray-500">{step.note}</div>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
