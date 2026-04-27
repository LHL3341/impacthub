import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import type {
  UserProfile, Stats, BuzzSnapshot, CitationOverview, AISummary,
  ResearcherPersona, AnnualPoemData,
} from "@/lib/api";
import ShareCard from "./ShareCard";
import PersonaCard from "./PersonaCard";
import AnnualPoemCard from "./AnnualPoemCard";
import { X, Download, Copy, Check, Loader2, Sparkles } from "lucide-react";

type CardMode = "impact" | "persona" | "poem";

interface Props {
  user: UserProfile;
  stats: Stats;
  buzz?: BuzzSnapshot | null;
  citationOverview?: CitationOverview | null;
  aiSummary?: AISummary | null;
  persona?: ResearcherPersona | null;
  poem?: AnnualPoemData | null;
  poemRefreshing?: boolean;
  onGeneratePoem?: () => void;
  onClose: () => void;
}

export default function ShareModal({
  user, stats, buzz, citationOverview, aiSummary, persona,
  poem, poemRefreshing, onGeneratePoem, onClose,
}: Props) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [cardMode, setCardMode] = useState<CardMode>("impact");

  // Per-section toggles for the impact card
  const [showAI, setShowAI] = useState(true);
  const [showBuzz, setShowBuzz] = useState(true);
  const [showCitations, setShowCitations] = useState(true);
  const [showPlatforms, setShowPlatforms] = useState(true);
  const [showCcfMini, setShowCcfMini] = useState(true);
  const [showOssMini, setShowOssMini] = useState(true);
  // Radar dims auto-derived from content toggles (unchecked content → mask matching dim to 0.7)
  const hiddenRadarDims = new Set<string>();
  if (!showBuzz) hiddenRadarDims.add("社区影响");
  if (!showOssMini) {
    hiddenRadarDims.add("代码影响");
    hiddenRadarDims.add("数据贡献");
  }

  const doExport = async (): Promise<string | null> => {
    if (!cardRef.current) return null;
    setError("");
    try {
      return await toPng(cardRef.current, {
        pixelRatio: 3,
        cacheBust: true,
        skipAutoScale: true,
        filter: (node: HTMLElement) => !node.classList?.contains("sr-only"),
      });
    } catch (err) {
      console.error("Export failed:", err);
      setError("生成图片失败，请重试");
      return null;
    }
  };

  const filenameSuffix = cardMode === "persona"
    ? "研究者人格"
    : cardMode === "poem"
    ? `年度诗篇${poem?.year ?? ""}`
    : "影响力卡片";

  const handleDownload = async () => {
    setExporting(true);
    try {
      const dataUrl = await doExport();
      if (!dataUrl) return;
      const link = document.createElement("a");
      link.download = `${user.name || "ImpactHub"}-${filenameSuffix}.png`;
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Download failed:", err);
      setError("导出失败，请重试");
    } finally {
      setExporting(false);
    }
  };

  const handleCopyToClipboard = async () => {
    setExporting(true);
    try {
      const dataUrl = await doExport();
      if (!dataUrl) return;
      const response = await fetch(dataUrl);
      const blob = await response.blob();
      try {
        await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        handleDownload();
      }
    } catch {
      handleDownload();
    } finally {
      setExporting(false);
    }
  };

  // Selective display for impact card
  const filteredAI = showAI ? aiSummary : null;
  const filteredBuzz = showBuzz ? buzz : null;
  const filteredCitations = showCitations ? citationOverview : null;

  const tabs: { key: CardMode; label: string; enabled: boolean }[] = [
    { key: "impact", label: "影响力卡片", enabled: true },
    { key: "persona", label: persona ? `${persona.emoji} 研究者人格` : "研究者人格", enabled: !!persona },
    { key: "poem", label: "年度诗篇", enabled: true },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      <div className="relative mx-4 flex max-h-[90vh] flex-col rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">导出分享卡片</h2>
            <p className="text-xs text-gray-400">选择卡片类型与要展示的要素</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Card mode tabs */}
        <div className="flex gap-1 border-b border-gray-100 px-6">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => t.enabled && setCardMode(t.key)}
              disabled={!t.enabled}
              className={`px-4 py-2 text-xs font-medium transition ${
                cardMode === t.key
                  ? "border-b-2 border-indigo-600 text-indigo-600"
                  : t.enabled
                  ? "text-gray-400 hover:text-gray-600"
                  : "text-gray-300 cursor-not-allowed"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Section toggles (only for impact mode) */}
        {cardMode === "impact" && (
          <div className="border-b border-gray-100 px-6 py-2.5">
            <div className="flex items-center gap-3 flex-wrap">
              <span
                className="text-[11px] text-gray-400 font-medium w-14 shrink-0"
                title="取消勾选会同时隐藏对应的卡片区块 & 把雷达图相关维度替换为中等偏上位置（0.7）"
              >
                展示要素
              </span>
              <Toggle checked={showAI} onChange={setShowAI} label="AI 标签" disabled={!aiSummary} />
              <Toggle checked={showBuzz} onChange={setShowBuzz} label="社区讨论" disabled={!buzz} />
              <Toggle checked={showCitations} onChange={setShowCitations} label="引用分析" disabled={!citationOverview} />
              <Toggle checked={showPlatforms} onChange={setShowPlatforms} label="平台链接" />
              <Toggle checked={showCcfMini} onChange={setShowCcfMini} label="CCF 统计" />
              <Toggle checked={showOssMini} onChange={setShowOssMini} label="开源数据" />
            </div>
          </div>
        )}

        {/* Card preview area */}
        <div className="overflow-auto p-6 min-h-[200px]">
          <div className="flex justify-center">
            {cardMode === "persona" && persona ? (
              <PersonaCard ref={cardRef} persona={persona} user={user} stats={stats} />
            ) : cardMode === "poem" ? (
              poem ? (
                <AnnualPoemCard ref={cardRef} poem={poem} user={user} />
              ) : (
                <PoemEmptyState
                  year={new Date().getUTCFullYear() - 1}
                  refreshing={!!poemRefreshing}
                  onGenerate={onGeneratePoem}
                />
              )
            ) : (
              <ShareCard
                ref={cardRef}
                user={user}
                stats={stats}
                buzz={filteredBuzz}
                citationOverview={filteredCitations}
                aiSummary={filteredAI}
                hiddenRadarDims={hiddenRadarDims}
                hidePlatformLinks={!showPlatforms}
                hideCcfMini={!showCcfMini}
                hideOssMini={!showOssMini}
              />
            )}
          </div>
        </div>

        {error && (
          <div className="mx-6 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
            {error}
          </div>
        )}

        {/* Footer action buttons (hide for poem empty state) */}
        {(cardMode !== "poem" || poem) && (
          <div className="flex items-center gap-3 border-t border-gray-100 px-6 py-4">
            <button
              onClick={handleDownload}
              disabled={exporting}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              保存为图片
            </button>
            <button
              onClick={handleCopyToClipboard}
              disabled={exporting}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-green-500" /> 已复制
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" /> 复制到剪贴板
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Toggle({
  checked, onChange, label, disabled,
}: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <label
      className={`flex items-center gap-1.5 text-xs font-medium ${
        disabled ? "text-gray-300 cursor-not-allowed" : "text-gray-600 cursor-pointer"
      }`}
    >
      <input
        type="checkbox"
        checked={checked && !disabled}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 rounded accent-indigo-600 disabled:cursor-not-allowed"
      />
      {label}
    </label>
  );
}

function PoemEmptyState({
  year, refreshing, onGenerate,
}: { year: number; refreshing: boolean; onGenerate?: () => void }) {
  return (
    <div
      style={{
        width: 460,
        background: "linear-gradient(160deg, #1e1b4b, #4338ca)",
        color: "#fff",
        borderRadius: 20,
        padding: "72px 48px",
        textAlign: "center",
        boxShadow: "0 10px 40px rgba(0,0,0,0.25)",
      }}
    >
      <div style={{ fontSize: 11, letterSpacing: 6, color: "#a5b4fc", opacity: 0.8, marginBottom: 10 }}>
        IMPACTHUB · 年度诗篇
      </div>
      <div style={{ fontSize: 40, fontWeight: 600, letterSpacing: 6 }}>{year}</div>
      <div style={{ marginTop: 24, fontSize: 13, opacity: 0.7, lineHeight: 2 }}>
        基于本年发表、引用增长、项目与讨论
        <br />
        由 AI 为你撰写一首年度研究诗
      </div>
      <button
        onClick={onGenerate}
        disabled={refreshing || !onGenerate}
        className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/15 backdrop-blur-sm px-5 py-2 text-sm font-medium text-white border border-white/20 transition hover:bg-white/25 disabled:opacity-50"
      >
        {refreshing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Sparkles className="h-4 w-4" />
        )}
        {refreshing ? "正在撰写…" : `生成 ${year} 年度诗篇`}
      </button>
    </div>
  );
}
