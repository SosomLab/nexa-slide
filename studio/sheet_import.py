# -*- coding: utf-8 -*-
"""엑셀 .xlsx → 시트 문서(kind sheet, docs/sheets.md) - 값·수식·표시 형식·글꼴·색·채움·맞춤·테두리·병합·열 너비·행 높이·틀 고정·눈금선.

    python3 nexa.py sheet_import <파일.xlsx> [--id <id>] [--title "…"]     # → decks/<id>.json (id 를 비우면 짧은 해시)

표준 라이브러리(zipfile·ElementTree)만 쓴다. 공유 수식(shared formula)은 셀마다 상대 참조를 옮겨 풀고, 계산값은 v 에 캐시로 둔다.
그림·차트·피벗·조건부 서식은 아직 옮기지 않는다(결과의 warnings 에 적는다).
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
    f0 = fonts[0] if fonts is not None and len(fonts) else None
    base_font = {"name": f0.find(N + "name").get("val") if f0 is not None and f0.find(N + "name") is not None else None,
                 "size": float(f0.find(N + "sz").get("val")) if f0 is not None and f0.find(N + "sz") is not None else 11.0}
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
        cells, shared, arrays = {}, {}, 0
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
                    o["f"] = re.sub(r"_xl(?:fn|ws|pm)\.", "", o["f"])  # 새 함수 접두사(_xlfn.TEXTJOIN) - 화면·계산기는 맨 이름을 쓴다(내보낼 때 XlsxWriter 가 다시 붙인다)
                if f.get("t") == "array":
                    arrays += 1
            o = {kk: vv for kk, vv in o.items() if vv not in (None, "")}
            if not o:
                continue
            cells[c.get("r")] = o["v"] if list(o) == ["v"] else o
            maxr, maxc = max(maxr, r0 + 1), max(maxc, c0 + 1)
        tab = {"id": f"t{len(tabs) + 1:02d}", "name": sh.get("name") or f"Sheet{k + 1}", "cells": cells}
        sp = x.find(N + "sheetPr")
        if sp is not None and sp.get("codeName"):  # 매크로(VBA)가 시트를 부르는 이름
            tab["codeName"] = sp.get("codeName")
        if sh.get("state") in ("hidden", "veryHidden"):
            tab["hidden"] = True
        cols = {}
        for cc in x.iter(N + "col"):
            if cc.get("width"):
                w = round(float(cc.get("width")) * 7 + 5)
                for ci in range(int(cc.get("min")) - 1, min(int(cc.get("max")), MAX_COLS)):
                    cols[col_name(ci)] = w
        if cols:
            tab["cols"] = cols
        rows = {r.get("r"): round(float(r.get("ht")) / 0.75) for r in x.iter(N + "row") if r.get("ht") and r.get("customHeight") in ("1", "true")}
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
        if arrays:
            warnings.append(f"{tab['name']}: 배열 수식 {arrays}개는 일반 수식으로 옮겼다")
        if cut:
            warnings.append(f"{tab['name']}: {MAX_ROWS}행·{MAX_COLS}열을 넘는 칸은 옮기지 않았다")
        if list(x.iter(N + "conditionalFormatting")):
            warnings.append(f"{tab['name']}: 조건부 서식은 아직 옮기지 않는다")
        if any(r.get("Type", "").endswith("/drawing") for r in _rels_of(z, part)):
            warnings.append(f"{tab['name']}: 그림·도형·차트는 아직 옮기지 않는다")
        tabs.append(tab)
    return tabs, warnings, base_font


def _rels_of(z, part):
    p = part.rsplit("/", 1)
    rp = f"{p[0]}/_rels/{p[1]}.rels"
    return list(ET.fromstring(z.read(rp))) if rp in z.namelist() else []


def to_doc(i, title, src, asset_root=None):
    """xlsx·xlsm → (문서, warnings). asset_root(작업 공간 assetRoot)를 주면 매크로(VBA)를 assets/sheets/<id>/vbaProject.bin 으로 둔다."""
    import datetime as dt
    tabs, warnings, font = import_xlsx(src)
    if not tabs:
        raise ValueError("시트가 없다")
    doc = {"id": i, "title": title, "kind": "sheet", "version": "0.1", "updated": dt.datetime.now().isoformat(timespec="seconds"), "slides": [], "sheets": tabs,
           "source": Path(src).name}
    z = zipfile.ZipFile(src)
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
            warnings.append("매크로(VBA)를 옮겼다 - 엑셀로 내보내면 .xlsm(매크로 포함). 매크로 단추·양식 컨트롤은 옮기지 않았다")
    if font.get("name"):
        doc["font"] = {"name": font["name"], "size": font["size"]}
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
