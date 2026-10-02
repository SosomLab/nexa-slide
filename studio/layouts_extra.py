# -*- coding: utf-8 -*-
"""업무·일정·이야기용 레이아웃 14종 - 보고서·결정 요청·일정·회고·공지·RFP 시작용 교안이 쓴다.

기존 요소(rect·text·pill·ellipse·arrow·image)만 조합한다 - 렌더러(render.js·export_pptx.py)는 그대로라
편집기와 PPTX 가 같은 규칙으로 그린다. 좌표·크기는 px(1280×720). 상태 값은 토큰 역할 ok·caution·bad·info·idle.

레이아웃                      쓰임
status_table   상태 표       계획/실적/차이/상태/담당 - 셀 상태 칩·행 채우기·합계 행·결론 상자
kpi_tiles      KPI 타일      큰 숫자 2~4개 + 목표·비교·상태
issue_cards    이슈 카드     상황·영향·요청·담당·기한
grid_cards     격자 카드     2×2·3×2·4열 카드(번호·상태·톤)
statement      한 문장       축 문장·결론 장(밝게/어둡게)
quote          인용          큰 인용 + 화자
big_number     큰 숫자       숫자 하나 + 맥락 + 비교 칩
decision_brief 결정 요청     위 결론 배너 / 3열 근거 / 아래 결정 띠(무엇을·누가·언제까지)
milestones     마일스톤      날짜 칩이 놓인 가로 타임라인 + NOW
roadmap        로드맵        Now / Next / Later 열 카드
gantt          간트          기간×작업 막대 + 게이트 + NOW 선
week_grid      시간표        일자×시간 칸(여러 칸 걸침)
photo_text     사진+글       사진(없으면 자리 표시) + 제목·글·목록
agenda         진행 순서     번호·제목·시간·담당 목록
여러 레이아웃이 함께 쓰는 필드: action(아래 행동 띠 한 줄), footnote(아래 한 줄 주석), crumb.
"""
from layouts import H, PAD, W, B, text_width  # noqa: F401

STATUS = {"ok": "정상", "caution": "주의", "bad": "위험", "info": "진행", "idle": "대기"}
RIGHT = W - PAD


def status_chip(b, x, y, st, label=None, h=28, size=15):
    st = st if st in STATUS else "idle"
    return b.pill(x, y, label or STATUS[st], f"{st}-container", st, size=size, h=h, padx=12)


def action_bar(b, text, y=588, label="다음 행동"):
    """아래 행동 띠 - 마지막 장·결론 장의 "누가 무엇을 언제까지" 한 줄."""
    b.rect(PAD, y, W - 2 * PAD, 56, "primary-container", "r-m")
    p = b.pill(PAD + 16, y + 13, label, "primary", "on-primary", size=15, h=30, padx=14)
    b.text(PAD + 32 + p["w"], y + 12, W - 2 * PAD - 48 - p["w"], 32, text, size=18, bold=True,
           color="on-primary-container", lineHeight=1.5, valign="middle")


def bottom_extras(b, f, y_free):
    """footnote·action 을 남은 자리에(action 이 있으면 588 고정)."""
    if f.get("footnote"):
        fy = (588 - 40) if f.get("action") else y_free
        b.text(PAD, fy, W - 2 * PAD, 30, f["footnote"], size=15, color="on-surface-variant", lineHeight=1.5)
    if f.get("action"):
        action_bar(b, f["action"], label=f.get("actionLabel", "다음 행동"))


def _cell(c):
    return c if isinstance(c, dict) else {"text": str(c)}


def status_table(b, f):
    """상태 표 - header, rows([셀…] 또는 {"cells": […], "fill": 토큰, "total": true}), 셀 = 글 또는
    {"text", "status", "bold", "color"}. colW(px 합 1152 또는 비율), align(열별 left/center/right),
    rowH(기본 48), conclusion(아래 결론 상자), action, footnote. 9행 넘으면 장을 나눈다."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    hdr, rows = f["header"], f["rows"]
    n = len(hdr)
    cw = f.get("colW") or [1] * n
    tot = sum(cw)
    cw = [w * 1152 / tot for w in cw]
    al = f.get("align") or ["left"] * n
    rh = f.get("rowH", 48)
    y = 180
    b.rect(PAD, y, 1152, 44, b.dcc, "r-s")
    x = PAD
    for j, h in enumerate(hdr):
        b.text(x + 14, y + 8, cw[j] - 28, 28, h, size=15, bold=True, color=b.dco, lineHeight=1.5, valign="middle", align=al[j])
        x += cw[j]
    y += 44
    if len(rows) > 9:
        print(f"  ! status_table {len(rows)}행 - 9행 이내 권장(장을 나눈다)")
    for r in rows:
        row = r if isinstance(r, dict) else {"cells": r}
        cells = [_cell(c) for c in row["cells"]]
        fill = row.get("fill") or ("surface-container" if row.get("total") else None)
        if fill:
            b.rect(PAD, y, 1152, rh, fill, 0)
        x = PAD
        for j, c in enumerate(cells[:n]):
            if c.get("status"):
                p = status_chip(b, 0, y + (rh - 28) / 2, c["status"], c.get("text") or None)
                p["x"] = round(x + (cw[j] - p["w"]) / 2 if al[j] == "center" else
                               (x + cw[j] - 14 - p["w"] if al[j] == "right" else x + 14))
            else:
                b.text(x + 14, y + 4, cw[j] - 28, rh - 8, c.get("text", ""), size=c.get("size", 16),
                       bold=bool(c.get("bold") or row.get("total")), color=c.get("color", "on-surface"),
                       lineHeight=1.4, valign="middle", align=al[j])
            x += cw[j]
        y += rh
        b.rect(PAD, y - 1, 1152, 1, "surface-container-high")
    if f.get("conclusion"):
        y += 16
        b.text(PAD, y, 1152, 52, f["conclusion"], size=17, bold=True, lineHeight=1.5, fill="surface-container",
               radius="r-m", pad=[12, 20, 12, 20], valign="middle")
        y += 52
    bottom_extras(b, f, y + 14)
    b.foot(f.get("crumb", ""))


def kpi_tiles(b, f):
    """KPI 타일 2~4개 - tiles: {label, value, unit, target, delta, status, note}. 아래 items(요약 줄, 선택)·action·footnote."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    ts = f["tiles"]
    n = len(ts)
    gap = 24
    tw = (1152 - (n - 1) * gap) / n
    th = f.get("tileH", 236)
    y = 184
    for i, t in enumerate(ts):
        x = PAD + i * (tw + gap)
        st = t.get("status")
        b.rect(x, y, tw, th, "surface-container", "r-l")
        b.rect(x, y, 8, th, st or b.dc, "r-s")
        b.text(x + 28, y + 22, tw - 56 - (90 if st else 0), 26, t["label"], size=17, bold=True,
               color="on-surface-variant", lineHeight=1.5)
        if st:
            p = status_chip(b, 0, y + 20, st, t.get("statusLabel"))
            p["x"] = round(x + tw - 20 - p["w"])
        vs = t.get("valueSize", 56 if n <= 3 else 46)
        vw = text_width(t["value"], vs, True) + 6
        b.text(x + 28, y + 60, min(vw, tw - 56), vs * 1.25, t["value"], size=vs, bold=True, lineHeight=1.2,
               color=t.get("color", "on-surface"))
        if t.get("unit"):
            b.text(x + 28 + vw + 6, y + 60 + vs * 1.25 - 34, tw - 56 - vw - 6, 30, t["unit"], size=19,
                   color="on-surface-variant", lineHeight=1.4)
        yy = y + 60 + vs * 1.25 + 10
        for k, col in (("target", "on-surface-variant"), ("delta", st or "on-surface-variant")):
            if t.get(k):
                b.text(x + 28, yy, tw - 56, 26, t[k], size=16, bold=k == "delta", color=col, lineHeight=1.5)
                yy += 28
    y += th + 24
    for it in f.get("items", [])[:3]:
        b.text(PAD, y, 1152, 30, f"·  {it}", size=17, lineHeight=1.6)
        y += 34
    bottom_extras(b, f, y + 6)
    b.foot(f.get("crumb", ""))


ISSUE_FIELDS = (("situation", "상황"), ("impact", "영향"), ("ask", "요청"))


def issue_cards(b, f):
    """이슈 카드 1~3개 - issues: {title, status, situation, impact, ask, owner, due}. 요청은 카드 아래 띠로."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    iss = f["issues"]
    n = len(iss)
    gap = 24
    cw = (1152 - (n - 1) * gap) / n
    ch = f.get("cardH", 380)
    y = 184
    for i, it in enumerate(iss):
        x = PAD + i * (cw + gap)
        st = it.get("status", "caution")
        b.rect(x, y, cw, ch, "surface-container", "r-l")
        b.rect(x, y, cw, 8, st, "r-s")
        p = status_chip(b, x + 24, y + 26, st, it.get("statusLabel"))
        b.text(x + 24, y + 66, cw - 48, 60, it["title"], size=20, bold=True, lineHeight=1.4)
        yy = y + 132
        for k, lab in ISSUE_FIELDS[:2]:
            if it.get(k):
                b.text(x + 24, yy, cw - 48, 66, f"**{lab}**  {it[k]}", size=16, lineHeight=1.55)
                yy += 74
        if it.get("ask"):
            b.text(x + 16, y + ch - 112, cw - 32, 96, f"**요청**  {it['ask']}" +
                   (f"\n{it.get('owner', '')} · {it.get('due', '')}" if it.get("owner") or it.get("due") else ""),
                   size=16, lineHeight=1.55, fill="white", radius="r-m", pad=[12, 14, 12, 14])
    bottom_extras(b, f, y + ch + 16)
    b.foot(f.get("crumb", ""))


def grid_cards(b, f):
    """격자 카드 - items: {num?, label?, title, body, tone?, status?}, cols(기본 2), rows 는 개수로. 2×2·3×2·4열."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    its = f["items"]
    cols = f.get("cols", 2)
    rows = (len(its) + cols - 1) // cols
    gap = 20
    top, bottom = 184, (568 if f.get("action") else 640)
    cw = (1152 - (cols - 1) * gap) / cols
    ch = f.get("cardH") or (bottom - top - (rows - 1) * gap) / rows
    if rows == 1 and not f.get("cardH"):  # 한 줄이면 바닥까지 늘이지 않는다
        ch = min(ch, 300)
    for i, it in enumerate(its):
        x = PAD + (i % cols) * (cw + gap)
        y = top + (i // cols) * (ch + gap)
        tone = it.get("tone", "neutral")
        fill = "surface-container" if tone == "neutral" else f"{tone}-container"
        acc = b.dc if tone == "neutral" else tone
        b.rect(x, y, cw, ch, fill, "r-l")
        tx = x + 24
        if it.get("num") is not None:
            b.ellipse(x + 22, y + 22, 40, acc, text=str(it["num"]), size=19, bold=True, color="white")
            tx = x + 76
        elif it.get("label"):
            p = b.pill(x + 24, y + 22, it["label"], acc, "white", size=15)
            tx = x + 24
        if it.get("status"):
            p = status_chip(b, 0, y + 22, it["status"], it.get("statusLabel"))
            p["x"] = round(x + cw - 20 - p["w"])
        ty = y + 24 if it.get("num") is not None else (y + 64 if it.get("label") else y + 24)
        b.text(tx, ty, x + cw - tx - (110 if it.get("status") else 24), 34, it["title"], size=f.get("titleSize", 20),
               bold=True, lineHeight=1.5)
        by = ty + 42
        b.text(x + 24, by, cw - 48, y + ch - by - 16, it.get("body", ""), size=f.get("bodySize", 16), lineHeight=1.6,
               color="on-surface-variant")
    bottom_extras(b, f, top + rows * ch + (rows - 1) * gap + 14)
    b.foot(f.get("crumb", ""))


def statement(b, f):
    """한 문장 - text(큰 문장), kicker(위 칩), sub(아래 작은 글), dark(어두운 바탕)."""
    dark = f.get("dark")
    if dark:
        b.rect(0, 0, W, H, b.dc, 0)
    fg = "white" if dark else "on-surface"
    if f.get("kicker"):
        b.pill(120, 200, f["kicker"], "white" if dark else b.dcc, b.dc if dark else b.dco, size=16, h=34)
    b.text(120, 252, 1040, 220, f["text"], size=f.get("size", 46), bold=True, lineHeight=1.35, color=fg,
           font="heading", role="title", valign="top")
    if f.get("sub"):
        b.text(120, 500, 1040, 60, f["sub"], size=20, lineHeight=1.6, color="white" if dark else "on-surface-variant")
    if not dark:
        b.logo()
    b.foot(f.get("crumb", ""))


def quote(b, f):
    """인용 - text, who(화자 실명), role(역할·소속), context(언제·어디서)."""
    b.head(f.get("title", ""), f.get("sub"), f.get("kick")) if f.get("title") else b.logo()
    y = 200 if f.get("title") else 150
    b.rect(120, y, 10, 300, b.dc, "r-s")
    b.text(160, y - 34, 120, 124, "“", size=120, bold=True, color=b.dcc, lineHeight=1, font="heading")
    b.text(170, y + 92, 960, 160, f["text"], size=f.get("size", 32), lineHeight=1.55, font="heading", color="on-surface")
    who = f.get("who", "")
    if f.get("role"):
        who += f"  ·  {f['role']}"
    b.text(170, y + 262, 960, 30, who, size=19, bold=True, color=b.dc, lineHeight=1.5)
    if f.get("context"):
        b.text(170, y + 296, 960, 28, f["context"], size=16, color="on-surface-variant", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def big_number(b, f):
    """큰 숫자 - value, unit, label(무엇의 숫자), context(의미 한두 줄), compare(비교 칩 [[이름, 값], …])."""
    b.head(f["title"], f.get("sub"), f.get("kick")) if f.get("title") else b.logo()
    y = 200
    vs = f.get("size", 150)
    vw = text_width(f["value"], vs, True) * 1.06 + 16
    b.text(PAD + 56, y, min(vw, 900), vs * 1.15, f["value"], size=vs, bold=True, lineHeight=1.1, color=b.dc)
    if f.get("unit"):
        b.text(PAD + 56 + vw + 8, y + vs * 1.15 - 64, 300, 56, f["unit"], size=36, bold=True, color=b.dc, lineHeight=1.3)
    yy = y + vs * 1.15 + 16
    if f.get("label"):
        b.text(PAD + 60, yy, 1000, 36, f["label"], size=24, bold=True, lineHeight=1.4)
        yy += 46
    if f.get("context"):
        b.text(PAD + 60, yy, 1000, 70, f["context"], size=18, lineHeight=1.6, color="on-surface-variant")
        yy += 80
    x = PAD + 60
    for name, val in f.get("compare", []):
        p = b.pill(x, yy, f"{name}  {val}", "surface-container", "on-surface", size=16, h=34, padx=14, bold=False)
        x += p["w"] + 10
    bottom_extras(b, f, 600)
    b.foot(f.get("crumb", ""))


def decision_brief(b, f):
    """결정 요청 1장 - 공통 머리 없이: 위 결론 배너(kicker·title·sub) / 가운데 근거 3열(columns: {title, body}) /
    아래 결정 띠(ask: 무엇을, owner: 누가, due: 언제까지, impact: 안 하면). 바닥은 crumb·출처."""
    b.rect(PAD, 40, 1152, 150, b.dcc, "r-l")
    p = b.pill(PAD + 28, 60, f.get("kicker", "결정 요청"), b.dc, "white", size=15)
    if f.get("date"):
        b.text(PAD + 40 + p["w"], 60, 400, 30, f["date"], size=15, color=b.dco, lineHeight=1.6, valign="middle")
    import layouts as _L
    b.image(RIGHT - 28 - 30 * _L.LOGO_RATIO, 60, 30 * _L.LOGO_RATIO, 30, _L.LOGO, locked=True)
    b.text(PAD + 28, 100, 1096, 46, f["title"], size=30, bold=True, color=b.dco, lineHeight=1.3, role="title")
    if f.get("sub"):
        b.text(PAD + 28, 148, 1096, 28, f["sub"], size=17, color=b.dco, lineHeight=1.5)
    cols = f["columns"]
    n = len(cols)
    gap = 20
    cw = (1152 - (n - 1) * gap) / n
    y, ch = 210, f.get("colH", 248)
    for i, c in enumerate(cols):
        x = PAD + i * (cw + gap)
        b.rect(x, y, cw, ch, "surface-container", "r-m")
        b.text(x + 22, y + 18, cw - 44, 30, c["title"], size=19, bold=True, color=b.dc, lineHeight=1.5)
        b.text(x + 22, y + 58, cw - 44, ch - 74, c["body"], size=16, lineHeight=1.6)
    y += ch + 18
    b.rect(PAD, y, 1152, 112, "primary-container", "r-m")
    b.pill(PAD + 20, y + 16, "결정할 것", "primary", "on-primary", size=15, h=30)
    b.text(PAD + 150, y + 14, 1150 - 170, 34, f["ask"], size=21, bold=True, color="on-primary-container", lineHeight=1.5)
    meta = "   ·   ".join(x for x in (f.get("owner") and f"**누가** {f['owner']}", f.get("due") and f"**언제까지** {f['due']}",
                                      f.get("impact") and f"**미결정 시** {f['impact']}") if x)
    b.text(PAD + 150, y + 58, 1150 - 170, 40, meta, size=16, color="on-primary-container", lineHeight=1.5)
    b.foot(f.get("crumb", ""))


def milestones(b, f):
    """마일스톤 - items: {date, title, desc?, status?}, now(0~1 위치 또는 items 사이 순번 + 0.5 등), 위치 at(0~1, 없으면 고르게)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    its = f["items"]
    n = len(its)
    x0, x1, ly = PAD + 60, RIGHT - 60, f.get("lineY", 360)
    b.rect(x0 - 40, ly - 3, x1 - x0 + 80, 6, "surface-container-high", "r-full")
    pos = lambda i, it: x0 + (x1 - x0) * (it["at"] if "at" in it else (i / (n - 1) if n > 1 else 0.5))
    if f.get("now") is not None:
        nx = x0 + (x1 - x0) * f["now"]
        b.rect(x0 - 40, ly - 3, nx - x0 + 40, 6, b.dc, "r-full")
        b.arrow(nx, 220, nx, 540, "primary", width=2, head="none", dash="dash")
        b.pill(nx - 34, 196, "NOW", "primary", "on-primary", size=15, h=28, w=68)
    slot = (x1 - x0) / max(n - 1, 1)
    w = min(220, slot - 12) if n > 1 else 300
    for i, it in enumerate(its):
        cx = pos(i, it)
        st = it.get("status")
        col = st or b.dc
        b.ellipse(cx - 13, ly - 13, 26, col if st else "white", stroke=col, strokeWidth=3)
        up = i % 2 == 0
        p = b.pill(cx - 60, ly - 70 if up else ly + 30, it["date"], col if st else b.dcc, "white" if st else b.dco,
                   size=15, h=30, w=120)
        ty = ly - 190 if up else ly + 74
        b.text(cx - w / 2, ty if not up else ty, w, 32, it["title"], size=18, bold=True, lineHeight=1.4, align="center")
        if it.get("desc"):
            b.text(cx - w / 2, ty + 34, w, 76, it["desc"], size=15, lineHeight=1.5, align="center", color="on-surface-variant")
    bottom_extras(b, f, 600)
    b.foot(f.get("crumb", ""))


def roadmap(b, f):
    """로드맵 열 - columns: {label, sub?, tone?, items: [{title, desc?, status?}]} (보통 Now / Next / Later 3열)."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    cols = f["columns"]
    n = len(cols)
    gap = 24
    cw = (1152 - (n - 1) * gap) / n
    top, bottom = 184, (568 if f.get("action") else 640)
    for i, c in enumerate(cols):
        x = PAD + i * (cw + gap)
        tone = c.get("tone", ["day1", "day2", "day3", "apx"][i % 4])
        b.rect(x, top, cw, bottom - top, f"{tone}-container", "r-l")
        b.text(x + 22, top + 18, cw - 44, 34, c["label"], size=22, bold=True, color=tone, lineHeight=1.5)
        if c.get("sub"):
            b.text(x + 22, top + 54, cw - 44, 24, c["sub"], size=15, color=f"on-{tone}-container" if tone != "apx" else "on-surface-variant", lineHeight=1.5)
        y = top + 90
        ih = min(110, (bottom - y - 16 - 10 * (len(c["items"]) - 1)) / max(len(c["items"]), 1))
        for it in c["items"]:
            b.rect(x + 14, y, cw - 28, ih, "white", "r-m")
            b.text(x + 30, y + 10, cw - 60 - (84 if it.get("status") else 0), 28, it["title"], size=17, bold=True, lineHeight=1.5)
            if it.get("status"):
                p = status_chip(b, 0, y + 10, it["status"], it.get("statusLabel"))
                p["x"] = round(x + cw - 28 - p["w"])
            if it.get("desc") and ih > 60:
                b.text(x + 30, y + 42, cw - 60, ih - 50, it["desc"], size=15, lineHeight=1.5, color="on-surface-variant")
            y += ih + 10
    bottom_extras(b, f, bottom + 14)
    b.foot(f.get("crumb", ""))


def gantt(b, f):
    """간트 - periods(열 이름: 주·월), rows: {task, owner?, bars: [[시작, 끝(포함), 상태·톤?, 글?]], gate?},
    gates: [[열 위치, 이름]](세로 점선), now(열 위치 실수, 예 3.5), legend(선택). 10행 이내."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    per, rows = f["periods"], f["rows"]
    lw = f.get("labelW", 260)
    x0, top = PAD + lw, 184
    gw = (1152 - lw) / len(per)
    bottom = 600 if f.get("footnote") or f.get("action") else 636
    rh = min(52, (bottom - top - 40) / max(len(rows), 1))
    if len(rows) > 10:
        print(f"  ! gantt {len(rows)}행 - 10행 이내 권장")
    b.rect(PAD, top, 1152, 36, b.dcc, "r-s")
    b.text(PAD + 14, top + 4, lw - 20, 28, f.get("taskHead", "작업 · 담당"), size=15, bold=True, color=b.dco, lineHeight=1.5, valign="middle")
    for j, p in enumerate(per):
        b.text(x0 + j * gw, top + 4, gw, 28, p, size=15, bold=True, color=b.dco, lineHeight=1.5, align="center", valign="middle")
    gy = top + 36
    gh = rh * len(rows)
    for j in range(len(per) + 1):
        b.rect(x0 + j * gw, gy, 1, gh, "surface-container-high")
    for i, r in enumerate(rows):
        y = gy + i * rh
        if i % 2 == 1:
            b.rect(PAD, y, 1152, rh, "surface-dim", 0)
        label = r["task"] + (f"\n{r['owner']}" if r.get("owner") and rh >= 44 else "")
        b.text(PAD + 14, y + 2, lw - 20, rh - 4, label, size=15 if "\n" in label else 16, bold=False, lineHeight=1.3, valign="middle")
        for bar in r.get("bars", []):
            s, e = bar[0], bar[1]
            tone = bar[2] if len(bar) > 2 and bar[2] else b.dc
            txt = bar[3] if len(bar) > 3 else ""
            fill = tone if tone in ("ok", "caution", "bad", "info", "idle") or not tone.endswith("-container") else tone
            bx = x0 + s * gw + 3
            b.rect(bx, y + rh * 0.22, (e - s + 1) * gw - 6, rh * 0.56, fill, "r-s",
                   **({"text": txt, "size": 15, "bold": True, "color": "white", "align": "center", "valign": "middle"} if txt else {}))
        b.rect(PAD, y + rh - 1, 1152, 1, "surface-container-high")
    for pos, name in f.get("gates", []):
        gx = x0 + pos * gw
        b.arrow(gx, gy - 6, gx, gy + gh, "on-surface-variant", width=2, head="none", dash="dash")
        lab = f"◆ {name}"
        lw_ = text_width(lab, 15, True) + 8
        if gx + 4 + lw_ > RIGHT:  # 오른쪽 끝: 선 왼쪽에 붙인다
            b.text(gx - 4 - lw_, gy + gh + 4, lw_, 22, lab, size=15, bold=True, color="on-surface-variant", lineHeight=1.4, align="right")
        else:
            b.text(gx + 4, gy + gh + 4, lw_, 22, lab, size=15, bold=True, color="on-surface-variant", lineHeight=1.4)
    if f.get("now") is not None:  # NOW 선 + 아래 이름표(머리글을 가리지 않게)
        nx = x0 + f["now"] * gw
        b.arrow(nx, gy - 6, nx, gy + gh + 4, "primary", width=2, head="none")
        b.pill(nx - 30, gy + gh + 2, "NOW", "primary", "on-primary", size=15, h=26, w=60)
    bottom_extras(b, f, gy + gh + 30)
    b.foot(f.get("crumb", ""))


def week_grid(b, f):
    """시간표 - days(열), slots(행 이름: 시간), sessions: {day, slot, span?(행 수), days?(열 수), title, sub?, tone?}."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    days, slots = f["days"], f["slots"]
    lw = f.get("slotW", 120)
    x0, top = PAD + lw, 184
    cw = (1152 - lw) / len(days)
    bottom = 600 if f.get("footnote") or f.get("action") else 640
    rh = min(64, (bottom - top - 40) / len(slots))
    for j, d in enumerate(days):
        b.rect(x0 + j * cw + 2, top, cw - 4, 36, b.dcc, "r-s")
        b.text(x0 + j * cw, top + 4, cw, 28, d, size=16, bold=True, color=b.dco, lineHeight=1.5, align="center", valign="middle")
    gy = top + 40
    for i, s in enumerate(slots):
        y = gy + i * rh
        b.text(PAD, y + 2, lw - 12, 26, s, size=15, color="on-surface-variant", lineHeight=1.5)
        b.rect(x0, y, cw * len(days), 1, "surface-container-high")
    b.rect(x0, gy + rh * len(slots), cw * len(days), 1, "surface-container-high")
    for se in f.get("sessions", []):
        tone = se.get("tone", "day1")
        x = x0 + se["day"] * cw + 4
        y = gy + se["slot"] * rh + 3
        w = se.get("days", 1) * cw - 8
        h = se.get("span", 1) * rh - 6
        b.rect(x, y, w, h, f"{tone}-container", "r-s")
        b.rect(x, y, 5, h, tone, "r-s")
        txt = se["title"] + (f"\n{se['sub']}" if se.get("sub") and h >= 50 else "")
        b.text(x + 12, y + 4, w - 18, h - 8, txt, size=15, bold=False, lineHeight=1.35, valign="middle",
               color=f"on-{tone}-container" if tone in ("day1", "day2", "day3", "lab", "primary") else "on-surface")
    bottom_extras(b, f, gy + rh * len(slots) + 12)
    b.foot(f.get("crumb", ""))


def photo_text(b, f):
    """사진 + 글 - img(작업 공간 그림 경로, 없으면 자리 표시), imgSide(left/right), kicker, title, body, items, action."""
    left = f.get("imgSide", "left") == "left"
    iw, ih = 540, 560
    ix = 40 if left else W - 40 - iw
    if f.get("img"):
        b.image(ix, 80, iw, ih, f["img"])
    else:
        b.rect(ix, 80, iw, ih, "surface-container-high", "r-l", text=f.get("imgHint", "사진 자리\n(img 필드에 경로)"), size=18,
               color="on-surface-variant", align="center", valign="middle")
    tx = ix + iw + 56 if left else PAD
    tw = W - PAD - tx if left else ix - 56 - PAD
    y = 110
    if f.get("kicker"):
        b.pill(tx, y, f["kicker"], b.dcc, b.dco, size=15)
        y += 50
    b.text(tx, y, tw, 100, f["title"], size=34, bold=True, lineHeight=1.3, font="heading", role="title")
    y += 116
    if f.get("body"):
        b.text(tx, y, tw, 120, f["body"], size=18, lineHeight=1.7, color="on-surface-variant")
        y += 130
    for it in f.get("items", []):
        b.text(tx, y, tw, 30, f"·  {it}", size=17, lineHeight=1.6)
        y += 34
    if not left:
        pass
    b.logo() if not left else None
    if f.get("action"):
        b.text(tx, 560, tw, 60, f"**{f.get('actionLabel', '부탁')}**  {f['action']}", size=17, lineHeight=1.5,
               fill="primary-container", color="on-primary-container", radius="r-m", pad=[12, 16, 12, 16], valign="middle")
    b.foot(f.get("crumb", ""))


def agenda(b, f):
    """진행 순서 - items: [번호·제목·시간·담당] 또는 {title, time?, owner?, desc?}. 현재 항목 current(0부터)."""
    b.head(f.get("title", "진행 순서"), f.get("sub"), f.get("kick"))
    its = [it if isinstance(it, dict) else {"title": it} for it in f["items"]]
    n = len(its)
    rh = min(72, (600 - 184) / max(n, 1))
    for i, it in enumerate(its):
        y = 184 + i * rh
        cur = f.get("current") == i
        b.rect(PAD, y, 1152, rh - 10, b.dcc if cur else "surface-container", "r-m")
        b.ellipse(PAD + 18, y + (rh - 10 - 36) / 2, 36, b.dc, text=str(i + 1), size=17, bold=True, color="white")
        b.text(PAD + 72, y + (rh - 10 - 30) / 2, 640, 30, it["title"], size=19, bold=True, lineHeight=1.5, valign="middle")
        if it.get("desc"):
            b.text(PAD + 72 + 330, y + (rh - 10 - 26) / 2, 420, 26, it["desc"], size=15, color="on-surface-variant", lineHeight=1.5, valign="middle")
        meta = "  ·  ".join(x for x in (it.get("time"), it.get("owner")) if x)
        if meta:
            b.text(RIGHT - 300, y + (rh - 10 - 26) / 2, 280, 26, meta, size=16, color="on-surface-variant", lineHeight=1.5,
                   align="right", valign="middle")
    bottom_extras(b, f, 184 + n * rh + 6)
    b.foot(f.get("crumb", ""))


def _nice_max(v):
    import math
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= v:
            return m * e
    return 10 * e


def _fmt(v):
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}"


def draw_columns(b, x, y, w, h, p, unit="", ymax=None):
    """세로 막대 한 판 - p: {label?, categories, values, mode(plain·cumulative·waterfall), highlight[], note?, line?}.
    cumulative: 앞까지의 누적(회색) 위에 이번 증가분(색) - 한 단계에 갑자기 솟는 "절벽"이 보인다. waterfall: 회색 없이 떠 있는 증가분."""
    cats, vals = p["categories"], p["values"]
    mode = p.get("mode", "plain")
    cum = []
    s = 0
    for v in vals:
        s += v
        cum.append(s)
    tops = cum if mode in ("cumulative", "waterfall") else vals
    ymax = ymax or _nice_max(max(tops))
    if p.get("label"):
        b.text(x, y, w, 30, p["label"], size=18, bold=True, lineHeight=1.5, color=p.get("labelColor", "on-surface"))
        y += 38
        h -= 38
    lw = 56  # 값 축 글자 폭
    cx0, cy0, cw, ch = x + lw, y + 24, w - lw, h - 24 - 50
    nt = 4 if ch >= 140 else 2  # 눈금 칸 수 - 작은 판은 2칸(눈금 글자가 겹치지 않게)
    for k in range(nt + 1):
        gy = cy0 + ch - ch * k / nt
        b.rect(cx0, gy, cw, 1, "surface-container-high")
        b.text(x, gy - 10, lw - 8, 20, _fmt(ymax * k / nt), size=15, color="on-surface-variant", lineHeight=1.2, align="right")
    n = len(cats)
    slot = cw / n
    bw = min(64, slot * 0.6)
    hi = set(p.get("highlight", []))
    totals = set(p.get("totals", []))  # 합계 막대(워터폴 끝): 그때까지의 누적을 바닥부터
    pts = []
    for i, (c, v) in enumerate(zip(cats, vals)):
        bx = cx0 + slot * i + (slot - bw) / 2
        top = tops[i]
        base = cum[i] - v if mode in ("cumulative", "waterfall") else 0
        if i in totals:
            top, base, v = cum[i], 0, cum[i]
        ty = cy0 + ch - ch * top / ymax
        by = cy0 + ch - ch * base / ymax
        if mode == "cumulative" and base > 0:
            b.rect(bx, by, bw, cy0 + ch - by, "outline-variant", 0)
        col = "bad" if i in hi else ("on-surface-variant" if i in totals else p.get("tone", b.dc))
        b.rect(bx, ty, bw, max(2, by - ty), col, 0)
        lab = (f"+{_fmt(v)}" if mode != "plain" and i not in totals else _fmt(v)) + unit
        b.text(bx - 30, ty - 26, bw + 60, 22, lab, size=15, bold=i in hi, color="bad" if i in hi else "on-surface",
               lineHeight=1.4, align="center")
        b.text(cx0 + slot * i, cy0 + ch + 8, slot, 44, c, size=15, lineHeight=1.35, align="center",
               color="on-surface-variant")
        pts.append((bx + bw / 2, ty))
    b.rect(cx0, cy0 + ch, cw, 2, "on-surface-variant")
    if p.get("line") and len(pts) > 1:
        lx, ly = min(q[0] for q in pts), min(q[1] for q in pts)
        lw2, lh2 = max(q[0] for q in pts) - lx, max(q[1] for q in pts) - ly
        b.add({"type": "curve", "x": round(lx), "y": round(ly), "w": round(max(lw2, 1)), "h": round(max(lh2, 1)),
               "points": [[round(q[0] - lx, 1), round(q[1] - ly, 1)] for q in pts], "color": "on-surface-variant",
               "width": 2, "head": "none", "dash": "dash"})
    if p.get("note"):
        b.text(x, y + h - 2, w, 26, p["note"], size=15, bold=True, color=p.get("noteColor", "on-surface"), lineHeight=1.5,
               align="center")


def draw_stack(b, x, y, w, rows, unit="", vmax=None, bar_h=26, label_w=96, size=15):
    """가로 누적 막대 묶음(작은 판) - rows: {label, segments: [[이름, 값, 톤?]]}. 구간 이름은 넉넉할 때만 막대 안에."""
    tones = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
    vmax = vmax or _nice_max(max(sum(s[1] for s in r["segments"]) for r in rows))
    aw = w - label_w - 64
    for i, r in enumerate(rows):
        yy = y + i * (bar_h + 18)
        b.text(x, yy + (bar_h - 22) / 2, label_w - 8, 22, r["label"], size=size, bold=True, lineHeight=1.4)
        xx = x + label_w
        tot = 0
        for j, seg in enumerate(r["segments"]):
            name, v = seg[0], seg[1]
            tone = seg[2] if len(seg) > 2 and seg[2] else tones[j % 7]
            sw_ = aw * v / vmax
            kw = {"text": name, "size": size, "bold": True, "color": "white", "align": "center", "valign": "middle"} \
                if sw_ >= text_width(name, size, True) + 10 else {}
            b.rect(xx, yy, max(sw_ - 2, 2), bar_h, tone, 0, **kw)
            xx += sw_
            tot += v
        b.text(xx + 6, yy + (bar_h - 22) / 2, 60, 22, f"{_fmt(tot)}{unit}", size=size, bold=True, lineHeight=1.4)
    return len(rows) * (bar_h + 18)


def draw_aside(b, items, x, y, w, h):
    """오른쪽 작은 그림 묶음 - items: {kind: columns|stack, title, …}. 개념만 보이는 작은 크기(제목 + 그림 + 한 줄)."""
    n = len(items)
    gap = 16
    ih = (h - (n - 1) * gap) / n
    for i, it in enumerate(items):
        yy = y + i * (ih + gap)
        b.rect(x, yy, w, ih, "surface-container", "r-m")
        b.text(x + 16, yy + 10, w - 32, 24, it.get("title", ""), size=15, bold=True, lineHeight=1.5,
               color=it.get("titleColor", "on-surface"))
        if it["kind"] == "columns":
            draw_columns(b, x + 8, yy + 34, w - 24, ih - 40 - (24 if it.get("note") else 0),
                         {k: it[k] for k in ("categories", "values", "mode", "highlight", "line") if k in it}, it.get("unit", ""))
        elif it["kind"] == "stack":
            used = draw_stack(b, x + 16, yy + 48, w - 32, it["rows"], it.get("unit", ""), label_w=it.get("labelW", 64))
            lx, ly = x + 16, yy + 48 + used  # 범례: 막대 안에 이름이 안 들어가는 구간
            for name, tone in it.get("legend", []):
                tw = text_width(name, 15) + 6
                if lx + 22 + tw > x + w - 12:
                    lx, ly = x + 16, ly + 26
                b.rect(lx, ly + 5, 14, 14, tone, "r-s")
                b.text(lx + 18, ly, tw, 24, name, size=15, lineHeight=1.5, color="on-surface-variant")
                lx += 18 + tw + 12
        if it.get("note"):
            b.text(x + 16, yy + ih - 30, w - 32, 22, it["note"], size=15, color=it.get("noteColor", "on-surface-variant"),
                   lineHeight=1.4)


def column_chart(b, f):
    """세로 막대 차트 - 판 하나(categories·values·mode·highlight) 또는 panels(판 여러 개 나란히, 같은 눈금).
    unit(값 뒤 단위), side(오른쪽 해설, 선택), footnote, action. 막대 12개 이내."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    panels = f.get("panels") or [{k: f[k] for k in ("categories", "values", "mode", "highlight", "line", "label", "note", "totals") if k in f}]

    def peak(p):
        s, m = 0, 0
        for v in p["values"]:
            s += v
            m = max(m, s if p.get("mode", "plain") != "plain" else v)
        return m
    ymax = _nice_max(max(peak(p) for p in panels))
    side = f.get("side")
    sw = f.get("sideW", 320) if side else 0
    top, bottom = 180, (560 if f.get("footnote") or f.get("action") else 640)
    aw = 1152 - (sw + 24 if side else 0)
    gap = 40
    pw = (aw - (len(panels) - 1) * gap) / len(panels)
    for i, p in enumerate(panels):
        draw_columns(b, PAD + i * (pw + gap), top, pw, bottom - top, p, f.get("unit", ""), ymax)
    if side:
        b.text(RIGHT - sw, top, sw, bottom - top, side, size=16, lineHeight=1.7, fill="surface-container", radius="r-m",
               pad=[18, 20, 18, 20])
    bottom_extras(b, f, bottom + 12)
    b.foot(f.get("crumb", ""))


def stack_bars(b, f):
    """가로 누적 막대 - rows: {label, sub?, segments: [[이름, 값, 톤?], …]}, unit, max(선택). 구간 이름은 막대 안(좁으면 생략),
    합계는 막대 끝. side(오른쪽 해설)·footnote·action."""
    b.head(f["title"], f.get("sub"), f.get("kick"))
    rows = f["rows"]
    unit = f.get("unit", "")
    side = f.get("side")
    sw = f.get("sideW", 300) if side else 0
    lw = f.get("labelW", 230)
    x0 = PAD + lw
    aw = 1152 - lw - (sw + 24 if side else 0) - 90
    vmax = f.get("max") or _nice_max(max(sum(s[1] for s in r["segments"]) for r in rows))
    top = 190
    rh = f.get("rowH", 96)
    tones = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
    for i, r in enumerate(rows):
        y = top + i * rh
        b.text(PAD, y, lw - 16, 30, r["label"], size=18, bold=True, lineHeight=1.5)
        if r.get("sub"):
            b.text(PAD, y + 32, lw - 16, 44, r["sub"], size=15, color="on-surface-variant", lineHeight=1.4)
        x = x0
        tot = 0
        for j, seg in enumerate(r["segments"]):
            name, v = seg[0], seg[1]
            tone = seg[2] if len(seg) > 2 and seg[2] else tones[j % 7]
            sw_ = aw * v / vmax
            kw = {}
            if sw_ >= text_width(name, 15, True) + 12:
                kw = {"text": name, "size": 15, "bold": True, "color": "white", "align": "center", "valign": "middle"}
            b.rect(x, y + 4, max(sw_ - 2, 2), 40, tone, 0, **kw)
            x += sw_
            tot += v
        b.text(x + 10, y + 10, 120, 28, f"{_fmt(tot)}{unit}", size=18, bold=True, lineHeight=1.5,
               color=r.get("totalColor", "on-surface"))
    if f.get("legend"):  # [[이름, 톤], …]
        lx, ly = x0, top + len(rows) * rh + 4
        for name, tone in f["legend"]:
            b.rect(lx, ly + 6, 16, 16, tone, "r-s")
            tw = text_width(name, 15) + 8
            b.text(lx + 22, ly, tw, 26, name, size=15, lineHeight=1.6, color="on-surface-variant")
            lx += 22 + tw + 18
    if side:
        b.text(RIGHT - sw, top - 10, sw, f.get("sideH", 360), side, size=16, lineHeight=1.7, fill="surface-container",
               radius="r-m", pad=[18, 20, 18, 20])
    bottom_extras(b, f, top + len(rows) * rh + 40)
    b.foot(f.get("crumb", ""))


EXTRA = {
    "column_chart": ("세로 막대 차트(누적·워터폴)", column_chart), "stack_bars": ("가로 누적 막대", stack_bars),
    "status_table": ("상태 표", status_table), "kpi_tiles": ("KPI 타일", kpi_tiles), "issue_cards": ("이슈 카드", issue_cards),
    "grid_cards": ("격자 카드(2×2·4열)", grid_cards), "statement": ("한 문장", statement), "quote": ("인용", quote),
    "big_number": ("큰 숫자", big_number), "decision_brief": ("결정 요청 1장", decision_brief),
    "milestones": ("마일스톤 타임라인", milestones), "roadmap": ("로드맵 열(Now·Next·Later)", roadmap),
    "gantt": ("간트", gantt), "week_grid": ("시간표(일자×시간)", week_grid), "photo_text": ("사진+글", photo_text),
    "agenda": ("진행 순서", agenda),
}

EXTRA_SAMPLES = {
    "column_chart": {"title": "결론형 제목 - 추이가 말하는 것", "categories": ["1월", "2월", "3월", "4월"], "values": [40, 52, 61, 75],
                     "unit": "건", "note": "한 줄 해석", "crumb": ""},
    "stack_bars": {"title": "구성 비교", "unit": "%", "rows": [{"label": "항목 A", "segments": [["가", 50], ["나", 30], ["다", 20]]},
                                                           {"label": "항목 B", "segments": [["가", 35], ["나", 40], ["다", 25]]}], "crumb": ""},
    "status_table": {"title": "결론형 제목 - 무엇이 어떤 상태인가", "header": ["항목", "계획", "실적", "상태", "담당"],
                     "colW": [4, 2, 2, 2, 2], "align": ["left", "right", "right", "center", "left"],
                     "rows": [["항목 A", "100", "96", {"status": "ok"}, "홍길동"], ["항목 B", "80", "62", {"status": "bad", "text": "지연"}, "김철수"],
                              {"cells": ["합계", "180", "158", {"status": "caution"}, ""], "total": True}],
                     "conclusion": "한 줄 결론", "crumb": ""},
    "kpi_tiles": {"title": "핵심 지표", "tiles": [{"label": "지표 1", "value": "96", "unit": "%", "target": "목표 95%", "delta": "+2%p 전주 대비", "status": "ok"},
                                              {"label": "지표 2", "value": "3", "unit": "건", "target": "목표 0건", "delta": "+1건", "status": "bad"}], "crumb": ""},
    "issue_cards": {"title": "이슈와 요청", "issues": [{"title": "이슈 제목", "status": "bad", "situation": "무슨 일인가", "impact": "무엇이 영향을 받나",
                                                    "ask": "무엇을 결정·지원해 달라", "owner": "담당", "due": "MM-DD"}], "crumb": ""},
    "grid_cards": {"title": "격자 카드", "cols": 2, "items": [{"num": 1, "title": "제목", "body": "내용"}, {"num": 2, "title": "제목", "body": "내용"},
                                                            {"num": 3, "title": "제목", "body": "내용"}, {"num": 4, "title": "제목", "body": "내용"}], "crumb": ""},
    "statement": {"text": "덱 전체를 꿰는 한 문장", "kicker": "핵심", "sub": "보조 설명", "crumb": ""},
    "quote": {"text": "인용 문장", "who": "이름", "role": "역할", "context": "언제·어디서", "crumb": ""},
    "big_number": {"title": "숫자 하나", "value": "42", "unit": "%", "label": "무엇의 숫자", "context": "의미", "compare": [["전년", "31%"]], "crumb": ""},
    "decision_brief": {"title": "결론 - 무엇을 하자", "sub": "근거 한 줄", "columns": [{"title": "근거 1", "body": "내용"}, {"title": "근거 2", "body": "내용"},
                                                                                 {"title": "근거 3", "body": "내용"}],
                       "ask": "결정할 것", "owner": "결정권자", "due": "MM-DD", "impact": "미결정 시 영향", "crumb": ""},
    "milestones": {"title": "마일스톤", "items": [{"date": "10-01", "title": "착수"}, {"date": "11-01", "title": "중간"}, {"date": "12-01", "title": "완료"}],
                   "now": 0.3, "crumb": ""},
    "roadmap": {"title": "로드맵", "columns": [{"label": "Now", "items": [{"title": "할 일"}]}, {"label": "Next", "items": [{"title": "할 일"}]},
                                             {"label": "Later", "items": [{"title": "할 일"}]}], "crumb": ""},
    "gantt": {"title": "일정", "periods": ["W1", "W2", "W3", "W4"], "rows": [{"task": "작업 1", "owner": "담당", "bars": [[0, 1]]},
                                                                       {"task": "작업 2", "bars": [[1, 3]]}], "now": 1.5, "crumb": ""},
    "week_grid": {"title": "시간표", "days": ["월", "화", "수"], "slots": ["09:00", "10:00", "11:00"],
                  "sessions": [{"day": 0, "slot": 0, "span": 2, "title": "세션"}], "crumb": ""},
    "photo_text": {"title": "사진과 글", "body": "설명", "items": ["항목"], "crumb": ""},
    "agenda": {"title": "진행 순서", "items": [{"title": "순서 1", "time": "10분", "owner": "담당"}], "crumb": ""},
}
