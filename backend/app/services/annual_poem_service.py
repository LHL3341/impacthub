"""Annual poem service: Xiaohongshu-style poetic year-in-review for researchers.

Gathers this year's key facts (new papers, citation delta, milestones, top paper,
repos created, community buzz highlights), then asks the LLM to write 5-6 short
verses in Chinese that weave the numbers into a poetic retrospective. Output is
cached per (user, year).
"""

import json
import logging
import re
from datetime import datetime, date

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_BUZZ_MODEL, LLM_FALLBACK_MODEL
from app.models import (
    User, Paper, GithubRepo, HFItem,
    DataSnapshot, Milestone, BuzzSnapshot,
    AnnualPoem,
)
from app.utils.paper_dedup import deduplicate_papers

logger = logging.getLogger(__name__)


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


async def _gather_year_stats(db: AsyncSession, user: User, year: int) -> dict:
    """Collect the year's concrete facts for the LLM to weave into verses."""
    uid = user.id

    # All papers, for dedup + year filter
    papers_raw = (await db.execute(
        select(Paper).where(Paper.user_id == uid)
    )).scalars().all()
    papers = deduplicate_papers(papers_raw)
    papers_this_year = [p for p in papers if p.year == year]
    papers_this_year.sort(key=lambda p: (p.citation_count or 0), reverse=True)

    # Venue distribution this year
    venue_set: list[str] = []
    seen_venue = set()
    for p in papers_this_year:
        v = (p.venue or "").split("|")[0].strip()
        if v and v not in seen_venue:
            seen_venue.add(v)
            venue_set.append(v)

    # Repos created this year
    repos = (await db.execute(
        select(GithubRepo).where(GithubRepo.user_id == uid)
    )).scalars().all()
    repos_this_year = [r for r in repos if r.created_at_remote and r.created_at_remote.year == year]
    repos_this_year.sort(key=lambda r: (r.stars or 0), reverse=True)
    top_new_repo = repos_this_year[0] if repos_this_year else None

    # HF items (they lack creation dates; skip year filter)
    hf_items = (await db.execute(
        select(HFItem).where(HFItem.user_id == uid)
    )).scalars().all()

    # Citation delta from DataSnapshot (compare earliest snapshot in year vs latest)
    y_start = date(year, 1, 1)
    y_end = date(year, 12, 31)
    snap_rows = (await db.execute(
        select(DataSnapshot).where(
            and_(
                DataSnapshot.user_id == uid,
                DataSnapshot.metric_type == "total_citations",
                DataSnapshot.snapshot_date >= y_start,
                DataSnapshot.snapshot_date <= y_end,
            )
        ).order_by(DataSnapshot.snapshot_date)
    )).scalars().all()
    cit_delta = None
    if snap_rows:
        first_val = snap_rows[0].value
        last_val = snap_rows[-1].value
        delta = int(last_val - first_val)
        if delta >= 0:
            cit_delta = delta

    # Milestones crossed this year
    milestones = (await db.execute(
        select(Milestone).where(
            and_(
                Milestone.user_id == uid,
                Milestone.achieved_at >= datetime(year, 1, 1),
                Milestone.achieved_at <= datetime(year, 12, 31, 23, 59, 59),
            )
        )
    )).scalars().all()
    total_milestones = [m for m in milestones if m.metric_key == "__total__"]

    # Buzz topics (optional flavor)
    buzz = (await db.execute(
        select(BuzzSnapshot).where(BuzzSnapshot.user_id == uid)
    )).scalars().first()
    buzz_topics = buzz.topics[:5] if buzz and isinstance(buzz.topics, list) else []

    return {
        "user": user,
        "year": year,
        "paper_count": len(papers_this_year),
        "papers_this_year": papers_this_year[:10],
        "venue_set": venue_set[:6],
        "repo_count": len(repos_this_year),
        "top_new_repo": top_new_repo,
        "hf_count": len(hf_items),
        "citation_delta": cit_delta,
        "milestone_total": len(total_milestones),
        "milestones": total_milestones[:5],
        "buzz_topics": buzz_topics,
        "total_paper_count": len(papers),
    }


def _build_prompt(stats: dict) -> str:
    user: User = stats["user"]
    year: int = stats["year"]
    name = user.name or user.github_username or "研究者"

    facts_lines: list[str] = []
    if stats["paper_count"]:
        facts_lines.append(f"- 本年发表论文 {stats['paper_count']} 篇")
    # Full paper listing with author lists — let LLM judge author position
    if stats["papers_this_year"]:
        facts_lines.append(f"- 本年论文明细（含作者列表，按引用量降序；研究者姓名：{name}）：")
        for p in stats["papers_this_year"]:
            authors = p.authors_json if isinstance(p.authors_json, list) else []
            n = len(authors)
            if n == 0:
                au_str = "(未知作者列表)"
            elif n <= 5:
                au_str = ", ".join(authors)
            else:
                au_str = ", ".join(authors[:3]) + f" … {authors[-1]}"  # show first 3 + last (通讯位)
            facts_lines.append(
                f"  · 《{p.title}》（{p.venue or '?'}，引用 {p.citation_count}，共 {n} 作者：{au_str}）"
            )
    if stats["venue_set"]:
        facts_lines.append(f"- 覆盖期刊/会议：{', '.join(stats['venue_set'])}")
    if stats["citation_delta"] is not None:
        facts_lines.append(f"- 新增引用约 {stats['citation_delta']} 次")
    if stats["repo_count"]:
        facts_lines.append(f"- 本年新增 GitHub 仓库 {stats['repo_count']} 个")
    if stats["top_new_repo"]:
        r = stats["top_new_repo"]
        facts_lines.append(f"- 代表开源项目：{r.repo_name}（{r.stars} stars）")
    if stats["milestone_total"]:
        milestones = stats["milestones"]
        ms_desc = "、".join(f"{m.metric_type} 突破 {m.threshold}" for m in milestones[:3])
        facts_lines.append(f"- 解锁里程碑：{ms_desc}")
    if stats["buzz_topics"]:
        facts_lines.append(f"- 社区讨论话题：{', '.join(stats['buzz_topics'])}")

    facts_block = "\n".join(facts_lines) if facts_lines else "（本年公开数据较少）"
    bio_line = f"\n研究者简介：{user.bio}" if user.bio else ""

    return f"""你是一位擅长写作现代中文短诗的科研笔记作家。请为研究者「{name}」撰写 {year} 年的 **年度诗篇**——**小红书/网易云「年度诗篇」风格**，数据驱动，诗意、克制、有呼吸感。

研究者数据：{bio_line}
{facts_block}

### 风格参考（小红书年度诗篇模板的典型结构）

```
在某某时候                     ← 1. 开篇设景，时间/场景起笔
我做了 XX 件事                  ← 2-3. 具体动作 + 具体数字
XX 次成功，XX 次失败            ←
但 2025 不只这些                ← 4. 转折连接
我还……                         ← 5-10. 「我 XX 了 XX」式排比，堆叠具体事件
……写了 XX 篇论文               ←        每行一件事，节奏密集
……被 XX 次引用                ←        混用情感与数据，忌空洞
……遇到了 XX 个合作者           ←
有些是惊喜，有些是意外           ← 11-12. 短暂抒情/自嘲/黑色幽默
原来 XX 和 XX                  ←        可带一句"原来…"式感悟
是同一件事的两面                ←
2026 我想                      ← 13-14. 结尾展望，留开口不写满
再鲁莽一次                      ←
```

### 硬性要求
1. **总共 10-14 行**，绝大多数行 **8-18 个汉字**（紧凑、有节奏），偶尔可有一行更短或更长做停顿。
2. **每行尽量一个画面或一件具体的事**，切忌空洞抒情。用 "我 XX 了 XX"、"XX 了 XX 次" 的排比堆。
3. **把真实数据融进诗句**（论文数、引用增长、代表作主题、合作者频次、venue 等）——**具体数字要出现**，但用诗化方式，不要直接写"12 篇论文"可以是"十二次深夜按下提交键"。
4. 开篇 **设情境**（例如"在冬夜里"/"那年春天"/"凌晨四点"），结尾 **留开口**（指向下一年的未尽之事，不要写得太满）。
5. 风格克制，**避免过度煽情和赞美**，允许一点点自嘲、疲惫、黑色幽默。
6. 不强求押韵，但有内在节奏（行内停顿感）。
7. 不要出现"加油"、"致敬"、"向前"、"坚持"这种鸡汤套话。
8. 另外提取 **3-4 个关键数据亮点**（label + value），用于卡片底部数据区。label 保持 2-4 个中文字，value 是醒目数字或短语。
   - **作者位置判断**（很重要）：遍历上面"本年论文明细"的作者列表，对比研究者姓名 {name}。
     - **第一作者** = 作者列表第 1 位是本人 → 算**代表作**，这是主导工作
     - **通讯作者 / 最后一作** = 作者列表最后一位是本人（且不是独作），对**资深学者**也算代表作（PI 工作）；对新锐研究者一般是导师位置，不算本人代表作
     - **中间作者** = 夹在中间 = 只是参与，**绝对不能写成代表作**
   - 只有确实存在代表作（第一作者 / 资深通讯作者）时，才可以用「代表作」作 label；否则换成「参与作品」「合作 venue」「引用增长」「新增仓库」等。
9. 选一个 **theme 色系**：`indigo`（深沉学术）/ `amber`（温暖丰收）/ `emerald`（生长蓬勃）/ `rose`（柔和温情），贴合本年情绪。
10. 出一个 4-10 字的诗篇标题，点题而不套话（例："退稿与热爱"、"提交键按了 327 次"）。

### 严格 JSON 输出（仅输出 JSON，不加 markdown 代码块、不加任何其他文字）
{{
  "title": "标题",
  "verses": [
    "第一行（开篇设景）",
    "第二行",
    "第三行",
    "...",
    "最后一行（结尾展望，留白）"
  ],
  "highlights": [
    {{"label": "论文", "value": "12 篇"}},
    {{"label": "引用增长", "value": "+5,231"}},
    {{"label": "代表作", "value": "某某主题"}}
  ],
  "theme": "indigo"
}}"""


async def _query_llm(client: httpx.AsyncClient, prompt: str) -> str | None:
    """Primary: Responses API. Fallback: Chat Completions on mini model."""
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/responses",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_BUZZ_MODEL,
                "input": prompt,
                "max_output_tokens": 6000,
            },
            timeout=180,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            t = c.get("text", "")
                            if t:
                                return t
    except Exception as e:
        logger.info("AnnualPoem Responses API failed (%s), falling back", e)

    try:
        resp = await client.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_FALLBACK_MODEL,
                "messages": [{"role": "user", "content": prompt + "\n\n再次强调：只输出 JSON。"}],
                "max_completion_tokens": 2000,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            logger.warning("AnnualPoem Chat API returned %d: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        return data["choices"][0]["message"].get("content", "")
    except Exception as e:
        logger.warning("AnnualPoem Chat API failed: %s", e)
        return None


THEMES = {"indigo", "amber", "emerald", "rose"}


async def refresh_annual_poem(db: AsyncSession, user: User, year: int) -> AnnualPoem | None:
    """Generate & cache a year's poem for a user."""
    stats = await _gather_year_stats(db, user, year)
    # Need at least some activity to make a meaningful poem
    if stats["paper_count"] == 0 and stats["repo_count"] == 0 and stats["citation_delta"] in (None, 0):
        logger.info("AnnualPoem: user %d has no activity in %d", user.id, year)
        return None

    prompt = _build_prompt(stats)

    async with httpx.AsyncClient(timeout=200) as client:
        content = await _query_llm(client, prompt)
    if not content:
        logger.warning("AnnualPoem: LLM returned nothing for user %d year %d", user.id, year)
        return None

    parsed = _parse_json(content)
    if not parsed or not isinstance(parsed, dict):
        logger.warning("AnnualPoem: parse failed for user %d year %d. Head: %s", user.id, year, content[:200])
        return None

    title = str(parsed.get("title", "") or "")[:40]
    verses_raw = parsed.get("verses") or []
    if not isinstance(verses_raw, list):
        verses_raw = []
    verses = [str(v)[:60] for v in verses_raw if str(v).strip()][:16]
    highlights_raw = parsed.get("highlights") or []
    highlights: list[dict] = []
    if isinstance(highlights_raw, list):
        for h in highlights_raw[:6]:
            if not isinstance(h, dict):
                continue
            label = str(h.get("label", ""))[:10]
            value = str(h.get("value", ""))[:30]
            if label and value:
                highlights.append({"label": label, "value": value})
    theme = str(parsed.get("theme", "indigo"))
    if theme not in THEMES:
        theme = "indigo"

    content_json = {
        "title": title,
        "verses": verses,
        "highlights": highlights,
        "theme": theme,
    }

    # Upsert by (user_id, year)
    existing = (await db.execute(
        select(AnnualPoem).where(and_(AnnualPoem.user_id == user.id, AnnualPoem.year == year))
    )).scalars().first()
    if existing:
        existing.content_json = content_json
        existing.refreshed_at = datetime.utcnow()
        poem = existing
    else:
        poem = AnnualPoem(
            user_id=user.id,
            year=year,
            content_json=content_json,
            refreshed_at=datetime.utcnow(),
        )
        db.add(poem)

    await db.flush()
    logger.info(
        "AnnualPoem refreshed for user %d year %d: %d verses, %d highlights, theme=%s",
        user.id, year, len(verses), len(highlights), theme,
    )
    return poem
