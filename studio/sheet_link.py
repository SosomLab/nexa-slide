# -*- coding: utf-8 -*-
"""시트 → 슬라이드 연결 - 시트 범위를 슬라이드의 표·차트 데이터로. 요소에는 link {deck, tab, range, as, header} 와 그 데이터가 함께 들어가므로
렌더·PPTX 규칙은 그대로이고, 편집기가 덱을 열 때(또는 [시트에서 새로 고침]) 원본이 바뀌었으면 데이터를 다시 받는다.

    python3 nexa.py sheet_link <시트 문서> <탭 이름|id> <범위> [--as table|chart] [--no-header]   # 표·차트 데이터 JSON(세션이 요소를 만들 때)
    API: GET /api/sheet-range?deck=&tab=&range=&as=table|chart&header=1

표: rows = 보이는 글(표시 형식 반영 - 1,234 · 15.0% · 2026-10-28). 차트: 첫 열 = 범주, 첫 줄 = 계열 이름(header), 나머지 = 계산값(숫자 아닌 칸은 null).
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sheet_calc  # noqa: E402


def display(raw):
    """셀 → 화면에 보이는 글(sheet.js display 와 같은 규칙의 하위 집합)."""
    o = raw if isinstance(raw, dict) else {"v": raw}
    v = o.get("v")
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        fmt = o.get("fmt")
        if fmt and fmt not in ("General", "@"):
            try:
                return sheet_calc.format_value(v, fmt)
            except Exception:  # noqa: BLE001 - 모르는 형식은 일반으로
                pass
        return sheet_calc.general(v)
    return str(v)


def find_tab(doc, tab):
    tabs = doc.get("sheets") or []
    return next((t for t in tabs if t.get("id") == tab), None) or next((t for t in tabs if str(t.get("name", "")).lower() == str(tab or "").lower()), None)


def range_data(doc, tab, rng, as_="table", header=True):
    """시트 범위 → {rows} 또는 {categories, series, numFmt?}. 수식은 계산해서."""
    if doc.get("kind") != "sheet":
        raise ValueError("시트 문서가 아니다")
    d = copy.deepcopy(doc)
    sheet_calc.recalc(d)
    t = find_tab(d, tab)
    if t is None:
        raise ValueError(f"없는 탭: {tab}")
    m = re.fullmatch(r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?", str(rng or "").strip().upper())
    if not m:
        raise ValueError(f"범위 형식 오류: {rng} (예 B2:E10)")
    c1, r1 = sheet_calc.col_index(m.group(1)), int(m.group(2)) - 1
    c2, r2 = (sheet_calc.col_index(m.group(3)), int(m.group(4)) - 1) if m.group(3) else (c1, r1)
    r1, r2, c1, c2 = min(r1, r2), max(r1, r2), min(c1, c2), max(c1, c2)
    if (r2 - r1 + 1) * (c2 - c1 + 1) > 5000:
        raise ValueError("범위가 너무 크다(5000칸까지)")
    cells = t.get("cells") or {}
    grid = [[cells.get(f"{sheet_calc.col_name(c)}{r + 1}") for c in range(c1, c2 + 1)] for r in range(r1, r2 + 1)]
    if as_ == "chart":
        head = grid[0] if header else None
        body = grid[1:] if header else grid
        val = lambda x: (x.get("v") if isinstance(x, dict) else x)  # noqa: E731
        series = []
        for j in range(1, len(grid[0])):
            name = display(head[j]) if head else f"계열 {j}"
            series.append({"name": name or f"계열 {j}", "values": [(lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else None)(val(row[j])) for row in body]})
        out = {"categories": [display(row[0]) for row in body], "series": series}
        fmts = {x.get("fmt") for row in body for x in row[1:] if isinstance(x, dict) and x.get("fmt")}
        if len(fmts) == 1:
            out["numFmt"] = fmts.pop()
        return out
    return {"rows": [[display(x) for x in row] for row in grid]}


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="시트 범위 → 슬라이드 표·차트 데이터")
    ap.add_argument("deck")
    ap.add_argument("tab")
    ap.add_argument("range")
    ap.add_argument("--as", dest="as_", choices=("table", "chart"), default="table")
    ap.add_argument("--no-header", action="store_true")
    a = ap.parse_args()
    from common import load_deck, safe_id
    if not safe_id(a.deck):
        sys.exit("잘못된 id")
    try:
        out = range_data(load_deck(a.deck), a.tab, a.range, a.as_, not a.no_header)
    except (OSError, ValueError) as e:
        sys.exit(str(e))
    print(json.dumps({**out, "link": {"deck": a.deck, "tab": a.tab, "range": a.range.upper(), "as": a.as_, "header": not a.no_header}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
