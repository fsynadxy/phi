"""Strict validator mirroring prpr's serde structs (parse/rpe.rs, parse/extra.rs, info.rs) plus
semantic hazards found while reading the engine source."""
import json
import math
import os
import re
import sys

import yaml  # pyyaml ships with matplotlib's deps? fall back below
from PIL import Image

ERR, WARN = [], []


def err(m):
    ERR.append(m)


def warn(m):
    WARN.append(m)


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def is_num(v):
    return (isinstance(v, (int, float)) and not isinstance(v, bool)) and math.isfinite(v)


def chk_triple(v, where):
    if not (isinstance(v, list) and len(v) == 3 and all(is_int(x) for x in v)):
        err(f"{where}: bad Triple {v!r}")
        return None
    a, b, c = v
    if b < 0 or c <= 0:
        err(f"{where}: Triple with negative/zero part {v!r}")
        return None
    return a + b / c


PRESETS = {
    "chromatic": {"sampleCount", "power"}, "circleBlur": {"size"}, "fisheye": {"power"},
    "glitch": {"power", "rate", "speed", "blockCount", "colorRate"}, "grayscale": {"factor"},
    "noise": {"seed", "power"}, "pixel": {"size"}, "radialBlur": {"centerX", "centerY", "power", "sampleCount"},
    "shockwave": {"progress", "centerX", "centerY", "width", "distortion", "expand"},
    "vignette": {"color", "extend", "radius"},
}
UI = {"pause", "combonumber", "combo", "score", "bar", "name", "level"}


def chk_event(e, where, kind):
    if not isinstance(e, dict):
        err(f"{where}: event not an object")
        return None
    for k in ("start", "end", "startTime", "endTime"):
        if k not in e:
            err(f"{where}: missing {k}")
            return None
    s = chk_triple(e["startTime"], where + ".startTime")
    t = chk_triple(e["endTime"], where + ".endTime")
    if "easingType" in e and not is_int(e["easingType"]):
        err(f"{where}: easingType not int")
    et = e.get("easingType", 1)
    if is_int(et) and not (0 <= et <= 29):
        warn(f"{where}: easingType {et} out of RPE map -> linear")
    for k in ("easingLeft", "easingRight"):
        if k in e and not is_num(e[k]):
            err(f"{where}: {k} not number")
    if "bezier" in e and not (is_int(e["bezier"]) and 0 <= e["bezier"] <= 255):
        err(f"{where}: bezier not u8")
    if e.get("bezier", 0) != 0:
        warn(f"{where}: bezier easing used")
    for k in ("start", "end"):
        v = e[k]
        if kind == "float" and not is_num(v):
            err(f"{where}: {k} not number: {v!r}")
        if kind == "color" and not (isinstance(v, list) and len(v) == 3 and all(is_int(c) and 0 <= c <= 255 for c in v)):
            err(f"{where}: {k} not RGB u8 triple: {v!r}")
        if kind == "str" and not isinstance(v, str):
            err(f"{where}: {k} not string")
    if s is not None and t is not None and t < s - 1e-9:
        err(f"{where}: endTime < startTime")
    return (s, t, e["start"], e["end"])


def chk_event_list(lst, where, kind, prefill_required=True):
    if not isinstance(lst, list):
        err(f"{where}: not a list")
        return []
    if len(lst) == 0:
        err(f"{where}: EMPTY event array (crashes Anim::chain in Phira)")
        return []
    out = []
    for i, e in enumerate(lst):
        r = chk_event(e, f"{where}[{i}]", kind)
        if r:
            out.append(r)
    for a, b in zip(out, out[1:]):
        if b[0] < a[0] - 1e-9:
            err(f"{where}: events not sorted ({a[0]} then {b[0]})")
        elif b[0] < a[1] - 1e-9:
            err(f"{where}: overlapping events {a[:2]} / {b[:2]}")
    if out and prefill_required and kind == "float" and out[0][0] > 1e-9 and out[0][2] != out[0][3]:
        err(f"{where}: first event starts at beat {out[0][0]} with changing value -> backward extrapolation")
    return out


def validate(pkg):
    info_path = os.path.join(pkg, "info.yml")
    info = yaml.safe_load(open(info_path, encoding="utf-8"))
    for k in ("name", "level", "charter", "composer", "chart", "music", "illustration"):
        if not isinstance(info.get(k), str):
            err(f"info.yml: {k} missing/not str")
    for k in ("chart", "music", "illustration"):
        if isinstance(info.get(k), str) and not os.path.exists(os.path.join(pkg, info[k])):
            err(f"info.yml: {k} file {info[k]} not found")
    for k, typ in (("difficulty", float), ("aspectRatio", float), ("backgroundDim", float), ("lineLength", float),
                   ("offset", float), ("previewStart", float)):
        if k in info and not is_num(info[k]):
            err(f"info.yml: {k} not number")
    if info.get("format") not in (None, "rpe", "pec", "pgr", "pbc"):
        err("info.yml: bad format")
    chart = json.load(open(os.path.join(pkg, info["chart"]), encoding="utf-8"))
    meta = chart.get("META")
    if not isinstance(meta, dict) or not is_int(meta.get("offset")):
        err("META.offset must be an int")
    bpms = chart.get("BPMList")
    if not isinstance(bpms, list) or not bpms:
        err("BPMList missing")
    for i, b in enumerate(bpms or []):
        if not is_num(b.get("bpm")):
            err(f"BPMList[{i}].bpm")
        chk_triple(b.get("startTime"), f"BPMList[{i}].startTime")
    lines = chart.get("judgeLineList")
    if not isinstance(lines, list):
        err("judgeLineList missing")
        return info, chart
    textures = set()
    parents = []
    for li, ln in enumerate(lines):
        w = f"line{li}({ln.get('Name')})"
        for k, t in (("Name", str), ("Texture", str)):
            if not isinstance(ln.get(k), t):
                err(f"{w}: {k} missing")
        if not (is_int(ln.get("isCover")) and 0 <= ln["isCover"] <= 255):
            err(f"{w}: isCover must be u8")
        if "zOrder" in ln and not is_int(ln["zOrder"]):
            err(f"{w}: zOrder not int")
        fa = ln.get("father", -1)
        if fa is not None and not is_int(fa):
            err(f"{w}: father not int")
        parents.append(fa if fa is not None else -1)
        if "rotateWithFather" in ln and not isinstance(ln["rotateWithFather"], bool):
            err(f"{w}: rotateWithFather not bool")
        if "attachUI" in ln and ln["attachUI"] not in UI:
            err(f"{w}: bad attachUI")
        layers = ln.get("eventLayers")
        if not isinstance(layers, list):
            err(f"{w}: eventLayers missing")
            layers = []
        has = {"alphaEvents": False, "speedEvents": False}
        speed_first = None
        for lj, L in enumerate(layers):
            if L is None:
                continue
            if not isinstance(L, dict):
                err(f"{w}.layer{lj}: not object/null")
                continue
            for key in ("alphaEvents", "moveXEvents", "moveYEvents", "rotateEvents", "speedEvents"):
                if key in L:
                    if L[key] is None:
                        continue
                    evs = chk_event_list(L[key], f"{w}.layer{lj}.{key}", "float", key != "speedEvents")
                    if key in has and evs:
                        has[key] = True
                    if key == "speedEvents" and evs:
                        speed_first = evs[0][0] if speed_first is None else min(speed_first, evs[0][0])
        notes = ln.get("notes") or []
        if notes and not has["speedEvents"]:
            err(f"{w}: has notes but no speed events (all notes would sit on the line)")
        if notes and speed_first is not None and speed_first > 1e-9:
            err(f"{w}: speed events must start at beat 0 (got {speed_first})")
        tex = ln.get("Texture")
        ext = ln.get("extended")
        has_text = False
        if ext is not None:
            if not isinstance(ext, dict):
                err(f"{w}: extended not object")
            else:
                for key, kind in (("colorEvents", "color"), ("textEvents", "str"), ("scaleXEvents", "float"),
                                  ("scaleYEvents", "float"), ("inclineEvents", "float"), ("paintEvents", "float"),
                                  ("gifEvents", "float")):
                    if key in ext and ext[key] is not None:
                        chk_event_list(ext[key], f"{w}.ext.{key}", kind, key in ("scaleXEvents", "scaleYEvents"))
                        if key == "textEvents":
                            has_text = True
                if "paintEvents" in ext or "gifEvents" in ext:
                    warn(f"{w}: paint/gif events used")
        if has_text and tex != "line.png":
            err(f"{w}: text events on a texture line are ignored")
        if tex != "line.png":
            textures.add(tex)
        if not has["alphaEvents"] and tex == "line.png" and not notes:
            warn(f"{w}: no alpha events and no notes -> line is invisible and useless")
        for ck in ("posControl", "sizeControl", "alphaControl", "yControl"):
            if ck in ln:
                lst = ln[ck]
                key = ck[:-7]
                if not isinstance(lst, list):
                    err(f"{w}: {ck} not a list")
                    continue
                for i, c in enumerate(lst):
                    if not (is_int(c.get("easing")) and 0 <= c["easing"] <= 255 and is_num(c.get("x")) and is_num(c.get(key))):
                        err(f"{w}: {ck}[{i}] needs easing(u8), x and '{key}'")
                if len(lst) == 2 and lst[0].get("easing") == 1 and abs(lst[0].get(key, 0) - 1) < 1e-4:
                    warn(f"{w}: {ck} with 2 points starting at 1 is treated as default by Phira")
                xs = [c.get("x", 0) for c in lst]
                if xs != sorted(xs):
                    err(f"{w}: {ck} x not increasing")
        for ni, n in enumerate(notes):
            nw = f"{w}.note{ni}"
            for k in ("type", "above", "isFake"):
                if not (is_int(n.get(k)) and 0 <= n[k] <= 255):
                    err(f"{nw}: {k} must be u8 int")
            if not (is_int(n.get("alpha")) and 0 <= n["alpha"] <= 65535):
                err(f"{nw}: alpha must be u16 int")
            for k in ("positionX", "yOffset", "size", "speed", "visibleTime"):
                if not is_num(n.get(k)):
                    err(f"{nw}: {k} must be number")
            if n.get("type") not in (1, 2, 3, 4):
                err(f"{nw}: unknown note type {n.get('type')}")
            s = chk_triple(n.get("startTime"), nw + ".startTime")
            e = chk_triple(n.get("endTime"), nw + ".endTime")
            if n.get("type") == 2 and s is not None and e is not None and e <= s:
                err(f"{nw}: hold with non-positive length")
            if "hitsound" in n:  # prpr bails ("hitsound-missing") when a custom hitsound file is absent
                hs = n["hitsound"]
                if not isinstance(hs, str):
                    err(f"{nw}: hitsound must be a string")
                elif hs not in ("tap.mp3", "flick.mp3", "drag.mp3") and not os.path.exists(os.path.join(pkg, hs)):
                    err(f"{nw}: custom hitsound {hs!r} missing from the package")
    for li, p in enumerate(parents):
        if p != -1 and not (0 <= p < len(lines)):
            err(f"line{li}: father {p} out of range")
    for li in range(len(lines)):
        seen, cur = set(), li
        while parents[cur] != -1:
            if cur in seen:
                err(f"line{li}: parent cycle")
                break
            seen.add(cur)
            cur = parents[cur]
    for t in sorted(textures):
        p = os.path.join(pkg, t)
        if not os.path.exists(p):
            err(f"texture {t} missing from package")
        else:
            try:
                Image.open(p).load()
            except Exception as ex:  # noqa
                err(f"texture {t} unreadable: {ex}")
    ex_path = os.path.join(pkg, "extra.json")
    if os.path.exists(ex_path):
        ex = json.load(open(ex_path, encoding="utf-8"))
        if "bpm" not in ex:
            err("extra.json: 'bpm' is required")
        for i, ef in enumerate(ex.get("effects", [])):
            w = f"extra.effects[{i}]"
            chk_triple(ef.get("start"), w + ".start")
            chk_triple(ef.get("end"), w + ".end")
            sh = ef.get("shader")
            if not isinstance(sh, str):
                err(f"{w}: shader missing")
                continue
            if sh.startswith("/"):
                if not os.path.exists(os.path.join(pkg, sh[1:])):
                    err(f"{w}: custom shader file missing")
                allowed = None
            else:
                if sh not in PRESETS:
                    err(f"{w}: unknown preset shader {sh}")
                    continue
                allowed = PRESETS[sh]
            if "global" in ef and not isinstance(ef["global"], bool):
                err(f"{w}: global must be bool")
            for vn, vv in (ef.get("vars") or {}).items():
                if allowed is not None and vn not in allowed:
                    err(f"{w}: var {vn} not a uniform of {sh}")
                if is_num(vv):
                    continue
                if isinstance(vv, list) and len(vv) == 2 and all(is_num(x) for x in vv):
                    continue  # Vec2: (f32, f32)
                if isinstance(vv, list) and len(vv) == 4 and all(is_int(x) and 0 <= x <= 255 for x in vv):
                    continue  # Color: [u8; 4] -- integers only, floats fail Phira's untagged enum
                if isinstance(vv, list) and vv and all(is_num(x) for x in vv):
                    err(f"{w}.vars.{vn}: {vv!r} matches no Variable form (colors must be 4 ints 0..255)")
                    continue
                if isinstance(vv, list) and vv and all(isinstance(k, dict) for k in vv):
                    prev_end = None
                    for j, k in enumerate(vv):
                        for f in ("startTime", "endTime", "start", "end", "easingType"):
                            if f not in k:
                                err(f"{w}.vars.{vn}[{j}]: missing {f} (easingType is REQUIRED in extra.json)")
                        s = chk_triple(k.get("startTime"), f"{w}.vars.{vn}[{j}].startTime")
                        e = chk_triple(k.get("endTime"), f"{w}.vars.{vn}[{j}].endTime")
                        if prev_end is not None and s is not None and s < prev_end - 1e-9:
                            err(f"{w}.vars.{vn}: keyframes overlap/unsorted")
                        prev_end = e
                    continue
                err(f"{w}.vars.{vn}: unsupported value {vv!r}")
        for i, v in enumerate(ex.get("videos", [])):  # prpr parse/extra.rs ExtVideo + core/video.rs
            w = f"extra.videos[{i}]"
            path = v.get("path")
            if not isinstance(path, str):
                err(f"{w}: path missing")
            elif not os.path.exists(os.path.join(pkg, path)):
                err(f"{w}: video {path!r} missing from the package (Phira fails with video-load-failed)")
            if "time" in v:
                chk_triple(v["time"], w + ".time")
            if v.get("scale", "cropCenter") not in ("cropCenter", "inside", "fit"):
                err(f"{w}: scale must be cropCenter / inside / fit")
            for k in ("alpha", "dim"):
                if k in v and not is_num(v[k]) and not isinstance(v[k], list):
                    err(f"{w}.{k}: must be a number or keyframes")
            for k in v:
                if k not in ("path", "time", "scale", "alpha", "dim", "attach"):
                    warn(f"{w}: unknown field {k}")
    return info, chart


if __name__ == "__main__":
    pkg = sys.argv[1]
    info, chart = validate(pkg)
    nl = len(chart.get("judgeLineList", []))
    nn = sum(len([n for n in (l.get("notes") or []) if not n.get("isFake")]) for l in chart.get("judgeLineList", []))
    print(f"lines={nl} notes={nn} errors={len(ERR)} warnings={len(WARN)}")
    for m in ERR[:60]:
        print("ERROR", m)
    for m in WARN[:30]:
        print("WARN ", m)
    sys.exit(1 if ERR else 0)
