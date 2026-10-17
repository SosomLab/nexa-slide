# -*- coding: utf-8 -*-
"""덱 JSON → 편집 가능한 PPTX (python-pptx, 모든 요소를 PowerPoint 기본 도형으로).

    python3 studio/export_pptx.py ch00            # → out/ch00.pptx
    python3 studio/export_pptx.py ch00 --out x.pptx
    python3 studio/export_pptx.py --selftest [--out x.pptx]   # 채우기(단색·투명도·그라데이션)·선 투명도·순서도 도형 견본을 내보내 XML 점검

단위: 요소 좌표 px(1280×720) → EMU = px × 9525, 글자 size(px) → pt = px × 0.75.
줄 간격은 "정확히(pt)" = size × lineHeight × 0.75 로 넣어 브라우저 line-height 와 같게 한다.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (cur_fonts, font_role, use_fonts, BULLET_HEAVY, table_merges, table_merges, table_merges, CODE_GUTTER_W, CODE_PAD_Y, OUT, REPO, HL_ROLE, bullet_rows, num_hang, code_lines, code_style, color, color_alpha, fill_spec, load_deck,  # noqa: E402
                    pad_of, plan_runs, radius, runs, safe_id, table_grid, tokens)

from lxml import etree  # noqa: E402  (python-pptx 의존성)
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE  # noqa: E402
from pptx.chart.data import CategoryChartData  # noqa: E402
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION  # noqa: E402
from pptx.util import Pt  # noqa: E402
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


_RUN_LINKS = []  # (rPr, 링크, 슬라이드 part) - 글자 단위 링크([[link:…|글]])는 슬라이드가 모두 만들어진 뒤 건다(뒤 슬라이드로도 가게)
_CUR = {"part": None}  # 지금 그리는 슬라이드의 part(export 루프가 바꾼다)


def set_run(r, text, size, bold=False, col="#000000", font="body", highlight=None, italic=False, underline=False, st=None):
    """run 서식을 XML로 직접 쓴다(순서: solidFill → highlight → latin → ea → cs → hlinkClick).
    st = common.runs 의 스타일 사전 - strike(취소선 sngStrike) · sup/sub(baseline ±) · bg(형광펜 = a:highlight) · link(글자 링크 - 밑줄, 색은 글자색 유지)."""
    st = st or {}
    r.text = text
    rPr = r._r.get_or_add_rPr()
    for c in list(rPr):
        rPr.remove(c)
    rPr.set("lang", "ko-KR")
    rPr.set("altLang", "en-US")
    rPr.set("sz", str(hpt(size)))
    rPr.set("b", "1" if bold else "0")
    rPr.set("i", "1" if italic else "0")
    if underline or st.get("link"):
        rPr.set("u", "sng")
    if st.get("strike"):
        rPr.set("strike", "sngStrike")
    if st.get("sup"):
        rPr.set("baseline", "30000")  # 위첨자(render.js spanRuns 와 같은 모양 - 글자 65%, 올림)
    elif st.get("sub"):
        rPr.set("baseline", "-25000")
    rPr.set("dirty", "0")
    sf = etree.SubElement(rPr, qn("a:solidFill"))
    rgb_el(sf, col or "#000000")
    if not highlight and st.get("bg"):
        highlight = color(st["bg"])
    if highlight:
        hl = etree.SubElement(rPr, qn("a:highlight"))
        rgb_el(hl, highlight)
    latin, ea = fonts_of(font)
    etree.SubElement(rPr, qn("a:latin")).set("typeface", latin)
    etree.SubElement(rPr, qn("a:ea")).set("typeface", ea)
    etree.SubElement(rPr, qn("a:cs")).set("typeface", latin)
    if st.get("link"):
        _RUN_LINKS.append((rPr, str(st["link"]).strip(), _CUR["part"]))


def apply_run_links(prs, index):
    """글자 단위 링크 - URL 은 외부 관계 + hlinkClick, '#3'·'#<슬라이드 id>' 는 슬라이드 관계 + ppaction://hlinksldjump.
    hlinkClr val=tx(Office 2019+ 확장) 로 글자색을 유지한다 - 이전 PowerPoint 는 테마 링크색(파랑)으로 보일 수 있다."""
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    for rPr, v, part in _RUN_LINKS:
        if part is None or not v:
            continue
        try:
            if v.startswith("#"):
                key = v[1:]
                n = int(key) if key.isdigit() else index.get(key)
                if not (n and 1 <= n <= len(prs.slides)):
                    print(f"  ! 글자 링크 - 없는 슬라이드 {v}")
                    continue
                rid = part.relate_to(prs.slides[n - 1].part, RT.SLIDE)
                h = rPr.get_or_add_hlinkClick()
                h.set(qn("r:id"), rid)
                h.set("action", "ppaction://hlinksldjump")
            else:
                rid = part.relate_to(v, RT.HYPERLINK, is_external=True)
                h = rPr.get_or_add_hlinkClick()
                h.set(qn("r:id"), rid)
            ns = "http://schemas.microsoft.com/office/drawing/2018/hyperlinkcolor"
            ext = etree.SubElement(etree.SubElement(h, qn("a:extLst")), qn("a:ext"))
            ext.set("uri", "{A12FA001-AC4F-418D-AE19-62706E023703}")
            etree.SubElement(ext, f"{{{ns}}}hlinkClr", nsmap={"ahyp": ns}).set("val", "tx")
        except Exception as e:  # noqa: BLE001
            print(f"  ! 글자 링크를 걸지 못함 {v} - {e}")
    _RUN_LINKS.clear()


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
                set_run(p.add_run(), t, size, st.get("bold", bold), color(st.get("color")) if st.get("color") else base, font, italic=st.get("italic", False), underline=st.get("underline", False), st=st)
        end_para(p, size)


def strip_style(shape):
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


def alpha_el(clr, alpha):
    """srgbClr 에 불투명도(a:alpha, 1/1000 %) - 1 이면 안 쓴다"""
    if alpha < 1:
        etree.SubElement(clr, qn("a:alpha")).set("val", str(int(round(alpha * 100000))))


def stroke_rgb(value, default="#000000"):
    """선·테두리 색(stroke · 선 color · 표 테두리 · 액자) - 토큰·#RRGGBB·#RRGGBBAA → ('#RRGGBB', 불투명도). render.js strokeCss 와 같은 규칙(common.color_alpha).
    PPTX 는 a:ln > a:solidFill > a:srgbClr 에 a:alpha(alpha_el, 1 미만일 때만) - 불투명한 선의 XML 은 전과 같다."""
    return color_alpha(value, default) or (default, 1.0)


def set_line_color(line, value, default="#000000"):
    """python-pptx LineFormat 에 선 색(+투명도) - line.color.rgb 가 만든 a:srgbClr 에 a:alpha 를 붙인다"""
    hexv, a = stroke_rgb(value, default)
    line.color.rgb = RGBColor.from_string(hexv[1:])
    if a < 1:
        alpha_el(line._get_or_add_ln().find(qn("a:solidFill")).find(qn("a:srgbClr")), a)


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
        set_line_color(shape.line, el["stroke"])  # #RRGGBBAA 면 a:alpha(0.22.23)
        shape.line.width = E(el.get("strokeWidth", 1))
        d = el.get("strokeDash")
        if d and d != "solid":  # 도형 테두리 점선·파선(render.js strokeDashSvg 와 같은 간격 - 선 요소의 dash 와 같은 값)
            from pptx.enum.dml import MSO_LINE_DASH_STYLE
            shape.line.dash_style = MSO_LINE_DASH_STYLE.ROUND_DOT if d == "dot" else MSO_LINE_DASH_STYLE.DASH
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
    # 순서도 4종(0.22.23) - prst flowChartProcess · flowChartDecision · flowChartDocument · flowChartInputOutput
    "flowChartProcess": MSO_SHAPE.FLOWCHART_PROCESS, "flowChartDecision": MSO_SHAPE.FLOWCHART_DECISION, "flowChartDocument": MSO_SHAPE.FLOWCHART_DOCUMENT, "flowChartInputOutput": MSO_SHAPE.FLOWCHART_DATA,
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


def apply_shadow(shp, el):
    """shadow(true 또는 {blur, dx, dy, color, alpha}) → a:effectLst/a:outerShdw (render.js shadowCss 와 같은 기본값)."""
    v = el.get("shadow")
    if not v or el.get("type") in ("line", "arrow", "curve", "table", "plan-table", "table-obj"):
        return
    o = v if isinstance(v, dict) else {}
    blur, dx, dy = float(o.get("blur", 6)), float(o.get("dx", 2)), float(o.get("dy", 3))
    col, alpha = color(o.get("color", "#000000")) or "#000000", float(o.get("alpha", 0.3))
    try:
        sp = shp._element.spPr
    except AttributeError:
        return
    import math
    for old in sp.findall(qn("a:effectLst")):
        sp.remove(old)
    ef = etree.SubElement(sp, qn("a:effectLst"))
    sh = etree.SubElement(ef, qn("a:outerShdw"))
    sh.set("blurRad", str(int(blur * PX)))
    sh.set("dist", str(int(math.hypot(dx, dy) * PX)))
    sh.set("dir", str(int((math.degrees(math.atan2(dy, dx)) % 360) * 60000)))
    sh.set("algn", "ctr")
    sh.set("rotWithShape", "0")
    c = etree.SubElement(sh, qn("a:srgbClr"))
    c.set("val", col.lstrip("#").upper()[:6])
    etree.SubElement(c, qn("a:alpha")).set("val", str(int(max(0.0, min(1.0, alpha)) * 100000)))


EFFECT_PX = {"softEdge": (6, 12, 24), "round": (8, 16, 32), "frame": (3, 6, 10), "glow": (8, 16, 24)}  # render.js EFFECT_PX 와 같다


def apply_effect(pic, el):
    """그림 프레임 효과 effect(softEdge·round·circle·frame·glow) · effectLevel 1~3 - 원본 파일은 그대로, 도형 속성으로만.
    softEdge/glow → a:effectLst(그림자 뒤에 덧붙임), round/circle → prstGeom, frame → 흰 테두리(a:ln) + 기본 그림자."""
    e = el.get("effect")
    if not e or pic is None:
        return
    if el.get("type") != "image":  # 도형(rect·ellipse·pill·text·shape)은 광선·부드러운 가장자리만(render.js 와 같다)
        if el.get("type") not in ("rect", "ellipse", "pill", "text", "shape") or e not in ("softEdge", "glow"):
            return
    lv = max(1, min(3, int(el.get("effectLevel") or 2)))
    px = EFFECT_PX.get(e, (0, 0, 0))[lv - 1]
    sp = pic._element.spPr
    if e in ("round", "circle"):
        geom = sp.find(qn("a:prstGeom"))
        if geom is None:
            geom = etree.SubElement(sp, qn("a:prstGeom"))
        for ch in list(geom):
            geom.remove(ch)
        if e == "circle":
            geom.set("prst", "ellipse"); etree.SubElement(geom, qn("a:avLst"))
        else:
            geom.set("prst", "roundRect")
            av = etree.SubElement(geom, qn("a:avLst"))
            m = max(1.0, min(float(el["w"]), float(el["h"])))
            etree.SubElement(av, qn("a:gd")).set("name", "adj"); av[0].set("fmla", f"val {int(min(50000, 100000 * px / m))}")
        return
    if e == "frame":  # 액자 - 테두리 두께(frameWidth, 기본 = 수준)·색(frameColor, 기본 흰색) + 기본 그림자 (render.js effectCss 와 같다)
        fw = float(el.get("frameWidth") or px)
        pic.line.width = Pt(fw * 0.75)
        set_line_color(pic.line, el.get("frameColor") or "#FFFFFF", "#FFFFFF")
        if not el.get("shadow"):
            apply_shadow(pic, {**el, "shadow": {"blur": 6, "dx": 0, "dy": 2, "alpha": 0.3}})
        return
    ef = sp.find(qn("a:effectLst"))
    if ef is None:
        ef = etree.SubElement(sp, qn("a:effectLst"))
    if e == "softEdge":
        etree.SubElement(ef, qn("a:softEdge")).set("rad", str(E(px)))
    elif e == "glow":
        g = etree.SubElement(ef, qn("a:glow")); g.set("rad", str(E(px)))
        c = etree.SubElement(g, qn("a:srgbClr")); c.set("val", (color(el.get("effectColor", "primary")) or "#000000").lstrip("#"))
        etree.SubElement(c, qn("a:alpha")).set("val", "60000")


def apply_link(shp, el, slides, index):
    """link: 'https://…' 또는 '#3'(3번 슬라이드)·'#<슬라이드 id>' → click_action. slides 는 prs.slides, index 는 {slide id: 번호}"""
    v = str(el.get("link") or "").strip()
    if not v:
        return
    try:
        if v.startswith("#"):
            key = v[1:]
            n = int(key) if key.isdigit() else index.get(key)
            if n and 1 <= n <= len(slides):
                shp.click_action.target_slide = slides[n - 1]
        else:
            shp.click_action.hyperlink.address = v
    except Exception as e:  # noqa: BLE001 - 묶음 등 링크를 못 거는 도형
        print(f"  ! {el.get('id')}: 링크를 걸지 못함 - {e}")


def apply_xfrm(shp, el):
    """요소의 rot(도, 시계 방향)·flipH·flipV 를 도형 xfrm 에(선·표는 제외). render.js 는 같은 값을 CSS transform 으로 그린다."""
    if el.get("type") in ("line", "arrow", "curve", "table", "plan-table", "table-obj") or not (el.get("rot") or el.get("flipH") or el.get("flipV")):
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


_PNG_1PX = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")  # 1×1 투명


def _svg_fallback_png(svg_path):
    """SVG 의 대체 PNG - 옆에 같은 이름의 .png 가 있으면 그것(편집기가 올릴 때 만들어 둘 수 있다), 없으면 1×1 투명(PowerPoint 2016 이전은 빈 그림)."""
    alt = svg_path.with_suffix(".png")
    if alt.is_file():
        return alt.read_bytes()
    return _PNG_1PX


def add_svg_picture(slide, path, x, y, w, h):
    """SVG 그림 - PowerPoint 2016+ 의 svgBlip 확장(a:blip 안 asvg:svgBlip). 본 blip 은 대체 PNG(_svg_fallback_png). Pillow 가 SVG 를 못 읽어 add_picture 로는 실패한다."""
    import io
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.opc.package import Part
    from pptx.opc.packuri import PackURI
    pic = slide.shapes.add_picture(io.BytesIO(_svg_fallback_png(path)), x, y, w, h)
    pkg = slide.part.package
    partname = pkg.next_partname("/ppt/media/image%d.svg")
    part = Part(PackURI(str(partname)), "image/svg+xml", pkg, path.read_bytes())
    rid = slide.part.relate_to(part, RT.IMAGE)
    blip = pic._element.find(f".//{{{NS_A}}}blip")
    ns = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
    ext = etree.SubElement(etree.SubElement(blip, qn("a:extLst")), qn("a:ext"))
    ext.set("uri", "{96DAC541-7B7A-43D3-8B79-37D633B846F1}")
    etree.SubElement(ext, f"{{{ns}}}svgBlip", nsmap={"asvg": ns}).set(qn("r:embed"), rid)
    return pic


def do_image(slide, el, page):
    p = REPO / el["src"]
    if not p.exists():
        print(f"  ! 이미지 없음: {el['src']}")
        return None
    if p.suffix.lower() == ".svg":
        pic = add_svg_picture(slide, p, E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]))
    else:
        pic = slide.shapes.add_picture(str(p), E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]))
    c = el.get("crop")
    if isinstance(c, (list, tuple)) and len(c) == 4 and any(c):  # [왼, 위, 오른, 아래] 비율 - render.js elImage 와 같다
        l, t, r, b = (max(0.0, min(0.95, float(v or 0))) for v in c)
        pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = l, t, r, b
    try:  # 대체 텍스트(접근성) - cNvPr descr. 없으면 비운다(python-pptx 는 파일 이름을 넣는다)
        pic._element.nvPicPr.cNvPr.set("descr", str(el.get("alt") or "")[:500])
    except AttributeError:
        pass
    op = el.get("opacity")
    blip = pic._element.find(f".//{{{NS_A}}}blip")
    if op is not None and float(op) < 1 and blip is not None:
        etree.SubElement(blip, qn("a:alphaModFix")).set("amt", str(int(max(0.0, min(1.0, float(op))) * 100000)))
    tone = el.get("tone")  # 톤 - 흑백 a:grayscl · 흐리게 a:blur · 어둡게 a:lum(밝기 -50%) · 세피아 a:duotone 대신 lum+grayscl 근사 (render.js TONE)
    if tone and blip is not None:
        if tone == "gray":
            etree.SubElement(blip, qn("a:grayscl"))
        elif tone == "blur":  # PowerPoint 는 blip 의 a:blur 를 그리지 않는다 → 예술 효과 확장(a14:artisticBlur) - PowerPoint 2010+
            ns = "http://schemas.microsoft.com/office/drawing/2010/main"
            ext = etree.SubElement(etree.SubElement(blip, qn("a:extLst")), qn("a:ext"))
            ext.set("uri", "{BEBA8EAE-BF5A-486C-A8C5-ECC9F3942E4B}")
            props = etree.SubElement(ext, f"{{{ns}}}imgProps", nsmap={"a14": ns})
            layer = etree.SubElement(props, f"{{{ns}}}imgLayer"); layer.set(qn("r:embed"), blip.get(qn("r:embed")))
            etree.SubElement(etree.SubElement(layer, f"{{{ns}}}imgEffect"), f"{{{ns}}}artisticBlur").set("radius", "20")
        elif tone == "dim":
            etree.SubElement(blip, qn("a:lum")).set("bright", "-50000")
        elif tone == "sepia":
            etree.SubElement(blip, qn("a:grayscl"))
            dt = etree.SubElement(blip, qn("a:duotone"))
            rgb_el(dt, "#2B1D0E"); rgb_el(dt, "#F3E6CF")
    return pic


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
    hexv, a = stroke_rgb(el.get("color", "on-surface"))
    alpha_el(rgb_el(sf, hexv), a)  # #RRGGBBAA 면 a:alpha(0.22.23)
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
        hexv, a = stroke_rgb(col)
        alpha_el(rgb_el(sf, hexv), a)
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
    VA = {"top": "t", "middle": "ctr", "bottom": "b"}
    for i in range(nr):
        tbl.rows[i].height = E(g["rowH"][i])
        for j in range(nc):
            c = g["cells"][i][j]
            cell = tbl.cell(i, j)
            csize = float(c.get("size") or size)  # 표 객체는 셀마다 크기·세로 정렬·여백·기울임을 가질 수 있다(render.js elTable 과 같다)
            pt_, pr_, pb_, pl_ = pad_of({"pad": c["pad"]}) if c.get("pad") is not None else (0, 14, 0, 14)
            cell.margin_left, cell.margin_right = E(pl_), E(pr_)
            cell.margin_top, cell.margin_bottom = E(pt_), E(pb_)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            para_fmt(p, csize, 1.4, c["align"])
            for t, st in runs(c["text"], page):
                if t:
                    set_run(p.add_run(), t, csize, st.get("bold", c["bold"]),
                            color(st.get("color") or c["color"]), c["font"], italic=st.get("italic", bool(c.get("italic"))), underline=st.get("underline", False), st=st)
            end_para(p, csize)
            tcPr = cell._tc.get_or_add_tcPr()
            for ch in list(tcPr):
                tcPr.remove(ch)
            tcPr.set("anchor", VA.get(c.get("valign"), "ctr"))
            is_head = bool(c.get("head")) if "head" in c else i == 0 and (el.get("type") == "plan-table" or el.get("header", True))
            bd = c.get("bd") or {}  # 셀별 테두리(common.table_cell_styles) - 없으면 본문 행 아래 선만(render.js elTable 과 같다)
            for side, dflt in (("L", None), ("R", None), ("T", None), ("B", None if is_head else [g["rule"], 1])):
                v = bd.get(side) or dflt
                _cell_border(tcPr, side, v[0] if v else None, float(v[1]) if v else 1)
            if c["fill"]:
                sf = etree.SubElement(tcPr, qn("a:solidFill"))
                rgb_el(sf, color(c["fill"]))
            else:
                etree.SubElement(tcPr, qn("a:noFill"))
    shapes = [gf]
    if el.get("type") != "plan-table":  # 셀 병합 - 왼쪽 위 셀의 글만 남고 덮인 셀은 비운다(render.js elTable 과 같은 규칙). 표 객체는 격자의 merge(셀 span)
        span, skip = table_merges({"merge": g["merge"]} if g.get("merge") is not None else el, nr, nc)
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
                set_run(p.add_run(), tt, sz, st.get("bold", False), color(st.get("color")) if st.get("color") else base, "body", italic=st.get("italic", False), underline=st.get("underline", False), st=st)
        end_para(p, sz)
    return shp


CHART_TYPES = {"column": XL_CHART_TYPE.COLUMN_CLUSTERED, "stackedColumn": XL_CHART_TYPE.COLUMN_STACKED, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
               "line": XL_CHART_TYPE.LINE_MARKERS, "area": XL_CHART_TYPE.AREA, "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT,
               # 0.22.13 - 누적 가로 · 100% 누적(세로·가로) · 콤보(막대 + 선, 선 계열은 _combo 가 c:lineChart 로 옮긴다)
               "stackedBar": XL_CHART_TYPE.BAR_STACKED, "stackedColumn100": XL_CHART_TYPE.COLUMN_STACKED_100, "stackedBar100": XL_CHART_TYPE.BAR_STACKED_100, "combo": XL_CHART_TYPE.COLUMN_CLUSTERED}
CHART_STACKED = {"stackedColumn", "stackedBar", "stackedColumn100", "stackedBar100"}
CHART_PCT = {"stackedColumn100", "stackedBar100"}
CHART_PALETTE = ["primary", "#4C7A9E", "#E0A458", "#7BAE7F", "#B57BA6", "#8C8C8C", "#D97B66", "#5FA8A3"]  # render.js CHART_PALETTE 와 같다


def _chart_axis(mx, mn):
    import math
    hi, lo = max(mx, 0), min(mn, 0)
    span = max(hi - lo, 1e-9)
    raw = span / 5
    p = 10 ** math.floor(math.log10(raw))
    step = next((k * p for k in (1, 2, 5, 10) if span / (k * p) <= 5.5), 10 * p)
    return math.ceil(hi / step) * step, math.floor(lo / step) * step, step


def _combo_lines(el, series):
    """콤보에서 선으로 그릴 계열 번호(render.js comboLines 와 같은 규칙) - lineSeries = 이름 또는 0부터 번호(배열·하나), 기본 = 마지막 계열. 없거나 전부 선이면 마지막만."""
    if (el.get("chart") or "column") != "combo" or len(series) < 2:
        return set()
    raw = el.get("lineSeries")
    if raw is None or raw == "":
        return {len(series) - 1}
    raw = raw if isinstance(raw, list) else [raw]
    out = set()
    names = [nm for nm, _ in series]
    for v in raw:
        sv = str(v).strip()
        if sv in names:
            out.add(names.index(sv))
        elif sv.isdigit() and int(sv) < len(series):
            out.add(int(sv))
    return out if out and len(out) < len(series) else {len(series) - 1}


def _combo(chart, line_idx, secondary):
    """콤보 - 묶은 세로 막대로 만든 차트의 선 계열(c:ser)을 새 c:lineChart 로 옮긴다(데이터는 같은 내장 워크북). secondary 면 보조 축(오른챡 c:valAx, 숨긴 c:catAx)."""
    import copy
    pa = chart._chartSpace.chart.plotArea
    bar = pa.find(qn("c:barChart"))
    if bar is None:
        return
    sers = bar.findall(qn("c:ser"))
    ax_ids = [a.get("val") for a in bar.findall(qn("c:axId"))]
    line = etree.Element(qn("c:lineChart"))
    etree.SubElement(line, qn("c:grouping")).set("val", "standard")
    etree.SubElement(line, qn("c:varyColors")).set("val", "0")
    moved = 0
    for i, ser in enumerate(sers):
        if i not in line_idx:
            continue
        bar.remove(ser)
        for x in ser.findall(qn("c:invertIfNegative")):
            ser.remove(x)
        mk = etree.Element(qn("c:marker"))
        etree.SubElement(mk, qn("c:symbol")).set("val", "circle")
        etree.SubElement(mk, qn("c:size")).set("val", "6")
        cat = ser.find(qn("c:cat"))
        if cat is not None:
            cat.addprevious(mk)
        else:
            ser.append(mk)
        etree.SubElement(ser, qn("c:smooth")).set("val", "0")
        line.append(ser)
        moved += 1
    if not moved:
        return
    etree.SubElement(line, qn("c:marker")).set("val", "1")
    bar.addnext(line)
    if secondary:
        cat_ax, val_ax = pa.find(qn("c:catAx")), pa.find(qn("c:valAx"))
        c2, v2 = copy.deepcopy(cat_ax), copy.deepcopy(val_ax)
        cid, vid = "500100", "500200"
        c2.find(qn("c:axId")).set("val", cid)
        c2.find(qn("c:crossAx")).set("val", vid)
        c2.find(qn("c:delete")).set("val", "1")
        v2.find(qn("c:axId")).set("val", vid)
        v2.find(qn("c:crossAx")).set("val", cid)
        v2.find(qn("c:axPos")).set("val", "r")
        for g in v2.findall(qn("c:majorGridlines")) + v2.findall(qn("c:title")) + v2.findall(qn("c:numFmt")):
            v2.remove(g)
        cr = v2.find(qn("c:crosses"))
        if cr is not None:
            cr.set("val", "max")
        sc = v2.find(qn("c:scaling"))
        for ch in list(sc):
            if ch.tag != qn("c:orientation"):
                sc.remove(ch)
        val_ax.addnext(c2)
        c2.addnext(v2)
        ax_ids = [cid, vid]
    for a in ax_ids:
        etree.SubElement(line, qn("c:axId")).set("val", a)


def _axis_title(ax, text, size):
    ax.has_title = True
    tf = ax.axis_title.text_frame
    tf.text = str(text)
    r = tf.paragraphs[0].runs[0]
    r.font.size = Pt(size * 0.75 * 0.9)
    r.font.bold = False


def _num_fmt(tick_labels, fmt):
    if fmt:
        tick_labels.number_format = str(fmt)
        tick_labels.number_format_is_linked = False


def do_chart(slide, el, page):
    """chart - PowerPoint 차트(편집 가능). 색·범례·데이터 레이블·눈금은 render.js elChart 와 같은 규칙, 그림은 PowerPoint 가 그린다.
    종류: column stackedColumn bar line area pie doughnut + stackedBar stackedColumn100 stackedBar100 combo(막대 + 선 lineSeries, secondaryAxis 보조 축).
    축 제목 axisTitle(값)·catTitle(범주)·axisTitle2(보조), 숫자 형식 numFmt·numFmt2(Excel 식 - 눈금·값 표시), axisMax·axisMax2."""
    kind = el.get("chart") or "column"
    if kind not in CHART_TYPES:
        kind = "column"
    cats = [str(c if c is not None else "") for c in el.get("categories") or []]
    series = [(str(s.get("name") or f"계열 {i + 1}"), [(None if v in (None, "") else float(v)) for v in (s.get("values") or [])]) for i, s in enumerate(el.get("series") or []) if isinstance(s, dict)]
    n = max([len(cats)] + [len(v) for _, v in series] + [0])
    cats += [""] * (n - len(cats))
    series = [(nm, v + [None] * (n - len(v))) for nm, v in series]
    if not n or not series:
        print(f"  ! {el.get('id')}: 차트 데이터 없음")
        return None
    pie = kind in ("pie", "doughnut")
    stacked, pct = kind in CHART_STACKED, kind in CHART_PCT
    lines = _combo_lines(el, series)
    sec = bool(lines) and bool(el.get("secondaryAxis"))
    cd = CategoryChartData()
    cd.categories = cats
    for nm, v in (series[:1] if pie else series):
        cd.add_series(nm, [0 if x is None else x for x in v] if pie else v)
    gf = slide.shapes.add_chart(CHART_TYPES.get(kind, XL_CHART_TYPE.COLUMN_CLUSTERED), E(el["x"]), E(el["y"]), E(el["w"]), E(el["h"]), cd)
    ch = gf.chart
    if lines:
        _combo(ch, lines, sec)
    size = float(el.get("size", 14))
    ch.font.size = Pt(size * 0.75)
    ch.font.name = fonts_of("body")[0]  # 본문 글꼴(글꼴 세트)
    legend = el.get("legend")
    if legend is None:
        legend = "bottom" if (len(series) > 1 or pie) else "none"
    ch.has_legend = legend != "none"
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.RIGHT if legend == "right" else XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(size * 0.75 * 0.9)
    ch.has_title = bool(el.get("title"))
    if ch.has_title:
        ch.chart_title.text_frame.text = str(el["title"])
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(size * 0.75 * 1.15)
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    fmt1, fmt2 = str(el.get("numFmt") or ""), str(el.get("numFmt2") or "")
    plots = list(ch.plots)
    for k, plot in enumerate(plots):
        plot.has_data_labels = bool(el.get("labels"))
        if plot.has_data_labels:
            plot.data_labels.font.size = Pt(size * 0.75 * 0.85)
            if pie:
                plot.data_labels.show_percentage = True
                plot.data_labels.show_value = False
                plot.data_labels.number_format = "0%"
                plot.data_labels.number_format_is_linked = False
            else:
                f = fmt2 if (k == 1 and sec) else fmt1
                if f:
                    plot.data_labels.number_format = f
                    plot.data_labels.number_format_is_linked = False
    plot = plots[0]
    if kind in ("column", "bar", "combo") or stacked:
        plot.gap_width = 80
        if stacked:
            plot.overlap = 100
    cols = el.get("colors") or []

    def rgb(i):
        return RGBColor.from_string((color(cols[i] if i < len(cols) and cols[i] else CHART_PALETTE[i % len(CHART_PALETTE)]) or "#888888")[1:])

    def style_line(s, i):
        s.format.line.color.rgb = rgb(i)
        s.format.line.width = Pt(2)
        s.smooth = False
        s.marker.format.fill.solid()
        s.marker.format.fill.fore_color.rgb = rgb(i)

    bar_idx = [i for i in range(len(series)) if i not in lines]
    for i, s in enumerate(plot.series):
        si = bar_idx[i] if lines else i  # 콤보는 막대 plot 에 선 계열이 빠져 있다 - 원래 번호로 색
        if pie:
            for j, pt in enumerate(s.points):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = rgb(j)
                pt.format.line.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        elif kind == "line":
            style_line(s, si)
        else:
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = rgb(si)
    if lines and len(plots) > 1:
        for s, si in zip(plots[1].series, sorted(lines)):
            style_line(s, si)
    if not pie:
        from pptx.chart.axis import ValueAxis
        v_axes = ch._chartSpace.chart.plotArea.findall(qn("c:valAx"))
        va, ca = ValueAxis(v_axes[0]), ch.category_axis  # 주 값 축 = 첫 valAx(python-pptx value_axis 는 축이 둘이면 둘째를 고른다 - XY 차트용)
        va.has_major_gridlines = el.get("grid") is not False
        va.tick_labels.font.size = Pt(size * 0.75 * 0.85)
        ca.tick_labels.font.size = Pt(size * 0.75 * 0.9)
        _num_fmt(va.tick_labels, fmt1)
        if not pct:  # 100% 누적은 PowerPoint 가 0~100% 로 맞춘다
            prim = bar_idx if sec else range(len(series))
            vals = [v for i in prim for v in series[i][1] if v is not None]
            if stacked:
                vals = [sum(max(0.0, series[i][1][k] or 0.0) for i in prim) for k in range(n)]
            mx, mn, step = _chart_axis(max(vals + [0]), min(vals + [0]))
            va.maximum_scale = float(el["axisMax"]) if el.get("axisMax") else mx
            va.minimum_scale = mn
            va.major_unit = step
        if va.has_major_gridlines:
            va.major_gridlines.format.line.color.rgb = RGBColor.from_string((color("outline-variant") or "#DDDDDD")[1:])
        if el.get("axisTitle"):
            _axis_title(va, el["axisTitle"], size)
        if el.get("catTitle"):
            _axis_title(ca, el["catTitle"], size)
        if sec:
            if len(v_axes) > 1:
                va2 = ValueAxis(v_axes[-1])
                va2.tick_labels.font.size = Pt(size * 0.75 * 0.85)
                _num_fmt(va2.tick_labels, fmt2)
                lv = [v for i in sorted(lines) for v in series[i][1] if v is not None]
                mx2, mn2, step2 = _chart_axis(max(lv + [0]), min(lv + [0]))
                va2.maximum_scale = float(el["axisMax2"]) if el.get("axisMax2") else mx2
                va2.minimum_scale = mn2
                va2.major_unit = step2
                if el.get("axisTitle2"):
                    _axis_title(va2, el["axisTitle2"], size)
    return gf


ICONS = {'check': {'ko': '확인 표시', 'layers': [['M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z', 'fill']]}, 'close': {'ko': '닫기 ×', 'layers': [['M19 6.4L17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z', 'fill']]}, 'plus': {'ko': '더하기', 'layers': [['M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6z', 'fill']]}, 'minus': {'ko': '빼기', 'layers': [['M19 13H5v-2h14z', 'fill']]}, 'arrowRight': {'ko': '오른쪽 화살', 'layers': [['M4 11v2h12l-5.5 5.5 1.4 1.4L20 12l-8.1-7.9-1.4 1.4L16 11z', 'fill']]}, 'arrowLeft': {'ko': '왼쪽 화살', 'layers': [['M20 11v2H8l5.5 5.5-1.4 1.4L4 12l8.1-7.9 1.4 1.4L8 11z', 'fill']]}, 'arrowUp': {'ko': '위 화살', 'layers': [['M13 20h-2V8l-5.5 5.5-1.4-1.4L12 4l7.9 8.1-1.4 1.4L13 8z', 'fill']]}, 'arrowDown': {'ko': '아래 화살', 'layers': [['M11 4h2v12l5.5-5.5 1.4 1.4L12 20l-7.9-8.1 1.4-1.4L11 16z', 'fill']]}, 'chevronRight': {'ko': '오른쪽 꺾쇠', 'layers': [['M8.6 4.6L7.2 6l6 6-6 6 1.4 1.4L16 12z', 'fill']]}, 'chevronLeft': {'ko': '왼쪽 꺾쇠', 'layers': [['M15.4 4.6L16.8 6l-6 6 6 6-1.4 1.4L8 12z', 'fill']]}, 'play': {'ko': '재생', 'layers': [['M7 4l13 8-13 8z', 'fill']]}, 'pause': {'ko': '일시정지', 'layers': [['M6 4h4v16H6zM14 4h4v16h-4z', 'fill']]}, 'stop': {'ko': '정지', 'layers': [['M5 5h14v14H5z', 'fill']]}, 'info': {'ko': '정보', 'layers': [['M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z', 'fill'], ['M11 10h2v7h-2zM11 7h2v2h-2z', 'on']]}, 'checkCircle': {'ko': '확인 원', 'layers': [['M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z', 'fill'], ['M10 15.6l-3.3-3.3 1.4-1.4 1.9 1.9 5.5-5.5 1.4 1.4z', 'on']]}, 'xCircle': {'ko': '취소 원', 'layers': [['M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z', 'fill'], ['M15.5 7.1L12 10.6 8.5 7.1 7.1 8.5l3.5 3.5-3.5 3.5 1.4 1.4 3.5-3.5 3.5 3.5 1.4-1.4-3.5-3.5 3.5-3.5z', 'on']]}, 'warning': {'ko': '경고', 'layers': [['M12 2L1 21h22z', 'fill'], ['M11 9h2v6h-2zM11 16.5h2v2h-2z', 'on']]}, 'question': {'ko': '물음표', 'layers': [['M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z', 'fill'], ['M11 16.5h2v2h-2zM12 6c-2.2 0-4 1.6-4 3.8h2c0-1 .9-1.8 2-1.8s2 .7 2 1.6c0 .8-.5 1.1-1.4 1.7-1 .7-1.6 1.3-1.6 2.9v.8h2v-.6c0-.9.3-1.2 1.2-1.8 1-.7 1.8-1.4 1.8-3 0-2.1-1.7-3.6-4-3.6z', 'on']]}, 'home': {'ko': '집', 'layers': [['M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3z', 'fill']]}, 'user': {'ko': '사람', 'layers': [['M16.5 8C16.5 10.48535 14.48535 12.5 12 12.5C9.51465 12.5 7.5 10.48535 7.5 8C7.5 5.51465 9.51465 3.5 12 3.5C14.48535 3.5 16.5 5.51465 16.5 8Z', 'fill'], ['M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z', 'fill']]}, 'users': {'ko': '사람들', 'layers': [['M12.8 8C12.8 10.09874 11.09874 11.8 9 11.8C6.901260000000001 11.8 5.2 10.09874 5.2 8C5.2 5.901260000000001 6.901260000000001 4.2 9 4.2C11.09874 4.2 12.8 5.901260000000001 12.8 8Z', 'fill'], ['M2 20c0-3.8 3-6.2 7-6.2s7 2.4 7 6.2z', 'fill'], ['M20 8.5C20 10.1569 18.6569 11.5 17 11.5C15.3431 11.5 14 10.1569 14 8.5C14 6.8431 15.3431 5.5 17 5.5C18.6569 5.5 20 6.8431 20 8.5Z', 'fill'], ['M15.5 13.2c3.7.2 6.5 2.5 6.5 6.8h-4.2c0-2.7-.8-4.9-2.3-6.8z', 'fill']]}, 'mail': {'ko': '메일', 'layers': [['M4 5L20 5C21.1046 5 22 5.8954 22 7L22 17C22 18.1046 21.1046 19 20 19L4 19C2.8954 19 2 18.1046 2 17L2 7C2 5.8954 2.8954 5 4 5Z', 'fill'], ['M4 7.5l8 5.5 8-5.5V9.8l-8 5.4-8-5.4z', 'on']]}, 'doc': {'ko': '문서', 'layers': [['M6 2h8l5 5v15H6z', 'fill'], ['M8 12h8v1.6H8zM8 15.5h8v1.6H8zM13 3.5V8h4.5z', 'on']]}, 'folder': {'ko': '폴더', 'layers': [['M2 5h7l2 2h11v13H2z', 'fill']]}, 'calendar': {'ko': '달력', 'layers': [['M5 4L19 4C20.1046 4 21 4.8954 21 6L21 19C21 20.1046 20.1046 21 19 21L5 21C3.8954 21 3 20.1046 3 19L3 6C3 4.8954 3.8954 4 5 4Z', 'fill'], ['M3 9h18v1.5H3z', 'on'], ['M7 2h2v4H7zM15 2h2v4h-2z', 'fill'], ['M7 12h3v3H7zM11.5 12h3v3h-3zM16 12h3v3h-3z', 'on']]}, 'clock': {'ko': '시계', 'layers': [['M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z', 'fill'], ['M11 6h2v6.6l4 2.4-1 1.7-5-3z', 'on']]}, 'pin': {'ko': '위치', 'layers': [['M12 2c-4 0-7 3-7 7 0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z', 'fill'], ['M14.6 9C14.6 10.43598 13.43598 11.6 12 11.6C10.56402 11.6 9.4 10.43598 9.4 9C9.4 7.56402 10.56402 6.4 12 6.4C13.43598 6.4 14.6 7.56402 14.6 9Z', 'on']]}, 'chat': {'ko': '말풍선', 'layers': [['M3 4h18v12H8l-5 4z', 'fill']]}, 'heart': {'ko': '하트', 'layers': [['M12 21s-8-5.6-8-11.2C4 7 6 5 8.5 5c1.6 0 2.8.8 3.5 2 .7-1.2 1.9-2 3.5-2C18 5 20 7 20 9.8 20 15.4 12 21 12 21z', 'fill']]}, 'bolt': {'ko': '번개', 'layers': [['M13 2L4 14h6l-1 8 9-12h-6z', 'fill']]}, 'search': {'ko': '찾기', 'layers': [['M17 10C17 13.8661 13.8661 17 10 17C6.1339 17 3 13.8661 3 10C3 6.1339 6.1339 3 10 3C13.8661 3 17 6.1339 17 10Z', 'fill'], ['M14.6 10C14.6 12.54058 12.54058 14.6 10 14.6C7.45942 14.6 5.4 12.54058 5.4 10C5.4 7.45942 7.45942 5.4 10 5.4C12.54058 5.4 14.6 7.45942 14.6 10Z', 'on'], ['M14.5 15.9l1.4-1.4L21 19.6 19.6 21z', 'fill']]}, 'star': {'ko': '별', 'layers': [['M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z', 'fill']]}, 'flag': {'ko': '깃발', 'layers': [['M5 2h2v20H5zM7 3h12l-3 4 3 4H7z', 'fill']]}, 'gear': {'ko': '톱니', 'layers': [['M12 2l1.8 2.6 3-.9 .9 3L20.3 8.5 19 11.3l1.3 2.8-2.6 1.8.3 3.1-3.1.3-1.5 2.7L12 20.5l-1.4 1.5-1.5-2.7-3.1-.3.3-3.1-2.6-1.8L5 11.3 3.7 8.5l2.6-1.8-.9-3 3 .9z', 'fill'], ['M15.2 11.5C15.2 13.26736 13.76736 14.7 12 14.7C10.23264 14.7 8.8 13.26736 8.8 11.5C8.8 9.73264 10.23264 8.3 12 8.3C13.76736 8.3 15.2 9.73264 15.2 11.5Z', 'on']]}}


def _svg_path_cmds(d):
    """SVG 경로(M L H V C Q Z, 절대·상대) → [(cmd, [(x, y)…])]. 아이콘 정의에 쓰는 범위만."""
    import re as _re
    toks = _re.findall(r"[MLHVCSQZmlhvcsqz]|-?\d*\.?\d+", d)
    out, i, cx, cy, sx, sy = [], 0, 0.0, 0.0, 0.0, 0.0
    cmd = None
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                out.append(("Z", []))
                cx, cy = sx, sy
            continue
        rel = cmd.islower()
        u = cmd.upper()
        def nxt():
            nonlocal i
            v = float(toks[i]); i += 1
            return v
        if u == "M":
            x, y = nxt(), nxt()
            if rel: x, y = cx + x, cy + y
            out.append(("M", [(x, y)])); cx, cy, sx, sy = x, y, x, y
            cmd = "l" if rel else "L"  # 잇따른 좌표는 L
        elif u == "L":
            x, y = nxt(), nxt()
            if rel: x, y = cx + x, cy + y
            out.append(("L", [(x, y)])); cx, cy = x, y
        elif u == "H":
            x = nxt(); x = cx + x if rel else x
            out.append(("L", [(x, cy)])); cx = x
        elif u == "V":
            y = nxt(); y = cy + y if rel else y
            out.append(("L", [(cx, y)])); cy = y
        elif u == "C":
            p = [nxt() for _ in range(6)]
            if rel: p = [p[0] + cx, p[1] + cy, p[2] + cx, p[3] + cy, p[4] + cx, p[5] + cy]
            out.append(("C", [(p[0], p[1]), (p[2], p[3]), (p[4], p[5])])); cx, cy = p[4], p[5]
        elif u == "S":  # 매끄러운 C - 첫 제어점은 앞 C 의 둘째 제어점을 현재점 기준으로 뒤집은 것
            p = [nxt() for _ in range(4)]
            if rel: p = [p[0] + cx, p[1] + cy, p[2] + cx, p[3] + cy]
            prev = out[-1] if out and out[-1][0] == "C" else None
            c1 = (2 * cx - prev[1][1][0], 2 * cy - prev[1][1][1]) if prev else (cx, cy)
            out.append(("C", [c1, (p[0], p[1]), (p[2], p[3])])); cx, cy = p[2], p[3]
        elif u == "Q":
            p = [nxt() for _ in range(4)]
            if rel: p = [p[0] + cx, p[1] + cy, p[2] + cx, p[3] + cy]
            c1 = (cx + 2 / 3 * (p[0] - cx), cy + 2 / 3 * (p[1] - cy)); c2 = (p[2] + 2 / 3 * (p[0] - p[2]), p[3] + 2 / 3 * (p[1] - p[3]))
            out.append(("C", [c1, c2, (p[2], p[3])])); cx, cy = p[2], p[3]
        else:
            i += 1
    return out


def _freeform(slide, x, y, s, d, col, name):
    """24×24 경로를 s×s px 자리에 custGeom 자유형으로. 채움 col(#hex), 선 없음."""
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, E(x), E(y), E(s), E(s))
    strip_style(shp)
    sp = shp._element.spPr
    pg = sp.find(qn("a:prstGeom"))
    cg = etree.Element(qn("a:custGeom"))
    for tag in ("a:avLst", "a:gdLst", "a:ahLst", "a:cxnLst"):
        etree.SubElement(cg, qn(tag))
    r = etree.SubElement(cg, qn("a:rect")); r.set("l", "0"); r.set("t", "0"); r.set("r", "r"); r.set("b", "b")
    pl = etree.SubElement(cg, qn("a:pathLst"))
    path = etree.SubElement(pl, qn("a:path")); path.set("w", "24000"); path.set("h", "24000")
    U = 1000
    def pt(parent, p):
        e = etree.SubElement(parent, qn("a:pt")); e.set("x", str(int(round(p[0] * U)))); e.set("y", str(int(round(p[1] * U))))
    for cmd, pts in _svg_path_cmds(d):
        if cmd == "M":
            pt(etree.SubElement(path, qn("a:moveTo")), pts[0])
        elif cmd == "L":
            pt(etree.SubElement(path, qn("a:lnTo")), pts[0])
        elif cmd == "C":
            c = etree.SubElement(path, qn("a:cubicBezTo"))
            for p in pts:
                pt(c, p)
        elif cmd == "Z":
            etree.SubElement(path, qn("a:close"))
    sp.replace(pg, cg)
    shape_fill_line(shp, {"fill": col})
    ln = sp.find(qn("a:ln"))
    if ln is None:
        ln = etree.SubElement(sp, qn("a:ln"))
    for ch in list(ln):
        ln.remove(ch)
    etree.SubElement(ln, qn("a:noFill"))
    shp.name = name
    return shp


def do_icon(slide, el, page):
    """icon - 내장 아이콘을 custGeom 자유형으로(층마다 도형). 두 층 이상이면 묶음으로 묶는다."""
    ic = ICONS.get(el.get("icon")) or ICONS["check"]
    w, h = float(el["w"]), float(el["h"])
    s = min(w, h)
    x, y = float(el["x"]) + (w - s) / 2, float(el["y"]) + (h - s) / 2
    c1, c2 = color(el.get("fill") or "primary"), color(el.get("color") or "white")
    layers = ic["layers"]
    if len(layers) == 1:
        return _freeform(slide, x, y, s, layers[0][0], c1 if layers[0][1] != "on" else c2, f"{el.get('id')} icon")
    grp = slide.shapes.add_group_shape()
    host = _GroupHost(grp)
    for i, (d, tone) in enumerate(layers):
        _freeform(host, x, y, s, d, c2 if tone == "on" else c1, f"{el.get('id')} icon {i}")
    return grp


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
        if not h or c.get("type") in ("table", "plan-table", "table-obj", "group", "chart"):
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
                apply_shadow(shp, cc)
                n += 1
    if not n:
        grp._element.getparent().remove(grp._element)
        return None
    return grp


HANDLERS = {"rect": do_box, "ellipse": do_box, "pill": do_box, "text": do_box, "image": do_image,
            "line": do_line, "arrow": do_line, "curve": do_curve, "table": do_table, "plan-table": do_table, "table-obj": do_table,
            "code": do_code, "plan": do_plan, "bullets": do_bullets, "shape": do_shape, "group": do_group, "chart": do_chart, "icon": do_icon}


def slide_title(s):
    """슬라이드 제목 글(섹션 이름용) - role=title 요소, 없으면 글자가 가장 큰 글 요소의 첫 줄."""
    from common import plain
    els = [e for e in s.get("elements", []) if e.get("type") in ("text", "rect", "pill", "shape") and str(e.get("text") or "").strip()]
    e = next((e for e in els if e.get("role") == "title"), None) or (max(els, key=lambda e: float(e.get("size") or 0)) if els else None)
    return plain(str(e.get("text")).split("\n")[0]).strip() if e else ""


def apply_sections(prs, deck):
    """PowerPoint 구분(섹션, p14:sectionLst) - 슬라이드의 `section`(이름) 또는 장 표지(layout=chapter, 이름 = 제목)에서 새 구분이 시작된다.
    하나도 없으면 만들지 않는다. 첫 슬라이드가 시작이 아니면 덱 제목으로 첫 구분을 둔다."""
    import uuid
    starts = []
    for i, s in enumerate(deck["slides"]):
        name = s.get("section")
        if name is None and s.get("layout") == "chapter":
            name = slide_title(s) or f"{i + 1}"
        if name not in (None, False, ""):
            starts.append((i, str(name)))
    if not starts:
        return 0
    if starts[0][0] != 0:
        starts.insert(0, (0, str(deck.get("title") or "시작")))
    ids = [sid.id for sid in prs.slides._sldIdLst]
    pres = prs.part._element
    ext_lst = pres.find(qn("p:extLst"))
    if ext_lst is None:
        ext_lst = etree.SubElement(pres, qn("p:extLst"))
    ns = "http://schemas.microsoft.com/office/powerpoint/2010/main"
    ext = etree.SubElement(ext_lst, qn("p:ext"))
    ext.set("uri", "{521415D9-36F7-43E2-AB2F-B90AF26B5E84}")
    lst = etree.SubElement(ext, f"{{{ns}}}sectionLst", nsmap={"p14": ns})
    for k, (i, name) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(ids)
        sec = etree.SubElement(lst, f"{{{ns}}}section")
        sec.set("name", name[:255])
        sec.set("id", "{" + str(uuid.uuid4()).upper() + "}")
        sl = etree.SubElement(sec, f"{{{ns}}}sldIdLst")
        for sid in ids[i:end]:
            etree.SubElement(sl, f"{{{ns}}}sldId").set("id", str(sid))
    return len(starts)


def apply_doc_props(prs, deck):
    """문서 속성(core.xml) - 제목 = 덱 제목(없으면 작업 공간 제목), 작성자 = 작업 공간 author(없으면 brand.name), 만든/고친 시각 = 지금."""
    import datetime
    try:
        from common import read_config
        cfg = read_config() or {}
    except Exception:  # noqa: BLE001
        cfg = {}
    cp = prs.core_properties
    cp.title = str(deck.get("title") or cfg.get("title") or deck.get("id") or "")[:255]
    author = str(cfg.get("author") or (cfg.get("brand") or {}).get("name") or "")[:255]
    cp.author = author
    cp.last_modified_by = author or "nexa-slide"
    if cfg.get("title"):
        cp.subject = str(cfg["title"])[:255]
    cp.comments = "nexa-slide"
    now = datetime.datetime.now()
    cp.created = cp.modified = now
    cp.revision = 1


def export(deck, out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = E(1280), E(720)
    blank = prs.slide_layouts[6]
    counts = []
    links = []  # (도형, 요소) - 슬라이드가 다 만들어진 뒤 걸어야 뒤 슬라이드로도 갈 수 있다
    sid_index = {s.get("id"): i for i, s in enumerate(deck["slides"], 1)}
    _RUN_LINKS.clear()
    for n, s in enumerate(deck["slides"], 1):
        use_fonts(s.get("fontPreset") or deck.get("fontPreset"))  # 슬라이드 > 덱 > 작업 공간
        slide = prs.slides.add_slide(blank)
        _CUR["part"] = slide.part
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
                    apply_shadow(shp, el)
                    apply_effect(shp, el)
                    if el.get("link"):
                        links.append((shp, el))
                    shp.name = f"{el.get('id')} {el.get('type')}"
        if s.get("notes"):
            slide.notes_slide.notes_text_frame.text = s["notes"]
        if s.get("hidden"):  # 숨김 슬라이드(show=0) - 편집기 발표·인쇄도 건너뛴다
            slide._element.set("show", "0")
        counts.append(len(slide.shapes))
    for shp, el in links:
        apply_link(shp, el, prs.slides, sid_index)
    apply_run_links(prs, sid_index)
    apply_sections(prs, deck)
    apply_doc_props(prs, deck)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return counts


def selftest(out):
    """채우기 견본(단색 · #hexAA · 색+alpha · 그라데이션 각도/정지점/고른 간격 · 글상자)과 선·테두리 투명도(stroke·선 color 의 #RRGGBBAA → a:ln 안 a:alpha, 0.22.23) ·
    순서도 도형(prst flowChart*) 견본을 내보내 슬라이드 XML 을 점검한다(개발·설치 점검용)."""
    import zipfile
    deck = {"id": "selftest", "slides": [{"id": "s01", "elements": [
        {"id": "e01", "type": "pill", "x": 80, "y": 200, "w": 400, "h": 80, "text": "01", "color": "white", "size": 32,
         "fill": {"gradient": {"angle": 0, "stops": [[0, "#002F7B00"], [1, "#002F7B"]]}}},
        {"id": "e02", "type": "rect", "x": 80, "y": 320, "w": 400, "h": 80, "fill": "#002F7B80", "radius": "r-m"},
        {"id": "e03", "type": "ellipse", "x": 560, "y": 200, "w": 120, "h": 120, "fill": {"color": "primary", "alpha": 0.5}},
        {"id": "e04", "type": "rect", "x": 560, "y": 340, "w": 400, "h": 60, "fill": {"gradient": {"angle": 90, "stops": ["#DCE3F0", "#B4C4E2", "#7F98C9", "#3F62A2"]}}},
        {"id": "e05", "type": "text", "x": 80, "y": 440, "w": 400, "h": 60, "text": "글", "fill": {"gradient": {"angle": 45, "stops": [[0, "primary", 0.2], [1, "primary"]]}, "alpha": 0.9}},
        {"id": "e06", "type": "pill", "x": 560, "y": 440, "w": 200, "h": 40, "text": "단색", "fill": "primary", "color": "white"},
        {"id": "e07", "type": "rect", "x": 80, "y": 540, "w": 200, "h": 60, "stroke": "#002F7B80", "strokeWidth": 2},  # 반투명 테두리
        {"id": "e08", "type": "shape", "shape": "flowChartDocument", "x": 320, "y": 540, "w": 200, "h": 100, "text": "문서", "fill": "surface", "stroke": "primary"},  # 순서도 + 불투명 테두리(alpha 없음)
        {"id": "e09", "type": "line", "x1": 560, "y1": 560, "x2": 900, "y2": 560, "color": "#FF000040", "width": 2},  # 반투명 선
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

    def ln_of(s):  # 첫 a:ln 블록(없으면 빈 문자열) - 선 투명도는 채우기가 아니라 a:ln 안에 있어야 한다
        m = re.search(r"<a:ln[ >].*?</a:ln>", s, re.S)
        return m.group(0) if m else ""
    cxn = re.search(r"<p:cxnSp>.*?</p:cxnSp>", xml, re.S)
    checks = [
        ("도형 8개", len(sp) == 8),
        ("그라데이션 투명→진한", '<a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:srgbClr val="002F7B"><a:alpha val="0"/></a:srgbClr></a:gs>'
         '<a:gs pos="100000"><a:srgbClr val="002F7B"/></a:gs></a:gsLst><a:lin ang="0" scaled="0"/></a:gradFill>' in sp.get("e01", "")),
        ("gradFill 이 ln 앞", all("<a:gradFill" in sp[k] and sp[k].index("<a:gradFill") < sp[k].index("<a:ln") for k in ("e01", "e04", "e05") if k in sp)),
        ("#hexAA 투명도", '<a:solidFill><a:srgbClr val="002F7B"><a:alpha val="50200"/></a:srgbClr></a:solidFill>' in sp.get("e02", "")),
        ("토큰+alpha", f'<a:solidFill><a:srgbClr val="{prim}"><a:alpha val="50000"/></a:srgbClr></a:solidFill>' in sp.get("e03", "")),
        ("고른 간격·위→아래", re.findall(r'<a:gs pos="(\d+)">', sp.get("e04", "")) == ["0", "33330", "66670", "100000"] and '<a:lin ang="5400000" scaled="0"/>' in sp.get("e04", "")),
        ("정지점 불투명도 × 전체 alpha", f'<a:gs pos="0"><a:srgbClr val="{prim}"><a:alpha val="18000"/></a:srgbClr></a:gs><a:gs pos="100000"><a:srgbClr val="{prim}"><a:alpha val="90000"/>' in sp.get("e05", "")
         and '<a:lin ang="2700000" scaled="0"/>' in sp.get("e05", "")),
        ("단색 그대로", bool(solid.search(sp.get("e06", ""))) and "<a:alpha" not in sp.get("e06", "") and "<a:gradFill" not in sp.get("e06", "")),
        ("테두리 #hexAA → a:ln 안 a:alpha", '<a:solidFill><a:srgbClr val="002F7B"><a:alpha val="50200"/></a:srgbClr></a:solidFill>' in ln_of(sp.get("e07", "")) and 'w="19050"' in ln_of(sp.get("e07", ""))),
        ("순서도 prst + 불투명 테두리는 alpha 없음", '<a:prstGeom prst="flowChartDocument">' in sp.get("e08", "")
         and f'<a:solidFill><a:srgbClr val="{prim}"/></a:solidFill>' in ln_of(sp.get("e08", "")) and "<a:alpha" not in ln_of(sp.get("e08", ""))),
        ("선 color #hexAA → a:ln 안 a:alpha", cxn is not None and '<a:solidFill><a:srgbClr val="FF0000"><a:alpha val="25100"/></a:srgbClr></a:solidFill>' in ln_of(cxn.group(0))),
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
