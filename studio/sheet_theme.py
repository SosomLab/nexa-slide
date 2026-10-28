# -*- coding: utf-8 -*-
"""시트 테마 - 색·글꼴(palette) + 이름 있는 셀 스타일(styles) + 페이지 틀(pages) + 로고. 형식은 docs/sheets.md 5절.

    python3 nexa.py sheet_theme list                                   # 엔진·작업 공간 테마
    python3 nexa.py sheet_theme show <이름>
    python3 nexa.py sheet_theme import <샘플.xlsx> [<샘플2.xlsx> …] --name <이름> [--label "…"]
        → assets/sheet-themes/<이름>/theme.json + 로고 그림. 여러 샘플이면 색은 모두에서, 로고·표지 글 크기는 도형이 있는 파일에서 뽑는다.
    python3 studio/sheet_theme.py build-basic                          # 엔진 기본 테마(studio/sheet_themes/basic) 다시 만들기

테마 위치: 엔진 studio/sheet_themes/<이름>/(공개 테마, 로고 없음) · 작업 공간 assets/sheet-themes/<이름>/(회사 테마, 같은 이름이면 이쪽).
셀 스타일 풀기(resolve_cell)는 화면 sheet.js 와 같은 규칙이다 - 스타일(s) 아래에 셀 키를 덮고, 색 값이 팔레트 이름이면 #RRGGBB 로 바꾼다.
"""
import argparse
import collections
import copy
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ASSET_ROOT, STUDIO  # noqa: E402

ENGINE_THEMES = STUDIO / "sheet_themes"
WS_THEMES = ASSET_ROOT / "assets" / "sheet-themes"
COLOR_KEYS = ("color", "fill")
PAGE_KINDS = ("cover", "history", "overview", "summary", "list")
DEFAULT_PALETTE = {"primary": "#2C3E50", "secondary": "#44607A", "line": "#BFC9D4", "band": "#EDF1F5",
                   "input": "#FFF2CC", "warn": "#C0392B", "muted": "#7F8C8D", "text": "#262626"}


# ---------------------------------------------------------------- 읽기·풀기
def theme_dir(name):
    """(폴더, 출처) - 작업 공간 테마가 엔진 테마보다 앞선다. 없으면 (None, None)."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", name or ""):
        return None, None
    for d, src in ((WS_THEMES / name, "workspace"), (ENGINE_THEMES / name, "engine")):
        if (d / "theme.json").is_file():
            return d, src
    return None, None


def load(name):
    d, src = theme_dir(name)
    if not d:
        return None
    t = json.loads((d / "theme.json").read_text(encoding="utf-8"))
    t["name"], t["source"] = name, src
    t["base"] = f"/assets/sheet-themes/{name}/" if src == "workspace" else f"/studio/sheet_themes/{name}/"  # 화면이 그림 src 앞에 붙이는 주소
    return t


def list_themes():
    names = set()
    for root in (ENGINE_THEMES, WS_THEMES):
        if root.is_dir():
            names |= {p.name for p in root.iterdir() if (p / "theme.json").is_file()}
    out = []
    for n in sorted(names):
        t = load(n)
        if t:
            out.append({"name": n, "label": t.get("label") or n, "source": t["source"], "font": t.get("font"),
                        "palette": t.get("palette", {}), "pages": [{"kind": p.get("kind"), "name": p.get("name")} for p in t.get("pages", [])]})
    return out


def color_of(theme, v):
    """팔레트 이름 → #RRGGBB(모르는 이름·이미 색이면 그대로)."""
    if isinstance(v, str) and not v.startswith("#"):
        return ((theme or {}).get("palette") or {}).get(v, DEFAULT_PALETTE.get(v, v))
    return v


def resolve_cell(theme, c):
    """셀(값 또는 객체) → 스타일을 푼 객체. 셀 키가 스타일을 이긴다. bd·color·fill 의 팔레트 이름은 색으로."""
    d = dict(c) if isinstance(c, dict) else {"v": c}
    if theme and d.get("s"):
        base = dict(((theme.get("styles") or {}).get(d["s"]) or {}))
        base.update({k: v for k, v in d.items() if k != "s"})
        d = base
    for k in COLOR_KEYS:
        if k in d:
            d[k] = color_of(theme, d[k])
    if isinstance(d.get("bd"), str):
        d["bd"] = color_of(theme, d["bd"])
    elif isinstance(d.get("bd"), dict):
        d["bd"] = {k: color_of(theme, v) for k, v in d["bd"].items() if v}
    return d


def image_path(theme, src):
    """그림 src → 디스크 경로(내보내기용). 테마 폴더 기준 · assets/… 작업 공간 기준 · @brand/logo."""
    if not src:
        return None
    if src == "@brand/logo":
        from common import BRAND
        p = ASSET_ROOT / BRAND.get("logo", "") if BRAND.get("logo") else None
    elif src.startswith("assets/"):
        p = ASSET_ROOT / src
    else:
        d, _ = theme_dir((theme or {}).get("name", ""))
        p = d / src if d else None
    return p if p and p.is_file() else None


def fill_vars(obj, vars_):
    """페이지 안 글의 {{이름}} 을 채운다(모르는 이름은 빈칸)."""
    if isinstance(obj, str):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(vars_.get(m.group(1), "")), obj)
    if isinstance(obj, list):
        return [fill_vars(x, vars_) for x in obj]
    if isinstance(obj, dict):
        return {k: fill_vars(v, vars_) for k, v in obj.items()}
    return obj


def new_tabs(theme, kinds=None, vars_=None, title=""):
    """테마 페이지 → 시트 탭 목록(id t01…). kinds 를 주면 그 페이지만(순서는 테마 순서)."""
    vs = {**(theme.get("vars") or {}), **{k: v for k, v in (vars_ or {}).items() if v not in (None, "")}}
    vs.setdefault("date", dt.date.today().isoformat())
    vs["title"] = title or vs.get("title", "")
    tabs = []
    for p in theme.get("pages", []):
        if kinds and p.get("kind") not in kinds:
            continue
        t = fill_vars(copy.deepcopy(p), vs)
        t["id"] = f"t{len(tabs) + 1:02d}"
        tabs.append(t)
    return tabs, vs


# ---------------------------------------------------------------- 페이지 틀(기본 테마·샘플링 공용)
def _row(cells, r, vals, style, start="A"):
    c0 = ord(start) - 65
    for k, v in enumerate(vals):
        ref = f"{chr(65 + c0 + k)}{r}"
        cells[ref] = {"s": style, **({"v": v} if v not in (None, "") else {})}


def build_pages(logos=None, sizes=None):
    """표준 페이지 5종 - logos {logo, small, partners[]}(테마 폴더 기준 그림 이름, 없으면 @brand/logo), sizes 표지 글 크기."""
    logos = logos or {}
    sz = {"project": 16, "title": 28, "date": 16, **(sizes or {})}
    logo = logos.get("logo") or "@brand/logo"
    foot = []  # 표지·이력 바닥 로고(왼쪽 작은 로고 · 오른쪽 협력사)
    if logos.get("small"):
        foot.append({"type": "image", "src": logos["small"]["src"], "at": "A{r}", "dx": 6, "dy": 6, "w": logos["small"]["w"], "h": logos["small"]["h"]})
    x = 0
    for p in logos.get("partners") or []:  # 표 오른쪽 끝 열({c})부터 오른쪽으로(엑셀 그림 오프셋은 양수만)
        foot.append({"type": "image", "src": p["src"], "at": "{c}{r}", "dx": x, "dy": 4, "w": p["w"], "h": p["h"]})
        x += p["w"] + 14

    def footer(r, c):
        return [{**f, "at": f["at"].replace("{r}", str(r)).replace("{c}", c)} for f in foot]
    lw = logos.get("logoW") or 220
    lh = logos.get("logoH") or 48
    # 표지 - 눈금선 없이 가운데 정렬 글 세 줄과 가로선, 아래 판·작성 줄과 바닥 로고
    cover = {"kind": "cover", "name": "표지", "grid": False, "print": {"landscape": True, "fitWidth": 1},
             "cols": {"A": 24, **{chr(c): 64 for c in range(66, 76)}, "L": 96}, "rows": {"14": 52, "12": 34, "18": 34},
             "merges": ["B12:K12", "B14:K14", "B18:K18", "B26:L26"],
             "cells": {"B12": {"v": "{{project}}", "s": "coverProject"}, "B14": {"v": "{{title}}", "s": "coverTitle"},
                       "B18": {"v": "{{date}}", "s": "coverDate"}, "B26": {"v": "{{version}}  {{date}}  {{author}}", "s": "note", "align": "right"},
                       **{f"{chr(c)}16": {"bd": {"b": "line"}} for c in range(66, 76)},
                       **{f"{chr(c)}27": {"bd": {"b": "line"}} for c in range(65, 77)}},
             "drawings": [{"type": "image", "src": logo, "at": "B2", "dx": 0, "dy": 6, "w": lw, "h": lh}] + footer(28, "J")}
    hist = {"kind": "history", "name": "이력", "grid": False, "print": {"landscape": True, "fitWidth": 1},
            "cols": {"A": 36, "B": 560, "C": 90, "D": 96, "E": 60}, "rows": {"1": 30}, "merges": ["A1:E1"], "freeze": "A3",
            "cells": {"A1": {"v": "개정 이력", "s": "header", "size": 14}, **{f"{c}1": {"s": "header"} for c in "BCDE"}}}
    _row(hist["cells"], 2, ["No", "변경 내역", "작성자", "개정일", "버전"], "subheader")
    _row(hist["cells"], 3, [1, "초안 작성", "{{author}}", "{{date}}", "{{version}}"], "cell")
    for r in range(4, 21):
        _row(hist["cells"], r, [""] * 5, "cell")
    for r in range(3, 21):
        for c in "ACDE":
            hist["cells"][f"{c}{r}"]["align"] = "center"
    hist["drawings"] = footer(22, "C")
    # 개요 - 제목·문서 정보(라벨/값 격자)·범례
    ov = {"kind": "overview", "name": "개요", "grid": False, "print": {"landscape": True, "fitWidth": 1},
          "cols": {"A": 20, "B": 130, "C": 170, "D": 170, "E": 130, "F": 170, "G": 170}, "rows": {"2": 36},
          "merges": ["C6:D6", "F6:G6", "C7:D7", "F7:G7", "C8:D8", "F8:G8", "D11:G11", "D12:G12", "D13:G13", "D14:G14"],
          "cells": {"B2": {"v": "『{{project}}』 {{title}}", "s": "title"}, "B4": {"v": "1. 문서 정보", "s": "section"},
                    "B10": {"v": "2. 범례 및 입력 규칙", "s": "section"}}}
    for r, (l1, v1, l2, v2) in enumerate([("프로젝트명", "{{project}}", "문서명", "{{title}}"), ("작성일", "{{date}}", "문서 버전", "{{version}}"),
                                          ("작성자", "{{author}}", "비고", "")], 6):
        ov["cells"].update({f"B{r}": {"v": l1, "s": "label"}, f"C{r}": {"v": v1, "s": "cell"}, f"D{r}": {"s": "cell"},
                            f"E{r}": {"v": l2, "s": "label"}, f"F{r}": {"v": v2, "s": "cell"}, f"G{r}": {"s": "cell"}})
    _row(ov["cells"], 11, ["구분", "표기", "의미 / 입력 규칙", "", "", ""], "header", "B")
    for r in (12, 13, 14):
        _row(ov["cells"], r, [""] * 6, "cell", "B")
        ov["cells"][f"B{r}"]["s"] = "key"
    # 요약 - 진행 현황 표(합계·진척률은 수식)
    sm = {"kind": "summary", "name": "요약", "grid": False, "print": {"landscape": True, "fitWidth": 1},
          "cols": {"A": 20, "B": 150, "C": 90, "D": 90, "E": 90, "F": 90, "G": 100}, "rows": {"2": 36},
          "cells": {"B2": {"v": "{{title}} 요약", "s": "title"}, "B4": {"v": "1. 진행 현황", "s": "section"}}}
    _row(sm["cells"], 5, ["구분", "전체", "완료", "진행중", "미착수", "진척률"], "header", "B")
    for r in range(6, 10):
        _row(sm["cells"], r, ["", "", "", "", "", ""], "cell", "B")
        sm["cells"][f"B{r}"]["s"] = "key"
        sm["cells"][f"G{r}"] = {"s": "cell", "f": f"=IF(C{r}=0,0,D{r}/C{r})", "fmt": "0.0%", "align": "center"}
    _row(sm["cells"], 10, ["합계"], "subheader", "B")
    for c in "CDEF":
        sm["cells"][f"{c}10"] = {"s": "subheader", "f": f"=SUM({c}6:{c}9)"}
    sm["cells"]["G10"] = {"s": "subheader", "f": "=IF(C10=0,0,D10/C10)", "fmt": "0.0%"}
    # 상세 목록 - 제목·부제·머리(고정)·빈 줄
    heads = ["No", "구분", "항목", "내용", "담당", "상태", "등록일", "완료일", "비고"]
    ls = {"kind": "list", "name": "상세목록", "print": {"landscape": True, "fitWidth": 1}, "freeze": "A5",
          "cols": {"A": 44, "B": 90, "C": 180, "D": 420, "E": 80, "F": 80, "G": 90, "H": 90, "I": 200}, "rows": {"1": 36, "4": 30},
          "merges": ["A1:I1", "A2:I2"],
          "cells": {"A1": {"v": "『{{project}}』 {{title}}", "s": "title"}, "A2": {"v": "작성일 : {{date}} │ 버전 : {{version}}", "s": "note"}}}
    _row(ls["cells"], 4, heads, "header")
    for r in range(5, 35):
        _row(ls["cells"], r, [r - 4] + [""] * 8, "cell")
        ls["cells"][f"A{r}"]["align"] = "center"
        for c in "EFGH":
            ls["cells"][f"{c}{r}"]["align"] = "center"
    return [cover, hist, ov, sm, ls]


def base_styles(sizes=None):
    sz = {"project": 16, "title": 28, "date": 16, **(sizes or {})}
    return {
        "title": {"size": 16, "b": True, "color": "primary"},
        "section": {"size": 12, "b": True, "color": "primary"},
        "header": {"b": True, "color": "#FFFFFF", "fill": "primary", "align": "center", "valign": "middle", "wrap": True, "bd": "line"},
        "subheader": {"b": True, "color": "primary", "fill": "band", "align": "center", "valign": "middle", "bd": "line"},
        "label": {"b": True, "color": "#FFFFFF", "fill": "secondary", "align": "center", "valign": "middle", "bd": "line"},
        "cell": {"valign": "middle", "bd": "line"},
        "key": {"b": True, "color": "primary", "align": "center", "valign": "middle", "bd": "line"},
        "input": {"fill": "input", "align": "center", "valign": "middle", "bd": "line"},
        "warn": {"b": True, "color": "warn"},
        "note": {"size": 9, "color": "muted"},
        "coverProject": {"size": sz["project"], "b": True, "color": "muted", "align": "center", "valign": "middle"},
        "coverTitle": {"size": sz["title"], "b": True, "color": "text", "align": "center", "valign": "middle"},
        "coverDate": {"size": sz["date"], "b": True, "color": "text", "align": "center", "valign": "middle"},
    }


def build_basic():
    """엔진 기본 테마 - 공개 색·글꼴만, 로고는 작업 공간 brand 로고(@brand/logo)."""
    t = {"label": "기본 산출물", "font": "맑은 고딕", "size": 10, "palette": dict(DEFAULT_PALETTE), "styles": base_styles(),
         "vars": {"project": "", "author": "", "version": "1.0"}, "pages": build_pages()}
    ENGINE_THEMES.joinpath("basic").mkdir(parents=True, exist_ok=True)
    (ENGINE_THEMES / "basic" / "theme.json").write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return ENGINE_THEMES / "basic" / "theme.json"


# ---------------------------------------------------------------- 샘플 엑셀에서 테마 뽑기
N = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
THEME_ORDER = ["lt1", "dk1", "lt2", "dk2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]


def _tint(hexc, t):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    f = (lambda c: c * (1 + t)) if t < 0 else (lambda c: c + (255 - c) * t)
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(f(c))))) for c in (r, g, b))


def _lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def scan_styles(src):
    """xlsx 의 값 있는 셀마다 (글꼴, 크기, 굵게, 글자색, 채움, 테두리색) - 색은 #RRGGBB(테마 색·밝기 풀어서)."""
    z = zipfile.ZipFile(src)
    names = z.namelist()
    th = z.read("xl/theme/theme1.xml").decode("utf-8") if "xl/theme/theme1.xml" in names else ""
    tc = dict(re.findall(r'<a:(dk1|lt1|dk2|lt2|accent\d|hlink)>.*?(?:val|lastClr)="([0-9A-Fa-f]{6})"', th, re.S))

    def col(e):
        if e is None:
            return None
        if e.get("rgb"):
            return "#" + e.get("rgb")[-6:].upper()
        if e.get("theme") is not None and int(e.get("theme")) < len(THEME_ORDER):
            h = tc.get(THEME_ORDER[int(e.get("theme"))], "000000")
            t = float(e.get("tint") or 0)
            return _tint(h, t) if t else "#" + h.upper()
        return None
    st = ET.fromstring(z.read("xl/styles.xml"))
    fonts, fills, borders, xfs = (st.find(N + k) for k in ("fonts", "fills", "borders", "cellXfs"))
    default_font = fonts[0].find(N + "name").get("val") if fonts[0].find(N + "name") is not None else None
    cache = {}

    def desc(s):
        if s in cache:
            return cache[s]
        x = xfs[int(s)]
        f = fonts[int(x.get("fontId") or 0)]
        pf = fills[int(x.get("fillId") or 0)].find(N + "patternFill")
        b = borders[int(x.get("borderId") or 0)]
        bcol = next((col(e.find(N + "color")) or "#000000" for k in ("bottom", "left", "top", "right") for e in [b.find(N + k)]
                     if e is not None and e.get("style")), None)
        cache[s] = (f.find(N + "name").get("val") if f.find(N + "name") is not None else None,
                    float(f.find(N + "sz").get("val")) if f.find(N + "sz") is not None else None,
                    f.find(N + "b") is not None and f.find(N + "b").get("val") not in ("0", "false"),
                    col(f.find(N + "color")),
                    col(pf.find(N + "fgColor")) if pf is not None and pf.get("patternType") == "solid" else None, bcol)
        return cache[s]
    out = []
    for n in names:
        if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n):
            for c in ET.fromstring(z.read(n)).iter(N + "c"):
                if c.find(N + "v") is not None or c.find(N + "is") is not None:
                    out.append(desc(c.get("s") or "0"))
    return out, default_font


def guess_palette(rows):
    """셀 스타일 통계 → 팔레트. 흰 글자 굵은 채움 = primary·secondary, 흔한 테두리색 = line, 밝은 채움(굵은 글) = band, 노란 채움 = input, 붉은 글 = warn."""
    pal = dict(DEFAULT_PALETTE)
    dark = collections.Counter(r[4] for r in rows if r[4] and r[3] == "#FFFFFF" and r[2])
    if not dark:
        dark = collections.Counter(r[4] for r in rows if r[4] and _lum(r[4]) < 0.45)
    if dark:
        ranked = [c for c, _ in dark.most_common()]
        pal["primary"] = ranked[0]
        pal["secondary"] = ranked[1] if len(ranked) > 1 else ranked[0]
    else:  # 진한 머리가 없는 샘플(옅은 머리) - 가장 흔한 밝은 머리 채움을 band 로, primary 는 기본값
        pass
    lines = collections.Counter(r[5] for r in rows if r[5] and r[5] not in ("#FFFFFF",))
    if lines:
        pal["line"] = lines.most_common(1)[0][0]
    band = collections.Counter(r[4] for r in rows if r[4] and 0.8 < _lum(r[4]) < 0.99 and not _yellowish(r[4]))
    if band:
        pal["band"] = band.most_common(1)[0][0]
    yel = collections.Counter(r[4] for r in rows if r[4] and _yellowish(r[4]))
    if yel:
        pal["input"] = yel.most_common(1)[0][0]
    red = collections.Counter(r[3] for r in rows if r[3] and _reddish(r[3]))
    if red:
        pal["warn"] = red.most_common(1)[0][0]
    big = sorted((r for r in rows if r[1] and r[3] and r[3] != "#FFFFFF"), key=lambda r: -r[1])
    if big and _lum(big[0][3]) < 0.4:
        pal["primary"] = pal["primary"] if dark else big[0][3]
    return pal


def _yellowish(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return r > 230 and g > 200 and b < 215 and r - b > 35


def _reddish(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return r > 150 and g < 90 and b < 90


def export_shapes(src, out):
    """Excel(Windows)로 도형을 PNG 로 떠낸다 - [{sheet, type, cell, left, top, width, height, text, size, bold, png}]. Excel 이 없으면 []."""
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if os.name != "nt" or not pwsh:
        return []
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "source.xlsx"  # 원본 경로(OneDrive·& ·괄호)를 Excel 이 못 열 때가 있어 단순한 이름의 사본을 연다
    try:
        shutil.copy2(src, tmp)
        subprocess.run([pwsh, "-NoProfile", "-File", str(STUDIO / "xlsx_shapes.ps1"), "-Xlsx", str(tmp.resolve()), "-OutDir", str(out.resolve())],
                       capture_output=True, timeout=300)
        return json.loads((out / "shapes.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def media_images(src, out):
    """Excel 이 없을 때 - xlsx 안 그림(png·jpg) 중 가로 40px 이상을 꺼낸다(도형 묶음 로고는 못 뽑는다)."""
    from PIL import Image
    z = zipfile.ZipFile(src)
    res = []
    for n in z.namelist():
        if n.startswith("xl/media/") and n.lower().endswith((".png", ".jpg", ".jpeg")):
            p = out / Path(n).name
            p.write_bytes(z.read(n))
            try:
                w, h = Image.open(p).size
            except OSError:
                continue
            if w >= 40:
                res.append({"png": str(p), "width": w * 0.75, "height": h * 0.75, "top": 0, "left": 0, "sheet": 1, "text": ""})
    return sorted(res, key=lambda x: -x["width"])


def import_xlsx(files, name, label=None, force=False):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", name):
        raise ValueError("테마 이름은 영문·숫자·-·_ 로 1~40자")
    dest = WS_THEMES / name
    if (dest / "theme.json").exists() and not force:
        raise ValueError(f"이미 있는 테마: {dest} (--force 로 덮어쓴다)")
    dest.mkdir(parents=True, exist_ok=True)
    rows, fonts = [], []
    shapes = []
    for f in files:
        r, df = scan_styles(f)
        rows += r
        fonts.append(df)
        tmp = dest / ".import" / Path(f).stem
        sh = export_shapes(f, tmp) or media_images(f, tmp)
        if sh and not shapes:
            shapes = sh
    pal = guess_palette(rows)
    font = next((f for f in fonts if f), None) or "맑은 고딕"
    sizes = collections.Counter(r[1] for r in rows if r[1])
    body = sizes.most_common(1)[0][0] if sizes else 10
    # 로고 - 표지(첫 시트)의 그림. 위쪽 큰 것 = 대표 로고, 바닥(가장 아래 줄) 왼쪽 = 작은 로고, 오른쪽 = 협력사
    pics = [s for s in shapes if s.get("png") and s.get("sheet") == min(x.get("sheet", 1) for x in shapes)]
    logos = {}
    if pics:
        bottom = max(s["top"] for s in pics)
        top = [s for s in pics if s["top"] < bottom - 40] or sorted(pics, key=lambda s: -s["width"])[:1]
        main = max(top, key=lambda s: s["width"] * s["height"])
        logos["logo"] = _copy_logo(main, dest, "logo.png")
        logos["logoW"], logos["logoH"] = logos["logo"]["w"], logos["logo"]["h"]
        foot = sorted((s for s in pics if s is not main and s["top"] >= bottom - 40), key=lambda s: s["left"])
        mid = max(s["left"] + s["width"] for s in pics) / 2
        left = [s for s in foot if s["left"] < mid]
        if left:
            logos["small"] = _copy_logo(left[0], dest, "logo-small.png")
        logos["partners"] = [_copy_logo(s, dest, f"partner-{k + 1}.png") for k, s in enumerate(s for s in foot if s["left"] >= mid)]
        logos["logo"] = logos["logo"]["src"]
    texts = sorted((s for s in shapes if s.get("text") and s.get("size")), key=lambda s: s["top"])
    cover_sizes, vars_ = {}, {"project": "", "author": "", "version": "1.0"}
    if texts:
        ti = max(range(len(texts)), key=lambda k: texts[k]["size"])
        cover_sizes["title"] = int(texts[ti]["size"])
        if ti > 0:
            cover_sizes["project"] = int(texts[ti - 1]["size"])
            vars_["project"] = texts[ti - 1]["text"].strip()
        if ti + 1 < len(texts):
            cover_sizes["date"] = int(texts[ti + 1]["size"])
    t = {"label": label or name, "font": font, "size": body, "palette": pal, "styles": base_styles(cover_sizes), "vars": vars_,
         "pages": build_pages(logos, cover_sizes),
         "source": {"files": [Path(f).name for f in files], "imported": dt.datetime.now().isoformat(timespec="seconds")}}
    (dest / "theme.json").write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    shutil.rmtree(dest / ".import", ignore_errors=True)
    return dest, t


def _copy_logo(s, dest, fname):
    """떠낸 그림을 테마 폴더로 - 화면 크기는 원래 크기(pt → px)."""
    shutil.copy2(s["png"], dest / fname)
    return {"src": fname, "w": round(s["width"] / 0.75), "h": round(s["height"] / 0.75)}


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="시트 테마 - 목록·보기·샘플 엑셀에서 만들기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("show"); s.add_argument("name")
    im = sub.add_parser("import"); im.add_argument("files", nargs="+"); im.add_argument("--name", required=True); im.add_argument("--label"); im.add_argument("--force", action="store_true")
    sub.add_parser("build-basic")
    a = ap.parse_args()
    if a.cmd == "list":
        for t in list_themes():
            print(f"{t['name']:16s} {t['source']:9s} {t['label']}  페이지: " + ", ".join(p["name"] for p in t["pages"]))
    elif a.cmd == "show":
        t = load(a.name)
        if not t:
            sys.exit(f"없는 테마: {a.name}")
        out = {k: t[k] for k in ("name", "label", "source", "font", "size", "palette", "vars") if k in t}
        out["styles"] = t.get("styles", {})
        out["pages"] = [{"kind": p.get("kind"), "name": p.get("name")} for p in t.get("pages", [])]
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif a.cmd == "import":
        try:
            dest, t = import_xlsx(a.files, a.name, a.label, a.force)
        except ValueError as e:
            sys.exit(str(e))
        print(f"테마: {dest}\n  글꼴 {t['font']} {t['size']}pt · 팔레트 " + " ".join(f"{k}={v}" for k, v in t["palette"].items()))
        print("  그림: " + ", ".join(sorted(p.name for p in dest.iterdir() if p.suffix == ".png")) + "\n다음: theme.json 을 다듬고 새 시트를 이 테마로 만든다")
    elif a.cmd == "build-basic":
        print(f"기본 테마: {build_basic()}")


if __name__ == "__main__":
    main()
