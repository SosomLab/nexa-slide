# -*- coding: utf-8 -*-
"""시트 구조 작업(행·열 삽입·삭제) - 동시 편집 3-2(docs/collab.md). 화면 sheet.js 의 shiftAxis 와 같은 규칙.

    apply(doc, ops)          문서 사본에 구조 작업들을 차례로 - ops = [{op: insertRows|deleteRows|insertCols|deleteCols, tab, at, n}]
    shift(doc, tab, axis, at, n)  탭 하나의 행("r")·열("c")을 at 부터 n 칸(음수 = 삭제) 옮긴다(문서를 고친다)

옮기는 것: 셀 키 · 병합 셀 · 행 높이(rows)·열 너비(cols) · 틀 고정 · 화면 크기(size) · 모든 탭의 수식 참조(같은 탭의 이름 없는 참조,
다른 탭의 '이름!' 참조 - 칸·범위·열 전체 A:C·행 전체 3:5·넘친 범위 H2#). 지워진 칸을 가리키던 참조는 #REF!.

병합 저장에서 쓰는 곳: 시트 화면이 행·열을 넣거나 지운 저장에 __struct 를 붙이면, 서버가 기준본과 지금 파일 둘 다에 같은 작업을 먼저
적용한 뒤 셀 병합한다 - 한쪽이 행을 넣는 사이 다른 쪽이 고친 아래 셀이 엉뚱한 칸에 들어가지 않게."""
import copy
import re

import sheet_calc

OPS = {"insertRows": ("r", 1), "deleteRows": ("r", -1), "insertCols": ("c", 1), "deleteCols": ("c", -1)}
col_index, col_name = sheet_calc.col_index, sheet_calc.col_name
END = re.compile(r"^(\$?)([A-Za-z]{1,3})?(\$?)(\d+)?$")


def key(r, c):
    return f"{col_name(c)}{r + 1}"


def _ref(k):
    m = re.fullmatch(r"([A-Za-z]{1,3})(\d+)", k or "")
    return (int(m.group(2)) - 1, col_index(m.group(1))) if m else None


def _range(s):
    a, _, b = str(s or "").partition(":")
    p, q = _ref(a), _ref(b or a)
    if not p or not q:
        return None
    return {"r1": min(p[0], q[0]), "c1": min(p[1], q[1]), "r2": max(p[0], q[0]), "c2": max(p[1], q[1])}


def _range_name(g):
    a, b = key(g["r1"], g["c1"]), key(g["r2"], g["c2"])
    return a if a == b else f"{a}:{b}"


def shift(doc, tab, axis, at, n):
    sheets = [t for t in doc.get("sheets") or [] if isinstance(t, dict)]
    sh = next((t for t in sheets if t.get("id") == tab), None)
    if sh is None or not n:
        return doc
    dele, cnt = n < 0, abs(n)
    end = at + cnt - 1

    def mv(v):  # 끝점 하나(행 또는 열 번호) → 새 번호(지워지면 None)
        if not dele:
            return v + cnt if v >= at else v
        if v > end:
            return v - cnt
        return None if v >= at else v

    def mv_range(a, b):  # (시작, 끝) → 새 (시작, 끝) - 통째로 지워지면 None, 삭제가 범위 안이면 줄어든다
        if dele:
            if a >= at and b <= end:
                return None
            na = a - cnt if a > end else at if a >= at else a
            nb = b - cnt if b > end else at - 1 if b >= at else b
            return na, nb
        return (a + cnt if a >= at else a), (b + cnt if b >= at else b)
    ri = 0 if axis == "r" else 1
    cells = {}
    for k, raw in (sh.get("cells") or {}).items():
        p = _ref(k)
        if not p:
            cells[k] = raw
            continue
        v = mv(p[ri])
        if v is None:
            continue
        cells[key(v, p[1]) if axis == "r" else key(p[0], v)] = raw
    sh["cells"] = cells
    if sh.get("merges"):
        out = []
        for m in sh["merges"]:
            g = _range(m)
            if not g:
                continue
            a, b = (g["r1"], g["r2"]) if axis == "r" else (g["c1"], g["c2"])
            nr = mv_range(a, b)
            if not nr:
                continue
            g = {**g, **({"r1": nr[0], "r2": nr[1]} if axis == "r" else {"c1": nr[0], "c2": nr[1]})}
            if g["r1"] != g["r2"] or g["c1"] != g["c2"]:
                out.append(_range_name(g))
        if out:
            sh["merges"] = out
        else:
            sh.pop("merges", None)
    if axis == "r" and isinstance(sh.get("rows"), dict):
        sh["rows"] = {str(v + 1): x for k, x in sh["rows"].items() if str(k).isdigit() for v in [mv(int(k) - 1)] if v is not None}
    if axis == "c" and isinstance(sh.get("cols"), dict):
        sh["cols"] = {col_name(v): x for k, x in sh["cols"].items() if re.fullmatch(r"[A-Za-z]{1,3}", str(k)) for v in [mv(col_index(k))] if v is not None}
    if sh.get("freeze"):
        f = _ref(sh["freeze"])
        if f:
            v = f[ri]
            if v > at:
                nv = max(at, v - cnt) if dele else v + cnt
                sh["freeze"] = key(nv, f[1]) if axis == "r" else key(f[0], nv)
    if isinstance(sh.get("size"), dict):
        k2 = "rows" if axis == "r" else "cols"
        if sh["size"].get(k2):
            sh["size"] = {**sh["size"], k2: max(1, int(sh["size"][k2]) + n)}
    name = str(sh.get("name") or "")
    for s2 in sheets:  # 수식 참조 - 이 탭을 가리키는 참조
        for k, raw in (s2.get("cells") or {}).items():
            if isinstance(raw, dict) and isinstance(raw.get("f"), str) and raw["f"].startswith("="):
                raw["f"] = _rewrite(raw["f"], lambda nm: (s2 is sh) if nm is None else nm.lower() == name.lower(), axis, mv, mv_range)

    def name_def(v, own):  # 이름 정의 값("데이터!$B$2:$B$5" · "0.1" · "=…") - 이름 없는 참조는 own 탭(문서 이름이면 없음)
        if not isinstance(v, str) or not v:
            return v
        f = v if v.startswith("=") else "=" + v
        out = _rewrite(f, lambda nm: (own is sh) if nm is None else nm.lower() == name.lower(), axis, mv, mv_range)
        return out if v.startswith("=") else out[1:]
    # 이름 정의(엑셀 이름 관리자) - 문서 names(통합 문서 범위)·탭 names(시트 범위). 범위 안에 넣으면 늘고, 지운 칸만 가리키면 #REF!
    if isinstance(doc.get("names"), dict):
        doc["names"] = {k: name_def(v, None) for k, v in doc["names"].items()}
    for s2 in sheets:
        if isinstance(s2.get("names"), dict):
            s2["names"] = {k: name_def(v, s2) for k, v in s2["names"].items()}
    return doc


def _rewrite(f, targets, axis, mv, mv_range):
    """수식의 참조 중 이 탭을 가리키는 것만 옮긴다 - 글자("…")·함수 이름은 그대로. 읽지 못하는 수식은 그대로 둔다."""
    src, out, i, last = f[1:], [], 0, 0
    while i < len(src):
        m = sheet_calc.TOK.match(src, i)
        if not m or m.end() == i:
            return f
        g = m.groups()
        if g[3]:
            nm = g[2][:-1].strip("'").replace("''", "'") if g[2] else None
            if targets(nm):
                new = _move_ref(g[3], axis, mv, mv_range)
                s = m.start(4)
                out.append(src[last:s] + new)
                last = m.end(4)
        i = m.end()
        if g[3] and src[i:i + 1] == "#" and ":" not in g[3]:  # 넘친 범위 참조 H2# - '#' 는 참조 뒤에 붙은 표시(sheet_calc.tokenize 와 같다)
            i += 1
    return "=" + "".join(out) + src[last:]


def _move_ref(text, axis, mv, mv_range):
    parts = text.split(":")
    ends = []
    for p in parts:
        m = END.match(p)
        if not m:
            return text
        ends.append({"ca": m.group(1), "c": col_index(m.group(2)) if m.group(2) else None, "ra": m.group(3), "r": int(m.group(4)) - 1 if m.group(4) else None})
    idx = "r" if axis == "r" else "c"
    if any(e[idx] is None for e in ends):  # 열 전체(A:C)를 행 작업이 · 행 전체(3:5)를 열 작업이 - 그대로
        return text

    def fmt(e):
        return (f"{e['ca']}{col_name(e['c'])}" if e["c"] is not None else "") + (f"{e['ra']}{e['r'] + 1}" if e["r"] is not None else "")
    if len(ends) == 1:
        v = mv(ends[0][idx])
        if v is None:
            return "#REF!"
        ends[0][idx] = v
        return fmt(ends[0])
    nr = mv_range(ends[0][idx], ends[1][idx])
    if nr is None:
        return "#REF!"
    ends[0][idx], ends[1][idx] = nr
    return fmt(ends[0]) + ":" + fmt(ends[1])


def apply(doc, ops):
    """문서 사본에 구조 작업들을 차례로. 모르는 작업·잘못된 값은 건너뛴다."""
    out = copy.deepcopy(doc)
    for o in ops or []:
        if not isinstance(o, dict) or o.get("op") not in OPS:
            continue
        axis, sign = OPS[o["op"]]
        try:
            at, n = int(o.get("at")), int(o.get("n") or 1)
        except (TypeError, ValueError):
            continue
        if at < 0 or n <= 0:
            continue
        shift(out, o.get("tab"), axis, at, sign * n)
    return out
