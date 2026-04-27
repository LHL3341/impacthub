import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { motion } from "framer-motion";
import { FileText, Loader2, BookOpen, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";

interface TocEntry {
  id: string;
  depth: 1 | 2 | 3;
  text: string;
}

/** Turn a heading text into a stable anchor id (supports CJK). */
function slugify(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[`~!@#$%^&*()+=\[\]{}|\\;:'",.<>/?]/g, "")
    .replace(/\s+/g, "-");
}

function extractToc(markdown: string): TocEntry[] {
  const toc: TocEntry[] = [];
  let inFence = false;
  for (const line of markdown.split("\n")) {
    if (/^\s*```/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const m = /^(#{1,3})\s+(.+?)\s*$/.exec(line);
    if (!m) continue;
    const depth = m[1].length as 1 | 2 | 3;
    const text = m[2].replace(/[`*_]/g, "").trim();
    if (!text) continue;
    toc.push({ id: slugify(text), depth, text });
  }
  return toc;
}

interface TocNode extends TocEntry {
  children: TocNode[];
}

/** Build a nested tree from a flat toc list. */
function buildTocTree(entries: TocEntry[]): TocNode[] {
  const root: TocNode[] = [];
  const stack: TocNode[] = [];
  for (const e of entries) {
    const node: TocNode = { ...e, children: [] };
    while (stack.length && stack[stack.length - 1].depth >= node.depth) {
      stack.pop();
    }
    if (stack.length === 0) {
      root.push(node);
    } else {
      stack[stack.length - 1].children.push(node);
    }
    stack.push(node);
  }
  return root;
}

interface TocItemProps {
  node: TocNode;
  activeId: string | null;
}

function TocItem({ node, activeId }: TocItemProps) {
  const [open, setOpen] = useState(true);
  const hasChildren = node.children.length > 0;
  const isActive = activeId === node.id;

  const titleClass =
    node.depth === 1
      ? "text-[13px] font-bold text-gray-900"
      : node.depth === 2
      ? "text-[12px] font-semibold text-gray-800"
      : "text-[11px] font-normal text-gray-600";

  return (
    <div>
      <div className="flex items-start gap-1">
        {hasChildren ? (
          <button
            onClick={() => setOpen((v) => !v)}
            className="mt-1 shrink-0 text-gray-400 hover:text-gray-700 transition"
            aria-label={open ? "折叠" : "展开"}
          >
            <ChevronRight
              className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`}
            />
          </button>
        ) : (
          <span className="mt-1 inline-block h-3 w-3 shrink-0" />
        )}
        <a
          href={`#${node.id}`}
          className={`block flex-1 py-0.5 hover:text-indigo-600 transition ${titleClass} ${
            isActive ? "text-indigo-600" : ""
          }`}
        >
          {node.text}
        </a>
      </div>
      {hasChildren && open && (
        <div className="ml-3 mt-0.5 border-l border-gray-100 pl-2 space-y-0.5">
          {node.children.map((child, i) => (
            <TocItem key={i} node={child} activeId={activeId} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DocsPage() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getDoc("system")
      .then((d) => setContent(d.content))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const toc = useMemo(() => extractToc(content), [content]);
  const tocTree = useMemo(() => buildTocTree(toc), [toc]);

  // Track which heading is currently in view for TOC highlight
  const [activeId, setActiveId] = useState<string | null>(null);
  useEffect(() => {
    if (!toc.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length > 0) {
          visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: "-80px 0px -70% 0px" },
    );
    toc.forEach((t) => {
      const el = document.getElementById(t.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [toc]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-gray-400">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        加载文档…
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 text-sm text-red-600">
        加载失败：{error}
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-[95rem] px-4 py-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-5 shadow-sm flex items-center gap-4"
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600">
          <FileText className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">系统文档</h1>
          <p className="text-xs text-gray-500">ImpactHub 数据聚合、页面结构、分析/趣味功能、API 接口全览</p>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        {/* TOC sidebar */}
        <aside className="hidden lg:block">
          <div className="sticky top-20 rounded-xl border border-gray-200 bg-white p-4 shadow-sm text-sm max-h-[calc(100vh-6rem)] overflow-y-auto">
            <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
              <BookOpen className="h-3 w-3" />
              目录
            </div>
            <nav className="space-y-0.5">
              {tocTree.map((node, i) => (
                <TocItem key={i} node={node} activeId={activeId} />
              ))}
            </nav>
          </div>
        </aside>

        {/* Markdown content */}
        <article className="rounded-2xl border border-gray-200 bg-white p-6 sm:p-8 shadow-sm">
          <div className="prose prose-sm max-w-none text-[13px] leading-relaxed
            prose-headings:scroll-mt-20
            prose-h1:text-xl prose-h1:font-bold
            prose-h2:text-base prose-h2:border-b prose-h2:border-gray-100 prose-h2:pb-1 prose-h2:mt-7
            prose-h3:text-sm prose-h3:font-semibold prose-h3:mt-5
            prose-p:text-[13px] prose-li:text-[13px]
            prose-table:text-[11px] prose-table:border
            prose-th:border prose-th:bg-gray-50 prose-th:px-2 prose-th:py-1 prose-th:text-gray-800
            prose-td:border prose-td:px-2 prose-td:py-1 prose-td:text-gray-700
            prose-code:text-[11px] prose-code:text-rose-600 prose-code:bg-rose-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:before:content-none prose-code:after:content-none
            prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-lg prose-pre:px-4 prose-pre:py-3 prose-pre:text-[11.5px] prose-pre:leading-relaxed
            [&_pre_code]:bg-transparent [&_pre_code]:text-slate-100 [&_pre_code]:p-0 [&_pre_code]:text-[11.5px]
            prose-img:my-2 prose-img:rounded-lg prose-img:inline-block prose-img:align-middle
            [&_td_img]:my-0 [&_td_img]:inline-block
            prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                h1: ({ children, ...props }) => {
                  const text = String(children);
                  return <h1 id={slugify(text)} {...props}>{children}</h1>;
                },
                h2: ({ children, ...props }) => {
                  const text = String(children);
                  return <h2 id={slugify(text)} {...props}>{children}</h2>;
                },
                h3: ({ children, ...props }) => {
                  const text = String(children);
                  return <h3 id={slugify(text)} {...props}>{children}</h3>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </article>
      </div>
    </main>
  );
}
