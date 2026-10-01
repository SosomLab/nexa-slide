# -*- coding: utf-8 -*-
"""레이아웃 검사 — 덱 JSON 만 읽어 슬라이드마다 겹침·넘침·최소 글자 크기·슬라이드 밖·고정폭 정렬을 찾는다 (DB·서버 불필요).

    python3 studio/check_layout.py --workspace <작업 공간> ch00            # 사람이 읽는 목록, ERROR 가 있으면 종료 코드 1
    python3 studio/check_layout.py --workspace <작업 공간> ch00 --json     # JSON(편집기·세션용)
    python3 studio/check_layout.py --workspace <작업 공간>                 # 모든 덱

규칙 (id 는 Genspark check_slide_layout 형식을 본떴다 — research 노트 7절)
    t1.overlap.text-text     글자가 있는 두 요소의 "글자 영역"이 겹침          ERROR(작은 쪽의 10% 이상) / WARNING
    t1.overlap.text-crosses-border  글자 영역이 도형(면·테두리 있는 상자) 경계에 걸침(일부만 안)   WARNING
    t2.cutoff.container      글자 영역이 그것을 담은 도형 밖으로 나감(글자 시작점이 들어 있는 가장 작은 도형 기준)   WARNING
    t2.cutoff.spill          글자가 상자보다 김(줄 수 추정) · 줄바꿈 없는 줄이 폭을 넘음   ERROR(15% 이상) / WARNING
    t3.offslide              요소가 슬라이드(1280×720) 밖으로 나감               ERROR
    t4.font.min              글자 크기가 역할별 최소 pt 보다 작음(pt = px × 0.75)  ERROR
    t5.mono.align            실행계획(plan)의 | 열 위치가 줄마다 다름(강조 표시를 뺀 원문 기준)   WARNING

기준값은 작업 공간 nexa-slide.json 의 "check" 로 바꾼다:
    "check": {"minFontPt": {"default": 9, "footnotes": 7}, "ignore": ["t5.mono.align"], "ignoreSlides": {"ch00": ["s12"]}}

추정의 한계: 줄바꿈은 어절 단위(keep-all)로 글꼴 폭을 재서 흉내 낸다(Pillow 가 있으면 실제 글꼴). 표·글머리 높이는 근사.
화면·PPT 의 최종 확인은 compare.py(PowerPoint 렌더 대조)로 한다.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, DECKS, code_lines, load_deck, plain, safe_id, text_width  # noqa: E402

W, H = 1280, 720
CHK = CONFIG.get("check", {})
MIN_PT = {"default": 9, "footnotes": 7, **CHK.get("minFontPt", {})}
IGNORE = set(CHK.get("ignore", []))
IGNORE_SLIDES = CHK.get("ignoreSlides", {})
TEXT_TYPES = ("text", "pill", "rect", "ellipse")
_PLAN_MARK = re.compile(r"\[\[(?:ok:|warn:)?(.+?)\]\]")


def _pad(el, d=0):
    p = el.get("pad", d)
    if isinstance(p, (int, float)):
        return [p] * 4
    p = list(p) + [0] * (4 - len(p))
    return p


def _wrap_count(line, size, bold, mono, width):
    """한 단락이 width 안에서 몇 줄이 되는지 — 어절 단위로 채운다(keep-all). 한 어절이 폭보다 길면 그 안에서 끊긴다."""
    if width <= 0:
        return 1
    words = plain(line).split(" ")
    n, cur = 1, 0.0
    sp = text_width(" ", size, bold, mono)
    for w in words:
        ww = text_width(w, size, bold, mono)
        add = ww if cur == 0 else sp + ww
        if cur + add <= width + 0.5:
            cur += add
        elif cur == 0:  # 어절 하나가 폭보다 김
            k = math.ceil(ww / width)
            n += k - 1
            cur = ww - (k - 1) * width
        else:
            n += 1
            cur = ww
            if ww > width:
                k = math.ceil(ww / width)
                n += k - 1
                cur = ww - (k - 1) * width
    return n


def text_extent(el):
    """글자 요소의 실제 글자 영역 [x, y, w, h] 과 필요한 높이·넓이 — 상자 안 정렬(align·valign)을 따른다."""
    t = el["type"]
    size = float(el.get("size") or 20)
    lh = float(el.get("lineHeight") or (1.4 if t == "text" else 1.2))
    bold = bool(el["bold"]) if "bold" in el else t == "pill"
    mono = el.get("font") == "mono"
    wrap = el["wrap"] if "wrap" in el else t in ("text", "rect")
    align = el.get("align") or ("center" if t in ("pill", "ellipse") else "left")
    valign = el.get("valign") or ("top" if t == "text" else "middle")
    pt, pr, pb, pl = _pad(el)
    iw, ih = el["w"] - pl - pr, el["h"] - pt - pb
    lines = str(el.get("text") or "").split("\n")
    widths = [text_width(ln, size, bold, mono) for ln in lines]
    n = sum(_wrap_count(ln, size, bold, mono, iw) for ln in lines) if wrap else len(lines)
    need_h = n * size * lh
    need_w = max(widths) if widths else 0
    cw = min(need_w, iw) if wrap else need_w
    ch = need_h
    x0 = el["x"] + pl + {"left": 0, "center": (iw - cw) / 2, "right": iw - cw}.get(align, 0)
    y0 = el["y"] + pt + {"top": 0, "middle": (ih - ch) / 2, "bottom": ih - ch}.get(valign, 0)
    return [x0, y0, cw, ch], need_h, need_w, iw, ih, wrap


def _inter(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return (x1, y1, x2 - x1, y2 - y1) if x2 > x1 and y2 > y1 else None


def _issue(rule, sev, slide, n, els, box, msg, **detail):
    return {"rule": rule, "severity": sev, "slide": slide["id"], "n": n, "elements": els,
            "box": [round(v) for v in box] if box else None, "message": msg, "detail": detail}


def _snip(el):
    return plain(str(el.get("text") or "")).replace(chr(10), " ")[:60]


def _contains(outer, inner, tol=1):
    return (inner[0] >= outer[0] - tol and inner[1] >= outer[1] - tol and
            inner[0] + inner[2] <= outer[0] + outer[2] + tol and inner[1] + inner[3] <= outer[1] + outer[3] + tol)


def check_slide(slide, n):
    out = []
    textual = []
    shapes = [e for e in slide.get("elements", []) if e.get("type") in ("rect", "ellipse", "pill") and (e.get("fill") or e.get("stroke"))]
    for el in slide.get("elements", []):
        t = el.get("type")
        if t in ("line", "arrow", "curve"):
            continue
        box = [el.get("x", 0), el.get("y", 0), el.get("w", 0), el.get("h", 0)]
        # t3 슬라이드 밖
        if box[0] < -1 or box[1] < -1 or box[0] + box[2] > W + 1 or box[1] + box[3] > H + 1:
            out.append(_issue("t3.offslide", "ERROR", slide, n, [el["id"]], box,
                              f"{el['id']}({t}) 가 슬라이드 밖으로 나감", x=box[0], y=box[1], right=box[0] + box[2], bottom=box[1] + box[3]))
        # t4 최소 글자 크기
        sizes = []
        if t in TEXT_TYPES and el.get("text"):
            sizes.append(("", float(el.get("size") or (14 if t == "pill" else 20))))
        elif t == "bullets":
            sizes += [("", float(el.get("size") or 20))]
            if any(isinstance(i, dict) and i.get("sub") for i in el.get("items", [])):
                sizes.append(("하위 ", float(el.get("subSize") or 17)))
        elif t in ("table", "plan", "plan-table", "code"):
            sizes.append(("", float(el.get("size") or {"code": 15, "plan": 14}.get(t, 16))))
        role = el.get("role") or "default"
        lim = MIN_PT.get(role, MIN_PT["default"])
        for label, px in sizes:
            if px * 0.75 + 1e-6 < lim:
                out.append(_issue("t4.font.min", "ERROR", slide, n, [el["id"]], box,
                                  f"{el['id']}({t}{'·' + role if role != 'default' else ''}) {label}글자 {px:g}px = {px * 0.75:g}pt < 최소 {lim:g}pt",
                                  px=px, pt=round(px * 0.75, 2), min_pt=lim, role=role))
        # t2 넘침 (글자 상자)
        if t in TEXT_TYPES and el.get("text"):
            ext, need_h, need_w, iw, ih, wrap = text_extent(el)
            textual.append((el, ext))
            if need_h > ih + 2:
                over = (need_h - ih) / max(ih, 1)
                out.append(_issue("t2.cutoff.spill", "ERROR" if over >= 0.15 else "WARNING", slide, n, [el["id"]], box,
                                  f"{el['id']}({t}) 글자 높이 {need_h:.0f}px > 상자 {ih:.0f}px (+{over:.0%})",
                                  need=round(need_h), have=round(ih), axis="y"))
            if not wrap and need_w > iw + 2:
                over = (need_w - iw) / max(iw, 1)
                out.append(_issue("t2.cutoff.spill", "ERROR" if over >= 0.15 else "WARNING", slide, n, [el["id"]], box,
                                  f"{el['id']}({t}) 한 줄 폭 {need_w:.0f}px > 상자 {iw:.0f}px (+{over:.0%})",
                                  need=round(need_w), have=round(iw), axis="x"))
        elif t in ("code", "plan"):
            size = float(el.get("size") or (15 if t == "code" else 14))
            lh = float(el.get("lineHeight") or (1.6 if t == "code" else 1.5))
            nl = len(code_lines(el)) if t == "code" else len(str(el.get("text") or "").split("\n"))
            pad = 24 if t == "code" else sum(_pad(el, [16, 18, 16, 18])[0::2])
            need_h = nl * size * lh + pad
            if need_h > el["h"] + 2:
                over = (need_h - el["h"]) / max(el["h"], 1)
                out.append(_issue("t2.cutoff.spill", "ERROR" if over >= 0.15 else "WARNING", slide, n, [el["id"]], box,
                                  f"{el['id']}({t}) {nl}줄 높이 {need_h:.0f}px > 상자 {el['h']}px", need=round(need_h), have=el["h"], axis="y"))
            if t == "plan":  # t5 고정폭 정렬
                cols = []
                for ln in str(el.get("text") or "").split("\n"):
                    raw = _PLAN_MARK.sub(r"\1", ln)
                    if raw.lstrip().startswith("|"):
                        cols.append(tuple(i for i, c in enumerate(raw) if c == "|"))
                if len(set(cols)) > 1:
                    common = max(set(cols), key=cols.count)
                    bad = [i + 1 for i, c in enumerate(cols) if c != common]
                    out.append(_issue("t5.mono.align", "WARNING", slide, n, [el["id"]], box,
                                      f"{el['id']}(plan) | 열 위치가 다른 줄 {len(bad)}개 (표 줄 번호 {bad[:8]})", lines=bad))
    # t1 글자 영역 겹침 — 같은 슬라이드의 글자 요소 쌍
    for i in range(len(textual)):
        for j in range(i + 1, len(textual)):
            (a, ea), (b, eb) = textual[i], textual[j]
            hit = _inter(ea, eb)
            if not hit or hit[2] < 2 or hit[3] < 2:
                continue
            small = min(ea[2] * ea[3], eb[2] * eb[3]) or 1
            ratio = hit[2] * hit[3] / small
            out.append(_issue("t1.overlap.text-text", "ERROR" if ratio >= 0.10 else "WARNING", slide, n, [a["id"], b["id"]], hit,
                              f"{a['id']}·{b['id']} 글자 영역 겹침 {hit[2]:.0f}×{hit[3]:.0f}px ({ratio:.0%})", ratio=round(ratio, 3)))
    # t1 도형 경계 걸침 · t2 담은 도형 밖 — Genspark text-crosses-border / cutoff.spill(기하 비교) 대응
    for el, ext in textual:
        sx, sy = el["x"], el["y"]
        holders = []
        for sh in shapes:
            if sh is el:
                continue
            sb = [sh["x"], sh["y"], sh["w"], sh["h"]]
            starts_in = sb[0] - 1 <= sx <= sb[0] + sb[2] and sb[1] - 1 <= sy <= sb[1] + sb[3]
            if starts_in:  # 글자 시작점이 들어 있는 도형 = 글자를 담은 도형 후보
                holders.append(sb)
                continue
            hit = _inter(ext, sb)
            if hit and min(hit[2], hit[3]) >= 2 and not _contains(sb, ext) and not _contains(ext, sb):
                out.append(_issue("t1.overlap.text-crosses-border", "WARNING", slide, n, [el["id"], sh["id"]], hit,
                                  f'{el["id"]}({el["type"]}) "{_snip(el)}" ∩ {sh["id"]}({sh["type"]}) 경계 → '
                                  f"{hit[2]:.0f}×{hit[3]:.0f} at ({hit[0]:.0f},{hit[1]:.0f})"))
        if holders:
            hb = min(holders, key=lambda b: b[2] * b[3])
            cut_r = ext[0] + ext[2] - (hb[0] + hb[2])
            cut_b = ext[1] + ext[3] - (hb[1] + hb[3])
            if cut_r > 2 or cut_b > 2:
                out.append(_issue("t2.cutoff.container", "WARNING", slide, n, [el["id"]], ext,
                                  f'{el["id"]}({el["type"]}) "{_snip(el)}" 담은 도형 밖으로 ~{max(cut_r, cut_b):.0f}px',
                                  cut_right=round(cut_r), cut_bottom=round(cut_b)))
    return out


def check_deck(deck_id):
    deck = load_deck(deck_id)
    skip = set(IGNORE_SLIDES.get(deck_id, []))
    issues = []
    for n, s in enumerate(deck.get("slides", []), 1):
        if s.get("id") in skip:
            continue
        issues += [dict(i, deck=deck_id) for i in check_slide(s, n) if i["rule"] not in IGNORE]
    order = {"ERROR": 0, "WARNING": 1}
    issues.sort(key=lambda i: (i["n"], order[i["severity"]], i["rule"]))
    return {"deck": deck_id, "slides": len(deck.get("slides", [])), "issues": issues,
            "errors": sum(i["severity"] == "ERROR" for i in issues), "warnings": sum(i["severity"] == "WARNING" for i in issues),
            "minFontPt": MIN_PT}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ids = args or sorted(p.stem for p in DECKS.glob("*.json") if not p.name.endswith(".requests.json"))
    results = []
    for i in ids:
        if not safe_id(i) or not (DECKS / f"{i}.json").exists():
            sys.exit(f"덱 없음: {i}")
        results.append(check_deck(i))
    if "--json" in sys.argv:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=1))
    else:
        for r in results:
            print(f"[{r['deck']}] 슬라이드 {r['slides']}장 · ERROR {r['errors']} · WARNING {r['warnings']}  (최소 pt {r['minFontPt']})")
            for i in r["issues"]:
                print(f"  {i['n']:>3}({i['slide']}) {i['severity']:<7} {i['rule']:<22} {i['message']}")
    return 1 if any(r["errors"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
