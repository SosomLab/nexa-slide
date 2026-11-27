# -*- coding: utf-8 -*-
"""Word .docx → 페이지 문서(kind page). export_docx.py 의 반대 방향 - 표준 라이브러리로 XML 을 직접 읽는다.

    python3 studio/import_docx.py <파일.docx> [--id <덱 id>] [--title 제목]    # 작업 공간 decks/<id>.json 을 만든다
    read(data, images=True) → (문서 dict, {그림 이름: bytes}, 경고 목록)        # 파일을 쓰지 않는 순수 함수

옮기는 것: 쪽 설정(용지·방향·여백) · 문단(정렬·들여쓰기·줄 간격·제목 수준) · 글 조각(굵게·기울임·밑줄·취소선·색·형광/음영·첨자·크기·링크·윗주·줄바꿈·탭) ·
목록(글머리·번호·단계 - numbering.xml 의 번호 꼴로 가린다) · 표(가로·세로 병합·머리글 행·칸 채움) · 글자처럼 놓인 그림 · 쪽 나누기 · 머리말·꼬리말 글 · 쪽 번호.
옮기지 않는 것(경고로 알린다): 떠 있는 개체·글 상자·도형 · 각주 · 변경 내용 추적 · 필드(쪽 번호 말고) · 구역이 여럿일 때 둘째부터의 쪽 설정 · 다단.
글꼴 이름·스타일 정의는 가져오지 않는다 - 문서는 이 작업 공간의 스타일(본문·제목 1~3)을 쓰고, 스타일과 다른 글자 크기·색만 글 조각에 남긴다.
"""
import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_doc  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
WPS = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}"
PRST_SHAPE = {"rect": "rect", "roundRect": "round", "ellipse": "ellipse", "line": "line", "straightConnector1": "line",
              "leftBracket": "bracket-l", "rightBracket": "bracket-r", "leftBrace": "brace-l", "rightBrace": "brace-r"}  # Word 기본 도형 → 개체 모양(export_docx.PRST 의 거꾸로)
TW = 1440 / 25.4
HIGHLIGHT = {"yellow": "#ffff00", "green": "#00ff00", "cyan": "#00ffff", "magenta": "#ff00ff", "blue": "#0000ff", "red": "#ff0000", "darkBlue": "#000080",
             "darkCyan": "#008080", "darkGreen": "#008000", "darkMagenta": "#800080", "darkRed": "#800000", "darkYellow": "#808000", "darkGray": "#808080", "lightGray": "#c0c0c0"}
UNDER = {"double": "double", "dotted": "dot", "dash": "dash", "wave": "wave"}
JC = {"center": "center", "right": "right", "end": "right", "both": "justify", "distribute": "justify"}
MAX_IMAGE = 20 * 1024 * 1024


def v(el, name, default=None):
    return default if el is None else el.get(W + name, default)


def on(el):
    """w:b 같은 켜고 끄는 속성 - 요소가 있고 val 이 0/false 가 아니면 켜짐."""
    return el is not None and el.get(W + "val", "1") not in ("0", "false", "off")


def mm(tw):
    try:
        return round(int(tw) / TW, 1)
    except (TypeError, ValueError):
        return None


class Reader:
    def __init__(self, z, images=True):
        self.z, self.want_images = z, images
        self.warn, self.images, self.n = [], {}, 0
        self._notes = None
        self._sect_ends = []           # 본문 안에서 끝난 구역들 [(그때까지의 블록 수, sectPr)]
        self.objects = []              # 떠 있는 도형·글 상자 → 개체(매인 문단 id 는 _para 가 채운다)
        self.rels = self._rels("word/_rels/document.xml.rels")
        self.styles = self._styles()
        self.nums = self._numbering()

    def _xml(self, name):
        try:
            return ET.fromstring(self.z.read(name))
        except (KeyError, ET.ParseError):
            return None

    def _rels(self, name):
        x = self._xml(name)
        return {} if x is None else {r.get("Id"): (r.get("Target"), r.get("TargetMode") == "External") for r in x.findall(PR + "Relationship")}

    def _styles(self):
        """스타일 id → {level: 제목 수준(1~3) | None, title: 문서 제목인가, size, bold, list} - 제목 판단과 '스타일과 다른 서식' 가리기에 쓴다."""
        out, x = {}, self._xml("word/styles.xml")
        for st in ([] if x is None else x.findall(W + "style")):
            sid, name = st.get(W + "styleId"), (v(st.find(W + "name"), "val") or "").lower()
            ppr, rpr = st.find(W + "pPr"), st.find(W + "rPr")
            lvl = v(ppr.find(W + "outlineLvl"), "val") if ppr is not None else None
            m = re.fullmatch(r"(?:heading|제목)\s*([1-9])", name) or re.fullmatch(r"h([1-9])", str(sid or "").lower())
            level = int(m.group(1)) if m else (int(lvl) + 1 if lvl is not None and str(lvl).isdigit() else None)
            out[sid] = {"level": level, "title": name in ("title", "제목", "문서 제목") or str(sid).lower() == "title", "based": v(st.find(W + "basedOn"), "val"),
                        "size": int(v(rpr.find(W + "sz"), "val")) / 2 if rpr is not None and rpr.find(W + "sz") is not None else None,
                        "bold": on(rpr.find(W + "b")) if rpr is not None else False, "quote": "quote" in name or "인용" in name, "caption": "caption" in name or "캡션" in name}
        return out

    def _numbering(self):
        """numId → {ilvl: 'bullet' | 'number'} (+ 확인란 글머리 ☐☑ 는 'check' · 'done')."""
        x = self._xml("word/numbering.xml")
        if x is None:
            return {}
        absn = {}
        for a in x.findall(W + "abstractNum"):
            lv = {}
            for l in a.findall(W + "lvl"):
                fmt, text = v(l.find(W + "numFmt"), "val"), v(l.find(W + "lvlText"), "val") or ""
                lv[int(l.get(W + "ilvl", "0"))] = ("done" if "☑" in text else "check" if "☐" in text else "bullet") if fmt == "bullet" else "number"
            absn[a.get(W + "abstractNumId")] = lv
        return {n.get(W + "numId"): absn.get(v(n.find(W + "abstractNumId"), "val"), {}) for n in x.findall(W + "num")}

    def new_id(self, p="b"):
        self.n += 1
        return f"{p}{self.n:03d}"

    # ---- 글 조각
    def _marks(self, rpr, style_size=None):
        m = {}
        if rpr is None:
            return m
        if on(rpr.find(W + "b")):
            m["b"] = True
        if on(rpr.find(W + "i")):
            m["i"] = True
        if on(rpr.find(W + "strike")):
            m["s"] = True
        u = rpr.find(W + "u")
        if u is not None and v(u, "val", "single") != "none":
            m["u"] = UNDER.get(v(u, "val", "single"), True)
        c = v(rpr.find(W + "color"), "val")
        if c and re.fullmatch(r"[0-9A-Fa-f]{6}", c) and c.lower() != "000000":
            m["c"] = "#" + c.lower()
        hl = v(rpr.find(W + "highlight"), "val")
        shd = v(rpr.find(W + "shd"), "fill")
        if hl in HIGHLIGHT:
            m["hl"] = HIGHLIGHT[hl]
        elif shd and re.fullmatch(r"[0-9A-Fa-f]{6}", shd) and shd.lower() != "ffffff":
            m["hl"] = "#" + shd.lower()
        va = v(rpr.find(W + "vertAlign"), "val")
        if va == "superscript":
            m["sup"] = True
        elif va == "subscript":
            m["sub"] = True
        sz = v(rpr.find(W + "sz"), "val")
        if sz and sz.isdigit() and int(sz) / 2 != (style_size or 10.5):
            m["size"] = int(sz) / 2
        return m

    def _run(self, r, extra, style_size):
        out = []
        ruby = r.find(W + "ruby")
        if ruby is not None:
            base = "".join(t.text or "" for t in ruby.find(W + "rubyBase").iter(W + "t")) if ruby.find(W + "rubyBase") is not None else ""
            top = "".join(t.text or "" for t in ruby.find(W + "rt").iter(W + "t")) if ruby.find(W + "rt") is not None else ""
            rb = ruby.find(f"{W}rubyBase/{W}r/{W}rPr")
            if base:
                out.append({"t": base, **self._marks(rb if rb is not None else r.find(W + "rPr"), style_size), **extra, **({"ruby": top} if top else {})})
            return out
        m = {**self._marks(r.find(W + "rPr"), style_size), **extra}
        for ch in r:
            tag = ch.tag
            if tag == W + "t":
                if ch.text:
                    out.append({"t": ch.text, **m})
            elif tag == W + "tab":
                out.append({"t": "\t", **m})
            elif tag == W + "br":
                kind = ch.get(W + "type")
                out.append({"__break": "column" if kind == "column" else "page"} if kind in ("page", "column") else {"t": "\n", **m})
            elif tag == W + "drawing" and ch.find(WP + "inline") is not None:
                out.append({"__image": ch})
            elif tag in (W + "drawing", W + "pict", MC + "AlternateContent"):
                # 떠 있는 개체 - 글 상자면 그 안의 글을 문단으로 꺼내고(위치·모양은 옮기지 않는다), 그 밖(도형·떠 있는 그림)은 경고만
                # AlternateContent 는 같은 개체를 새 형식(Choice)과 옛 형식(Fallback)으로 두 번 담는다 - 한쪽만 본다
                scope = ch.find(MC + "Choice") if tag == MC + "AlternateContent" and ch.find(MC + "Choice") is not None else ch
                obj = self._shape(scope)
                if obj:  # 아는 모양의 떠 있는 도형·글 상자 - 자리·크기·선·채움·안의 글까지 개체로 옮긴다
                    out.append({"__obj": obj})
                    continue
                boxes = list(scope.iter(W + "txbxContent")) or (list(ch.iter(W + "txbxContent"))[:1] if scope is not ch else [])
                if boxes:
                    self._warn("글 상자는 글만 문단으로 옮겼다(위치·모양은 옮기지 않음)")
                    out += [{"__textbox": b} for b in boxes]
                else:
                    self._warn("떠 있는 그림·도형은 옮기지 않았다(글자처럼 놓인 그림만)")
                    out.append({"__dropped": True})
            elif tag == W + "footnoteReference":
                t = self._note(ch.get(W + "id"))
                if t:
                    out.append({"__fn": t})
            elif tag == W + "endnoteReference":
                self._warn("미주는 옮기지 않았다")
            elif tag == W + "fldChar" or tag == W + "instrText":
                out.append({"__field": (ch.text or "") if tag == W + "instrText" else v(ch, "fldCharType")})
        return out

    def _shape(self, scope):
        """떠 있는 도형(wp:anchor 안의 wps:wsp · 기본 도형) → 개체 dict(anchor 는 비워 둔다). 모르는 모양·묶음·그림이면 None."""
        an = next(iter(scope.iter(WP + "anchor")), None)
        wsps = list(an.iter(WPS + "wsp")) if an is not None else []
        if len(wsps) != 1:
            return None
        sp = wsps[0].find(WPS + "spPr")
        geom = sp.find(A + "prstGeom") if sp is not None else None
        shape = PRST_SHAPE.get(geom.get("prst") if geom is not None else "")
        ext = an.find(WP + "extent")
        if not shape or ext is None:
            return None

        def off(tag):
            el = an.find(f"{WP}{tag}/{WP}posOffset")
            try:
                return round(int(el.text) / 36000, 1) if el is not None and el.text else 0.0
            except ValueError:
                return 0.0
        try:
            w, h = round(int(ext.get("cx", "0")) / 36000, 1), round(int(ext.get("cy", "0")) / 36000, 1)
        except ValueError:
            return None
        if w <= 0 and h <= 0:
            return None
        ph, pv = an.find(WP + "positionH"), an.find(WP + "positionV")
        para = (pv.get("relativeFrom") if pv is not None else "") in ("paragraph", "line")
        o = {"id": self.new_id("o"), "type": "shape", "shape": shape, "rel": "para" if para else "page",
             "x": max(-1000, min(2000, off("positionH"))), "y": max(-1000, min(2000, off("positionV"))), "w": min(2000, max(0, w)), "h": min(2000, max(0, h))}
        if ph is not None and ph.get("relativeFrom") in ("margin", "column") and not para:
            self._warn("일부 도형은 여백 기준 자리라 조금 어긋날 수 있다")
        ln = sp.find(A + "ln")
        if ln is not None and ln.find(A + "noFill") is not None:
            o["line"] = None
        elif ln is not None:
            line = {}
            c = ln.find(f"{A}solidFill/{A}srgbClr")
            if c is not None and re.fullmatch(r"[0-9A-Fa-f]{6}", c.get("val", "")):
                line["c"] = "#" + c.get("val").upper()
            try:
                if ln.get("w"):
                    line["w"] = max(0, min(20, round(int(ln.get("w")) / 12700, 2)))
            except ValueError:
                pass
            d = ln.find(A + "prstDash")
            if d is not None and d.get("val") in ("dash", "lgDash", "sysDash"):
                line["dash"] = "dash"
            elif d is not None and d.get("val") in ("dot", "sysDot"):
                line["dash"] = "dot"
            if line:
                o["line"] = line
            if shape == "line" and (ln.find(A + "tailEnd") is not None or ln.find(A + "headEnd") is not None):
                o["shape"] = "arrow"
        if o["shape"] in ("line", "arrow"):
            xf = sp.find(A + "xfrm")
            if xf is not None and xf.get("flipV") in ("1", "true"):
                o["flip"] = True
        else:
            f = sp.find(f"{A}solidFill/{A}srgbClr")
            if f is not None and re.fullmatch(r"[0-9A-Fa-f]{6}", f.get("val", "")):
                o["fill"] = "#" + f.get("val").upper()
            tx = wsps[0].find(f"{WPS}txbx/{W}txbxContent")
            if tx is not None:
                bs = [x for q in tx.findall(W + "p") for x in self._para(q)[0] if x["type"] == "p"]
                while bs and not bs[-1]["runs"]:
                    bs.pop()
                if bs:
                    o["blocks"] = bs
                    bp = wsps[0].find(WPS + "bodyPr")
                    va = {"ctr": "middle", "b": "bottom"}.get(bp.get("anchor") if bp is not None else "")
                    if va:
                        o["valign"] = va
        if an.get("behindDoc") in ("1", "true"):
            o["z"] = "behind"
        return o

    def _note(self, i):
        """각주 id → 글(여러 문단은 줄바꿈으로 잇는다). 구분선(separator)은 없다."""
        if self._notes is None:
            self._notes = {}
            root = self._xml("word/footnotes.xml")
            for f in (root.findall(W + "footnote") if root is not None else []):
                if f.get(W + "type") in ("separator", "continuationSeparator"):
                    continue
                self._notes[f.get(W + "id")] = "\n".join("".join(t.text or "" for t in p.iter(W + "t")).strip() for p in f.findall(W + "p")).strip()[:2000]
        return self._notes.get(i) or ""

    def _warn(self, msg):
        if msg not in self.warn:
            self.warn.append(msg)

    def _image(self, drawing):
        inline = drawing.find(WP + "inline")
        if inline is None:
            self._warn("떠 있는 그림·도형·글 상자는 옮기지 않았다(글자처럼 놓인 그림만)")
            return None
        blip = inline.find(f".//{A}blip")
        target = self.rels.get(blip.get(R + "embed"), (None, False))[0] if blip is not None else None
        if not target:
            return None
        ext = target.rsplit(".", 1)[-1].lower()
        if ext not in ("png", "jpg", "jpeg", "gif"):
            self._warn(f"그림 형식 {ext} 은 옮기지 않았다(png·jpg·gif 만)")
            return None
        name = f"import-{len(self.images) + 1}.{ext}"
        if self.want_images:
            try:
                data = self.z.read("word/" + target.lstrip("/"))
            except KeyError:
                return None
            if len(data) > MAX_IMAGE:
                self._warn("너무 큰 그림은 옮기지 않았다(20MB 넘음)")
                return None
            self.images[name] = data
        b = {"id": self.new_id("i"), "type": "image", "src": name}
        ext_el = inline.find(WP + "extent")
        if ext_el is not None and ext_el.get("cx", "").isdigit():
            b["w"] = round(int(ext_el.get("cx")) / 36000, 1)
        alt = (inline.find(WP + "docPr").get("descr") if inline.find(WP + "docPr") is not None else "") or ""
        if alt:
            b["alt"] = alt
        return b

    # ---- 문단
    def _para(self, p):
        """문단 하나 → 블록 목록(문단 안의 그림·쪽 나누기는 따로 블록이 된다). (블록들, 이 문단이 쪽 번호 필드를 가졌나)"""
        ppr = p.find(W + "pPr")
        sid = v(ppr.find(W + "pStyle"), "val") if ppr is not None else None
        st = self.styles.get(sid, {})
        seen, cur = set(), st
        while cur and cur.get("level") is None and not cur.get("title") and cur.get("based") in self.styles and cur["based"] not in seen:  # 기준 스타일을 따라가 제목 수준을 찾는다
            seen.add(cur["based"])
            cur = self.styles[cur["based"]]
        b = {"id": self.new_id(), "type": "p"}
        if st.get("title") or (cur and cur.get("title")):
            b["style"] = "title"
        elif (cur or {}).get("level"):
            b["style"] = f"h{min(3, cur['level'])}"
        elif st.get("quote"):
            b["style"] = "quote"
        elif st.get("caption"):
            b["style"] = "caption"
        if ppr is not None:
            jc = JC.get(v(ppr.find(W + "jc"), "val"))
            if jc:
                b["align"] = jc
            num = ppr.find(W + "numPr")
            if num is not None:
                nid, lv = v(num.find(W + "numId"), "val"), int(v(num.find(W + "ilvl"), "val", "0") or 0)
                kind = self.nums.get(nid, {}).get(lv)
                if kind and nid != "0":
                    b["list"] = {"kind": "check" if kind == "done" else kind, "level": min(8, lv), **({"done": True} if kind == "done" else {})}
            ind = ppr.find(W + "ind")
            if ind is not None and "list" not in b:
                left = mm(v(ind, "left") or v(ind, "start"))
                if left:
                    b["indent"] = left
                first = mm(v(ind, "firstLine"))
                if first:
                    b["first"] = first
            pf = v(ppr.find(W + "shd"), "fill")
            if pf and re.fullmatch(r"[0-9A-Fa-f]{6}", pf) and pf.lower() != "ffffff":
                b["fill"] = "#" + pf.lower()
            sp = ppr.find(W + "spacing")
            if sp is not None and v(sp, "line") and v(sp, "lineRule", "auto") == "auto":
                b["line"] = round(int(v(sp, "line")) / 240, 2)
        runs, out, field, has_page, boxed, dropped, objs = [], [], None, False, [], False, []
        style_size = st.get("size")

        def flush():
            nonlocal runs, b
            bb = {**b, "runs": page_doc.norm_runs(runs)}
            runs = []
            out.append(bb)
            b = {**{k: x for k, x in b.items() if k not in ("id",)}, "id": self.new_id()}

        for ch in p:
            items = []
            if ch.tag == W + "r":
                items = self._run(ch, {}, style_size)
            elif ch.tag == W + "hyperlink":
                tgt = self.rels.get(ch.get(R + "id"), (None, False))
                link = {"link": tgt[0]} if tgt[0] and tgt[1] and re.match(r"^(https?:|mailto:)", tgt[0]) else {}
                for r in ch.findall(W + "r"):
                    items += self._run(r, link, style_size)
            elif ch.tag in (W + "ins",):
                for r in ch.findall(W + "r"):
                    items += self._run(r, {}, style_size)
                self._warn("변경 내용 추적은 받아들인 것으로 옮겼다")
            elif ch.tag == W + "del":
                self._warn("변경 내용 추적은 받아들인 것으로 옮겼다")
            for it in items:
                if "__field" in it:  # 필드 - PAGE 만 알아본다(결과 글은 버린다)
                    f = it["__field"]
                    if f == "begin":
                        field = ""
                    elif f == "end":
                        field = None
                    elif f == "separate":
                        field = "result"
                    elif field == "":
                        if re.search(r"\bPAGE\b", f or ""):
                            has_page = True
                    continue
                if field is not None:
                    continue  # 필드 안의 글(명령·결과)은 옮기지 않는다
                if "__dropped" in it:
                    dropped = True
                elif "__textbox" in it:  # 글 상자의 글 - 이 문단 뒤에 문단들로
                    boxed += [x for q in it["__textbox"].findall(W + "p") for x in self._para(q)[0] if x["type"] == "p" and x["runs"]]
                elif "__obj" in it:
                    objs.append(it["__obj"])
                elif "__fn" in it:  # 각주 - 바로 앞 글자에 단다(앞에 글이 없으면 표시 글자 ※ 를 둔다)
                    last = runs[-1] if runs and "t" in runs[-1] and runs[-1]["t"] and not runs[-1].get("fn") else None
                    if last is None:
                        runs.append({"t": "※", "fn": it["__fn"]})
                    elif len(last["t"]) > 1:
                        runs[-1] = {**last, "t": last["t"][:-1]}
                        runs.append({**last, "t": last["t"][-1], "fn": it["__fn"]})
                    else:
                        last["fn"] = it["__fn"]
                elif "__break" in it:
                    if runs:
                        flush()
                    out.append({"id": self.new_id("k"), "type": "break", "kind": it["__break"]})
                elif "__image" in it:
                    img = self._image(it["__image"])
                    if img:
                        if runs:
                            flush()
                        if b.get("align") in ("left", "right"):
                            img["align"] = b["align"]
                        out.append(img)
                else:
                    runs.append(it)
        if runs or not out:
            out.append({**b, "runs": page_doc.norm_runs(runs)})
        if (boxed or dropped) and not objs and len(out) == 1 and out[0]["type"] == "p" and not out[0]["runs"]:
            out = []  # 글 상자·떠 있는 개체만 붙어 있던 빈 문단은 남기지 않는다
        if objs:  # 개체는 이 문단에 맨다(도형만 붙어 있던 빈 문단도 매일 자리라 남긴다)
            host = next((x for x in out if x["type"] == "p"), None)
            if host is None:
                host = {"id": self.new_id(), "type": "p", "runs": []}
                out.insert(0, host)
            for o in objs:
                o["anchor"] = host["id"]
                self.objects.append(o)
        return out + boxed, has_page

    def _table(self, tbl):
        grid = [int(g.get(W + "w", "0") or 0) for g in tbl.findall(f"{W}tblGrid/{W}gridCol")]
        rows, open_cells = [], {}  # open_cells[열] = 세로로 이어지는 칸(restart 한 칸)
        for tr in tbl.findall(W + "tr"):
            row = {"id": self.new_id("r"), "cells": []}
            if tr.find(f"{W}trPr/{W}tblHeader") is not None:
                row["head"] = True
            col = 0
            for tc in tr.findall(W + "tc"):
                pr = tc.find(W + "tcPr")
                span = int(v(pr.find(W + "gridSpan"), "val", "1") or 1) if pr is not None else 1
                vm = pr.find(W + "vMerge") if pr is not None else None
                if vm is not None and v(vm, "val", "continue") != "restart":  # 위 칸에 이어진다
                    if col in open_cells:
                        open_cells[col]["rowspan"] = open_cells[col].get("rowspan", 1) + 1
                    col += span
                    continue
                cell = {"id": self.new_id("c"), "blocks": self._blocks(tc, nested=True)}
                if span > 1:
                    cell["colspan"] = span
                fill = v(pr.find(W + "shd"), "fill") if pr is not None else None
                if fill and re.fullmatch(r"[0-9A-Fa-f]{6}", fill) and fill.lower() not in ("ffffff", "f0f0f0"):
                    cell["fill"] = "#" + fill.lower()
                va = v(pr.find(W + "vAlign"), "val") if pr is not None else None
                if va in ("center", "bottom"):
                    cell["valign"] = "middle" if va == "center" else "bottom"
                if vm is not None:
                    open_cells[col] = cell
                else:
                    open_cells.pop(col, None)
                row["cells"].append(cell)
                col += span
            if row["cells"]:
                rows.append(row)
        ncol = len(grid) or max((sum(c.get("colspan", 1) for c in r["cells"]) for r in rows), default=1)
        total = sum(grid) or ncol
        cols = [round(g / total * 100, 1) for g in grid] if grid and total else [round(100 / ncol, 1)] * ncol
        if rows and rows[0].get("head"):  # (테두리 있는 표) 머리글 칸의 굵게는 내보낼 때 다시 붙는다 - 문서에는 남기지 않는다
            for c in rows[0]["cells"]:
                for b in c["blocks"]:
                    for r in b.get("runs", []):
                        r.pop("b", None)
                    if "runs" in b:
                        b["runs"] = page_doc.norm_runs(b["runs"])
        out = {"id": self.new_id("t"), "type": "table", "cols": cols, "rows": rows}
        tb = tbl.find(f"{W}tblPr/{W}tblBorders")
        if tb is not None:  # 테두리 - 바깥이 없으면 배치용 표(none), 칸 사이 세로선만 있으면 inner-v
            has = lambda s: tb.find(W + s) is not None and v(tb.find(W + s), "val", "nil") not in ("nil", "none")  # noqa: E731
            if not any(has(s) for s in ("top", "left", "bottom", "right", "insideH")):
                out["border"] = "inner-v" if has("insideV") else "none"
        return out if rows else None

    def _blocks(self, parent, nested=False):
        out, page_field, after_table = [], False, False
        for ch in parent:
            if ch.tag == W + "p":
                bs, hp = self._para(ch)
                # 표 바로 뒤의 빈 문단 하나는 Word 형식이 요구하는 자리(표 뒤에는 문단이 있어야 한다 - export_docx 가 넣는다)라 옮기지 않는다
                if after_table and len(bs) == 1 and bs[0]["type"] == "p" and not bs[0]["runs"] and set(bs[0]) <= {"id", "type", "runs"}:
                    after_table = False
                    continue
                after_table = False
                sp = None if nested else ch.find(f"{W}pPr/{W}sectPr")
                if sp is not None:  # 구역의 끝 - 이 문단까지가 한 구역(빈 문단이면 구역을 닫으려고 둔 것이라 버린다)
                    if len(bs) == 1 and bs[0]["type"] == "p" and not bs[0]["runs"]:
                        bs = []
                    out += bs
                    self._sect_ends.append((len(out), sp))
                    page_field = page_field or hp
                    continue
                out += bs
                page_field = page_field or hp
            elif ch.tag == W + "tbl":
                if nested:
                    self._warn("표 안의 표는 글만 옮겼다")
                    for p in ch.iter(W + "p"):
                        out += self._para(p)[0]
                else:
                    t = self._table(ch)
                    if t:
                        out.append(t)
                        after_table = True
        if nested:
            out = [b for b in out if b["type"] != "break"]
            while len(out) > 1 and out[-1]["type"] == "p" and not out[-1]["runs"]:  # 칸 끝의 빈 문단(표 형식이 요구하는 것)은 뺀다
                out.pop()
        self.page_field = page_field
        return out

    def _hf(self, sect, kind):
        """머리말·꼬리말(default) → (블록들, 쪽 번호 위치 | None)."""
        for ref in sect.findall(W + f"{kind}Reference") if sect is not None else []:
            if ref.get(W + "type", "default") != "default":
                continue
            target = self.rels.get(ref.get(R + "id"), (None, False))[0]
            x = self._xml("word/" + target) if target else None
            if x is None:
                continue
            blocks, pos = [], None
            for p in x.findall(W + "p"):
                bs, hp = self._para(p)
                bs = [b for b in bs if b["type"] == "p"]
                if hp:
                    pos = f"{kind}-{(bs[0].get('align') if bs else None) or 'left'}".replace("justify", "left")
                    bs = [b for b in bs if b["runs"]]
                blocks += [b for b in bs if b["runs"]]
            return blocks, pos
        return [], None

    def read(self):
        x = self._xml("word/document.xml")
        if x is None or x.find(W + "body") is None:
            raise ValueError("Word 문서가 아니다(word/document.xml 없음)")
        body = x.find(W + "body")
        blocks = self._blocks(body)
        sects = [s for s in body.iter(W + "sectPr")]
        sect = body.find(W + "sectPr") if body.find(W + "sectPr") is not None else (sects[-1] if sects else None)

        def cols_of(s):
            c = s.find(W + "cols") if s is not None else None
            try:
                n = int(v(c, "num", "1") or 1) if c is not None else 1
            except ValueError:
                n = 1
            if n <= 1:
                return None
            gap = mm(v(c, "space"))
            return {"count": min(4, n), "gap": max(0, min(50, round(gap))) if gap else 8}
        # 구역 - 구역마다 단이 다를 수 있다. 구역 i 의 설정은 그 구역을 닫는 sectPr 에 있다(마지막 구역 = 본문 끝의 sectPr). 용지·여백은 마지막 구역 것만 옮긴다
        ends = self._sect_ends
        order = [sp for _, sp in ends] + [sect]
        if len({(s.find(W + "pgSz").get(W + "w"), s.find(W + "pgSz").get(W + "h")) for s in order if s is not None and s.find(W + "pgSz") is not None}) > 1:
            self._warn("구역마다 용지가 다르다 - 쪽 설정은 마지막 구역 것만 옮겼다")
        for k in range(len(ends) - 1, -1, -1):  # 뒤에서부터 끼운다(앞의 색인이 그대로)
            at, _ = ends[k]
            nxt, cur = order[k + 1], order[k]
            ins = []
            typ = nxt.find(W + "type") if nxt is not None else None
            if (typ.get(W + "val") if typ is not None else "nextPage") != "continuous":
                ins.append({"id": self.new_id("k"), "type": "break", "kind": "page"})
            if cols_of(nxt) != cols_of(cur):
                ins.append({"id": self.new_id("k"), "type": "break", "kind": "section", "columns": cols_of(nxt) or {"count": 1}})
            blocks[at:at] = ins
        page = {}
        if order and cols_of(order[0]):
            page["columns"] = cols_of(order[0])
        if sect is not None:
            sz, mar = sect.find(W + "pgSz"), sect.find(W + "pgMar")
            if sz is not None:
                w, h = mm(v(sz, "w")), mm(v(sz, "h"))
                land = v(sz, "orient") == "landscape" or (w and h and w > h)
                if w and h:
                    pw, ph = (h, w) if land else (w, h)
                    name = next((k for k, (a, b) in page_doc.SIZES.items() if abs(a - pw) < 1.5 and abs(b - ph) < 1.5), None)
                    page["size"] = name or {"w": round(pw), "h": round(ph)}
                    page["orient"] = "landscape" if land else "portrait"
            if mar is not None:
                m = {k: mm(v(mar, n)) for k, n in (("t", "top"), ("r", "right"), ("b", "bottom"), ("l", "left"))}
                if all(x is not None for x in m.values()):
                    page["margin"] = {k: max(0, min(150, round(abs(x)))) for k, x in m.items()}
            number = None
            for kind in ("header", "footer"):
                bs, pos = self._hf(sect, kind)
                page[kind] = {"blocks": bs}
                number = number or pos
            if number:
                page["number"] = {"show": True, "pos": number}
        # 개체는 본문 맨 위 단계의 문단에만 맬 수 있다 - 표 칸·머리말·글 상자 안에 있던 도형은 옮기지 못한다
        top = {b["id"] for b in blocks if b.get("type") == "p"}
        objects = [o for o in self.objects if o.get("anchor") in top]
        if len(objects) != len(self.objects):
            self._warn("표 칸·머리말 안의 도형은 옮기지 않았다")
        return {"page": page, "blocks": blocks, "objects": objects}


def read(data, images=True, doc_id="imported", title=None):
    """(문서 dict, {그림 이름: bytes}, 경고). data = .docx 바이트."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Word 문서(.docx)가 아니다") from None
    rd = Reader(z, images)
    got = rd.read()
    t = title
    if not t:
        core = rd._xml("docProps/core.xml")
        el = core.find("{http://purl.org/dc/elements/1.1/}title") if core is not None else None
        t = (el.text or "").strip() if el is not None else ""
    if not t:
        first = next((b for b in got["blocks"] if b["type"] == "p" and b["runs"]), None)
        t = page_doc.runs_text(first["runs"])[:80] if first else doc_id
    doc = page_doc.new_page(doc_id, t, {"page": got["page"], "blocks": got["blocks"] or None})
    if got.get("objects"):
        doc["objects"] = got["objects"]
    e = page_doc.validate(doc)
    if e:
        raise ValueError("가져온 문서가 형식에 맞지 않는다 - " + e)
    return doc, rd.images, rd.warn


def save_images(doc, images, asset_root, prefix):
    """꺼낸 그림을 <asset_root>/assets/images/<prefix>-<이름> 으로 쓰고 문서의 그림 src 를 그 경로로 바꾼다."""
    if not images:
        return
    d = Path(asset_root) / "assets" / "images"
    d.mkdir(parents=True, exist_ok=True)
    names = {}
    for name, data in images.items():
        dst = d / f"{prefix}-{name}"
        dst.write_bytes(data)
        names[name] = f"assets/images/{dst.name}"
    for _, b in page_doc.walk(doc):
        if b.get("type") == "image" and b.get("src") in names:
            b["src"] = names[b["src"]]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from common import ASSET_ROOT, DECKS, safe_id  # -W <작업 공간> 을 읽고 인자에서 뺀다 - 인자를 읽기 전에
    ap = argparse.ArgumentParser(description="Word .docx → 페이지 문서")
    ap.add_argument("docx")
    ap.add_argument("--id")
    ap.add_argument("--title")
    ap.add_argument("--blocks", action="store_true", help="문서를 만들지 않고 블록(JSON)만 꺼낸다 → out/import/<이름>/page.json - 요청 첨부(Word)의 내용을 있는 페이지 문서에 서식째 넣을 때")
    a = ap.parse_args()
    import deck_admin
    src = Path(a.docx)
    i = a.id or deck_admin.new_id()
    safe_id(i)
    if a.blocks:  # 첨부 분석용 - 덱을 만들지 않는다. 그림은 assets 에 꺼내 두어 블록의 src 가 그대로 쓰인다
        from common import OUT
        doc, images, warn = read(src.read_bytes(), doc_id=i, title=a.title or src.stem)
        save_images(doc, images, ASSET_ROOT, i)
        d = OUT / "import" / (re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", src.stem)[:60] or "docx")
        d.mkdir(parents=True, exist_ok=True)
        (d / "page.json").write_text(json.dumps({"title": doc.get("title"), "page": doc.get("page"), "styles": doc.get("styles"), "blocks": doc.get("blocks"), "objects": doc.get("objects") or []}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"꺼냄: {d / 'page.json'} · 블록 {len(doc['blocks'])}개 · 그림 {len(images)}개 (문서는 만들지 않았다)")
        for w in warn:
            print("  주의: " + w)
        return
    out = DECKS / f"{i}.json"
    if out.exists():
        sys.exit(f"이미 있는 덱: {i}")
    doc, images, warn = read(src.read_bytes(), doc_id=i, title=a.title or src.stem)
    save_images(doc, images, ASSET_ROOT, i)
    DECKS.mkdir(parents=True, exist_ok=True)
    deck_admin.atomic_write(out, deck_admin._dumps(doc))
    print(f"가져옴: {out} · 블록 {len(doc['blocks'])}개 · 그림 {len(images)}개")
    for w in warn:
        print("  주의: " + w)


if __name__ == "__main__":
    main()
