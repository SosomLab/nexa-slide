# -*- coding: utf-8 -*-
"""페이지 문서(kind page) JSON → Word .docx - 표준 라이브러리 zip + XML 을 직접 쓴다(Word·Pages 에서 열린다).

    python3 studio/export_docx.py <id>              # → out/<id>.docx
    python3 studio/export_docx.py <id> --out x.docx

형식은 docs/dev/page-editor/design.md 3절. 대응: 쪽 설정 → sectPr · 스타일 → styles.xml(상속 basedOn) · 문단 → w:p(pStyle·정렬·들여쓰기) ·
글 조각 → w:r(rPr) · 목록(문단 속성) → numbering.xml 의 numPr · 표 → w:tbl(gridSpan·vMerge·머리글 행 반복) · 그림 → 글자처럼(inline) ·
쪽 나누기 → w:br · 머리말·꼬리말·쪽 번호(PAGE 필드) · 링크 · 윗주(w:ruby).
화면(page-render.js)과 같은 규칙을 쓴다: 스타일 풀기·목록 번호 꼴(1. a. i.)·쪽 상자는 page_doc.py 에 있고 화면은 그것과 맞춘다.
build(doc, …) 는 파일을 읽지 않는 순수 함수다(그림 바이트는 images 로 받는다) - 시험이 구조를 본다(tests/page_docx_test.py).
"""
import argparse
import io
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_doc  # noqa: E402

TW = 1440 / 25.4      # mm → twip(1/20 pt)
EMU = 36000           # mm → EMU
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
DEFAULT_FONTS = {"body": "맑은 고딕", "title": "맑은 고딕", "heading": "맑은 고딕", "mono": "Consolas"}
DEFAULT_COLORS = {"accent": "C8553D", "muted": "7A756D", "ink": "1F1F1F"}
UNDERLINE = {"double": "double", "dot": "dotted", "dash": "dash", "wave": "wave"}
JC = {"left": "left", "center": "center", "right": "right", "justify": "both"}
LIST_INDENT = 6  # mm - 화면 page-render.js 와 같다
IMG_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif"}


def tw(mm):
    return int(round(mm * TW))


class Ctx:
    """토큰 → 값. fonts = {역할: 글꼴 이름} · colors = {토큰: RRGGBB}. 모르는 색 이름은 무시(검정)."""

    def __init__(self, fonts=None, colors=None, images=None):
        self.fonts = {**DEFAULT_FONTS, **(fonts or {})}
        self.colors = {**DEFAULT_COLORS, **(colors or {})}
        self.images = images or {}     # src → (bytes, 너비 px, 높이 px)
        self.rels = []                 # (rId, type, target, external)
        self.media = {}                # 파일 이름 → bytes
        self.nums = []                 # numbering 인스턴스 [(numId, abstractId)]
        self.pic = 0

    def font(self, f):
        return self.fonts.get(f, f)

    def color(self, c):
        if not isinstance(c, str):
            return None
        if c in self.colors:
            return self.colors[c].lstrip("#").upper()
        m = re.fullmatch(r"#?([0-9a-fA-F]{6})", c.strip())
        if m:
            return m.group(1).upper()
        m = re.fullmatch(r"#?([0-9a-fA-F]{3})", c.strip())
        return "".join(ch * 2 for ch in m.group(1)).upper() if m else None

    def rel(self, typ, target, external=False):
        rid = f"rId{len(self.rels) + 10}"
        self.rels.append((rid, typ, target, external))
        return rid


def _rpr(m, ctx, style=False):
    """글자 속성 - m 은 글 조각(run)의 서식 또는 풀린 스타일. style=True 면 스타일의 키 이름(bold·italic·color·font·size)."""
    b, i = (m.get("bold"), m.get("italic")) if style else (m.get("b"), m.get("i"))
    font, size, color = m.get("font"), m.get("size"), (m.get("color") if style else m.get("c"))
    x = []
    if font:
        f = ctx.font(font)  # 글꼴 이름, 또는 {latin, ea} - 영문과 한글(동아시아) 글꼴을 따로 준다
        la, ea = (f.get("latin") or f.get("ea"), f.get("ea") or f.get("latin")) if isinstance(f, dict) else (f, f)
        la, ea = escape(str(la), {'"': "&quot;"}), escape(str(ea), {'"': "&quot;"})
        x.append(f'<w:rFonts w:ascii="{la}" w:hAnsi="{la}" w:eastAsia="{ea}" w:cs="{la}"/>')
    if b:
        x.append("<w:b/><w:bCs/>")
    if i:
        x.append("<w:i/><w:iCs/>")
    if not style and m.get("s"):
        x.append("<w:strike/>")
    c = ctx.color(color)
    if c:
        x.append(f'<w:color w:val="{c}"/>')
    if size:
        hp = int(round(float(size) * 2))
        x.append(f'<w:sz w:val="{hp}"/><w:szCs w:val="{hp}"/>')
    if not style:
        if m.get("u"):
            x.append(f'<w:u w:val="{UNDERLINE.get(m["u"], "single")}"/>')
        hl = ctx.color(m.get("hl"))
        if hl:
            x.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{hl}"/>')
        if m.get("sup") or m.get("sub"):
            x.append(f'<w:vertAlign w:val="{"superscript" if m.get("sup") else "subscript"}"/>')
    return "<w:rPr>" + "".join(x) + "</w:rPr>" if x else ""


def _text(t):
    """글 → w:t · 줄바꿈 w:br · 탭 w:tab."""
    out = []
    for part in re.split(r"(\n|\t)", t):
        if part == "\n":
            out.append("<w:br/>")
        elif part == "\t":
            out.append("<w:tab/>")
        elif part:
            out.append(f'<w:t xml:space="preserve">{escape(part)}</w:t>')
    return "".join(out)


def _runs(runs, ctx):
    out = []
    for r in runs or []:
        rpr = _rpr(r, ctx)
        if r.get("ruby"):  # 윗주(루비) - 본문 글 위에 작은 글
            hps = int(round(float(r.get("size") or 10.5)))  # 윗주 크기 = 본문의 절반(반 포인트 단위라 pt 값 그대로)
            x = (f'<w:r>{rpr}<w:ruby><w:rubyPr><w:rubyAlign w:val="center"/><w:hps w:val="{hps}"/><w:hpsRaise w:val="{hps * 2 - 2}"/><w:hpsBaseText w:val="{hps * 2}"/>'
                 f'<w:lid w:val="ko-KR"/></w:rubyPr><w:rt><w:r><w:rPr><w:sz w:val="{hps}"/></w:rPr><w:t>{escape(str(r["ruby"]))}</w:t></w:r></w:rt>'
                 f'<w:rubyBase><w:r>{rpr}{_text(r["t"])}</w:r></w:rubyBase></w:ruby></w:r>')
        else:
            x = f'<w:r>{rpr}{_text(r["t"])}</w:r>'
        if r.get("link"):
            rid = ctx.rel("http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", str(r["link"]), True)
            x = f'<w:hyperlink r:id="{rid}" w:history="1">{x}</w:hyperlink>'
        out.append(x)
    return "".join(out)


def _ppr(b, ctx, num=None, style_ids=None):
    """문단 속성 - 스타일 · 목록 · 정렬 · 들여쓰기(스타일에 있는 것은 스타일이 낸다 - 여기는 문단이 직접 정한 것만)."""
    x = []
    st = b.get("style")
    if st and (style_ids is None or st in style_ids) and st != "body":
        x.append(f'<w:pStyle w:val="{escape(st)}"/>')
    if num:
        x.append(f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>')
    ind = []
    if b.get("indent") is not None and not num:
        ind.append(f'w:left="{tw(b["indent"])}"')
    elif num and b.get("indent"):
        ind.append(f'w:left="{tw(b["indent"] + (num[1] + 1) * LIST_INDENT)}" w:hanging="{tw(LIST_INDENT)}"')
    if b.get("first") is not None:
        ind.append(f'w:firstLine="{tw(b["first"])}"' if b["first"] >= 0 else f'w:hanging="{tw(-b["first"])}"')
    if ind:
        x.append("<w:ind " + " ".join(ind) + "/>")
    fill = ctx.color(b.get("fill"))
    if fill:  # 문단 음영 - pPr 안의 순서: pStyle → numPr → shd → spacing → ind → jc
        x.insert(sum(1 for e in x if e.startswith(("<w:pStyle", "<w:numPr"))), f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>')
    if isinstance(b.get("line"), (int, float)) and not isinstance(b.get("line"), bool) and b["line"] > 0:  # 문단이 직접 정한 줄 간격(배수)
        at = sum(1 for e in x if e.startswith(("<w:pStyle", "<w:numPr", "<w:shd")))  # pPr 안의 순서: pStyle → numPr → shd → spacing → ind → jc
        x.insert(at, f'<w:spacing w:line="{int(round(b["line"] * 240))}" w:lineRule="auto"/>')
    if b.get("align") in JC:
        x.append(f'<w:jc w:val="{JC[b["align"]]}"/>')
    return "<w:pPr>" + "".join(x) + "</w:pPr>" if x else ""


def _para(b, ctx, num=None, style_ids=None):
    return f"<w:p>{_ppr(b, ctx, num, style_ids)}{_runs(b.get('runs'), ctx)}</w:p>"


def _image(b, ctx, width_mm):
    src = b.get("src") or ""
    data = ctx.images.get(src)
    if not data:
        return f'<w:p><w:r><w:rPr><w:color w:val="999999"/></w:rPr><w:t>[그림 없음: {escape(src)}]</w:t></w:r></w:p>'
    raw, pw, ph = data
    ext = src.rsplit(".", 1)[-1].lower() if "." in src else "png"
    ext = ext if ext in IMG_TYPES else "png"
    ctx.pic += 1
    name = f"image{ctx.pic}.{ext}"
    ctx.media[name] = raw
    rid = ctx.rel("http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", f"media/{name}")
    w = min(float(b.get("w") or (pw * 25.4 / 96)), width_mm)       # 본문 너비를 넘지 않게
    h = float(b["h"]) if b.get("h") and b.get("w") and float(b["w"]) <= width_mm else w * (ph / pw if pw else 1)
    cx, cy = int(w * EMU), int(h * EMU)
    alt = escape(str(b.get("alt") or ""), {'"': "&quot;"})
    jc = JC.get(b.get("align") or "center", "center")
    pic = (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{ctx.pic}" name="Picture {ctx.pic}" descr="{alt}"/>'
           f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="{ctx.pic}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
           f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
           f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
    out = f'<w:p><w:pPr><w:jc w:val="{jc}"/></w:pPr>{pic}</w:p>'
    if b.get("caption"):
        out += f'<w:p><w:pPr><w:pStyle w:val="caption"/></w:pPr><w:r><w:t xml:space="preserve">{escape(str(b["caption"]))}</w:t></w:r></w:p>'
    return out


def _table(b, ctx, width_mm, style_ids):
    cols = b["cols"]
    total = sum(cols) or 1
    widths = [max(1, int(tw(width_mm) * c / total)) for c in cols]
    border = b.get("border", "all")  # all | none(배치용 표) | inner-v(칸 사이 세로선만 - 단 구분선)
    line = lambda s: ('<w:%s w:val="single" w:sz="4" w:space="0" w:color="8A8A8A"/>' if border == "all" or (border == "inner-v" and s == "insideV") else '<w:%s w:val="none" w:sz="0" w:space="0" w:color="auto"/>') % s  # noqa: E731
    x = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>'
         + "".join(line(s) for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
         + '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
         + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"]
    carry = {}  # 열 번호 → [남은 행 수, 칸 수] - 위에서 내려온 세로 병합
    for row in b["rows"]:
        x.append("<w:tr>" + ("<w:trPr><w:tblHeader/></w:trPr>" if row.get("head") else ""))
        col, cells = 0, list(row.get("cells") or [])
        while col < len(cols):
            if col in carry:  # 세로로 이어지는 칸 - 빈 칸에 vMerge(continue)
                left, span = carry[col]
                w = sum(widths[col:col + span])
                x.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{span}"/>' if span > 1 else "") + "<w:vMerge/></w:tcPr><w:p/></w:tc>")
                if left <= 1:
                    del carry[col]
                else:
                    carry[col] = [left - 1, span]
                col += span
                continue
            if not cells:
                x.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[col]}" w:type="dxa"/></w:tcPr><w:p/></w:tc>')  # 칸이 모자라면 빈 칸으로 채운다
                col += 1
                continue
            c = cells.pop(0)
            span = max(1, min(int(c.get("colspan", 1)), len(cols) - col))
            rs = max(1, int(c.get("rowspan", 1)))
            w = sum(widths[col:col + span])
            pr = [f'<w:tcW w:w="{w}" w:type="dxa"/>']
            if span > 1:
                pr.append(f'<w:gridSpan w:val="{span}"/>')
            if rs > 1:
                pr.append('<w:vMerge w:val="restart"/>')
                carry[col] = [rs - 1, span]
            fill = ctx.color(c.get("fill")) or ("F0F0F0" if row.get("head") and border == "all" else None)
            if fill:
                pr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>')
            if c.get("valign") in ("middle", "bottom"):
                pr.append(f'<w:vAlign w:val="{"center" if c["valign"] == "middle" else "bottom"}"/>')
            body = _blocks(c.get("blocks") or [], ctx, w / TW - 4, style_ids, head=bool(row.get("head")) and border == "all") or "<w:p/>"
            if not body.rstrip().endswith(("</w:p>", "<w:p/>")):
                body += "<w:p/>"  # 칸은 문단으로 끝나야 한다
            x.append("<w:tc><w:tcPr>" + "".join(pr) + "</w:tcPr>" + body + "</w:tc>")
            col += span
        x.append("</w:tr>")
    return "".join(x) + "</w:tbl>"


def _blocks(blocks, ctx, width_mm, style_ids, head=False):
    out, prev, cur = [], None, None
    for b in blocks or []:
        t = b.get("type")
        ls = b.get("list") if t == "p" else None
        if ls:
            kind = ls.get("kind")
            if prev is None or ls.get("restart") or (kind == "number" and prev.get("kind") != "number" and cur is None):
                cur = None
            if kind == "number":
                if cur is None or prev is None or ls.get("restart"):
                    cur = len(ctx.nums) + 10  # 번호 목록은 이어진 묶음마다 새 번호 인스턴스(1부터 다시)
                    ctx.nums.append((cur, 2))
                num = (cur, min(8, ls.get("level", 0)))
            else:
                num = (1 if kind == "bullet" else 3, min(8, ls.get("level", 0)))
                if kind == "check" and ls.get("done"):
                    num = (4, num[1])
            prev = ls
        else:
            num, prev, cur = None, None, None
        if t == "p":
            if head and not b.get("runs"):
                out.append("<w:p/>")
            else:
                bb = b if not head else {**b, "runs": [{**r, "b": True} for r in b.get("runs") or []]}
                out.append(_para(bb, ctx, num, style_ids))
        elif t == "table":
            out.append(_table(b, ctx, width_mm, style_ids))
            out.append("<w:p/>")  # 표 뒤에는 문단이 있어야 한다(표가 맨 끝이거나 표가 이어질 때)
        elif t == "image":
            out.append(_image(b, ctx, width_mm))
        elif t == "break":
            kind = b.get("kind", "page")
            out.append(f'<w:p><w:r><w:br w:type="{"column" if kind == "column" else "page"}"/></w:r></w:p>')
    return "".join(out)


def _styles(doc, ctx):
    body = page_doc.resolve_style(doc, "body")
    x = [XML, f"<w:styles {NS}><w:docDefaults><w:rPrDefault>{_rpr(body, ctx, True) or '<w:rPr/>'}</w:rPrDefault><w:pPrDefault><w:pPr/></w:pPrDefault></w:docDefaults>"]
    for name, st in (doc.get("styles") or {}).items():
        sid = "Normal" if name == "body" else escape(name, {'"': "&quot;"})
        own = {k: v for k, v in st.items() if k not in ("based", "name")} if name != "body" else body
        ppr = []
        if st.get("next") and st["next"] in doc["styles"]:
            ppr_next = f'<w:next w:val="{"Normal" if st["next"] == "body" else escape(st["next"])}"/>'
        else:
            ppr_next = ""
        sfill = ctx.color(own.get("fill"))
        if sfill:
            ppr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{sfill}"/>')
        before, after, line = own.get("before"), own.get("after"), own.get("line")
        if before is not None or after is not None or line is not None:
            sp = []
            if before is not None:
                sp.append(f'w:before="{int(round(before * 20))}"')
            if after is not None:
                sp.append(f'w:after="{int(round(after * 20))}"')
            if line is not None:
                sp.append(f'w:line="{int(round(line * 240))}" w:lineRule="auto"')
            ppr.append("<w:spacing " + " ".join(sp) + "/>")
        if own.get("indent") is not None or own.get("first") is not None:
            ind = []
            if own.get("indent") is not None:
                ind.append(f'w:left="{tw(own["indent"])}"')
            if own.get("first") is not None:
                ind.append(f'w:firstLine="{tw(own["first"])}"')
            ppr.append("<w:ind " + " ".join(ind) + "/>")
        if own.get("align") in JC:
            ppr.append(f'<w:jc w:val="{JC[own["align"]]}"/>')
        lvl = {"h1": 0, "h2": 1, "h3": 2}.get(name)
        if lvl is not None:
            ppr.append(f'<w:keepNext/><w:outlineLvl w:val="{lvl}"/>')  # 제목 - 다음 문단과 붙이고 개요 수준을 준다(목차·탐색 창)
        based = "" if name == "body" else f'<w:basedOn w:val="{"Normal" if st.get("based", "body") == "body" else escape(st.get("based", "body"))}"/>'
        default = ' w:default="1"' if name == "body" else ""
        x.append(f'<w:style w:type="paragraph"{default} w:styleId="{sid}"><w:name w:val="{escape(st.get("name") or name, {chr(34): "&quot;"})}"/>{based}{ppr_next}<w:qFormat/>'
                 + ("<w:pPr>" + "".join(ppr) + "</w:pPr>" if ppr else "") + _rpr(own, ctx, True) + "</w:style>")
    x.append("</w:styles>")
    return "".join(x)


def _numbering(ctx):
    def lvls(kind):
        out = []
        for lv in range(9):
            left, hang = tw((lv + 1) * LIST_INDENT), tw(LIST_INDENT)
            if kind == "number":
                fmt = ("decimal", "lowerLetter", "lowerRoman")[lv % 3]
                out.append(f'<w:lvl w:ilvl="{lv}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="%{lv + 1}."/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{left}" w:hanging="{hang}"/></w:pPr></w:lvl>')
            else:
                ch = {"bullet": "•◦▪"[lv % 3], "check": "☐", "done": "☑"}[kind]
                out.append(f'<w:lvl w:ilvl="{lv}"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="{ch}"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{left}" w:hanging="{hang}"/></w:pPr></w:lvl>')
        return "".join(out)
    x = [XML, f"<w:numbering {NS}>"]
    for aid, kind in ((1, "bullet"), (2, "number"), (3, "check"), (4, "done")):
        x.append(f'<w:abstractNum w:abstractNumId="{aid}"><w:multiLevelType w:val="hybridMultilevel"/>{lvls(kind)}</w:abstractNum>')
    for nid, aid in ((1, 1), (3, 3), (4, 4)):
        x.append(f'<w:num w:numId="{nid}"><w:abstractNumId w:val="{aid}"/></w:num>')
    for nid, aid in ctx.nums:  # 번호 목록 묶음마다 - 모든 단계를 1부터 다시
        x.append(f'<w:num w:numId="{nid}"><w:abstractNumId w:val="{aid}"/>' + "".join(f'<w:lvlOverride w:ilvl="{lv}"><w:startOverride w:val="1"/></w:lvlOverride>' for lv in range(9)) + "</w:num>")
    x.append("</w:numbering>")
    return "".join(x)


def _page_number(pos):
    jc = {"left": "left", "center": "center", "right": "right"}[pos.rsplit("-", 1)[-1] if "-" in pos else "center"]
    return (f'<w:p><w:pPr><w:jc w:val="{jc}"/></w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def build(doc, fonts=None, colors=None, images=None):
    """페이지 문서 → .docx 바이트. images = {src: (bytes, 너비 px, 높이 px)}."""
    doc = page_doc.normalize(doc)
    e = page_doc.validate(doc)
    if e:
        raise ValueError("페이지 형식 아님 - " + e)
    ctx = Ctx(fonts, colors, images)
    box = page_doc.page_box(doc)
    page = doc["page"]
    style_ids = set(doc["styles"])
    body = _blocks(doc["blocks"], ctx, box["cw"], style_ids)
    number = page.get("number") or {}
    parts, refs = {}, []
    for part, tag in (("header", "hdr"), ("footer", "ftr")):
        blocks = (page.get(part) or {}).get("blocks") or []
        inner = _blocks(blocks, ctx, box["cw"], style_ids)
        if number.get("show") and str(number.get("pos") or "footer-center").startswith(part):
            inner += _page_number(str(number.get("pos") or "footer-center"))
        if inner:
            rid = ctx.rel(f"http://schemas.openxmlformats.org/officeDocument/2006/relationships/{part}", f"{part}1.xml")
            parts[f"word/{part}1.xml"] = XML + f"<w:{tag} {NS}>{inner}</w:{tag}>"
            refs.append(f'<w:{part}Reference w:type="default" r:id="{rid}"/>')
    orient = ' w:orient="landscape"' if page.get("orient") == "landscape" else ""
    sect = (f'<w:sectPr>{"".join(refs)}<w:pgSz w:w="{tw(box["w"])}" w:h="{tw(box["h"])}"{orient}/>'
            f'<w:pgMar w:top="{tw(box["t"])}" w:right="{tw(box["r"])}" w:bottom="{tw(box["b"])}" w:left="{tw(box["l"])}" w:header="{tw(min(12.5, box["t"] / 2))}" w:footer="{tw(min(12.5, box["b"] / 2))}" w:gutter="0"/></w:sectPr>')
    document = XML + f"<w:document {NS}><w:body>{body}{sect}</w:body></w:document>"
    rels = [("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml", False),
            ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering", "numbering.xml", False),
            ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings", "settings.xml", False)] + ctx.rels
    rel_xml = lambda items: XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(  # noqa: E731
        f'<Relationship Id="{i}" Type="{t}" Target="{escape(g, {chr(34): "&quot;"})}"' + (' TargetMode="External"' if ext else "") + "/>" for i, t, g, ext in items) + "</Relationships>"
    exts = sorted({n.rsplit(".", 1)[-1] for n in ctx.media})
    types = (XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>' + "".join(f'<Default Extension="{x}" ContentType="{IMG_TYPES[x]}"/>' for x in exts)
             + '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
             '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
             '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
             + "".join(f'<Override PartName="/{n}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{"header" if "header" in n else "footer"}+xml"/>' for n in parts)
             + '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>')
    core = (XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:title>{escape(str(doc.get("title") or ""))}</dc:title><dc:creator>nexa-slide</dc:creator></cp:coreProperties>')
    settings = XML + f'<w:settings {NS}><w:defaultTabStop w:val="{tw(10)}"/><w:characterSpacingControl w:val="doNotCompress"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rel_xml([("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "word/document.xml", False),
                                           ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml", False)]))
        z.writestr("docProps/core.xml", core)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", rel_xml(rels))
        z.writestr("word/styles.xml", _styles(doc, ctx))
        z.writestr("word/numbering.xml", _numbering(ctx))
        z.writestr("word/settings.xml", settings)
        for name, xml in parts.items():
            z.writestr(name, xml)
        for name, data in ctx.media.items():
            z.writestr(f"word/media/{name}", data)
    return buf.getvalue()


def _collect_images(doc, root):
    """문서의 그림 파일을 읽는다 {src: (bytes, w px, h px)} - 작업 공간 밖 경로·없는 파일은 뺀다(문서에는 '그림 없음' 으로 나간다)."""
    out = {}
    root = Path(root).resolve()
    for _, b in page_doc.walk(doc):
        src = b.get("src") if b.get("type") == "image" else None
        if not isinstance(src, str) or src in out or re.match(r"^(https?:|data:)", src):
            continue
        p = (root / src).resolve()
        if root not in p.parents or not p.is_file():
            continue
        try:
            from PIL import Image
            with Image.open(p) as im:
                w, h = im.size
            out[src] = (p.read_bytes(), w, h)
        except Exception:  # noqa: BLE001 - 읽지 못하는 그림은 뺀다
            continue
    return out


def export(doc, out, fonts=None, colors=None, root=None):
    """파일로 쓴다 - out 경로를 돌려준다."""
    from common import WORKSPACE
    images = _collect_images(doc, root or WORKSPACE)
    data = build(doc, fonts, colors, images)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(out)
    return out


def workspace_tokens():
    """작업 공간 토큰에서 글꼴·색을 꺼낸다(없으면 기본값) - 화면이 쓰는 것과 같은 tokens."""
    try:
        from common import resolve_tokens
        t = resolve_tokens()
    except Exception:  # noqa: BLE001
        return {}, {}
    return token_maps(t)


# 페이지 스타일이 쓰는 이름 → 템플릿 토큰 이름(화면 page.js 의 TOKEN_ALIAS 와 같다)
COLOR_ALIAS = {"accent": "primary", "muted": "on-surface-variant", "ink": "on-surface"}
FONT_ALIAS = {"title": "heading"}


def token_maps(t):
    """템플릿 토큰(tokens.json) → (글꼴 {역할: {latin, ea}}, 색 {이름: #RRGGBB}) - 별칭(accent·muted·ink · title)을 채운다."""
    fonts = {}
    for k, v in (t.get("fonts") or {}).items():
        if isinstance(v, dict) and (v.get("latin") or v.get("ea")):
            fonts[k] = {"latin": v.get("latin") or v.get("ea"), "ea": v.get("ea") or v.get("latin")}
        elif isinstance(v, str) and v:
            fonts[k] = v.split(",")[0].strip().strip("\"'")
    for alias, name in FONT_ALIAS.items():
        if name in fonts and alias not in fonts:
            fonts[alias] = fonts[name]
    colors = {k: v for k, v in (t.get("colors") or {}).items() if isinstance(v, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", v)}
    for alias, name in COLOR_ALIAS.items():
        if name in colors and alias not in colors:
            colors[alias] = colors[name]
    return fonts, colors


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="페이지 문서 → docx")
    ap.add_argument("id")
    ap.add_argument("--out")
    a = ap.parse_args()
    from common import OUT, load_deck, safe_id
    safe_id(a.id)
    doc = load_deck(a.id)
    if doc.get("kind") != "page":
        sys.exit(f"페이지 문서가 아니다: {a.id} (kind = {doc.get('kind') or 'deck'})")
    fonts, colors = workspace_tokens()
    out = export(doc, Path(a.out) if a.out else OUT / f"{a.id}.docx", fonts, colors)
    print(out)


if __name__ == "__main__":
    main()
