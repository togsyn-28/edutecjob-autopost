"""
Creates today's "Question of the Day" post for @edutecjob.

  python3 make_post.py               -> makes today's image + caption (does not mark it posted)
  python3 make_post.py --mark-posted -> call after a successful post, moves to the next question
  python3 make_post.py --preview 5   -> makes the first 5 posts into previews/ to look at

Questions come from questions.csv. Progress is kept in state.json.
"""
import argparse
import csv
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = os.path.join(HERE, "questions.csv")
STATE = os.path.join(HERE, "state.json")
OUT_DIR = os.path.join(HERE, "published")

W, H = 1080, 1350
NAVY = (18, 35, 90)
NAVY_DARK = (10, 22, 60)
ORANGE = (247, 147, 30)
WHITE = (255, 255, 255)
INK = (25, 30, 45)
SOFT = (200, 210, 235)
GREEN = (34, 160, 90)

FONT_PATHS = {
    True: [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    False: [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
}

HASHTAGS_BASE = [
    "#edutecjob", "#mocktest", "#competitiveexams", "#governmentjobs", "#sscexam",
    "#bankexam", "#railwayexam", "#dailyquiz", "#studymotivation", "#aspirants",
]
HASHTAGS_BY_CATEGORY = {
    "Reasoning": ["#reasoning", "#reasoningtricks", "#logicalreasoning"],
    "Aptitude": ["#quantitativeaptitude", "#mathstricks", "#aptitude"],
    "English": ["#englishgrammar", "#vocabulary", "#spokenenglish"],
}
HASHTAGS_GK = ["#gk", "#generalknowledge", "#gkquiz"]


def font(size, bold=False):
    for path in FONT_PATHS[bold]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fix(text, fnt):
    """Some fonts have no rupee sign; show 'Rs.' instead of an empty box."""
    if "₹" in text and fnt.getmask("₹").getbbox() == fnt.getmask("￿").getbbox():
        return text.replace("₹", "Rs.")
    return text


def load_questions():
    with open(QUESTIONS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows, start=2):
        if r["answer"].strip().upper() not in "ABCD" or not r["question"].strip():
            raise SystemExit("questions.csv line %d: answer must be A, B, C or D" % i)
    return rows


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"posted_count": 0, "last": None}


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def answer_text(q):
    letter = q["answer"].strip().upper()
    return letter, q[letter.lower()]


def wrap_to_width(draw, text, fnt, max_w):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def render(q, day, yesterday, path):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # soft background gradient
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[i] * (1 - t) + NAVY_DARK[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)

    pad = 70
    # header
    d.text((pad, 60), "EduTecJob", font=font(54, True), fill=WHITE)
    d.text((pad, 124), "Learn  •  Practice  •  Get Placed", font=font(26), fill=SOFT)
    tag = "QUESTION OF THE DAY  #%d" % day
    tf = font(26, True)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle([W - pad - tw - 44, 72, W - pad, 124], radius=26, fill=ORANGE)
    d.text((W - pad - tw - 22, 84), tag, font=tf, fill=WHITE)

    # category pill
    y = 210
    cf = font(28, True)
    cat = q["category"].upper()
    cw = d.textlength(cat, font=cf)
    d.rounded_rectangle([pad, y, pad + cw + 40, y + 50], radius=25, outline=ORANGE, width=3)
    d.text((pad + 20, y + 10), cat, font=cf, fill=ORANGE)

    # Space below the question is fixed; the question and option boxes
    # shrink step by step until everything fits above the footer.
    footer_top = H - 110
    bottom_limit = footer_top - (125 if yesterday else 20)
    y += 85
    for size, box_h, gap in [(56, 104, 22), (50, 96, 18), (46, 88, 16), (42, 82, 14), (38, 76, 12), (34, 70, 10)]:
        qf = font(size, True)
        lines = wrap_to_width(d, q["question"], qf, W - 2 * pad)
        needed = len(lines) * int(size * 1.25) + 30 + 4 * (box_h + gap) + 110
        if y + needed <= bottom_limit:
            break
    for line in lines:
        d.text((pad, y), fix(line, qf), font=qf, fill=WHITE)
        y += int(size * 1.25)

    # options
    y += 30
    lf = font(36, True)
    for letter in "ABCD":
        d.rounded_rectangle([pad, y, W - pad, y + box_h], radius=22, fill=WHITE)
        cx, cy = pad + 56, y + box_h // 2
        d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], fill=NAVY)
        d.text((cx, cy), letter, font=lf, fill=WHITE, anchor="mm")
        s = 38
        f = font(s, True)
        opt = fix(q[letter.lower()], f)
        while d.textlength(opt, font=f) > W - 2 * pad - 140 and s > 24:
            s -= 2
            f = font(s, True)
        d.text((pad + 115, cy), opt, font=f, fill=INK, anchor="lm")
        y += box_h + gap

    # call to action
    d.text((W // 2, y + 30), "Comment your answer: A, B, C or D", font=font(38, True), fill=ORANGE, anchor="mm")
    d.text((W // 2, y + 76), "Answer revealed in tomorrow's post", font=font(28), fill=SOFT, anchor="mm")

    # yesterday's answer
    if yesterday:
        yy = footer_top - 105
        d.rounded_rectangle([pad, yy, W - pad, yy + 80], radius=18, fill=NAVY_DARK, outline=GREEN, width=3)
        ff = font(30, True)
        txt = fix("Yesterday's answer: (%s) %s" % (yesterday["letter"], yesterday["text"]), ff)
        while d.textlength(txt, font=ff) > W - 2 * pad - 40:
            txt = txt[:-4] + "..."
        d.text((W // 2, yy + 40), txt, font=ff, fill=WHITE, anchor="mm")

    # footer band
    d.rectangle([0, footer_top, W, H], fill=ORANGE)
    ff = font(30, True)
    d.text((W // 2, footer_top + 36), fix("Mock tests for 23 exams  •  From just ₹10 per test", ff),
           font=ff, fill=WHITE, anchor="mm")
    d.text((W // 2, footer_top + 78), "www.edutecjob.com", font=font(32, True), fill=NAVY_DARK, anchor="mm")

    img.save(path, "PNG", optimize=True)


def caption(q, day, yesterday):
    cat = q["category"]
    tags = HASHTAGS_BASE + HASHTAGS_BY_CATEGORY.get(cat, HASHTAGS_GK)
    parts = [
        "\U0001f9e0 Question of the Day #%d | %s" % (day, cat),
        "",
        q["question"],
        "",
        "A) %s\nB) %s\nC) %s\nD) %s" % (q["a"], q["b"], q["c"], q["d"]),
        "",
        "\U0001f447 Comment your answer (A/B/C/D). Answer in tomorrow's post!",
    ]
    if yesterday:
        parts += ["", "\u2705 Yesterday's answer: (%s) %s" % (yesterday["letter"], yesterday["text"]),
                  yesterday["explanation"]]
    parts += [
        "",
        "\U0001f3af Practise real exam patterns: SSC, Banking, Railways, UPSC, NDA, Police & more",
        "\U0001f4b0 Mock tests from just \u20b910 | Free skill certifications",
        "\U0001f517 edutecjob.com (link in bio)",
        "",
        "Follow @edutecjob for a new question every day!",
        "",
        " ".join(tags),
    ]
    return "\n".join(parts)


def build(questions, count, last, out_path):
    q = questions[count % len(questions)]
    day = count + 1
    render(q, day, last, out_path)
    letter, text = answer_text(q)
    return q, day, caption(q, day, last), {
        "letter": letter, "text": text, "explanation": q["explanation"]}


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
        last = None
        for i in range(args.preview):
            p = os.path.join(prev_dir, "day-%03d.png" % (i + 1))
            _, _, cap, last = build(questions, i, last, p)
            with open(p.replace(".png", ".txt"), "w", encoding="utf-8") as f:
                f.write(cap)
            print("Preview:", p)
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    count = state["posted_count"]
    image_name = "day-%03d.png" % (count + 1)
    path = os.path.join(OUT_DIR, image_name)
    q, day, cap, this_answer = build(questions, count, state.get("last"), path)

    if args.mark_posted:
        state["posted_count"] = count + 1
        state["last"] = this_answer
        save_state(state)
        print("Marked day %d as posted." % day)
        return

    with open(os.path.join(HERE, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(cap)
    print(json.dumps({"day": day, "image": "published/" + image_name}))


if __name__ == "__main__":
    main()
