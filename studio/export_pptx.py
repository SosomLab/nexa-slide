# -*- coding: utf-8 -*-
"""덱 JSON → 편집 가능한 PPTX (python-pptx, 모든 요소를 PowerPoint 기본 도형으로).

    python3 studio/export_pptx.py ch00            # → out/ch00.pptx
    python3 studio/export_pptx.py ch00 --out x.pptx
    python3 studio/export_pptx.py --selftest [--out x.pptx]   # 채우기(단색·투명도·그라데이션) 견본을 내보내 XML 점검

단위: 요소 좌표 px(1280×720) → EMU = px × 9525, 글자 size(px) → pt = px × 0.75.
줄 간격은 "정확히(pt)" = size × lineHeight × 0.75 로 넣어 브라우저 line-height 와 같게 한다.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (cur_fonts, font_role, use_fonts, BULLET_HEAVY, table_merges, table_merges, table_merges, CODE_GUTTER_W, CODE_PAD_Y, OUT, REPO, HL_ROLE, bullet_rows, num_hang, code_lines, code_style, color, fill_spec, load_deck,  # noqa: E402
                    pad_of, plan_runs, radius, runs, safe_id, table_grid, tokens)

from lxml import etree  # noqa: E402  (python-pptx 의존성)
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE  # noqa: E402
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402
from pptx.util import Emu  # noqa: E402

PX = 9525


def E(px):
    return Emu(int(round(float(px) * PX)))


def hpt(px):
    """px → 1/100 pt (글자 크기·줄 간격 XML 값)"""
    return int(round(float(px) * 0.75 * 100))


ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
NOSTYLE_TABLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid


def rgb_el(parent_tag, hexv):
    el = etree.SubElement(parent_tag, qn("a:srgbClr")) if parent_tag is not None else etree.Element(qn("a:srgbClr"))
    el.set("val", hexv.lstrip("#").upper())
    return el


def fonts_of(key):
    fs = cur_fonts()  # 슬라이드·덱 글꼴 세트(fontPreset)가 있으면 그 글꼴
    f = fs.get(font_role(key), fs["body"])  # 역할 이름 정규화(render.js font 와 같은 규칙 - "code" 도 mono)
    return f["latin"], f["ea"]


def set_run(r, text, size, bold=False, col="#000000", font="body", highlight=None, italic=False, underline=False):
    """run 서식을 XML로 직접 쓴다(순서: solidFill → highlight → latin → ea → cs)."""
    r.text = text
    rPr = r._r.get_or_add_rPr()
    for c in list(rPr):
        rPr.remove(c)
    rPr.set("lang", "ko-KR")
    rPr.set("altLang", "en-US")
    rPr.set("sz", str(hpt(size)))
    rPr.set("b", "1" if bold else "0")
    rPr.set("i", "1" if italic else "0")
    if underline:
        rPr.set("u", "sng")
    rPr.set("dirty", "0")
    sf = etree.SubElement(rPr, qn("a:solidFill"))
    rgb_el(sf, col or "#000000")
    if highlight:
        hl = etree.SubElement(rPr, qn("a:highlight"))
        rgb_el(hl, highlight)
    latin, ea = fonts_of(font)
    etree.SubElement(rPr, qn("a:latin")).set("typeface", latin)
    etree.SubElement(rPr, qn("a:ea")).set("typeface", ea)
    etree.SubElement(rPr, qn("a:cs")).set("typeface", latin)


def end_para(p, size):
    """빈 줄도 같은 높이를 갖도록 endParaRPr 크기 지정"""
    epr = p._p.find(qn("a:endParaRPr"))
    if epr is None:
        epr = etree.SubElement(p._p, qn("a:endParaRPr"))
    epr.set("lang", "ko-KR")
    epr.set("sz", str(hpt(size)))


def para_fmt(p, size, lh, align="left", after_px=0):
    p.alignment = ALIGN.get(align, PP_ALIGN.LEFT)
    pPr = p._p.get_or_add_pPr()
    for tag in ("a:lnSpc", "a:spcBef", "a:spcAft"):
        for c in pPr.findall(qn(tag)):
            pPr.remove(c)
    ln = etree.SubElement(pPr, qn("a:lnSpc"))
    etree.SubElement(ln, qn("a:spcPts")).set("val", str(hpt(size * lh)))
    sb = etree.SubElement(pPr, qn("a:spcBef"))
    etree.SubElement(sb, qn("a:spcPts")).set("val", "0")
    sa = etree.SubElement(pPr, qn("a:spcAft"))
    etree.SubElement(sa, qn("a:spcPts")).set("val", str(hpt(after_px)))
    return pPr


def frame(tf, pad=(0, 0, 0, 0), valign="top", wrap=True):
    tf.word_wrap = bool(wrap)
    tf.auto_size = MSO_AUTO_SIZE.NONE
    t, r, b, l = pad
    tf.margin_top, tf.margin_right, tf.margin_bottom, tf.margin_left = E(t), E(r), E(b), E(l)
    tf.vertical_anchor = ANCHOR.get(valign, MSO_ANCHOR.TOP)
    bp = tf._txBody.find(qn("a:bodyPr"))
    bp.set("rtlCol", "0")


def fill_markup_text(tf, el, page, default_color="on-surface"):
    """text/pill/rect 글자(인라인 강조 포함) → 단락들"""
    size = float(el.get("size", 20))
    lh = float(el.get("lineHeight", 1.2 if el["type"] in ("pill", "ellipse", "rect") else 1.4))
    base = color(el.get("color", default_color))
    bold = bool(el.get("bold", el["type"] == "pill"))
    font = el.get("font", "body")
    lines = str(el.get("text", "")).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para_fmt(p, size, lh, el.get("align", "center" if el["type"] in ("pill", "ellipse") else "left"))
        for t, st in runs(line, page):
            if t:
                set_run(p.add_run(), t, size, st.get("bold", bold), color(st.get("color")) if st.get("color") else base, font, italic=st.get("italic", False), underline=st.get("underline", False))
        end_para(p, size)


def strip_style(shape):
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


def alpha_el(clr, alpha):
    """srgbClr 에 불투명도(a:alpha, 1/1000 %) - 1 이면 안 쓴다"""
    if alpha < 1:
        etree.SubElement(clr, qn("a:alpha")).set("val", str(int(round(alpha * 100000))))


def shape_fill_line(shape, el):
    f = fill_spec(el.get("fill"))  # 단색(+투명도) · 선형 그라데이션 - render.fillCss 와 같은 규칙
    if f:
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(f["color"][1:] if f["kind"] == "solid" else f["stops"][0][1][1:])
        sf = shape._element.spPr.find(qn("a:solidFill"))
        if f["kind"] == "solid":
            alpha_el(sf.find(qn("a:srgbClr")), f["alpha"])
        else:  # solidFill 자리에 gradFill(gsLst + lin). ang = 1/60000 도, 0 = 왼→오, 시계 방향. scaled=0 = CSS linear-gradient 와 같은 기하
            gf = etree.Element(qn("a:gradFill"))
            gf.set("rotWithShape", "1")
            gs = etree.SubElement(gf, qn("a:gsLst"))
            for pos, hexv, alpha in f["stops"]:
                g = etree.SubElement(gs, qn("a:gs"))
                g.set("pos", str(int(round(pos * 100000))))
                alpha_el(rgb_el(g, hexv), alpha)
            lin = etree.SubElement(gf, qn("a:lin"))
            lin.set("ang", str(int(round(f["angle"] * 60000))))
            lin.set("scaled", "0")
            sf.getparent().replace(sf, gf)
    else:
        shape.fill.background()
    if el.get("stroke"):
        shape.line.color.rgb = RGBColor.from_string(color(el["stroke"])[1:])
        shape.line.width = E(el.get("strokeWidth", 1))
    else:
        shape.line.fill.background()


def add_shape(slide, el, kind):
    x, y, w, h = el["x"], el["y"], el["w"], el["h"]
    if kind == "ellipse":
        shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, E(x), E(y), E(w), E(h))
    else:
        r = min(w, h) / 2 if kind == "pill" else radius(el.get("radius"), w, h)
        if r > 0:
            shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, E(x), E(y), E(w), E(h))
            shp.adjustments[0] = min(0.5, r / min(w, h))
        else:
            shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, E(x), E(y), E(w), E(h))
    strip_style(shp)
    shape_fill_line(shp, el)
    return shp


def text_pad(el, kind, default=0):
    """PowerPoint 기본 도형의 글자 영역은 도형 안쪽으로 들어가 있다(둥근 사각형 = 반경 × 0.29289, 타원 = 폭·높이 × 0.14645).
    브라우저처럼 도형 가장자리에서 pad 만큼 떨어지도록 그만큼 여백에서 뺀다(음수는 0)."""
    t, r, b, l = pad_of(el, default)
    w, h = float(el["w"]), float(el["h"])
    if kind == "ellipse":
        ix, iy = w * 0.14645, h * 0.14645
    else:
        rad = min(w, h) / 2 if kind == "pill" else radius(el.get("radius"), w, h)
        ix = iy = 0.29289 * rad
    return (max(0, t - iy), max(0, r - ix), max(0, b - iy), max(0, l - ix))


# ---------------------------------------------------------------- 요소별
def do_box(slide, el, page):
    """rect · ellipse · pill · text(fill 있음/없음)"""
    t = el["type"]
    has_text = str(el.get("text", "")) != ""
    if t == "text" and not el.get("fill"):
        shp = slide.shapes.add_textbox(E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]))
    else:
        shp = add_shape(slide, el, "rect" if t == "text" else t)
    if has_text:
        tf = shp.text_frame
        default_valign = "top" if t == "text" else "middle"
        wrap = el.get("wrap", t in ("text", "rect"))
        pad = pad_of(el) if t == "text" and not el.get("fill") else text_pad(el, "rect" if t == "text" else t)
        frame(tf, pad, el.get("valign", default_valign), wrap)
        fill_markup_text(tf, el, page)
    elif t != "text":
        frame(shp.text_frame, (0, 0, 0, 0), "middle", False)
    return shp


SHAPE_PRESETS = {  # render.js SHAPES 와 같은 이름 → PowerPoint 프리셋(기본 조정값) - 기하·글 영역이 render.js 경로와 같다
    "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE, "rtTriangle": MSO_SHAPE.RIGHT_TRIANGLE, "diamond": MSO_SHAPE.DIAMOND, "parallelogram": MSO_SHAPE.PARALLELOGRAM,
    "trapezoid": MSO_SHAPE.TRAPEZOID, "pentagon": MSO_SHAPE.REGULAR_PENTAGON, "hexagon": MSO_SHAPE.HEXAGON, "octagon": MSO_SHAPE.OCTAGON,
    "rightArrow": MSO_SHAPE.RIGHT_ARROW, "leftArrow": MSO_SHAPE.LEFT_ARROW, "upArrow": MSO_SHAPE.UP_ARROW, "downArrow": MSO_SHAPE.DOWN_ARROW,
    "leftRightArrow": MSO_SHAPE.LEFT_RIGHT_ARROW, "chevron": MSO_SHAPE.CHEVRON, "homePlate": MSO_SHAPE.PENTAGON, "star5": MSO_SHAPE.STAR_5_POINT,
    "plus": MSO_SHAPE.CROSS, "callout": MSO_SHAPE.RECTANGULAR_CALLOUT, "roundCallout": MSO_SHAPE.ROUNDED_RECTANGULAR_CALLOUT, "can": MSO_SHAPE.CAN, "cube": MSO_SHAPE.CUBE,
}


def do_shape(slide, el, page):
    """shape - PowerPoint 기본 도형(prstGeom, 기본 조정값). 글은 프리셋의 글 영역에 가운데(render.js elShape 의 rect 와 같다)"""
    shp = slide.shapes.add_shape(SHAPE_PRESETS.get(el.get("shape"), MSO_SHAPE.DIAMOND), E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]))
    strip_style(shp)
    shape_fill_line(shp, el)
    tf = shp.text_frame
    if str(el.get("text", "")) != "":
        frame(tf, pad_of(el), el.get("valign", "middle"), el.get("wrap", True))
        fill_markup_text(tf, {**el, "align": el.get("align", "center"), "lineHeight": el.get("lineHeight", 1.2)}, page)
    else:
        frame(tf, (0, 0, 0, 0), "middle", False)
    return shp


def apply_xfrm(shp, el):
    """요소의 rot(도, 시계 방향)·flipH·flipV 를 도형 xfrm 에(선·표는 제외). render.js 는 같은 값을 CSS transform 으로 그린다."""
    if el.get("type") in ("line", "arrow", "curve", "table", "plan-table") or not (el.get("rot") or el.get("flipH") or el.get("flipV")):
        return
    try:
        xfrm = shp._element.find(f".//{{{NS_A}}}xfrm")
    except Exception:  # noqa: BLE001
        return
    if xfrm is None:
        return
    if el.get("rot"):
        xfrm.set("rot", str(int(round(float(el["rot"]) * 60000))))
    if el.get("flipH"):
        xfrm.set("flipH", "1")
    if el.get("flipV"):
        xfrm.set("flipV", "1")


NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def do_image(slide, el, page):
    p = REPO / el["src"]
    if not p.exists():
        print(f"  ! 이미지 없음: {el['src']}")
        return None
    return slide.shapes.add_picture(str(p), E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]))


def do_line(slide, el, page):
    x1, y1, x2, y2 = (el.get(k) for k in ("x1", "y1", "x2", "y2"))
    if x1 is None:
        x1, y1, x2, y2 = el["x"], el["y"], el["x"] + el["w"], el["y"] + el["h"]
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
    strip_style(c)
    style_line(c.line._get_or_add_ln(), el)
    return c


def do_curve(slide, el, page):
    """곡선 — 꺾은선 근사 자유형(채우기 없음) + 끝 화살 머리. points 는 요소 상자 기준 px."""
    pts = [(el["x"] + x, el["y"] + y) for x, y in el.get("points", [])]
    if len(pts) < 2:
        return None
    fb = slide.shapes.build_freeform(E(pts[0][0]), E(pts[0][1]), scale=1.0)
    fb.add_line_segments([(E(x), E(y)) for x, y in pts[1:]], close=False)
    shp = fb.convert_to_shape()
    strip_style(shp)
    shp.fill.background()
    style_line(shp.line._get_or_add_ln(), {**el, "type": "arrow" if el.get("head", "end") != "none" else "line"})
    return shp


def style_line(ln, el):
    for ch in list(ln):
        ln.remove(ch)
    ln.set("w", str(int(round(float(el.get("width", 2)) * PX))))
    ln.set("cap", "flat")
    sf = etree.SubElement(ln, qn("a:solidFill"))
    rgb_el(sf, color(el.get("color", "on-surface")))
    if el.get("dash") and el["dash"] != "solid":
        etree.SubElement(ln, qn("a:prstDash")).set("val", "sysDot" if el["dash"] == "dot" else "dash")
    head = el.get("head", "end" if el["type"] == "arrow" else "none")
    if head in ("start", "both"):
        he = etree.SubElement(ln, qn("a:headEnd"))
        he.set("type", "triangle"), he.set("w", "lg"), he.set("len", "lg")
    if head in ("end", "both"):
        te = etree.SubElement(ln, qn("a:tailEnd"))
        te.set("type", "triangle"), te.set("w", "lg"), te.set("len", "lg")


def _cell_border(tcPr, side, col=None, w_px=1):
    ln = etree.SubElement(tcPr, qn(f"a:ln{side}"))
    if col:
        ln.set("w", str(int(w_px * PX)))
        ln.set("cap", "flat"), ln.set("cmpd", "sng"), ln.set("algn", "ctr")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        rgb_el(sf, color(col))
        etree.SubElement(ln, qn("a:prstDash")).set("val", "solid")
    else:
        ln.set("w", "0")
        etree.SubElement(ln, qn("a:noFill"))


def do_table(slide, el, page):
    g = table_grid(el)
    nr, nc = len(g["cells"]), len(g["colW"])
    if not nr or not nc:
        return None
    gf = slide.shapes.add_table(nr, nc, E(g["x"]), E(g["y"]), E(g["tw"]), E(sum(g["rowH"])))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    for a in ("firstRow", "bandRow", "firstCol", "lastRow", "lastCol", "bandCol"):
        if a in tblPr.attrib:
            del tblPr.attrib[a]
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = NOSTYLE_TABLE
    for j, cw in enumerate(g["colW"]):
        tbl.columns[j].width = E(cw)
    size = float(g["size"])
    for i in range(nr):
        tbl.rows[i].height = E(g["rowH"][i])
        for j in range(nc):
            c = g["cells"][i][j]
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = E(14)
            cell.margin_top = cell.margin_bottom = E(0)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            para_fmt(p, size, 1.4, c["align"])
            for t, st in runs(c["text"], page):
                if t:
                    set_run(p.add_run(), t, size, st.get("bold", c["bold"]),
                            color(st.get("color") or c["color"]), c["font"], italic=st.get("italic", False), underline=st.get("underline", False))
            end_para(p, size)
            tcPr = cell._tc.get_or_add_tcPr()
            for ch in list(tcPr):
                tcPr.remove(ch)
            tcPr.set("anchor", "ctr")
            _cell_border(tcPr, "L")
            _cell_border(tcPr, "R")
            _cell_border(tcPr, "T")
            is_head = i == 0 and (el.get("type") == "plan-table" or el.get("header", True))
            _cell_border(tcPr, "B", None if is_head else g["rule"], 1)
            if c["fill"]:
                sf = etree.SubElement(tcPr, qn("a:solidFill"))
                rgb_el(sf, color(c["fill"]))
            else:
                etree.SubElement(tcPr, qn("a:noFill"))
    shapes = [gf]
    if el.get("type") != "plan-table":  # 셀 병합 - 왼쪽 위 셀의 글만 남고 덮인 셀은 비운다(render.js elTable 과 같은 규칙)
        span, skip = table_merges(el, nr, nc)
        for (r, c) in sorted(skip):
            tbl.cell(r, c).text_frame.text = ""
        for (r, c), (rs, cs) in span.items():
            tbl.cell(r, c).merge(tbl.cell(r + rs - 1, c + cs - 1))
    for co in g["callouts"]:
        ln = {"type": "line", "x1": co["tx"] + 4, "y1": co["cy"], "x2": co["x"], "y2": co["cy"], "color": co["line"], "width": 2, "head": "none"}
        shapes.append(do_line(slide, ln, page))
        box = {"type": "text", "x": co["x"], "y": co["y"], "w": co["w"], "h": co["h"], "text": co["text"], "size": size,
               "lineHeight": 1.5, "fill": co["fill"], "color": co["color"], "radius": "r-s", "pad": [6, 14, 6, 14], "valign": "middle"}
        shapes.append(do_box(slide, box, page))
    return shapes


def do_plan(slide, el, page):
    """plan: 실행계획 원문(고정폭) + [[강조]] — run 글자색·굵게 + run 강조색(a:highlight)"""
    box = dict(el)
    box.setdefault("fill", "surface-container")
    box.setdefault("radius", "r-m")
    shp = add_shape(slide, box, "rect")
    tf = shp.text_frame
    frame(tf, text_pad(box, "rect", [16, 18, 16, 18]), "top", False)
    size = float(el.get("size", 14))
    lh = float(el.get("lineHeight", 1.5))
    base = color(el.get("color", "on-surface"))
    for i, line in enumerate(str(el.get("text", "")).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para_fmt(p, size, lh)
        for t, role in plan_runs(line):
            if not t:
                continue
            if role:
                bg, fg = HL_ROLE.get(role, HL_ROLE["warn"])
                set_run(p.add_run(), t, size, True, color(fg), "mono", highlight=color(bg))
            else:
                set_run(p.add_run(), t, size, False, base, "mono")
        end_para(p, size)
    return shp


def do_code(slide, el, page):
    """code: DBeaver 라이트 — 그룹 도형(여백 면·코드 면·강조 줄 면·테두리·줄 번호 글상자·코드 글상자).
    render.js elCode 와 같은 배치: 줄 번호 열 48px(오른쪽 여백 12), 코드 왼쪽 여백 14, 위아래 12."""
    x, y, w, h = float(el["x"]), float(el["y"]), float(el["w"]), float(el["h"])
    size = float(el.get("size", 15))
    lh = float(el.get("lineHeight", 1.6))
    L = size * lh
    gw = 0.0 if el.get("lineNo") is False else float(el.get("gutterW", CODE_GUTTER_W))
    r = radius(el.get("radius", "r-m"), w, h)
    lines = code_lines(el)
    grp = slide.shapes.add_group_shape()
    if gw:
        add_shape(grp, {"x": x, "y": y, "w": w, "h": h, "fill": "code-gutter-bg", "radius": r}, "rect")
    add_shape(grp, {"x": x + gw, "y": y, "w": w - gw, "h": h, "fill": "code-bg", "radius": r}, "rect")
    if r > 0 and gw:
        add_shape(grp, {"x": x + gw, "y": y, "w": min(r, w - gw), "h": h, "fill": "code-bg"}, "rect")
    for i, ln in enumerate(lines):
        if ln["focus"]:
            add_shape(grp, {"x": x + gw, "y": y + CODE_PAD_Y + i * L, "w": w - gw, "h": L, "fill": "code-focus"}, "rect")
    add_shape(grp, {"x": x + 0.5, "y": y + 0.5, "w": w - 1, "h": h - 1, "radius": max(0, r - 0.5),
                    "stroke": "surface-container-high", "strokeWidth": 1}, "rect")
    # 줄 번호(lineNo: false 면 없음)
    if gw:
        g = grp.shapes.add_textbox(E(x), E(y + CODE_PAD_Y), E(gw - 12), E(len(lines) * L))
        frame(g.text_frame, (0, 0, 0, 0), "top", False)
        for i, ln in enumerate(lines):
            p = g.text_frame.paragraphs[0] if i == 0 else g.text_frame.add_paragraph()
            para_fmt(p, size, lh, "right")
            set_run(p.add_run(), ln["n"], size, ln["focus"], color("on-surface" if ln["focus"] else "code-gutter"), "mono")
            end_para(p, size)
        g.name = f"{el.get('id')} code-gutter"
    # 코드
    c = grp.shapes.add_textbox(E(x + gw + 14), E(y + CODE_PAD_Y), E(max(1, w - gw - 14)), E(len(lines) * L))
    frame(c.text_frame, (0, 0, 0, 0), "top", False)
    for i, ln in enumerate(lines):
        p = c.text_frame.paragraphs[0] if i == 0 else c.text_frame.add_paragraph()
        para_fmt(p, size, lh)
        for t, role in ln["runs"]:
            col, bold, italic = code_style(role)
            set_run(p.add_run(), t, size, bold, color(col), "mono", italic=italic)
        end_para(p, size)
    c.name = f"{el.get('id')} code-text"
    return grp


def do_bullets(slide, el, page):
    """bullets — 행(글자·수준·뒤 간격)은 common.bullet_rows(spread = 균등 간격 포함), 뒤 간격은 단락 뒤 간격(spcAft)으로"""
    shp = slide.shapes.add_textbox(E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]))
    tf = shp.text_frame
    frame(tf, pad_of(el), el.get("valign", "top"), True)
    size, sub = float(el.get("size", 20)), float(el.get("subSize", 17))
    lh = float(el.get("lineHeight", 1.55))
    for i, (t, lvl, after, num) in enumerate(bullet_rows(el)):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        sz = size if lvl == 0 else sub
        pPr = para_fmt(p, sz, lh, "left", after)
        marL0, hang0 = (28, 28) if lvl == 0 else (48, 20)
        none = bool(num) and num.get("kind") == "none"
        hang = 0 if none else num_hang(num["label"], sz, hang0) if num else hang0
        marL = marL0 - hang0 + hang
        pPr.set("marL", str(marL * PX))
        pPr.set("indent", str(-hang * PX))
        pPr.set("lvl", "0")
        base = color(el.get("color", "on-surface") if lvl == 0 else el.get("subColor", "on-surface-variant"))
        bc = etree.SubElement(pPr, qn("a:buClr"))
        if none:  # 글머리 없음(marker: none) - 내어쓰기도 없이 글만
            pPr.remove(bc)
            etree.SubElement(pPr, qn("a:buNone"))
        elif num and num.get("kind") == "symbol":  # 글 앞의 글머리 기호(* - · • ■ …) - 그 기호를 글머리로, 색은 글머리 색, 굵은 기호는 60%
            rgb_el(bc, color(el.get("dot", "primary") if lvl == 0 else el.get("subColor", "on-surface-variant")))
            etree.SubElement(pPr, qn("a:buSzPct")).set("val", "60000" if num["label"] in BULLET_HEAVY else "100000")
            bf = etree.SubElement(pPr, qn("a:buFont"))
            bf.set("typeface", "맑은 고딕")
            etree.SubElement(pPr, qn("a:buChar")).set("char", num["label"])
        elif num:  # 글 앞의 번호를 자동 감지 - 번호 글머리(자동 번호 종류가 있으면 buAutoNum, 가. 같은 것은 글자 그대로). 색·크기는 글과 같게
            rgb_el(bc, base)
            etree.SubElement(pPr, qn("a:buSzPct")).set("val", "100000")
            etree.SubElement(pPr, qn("a:buFontTx"))
            if num.get("scheme"):
                an = etree.SubElement(pPr, qn("a:buAutoNum"))
                an.set("type", num["scheme"])
                an.set("startAt", str(num["start"]))
            else:
                etree.SubElement(pPr, qn("a:buChar")).set("char", num["label"])
        else:
            rgb_el(bc, color(el.get("dot", "primary") if lvl == 0 else el.get("subColor", "on-surface-variant")))
            etree.SubElement(pPr, qn("a:buSzPct")).set("val", "60000" if lvl == 0 else "100000")
            bf = etree.SubElement(pPr, qn("a:buFont"))
            bf.set("typeface", "맑은 고딕")
            etree.SubElement(pPr, qn("a:buChar")).set("char", "●" if lvl == 0 else "–")
        for tt, st in runs(t, page):
            if tt:
                set_run(p.add_run(), tt, sz, st.get("bold", False), color(st.get("color")) if st.get("color") else base, "body", italic=st.get("italic", False), underline=st.get("underline", False))
        end_para(p, sz)
    return shp


class _GroupHost:
    """묶음 안에 그릴 때 핸들러에 slide 대신 준다(핸들러는 slide.shapes 만 쓴다)."""

    def __init__(self, grp):
        self.shapes = grp.shapes


def do_group(slide, el, page):
    """group - PPTX 묶음 도형(grpSp). 자식은 묶음 상자 기준 좌표 → 절대 좌표로 바꿔 묶음 안에 그린다(표·실행계획 표는 묶음에 못 넣어 건너뛴다). 묶음의 회전·뒤집기는 main 루프의 apply_xfrm."""
    kids = sorted(enumerate(el.get("children", [])), key=lambda t: (t[1].get("z", 0), t[0]))
    if not kids:
        return None
    grp = slide.shapes.add_group_shape()
    host = _GroupHost(grp)
    ox, oy = float(el.get("x", 0)), float(el.get("y", 0))
    n = 0
    for _, c in kids:
        h = HANDLERS.get(c.get("type"))
        if not h or c.get("type") in ("table", "plan-table", "group"):
            print(f"  ! {el.get('id')}: 묶음 안의 {c.get('type')} 은 건너뜀(표·묶음은 묶음에 넣지 않는다)")
            continue
        cc = dict(c)
        if c.get("type") in ("line", "arrow", "curve"):
            for k in ("x1", "x2"):
                if k in cc:
                    cc[k] = cc[k] + ox
            for k in ("y1", "y2"):
                if k in cc:
                    cc[k] = cc[k] + oy
        cc["x"] = float(c.get("x", 0)) + ox
        cc["y"] = float(c.get("y", 0)) + oy
        res = h(host, cc, page)
        for shp in (res if isinstance(res, list) else [res]):
            if shp is not None:
                apply_xfrm(shp, cc)
                n += 1
    if not n:
        grp._element.getparent().remove(grp._element)
        return None
    return grp


HANDLERS = {"rect": do_box, "ellipse": do_box, "pill": do_box, "text": do_box, "image": do_image,
            "line": do_line, "arrow": do_line, "curve": do_curve, "table": do_table, "plan-table": do_table,
            "code": do_code, "plan": do_plan, "bullets": do_bullets, "shape": do_shape, "group": do_group}


def export(deck, out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = E(1280), E(720)
    blank = prs.slide_layouts[6]
    counts = []
    for n, s in enumerate(deck["slides"], 1):
        use_fonts(s.get("fontPreset") or deck.get("fontPreset"))  # 슬라이드 > 덱 > 작업 공간
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(color(s.get("bg", "surface"))[1:])
        els = sorted(enumerate(s.get("elements", [])), key=lambda t: (t[1].get("z", 0), t[0]))
        for _, el in els:
            h = HANDLERS.get(el.get("type"))
            if not h:
                print(f"  ! {s['id']}/{el.get('id')}: 모르는 요소 {el.get('type')}")
                continue
            res = h(slide, el, n)
            for shp in (res if isinstance(res, list) else [res]):
                if shp is not None:
                    apply_xfrm(shp, el)
                    shp.name = f"{el.get('id')} {el.get('type')}"
        if s.get("notes"):
            slide.notes_slide.notes_text_frame.text = s["notes"]
        counts.append(len(slide.shapes))
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return counts


def selftest(out):
    """채우기 견본(단색 · #hexAA · 색+alpha · 그라데이션 각도/정지점/고른 간격 · 글상자)을 내보내 슬라이드 XML 을 점검한다(개발·설치 점검용)."""
    import zipfile
    deck = {"id": "selftest", "slides": [{"id": "s01", "elements": [
        {"id": "e01", "type": "pill", "x": 80, "y": 200, "w": 400, "h": 80, "text": "01", "color": "white", "size": 32,
         "fill": {"gradient": {"angle": 0, "stops": [[0, "#002F7B00"], [1, "#002F7B"]]}}},
        {"id": "e02", "type": "rect", "x": 80, "y": 320, "w": 400, "h": 80, "fill": "#002F7B80", "radius": "r-m"},
        {"id": "e03", "type": "ellipse", "x": 560, "y": 200, "w": 120, "h": 120, "fill": {"color": "primary", "alpha": 0.5}},
        {"id": "e04", "type": "rect", "x": 560, "y": 340, "w": 400, "h": 60, "fill": {"gradient": {"angle": 90, "stops": ["#DCE3F0", "#B4C4E2", "#7F98C9", "#3F62A2"]}}},
        {"id": "e05", "type": "text", "x": 80, "y": 440, "w": 400, "h": 60, "text": "글", "fill": {"gradient": {"angle": 45, "stops": [[0, "primary", 0.2], [1, "primary"]]}, "alpha": 0.9}},
        {"id": "e06", "type": "pill", "x": 560, "y": 440, "w": 200, "h": 40, "text": "단색", "fill": "primary", "color": "white"},
    ]}]}
    out = Path(out)
    export(deck, out)
    with zipfile.ZipFile(out) as z:
        xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    sp = {}  # 요소 id → spPr XML
    for m in re.finditer(r"<p:sp>.*?</p:sp>", xml, re.S):
        nm, pr = re.search(r'name="(e\d\d) ', m.group(0)), re.search(r"<p:spPr>.*?</p:spPr>", m.group(0), re.S)
        if nm and pr:
            sp[nm.group(1)] = pr.group(0)
    prim = color("primary")[1:]
    solid = re.compile(r'<a:solidFill><a:srgbClr val="[0-9A-F]{6}"/></a:solidFill>')
    checks = [
        ("도형 6개", len(sp) == 6),
        ("그라데이션 투명→진한", '<a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:srgbClr val="002F7B"><a:alpha val="0"/></a:srgbClr></a:gs>'
         '<a:gs pos="100000"><a:srgbClr val="002F7B"/></a:gs></a:gsLst><a:lin ang="0" scaled="0"/></a:gradFill>' in sp.get("e01", "")),
        ("gradFill 이 ln 앞", all("<a:gradFill" in sp[k] and sp[k].index("<a:gradFill") < sp[k].index("<a:ln") for k in ("e01", "e04", "e05") if k in sp)),
        ("#hexAA 투명도", '<a:solidFill><a:srgbClr val="002F7B"><a:alpha val="50200"/></a:srgbClr></a:solidFill>' in sp.get("e02", "")),
        ("토큰+alpha", f'<a:solidFill><a:srgbClr val="{prim}"><a:alpha val="50000"/></a:srgbClr></a:solidFill>' in sp.get("e03", "")),
        ("고른 간격·위→아래", re.findall(r'<a:gs pos="(\d+)">', sp.get("e04", "")) == ["0", "33330", "66670", "100000"] and '<a:lin ang="5400000" scaled="0"/>' in sp.get("e04", "")),
        ("정지점 불투명도 × 전체 alpha", f'<a:gs pos="0"><a:srgbClr val="{prim}"><a:alpha val="18000"/></a:srgbClr></a:gs><a:gs pos="100000"><a:srgbClr val="{prim}"><a:alpha val="90000"/>' in sp.get("e05", "")
         and '<a:lin ang="2700000" scaled="0"/>' in sp.get("e05", "")),
        ("단색 그대로", bool(solid.search(sp.get("e06", ""))) and "<a:alpha" not in sp.get("e06", "") and "<a:gradFill" not in sp.get("e06", "")),
    ]
    bad = [n for n, ok in checks if not ok]
    print("selftest: " + ("모두 통과 " + str([n for n, _ in checks]) if not bad else "실패 " + str(bad)))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true", help="채우기 견본을 내보내 슬라이드 XML 을 점검")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.out or OUT / ".studio" / "export-selftest.pptx"))
    if not a.id:
        ap.error("덱 id 를 준다")
    if not safe_id(a.id):
        sys.exit("잘못된 덱 id")
    out = Path(a.out) if a.out else OUT / f"{a.id}.pptx"
    counts = export(load_deck(a.id), out)
    print(f"{out} — 슬라이드 {len(counts)}장, 도형 {sum(counts)}개 ({', '.join(map(str, counts))})")
    if not a.out:  # 실제로 쓴 글꼴 기록 → out/<덱>.fonts.json (기록 실패는 내보내기를 막지 않는다)
        try:
            import font_report
            fo, rep = font_report.write(a.id, out)
            print(f"{fo} — 글꼴 " + ", ".join(u["typeface"] for u in rep["used"]))
        except Exception as e:  # noqa: BLE001
            print(f"글꼴 기록 실패: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
