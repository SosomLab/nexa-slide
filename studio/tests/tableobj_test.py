# -*- coding: utf-8 -*-
"""표 객체(table-obj, 0.22.17) 시험 - 리졸버 우선순위(셀 > 행 > 열 > style), span 병합, 변환 왕복(table ↔ table-obj, Python ↔ render.js 는 check_parity),
PPTX 로 내보내 셀별 크기·세로 정렬·여백·기울임·채움·테두리·병합이 XML 에 들어가는지."""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "tableobj시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


OBJ = {"id": "t1", "type": "table-obj", "x": 60, "y": 60, "w": 600, "h": 200, "cols": [{"w": 2, "font": "mono", "align": "right"}, {"w": 1}, 1],
       "style": {"headFill": "s1", "size": 14, "font": "heading", "color": "on-surface-variant"},
       "rows": [{"header": True, "cells": ["항목", {"v": "값", "align": "center"}, "비고"]},
                ["매출", "10", {"v": "주", "italic": True, "size": 11}],
                {"h": 2, "fill": "surface-container", "bold": True, "valign": "bottom", "cells": [{"v": "합계", "color": "primary", "bd": {"T": ["primary", 2]}, "pad": [2, 4, 2, 4]}, {"v": "15", "span": [1, 2]}, ""]}]}
TBL = {"id": "t2", "type": "table", "x": 60, "y": 300, "w": 600, "h": 150, "rows": [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]], "colW": [2, 1, 1], "colFont": ["", "mono", ""],
       "align": ["", "right", ""], "rowH": [1, 1, 2], "cellFill": [[2, None, "s1"], [1, 2, "#FF0000"]], "merge": [[1, 0, 1, 2]], "headFill": "primary", "size": 15, "borders": [[2, "*", "T", "primary", 2]]}


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "tableobj시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    sys.path.insert(0, str(STUDIO))
    os.environ.update(ENV)
    from common import table_grid, table_to_obj, obj_to_table
    g = table_grid(OBJ)
    c = g["cells"]
    check("열 폭 2:1:1", [round(v) for v in g["colW"]] == [300, 150, 150], str(g["colW"]))
    check("행 높이 1:1:2", [round(v) for v in g["rowH"]] == [50, 50, 100], str(g["rowH"]))
    check("머리 행 - style.headFill·굵게·열 글꼴(mono) 적용·셀 align 우선", c[0][0]["fill"] == "s1" and c[0][0]["bold"] and c[0][0]["font"] == "mono" and c[0][1]["align"] == "center" and c[0][0]["align"] == "right" and c[0][0]["head"])
    check("열 기본 - 1열 mono·right, 2열 style 글꼴 heading, 색 style.color", c[1][0]["font"] == "mono" and c[1][0]["align"] == "right" and c[1][1]["font"] == "heading" and c[1][1]["color"] == "on-surface-variant" and not c[1][0]["head"])
    check("셀 서식 - italic·size", c[1][2].get("italic") is True and c[1][2].get("size") == 11)
    check("행 서식 - fill·bold·valign 이 셀에, 셀 color·bd·pad 우선", c[2][1]["fill"] == "surface-container" and c[2][1]["bold"] and c[2][1].get("valign") == "bottom" and c[2][0]["color"] == "primary" and c[2][0]["bd"] == {"T": ["primary", 2]} and c[2][0].get("pad") == [2, 4, 2, 4])
    check("span → merge", g["merge"] == [[2, 1, 1, 2]], str(g["merge"]))
    # 변환 왕복
    o = table_to_obj(TBL)
    check("table → obj: cols(w·font·align)·header·h·fill·span·style", o["type"] == "table-obj" and o["cols"] == [{"w": 2.0}, {"w": 1.0, "font": "mono", "align": "right"}, {"w": 1.0}] and o["rows"][0].get("header") is True and o["rows"][2]["h"] == 2.0
          and o["rows"][2]["cells"][0] == {"v": "4", "fill": "s1"} and o["rows"][1]["cells"][0] == {"v": "1", "span": [1, 2]} and o["rows"][1]["cells"][2] == {"v": "3", "fill": "#FF0000"} and o["style"] == {"headFill": "primary", "size": 15} and o["borders"] == TBL["borders"], json.dumps(o, ensure_ascii=False)[:300])
    back, dropped = obj_to_table(o)
    check("obj → table 왕복: rows·colW·colFont·align·rowH·merge·headFill·size 같음, 버린 것 없음", back["rows"] == TBL["rows"] and back["colW"] == [2.0, 1.0, 1.0] and back["colFont"] == ["", "mono", ""] and back["align"] == ["", "right", ""] and back["rowH"] == [1.0, 1.0, 2.0] and back["merge"] == [[1, 0, 1, 2]] and back["headFill"] == "primary" and back["size"] == 15 and not dropped, str((dropped, back.get("cellFill"))))
    check("왕복 뒤 셀 채움 집합 같음", sorted(map(str, back["cellFill"])) == sorted(map(str, [[2, 0, "s1"], [2, 1, "s1"], [2, 2, "s1"], [1, 2, "#FF0000"]])), str(back["cellFill"]))
    ga, gb = table_grid(TBL), table_grid(o)
    check("렌더 표·표 객체 격자 동일(변환 뒤) - 셀·열 폭·행 높이·선 색", all(json.dumps(ga[k], sort_keys=True) == json.dumps(gb[k], sort_keys=True) for k in ("cells", "colW", "rowH", "rule", "size")))
    b2, d2 = obj_to_table(OBJ)
    check("서식 있는 표 객체 → 렌더 표: 버린 서식 목록", set(d2) >= {"bold", "color", "italic", "size", "valign", "pad", "bd"} and b2["rows"][2] == ["합계", "15", ""] and b2["merge"] == [[2, 1, 1, 2]], str((d2, b2["rows"])))
    # PPTX
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "decks" / "to.json").write_text(json.dumps({"title": "표 객체", "slides": [{"id": "s1", "elements": [OBJ, TBL]}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(STUDIO / "export_pptx.py"), "to", "--out", "out/to.pptx"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("export_pptx 성공", r.returncode == 0 and (WS / "out" / "to.pptx").is_file(), (r.stderr or r.stdout)[-400:])
    if (WS / "out" / "to.pptx").is_file():
        with zipfile.ZipFile(WS / "out" / "to.pptx") as z:
            x = z.read("ppt/slides/slide1.xml").decode("utf-8")
        tbls = re.findall(r"<a:tbl>.*?</a:tbl>", x, re.S)
        check("표 2개(표 객체·렌더 표)", len(tbls) == 2, str(len(tbls)))
        if len(tbls) == 2:
            t1 = tbls[0]
            rows = re.findall(r"<a:tr .*?</a:tr>", t1, re.S)
            check("셀 크기 11px → sz 825 · 기울임 i=1 (1행 3열)", 'sz="825"' in rows[1] and re.search(r'sz="825" b="0" i="1"', rows[1]) is not None)
            check("2행 세로 아래 anchor=b · 여백 pad 2/4 (EMU 19050/38100) · 굵게", 'anchor="b"' in rows[2] and 'marL="38100"' in rows[2] and 'marT="19050"' in rows[2] and 'b="1"' in rows[2])
            check("2행 1열 위 2px primary 선 · 채움 surface-container", re.search(r'<a:lnT w="19050"[^>]*>\s*<a:solidFill>\s*<a:srgbClr val="A91F24"', rows[2]) is not None and rows[2].count("<a:solidFill>") >= 4)
            check("span 병합 gridSpan=2", 'gridSpan="2"' in rows[2] and 'hMerge="1"' in rows[2])
            check("머리 행 s1 채움·굵게", 'b="1"' in rows[0] and "3B5BA9" in rows[0])
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
