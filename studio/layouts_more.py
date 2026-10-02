# -*- coding: utf-8 -*-
"""슬라이드 유형용 레이아웃 17종 — Genspark 전수 조사(docs/research/genspark-skills/03-slide-archetypes.md)의 새 유형을 구현.

기존 요소(rect·text·pill·ellipse·line·image)만 조합한다 — 렌더러(render.js·export_pptx.py)는 그대로라 편집기와 PPTX 가 같다.
좌표·크기 px(1280×720). 슬라이드 유형 목록(studio/slide_types.json)이 이 레이아웃에 목적별 예시 내용을 채워 쓴다.

레이아웃            쓰임
insight_panel   본문 + 결론 패널     왼쪽 글머리·표·숫자 / 오른쪽 어두운 패널(라벨·큰 수치·해석)
line_chart      선 그래프            계열 1~3개, 기준 띠·이벤트 세로선·선 끝 직접 라벨, 오른쪽 해석
number_chart    숫자 + 근거 차트     왼쪽 큰 숫자·보조 지표 / 오른쪽 막대
range_bars      범위 막대            항목별 최소~최대 막대 + 기준선(현재값)
funnel          깔때기·계층          위에서 아래로 줄어드는 단(값·비율)
tier_columns    선택지 열            2~4열(이름·값·항목), 추천 열 강조
matrix_plot     사분면               2×2 칸 + 번호 점 + 오른쪽 범례
numbered_rows   큰 번호 행           01~05 번호 + 문장 + 설명 + 메타 열
tree            트리                 루트 → 가지 2~4 → 잎(값)
people_cards    인물 카드            2~4명(사진 자리·이름·역할·한 줄)
case_story      사례 제시            왼쪽 사례 카드 / 오른쪽 질문·선택지
photo_plates    사진 도판            사진 2~4장 가로 줄 + 그림 번호 캡션
photo_statement 사진 + 한 문장       사진 전면 + 아래 어두운 띠의 문장(사진 없으면 어두운 바탕)
worked_example  단계별 풀이          왼쪽 문제·번호 단계 / 오른쪽 규칙·함정 패널
quiz            확인 문제            문제 + 보기 2×2 + 아래 메모
references      참고문헌             번호 목록 2단(저자·제목·연도·쓴 장)
qa              예상 질문            질문(크게) + 답 띠 + 근거
"""
from layouts import H, PAD, W, B, text_width  # noqa: F401
from layouts_extra import bottom_extras

RIGHT = W - PAD
DARK, ON_DARK = "on-surface", "white"  # 결론 패널(먹색 바탕 + 흰 글자)


def line(b, x1, y1, x2, y2, color, width=2, **kw):
    return b.add({"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "x": min(x1, x2), "y": min(y1, y2),
                  "w": abs(x2 - x1), "h": abs(y2 - y1), "color": color, "width": width, "head": "none", **kw})


def panel(b, x, y, w, h, f):
    """어두운 결론 패널 — f: {label, value, unit, text, items}."""
    b.rect(x, y, w, h, DARK, "r-l")
    yy = y + 28
    if f.get("label"):
        b.text(x + 28, yy, w - 56, 24, f["label"], size=15, bold=True, color=ON_DARK, lineHeight=1.4)
        yy += 36
    if f.get("value"):
        b.text(x + 28, yy, w - 56, 76, f"{f['value']}{(' ' + f['unit']) if f.get('unit') else ''}", size=56, bold=True,
               color=ON_DARK, lineHeight=1.1, font="heading")
        yy += 92
    if f.get("text"):
        b.text(x + 28, yy, w - 56, y + h - yy - 20, f["text"], size=18, color=ON_DARK, lineHeight=1.6)
    for i, it in enumerate(f.get("items", [])):
        b.text(x + 28, yy + i * 40, w - 56, 34, f"·  {it}", size=17, color=ON_DARK, lineHeight=1.5)


def _nice(v):
    import math
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if v <= m * e:
            return m * e
    return 10 * e


# ---------------------------------------------------------------- 레이아웃
def insight_panel(b, f):
    """본문 + 결론 패널 - items(글머리) 또는 rows+header(작은 표), panel {label, value, unit, text}."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    pw = f.get("panelW", 360)
    bx, bw, y = PAD, RIGHT - pw - 32 - PAD, 190
    if f.get("rows"):
        hdr, rows = f.get("header", []), f["rows"]
        cw = bw / max(1, len(hdr or rows[0]))
        if hdr:
            b.rect(bx, y, bw, 44, "surface-container", "r-s")
            for i, c in enumerate(hdr):
                b.text(bx + 16 + i * cw, y + 8, cw - 20, 30, c, size=16, bold=True, color="on-surface-variant", lineHeight=1.5)
            y += 52
        for r in rows[:7]:
            for i, c in enumerate(r):
                b.text(bx + 16 + i * cw, y, cw - 20, 34, str(c), size=17, lineHeight=1.5, bold=i == 0)
            line(b, bx, y + 42, bx + bw, y + 42, "outline-variant", 1)
            y += 52
    else:
        for i, it in enumerate(f.get("items", [])[:6]):
            b.text(bx, y, 40, 34, f"{i + 1:02d}", size=20, bold=True, color="primary", font="mono", lineHeight=1.5)
            b.text(bx + 52, y, bw - 52, 64, it, size=19, lineHeight=1.55)
            y += 72
    panel(b, RIGHT - pw, 180, pw, 400, f.get("panel", {}))
    bottom_extras(b, f, 600)
    b.foot(f.get("crumb", ""))


def line_chart(b, f):
    """선 그래프 - categories, series [{name, values, color?}] 1~3개, unit, band [lo, hi, 라벨](기준 띠),
    events [[인덱스, 라벨]](세로선), side(오른쪽 해석 글 - 있으면 그래프 폭 줄임)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    side = f.get("side")
    x0, y0, x1, y1 = PAD + 56, 190, (RIGHT - 360) if side else RIGHT - 120, 560
    cats, series = f["categories"], f["series"]
    vmax = f.get("max") or _nice(max(max(s["values"]) for s in series) * 1.05)
    vmin = f.get("min", 0)
    sx = lambda i: x0 + (x1 - x0) * (i / max(1, len(cats) - 1))  # noqa: E731
    sy = lambda v: y1 - (y1 - y0) * ((v - vmin) / (vmax - vmin or 1))  # noqa: E731
    if f.get("band"):
        lo, hi = f["band"][0], f["band"][1]
        b.rect(x0, sy(hi), x1 - x0, sy(lo) - sy(hi), "surface-container", 0)
        if len(f["band"]) > 2:
            b.text(x0 + 8, sy(hi) + 4, 300, 24, f["band"][2], size=15, color="on-surface-variant", lineHeight=1.4)
    for k in range(5):
        v = vmin + (vmax - vmin) * k / 4
        line(b, x0, sy(v), x1, sy(v), "outline-variant", 1)
        b.text(PAD, sy(v) - 12, 48, 24, f"{v:g}", size=15, color="on-surface-variant", align="right", lineHeight=1.4)
    step = max(1, -(-len(cats) // 8))
    for i, c in enumerate(cats):
        if i % step == 0 or i == len(cats) - 1:
            b.text(sx(i) - 40, y1 + 10, 80, 24, c, size=15, color="on-surface-variant", align="center", lineHeight=1.4)
    for i, lab in f.get("events", []):
        line(b, sx(i), y0, sx(i), y1, "on-surface-variant", 1.5, dash="dash")
        b.text(sx(i) + 6, y0, 200, 24, lab, size=15, bold=True, color="on-surface-variant", lineHeight=1.4)
    tones = ["primary", "s3", "s5"]
    for k, s in enumerate(series[:3]):
        col = s.get("color", tones[k])
        vs = s["values"]
        for i in range(len(vs) - 1):
            line(b, sx(i), sy(vs[i]), sx(i + 1), sy(vs[i + 1]), col, 4 if k == 0 else 3)
        b.ellipse(sx(len(vs) - 1) - 7, sy(vs[-1]) - 7, 14, col)
        b.text(sx(len(vs) - 1) + 12, sy(vs[-1]) - 14, 110, 28, f"{s['name']} {vs[-1]:g}{f.get('unit', '')}", size=16, bold=True,
               color=col, lineHeight=1.4)
    if side:
        panel(b, RIGHT - 300, 180, 300, 400, side if isinstance(side, dict) else {"text": side})
    bottom_extras(b, f, 610)
    b.foot(f.get("crumb", ""))


def number_chart(b, f):
    """숫자 + 근거 차트 - value, unit, label, metrics [[라벨, 값]], categories, values(막대, 마지막 강조)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    b.text(PAD, 200, 420, 130, f["value"], size=110, bold=True, color="primary", lineHeight=1.05, font="heading")
    if f.get("unit"):
        b.text(PAD + text_width(f["value"], 110, True) + 12, 270, 160, 50, f["unit"], size=32, bold=True, color="primary", lineHeight=1.2)
    b.text(PAD, 340, 420, 60, f.get("label", ""), size=20, lineHeight=1.5)
    y = 420
    for lab, v in f.get("metrics", [])[:3]:
        line(b, PAD, y, PAD + 400, y, "outline-variant", 1)
        b.text(PAD, y + 10, 240, 28, lab, size=16, color="on-surface-variant", lineHeight=1.5)
        b.text(PAD + 240, y + 6, 160, 32, v, size=20, bold=True, align="right", lineHeight=1.5)
        y += 52
    cats, vals = f.get("categories", []), f.get("values", [])
    if vals:
        x0, x1, yt, yb = 540, RIGHT, 200, 540
        vmax = _nice(max(vals) * 1.05)
        bw = (x1 - x0) / len(vals)
        for i, (c, v) in enumerate(zip(cats, vals)):
            h = (yb - yt) * v / vmax
            last = i == len(vals) - 1
            b.rect(x0 + i * bw + bw * 0.18, yb - h, bw * 0.64, h, "primary" if last else "surface-container-high", "r-s")
            b.text(x0 + i * bw, yb - h - 30, bw, 26, f"{v:g}", size=15, bold=last, align="center", lineHeight=1.4,
                   color="primary" if last else "on-surface-variant")
            b.text(x0 + i * bw, yb + 8, bw, 24, c, size=15, align="center", color="on-surface-variant", lineHeight=1.4)
        line(b, x0, yb, x1, yb, "on-surface-variant", 1.5)
    bottom_extras(b, f, 600)
    b.foot(f.get("crumb", ""))


def range_bars(b, f):
    """범위 막대 - rows [{label, lo, hi, mid?}], ref [값, 라벨](세로 기준선), unit, min/max(축)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    rows = f["rows"][:7]
    lo = f.get("min", min(r["lo"] for r in rows))
    hi = f.get("max", max(r["hi"] for r in rows))
    lw, x0, x1 = 260, PAD + 280, RIGHT - 110  # 오른쪽 끝 숫자 자리
    sx = lambda v: x0 + (x1 - x0) * (v - lo) / ((hi - lo) or 1)  # noqa: E731
    rh = min(64, 380 / len(rows))
    y = 210
    for r in rows:
        b.text(PAD, y + rh / 2 - 15, lw, 30, r["label"], size=18, bold=True, lineHeight=1.5)
        b.rect(sx(r["lo"]), y + rh / 2 - 12, sx(r["hi"]) - sx(r["lo"]), 24, "primary-container", "r-s")
        if r.get("mid") is not None:
            b.rect(sx(r["mid"]) - 2, y + rh / 2 - 16, 4, 32, "primary", 0)
        b.text(sx(r["lo"]) - 84, y + rh / 2 - 12, 78, 24, f"{r['lo']:g}{f.get('unit', '')}", size=15, align="right", color="on-surface-variant", lineHeight=1.4)
        b.text(sx(r["hi"]) + 6, y + rh / 2 - 12, 90, 24, f"{r['hi']:g}{f.get('unit', '')}", size=15, color="on-surface-variant", lineHeight=1.4)
        y += rh
    if f.get("ref"):
        v, lab = f["ref"][0], f["ref"][1] if len(f["ref"]) > 1 else ""
        line(b, sx(v), 196, sx(v), y + 6, "bad", 2, dash="dash")
        b.pill(sx(v) - 60, y + 14, f"{lab} {v:g}{f.get('unit', '')}", "bad-container", "bad", size=15, h=28)
    bottom_extras(b, f, 620)
    b.foot(f.get("crumb", ""))


def funnel(b, f):
    """깔때기·계층 - stages [{label, value, note?}] 위→아래로 줄어드는 단(3~5), side(오른쪽 해석)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    st = f["stages"][:5]
    full, cx, y, h = 620, PAD + 340, 196, min(76, 380 / len(st))
    tones = ["primary", "s3", "s5", "s2", "s6"]
    for i, s in enumerate(st):
        w = full * (1 - i * 0.16)
        b.rect(cx - w / 2, y, w, h - 10, tones[i % 5], "r-s", text=f"{s['label']}   {s['value']}", size=20, bold=True,
               color="white", align="center", valign="middle")
        if s.get("note"):
            b.text(cx + full / 2 + 24, y + (h - 10) / 2 - 14, 300, 28, s["note"], size=16, color="on-surface-variant", lineHeight=1.5)
        y += h
    if f.get("side"):
        panel(b, RIGHT - 300, 196, 300, 380, f["side"] if isinstance(f["side"], dict) else {"text": f["side"]})
    bottom_extras(b, f, 610)
    b.foot(f.get("crumb", ""))


def tier_columns(b, f):
    """선택지 열 - columns [{name, value, sub, items, pick}] 2~4열, pick=true 열 강조(추천)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    cols = f["columns"][:4]
    gap = 20
    cw = (RIGHT - PAD - gap * (len(cols) - 1)) / len(cols)
    for i, c in enumerate(cols):
        x, pick = PAD + i * (cw + gap), c.get("pick")
        b.rect(x, 190, cw, 400, "primary-container" if pick else "surface-container", "r-l",
               stroke="primary" if pick else None, strokeWidth=3 if pick else None)
        if pick:
            b.pill(x + 20, 172, f.get("pickLabel", "추천"), "primary", "on-primary", size=15, h=30)
        b.text(x + 24, 212, cw - 48, 30, c["name"], size=20, bold=True, lineHeight=1.5)
        b.text(x + 24, 252, cw - 48, 64, c.get("value", ""), size=40, bold=True, color="primary" if pick else "on-surface",
               lineHeight=1.2, font="heading")
        if c.get("sub"):
            b.text(x + 24, 316, cw - 48, 26, c["sub"], size=15, color="on-surface-variant", lineHeight=1.5)
        for k, it in enumerate(c.get("items", [])[:5]):
            b.text(x + 24, 356 + k * 44, cw - 48, 40, f"✓  {it}", size=16, lineHeight=1.5)
    bottom_extras(b, f, 606)
    b.foot(f.get("crumb", ""))


def matrix_plot(b, f):
    """사분면 - xLabel, yLabel, quads [좌상, 우상, 좌하, 우하](칸 이름), points [{n, x 0~1, y 0~1, label}], 오른쪽 범례."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    x0, y0, s = PAD + 40, 180, 420
    q = f.get("quads", ["", "", "", ""])
    fills = ["surface-container", "primary-container", "surface-dim", "surface-container"]
    for k in range(4):
        cx, cy = x0 + (k % 2) * s / 2, y0 + (k // 2) * s / 2
        b.rect(cx, cy, s / 2 - 4, s / 2 - 4, fills[k], "r-s")
        if q[k]:
            b.text(cx + 12, cy + 10, s / 2 - 28, 26, q[k], size=15, bold=True, color="on-surface-variant", lineHeight=1.4)
    b.text(x0, y0 + s + 8, s, 26, f"{f.get('xLabel', '')} →", size=16, bold=True, align="center", color="on-surface-variant", lineHeight=1.5)
    b.text(PAD - 30, y0 + s / 2 - 13, 60, 26, "↑", size=18, bold=True, color="on-surface-variant", align="center", lineHeight=1.4)
    b.text(PAD - 20, y0 - 30, 300, 26, f.get("yLabel", ""), size=16, bold=True, color="on-surface-variant", lineHeight=1.5)
    lx, ly = x0 + s + 64, 190
    for p in f.get("points", [])[:8]:
        px, py = x0 + p["x"] * (s - 4), y0 + (1 - p["y"]) * (s - 4)
        b.ellipse(px - 16, py - 16, 32, "primary", text=str(p["n"]), size=15, bold=True, color="on-primary", align="center", valign="middle")
        b.ellipse(lx, ly, 30, "primary", text=str(p["n"]), size=15, bold=True, color="on-primary", align="center", valign="middle")
        b.text(lx + 44, ly, RIGHT - lx - 44, 30, p["label"], size=17, lineHeight=1.6)
        ly += 46
    bottom_extras(b, f, 640)
    b.foot(f.get("crumb", ""))


def numbered_rows(b, f):
    """큰 번호 행 - rows [{title, body, meta}] 3~5행(01~05 큰 번호 + 문장 + 설명 + 오른쪽 메타)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    rows = f["rows"][:5]
    rh = min(96, 420 / len(rows))
    y = 184
    for i, r in enumerate(rows):
        b.text(PAD, y, 100, rh - 12, f"{i + 1:02d}", size=48, bold=True, color="primary", lineHeight=1.1, font="heading")
        b.text(PAD + 110, y + 2, 780, 32, r["title"], size=21, bold=True, lineHeight=1.45)
        if r.get("body"):
            b.text(PAD + 110, y + 38, 780, rh - 46, r["body"], size=16, color="on-surface-variant", lineHeight=1.5)
        if r.get("meta"):
            b.text(RIGHT - 240, y + 4, 240, 30, r["meta"], size=16, bold=True, align="right", color="on-surface-variant", lineHeight=1.5)
        line(b, PAD, y + rh - 8, RIGHT, y + rh - 8, "outline-variant", 1)
        y += rh
    bottom_extras(b, f, 620)
    b.foot(f.get("crumb", ""))


def tree(b, f):
    """트리 - root {label, value}, branches [{label, value, leaves [[라벨, 값]…]}] 2~4가지."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    r = f["root"]
    br = f["branches"][:4]
    rx, ry, rw, rh = PAD, 330, 220, 96
    b.rect(rx, ry, rw, rh, "primary", "r-m", text=f"{r['label']}\n{r.get('value', '')}", size=20, bold=True, color="on-primary",
           align="center", valign="middle", lineHeight=1.4)
    bx, bw, bh = rx + rw + 90, 240, 70
    gap = (420 - len(br) * bh) / max(1, len(br) - 1) if len(br) > 1 else 0
    jx = rx + rw + 45
    ys = [184 + i * (bh + gap) for i in range(len(br))]
    line(b, rx + rw, ry + rh / 2, jx, ry + rh / 2, "on-surface-variant", 2)
    line(b, jx, ys[0] + bh / 2, jx, ys[-1] + bh / 2, "on-surface-variant", 2)
    for y, x in zip(ys, br):
        line(b, jx, y + bh / 2, bx, y + bh / 2, "on-surface-variant", 2)
        b.rect(bx, y, bw, bh, "primary-container", "r-m", text=f"{x['label']}  {x.get('value', '')}", size=18, bold=True,
               color="on-primary-container", align="center", valign="middle")
        lx = bx + bw + 60
        leaves = x.get("leaves", [])[:3]
        if leaves:
            line(b, bx + bw, y + bh / 2, lx - 10, y + bh / 2, "outline-variant", 1.5)
        for k, (lab, v) in enumerate(leaves):
            b.text(lx + k * 190, y + 4, 180, 62, f"{lab}\n**{v}**", size=15, lineHeight=1.4, fill="surface-container", radius="r-s",
                   pad=[6, 10, 6, 10], valign="middle")
    bottom_extras(b, f, 620)
    b.foot(f.get("crumb", ""))


def _photo(b, x, y, w, h, src, hint, radius="r-m"):
    if src:
        b.image(x, y, w, h, src)
    else:
        b.rect(x, y, w, h, "surface-container-high", radius, text=hint, size=15, color="on-surface-variant", align="center", valign="middle")


def people_cards(b, f):
    """인물 카드 - people [{name, role, line, img}] 2~4명(위 사진 자리 · 이름 · 역할 · 한 줄)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    ps = f["people"][:4]
    gap = 24
    cw = (RIGHT - PAD - gap * (len(ps) - 1)) / len(ps)
    for i, p in enumerate(ps):
        x = PAD + i * (cw + gap)
        b.rect(x, 186, cw, 420, "surface-container", "r-l")
        _photo(b, x + 20, 206, cw - 40, 190, p.get("img"), "인물 사진\n세로 3:4 · 얼굴 위쪽")
        b.text(x + 20, 412, cw - 40, 32, p["name"], size=21, bold=True, lineHeight=1.45)
        b.text(x + 20, 448, cw - 40, 26, p.get("role", ""), size=16, color="primary", bold=True, lineHeight=1.5)
        b.text(x + 20, 484, cw - 40, 110, p.get("line", ""), size=16, color="on-surface-variant", lineHeight=1.55)
    bottom_extras(b, f, 620)
    b.foot(f.get("crumb", ""))


def case_story(b, f):
    """사례 제시 - case {label, title, body, meta}, questions [질문…] 또는 options [{key, text}], verdict(아래 판정 띠)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    c = f["case"]
    b.rect(PAD, 184, 680, 410, "surface-container", "r-l")
    b.pill(PAD + 24, 204, c.get("label", "사례"), "primary", "on-primary", size=15, h=30)
    if c.get("meta"):
        b.text(PAD + 24 + 160, 206, 470, 26, c["meta"], size=15, color="on-surface-variant", lineHeight=1.5, align="right")
    b.text(PAD + 24, 252, 630, 40, c["title"], size=24, bold=True, lineHeight=1.4)
    b.text(PAD + 24, 302, 630, 270, c.get("body", ""), size=17, lineHeight=1.65)
    x, w, y = PAD + 712, RIGHT - PAD - 712, 184
    if f.get("options"):
        for o in f["options"][:4]:
            b.rect(x, y, w, 88, "white", "r-m", stroke="outline-variant", strokeWidth=1.5)
            b.ellipse(x + 16, y + 26, 36, "primary-container", text=o["key"], size=17, bold=True, color="on-primary-container",
                      align="center", valign="middle")
            b.text(x + 66, y + 12, w - 82, 64, o["text"], size=16, lineHeight=1.5, valign="middle")
            y += 104
    else:
        b.text(x, y, w, 28, f.get("qLabel", "생각해 볼 질문"), size=17, bold=True, color="primary", lineHeight=1.5)
        y += 40
        for k, q in enumerate(f.get("questions", [])[:4]):
            b.text(x, y, w, 80, f"Q{k + 1}.  {q}", size=17, lineHeight=1.55)
            y += 92
    if f.get("verdict"):
        b.text(PAD, 608, RIGHT - PAD, 44, f["verdict"], size=18, bold=True, fill=DARK, color=ON_DARK, radius="r-m",
               pad=[8, 20, 8, 20], valign="middle")
    b.foot(f.get("crumb", ""))


def photo_plates(b, f):
    """사진 도판 - plates [{img, caption}] 2~4장 가로 줄(그림 번호 FIG.01 캡션), body(위 설명 한 줄)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    ps = f["plates"][:4]
    gap = 20
    pw = (RIGHT - PAD - gap * (len(ps) - 1)) / len(ps)
    ph = min(330, pw * 0.75)
    y = 200
    for i, p in enumerate(ps):
        x = PAD + i * (pw + gap)
        _photo(b, x, y, pw, ph, p.get("img"), "사진 자리\n같은 톤·밝기로", "r-s")
        b.text(x, y + ph + 12, pw, 24, f"FIG. {i + 1:02d}", size=15, bold=True, color="primary", font="mono", lineHeight=1.4)
        b.text(x, y + ph + 40, pw, 60, p.get("caption", ""), size=16, color="on-surface-variant", lineHeight=1.5)
    bottom_extras(b, f, 620)
    b.foot(f.get("crumb", ""))


def photo_statement(b, f):
    """사진 + 한 문장 - img(전면, 없으면 어두운 바탕), text(문장), kicker, sub. 글자는 아래 어두운 띠 안(사진 위 안전 영역)."""
    if f.get("img"):
        b.image(0, 0, W, H, f["img"])
    else:
        b.rect(0, 0, W, H, DARK, 0)
        b.text(W - 420, 60, 360, 60, f.get("imgHint", "전면 사진 자리 — 피사체는 위쪽,\n아래 1/3 은 어둡고 비어 있게"), size=15,
               color="on-surface-variant", align="right", lineHeight=1.5)
    b.rect(0, 430, W, 290, DARK, 0)
    if f.get("kicker"):
        b.pill(PAD + 40, 462, f["kicker"], "primary", "on-primary", size=15, h=30)
    b.text(PAD + 40, 506, W - 2 * PAD - 80, 120, f["text"], size=f.get("size", 40), bold=True, color=ON_DARK, lineHeight=1.35,
           font="heading", role="title")
    if f.get("sub"):
        b.text(PAD + 40, 634, W - 2 * PAD - 80, 30, f["sub"], size=17, color=ON_DARK, lineHeight=1.5)


def worked_example(b, f):
    """단계별 풀이 - problem(문제), steps [단계…](번호 붙음 · `코드`·수식 가능), rules {label, items}(오른쪽 규칙·함정 패널)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    lw = 760
    b.text(PAD, 184, lw, 70, f"**문제**  {f['problem']}", size=18, lineHeight=1.6, fill="surface-container", radius="r-m",
           pad=[12, 18, 12, 18], valign="middle")
    y = 276
    for i, s in enumerate(f.get("steps", [])[:5]):
        b.ellipse(PAD, y + 2, 34, "primary", text=str(i + 1), size=16, bold=True, color="on-primary", align="center", valign="middle")
        b.text(PAD + 50, y, lw - 50, 60, s, size=18, lineHeight=1.55)
        y += 64
    panel(b, PAD + lw + 32, 184, RIGHT - PAD - lw - 32, 420, f.get("rules", {}))
    bottom_extras(b, f, 620)
    b.foot(f.get("crumb", ""))


def quiz(b, f):
    """확인 문제 - question, choices [보기 4개](A~D, 2×2), answer(정답 키 — 화면에 그리지 않고 노트로), note(아래 메모)."""
    b.head(f.get("title", "확인 문제"), f.get("sub"), f.get("kick"))
    b.text(PAD, 180, RIGHT - PAD, 90, f["question"], size=26, bold=True, lineHeight=1.45)
    ch = f.get("choices", [])[:4]
    cw, chh = (RIGHT - PAD - 24) / 2, 120
    for i, c in enumerate(ch):
        x, y = PAD + (i % 2) * (cw + 24), 290 + (i // 2) * (chh + 20)
        b.rect(x, y, cw, chh, "surface-container", "r-l")
        b.ellipse(x + 20, y + chh / 2 - 22, 44, "primary", text="ABCD"[i], size=20, bold=True, color="on-primary", align="center", valign="middle")
        b.text(x + 84, y + 14, cw - 104, chh - 28, c, size=19, lineHeight=1.5, valign="middle")
    if f.get("note"):
        b.text(PAD, 584, RIGHT - PAD, 40, f["note"], size=16, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def references(b, f):
    """참고문헌 - refs [{who, title, year, used}] 2단 번호 목록(최대 10), note(아래 한 줄)."""
    b.head(f.get("title", "참고문헌"), f.get("sub"), f.get("kick"))
    refs = f["refs"][:10]
    cw = (RIGHT - PAD - 40) / 2
    for i, r in enumerate(refs):
        x, y = PAD + (i // 5) * (cw + 40), 186 + (i % 5) * 80
        b.text(x, y, 44, 30, f"{i + 1:02d}", size=18, bold=True, color="primary", font="mono", lineHeight=1.5)
        b.text(x + 50, y, cw - 50, 50, f"**{r['who']}** ({r.get('year', '')}). {r['title']}", size=16, lineHeight=1.5)
        if r.get("used"):
            b.text(x + 50, y + 50, cw - 50, 22, f"쓴 장: {r['used']}", size=15, color="on-surface-variant", lineHeight=1.4)
    if f.get("note"):
        b.text(PAD, 600, RIGHT - PAD, 30, f["note"], size=15, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def qa(b, f):
    """예상 질문 - question(크게), answer(짙은 띠 한두 문장), evidence [근거…] 또는 metrics [[라벨, 값]]."""
    b.head(f.get("title", "예상 질문"), f.get("sub"), f.get("kick") or "neutral:부록 · Q&A")
    b.text(PAD, 176, RIGHT - PAD, 96, f"“{f['question']}”", size=30, bold=True, lineHeight=1.4, font="heading")
    b.text(PAD, 284, RIGHT - PAD, 76, f["answer"], size=20, bold=True, fill=DARK, color=ON_DARK, radius="r-m", pad=[12, 22, 12, 22],
           lineHeight=1.5, valign="middle")
    y = 384
    for i, e in enumerate(f.get("evidence", [])[:4]):
        b.text(PAD, y, RIGHT - PAD, 44, f"근거 {i + 1}.  {e}", size=17, lineHeight=1.55)
        y += 52
    mets = f.get("metrics", [])[:4]
    if mets:
        mw = (RIGHT - PAD - 16 * (len(mets) - 1)) / len(mets)
        for i, (lab, v) in enumerate(mets):
            x = PAD + i * (mw + 16)
            b.rect(x, y + 6, mw, 110, "surface-container", "r-m")
            b.text(x + 18, y + 18, mw - 36, 24, lab, size=15, color="on-surface-variant", lineHeight=1.4)
            b.text(x + 18, y + 48, mw - 36, 56, v, size=34, bold=True, color="primary", lineHeight=1.2)
    b.foot(f.get("crumb", ""))


MORE = {
    "insight_panel": ("본문 + 결론 패널", insight_panel), "line_chart": ("선 그래프", line_chart), "number_chart": ("숫자 + 근거 차트", number_chart),
    "range_bars": ("범위 막대", range_bars), "funnel": ("깔때기·계층", funnel), "tier_columns": ("선택지 열(추천 강조)", tier_columns),
    "matrix_plot": ("사분면", matrix_plot), "numbered_rows": ("큰 번호 행", numbered_rows), "tree": ("트리", tree),
    "people_cards": ("인물 카드", people_cards), "case_story": ("사례 제시", case_story), "photo_plates": ("사진 도판", photo_plates),
    "photo_statement": ("사진 + 한 문장", photo_statement), "worked_example": ("단계별 풀이", worked_example), "quiz": ("확인 문제", quiz),
    "references": ("참고문헌", references), "qa": ("예상 질문", qa),
}

MORE_SAMPLES = {
    "insight_panel": {"title": "결론형 제목 — 근거와 해석을 한 장에", "items": ["근거 1 — 숫자와 출처", "근거 2 — 비교 기준", "근거 3 — 반례와 한계"],
                      "panel": {"label": "핵심", "value": "+18", "unit": "%", "text": "근거를 종합한 해석 한두 문장"}, "crumb": ""},
    "line_chart": {"title": "추이가 말하는 것", "categories": ["1월", "2월", "3월", "4월", "5월", "6월"],
                   "series": [{"name": "실적", "values": [40, 44, 47, 55, 61, 66]}, {"name": "계획", "values": [42, 45, 48, 51, 54, 57]}],
                   "band": [45, 55, "목표 범위"], "events": [[3, "개편"]], "crumb": ""},
    "number_chart": {"title": "숫자 하나가 결론", "value": "1.8", "unit": "배", "label": "무엇이 몇 배 늘었나",
                     "metrics": [["기준", "100"], ["현재", "180"]], "categories": ["1분기", "2분기", "3분기", "4분기"], "values": [100, 120, 150, 180], "crumb": ""},
    "range_bars": {"title": "범위로 보는 추정", "rows": [{"label": "방법 A", "lo": 80, "hi": 120, "mid": 100}, {"label": "방법 B", "lo": 90, "hi": 140, "mid": 110},
                                                  {"label": "방법 C", "lo": 70, "hi": 105, "mid": 88}], "ref": [100, "현재"], "unit": "억", "crumb": ""},
    "funnel": {"title": "단계별로 줄어드는 수", "stages": [{"label": "방문", "value": "10,000"}, {"label": "가입", "value": "2,400", "note": "24%"},
                                                    {"label": "사용", "value": "1,100", "note": "46%"}, {"label": "결제", "value": "320", "note": "29%"}], "crumb": ""},
    "tier_columns": {"title": "선택지 비교", "columns": [{"name": "A안", "value": "3개월", "items": ["빠름", "범위 작음"]},
                                                      {"name": "B안", "value": "5개월", "items": ["균형", "위험 낮음"], "pick": True},
                                                      {"name": "C안", "value": "9개월", "items": ["전면 개편", "비용 큼"]}], "crumb": ""},
    "matrix_plot": {"title": "어디에 집중할까", "xLabel": "실행 쉬움", "yLabel": "효과 큼", "quads": ["큰 과제", "먼저 할 것", "미룰 것", "빠른 개선"],
                    "points": [{"n": 1, "x": 0.8, "y": 0.8, "label": "항목 1"}, {"n": 2, "x": 0.3, "y": 0.7, "label": "항목 2"},
                               {"n": 3, "x": 0.7, "y": 0.3, "label": "항목 3"}], "crumb": ""},
    "numbered_rows": {"title": "세 가지", "rows": [{"title": "첫째 문장", "body": "설명", "meta": "담당 · 기한"},
                                                 {"title": "둘째 문장", "body": "설명", "meta": "담당 · 기한"},
                                                 {"title": "셋째 문장", "body": "설명", "meta": "담당 · 기한"}], "crumb": ""},
    "tree": {"title": "지표를 나눠 보면", "root": {"label": "매출", "value": "100"},
             "branches": [{"label": "고객 수", "value": "40", "leaves": [["신규", "15"], ["기존", "25"]]},
                          {"label": "객단가", "value": "2.5", "leaves": [["가격", "2.0"], ["수량", "1.25"]]}], "crumb": ""},
    "people_cards": {"title": "함께하는 사람", "people": [{"name": "이름", "role": "역할", "line": "한 줄 소개"}, {"name": "이름", "role": "역할", "line": "한 줄 소개"},
                                                       {"name": "이름", "role": "역할", "line": "한 줄 소개"}], "crumb": ""},
    "case_story": {"title": "사례로 생각해 보기", "case": {"label": "사례", "title": "무슨 일이 있었나", "body": "상황 설명 서너 줄", "meta": "언제 · 어디서"},
                   "questions": ["무엇이 문제였나", "어떻게 했어야 했나"], "crumb": ""},
    "photo_plates": {"title": "현장 기록", "plates": [{"caption": "설명"}, {"caption": "설명"}, {"caption": "설명"}], "crumb": ""},
    "photo_statement": {"text": "사진 위에 남길 한 문장", "kicker": "장면", "sub": "보조 설명"},
    "worked_example": {"title": "단계별로 풀기", "problem": "문제 한 문장", "steps": ["첫 단계", "둘째 단계", "셋째 단계 — 답"],
                       "rules": {"label": "기억할 규칙", "items": ["규칙 1", "흔한 실수"]}, "crumb": ""},
    "quiz": {"title": "확인 문제", "question": "질문 한 문장?", "choices": ["보기 1", "보기 2", "보기 3", "보기 4"], "answer": "B", "crumb": ""},
    "references": {"title": "참고문헌", "refs": [{"who": "저자", "title": "제목", "year": "2026", "used": "3·5장"}, {"who": "기관", "title": "보고서", "year": "2025"}], "crumb": ""},
    "qa": {"question": "예상 질문?", "answer": "한두 문장 답", "evidence": ["근거 1", "근거 2"], "crumb": ""},
}
