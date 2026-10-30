# -*- coding: utf-8 -*-
"""엑셀 .xlsx → 시트 문서(kind sheet, docs/sheets.md) - 값·수식·표시 형식·글꼴·색·채움·맞춤·테두리·병합·열 너비·행 높이·틀 고정·눈금선.

    python3 nexa.py sheet_import <파일.xlsx> [--id <id>] [--title "…"]     # → decks/<id>.json (id 를 비우면 짧은 해시)

표준 라이브러리(zipfile·ElementTree)만 쓴다. 공유 수식(shared formula)은 셀마다 상대 참조를 옮겨 풀고, 계산값은 v 에 캐시로 둔다.
그림·도형은 작업 공간 assets/sheets/<id>/ 에 PNG 로 두고 탭 drawings 로 같은 자리에 놓는다 - Excel 이 있으면(Windows) 도형 묶음·글 상자까지
떠내고(xlsx_shapes.ps1), 없으면 파일 안의 그림(png·jpg·gif)만. 선·차트·피벗은 아직 옮기지 않는다(결과의 warnings 에 적는다).
매크로 통합 문서(.xlsm)면 VBA 프로젝트(xl/vbaProject.bin)를 작업 공간 assets/sheets/<id>/ 에 두고 문서 macros 에 적는다 -
내보내면 .xlsm 으로 매크로가 그대로 들어간다(통합 문서·시트 codeName 도 옮겨 매크로가 시트를 찾게). 매크로 단추·양식 컨트롤은 아직 옮기지 않는다.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheet_theme import THEME_ORDER, _tint  # noqa: E402

N = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
BUILTIN_FMT = {1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00", 9: "0%", 10: "0.00%", 11: "0.00E+00", 14: "yyyy-mm-dd", 15: "d-mmm-yy", 16: "d-mmm",
               17: "mmm-yy", 18: "h:mm AM/PM", 19: "h:mm:ss AM/PM", 20: "h:mm", 21: "h:mm:ss", 22: "yyyy-mm-dd hh:mm", 37: "#,##0 ;(#,##0)",
               38: "#,##0 ;[Red](#,##0)", 39: "#,##0.00;(#,##0.00)", 40: "#,##0.00;[Red](#,##0.00)", 45: "mm:ss", 46: "[h]:mm:ss", 47: "mmss.0", 48: "##0.0E+0", 49: "@"}
MAX_ROWS, MAX_COLS = 5000, 200
REF = re.compile(r"(?<![A-Za-z0-9_.$!])(\$?)([A-Z]{1,3})(\$?)(\d{1,7})(?![A-Za-z0-9_(])")


def col_px(width, mdw=7):
    """엑셀 열 너비(파일 값 - 글자 폭 단위, 여백 포함) → px. ECMA-376: trunc((256·w + trunc(128/mdw)) / 256 · mdw).
    mdw = 기본 글꼴의 숫자 최대 폭(px) - Calibri 11 = 7, 맑은 고딕 11 = 8(mdw_of)."""
    return int((256 * float(width) + int(128 / mdw)) / 256 * mdw)


# 기본 글꼴(표준 스타일) 크기별 숫자 최대 폭(px, 96 dpi)과 기본 행 높이(pt) - 엑셀(한국어 365)에서 표준 스타일 글꼴을 바꿔 가며 잰 값
# (기본 열 너비 px = DEF_COL_PX[숫자 폭]). 엑셀은 열 너비를 이 숫자 폭으로 px 로 바꾸고, 높이를 정하지 않은 행은 이 높이로 그린다
_MDW = {"calibri": {8: 6, 9: 6, 10: 7, 11: 7, 12: 8, 14: 10}, "맑은 고딕": {8: 6, 9: 7, 10: 7, 11: 8, 12: 9, 14: 10},
        "굴림": {8: 6, 9: 6, 10: 7, 11: 8, 12: 9, 14: 10}, "바탕": {8: 6, 9: 6, 10: 7, 11: 8, 12: 9, 14: 10},
        "arial": {8: 6, 9: 7, 10: 7, 11: 8, 12: 9, 14: 11}, "aptos narrow": {8: 6, 9: 6, 10: 7, 11: 7, 12: 8, 14: 10}}
_ROWPT = {"calibri": {8: 11.25, 9: 12, 10: 12.75, 11: 15, 12: 15.75, 14: 18.75}, "맑은 고딕": {8: 11.25, 9: 12, 10: 13.5, 11: 16.5, 12: 17.25, 14: 20.25},
          "굴림": {8: 10.5, 9: 11.25, 10: 12, 11: 13.5, 12: 14.25, 14: 18.75}, "바탕": {8: 10.5, 9: 11.25, 10: 12, 11: 13.5, 12: 14.25, 14: 18.75},
          "arial": {8: 11.25, 9: 12, 10: 12.75, 11: 14.25, 12: 15, 14: 18}, "aptos narrow": {8: 11.25, 9: 12, 10: 13.5, 11: 15, 12: 15.75, 14: 18.75}}
for _t in (_MDW, _ROWPT):
    _t.update({"malgun gothic": _t["맑은 고딕"], "gulim": _t["굴림"], "batang": _t["바탕"]})
DEF_COL_PX = {6: 56, 7: 64, 8: 72, 9: 80, 10: 88, 11: 96, 12: 104, 13: 120}  # 기본 열 너비(8.43 글자) px - xlsxwriter 와 같은 표


def mdw_of(name, size):
    t = _MDW.get(str(name or "").strip().lower())
    sz = round(float(size or 11))
    if t:
        return t.get(sz) or t[min(t, key=lambda k: abs(k - sz))]
    return max(5, min(13, round(sz * 0.66)))


def row_px_of(name, size):
    """높이를 정하지 않은 행의 px(엑셀 기본 행 높이)."""
    t = _ROWPT.get(str(name or "").strip().lower())
    sz = round(float(size or 11))
    pt = (t.get(sz) or t[min(t, key=lambda k: abs(k - sz))]) if t else sz * 1.36
    return round(pt / 0.75)


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def col_name(c):
    s = ""
    c += 1
    while c:
        c, m = divmod(c - 1, 26)
        s = chr(65 + m) + s
    return s


def split_ref(ref):
    m = re.fullmatch(r"([A-Z]{1,3})(\d+)", ref or "")
    return (int(m.group(2)) - 1, col_index(m.group(1))) if m else (None, None)


def shift_formula(f, dr, dc):
    """수식 안 상대 참조를 dr 행·dc 열 옮긴다($ 고정은 그대로). 따옴표 글은 건드리지 않는다 - 공유 수식 풀기용."""
    parts = re.split(r'("(?:[^"]|"")*")', f)

    def mv(m):
        c = col_index(m.group(2)) + (0 if m.group(1) else dc)
        r = int(m.group(4)) + (0 if m.group(3) else dr)
        return f"{m.group(1)}{col_name(max(c, 0))}{m.group(3)}{max(r, 1)}"
    return "".join(p if p.startswith('"') else REF.sub(mv, p) for p in parts)


def import_xlsx(src, title=None):
    """xlsx → (시트 문서 dict 의 sheets 목록, warnings)."""
    z = zipfile.ZipFile(src)
    names = z.namelist()
    if "xl/workbook.xml" not in names:
        raise ValueError("xl/workbook.xml 이 없다 - Excel 통합 문서가 아니다")
    th = z.read("xl/theme/theme1.xml").decode("utf-8") if "xl/theme/theme1.xml" in names else ""
    tc = dict(re.findall(r'<a:(dk1|lt1|dk2|lt2|accent\d|hlink)>.*?(?:val|lastClr)="([0-9A-Fa-f]{6})"', th, re.S))

    def color(e):
        if e is None:
            return None
        if e.get("rgb"):
            return "#" + e.get("rgb")[-6:].upper()
        if e.get("theme") is not None and int(e.get("theme")) < len(THEME_ORDER):
            h = tc.get(THEME_ORDER[int(e.get("theme"))], "000000")
            t = float(e.get("tint") or 0)
            return _tint(h, t) if t else "#" + h.upper()
        if e.get("indexed") is not None:
            return {"8": "#000000", "9": "#FFFFFF", "10": "#FF0000", "12": "#0000FF", "64": None}.get(e.get("indexed"))
        return None
    ss = []
    if "xl/sharedStrings.xml" in names:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(N + "si"):
            ss.append("".join(t.text or "" for t in si.iter(N + "t")))
    st = ET.fromstring(z.read("xl/styles.xml")) if "xl/styles.xml" in names else None
    fmts = {int(n.get("numFmtId")): n.get("formatCode") for n in (st.iter(N + "numFmt") if st is not None else [])}
    fonts = st.find(N + "fonts") if st is not None else None
    fills = st.find(N + "fills") if st is not None else None
    borders = st.find(N + "borders") if st is not None else None
    xfs = st.find(N + "cellXfs") if st is not None else None
    dxfs = list(st.find(N + "dxfs")) if st is not None and st.find(N + "dxfs") is not None else []  # 조건부 서식이 쓰는 서식
    f0 = fonts[0] if fonts is not None and len(fonts) else None
    base_font = {"name": f0.find(N + "name").get("val") if f0 is not None and f0.find(N + "name") is not None else None,
                 "size": float(f0.find(N + "sz").get("val")) if f0 is not None and f0.find(N + "sz") is not None else 11.0}
    # 열 너비를 재는 글꼴 - 표준 글꼴이 테마 글꼴(scheme minor·major)이면 테마의 한글 글꼴(Hang, 한국어 엑셀이 쓰는 것) 또는 라틴 글꼴
    wfont = base_font["name"]
    sch = f0.find(N + "scheme") if f0 is not None else None
    if sch is not None and sch.get("val") in ("minor", "major"):
        blk = re.search(rf"<a:{sch.get('val')}Font>(.*?)</a:{sch.get('val')}Font>", th, re.S)
        hang = re.search(r'<a:font script="Hang" typeface="([^"]+)"', blk.group(1)) if blk else None
        latin = re.search(r'<a:latin typeface="([^"]+)"', blk.group(1)) if blk else None
        wfont = (hang or latin).group(1) if (hang or latin) else wfont
    mdw = mdw_of(wfont, base_font["size"])
    base_font["mdw"], base_font["rowPx"] = mdw, row_px_of(wfont, base_font["size"])
    style_cache = {}

    def style(s):
        """셀 서식 번호 → 셀 키 dict(b·i·u·color·fill·align·valign·wrap·size·fmt·bd)."""
        if s in style_cache or xfs is None:
            return style_cache.get(s, {})
        x = xfs[int(s)] if int(s) < len(xfs) else None
        d = {}
        if x is None:
            style_cache[s] = d
            return d
        nid = int(x.get("numFmtId") or 0)
        fc = fmts.get(nid) or BUILTIN_FMT.get(nid)
        if fc and fc != "General":
            d["fmt"] = fc
        f = fonts[int(x.get("fontId") or 0)] if fonts is not None else None
        if f is not None:
            if f.find(N + "b") is not None and f.find(N + "b").get("val") not in ("0", "false"):
                d["b"] = True
            if f.find(N + "i") is not None and f.find(N + "i").get("val") not in ("0", "false"):
                d["i"] = True
            if f.find(N + "u") is not None:
                d["u"] = True
            if f.find(N + "strike") is not None and f.find(N + "strike").get("val") not in ("0", "false"):
                d["strike"] = True
            c = color(f.find(N + "color"))
            if c and c not in ("#000000",):
                d["color"] = c
            sz = f.find(N + "sz")
            if sz is not None and float(sz.get("val")) != base_font["size"]:
                d["size"] = float(sz.get("val"))
        pf = fills[int(x.get("fillId") or 0)].find(N + "patternFill") if fills is not None else None
        if pf is not None and pf.get("patternType") == "solid":
            c = color(pf.find(N + "fgColor"))
            if c:
                d["fill"] = c
        b = borders[int(x.get("borderId") or 0)] if borders is not None else None
        if b is not None:
            bd = {}
            for k, side in (("t", "top"), ("r", "right"), ("b", "bottom"), ("l", "left")):
                e = b.find(N + side)
                if e is not None and e.get("style"):
                    bd[k] = color(e.find(N + "color")) or "#000000"
            if bd:
                d["bd"] = next(iter(bd.values())) if len(bd) == 4 and len(set(bd.values())) == 1 else bd
        al = x.find(N + "alignment")
        if al is not None:
            if al.get("horizontal") in ("left", "center", "right"):
                d["align"] = al.get("horizontal")
            elif al.get("horizontal") == "centerContinuous":
                d["align"] = "center"
            if al.get("vertical") in ("top", "center", "bottom"):
                d["valign"] = {"center": "middle"}.get(al.get("vertical"), al.get("vertical"))
            if al.get("wrapText") in ("1", "true"):
                d["wrap"] = True
        style_cache[s] = d
        return d
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {}
    if "xl/_rels/workbook.xml.rels" in names:
        for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            t = r.get("Target") or ""
            rels[r.get("Id")] = t.lstrip("/") if t.startswith("/") else "xl/" + t
    tabs, warnings = [], []
    for k, sh in enumerate(wb.iter(N + "sheet")):
        part = rels.get(sh.get(R + "id"))
        if not part or part not in names:
            continue
        x = ET.fromstring(z.read(part))
        cells, shared, arrays, spills = {}, {}, 0, []
        maxr = maxc = 0
        cut = False
        for c in x.iter(N + "c"):
            r0, c0 = split_ref(c.get("r"))
            if r0 is None:
                continue
            if r0 >= MAX_ROWS or c0 >= MAX_COLS:
                cut = True
                continue
            t, v, f = c.get("t"), c.find(N + "v"), c.find(N + "f")
            val = v.text if v is not None else None
            o = dict(style(c.get("s") or "0"))
            if t == "s" and val is not None:
                o["v"] = ss[int(val)] if int(val) < len(ss) else ""
            elif t == "inlineStr":
                o["v"] = "".join(tt.text or "" for tt in c.iter(N + "t"))
            elif t == "b" and val is not None:
                o["v"] = val == "1"
            elif t == "e" and val is not None:
                o["v"] = val
            elif t == "str" and val is not None:
                o["v"] = val
            elif val is not None:
                try:
                    fv = float(val)
                    o["v"] = int(fv) if fv.is_integer() and abs(fv) < 1e15 else fv
                except ValueError:
                    o["v"] = val
            if f is not None:
                if f.get("t") == "shared" and f.get("si") is not None:
                    if f.text:  # 공유 수식의 원본 칸
                        shared[f.get("si")] = (f.text, r0, c0)
                        o["f"] = "=" + f.text
                    elif f.get("si") in shared:
                        txt, sr, sc = shared[f.get("si")]
                        o["f"] = "=" + shift_formula(txt, r0 - sr, c0 - sc)
                elif f.text:
                    o["f"] = "=" + f.text
                if o.get("f"):
                    o["f"] = re.sub(r"_xl(?:fn|ws|pm|eta)\.", "", o["f"])  # 새 함수 접두사(_xlfn.TEXTJOIN) - 화면·계산기는 맨 이름을 쓴다(내보낼 때 XlsxWriter 가 다시 붙인다)
                    o["f"] = o["f"].replace("[#This Row],", "@")  # 파일 형식 표1[[#This Row],[열]] → 화면 형식 표1[@[열]]
                    o["f"] = re.sub(r"ANCHORARRAY\(((?:'[^']+'|[^\W\d][\w.]*)!)?(\$?[A-Z]{1,3}\$?\d+)\)", r"\1\2#", o["f"])  # 넘친 범위 참조 - 화면에서 쓰는 H2#
                if f.get("t") == "array":
                    if c.get("cm") or ":" in str(f.get("ref") or ""):  # 동적 배열(넘침) · 여러 칸 배열 수식 - 넘친 칸은 아래에서 sp 로
                        o["da"] = True
                        spills.append((str(f.get("ref") or c.get("r")), c.get("r")))
                    else:
                        arrays += 1
            o = {kk: vv for kk, vv in o.items() if vv not in (None, "")}
            if not o:
                continue
            cells[c.get("r")] = o["v"] if list(o) == ["v"] else o
            maxr, maxc = max(maxr, r0 + 1), max(maxc, c0 + 1)
        for ref, anchor in spills:  # 넘친 칸 = 엑셀이 저장한 값 + 기준 칸(sp) - 계산기가 다시 채운다
            a, _, b = ref.partition(":")
            (r1, c1), (r2, c2) = split_ref(a), split_ref(b or a)
            for rr in range(r1, min(r2, MAX_ROWS - 1) + 1):
                for cc in range(c1, min(c2, MAX_COLS - 1) + 1):
                    key = f"{col_name(cc)}{rr + 1}"
                    if key != anchor and key in cells:
                        cells[key] = {**(cells[key] if isinstance(cells[key], dict) else {"v": cells[key]}), "sp": anchor}
        tab = {"id": f"t{len(tabs) + 1:02d}", "name": sh.get("name") or f"Sheet{k + 1}", "cells": cells}
        sp = x.find(N + "sheetPr")
        if sp is not None and sp.get("codeName"):  # 매크로(VBA)가 시트를 부르는 이름
            tab["codeName"] = sp.get("codeName")
        if sh.get("state") in ("hidden", "veryHidden"):
            tab["hidden"] = True
        cols = {}
        for cc in x.iter(N + "col"):
            if cc.get("width"):
                w = col_px(cc.get("width"), mdw)
                for ci in range(int(cc.get("min")) - 1, min(int(cc.get("max")), MAX_COLS)):
                    cols[col_name(ci)] = w
        if cols:
            tab["cols"] = cols
        rows = {r.get("r"): round(float(r.get("ht")) / 0.75) for r in x.iter(N + "row") if r.get("ht") and r.get("customHeight") in ("1", "true")}
        hr = [r.get("r") for r in x.iter(N + "row") if r.get("hidden") in ("1", "true")][:2000]
        if hr:
            tab["hiddenRows"] = hr
        hc = [col_name(ci) for cc in x.iter(N + "col") if cc.get("hidden") in ("1", "true") for ci in range(int(cc.get("min")) - 1, min(int(cc.get("max")), MAX_COLS))]
        if hc:
            tab["hiddenCols"] = hc
        if rows:
            tab["rows"] = rows
        merges = [m.get("ref") for m in x.iter(N + "mergeCell")]
        if merges:
            tab["merges"] = merges
        sv = x.find(N + "sheetViews")
        v0 = sv.find(N + "sheetView") if sv is not None else None
        if v0 is not None:
            if v0.get("showGridLines") in ("0", "false"):
                tab["grid"] = False
            pane = v0.find(N + "pane")
            if pane is not None and pane.get("state") in ("frozen", "frozenSplit") and pane.get("topLeftCell"):
                tab["freeze"] = pane.get("topLeftCell")
        dvs = []
        for dv in x.iter(N + "dataValidation"):
            f1 = dv.find(N + "formula1")
            if dv.get("type") == "list" and f1 is not None and f1.text:
                items = f1.text.strip('"').split(",") if f1.text.startswith('"') else None
                dvs.append({"range": dv.get("sqref"), **({"list": items} if items else {"source": f1.text})})
        if dvs:
            tab["validations"] = dvs
        tab["size"] = {"rows": max(maxr + 20, 50), "cols": max(maxc + 2, 12)}
        fp = x.find(N + "sheetFormatPr")  # 그림 자리 계산용 기본 열 너비·행 높이(px) - to_doc 이 쓰고 지운다
        tab["_defW"] = col_px(fp.get("defaultColWidth"), mdw) if fp is not None and fp.get("defaultColWidth") else DEF_COL_PX.get(mdw, 64)
        tab["_rowsAll"] = {r.get("r"): round(float(r.get("ht")) / 0.75) for r in x.iter(N + "row") if r.get("ht")}  # 사용자 지정이 아닌 행 높이도(그림 자리)
        tab["_defH"] = round(float(fp.get("defaultRowHeight")) / 0.75) if fp is not None and fp.get("defaultRowHeight") and fp.get("customHeight") in ("1", "true") else base_font["rowPx"]  # 정하지 않은 기본 높이는 엑셀이 글꼴로 정한다
        tab["_part"] = part
        if arrays:
            warnings.append(f"{tab['name']}: 배열 수식 {arrays}개는 일반 수식으로 옮겼다")
        if cut:
            warnings.append(f"{tab['name']}: {MAX_ROWS}행·{MAX_COLS}열을 넘는 칸은 옮기지 않았다")
        conds, skipped = [], 0
        for cf in x.iter(N + "conditionalFormatting"):
            for rule in cf.findall(N + "cfRule"):
                cd = cond_of(rule, cf.get("sqref"), dxfs, color)
                if cd:
                    conds.append(cd)
                else:
                    skipped += 1
        if conds:
            tab["conds"] = conds
        if skipped:
            warnings.append(f"{tab['name']}: 조건부 서식 {skipped}개(수식·아이콘·데이터 막대 등)는 옮기지 않았다")
        af = x.find(N + "autoFilter")  # 시트 자동 필터(엑셀 표의 필터는 표 파트에 따로 있다)
        if af is not None and af.get("ref"):
            flt, lost = filter_of(af, dxfs, color)
            ag = split_ref(flt["ref"].split(":")[0]), split_ref(flt["ref"].split(":")[-1])
            if flt.get("cols") and ag[0][0] is not None and ag[1][0] is not None:  # 범위 안(머리글 아래)의 숨긴 행 = 필터가 가린 행 - 엑셀 파일은 둘을 가르지 않는다
                inside = [r for r in tab.get("hiddenRows") or [] if ag[0][0] + 1 < int(r) <= ag[1][0] + 1]
                if inside:
                    flt["rows"] = inside
                    rest = [r for r in tab["hiddenRows"] if r not in inside]
                    if rest:
                        tab["hiddenRows"] = rest
                    else:
                        tab.pop("hiddenRows")
            tab["filter"] = flt
            if lost:
                warnings.append(f"{tab['name']}: 필터 조건 {lost}개(날짜 묶음·평균 위/아래 같은 동적 조건)는 옮기지 않았다 - 가린 행은 그대로")
        for rel in _rels_of(z, part):  # 메모(옛 형식 comments - 엑셀이 스레드 메모도 함께 남긴다) → 셀 note
            if not rel.get("Type", "").endswith("/comments"):
                continue
            cp = "xl/" + rel.get("Target").replace("../", "")
            if cp not in names:
                continue
            cx = ET.fromstring(z.read(cp))
            authors = [a.text or "" for a in cx.iter(N + "author")]
            for cm in cx.iter(N + "comment"):
                ref, txt = cm.get("ref"), "".join(t.text or "" for t in cm.iter(N + "t")).strip()
                au = authors[int(cm.get("authorId") or 0)] if authors and int(cm.get("authorId") or 0) < len(authors) else ""
                if au and txt.startswith(au + ":"):  # 엑셀이 앞에 붙이는 "작성자:" 줄
                    txt = txt[len(au) + 1:].strip()
                if ref and txt and split_ref(ref)[0] is not None:
                    c0 = cells.get(ref)
                    cells[ref] = {**(c0 if isinstance(c0, dict) else {} if c0 is None else {"v": c0}), "note": txt}
        tables = []  # 엑셀 표 - 이름·범위·열 이름(구조적 참조 표1[열] 계산)·머리글/요약 행·스타일
        for rel in _rels_of(z, part):
            if not rel.get("Type", "").endswith("/table"):
                continue
            tp = "xl/" + rel.get("Target").replace("../", "")
            if tp not in names:
                continue
            tx = ET.fromstring(z.read(tp))
            t = {"name": tx.get("displayName") or tx.get("name"), "ref": tx.get("ref"),
                 "cols": [c.get("name") for c in tx.iter(N + "tableColumn")]}
            if tx.get("headerRowCount") == "0":
                t["header"] = False
            if int(tx.get("totalsRowCount") or 0):
                t["totals"] = True
            si = tx.find(N + "tableStyleInfo")
            if si is not None and si.get("name"):
                t["style"] = si.get("name")
            if t["name"] and t["ref"]:
                tables.append(t)
        if tables:
            tab["tables"] = tables

        tabs.append(tab)
    return tabs, warnings, base_font


def _offset_px(tab, r, c):
    """탭 칸 (r, c) 의 왼쪽 위 px - 열 너비·행 높이(숨김은 0)."""
    from sheet_calc import col_name as cn
    cols, rows = tab.get("cols") or {}, {**(tab.get("_rowsAll") or {}), **(tab.get("rows") or {})}
    hc, hr = set(tab.get("hiddenCols") or []), set(tab.get("hiddenRows") or [])
    x = sum(0 if cn(k) in hc else cols.get(cn(k), tab["_defW"]) for k in range(c))
    y = sum(0 if str(k + 1) in hr else rows.get(str(k + 1), tab["_defH"]) for k in range(r))
    return x, y


def import_drawings(src, z, tabs, asset_root, i, warnings):
    """그림·도형 → assets/sheets/<id>/d<탭>-<n>.png + 탭 drawings[{type:image, src, at, dx, dy, w, h}]."""
    import shutil
    import tempfile
    dest_rel = f"assets/sheets/{i}"
    dest = asset_root / dest_rel
    shapes = []
    try:
        import sheet_theme
        tmp = Path(tempfile.mkdtemp(prefix="nexa-shapes-"))
        shapes = sheet_theme.export_shapes(Path(src), tmp, text=True)
    except Exception:  # noqa: BLE001 - Excel 없음·실패면 파일 안 그림으로
        shapes = []
    lines = 0
    if shapes:
        for s in shapes:
            ti = int(s.get("sheet") or 0) - 1
            if not (0 <= ti < len(tabs)):
                continue
            if not s.get("png"):
                lines += int(s.get("type") == 9)
                continue
            tab = tabs[ti]
            m = re.fullmatch(r"\$?([A-Z]{1,3})\$?(\d+)", str(s.get("cell") or "A1"))
            r0, c0 = (int(m.group(2)) - 1, col_index(m.group(1))) if m else (0, 0)
            x0, y0 = _offset_px(tab, r0, c0)
            n = len(tab.get("drawings") or []) + 1
            dest.mkdir(parents=True, exist_ok=True)
            name = f"d{ti + 1:02d}-{n:02d}.png"
            shutil.copy2(s["png"], dest / name)
            tab.setdefault("drawings", []).append({"type": "image", "src": f"{dest_rel}/{name}", "at": f"{col_name(c0)}{r0 + 1}",
                                                   "dx": max(0, round((float(s["left"]) - float(s.get("cellLeft", x0 * 0.75))) / 0.75)),
                                                   "dy": max(0, round((float(s["top"]) - float(s.get("cellTop", y0 * 0.75))) / 0.75)),
                                                   "w": round(float(s["width"]) / 0.75), "h": round(float(s["height"]) / 0.75)})
        if lines:
            warnings.append(f"선 {lines}개는 옮기지 않았다(그림·글 상자·도형 묶음은 그림으로 옮김)")
        return
    # Excel 이 없을 때 - drawing XML 의 그림(pic)만, 앵커 칸 + 오프셋(EMU → px)
    XD = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    moved = skipped = 0
    for ti, tab in enumerate(tabs):
        part = tab.get("_part")
        drw = next((("xl/" + r.get("Target").replace("../", "")) for r in _rels_of(z, part) if r.get("Type", "").endswith("/drawing")), None) if part else None
        if not drw or drw not in z.namelist():
            continue
        rels = {r.get("Id"): "xl/" + r.get("Target").replace("../", "") for r in _rels_of(z, drw)}
        for anc in ET.fromstring(z.read(drw)):
            pic = anc.find(XD + "pic")
            if pic is None:
                skipped += 1
                continue
            blip = pic.find(f".//{A}blip")
            media = rels.get(blip.get(R + "embed")) if blip is not None else None
            if not media or not media.lower().endswith((".png", ".jpg", ".jpeg", ".gif")) or media not in z.namelist():
                skipped += 1
                continue
            fr = anc.find(XD + "from")
            if fr is None:
                skipped += 1
                continue
            c0, r0 = int(fr.find(XD + "col").text), int(fr.find(XD + "row").text)
            dx, dy = int(fr.find(XD + "colOff").text) // 9525, int(fr.find(XD + "rowOff").text) // 9525
            ext = anc.find(XD + "ext") if anc.find(XD + "ext") is not None else pic.find(f"{XD}spPr/{A}xfrm/{A}ext")  # oneCellAnchor 의 ext · 그림 변형 크기
            to = anc.find(XD + "to")
            if to is None and ext is not None and ext.get("cx"):
                w, h = int(ext.get("cx")) // 9525, int(ext.get("cy")) // 9525
            elif to is not None:
                x1, y1 = _offset_px(tab, int(to.find(XD + "row").text), int(to.find(XD + "col").text))
                x0, y0 = _offset_px(tab, r0, c0)
                w = x1 + int(to.find(XD + "colOff").text) // 9525 - x0 - dx
                h = y1 + int(to.find(XD + "rowOff").text) // 9525 - y0 - dy
            else:
                skipped += 1
                continue
            dest.mkdir(parents=True, exist_ok=True)
            name = f"d{ti + 1:02d}-{len(tab.get('drawings') or []) + 1:02d}{Path(media).suffix.lower()}"
            (dest / name).write_bytes(z.read(media))
            tab.setdefault("drawings", []).append({"type": "image", "src": f"{dest_rel}/{name}", "at": f"{col_name(c0)}{r0 + 1}", "dx": dx, "dy": dy, "w": max(w, 1), "h": max(h, 1)})
            moved += 1
    if skipped:
        warnings.append(f"도형·글 상자·그 밖의 그림 {skipped}개는 옮기지 않았다(Excel 이 있는 PC 에서 가져오면 그림으로 옮긴다)")


CF_OPS = {"greaterThan": "gt", "greaterThanOrEqual": "ge", "lessThan": "lt", "lessThanOrEqual": "le", "equal": "eq", "notEqual": "ne", "between": "between"}


def cond_of(rule, sqref, dxfs, color):
    """cfRule → 시트 조건부 서식 {range, type, value, value2, style, colors} (모르는 종류면 None)."""
    t = rule.get("type")
    style = {}
    if rule.get("dxfId") is not None and int(rule.get("dxfId")) < len(dxfs):
        d = dxfs[int(rule.get("dxfId"))]
        f = d.find(N + "font")
        if f is not None:
            if f.find(N + "b") is not None:
                style["b"] = True
            c = color(f.find(N + "color"))
            if c:
                style["color"] = c
        pf = d.find(N + "fill/" + N + "patternFill")
        if pf is not None:
            c = color(pf.find(N + "bgColor")) or color(pf.find(N + "fgColor"))
            if c:
                style["fill"] = c
    fs = [(e.text or "").strip() for e in rule.findall(N + "formula")]

    def val(s):
        s = (s or "").strip()
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1].replace('""', '"')
        try:
            v = float(s)
            return int(v) if v.is_integer() else v
        except ValueError:
            return None
    cd = {"range": sqref}
    if t == "cellIs" and rule.get("operator") in CF_OPS and fs:
        cd.update(type=CF_OPS[rule.get("operator")], value=val(fs[0]))
        if cd["value"] is None:
            return None
        if cd["type"] == "between":
            cd["value2"] = val(fs[1]) if len(fs) > 1 else None
    elif t == "containsText" and rule.get("text") is not None:
        cd.update(type="text", value=rule.get("text"))
    elif t == "duplicateValues":
        cd.update(type="dup")
    elif t == "top10":
        cd.update(type="bottom" if rule.get("bottom") in ("1", "true") else "top", value=int(rule.get("rank") or 10))
    elif t == "colorScale":
        cs = rule.find(N + "colorScale")
        cols = [color(c) for c in cs.findall(N + "color")] if cs is not None else []
        if len(cols) < 2 or not all(cols):
            return None
        return {"range": sqref, "type": "scale", "colors": [cols[0], cols[-1]]}
    else:
        return None
    if style:
        cd["style"] = style
    return cd


_FOPS = {"equal": "eq", "notEqual": "ne", "greaterThan": "gt", "greaterThanOrEqual": "ge", "lessThan": "lt", "lessThanOrEqual": "le"}


def _fcond(op, v):
    """customFilter → {op, v}. 엑셀은 포함·시작·끝을 같음 + 와일드카드(*x*·x*·*x)로 적는다."""
    op = _FOPS.get(op or "equal", "eq")
    s = str(v if v is not None else "")
    core = s.strip("*")
    if core and not re.search(r"[*?]", core):
        if op == "eq" and s == f"*{core}*":
            return {"op": "contains", "v": core}
        if op == "ne" and s == f"*{core}*":
            return {"op": "notContains", "v": core}
        if op == "eq" and s == f"{core}*":
            return {"op": "begins", "v": core}
        if op == "eq" and s == f"*{core}":
            return {"op": "ends", "v": core}
    try:
        return {"op": op, "v": int(s) if re.fullmatch(r"-?\d+", s) else float(s)}
    except ValueError:
        return {"op": op, "v": s}


def filter_of(af, dxfs, color):
    """<autoFilter> → (탭 filter {ref, cols}, 옮기지 못한 조건 수). 조건 형식은 sheetx.js 필터와 같다."""
    flt, cols, lost = {"ref": af.get("ref").replace("$", "")}, {}, 0
    first = split_ref(flt["ref"].split(":")[0])
    for fc in af.findall(N + "filterColumn"):
        c = (first[1] or 0) + int(fc.get("colId") or 0)
        fs, cu, tp, cf = fc.find(N + "filters"), fc.find(N + "customFilters"), fc.find(N + "top10"), fc.find(N + "colorFilter")
        cr = None
        if fs is not None and fs.find(N + "dateGroupItem") is None:
            cr = {"vals": [e.get("val") or "" for e in fs.findall(N + "filter")] + ([""] if fs.get("blank") in ("1", "true") else [])}
        elif cu is not None:
            cond = [_fcond(e.get("operator"), e.get("val")) for e in cu.findall(N + "customFilter")][:2]
            cr = {"cond": cond, **({"or": True} if len(cond) > 1 and cu.get("and") not in ("1", "true") else {})}
        elif tp is not None and tp.get("val"):
            cr = {"top": int(float(tp.get("val"))), **({"bottom": True} if tp.get("top") in ("0", "false") else {}), **({"pct": True} if tp.get("percent") in ("1", "true") else {})}
        elif cf is not None and cf.get("dxfId") is not None and int(cf.get("dxfId")) < len(dxfs):
            d, font = dxfs[int(cf.get("dxfId"))], cf.get("cellColor") in ("0", "false")
            if font:
                f = d.find(N + "font")
                cr = {"font": (color(f.find(N + "color")) if f is not None else None) or ""}
            else:
                pf = d.find(N + "fill/" + N + "patternFill")
                cr = {"fill": ((color(pf.find(N + "fgColor")) or color(pf.find(N + "bgColor"))) if pf is not None else None) or ""}
        if cr:
            cols[col_name(c)] = cr
        else:
            lost += 1
    if cols:
        flt["cols"] = cols
    return flt, lost


def _rels_of(z, part):
    p = part.rsplit("/", 1)
    rp = f"{p[0]}/_rels/{p[1]}.rels"
    return list(ET.fromstring(z.read(rp))) if rp in z.namelist() else []


def import_names(z, doc, warnings):
    """이름 정의(엑셀 이름 관리자) → 문서 names(통합 문서 범위)·탭 names(시트 범위, localSheetId). 계산기가 =SUM(매출) 을 계산한다.
    엑셀 내부 이름(_xlnm.Print_Area 등)·숨은 이름·외부 통합 문서 참조([1]…)·깨진 참조(#REF!)는 뺀다."""
    wbx = ET.fromstring(z.read("xl/workbook.xml"))
    order = [s.get("name") for s in wbx.iter(N + "sheet")]
    tabs = {t.get("name"): t for t in doc["sheets"]}
    skipped = 0
    for d in wbx.iter(N + "definedName"):
        nm, ref = d.get("name") or "", (d.text or "").strip()
        if not nm or not ref or nm.lower().startswith(("_xlnm.", "_xlfn.", "_xlpm.")) or d.get("hidden") == "1":
            continue
        if "[" in ref.split("!")[0] or "#REF!" in ref:
            skipped += 1
            continue
        ref = re.sub(r"_xl(?:fn|ws|pm|eta)\.", "", ref)  # 이름에 담은 LAMBDA 의 _xlfn.·_xlpm. - 수식 칸과 같이 맨 이름으로
        loc = d.get("localSheetId")
        if loc is not None:
            tab = tabs.get(order[int(loc)]) if int(loc) < len(order) else None
            if tab is None:
                continue
            tab.setdefault("names", {})[nm] = ref
        else:
            doc.setdefault("names", {})[nm] = ref
    if skipped:
        warnings.append(f"이름 정의 {skipped}개는 다른 통합 문서를 가리키거나 깨져 있어 옮기지 않았다(그 이름을 쓰는 수식은 엑셀 값을 그대로 둔다)")


def to_doc(i, title, src, asset_root=None):
    """xlsx·xlsm → (문서, warnings). asset_root(작업 공간 assetRoot)를 주면 매크로(VBA)를 assets/sheets/<id>/vbaProject.bin 으로 둔다."""
    import datetime as dt
    tabs, warnings, font = import_xlsx(src)
    if not tabs:
        raise ValueError("시트가 없다")
    doc = {"id": i, "title": title, "kind": "sheet", "version": "0.1", "updated": dt.datetime.now().isoformat(timespec="seconds"), "slides": [], "sheets": tabs,
           "source": Path(src).name}
    z = zipfile.ZipFile(src)
    if asset_root is not None:
        try:
            import_drawings(src, z, tabs, Path(asset_root), i, warnings)
        except Exception as e:  # noqa: BLE001 - 그림은 덤 - 실패해도 값·수식은 가져온다
            warnings.append(f"그림·도형을 옮기지 못했다: {e}")
    import_names(z, doc, warnings)
    for t in tabs:
        for k in ("_defW", "_defH", "_part", "_rowsAll"):
            t.pop(k, None)
    if "xl/vbaProject.bin" in z.namelist():
        if asset_root is None:
            warnings.append("매크로(VBA)가 있지만 둘 곳(작업 공간)이 없어 옮기지 않았다")
        else:
            rel = f"assets/sheets/{i}/vbaProject.bin"
            (Path(asset_root) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(asset_root) / rel).write_bytes(z.read("xl/vbaProject.bin"))
            wbx = ET.fromstring(z.read("xl/workbook.xml"))
            pr = wbx.find(N + "workbookPr")
            doc["macros"] = {"vba": rel, "codeName": (pr.get("codeName") if pr is not None else None) or "ThisWorkbook"}
            try:  # 모듈 소스 - 화면 VBA 실행기(vba.js)·코드 창이 쓴다. 내보낼 때 바뀌었으면 vbaProject.bin 을 고쳐 쓴다(vba_project.py)
                import vba_project
                doc["macros"]["modules"] = vba_project.read_modules(z.read("xl/vbaProject.bin"))
                risky = vba_project.risks(doc["macros"]["modules"])
                if risky:
                    warnings.append(f"⛨ 엑셀에서 위험할 수 있는 매크로 {len(risky)}줄(이 편집기는 실행하지 않는다 - 내보낼 때 매크로를 뺄 수 있다): "
                                    + ", ".join(f"{r['module']} {r['line']}행 {r['word']}" for r in risky[:6]) + (" …" if len(risky) > 6 else ""))
            except Exception as e:  # noqa: BLE001 - 읽지 못하면 바이너리만 보관(엑셀에서는 그대로 돈다)
                warnings.append(f"VBA 모듈 소스를 읽지 못했다(바이너리는 보관): {e}")
            warnings.append("매크로(VBA)를 옮겼다 - 엑셀로 내보내면 .xlsm(매크로 포함). 매크로 단추·양식 컨트롤은 옮기지 않았다")
    if font.get("name"):
        doc["font"] = {"name": font["name"], "size": font["size"], **({"mdw": font["mdw"]} if font.get("mdw", 7) != 7 else {}),
                       **({"rowPx": font["rowPx"]} if font.get("rowPx", 20) != 20 else {})}  # mdw·rowPx - 열 너비 px 를 잰 숫자 폭·기본 행 높이(내보낼 때 같은 값으로)
    return doc, warnings


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="xlsx → 시트 문서(decks/<id>.json)")
    ap.add_argument("file")
    ap.add_argument("--id", default="")
    ap.add_argument("--title")
    a = ap.parse_args()
    import deck_admin
    from ledger import atomic_write
    i = (a.id or "").strip() or deck_admin.new_id()
    deck_admin.check_id(i)
    p = deck_admin.DECKS / f"{i}.json"
    if p.exists():
        sys.exit(f"이미 있는 덱: {i}")
    from common import ASSET_ROOT
    try:
        doc, warnings = to_doc(i, a.title or Path(a.file).stem, a.file, ASSET_ROOT)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        sys.exit(f"가져오지 못했다: {e}")
    deck_admin.DECKS.mkdir(parents=True, exist_ok=True)
    atomic_write(p, json.dumps(doc, ensure_ascii=False, indent=1))
    print(f"시트: {p} ({doc['title']}, 탭 {len(doc['sheets'])}개: " + ", ".join(t["name"] for t in doc["sheets"]) + ")")
    for w in warnings[:20]:
        print(f"  알림: {w}")


if __name__ == "__main__":
    main()
