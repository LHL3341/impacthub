import { useState, useEffect } from "react";
import { api, type TrajectoryData } from "@/lib/api";
import ResearchTree from "./ResearchTree";
import BuzzTimeline from "./BuzzTimeline";
import { Network, Loader2, RefreshCw, AlertCircle } from "lucide-react";

interface Props {
  userId: string;
  /** Hoisted state from parent so switching tabs doesn't lose the tree. */
  data: TrajectoryData | null;
  onUpdate: (d: TrajectoryData | null) => void;
}

export default function EvolutionTab({ userId, data, onUpdate }: Props) {
  // Only show "loading" on very first mount when parent hasn't fetched yet
  const [loading, setLoading] = useState(data === null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  // If parent hasn't loaded yet, fetch here as a safety net
  useEffect(() => {
    if (data) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    api
      .getTrajectory(userId)
      .then((d) => {
        if (cancelled) return;
        if (d && (d as unknown as { root?: unknown }).root) {
          onUpdate(d);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Intentionally only run once per (userId); onUpdate is stable enough from parent
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    setError("");
    try {
      const res = await api.refreshTrajectory(userId);
      const body = res as unknown as { status: string; data?: TrajectoryData; reason?: string };
      if (body.status === "done" && body.data) {
        onUpdate(body.data);
      } else if (body.status === "skipped") {
        setError(body.reason === "insufficient papers" ? "论文数量不足（至少需要 3 篇）" : "分析跳过");
      } else if (body.status === "error") {
        setError("分析失败，请查看后端日志");
      } else {
        const fresh = await api.getTrajectory(userId).catch(() => null);
        if (fresh) onUpdate(fresh);
      }
    } catch {
      setError("请求失败，请检查后端是否运行");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        加载中...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-10 shadow-sm">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600">
            <Network className="h-7 w-7" />
          </div>
          <h3 className="text-base font-semibold text-gray-900 mb-1">研究演化分析</h3>
          <p className="text-sm text-gray-500 mb-5 max-w-md">
            基于论文发表数据，自动提取研究方向演变脉络、主题迁移和方法转变
          </p>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Network className="h-4 w-4" />
            )}
            {refreshing ? "分析中..." : "开始分析"}
          </button>
          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-xs text-red-700">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header card */}
      <div className="flex items-center justify-between rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
            <Network className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">研究演化</h3>
            <p className="text-xs text-gray-400">
              {data.refreshed_at
                ? `更新于 ${new Date(data.refreshed_at).toLocaleString("zh-CN")}`
                : "基于论文数据的自动分析"}
            </p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-600 transition hover:bg-gray-50 disabled:opacity-50"
        >
          {refreshing ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <RefreshCw className="h-3 w-3" />
          )}
          {refreshing ? "刷新中..." : "刷新"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-xs text-red-700">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}

      <ResearchTree data={data} />

      {(data.buzz_timeline?.length || 0) > 0 && <BuzzTimeline data={data.buzz_timeline || []} />}
    </div>
  );
}
