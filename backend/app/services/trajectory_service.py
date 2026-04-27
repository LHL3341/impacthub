"""Research trajectory service: LLM generates a strict tree structure from rich researcher context.

Takes advantage of 1M-context models by feeding in:
- All papers (title, year, venue, citations, authors)
- All repos (name, stars, description, language, created year)
- All HF items (name, type, downloads, likes)
- Top notable citations (who cites this person + their h-index/honors)
- Buzz snapshot summary (external web perspective)
- Existing AI summary / tags (prior interpretation hint)
- User bio / honor tags
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models import (
    User, Paper, GithubRepo, HFItem,
    BuzzSnapshot, AISummary, NotableCitation, ResearchTrajectory,
)
from app.config import LLM_API_BASE, LLM_API_KEY, LLM_BUZZ_MODEL, LLM_FALLBACK_MODEL
from app.utils.paper_dedup import deduplicate_papers

logger = logging.getLogger(__name__)

# Context limits (1M-token friendly, but keep each prompt reasonable)
MAX_PAPERS_IN_PROMPT = 400        # was 60
MAX_REPOS_IN_PROMPT = 50
MAX_HF_IN_PROMPT = 30
MAX_NOTABLE_CITERS = 15
BUZZ_SUMMARY_CHARS = 2000


def _parse_llm_json(content: str) -> dict | None:
    """Extract and parse JSON, tolerant of markdown code blocks."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


async def _query_llm(client: httpx.AsyncClient, prompt: str) -> str | None:
    """Call LLM with dual API fallback. Returns raw text content."""
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/responses",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_BUZZ_MODEL,
                "input": prompt,
                "max_output_tokens": 8000,
            },
            timeout=300,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            text = c.get("text", "")
                            if text:
                                return text
    except Exception as e:
        logger.info("Trajectory: Responses API failed (%s), trying chat completions", e)

    try:
        resp = await client.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_FALLBACK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": 8000,
            },
            timeout=300,
        )
        if resp.status_code != 200:
            logger.warning("Trajectory: Chat API returned %d: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        return data["choices"][0]["message"].get("content", "")
    except Exception as e:
        logger.warning("Trajectory: Chat API call failed: %s", e)
        return None


async def _gather_context(db: AsyncSession, user: User) -> dict:
    """Pull all relevant signals from DB for one user."""
    uid = user.id

    # Papers
    papers_raw = (await db.execute(
        select(Paper).where(Paper.user_id == uid)
    )).scalars().all()
    papers = deduplicate_papers(papers_raw)
    paper_ids = [p.id for p in papers]

    # Repos (ordered by stars)
    repos = (await db.execute(
        select(GithubRepo).where(GithubRepo.user_id == uid).order_by(desc(GithubRepo.stars))
    )).scalars().all()

    # HF items
    hf_items = (await db.execute(
        select(HFItem).where(HFItem.user_id == uid).order_by(desc(HFItem.downloads))
    )).scalars().all()

    # Notable citations — who is citing this person's work
    notable = []
    if paper_ids:
        notable = (await db.execute(
            select(NotableCitation)
            .where(NotableCitation.user_id == uid)
            .order_by(desc(NotableCitation.author_h_index))
            .limit(MAX_NOTABLE_CITERS)
        )).scalars().all()

    # Buzz
    buzz = (await db.execute(
        select(BuzzSnapshot).where(BuzzSnapshot.user_id == uid)
    )).scalars().first()

    # AI summary
    ai_sum = (await db.execute(
        select(AISummary).where(AISummary.user_id == uid)
    )).scalars().first()

    return {
        "papers": papers,
        "repos": repos,
        "hf_items": hf_items,
        "notable": notable,
        "buzz": buzz,
        "ai_summary": ai_sum,
    }


def _build_prompt(user: User, ctx: dict) -> str:
    """Build a rich LLM prompt from all available context."""
    papers = ctx["papers"]
    repos = ctx["repos"]
    hf_items = ctx["hf_items"]
    notable = ctx["notable"]
    buzz = ctx["buzz"]
    ai_sum = ctx["ai_summary"]

    name = user.name or user.github_username or "研究者"
    bio = (user.bio or "").strip()

    # ── Identity block ──
    identity_lines = [f"姓名：{name}"]
    if bio:
        identity_lines.append(f"简介：{bio}")
    if user.honor_tags and isinstance(user.honor_tags, list) and user.honor_tags:
        identity_lines.append(f"已知荣誉：{', '.join(user.honor_tags)}")
    link_parts = []
    if user.scholar_id:
        link_parts.append(f"Scholar: {user.scholar_id}")
    if user.github_username:
        link_parts.append(f"GitHub: @{user.github_username}")
    if user.hf_username:
        link_parts.append(f"HF: @{user.hf_username}")
    if user.homepage:
        link_parts.append(f"主页: {user.homepage}")
    if link_parts:
        identity_lines.append("链接：" + " | ".join(link_parts))
    identity_block = "\n".join(identity_lines)

    # ── Career stats (inferred) ──
    valid_papers = [p for p in papers if p.year and p.year > 0]
    career_start = min((p.year for p in valid_papers), default=None)
    career_end = max((p.year for p in valid_papers), default=None)
    career_span = (career_end - career_start + 1) if (career_start and career_end) else 0

    first_author_count = 0
    total_with_authors = 0
    name_tokens = set(re.findall(r"[a-zA-Z]+", (user.name or "").lower()))
    for p in valid_papers:
        authors = p.authors_json if isinstance(p.authors_json, list) else []
        if not authors:
            continue
        total_with_authors += 1
        first = (authors[0] or "").lower() if authors else ""
        first_tokens = set(re.findall(r"[a-zA-Z]+", first))
        if name_tokens and name_tokens & first_tokens:
            first_author_count += 1
    fa_ratio = (first_author_count / total_with_authors) if total_with_authors else 0

    # Top coauthors (frequency)
    coauthor_counter: Counter = Counter()
    for p in valid_papers:
        authors = p.authors_json if isinstance(p.authors_json, list) else []
        for a in authors[:8]:
            if not a:
                continue
            a_tokens = set(re.findall(r"[a-zA-Z]+", a.lower()))
            if name_tokens and name_tokens & a_tokens:
                continue
            coauthor_counter[a[:40]] += 1
    top_coauthors = coauthor_counter.most_common(8)

    # Per-year paper count (for rhythm)
    year_counter: Counter = Counter(p.year for p in valid_papers)
    yearly_rhythm = " ".join(
        f"{y}:{year_counter[y]}" for y in sorted(year_counter.keys())
    )

    # Venue distribution by 3-year window
    venue_by_window: dict[str, Counter] = {}
    if career_start and career_end:
        for p in valid_papers:
            if not p.venue:
                continue
            window_start = career_start + ((p.year - career_start) // 3) * 3
            window_end = min(window_start + 2, career_end)
            key = f"{window_start}-{window_end}"
            venue_by_window.setdefault(key, Counter())[p.venue.split()[0][:30]] += 1

    career_lines = []
    if career_start and career_end:
        career_lines.append(f"- 发表年限：{career_start}–{career_end}（{career_span} 年）")
    career_lines.append(
        f"- 论文总数（去重后）：{len(papers)}；其中第一作者 {first_author_count}/{total_with_authors}（{fa_ratio:.0%}）"
    )
    if yearly_rhythm:
        career_lines.append(f"- 年度发表节奏：{yearly_rhythm}")
    if top_coauthors:
        coauthor_str = "、".join(f"{n}×{c}" for n, c in top_coauthors)
        career_lines.append(f"- 主要合作者（按合作次数）：{coauthor_str}")
    if venue_by_window:
        career_lines.append("- 各阶段主要发表场所：")
        for window_key in sorted(venue_by_window.keys()):
            top_venues = venue_by_window[window_key].most_common(4)
            venue_str = "、".join(f"{v}×{c}" for v, c in top_venues)
            career_lines.append(f"  · {window_key}: {venue_str}")
    if repos:
        repo_years = [r.created_at_remote.year for r in repos if r.created_at_remote]
        if repo_years:
            career_lines.append(f"- 开源活跃年份：{min(repo_years)}–{max(repo_years)}")
    career_block = "\n".join(career_lines)

    # ── Papers block: now much fuller ──
    sorted_papers = sorted(papers, key=lambda p: (p.year or 0, -(p.citation_count or 0)))
    if len(sorted_papers) > MAX_PAPERS_IN_PROMPT:
        # Keep all with high citation count + a uniform sample of the rest
        highcit = [p for p in sorted_papers if (p.citation_count or 0) >= 10]
        others = [p for p in sorted_papers if (p.citation_count or 0) < 10]
        remaining = MAX_PAPERS_IN_PROMPT - len(highcit)
        if remaining > 0 and others:
            step = max(1, len(others) // remaining)
            sampled_others = others[::step][:remaining]
        else:
            sampled_others = []
        kept = sorted(highcit + sampled_others, key=lambda p: (p.year or 0, -(p.citation_count or 0)))
    else:
        kept = sorted_papers

    paper_lines = []
    for p in kept:
        venue = (p.venue or "").split("|")[0][:60]
        ccf = f" [CCF-{p.ccf_rank}]" if p.ccf_rank else ""
        authors = p.authors_json if isinstance(p.authors_json, list) else []
        # Show up to 3 authors to hint collaboration structure
        au = ", ".join(authors[:3]) + ("..." if len(authors) > 3 else "")
        paper_lines.append(f"({p.year or '?'}) [{p.citation_count}] {p.title} — {venue}{ccf}" + (f" · 作者: {au}" if au else ""))
    papers_block = "\n".join(paper_lines) if paper_lines else "（无论文数据）"

    # ── Repos block ──
    repos_lines = []
    for r in repos[:MAX_REPOS_IN_PROMPT]:
        y = r.created_at_remote.year if r.created_at_remote else "?"
        desc_text = (r.description or "")[:120]
        repos_lines.append(f"({y}) {r.repo_name} ★{r.stars} · {r.language or '-'} · {desc_text}")
    repos_block = "\n".join(repos_lines) if repos_lines else ""

    # ── HF items ──
    hf_lines = []
    for h in hf_items[:MAX_HF_IN_PROMPT]:
        hf_lines.append(f"[{h.item_type}] {h.name} · {h.downloads} dl / {h.likes} ♥")
    hf_block = "\n".join(hf_lines) if hf_lines else ""

    # ── Notable citers ──
    notable_lines = []
    for n in notable[:MAX_NOTABLE_CITERS]:
        honor_str = ""
        if n.honor_tags and isinstance(n.honor_tags, list) and n.honor_tags:
            honor_str = f" [{'/'.join(n.honor_tags[:2])}]"
        notable_lines.append(
            f"- {n.author_name} (h={n.author_h_index}{honor_str}) 在 {n.citing_paper_year} 《{n.citing_paper_title[:60]}》里引用"
        )
    notable_block = "\n".join(notable_lines) if notable_lines else ""

    # ── Buzz ──
    buzz_block = ""
    if buzz and buzz.summary:
        buzz_block = f"\n外部网络讨论（供参考，非结论）：\n{buzz.summary[:BUZZ_SUMMARY_CHARS]}"
        if buzz.topics:
            buzz_block += f"\n讨论话题：{', '.join(buzz.topics[:8])}"

    # ── Prior AI summary (hint, not answer) ──
    ai_hint = ""
    if ai_sum and ai_sum.summary:
        ai_hint = f"\n已有的 AI 简介（仅供参考）：{ai_sum.summary}"
        if ai_sum.tags:
            ai_hint += f"\n已有标签：{', '.join(ai_sum.tags)}"

    # Final assembly
    sections = [
        f"【身份信息】\n{identity_block}",
        f"【职业/研究经历线索】\n{career_block}",
    ]
    if papers_block:
        sections.append(f"【完整论文列表（{len(kept)} 篇 / 共 {len(papers)}）】\n{papers_block}")
    if repos_block:
        sections.append(f"【开源项目（{min(len(repos), MAX_REPOS_IN_PROMPT)} / {len(repos)}）】\n{repos_block}")
    if hf_block:
        sections.append(f"【HuggingFace 产出】\n{hf_block}")
    if notable_block:
        sections.append(f"【引用 TA 的知名学者（揭示影响力辐射范围）】\n{notable_block}")
    if buzz_block:
        sections.append(buzz_block.strip())
    if ai_hint:
        sections.append(ai_hint.strip())

    context = "\n\n".join(sections)

    return f"""你是一位科研画像分析助手。基于下面的**完整信息**生成一个树状 JSON，叙述研究者「职业轨迹 + 研究方向演化」的综合脉络（宏观画像，不要罗列单篇论文）。

{context}

请严格按照下面的 JSON Schema 输出（仅输出 JSON，不加任何其他文字、注释、markdown 代码块标记）：

{{
  "root": {{
    "label": "研究者姓名",
    "summary": "三到四句话，综合概括研究者的整体画像：包括推断的职业阶段、核心研究特色、贡献风格、影响力辐射",
    "year_range": "最早年份-最近年份",
    "paper_count": 总论文数,
    "children": [
      {{
        "label": "主要研究方向/职业阶段名（4-12字，如「博士期：NLP 基础」「独立研究期：多模态」）",
        "summary": "两三句话：说明该阶段的研究内容 + 可能的职业角色 + 里程碑事件（结合 venue 变化、合作者变化、产出节奏来推断）",
        "year_range": "2015-2020",
        "paper_count": 该阶段大致论文数,
        "children": [
          {{
            "label": "子主题或技术路线（4-12字）",
            "summary": "一两句话描述子主题的核心思路、方法或贡献",
            "year_range": "2017-2019"
          }}
        ]
      }}
    ]
  }}
}}

要求：
1. root 下 3~6 个 children，每个 children 下 2~4 个子主题。
2. children 应是 **"研究方向 × 职业阶段"** 的复合概念，读者既能看出做什么研究，也能从发表节奏/venue/合作者变化推断出职业阶段。
3. summary 要有故事感：按时间描述方向的演化、延续、转折；方向变化时要写出衔接句（"在前一阶段的 XX 基础上，本阶段转向 YY"）；必要时引用合作者或引用者来体现影响力。
4. 按时间顺序排列 children。
5. label 用中文，简洁具体，禁止用"研究方向1"这种泛称。
6. 不要包含 paper_ids 字段。
7. 若信息薄（比如只有 1-2 篇论文或只有 GitHub），就产出一个精简但有洞察的树，children 数量可以少（1-2 个），而不是硬凑。
8. 只输出有效 JSON，不要加解释、不要用 ```json 包裹。"""


async def refresh_trajectory(db: AsyncSession, user: User) -> ResearchTrajectory | None:
    """Generate research evolution tree via LLM using rich context."""
    ctx = await _gather_context(db, user)
    papers = ctx["papers"]
    repos = ctx["repos"]
    hf_items = ctx["hf_items"]

    # Much more permissive gate: any non-trivial profile can generate a tree
    signal = len(papers) + len(repos) + len(hf_items) + (1 if (user.bio or "").strip() else 0)
    if signal < 1:
        logger.info("Trajectory: user %d has no data at all, skipping", user.id)
        return None

    prompt = _build_prompt(user, ctx)

    async with httpx.AsyncClient(timeout=310) as client:
        content = await _query_llm(client, prompt)

    if not content:
        logger.warning("Trajectory: LLM returned no content for user %d", user.id)
        return None

    result = _parse_llm_json(content)
    if not result or "root" not in result:
        logger.warning("Trajectory: Failed to parse tree JSON for user %d. Content: %s", user.id, content[:300])
        return None

    papers_index = {
        p.id: {
            "id": p.id,
            "title": p.title,
            "year": p.year,
            "venue": p.venue or "",
            "citation_count": p.citation_count,
            "ccf_rank": p.ccf_rank or "",
        }
        for p in papers
    }

    def _sanitize(node: dict) -> dict:
        clean = {
            "label": str(node.get("label", ""))[:80],
            "summary": str(node.get("summary", ""))[:400],
            "year_range": str(node.get("year_range", "")),
            "paper_count": int(node.get("paper_count", 0) or 0),
            "children": [_sanitize(c) for c in node.get("children", []) if isinstance(c, dict)][:8],
        }
        return clean

    root = _sanitize(result["root"])

    buzz = ctx["buzz"]
    buzz_timeline = []
    if buzz and buzz.topics:
        buzz_timeline.append({
            "period_label": "当前",
            "heat_label": buzz.heat_label or "medium",
            "topics": buzz.topics[:5] if isinstance(buzz.topics, list) else [],
        })

    trajectory_data = {
        "root": root,
        "papers_index": papers_index,
        "buzz_timeline": buzz_timeline,
    }

    existing = (await db.execute(
        select(ResearchTrajectory).where(ResearchTrajectory.user_id == user.id)
    )).scalars().first()

    if existing:
        existing.trajectory_json = trajectory_data
        existing.refreshed_at = datetime.utcnow()
        trajectory = existing
    else:
        trajectory = ResearchTrajectory(
            user_id=user.id,
            trajectory_json=trajectory_data,
            refreshed_at=datetime.utcnow(),
        )
        db.add(trajectory)

    await db.flush()
    logger.info(
        "Trajectory refreshed for user %d: %d papers, %d repos, %d hf, %d notable citers",
        user.id, len(papers), len(repos), len(hf_items), len(ctx["notable"]),
    )
    return trajectory
