"""Multi-direction capability portrait service.

LLM identifies the research directions the user covers, then for each
direction classifies role (originator / early_adopter / extender / follower)
and summarises achievements with representative works.

Approach is LLM-first: we pass the complete paper list + citation time-series
to LLM and let it simultaneously:
  1. partition the work into 1-4 research directions
  2. for each direction, judge role + score + write achievements + pick reps
  3. assign a weight to each direction (proportion of overall body of work)

No per-direction heuristic; LLM sees raw data and decides everything.
"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_BUZZ_MODEL, LLM_FALLBACK_MODEL
from app.models import (
    User, Paper, NotableCitation, CitationAnalysis, CapabilityProfile,
)
from app.utils.paper_dedup import deduplicate_papers

logger = logging.getLogger(__name__)

VALID_ROLES = {"originator", "early_adopter", "extender", "follower"}
FALLBACK_ROLE = "extender"

MAX_PAPERS_IN_PROMPT = 40   # top-cited papers fed to LLM


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


async def _gather_context(db: AsyncSession, user: User) -> dict:
    """Collect top papers + their citation year histograms."""
    uid = user.id

    papers_raw = (await db.execute(
        select(Paper).where(Paper.user_id == uid).order_by(Paper.citation_count.desc())
    )).scalars().all()
    papers = deduplicate_papers(papers_raw)
    top_papers = sorted(papers, key=lambda p: (p.citation_count or 0), reverse=True)[:MAX_PAPERS_IN_PROMPT]
    paper_ids = [p.id for p in top_papers]

    notable = []
    if paper_ids:
        notable = (await db.execute(
            select(NotableCitation).where(NotableCitation.paper_id.in_(paper_ids))
        )).scalars().all()
    by_paper: dict[int, list[NotableCitation]] = defaultdict(list)
    for n in notable:
        by_paper[n.paper_id].append(n)

    analyses = []
    if paper_ids:
        analyses = (await db.execute(
            select(CitationAnalysis).where(CitationAnalysis.paper_id.in_(paper_ids))
        )).scalars().all()
    analysis_by_paper: dict[int, CitationAnalysis] = {a.paper_id: a for a in analyses}

    # Build compact paper records for the prompt
    records = []
    for p in top_papers:
        cites = by_paper.get(p.id, [])
        year_bins: dict[int, int] = defaultdict(int)
        for c in cites:
            if c.citing_paper_year:
                year_bins[c.citing_paper_year] += 1
        year_histogram = sorted(year_bins.items())
        analysis = analysis_by_paper.get(p.id)
        total_citing = analysis.total_citing_papers if analysis else (p.citation_count or 0)

        records.append({
            "title": p.title,
            "year": p.year,
            "venue": p.venue or "",
            "citation_count": p.citation_count or 0,
            "total_citing_papers": total_citing,
            "year_histogram": year_histogram[:15],
            "top_citer_h": [
                (c.author_name, c.author_h_index, c.citing_paper_year)
                for c in sorted(cites, key=lambda x: (x.author_h_index or 0), reverse=True)[:3]
            ],
        })

    return {"papers": records, "total_papers": len(papers)}


def _build_prompt(user: User, ctx: dict) -> str:
    name = user.name or user.github_username or "研究者"
    bio = (user.bio or "").strip()
    honor = ""
    if user.honor_tags and isinstance(user.honor_tags, list) and user.honor_tags:
        honor = f"已知荣誉: {', '.join(user.honor_tags)}"

    lines = [f"研究者: {name}"]
    if bio:
        lines.append(f"简介: {bio}")
    if honor:
        lines.append(honor)
    lines.append(f"去重后论文总数 {ctx['total_papers']}，以下是 top {len(ctx['papers'])} 高被引论文 + 引用时序:")
    lines.append("")

    for i, r in enumerate(ctx["papers"], 1):
        hist = " · ".join(f"{y}:{c}" for y, c in r["year_histogram"]) or "（无详细引用时序）"
        citer_str = "; ".join(f"{n}(h={h}, {y})" for n, h, y in r["top_citer_h"]) or "—"
        lines.append(f"[{i}] ({r['year']}) {r['title']}")
        lines.append(f"     venue={r['venue']} · 引用 {r['citation_count']} · 记录到 citer {r['total_citing_papers']}")
        lines.append(f"     年度引用: {hist}")
        lines.append(f"     高 h-index citer: {citer_str}")
        lines.append("")

    data_block = "\n".join(lines)

    return f"""你是一位资深的科研画像分析助手。基于下面研究者的论文数据 + 引用时序，给出一份**多方向立体能力画像**——不是一个标签，而是 per-direction 的角色与成果。

### 分析数据
{data_block}

### 任务
对这位研究者：
1. 识别 TA 真正从事过的研究方向（1-4 个，不要为了凑数编造）。方向要具体（例如 "视觉-语言预训练"、"对比学习" 而不是 "AI" / "深度学习" 这种太泛的）。
2. 对每个方向单独判断：
   - **role**（角色）：从下列 4 种选一种
     - `originator` 开创者: 在该方向有开山之作或奠基工作，被长期独立工作引用
     - `early_adopter` 早期采用者: 在方向刚起步时即加入，做了早期 benchmark/实验贡献
     - `extender` 扩展者: 在已有方法上做改进、延伸、应用
     - `follower` 跟随者: 跟进方向做相关研究，但非关键里程碑
   - **score** (0-1): 在该方向上这个角色的强度；1 = 非常典型的 originator，0.1 = 边缘的 follower
   - **achievements**: 用 1-2 句话概括 TA 在该方向的成就（具体，例如"在 CLIP 这一方向上通过 ALBEF 等工作建立了对比多模态预训练 benchmark"）
   - **representative_works**: 挑 1-3 篇该方向最能代表角色的论文（从上面列表挑），给 title + year + citing_count
   - **weight** (0-1): 该方向在 TA 整体研究中的占比（所有方向 weight 总和应该约等于 1.0）

3. 给出 **primary_direction**（weight 最大的方向的中文名）+ **primary_role**（对应该方向的 role）
4. 给出 **rationale**: 一句话总结整体画像（20-50 字）

### 严格 JSON 输出（不要 markdown、不加任何其他文字）
{{
  "primary_direction": "主要方向中文名",
  "primary_role": "originator | early_adopter | extender | follower",
  "rationale": "一句话整体总结",
  "profiles": [
    {{
      "direction_en": "Vision-Language Pre-training",
      "direction_zh": "视觉-语言预训练",
      "weight": 0.55,
      "role": "originator",
      "score": 0.85,
      "achievements": "通过 XX、YY 等工作推动了对比多模态预训练的范式形成，XX 发表后 5+ 年仍在被独立工作引用。",
      "representative_works": [
        {{"title": "XX: ...", "year": 2021, "citing_count": 4200}},
        {{"title": "YY: ...", "year": 2022, "citing_count": 1800}}
      ]
    }}
  ]
}}

### 要求
- 方向数目根据实际情况，1-4 个之间；论文少/方向单一的就给 1-2 个方向
- 不要给所有方向都打 originator；多数研究者在大多数方向是 extender/follower，只在 1 个方向是 originator
- representative_works 的 title 必须直接复制上面列表里的原文标题
- weight 反映 TA 在该方向投入的相对比重；所有方向 weight 总和应约等于 1.0（允许±0.1 误差）
- 只输出 JSON"""


async def _query_llm(client: httpx.AsyncClient, prompt: str) -> dict | None:
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/responses",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_BUZZ_MODEL,
                "input": prompt,
                "max_output_tokens": 8000,
            },
            timeout=240,
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
        logger.info("Capability Responses API failed (%s), falling back", e)

    try:
        resp = await client.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_FALLBACK_MODEL,
                "messages": [{"role": "user", "content": prompt + "\n\n再次强调：只输出 JSON。"}],
                "max_completion_tokens": 4000,
            },
            timeout=180,
        )
        if resp.status_code != 200:
            logger.warning("Capability Chat API %d: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        return _parse_json(data["choices"][0]["message"].get("content", ""))
    except Exception as e:
        logger.warning("Capability Chat API failed: %s", e)
        return None


def _sanitize_profile(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    role = str(raw.get("role", "")).strip().lower()
    if role not in VALID_ROLES:
        role = FALLBACK_ROLE
    try:
        score = max(0.0, min(1.0, float(raw.get("score", 0.3))))
    except (TypeError, ValueError):
        score = 0.3
    try:
        weight = max(0.0, min(1.0, float(raw.get("weight", 0.0))))
    except (TypeError, ValueError):
        weight = 0.0

    works = []
    for w in (raw.get("representative_works") or [])[:5]:
        if not isinstance(w, dict):
            continue
        works.append({
            "title": str(w.get("title", ""))[:200],
            "year": w.get("year") if isinstance(w.get("year"), int) else None,
            "citing_count": int(w.get("citing_count") or 0),
        })

    return {
        "direction_en": str(raw.get("direction_en", ""))[:120],
        "direction_zh": str(raw.get("direction_zh", ""))[:80],
        "weight": round(weight, 3),
        "role": role,
        "score": round(score, 3),
        "achievements": str(raw.get("achievements", ""))[:400],
        "representative_works": works,
    }


async def refresh_capability(db: AsyncSession, user: User) -> CapabilityProfile | None:
    ctx = await _gather_context(db, user)
    if not ctx["papers"]:
        logger.info("Capability: user %d has no papers, skipping", user.id)
        return None

    prompt = _build_prompt(user, ctx)

    async with httpx.AsyncClient(timeout=250) as client:
        result = await _query_llm(client, prompt)

    profiles: list[dict] = []
    primary_role = FALLBACK_ROLE
    primary_direction = ""
    rationale = ""

    if result and isinstance(result, dict):
        for p in (result.get("profiles") or [])[:5]:
            sp = _sanitize_profile(p)
            if sp and (sp["direction_zh"] or sp["direction_en"]):
                profiles.append(sp)
        # Sort profiles by weight desc
        profiles.sort(key=lambda p: -p["weight"])
        # Primary = top-weight profile (fall back to LLM's primary_* if missing)
        if profiles:
            primary_direction = profiles[0]["direction_zh"] or profiles[0]["direction_en"]
            primary_role = profiles[0]["role"]
        pr = str(result.get("primary_role", "")).strip().lower()
        if pr in VALID_ROLES:
            primary_role = pr
        pd = str(result.get("primary_direction", "")).strip()
        if pd:
            primary_direction = pd
        rationale = str(result.get("rationale", ""))[:300]
    else:
        logger.warning("Capability: LLM failed for user %d", user.id)

    existing = (await db.execute(
        select(CapabilityProfile).where(CapabilityProfile.user_id == user.id)
    )).scalars().first()
    if existing:
        existing.primary_role = primary_role
        existing.primary_direction = primary_direction
        existing.profiles_json = profiles
        existing.rationale = rationale
        existing.refreshed_at = datetime.utcnow()
        profile = existing
    else:
        profile = CapabilityProfile(
            user_id=user.id,
            primary_role=primary_role,
            primary_direction=primary_direction,
            profiles_json=profiles,
            rationale=rationale,
            refreshed_at=datetime.utcnow(),
        )
        db.add(profile)

    await db.flush()
    logger.info(
        "Capability refreshed for user %d: %d directions, primary=%s/%s",
        user.id, len(profiles), primary_direction, primary_role,
    )
    return profile
