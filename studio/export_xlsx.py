# -*- coding: utf-8 -*-
"""시트 문서(kind sheet) JSON → 엑셀 .xlsx (XlsxWriter - python-pptx 의존성으로 이미 설치돼 있다).

    python3 studio/export_xlsx.py <id>              # → out/<id>.xlsx (문서에 매크로(macros.vba)가 있으면 out/<id>.xlsm)
    python3 studio/export_xlsx.py <id> --out x.xlsx

형식은 docs/sheets.md. 수식(f)은 수식 그대로, 마지막 계산값(v)을 캐시로 넣어 엑셀이 열기 전에도 값이 보이게 한다.
열 너비·행 높이는 px 그대로(set_column_pixels·set_row_pixels).
테마(theme)가 있으면 셀 스타일(s)·팔레트 이름을 sheet_theme.resolve_cell 로 풀고(화면 sheet.js 와 같은 규칙), 테마 글꼴을 기본 글꼴로,
탭의 grid(눈금선)·print(인쇄)·drawings(그림)도 옮긴다.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, load_deck, safe_id  # noqa: E402
import sheet_theme  # noqa: E402

import xlsxwriter  # noqa: E402  (python-pptx 의존성)
from xlsxwriter.utility import xl_cell_to_rowcol  # noqa: E402

CELL = re.compile(r"^([A-Z]{1,3})([1-9][0-9]*)$")
ALIGN = {"left": "left", "center": "center", "right": "right"}
VALIGN = {"top": "top", "middle": "vcenter", "bottom": "bottom"}


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def sheet_name(name, used):
    """엑셀 탭 이름 규칙 - 31자, []:*?/\\ 금지, 중복 금지."""
    s = re.sub(r"[\[\]:*?/\\]", " ", str(name or "")).strip()[:31] or "Sheet"
    base, k = s, 2
    while s.lower() in used:
        tail = f" ({k})"
        s, k = base[:31 - len(tail)] + tail, k + 1
    used.add(s.lower())
    return s


def cell_format(c):
    """셀 객체(테마를 푼 것) → XlsxWriter 서식 속성(없으면 빈 dict)."""
    if not isinstance(c, dict):
        return {}
    f = {}
    if c.get("b"):
        f["bold"] = True
    if c.get("i"):
        f["italic"] = True
    if c.get("u"):
        f["underline"] = 1
    if c.get("color"):
        f["font_color"] = c["color"]
    if c.get("fill"):
        f["bg_color"], f["pattern"] = c["fill"], 1
    if c.get("align") in ALIGN:
        f["align"] = ALIGN[c["align"]]
    if c.get("valign") in VALIGN:
        f["valign"] = VALIGN[c["valign"]]
    if c.get("size"):
        f["font_size"] = float(c["size"])
    if c.get("wrap"):
        f["text_wrap"] = True
    if c.get("fmt"):
        f["num_format"] = str(c["fmt"])
    bd = c.get("bd")
    if isinstance(bd, str) and bd:  # 네 변 가는 선
        bd = {k: bd for k in ("t", "r", "b", "l")}
    if isinstance(bd, dict):
        for k, side in (("t", "top"), ("r", "right"), ("b", "bottom"), ("l", "left")):
            if bd.get(k):
                f[side], f[f"{side}_color"] = 1, bd[k]
    return f


def export(deck, out):
    if deck.get("kind") != "sheet":
        raise ValueError("시트 문서가 아니다(kind sheet) - 슬라이드 덱은 export_pptx.py")
    import copy
    import sheet_calc
    deck = copy.deepcopy(deck)
    sheet_calc.recalc(deck)  # 수식 계산값 캐시 - AI 세션이 f 만 쓴 칸도 뷰어·미리보기에서 0 이 아니라 값이 보이게(엑셀은 열 때 다시 계산)
    out.parent.mkdir(parents=True, exist_ok=True)
    theme = sheet_theme.load(deck["theme"]) if deck.get("theme") else None
    opts = {"strings_to_numbers": False, "strings_to_formulas": False, "strings_to_urls": False}
    if theme:
        opts["default_format_properties"] = {"font_name": theme.get("font") or "맑은 고딕", "font_size": float(theme.get("size") or 10)}
    vba = None
    if (deck.get("macros") or {}).get("vba"):  # 매크로 통합 문서 - VBA 프로젝트를 넣고 .xlsm 으로(엑셀은 확장자가 .xlsm 이어야 매크로를 연다)
        from common import ASSET_ROOT
        vp = ASSET_ROOT / deck["macros"]["vba"]
        if vp.is_file():
            vba, out = vp, out.with_suffix(".xlsm")
    wb = xlsxwriter.Workbook(str(out), opts)
    if vba:
        wb.add_vba_project(str(vba))
        wb.set_vba_name(deck["macros"].get("codeName") or "ThisWorkbook")
    wb.set_properties({"title": deck.get("title") or deck.get("id") or ""})
    cache, used = {}, set()

    def fmt(props):
        if not props:
            return None
        k = tuple(sorted(props.items()))
        if k not in cache:
            cache[k] = wb.add_format(props)
        return cache[k]

    for t in deck.get("sheets") or [{}]:
        ws = wb.add_worksheet(sheet_name(t.get("name"), used))
        if vba:
            ws.set_vba_name(t.get("codeName") or f"Sheet{len(used)}")  # 매크로가 시트를 부르는 이름(가져올 때 옮긴 codeName)
        if t.get("hidden"):
            ws.hide()
        for letters, w in (t.get("cols") or {}).items():
            if re.fullmatch(r"[A-Z]{1,3}", str(letters)) and isinstance(w, (int, float)):
                c = col_index(letters)
                ws.set_column_pixels(c, c, int(w))
        for r, h in (t.get("rows") or {}).items():
            if str(r).isdigit() and isinstance(h, (int, float)):
                ws.set_row_pixels(int(r) - 1, int(h))
        if t.get("freeze") and CELL.match(str(t["freeze"])):
            ws.freeze_panes(*xl_cell_to_rowcol(t["freeze"]))
        merged = {}  # 병합 왼쪽 위 셀 → 범위 (값·서식은 merge_range 로 한 번에)
        for m in t.get("merges") or []:
            if isinstance(m, str) and ":" in m:
                merged[m.split(":")[0]] = m
        for ref, c in (t.get("cells") or {}).items():
            mm = CELL.match(str(ref))
            if not mm:
                continue
            r, col = int(mm.group(2)) - 1, col_index(mm.group(1))
            d = sheet_theme.resolve_cell(theme, c)
            f = fmt(cell_format(d))
            v = d.get("v")
            if ref in merged:
                a, b = merged.pop(ref).split(":")
                (r1, c1), (r2, c2) = xl_cell_to_rowcol(a), xl_cell_to_rowcol(b)
                ws.merge_range(r1, c1, r2, c2, "", f)
            if d.get("f"):
                form = str(d["f"])
                ws.write_formula(r, col, form if form.startswith("=") else "=" + form, f, v if v is not None else 0)
            elif isinstance(v, bool):
                ws.write_boolean(r, col, v, f)
            elif isinstance(v, (int, float)):
                ws.write_number(r, col, v, f)
            elif v is None or v == "":
                ws.write_blank(r, col, None, f)
            else:
                ws.write_string(r, col, str(v), f)
            if d.get("note"):
                ws.write_comment(r, col, str(d["note"]))
        for dv in t.get("validations") or []:  # 목록 유효성(드롭다운) - 가져온 엑셀·화면에서 정한 것
            rng = str(dv.get("range") or "").split()
            opt = {"validate": "list", "source": dv["list"]} if dv.get("list") else {"validate": "list", "source": "=" + str(dv.get("source") or "").lstrip("=")} if dv.get("source") else None
            if opt and sum(len(str(x)) + 1 for x in opt["source"]) > 255 if isinstance(opt and opt["source"], list) else False:
                opt = None  # 엑셀 목록은 255자까지 - 넘으면 범위 참조로 둬야 한다(가져온 것은 보통 범위)
            for r in rng if opt else []:
                try:
                    ws.data_validation(r, opt)
                except Exception:  # noqa: BLE001 - 잘못된 범위는 건너뛴다
                    pass
        for c in t.get("hiddenCols") or []:  # 숨긴 열·행
            if re.fullmatch(r"[A-Z]{1,3}", str(c)):
                ci = col_index(c)
                ws.set_column(ci, ci, None, None, {"hidden": True})
        for r in t.get("hiddenRows") or []:
            if str(r).isdigit():
                ws.set_row(int(r) - 1, None, None, {"hidden": True})
        if t.get("grid") is False:
            ws.hide_gridlines(2)
        pr = t.get("print") or {}
        if pr.get("landscape"):
            ws.set_landscape()
        if pr.get("fitWidth"):
            ws.fit_to_pages(int(pr["fitWidth"]), 0)
        for dr in t.get("drawings") or []:  # 셀에 고정한 그림(px)
            p = sheet_theme.image_path(theme, dr.get("src")) if dr.get("type") == "image" else None
            if not p or not CELL.match(str(dr.get("at", ""))):
                continue
            from PIL import Image
            iw, ih = Image.open(p).size
            r0, c0 = xl_cell_to_rowcol(dr["at"])
            ws.insert_image(r0, c0, str(p), {"x_offset": max(0, int(dr.get("dx", 0))), "y_offset": max(0, int(dr.get("dy", 0))),
                                              "x_scale": float(dr.get("w") or iw) / iw, "y_scale": float(dr.get("h") or ih) / ih, "object_position": 1})
        for rng in merged.values():  # 값 없는 병합
            a, b = rng.split(":")
            (r1, c1), (r2, c2) = xl_cell_to_rowcol(a), xl_cell_to_rowcol(b)
            ws.merge_range(r1, c1, r2, c2, "", None)
    wb.close()
    return out


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="시트 문서 → xlsx")
    ap.add_argument("id")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not safe_id(a.id):
        sys.exit(f"쓸 수 없는 id: {a.id}")
    try:
        out = export(load_deck(a.id), Path(a.out) if a.out else OUT / f"{a.id}.xlsx")
    except (OSError, ValueError) as e:
        sys.exit(str(e))
    print(f"{out.suffix[1:]}: {out}")


if __name__ == "__main__":
    main()
