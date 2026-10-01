# -*- coding: utf-8 -*-
"""레이아웃 빌더 — 장 내용(레이아웃 이름 + 필드) → 슬라이드 요소 목록.

디자인 기준(concept v2 Material)의 레이아웃 13종을 같은 좌표로 옮겼다.
브랜드(로고·워드마크)·부 이름·표지 배지는 작업 공간 nexa-slide.json 에서 읽는다(없으면 중립 기본값).
좌표·크기는 px(1280×720), 글자 크기 size 도 px(PPT pt = px × 0.75).
"""
import copy
import struct

from common import ASSET_ROOT, BRAND, CONFIG, fit_size, text_width

W, H, PAD = 1280, 720, 64


def _png_ratio(src, default):
    """PNG 머리(IHDR)에서 가로/세로 비율 — 파일이 없거나 PNG 가 아니면 기본값."""
    try:
        with open(ASSET_ROOT / src, "rb") as fh:
            w, h = struct.unpack(">II", fh.read(24)[16:24])
        return w / h
    except (OSError, struct.error, ZeroDivisionError):
        return default


LOGO = BRAND.get("logo") or "assets/brand/logo.png"            # 머리 오른쪽·표지 로고
WORDMARK = BRAND.get("wordmark") or "assets/brand/wordmark.png"  # 바닥 워드마크
LOGO_RATIO = _png_ratio(LOGO, 765 / 237)
WM_RATIO = _png_ratio(WORDMARK, 117 / 13)

SUP = "¹²³⁴⁵⁶⁷⁸⁹"  # 근거 각주 번호 — 본문에는 [[theory|¹]] 로 표식을 단다

PART_LABEL = {"day1": "Part 1", "day2": "Part 2", "day3": "Part 3", "apx": "Appendix", **CONFIG.get("partLabels", {})}
COVER_BADGE = CONFIG.get("coverBadge", "Presentation")


class B:
    """요소 목록을 쌓는 도우미. id 는 슬라이드 안에서 e01, e02 … 순서."""

    def __init__(self, part="day1"):
        self.els = []
        self.part = part
        self.dc, self.dcc, self.dco = part, f"{part}-container", f"on-{part}-container"
        self.level = None  # "req"(필수) | "adv"(심화) — 머리의 부 칩 옆에 표시
        self.source = None  # 근거 목록(각주 번호 순) — 화면에는 그리지 않는다

    def add(self, el):
        el = {"id": f"e{len(self.els) + 1:02d}", **el}
        # 템플릿 최소 글자 크기(sizes.minPx) — 역할별, 이미 크면 그대로
        for k in ("size", "subSize"):
            if isinstance(el.get(k), (int, float)):
                el[k] = fit_size(el[k], el.get("role"))
        for k in ("x", "y", "w", "h"):
            if k in el:
                el[k] = round(el[k])
        self.els.append(el)
        return el

    # 기본 도형
    def rect(self, x, y, w, h, fill, radius=0, **kw):
        return self.add({"type": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "radius": radius, **kw})

    def ellipse(self, x, y, d, fill, **kw):
        return self.add({"type": "ellipse", "x": x, "y": y, "w": d, "h": d, "fill": fill, **kw})

    def text(self, x, y, w, h, text, size=20, color="on-surface", **kw):
        return self.add({"type": "text", "x": x, "y": y, "w": w, "h": h, "text": text, "size": size, "color": color, **kw})

    def pill(self, x, y, text, fill, color, size=14, h=30, padx=14, bold=True, w=None, **kw):
        size = fit_size(size, kw.get("role"))  # 폭을 재기 전에 — 칩 폭이 커진 글자에 맞게
        if w is None:
            w = text_width(text, size, bold, kw.get("font") == "mono") + padx * 2 + 2
        return self.add({"type": "pill", "x": x, "y": y, "w": w, "h": h, "text": text, "fill": fill,
                         "color": color, "size": size, "bold": bold, **kw})

    def image(self, x, y, w, h, src, **kw):
        return self.add({"type": "image", "x": x, "y": y, "w": w, "h": h, "src": src, **kw})

    def arrow(self, x1, y1, x2, y2, color, width=2, head="end", **kw):
        return self.add({"type": "arrow", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "x": min(x1, x2), "y": min(y1, y2),
                         "w": abs(x2 - x1), "h": abs(y2 - y1), "color": color, "width": width, "head": head, **kw})

    # 칩 묶음
    def tag(self, x, y, kind, sm=True):
        h, size, padx = (26, 13, 12) if sm else (30, 14, 14)
        spec = {
            "req": ("primary", "on-primary", "필수", True, None),
            "adv": (None, "on-surface-variant", "심화", False, "outline-variant"),
            "theory": ("theory-container", "theory", "이론", True, None),
            "lab": ("lab-container", "lab", "실습", True, None),
        }
        if kind in spec:
            fill, col, t, bold, stroke = spec[kind]
        else:  # "neutral:글자"
            fill, col, t, bold, stroke = "surface-container", "on-surface-variant", kind.split(":", 1)[-1], True, None
        kw = {"stroke": stroke, "strokeWidth": 1.5} if stroke else {}
        return self.pill(x, y, t, fill, col, size=size, h=h, padx=padx, bold=bold, **kw)

    def tags(self, x, y, kinds, sm=True, gap=8):
        for k in kinds:
            x += self.tag(x, y, k, sm)["w"] + gap
        return x

    def day_pill(self, x, y, label=None):
        return self.pill(x, y, label or PART_LABEL.get(self.part, self.part), self.dcc, self.dco)

    def logo(self, x=None, y=36, h=34):
        w = h * LOGO_RATIO
        return self.image(W - 48 - w if x is None else x, y, w, h, LOGO, locked=True)

    # 공통 머리·바닥
    def head(self, title, sub=None, kick=None):
        """kick: None(부 칩) | 'neutral:전체' 같은 칩 목록"""
        if kick is None:
            p = self.day_pill(PAD, 36)
            if self.level:
                self.tag(PAD + p["w"] + 8, 36, self.level, sm=False)
        else:
            self.tags(PAD, 36, kick if isinstance(kick, list) else [kick], sm=False)
        self.text(PAD, 80, W - PAD - 240, 44, title, size=34, bold=True, lineHeight=1.25, role="title")
        if sub:
            self.text(PAD, 128, W - PAD - 240, 28, sub, size=18, color="on-surface-variant", lineHeight=1.4, role="subtitle")
        self.logo()

    def foot(self, crumb):
        # 근거(source): 본문에는 각주 표식 [[theory|¹]], 슬라이드 맨 아래 띠에 작은 글씨로 번호별 한 줄씩 쌓는다
        # (2026-09-30 요청 r20260930235223630 — 요청 #15의 "표식만"에서 바꿈). 원문 인용은 발표자 노트의 "원문 (각주 순서)".
        # 각주가 있으면 위치(crumb)는 오른쪽(워드마크 앞)으로 옮기고, 왼쪽 아래 띠(본문 영역 656 아래)를 각주가 쓴다.
        wh = 12
        wm_x = W - 112 - wh * WM_RATIO
        if self.source:
            fs, lh = 10, 1.3
            lines = [f"{SUP[i] if i < len(SUP) else i + 1} {s}" for i, s in enumerate(self.source)]
            h = round(len(lines) * fs * lh) + 2
            self.text(PAD, 713 - h, wm_x - 340 - PAD, h, "\n".join(lines), size=fs, color="on-surface-variant",
                      lineHeight=lh, valign="bottom", role="footnotes")
            self.text(wm_x - 330, 675, 314, 20, crumb, size=13, color="on-surface-variant", lineHeight=1.4,
                      align="right", role="crumb")
        else:
            self.text(PAD, 675, 800, 20, crumb, size=13, color="on-surface-variant", lineHeight=1.4, role="crumb")
        self.image(W - 112 - wh * WM_RATIO, H - 30 - wh, wh * WM_RATIO, wh, WORDMARK, locked=True)
        self.pill(W - 48 - 44, H - 22 - 28, "{page}", "surface-container", "on-surface-variant", size=13, h=28, bold=False, w=44, role="page")


# ---------------------------------------------------------------- 레이아웃 13종
def cover(b, f):
    b.rect(40, 40, 760, 640, "primary-container", "r-l")
    b.pill(88, 92, f.get("badge", COVER_BADGE), "white", "primary")
    b.text(88, 170, 680, 150, f["title"], size=60, bold=True, lineHeight=1.15, color="on-primary-container", role="title")
    sub = f.get("subtitle", "")
    ss = f.get("subtitleSize", 22)
    b.text(88, 352, 660, round((sub.count("\n") + 1) * ss * 1.6), sub, size=ss, lineHeight=1.6, color="on-primary-container")
    x = 88
    for part, label in f.get("days", []):
        x += b.pill(x, 560, label, f"{part}-container", f"on-{part}-container")["w"] + 8
    b.image(864, 96, 88 * LOGO_RATIO, 88, LOGO, locked=True)
    b.text(864, 470, 380, 95, f.get("meta", ""), size=16, lineHeight=1.9, color="on-surface-variant")


def toc(b, f):
    b.head(f.get("title", "목차"), f.get("sub"), f.get("kick", ["neutral:전체"]))
    for i, g in enumerate(f["groups"]):
        x, y = 64 + i * 392, 176
        part = g["part"]
        b.rect(x, y, 368, 470, "surface-container", "r-m")
        b.pill(x + 20, y + 18, g["label"], f"{part}-container", f"on-{part}-container")
        for j, it in enumerate(g["items"]):
            code, name = it[0], it[1]
            ip = it[2] if len(it) > 2 else part
            ry = y + 60 + j * 38
            cur = code == f.get("current")
            if cur:
                b.rect(x + 12, ry + 1, 344, 36, "white", "r-s")
            b.pill(x + 20, ry + 6, code, ip, "white", size=13, h=26, padx=10, font="mono", w=56)
            b.text(x + 86, ry + 6, 262, 26, name, size=16, lineHeight=1.6, valign="middle", bold=cur,
                   color="primary" if cur else "on-surface")
    b.foot(f.get("crumb", "목차"))


def revisions(b, f):
    b.head(f.get("title", "개정 내역"), f.get("sub"), f.get("kick", ["neutral:전체"]))
    rows = [f.get("header", ["버전", "일자", "내용", "작성·검토"])] + f["rows"]
    rh = 46
    b.add({"type": "table", "x": 64, "y": 184, "w": 1152, "h": rh * len(rows), "rows": rows,
           "colW": f.get("colW", [110, 150, 732, 160]), "header": True, "headFill": "surface-container-high",
           "headColor": "on-surface", "size": 16, "rule": "surface-container-high"})
    if f.get("note"):
        y = 184 + rh * len(rows) + 28
        b.rect(64, y, 1152, 58, "surface-container", "r-m")
        b.text(84, y + 16, 1112, 26, f["note"], size=16, color="on-surface-variant", lineHeight=1.6, valign="middle")
    b.foot(f.get("crumb", "개정 내역"))


def chapter(b, f):
    b.rect(40, 40, 1200, 640, b.dcc, "r-l")
    b.pill(96, 96, f.get("part_label", PART_LABEL.get(b.part, "")), b.dc, "white")
    b.text(88, 170, 600, 190, f["number"], size=180, bold=True, font="mono", lineHeight=1, color=b.dc)
    b.text(96, 390, 900, 120, f["title"], size=46, bold=True, lineHeight=1.2, color=b.dco, role="title")
    b.text(96, 540, 820, 70, f.get("desc", ""), size=19, lineHeight=1.6, color=b.dco)
    lw = 36 * LOGO_RATIO
    b.rect(W - 88 - lw - 36, 88, lw + 36, 64, "white", "r-m", locked=True)
    b.image(W - 88 - lw - 18, 102, lw, 36, LOGO, locked=True)


def section(b, f):
    n = f["number"]  # 5글자 이상(18.12 등)은 원 안에 들어가게 줄인다
    b.ellipse(96, 228, 200, b.dcc, text=n, size=72 if len(n) <= 4 else 58, bold=True, font="mono", color=b.dc)
    b.day_pill(340, 240)
    b.text(340, 288, 820, 52, f["title"], size=42, bold=True, lineHeight=1.2, role="title")
    if f.get("sub"):
        b.text(340, 350, 820, 32, f["sub"], size=22, color="on-surface-variant", lineHeight=1.4)
    b.tags(340, 404, f.get("tags", []))
    b.logo()
    b.foot(f.get("crumb", ""))


def bullets(b, f):
    b.head(f["title"], f.get("sub"))
    b.add({"type": "bullets", "x": 64, "y": 184, "w": 1152, "h": 330, "items": f["items"], "size": 20,
           "subSize": 17, "lineHeight": 1.55, "dot": b.dc, "color": "on-surface", "subColor": "on-surface-variant",
           "gap": 14, "subGap": 6})
    if f.get("note"):
        n = f["note"]
        x, w = W - 64 - 400, 400
        b.rect(x, 520, w, 120, "surface-container", "r-m")
        b.tag(x + 20, 536, n.get("tag", "theory"))
        b.text(x + 20, 570, w - 40, 54, n["text"], size=13, lineHeight=1.6, color="on-surface-variant")
    b.foot(f.get("crumb", ""))


STEP = "①②③④⑤⑥⑦"


def sequence(b, f):
    """시퀀스 다이어그램 — 참여자(생명선) · 메시지(순서 색 s1~s7, 번호 원) · 묶음(groups: 프로세스 경계) · 반복(loops) · 경계 표시(links).
    참여자 수에 맞춰 열을 고르게 나눈다(x 를 주면 그 좌표)."""
    b.head(f["title"], f.get("sub"))
    ox, oy = 64, 184
    n = len(f["actors"])
    cw = 1152 / n
    X = f.get("x") or [i * cw for i in range(n)]
    pw = f.get("actorW", min(180, cw - 16))
    cx = lambda i: ox + X[i] + (pw / 2 if f.get("x") is None else 90) + ((cw - pw) / 2 if f.get("x") is None else 0)
    bottom = oy + f.get("lifeH", 428)
    for g0, g1, label in f.get("groups", []):  # 프로세스 경계(배경 면)
        x0, x1 = cx(g0) - pw / 2 - 6, cx(g1) + pw / 2 + 6
        b.rect(x0, oy - 26, x1 - x0, bottom - oy + 26, "surface-dim", "r-m")
        b.text(x0 + 10, oy - 22, x1 - x0 - 20, 18, label, size=12, bold=True, color="on-surface-variant", lineHeight=1.4)
    for y1, y2, a0, a1, label in f.get("loops", []):  # 반복 구간
        x0, x1 = cx(a0) - 24, cx(a1) + 24
        b.rect(x0, oy + y1, x1 - x0, y2 - y1, "surface-container-high", "r-s")
        b.text(x0 - 156, oy + y1 + 6, 150, 34, label, size=11, color="on-surface-variant", lineHeight=1.45, align="right")
    frames = []
    for kind, guard, y1, y2, a0, a1 in f.get("frames", []):  # UML 결합 프래그먼트: loop·opt·alt [조건]
        x0, x1 = cx(a0) - 40, cx(a1) + 26
        frames.append((kind, guard, x0, x1, y1, y2))
    for i, name in enumerate(f["actors"]):
        b.pill(cx(i) - pw / 2, oy, name, "white", "on-surface", size=f.get("actorSize", 14), h=40, w=pw,
               stroke="outline-variant", strokeWidth=1)
        b.rect(cx(i) - 1, oy + 44, 2, bottom - oy - 44, "outline-variant")
    for i, label in f.get("links", []):  # 두 참여자 사이 경계(네트워크) 표시
        mx = (cx(i) + cx(i + 1)) / 2
        b.pill(mx - 60, bottom - 22, label, "surface-container", "on-surface-variant", size=11, h=20, w=120, bold=False)
    for kind, guard, x0, x1, y1, y2 in frames:  # 테두리·태그는 생명선 위에
        b.rect(x0, oy + y1, x1 - x0, y2 - y1, None, "r-s", stroke="on-surface-variant", strokeWidth=1)
        tw = text_width(kind, 11, True) + 14
        b.rect(x0, oy + y1, tw, 16, "on-surface-variant", 0, text=kind, size=11, bold=True, color="white", align="center", valign="middle")
        b.text(x0 + tw + 6, oy + y1 + 1, x1 - x0 - tw - 12, 15, f"[{guard}]", size=11, bold=True,
               color="on-surface-variant", lineHeight=1.3)
    ing = lambda i: any(g0 <= i <= g1 for g0, g1, _ in f.get("groups", []))
    for a, c, y, s, t in f["messages"]:
        col = f"s{s + 1}"
        y += oy
        num = str(s + 1)
        if a == c:
            sw = round(text_width(t, 13) + 12)
            if a == n - 1:  # 마지막 열: 생명선 왼쪽에 둔다
                x = cx(a) - 30
                b.ellipse(x, y - 11, 22, col, text=num, size=12, bold=True, color="white")
                kw = {"fill": "surface-dim", "pad": [0, 4, 0, 6]} if ing(a) else {}
                b.text(x - 6 - sw, y - 10, sw, 20, t, size=13, lineHeight=1.5, align="right", **kw)
            else:
                x = cx(a) + 8
                b.ellipse(x, y - 11, 22, col, text=num, size=12, bold=True, color="white")
                kw = {"fill": "surface-dim", "pad": [0, 6, 0, 4]} if ing(a) else {}
                b.text(x + 28, y - 10, sw, 20, t, size=13, lineHeight=1.5, **kw)
            continue
        xa, xc = cx(a), cx(c)
        b.arrow(xa, y, xc, y, col, width=2)
        x1 = min(xa, xc)
        b.ellipse(x1 + 8, y - 25, 22, col, text=num, size=12, bold=True, color="white")
        b.text(x1 + 36, y - 24, abs(xc - xa) - 40, 20, t, size=13, lineHeight=1.5)
    import math
    for a, y1, y2, s, *opt in f.get("returns", []):  # 반원 되돌이 화살표: 생명선 왼쪽으로 y1(아래) → y2(위), opt[0] = dash
        r = (y1 - y2) / 2
        pts = [[r + 2 - r * math.sin(math.pi * k / 16), r - r * math.cos(math.pi * k / 16) * -1] for k in range(17)]
        pts = [[round(x, 1), round(y, 1)] for x, y in pts]
        pts[-1][0] += 2
        b.add({"type": "curve", "x": cx(a) - r - 4, "y": oy + y2, "w": r + 6, "h": 2 * r, "points": pts,
               "color": f"s{s + 1}", "width": 2, "head": "end", **({"dash": opt[0]} if opt else {})})
    if f.get("side"):
        sx, sy = f.get("sideXY", [W - 64 - 170, 250])
        b.text(sx, sy, 170, 136, f["side"], size=15, lineHeight=1.7, fill="primary-container",
               color="on-primary-container", radius="r-m", pad=[16, 16, 16, 16])
    b.foot(f.get("crumb", ""))


def table(b, f):
    b.head(f["title"], f.get("sub"))
    rows = [f["header"]] + f["rows"]
    rh = f.get("rowH", 46)
    b.add({"type": "table", "x": 64, "y": 180, "w": 1152, "h": rh * len(rows), "rows": rows,
           "colW": f.get("colW", [1] * len(f["header"])), "header": True, "headFill": b.dcc, "headColor": b.dco,
           "size": 16, "rule": "surface-container-high", "colFont": f.get("colFont")})
    if f.get("footnote"):
        b.text(64, 180 + rh * len(rows) + 20, 1152, 50, f["footnote"], size=15, color="on-surface-variant", lineHeight=1.6)
    b.foot(f.get("crumb", ""))


MAX_CODE_LINES = 18


def png_size(src):
    """PNG 머리(IHDR)에서 픽셀 크기를 읽는다 — 이미지 라이브러리 없이."""
    import struct
    from common import REPO
    with open(REPO / src, "rb") as fh:
        head = fh.read(24)
    return struct.unpack(">II", head[16:24])


def diagram(b, f):
    """다이어그램(Mermaid 원본 → PNG, render_mermaid.py) + 오른쪽 해설 상자 + 아래 각주.
    필드: img(저장소 기준 PNG 경로), mermaid(원본 코드 — render_mermaid.py 가 img 를 만든다),
    side(해설, 선택), sideW(기본 330), imgScale(PNG 픽셀 → 화면 px 비율, 기본 0.5 = 2배 해상도 렌더), footnote(선택)."""
    b.head(f["title"], f.get("sub"))
    side = f.get("side")
    sw = f.get("sideW", 330) if side else 0
    foot_h = 44 if f.get("footnote") else 0
    x0, y0 = PAD, 176
    maxw = W - 2 * PAD - (sw + 24 if side else 0)
    maxh = 656 - y0 - foot_h - 8
    pw, ph = png_size(f["img"])
    s = f.get("imgScale", 0.5)
    w, h = pw * s, ph * s
    k = min(1.0, maxw / w, maxh / h)
    w, h = w * k, h * k
    b.image(x0 + (maxw - w) / 2, y0 + (maxh - h) / 2, w, h, f["img"])
    if side:
        b.text(W - PAD - sw, y0, sw, f.get("sideH", maxh), side, size=16, lineHeight=1.7, fill="surface-container",
               radius="r-m", pad=[18, 20, 18, 20])
    if f.get("footnote"):
        b.text(PAD, 656 - foot_h, W - 2 * PAD, foot_h, f["footnote"], size=14, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def code_el(b, x, y, w, f, size=14, lh=1.6):
    """code 요소 — 높이는 표시 줄 수로 계산. 18줄을 넘으면 경고(show 로 발췌할 것)."""
    from common import code_lines, CODE_GUTTER_W
    size = fit_size(size)
    el = {"type": "code", "x": x, "y": y, "w": w, "h": 0, "text": f["code"], "lang": f.get("lang", "sql"),
          "size": size, "lineHeight": lh, "radius": "r-m"}
    for k in ("start", "focus", "show"):
        if f.get(k):
            el[k] = f[k]
    lines = code_lines(el)
    n = len(lines)
    # 가장 긴 줄이 상자(줄 번호 열·좌우 여백 제외)를 넘으면 글자를 줄인다 — 고정폭 글꼴을 바꿔도 잘리지 않게
    avail = w - CODE_GUTTER_W - 14 - 12
    longest = max((text_width("".join(r[0] for r in l.get("runs", [])), size, mono=True) for l in lines), default=0)
    if longest > avail:
        size = round(size * avail / longest * 2) / 2
        el["size"] = size
    if n > MAX_CODE_LINES:
        print(f"  ! 코드 {n}줄 — 한 슬라이드 {MAX_CODE_LINES}줄 이내 권장(show 로 발췌)")
    el["h"] = round(24 + n * size * lh)
    return b.add(el)


def code_plan(b, f):
    b.head(f["title"], f.get("sub"))
    c = code_el(b, 64, 184, f.get("codeW", 528), f, size=f.get("codeSize", 14))
    px = 64 + c["w"] + 24
    pw = W - 64 - px
    size, lh = f.get("planSize", 12.5), 1.55
    import re as _re
    longest = text_width(_re.sub(r"\[\[(\d+)\]\]", r"\1", f["plan"]), size, mono=True)
    if longest > pw - 36:  # 좌우 여백 18+18
        size = round(size * (pw - 36) / longest * 2) / 2
    pn = f["plan"].count("\n") + 1
    ph = round(pn * size * lh + 32)
    b.add({"type": "plan", "x": px, "y": 184, "w": pw, "h": ph, "text": f["plan"], "size": size, "lineHeight": lh,
           "fill": "surface-container", "color": "on-surface", "radius": "r-m", "pad": [16, 18, 16, 18]})
    if f.get("callout"):
        b.text(px, 184 + ph + 20, pw, 84, f["callout"], size=16, lineHeight=1.6, fill="primary-container",
               color="on-primary-container", radius="r-m", pad=[16, 18, 16, 18], valign="middle")
    b.foot(f.get("crumb", ""))


def code_excerpt(b, f):
    """긴 코드 발췌 — 원본 줄 번호 유지 + 생략(⋮) + 강조 줄 + 설명 카드 + 전체 파일 칩"""
    b.head(f["title"], f.get("sub"))
    code_el(b, 64, 184, 760, f, size=f.get("codeSize", 14), lh=1.55)
    x, w = 848, 368
    if f.get("side"):
        n = f.get("sideLines", f["side"].count("\n") + 1)
        hh = round(18 + 26 + 12 + n * 16 * 1.7 + 18)
        b.rect(x, 184, w, hh, "surface-container", "r-m")
        b.tags(x + 20, 202, f.get("tags", ["theory", "lab"]))
        b.text(x + 20, 240, w - 40, hh - 58, f["side"], size=16, lineHeight=1.7)
        y2 = 184 + hh + 20
    else:
        y2 = 184
    if f.get("file"):
        kind, path, desc = f["file"]
        b.rect(x, y2, w, 80, "surface-container", "r-m")
        b.rect(x + 18, y2 + 14, 52, 52, "ci-dark", "r-m", text=kind, size=14, bold=True, color="white", align="center", valign="middle")
        b.text(x + 84, y2 + 16, w - 100, 24, path, size=14, font="mono", lineHeight=1.5)
        b.text(x + 84, y2 + 44, w - 100, 20, desc, size=13, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def plan_table(b, f):
    """실행계획 해설용 표 — Operation 들여쓰기(depth), 셀 강조(warn/ok), 오른쪽 콜아웃."""
    b.head(f["title"], f.get("sub"))
    rows = f["rows"]
    rh = f.get("rowH", 46)
    cw = f.get("calloutW", 380)
    b.add({"type": "plan-table", "x": 64, "y": 184, "w": 1152, "h": rh * (len(rows) + 1), "columns": f["columns"],
           "colW": f.get("colW"), "align": f.get("align"), "opCol": f.get("opCol", 1), "rows": rows,
           "size": 15, "headFill": b.dcc, "headColor": b.dco, "rule": "surface-container-high", "calloutW": cw})
    if f.get("footnote"):
        b.text(64, 184 + rh * (len(rows) + 1) + 28, 1152 - cw - 24, 60, f["footnote"], size=15, lineHeight=1.6,
               color="on-surface-variant")
    b.foot(f.get("crumb", ""))


def compare(b, f):
    b.head(f["title"], f.get("sub"))
    spec = [("before", "primary-container", "primary", "on-primary-container"),
            ("after", "lab-container", "lab", "on-lab-container")]
    for i, (k, bg, c, on) in enumerate(spec):
        d = f[k]
        x, y = 64 + i * 588, 184
        b.rect(x, y, 564, 330, bg, "r-l")
        b.pill(x + 28, y + 26, d.get("label", k.title()), c, "white")
        b.text(x + 28, y + 70, 508, 34, d["title"], size=24, bold=True, color=on, lineHeight=1.3)
        b.text(x + 28, y + 116, 508, 70, d["desc"], size=18, lineHeight=1.7, color=on)
        b.text(x + 28, y + 330 - 26 - 40, 508, 40, d["result"], size=30, bold=True, color=c, lineHeight=1.3)
    if f.get("footnote"):
        b.text(64, 540, 1000, 22, f["footnote"], size=14, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def files(b, f):
    b.head(f["title"], f.get("sub"))
    for i, (kind, path, desc, lab) in enumerate(f["files"]):
        x, y = 64, 184 + i * 124
        b.rect(x, y, 1152, 104, "surface-container", "r-m")
        b.rect(x + 20, y + 20, 64, 64, "ci-dark", "r-m", text=kind, size=17, bold=True, color="white", align="center", valign="middle")
        b.text(x + 108, y + 20, 820, 28, path, size=19, font="mono", lineHeight=1.4)
        b.text(x + 108, y + 58, 820, 24, desc, size=16, color="on-surface-variant", lineHeight=1.5)
        p = b.pill(0, y + 36, lab, "lab-container", "lab", size=13, h=26, padx=12)
        p["x"] = x + 1152 - 24 - p["w"]
    b.foot(f.get("crumb", ""))


def lab(b, f):
    b.head(f["title"], f.get("sub"), f.get("tags", ["lab", "req"]))
    for i, s in enumerate(f["steps"]):
        y = 184 + i * 62
        b.ellipse(64, y + 14, 34, "lab", text=str(i + 1), size=16, bold=True, color="white")
        b.text(112, y + 14, 590, 34, s, size=19, lineHeight=1.5, valign="middle")
    if f.get("side"):
        # 높이는 줄 수에 맞춘다(17px × 1.8 ≈ 31px/줄 + 위아래 여백 40) — 최소 170
        h = max(170, 40 + 31 * (f["side"].count("\n") + 1))
        b.text(W - 64 - 470, 184, 470, h, f["side"], size=17, lineHeight=1.8, fill="surface-container",
               radius="r-m", pad=[20, 24, 20, 24])
    b.foot(f.get("crumb", ""))


def summary(b, f):
    b.head(f["title"], f.get("sub"))
    for i, t in enumerate(f["items"]):
        y = 184 + i * 68
        b.rect(64, y, 1152, 58, "surface-container", "r-m")
        b.ellipse(84, y + 14, 30, b.dc, text="✓", size=16, bold=True, color="white")
        b.text(130, y + 14, 1060, 30, t, size=19, lineHeight=1.55, valign="middle")
    b.foot(f.get("crumb", ""))


def chapter_toc(b, f):
    """장 목차(중분류 지도) — 절 번호·제목·필수/심화를 두 열로."""
    b.head(f.get("title", "이 장의 구성"), f.get("sub"))
    items = f["sections"]
    per = f.get("perCol", (len(items) + 1) // 2)
    rh = f.get("rowH", 66)
    for i, it in enumerate(items):
        num, title, lv = it[0], it[1], (it[2] if len(it) > 2 else "req")
        x = 64 + (i // per) * 588
        y = 184 + (i % per) * rh
        b.rect(x, y, 564, rh - 10, "surface-container", "r-m")
        b.pill(x + 16, y + (rh - 10 - 30) / 2, num, b.dc, "white", size=14, h=30, padx=10, font="mono", w=64)
        b.text(x + 96, y + (rh - 10 - 28) / 2, 370, 28, title, size=17, lineHeight=1.6, valign="middle")
        t = b.tag(0, y + (rh - 10 - 26) / 2, lv)
        t["x"] = x + 564 - 16 - t["w"]
    if f.get("stats"):  # 요약 칩 줄: [["절", "필수 8 · 심화 3"], ["예상 시간", "필수 90분 · 전체 140분"], …]
        x, y = 64, 184 + per * rh + 10
        for label, value in f["stats"]:
            p = b.pill(x, y, label, b.dcc, b.dco, size=13, h=28, padx=12)
            vw = text_width(value, 16, True) + 4
            b.text(x + p["w"] + 10, y, vw, 28, value, size=16, bold=True, lineHeight=1.6, valign="middle")
            x += p["w"] + 10 + vw + 28
    elif f.get("note"):
        b.text(64, 184 + per * rh + 8, 1152, 24, f["note"], size=14, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def subsection(b, f):
    """소분류 — 절 안의 주제. 상위 절 칩 + 번호·제목·설명 + 같은 절 소분류 흐름(현재 강조)."""
    x = b.day_pill(PAD, 36)["w"] + PAD + 8
    if f.get("parent"):
        b.pill(x, 36, f["parent"], "surface-container", "on-surface-variant")
    b.logo()
    b.text(64, 200, 600, 48, f["number"], size=40, bold=True, font="mono", color=b.dc, lineHeight=1.2)
    b.text(64, 262, 1100, 56, f["title"], size=40, bold=True, lineHeight=1.25, role="title")
    if f.get("desc"):
        b.text(64, 336, 1000, 70, f["desc"], size=20, color="on-surface-variant", lineHeight=1.6)
    if f.get("tags"):
        b.tags(64, 424, f["tags"])
    sib = f.get("siblings", [])
    if sib:
        xx, y = 64, 520
        b.rect(64, y - 20, 1152, 2, "surface-container-high")
        for num, name in sib:
            cur = num == f["number"]
            p = b.pill(xx, y, f"{num}  {name}", b.dc if cur else "surface-container",
                       "white" if cur else "on-surface-variant", size=14, h=32, padx=14, bold=cur)
            xx += p["w"] + 10
    b.foot(f.get("crumb", ""))


def flow(b, f):
    """순서 흐름 — 단계 카드(순서 색 s1~s7) + 사이 화살표, 아래 규칙 카드."""
    b.head(f["title"], f.get("sub"))
    steps = f["steps"]
    n = len(steps)
    gap = 32
    cw = (1152 - (n - 1) * gap) / n
    y0 = 214 if f.get("ends") else 184
    ch = f.get("cardH", 220)
    if f.get("ends"):
        left, right = f["ends"]
        b.text(64, 182, 400, 22, left, size=14, bold=True, color="primary", lineHeight=1.5)
        b.text(1216 - 400, 182, 400, 22, right, size=14, color="on-surface-variant", lineHeight=1.5, align="right")
    for i, st in enumerate(steps):
        x = 64 + i * (cw + gap)
        col = st.get("color", f"s{i % 7 + 1}")
        b.rect(x, y0, cw, ch, "surface-container", "r-m")
        b.ellipse(x + 16, y0 + 16, 34, col, text=st.get("mark", str(i + 1)), size=16, bold=True, color="white")
        b.text(x + 16, y0 + 62, cw - 32, 52, st["title"], size=f.get("titleSize", 18), bold=True, lineHeight=1.4, color=col)
        if st.get("desc"):
            b.text(x + 16, y0 + 116, cw - 32, ch - 128, st["desc"], size=f.get("descSize", 15), lineHeight=1.6,
                   color="on-surface-variant")
        if i < n - 1:
            ax = x + cw + 4
            b.arrow(ax, y0 + ch / 2, ax + gap - 8, y0 + ch / 2, "outline-variant", width=2)
    notes = f.get("cardsBelow") or []
    if notes:
        ny = y0 + ch + 24
        nw = (1152 - (len(notes) - 1) * 24) / len(notes)
        nh = f.get("noteH", 104)
        for i, nt in enumerate(notes):
            x = 64 + i * (nw + 24)
            tone = nt.get("tone", "neutral")
            fill = "surface-container" if tone == "neutral" else f"{tone}-container"
            b.rect(x, ny, nw, nh, fill, "r-m")
            b.text(x + 20, ny + 12, nw - 40, nh - 24, nt["text"], size=16, lineHeight=1.6, valign="middle")
    b.foot(f.get("crumb", ""))


def cards(b, f):
    """카드 2~3장 나란히 — 개념 대비. tone: day1/day2/day3/theory/lab/primary/neutral"""
    b.head(f["title"], f.get("sub"))
    cs = f["cards"]
    n = len(cs)
    gap = 24
    cw = (1152 - (n - 1) * gap) / n
    ch = f.get("cardH", 340)
    for i, c in enumerate(cs):
        x, y = 64 + i * (cw + gap), 184
        tone = c.get("tone", "neutral")
        fill = "surface-container" if tone == "neutral" else f"{tone}-container"
        acc = "ci-dark" if tone == "neutral" else tone
        b.rect(x, y, cw, ch, fill, "r-l")
        if c.get("label"):
            b.pill(x + 24, y + 22, c["label"], acc, "white")
        tl, ts = f.get("titleLines", 1), f.get("titleSize", 23)
        th = round(ts * 1.3 * tl)
        b.text(x + 24, y + 66, cw - 48, th, c["title"], size=ts, bold=True, lineHeight=1.3)
        by = y + 66 + th + 14
        b.text(x + 24, by, cw - 48, y + ch - by - (60 if c.get("result") else 20), c["body"],
               size=f.get("bodySize", 17), lineHeight=1.65)
        if c.get("result"):
            b.text(x + 24, y + ch - 54, cw - 48, 34, c["result"], size=20, bold=True, color=acc, lineHeight=1.4)
    if f.get("footnote"):
        b.text(64, 184 + ch + 22, 1152, 50, f["footnote"], size=15, color="on-surface-variant", lineHeight=1.6)
    b.foot(f.get("crumb", ""))


def end(b, f):
    """EoD(문서 끝) — 공통. 다음 장 안내·문의."""
    b.rect(40, 40, 1200, 640, "surface-container", "r-l")
    b.image(96, 96, 44 * LOGO_RATIO, 44, LOGO, locked=True)
    b.text(96, 250, 900, 80, f.get("title", "End of Document"), size=60, bold=True, lineHeight=1.2, role="title")
    b.text(96, 340, 900, 36, f.get("sub", ""), size=22, color="on-surface-variant", lineHeight=1.5)
    if f.get("next"):
        code, name, part, *where = f["next"]
        # 장 번호는 주제 번호이고 순서는 전체 목차(교육 순서)를 따른다 — "다음 장"이 번호순이 아님을 밝힌다
        label = "다음 순서" + (f" · {where[0]}" if where else "") + CONFIG.get("endNextNote", "")
        b.text(96, 452, 900, 24, label, size=15, color="on-surface-variant", lineHeight=1.5)
        p = b.pill(96, 484, code, part, "white", size=16, h=36, padx=14, font="mono")
        b.text(96 + p["w"] + 14, 484, 700, 36, name, size=22, bold=True, lineHeight=1.6, valign="middle")
    b.text(760, 560, 420, 80, f.get("meta", ""), size=15, lineHeight=1.8, color="on-surface-variant", align="right")


LAYOUTS = {
    "cover": ("표지", cover), "toc": ("목차", toc), "revisions": ("개정 내역", revisions),
    "chapter": ("장 표지", chapter), "section": ("절 구분", section), "bullets": ("본문 글머리", bullets),
    "sequence": ("본문+다이어그램(시퀀스)", sequence), "table": ("표", table), "code_plan": ("코드+실행계획", code_plan),
    "plan_table": ("실행계획 해설 표", plan_table), "code_excerpt": ("긴 코드 발췌", code_excerpt),
    "compare": ("전후 비교", compare), "files": ("예제 파일 연결", files), "lab": ("실습", lab), "summary": ("장 정리", summary),
    "chapter_toc": ("장 목차(중분류)", chapter_toc), "subsection": ("소분류", subsection), "flow": ("순서 흐름", flow),
    "cards": ("카드 대비", cards), "diagram": ("다이어그램(Mermaid 이미지)", diagram), "end": ("문서 끝(EoD)", end),
}

# 편집기의 "레이아웃으로 새 슬라이드" 기본 내용(자리 표시)
SAMPLES = {
    "cover": {"title": "제목\n두 번째 줄", "subtitle": "부제", "days": [["day1", "Day1 설계"]], "meta": "작성 부서\n장 제목\nv0.1"},
    "toc": {"groups": [{"part": "day1", "label": "Day1 설계", "items": [["ch00", "장 제목"]]}]},
    "revisions": {"rows": [["v0.1", "2026-00-00", "내용", "작성자"]], "note": "버전 규칙"},
    "chapter": {"number": "00", "title": "장 제목\n두 번째 줄", "desc": "장 소개 문장"},
    "section": {"number": "0.0", "title": "절 제목", "sub": "부제", "tags": ["req"], "crumb": "chNN › 0.0"},
    "bullets": {"title": "소제목", "sub": "부제", "items": ["항목 1", {"text": "항목 2", "sub": ["보조 설명"]}], "crumb": "chNN › 0.0"},
    "sequence": {"title": "시퀀스", "actors": ["A", "B"], "messages": [[0, 1, 84, 0, "요청"], [1, 0, 134, 1, "응답"]], "crumb": ""},
    "table": {"title": "표", "header": ["열 1", "열 2"], "rows": [["값", "값"]], "crumb": ""},
    "code_plan": {"title": "코드와 실행계획", "code": "SELECT *\nFROM   t\nWHERE  c = :b;", "plan": "| Id | Operation |", "crumb": ""},
    "code_excerpt": {"title": "긴 코드 발췌", "code": "SELECT 1\nFROM   dual;", "show": [[1, 2]], "focus": [1],
                     "side": "**1행** 설명", "file": ["SQL", "sql/chNN/파일.sql", "전체 N줄 · 실습 NN-NN"], "crumb": ""},
    "plan_table": {"title": "실행계획 해설", "columns": ["Id", "Operation", "Rows"], "colW": [1, 4, 1],
                   "rows": [{"cells": ["0", "SELECT STATEMENT", ""], "depth": 0},
                            {"cells": ["1", "TABLE ACCESS FULL", "1"], "depth": 1, "hl": {"2": "warn"}, "note": "설명"}], "crumb": ""},
    "compare": {"title": "전후 비교", "before": {"label": "Before", "title": "이전", "desc": "설명", "result": "결과"},
                "after": {"label": "After", "title": "이후", "desc": "설명", "result": "결과"}, "crumb": ""},
    "files": {"title": "예제 파일", "files": [["SQL", "sql/chNN/파일.sql", "설명", "실습 NN-NN"]], "crumb": ""},
    "lab": {"title": "실습", "steps": ["단계 1", "단계 2"], "side": "**확인 지표**\n항목", "crumb": ""},
    "summary": {"title": "정리", "items": ["기억할 것 1", "기억할 것 2"], "crumb": ""},
    "chapter_toc": {"title": "이 장의 구성", "sections": [["0.1", "절 제목", "req"], ["0.2", "절 제목", "adv"]], "crumb": ""},
    "subsection": {"number": "0.0.1", "title": "소분류 제목", "desc": "설명", "parent": "0.0 절 제목",
                   "siblings": [["0.0.1", "주제 1"], ["0.0.2", "주제 2"]], "crumb": ""},
    "flow": {"title": "순서 흐름", "steps": [{"title": "단계 1", "desc": "설명"}, {"title": "단계 2", "desc": "설명"}], "crumb": ""},
    "cards": {"title": "카드 대비", "cards": [{"label": "A", "title": "제목", "body": "내용"},
                                         {"label": "B", "title": "제목", "body": "내용"}], "crumb": ""},
    "diagram": {"title": "다이어그램", "sub": "Mermaid 원본은 content 의 mermaid 필드", "img": LOGO,
                "imgScale": 0.4, "side": "**해설**\n내용", "crumb": ""},
    "end": {"title": "End of Document", "sub": "부제", "meta": "문의"},
}


def build_slide(layout, fields, part="day1", sid="s01"):
    if layout not in LAYOUTS:
        raise ValueError(f"알 수 없는 레이아웃: {layout}")
    b = B(part)
    b.level = fields.get("level")
    b.source = fields.get("source")
    LAYOUTS[layout][1](b, copy.deepcopy(fields))
    return {"id": sid, "layout": layout, "notes": fields.get("notes", ""), "elements": b.els}
