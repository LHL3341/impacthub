import type { BuzzTimepoint } from "@/lib/api";

const heatColors: Record<string, string> = {
  very_hot: "#ef4444",
  hot: "#f97316",
  medium: "#facc15",
  cold: "#60a5fa",
  very_cold: "#94a3b8",
};

const heatLabels: Record<string, string> = {
  very_hot: "极高",
  hot: "较高",
  medium: "一般",
  cold: "较低",
  very_cold: "极低",
};

interface Props {
  data: BuzzTimepoint[];
}

export default function BuzzTimeline({ data }: Props) {
  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
        网络讨论热度
      </h3>
      <div className="space-y-2">
        {data.map((item, idx) => {
          const color = heatColors[item.heat_label] || heatColors.medium;
          const label = heatLabels[item.heat_label] || "一般";
          return (
            <div
              key={idx}
              className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-sm"
            >
              <span
                className="inline-block h-3 w-3 rounded-full shrink-0"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs font-medium text-gray-700">{item.period_label}</span>
              <span className="text-[10px] font-semibold" style={{ color }}>
                {label}
              </span>
              <div className="flex flex-wrap gap-1 ml-auto">
                {item.topics.slice(0, 3).map((t, ti) => (
                  <span
                    key={ti}
                    className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
