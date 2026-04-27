"""Researcher persona service.

12 meme-coded archetypes (GOAT / PI / WOLF / ...), decided by LLM based on
rich context (metrics + heuristic dimension hints + representative papers/repos).
Dimension scores are still computed locally for UI progress bars.
"""

import json
import logging
import re
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_BUZZ_MODEL, LLM_FALLBACK_MODEL
from app.models import User, Paper, GithubRepo, HFItem, ResearcherPersona
from app.utils.paper_dedup import deduplicate_papers

logger = logging.getLogger(__name__)


# ── 12 persona definitions keyed by the meme code itself ──
PERSONAS: dict[str, dict] = {
    "GOAT": {
        "name_zh": "老神仙", "name_en": "Veteran Sage", "emoji": "🏔️",
        "tagline": "嘴上要退休，手上还在发 Nature",
        "description": "深耕一生、独立建树的资深研究者，一个人扛起一整条技术路线，产出稀少但篇篇封神",
        "traits": ["篇篇封神", "代码自己敲", "不带学生", "至今仍在一线"],
        "color_from": "#6366f1", "color_to": "#8b5cf6",
    },
    "PI": {
        "name_zh": "组里老大", "name_en": "The PI", "emoji": "👑",
        "tagline": "同时带 8 个博士生还能发顶会",
        "description": "资深领军 PI，坐镇实验室、吸引顶尖合作者，把深度研究做成生态",
        "traits": ["实打实的 PI", "合作者成群", "学生晋升机", "论文质 + 量并存"],
        "color_from": "#7c3aed", "color_to": "#a855f7",
    },
    "WOLF": {
        "name_zh": "独狼", "name_en": "Lone Wolf", "emoji": "🐺",
        "tagline": "一个人 = 一整个实验室",
        "description": "年轻、独立、不合群的硬核 solo 玩家，一人包揽 idea、代码、写作、rebuttal",
        "traits": ["solo 之王", "全栈全能", "不屑合作", "潜力巨大"],
        "color_from": "#2563eb", "color_to": "#3b82f6",
    },
    "VIRAL": {
        "name_zh": "开源新贵", "name_en": "OSS Rising Star", "emoji": "🚀",
        "tagline": "GitHub star 长得比头发快",
        "description": "新生代开源实干派，论文代码两开花，twitter 动不动 trending",
        "traits": ["一年爆款 repo", "GitHub 简历者", "协作型选手", "涨粉中"],
        "color_from": "#0ea5e9", "color_to": "#06b6d4",
    },
    "PROOF": {
        "name_zh": "理论大神", "name_en": "Theory Oracle", "emoji": "🧠",
        "tagline": "20 年 30 篇，每篇引用破千",
        "description": "只谈理论、从不碰代码的资深大神，篇数稀少但都是教科书级",
        "traits": ["黑板写证明", "篇篇教科书", "不搞 GitHub", "被模仿无数"],
        "color_from": "#6d28d9", "color_to": "#7c3aed",
    },
    "SENSEI": {
        "name_zh": "学派掌门", "name_en": "School Founder", "emoji": "📜",
        "tagline": "桃李满天下，孙辈都带出来了",
        "description": "建立了整条学派脉络的资深理论 PI，学生的学生的学生都是同行大佬",
        "traits": ["开山立派", "三代桃李", "学界话事人", "代表教材编者"],
        "color_from": "#4f46e5", "color_to": "#6366f1",
    },
    "MONK": {
        "name_zh": "苦行僧", "name_en": "Monk", "emoji": "🪷",
        "tagline": "一年憋一篇，审稿人看完跪了",
        "description": "年轻独立的精品派，慢工出细活，每篇都 best paper candidate",
        "traits": ["一年一作", "reviewer 敬畏", "不混圈子", "纯粹热爱"],
        "color_from": "#8b5cf6", "color_to": "#a78bfa",
    },
    "HYPE": {
        "name_zh": "学术新贵", "name_en": "Rising Aristocrat", "emoji": "✨",
        "tagline": "Faculty Market 上的抢手货",
        "description": "合作广、名声响、简历漂亮的新锐理论家，今年在 job market 被多家抢",
        "traits": ["CV 漂亮", "合作圈硬核", "潜力爆棚", "大佬眼中的明日之星"],
        "color_from": "#ec4899", "color_to": "#f472b6",
    },
    "NINJA": {
        "name_zh": "一人成军", "name_en": "Solo Army", "emoji": "⚡",
        "tagline": "代码实验论文回复全是一个人",
        "description": "资深全栈单兵作战者，从 idea 到上线、从审稿到 rebuttal 全程 solo",
        "traits": ["十项全能", "深夜 commit", "不依赖学生", "产量爆表"],
        "color_from": "#f59e0b", "color_to": "#fbbf24",
    },
    "BDFL": {
        "name_zh": "造轮大师", "name_en": "Wheel Forger", "emoji": "🌍",
        "tagline": "论文和 repo 双飞，社区围着你转",
        "description": "资深生态构建者，手下既有顶会论文也有 10k star 项目，整个子领域靠你推动",
        "traits": ["10k star 项目", "issue 处理王", "社区 BDFL", "顶会常客"],
        "color_from": "#10b981", "color_to": "#34d399",
    },
    "JUAN": {
        "name_zh": "卷王", "name_en": "Hustle King", "emoji": "🔥",
        "tagline": "一个月三篇 arXiv，导师看了都心疼",
        "description": "年轻高产选手，arXiv 日更、论文机关枪，代码和实验一个不落",
        "traits": ["arXiv 钉子户", "睡眠不足", "Cursor 100 tabs", "导师都追不上"],
        "color_from": "#ef4444", "color_to": "#f97316",
    },
    "KPI": {
        "name_zh": "论文工厂", "name_en": "Paper Factory", "emoji": "🏭",
        "tagline": "量大管饱，审稿人看名字就知道",
        "description": "专注论文数量的工厂型选手，题材覆盖面广，但代码开源什么的就算了",
        "traits": ["量大管饱", "题材漂移", "从不开源", "审稿缘分深"],
        "color_from": "#64748b", "color_to": "#94a3b8",
    },
}

VALID_CODES = set(PERSONAS.keys())
FALLBACK_CODE = "MONK"  # safe default if LLM fails


def _placeholder_scores() -> dict[str, float]:
    """Neutral 0.5 placeholder when LLM fails — UI bars will show 'middle' position."""
    return {
        "output_depth": 0.5,
        "ecosystem": 0.5,
        "seniority": 0.5,
        "collaboration": 0.5,
    }


def _compute_raw_metrics(papers: list, repos: list, hf_items: list) -> dict[str, float]:
    paper_count = max(len(papers), 1)
    total_citations = sum(p.citation_count for p in papers)
    cits = sorted([p.citation_count for p in papers], reverse=True)
    h_index = 0
    for i, c in enumerate(cits):
        if c >= i + 1:
            h_index = i + 1
        else:
            break
    author_counts = [len(p.authors_json) if isinstance(p.authors_json, list) else 1 for p in papers]
    return {
        "paper_count": float(len(papers)),
        "total_citations": float(total_citations),
        "h_index": float(h_index),
        "citations_per_paper": round(total_citations / paper_count, 1),
        "repo_count": float(len(repos)),
        "hf_count": float(len(hf_items)),
        "total_stars": float(sum(r.stars for r in repos)),
        "avg_authors": round(sum(author_counts) / max(len(author_counts), 1), 1),
    }


def _parse_json(text: str) -> dict | None:
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        s = s.rsplit("```", 1)[0]
    try:
        return json.loads(s.strip())
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def _build_prompt(
    user: User,
    papers: list,
    repos: list,
    hf_items: list,
    metrics: dict[str, float],
) -> str:
    name = user.name or user.github_username or "研究者"
    bio = (user.bio or "").strip()

    # Top 6 papers by citation
    sorted_papers = sorted(papers, key=lambda p: (p.citation_count or 0), reverse=True)[:6]
    paper_lines = [
        f"- ({p.year or '?'}) [{p.citation_count}] {p.title} — {p.venue or '未知期刊'}"
        for p in sorted_papers
    ]

    # Top 4 repos
    sorted_repos = sorted(repos, key=lambda r: (r.stars or 0), reverse=True)[:4]
    repo_lines = [f"- {r.repo_name} ★{r.stars} · {r.language or '-'}" for r in sorted_repos]

    hf_lines = [f"- {h.name} ({h.item_type}) · {h.downloads} dl / {h.likes} ♥"
                for h in sorted(hf_items, key=lambda h: (h.downloads or 0), reverse=True)[:4]]

    personas_block = "\n".join(
        f"- **{code}** {p['emoji']} {p['name_zh']}：{p['tagline']}（{p['description']}）"
        for code, p in PERSONAS.items()
    )

    return f"""你是一个研究者人格分类助手。给定研究者的完整画像，从下面 **12 种 meme 人格**中选出**最贴合的一种**。

### 研究者
- 姓名：{name}
{f"- 简介：{bio}" if bio else ""}
- 核心指标：论文 {int(metrics['paper_count'])} 篇，总引用 {int(metrics['total_citations'])}，h-index {int(metrics['h_index'])}，篇均引用 {metrics['citations_per_paper']}
- 开源：repo {int(metrics['repo_count'])} 个（{int(metrics['total_stars'])} stars），HF 产出 {int(metrics['hf_count'])} 个
- 合作：平均作者数 {metrics['avg_authors']}

### 代表论文
{chr(10).join(paper_lines) if paper_lines else "（暂无）"}

### 代表 GitHub 项目
{chr(10).join(repo_lines) if repo_lines else "（无）"}

### HuggingFace 产出
{chr(10).join(hf_lines) if hf_lines else "（无）"}

### 12 种候选人格
{personas_block}

### 输出要求（严格 JSON，不要 markdown 代码块）
{{
  "persona_code": "从 [GOAT, PI, WOLF, VIRAL, PROOF, SENSEI, MONK, HYPE, NINJA, BDFL, JUAN, KPI] 中挑一个",
  "dimension_scores": {{
    "output_depth":    0-1 小数（0=多产量但篇均引用低, 1=深耕质、篇均极高）,
    "ecosystem":       0-1 小数（0=纯论文派无开源, 1=GitHub/HF 重建设者）,
    "seniority":       0-1 小数（0=新锐刚起步, 1=资深大牛）,
    "collaboration":   0-1 小数（0=独行侠, 1=大型合作者）
  }},
  "reason": "1-2 句话说明为什么这个最贴合（可引用具体数据）"
}}

注意：
1. 考虑**全局画像**：资深学者如果没什么 GitHub 活动，应该是 PROOF 或 SENSEI 而不是 JUAN
2. 如果指标边界模糊，参考 tagline 和 description 做判断
3. 优先选更有辨识度的类别，不要默认给"中位数"人格
4. 必须从 12 个候选里选，不要造新的 code
5. **dimension_scores 要跟你选的 persona 一致** — 选了 GOAT（深耕/资深）就应该 output_depth 高、seniority 高；选了 JUAN（多产/新锐）就应该 output_depth 低、seniority 低"""


async def _query_llm(client: httpx.AsyncClient, prompt: str) -> dict | None:
    # Primary: Responses API on main model
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/responses",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_BUZZ_MODEL,
                "input": prompt,
                "max_output_tokens": 4000,
            },
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            text = c.get("text", "")
                            if text:
                                parsed = _parse_json(text)
                                if parsed:
                                    return parsed
    except Exception as e:
        logger.info("Persona Responses API failed (%s), falling back", e)

    # Fallback: mini model chat completions
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_FALLBACK_MODEL,
                "messages": [{"role": "user", "content": prompt + "\n\n再次强调：只输出 JSON。"}],
                "max_completion_tokens": 2000,
            },
            timeout=90,
        )
        if resp.status_code != 200:
            logger.warning("Persona Chat API returned %d: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        content = data["choices"][0]["message"].get("content", "")
        return _parse_json(content)
    except Exception as e:
        logger.warning("Persona Chat API failed: %s", e)
        return None


async def compute_persona(db: AsyncSession, user: User) -> ResearcherPersona | None:
    """Classify the researcher into one of 12 meme personas via LLM."""
    papers_raw = (await db.execute(
        select(Paper).where(Paper.user_id == user.id)
    )).scalars().all()
    papers = deduplicate_papers(papers_raw)
    if len(papers) < 3:
        logger.info("Persona: user %d has fewer than 3 papers, skipping", user.id)
        return None

    repos = (await db.execute(
        select(GithubRepo).where(GithubRepo.user_id == user.id)
    )).scalars().all()
    hf_items = (await db.execute(
        select(HFItem).where(HFItem.user_id == user.id)
    )).scalars().all()

    metrics = _compute_raw_metrics(papers, repos, hf_items)

    prompt = _build_prompt(user, papers, repos, hf_items, metrics)

    async with httpx.AsyncClient(timeout=130) as client:
        result = await _query_llm(client, prompt)

    persona_code = FALLBACK_CODE
    reason = ""
    scores = _placeholder_scores()
    if result and isinstance(result, dict):
        code = str(result.get("persona_code", "")).strip().upper()
        if code in VALID_CODES:
            persona_code = code
            reason = str(result.get("reason", ""))[:300]
        else:
            logger.warning("Persona: LLM returned unknown code %r for user %d, fallback to %s", code, user.id, FALLBACK_CODE)
        # LLM-supplied dimension scores (preferred over hardcoded formulas)
        raw_scores = result.get("dimension_scores") or {}
        if isinstance(raw_scores, dict):
            for k in ("output_depth", "ecosystem", "seniority", "collaboration"):
                try:
                    v = float(raw_scores.get(k, scores[k]))
                    scores[k] = round(max(0.0, min(1.0, v)), 3)
                except (TypeError, ValueError):
                    pass
    else:
        logger.warning("Persona: LLM failed for user %d, fallback to %s", user.id, FALLBACK_CODE)

    # Store reason inside raw_metrics (no schema change needed)
    metrics_with_reason = {**metrics, "llm_reason": reason} if reason else metrics

    # Upsert
    existing = (await db.execute(
        select(ResearcherPersona).where(ResearcherPersona.user_id == user.id)
    )).scalars().first()
    if existing:
        existing.persona_code = persona_code
        existing.dimension_scores = scores
        existing.raw_metrics = metrics_with_reason
        existing.refreshed_at = datetime.utcnow()
        persona = existing
    else:
        persona = ResearcherPersona(
            user_id=user.id,
            persona_code=persona_code,
            dimension_scores=scores,
            raw_metrics=metrics_with_reason,
            refreshed_at=datetime.utcnow(),
        )
        db.add(persona)

    await db.flush()
    logger.info(
        "Persona computed for user %d: %s (%s) — %s",
        user.id, persona_code, PERSONAS[persona_code]["name_zh"], reason[:60] if reason else "no reason",
    )
    return persona
