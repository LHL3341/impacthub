# ImpactHub 系统总览文档

> 最后更新：2026-04-22
> 项目根：`/mnt/dhwfile/raise/user/linhonglin/impacthub`
> 后端端口 8001 (uvicorn) · 前端端口 5173 (vite dev) / 19487 (serve.py 代理 dist)

---

## 0. 定位一句话

把一个研究者在 **Semantic Scholar / GitHub / Hugging Face** 的信息聚合成统一的"科研画像"，再叠加 **引用分析、增量追踪、社区讨论、研究演化、人格分类、职业经历、年度诗篇** 等多层分析 + 趣味功能。

---

## 1. 数据聚合层

### 1.1 外部来源与字段

| 来源 | 通过 | 抓到的字段 |
|------|------|----------|
| Semantic Scholar `/author/{id}` | `scholar_service.fetch_papers_for_user` | 论文：title / year / venue / citation_count / authors / externalIds |
| DBLP | `dblp_service` | 补充 CCF 分类用的 venue key |
| GitHub `/users/{login}` + search | `github_service` | repo 列表、stars、forks、language、created_at；头像、bio |
| Hugging Face `/api/users/{login}` | `hf_service` | 模型 / 数据集列表、下载数、like 数 |
| Perplexity / gpt-5 web search | `buzz_service` / `career_service` / `enrich_honors` | 网络讨论、职业经历、荣誉 |

### 1.2 自动发现

`discover_service.discover_from_scholar`：只给 Scholar ID，系统自动尝试：
1. 从 SS 作者页拿 name + affiliations
2. 以姓名在 GitHub user search 找账号（需要姓名至少两个 token 匹配），命中后拉 avatar/bio
3. 同样方式找 HuggingFace 账号

### 1.3 数据模型（SQLite via aiosqlite）

位于 `backend/app/models.py`：

| 表 | 作用 | 主要字段 |
|----|------|----------|
| `users` | 研究者主体 | scholar_id, github_username, hf_username, homepage, bio, avatar_url, **honor_tags**, **research_direction** (llm/cv/vlm/...), **seed_tier** (senior/mid/rising), visible |
| `papers` | 论文 | title, year, venue, citation_count, authors_json, ccf_rank, ccf_category, dblp_key |
| `github_repos` | GitHub 仓库 | repo_name, stars, forks, language, created_at_remote, is_pinned |
| `hf_items` | HF 模型/数据集 | item_id, item_type, downloads, likes |
| `milestones` | 里程碑 | metric_type (citations/stars/downloads/hf_likes), threshold, achieved_value, achieved_at |
| `notable_citations` | 引用者 | author_name, author_h_index, citing_paper_*, contexts, **honor_tags** |
| `citation_analyses` | 每篇论文的引用统计 | total_citing_papers, influential_count, top_scholar_count, notable_scholar_count |
| `buzz_snapshots` | 网络讨论快照 | heat_label, summary (Markdown), sources, topics |
| `ai_summaries` | AI 画像 | summary, tags |
| `data_snapshots` | 每日指标快照 | metric_type, value, snapshot_date |
| `research_trajectories` | 研究演化树 | trajectory_json (root + children) |
| `capability_profiles` | 能力画像分类 | type (originator/early_adopter/extender/follower), score, evidences, rationale |
| `researcher_personas` | 人格分类 | persona_code, dimension_scores, raw_metrics |
| `career_histories` | 职业经历 | timeline_json (教育 + 职位), current, sources |
| `annual_poems` | 年度诗篇 | year (复合唯一), content_json (title/verses/highlights/theme) |

### 1.4 刷新链路

- **按需全量刷新**：用户点 "刷新" → `POST /api/refresh/{id}` → `_full_refresh` 后台任务：
  `scholar_service → dblp_service → ccf_recompute → github_service → hf_service → milestone_service → snapshot_service → persona_service`
- **周期自动刷新**：`app.tasks.scheduler` 每 6 小时调用所有可见用户的 `_full_refresh`
- **按需功能刷新**：buzz / ai_summary / trajectory / career / annual_poem / persona 各自独立的 `POST /api/<x>/{id}/refresh` 端点（前端手动点"生成"按钮触发）

---

## 2. 前端页面结构

### 2.1 路由

| 路径 | 页面 | 文件 |
|------|------|------|
| `/` | 引导页（扫码输入 Scholar ID） | `SetupPage.tsx` |
| `/profile/:id` | 研究者主页 | `ProfilePage.tsx` |
| `/milestones/:id` | 里程碑专页 | `MilestonePage.tsx` |
| `/users` | 用户列表 | `UsersPage.tsx` |
| `/leaderboard` | 排行榜 | `LeaderboardPage.tsx` |

TopBar 有「排行榜」「用户列表」两个导航入口（激活态浅蓝 pill）。

### 2.2 ProfilePage 结构（自上而下）

1. **HeroSection**
   - 头像 + 姓名 + bio + 平台链接
   - 人格徽章 (PersonaBadge)
   - AI 总结一句话 + 趣味标签 (生成按钮)
   - 4 个主指标 big nums（总引用 / GitHub Stars / 总下载 / h-index）有 count-up 动画

2. **CareerCard**（职业经历）
   - Header 卡：标题 + 当前职位小标签 + 刷新按钮
   - 时间线卡：垂直 dendrogram，教育=蓝点 / 任职=绿点，每行 year range + badge + role @ institution + advisor
   - 进度条卡：生成过程中显示"搜索来源 / 核实机构 / 整理时间线"阶段
   - 来源卡：2-8 个外部 URL 标签

3. **Overview 栏** (lg:grid-cols-3)
   - 左 1 列：RadarChart（6 维：学术深度 / 代码影响 / 数据贡献 / 产出广度 / h-index / 社区影响）
   - 右 2 列：StatsOverview（CCF 统计 + 引用分析进度）

4. **主 Tab 栏**（重构后 4 个顶级组）
   
   | 顶级 | 子 tab |
   |------|------|
   | **成果** | 学术论文 / 代码仓库 / 模型与数据集 / 时间轴 |
   | **影响** | 引用分析 / 增量追踪 / 社区讨论 |
   | **演化** | （研究演化树，无子 tab） |
   | **导出** | （智能导出，无子 tab） |

5. **ShareModal**（点"分享"按钮触发）
   - 3 种卡片切换：**影响力卡片** / **研究者人格** / **年度诗篇**
   - 影响力卡片模式有 3 个要素开关：AI 标签 / 社区讨论 / 引用分析
   - 下载 PNG / 复制到剪贴板

---

## 3. 分析功能

### 3.1 引用分析

**流程**
1. 对用户的每篇论文调用 Semantic Scholar `/paper/{id}/citations`
2. 对每位 citing author 再拉一次作者信息拿到 h-index / citation_count
3. 按 h-index 分级并写入 `notable_citations` 表

**分级阈值**
- `top` scholar：h-index ≥ 50
- `notable` scholar：h-index ≥ 25 且 < 50
- `influential`：SS 自身打的旗标（是否对该篇论文产生 influential citation）

**产物**
- `citation_analyses` 表：每篇论文的聚合统计（总 citing_papers / influential / top_scholar_count / notable_scholar_count）
- `notable_citations` 表：按作者展开的明细，含 citing_paper 标题/年份/venue + contexts（citation 摘录片段）

**可选的荣誉识别**（`POST /api/citations/{id}/enrich-honors`）
- 分批（15 人一批）把 citer 名字喂 LLM + web_search
- 核实以下 8 种荣誉：IEEE Fellow / ACM Fellow / ACL Fellow / 中科院院士 / 工程院院士 / 其他国家院士 / 图灵奖 / 诺贝尔奖
- 结果写入 `notable_citations.honor_tags`，前端可在引用者名片显示徽章

**前端**
- `CitationAnalysisView.tsx`：Top scholars / Notable scholars 分页 tab，每人卡片显示 h-index、引用我的论文标题、荣誉徽章

### 3.2 增量追踪

**记录的指标**（每日快照）
| metric_type | 含义 |
|-------------|------|
| `total_citations` | 全部论文引用合计 |
| `h_index` | h-index |
| `paper_count` | 去重后论文数 |
| `ccf_a_count` / `ccf_b_count` | CCF-A / B 数量 |
| `total_stars` | GitHub 全部仓库 stars 合计 |
| `total_forks` | Forks 合计 |
| `total_downloads` | HF 模型总下载 |
| `total_hf_likes` | HF 项目 like 合计 |

**前端 GrowthDashboard**
- 时间窗口：7 / 30 / 90 天三档
- Y 轴模式：
  - **自动**（默认）— 缩放到数据范围 `[min-10%, max+10%]`，让小变化也能看见
  - **从 0** — 原始行为，保留绝对值感
  - **增量** — 每日差分（v[i] − v[i-1]）
- 顶部 4-8 个 DeltaCard 显示"昨日 vs 今日"变化
- 线条颜色按指标区分（citations 蓝 / stars 琥珀 / downloads 翠绿 / h_index 青 / ccf_a 红 / ...）

### 3.3 研究演化树

**上下文（喂给 gpt-5 的信息，1M context 友好）**
- `User` 身份 + bio + honor_tags + 4 个外链
- 推断出的职业线索：发表年限、年度发表节奏（`2015:3 2016:5 ...`）、第一作者比例、主要合作者 top 8、各 3 年窗口的主要 venue 分布、开源活跃年份
- **论文**：最多 400 篇（按引用排序 + 年份保留时间分布），含 title / year / venue / CCF / 引用 / 前 3 作者
- **Repos**：最多 50（含创建年份 + 描述片段）
- **HF items**：最多 30
- **引用者 top 15**（带 h-index + honor_tags）——体现影响力辐射
- **Buzz summary 前 2000 字**（外部视角）
- 已有的 AI Summary + tags（作为 hint，LLM 可复用或反驳）

**输出 JSON 结构**
```json
{
  "root": {
    "label": "研究者姓名",
    "summary": "3-4 句整体画像",
    "year_range": "2013-2026",
    "paper_count": 87,
    "children": [
      {
        "label": "博士期：NLP 基础",
        "summary": "基于发表节奏推断，此阶段以第一作者身份攻坚...",
        "year_range": "2013-2017",
        "paper_count": 22,
        "children": [
          {"label": "词向量表示", "summary": "...", "year_range": "2013-2015"},
          {"label": "依存分析", "summary": "...", "year_range": "2015-2017"}
        ]
      },
      { "label": "独立研究期：多模态", "...": "..." }
    ]
  },
  "papers_index": { "123": {...}, ... }
}
```

**约束**
- `root.children` 3-6 个（主要方向 × 职业阶段复合命名）
- 每个 child 下 2-4 个子主题
- 方向有明显转变时 summary 带衔接句（"在前一阶段 XX 基础上，本阶段转向 YY"）

**前端 `ResearchTree.tsx`**
- 左侧根画像卡（完整 `root.summary` 不截断）
- 下方分支徽章 legend（hover 高亮单一分支）
- SVG 树：左侧竖直树干 → 分支向右伸 → 叶子再向右
- Framer Motion 动画：树干生长 → 分支延伸 → 节点 spring 弹入
- 叶子节点固定高度 + `line-clamp-3` 防止重叠

### 3.4 网络讨论分析

**搜索范围**
- Twitter/X、Reddit (r/MachineLearning / r/LocalLLaMA 等)、Hacker News
- Hugging Face 社区、GitHub Issues/Discussions、LessWrong、EA Forum
- YouTube 评论、播客、Bilibili、知乎、微信公众号
- arXiv 论文页、Semantic Scholar、Papers with Code、OpenReview
- 技术博客 / Substack / Medium、实验室官网、个人主页

**输出 Markdown 结构**（7 节）
1. 一句话结论（近期热度来源、最活跃平台、最受关注作品）
2. 研究对象背景（领域、机构、被提及原因）
3. 主要讨论主题（3-8 个，每个含：内容 / 受关注原因 / 活跃平台 / 代表作品 / 倾向 / 来源）
4. 平台活跃度对比（表格）
5. 最受关注的作品/论文/项目/事件
6. 时间脉络（引爆 → 扩散 → 降温/持续）
7. 当前热度标签：`【当前热度】极高 / 较高 / 一般 / 较低 / 极低`

**热度标签对应 `heat_label`**
| 中文 | `heat_label` | 前端配色 |
|------|--------------|---------|
| 极高 | `very_hot` | 红色 |
| 较高 | `hot` | 橙色 |
| 一般 | `medium` | 琥珀 |
| 较低 | `cold` | 青蓝 |
| 极低 | `very_cold` | 灰 |

**产物**
- `BuzzSnapshot.summary`：完整 Markdown（前端用 `ReactMarkdown` 渲染，citations 以 `[1][2]` 注入上标链接）
- `BuzzSnapshot.topics`：抽取的 3-8 个讨论话题关键词（注入到 trajectory / ai_summary 作 hint）
- `BuzzSnapshot.sources`：verified URL 列表（来自 Responses API 的 `url_citation` annotations）

### 3.5 排行榜

**三种榜单类型**
| type | 筛选逻辑 | 前端 tab |
|------|---------|---------|
| `total` | 全体可见用户 | 总榜 |
| `young` | 首篇论文年份 ≥ 当前年 − 10 | 年轻学者 |
| `direction` | `research_direction` == 指定值 | LLM / CV / VLM / Systems / Theory / RL |

**六个方向**
| code | 含义 |
|------|------|
| `llm` | LLM / NLP |
| `cv` | Computer Vision |
| `vlm` | Vision-Language / Multimodal / Generative |
| `systems` | ML Systems / Infrastructure |
| `theory` | ML Theory |
| `rl` | Reinforcement Learning |

**四种排序指标**
| metric | 字段来源 |
|--------|----------|
| `h_index` | 按去重后论文 citation 序列算 |
| `total_citations` | 全部论文引用之和 |
| `ccf_a_count` | CCF-A 论文篇数 |
| `total_stars` | GitHub 全部仓库 stars 之和 |

**展示规则**
- **前 10000 名**：显示精确 rank（奖牌色：第 1 金、第 2 银、第 3 铜）
- **10000 名之后**：隐藏 rank，只显示 `前 X%` 百分位
- 每行卡片：头像 / 姓名 / 方向徽章 / tier (senior/mid/rising) / 荣誉徽章前 2 个（如 "Turing Award"）/ 关键指标（h-index / 引用 / 论文 / CCF-A）/ 主排序指标大字
- 点击跳转到该学者的 profile 页

**目标用户高亮**（未使用但已支持）
`target_user_id` 参数返回 `{rank, percentile, metric_value}`，可用于"你的排名是第 X 名"提示。

### 3.6 职业经历

**输入**：仅身份（姓名 / bio / scholar_id / github_username / hf_username / homepage）
**方法**：gpt-5 + `web_search_preview`，优先查个人主页 / Google Scholar / LinkedIn / Wikipedia / DBLP 履历页

**输出 JSON**
```json
{
  "timeline": [
    {
      "start_year": 1988,
      "end_year": 1991,
      "type": "education",
      "role": "Ph.D. in Computer Science",
      "institution": "McGill University",
      "advisor": "Renato De Mori",
      "note": ""
    },
    {
      "start_year": 1991,
      "end_year": 1992,
      "type": "position",
      "role": "Postdoctoral Fellow",
      "institution": "MIT",
      "advisor": "",
      "note": ""
    },
    {
      "start_year": 2002,
      "end_year": null,
      "type": "position",
      "role": "Full Professor",
      "institution": "Université de Montréal",
      "advisor": "",
      "note": ""
    }
  ],
  "current": "Full Professor at Université de Montréal; Founder at Mila",
  "sources": [
    {"title": "Personal homepage", "url": "https://yoshuabengio.org/"},
    {"title": "Wikipedia", "url": "https://..."}
  ]
}
```

**前端 `CareerCard.tsx`**（按 BuzzCard 风格分段卡片）
- Header 卡：图标 + 标题 + 当前职位小标签 + 刷新按钮
- Progress 卡（生成中）：「搜索来源 / 核实机构 / 整理时间线」分阶段
- Timeline 卡：竖直 dendrogram，教育蓝点 / 任职绿点，含 year range + Education/Position badge + role @ institution + 导师 + note
- Sources 卡：2-8 个可点的来源链接

**展示位置**：HeroSection 下方（个人身份区之后、tabs 之前）

### 3.7 能力画像（开创者 vs 追随者）

除了排名，系统还会给出**在知识网络中的位置**画像，从 4 种类型中选一种：

| 类型 | 中文 | Emoji | 特征 |
|------|------|-------|------|
| `originator` | 开创者 | 🌱 | 论文发表后 5+ 年仍在被引用，被多个独立实验室反复引用，像"地基" |
| `early_adopter` | 早期采用者 | ⚡ | 刚发表就大量引用，2-3 年高峰，是方向起步时的里程碑贡献者 |
| `extender` | 扩展者 | 🛠️ | 基于已有经典做延伸/改进/应用，引用中等但集中 |
| `follower` | 跟随者 | 🚶 | 主流方向研究，但没有成为关键里程碑 |

**数据来源**
- Top 10 高被引论文的引用时序（来自 `notable_citations` 表）
- 每篇的年度引用柱状图 + 前 5 位高 h-index 引用者 + 引用 context 片段
- 计算信号：
  - `late_citations` = 论文发表后 ≥5 年仍收到的引用（长尾信号 → originator）
  - `immediate_citations` = 发表 2 年内收到的引用（即时峰值 → early_adopter）

**判断方式**：LLM 综合上述数据打分，输出 `type` + `score` (0-1) + `rationale` + 3-5 条具体 `evidences`（每条引用具体论文标题和数字）

**产物**（`capability_profiles` 表）
- `type` / `score` / `rationale` / `evidences`（JSON 列表）
- API：`GET /api/capability/{id}` + `POST /api/capability/{id}/refresh`

---

## 4. 趣味功能

### 4.1 研究者人格 — Meme 风格

**分类思路**（LLM 决策）：
1. 本地算 4 个维度的连续分数（0-1），作为**定量提示 + UI 进度条**
2. 把 4 维度分数 + 核心指标 + 代表论文 / repos，连同 12 种人格定义一起喂给 LLM
3. LLM 综合画像，从 12 种里**挑一个最贴合**的 meme 人格代号
4. 入库：`persona_code`（如 `GOAT` / `PI`）+ `dimension_scores` + `raw_metrics`（含 LLM 给的 `llm_reason`）

#### 四个维度（LLM 参考 + UI 进度条）

| 维度 | 分数公式 | 语义 |
|------|---------|------|
| **Output** | `min(1, 篇均引用/50)×0.7 + (1 − min(1, 论文数/100))×0.3` | 0 = 多产量，1 = 深耕质 |
| **Ecosystem** | `0.4×min(1,(#repos+#hf)/8) + 0.3×min(1,stars/1000) + 0.3×min(1,downloads/10000)` | 0 = 纯理论，1 = 重建设 |
| **Seniority** | `0.6×min(1, h/30) + 0.4×min(1, 学术年龄/12)` | 0 = 新锐，1 = 资深 |
| **Collaboration** | `(平均作者数 − 1) / 6`，clamp [0,1] | 0 = 独行，1 = 协作 |

LLM 会参考这 4 个分数，但**最终决定权在 LLM**——比如一个刚起步但 h-index 已破 20 的人，LLM 可能判为 `HYPE` 而不是 `WOLF`。

#### 为什么改成 LLM 决策

- 纯硬阈值（0.5 cut）会让边界附近的人被错误归类（某维度 0.49 vs 0.51 差异巨大）
- LLM 能综合**代表论文题材、开源项目爆款 vs 长尾、合作者网络**等细节，比规则更灵活
- 有 `llm_reason` 字段保存判定理由，方便 debug / 展示

#### 12 种人格一览

##### 形象画廊（AI 生成的 MBTI 风格插画）

<table>
<tr>
<td align="center"><img src="/static/personas/GOAT.png" width="120" /><br/><b>GOAT</b><br/>老神仙 🏔️</td>
<td align="center"><img src="/static/personas/PI.png" width="120" /><br/><b>PI</b><br/>组里老大 👑</td>
<td align="center"><img src="/static/personas/WOLF.png" width="120" /><br/><b>WOLF</b><br/>独狼 🐺</td>
<td align="center"><img src="/static/personas/VIRAL.png" width="120" /><br/><b>VIRAL</b><br/>开源新贵 🚀</td>
</tr>
<tr>
<td align="center"><img src="/static/personas/PROOF.png" width="120" /><br/><b>PROOF</b><br/>理论大神 🧠</td>
<td align="center"><img src="/static/personas/SENSEI.png" width="120" /><br/><b>SENSEI</b><br/>学派掌门 📜</td>
<td align="center"><img src="/static/personas/MONK.png" width="120" /><br/><b>MONK</b><br/>苦行僧 🪷</td>
<td align="center"><img src="/static/personas/HYPE.png" width="120" /><br/><b>HYPE</b><br/>学术新贵 ✨</td>
</tr>
<tr>
<td align="center"><img src="/static/personas/NINJA.png" width="120" /><br/><b>NINJA</b><br/>一人成军 ⚡</td>
<td align="center"><img src="/static/personas/BDFL.png" width="120" /><br/><b>BDFL</b><br/>造轮大师 🌍</td>
<td align="center"><img src="/static/personas/JUAN.png" width="120" /><br/><b>JUAN</b><br/>卷王 🔥</td>
<td align="center"><img src="/static/personas/KPI.png" width="120" /><br/><b>KPI</b><br/>论文工厂 🏭</td>
</tr>
</table>

##### 代号 + 描述

每个人格有一个 **meme 代号**（CS/学术圈内梗 + 网络流行语双关）：

| 梗代号 | 名字 | Emoji | 一句话 | Traits |
|-------|------|-------|--------|--------|
| **GOAT** 🏔️ | 老神仙 | 🏔️ | 嘴上要退休，手上还在发 Nature | 篇篇封神 / 代码自己敲 / 不带学生 / 至今仍在一线 |
| **PI** 👑 | 组里老大 | 👑 | 同时带 8 个博士生还能发顶会 | 实打实的 PI / 合作者成群 / 学生晋升机 / 论文质+量并存 |
| **WOLF** 🐺 | 独狼 | 🐺 | 一个人 = 一整个实验室 | solo 之王 / 全栈全能 / 不屑合作 / 潜力巨大 |
| **VIRAL** 🚀 | 开源新贵 | 🚀 | GitHub star 长得比头发快 | 一年爆款 repo / GitHub 简历者 / 协作型 / 涨粉中 |
| **PROOF** 🧠 | 理论大神 | 🧠 | 20 年 30 篇，每篇引用破千 | 黑板写证明 / 篇篇教科书 / 不搞 GitHub / 被模仿无数 |
| **SENSEI** 📜 | 学派掌门 | 📜 | 桃李满天下，孙辈都带出来了 | 开山立派 / 三代桃李 / 学界话事人 / 代表教材编者 |
| **MONK** 🪷 | 苦行僧 | 🪷 | 一年憋一篇，审稿人看完跪了 | 一年一作 / reviewer 敬畏 / 不混圈子 / 纯粹热爱 |
| **HYPE** ✨ | 学术新贵 | ✨ | Faculty Market 上的抢手货 | CV 漂亮 / 合作圈硬核 / 潜力爆棚 / 大佬眼中的明日之星 |
| **NINJA** ⚡ | 一人成军 | ⚡ | 代码实验论文回复全是一个人 | 十项全能 / 深夜 commit / 不依赖学生 / 产量爆表 |
| **BDFL** 🌍 | 造轮大师 | 🌍 | 论文和 repo 双飞，社区围着你转 | 10k star 项目 / issue 处理王 / 社区 BDFL / 顶会常客 |
| **JUAN** 🔥 | 卷王 | 🔥 | 一个月三篇 arXiv，导师看了都心疼 | arXiv 钉子户 / 睡眠不足 / Cursor 100 tabs / 导师都追不上 |
| **KPI** 🏭 | 论文工厂 | 🏭 | 量大管饱，审稿人看名字就知道 | 量大管饱 / 题材漂移 / 从不开源 / 审稿缘分深 |

#### 梗代号出处

| 代号 | 英文全称 / 梗出处 |
|-----|-----------------|
| **GOAT** | Greatest Of All Time — 体育 / Twitter 经典老梗 |
| **PI** | Principal Investigator — 学术内行梗 |
| **WOLF** | Lone Wolf — 独狼 |
| **VIRAL** | 推特爆款 / 开源出圈 |
| **PROOF** | 直接说"证明"，理论家的看家本领 |
| **SENSEI** | 日漫祖师爷梗 |
| **MONK** | 苦行僧的直译 |
| **HYPE** | Faculty market 上被 N 个 offer 抢 |
| **NINJA** | Code ninja — 深夜悄悄 commit 的独行高手 |
| **BDFL** | Benevolent Dictator For Life — Guido van Rossum / Linus 经典梗 |
| **JUAN** | "卷" 的拼音，AI 推特圈梗 |
| **KPI** | Key Performance Indicator — 为绩效指标发论文，国内科研圈本土梗 |


#### 触发 & 展示
- `POST /api/persona/{id}/refresh` 重算（纯本地计算，毫秒级）
- 每次用户全量刷新时也自动重算
- HeroSection 顶部的「研究者人格徽章」显示 emoji + 名称
- 分享卡 ShareModal 的「研究者人格」tab 导出独立渐变 PNG

### 4.2 AI 个人画像

**输入（漏斗顶层已汇总的产物）**
- `Trajectory.root.summary` + 每个 branch 的 label / year_range / summary 一句话
- `User.honor_tags`（若已识别）
- 原始指标（h-index / 总引用 / CCF 数 / notable citers 数）
- 代表论文 top 8 + top 5 repos + top 5 HF
- `BuzzSnapshot.heat_label` + `topics`

**输出格式**
```json
{
  "summary": "深耕多模态与大模型的资深研究者，以 CLIP 系工作塑造了视觉-语言领域的主流范式。",
  "tags": ["开源狂魔", "引用收割机", "Benchmark 制造者", "CCF-A 常客"]
}
```

**头衔标签风格**：要绰号感而非研究方向
- ✅ 好：开源狂魔、引用收割机、Benchmark 制造者、数据炼金术师、多模态探索家、Star 破万俱乐部、CCF-A 常客、顶会收割机
- ❌ 坏：数据驱动、数学推理、合成检测（这是研究方向，不是头衔）

### 4.3 年度诗篇

**数据聚合**（`_gather_year_stats`）
- 本年发表论文数 + 列表（去重后）
- 年度代表作（当年论文中引用最高那篇）
- 本年涉及的 venue 集合（最多 6 个）
- 本年引用增量（从 `DataSnapshot` 取 `total_citations` 年初 vs 年末差）
- 本年新建 GitHub 仓库数 + 最火那个
- 本年跨越的 Milestones（citations / stars 等跨阈值事件）
- 当前 Buzz topics（作为风味来源）

**LLM 输出约束**
- 5 行现代中文短诗，每行 12-22 字
- 把真实数据融进意象（例："十二篇论文如落英"）
- 首末行用主题色强调（点题 + 留白）
- 3-4 个数据亮点（label 2-4 字 + value 醒目数字）
- 主题色从 `indigo` / `amber` / `emerald` / `rose` 四选一

**示例输出**
```json
{
  "title": "风起长夜",
  "verses": [
    "冬至前落笔，十二篇论文如雪",
    "多模态的冰原上第一次有人点火",
    "八月 CLIP 的星光越过引用的山脊",
    "GitHub 的潮汐带着五千星辰上岸",
    "明年再赴一场未写完的春天"
  ],
  "highlights": [
    {"label": "论文", "value": "12 篇"},
    {"label": "引用增长", "value": "+8,231"},
    {"label": "Stars", "value": "5,420"},
    {"label": "代表作", "value": "多模态对齐"}
  ],
  "theme": "indigo"
}
```

**渲染**
- `AnnualPoemCard.tsx`：深色渐变底 + 大年份水印 + 5 行居中诗句 + 底部亮点环 + 研究者印章
- 仅在 ShareModal 的「年度诗篇」tab 显示，可导出 PNG
- 默认生成**上一年**（避免今年还没过完）；支持 `?year=2024` 覆盖

### 4.4 里程碑
- 自动跨阈值时记录：citations 10/50/100/200/500/1000/5000, stars 10/50/…/10k, downloads 100/1k/…/100k, hf_likes 10/…/1000

### 4.5 智能导出
- 按 year / CCF rank / min_citations / first_author 过滤论文
- 多种场景模板：NSFC / 长江 / 万人 / 海外优青 的"研究基础"自动生成
- 可输出 Markdown / BibTeX / JSON

---

## 5. LLM 使用一览

| 用途 | 服务 | 接口 | 联网 | 模型 | max_tokens |
|------|------|------|------|------|-----------|
| 社区讨论 | `buzz_service` | Responses API + `web_search_preview` | ✅ | gpt-5（fallback: gpt-5-mini） | 16000 |
| AI 画像 | `ai_summary_service` | Responses API / Chat Completions | ❌ | gpt-5 / gpt-5-mini | 2000 |
| 引用者荣誉 | `honor_service` | Responses API + `web_search_preview` | ✅ | gpt-5 / gpt-5-mini | 4000 |
| 研究演化树 | `trajectory_service` | Responses API / Chat Completions | ❌ | gpt-5 / gpt-5-mini | 8000 |
| 职业经历 | `career_service` | Responses API + `web_search_preview` | ✅ | gpt-5 / gpt-5-mini | 16000 |
| 年度诗篇 | `annual_poem_service` | Responses API / Chat Completions | ❌ | gpt-5 / gpt-5-mini | 4000 |
| 学者荣誉批量 | `scripts/enrich_honors.py` | Responses API + `web_search_preview` | ✅ | gpt-5 / gpt-5-mini | 16000 |
| 研究人格 | `persona_service` | Responses API / Chat Completions | ❌ | gpt-5 / gpt-5-mini | 4000 |
| 能力画像 | `capability_service` | Responses API / Chat Completions | ❌ | gpt-5 / gpt-5-mini | 6000 |

**漏斗依赖**：`buzz (联网收集) → trajectory (库内汇总) → ai_summary (画像)`。AI Summary 现在首要消费 Trajectory 的 root.summary + branch summaries，原始指标次之。

**环境变量**（`backend/.env`）：
- `LLM_API_BASE` / `LLM_API_KEY`：OpenAI-compatible 端点
- `LLM_BUZZ_MODEL`：主模型，默认 `gpt-5`
- `LLM_FALLBACK_MODEL`：回退小模型，默认 `gpt-5-mini`
- `OUTBOUND_PROXY`：集群内访问外网用
- `GITHUB_TOKEN`：GitHub API 高 rate limit

---

## 6. 后端 API 全清单

所有路由都挂在 `/api` 前缀下，在 `backend/app/main.py` 注册。

### 6.1 Profile / Data
| Method | Path | 功能 |
|--------|------|------|
| GET | `/profile/{id}` | 完整档案（含 papers/repos/hf） |
| GET | `/profile/{id}/stats` | 聚合指标（总引用 / h-index / CCF 等） |
| GET | `/profile/{id}/timeline` | 按时间排序的产出列表 |
| POST | `/profile` | 创建 profile（auto-discover 触发 full refresh） |
| PATCH | `/profile/{id}` | 更新 scholar_id / github / hf / homepage 等 |
| POST | `/refresh/{id}` | 触发全量刷新 |
| GET | `/profiles` | 列出所有用户 |
| GET | `/scholar-search?q=` | 代理 Semantic Scholar 作者搜索 |
| POST | `/profile/{id}/repos` / `/hf-items` | 手动添加 repo/HF |
| DELETE | 上面的 id | 删除 |

### 6.2 分析类
| Method | Path | 功能 |
|--------|------|------|
| GET | `/citations/{id}` | 引用概览 + top/notable scholars |
| GET | `/citations/{id}/papers?offset&limit` | 论文级别分析分页 |
| GET | `/citations/{id}/scholars?level=top&offset&limit` | 引用学者分页 |
| POST | `/citations/{id}/analyze` | 触发引用分析 |
| POST | `/citations/{id}/enrich-honors` | 引用者荣誉识别 |
| GET | `/growth/{id}?days=30` | 增量曲线 |
| GET | `/milestones/{id}` | 里程碑列表 |
| GET | `/stats` | 站点统计 |

### 6.3 画像 / 趣味功能
| Method | Path | 功能 |
|--------|------|------|
| GET `POST` | `/buzz/{id}` `/buzz/{id}/refresh` | 网络讨论快照 / 刷新 |
| GET `POST` | `/ai-summary/{id}` `/ai-summary/{id}/refresh` | AI 画像 |
| GET `POST` | `/trajectory/{id}` `/trajectory/{id}/refresh` | 研究演化树 |
| GET `POST` | `/persona/{id}` `/persona/{id}/refresh` | 研究者人格 |
| GET `POST` | `/career/{id}` `/career/{id}/refresh` | 职业经历 |
| GET `POST` | `/poem/{id}?year=` `/poem/{id}/refresh?year=` | 年度诗篇 |
| GET `POST` | `/capability/{id}` `/capability/{id}/refresh` | 能力画像（开创者/扩展者/追随者） |

### 6.4 排行榜
| Method | Path | 功能 |
|--------|------|------|
| GET | `/rankings?type=total\|young\|direction&direction=llm&metric=h_index&offset&limit&target_user_id` | 排行榜分页 + 目标用户位次 |
| GET | `/rankings/directions` | 方向列表 |

### 6.5 报表
| Method | Path | 功能 |
|--------|------|------|
| GET | `/report/{id}/summary` | 综合 CV JSON |
| GET | `/report/{id}/papers?year_from&year_to&ccf_rank&min_citations&first_author` | 论文筛选导出（md/bib/json） |
| GET | `/report/grant-types` | 支持的基金类型 |
| GET | `/report/{id}/paper-evidence/{paper_id}` | 单篇论文的引用/开源证据链 |
| POST | `/report/{id}/research-basis` | 生成"研究基础"Markdown（NSFC 各种类） |

### 6.6 其他
| Method | Path | 功能 |
|--------|------|------|
| GET | `/api/proxy/image?url=` | 代理外部头像（CORS 规避） |
| POST | `/track` | 页面访问记录 |

---

## 7. 前端 API 客户端

位于 `frontend/src/lib/api.ts`，所有方法都统一通过 `request<T>(path, init?)` 调用 `/api/*`。

**按功能分组：**

```ts
// 基础
api.searchScholars / searchGithubRepos / searchHFItems
api.createProfile / updateProfile / getProfile / listUsers / refresh
api.getStats / getTimeline / getMilestones
api.addRepo / deleteRepo / addHFItem / deleteHFItem

// 引用分析
api.getCitationOverview / triggerCitationAnalysis / enrichHonors
api.getScholars / getPaperAnalyses

// 增量 & 报表
api.getGrowth / getReportSummary / getPaperReport / getGrantTypes
api.getPaperEvidence / generateResearchBasis

// 画像 / 趣味
api.getBuzz / refreshBuzz
api.getAISummary / refreshAISummary
api.getTrajectory / refreshTrajectory
api.getPersona / refreshPersona
api.getCareer / refreshCareer
api.getAnnualPoem / refreshAnnualPoem

// 排行榜
api.getRankings / getRankingDirections

// 其他
api.getSiteStats / trackVisit
```

**类型定义**（同文件）：Paper, GithubRepo, HFItem, ProfileFull, Stats, UserProfile, TimelineEntry, Milestone, CitationOverview, BuzzSnapshot, AISummary, TrajectoryData (TreeNode), ResearcherPersona, CareerData (CareerStep), AnnualPoemData (PoemHighlight), LeaderboardData (LeaderboardEntry), SiteStats...

---

## 8. 种子学者 & 批量导入

### 8.1 种子名单
`docs/seed_scholars.json` — 87 位知名学者（LLM/NLP 29, CV 24, VLM 14, Systems 6, Theory 4, RL 4）。每条：`{name, cn?, affiliation, direction, tier, honors}`。

### 8.2 批量工具
| 脚本 | 用途 |
|------|------|
| `backend/scripts/seed_import.py` | 读 seed JSON → Scholar search → 自动 discover + 创建 + full refresh |
| `backend/scripts/enrich_honors.py` | 为 seed/existing 用户批量补全 honor_tags（LLM + web_search） |
| `backend/scripts/honor_enrich/` | api_tool 批处理配置（不联网，只用 gemini-3 脑内知识） |

### 8.3 运行
```bash
cd backend

# 批量导入全部 seed（concurrency=1 避开 SS rate limit）
python -m scripts.seed_import --enriched

# 批量查荣誉（concurrency=30，联网搜索）
python -m scripts.enrich_honors --concurrency 30
```

结果写入 `docs/seed_scholars_enriched.json`（新增 `honors_proposed` 字段，人工核对后可合并到 `honors`）。

---

## 9. 构建 & 部署

### 9.1 开发模式
```bash
# 后端
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端（HMR）
cd frontend && npm run dev  # vite 默认 5173
```

### 9.2 生产模式
```bash
cd frontend && npm run build  # 产出 dist/
python serve.py 19487          # 同时服务 dist/ + 代理 /api 到 8001
```

### 9.3 TypeScript 构建注意
`tsc -b && vite build` 的 `tsc` 检查比较严，改 `api.ts` / `updateProfile` 签名时要保证下游使用兼容。最新一次 build 已修了 3 个 pre-existing TS error（见 commit 历史）。

### 9.4 SQLite 迁移
`database.py` 的 `init_db()` 会：
1. `Base.metadata.create_all` 自动建新表
2. 对需要 `ALTER TABLE ADD COLUMN` 的旧表做 try/except 迁移（如 `users.honor_tags`, `users.research_direction`, `users.seed_tier`, `notable_citations.honor_tags`）

---

## 10. 已知坑 / 避免走过的路

1. **Tab 子组件 unmount 丢 state** — ProfilePage 的 tab 切换会 unmount child。所有"用户手动触发"的数据（trajectory / career / poem 等）必须把 state 提升到 ProfilePage，用 `data` + `onUpdate` props 控制。见 `memory/feedback_tab_state_hoisting.md`。

2. **gpt-5 reasoning token 预算** — Responses API + `web_search_preview` 的 gpt-5 会在多轮 reasoning + 搜索上消耗大量 token；`max_output_tokens` 小于 8000 经常拿不到最终 message。career / enrich_honors 都设成了 16000。

3. **SS API rate limit** — 种子批量导入时必须 `--concurrency 1`，且要在代码里加指数退避 retry（已实现）。

4. **分享卡 CSS 兼容** — PersonaCard / AnnualPoemCard / ShareCard 里全部用**内联样式**（html-to-image 对 tailwind 类名支持不稳定）。

5. **DB schema 演化** — 修改 trajectory_json 结构时记得清空旧缓存（`DELETE FROM research_trajectories`），否则前端拿到老格式会 TypeError。

6. **honor_tags 三态语义** — `NULL` = 未识别，`[]` = 已识别但无荣誉，`["IEEE Fellow", ...]` = 有荣誉。前端判断时要区分 null 和空数组。

7. **CORS 与代理** — 前端 dev server（5173）代理 `/api` → 127.0.0.1:8001；`serve.py` 也代理 `/api`，但用浏览器直连要注意 `--noproxy '*'`。
