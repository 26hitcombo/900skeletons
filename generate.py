"""Generate today's image: same background, 18 random characters in fixed slots."""
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text())
HASHTAGS = json.loads((ROOT / "hashtags.json").read_text())
HIST_PATH = ROOT / "history.json"
OUT = ROOT / "output"


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_history():
    return json.loads(HIST_PATH.read_text()) if HIST_PATH.exists() else []


def slot_centers():
    """Fixed positions (centre points). Use "slots": [[x, y], ...] in config to override the grid."""
    if "slots" in CFG:
        slots = [tuple(s) for s in CFG["slots"]]
    else:
        g = CFG["grid"]
        slots = [
            (g["x0"] + c * g["cell_w"] + g["cell_w"] / 2, g["y0"] + r * g["cell_h"] + g["cell_h"] / 2)
            for r in range(g["rows"])
            for c in range(g["cols"])
        ]
    assert len(slots) == CFG["count"], f"{len(slots)} slots but count is {CFG['count']}"
    return slots


def pick_characters(date, history):
    all_ids = sorted(p.stem for p in (ROOT / CFG["characters_dir"]).glob("*.png"))
    n = CFG["count"]
    rng = random.Random(date)  # seeded by date: same day always gives the same image

    if CFG.get("allow_repeats", False):
        # Each slot is drawn independently from the full set, so a character can appear more than once
        if not all_ids:
            raise SystemExit("No characters found")
        return rng.choices(all_ids, k=n), rng

    if len(all_ids) < n:
        raise SystemExit(f"Only {len(all_ids)} characters found, need at least {n}")
    recent = set()
    k = CFG.get("cooldown_posts", 0)
    if k:
        for h in [h for h in history if h["date"] != date][-k:]:
            recent.update(h["ids"])
    pool = [i for i in all_ids if i not in recent]
    if len(pool) < n:
        pool = all_ids
    return rng.sample(pool, n), rng


def build_caption(date, ids, rng):
    tags = list(HASHTAGS["core"])
    per = HASHTAGS.get("per_character", {})
    char_tags = list(dict.fromkeys(t for i in ids for t in per.get(i, [])))
    rng.shuffle(char_tags)
    tags += char_tags[:8]
    pool = HASHTAGS["pool"][:]
    rng.shuffle(pool)
    tags += pool
    tags = list(dict.fromkeys(tags))[: min(CFG.get("max_hashtags", 25), 30)]  # Instagram max is 30
    return f"{CFG['caption_text']}\n\n{' '.join(tags)}"


def render(ids, path):
    bg = Image.open(ROOT / CFG["background"]).convert("RGBA")
    max_w, max_h = CFG["max_char_size"]
    for (cx, cy), cid in zip(slot_centers(), ids):
        ch = Image.open(ROOT / CFG["characters_dir"] / f"{cid}.png").convert("RGBA")
        ch.thumbnail((max_w, max_h), Image.LANCZOS)  # shrink to fit slot, keep aspect ratio
        bg.paste(ch, (round(cx - ch.width / 2), round(cy - ch.height / 2)), ch)
    # Instagram's API only accepts JPEG
    bg.convert("RGB").save(path, "JPEG", quality=95)


def main():
    date = today()
    history = load_history()
    existing = next((h for h in history if h["date"] == date), None)
    if existing:
        # Keep the entry (and its "posted" flag) untouched; just recreate the image if it's missing
        if not (OUT / existing["file"]).exists():
            OUT.mkdir(exist_ok=True)
            render(existing["ids"], OUT / existing["file"])
            print(f"Re-rendered {existing['file']} from saved characters")
        else:
            print(f"Already generated for {date}: {existing['file']}")
        return
    ids, rng = pick_characters(date, history)
    OUT.mkdir(exist_ok=True)
    filename = f"{date}.jpg"
    render(ids, OUT / filename)
    entry = {"date": date, "ids": ids, "file": filename,
             "caption": build_caption(date, ids, rng), "posted": False}
    history = [h for h in history if h["date"] != date] + [entry]
    HIST_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    print(f"Generated {filename} with characters {ids}")


if __name__ == "__main__":
    main()
