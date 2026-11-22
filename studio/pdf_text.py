# -*- coding: utf-8 -*-
"""표준 라이브러리만으로 PDF 의 글을 꺼낸다 - PyMuPDF·pypdf 가 없을 때 import_doc 의 마지막 대체 경로.

    from pdf_text import read
    doc = read(path)   # {"pages": [{"text": …, "jpegs": [bytes…]}], "meta": {…}, "toc": [{"level", "title", "page"}]}

할 수 있는 것: 객체·객체 스트림(PDF 1.5+) 훑기, FlateDecode·ASCIIHex·ASCII85 풀기, 글꼴 ToUnicode(CMap) 로 한글 등 유니코드 복원,
쪽·양식(Form XObject) 안의 글, 책갈피(목차), JPEG(DCTDecode) 그림 꺼내기.
못 하는 것: 암호가 걸린 PDF(빈 암호 포함), ToUnicode 가 없는 CID 글꼴의 글(코드만 있어 글자로 못 바꾼다), 표 구조, LZW 등 드문 압축.
글 순서는 내용 스트림 순서다(화면 위치로 다시 정렬하지 않는다) - 줄은 글 위치(y)가 바뀌면 나눈다.
"""
import base64
import re
import zlib

_WS = b" \t\r\n\f\x00"
_DELIM = b"()<>[]{}/%"


class _Name(str):
    """/이름."""


class _Kw(str):
    """키워드·연산자(obj, R, Tj, [, << …)."""


class _Ref(tuple):
    """간접 참조 (번호, 세대)."""


_NONE = object()


class _Lex:
    """PDF 토큰 읽개 - 바이트에서 수·이름·문자열(bytes)·키워드를 차례로."""

    def __init__(self, data, pos=0):
        self.d, self.i = data, pos

    def skip(self):
        d, n = self.d, len(self.d)
        while self.i < n:
            c = d[self.i]
            if c in _WS:
                self.i += 1
            elif c == 0x25:  # % 주석은 줄 끝까지
                while self.i < n and d[self.i] not in (10, 13):
                    self.i += 1
            else:
                break

    def token(self):
        self.skip()
        d, i, n = self.d, self.i, len(self.d)
        if i >= n:
            return None
        c = d[i]
        if c == 0x2F:  # /이름 (#xx 는 바이트)
            j = i + 1
            while j < n and d[j] not in _WS and d[j] not in _DELIM:
                j += 1
            self.i = j
            return _Name(re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), d[i + 1:j]).decode("latin-1"))
        if c == 0x28:
            return self._literal()
        if c == 0x3C:
            if d[i + 1:i + 2] == b"<":
                self.i = i + 2
                return _Kw("<<")
            j = d.find(b">", i)
            j = n if j < 0 else j
            self.i = j + 1
            h = re.sub(rb"[^0-9A-Fa-f]", b"", d[i + 1:j])
            return bytes.fromhex((h + b"0" if len(h) % 2 else h).decode())
        if c == 0x3E and d[i + 1:i + 2] == b">":
            self.i = i + 2
            return _Kw(">>")
        if c in b"[]{}":
            self.i = i + 1
            return _Kw(chr(c))
        j = i
        while j < n and d[j] not in _WS and d[j] not in _DELIM:
            j += 1
        j = j if j > i else i + 1  # 짝 없는 ')' '>' 는 한 글자 키워드로 넘긴다
        self.i = j
        w = d[i:j]
        if re.fullmatch(rb"[+-]?\d+", w):
            return int(w)
        if re.fullmatch(rb"[+-]?(\d+\.\d*|\.\d+|\d+\.)", w):
            return float(w)
        return _Kw(w.decode("latin-1"))

    def _literal(self):
        d, n = self.d, len(self.d)
        i, depth, out = self.i + 1, 1, bytearray()
        esc = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
        while i < n:
            c = d[i]
            if c == 0x5C:  # \ 이스케이프
                i += 1
                if i >= n:
                    break
                c = d[i]
                if c in esc:
                    out.append(esc[c])
                elif 0x30 <= c <= 0x37:  # \ddd 8진수
                    k = i
                    while k < n and k < i + 3 and 0x30 <= d[k] <= 0x37:
                        k += 1
                    out.append(int(d[i:k], 8) & 0xFF)
                    i = k - 1
                elif c == 13:  # 줄 이음
                    if d[i + 1:i + 2] == b"\n":
                        i += 1
                elif c != 10:
                    out.append(c)
            elif c == 0x28:
                depth += 1
                out.append(c)
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    i += 1
                    break
                out.append(c)
            else:
                out.append(c)
            i += 1
        self.i = i
        return bytes(out)


def _obj(lx, t=_NONE, depth=0):
    """토큰 하나로 시작하는 객체 - dict·list·_Ref·수·bytes·_Name·bool·None, 그 밖의 키워드는 _Kw 그대로."""
    t = lx.token() if t is _NONE else t
    if isinstance(t, _Kw):
        if t == "<<" and depth < 64:
            out = {}
            while True:
                k = lx.token()
                if k is None or (isinstance(k, _Kw) and k == ">>"):
                    return out
                if isinstance(k, _Name):
                    out[str(k)] = _obj(lx, depth=depth + 1)
        if t == "[" and depth < 64:
            out = []
            while True:
                x = lx.token()
                if x is None or (isinstance(x, _Kw) and x == "]"):
                    return out
                out.append(_obj(lx, x, depth + 1))
        return {"true": True, "false": False, "null": None}.get(t, t)
    if isinstance(t, int):  # 번호 세대 R
        save = lx.i
        g = lx.token()
        if isinstance(g, int) and g >= 0:
            r = lx.token()
            if isinstance(r, _Kw) and r == "R":
                return _Ref((t, g))
        lx.i = save
    return t


def _decode(dct, raw):
    """스트림 풀기 - 모르는 압축이면 None."""
    flt = dct.get("Filter")
    for f in (flt if isinstance(flt, list) else [flt] if flt else []):
        if f in ("FlateDecode", "Fl"):
            try:
                raw = zlib.decompressobj().decompress(raw)  # 끝이 잘린 스트림도 읽은 데까지
            except zlib.error:
                return None
        elif f in ("ASCIIHexDecode", "AHx"):
            h = re.sub(rb"[^0-9A-Fa-f]", b"", raw.split(b">")[0])
            raw = bytes.fromhex((h + b"0" if len(h) % 2 else h).decode())
        elif f in ("ASCII85Decode", "A85"):
            s = raw.strip()
            s = s[2:] if s.startswith(b"<~") else s
            try:
                raw = base64.a85decode(s.split(b"~>")[0])
            except ValueError:
                return None
        else:
            return None
    return raw


def _pdfstr(b):
    """문서 정보·책갈피 글 - UTF-16BE(BOM)·UTF-8(BOM)·PDFDocEncoding(≈latin-1)."""
    if not isinstance(b, bytes):
        return str(b) if b is not None else ""
    if b[:2] == b"\xfe\xff":
        return b[2:].decode("utf-16-be", "replace")
    if b[:3] == b"\xef\xbb\xbf":
        return b[3:].decode("utf-8", "replace")
    return b.decode("latin-1")


def _u16(h):
    b = bytes.fromhex(re.sub(rb"[^0-9A-Fa-f]", b"", h).decode())
    return (b + b"\0" if len(b) % 2 else b).decode("utf-16-be", "replace")


def _cmap(txt):
    """ToUnicode CMap → (코드 공간 [(바이트 수, 시작, 끝)], {코드: 글자})."""
    space, m = [], {}
    for blk in re.findall(rb"begincodespacerange(.*?)endcodespacerange", txt, re.S):
        h = [re.sub(rb"\s", b"", x) for x in re.findall(rb"<([^>]*)>", blk)]
        for a, b in zip(h[::2], h[1::2]):
            if a and b:
                space.append((len(a) // 2 or 1, int(a, 16), int(b, 16)))
    for blk in re.findall(rb"beginbfchar(.*?)endbfchar", txt, re.S):
        h = re.findall(rb"<([^>]*)>", blk)
        for a, b in zip(h[::2], h[1::2]):
            if re.sub(rb"\s", b"", a):
                m[int(re.sub(rb"\s", b"", a), 16)] = _u16(b)
    for blk in re.findall(rb"beginbfrange(.*?)endbfrange", txt, re.S):
        it = re.findall(rb"<[^>]*>|\[[^\]]*\]", blk)
        for a, b, dst in zip(it[::3], it[1::3], it[2::3]):
            try:
                lo, hi = int(re.sub(rb"[^0-9A-Fa-f]", b"", a), 16), int(re.sub(rb"[^0-9A-Fa-f]", b"", b), 16)
            except ValueError:
                continue
            if hi < lo or hi - lo > 65535:
                continue
            if dst.startswith(b"["):
                for k, h in enumerate(re.findall(rb"<([^>]*)>", dst)):
                    m[lo + k] = _u16(h)
            else:
                u = bytes.fromhex(re.sub(rb"[^0-9A-Fa-f]", b"", dst).decode() or "0000")
                u = u if len(u) >= 2 else b"\0" + u
                base = int.from_bytes(u[-2:], "big")
                for k in range(hi - lo + 1):
                    m[lo + k] = (u[:-2] + ((base + k) & 0xFFFF).to_bytes(2, "big")).decode("utf-16-be", "replace")
    return space, m


class _Font:
    """글꼴의 바이트 → 글자. ToUnicode 가 있으면 그것, 없으면 단순 글꼴은 cp1252(+Differences), CID 글꼴은 못 읽음(빈 글)."""

    def __init__(self, n=1, space=None, cmap=None):
        self.n, self.space, self.map = n, space or [], cmap or {}

    def _len(self, b, i):
        for n, lo, hi in self.space:
            if i + n <= len(b) and lo <= int.from_bytes(b[i:i + n], "big") <= hi:
                return n
        return self.n

    def text(self, b):
        out, i = [], 0
        while i < len(b):
            n = self._len(b, i)
            code = int.from_bytes(b[i:i + n], "big")
            i += n
            ch = self.map.get(code)
            if ch is None and n == 1 and code >= 32:
                ch = bytes([code]).decode("cp1252", "replace")
            out.append(ch or "")
        return "".join(out)


_GLYPH = {"space": " ", "period": ".", "comma": ",", "hyphen": "-", "colon": ":", "semicolon": ";", "quoteright": "’", "quoteleft": "‘",
          "quotedblleft": "“", "quotedblright": "”", "parenleft": "(", "parenright": ")", "endash": "–", "emdash": "—", "bullet": "•"}
for _d, _nm in enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")):
    _GLYPH[_nm] = str(_d)


class Pdf:
    def __init__(self, data):
        self.d = data
        self.objs = {}  # 번호 → (객체, 스트림 원본 bytes 또는 None)
        self.fonts = {}
        self._scan()
        self.trailer = self._trailer()
        if self.trailer.get("Encrypt") is not None:
            raise ValueError("암호가 걸린 PDF 다(열기 암호가 없어도 권한 암호화면 내장 읽개로는 못 연다) - "
                             "`python3 -m pip install pymupdf` 를 설치하거나 PDF 를 암호 없이 다시 저장해 올린다")

    # ---- 객체 ----
    def _scan(self):
        d, skip = self.d, 0
        for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b", d):
            if m.start() < skip:
                continue
            lx = _Lex(d, m.end())
            try:
                o = _obj(lx)
            except (IndexError, ValueError, RecursionError):
                continue
            raw = None
            lx.skip()
            if isinstance(o, dict) and d.startswith(b"stream", lx.i):
                s = lx.i + 6
                s += 2 if d[s:s + 2] == b"\r\n" else 1 if d[s:s + 1] in (b"\n", b"\r") else 0
                ln = o.get("Length")
                if isinstance(ln, int) and ln >= 0 and d[s + ln:s + ln + 40].lstrip().startswith(b"endstream"):
                    raw, skip = d[s:s + ln], s + ln
                else:
                    e = d.find(b"endstream", s)
                    e = len(d) if e < 0 else e
                    raw, skip = d[s:e].rstrip(b"\r\n") if e - s > 0 else b"", e
            self.objs[int(m.group(1))] = (o, raw)
        for num, (o, raw) in list(self.objs.items()):  # 객체 스트림(PDF 1.5+) 안의 객체 - 바깥에 같은 번호가 없을 때만
            if isinstance(o, dict) and o.get("Type") == "ObjStm" and raw is not None:
                data = _decode(o, raw)
                n, first = o.get("N"), o.get("First")
                if data is None or not isinstance(n, int) or not isinstance(first, int):
                    continue
                lx = _Lex(data)
                head = [lx.token() for _ in range(2 * n)]
                for k in range(0, len(head) - 1, 2):
                    if isinstance(head[k], int) and isinstance(head[k + 1], int) and head[k] not in self.objs:
                        try:
                            self.objs[head[k]] = (_obj(_Lex(data, first + head[k + 1])), None)
                        except (IndexError, ValueError, RecursionError):
                            pass

    def _trailer(self):
        tr = {}
        for o, _ in self.objs.values():  # 교차 참조 스트림의 사전(PDF 1.5+)
            if isinstance(o, dict) and o.get("Type") == "XRef":
                tr.update(o)
        for m in re.finditer(rb"trailer", self.d):
            try:
                t = _obj(_Lex(self.d, m.end()))
            except (IndexError, ValueError, RecursionError):
                continue
            if isinstance(t, dict):
                tr.update(t)
        return tr

    def r(self, x):
        for _ in range(32):
            if not isinstance(x, _Ref):
                return x
            x = self.objs.get(x[0], (None, None))[0]
        return None

    def stream(self, x):
        """간접 참조 → (사전, 풀린 데이터) - 스트림이 아니거나 못 풀면 (사전, None)."""
        if not isinstance(x, _Ref) or x[0] not in self.objs:
            return {}, None
        o, raw = self.objs[x[0]]
        o = o if isinstance(o, dict) else {}
        return o, (_decode(o, raw) if raw is not None else None)

    # ---- 쪽 ----
    def pages(self):
        root = self.r(self.trailer.get("Root"))
        if not isinstance(root, dict):
            root = next((o for o, _ in self.objs.values() if isinstance(o, dict) and o.get("Type") == "Catalog"), {})
        self.root, out, seen = root, [], set()

        def walk(ref, res, depth):
            node = self.r(ref)
            if not isinstance(node, dict) or depth > 64 or (isinstance(ref, _Ref) and ref[0] in seen):
                return
            if isinstance(ref, _Ref):
                seen.add(ref[0])
            res = node.get("Resources", res)
            kids = self.r(node.get("Kids"))
            if isinstance(kids, list):
                for k in kids:
                    walk(k, res, depth + 1)
            elif node.get("Type") != "Pages":
                out.append((ref, node, res))

        walk(root.get("Pages"), None, 0)
        if not out:  # 쪽 나무가 깨졌으면 /Type /Page 객체를 번호 순으로
            out = [(_Ref((n, 0)), o, o.get("Resources")) for n, o in sorted((n, o) for n, (o, _) in self.objs.items()
                                                                            if isinstance(o, dict) and o.get("Type") == "Page")]
        return out

    def _font(self, fonts, name):
        ref = fonts.get(str(name)) if isinstance(fonts, dict) else None
        key = ref[0] if isinstance(ref, _Ref) else id(ref)
        if key in self.fonts:
            return self.fonts[key]
        fd = self.r(ref)
        f = _Font()
        if isinstance(fd, dict):
            n = 2 if fd.get("Subtype") == "Type0" else 1
            _, tu = self.stream(fd.get("ToUnicode"))
            if tu:
                space, m = _cmap(tu)
                f = _Font(n, space, m)
            elif n == 2:
                f = _Font(2, cmap={})  # ToUnicode 없는 CID 글꼴 - 글자로 못 바꾼다
            else:
                enc = self.r(fd.get("Encoding"))
                m = {}
                if isinstance(enc, dict) and isinstance(self.r(enc.get("Differences")), list):
                    code = 0
                    for x in self.r(enc.get("Differences")):
                        if isinstance(x, int):
                            code = x
                        elif isinstance(x, _Name):
                            g = str(x)
                            u = re.fullmatch(r"uni([0-9A-Fa-f]{4})", g)
                            m[code] = chr(int(u.group(1), 16)) if u else _GLYPH.get(g, g if len(g) == 1 else None)
                            if m[code] is None:
                                del m[code]
                            code += 1
                f = _Font(1, cmap=m)
        self.fonts[key] = f
        return f

    def _run(self, data, res, st, depth=0):
        """내용 스트림을 따라가며 글을 st["out"] 에 쌓는다."""
        res = self.r(res)
        res = res if isinstance(res, dict) else {}
        fonts, xobj = self.r(res.get("Font")) or {}, self.r(res.get("XObject")) or {}
        lx, ops, font, out = _Lex(data), [], _Font(), st["out"]

        def nl():
            if out and out[-1] != "\n":
                out.append("\n")
            st["sp"] = False

        def emit(s):
            if not s:
                return
            if st["last"] is not None and abs(st["y"] - st["last"]) > max(1.0, 0.5 * abs(st["fs"] * st["dy"])):
                nl()
            elif st["sp"] and out and not out[-1][-1:].isspace() and not s[:1].isspace():
                out.append(" ")
            st["sp"], st["last"] = False, st["y"]
            out.append(s)

        def num(k):
            x = ops[k] if len(ops) >= -k else 0
            return x if isinstance(x, (int, float)) and not isinstance(x, bool) else 0

        while True:
            try:
                t = lx.token()
                if t is None:
                    break
                x = _obj(lx, t)
            except (IndexError, ValueError, RecursionError):
                break
            if not isinstance(x, _Kw):
                ops.append(x)
                continue
            op = str(x)
            if op == "BI":  # 인라인 그림 - ID 와 EI 사이 바이너리를 건너뛴다
                j = data.find(b"ID", lx.i)
                m = re.compile(rb"\sEI(?=[\s/]|$)").search(data, j + 2) if j >= 0 else None
                lx.i = m.end() if m else len(data)
            elif op == "BT":
                st["y"], st["dy"] = 0.0, 1.0
            elif op == "Tf" and len(ops) >= 2:
                font, st["fs"] = self._font(fonts, ops[-2]), num(-1) or st["fs"]
            elif op == "Tm" and len(ops) >= 6:
                if st["last"] is not None and abs(num(-1) - st["y"]) < 0.01 and num(-2) != st.get("x"):
                    st["sp"] = True
                st["y"], st["dy"], st["x"] = num(-1), num(-3) or 1.0, num(-2)
            elif op in ("Td", "TD"):
                st["y"] += num(-1) * st["dy"]
                if abs(num(-1)) < 0.01 and num(-2) > 0:
                    st["sp"] = True
            elif op == "T*":
                nl()
                st["last"] = None
            elif op in ("Tj", "'", '"') and ops and isinstance(ops[-1], bytes):
                if op != "Tj":
                    nl()
                    st["last"] = None
                emit(font.text(ops[-1]))
            elif op == "TJ" and ops and isinstance(ops[-1], list):
                for it in ops[-1]:
                    if isinstance(it, bytes):
                        emit(font.text(it))
                    elif isinstance(it, (int, float)) and it < -200:  # 큰 음수 자간 = 낱말 사이
                        st["sp"] = True
            elif op == "Do" and ops and isinstance(xobj, dict):
                ref = xobj.get(str(ops[-1]))
                o, sub = self.stream(ref)
                if o.get("Subtype") == "Form" and sub is not None and depth < 8 and ref not in st["forms"]:
                    st["forms"].add(ref)
                    self._run(sub, o.get("Resources", res), st, depth + 1)
                    st["forms"].discard(ref)
                elif o.get("Subtype") == "Image" and o.get("Filter") in ("DCTDecode", ["DCTDecode"]) and isinstance(ref, _Ref):
                    w, h = o.get("Width"), o.get("Height")
                    if isinstance(w, int) and isinstance(h, int) and w * h >= 64 * 64:  # 아이콘·선 조각은 뺀다
                        st["jpegs"].append(self.objs[ref[0]][1])
            ops = []

    def page_text(self, node, res):
        st = {"out": [], "y": 0.0, "dy": 1.0, "fs": 10, "last": None, "sp": False, "forms": set(), "jpegs": []}
        c = self.r(node.get("Contents"))
        refs = c if isinstance(c, list) else [node.get("Contents")]
        data = b"\n".join(s for s in (self.stream(x)[1] for x in refs) if s)
        self._run(data, res, st)
        txt = "".join(st["out"])
        lines = [" ".join(ln.split()) for ln in txt.split("\n")]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip(), st["jpegs"]

    def toc(self, page_no):
        out, seen = [], set()

        def walk(ref, level):
            while isinstance(ref, _Ref) and ref[0] not in seen and len(out) < 200:
                seen.add(ref[0])
                it = self.r(ref)
                if not isinstance(it, dict):
                    return
                dest = self.r(it.get("Dest"))
                act = self.r(it.get("A"))
                if dest is None and isinstance(act, dict):
                    dest = self.r(act.get("D"))
                if isinstance(dest, dict):
                    dest = self.r(dest.get("D"))
                page = page_no.get(dest[0][0]) if isinstance(dest, list) and dest and isinstance(dest[0], _Ref) else None
                out.append({"level": level, "title": _pdfstr(self.r(it.get("Title"))).strip(), "page": page})
                walk(it.get("First"), level + 1)
                ref = it.get("Next")

        ol = self.r(self.root.get("Outlines")) if isinstance(self.root, dict) else None
        if isinstance(ol, dict):
            walk(ol.get("First"), 1)
        return out


def read(path):
    """PDF 파일 → {"pages": [{"n", "text", "jpegs"}], "meta": {…}, "toc": […]}. 암호·깨진 파일은 ValueError."""
    data = open(path, "rb").read()
    if not data.lstrip()[:5] == b"%PDF-" and b"%PDF-" not in data[:1024]:
        raise ValueError("PDF 머리(%PDF-)가 없다 - PDF 파일이 아니다")
    pdf = Pdf(data)
    pl = pdf.pages()
    if not pl:
        raise ValueError("쪽을 찾지 못했다 - 깨졌거나 내장 읽개가 모르는 구조다(`python3 -m pip install pymupdf`)")
    pages = []
    for i, (_, node, res) in enumerate(pl):
        text, jpegs = pdf.page_text(node, res)
        pages.append({"n": i + 1, "text": text, "jpegs": jpegs})
    info = pdf.r(pdf.trailer.get("Info"))
    meta = {k[0].lower() + k[1:]: _pdfstr(pdf.r(v)).strip() for k, v in (info.items() if isinstance(info, dict) else []) if isinstance(pdf.r(v), bytes)}
    page_no = {ref[0]: i + 1 for i, (ref, _, _) in enumerate(pl) if isinstance(ref, _Ref)}
    return {"pages": pages, "meta": {k: v for k, v in meta.items() if v}, "toc": pdf.toc(page_no)}
