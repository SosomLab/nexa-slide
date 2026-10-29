# -*- coding: utf-8 -*-
"""시트 수식 계산기(Python) - 화면 sheet.js 와 같은 규칙. xlsx 내보내기의 계산값 캐시·AI 세션의 수식 확인에 쓴다.

    python3 nexa.py sheet_calc <시트 문서>            # 수식을 계산해 오류 셀·순환 참조를 보여 준다(파일은 그대로)
    python3 nexa.py sheet_calc <시트 문서> --cell 탭!B3  # 한 칸 값

문법: 사칙연산·^·&·비교·%, 셀·범위 참조($ 고정, 다른 탭 '이름'!A1), 함수(FUNCS). 오류 값은 문자열("#DIV/0!" 등).
같은 입력이면 화면과 같은 값이 나와야 한다 - 시험 사례는 studio/tests/sheetcalc_cases.json(화면 시나리오와 같이 쓴다).
"""
import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

ERRS = ("#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#NULL!", "#SPILL!", "#CALC!")
DYN = {"FILTER", "SORT", "SORTBY", "UNIQUE", "SEQUENCE", "TRANSPOSE", "TAKE", "DROP", "CHOOSECOLS", "CHOOSEROWS", "HSTACK", "VSTACK", "TOCOL", "TOROW", "TEXTSPLIT", "GROUPBY", "PIVOTBY", "MAP", "BYROW", "BYCOL", "SCAN", "MAKEARRAY"}  # 동적 배열 함수 - 이 함수를 쓴(또는 가져온 동적 배열 da) 수식만 옆 칸으로 넘친다
DAY0 = dt.date(1899, 12, 30)


class FErr(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class Rng:
    """범위 값 - rows × cols 2차원(행 우선)."""
    def __init__(self, rows):
        self.rows = rows

    @property
    def vals(self):
        return [v for r in self.rows for v in r]


L = r"[^\W\d]"  # 글자(밑줄 포함)
TOK = re.compile("|".join([
    r"(\s+)",
    r'("(?:[^"]|"")*")',
    rf"((?:'(?:[^']|'')+'|{L}[\w.]*)!)?(\$?[A-Za-z]{{1,3}}\$?\d+(?::\$?[A-Za-z]{{1,3}}\$?\d+)?|\$?[A-Za-z]{{1,3}}:\$?[A-Za-z]{{1,3}}|\$?\d+:\$?\d+)(?![\w(])",
    rf"({L}[\w.]*)(?=\s*\()",
    r"(TRUE|FALSE)(?!\w)",
    r"(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)",
    r"(<=|>=|<>|[-+*/^&=<>(),%])",
    r"(#[A-Z/0]+[!?])",
    rf"((?:{L}[\w.]*)?\[(?:[^\[\]]|\[[^\[\]]*\])*\])",  # 표 구조적 참조 표1[열] · [@열] · 표1[[#Headers],[열]]
    rf"({L}[\w.]*)",
]), re.I)


def col_index(s):
    n = 0
    for ch in s.upper():
        n = n * 26 + ord(ch) - 64
    return n - 1


def col_name(c):
    s = ""
    c += 1
    while c:
        c, m = divmod(c - 1, 26)
        s = chr(65 + m) + s
    return s


def parse_ref(s):
    m = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d+)", s.strip())
    return (int(m.group(2)) - 1, col_index(m.group(1))) if m else None


def tokenize(src):
    out, i = [], 0
    while i < len(src):
        m = TOK.match(src, i)
        if not m or m.end() == i:
            raise FErr("#NAME?")
        i = m.end()
        g = m.groups()
        if g[0]:
            continue
        if g[1]:
            out.append(("str", g[1][1:-1].replace('""', '"')))
        elif g[3]:
            sheet = g[2][:-1].strip("'").replace("''", "'") if g[2] else None
            if src[i:i + 1] == "#" and ":" not in g[3]:  # 넘친 범위 참조 H2# (엑셀 파일에는 ANCHORARRAY(H2))
                i += 1
                out.append(("ref", g[3], sheet, "#"))
            else:
                out.append(("ref", g[3], sheet))
        elif g[4]:
            out.append(("fn", re.sub(r"^(?:_XL(?:FN|WS)\.)+", "", g[4].upper())))  # 파일에 저장된 새 함수 접두사(_xlfn.TEXTJOIN)
        elif g[5]:
            out.append(("bool", g[5].upper() == "TRUE"))
        elif g[6]:
            out.append(("num", float(g[6])))
        elif g[7]:
            out.append(("op", g[7]))
        elif g[8]:
            out.append(("err", g[8]))
        elif g[9]:
            k = g[9].index("[")
            out.append(("sref", g[9][:k] or None, g[9][k + 1:-1]))
        else:
            out.append(("name", g[10]))
    return out


def parse(src):
    T, p = tokenize(src), [0]

    def peek():
        return T[p[0]] if p[0] < len(T) else None

    def is_op(v):
        t = peek()
        return t is not None and t[0] == "op" and t[1] == v

    def eat(v):
        if not is_op(v):
            raise FErr("#NAME?")
        p[0] += 1

    def binl(nxt, ops):
        def f():
            a = nxt()
            while peek() and peek()[0] == "op" and peek()[1] in ops:
                op = peek()[1]
                p[0] += 1
                a = ("bin", op, a, nxt())
            return a
        return f

    def unary():
        if is_op("-"):
            p[0] += 1
            return ("neg", unary())
        if is_op("+"):
            p[0] += 1
            return unary()
        a = prim()
        while is_op("%"):
            p[0] += 1
            a = ("pct", a)
        return a

    def prim():
        t = peek()
        if t is None:
            raise FErr("#NAME?")
        p[0] += 1
        k = t[0]
        if k in ("num", "str", "bool"):
            return ("lit", t[1])
        if k == "err":
            return ("err", t[1])
        if k == "name":
            return ("name", t[1].upper())  # LET 이름 - 밖에서는 #NAME?
        if k == "sref":
            return ("sref", t[1], t[2])
        if k == "ref":
            if len(t) > 3:
                a = parse_ref(t[1])
                return ("spill", t[2], a[0], a[1])
            ends = t[1].split(":")
            if re.fullmatch(r"\$?[A-Za-z]{1,3}", ends[0]):  # 열 전체 A:A - 끝 행은 계산할 때 그 탭의 데이터 끝으로
                return ("range", t[2], 0, col_index(ends[0].lstrip("$")), -1, col_index(ends[-1].lstrip("$")))
            if re.fullmatch(r"\$?\d+", ends[0]):  # 행 전체 1:1
                return ("range", t[2], int(ends[0].lstrip("$")) - 1, 0, int(ends[-1].lstrip("$")) - 1, -1)
            a = parse_ref(ends[0])
            b = parse_ref(ends[-1])
            if len(ends) > 1:
                return ("range", t[2], min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
            return ("ref", t[2], a[0], a[1])
        if k == "fn":
            eat("(")
            args = []
            if not is_op(")"):
                while True:
                    args.append(("lit", None) if is_op(",") or is_op(")") else cmp_())
                    if is_op(","):
                        p[0] += 1
                        continue
                    break
            eat(")")
            return ("fn", t[1], args)
        if k == "op" and t[1] == "(":
            a = cmp_()
            eat(")")
            return a
        raise FErr("#NAME?")
    pow_ = binl(unary, ("^",))
    mul = binl(pow_, ("*", "/"))
    add = binl(mul, ("+", "-"))
    cat = binl(add, ("&",))
    cmp_ = binl(cat, ("=", "<>", "<", ">", "<=", ">="))
    ast = cmp_()
    if p[0] < len(T):
        raise FErr("#NAME?")
    return ast


# ---------------------------------------------------------------- 값 바꾸기
def fix(x):
    if isinstance(x, float):
        if math.isinf(x) or math.isnan(x):
            raise FErr("#NUM!")
        y = float(f"{x:.15g}")
        return int(y) if y.is_integer() and abs(y) < 1e15 else y
    return x


def parse_number_text(s):
    s = str(s).strip()
    if not s:
        return None
    m = re.fullmatch(r"([+-]?)((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?(%?)", s)
    if m:
        v = float(m.group(2).replace(",", "")) * (10 ** int(m.group(3)) if m.group(3) else 1)
        v = -v if m.group(1) == "-" else v
        return v / 100 if m.group(4) else v
    m = re.fullmatch(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", s)
    if m:
        try:
            return (dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) - DAY0).days
        except ValueError:
            return None
    return None


def to_num(v):
    if isinstance(v, FErr):
        raise v
    if v is None or v == "":
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    if v in ERRS:
        raise FErr(v)
    n = parse_number_text(v)
    if n is None:
        raise FErr("#VALUE!")
    return n


def general(v):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, int):
        return str(v)
    a = abs(v)
    if a and (a < 1e-9 or a >= 1e15):
        return f"{v:.5E}".replace("E+0", "E+").replace("E-0", "E-")
    s = f"{v:.11g}"
    return str(int(float(s))) if float(s).is_integer() else s


def to_str(v):
    if isinstance(v, FErr):
        raise v
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return general(v)
    return str(v)


def to_bool(v):
    if isinstance(v, FErr):
        raise v
    if isinstance(v, str):
        if v.upper() == "TRUE":
            return True
        if v.upper() == "FALSE":
            return False
        raise FErr("#VALUE!")
    return bool(to_num(v))


def rank(v):
    return 0 if v is None else 1 if isinstance(v, (int, float)) and not isinstance(v, bool) else 2 if isinstance(v, str) else 3


def compare(a, b, op):
    if a is None:
        a = "" if isinstance(b, str) else False if isinstance(b, bool) else 0
    if b is None:
        b = "" if isinstance(a, str) else False if isinstance(a, bool) else 0
    if rank(a) != rank(b):
        d = rank(a) - rank(b)
    elif isinstance(a, str):
        x, y = a.lower(), b.lower()
        d = (x > y) - (x < y)
    else:
        d = (a > b) - (a < b)
    return {"=": d == 0, "<>": d != 0, "<": d < 0, ">": d > 0, "<=": d <= 0, ">=": d >= 0}[op]


def date_of(n):
    return DAY0 + dt.timedelta(days=int(math.floor(to_num(n))))


def serial(d):
    return (d - DAY0).days


def add_months(d, k):
    y, m = divmod(d.month - 1 + k, 12)
    y += d.year
    last = (dt.date(y + (m + 1) // 12, (m + 1) % 12 + 1, 1) - dt.timedelta(days=1)).day
    return dt.date(y, m + 1, min(d.day, last))


def criteria(c):
    """SUMIF·COUNTIF 조건 → 판정 함수. ">5" · "<>x" · "=a" · "a*b?" · 5."""
    if isinstance(c, (int, float)) and not isinstance(c, bool):
        return lambda v: rank(v) == 1 and v == c
    s = to_str(c)
    m = re.match(r"^(<=|>=|<>|<|>|=)?(.*)$", s, re.S)
    op, rest = m.group(1) or "=", m.group(2)
    n = parse_number_text(rest)
    if n is not None:
        return lambda v: (rank(v) == 1 and compare(v, n, op)) if op != "<>" else not (rank(v) == 1 and v == n)
    if op in ("=", "<>") and re.search(r"[*?]", rest):
        rx = re.compile("^" + re.escape(rest).replace(r"\*", ".*").replace(r"\?", ".") + "$", re.I | re.S)
        hit = lambda v: isinstance(v, str) and bool(rx.match(v))  # noqa: E731
        return hit if op == "=" else (lambda v: not hit(v))
    if op == "=" and rest == "":
        return lambda v: v is None or v == ""
    return lambda v: compare(v if v is not None else "", rest, op) if (isinstance(v, str) or v is None or op == "<>") else (op == "<>")


# ---------------------------------------------------------------- 계산기
class Calc:
    def __init__(self, doc):
        self.doc = doc
        self.sheets = doc.get("sheets") or []
        self.memo, self.busy, self.ast = {}, set(), {}
        self.at = []  # 계산 중인 셀 (행, 열) - ROW()·COLUMN() 인수 없음
        self.dims = {}
        self.spill, self.anchors, self.dyn = {}, {}, {}
        self.extent, self.scope = {}, []  # 동적 배열 기준 칸 → 넘친 크기 (행 수, 열 수) · LET 이름 묶음  # 넘친 칸 (탭 id, 행, 열) → (값, 기준 칸) · 탭별 동적 배열 수식 칸 · 수식 → 동적인가
        self.names, self.naming = {}, set()  # 이름 정의 (탭 id|None, 이름) → 구문 트리 · 계산 중인 이름(순환)
        self.depth = 0  # LAMBDA 부르기 깊이

    def named(self, nm, sh):
        """이름 정의 → 구문 트리(없으면 None). 탭 names(엑셀 시트 범위 이름)가 문서 names 보다 먼저, 이름은 대소문자 무시.
        탭 이름의 참조에 탭이 없으면 그 탭을 가리킨다(문서 이름은 계산하는 칸의 탭)."""
        for owner in (sh, None):
            book = (owner if owner is not None else self.doc).get("names") or {}
            hit = next((v for k, v in book.items() if str(k).upper() == nm), None)
            if hit is None:
                continue
            key = (owner.get("id") if owner is not None else None, nm)
            if key not in self.names:
                try:
                    node = parse(str(hit)[1:] if str(hit).startswith("=") else str(hit))
                except FErr as e:
                    node = ("err", e.code)
                if owner is not None and node[0] in ("ref", "range") and node[1] is None:
                    node = (node[0], owner.get("name")) + node[2:]
                self.names[key] = node
            return self.names[key]
        return None

    def lam_of(self, nm, sh):
        """f(…) 의 f - LET 이름이나 이름 정의에 담긴 LAMBDA(없으면 None)."""
        for sc in reversed(self.scope):
            if nm in sc:
                return sc[nm] if isinstance(sc[nm], Lam) else None
        node = self.named(nm, sh)
        if node is None or nm in self.naming:
            return None
        self.naming.add(nm)
        try:
            f = _cellv(lambda: self.ev(node, sh))
        finally:
            self.naming.discard(nm)
        return f if isinstance(f, Lam) else None

    def call(self, f, vals, sh):
        """LAMBDA 부르기 - 매개변수를 만든 곳의 이름 묶음 위에 얹는다. 이름 정의 LAMBDA 는 자기를 부를 수 있다(깊이 200까지)."""
        if len(vals) != len(f.params):
            raise FErr("#VALUE!")
        if self.depth > 200:
            raise FErr("#NUM!")
        saved = self.scope
        self.scope, self.depth = f.scope + [dict(zip(f.params, vals))], self.depth + 1
        try:
            return self.ev(f.body, sh)
        finally:
            self.scope, self.depth = saved, self.depth - 1

    def deref(self, n, sh):
        """LET 이름이 아닌 이름 → 이름 정의의 참조·식 - 범위를 받는 함수(SUM·COUNT·ROW·OFFSET)가 참조로 보게."""
        if n[0] == "name" and not any(n[1] in sc for sc in self.scope):
            node = self.named(n[1], sh)
            if node is not None and n[1] not in self.naming:
                return node
        return n

    def is_dyn(self, raw):
        if raw.get("da"):
            return True
        if raw["f"] not in self.dyn:
            self.dyn[raw["f"]] = dynamic(raw)
        return self.dyn[raw["f"]]

    def sref(self, n, sh):
        """표1[열] · [@열] · 표1[[#Headers],[열1]:[열2]] → ("ref"|"range", 탭 이름, …)."""
        _, name, inner = n
        hit = None
        for s in self.sheets:
            for t in s.get("tables") or []:
                if name and str(t.get("name", "")).lower() == name.lower():
                    hit = (s, t)
                elif not name and s is sh and self.at:
                    r1, c1, r2, c2 = _tref(t)
                    if r1 <= self.at[-1][0] <= r2 and c1 <= self.at[-1][1] <= c2:
                        hit = (s, t)
        if hit is None:
            raise FErr("#REF!")
        s, t = hit
        spec, cols = table_spec(inner)
        r1, c1, r2, c2 = _tref(t)
        names = [str(x).lower() for x in t.get("cols") or []]
        d1 = r1 + (1 if t.get("header", True) else 0)
        d2 = r2 - (1 if t.get("totals") else 0)
        if "@" in spec or "#this row" in spec:
            if not self.at or not d1 <= self.at[-1][0] <= d2:
                raise FErr("#VALUE!")
            ra = rb = self.at[-1][0]
        elif "#all" in spec:
            ra, rb = r1, r2
        else:
            ra, rb = d1, d2
            if "#headers" in spec:
                ra = r1 if t.get("header", True) else d1
                rb = rb if "#data" in spec else ra
            if "#totals" in spec:
                if not t.get("totals"):
                    raise FErr("#REF!")
                rb = r2
                ra = ra if "#data" in spec else r2
        if cols:
            try:
                k = [c1 + names.index(x.lower()) for x in cols]
            except ValueError:
                raise FErr("#REF!")
            ca, cb = min(k), max(k)
        else:
            ca, cb = c1, c2
        tab = None if s is sh else s.get("name")
        return ("ref", tab, ra, ca) if ra == rb and ca == cb else ("range", tab, ra, ca, rb, cb)

    def spilled(self, sh, r, c):
        """빈 칸(또는 넘친 칸)의 값 - 왼쪽 위의 동적 배열 수식을 먼저 계산해 넘친 값이 있으면 그것."""
        sid = sh.get("id")
        if sid not in self.anchors:
            self.anchors[sid] = [(p, k) for k, raw in (sh.get("cells") or {}).items()
                                 if isinstance(raw, dict) and raw.get("f") and self.is_dyn(raw) and (p := parse_ref(k))]
        for (ar, ac), k in self.anchors[sid]:
            if ar <= r and ac <= c and (sid, k) not in self.memo and (sid, k) not in self.busy:
                self.cell(sh, k)
        hit = self.spill.get((sid, r, c))
        return hit[0] if hit else None

    def spill_out(self, sh, k, v):
        """배열 결과를 기준 칸 k 에서 오른쪽·아래로 넘긴다 - 자리에 값이 있으면 #SPILL!."""
        sid, (ar, ac) = sh.get("id"), parse_ref(k)
        h, w = len(v.rows), len(v.rows[0])
        if h * w > 100000:
            return FErr("#SPILL!")
        cells = sh.get("cells") or {}
        for i in range(h):
            for j in range(w):
                if i == j == 0:
                    continue
                raw = cells.get(f"{col_name(ac + j)}{ar + i + 1}")
                busy = raw.get("f") or (raw.get("v") not in (None, "") and not raw.get("sp")) if isinstance(raw, dict) else raw not in (None, "")
                if busy or (sid, ar + i, ac + j) in self.spill:
                    return FErr("#SPILL!")
        for i in range(h):
            for j in range(w):
                if i or j:
                    x = v.rows[i][j]
                    self.spill[(sid, ar + i, ac + j)] = (0 if x is None else x, k)
        self.extent[(sid, k)] = (h, w)
        return v.rows[0][0]

    def sheet(self, name, cur):
        if name is None:
            return cur
        return next((s for s in self.sheets if str(s.get("name", "")).lower() == name.lower()), None)

    def value(self, sh, r, c):
        k = f"{col_name(c)}{r + 1}"
        raw = (sh.get("cells") or {}).get(k)
        if isinstance(raw, dict) and raw.get("f"):
            return self.cell(sh, k)
        v = raw.get("v") if isinstance(raw, dict) and not raw.get("sp") else None if isinstance(raw, dict) else raw
        if v is None:
            v = self.spilled(sh, r, c)
        if isinstance(v, str) and v in ERRS:
            return FErr(v)
        return v

    def cell(self, sh, k):
        key = (sh.get("id"), k)
        if key in self.memo:
            return self.memo[key]
        if key in self.busy:
            return FErr("#REF!")  # 순환 참조
        self.busy.add(key)
        self.at.append(parse_ref(k))
        f = sh["cells"][k]["f"]
        try:
            if f not in self.ast:
                try:
                    self.ast[f] = parse(f[1:] if f.startswith("=") else f)
                except FErr as e:
                    self.ast[f] = ("err", e.code)
            v = self.ev(self.ast[f], sh)
            if self.is_dyn(sh["cells"][k]):
                if isinstance(v, Rng) and len(v.vals) > 1:
                    v = self.spill_out(sh, k, v)
                if not isinstance(v, FErr) and (sh.get("id"), k) not in self.extent:
                    self.extent[(sh.get("id"), k)] = (1, 1)
            if isinstance(v, Lam):
                v = FErr("#CALC!")  # 칸 값이 함수 - 엑셀도 #CALC!
            if isinstance(v, Rng):
                v = v.vals[0] if len(v.vals) == 1 else FErr("#VALUE!")
            if v is None:
                v = 0
            v = fix(v) if not isinstance(v, FErr) else v
        except FErr as e:
            v = e
        except (ZeroDivisionError, OverflowError, ValueError, TypeError, IndexError):
            v = FErr("#VALUE!")
        self.busy.discard(key)
        self.at.pop()
        self.memo[key] = v
        return v

    def dim(self, s):
        """탭의 데이터 끝 (행 수, 열 수) - 열 전체·행 전체 참조를 여기까지로 자른다."""
        if s.get("id") not in self.dims:
            rr = cc = 0
            for k in s.get("cells") or {}:
                p = parse_ref(k)
                if p:
                    rr, cc = max(rr, p[0] + 1), max(cc, p[1] + 1)
            self.dims[s.get("id")] = (rr, cc)
        return self.dims[s.get("id")]

    def bounds(self, n, s):
        r1, c1, r2, c2 = n[2], n[3], n[4], n[5]
        if r2 < 0 or c2 < 0:
            rr, cc = self.dim(s)
            r2 = max(rr - 1, r1) if r2 < 0 else r2
            c2 = max(cc - 1, c1) if c2 < 0 else c2
        return r1, c1, r2, c2

    def rng(self, n, sh):
        s = self.sheet(n[1], sh)
        if s is None:
            raise FErr("#REF!")
        r1, c1, r2, c2 = self.bounds(n, s)
        out = Rng([[self.value(s, r, c) for c in range(c1, c2 + 1)] for r in range(r1, r2 + 1)])
        out.origin = (r1, c1)
        return out

    def ev(self, n, sh):
        k = n[0]
        if k == "lit":
            return n[1]
        if k == "err":
            raise FErr(n[1])
        if k == "arr":  # 계산된 배열을 범위처럼(GROUPBY 집계 - 빈 칸·글은 건너뜀)
            return n[1]
        if k == "ref":
            s = self.sheet(n[1], sh)
            if s is None:
                raise FErr("#REF!")
            v = self.value(s, n[2], n[3])
            if isinstance(v, FErr):
                raise v
            return v
        if k == "range":
            return self.rng(n, sh)
        if k == "spill":  # H2# - 그 칸의 동적 배열이 넘친 범위 전체
            s = self.sheet(n[1], sh)
            if s is None:
                raise FErr("#REF!")
            key = f"{col_name(n[3])}{n[2] + 1}"
            raw = (s.get("cells") or {}).get(key)
            if isinstance(raw, dict) and raw.get("f"):
                self.cell(s, key)
            h, w = self.extent.get((s.get("id"), key), (0, 0))
            if not h:
                raise FErr("#REF!")
            return self.rng(("range", n[1], n[2], n[3], n[2] + h - 1, n[3] + w - 1), sh)
        if k == "sref":  # 표 구조적 참조 → 셀·범위
            return self.ev(self.sref(n, sh), sh)
        if k == "name":
            for sc in reversed(self.scope):
                if n[1] in sc:
                    v = sc[n[1]]
                    if isinstance(v, FErr):
                        raise v
                    return v
            node = self.named(n[1], sh)  # 이름 정의(매출 = 데이터!$B$2:$B$5 · 세율 = 0.1)
            if node is None:
                raise FErr("#NAME?")
            if n[1] in self.naming:
                raise FErr("#REF!")  # 이름이 자기를 부른다
            self.naming.add(n[1])
            try:
                return self.ev(node, sh)
            finally:
                self.naming.discard(n[1])
        if k == "neg":
            x = self.ev(n[1], sh)
            if isinstance(x, Rng) and len(x.vals) > 1:  # 배열 - 칸마다
                return amap(lambda v: -to_num(v), x)
            return -to_num(self.sc(x))
        if k == "pct":
            return to_num(self.sc(self.ev(n[1], sh))) / 100
        if k == "bin":
            ra, rb = self.ev(n[2], sh), self.ev(n[3], sh)
            if (isinstance(ra, Rng) and len(ra.vals) > 1) or (isinstance(rb, Rng) and len(rb.vals) > 1):  # 배열 수식 - 칸마다(오류는 그 칸만)
                return azip(lambda x, y: self.binop(n[1], x, y), ra, rb)
            return self.binop(n[1], self.sc(ra), self.sc(rb))
        if k == "fn":
            fn = FUNCS.get(n[1])
            if fn is None:  # LET 이름·이름 정의에 담긴 LAMBDA - f(1, 2)
                lam = self.lam_of(n[1], sh)
                if lam is None:
                    raise FErr("#NAME?")
                return self.call(lam, [_cellv(lambda a=a: self.ev(a, sh)) for a in n[2]], sh)
            if n[1] in SCALAR:  # 한 칸 함수에 배열이 오면 칸마다(엑셀 배열 수식처럼 - SUMPRODUCT(--ISNUMBER(SEARCH(x, 범위))))
                vals = [_cellv(lambda a=a: self.ev(a, sh)) if a[0] != "lit" else a[1] for a in n[2]]  # 오류 인수는 값(FErr)으로 - ISERROR 가 본다
                if any(isinstance(v, Rng) and len(v.vals) > 1 for v in vals):
                    big = max((v for v in vals if isinstance(v, Rng)), key=lambda v: len(v.vals))
                    h, w = len(big.rows), len(big.rows[0])
                    pick = lambda v, i, j: (v.rows[i if len(v.rows) > 1 else 0][j if len(v.rows[0]) > 1 else 0] if isinstance(v, Rng) else v)  # noqa: E731
                    return Rng([[_cellv(lambda: fn(self, [("lit", pick(v, i, j)) for v in vals], sh)) for j in range(w)] for i in range(h)])
            return fn(self, n[2], sh)
        raise FErr("#VALUE!")

    def binop(self, op, a, b):
        if isinstance(a, FErr):
            raise a
        if isinstance(b, FErr):
            raise b
        if True:
            if op == "+":
                return to_num(a) + to_num(b)
            if op == "-":
                return to_num(a) - to_num(b)
            if op == "*":
                return to_num(a) * to_num(b)
            if op == "/":
                d = to_num(b)
                if d == 0:
                    raise FErr("#DIV/0!")
                return to_num(a) / d
            if op == "^":
                try:
                    r = to_num(a) ** to_num(b)
                except (OverflowError, ZeroDivisionError):
                    raise FErr("#NUM!")
                if isinstance(r, complex):
                    raise FErr("#NUM!")
                return r
            if op == "&":
                return to_str(a) + to_str(b)
            return compare(a, b, op)

    @staticmethod
    def sc(v):
        if isinstance(v, FErr):
            raise v
        if isinstance(v, Rng):
            if len(v.vals) != 1:
                raise FErr("#VALUE!")
            x = v.vals[0]
            if isinstance(x, FErr):
                raise x
            return x
        return v

    def one(self, args, i, sh, default=None):
        if i >= len(args):
            return default
        return self.sc(self.ev(args[i], sh))

    def nums(self, args, sh, mode=""):
        """집계 인수 - 참조·범위 안은 숫자만(글·빈 칸 무시, 오류는 그대로), 직접 쓴 값은 숫자로. mode count·counta·blank."""
        out = []
        for a in args:
            a = self.deref(a, sh)
            is_ref = a[0] in ("ref", "range", "arr")
            v = self.ev(a, sh)
            for x in (v.vals if isinstance(v, Rng) else [v]):
                if isinstance(x, FErr):
                    if mode in ("count", "counta", "blank"):
                        if mode == "counta":
                            out.append(x)
                        continue
                    raise x
                if mode == "blank":
                    if x is None or x == "":
                        out.append(x)
                elif is_ref:
                    if isinstance(x, (int, float)) and not isinstance(x, bool):
                        out.append(x)
                    elif mode == "counta" and x is not None and x != "":
                        out.append(x)
                elif mode == "counta":
                    if x is not None:
                        out.append(x)
                elif mode == "count":
                    if isinstance(x, (int, float)) or (isinstance(x, str) and parse_number_text(x) is not None):
                        out.append(x)
                else:
                    out.append(to_num(x))
        return out

    def area(self, a, sh):
        v = self.ev(a, sh)
        return v if isinstance(v, Rng) else Rng([[v]])

    def refnode(self, n, sh):
        """INDIRECT·OFFSET·이름 정의 → 참조 노드(ref·range). 다른 함수가 범위로 쓸 수 있게."""
        n = self.deref(n, sh)
        if n[0] in ("ref", "range"):
            return n
        if n[0] == "fn" and n[1] == "INDIRECT":
            txt = to_str(self.one(n[2], 0, sh))
            try:
                node = parse(txt)
            except FErr:
                raise FErr("#REF!")
            if node[0] not in ("ref", "range"):
                raise FErr("#REF!")
            return node
        if n[0] == "fn" and n[1] == "OFFSET":
            A = n[2]
            base = self.refnode(A[0], sh)
            dr, dc = int(to_num(self.one(A, 1, sh, 0))), int(to_num(self.one(A, 2, sh, 0)))
            s = self.sheet(base[1], sh) or sh
            r1, c1 = base[2], base[3]
            if base[0] == "range":
                r1, c1, r2, c2 = self.bounds(base, s)
                h, w = r2 - r1 + 1, c2 - c1 + 1
            else:
                h = w = 1
            h = int(to_num(self.one(A, 3, sh, h))) if len(A) > 3 and A[3] != ("lit", None) else h
            w = int(to_num(self.one(A, 4, sh, w))) if len(A) > 4 and A[4] != ("lit", None) else w
            r1, c1 = r1 + dr, c1 + dc
            if r1 < 0 or c1 < 0 or h < 1 or w < 1:
                raise FErr("#REF!")
            return ("ref", base[1], r1, c1) if h == w == 1 else ("range", base[1], r1, c1, r1 + h - 1, c1 + w - 1)
        raise FErr("#REF!")


def _tref(t):
    a, _, b = str(t.get("ref", "")).partition(":")
    pa, pb = parse_ref(a), parse_ref(b or a)
    if not pa or not pb:
        raise FErr("#REF!")
    return pa[0], pa[1], pb[0], pb[1]


def table_spec(inner):
    """구조적 참조 안쪽 → (특수 지정 집합 {#all,#data,#headers,#totals,#this row,@}, 열 이름 [처음, 끝])."""
    inner = inner.strip()
    spec, cols = set(), []
    if inner.startswith("@"):
        spec.add("@")
        inner = inner[1:].strip()
    if "[" not in inner:
        items = [inner] if inner else []
    else:
        items = re.findall(r"\[([^\]]*)\]", inner)
    for it in items:
        if it.startswith("#"):
            spec.add(it.lower())
        elif it:
            cols.append(it.replace("'", ""))
    if len(cols) > 2:
        cols = [cols[0], cols[-1]]
    return spec, cols


def _cellv(f, *xs):
    try:
        return f(*xs)
    except FErr as e:
        return e


def amap(f, r):
    return Rng([[_cellv(f, v) for v in row] for row in r.rows])


def azip(f, a, b):
    ra = a.rows if isinstance(a, Rng) else [[a]]
    rb = b.rows if isinstance(b, Rng) else [[b]]
    h, w = max(len(ra), len(rb)), max(len(ra[0]), len(rb[0]))
    pick = lambda m, i, j: m[i if len(m) > 1 else 0][j if len(m[0]) > 1 else 0]  # noqa: E731 - 한 칸·한 줄은 늘려 쓴다
    return Rng([[_cellv(f, pick(ra, i, j), pick(rb, i, j)) for j in range(w)] for i in range(h)])


def _row_col(which):
    def f(c, A, sh):
        if not A:
            at = c.at[-1] if c.at else (0, 0)
            return at[which] + 1
        n = c.deref(A[0], sh)
        if n[0] == "ref":
            return n[2 + which] + 1
        if n[0] == "range":
            s = c.sheet(n[1], sh) or sh
            r1, c1, r2, c2 = c.bounds(n, s)
            if which == 0:
                return Rng([[r + 1] for r in range(r1, r2 + 1)]) if r2 > r1 else r1 + 1
            return Rng([[k + 1 for k in range(c1, c2 + 1)]]) if c2 > c1 else c1 + 1
        if n[0] == "fn" and n[1] in ("INDIRECT", "OFFSET"):
            return f(c, [c.refnode(n, sh)], sh)
        raise FErr("#VALUE!")
    return f


def _indirect(c, A, sh):
    return c.ev(c.refnode(("fn", "INDIRECT", A), sh), sh)


def _offset(c, A, sh):
    return c.ev(c.refnode(("fn", "OFFSET", A), sh), sh)


def _subtotal(c, A, sh):
    k = int(to_num(c.one(A, 0, sh))) % 100
    fn = {1: "AVERAGE", 2: "COUNT", 3: "COUNTA", 4: "MAX", 5: "MIN", 6: "PRODUCT", 9: "SUM"}.get(k)
    if not fn:
        raise FErr("#VALUE!")
    return FUNCS[fn](c, A[1:], sh)


def _rows_cols(which):
    def f(c, A, sh):
        r = c.area(A[0], sh)
        return len(r.rows) if which == 0 else len(r.rows[0]) if r.rows else 0
    return f


def round_x(x, n, how=""):
    f = 10 ** n
    y = float(f"{abs(x) * f:.15g}")
    z = math.ceil(y) if how == "up" else math.floor(y) if how == "down" else math.floor(y + 0.5)
    return math.copysign(z / f, x) if z else 0


def _sum(c, A, sh):
    return sum(c.nums(A, sh))


def _avg(c, A, sh):
    lst = c.nums(A, sh)
    if not lst:
        raise FErr("#DIV/0!")
    return sum(lst) / len(lst)


def _median(c, A, sh):
    lst = sorted(c.nums(A, sh))
    if not lst:
        raise FErr("#NUM!")
    m = len(lst) // 2
    return lst[m] if len(lst) % 2 else (lst[m - 1] + lst[m]) / 2


def _if(c, A, sh):
    if not A:
        raise FErr("#VALUE!")
    cond = c.ev(A[0], sh)
    if isinstance(cond, Rng) and len(cond.vals) > 1:  # 배열 조건 - 칸마다(거짓이고 셋째 인수가 없으면 FALSE)
        yes = c.ev(A[1], sh) if len(A) > 1 else True
        no = c.ev(A[2], sh) if len(A) > 2 else False
        ys = yes if isinstance(yes, Rng) else None
        ns = no if isinstance(no, Rng) else None
        rows = []
        for i, row in enumerate(cond.rows):
            out = []
            for j, v in enumerate(row):
                try:
                    t = to_bool(v)
                except FErr as e:
                    out.append(e)
                    continue
                src, sc = (ys, yes) if t else (ns, no)
                out.append(src.rows[i if len(src.rows) > 1 else 0][j if len(src.rows[0]) > 1 else 0] if src is not None else sc)
            rows.append(out)
        return Rng(rows)
    return (c.one(A, 1, sh, True) if len(A) > 1 else True) if to_bool(c.one(A, 0, sh)) else (c.one(A, 2, sh, False) if len(A) > 2 else False)


def _ifs(c, A, sh):
    for i in range(0, len(A) - 1, 2):
        if to_bool(c.one(A, i, sh)):
            return c.one(A, i + 1, sh)
    raise FErr("#N/A")


def _iferror(c, A, sh):
    try:
        return c.one(A, 0, sh)
    except FErr:
        return c.one(A, 1, sh, "") if len(A) > 1 else ""


def _ifna(c, A, sh):
    try:
        return c.one(A, 0, sh)
    except FErr as e:
        if e.code != "#N/A":
            raise
        return c.one(A, 1, sh, "") if len(A) > 1 else ""


def _switch(c, A, sh):
    x = c.one(A, 0, sh)
    i = 1
    while i + 1 < len(A):
        if compare(x, c.one(A, i, sh), "="):
            return c.one(A, i + 1, sh)
        i += 2
    if i < len(A):
        return c.one(A, i, sh)
    raise FErr("#N/A")


def _choose(c, A, sh):
    i = int(to_num(c.one(A, 0, sh)))
    if i < 1 or i >= len(A):
        raise FErr("#VALUE!")
    return c.one(A, i, sh)


def _ifagg(kind):
    """SUMIF·COUNTIF·AVERAGEIF(S) - 조건 범위와 합 범위는 같은 모양."""
    def f(c, A, sh):
        multi = kind.endswith("S")
        if multi:
            sum_rng = c.area(A[0], sh) if kind != "COUNTIFS" else None
            pairs = A[1:] if kind != "COUNTIFS" else A
        else:
            pairs = A[:2]
            sum_rng = c.area(A[2], sh) if len(A) > 2 and kind != "COUNTIF" else None
        conds = [(c.area(pairs[i], sh).vals, criteria(c.one(pairs, i + 1, sh))) for i in range(0, len(pairs) - 1, 2)]
        n = len(conds[0][0]) if conds else 0
        hits = [j for j in range(n) if all(j < len(vals) and ok(vals[j]) for vals, ok in conds)]
        if kind.startswith("COUNT"):
            return len(hits)
        src = (sum_rng.vals if sum_rng is not None else conds[0][0])
        xs = [src[j] for j in hits if j < len(src) and isinstance(src[j], (int, float)) and not isinstance(src[j], bool)]
        if kind.startswith("AVERAGE"):
            if not xs:
                raise FErr("#DIV/0!")
            return sum(xs) / len(xs)
        return sum(xs)
    return f


def _sumproduct(c, A, sh):
    arrs = [c.area(a, sh).vals for a in A]
    if len({len(x) for x in arrs}) > 1:
        raise FErr("#VALUE!")
    tot = 0
    for vs in zip(*arrs):
        p = 1
        for v in vs:
            p *= v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0
        tot += p
    return tot


def _product(c, A, sh):
    p = 1
    for x in c.nums(A, sh):
        p *= x
    return p


def _match_pos(look, vals, mode):
    if mode == 0:
        ok = criteria(look) if isinstance(look, str) and re.search(r"[*?]", look) else (lambda v: compare(v, look, "=") and rank(v) == rank(look))
        for i, v in enumerate(vals):
            if ok(v):
                return i
        raise FErr("#N/A")
    best = None
    for i, v in enumerate(vals):
        if v is None or rank(v) != rank(look):
            continue
        if (mode == 1 and compare(v, look, "<=")) or (mode == -1 and compare(v, look, ">=")):
            best = i
        elif best is not None:
            break
    if best is None:
        raise FErr("#N/A")
    return best


def _vlookup(horiz):
    def f(c, A, sh):
        look, tbl = c.one(A, 0, sh), c.area(A[1], sh)
        idx = int(to_num(c.one(A, 2, sh)))
        approx = to_bool(c.one(A, 3, sh, True)) if len(A) > 3 else True
        rows = tbl.rows if not horiz else [list(x) for x in zip(*tbl.rows)]
        if idx < 1 or idx > (len(rows[0]) if rows else 0):
            raise FErr("#REF!")
        pos = _match_pos(look, [r[0] for r in rows], 1 if approx else 0)
        v = rows[pos][idx - 1]
        if isinstance(v, FErr):
            raise v
        return v
    return f


def _match(c, A, sh):
    look, vals = c.one(A, 0, sh), c.area(A[1], sh).vals
    mode = int(to_num(c.one(A, 2, sh, 1))) if len(A) > 2 else 1
    return _match_pos(look, vals, mode) + 1


def _index(c, A, sh):
    tbl = c.area(A[0], sh)
    r = int(to_num(c.one(A, 1, sh, 0))) if len(A) > 1 else 0
    k = int(to_num(c.one(A, 2, sh, 0))) if len(A) > 2 else 0
    if len(tbl.rows) == 1 and len(A) == 2:  # 한 줄 범위는 두 번째 인수가 열 위치
        r, k = 1, r
    if r < 0 or k < 0 or r > len(tbl.rows) or (tbl.rows and k > len(tbl.rows[0])):
        raise FErr("#REF!")
    v = tbl.rows[max(r, 1) - 1][max(k, 1) - 1]
    if isinstance(v, FErr):
        raise v
    return v


def _xlookup(c, A, sh):
    look, src, ret = c.one(A, 0, sh), c.area(A[1], sh).vals, c.area(A[2], sh)
    try:
        i = _match_pos(look, src, 0)
    except FErr:
        if len(A) > 3 and A[3] != ("lit", None):
            return c.one(A, 3, sh)
        raise
    rv = ret.rows[i] if len(ret.rows) == len(src) and len(ret.rows) > 1 else [ret.vals[i]] if len(ret.vals) == len(src) else None
    if rv is None:
        raise FErr("#VALUE!")
    v = rv[0]
    if isinstance(v, FErr):
        raise v
    return v


def _text1(fn):
    return lambda c, A, sh: fn(to_str(c.one(A, 0, sh)))


def _left(c, A, sh):
    return to_str(c.one(A, 0, sh))[: int(to_num(c.one(A, 1, sh, 1))) if len(A) > 1 else 1]


def _right(c, A, sh):
    s, n = to_str(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh, 1))) if len(A) > 1 else 1
    return s[-n:] if n else ""


def _mid(c, A, sh):
    s, st, n = to_str(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh))), int(to_num(c.one(A, 2, sh)))
    if st < 1 or n < 0:
        raise FErr("#VALUE!")
    return s[st - 1: st - 1 + n]


def _substitute(c, A, sh):
    s, old, new = to_str(c.one(A, 0, sh)), to_str(c.one(A, 1, sh)), to_str(c.one(A, 2, sh))
    if len(A) > 3:
        k = int(to_num(c.one(A, 3, sh)))
        idx = -1
        for _ in range(k):
            idx = s.find(old, idx + 1)
            if idx < 0:
                return s
        return s[:idx] + new + s[idx + len(old):]
    return s.replace(old, new) if old else s


def _find(ci):
    def f(c, A, sh):
        what, s = to_str(c.one(A, 0, sh)), to_str(c.one(A, 1, sh))
        st = int(to_num(c.one(A, 2, sh, 1))) if len(A) > 2 else 1
        if ci:
            rx = re.compile(re.escape(what).replace(r"\*", ".*").replace(r"\?", "."), re.I | re.S)
            m = rx.search(s, st - 1)
            if not m:
                raise FErr("#VALUE!")
            return m.start() + 1
        i = s.find(what, st - 1)
        if i < 0:
            raise FErr("#VALUE!")
        return i + 1
    return f


def _textjoin(c, A, sh):
    d, skip = to_str(c.one(A, 0, sh)), to_bool(c.one(A, 1, sh))
    parts = []
    for a in A[2:]:
        v = c.ev(a, sh)
        for x in (v.vals if isinstance(v, Rng) else [v]):
            s = to_str(x)
            if s or not skip:
                parts.append(s)
    return d.join(parts)


def _concat(c, A, sh):
    out = []
    for a in A:
        v = c.ev(a, sh)
        out.append("".join(to_str(x) for x in v.vals) if isinstance(v, Rng) else to_str(v))
    return "".join(out)


def _value(c, A, sh):
    v = c.one(A, 0, sh)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    n = parse_number_text(to_str(v))
    if n is None:
        raise FErr("#VALUE!")
    return n


def _text(c, A, sh):
    v, fmt = c.one(A, 0, sh), to_str(c.one(A, 1, sh))
    try:
        x = to_num(v)
    except FErr:
        return to_str(v)
    return format_value(x, fmt)


def _date(c, A, sh):
    y, m, d = (int(to_num(c.one(A, i, sh))) for i in range(3))
    base = dt.date(y if y >= 1900 else y + 1900, 1, 1)
    return serial(add_months(base, m - 1)) + d - 1


def _weekday(c, A, sh):
    d = date_of(c.one(A, 0, sh))
    t = int(to_num(c.one(A, 1, sh, 1))) if len(A) > 1 else 1
    w = d.isoweekday() % 7 + 1  # 일=1
    return w if t == 1 else d.isoweekday() if t == 2 else d.weekday() if t == 3 else w


def _eomonth(c, A, sh):
    d = add_months(date_of(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh))))
    nxt = add_months(dt.date(d.year, d.month, 1), 1)
    return serial(nxt) - 1


def _opt(c, A, i, sh, default):
    """생략할 수 있는 인수 - 없거나 비워 둔 칸(SORT(A1:B5,,-1))이면 default."""
    return default if i >= len(A) or A[i] == ("lit", None) else c.one(A, i, sh)


def _truthy(x):
    if isinstance(x, FErr):
        raise x
    if x is None or x == "":
        return False
    if isinstance(x, str):
        raise FErr("#VALUE!")
    return bool(to_num(x))


def _transpose_rows(rows):
    return [list(r) for r in zip(*rows)]


def _skey(v):
    """정렬 순서 - 숫자 < 글(대소문자 무시) < 논리 < 오류. 빈 칸은 따로 맨 뒤."""
    if isinstance(v, FErr):
        return (3, v.code)
    if isinstance(v, bool):
        return (2, v)
    if isinstance(v, (int, float)):
        return (0, v)
    return (1, str(v).lower())


def _sort_rows(rows, keys):
    """keys = [(행 → 값, 내림차순?)] - 안정 정렬, 빈 칸은 순서와 관계없이 맨 뒤."""
    import functools

    def cmp(a, b):
        for get, desc in keys:
            x, y = get(a), get(b)
            if x is None or y is None:
                if (x is None) != (y is None):
                    return 1 if x is None else -1
                continue
            kx, ky = _skey(x), _skey(y)
            if kx != ky:
                return (1 if kx > ky else -1) * (-1 if desc else 1)
        return 0
    return sorted(rows, key=functools.cmp_to_key(cmp))


def _filter(c, A, sh):
    arr, inc = c.area(A[0], sh), c.area(A[1], sh)
    rows = arr.rows
    h, w = len(rows), len(rows[0])
    if len(inc.rows) == h and len(inc.rows[0]) == 1:
        out = [rows[i] for i in range(h) if _truthy(inc.rows[i][0])]
    elif len(inc.rows) == 1 and len(inc.rows[0]) == w:
        keep = [j for j in range(w) if _truthy(inc.rows[0][j])]
        out = [[r[j] for j in keep] for r in rows] if keep else []
    else:
        raise FErr("#VALUE!")
    if not out:
        if len(A) > 2 and A[2] != ("lit", None):
            return c.ev(A[2], sh)
        raise FErr("#CALC!")
    return Rng(out)


def _sort(c, A, sh):
    rows = c.area(A[0], sh).rows
    idx, order, by_col = int(to_num(_opt(c, A, 1, sh, 1))), to_num(_opt(c, A, 2, sh, 1)), to_bool(_opt(c, A, 3, sh, False))
    if by_col:
        rows = _transpose_rows(rows)
    if idx < 1 or idx > len(rows[0]) or order not in (1, -1):
        raise FErr("#VALUE!")
    out = _sort_rows(rows, [(lambda r: r[idx - 1], order == -1)])
    return Rng(_transpose_rows(out) if by_col else out)


def _sortby(c, A, sh):
    rows = c.area(A[0], sh).rows
    h, w = len(rows), len(rows[0])
    keys, by_col = [], None
    for i in range(1, len(A), 2):
        b = c.area(A[i], sh)
        order = to_num(_opt(c, A, i + 1, sh, 1))
        if order not in (1, -1):
            raise FErr("#VALUE!")
        col = len(b.rows) == h and len(b.rows[0]) == 1 and h > 1 or (h == 1 and w == 1)
        row = len(b.rows) == 1 and len(b.rows[0]) == w
        if not (col or row) or (by_col is not None and by_col != (not col)):
            raise FErr("#VALUE!")
        by_col = not col
        keys.append((b.rows[0] if by_col else [r[0] for r in b.rows], order == -1))
    if not keys:
        raise FErr("#VALUE!")
    base = _transpose_rows(rows) if by_col else rows
    idx = _sort_rows(list(range(len(base))), [(lambda i, vals=vals: vals[i], desc) for vals, desc in keys])
    out = [base[i] for i in idx]
    return Rng(_transpose_rows(out) if by_col else out)


def _ukey(v):
    if isinstance(v, FErr):
        return ("e", v.code)
    if isinstance(v, bool):
        return ("b", v)
    if isinstance(v, (int, float)):
        return ("n", v)
    return ("z",) if v is None else ("s", str(v).lower())


def _unique(c, A, sh):
    rows = c.area(A[0], sh).rows
    by_col, once = to_bool(_opt(c, A, 1, sh, False)), to_bool(_opt(c, A, 2, sh, False))
    base = _transpose_rows(rows) if by_col else rows
    seen, order = {}, []
    for r in base:
        k = tuple(_ukey(v) for v in r)
        if k not in seen:
            seen[k] = [r, 0]
            order.append(k)
        seen[k][1] += 1
    out = [seen[k][0] for k in order if not once or seen[k][1] == 1]
    if not out:
        raise FErr("#CALC!")
    return Rng(_transpose_rows(out) if by_col else out)


def _sequence(c, A, sh):
    h, w = int(to_num(c.one(A, 0, sh))), int(to_num(_opt(c, A, 1, sh, 1)))
    start, step = to_num(_opt(c, A, 2, sh, 1)), to_num(_opt(c, A, 3, sh, 1))
    if h < 1 or w < 1:
        raise FErr("#CALC!")
    if h * w > 100000:
        raise FErr("#NUM!")
    return Rng([[start + step * (i * w + j) for j in range(w)] for i in range(h)])


def _is(test):
    def f(c, A, sh):
        try:
            v = c.one(A, 0, sh)
        except FErr as e:
            return test(e)
        return test(v)
    return f


FUNCS = {
    "SUM": _sum, "AVERAGE": _avg, "MEDIAN": _median, "PRODUCT": _product,
    "MIN": lambda c, A, sh: min(c.nums(A, sh), default=0), "MAX": lambda c, A, sh: max(c.nums(A, sh), default=0),
    "COUNT": lambda c, A, sh: len(c.nums(A, sh, "count")), "COUNTA": lambda c, A, sh: len(c.nums(A, sh, "counta")),
    "COUNTBLANK": lambda c, A, sh: len(c.nums(A, sh, "blank")),
    "SUMIF": _ifagg("SUMIF"), "SUMIFS": _ifagg("SUMIFS"), "COUNTIF": _ifagg("COUNTIF"), "COUNTIFS": _ifagg("COUNTIFS"),
    "AVERAGEIF": _ifagg("AVERAGEIF"), "AVERAGEIFS": _ifagg("AVERAGEIFS"), "SUMPRODUCT": _sumproduct,
    "ROUND": lambda c, A, sh: round_x(to_num(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh, 0)))),
    "ROUNDUP": lambda c, A, sh: round_x(to_num(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh, 0))), "up"),
    "ROUNDDOWN": lambda c, A, sh: round_x(to_num(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh, 0))), "down"),
    "INT": lambda c, A, sh: math.floor(to_num(c.one(A, 0, sh))), "ABS": lambda c, A, sh: abs(to_num(c.one(A, 0, sh))),
    "MOD": lambda c, A, sh: _mod(to_num(c.one(A, 0, sh)), to_num(c.one(A, 1, sh))),
    "IF": _if, "IFS": _ifs, "IFERROR": _iferror, "IFNA": _ifna, "SWITCH": _switch, "CHOOSE": _choose,
    "AND": lambda c, A, sh: all(to_bool(c.one(A, i, sh)) for i in range(len(A))),
    "OR": lambda c, A, sh: any(to_bool(c.one(A, i, sh)) for i in range(len(A))),
    "NOT": lambda c, A, sh: not to_bool(c.one(A, 0, sh)),
    "VLOOKUP": _vlookup(False), "HLOOKUP": _vlookup(True), "MATCH": _match, "INDEX": _index, "XLOOKUP": _xlookup,
    "CONCAT": _concat, "CONCATENATE": _concat, "TEXTJOIN": _textjoin,
    "LEFT": _left, "RIGHT": _right, "MID": _mid, "LEN": _text1(len), "TRIM": _text1(lambda s: re.sub(r" +", " ", s.strip(" "))),
    "UPPER": _text1(str.upper), "LOWER": _text1(str.lower), "SUBSTITUTE": _substitute, "FIND": _find(False), "SEARCH": _find(True),
    "VALUE": _value, "TEXT": _text,
    "TODAY": lambda c, A, sh: serial(dt.date.today()),
    "NOW": lambda c, A, sh: serial(dt.date.today()) + (dt.datetime.now() - dt.datetime.combine(dt.date.today(), dt.time())).seconds / 86400,
    "DATE": _date, "YEAR": lambda c, A, sh: date_of(c.one(A, 0, sh)).year, "MONTH": lambda c, A, sh: date_of(c.one(A, 0, sh)).month,
    "DAY": lambda c, A, sh: date_of(c.one(A, 0, sh)).day, "WEEKDAY": _weekday,
    "EDATE": lambda c, A, sh: serial(add_months(date_of(c.one(A, 0, sh)), int(to_num(c.one(A, 1, sh))))), "EOMONTH": _eomonth,
    "ROW": _row_col(0), "COLUMN": _row_col(1), "ROWS": _rows_cols(0), "COLUMNS": _rows_cols(1),
    "INDIRECT": _indirect, "OFFSET": _offset, "SUBTOTAL": _subtotal,
    "FILTER": _filter, "SORT": _sort, "SORTBY": _sortby, "UNIQUE": _unique, "SEQUENCE": _sequence,
    "TRANSPOSE": lambda c, A, sh: Rng(_transpose_rows(c.area(A[0], sh).rows)),
    "HYPERLINK": lambda c, A, sh: c.one(A, 1, sh) if len(A) > 1 else c.one(A, 0, sh),  # 링크는 화면에서 열지 않는다 - 보이는 글만
    "ISBLANK": _is(lambda v: v is None or v == ""), "ISNUMBER": _is(lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)),
    "ISTEXT": _is(lambda v: isinstance(v, str)), "ISERROR": _is(lambda v: isinstance(v, FErr)), "ISNA": _is(lambda v: isinstance(v, FErr) and v.code == "#N/A"),
}


SCALAR = {"ISNUMBER", "ISTEXT", "ISBLANK", "ISERROR", "ISNA", "SEARCH", "FIND", "LEFT", "RIGHT", "MID", "LEN", "TRIM", "UPPER", "LOWER", "SUBSTITUTE",
          "VALUE", "TEXT", "ABS", "INT", "ROUND", "ROUNDUP", "ROUNDDOWN", "MOD", "YEAR", "MONTH", "DAY", "NOT"}


def _mod(a, b):
    if b == 0:
        raise FErr("#DIV/0!")
    return a - b * math.floor(a / b)


# ---------------------------------------------------------------- 표시 형식(TEXT 함수·화면 표시와 같은 규칙의 하위 집합)
def format_value(v, fmt):
    secs = fmt.split(";")
    sec = secs[0]
    neg = v < 0
    if neg and len(secs) > 1 and secs[1]:
        sec, v, neg = secs[1], -v, False
    bare = re.sub(r'"[^"]*"', "", sec)
    if re.search(r"[yd]|mm(?!.*0)", bare, re.I) and not re.search(r"[#0]", bare):
        d = DAY0 + dt.timedelta(days=v)
        out = re.sub(r'"([^"]*)"', r"\1", sec)
        out = re.sub("yyyy", f"{d.year}", out, flags=re.I)
        out = re.sub("yy", f"{d.year % 100:02d}", out, flags=re.I)
        out = out.replace("mm", f"{d.month:02d}")
        out = re.sub(r"(?<![A-Za-z])m(?![A-Za-z])", str(d.month), out)
        out = re.sub("dd", f"{d.day:02d}", out, flags=re.I)
        out = re.sub(r"(?<![A-Za-z])d(?![A-Za-z])", str(d.day), out, flags=re.I)
        return out
    m = re.search(r"([#0,]*0|#[#,]*)(\.([0#]+))?", sec)
    if not m:
        return general(v)
    pct = "%" in sec
    x = abs(v * 100 if pct else v)
    dec = m.group(3) or ""
    mind, maxd = dec.count("0"), len(dec)
    s = f"{round_x(x, maxd):.{maxd}f}"
    if maxd > mind:
        s = re.sub(rf"0{{1,{maxd - mind}}}$", "", s).rstrip(".")
    if "," in m.group(1):
        i, _, d = s.partition(".")
        s = f"{int(i):,}" + (f".{d}" if d else "")

    def lit(t):
        return re.sub(r'"([^"]*)"|([^"]+)', lambda q: q.group(1) if q.group(1) is not None else re.sub(r"[#0,?]", "", q.group(2).replace("\\", "")), t)
    return ("-" if neg and round_x(x, maxd) != 0 else "") + lit(sec[:m.start()]) + s + lit(sec[m.end():])


# ---------------------------------------------------------------- 문서 전체 계산
def recalc(doc):
    """모든 탭의 수식을 계산해 v 에 넣는다(오류는 "#…" 문자열). 바뀐 셀 수."""
    c = Calc(doc)
    changed = 0
    no_tables = not any(s.get("tables") for s in doc.get("sheets") or [])
    for sh in doc.get("sheets") or []:
        for k, raw in (sh.get("cells") or {}).items():
            if isinstance(raw, dict) and raw.get("f"):
                v = c.cell(sh, k)
                v = v.code if isinstance(v, FErr) else v
                if v == "#NAME?" and raw.get("v") not in (None, "#NAME?") and (unknown_fn(raw["f"]) or unknown_name(raw["f"], c, sh)):
                    continue  # 매크로(VBA) 사용자 함수·정의를 모르는 이름 - 계산할 수 없어 엑셀이 마지막에 계산한 값을 그대로 둔다
                if v == "#REF!" and no_tables and "[" in raw["f"] and raw.get("v") not in (None, "#REF!"):
                    continue  # 표 정의 없이 가져온 옛 문서의 구조적 참조 - 엑셀 값을 그대로
                if raw.get("v") != v:
                    raw["v"] = v
                    changed += 1
    return changed + sync_spill(doc, c)


def _let(c, A, sh):
    """LET(이름1, 값1, …, 계산) - 이름은 뒤의 값·계산에서 쓴다."""
    if len(A) < 3 or len(A) % 2 == 0:
        raise FErr("#VALUE!")
    c.scope.append({})
    try:
        for i in range(0, len(A) - 1, 2):
            if A[i][0] != "name":
                raise FErr("#NAME?")
            c.scope[-1][A[i][1]] = _cellv(lambda i=i: c.ev(A[i + 1], sh))
        return c.ev(A[-1], sh)
    finally:
        c.scope.pop()


def _datedif(c, A, sh):
    a, b, u = date_of(c.one(A, 0, sh)), date_of(c.one(A, 1, sh)), to_str(c.one(A, 2, sh)).upper()
    if a > b:
        raise FErr("#NUM!")
    months = (b.year - a.year) * 12 + b.month - a.month - (1 if b.day < a.day else 0)
    if u == "Y":
        return months // 12
    if u == "M":
        return months
    if u == "D":
        return (b - a).days
    if u == "YM":
        return months % 12
    if u == "MD":
        return (b - add_months(a, months)).days
    if u == "YD":
        k = (b.year - a.year) - (1 if (b.month, b.day) < (a.month, a.day) else 0)
        return (b - add_months(a, 12 * k)).days
    raise FErr("#NUM!")


def _holidays(c, A, i, sh):
    if i >= len(A) or A[i] == ("lit", None):
        return set()
    return {int(to_num(v)) for v in c.area(A[i], sh).vals if v not in (None, "")}


def _networkdays(c, A, sh):
    a, b = int(to_num(c.one(A, 0, sh))), int(to_num(c.one(A, 1, sh)))
    hol, sign = _holidays(c, A, 2, sh), 1
    if a > b:
        a, b, sign = b, a, -1
    return sign * sum(1 for d in range(a, b + 1) if date_of(d).weekday() < 5 and d not in hol)


def _workday(c, A, sh):
    d, n = int(to_num(c.one(A, 0, sh))), int(to_num(c.one(A, 1, sh)))
    hol, step = _holidays(c, A, 2, sh), 1 if n >= 0 else -1
    while n:
        d += step
        if date_of(d).weekday() < 5 and d not in hol:
            n -= step
    return d


def _xmatch(c, A, sh):
    look, vals = c.one(A, 0, sh), c.area(A[1], sh).vals
    mode, order = int(to_num(_opt(c, A, 2, sh, 0))), int(to_num(_opt(c, A, 3, sh, 1)))
    idx = list(range(len(vals)))[::-1 if order < 0 else 1]
    if mode == 2:
        ok = criteria(look)
        hit = next((i for i in idx if ok(vals[i])), None)
    else:
        hit = next((i for i in idx if vals[i] is not None and rank(vals[i]) == rank(look) and compare(vals[i], look, "=")), None)
        if hit is None and mode in (1, -1):
            cand = [i for i in idx if vals[i] is not None and rank(vals[i]) == rank(look) and compare(vals[i], look, ">" if mode == 1 else "<")]
            if cand:
                hit = cand[0]
                for i in cand:
                    if compare(vals[i], vals[hit], "<" if mode == 1 else ">"):
                        hit = i
    if hit is None:
        raise FErr("#N/A")
    return hit + 1


def _rows(c, A, i, sh):
    return [list(r) for r in c.area(A[i], sh).rows]


def _take_drop(drop):
    def f(c, A, sh):
        rows = _rows(c, A, 0, sh)
        h, w = len(rows), len(rows[0])
        r = _opt(c, A, 1, sh, None)
        k = _opt(c, A, 2, sh, None)

        def cut(n, size):
            if n is None:
                return 0, size
            n = int(to_num(n))
            if drop:
                return (n, size) if n >= 0 else (0, size + n)
            return (0, n) if n >= 0 else (size + n, size)
        r1, r2 = cut(r, h)
        c1, c2 = cut(k, w)
        out = [row[max(c1, 0):max(c2, 0)] for row in rows[max(r1, 0):max(r2, 0)]]
        if not out or not out[0]:
            raise FErr("#CALC!")
        return Rng(out)
    return f


def _choose(cols):
    def f(c, A, sh):
        rows = _rows(c, A, 0, sh)
        size = len(rows[0]) if cols else len(rows)
        idx = []
        for i in range(1, len(A)):
            for v in c.area(A[i], sh).vals:
                n = int(to_num(v))
                if n == 0 or abs(n) > size:
                    raise FErr("#VALUE!")
                idx.append(n - 1 if n > 0 else size + n)
        if not idx:
            raise FErr("#VALUE!")
        return Rng([[r[j] for j in idx] for r in rows] if cols else [rows[j] for j in idx])
    return f


def _stack(horiz):
    def f(c, A, sh):
        parts = [_rows(c, A, i, sh) for i in range(len(A))]
        if horiz:
            h = max(len(p) for p in parts)
            return Rng([[x for p in parts for x in (p[i] if i < len(p) else [FErr("#N/A")] * len(p[0]))] for i in range(h)])
        w = max(len(p[0]) for p in parts)
        return Rng([r + [FErr("#N/A")] * (w - len(r)) for p in parts for r in p])
    return f


def _to_line(col):
    def f(c, A, sh):
        rows = _rows(c, A, 0, sh)
        ignore = int(to_num(_opt(c, A, 1, sh, 0)))
        by_col = to_bool(_opt(c, A, 2, sh, False))
        vals = [r[j] for j in range(len(rows[0])) for r in rows] if by_col else [x for r in rows for x in r]
        vals = [x for x in vals if not ((ignore in (1, 3) and x is None) or (ignore in (2, 3) and isinstance(x, FErr)))]
        if not vals:
            raise FErr("#CALC!")
        return Rng([[x] for x in vals] if col else [vals])
    return f


def _textsplit(c, A, sh):
    text = to_str(c.one(A, 0, sh))
    cd = to_str(_opt(c, A, 1, sh, ""))
    rd = _opt(c, A, 2, sh, None)
    skip = to_bool(_opt(c, A, 3, sh, False))
    pad = _opt(c, A, 5, sh, FErr("#N/A")) if len(A) > 5 and A[5] != ("lit", None) else FErr("#N/A")
    lines = text.split(to_str(rd)) if rd not in (None, "") else [text]
    rows = [(ln.split(cd) if cd else [ln]) for ln in lines]
    if skip:
        rows = [[x for x in r if x != ""] for r in rows]
        rows = [r for r in rows if r]
    if not rows:
        raise FErr("#CALC!")
    w = max(len(r) for r in rows)
    return Rng([r + [pad] * (w - len(r)) for r in rows])


FUNCS.update({"TAKE": _take_drop(False), "DROP": _take_drop(True), "CHOOSECOLS": _choose(True), "CHOOSEROWS": _choose(False),
              "HSTACK": _stack(True), "VSTACK": _stack(False), "TOCOL": _to_line(True), "TOROW": _to_line(False), "TEXTSPLIT": _textsplit})
FUNCS.update({"LET": _let, "DATEDIF": _datedif, "NETWORKDAYS": _networkdays, "WORKDAY": _workday, "XMATCH": _xmatch})

# ---------------------------------------------------------------- LAMBDA (엑셀 365) - 값으로 넘기는 함수. MAP·BYROW·BYCOL·REDUCE·SCAN·MAKEARRAY·GROUPBY 가 부르고,
# LET 이름·이름 정의(이름 관리자 사용자 함수 =세후(금액))에 담으면 f(값) 으로 부른다
class Lam:
    def __init__(self, params, body, scope):
        self.params, self.body, self.scope = params, body, scope  # 매개변수 이름 · 본문 · 만든 곳의 LET 이름 묶음


def _lambda(c, A, sh):
    if not A or any(a[0] != "name" for a in A[:-1]):
        raise FErr("#VALUE!")
    return Lam([a[1] for a in A[:-1]], A[-1], list(c.scope))


def _scalar(v):
    """LAMBDA 결과 한 칸 - 1×1 배열은 값, 더 크면 #CALC!(엑셀: 배열의 배열은 안 된다)."""
    if isinstance(v, Rng):
        if len(v.vals) != 1:
            raise FErr("#CALC!")
        v = v.vals[0]
    if isinstance(v, FErr):
        raise v
    return v


def _lam_arg(c, A, i, sh):
    f = c.ev(A[i], sh) if i < len(A) else None
    if not isinstance(f, Lam):
        raise FErr("#VALUE!")
    return f


def _map(c, A, sh):
    if len(A) < 2:
        raise FErr("#VALUE!")
    f, arrs = _lam_arg(c, A, len(A) - 1, sh), [c.area(a, sh) for a in A[:-1]]
    h, w = len(arrs[0].rows), len(arrs[0].rows[0])
    if any(len(a.rows) != h or len(a.rows[0]) != w for a in arrs):
        raise FErr("#VALUE!")
    return Rng([[_cellv(lambda i=i, j=j: _scalar(c.call(f, [a.rows[i][j] for a in arrs], sh))) for j in range(w)] for i in range(h)])


def _by(rows_):
    def f(c, A, sh):
        rows, lam = c.area(A[0], sh).rows, _lam_arg(c, A, 1, sh)
        if rows_:
            return Rng([[_cellv(lambda r=r: _scalar(c.call(lam, [Rng([r])], sh)))] for r in rows])
        return Rng([[_cellv(lambda j=j: _scalar(c.call(lam, [Rng([[r[j]] for r in rows])], sh))) for j in range(len(rows[0]))]])
    return f


def _reduce(scan):
    def f(c, A, sh):
        acc = _opt(c, A, 0, sh, 0)
        arr, lam = c.area(A[1], sh), _lam_arg(c, A, 2, sh)
        out = []
        for row in arr.rows:
            line = []
            for v in row:
                acc = _scalar(c.call(lam, [acc, v], sh))
                line.append(acc)
            out.append(line)
        return Rng(out) if scan else acc
    return f


def _makearray(c, A, sh):
    h, w, lam = int(to_num(c.one(A, 0, sh))), int(to_num(c.one(A, 1, sh))), _lam_arg(c, A, 2, sh)
    if h < 1 or w < 1:
        raise FErr("#VALUE!")
    if h * w > 100000:
        raise FErr("#NUM!")
    return Rng([[_cellv(lambda i=i, j=j: _scalar(c.call(lam, [i + 1, j + 1], sh))) for j in range(w)] for i in range(h)])


FUNCS.update({"LAMBDA": _lambda, "MAP": _map, "BYROW": _by(True), "BYCOL": _by(False), "REDUCE": _reduce(False), "SCAN": _reduce(True), "MAKEARRAY": _makearray})

# ---------------------------------------------------------------- 수식형 요약 GROUPBY·PIVOTBY (엑셀 365) - 집계는 함수 이름(SUM, 파일에는 _xleta.SUM) 또는 LAMBDA
AGG = ("SUM", "AVERAGE", "COUNT", "COUNTA", "MAX", "MIN", "MEDIAN", "PRODUCT")


def _agg_fn(c, n, sh):
    """집계 - 함수 이름(SUM·_xleta.SUM) 또는 LAMBDA(값 열을 받아 한 값)."""
    nm = re.sub(r"^_XLETA\.", "", n[1]) if n[0] == "name" else None
    if nm in AGG:
        return nm
    f = c.ev(n, sh)
    if not isinstance(f, Lam):
        raise FErr("#VALUE!")
    return f


def _agg(c, fn, vals, sh):
    """값 목록을 범위처럼(빈 칸·글은 건너뜀) 집계 - 오류는 그 칸만."""
    try:
        if isinstance(fn, Lam):
            return _scalar(c.call(fn, [Rng([[v] for v in vals] or [[None]])], sh))
        return FUNCS[fn](c, [("arr", Rng([[v] for v in vals] or [[None]]))], sh)
    except FErr as e:
        return e


def _fields(c, A, i_hdr, keys, vals, sh):
    """머리글 인수(생략 = 값 첫 줄이 글이고 둘째 줄이 숫자면 머리글) → (머리글이 있나, 보이나, 키 머리글, 값 머리글, 키, 값)."""
    hdr = _opt(c, A, i_hdr, sh, None)
    if hdr is None:
        hdr = 1 if len(vals) > 1 and isinstance(vals[0][0], str) and isinstance(vals[1][0], (int, float)) and not isinstance(vals[1][0], bool) else 0
    hdr = int(to_num(hdr))
    if hdr not in (0, 1, 3):
        raise FErr("#VALUE!")  # 2(머리글 만들기)는 아직
    if hdr in (1, 3):
        return True, hdr == 3, keys[0], vals[0], keys[1:], vals[1:]
    return False, False, None, None, keys, vals


def _picked(c, A, i, n, sh):
    """거르기 배열(행마다 참·거짓) → 남길 행 번호."""
    if i >= len(A) or A[i] == ("lit", None):
        return list(range(n))
    f = c.area(A[i], sh).rows
    if len(f) != n:
        raise FErr("#VALUE!")
    return [k for k in range(n) if _truthy(f[k][0])]


def _groups(rows, idx):
    """같은 키(대소문자 무시)끼리 - 처음 나온 순서, (보이는 키, 행 번호들)."""
    seen, out = {}, []
    for k in idx:
        key = tuple(_ukey(v) for v in rows[k])
        if key not in seen:
            seen[key] = (["" if v is None else v for v in rows[k]], [])
            out.append(seen[key])
        seen[key][1].append(k)
    return out


def _groupby(c, A, sh):
    """GROUPBY(행 필드, 값, 함수, [머리글], [합계 깊이 1], [정렬 1], [거르기])."""
    keys, vals = c.area(A[0], sh).rows, c.area(A[1], sh).rows
    fn = _agg_fn(c, A[2], sh)
    if len(keys) != len(vals):
        raise FErr("#VALUE!")
    has, show, kh, vh, keys, vals = _fields(c, A, 3, keys, vals, sh)
    depth, order = int(to_num(_opt(c, A, 4, sh, 1))), int(to_num(_opt(c, A, 5, sh, 1)))
    idx = _picked(c, A, 6, len(keys), sh)
    kw, vw = len(keys[0]), len(vals[0])
    out = [disp + [_agg(c, fn, [vals[i][j] for i in ks], sh) for j in range(vw)] for disp, ks in _groups(keys, idx)]
    if not out:
        raise FErr("#CALC!")
    if order:
        if abs(order) > kw + vw:
            raise FErr("#VALUE!")
        out = _sort_rows(out, [(lambda r, k=abs(order) - 1: r[k], order < 0)])
    if depth:
        tot = ["Total"] + [""] * (kw - 1) + [_agg(c, fn, [vals[i][j] for i in idx], sh) for j in range(vw)]
        out = [tot] + out if depth < 0 else out + [tot]
    if show:
        out = [list(kh) + list(vh)] + out
    return Rng(out)


def _pivotby(c, A, sh):
    """PIVOTBY(행 필드, 열 필드, 값, 함수, [머리글], [행 합계 1], [행 정렬 1], [열 합계 1], [열 정렬 1], [거르기]) - 필드·값은 한 열씩."""
    rk, ck, vals = c.area(A[0], sh).rows, c.area(A[1], sh).rows, c.area(A[2], sh).rows
    fn = _agg_fn(c, A[3], sh)
    if not (len(rk) == len(ck) == len(vals)) or len(rk[0]) != 1 or len(ck[0]) != 1 or len(vals[0]) != 1:
        raise FErr("#VALUE!")  # 여러 열 필드·값은 아직
    has, _, _, _, rk2, vals2 = _fields(c, A, 4, rk, vals, sh)
    ck = ck[1:] if has else ck
    rk, vals = rk2, vals2
    rt, ro, ct, co = (int(to_num(_opt(c, A, i, sh, 1))) for i in (5, 6, 7, 8))
    if ro not in (1, -1) or co not in (1, -1):
        raise FErr("#VALUE!")  # 값 열로 정렬은 아직
    idx = _picked(c, A, 9, len(rk), sh)
    rows = _sort_rows(_groups(rk, idx), [(lambda g: g[0][0], ro < 0)])
    cols = _sort_rows(_groups(ck, idx), [(lambda g: g[0][0], co < 0)])
    if not rows or not cols:
        raise FErr("#CALC!")
    v = lambda ks: _agg(c, fn, [vals[i][0] for i in ks], sh)  # noqa: E731
    cell = lambda a, b: v([i for i in a if i in set(b)]) if set(a) & set(b) else ""  # noqa: E731
    out = [[""] + [g[0][0] for g in cols] + (["Total"] if ct else [])]
    body = [[g[0][0]] + [cell(g[1], h[1]) for h in cols] + ([v(g[1])] if ct else []) for g in rows]
    if rt:
        tot = ["Total"] + [v(h[1]) for h in cols] + ([v(idx)] if ct else [])
        body = [tot] + body if rt < 0 else body + [tot]
    return Rng(out + body)


FUNCS.update({"GROUPBY": _groupby, "PIVOTBY": _pivotby})


def dynamic(raw):
    """동적 배열 수식인가 - 가져온 동적 배열(da) 이거나 FILTER·SORT·UNIQUE·SEQUENCE … 를 쓴 수식."""
    if not isinstance(raw, dict) or not raw.get("f"):
        return False
    if raw.get("da"):
        return True
    f = raw["f"]
    try:
        return any((t[0] == "fn" and t[1] in DYN) or (t[0] == "ref" and len(t) > 3) for t in tokenize(f[1:] if f.startswith("=") else f))
    except FErr:
        return False


def sync_spill(doc, c):
    """계산기의 넘친 값 → 칸 {v, sp: 기준 칸}. 더는 넘치지 않는 칸은 비운다(기준 칸 오른쪽·아래이거나 기준이 없어졌으면)
    - 다른 곳에 복사돼 온 sp 칸은 값만 남긴다. 바뀐 칸 수."""
    changed = 0
    for sh in doc.get("sheets") or []:
        sid, cells = sh.get("id"), sh.get("cells") or {}
        new = {f"{col_name(cc)}{r + 1}": hit for (s, r, cc), hit in c.spill.items() if s == sid}
        for k, raw in list(cells.items()):
            if not isinstance(raw, dict) or not raw.get("sp") or k in new:
                continue
            a, p, ap = cells.get(raw["sp"]), parse_ref(k), parse_ref(raw["sp"])
            gone = not (isinstance(a, dict) and a.get("f")) or (p and ap and p[0] >= ap[0] and p[1] >= ap[1])
            raw.pop("sp")
            if gone:
                raw.pop("v", None)
                if not raw:
                    del cells[k]
            changed += 1
        for k, (v, a) in new.items():
            raw = cells.get(k)
            if not isinstance(raw, dict):
                raw = cells[k] = {}
            v = v.code if isinstance(v, FErr) else fix(v) if isinstance(v, float) else v
            if raw.get("v") != v or raw.get("sp") != a:
                raw["v"], raw["sp"] = v, a
                changed += 1
    return changed


def unknown_fn(f):
    """수식에 계산기가 모르는 함수(매크로 사용자 함수 등)가 있나 - 읽지 못하는 수식(외부 통합 문서 참조 등)도."""
    src = f[1:] if f.startswith("=") else f
    try:
        parse(src)
        return any(t[0] == "fn" and t[1] not in FUNCS for t in tokenize(src))
    except FErr:
        return True


def unknown_name(f, c, sh):
    """수식에 정의를 모르는 이름이 있나 - 이름 정의(names) 없이 가져온 문서. LET 이름도 여기 들지만 #NAME? 일 때만 묻는다."""
    try:
        return any(t[0] == "name" and c.named(t[1].upper(), sh) is None for t in tokenize(f[1:] if f.startswith("=") else f))
    except FErr:
        return True


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description="시트 수식 계산 - 오류 셀 찾기")
    ap.add_argument("deck")
    ap.add_argument("--cell", help="탭!B3 (탭을 빼면 첫 탭)")
    a = ap.parse_args()
    from common import load_deck, safe_id
    if not safe_id(a.deck):
        sys.exit("잘못된 id")
    doc = load_deck(a.deck)
    if doc.get("kind") != "sheet":
        sys.exit("시트 문서가 아니다")
    if a.cell:
        tab, _, ref = a.cell.rpartition("!")
        sh = next((s for s in doc["sheets"] if s.get("name") == tab or s.get("id") == tab), doc["sheets"][0]) if tab else doc["sheets"][0]
        c = Calc(doc)
        raw = sh.get("cells", {}).get(ref.upper())
        v = c.cell(sh, ref.upper()) if isinstance(raw, dict) and raw.get("f") else (raw.get("v") if isinstance(raw, dict) else raw)
        print(json.dumps(v.code if isinstance(v, FErr) else v, ensure_ascii=False))
        return
    recalc(doc)
    bad = [(s["name"], k, r["v"], r["f"]) for s in doc["sheets"] for k, r in (s.get("cells") or {}).items() if isinstance(r, dict) and r.get("f") and r.get("v") in ERRS]
    n = sum(1 for s in doc["sheets"] for r in (s.get("cells") or {}).values() if isinstance(r, dict) and r.get("f"))
    print(f"수식 {n}개 · 오류 {len(bad)}개")
    for t, k, v, f in bad[:40]:
        print(f"  {t}!{k}: {v}   {f}")


if __name__ == "__main__":
    main()
