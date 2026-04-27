<p align="center">
  <img src="frontend/public/logo.svg" width="120" alt="ImpactHub Logo" />
</p>

<h1 align="center">ImpactHub</h1>

<p align="center">
  <b>统一的科研影响力仪表盘</b><br/>
  研究者画像 + 147 所双一流保研导师库 + AI-native 人才查询
</p>

<p align="center">
  <a href="README.md">English</a> | <b>中文</b>
</p>

<p align="center">
  <a href="#核心功能">核心功能</a> &bull;
  <a href="#快速开始">快速开始</a> &bull;
  <a href="#环境变量">环境变量</a> &bull;
  <a href="#项目结构">项目结构</a>
</p>

---

## 主要页面

| 路由 | 用途 |
|------|------|
| `/profile/:id` | 单个研究者主页（论文 / 仓库 / HF / 人格 / 能力画像 / 年度诗篇 / 分享卡） |
| `/leaderboard` | 总榜 + 年轻学者榜 + 6 个方向榜（前 10000 精确排位，之后百分位） |
| `/recruit` | **B2B AI 人才查询** — 猎头粘 JD → LLM 解析条件 → DB 粗筛 → LLM 精排带理由 |
| `/advisor` | **保研导师库** — 147 所双一流（含全部 985/211），LLM-driven 通用爬虫抓学院 + 师资 stub |
| `/users` | 所有 ImpactHub 用户列表 |
| `/docs` | 系统总览 |

## 核心功能

### 跨平台个人主页

输入 Semantic Scholar ID，系统自动发现并关联你的 GitHub 和 Hugging Face 账号，一站式展示论文、代码仓库和模型。

### 引用分析

- 自动计算 H-index，按 CCF-A/B/C 分类期刊/会议
- 识别引用你论文的**顶尖学者**（h-index ≥ 50）和**知名学者**（h-index ≥ 25）
- LLM 驱动的荣誉标签识别 — 检测引用者中的 IEEE Fellow、ACM Fellow、院士等头衔
- 逐篇论文的引用详情，包含引用上下文片段

### 增长追踪

- 每日指标快照：引用数、h-index、Star 数、Fork 数、下载量、点赞数
- 可交互趋势图，支持 30/60/90/365 天窗口
- 里程碑系统：达到阈值自动触发成就（100 次引用、1K Star 等）

### 网络热度监测

- 基于 Perplexity 的网络搜索，评估你的研究可见度
- 热度分级（热门 / 一般 / 冷门），附来源链接

### AI 摘要

- LLM 生成的研究者简介，捕捉你的科研画像
- 基于论文主题自动生成研究标签

### 研究者人格（12 种 MBTI 风格）

- LLM 从 12 种 meme 人格中选一种（老神仙 GOAT / 组里老大 PI / 独狼 WOLF / 卷王 JUAN / 论文工厂 KPI / 苦行僧 MONK / 学霸 NINJA / 证明哥 PROOF / 长老 SENSEI / 网红 VIRAL / 仁慈独裁者 BDFL / 噱头型 HYPE），配 AI 生成插画
- 4 轴维度（产出 / 生态 / 资历 / 协作）连续分数

### 多方向能力画像

- LLM 识别研究者真正从事的 1-4 个方向
- 每个方向单独给角色（开创者 / 早期采用者 / 扩展者 / 跟随者）+ 占比 + 成就概括 + 代表作
- 一个人可以"在 A 方向是开创者，在 B 方向是扩展者"，避免单一标签

### 研究演化树 + 年度诗篇 + 履历

- 树状研究路径：时间为 Y 轴，研究分支为 X 轴
- 仿小红书"年度诗篇" — 10-14 行数据驱动的现代短诗
- LLM + 联网搜索整理教育背景 + 任职经历（含导师、机构、任期、来源）

### 排行榜

- 总榜 / 年轻学者榜（首篇 <10 年） / 6 个方向榜（LLM、CV、VLM、Systems、Theory、RL）
- 前 10000 名精确排位，之后只显示百分位

### B2B 人才查询

- 猎头自由文本 JD → LLM 抽取结构化条件（方向、资历、h-index 阈值、必要/加分关键词、荣誉）
- DB 粗筛 → 40 份候选 dossier → LLM 精排，给 `match_score`、`tier`、匹配理由、潜在差距、代表作

### 保研导师库（`/advisor`）

- 种子：147 所双一流（含全部 985/211），权威来源：教育部 2022 第二轮双一流名单
- LLM-driven 通用爬虫 — 不写 per-school adapter，启发式抽学院/师资，自动跟 JS 重定向、宽松 SSL（兼容老 .edu.cn）
- 三层流水线：学校目录 → 学院列表 → 导师 stub（姓名 + 职称 + 主页）

### 基金申请工具

- **研究基础生成器**：支持国自然（青年/面上/优青/杰青/重点）、长江学者、万人计划等
- 自适应语气：青年项目强调"潜力+可行性"，资深项目强调"原创性+引领性"
- 论文选择界面，预览引用分析 + 知名学者背书 + 关联代码仓库

### 智能导出

- 论文列表导出：Markdown、BibTeX、JSON
- 按年份、CCF 等级、引用数、一作筛选
- 完整 CV 风格的汇总 JSON

### 自动刷新

- 后台调度器每 6 小时自动刷新所有数据
- 支持手动触发即时刷新

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- OpenAI 兼容的 API Key（用于 AI 摘要和热度功能）

### 后端

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# 编辑 .env，填入你的 API Key
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 前端

```bash
cd frontend
npm install
npm run build    # 生产构建，由后端静态服务
# 或
npm run dev      # 开发模式，热重载
```

### 一键启动（可选）

```bash
python serve.py 19487
```

打开 `http://localhost:19487`，输入你的 Semantic Scholar ID 即可开始使用。

---

## 环境变量

将 `.env.example` 复制到 `backend/.env` 并填写：

| 变量 | 说明 | 必填 |
|------|------|------|
| `LLM_API_BASE` | OpenAI 兼容的 API 地址 | 是 |
| `LLM_API_KEY` | LLM 服务的 API Key | 是 |
| `LLM_BUZZ_MODEL` | 热度/摘要生成模型（默认 `gpt-5`） | 否 |
| `OUTBOUND_PROXY` | 出站 HTTP 代理 | 否 |
| `GITHUB_TOKEN` | GitHub 个人访问令牌（提高 API 速率限制） | 否 |

---

## 项目结构

```
impacthub/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + 静态文件服务
│   │   ├── config.py            # 环境变量与常量
│   │   ├── models.py            # SQLAlchemy ORM 模型
│   │   ├── schemas.py           # Pydantic 数据结构
│   │   ├── routers/
│   │   │   ├── profile.py       # 个人主页 CRUD & 账号关联
│   │   │   ├── stats.py         # 聚合统计
│   │   │   ├── citations.py     # 引用分析 & 学者分级
│   │   │   ├── growth.py        # 增长快照 & 趋势
│   │   │   ├── milestones.py    # 里程碑追踪
│   │   │   ├── buzz.py          # 网络热度监测
│   │   │   ├── ai_summary.py    # AI 生成简介 & 标签
│   │   │   ├── reports.py       # 基金研究基础生成器
│   │   │   └── data.py          # 数据导出
│   │   ├── services/            # 各领域业务逻辑
│   │   └── tasks/
│   │       └── scheduler.py     # APScheduler（6 小时刷新）
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # Setup, Profile, Milestone, Users
│   │   ├── components/          # 图表、卡片、弹窗、导出器
│   │   └── lib/                 # API 客户端、工具函数、会议数据
│   └── package.json
└── serve.py                     # 开发用代理服务器
```

**技术栈**：FastAPI + SQLAlchemy + aiosqlite | React 19 + Tailwind CSS 4 + Recharts | Semantic Scholar + GitHub + Hugging Face APIs

---

## 许可证

MIT
