"""Playability audit for a built package (screen-space, two-hand model).

usage: RESPACK=... python tools/gen/playcheck.py <pkg> [limit]

Reports note count, NPS, and every place where the chart asks for something a two-thumb player
cannot do: more than two fingers, notes on top of each other, a hand tapping twice faster than a 16th
(or jumping far within one), notes landing on an invisible line or off screen.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview import ASP, Chart  # noqa: E402

TAP, HOLD, FLICK, DRAG = 1, 2, 3, 4


def collect(ch):
    out = []
    for i, L in enumerate(ch.L):
        for n in L["notes"]:
            if n["fake"]:
                continue
            t = n["time"]
            p = ch.pos(i, t)
            a = math.radians(ch.rot(i, t))
            out.append({"t": t, "end": n["end"], "kind": n["kind"], "line": i, "name": L["name"],
                        "x": p[0] + math.cos(a) * n["x"], "y": p[1] + math.sin(a) * n["x"], "alpha": L["alpha"](t)})
    out.sort(key=lambda n: (n["t"], n["x"]))
    return out


def audit(ch, limit=60):
    spb = ch.spb
    notes = collect(ch)
    probs = []
    B = lambda t: t / spb  # noqa: E731
    # groups of simultaneous notes
    groups, cur = [], []
    for n in notes:
        if cur and n["t"] - cur[0]["t"] > 0.002:
            groups.append(cur)
            cur = []
        cur.append(n)
    if cur:
        groups.append(cur)
    holds = []  # (end, x)
    hands = {0: None, 1: None}  # last (t, x, y, kind)
    busy = {0: -1.0, 1: -1.0}
    stats = {"notes": len(notes), "groups": len(groups), "3+fingers": 0, "overlap": 0, "fast_hand": 0, "far_jump": 0,
             "invisible_line": 0, "offscreen": 0}
    for g in groups:
        t = g[0]["t"]
        holds = [h for h in holds if h[0] > t + 0.01]
        taps = [n for n in g if n["kind"] != DRAG]
        fingers = len(taps) + len(holds) + (1 if len(taps) < len(g) and not taps else 0)
        if len(taps) + len(holds) > 2:
            stats["3+fingers"] += 1
            probs.append(f"b{B(t):7.2f} {len(taps)} notes + {len(holds)} holds at once")
        for a in range(len(g)):
            for b in range(a + 1, len(g)):
                if math.hypot(g[a]["x"] - g[b]["x"], (g[a]["y"] - g[b]["y"]) * 1.5) < 0.17:
                    stats["overlap"] += 1
                    probs.append(f"b{B(t):7.2f} overlapping notes at x={g[a]['x']:.2f}")
        for n in g:
            if n["alpha"] < 0.3:
                stats["invisible_line"] += 1
                probs.append(f"b{B(t):7.2f} note on invisible line {n['name']}")
            if not (-1.0 < n["x"] < 1.0 and -1 / ASP < n["y"] < 1 / ASP):
                stats["offscreen"] += 1
                probs.append(f"b{B(t):7.2f} off-screen hit {n['name']} ({n['x']:.2f},{n['y']:.2f})")
        # hand assignment (drags excluded: a finger can slide through them)
        order = sorted(taps, key=lambda n: n["x"])
        if len(order) == 2:
            assign = [(0, order[0]), (1, order[1])]
        elif len(order) == 1:
            n = order[0]
            free = [h for h in (0, 1) if busy[h] <= t + 0.01]
            if len(free) == 1:
                h = free[0]
            elif abs(n["x"]) > 0.12:
                h = 0 if n["x"] < 0 else 1
            else:
                last = {h: (hands[h][0] if hands[h] else -9) for h in (0, 1)}
                h = 0 if last[0] <= last[1] else 1
            assign = [(h, n)]
        else:
            assign = []
        for h, n in assign:
            if busy[h] > t + 0.01:
                probs.append(f"b{B(t):7.2f} hand {'LR'[h]} still holding")
            prev = hands[h]
            if prev:
                dt = t - prev[0]
                d = math.hypot(n["x"] - prev[1], (n["y"] - prev[2]))
                if dt < spb / 4 - 0.004 and not (prev[3] == FLICK and n["kind"] == FLICK and d < 0.3):
                    stats["fast_hand"] += 1
                    probs.append(f"b{B(t):7.2f} hand {'LR'[h]} twice within {dt / spb * 4:.2f} 16th")
                elif dt > 0 and d / dt > 7.0 and dt < spb:
                    stats["far_jump"] += 1
                    probs.append(f"b{B(t):7.2f} hand {'LR'[h]} jumps {d:.2f} in {dt:.3f}s")
            hands[h] = (t, n["x"], n["y"], n["kind"])
            if n["kind"] == HOLD:
                busy[h] = n["end"]
                holds.append((n["end"], n["x"]))
    # density
    ts = [n["t"] for n in notes]
    peak, j = 0, 0
    for i in range(len(ts)):
        while ts[i] - ts[j] > 1.0:
            j += 1
        peak = max(peak, i - j + 1)
    stats["nps_peak_1s"] = peak
    return stats, probs[:limit]


if __name__ == "__main__":
    ch = Chart(sys.argv[1])
    st, pr = audit(ch, int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    kinds = {}
    for n in collect(ch):
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print(st, {"tap": kinds.get(1, 0), "hold": kinds.get(2, 0), "flick": kinds.get(3, 0), "drag": kinds.get(4, 0)})
    for p in pr:
        print(" ", p)
