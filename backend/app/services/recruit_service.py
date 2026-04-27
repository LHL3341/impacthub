"""B2B recruiter talent search.

Two-stage LLM workflow:
  1. Extract structured criteria from the recruiter's free-text JD/requirements
  2. Coarse-filter the visible-user DB by direction / honors / quantitative thresholds
  3. Build compact candidate dossiers (top papers + repos + capability summary + AI tags)
  4. LLM rerank: pick top-K with match score + fit reasoning + concerns

Returns a structured payload the frontend can render directly.
"""

import json
import logging
import re
from collections import defaultdict
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_BUZZ_MODEL, LLM_FALLBACK_MODEL
from app.models import (
    User, Paper, GithubRepo, HFItem,
    AISummary, CapabilityProfile, ResearcherPersona,
)
from app.utils.paper_dedup import deduplicate_papers

logger = logging.getLogger(__name__)

VALID_DIRECTIONS = {"llm", "cv", "vlm", "systems", "theory", "rl"}
VALID_SENIORITY = {"senior", "mid", "junior", "any"}

COARSE_LIMIT = 40   # max candidates fed to the rerank stage
DEFAULT_TOP_K = 10   # default candidates returned to the recruiter


# ──────────────────────────── JSON helpers ────────────────────────────

def _parse_json(text: str) -> dict | None:
    if not text:
        return None
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


async def _call_llm(client: httpx.AsyncClient, prompt: str, *, max_tokens: int = 6000) -> dict | None:
    """Call LLM with Responses API → Chat Completions fallback. Expect JSON output."""
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/responses",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_BUZZ_MODEL,
                "input": prompt,
                "max_output_tokens": max_tokens,
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
        logger.info("Recruit Responses API failed (%s), falling back", e)

    try:
        resp = await client.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_FALLBACK_MODEL,
                "messages": [{"role": "user", "content": prompt + "\n\n再次强调：只输出 JSON。"}],
                "max_completion_tokens": max_tokens,
            },
            timeout=180,
        )
        if resp.status_code != 200:
            logger.warning("Recruit Chat API %d: %s", resp.status_code, resp.text[:200])
            return None
        return _parse_json(resp.json()["choices"][0]["message"].get("content", ""))
    except Exception as e:
        logger.warning("Recruit Chat API failed: %s", e)
        return None


# ──────────────────────────── Stage 1: Criteria extraction ────────────────────────────

CRITERIA_PROMPT = """你是一位资深 AI/CS 领域猎头顾问。下面是猎头给出的岗位需求描述，请你把自由文本拆解成**结构化的检索条件**，让后续系统能在学者数据库里筛人。

### 岗位需求原文
{jd}

### 输出要求（严格 JSON，不要 markdown）
{{
  "intent_summary": "一句话概括这个岗位在找什么样的人（30-60 字）",
  "research_directions": ["llm" | "cv" | "vlm" | "systems" | "theory" | "rl"],
  "must_have_keywords": ["RLHF", "alignment", ...],
  "nice_to_have_keywords": ["safety", ...],
  "seniority": "senior" | "mid" | "junior" | "any",
  "min_h_index": 0,
  "min_paper_count": 0,
  "min_ccf_a_count": 0,
  "min_total_stars": 0,
  "needs_open_source": false,
  "needs_industry_experience": false,
  "honors_preferred": ["IEEE Fellow", "杰青", "ACM Fellow", "院士", "Turing Award", ...],
  "exclude_keywords": [],
  "ranking_priority": "学术影响力" | "工程能力" | "方向匹配度" | "综合"
}}

### 字段说明
- `research_directions`: 只能从 llm/cv/vlm/systems/theory/rl 这 6 个标签中挑（小写）。如果 JD 里方向写得很泛或不确定，给空数组 []。
- `seniority`:
  - senior = 资深/PI/教授/总监级别
  - mid = 中坚/副教授/资深研究员/工程师
  - junior = 应届/博士在读/博士后/校招
  - any = JD 没有明确说，或希望都看
- `min_h_index`/`min_paper_count`/`min_ccf_a_count`/`min_total_stars`: 给出**保守门槛**；JD 没写就给 0；JD 说"必须有顶会论文"就给 min_ccf_a_count=2-5。
- `needs_open_source`: JD 强调开源贡献/repo/工程能力时设 true
- `needs_industry_experience`: JD 是工业界岗位、强调落地经验时设 true
- `honors_preferred`: JD 明确提到的头衔；可空
- `exclude_keywords`: JD 明确不要的（如"不要纯理论"）
- `ranking_priority`: 排序时哪一维最重要。综合 = 都重要

只输出 JSON。
"""


async def extract_criteria(client: httpx.AsyncClient, jd: str) -> dict:
    """Stage 1: parse JD text into structured search criteria."""
    prompt = CRITERIA_PROMPT.format(jd=jd.strip()[:4000])
    raw = await _call_llm(client, prompt, max_tokens=2000)
    return _sanitize_criteria(raw or {})


def _sanitize_criteria(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raw = {}

    dirs = []
    for d in raw.get("research_directions") or []:
        d = str(d).strip().lower()
        if d in VALID_DIRECTIONS and d not in dirs:
            dirs.append(d)

    seniority = str(raw.get("seniority", "any")).strip().lower()
    if seniority not in VALID_SENIORITY:
        seniority = "any"

    def _int(key: str, default: int = 0) -> int:
        try:
            return max(0, int(raw.get(key) or 0))
        except (TypeError, ValueError):
            return default

    must = [str(k).strip() for k in (raw.get("must_have_keywords") or []) if str(k).strip()][:12]
    nice = [str(k).strip() for k in (raw.get("nice_to_have_keywords") or []) if str(k).strip()][:12]
    honors = [str(k).strip() for k in (raw.get("honors_preferred") or []) if str(k).strip()][:8]
    excl = [str(k).strip() for k in (raw.get("exclude_keywords") or []) if str(k).strip()][:8]

    priority = str(raw.get("ranking_priority", "综合")).strip() or "综合"

    return {
        "intent_summary": str(raw.get("intent_summary", ""))[:200],
        "research_directions": dirs,
        "must_have_keywords": must,
        "nice_to_have_keywords": nice,
        "seniority": seniority,
        "min_h_index": _int("min_h_index"),
        "min_paper_count": _int("min_paper_count"),
        "min_ccf_a_count": _int("min_ccf_a_count"),
        "min_total_stars": _int("min_total_stars"),
        "needs_open_source": bool(raw.get("needs_open_source")),
        "needs_industry_experience": bool(raw.get("needs_industry_experience")),
        "honors_preferred": honors,
        "exclude_keywords": excl,
        "ranking_priority": priority,
    }


# ──────────────────────────── Stage 2: Coarse filtering ────────────────────────────

async def _load_visible_users(db: AsyncSession) -> list[User]:
    return (await db.execute(
        select(User).where(User.visible == True)  # noqa: E712
    )).scalars().all()


def _compute_user_metrics(papers: list[Paper], repos: list[GithubRepo]) -> dict:
    deduped = deduplicate_papers(papers)
    citations = sorted([p.citation_count or 0 for p in deduped], reverse=True)
    h = 0
    for i, c in enumerate(citations):
        if c >= i + 1:
            h = i + 1
        else:
            break
    years = [p.year for p in deduped if p.year and p.year > 0]
    return {
        "h_index": h,
        "total_citations": sum(citations),
        "paper_count": len(deduped),
        "ccf_a_count": sum(1 for p in deduped if (p.ccf_rank or "") == "A"),
        "ccf_b_count": sum(1 for p in deduped if (p.ccf_rank or "") == "B"),
        "total_stars": sum(r.stars or 0 for r in repos),
        "first_paper_year": min(years) if years else None,
        "papers_dedup": deduped,
    }


def _coarse_filter(
    users: list[User],
    metrics_by_uid: dict[int, dict],
    capability_by_uid: dict[int, CapabilityProfile],
    criteria: dict,
) -> list[User]:
    """Apply hard quantitative filters; return survivors sorted by composite score."""
    dirs = set(criteria["research_directions"])
    min_h = criteria["min_h_index"]
    min_papers = criteria["min_paper_count"]
    min_ccf_a = criteria["min_ccf_a_count"]
    min_stars = criteria["min_total_stars"]
    needs_oss = criteria["needs_open_source"]
    honors_pref = set(criteria["honors_preferred"])
    excl = [k.lower() for k in criteria["exclude_keywords"]]
    must = [k.lower() for k in criteria["must_have_keywords"]]
    nice = [k.lower() for k in criteria["nice_to_have_keywords"]]

    scored: list[tuple[float, User]] = []
    for u in users:
        m = metrics_by_uid.get(u.id, {})
        if not m:
            continue
        if m["h_index"] < min_h:
            continue
        if m["paper_count"] < min_papers:
            continue
        if m["ccf_a_count"] < min_ccf_a:
            continue
        if m["total_stars"] < min_stars:
            continue
        if needs_oss and m["total_stars"] < 1:
            continue

        # Direction filter: prefer matching, but don't reject if user has no labelled dir
        if dirs and u.research_direction:
            if u.research_direction not in dirs:
                continue

        # Build searchable haystack: bio + paper titles + capability directions
        cap = capability_by_uid.get(u.id)
        haystack_parts = [(u.bio or "").lower()]
        for p in m["papers_dedup"][:30]:
            haystack_parts.append((p.title or "").lower())
        if cap and cap.profiles_json:
            for prof in cap.profiles_json:
                haystack_parts.append(str(prof.get("direction_zh", "")).lower())
                haystack_parts.append(str(prof.get("direction_en", "")).lower())
                haystack_parts.append(str(prof.get("achievements", "")).lower())
        haystack = " ".join(haystack_parts)

        if any(k in haystack for k in excl):
            continue

        # Composite score for coarse ranking
        score = 0.0
        score += min(m["h_index"], 80) / 80.0 * 30
        score += min(m["ccf_a_count"], 30) / 30.0 * 15
        score += min(m["total_stars"], 20000) / 20000.0 * 15
        if dirs and u.research_direction in dirs:
            score += 15
        if must:
            hit = sum(1 for k in must if k in haystack)
            score += (hit / len(must)) * 25 if must else 0
        if nice:
            hit_n = sum(1 for k in nice if k in haystack)
            score += (hit_n / len(nice)) * 10
        if honors_pref and u.honor_tags:
            user_honors = {str(h) for h in (u.honor_tags or [])}
            if user_honors & honors_pref:
                score += 20
        scored.append((score, u))

    scored.sort(key=lambda x: -x[0])
    return [u for _, u in scored[:COARSE_LIMIT]]


# ──────────────────────────── Stage 3: Build dossiers + LLM rerank ────────────────────────────

def _build_dossier(
    user: User,
    metrics: dict,
    capability: CapabilityProfile | None,
    ai_summary: AISummary | None,
    repos: list[GithubRepo],
    persona_code: str | None,
) -> dict:
    """Compact, LLM-friendly summary of a candidate."""
    deduped = metrics["papers_dedup"]
    top_papers = sorted(deduped, key=lambda p: -(p.citation_count or 0))[:8]
    top_repos = sorted(repos, key=lambda r: -(r.stars or 0))[:5]

    cap_lines = []
    if capability and capability.profiles_json:
        for prof in capability.profiles_json[:4]:
            cap_lines.append({
                "direction": prof.get("direction_zh") or prof.get("direction_en", ""),
                "role": prof.get("role", ""),
                "weight": prof.get("weight", 0),
                "achievements": (prof.get("achievements") or "")[:160],
            })

    return {
        "user_id": user.id,
        "name": user.name or user.github_username or f"user_{user.id}",
        "bio": (user.bio or "")[:240],
        "honors": list(user.honor_tags or []),
        "research_direction": user.research_direction or "",
        "persona_code": persona_code or "",
        "metrics": {
            "h_index": metrics["h_index"],
            "total_citations": metrics["total_citations"],
            "paper_count": metrics["paper_count"],
            "ccf_a_count": metrics["ccf_a_count"],
            "total_stars": metrics["total_stars"],
            "first_paper_year": metrics["first_paper_year"],
        },
        "capability_directions": cap_lines,
        "ai_tags": list(ai_summary.tags or [])[:8] if ai_summary else [],
        "ai_summary": (ai_summary.summary or "")[:240] if ai_summary else "",
        "top_papers": [
            {
                "title": (p.title or "")[:140],
                "year": p.year or 0,
                "venue": (p.venue or "")[:60],
                "ccf_rank": p.ccf_rank or "",
                "citation_count": p.citation_count or 0,
            }
            for p in top_papers
        ],
        "top_repos": [
            {
                "name": (r.repo_name or "")[:80],
                "stars": r.stars or 0,
                "language": r.language or "",
                "description": (r.description or "")[:120],
            }
            for r in top_repos
        ],
    }


RERANK_PROMPT = """你是一位资深 AI/CS 猎头顾问，正在为一个具体岗位评估候选学者。

### 岗位需求（结构化）
{criteria}

### 候选学者列表（按粗筛分数排序）
共 {n} 位候选人。每条候选人包含基础指标、能力画像方向、AI 标签、代表论文、代表 repo。

{candidates}

### 任务
从候选名单中挑出最匹配岗位的 **{top_k} 位**（如果合适人选少于 {top_k}，宁缺毋滥）。对每位入选者，给出：

- `match_score` (0-100): 综合匹配度
- `tier`: "perfect"（完美匹配）/ "strong"（强匹配，多数维度达标）/ "potential"（潜力候选，部分维度突出但有缺口）
- `fit_reasoning`: 为什么这个人适合这个岗位（1-2 句中文，**结合具体作品/方向/数据**，避免泛泛而谈）
- `highlights`: 3-5 条最闪光的卖点（每条 ≤30 字，**具体**，例如"vLLM 一作，38k stars 开源主力"而不是"开源能力强"）
- `concerns`: 0-3 条潜在差距或风险（≤30 字，例如"主要在工业界、学术发表节奏放缓"，没有就空数组）
- `key_works`: 1-3 篇最契合岗位的代表作（直接复制候选人列表里的论文标题）

### 输出（严格 JSON，不要 markdown，不要解释）
{{
  "ranked": [
    {{
      "user_id": 1,
      "name": "学者姓名",
      "match_score": 92,
      "tier": "perfect",
      "fit_reasoning": "...",
      "highlights": ["...", "..."],
      "concerns": ["..."],
      "key_works": ["论文标题 1", "论文标题 2"]
    }}
  ],
  "search_summary": "用 1-2 句话总结本次匹配整体情况（例如：找到 8 位完美匹配的视觉生成方向资深学者，多在工业界）"
}}

排序要求：
- `match_score` 从高到低排
- 不要无脑选粗筛 top；如果某个粗筛靠后的人在岗位关键维度上更突出，他可以排到前面
- 如果有候选人完全不匹配核心要求（例如方向完全无关），就不要纳入
"""


async def rerank_candidates(
    client: httpx.AsyncClient,
    criteria: dict,
    dossiers: list[dict],
    top_k: int,
) -> dict:
    """Stage 3: LLM picks top-K with reasoning."""
    if not dossiers:
        return {"ranked": [], "search_summary": "未找到符合条件的候选人，请放宽筛选条件后再试。"}

    candidate_block = json.dumps(dossiers, ensure_ascii=False, indent=2)
    prompt = RERANK_PROMPT.format(
        criteria=json.dumps(criteria, ensure_ascii=False, indent=2),
        n=len(dossiers),
        candidates=candidate_block,
        top_k=top_k,
    )
    raw = await _call_llm(client, prompt, max_tokens=8000)
    if not raw or not isinstance(raw, dict):
        # Fallback: return top dossiers without LLM commentary
        return {
            "ranked": [
                {
                    "user_id": d["user_id"],
                    "name": d["name"],
                    "match_score": max(40, 90 - i * 4),
                    "tier": "strong" if i < 3 else "potential",
                    "fit_reasoning": "AI 排序失败，按粗筛分数返回。",
                    "highlights": [],
                    "concerns": [],
                    "key_works": [p["title"] for p in d["top_papers"][:2]],
                }
                for i, d in enumerate(dossiers[:top_k])
            ],
            "search_summary": "AI 评分服务暂时失败，已返回粗筛 top 结果。",
        }
    return _sanitize_rerank(raw, top_k)


def _sanitize_rerank(raw: dict, top_k: int) -> dict:
    ranked = []
    for r in (raw.get("ranked") or [])[:top_k]:
        if not isinstance(r, dict):
            continue
        try:
            uid = int(r.get("user_id"))
        except (TypeError, ValueError):
            continue
        try:
            score = max(0, min(100, int(round(float(r.get("match_score", 0))))))
        except (TypeError, ValueError):
            score = 0
        tier = str(r.get("tier", "potential")).strip().lower()
        if tier not in {"perfect", "strong", "potential"}:
            tier = "potential"
        ranked.append({
            "user_id": uid,
            "name": str(r.get("name", ""))[:120],
            "match_score": score,
            "tier": tier,
            "fit_reasoning": str(r.get("fit_reasoning", ""))[:400],
            "highlights": [str(h)[:80] for h in (r.get("highlights") or [])][:5],
            "concerns": [str(c)[:80] for c in (r.get("concerns") or [])][:3],
            "key_works": [str(w)[:200] for w in (r.get("key_works") or [])][:3],
        })
    return {
        "ranked": ranked,
        "search_summary": str(raw.get("search_summary", ""))[:400],
    }


# ──────────────────────────── Top-level orchestrator ────────────────────────────

def _decorate_results(
    ranked: list[dict],
    user_by_id: dict[int, User],
    metrics_by_uid: dict[int, dict],
    capability_by_uid: dict[int, CapabilityProfile],
    repos_by_uid: dict[int, list[GithubRepo]],
    persona_by_uid: dict[int, str],
) -> list[dict]:
    """Attach profile + metrics + key works back to LLM ranked list."""
    out = []
    for r in ranked:
        uid = r["user_id"]
        u = user_by_id.get(uid)
        if not u:
            continue
        m = metrics_by_uid.get(uid, {})
        cap = capability_by_uid.get(uid)
        primary_dir = ""
        if cap:
            primary_dir = cap.primary_direction or ""
        repos = repos_by_uid.get(uid, [])
        top_repos = sorted(repos, key=lambda x: -(x.stars or 0))[:3]
        # Match key_works strings back to actual paper records when possible
        key_paper_records = []
        deduped = m.get("papers_dedup", [])
        title_lookup = {(p.title or "").lower().strip(): p for p in deduped}
        for w in r["key_works"]:
            key = (w or "").lower().strip()
            if not key:
                continue
            paper = title_lookup.get(key)
            if not paper:
                # Try prefix / substring match
                for t, p in title_lookup.items():
                    if key in t or t in key:
                        paper = p
                        break
            if paper:
                key_paper_records.append({
                    "title": paper.title,
                    "year": paper.year or 0,
                    "venue": paper.venue or "",
                    "ccf_rank": paper.ccf_rank or "",
                    "citation_count": paper.citation_count or 0,
                    "url": paper.url or "",
                })
            else:
                key_paper_records.append({
                    "title": w, "year": 0, "venue": "", "ccf_rank": "",
                    "citation_count": 0, "url": "",
                })

        out.append({
            **r,
            "key_works": key_paper_records,
            "user": {
                "id": u.id,
                "name": u.name or u.github_username,
                "avatar_url": u.avatar_url,
                "scholar_id": u.scholar_id,
                "github_username": u.github_username,
                "homepage": u.homepage,
                "bio": (u.bio or "")[:300],
                "honor_tags": list(u.honor_tags or []),
                "research_direction": u.research_direction or "",
            },
            "metrics": {
                "h_index": m.get("h_index", 0),
                "total_citations": m.get("total_citations", 0),
                "paper_count": m.get("paper_count", 0),
                "ccf_a_count": m.get("ccf_a_count", 0),
                "total_stars": m.get("total_stars", 0),
                "first_paper_year": m.get("first_paper_year"),
            },
            "primary_direction": primary_dir,
            "persona_code": persona_by_uid.get(uid, ""),
            "top_repos": [
                {"name": r.repo_name, "stars": r.stars or 0, "url": r.url or ""}
                for r in top_repos
            ],
        })
    return out


async def search_talent(db: AsyncSession, jd: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """Main entry: JD → criteria → coarse filter → rerank → decorated results."""
    jd = (jd or "").strip()
    if not jd:
        return {
            "criteria": _sanitize_criteria({}),
            "results": [],
            "search_summary": "请输入岗位需求或人才画像描述。",
            "candidate_pool_size": 0,
        }

    async with httpx.AsyncClient(timeout=300) as client:
        criteria = await extract_criteria(client, jd)
        logger.info("Recruit criteria extracted: %s", criteria.get("intent_summary"))

        users = await _load_visible_users(db)
        if not users:
            return {
                "criteria": criteria,
                "results": [],
                "search_summary": "学者数据库为空。",
                "candidate_pool_size": 0,
            }

        user_ids = [u.id for u in users]
        # Bulk-load papers / repos / capability / ai_summary / persona
        papers = (await db.execute(
            select(Paper).where(Paper.user_id.in_(user_ids))
        )).scalars().all()
        repos = (await db.execute(
            select(GithubRepo).where(GithubRepo.user_id.in_(user_ids))
        )).scalars().all()
        caps = (await db.execute(
            select(CapabilityProfile).where(CapabilityProfile.user_id.in_(user_ids))
        )).scalars().all()
        summaries = (await db.execute(
            select(AISummary).where(AISummary.user_id.in_(user_ids))
        )).scalars().all()
        personas = (await db.execute(
            select(ResearcherPersona).where(ResearcherPersona.user_id.in_(user_ids))
        )).scalars().all()

        papers_by_uid: dict[int, list[Paper]] = defaultdict(list)
        for p in papers:
            papers_by_uid[p.user_id].append(p)
        repos_by_uid: dict[int, list[GithubRepo]] = defaultdict(list)
        for r in repos:
            repos_by_uid[r.user_id].append(r)
        caps_by_uid = {c.user_id: c for c in caps}
        summary_by_uid = {s.user_id: s for s in summaries}
        persona_by_uid = {p.user_id: p.persona_code for p in personas}

        metrics_by_uid: dict[int, dict] = {}
        for u in users:
            metrics_by_uid[u.id] = _compute_user_metrics(
                papers_by_uid.get(u.id, []),
                repos_by_uid.get(u.id, []),
            )

        survivors = _coarse_filter(users, metrics_by_uid, caps_by_uid, criteria)
        logger.info("Coarse filter: %d → %d candidates", len(users), len(survivors))

        if not survivors:
            return {
                "criteria": criteria,
                "results": [],
                "search_summary": (
                    f"按当前条件未匹配到候选人（候选池 {len(users)} 人）。"
                    "可尝试放宽方向、降低 h-index 门槛，或减少 must_have 关键词。"
                ),
                "candidate_pool_size": len(users),
            }

        dossiers = [
            _build_dossier(
                u,
                metrics_by_uid[u.id],
                caps_by_uid.get(u.id),
                summary_by_uid.get(u.id),
                repos_by_uid.get(u.id, []),
                persona_by_uid.get(u.id),
            )
            for u in survivors
        ]

        rerank = await rerank_candidates(client, criteria, dossiers, top_k)

    user_by_id = {u.id: u for u in users}
    results = _decorate_results(
        rerank["ranked"],
        user_by_id,
        metrics_by_uid,
        caps_by_uid,
        repos_by_uid,
        persona_by_uid,
    )

    return {
        "criteria": criteria,
        "results": results,
        "search_summary": rerank["search_summary"],
        "candidate_pool_size": len(users),
        "filtered_pool_size": len(survivors),
    }
