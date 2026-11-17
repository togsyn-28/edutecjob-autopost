"""
Creates today's post for @edutecjob.

Every day is a different puzzle type (see ROTATION). Each post is a carousel:
  slide 1 = today's puzzle
  slide 2 = yesterday's solution (from day 2 onwards)

  python3 make_post.py               -> makes today's images + caption (does not mark it posted)
  python3 make_post.py --mark-posted -> call after a successful post, moves to the next day
  python3 make_post.py --preview 10  -> makes the first 10 days into previews/ to look at

Quiz questions come from questions.csv. Progress is kept in state.json.
"""
import argparse
import csv
import json
import os
import random

from PIL import Image, ImageDraw, ImageFont

import puzzles

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = os.path.join(HERE, "questions.csv")
STATE = os.path.join(HERE, "state.json")
OUT_DIR = os.path.join(HERE, "published")

# Order of puzzle types, repeated forever. Change it freely.
ROTATION = ["quiz", "sudoku", "race", "spot", "quiz", "path", "team", "gears", "quiz", "maze"]

W, H = 1080, 1350
PAD = 70
NAVY = (18, 35, 90)
NAVY_DARK = (10, 22, 60)
ORANGE = (247, 147, 30)
WHITE = (255, 255, 255)
INK = (25, 30, 45)
SOFT = (200, 210, 235)
GREEN = (34, 160, 90)

FONT_PATHS = {
    True: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    False: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
}
_font_cache = {}

HASHTAGS_BASE = [
    "#edutecjob", "#competitiveexams", "#governmentjobs", "#sscexam", "#bankexam",
    "#dailyquiz", "#dailypuzzle", "#studymotivation", "#aspirants", "#mocktest",
]
QUIZ_TAGS = {
    "Reasoning": ["#reasoning", "#reasoningtricks", "#logicalreasoning"],
    "Aptitude": ["#quantitativeaptitude", "#mathstricks", "#aptitude"],
    "English": ["#englishgrammar", "#vocabulary", "#spokenenglish"],
}


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        f = None
        for path in FONT_PATHS[bold]:
            if os.path.exists(path):
                f = ImageFont.truetype(path, size)
                break
        _font_cache[key] = f or ImageFont.load_default()
    return _font_cache[key]


puzzles.set_font(font)


def fix(text, fnt):
    """Some fonts have no rupee sign; show 'Rs.' instead of an empty box."""
    if "\u20b9" in text and fnt.getmask("\u20b9").getbbox() == fnt.getmask("\uffff").getbbox():
        return text.replace("\u20b9", "Rs.")
    return text


def wrap(d, text, fnt, max_w):
    lines, line = [], ""
    for w in text.split():
        test = (line + " " + w).strip()
        if d.textlength(test, font=fnt) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


# ---------------------------------------------------------------- quiz type
def load_questions():
    with open(QUESTIONS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows, start=2):
        if r["answer"].strip().upper() not in ("A", "B", "C", "D") or not r["question"].strip():
            raise SystemExit("questions.csv line %d: answer must be A, B, C or D" % i)
    return rows


def gen_quiz(q):
    letter = q["answer"].strip().upper()

    def draw(d, box, show_solution):
        x0, y0, x1, y1 = box
        n = 4
        gap = 20
        box_h = min(104, (y1 - y0 - 3 * gap - (110 if show_solution else 0)) / n)
        y = y0 + 10
        for L in "ABCD":
            right = show_solution and L == letter
            d.rounded_rectangle([x0, y, x1, y + box_h], radius=22, fill=GREEN if right else WHITE)
            cx, cy = x0 + 56, y + box_h / 2
            d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], fill=WHITE if right else NAVY)
            d.text((cx, cy), L, font=font(36, True), fill=GREEN if right else WHITE, anchor="mm")
            s = 38
            f = font(s, True)
            opt = fix(q[L.lower()], f)
            while d.textlength(opt, font=f) > x1 - x0 - 140 and s > 24:
                s -= 2
                f = font(s, True)
            d.text((x0 + 115, cy), opt, font=f, fill=WHITE if right else INK, anchor="lm")
            y += box_h + gap
        if show_solution:
            f = font(30, False)
            for line in wrap(d, fix(q["explanation"], f), f, x1 - x0)[:3]:
                d.text((x0, y + 8), line, font=f, fill=WHITE)
                y += 40

    return {
        "name": "Quiz", "category": q["category"], "title": q["question"], "rules": "",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "(%s) %s. %s" % (letter, q[letter.lower()], q["explanation"]),
        "options": "A) %s\nB) %s\nC) %s\nD) %s" % (q["a"], q["b"], q["c"], q["d"]),
        "hashtags": QUIZ_TAGS.get(q["category"], ["#gk", "#generalknowledge", "#gkquiz"]),
    }


# ---------------------------------------------------------------- which puzzle on which day
def puzzle_for_day(day, questions):
    pos = (day - 1) % len(ROTATION)
    kind = ROTATION[pos]
    if kind == "quiz":
        per_cycle = ROTATION.count("quiz")
        idx = ((day - 1) // len(ROTATION)) * per_cycle + ROTATION[:pos].count("quiz")
        return gen_quiz(questions[idx % len(questions)])
    return puzzles.GENERATORS[kind](random.Random(day * 7919 + 17))


# ---------------------------------------------------------------- page layout
def frame(tag, category, title, title_max_lines=3):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(NAVY[i] * (1 - t) + NAVY_DARK[i] * t) for i in range(3)))
    d.text((PAD, 55), "EduTecJob", font=font(52, True), fill=WHITE)
    d.text((PAD, 117), "Learn  \u2022  Practice  \u2022  Get Placed", font=font(25), fill=SOFT)
    tf = font(25, True)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle([W - PAD - tw - 44, 66, W - PAD, 116], radius=25, fill=ORANGE)
    d.text((W - PAD - tw - 22, 91), tag, font=tf, fill=WHITE, anchor="lm")

    y = 185
    cf = font(26, True)
    cat = category.upper()
    cw = d.textlength(cat, font=cf)
    d.rounded_rectangle([PAD, y, PAD + cw + 40, y + 46], radius=23, outline=ORANGE, width=3)
    d.text((PAD + 20, y + 23), cat, font=cf, fill=ORANGE, anchor="lm")
    y += 70
    for size in (50, 46, 42, 38, 34):
        tf = font(size, True)
        lines = wrap(d, fix(title, tf), tf, W - 2 * PAD)
        if len(lines) <= title_max_lines:
            break
    for line in lines:
        d.text((PAD, y), line, font=tf, fill=WHITE)
        y += int(size * 1.22)

    footer_top = H - 105
    d.rectangle([0, footer_top, W, H], fill=ORANGE)
    ff = font(29, True)
    d.text((W // 2, footer_top + 34), fix("Mock tests for 23 exams  \u2022  From just \u20b910 per test", ff),
           font=ff, fill=WHITE, anchor="mm")
    d.text((W // 2, footer_top + 74), "www.edutecjob.com", font=font(31, True), fill=NAVY_DARK, anchor="mm")
    return img, d, y + 10, footer_top


def render_puzzle(p, day, path):
    img, d, top, bottom = frame("DAY %d  \u2022  %s" % (day, p["name"].upper()), p["category"], p["title"])
    if p["rules"]:
        rf = font(27, False)
        for line in wrap(d, p["rules"], rf, W - 2 * PAD)[:2]:
            d.text((PAD, top), line, font=rf, fill=SOFT)
            top += 36
        top += 10
    cta_h = 70
    p["puzzle"](d, (PAD, top + 10, W - PAD, bottom - cta_h - 10))
    d.text((W // 2, bottom - 40), "Comment your answer!  Solution tomorrow", font=font(34, True), fill=ORANGE,
           anchor="mm")
    img.save(path, "PNG", optimize=True)


def render_answer(p, day, path):
    title = p["title"] if p["name"] == "Quiz" else "Solution: " + p["name"]
    img, d, top, bottom = frame("ANSWER  \u2022  DAY %d" % day, p["category"], title)
    p["answer"](d, (PAD, top + 10, W - PAD, bottom - 80))
    d.text((W // 2, bottom - 42), "Did you get it right? Follow for today's puzzle!", font=font(31, True),
           fill=ORANGE, anchor="mm")
    img.save(path, "PNG", optimize=True)


def caption(p, day, prev):
    parts = ["\U0001f9e9 Puzzle of the Day #%d | %s" % (day, p["name"] if p["name"] != "Quiz" else p["category"]),
             "", p["title"]]
    if p.get("options"):
        parts += ["", p["options"]]
    if p["rules"]:
        parts += ["", p["rules"]]
    parts += ["", "\U0001f447 Comment your answer! Solution in tomorrow's post."]
    if prev:
        parts += ["", "\u2705 Yesterday's answer (swipe \u27a1\ufe0f): " + prev["answer_text"]]
    parts += [
        "",
        "\U0001f3af Practise real exam patterns: SSC, Banking, Railways, UPSC, NDA, Police & more",
        "\U0001f4b0 Mock tests from just \u20b910 | Free skill certifications",
        "\U0001f517 edutecjob.com (link in bio)",
        "",
        "Follow @edutecjob for a new puzzle every day!",
        "",
        " ".join(HASHTAGS_BASE + p["hashtags"]),
    ]
    return "\n".join(parts)


def build(day, questions, out_dir):
    """Makes the images for one day. Returns (list of image file names, caption)."""
    p = puzzle_for_day(day, questions)
    names = ["day-%03d-1.png" % day]
    render_puzzle(p, day, os.path.join(out_dir, names[0]))
    prev = None
    if day > 1:
        prev = puzzle_for_day(day - 1, questions)
        names.append("day-%03d-2.png" % day)
        render_answer(prev, day - 1, os.path.join(out_dir, names[1]))
    return names, caption(p, day, prev)


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"posted_count": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark-posted", action="store_true")
    ap.add_argument("--preview", type=int, default=0)
    args = ap.parse_args()

    questions = load_questions()
    state = load_state()

    if args.preview:
        prev_dir = os.path.join(HERE, "previews")
        os.makedirs(prev_dir, exist_ok=True)
        for day in range(1, args.preview + 1):
            names, cap = build(day, questions, prev_dir)
            with open(os.path.join(prev_dir, "day-%03d.txt" % day), "w", encoding="utf-8") as f:
                f.write(cap)
            print("Preview day %d: %s" % (day, ", ".join(names)))
        return

    day = state["posted_count"] + 1
    if args.mark_posted:
        state["posted_count"] = day
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        print("Marked day %d as posted." % day)
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    names, cap = build(day, questions, OUT_DIR)
    with open(os.path.join(HERE, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(cap)
    print(json.dumps({"day": day, "images": ["published/" + n for n in names]}))


if __name__ == "__main__":
    main()
