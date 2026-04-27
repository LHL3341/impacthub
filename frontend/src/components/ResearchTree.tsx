import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { TrajectoryData, TreeNode, TrajectoryPaperRef } from "@/lib/api";
import { BookOpen, X } from "lucide-react";

interface Props {
  data: TrajectoryData;
}

const BRANCH_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#f97316",
];

// Layout constants — each node is a fixed-size card; text inside uses line-clamp.
const BRANCH_WIDTH = 240;
const LEAF_WIDTH = 240;
const COLUMN_GAP = 70;
const ROW_GAP = 18;
const BRANCH_HEIGHT = 130;
const LEAF_HEIGHT = 110;
const LEFT_PADDING = 20;
const TOP_PADDING = 20;

interface LayoutNode {
  node: TreeNode;
  x: number;
  y: number;
  width: number;
  height: number;
  level: number;       // 1 = branch, 2 = leaf
  parentCenter?: { x: number; y: number };
  color: string;
  branchIdx: number;   // which top-level branch it belongs to
}

function ccfBadge(rank: string) {
  if (!rank) return null;
  const colors: Record<string, string> = { A: "#dc2626", B: "#f97316", C: "#facc15" };
  return (
    <span
      className="ml-1.5 inline-block rounded px-1.5 py-0.5 text-[9px] font-bold text-white"
      style={{ background: colors[rank] || "#94a3b8" }}
    >
      CCF-{rank}
    </span>
  );
}

export default function ResearchTree({ data }: Props) {
  const [selectedPaper, setSelectedPaper] = useState<TrajectoryPaperRef | null>(null);
  const [hoveredBranch, setHoveredBranch] = useState<number | null>(null);

  // Layout: branches stacked vertically on the left, leaves stacked to their right.
  // Each branch "slot" height = max(BRANCH_HEIGHT, leaves * LEAF_HEIGHT + gaps).
  const { nodes, width, height, trunkX, trunkYStart, trunkYEnd } = useMemo(() => {
    const result: LayoutNode[] = [];
    const root = data?.root;
    if (!root) {
      return { nodes: result, width: 400, height: 200, trunkX: 0, trunkYStart: 0, trunkYEnd: 0 };
    }
    const branches = root.children || [];

    // Compute slot height for each branch
    const branchSlotH = branches.map((b) => {
      const leafCount = (b.children || []).length || 1;
      const leavesH = leafCount * LEAF_HEIGHT + Math.max(0, leafCount - 1) * ROW_GAP;
      return Math.max(BRANCH_HEIGHT, leavesH);
    });

    const totalH = branchSlotH.reduce((a, b) => a + b, 0) + Math.max(0, branches.length - 1) * ROW_GAP;
    const svgHeight = totalH + TOP_PADDING * 2;
    const branchX = LEFT_PADDING + 40;   // leave room for trunk line on left
    const leafX = branchX + BRANCH_WIDTH + COLUMN_GAP;
    const svgWidth = leafX + LEAF_WIDTH + LEFT_PADDING;

    const trunkX = LEFT_PADDING;

    // Place branches + their leaves
    let yCursor = TOP_PADDING;
    branches.forEach((branch, bi) => {
      const color = BRANCH_COLORS[bi % BRANCH_COLORS.length];
      const slotH = branchSlotH[bi];
      const branchCenterY = yCursor + slotH / 2;
      const branchY = branchCenterY - BRANCH_HEIGHT / 2;

      result.push({
        node: branch,
        x: branchX,
        y: branchY,
        width: BRANCH_WIDTH,
        height: BRANCH_HEIGHT,
        level: 1,
        parentCenter: { x: trunkX, y: branchCenterY },
        color,
        branchIdx: bi,
      });

      const branchCenter = { x: branchX + BRANCH_WIDTH, y: branchCenterY };

      const leaves = branch.children || [];
      const leavesH = leaves.length * LEAF_HEIGHT + Math.max(0, leaves.length - 1) * ROW_GAP;
      let leafY = branchCenterY - leavesH / 2;
      leaves.forEach((leaf) => {
        result.push({
          node: leaf,
          x: leafX,
          y: leafY,
          width: LEAF_WIDTH,
          height: LEAF_HEIGHT,
          level: 2,
          parentCenter: branchCenter,
          color,
          branchIdx: bi,
        });
        leafY += LEAF_HEIGHT + ROW_GAP;
      });

      yCursor += slotH + ROW_GAP;
    });

    return {
      nodes: result,
      width: svgWidth,
      height: svgHeight,
      trunkX,
      trunkYStart: TOP_PADDING,
      trunkYEnd: svgHeight - TOP_PADDING,
    };
  }, [data]);

  if (!data?.root) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
        数据格式已更新，请点击「刷新」重新生成演化树。
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Root summary card */}
      {data.root.summary && (
        <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
              研究画像
            </span>
            {data.root.year_range && (
              <span className="text-xs font-mono text-gray-400">{data.root.year_range}</span>
            )}
            {data.root.paper_count ? (
              <span className="text-xs text-gray-500">· {data.root.paper_count} 篇论文</span>
            ) : null}
          </div>
          <p className="text-sm leading-relaxed text-gray-800 whitespace-pre-wrap">
            {data.root.summary}
          </p>
        </div>
      )}

      {/* Branch legend */}
      {(data.root.children?.length || 0) > 0 && (
        <div className="flex flex-wrap gap-2">
          {(data.root.children || []).map((b, i) => {
            const color = BRANCH_COLORS[i % BRANCH_COLORS.length];
            const active = hoveredBranch === i;
            return (
              <button
                key={i}
                onMouseEnter={() => setHoveredBranch(i)}
                onMouseLeave={() => setHoveredBranch(null)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                  active ? "ring-2 ring-offset-1 scale-105" : "hover:scale-105"
                }`}
                style={{
                  backgroundColor: color + "15",
                  color,
                  borderColor: color + "50",
                }}
              >
                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                {b.label}
                {b.year_range && <span className="text-[10px] opacity-60">{b.year_range}</span>}
              </button>
            );
          })}
        </div>
      )}

      {/* Tree SVG */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-gradient-to-br from-slate-50 to-white p-4 shadow-sm">
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Trunk line (left vertical) */}
          <motion.line
            x1={trunkX}
            y1={trunkYStart}
            x2={trunkX}
            y2={trunkYEnd}
            stroke="rgba(100,116,139,0.25)"
            strokeWidth={2}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
          />

          {/* Connector paths */}
          {nodes.map((n, i) => {
            if (!n.parentCenter) return null;
            const startX = n.parentCenter.x;
            const startY = n.parentCenter.y;
            const endX = n.x;
            const endY = n.y + n.height / 2;
            const midX = (startX + endX) / 2;
            const path = `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
            const dimmed = hoveredBranch !== null && n.branchIdx !== hoveredBranch;
            return (
              <motion.path
                key={`edge-${i}`}
                d={path}
                stroke={n.color}
                strokeWidth={2}
                fill="none"
                opacity={dimmed ? 0.12 : 0.55}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: 0.2 + n.level * 0.2, duration: 0.7, ease: "easeOut" }}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((n, i) => {
            const dimmed = hoveredBranch !== null && n.branchIdx !== hoveredBranch;
            return (
              <motion.g
                key={`node-${i}`}
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: dimmed ? 0.35 : 1, scale: 1 }}
                transition={{ delay: 0.2 + n.level * 0.2 + (i * 0.02), duration: 0.35, ease: "easeOut" }}
              >
                <foreignObject x={n.x} y={n.y} width={n.width} height={n.height}>
                  <NodeCard node={n.node} level={n.level} color={n.color} />
                </foreignObject>
              </motion.g>
            );
          })}
        </svg>
      </div>

      {/* Paper detail popover (kept for compatibility; currently tree has no paper_ids) */}
      <AnimatePresence>
        {selectedPaper && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2">
                <BookOpen className="mt-0.5 h-4 w-4 text-indigo-600 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{selectedPaper.title}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {selectedPaper.venue || "未知期刊"} &middot; {selectedPaper.year}
                    {ccfBadge(selectedPaper.ccf_rank)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">引用: {selectedPaper.citation_count}</p>
                </div>
              </div>
              <button onClick={() => setSelectedPaper(null)} className="text-gray-400 hover:text-gray-700">
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface NodeCardProps {
  node: TreeNode;
  level: number;
  color: string;
}

function NodeCard({ node, level, color }: NodeCardProps) {
  const isBranch = level === 1;
  // line-clamp to keep card height stable regardless of LLM output length
  // branch: 3 lines (bigger card), leaf: 3 lines (smaller card, less meta)
  const clampClass = isBranch ? "line-clamp-3" : "line-clamp-3";

  return (
    <div
      className="rounded-xl border p-3 shadow-sm h-full overflow-hidden"
      style={{
        background: "white",
        borderColor: isBranch ? color + "80" : "#e5e7eb",
        borderLeftWidth: isBranch ? 4 : 2,
        borderLeftColor: color,
      }}
      title={node.summary}
    >
      <div className="flex items-start gap-1.5">
        <span
          className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        <div className="min-w-0 flex-1">
          <div className={`${isBranch ? "text-sm font-semibold" : "text-[13px] font-medium"} text-gray-900 leading-snug line-clamp-1`}>
            {node.label}
          </div>
          {(node.year_range || node.paper_count) ? (
            <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-gray-400 font-mono">
              {node.year_range && <span>{node.year_range}</span>}
              {node.paper_count ? <span>· {node.paper_count}篇</span> : null}
            </div>
          ) : null}
          {node.summary && (
            <div className={`mt-1 text-[11px] leading-relaxed text-gray-600 ${clampClass}`}>
              {node.summary}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
