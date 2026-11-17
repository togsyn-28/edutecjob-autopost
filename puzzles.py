"""
Puzzle generators for EduTecJob daily posts.

Each generator takes a random.Random and returns a dict:
  name      short name shown on the post, e.g. "Mini Sudoku"
  category  label in the orange pill
  title     the big question text
  rules     one line explaining how to play
  puzzle    function(draw, box) that draws the puzzle inside box=(x0, y0, x1, y1)
  answer    function(draw, box) that draws the solution inside box
  answer_text  short text answer for the caption
  hashtags  extra hashtags
Everything is built from the seed, so the same day always gives the same puzzle.
"""
import math
from collections import deque

NAVY = (18, 35, 90)
NAVY_DARK = (10, 22, 60)
ORANGE = (247, 147, 30)
WHITE = (255, 255, 255)
INK = (25, 30, 45)
SOFT = (200, 210, 235)
GREEN = (34, 160, 90)
RED = (225, 45, 45)
GRID = (150, 160, 185)

_font = None  # set by make_post.py: function(size, bold) -> ImageFont


def set_font(fn):
    global _font
    _font = fn


def F(size, bold=True):
    return _font(size, bold)


def center_square(box, max_side=None):
    x0, y0, x1, y1 = box
    side = min(x1 - x0, y1 - y0)
    if max_side:
        side = min(side, max_side)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return cx - side / 2, cy - side / 2, side


# ---------------------------------------------------------------- Mini Sudoku
def _sudoku_cands(g, i):
    r, c = divmod(i, 6)
    used = set(g[r * 6:(r + 1) * 6]) | {g[k * 6 + c] for k in range(6)}
    br, bc = r // 2 * 2, c // 3 * 3
    used |= {g[(br + a) * 6 + bc + b] for a in range(2) for b in range(3)}
    return [v for v in range(1, 7) if v not in used]


def _sudoku_count(g, limit=2):
    empties = [i for i in range(36) if g[i] == 0]
    if not empties:
        return 1
    best, bc = None, None
    for i in empties:
        c = _sudoku_cands(g, i)
        if best is None or len(c) < len(bc):
            best, bc = i, c
            if len(c) <= 1:
                break
    total = 0
    for v in bc:
        g[best] = v
        total += _sudoku_count(g, limit - total)
        g[best] = 0
        if total >= limit:
            break
    return total


def _sudoku_fill(g, rng):
    try:
        i = g.index(0)
    except ValueError:
        return True
    c = _sudoku_cands(g, i)
    rng.shuffle(c)
    for v in c:
        g[i] = v
        if _sudoku_fill(g, rng):
            return True
    g[i] = 0
    return False


def gen_sudoku(rng):
    sol = [0] * 36
    _sudoku_fill(sol, rng)
    puzzle = sol[:]
    order = list(range(36))
    rng.shuffle(order)
    givens = 36
    for i in order:
        if givens <= 13:
            break
        keep = puzzle[i]
        puzzle[i] = 0
        if _sudoku_count(puzzle[:]) == 1:
            givens -= 1
        else:
            puzzle[i] = keep

    def draw(d, box, show_solution):
        x, y, side = center_square(box, 760)
        cell = side / 6
        d.rectangle([x, y, x + side, y + side], fill=WHITE)
        for i in range(36):
            r, c = divmod(i, 6)
            cx, cy = x + c * cell + cell / 2, y + r * cell + cell / 2
            if puzzle[i]:
                d.text((cx, cy), str(puzzle[i]), font=F(int(cell * 0.55)), fill=NAVY, anchor="mm")
            elif show_solution:
                d.text((cx, cy), str(sol[i]), font=F(int(cell * 0.55)), fill=ORANGE, anchor="mm")
        for k in range(7):
            thick = 7 if k in (0, 6) or (k % 3 == 0) else 2
            d.line([x + k * cell, y, x + k * cell, y + side], fill=NAVY if thick > 2 else GRID, width=thick)
            thick = 7 if k % 2 == 0 else 2
            d.line([x, y + k * cell, x + side, y + k * cell], fill=NAVY if thick > 2 else GRID, width=thick)

    return {
        "name": "Mini Sudoku", "category": "Logic Puzzle",
        "title": "Can you solve this Mini Sudoku?",
        "rules": "Fill 1 to 6 so each row, column and 2x3 box has every number once.",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "Top row: " + " ".join(str(v) for v in sol[:6]),
        "data": {"puzzle": puzzle, "solution": sol},
        "hashtags": ["#sudoku", "#minisudoku", "#logicpuzzle", "#brainteaser"],
    }


# ---------------------------------------------------------------- Number Path
def _neighbors(i, n):
    r, c = divmod(i, n)
    if r > 0: yield i - n
    if r < n - 1: yield i + n
    if c > 0: yield i - 1
    if c < n - 1: yield i + 1


def _ham_path(n, rng):
    total = n * n
    start = rng.randrange(total)
    path, seen = [start], {start}

    def onward(j):
        return sum(1 for k in _neighbors(j, n) if k not in seen)

    def dfs():
        if len(path) == total:
            return True
        nbs = [k for k in _neighbors(path[-1], n) if k not in seen]
        rng.shuffle(nbs)
        nbs.sort(key=onward)
        for k in nbs:
            path.append(k)
            seen.add(k)
            if dfs():
                return True
            path.pop()
            seen.discard(k)
        return False

    dfs()
    return path


def _path_solutions(n, clues, last_k, limit=2):
    total = n * n
    start = next(c for c, k in clues.items() if k == 1)
    end = next(c for c, k in clues.items() if k == last_k)
    visited = [False] * total
    visited[start] = True
    sols = []
    cur = [start]

    def connected(frm, remaining):
        if remaining == 0:
            return True
        seen = {frm}
        q = deque([frm])
        reached = 0
        while q:
            j = q.popleft()
            for k in _neighbors(j, n):
                if not visited[k] and k not in seen:
                    seen.add(k)
                    reached += 1
                    q.append(k)
        return reached == remaining

    def dfs(cell, nvis, nk):
        if len(sols) >= limit:
            return
        if nvis == total:
            if cell == end:
                sols.append(list(cur))
            return
        if not connected(cell, total - nvis):
            return
        dead = 0
        for j in range(total):
            if visited[j] or j == end:
                continue
            free = sum(1 for k in _neighbors(j, n) if not visited[k] or k == cell)
            if free < 2:
                dead += 1
                if dead > 1 or cell not in _neighbors(j, n):
                    return
        for k in _neighbors(cell, n):
            if visited[k]:
                continue
            if k in clues:
                if clues[k] != nk:
                    continue
                nk2 = nk + 1
            else:
                nk2 = nk
            if k == end and nvis + 1 < total:
                continue
            visited[k] = True
            cur.append(k)
            dfs(k, nvis + 1, nk2)
            cur.pop()
            visited[k] = False

    dfs(start, 1, 2)
    return sols


def _clues_for(path, n, step, rng):
    idx = sorted({0, len(path) - 1} | set(range(0, len(path), step)))
    while True:
        clues = {path[p]: k + 1 for k, p in enumerate(idx)}
        others = [sl for sl in _path_solutions(n, clues, len(idx)) if sl != path]
        if not others:
            return idx
        # add a number exactly where another solution would go a different way
        diff = next(i for i in range(len(path)) if others[0][i] != path[i] and i not in idx)
        idx = sorted(set(idx) | {diff})


def gen_path(rng):
    n = 6
    best = None
    for _ in range(25):  # try several paths, keep the one needing the fewest numbers
        path = _ham_path(n, rng)
        if len(path) != n * n:
            continue
        idx = _clues_for(path, n, rng.choice([6, 7, 8]), rng)
        if best is None or len(idx) < len(best[1]):
            best = (path, idx)
        if len(idx) <= 10:
            break
    path, idx = best
    clues = {path[p]: k + 1 for k, p in enumerate(idx)}
    last_k = len(idx)

    def draw(d, box, show_solution):
        x, y, side = center_square(box, 760)
        cell = side / n
        d.rounded_rectangle([x, y, x + side, y + side], radius=18, fill=WHITE)
        for k in range(1, n):
            d.line([x + k * cell, y, x + k * cell, y + side], fill=GRID, width=2)
            d.line([x, y + k * cell, x + side, y + k * cell], fill=GRID, width=2)

        def ctr(i):
            r, c = divmod(i, n)
            return x + c * cell + cell / 2, y + r * cell + cell / 2

        if show_solution:
            d.line([ctr(i) for i in path], fill=ORANGE, width=int(cell * 0.32), joint="curve")
        for i, k in clues.items():
            cx, cy = ctr(i)
            rad = cell * 0.33
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=NAVY)
            d.text((cx, cy), str(k), font=F(int(cell * 0.32)), fill=WHITE, anchor="mm")

    return {
        "name": "Number Path", "category": "Logic Puzzle",
        "title": "Connect 1 to %d in one line!" % last_k,
        "rules": "Draw ONE line through every square, visiting the numbers in order. No diagonals.",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "See the full path in the image",
        "data": {"n": n, "clues": {str(c): k for c, k in clues.items()}, "solution": path},
        "hashtags": ["#numberpuzzle", "#logicpuzzle", "#brainteaser", "#puzzlegame"],
    }


# ---------------------------------------------------------------- Maze
def gen_maze(rng):
    n = 12
    walls = {}  # (cell, cell) pairs that are open
    seen = {0}
    stack = [0]
    opened = set()
    while stack:
        cur = stack[-1]
        nbs = [k for k in _neighbors(cur, n) if k not in seen]
        if not nbs:
            stack.pop()
            continue
        k = rng.choice(nbs)
        opened.add((min(cur, k), max(cur, k)))
        seen.add(k)
        stack.append(k)
    # solution by BFS
    goal = n * n - 1
    prev = {0: None}
    q = deque([0])
    while q:
        j = q.popleft()
        for k in _neighbors(j, n):
            if k not in prev and (min(j, k), max(j, k)) in opened:
                prev[k] = j
                q.append(k)
    sol = []
    j = goal
    while j is not None:
        sol.append(j)
        j = prev[j]
    sol.reverse()

    def draw(d, box, show_solution):
        x0, y0, x1, y1 = box
        x, y, side = center_square((x0, y0 + 40, x1, y1 - 40), 720)
        cell = side / n
        d.rectangle([x, y, x + side, y + side], fill=WHITE)

        def ctr(i):
            r, c = divmod(i, n)
            return x + c * cell + cell / 2, y + r * cell + cell / 2

        if show_solution:
            d.line([ctr(i) for i in sol], fill=ORANGE, width=int(cell * 0.35), joint="curve")
        w = 6
        for i in range(n * n):
            r, c = divmod(i, n)
            cx, cy = x + c * cell, y + r * cell
            if c == n - 1 or (i, i + 1) not in opened:
                if not (i == goal and c == n - 1):
                    d.line([cx + cell, cy, cx + cell, cy + cell], fill=NAVY, width=w)
            if r == n - 1 or (i, i + n) not in opened:
                d.line([cx, cy + cell, cx + cell, cy + cell], fill=NAVY, width=w)
        d.line([x, y + cell, x, y + side], fill=NAVY, width=w)   # left wall, gap at start
        d.line([x, y, x + side, y], fill=NAVY, width=w)          # top wall
        sx, sy = ctr(0)
        gx, gy = ctr(goal)
        rad = cell * 0.3
        d.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=GREEN)
        d.ellipse([gx - rad, gy - rad, gx + rad, gy + rad], fill=ORANGE)
        d.text((x, y - 12), "START", font=F(30), fill=GREEN, anchor="ls")
        d.text((x + side, y + side + 12), "DREAM JOB", font=F(30), fill=ORANGE, anchor="rt")

    return {
        "name": "Career Maze", "category": "Maze",
        "title": "Help the job seeker reach the DREAM JOB!",
        "rules": "Find the way from START (green) to DREAM JOB (orange).",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "See the route in the image",
        "data": {"n": n, "open": sorted([a, b] for a, b in opened), "solution": sol},
        "hashtags": ["#maze", "#mazepuzzle", "#brainteaser", "#careergoals"],
    }


# ---------------------------------------------------------------- Spot the difference
SPOT_DIFFS = [
    # key, bbox (fractions of panel), how it changes
    ("sun", (0.82, 0.06, 0.95, 0.34)),
    ("cloud1", (0.11, 0.04, 0.29, 0.28)),
    ("cloud2", (0.41, 0.02, 0.59, 0.24)),
    ("bird", (0.44, 0.26, 0.53, 0.38)),
    ("roof", (0.05, 0.2, 0.41, 0.43)),
    ("door", (0.18, 0.58, 0.28, 0.82)),
    ("windowL", (0.09, 0.47, 0.19, 0.61)),
    ("windowR", (0.27, 0.47, 0.37, 0.61)),
    ("chimney", (0.28, 0.2, 0.36, 0.38)),
    ("apple", (0.57, 0.38, 0.63, 0.5)),
    ("car", (0.64, 0.56, 0.94, 0.9)),
    ("wheel", (0.82, 0.74, 0.92, 0.9)),
    ("flower", None),
]


def _scene(d, x0, y0, w, h, p):
    def P(fx, fy):
        return x0 + fx * w, y0 + fy * h

    def circ(fx, fy, r, fill):
        cx, cy = P(fx, fy)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    d.rectangle([x0, y0, x0 + w, y0 + h], fill=(190, 225, 250))
    d.rectangle([P(0, 0.74), P(1, 1)], fill=(120, 190, 90))
    circ(0.88, 0.2, h * 0.1, p["sun"])
    for key, (fx, fy) in (("cloud1", (0.2, 0.16)), ("cloud2", (0.5, 0.12))):
        if p[key]:
            for dx, dy, r in ((-0.04, 0.02, 0.07), (0, -0.02, 0.09), (0.045, 0.02, 0.07)):
                circ(fx + dx, fy + dy, h * r, WHITE)
    for k in range(p["birds"]):
        bx, by = ((0.33, 0.3), (0.4, 0.25), (0.485, 0.32))[k]
        d.line([P(bx - 0.02, by - 0.03), P(bx, by), P(bx + 0.02, by - 0.03)], fill=INK, width=4)
    if p["chimney"]:
        d.rectangle([P(0.3, 0.24), P(0.34, 0.36)], fill=(140, 70, 50))
    d.rectangle([P(0.08, 0.42), P(0.38, 0.8)], fill=(245, 225, 180))
    d.polygon([P(0.05, 0.43), P(0.23, 0.22), P(0.41, 0.43)], fill=p["roof"])
    d.rectangle([P(0.2, 0.6), P(0.26, 0.8)], fill=p["door"])
    circ(0.245, 0.71, 4, INK)
    for key, fx in (("windowL", 0.11), ("windowR", 0.29)):
        if p[key]:
            d.rectangle([P(fx, 0.5), P(fx + 0.06, 0.58)], fill=(170, 215, 245), outline=INK, width=3)
            d.line([P(fx + 0.03, 0.5), P(fx + 0.03, 0.58)], fill=INK, width=2)
    d.rectangle([P(0.535, 0.5), P(0.565, 0.79)], fill=(120, 80, 45))
    circ(0.55, 0.4, h * 0.17, (60, 150, 60))
    for k in range(p["apples"]):
        ax, ay = ((0.51, 0.36), (0.58, 0.32), (0.6, 0.44))[k]
        circ(ax, ay, h * 0.025, RED)
    d.rounded_rectangle([P(0.71, 0.6), P(0.86, 0.7)], radius=10, fill=p["car"])
    d.rounded_rectangle([P(0.66, 0.68), P(0.92, 0.8)], radius=12, fill=p["car"])
    d.rectangle([P(0.735, 0.62), P(0.835, 0.68)], fill=(170, 215, 245))
    circ(0.71, 0.81, h * 0.05, INK)
    if p["wheel"]:
        circ(0.87, 0.81, h * 0.05, INK)
    for k, col in enumerate(p["flowers"]):
        fx = 0.08 + k * 0.1
        d.line([P(fx, 0.86), P(fx, 0.96)], fill=(40, 120, 40), width=4)
        circ(fx, 0.86, h * 0.035, col)
        circ(fx, 0.86, h * 0.012, (250, 220, 60))


def gen_spot(rng):
    flower_cols = [(230, 80, 140), (150, 90, 220), (240, 120, 40), (60, 120, 230)]
    base = {
        "sun": (255, 200, 40), "cloud1": True, "cloud2": True, "birds": 3,
        "roof": (200, 60, 50), "door": (110, 70, 160), "windowL": True, "windowR": True,
        "chimney": True, "apples": 3, "car": (40, 110, 220), "wheel": True,
        "flowers": rng.sample(flower_cols, 4),
    }
    clashes = [{"car", "wheel"}, {"roof", "chimney"}, {"cloud2", "bird"}]
    while True:
        picks = rng.sample(SPOT_DIFFS, 5)
        keys = {k for k, _ in picks}
        if not any(c <= keys for c in clashes):
            break
    changed = dict(base)
    changed["flowers"] = list(base["flowers"])
    boxes = []
    for key, bb in picks:
        if key == "sun":
            changed["sun"] = (250, 110, 40)
        elif key in ("cloud1", "cloud2", "windowL", "windowR", "chimney", "wheel"):
            changed[key] = False
        elif key == "bird":
            changed["birds"] = 2
        elif key == "apple":
            changed["apples"] = 2
        elif key == "roof":
            changed["roof"] = (40, 130, 120)
        elif key == "door":
            changed["door"] = (220, 160, 30)
        elif key == "car":
            changed["car"] = (220, 50, 60)
        elif key == "flower":
            k = rng.randrange(4)
            others = [c for c in flower_cols if c != base["flowers"][k]]
            changed["flowers"][k] = rng.choice(others)
            fx = 0.08 + k * 0.1
            bb = (fx - 0.05, 0.78, fx + 0.05, 0.98)
        boxes.append(bb)

    def panels(box):
        x0, y0, x1, y1 = box
        w = x1 - x0
        gap = 26
        h = min((y1 - y0 - gap) / 2, w * 0.45)
        top = y0 + (y1 - y0 - (2 * h + gap)) / 2
        return x0, top, w, h, top + h + gap

    def draw(d, box, show_solution):
        x, top, w, h, top2 = panels(box)
        _scene(d, x, top, w, h, base)
        _scene(d, x, top2, w, h, changed)
        for yy in (top, top2):
            d.rectangle([x, yy, x + w, yy + h], outline=WHITE, width=5)
        if show_solution:
            for (a, b, c, e) in boxes:
                d.ellipse([x + a * w - 8, top2 + b * h - 8, x + c * w + 8, top2 + e * h + 8], outline=RED, width=7)

    return {
        "name": "Spot the Difference", "category": "Observation",
        "title": "Find 5 differences between the pictures!",
        "rules": "Look closely. Comment how many you found and where!",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "All 5 differences are circled in red",
        "data": {"boxes": [list(b) for b in boxes]},
        "scenes": (base, changed),
        "hashtags": ["#spotthedifference", "#findthedifference", "#observation", "#brainteaser"],
    }


# ---------------------------------------------------------------- Which car arrives first
def _fmt_minutes(m):
    m = int(round(m))
    hrs, mins = divmod(m, 60)
    if hrs and mins:
        return "%d h %d min" % (hrs, mins)
    if hrs:
        return "%d h" % hrs
    return "%d min" % mins


def _draw_car(d, x, y, w, color):
    h = w * 0.42
    d.rounded_rectangle([x + w * 0.2, y, x + w * 0.75, y + h * 0.55], radius=10, fill=color)
    d.rounded_rectangle([x, y + h * 0.4, x + w, y + h], radius=12, fill=color)
    d.rectangle([x + w * 0.28, y + h * 0.1, x + w * 0.68, y + h * 0.42], fill=(170, 215, 245))
    for fx in (0.22, 0.78):
        cx, cy, r = x + w * fx, y + h, h * 0.24
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK)


def gen_race(rng):
    names = ["A", "B", "C"]
    colors = [(225, 50, 60), (40, 110, 220), (34, 160, 90)]
    while True:
        cars = []
        for nm in names:
            dist = rng.choice([60, 90, 100, 120, 150, 180, 200, 240])
            speed = rng.choice([30, 40, 45, 50, 60, 75, 80, 90])
            delay = rng.choice([0, 0, 0, 15, 20, 30, 45])
            t = dist / speed * 60 + delay
            if abs(t - round(t)) > 1e-9:
                break
            cars.append((nm, dist, speed, delay, t))
        if len(cars) < 3:
            continue
        times = sorted(c[4] for c in cars)
        if times[1] - times[0] < 5:
            continue
        win = min(cars, key=lambda c: c[4])
        fastest = max(cars, key=lambda c: c[2])
        if win is fastest and win[3] == 0:
            continue  # too easy: the fastest car simply wins
        if sum(1 for c in cars if c[3]) == 0:
            continue
        break

    def draw(d, box, show_solution):
        x0, y0, x1, y1 = box
        lane_h = min(190, (y1 - y0) / 3 - 10)
        top = y0 + ((y1 - y0) - 3 * (lane_h + 10)) / 2
        for k, (nm, dist, speed, delay, t) in enumerate(cars):
            ly = top + k * (lane_h + 10)
            win_lane = show_solution and nm == win[0]
            d.rounded_rectangle([x0, ly, x1, ly + lane_h], radius=18,
                                fill=(60, 66, 80), outline=ORANGE if win_lane else None, width=6)
            for sx in range(int(x0 + 20), int(x1 - 20), 60):
                d.line([sx, ly + lane_h - 18, sx + 30, ly + lane_h - 18], fill=WHITE, width=4)
            _draw_car(d, x0 + 25, ly + 30, 170, colors[k])
            tx = x0 + 225
            d.text((tx, ly + 22), "Car %s" % nm, font=F(38), fill=WHITE)
            d.text((tx, ly + 72), "%d km at %d km/h" % (dist, speed), font=F(32, False), fill=SOFT)
            d.text((tx, ly + 112), "Starts %d min late" % delay if delay else "Starts on time",
                   font=F(28, False), fill=ORANGE if delay else SOFT)
            if show_solution:
                d.text((x1 - 25, ly + lane_h / 2), _fmt_minutes(t), font=F(40), fill=ORANGE if win_lane else WHITE,
                       anchor="rm")

    lines = ["Car %s: %d/%d h%s = %s" % (nm, dist, speed, " + %d min" % delay if delay else "", _fmt_minutes(t))
             for nm, dist, speed, delay, t in cars]
    return {
        "name": "Speed Race", "category": "Time, Speed & Distance",
        "title": "All cars leave at 9:00 AM. Which car reaches first?",
        "rules": "Time = Distance / Speed. Don't forget the late starts!",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "Car %s wins! " % win[0] + " | ".join(lines),
        "data": {"options": ["Car %s" % c[0] for c in cars], "correct": cars.index(win)},
        "hashtags": ["#timespeeddistance", "#quantitativeaptitude", "#mathstricks", "#aptitude"],
    }


# ---------------------------------------------------------------- Which team finishes first
def _person(d, cx, top, size, color):
    r = size * 0.22
    d.ellipse([cx - r, top, cx + r, top + 2 * r], fill=color)
    d.rounded_rectangle([cx - size * 0.3, top + 2 * r + 4, cx + size * 0.3, top + size], radius=int(size * 0.15),
                        fill=color)


def gen_team(rng):
    names = ["A", "B", "C"]
    colors = [(225, 80, 70), (60, 120, 230), (40, 160, 100)]
    while True:
        teams = []
        for nm in names:
            n = rng.randint(2, 7)
            days = n * rng.choice([2, 3, 4, 5, 6])  # whole-number team time
            if days > 40:
                break
            teams.append((nm, n, days, days / n))
        if len(teams) < 3:
            continue
        ts = sorted(t[3] for t in teams)
        if ts[1] - ts[0] < 1:
            continue
        win = min(teams, key=lambda t: t[3])
        if win[1] >= max(t[1] for t in teams):
            continue  # make it tricky: the biggest team should not win
        break

    def draw(d, box, show_solution):
        x0, y0, x1, y1 = box
        row_h = min(200, (y1 - y0) / 3 - 12)
        top = y0 + ((y1 - y0) - 3 * (row_h + 12)) / 2
        for k, (nm, n, days, t) in enumerate(teams):
            ry = top + k * (row_h + 12)
            win_row = show_solution and nm == win[0]
            d.rounded_rectangle([x0, ry, x1, ry + row_h], radius=18, fill=WHITE,
                                outline=ORANGE if win_row else None, width=7)
            d.text((x0 + 25, ry + 20), "Team %s" % nm, font=F(38), fill=NAVY)
            d.text((x0 + 25, ry + 70), "%d people" % n, font=F(30, False), fill=INK)
            d.text((x0 + 25, ry + 110), "1 person alone: %d days" % days, font=F(28, False), fill=INK)
            size = 62
            px = x0 + 470
            for j in range(n):
                _person(d, px + (j % 7) * 64, ry + 25 + (j // 7) * 70, size, colors[k])
            if show_solution:
                d.text((x1 - 25, ry + row_h - 22), "%d / %d = %d days" % (days, n, t), font=F(34),
                       fill=ORANGE if win_row else NAVY, anchor="rs")

    lines = ["Team %s: %d / %d = %d days" % (nm, days, n, t) for nm, n, days, t in teams]
    return {
        "name": "Team Work", "category": "Time & Work",
        "title": "Which team paints the school building first?",
        "rules": "Everyone in a team works at the same speed and they work together.",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "Team %s wins! " % win[0] + " | ".join(lines),
        "data": {"options": ["Team %s" % t[0] for t in teams], "correct": teams.index(win)},
        "hashtags": ["#timeandwork", "#quantitativeaptitude", "#aptitude", "#mathstricks"],
    }


# ---------------------------------------------------------------- Gears
SNAKE = [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1), (0, 2), (1, 2), (2, 2)]


def _gear(d, cx, cy, r, fill, scale):
    teeth = max(8, int(r / 14))
    pts = []
    for t in range(teeth * 4):
        a = 2 * math.pi * t / (teeth * 4)
        rr = r if t % 4 in (1, 2) else r - 14 * scale
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)
    hr = r * 0.25
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=WHITE)


def _arrow(d, cx, cy, r, clockwise, color, width):
    box = [cx - r, cy - r, cx + r, cy + r]
    s, e = 200, 320
    d.arc(box, s, e, fill=color, width=width)
    ang = math.radians(e if clockwise else s)
    px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
    tx, ty = (-math.sin(ang), math.cos(ang)) if clockwise else (math.sin(ang), -math.cos(ang))
    nx, ny = -ty, tx
    L = width * 2.6
    d.polygon([(px + tx * L, py + ty * L), (px + nx * L * 0.7, py + ny * L * 0.7),
               (px - nx * L * 0.7, py - ny * L * 0.7)], fill=color)


def gen_gears(rng):
    D = 250
    while True:
        count = rng.randint(6, 9)
        links = [rng.choice(["mesh", "mesh", "mesh", "belt", "cross"]) for _ in range(count - 1)]
        if "belt" not in links and "cross" not in links:
            continue
        radii = [rng.randint(95, 150)]
        ok = True
        for lk in links:
            r = D + 10 - radii[-1] if lk == "mesh" else rng.randint(70, 110)
            if not 65 <= r <= 165:
                ok = False
                break
            radii.append(r)
        if not ok:
            continue
        # gears that sit next to each other on the grid but are NOT linked must not touch
        for i in range(count):
            for j in range(i + 2, count):
                (a, b), (c, e) = SNAKE[i], SNAKE[j]
                if abs(a - c) + abs(b - e) == 1 and radii[i] + radii[j] > D - 40:
                    ok = False
        if ok:
            break
    dirs = [1]
    for lk in links:
        dirs.append(dirs[-1] if lk == "belt" else -dirs[-1])
    last_cw = dirs[-1] == 1

    def draw(d, box, show_solution):
        x0, y0, x1, y1 = box
        rows = 1 + (count - 1) // 3
        absw, absh = 2 * D + 340, (rows - 1) * D + 340
        s = min((x1 - x0) / absw, (y1 - y0) / absh)
        ox = x0 + ((x1 - x0) - absw * s) / 2 + 170 * s
        oy = y0 + ((y1 - y0) - absh * s) / 2 + 170 * s
        cs = [(ox + SNAKE[i][0] * D * s, oy + SNAKE[i][1] * D * s) for i in range(count)]
        for i in range(count):
            cx, cy = cs[i]
            col = ORANGE if i == 0 else (GRID if i < count - 1 else (120, 135, 175))
            _gear(d, cx, cy, radii[i] * s, col, s)
            if i < count - 1 and links[i] != "mesh":
                pr = radii[i] * s * 0.6
                d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=INK, width=max(3, int(6 * s)))
            if i > 0 and links[i - 1] != "mesh":
                pr = radii[i] * s * 0.6
                d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=INK, width=max(3, int(6 * s)))
        for i, lk in enumerate(links):
            if lk == "mesh":
                continue
            (ax, ay), (bx, by) = cs[i], cs[i + 1]
            ra, rb = radii[i] * s * 0.6, radii[i + 1] * s * 0.6
            ux, uy = (bx - ax), (by - ay)
            ln = math.hypot(ux, uy)
            nx, ny = -uy / ln, ux / ln
            if lk == "belt":
                segs = [((ax + nx * ra, ay + ny * ra), (bx + nx * rb, by + ny * rb)),
                        ((ax - nx * ra, ay - ny * ra), (bx - nx * rb, by - ny * rb))]
            else:
                segs = [((ax + nx * ra, ay + ny * ra), (bx - nx * rb, by - ny * rb)),
                        ((ax - nx * ra, ay - ny * ra), (bx + nx * rb, by + ny * rb))]
            for p, q in segs:
                d.line([p, q], fill=INK, width=max(4, int(9 * s)))
        for i in range(count):
            cx, cy = cs[i]
            r = radii[i] * s
            if i == 0 or show_solution:
                _arrow(d, cx, cy, r * 0.62, dirs[i] == 1, NAVY_DARK, max(5, int(10 * s)))
            elif i == count - 1:
                d.text((cx, cy), "?", font=F(int(r * 0.9)), fill=NAVY_DARK, anchor="mm")
        d.text((cs[0][0], cs[0][1]), "1", font=F(int(radii[0] * s * 0.35)), fill=NAVY_DARK, anchor="mm")

    return {
        "name": "Gear Puzzle", "category": "Mechanical Reasoning",
        "title": "Gear 1 turns clockwise. Which way does the last gear (?) turn?",
        "rules": "Touching gears turn opposite ways. A straight belt keeps the same way, a crossed belt flips it.",
        "puzzle": lambda d, b: draw(d, b, False),
        "answer": lambda d, b: draw(d, b, True),
        "answer_text": "The last gear turns %s" % ("CLOCKWISE" if last_cw else "ANTICLOCKWISE"),
        "data": {"options": ["Clockwise", "Anticlockwise"], "correct": 0 if last_cw else 1},
        "hashtags": ["#reasoning", "#mechanicalreasoning", "#logicalreasoning", "#brainteaser"],
    }


GENERATORS = {
    "sudoku": gen_sudoku,
    "path": gen_path,
    "maze": gen_maze,
    "spot": gen_spot,
    "race": gen_race,
    "team": gen_team,
    "gears": gen_gears,
}
