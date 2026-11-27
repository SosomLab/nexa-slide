# -*- coding: utf-8 -*-
"""페이지 문서(kind = "page") - 새 문서 · 형식 검사 · 정규화 · 스타일 풀기. 형식은 docs/dev/page-editor/design.md 3절.

    new_page(i, title, template=None)   새 문서(dict)
    validate(doc)                        형식이 맞으면 None, 아니면 이유(글)
    normalize(doc)                       사본을 정규화(runs 합치기 · 빠진 id 채우기 · 기본값)
    resolve_style(doc, name)             스타일 상속(based)을 풀어 한 벌로
    text_blocks(doc)                     글이 든 것(문단 · 목록 항목 · 표 셀 안 문단)을 차례로 - (경로, 블록)

글 조각(run)의 규칙은 화면 nexa-text.js 와 같다(MARKS · 꺼진 서식 키 없음 · 같은 서식의 이웃은 합침) - 같은 사례로 맞춘다.
"""
import copy
import datetime as dt
import re

MARKS = ("b", "i", "u", "s", "c", "hl", "sup", "sub", "font", "size", "link", "ruby", "fn")
BOOL = {"b", "i", "s", "sup", "sub"}
BLOCK_TYPES = ("p", "table", "image", "break")
LIST_KINDS = ("bullet", "number", "check")
# 개체(objects) - 본문 위에 떠 있는 도형·글 상자(PG-103). Word 와 같은 방식: 본문 문단 하나에 매이고(anchor = 그 문단 id),
#   자리는 그 문단이 놓인 쪽의 왼쪽 위(rel "page") 또는 그 문단의 왼쪽 위(rel "para")에서 잰 x·y(mm). 문단이 다른 쪽으로 가면 따라간다.
#   {id, type: "shape", shape, anchor, rel, x, y, w, h, fill?, line?: {c, w(pt), dash}|None, flip?(선이 오른쪽 위로), z?: "front"|"behind",
#    blocks?: 안의 글(문단들 - 선에는 없다), valign?: "top"|"middle"|"bottom", pad?(mm)}
OBJ_SHAPES = ("rect", "round", "ellipse", "line", "arrow", "bracket-l", "bracket-r", "brace-l", "brace-r")
OBJ_LINES = ("line", "arrow")
OBJ_DASH = ("solid", "dash", "dot")
SIZES = {"A4": (210, 297), "A5": (148, 210), "B5": (182, 257), "Letter": (215.9, 279.4), "Legal": (215.9, 355.6)}  # mm(세로 방향 기준)
ALIGN = ("left", "center", "right", "justify")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

DEFAULT_PAGE = {"size": "A4", "orient": "portrait", "margin": {"t": 25, "r": 20, "b": 25, "l": 20},
                "header": {"blocks": []}, "footer": {"blocks": []}, "first": None, "number": {"show": False, "pos": "footer-center"}}
DEFAULT_STYLES = {
    "body": {"name": "본문", "font": "body", "size": 10.5, "line": 1.6, "after": 6},
    "h1": {"name": "제목 1", "based": "body", "font": "title", "size": 20, "bold": True, "before": 12, "after": 8, "next": "body"},
    "h2": {"name": "제목 2", "based": "h1", "size": 15, "before": 10, "after": 6},
    "h3": {"name": "제목 3", "based": "h1", "size": 12, "before": 8, "after": 4},
    "title": {"name": "문서 제목", "based": "h1", "size": 26, "align": "center", "after": 14},
    "quote": {"name": "인용", "based": "body", "indent": 8, "color": "muted", "italic": True},
    "caption": {"name": "캡션", "based": "body", "size": 9, "color": "muted", "align": "center"},
}


def _on(v):
    return not (v is None or v is False or v == "" or v == 0)


def norm_runs(runs):
    """nexa-text.js normalize 와 같다 - 빈 조각을 버리고, 꺼진 서식 키를 빼고, 서식이 같은 이웃을 합친다."""
    out = []
    for r in runs or []:
        if not isinstance(r, dict) or not isinstance(r.get("t"), str) or not r["t"]:
            continue
        m = {k: (True if k in BOOL else r[k]) for k in MARKS if _on(r.get(k))}
        if out and {k: v for k, v in out[-1].items() if k != "t"} == m:
            out[-1]["t"] += r["t"]
        else:
            out.append({"t": r["t"], **m})
    return out


def runs_text(runs):
    return "".join(r.get("t", "") for r in runs or [])


def _ids(doc):
    seen = set()
    for _, b in walk(doc):
        if isinstance(b.get("id"), str):
            seen.add(b["id"])
    return seen


def _new_id(seen, prefix="b"):
    n = len(seen) + 1
    while f"{prefix}{n:02d}" in seen:
        n += 1
    seen.add(f"{prefix}{n:02d}")
    return f"{prefix}{n:02d}"


def walk(doc):
    """id 를 갖는 것 전부를 문서 순서로 - (경로, 객체). 블록 · 표의 행 · 셀 · 셀 안 블록 · 머리말·꼬리말 블록 · 개체와 그 안의 블록."""
    def blocks(bs, path):
        for b in bs or []:
            if not isinstance(b, dict):
                continue
            p = path + (b.get("id"),)
            yield p, b
            if b.get("type") == "table":
                for row in b.get("rows") or []:
                    if not isinstance(row, dict):
                        continue
                    yield p + (row.get("id"),), row
                    for c in row.get("cells") or []:
                        if isinstance(c, dict):
                            yield p + (row.get("id"), c.get("id")), c
                            yield from blocks(c.get("blocks"), p + (row.get("id"), c.get("id")))
    yield from blocks(doc.get("blocks"), ())
    page = doc.get("page") or {}
    for part in ("header", "footer"):
        yield from blocks((page.get(part) or {}).get("blocks"), (part,))
    for o in doc.get("objects") if isinstance(doc.get("objects"), list) else []:
        if isinstance(o, dict):
            yield ("objects", o.get("id")), o
            yield from blocks(o.get("blocks"), ("objects", o.get("id")))


def anchors(doc):
    """개체가 매일 수 있는 문단 = 본문 맨 위 단계의 문단 id 들(문서 순서)."""
    return [b["id"] for b in doc.get("blocks") or [] if isinstance(b, dict) and b.get("type") == "p" and isinstance(b.get("id"), str)]


def footnotes(doc):
    """각주를 문서 순서로 - [(번호(1부터), 각주 글)]. 본문(표 칸 포함)의 글 조각 fn 만 센다(머리말·꼬리말·개체 안은 Word 가 각주를 받지 않는다)."""
    out = []
    for path, b in walk(doc):
        if path and path[0] in ("header", "footer", "objects"):
            continue
        for r in b.get("runs") or [] if isinstance(b.get("runs"), list) else []:
            if isinstance(r, dict) and r.get("fn"):
                out.append((len(out) + 1, r["fn"]))
    return out


def text_blocks(doc):
    """글(runs)이 든 것만 - 문단(목록 문단 포함) · 셀 안 문단."""
    for p, b in walk(doc):
        if isinstance(b.get("runs"), list):
            yield p, b


def new_page(i, title, template=None):
    """새 페이지 문서. template = 템플릿 dict(page · styles · blocks 를 덮어쓴다)."""
    t = template or {}
    doc = {"id": i, "title": title or i, "kind": "page", "version": 1,
           "updated": dt.datetime.now().isoformat(timespec="seconds"), "slides": [],
           "page": {**copy.deepcopy(DEFAULT_PAGE), **copy.deepcopy(t.get("page") or {})},
           "styles": {**copy.deepcopy(DEFAULT_STYLES), **copy.deepcopy(t.get("styles") or {})},
           "blocks": copy.deepcopy(t.get("blocks")) or [{"id": "b01", "type": "p", "style": "title", "runs": [{"t": title}] if title else []},
                                                         {"id": "b02", "type": "p", "runs": []}],
           "objects": []}
    if t.get("name"):
        doc["template"] = t["name"]
    return normalize(doc)


def normalize(doc):
    """사본을 정규화 - runs 합치기 · 빠진 id 채우기 · page·styles 기본값. 형식이 틀린 것은 고치지 않는다(validate 가 알린다)."""
    d = copy.deepcopy(doc)
    d.setdefault("kind", "page")
    d.setdefault("slides", [])
    d["page"] = {**copy.deepcopy(DEFAULT_PAGE), **(d.get("page") if isinstance(d.get("page"), dict) else {})}
    if not isinstance(d.get("styles"), dict) or not d["styles"]:
        d["styles"] = copy.deepcopy(DEFAULT_STYLES)
    if "body" not in d["styles"]:
        d["styles"]["body"] = copy.deepcopy(DEFAULT_STYLES["body"])
    if not isinstance(d.get("blocks"), list):
        d["blocks"] = []
    if not isinstance(d.get("objects"), list):
        d["objects"] = []
    seen = _ids(d)
    for _, b in walk(d):
        if not isinstance(b.get("id"), str) or not b["id"]:
            b["id"] = _new_id(seen)
        if isinstance(b.get("runs"), list):
            b["runs"] = norm_runs(b["runs"])
    if not d["blocks"]:  # 빈 문서도 칠 자리는 하나 있다
        d["blocks"] = [{"id": _new_id(seen), "type": "p", "runs": []}]
    # 매인 문단이 지워진 개체 - 버리지 않고 첫 문단에 다시 맨다(문단이 하나도 없으면 그대로 두고 validate 가 알린다)
    ok = anchors(d)
    for o in d["objects"]:
        if isinstance(o, dict) and ok and o.get("anchor") not in ok:
            o["anchor"] = ok[0]
    return d


def _check_runs(runs, where):
    if not isinstance(runs, list):
        return f"{where}: runs 는 목록"
    for r in runs:
        if not isinstance(r, dict) or not isinstance(r.get("t"), str):
            return f"{where}: 글 조각은 {{t: 글, …}}"
        for k in r:
            if k != "t" and k not in MARKS:
                return f"{where}: 모르는 서식 {k}"
        if "fn" in r and (not isinstance(r["fn"], str) or not r["fn"].strip() or len(r["fn"]) > 2000):
            return f"{where}: 각주(fn)는 글(1~2000자)"
    return None


def _check_columns(c, where):
    """단 설정 {count 1~4, gap(mm 0~50)?} - 문서(page.columns)와 구역 나누기(break kind section 의 columns)가 같이 쓴다."""
    if not isinstance(c, dict) or not isinstance(c.get("count"), int) or isinstance(c.get("count"), bool) or not 1 <= c["count"] <= 4:
        return f"{where}: columns = {{count: 1~4, gap?: mm}}"
    if "gap" in c and (not isinstance(c["gap"], (int, float)) or isinstance(c["gap"], bool) or not 0 <= c["gap"] <= 50):
        return f"{where}: 단 간격 gap 은 mm(0~50)"
    return None


def columns_of(doc):
    """구역별 단 설정 - [(시작 블록 색인, {count, gap})]. 첫 구역 = page.columns(없으면 1단), 구역 나누기 블록 뒤부터 그 블록의 columns."""
    page = doc.get("page") or {}
    norm = lambda c: {"count": c.get("count", 1) if isinstance(c, dict) else 1, "gap": c.get("gap", 8) if isinstance(c, dict) else 8}  # noqa: E731
    out = [(0, norm(page.get("columns")))]
    for k, b in enumerate(doc.get("blocks") or []):
        if isinstance(b, dict) and b.get("type") == "break" and b.get("kind") == "section":
            out.append((k + 1, norm(b.get("columns"))))
    return out


def _check_blocks(bs, where, styles, depth=0):
    if not isinstance(bs, list):
        return f"{where}: blocks 는 목록"
    for b in bs:
        if not isinstance(b, dict):
            return f"{where}: 블록은 객체"
        w = f"{where} {b.get('id')}"
        if b.get("type") not in BLOCK_TYPES:
            return f"{w}: 모르는 블록 종류 {b.get('type')}"
        if "style" in b and b["style"] not in styles:
            return f"{w}: 없는 스타일 {b['style']}"
        if "align" in b and b["align"] not in ALIGN:
            return f"{w}: align = {' | '.join(ALIGN)}"
        t = b["type"]
        if t == "p":
            e = _check_runs(b.get("runs"), w)
            if e:
                return e
            if "list" in b:  # 목록은 문단의 속성이다(Word 의 번호 매기기와 같다) - 이어진 목록 문단이 한 목록
                ls = b["list"]
                if not isinstance(ls, dict) or ls.get("kind") not in LIST_KINDS:
                    return f"{w}: 목록 kind = {' | '.join(LIST_KINDS)}"
                if not isinstance(ls.get("level", 0), int) or isinstance(ls.get("level", 0), bool) or not 0 <= ls.get("level", 0) <= 8:
                    return f"{w}: 목록 level 은 0~8"
        elif t == "table":
            if depth:
                return f"{w}: 표 안의 표는 지원하지 않는다"
            cols, rows = b.get("cols"), b.get("rows")
            if not isinstance(cols, list) or not cols or any(not isinstance(c, (int, float)) or c <= 0 for c in cols):
                return f"{w}: cols 는 양수 너비 목록"
            if not isinstance(rows, list) or not rows:
                return f"{w}: rows 는 비지 않은 목록"
            if b.get("border", "all") not in ("all", "none", "inner-v"):
                return f"{w}: 표 border = all | none | inner-v"
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("cells"), list):
                    return f"{w}: 행은 {{id, cells}}"
                span = 0
                for c in row["cells"]:
                    if not isinstance(c, dict):
                        return f"{w}: 셀은 객체"
                    cs, rs = c.get("colspan", 1), c.get("rowspan", 1)
                    if not isinstance(cs, int) or not isinstance(rs, int) or cs < 1 or rs < 1:
                        return f"{w}: colspan·rowspan 은 1 이상의 정수"
                    span += cs
                    e = _check_blocks(c.get("blocks", []), w, styles, depth + 1)
                    if e:
                        return e
                if span > len(cols):
                    return f"{w}: 행의 칸 수({span})가 열 수({len(cols)})를 넘는다"
        elif t == "image":
            if not isinstance(b.get("src"), str) or not b["src"]:
                return f"{w}: 그림은 src 필요"
        elif t == "break":
            if b.get("kind", "page") not in ("page", "column", "section"):
                return f"{w}: 나누기 kind = page | column | section"
            if "columns" in b:
                e = _check_columns(b["columns"], w)
                if e or b.get("kind") != "section":
                    return e or f"{w}: columns 는 구역 나누기(kind section)에만"
    return None


def _check_objects(objs, anchor_ids, styles):
    if objs is None:
        return None
    if not isinstance(objs, list):
        return "objects 는 목록"
    num = lambda v, lo, hi: isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi  # noqa: E731
    for o in objs:
        if not isinstance(o, dict):
            return "개체는 객체"
        w = f"개체 {o.get('id')}"
        if o.get("type") != "shape":
            return f"{w}: 모르는 개체 종류 {o.get('type')}"
        if o.get("shape") not in OBJ_SHAPES:
            return f"{w}: shape = {' | '.join(OBJ_SHAPES)}"
        if o.get("anchor") not in anchor_ids:
            return f"{w}: anchor 는 본문 문단의 id"
        if o.get("rel", "page") not in ("page", "para"):
            return f"{w}: rel = page | para"
        if not num(o.get("x"), -1000, 2000) or not num(o.get("y"), -1000, 2000):
            return f"{w}: x·y(mm)"
        if not num(o.get("w"), 0, 2000) or not num(o.get("h"), 0, 2000) or (o["w"] == 0 and o["h"] == 0):
            return f"{w}: w·h(mm, 둘 다 0 은 안 됨)"
        if o.get("fill") is not None and not isinstance(o["fill"], str):
            return f"{w}: fill 은 색(글)"
        ln = o.get("line")
        if ln is not None and (not isinstance(ln, dict) or ("c" in ln and not isinstance(ln["c"], str)) or ("w" in ln and not num(ln["w"], 0, 20)) or ln.get("dash", "solid") not in OBJ_DASH):
            return f"{w}: line = {{c, w(pt 0~20), dash: {' | '.join(OBJ_DASH)}}}"
        if o.get("z", "front") not in ("front", "behind"):
            return f"{w}: z = front | behind"
        if o.get("valign", "top") not in ("top", "middle", "bottom"):
            return f"{w}: valign = top | middle | bottom"
        if "pad" in o and not num(o["pad"], 0, 50):
            return f"{w}: pad(mm 0~50)"
        if "blocks" in o:
            if o["shape"] in OBJ_LINES:
                return f"{w}: 선에는 글을 넣을 수 없다"
            e = _check_blocks(o["blocks"], w, styles, 1)
            if e:
                return e
    return None


def validate(doc):
    """형식이 맞으면 None, 아니면 첫 문제(글). 서버 저장·save_deck 검사가 쓴다."""
    if not isinstance(doc, dict) or doc.get("kind") != "page":
        return "페이지 문서 아님(kind = page)"
    page = doc.get("page")
    if not isinstance(page, dict):
        return "page(쪽 설정) 필요"
    size = page.get("size")
    if not (size in SIZES or (isinstance(size, dict) and all(isinstance(size.get(k), (int, float)) and 50 <= size[k] <= 2000 for k in ("w", "h")))):
        return f"용지 크기 = {' | '.join(SIZES)} 또는 {{w, h}}(mm)"
    if page.get("orient") not in ("portrait", "landscape"):
        return "방향 = portrait | landscape"
    m = page.get("margin")
    if not isinstance(m, dict) or any(not isinstance(m.get(k), (int, float)) or not 0 <= m[k] <= 150 for k in "trbl"):
        return "여백은 t·r·b·l(mm, 0~150)"
    if page.get("columns") is not None:
        e = _check_columns(page["columns"], "page")
        if e:
            return e
    styles = doc.get("styles")
    if not isinstance(styles, dict) or "body" not in styles:
        return "styles 에 body 필요"
    for name, st in styles.items():
        if not ID_RE.match(str(name)) or not isinstance(st, dict):
            return f"스타일 이름·형식: {name}"
        seen, cur = {name}, st
        while cur.get("based"):
            if cur["based"] not in styles:
                return f"스타일 {name}: 없는 기준 스타일 {cur['based']}"
            if cur["based"] in seen:
                return f"스타일 {name}: 기준 스타일이 돈다"
            seen.add(cur["based"])
            cur = styles[cur["based"]]
    e = _check_blocks(doc.get("blocks"), "본문", styles)
    if e:
        return e
    for part in ("header", "footer"):
        hb = page.get(part)
        if hb is not None:
            if not isinstance(hb, dict):
                return f"{part} 는 {{blocks}}"
            e = _check_blocks(hb.get("blocks", []), part, styles)
            if e:
                return e
    e = _check_objects(doc.get("objects"), set(anchors(doc)), styles)
    if e:
        return e
    ids = [b.get("id") for _, b in walk(doc)]
    bad = [x for x in ids if not isinstance(x, str) or not ID_RE.match(x)]
    if bad:
        return f"id 형식 아님: {bad[0]!r}"
    dup = {x for x in ids if ids.count(x) > 1}
    if dup:
        return f"id 중복: {sorted(dup)[0]}"
    return None


def list_markers(blocks):
    """목록 문단의 머리 기호 {id: 글} - 번호는 이어진 목록 문단 안에서 단계별로 센다(목록이 끊기거나 restart 면 1부터).
    화면 page-render.js markers 와 같은 규칙. 글머리 = • ◦ ▪ 를 단계마다 돌려 쓰고, 번호 = 1. → a. → i. 차례."""
    out, counts, prev = {}, {}, None
    for b in blocks or []:
        ls = b.get("list") if isinstance(b, dict) and b.get("type") == "p" else None
        if not ls:
            counts, prev = {}, None
            continue
        lv = ls.get("level", 0)
        if prev is None or ls.get("restart"):
            counts = {}
        for k in [k for k in counts if k > lv]:  # 더 깊은 단계의 번호는 얕은 단계로 돌아오면 다시 센다
            del counts[k]
        if ls["kind"] == "number":
            counts[lv] = counts.get(lv, 0) + 1
            out[b["id"]] = _number(counts[lv], lv)
        elif ls["kind"] == "check":
            out[b["id"]] = "☑" if ls.get("done") else "☐"
        else:
            out[b["id"]] = "•◦▪"[lv % 3]
        prev = ls
    return out


def _number(n, level):
    kind = level % 3
    if kind == 0:
        return f"{n}."
    if kind == 1:
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(97 + r) + s
        return s + "."
    out = ""
    for v, t in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out += t
            n -= v
    return out + "."


def resolve_style(doc, name):
    """스타일의 상속(based)을 풀어 한 벌로 - 없는 이름은 body. 화면 page-render.js 의 styleOf 와 같은 규칙."""
    styles = doc.get("styles") or DEFAULT_STYLES
    chain, cur, seen = [], name if name in styles else "body", set()
    while cur and cur in styles and cur not in seen:
        seen.add(cur)
        chain.append(styles[cur])
        cur = styles[cur].get("based")
    out = {}
    for st in reversed(chain):
        out.update({k: v for k, v in st.items() if k not in ("based", "name")})
    return out


def page_box(doc):
    """쪽 크기와 본문 영역(mm) - {w, h, t, r, b, l, cw, ch}."""
    page = {**DEFAULT_PAGE, **(doc.get("page") or {})}
    size = page["size"]
    w, h = SIZES[size] if size in SIZES else (size["w"], size["h"])
    if page.get("orient") == "landscape":
        w, h = h, w
    m = {**DEFAULT_PAGE["margin"], **(page.get("margin") or {})}
    return {"w": w, "h": h, **{k: m[k] for k in "trbl"}, "cw": w - m["l"] - m["r"], "ch": h - m["t"] - m["b"]}
