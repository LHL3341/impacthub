"""Generate 12 MBTI-style persona illustrations via gpt-image-1.

Uses a strict shared style preamble for all 12 personas so the outputs are
visually consistent, and unique character descriptions per persona (no code
letters in the description so the model doesn't misread GOAT as goat).

Usage:
    cd backend
    python -m scripts.generate_persona_images              # generate all
    python -m scripts.generate_persona_images --only GOAT  # just one
    python -m scripts.generate_persona_images --force      # regen even if PNG exists
"""

import argparse
import asyncio
import base64
import logging
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from app.config import LLM_API_BASE, LLM_API_KEY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).resolve().parent.parent / "static" / "personas"

STYLE_PREAMBLE = (
    "Character illustration in the exact visual language of the 16personalities.com / MBTI "
    "personality test result page — but rendered in LOW-POLY FLAT DESIGN: the character body is "
    "composed of simplified geometric shapes (triangles, trapezoids, polygonal blocks), no outlines, "
    "flat solid fills, no gradients. "
    "Facial features are minimal (tiny dot eyes, small mouth), with a clear DEADPAN / DARK-HUMOR vibe — "
    "the character is exhausted, over-it, or sarcastically resigned to their fate, never cheerful or cute. "
    "Think burnt-out researcher meme energy — like a 16personalities INFJ / INTP character but even more "
    "tired and self-aware. "
    "Restrained modern palette consistent across all personas: warm beige skin, dark grey hair, "
    "soft pale mint-green accent color, with a small amount of muted prop color. Very light (almost "
    "invisible) soft shadow. "
    "Plenty of white empty space around the character, clean infographic look, modern minimalist "
    "internet-meme feel. Character centered, full body visible, facing the viewer directly. "
    "No text, no letters, no numbers, no watermark, no logos."
)

# Character descriptions — DO NOT include the code letters (avoids GOAT→goat confusion)
CHARACTERS: dict[str, str] = {
    "GOAT": (
        "an ancient weary sage who should have retired 30 years ago but can't let go, "
        "long snow-white beard, dark-blue scholar robe, tilted small graduation cap, "
        "holding yet another yellow submission scroll with resigned expression, "
        "standing on a tiny mountain peak with slightly hunched back, tired half-closed eyes"
    ),
    "PI": (
        "a hollow-eyed middle-aged professor with a slightly too-small crown wobbling on head, "
        "crumpled lab coat, forced polite smile, holding a clipboard, "
        "surrounded by three tiny demanding student figures pulling at his coat, looking slightly drained"
    ),
    "WOLF": (
        "a lone young researcher with thousand-yard stare and dark under-eye circles, "
        "wearing oversized dark grey hoodie with subtle wolf-ear hood, round glasses, "
        "holding a laptop, expression is unbothered-but-tired, standing alone, no one else around"
    ),
    "VIRAL": (
        "a manic young developer with bloodshot wide eyes and forced smile, "
        "awkwardly clinging to a small cartoon rocket leaving star trails, "
        "looking like he's not sure he's actually in control, modern hoodie and sneakers"
    ),
    "QED": (
        "a thin ancient-looking mathematician with completely blank dot eyes and flat line mouth, "
        "propping up his tired face with one bony hand in absolute existential boredom, "
        "a giant floating cloud of incomprehensible mathematical symbols (∀ ∃ ∑ ∫ ∞ π) chaotically surrounding him, "
        "chalk dust smeared on his bow-tie and robe, holding a piece of chalk in the other hand, "
        "one eyebrow very slightly raised in silent contempt, 'I already finished your thesis in my head' energy"
    ),
    "SENSEI": (
        "a tired but outwardly serene old master with long grey beard and traditional Chinese hanfu, "
        "holding ancient scrolls, two tiny needy disciples clinging to his robe begging for attention, "
        "expression is patient-but-worn-down"
    ),
    "MONK": (
        "a minimalist young shaved-head monk in simple saffron robes, sitting cross-legged in lotus position, "
        "tiny dot eyes with unsettling empty stare, holding a single holy research paper like it's his whole world, "
        "subtle halo behind head, 'I only submit once a year' energy"
    ),
    "HYPE": (
        "a slightly too-enthusiastic young scholar in graduation gown with slightly manic over-wide smile, "
        "clutching a fan of golden offer letters desperately like they prove his worth, "
        "small sparkle aura, vibes of 'please hire me I'm great'"
    ),
    "NINJA": (
        "a hooded dev ninja with full thousand-yard stare, ninja mask pulled down, "
        "holding a laptop and a shuriken, a coffee mug near feet attached to IV-like drip tube, "
        "floating code brackets around, awake-for-72-hours vibe"
    ),
    "BDFL": (
        "a bearded maker in a blue maker apron, carrying a huge golden star on his back like a burden, "
        "surrounded by demanding floating gears and a globe, "
        "polite but visibly tired smile — running the entire open source world by himself"
    ),
    "JUAN": (
        "a bloodshot-eyed young researcher with deep dark under-eye bags and intensely manic focused stare, "
        "multiple paper sheets chaotically flying around, holding a giant coffee cup like a lifeline, "
        "warm flame aura behind, dead-tired but unstoppable"
    ),
    "MILL": (
        "a completely glazed-over worker with utterly dead empty dot eyes and vacant slack-jawed expression, "
        "standing robotically behind an assembly-line paper-printing machine that is absurdly spitting out "
        "an enormous tower of identical papers that has already buried his legs up to the knees, "
        "one hand mechanically stamping papers, wearing a slightly drooping worker cap, "
        "'clocked in 15 hours ago, still here' energy, deeply fried inside"
    ),
}


async def _generate_one(client: httpx.AsyncClient, code: str, description: str) -> bytes | None:
    prompt = f"{STYLE_PREAMBLE}\n\nCharacter (do not render text or letters): {description}"
    try:
        resp = await client.post(
            f"{LLM_API_BASE}/images/generations",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": "gpt-image-1",
                "prompt": prompt,
                "size": "1024x1024",
                "n": 1,
                "background": "transparent",
                "quality": "medium",
            },
            timeout=300,
        )
        if resp.status_code != 200:
            logger.warning("Image gen for %s failed: %d %s", code, resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        b64 = data["data"][0].get("b64_json")
        if not b64:
            logger.warning("No b64_json for %s", code)
            return None
        return base64.b64decode(b64)
    except Exception as e:
        logger.warning("Image gen error for %s: %s", code, e)
        return None


def _optimize(png_bytes: bytes, target_size: int = 512) -> bytes:
    """Resize to target_size × target_size and optimize file size."""
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    img.thumbnail((target_size, target_size), Image.LANCZOS)
    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default="", help="Generate only this one code")
    parser.add_argument("--force", action="store_true", help="Overwrite existing PNGs")
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    codes = [args.only] if args.only else list(CHARACTERS.keys())
    codes = [c for c in codes if c in CHARACTERS]

    # Skip existing unless --force
    todo = []
    for code in codes:
        path = OUT_DIR / f"{code}.png"
        if path.exists() and not args.force:
            logger.info("⏭  %s already exists, skip", code)
            continue
        todo.append(code)

    if not todo:
        logger.info("Nothing to do.")
        return

    logger.info("Generating %d images → %s (concurrency=%d)", len(todo), OUT_DIR, args.concurrency)

    semaphore = asyncio.Semaphore(args.concurrency)
    ok = 0
    fail = 0

    async def _worker(code: str):
        nonlocal ok, fail
        async with semaphore:
            logger.info("▶ %s", code)
            async with httpx.AsyncClient(timeout=310) as client:
                raw = await _generate_one(client, code, CHARACTERS[code])
            if not raw:
                fail += 1
                return
            optimized = _optimize(raw, target_size=512)
            path = OUT_DIR / f"{code}.png"
            path.write_bytes(optimized)
            logger.info("  ✓ %s → %s (%d KB)", code, path.name, len(optimized) // 1024)
            ok += 1

    await asyncio.gather(*[_worker(c) for c in todo])
    logger.info("=" * 50)
    logger.info("Done. ok=%d fail=%d", ok, fail)


if __name__ == "__main__":
    asyncio.run(main())
