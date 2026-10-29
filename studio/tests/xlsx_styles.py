# -*- coding: utf-8 -*-
"""엑셀 파일의 칸 서식을 파일에서 바로 풀어 읽는다(가져오기 코드와 따로) - xlsm_crosscheck.py 가 원본·저장본 서식을 견준다.

cell_styles(path) → {탭 이름: {A1: 서식 dict}}  - 기본값과 다른 속성만. 색은 #RRGGBB(테마 색·밝기를 엑셀 방식(HSL)으로 풀어서).
"""
import colorsys
import re
import zipfile
import xml.etree.ElementTree as ET

N = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
THEME = ["lt1", "dk1", "lt2", "dk2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"]
INDEXED = {8: "000000", 9: "FFFFFF", 10: "FF0000", 11: "00FF00", 12: "0000FF", 13: "FFFF00", 14: "FF00FF", 15: "00FFFF", 64: None, 65: None}
BUILTIN_FMT = {0: "General", 1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00", 9: "0%", 10: "0.00%", 11: "0.00E+00", 14: "mm-dd-yy", 22: "m/d/yy h:mm", 49: "@"}


def tint(h, t):
    """엑셀 밝기(tint) - HSL 의 L 을 바꾼다(ECMA-376 18.8.19)."""
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = ll * (1 + t) if t < 0 else ll * (1 - t) + t
    r, g, b = colorsys.hls_to_rgb(hh, max(0, min(1, ll)), ss)
    return "%02X%02X%02X" % tuple(int(round(x * 255)) for x in (r, g, b))


def cell_styles(path):
    z = zipfile.ZipFile(path)
    th = z.read("xl/theme/theme1.xml").decode("utf-8") if "xl/theme/theme1.xml" in z.namelist() else ""
    tc = {}  # 칸 서식의 theme 번호는 [lt1, dk1, lt2, dk2, accent1…] 순서(테마 파일은 dk1 이 먼저지만 엑셀은 밝은 색을 0 번으로 쓴다)
    for k in THEME:
        m = re.search(rf"<a:{k}>.*?(?:val|lastClr)=\"([0-9A-Fa-f]{{6}})\"", th, re.S)
        if m:
            tc[k] = m.group(1).upper()

    def color(e):
        if e is None:
            return None
        if e.get("auto") in ("1", "true"):
            return "auto"
        h = None
        if e.get("rgb"):
            h = e.get("rgb")[-6:].upper()
        elif e.get("theme") is not None:
            i = int(e.get("theme"))
            h = tc.get(THEME[i]) if i < len(THEME) else None
        elif e.get("indexed") is not None:
            h = INDEXED.get(int(e.get("indexed")), "idx" + e.get("indexed"))
        if h and e.get("tint") and float(e.get("tint")) and not h.startswith("idx"):
            h = tint(h, float(e.get("tint")))
        return h
    st = ET.fromstring(z.read("xl/styles.xml"))
    fmts = dict(BUILTIN_FMT)
    fmts.update({int(n.get("numFmtId")): n.get("formatCode") for n in st.iter(N + "numFmt")})
    fonts = list(st.find(N + "fonts") or [])
    fills = list(st.find(N + "fills") or [])
    borders = list(st.find(N + "borders") or [])
    xfs = list(st.find(N + "cellXfs") or [])

    def font(f):
        d = {}
        for k in ("b", "i", "strike"):
            e = f.find(N + k)
            if e is not None and e.get("val") not in ("0", "false"):
                d[k] = True
        u = f.find(N + "u")
        if u is not None and u.get("val") != "none":
            d["u"] = u.get("val") or "single"
        for k in ("name", "sz"):
            e = f.find(N + k)
            if e is not None:
                d[k] = float(e.get("val")) if k == "sz" else e.get("val")
        va = f.find(N + "vertAlign")
        if va is not None and va.get("val") != "baseline":
            d["vertAlign"] = va.get("val")
        c = color(f.find(N + "color"))
        if c and c not in ("auto", "000000"):
            d["color"] = c
        return d

    def fill(f):
        p = f.find(N + "patternFill")
        if p is None or (p.get("patternType") or "none") in ("none", "gray125"):
            return {}
        return {"pattern": p.get("patternType"), "fg": color(p.find(N + "fgColor")), **({"bg": color(p.find(N + "bgColor"))} if p.get("patternType") != "solid" else {})}

    def border(b):
        d = {}
        for side in ("left", "right", "top", "bottom", "diagonal"):
            e = b.find(N + side)
            if e is not None and e.get("style"):
                d[side] = (e.get("style"), color(e.find(N + "color")) or "auto")
        return d
    resolved = []
    for x in xfs:
        d = {}
        fid, flid, bid = int(x.get("fontId") or 0), int(x.get("fillId") or 0), int(x.get("borderId") or 0)
        if fid < len(fonts):
            d["font"] = font(fonts[fid])
        if flid < len(fills):
            fl = fill(fills[flid])
            if fl:
                d["fill"] = fl
        if bid < len(borders):
            bd = border(borders[bid])
            if bd:
                d["border"] = bd
        nf = fmts.get(int(x.get("numFmtId") or 0), "id" + str(x.get("numFmtId")))
        if nf != "General":
            d["fmt"] = nf
        al = x.find(N + "alignment")
        if al is not None:
            a = {k: v for k, v in al.attrib.items() if v not in ("0", "false", "general") and not (k == "vertical" and v == "bottom")}
            if a:
                d["align"] = a
        pr = x.find(N + "protection")
        if pr is not None and pr.get("locked") in ("0", "false"):
            d["unlocked"] = True
        resolved.append(d)
    base = resolved[0].get("font", {}) if resolved else {}
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    tgt = {r.get("Id"): r.get("Target") for r in rels}
    out = {}
    for s in wb.iter(N + "sheet"):
        t = tgt.get(s.get(R + "id"), "")
        part = "xl/" + t.replace("/xl/", "").lstrip("/") if not t.startswith("xl/") else t
        if part not in z.namelist():
            continue
        x = ET.fromstring(z.read(part))
        m = {}
        for c in x.iter(N + "c"):
            si = int(c.get("s") or 0)
            if si >= len(resolved):
                continue
            d = dict(resolved[si])
            f = {k: v for k, v in (d.get("font") or {}).items() if base.get(k) != v}  # 표준 글꼴과 다른 것만
            if f:
                d["font"] = f
            else:
                d.pop("font", None)
            if d:
                m[c.get("r")] = d
        out[s.get("name")] = m
    return out
