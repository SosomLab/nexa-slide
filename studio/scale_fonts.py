# -*- coding: utf-8 -*-
"""덱 전체 글자 크기를 비율로 키우고(줄이고), 커진 글에 맞춰 상자 높이·세로 배치를 다시 잡는다.

    python3 nexa.py scale_fonts <덱> --ratio 1.2                      # 모든 글자 1.2배 + 상자·배치 맞춤 → 덱 저장(save_deck 과 같은 경로)
    python3 nexa.py scale_fonts <덱> --ratio 1.2 --role body,title    # 역할을 골라서(body = role 이 없는 본문 요소)
    python3 nexa.py scale_fonts <덱> --ratio 1.2 --slides s03,s05     # 일부 슬라이드만
    python3 nexa.py scale_fonts <덱> --ratio 1.2 --dry-run            # 무엇이 어떻게 바뀌는지만 본다(저장 안 함)
    python3 nexa.py scale_fonts <덱> --ratio 1.2 --keep-ratio         # 바닥을 넘쳐도 비율을 낮추지 않는다(넘침은 check_layout 으로 손본다)
    python3 nexa.py scale_fonts <덱> --ratio 1.2 --no-fit             # 글자 크기만(상자·배치는 그대로)
    python3 nexa.py scale_fonts <덱> --ratio 1.2 --out x.json         # 덱 대신 다른 파일에

요소별 고정 size·고정 상자로 된 덱(원본 PPT 를 옮긴 덱 등)에서 "전체적으로 조금 더 크게"를 값 하나로 끝내려는 명령이다.
템플릿 sizes.minPx(lecture-large)는 하한만 올리므로 이미 큰 글에는 효과가 없다 — 이 명령은 비율이라 모든 글이 같이 커진다.

슬라이드마다
  1. 글자 크기(size·subSize)에 비율을 곱한다(정수 px). 바닥 부품(role crumb·page·footnotes·decor)과 잠긴(locked) 요소는 --role 로 고르지 않는 한 그대로.
  2. 맞춤(fit): 글이 상자보다 커지면 상자 높이를 늘리고(줄바꿈 없는 글·칩은 폭도), 늘어난 만큼 그 아래(가로로 겹치는) 요소를 내린다.
     글상자를 담은 도형(카드 rect)은 안의 글에 맞춰 같이 늘고, 그 아래 요소도 내려간다. 표는 행 높이(rowH)를 행별로 늘린다.
     오른쪽으로 커진 칩은 같은 줄의 오른쪽 이웃을 민다. 바닥 부품(경로·쪽번호·각주)·잠긴 요소는 움직이지 않는다.
  3. 내린 결과가 바닥 부품 위 한계를 넘으면 비율을 0.02 씩 낮춰 들어가는 값으로 다시 한다(--keep-ratio 가 아니면).
     1.02 까지 낮춰도 넘치면 그 슬라이드는 그대로 두고 알린다 — 내용을 줄이거나 나누는 일은 사람·AI 가 한다.
content 에 두려면 `"fontScale": 1.2`(또는 {"ratio": 1.2, "roles": ["body"], "keep": true}) — build_deck 이 같은 규칙으로 적용한다(슬라이드마다 덮어쓰기 가능).

줄 수·폭 추정은 check_layout 과 같은 방법(어절 단위 줄바꿈, Pillow 가 있으면 실제 글꼴)이라 저장 뒤 check_layout 으로 확인한다.
"""
import argparse
import copy
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CELL_PADX, CODE_PAD_Y, DECKS, bullet_rows, num_hang, code_lines, load_deck, pad_of, safe_id, table_grid, use_fonts  # noqa: E402
from check_layout import W, H, _wrap_count, text_extent  # noqa: E402

FIXED_ROLES = ("crumb", "page", "footnotes", "decor")  # 바닥·장식 부품 — 고르지 않으면 크기를 바꾸지 않고, 자리는 언제나 그대로
TEXT_TYPES = ("text", "pill", "rect", "ellipse")
SIZED = ("bullets", "table", "plan-table", "plan", "code")
DEFAULT_SIZE = {"text": 20, "pill": 20, "rect": 20, "ellipse": 20, "bullets": 20, "table": 16, "plan-table": 16, "plan": 14, "code": 15}
STEP = 0.02      # 바닥을 넘칠 때 비율을 낮추는 단위
FLOOR_GAP = 8    # 바닥 부품 위에 남기는 틈(px)
HOLDER_PAD = 12  # 카드(담은 도형)가 늘어나기 전에 지키는 아래 여백(px) — 원래 여백이 이보다 작으면 그 값


def _px(v):
    return int(v + 0.5)


def _role(el):
    return el.get("role") or "body"


def _fixed(el):
    return _role(el) in FIXED_ROLES or bool(el.get("locked"))


def _box(el):
    return (el.get("x", 0), el.get("y", 0), el.get("w", 0), el.get("h", 0))


def _lines(text, size, bold, mono, width):
    return sum(_wrap_count(ln, size, bold, mono, width) for ln in str(text or "").split("\n"))


# ---------- 1. 글자 크기 ----------
def scale_el(el, ratio, roles=None):
    """요소 하나의 글자 크기에 비율을 곱한다. 바꿨으면 True. roles 가 있으면 그 역할만(body = role 없음), 없으면 바닥 부품을 뺀 전부."""
    t, role = el.get("type"), _role(el)
    if roles is not None:
        if role not in roles:
            return False
    elif role in FIXED_ROLES:
        return False
    keys = []
    if t in TEXT_TYPES and el.get("text"):
        keys = ["size"]
    elif t == "bullets" and el.get("items"):
        keys = ["size", "subSize"]
    elif t in SIZED:
        keys = ["size"]
    for k in keys:
        cur = el.get(k)
        if cur is None:
            cur = 17 if k == "subSize" else DEFAULT_SIZE.get(t, 20)
        el[k] = _px(float(cur) * ratio)
    return bool(keys)


# ---------- 2. 상자 맞춤 ----------
def fit_el(el):
    """글이 다 들어가게 상자를 늘린다(높이, 줄바꿈 없는 글은 폭, 표는 행 높이). 돌려주는 값: (늘린 높이, 늘린 폭)."""
    t = el.get("type")
    dh = dw = 0
    if t in TEXT_TYPES and el.get("text"):
        _, need_h, need_w, iw, ih, wrap = text_extent(el)
        pt, pr, pb, pl = pad_of(el)
        if need_h > ih + 1:
            dh = math.ceil(need_h + pt + pb) - el["h"]
        if not wrap and need_w > iw + 1:
            dw = math.ceil(need_w + pl + pr + 2) - el["w"]
    elif t == "bullets" and el.get("items"):
        size, sub, lh = float(el.get("size") or 20), float(el.get("subSize") or 17), float(el.get("lineHeight") or 1.55)
        pt, pr, pb, pl = pad_of(el)
        rows = bullet_rows({**el, "spread": False})  # 균등 간격이라도 보통 간격만큼은 들어가게
        need = pt + pb
        for i, (text, lvl, after, num) in enumerate(rows):
            sz = sub if lvl else size
            hang0 = 20 if lvl else 28
            need += _lines(text, sz, False, False, el["w"] - pl - pr - (48 if lvl else 28) - ((num_hang(num["label"], sz, hang0) - hang0) if num else 0)) * sz * lh
            need += after if i < len(rows) - 1 else 0
        if need > el["h"] + 1:
            dh = math.ceil(need) - el["h"]
    elif t in ("table", "plan-table"):
        g = table_grid(el)
        size = float(g["size"])
        need = []
        for row in g["cells"]:
            n = max((_lines(c["text"], size, c["bold"], c["font"] == "mono", g["colW"][j] - 2 * CELL_PADX) for j, c in enumerate(row)), default=1)
            need.append(n * size * 1.4 + 4)
        if any(nd > rh + 1 for nd, rh in zip(need, g["rowH"])):
            new = [math.ceil(max(nd, rh)) for nd, rh in zip(need, g["rowH"])]  # 행별 px 그대로(합 = h)
            el["rowH"] = new
            dh = sum(new) - el["h"]
    elif t in ("code", "plan"):
        size = float(el.get("size") or DEFAULT_SIZE[t])
        lh = float(el.get("lineHeight") or (1.6 if t == "code" else 1.5))
        nl = len(code_lines(el)) if t == "code" else len(str(el.get("text") or "").split("\n"))
        pad = 2 * CODE_PAD_Y if t == "code" else sum(pad_of(el, [16, 18, 16, 18])[0::2])
        need = nl * size * lh + pad
        if need > el["h"] + 1:
            dh = math.ceil(need) - el["h"]
    if dh > 0:
        el["h"] += dh
    if dw > 0:
        if (el.get("align") or "") == "right":  # 오른쪽 정렬은 오른쪽 끝을 지킨다
            el["x"] = max(0, el["x"] - dw)
        el["w"] += dw
    return max(dh, 0), max(dw, 0)


def _move(el, dy, dx=0):
    if not dy and not dx:
        return
    el["y"] = el.get("y", 0) + dy
    el["x"] = el.get("x", 0) + dx
    if "y1" in el:  # 선·화살표는 끝점도
        el["y1"], el["y2"] = el["y1"] + dy, el["y2"] + dy
        el["x1"], el["x2"] = el["x1"] + dx, el["x2"] + dx


def _x_overlap(a, b):
    return min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])


def _y_overlap(a, b):
    return min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])


def _contains(outer, inner, tol=2):
    return (inner[0] >= outer[0] - tol and inner[1] >= outer[1] - tol and
            inner[0] + inner[2] <= outer[0] + outer[2] + tol and inner[1] + inner[3] <= outer[1] + outer[3] + tol)


def refit(els):
    """상자를 늘리고 아래·오른쪽 요소를 민다(위에서 아래, 왼쪽에서 오른쪽 순서). 돌려주는 값: {grown, moved, over}.
    over = 움직인 요소의 바닥이 한계(바닥 부품 위 FLOOR_GAP, 원래 가장 낮은 요소보다 아래로는 가지 않음)를 넘은 px."""
    orig = {e["id"]: _box(e) for e in els}
    fixed = {e["id"] for e in els if _fixed(e)}
    floor = min([orig[i][1] for i in fixed if orig[i][1] > H / 2] + [H - 2 * FLOOR_GAP]) - FLOOR_GAP
    floor = max(floor, max((orig[e["id"]][1] + orig[e["id"]][3] for e in els if e["id"] not in fixed), default=0))
    # 담은 도형 후보: 면·테두리가 있는 rect·ellipse(글상자가 그 위에 놓인 카드)
    shapes = [e for e in els if e.get("type") in ("rect", "ellipse") and (e.get("fill") or e.get("stroke")) and e["id"] not in fixed]

    def holder_of(e):
        hs = [s for s in shapes if s is not e and _contains(orig[s["id"]], orig[e["id"]])]
        return min(hs, key=lambda s: orig[s["id"]][2] * orig[s["id"]][3]) if hs else None

    hold = {e["id"]: holder_of(e) for e in els if e["id"] not in fixed}
    hpad = {}  # 담은 도형의 아래 여백 = 안에 든 요소 중 가장 낮은 것과의 원래 틈(HOLDER_PAD 까지만 지킨다 — 그 안쪽은 여유로 쓴다)
    for i, h in hold.items():
        if h is not None:
            hpad[h["id"]] = max(0, min(hpad.get(h["id"], HOLDER_PAD), orig[h["id"]][1] + orig[h["id"]][3] - (orig[i][1] + orig[i][3])))
    dy = {e["id"]: 0 for e in els}
    dx = {e["id"]: 0 for e in els}
    grown = moved = 0
    for e in sorted(els, key=lambda e: (orig[e["id"]][1], orig[e["id"]][0])):
        if e["id"] in fixed:
            continue
        ob = orig[e["id"]]
        holder = hold[e["id"]]
        if holder is not None:  # 담은 도형이 내려간 만큼 같이
            dy[e["id"]] = max(dy[e["id"]], dy[holder["id"]])
            dx[e["id"]] = max(dx[e["id"]], dx[holder["id"]])
        _move(e, dy[e["id"]], dx[e["id"]])
        if dy[e["id"]] or dx[e["id"]]:
            moved += 1
        gh, gw = fit_el(e)
        if gh or gw:
            grown += 1
        d_bottom = e["y"] + e["h"] - (ob[1] + ob[3])
        d_right = e["x"] + e["w"] - (ob[0] + ob[2])
        if d_bottom > 0 and holder is not None:  # 카드 안의 글이 카드 아래 여백을 넘으면 카드를 늘리고, 카드 아래를 민다
            hb = orig[holder["id"]]
            holder["h"] = max(holder["h"], e["y"] + e["h"] + hpad[holder["id"]] - holder["y"])
            hd = holder["y"] + holder["h"] - (hb[1] + hb[3])
            if hd > 0:
                for f in els:
                    if f is holder or f["id"] in fixed or _contains(hb, orig[f["id"]]):
                        continue
                    if orig[f["id"]][1] >= hb[1] + hb[3] - 2 and _x_overlap(hb, orig[f["id"]]) > 0:
                        dy[f["id"]] = max(dy[f["id"]], hd)
        for f in els:
            if f is e or f["id"] in fixed:
                continue
            fb = orig[f["id"]]
            if d_bottom > 0 and fb[1] >= ob[1] + ob[3] - 2 and _x_overlap(ob, fb) > 0:
                dy[f["id"]] = max(dy[f["id"]], d_bottom)
            if d_right > 0 and fb[0] >= ob[0] + ob[2] - 2 and _y_overlap(ob, fb) > 0:
                dx[f["id"]] = max(dx[f["id"]], d_right)
    bottom = max((e["y"] + e["h"] for e in els if e["id"] not in fixed), default=0)
    return {"grown": grown, "moved": moved, "over": max(0, bottom - floor)}


# ---------- 3. 슬라이드 하나 ----------
def parse_scale(spec):
    """content 의 fontScale 값 → scale_slide 인자. 숫자 = 비율, 사전 = {ratio, roles, fit, keep}."""
    if isinstance(spec, dict):
        return {"ratio": float(spec.get("ratio") or 1), "roles": spec.get("roles"), "fit": spec.get("fit", True), "keep": bool(spec.get("keep"))}
    return {"ratio": float(spec), "roles": None, "fit": True, "keep": False}


def scale_slide(slide, ratio, roles=None, fit=True, keep=False):
    """슬라이드의 글자를 ratio 배로(fit 이면 상자·배치도). 넘치면 비율을 STEP 씩 낮춰 들어가는 값을 찾는다(keep 이면 그대로).
    돌려주는 값: {applied, ratio(실제), requested, scaled, grown, moved, over}. applied 가 거짓이면 슬라이드는 바뀌지 않았다."""
    r = ratio
    while True:
        els = copy.deepcopy(slide.get("elements", []))
        info = {"applied": True, "ratio": round(r, 2), "requested": ratio, "scaled": sum(scale_el(e, r, roles) for e in els),
                "grown": 0, "moved": 0, "over": 0}
        if fit:
            info.update(refit(els))
        if keep or not fit or info["over"] <= 0 or ratio <= 1:
            slide["elements"] = els
            return info
        r = round(r - STEP, 2)
        if r < 1 + STEP / 2:  # 거의 원래 크기까지 낮춰도 넘침 — 그대로 둔다
            info["applied"] = False
            return info


def _fmt(sid, info):
    if not info["applied"]:
        return f"  {sid}  그대로 — ×{info['requested']:.2f}~1.02 모두 바닥을 {info['over']:.0f}px 넘침(내용을 줄이거나 나눠야 한다)"
    s = f"  {sid}  ×{info['ratio']:.2f}"
    if info["ratio"] != round(info["requested"], 2):
        s += f" (요청 ×{info['requested']:.2f} 은 바닥 넘침 → 낮춤)"
    s += f"  글자 {info['scaled']} · 상자 늘림 {info['grown']} · 옮김 {info['moved']}"
    if info["over"] > 0:
        s += f" · 바닥 {info['over']:.0f}px 넘침"
    return s


def main():
    ap = argparse.ArgumentParser(description="덱 글자 크기를 비율로 키우고 상자·세로 배치를 다시 잡는다")
    ap.add_argument("deck")
    ap.add_argument("--ratio", type=float, required=True, help="글자 크기 배율(예: 1.2)")
    ap.add_argument("--role", help="바꿀 역할(쉼표) — body(role 없음)·title·subtitle·label·crumb·page·footnotes. 없으면 바닥 부품을 뺀 전부")
    ap.add_argument("--slides", help="슬라이드 id(쉼표). 없으면 전부")
    ap.add_argument("--no-fit", action="store_true", help="글자 크기만 바꾸고 상자·배치는 그대로")
    ap.add_argument("--keep-ratio", action="store_true", help="바닥을 넘쳐도 비율을 낮추지 않는다")
    ap.add_argument("--dry-run", action="store_true", help="결과만 보고 저장하지 않는다")
    ap.add_argument("--out", help="덱 대신 이 파일에 쓴다(원장 밖)")
    ap.add_argument("--request", help="처리 중인 요청 id(원장)")
    ap.add_argument("--note", help="원장 한 줄(기본: 비율·역할)")
    ap.add_argument("--label", default=os.environ.get("NEXA_SLIDE_SESSION", ""), help="세션 이름(기본 NEXA_SLIDE_SESSION)")
    ap.add_argument("--force", action="store_true", help="편집기가 그 사이 저장했어도 덮어쓴다")
    a = ap.parse_args()
    if not safe_id(a.deck):
        sys.exit("잘못된 덱 id")
    if not 0.5 <= a.ratio <= 3:
        sys.exit("--ratio 는 0.5~3 사이")
    if not (DECKS / f"{a.deck}.json").is_file():
        sys.exit(f"덱 없음: {DECKS / f'{a.deck}.json'}")
    roles = [r.strip() for r in a.role.split(",") if r.strip()] if a.role else None
    only = set(s.strip() for s in a.slides.split(",") if s.strip()) if a.slides else None
    deck = load_deck(a.deck)
    print(f"[{a.deck}] ×{a.ratio:.2f}" + (f" 역할 {','.join(roles)}" if roles else "") + (" (맞춤 없음)" if a.no_fit else "") + (" (미리 보기)" if a.dry_run else ""))
    short, changed = [], 0
    for s in deck.get("slides", []):
        if only and s.get("id") not in only:
            continue
        use_fonts(s.get("fontPreset") or deck.get("fontPreset"))  # 글자 폭을 그 장의 글꼴로 잰다
        info = scale_slide(s, a.ratio, roles, fit=not a.no_fit, keep=a.keep_ratio)
        print(_fmt(s.get("id"), info))
        changed += info["applied"]
        if not info["applied"] or info["ratio"] != round(a.ratio, 2):
            short.append(s.get("id"))
    use_fonts(None)
    if short:
        print(f"비율을 못 채운 슬라이드 {len(short)}장: {', '.join(short)} — 내용을 줄이거나 장을 나눈 뒤 다시 돌린다")
    if a.dry_run or not changed:
        print("저장하지 않았다" if a.dry_run else "바꾼 슬라이드가 없다")
        return 0
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"→ {a.out} (덱은 그대로)")
        return 0
    from save_deck import direct, via_server  # 변경 원장에 Claude 로 남기고 백업·충돌 검사를 거친다
    from common import running_server
    opt = argparse.Namespace(action="save", request=a.request, label=a.label, force=a.force,
                             note=a.note or f"scale_fonts ×{a.ratio:g}" + (f" 역할 {','.join(roles)}" if roles else ""))
    run = running_server()
    rc = via_server(run["url"], a.deck, deck, opt) if run else direct(a.deck, deck, opt)
    if rc == 0:
        print(f"다음: python3 nexa.py check_layout {a.deck} 로 넘침·겹침을 확인한다")
    return rc


if __name__ == "__main__":
    sys.exit(main())
