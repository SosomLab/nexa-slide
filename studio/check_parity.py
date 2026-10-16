# -*- coding: utf-8 -*-
"""render.js(JS) 와 common.py(Python) 가 같은 결과를 내는지 확인 (검증 도구, node 필요).

    python3 studio/check_parity.py [ch00 …]

비교 대상: 덱의 모든 code 요소 줄 하이라이트(codeLines) · 모든 요소의 인라인 강조(runs) · plan 강조 · 표 격자(tableGrid) · 글머리 행(bulletRows, 균등 간격 포함).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS, LANGS, STUDIO, bullet_rows, num_hang, code_lines, fill_spec, obj_to_table, resolve_tokens, plan_runs, runs, table_grid, table_to_obj  # noqa: E402

SAMPLES = [
    {"type": "code", "lang": "python", "text": "def f(x):\n    # 주석\n    return x * 2 + 'a'  # 끝\n"},
    {"type": "code", "lang": "sql", "text": "WITH t AS (SELECT a.id AS k FROM tab a JOIN tab2 b ON b.id = a.id)\nSELECT t.k, COUNT(*) cnt\nFROM t\nWHERE t.k > 10 AND x = 'it''s' -- c\n/* 여러\n 줄 */ AND y = :b1;"},
]
# 글머리 행 예제 - 기본 간격 · 균등 간격(spread, pad·두 줄 항목·하위 항목 포함) · 행 하나(spread 무시)
BULLET_SAMPLES = [
    {"type": "bullets", "h": 330, "items": ["가", {"text": "나", "sub": ["나-1", "나-2"]}, "다"]},
    {"type": "bullets", "h": 400, "size": 20, "subSize": 17, "lineHeight": 1.55, "spread": True, "pad": [10, 0, 6, 0],
     "items": ["가\n두 줄", {"text": "나", "sub": ["나-1"]}, "다", "라"]},
    {"type": "bullets", "h": 200, "spread": True, "gap": 20, "items": ["하나"]},
    # 번호 자동 감지 - 1. · 2) · (3) · a. · B) · ⑤ · 가. 는 번호 글머리, 2024.(연도)·1.5배(공백 없음)·autoNum:false 는 그대로
    {"type": "bullets", "h": 400, "items": ["1. 첫째", {"text": "2) 둘째", "sub": ["a. 하나", "(3) 둘", "B) 셋"]}, "⑤ 다섯째", "가. 여섯째", "2024. 매출", "1.5배 성장", "10. 열째"]},
    {"type": "bullets", "h": 200, "autoNum": False, "items": ["1. 그대로"], "spread": True},
    # 글머리 기호 감지 - * - + · • ■ ▶ ✓ 는 그 기호가 글머리(공백 없는 •도), "a-b" "*강조*" 는 아님
    {"type": "bullets", "h": 400, "items": ["* 별표", "- 붙임표", "+ 더하기", "· 가운뎃점", "•공백 없는 점", {"text": "■ 네모", "sub": ["▶ 화살", "✓ 확인"]}, "a-b 는 아님", "**굵게** 는 아님"]},
    # 글머리 종류(marker·subMarker) - 번호 매기기(순번, 하위는 상위마다 1부터)·기호·없음, 글 앞에 적은 번호가 우선
    {"type": "bullets", "h": 400, "marker": "1.", "subMarker": "a)", "items": ["첫째", {"text": "둘째", "sub": ["하나", "둘"]}, {"text": "셋째", "sub": ["다시 하나"]}, "7) 적은 번호 우선"]},
    {"type": "bullets", "h": 300, "marker": "①", "subMarker": "none", "items": [{"text": "원", "sub": ["글머리 없음"]}, "둘"]},
    {"type": "bullets", "h": 300, "marker": "가.", "subMarker": "▸", "items": [{"text": "한글", "sub": ["기호"]}, "둘", "셋"]},
    {"type": "bullets", "h": 300, "marker": "■", "items": ["네모", "네모"]},
]
# 표 글꼴 역할 예제 - font(본문 셀 기본) · colFont(열별, 빈 값은 font, "code" 는 mono, 모르는 값은 body) · 머리 행은 본문 · header 없는 표
TABLE_SAMPLES = [
    {"type": "table", "x": 0, "y": 0, "w": 600, "h": 120, "rows": [["a", "b", "c", "d"], ["1", "2", "3", "4"]], "font": "mono", "colFont": ["body", "", "code", "x"]},
    {"type": "table", "x": 0, "y": 0, "w": 600, "h": 120, "rows": [["a", "b"], ["1", "2"]], "font": "heading", "header": False},
    {"type": "table", "x": 0, "y": 0, "w": 600, "h": 120, "rows": [["a", "b"], ["1", "2"]], "colFont": None},
    # 셀별 채움·테두리·격자(0.22.12) - cellFill(행 전체·한 칸·잘못된 좌표) · borders(변 조합·색·두께, 열 전체) · gridLines
    {"type": "table", "x": 0, "y": 0, "w": 600, "h": 180, "rows": [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]], "cellFill": [[1, None, "s1"], [2, 2, "#FF0000"], ["x", 0, "s2"], [0, 9, "s3"]],
     "borders": [[2, "*", "T", "primary", 2], [None, 1, "lr"], [1, 1, "B"], [None, None, "Q"]]},
    {"type": "table", "x": 0, "y": 0, "w": 600, "h": 120, "rows": [["a", "b"], ["1", "2"]], "gridLines": True, "borders": [[1, 0, "B", "s1", 3]], "header": False},
    # 표 객체(table-obj, 0.22.17) - 셀 > 행 > 열 > style 우선순위 · span 병합 · 배열 행 · 머리 행 지정 · 덧씌우기 겸용
    {"type": "table-obj", "x": 0, "y": 0, "w": 600, "h": 200, "cols": [{"w": 2, "font": "mono", "align": "right"}, {"w": 1}, 1],
     "style": {"headFill": "s1", "size": 14, "font": "heading", "color": "on-surface-variant", "gridLines": True},
     "rows": [{"header": True, "h": 1, "cells": ["항목", {"v": "값", "align": "center"}, "비고"]},
              ["매출", "10", {"v": "주", "italic": True, "size": 11}],
              {"h": 2, "fill": "surface-container", "bold": True, "valign": "bottom", "cells": [{"v": "합계", "color": "primary", "bd": {"T": ["primary", 2]}, "pad": [2, 4, 2, 4]}, {"v": "15", "span": [1, 2]}, ""]}],
     "cellFill": [[1, 1, "s2"]], "borders": [[None, 0, "LR"]]},
    {"type": "table-obj", "x": 0, "y": 0, "w": 300, "h": 100, "rows": [["a", "b"], ["1", "2"]], "style": {"header": False}},
]
# 변환 왕복 예제 - table → table-obj → table (common.table_to_obj·obj_to_table ↔ render.tableToObj·objToTable)
CONV_SAMPLES = [
    {"type": "table", "id": "t1", "x": 0, "y": 0, "w": 600, "h": 180, "rows": [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]], "colW": [2, 1, 1], "colFont": ["", "mono", ""], "align": ["", "right", ""], "rowH": [1, 1, 2],
     "cellFill": [[2, None, "s1"], [1, 2, "#FF0000"]], "merge": [[1, 0, 1, 2]], "headFill": "primary", "size": 15, "borders": [[2, "*", "T", "primary", 2]]},
    {"type": "table", "id": "t2", "x": 0, "y": 0, "w": 300, "h": 100, "rows": [["a", "b"], ["1", "2"]], "header": False},
]
# 채우기(fill) 예제 - 토큰 · #hex · #hexAA(투명도) · 색+alpha · 그라데이션(각도·정지점 순서·고른 간격·토큰·잘못된 값)
FILL_SAMPLES = [
    "primary", "#002F7B", "#002F7B80", "#002F7B00", "#12345", "no-such-token", {"color": "primary", "alpha": 0.5}, {"color": "#002F7BFF", "alpha": "0.25"},
    {"gradient": {"angle": 0, "stops": [[0, "#002F7B00"], [1, "#002F7B"]]}},
    {"gradient": {"angle": -90, "stops": [[1, "primary"], [0.5, "#FFFFFF", 0.5], [0, "surface"]]}, "alpha": 0.8},
    {"gradient": {"angle": 450.5, "stops": ["#DCE3F0", "#B4C4E2", "#7F98C9", "#3F62A2"]}},
    {"gradient": {"angle": "x", "stops": [[0, "#002F7B"]]}}, {"gradient": {"stops": [[0, "#zz"], ["a", "primary", "b"], 3, "#002F7BGG"]}},
    {"gradient": {"stops": []}}, {"gradient": "no"}, [1, 2], 5, "", None,
]

JS = r"""
const R = require(process.argv[1]);
const inp = JSON.parse(require('fs').readFileSync(0, 'utf8'));
R.setTokens(inp.tokens); R.setLangs(inp.langs);
const out = {code: inp.code.map(e => R.codeLines(e).map(l => ({n: l.n, focus: l.focus, gap: l.gap, runs: l.runs}))),
  runs: inp.texts.map(t => R.runs(t, 3).map(([t2, st]) => [t2, Object.fromEntries(Object.entries(st).filter(([k, v]) => v))])),
  plan: inp.plans.map(p => R.planRuns(p)),
  grid: inp.tables.map(e => { const g = R.tableGrid(e); return {colW: g.colW.map(v => +v.toFixed(3)), rowH: g.rowH.map(v => +v.toFixed(3)), cells: g.cells, callouts: g.callouts.map(c => ({...c, x: +c.x.toFixed(3), y: +c.y.toFixed(3), h: +c.h.toFixed(3), cy: +c.cy.toFixed(3), tx: +c.tx.toFixed(3)}))}; }),
  bullets: inp.bullets.map(e => R.bulletRows(e).map(([t, lvl, after, num]) => [t, lvl, +(+after).toFixed(3), num ? [num.label, num.scheme || "", num.start, num.kind || "", R.numHang(num.label, lvl ? +e.subSize || 17 : +e.size || 20, lvl ? 20 : 28)] : null])),
  fills: inp.fills.map(f => R.fillSpec(f)),
  conv: inp.conv.map(e => { const o = R.tableToObj(e); const back = R.objToTable(o); return {obj: o, back: back.el, dropped: back.dropped}; })};
process.stdout.write(JSON.stringify(out));
"""


def first_diff(a, b, path):
    """처음 다른 위치(경로, py 값, js 값)"""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                return first_diff(a.get(k), b.get(k), f"{path}.{k}")
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return first_diff(x, y, f"{path}[{i}]")
    return path, a, b


def main():
    ids = sys.argv[1:] or [p.stem for p in DECKS.glob("*.json") if not p.name.endswith(".requests.json")]
    # 언어별 하이라이트 예제(tests/fixtures/code_samples.json - 35개 언어·별칭·줄 번호 끔·이모지)
    extra = STUDIO.parent / "tests" / "fixtures" / "code_samples.json"
    code, texts, plans, tables = list(SAMPLES) + (json.loads(extra.read_text(encoding="utf-8")) if extra.is_file() else []), [], [], list(TABLE_SAMPLES)
    bullets = list(BULLET_SAMPLES)
    for i in ids:
        for s in json.loads((DECKS / f"{i}.json").read_text(encoding="utf-8"))["slides"]:
            for e in s["elements"]:
                if e["type"] == "code":
                    code.append(e)
                elif e["type"] == "plan":
                    plans += str(e.get("text", "")).split("\n")
                elif e["type"] in ("table", "plan-table"):
                    tables.append(e)
                elif e["type"] == "bullets":
                    bullets.append(e)
                if e["type"] in ("text", "pill", "rect", "ellipse") and e.get("text"):
                    texts += str(e["text"]).split("\n")
                if e["type"] == "table":
                    texts += [c for r in e["rows"] for c in r]
    tokens = resolve_tokens()
    # 채우기: 고정 예제 + 덱의 모든 fill 값
    fills = list(FILL_SAMPLES) + [e["fill"] for i in ids for s in json.loads((DECKS / f"{i}.json").read_text(encoding="utf-8"))["slides"]
                                  for e in s["elements"] if e.get("fill")]
    inp = json.dumps({"tokens": tokens, "langs": LANGS, "code": code, "texts": texts, "plans": plans, "tables": tables, "bullets": bullets, "fills": fills, "conv": CONV_SAMPLES},
                     ensure_ascii=False)
    r = subprocess.run(["node", "-e", JS, str(STUDIO / "render.js")], input=inp.encode("utf-8"), capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode("utf-8", "replace"))
    js = json.loads(r.stdout.decode("utf-8"))

    def norm_runs(rs):
        return [[t, {k: v for k, v in st.items() if v}] for t, st in rs]  # bold·color·underline·italic·strike·sup·sub·link·bg

    def rnd(g):
        return {"colW": [round(v, 3) for v in g["colW"]], "rowH": [round(v, 3) for v in g["rowH"]], "cells": g["cells"],
                "callouts": [{**c, **{k: round(c[k], 3) for k in ("x", "y", "h", "cy", "tx")}} for c in g["callouts"]]}

    py = {"code": [[{"n": l["n"], "focus": l["focus"], "gap": l["gap"], "runs": [list(x) for x in l["runs"]]} for l in code_lines(e)] for e in code],
          "runs": [norm_runs(runs(t, 3)) for t in texts],
          "plan": [[list(x) for x in plan_runs(p)] for p in plans],
          "grid": [rnd(table_grid(e)) for e in tables],
          "bullets": [[[t, lvl, round(float(after), 3), [num["label"], num.get("scheme") or "", num["start"], num.get("kind") or "", num_hang(num["label"], float(e.get("subSize", 17)) if lvl else float(e.get("size", 20)), 20 if lvl else 28)] if num else None]
                       for t, lvl, after, num in bullet_rows(e)] for e in bullets],
          "fills": [fill_spec(f) for f in fills],
          "conv": [(lambda o: {"obj": o, "back": obj_to_table(o)[0], "dropped": obj_to_table(o)[1]})(table_to_obj(e)) for e in CONV_SAMPLES]}
    def canon(o):  # 직렬화 차이(정수/실수, 빠진 키/null) 제거
        if isinstance(o, dict):
            return {k: canon(v) for k, v in o.items() if v is not None}
        if isinstance(o, list):
            return [canon(v) for v in o]
        if isinstance(o, (int, float)) and not isinstance(o, bool):
            return round(float(o), 3)
        return o

    py, js = canon(json.loads(json.dumps(py))), canon(js)
    bad = 0
    for k in py:
        for i, (a, b) in enumerate(zip(py[k], js[k])):
            if a != b:
                bad += 1
                p, x, y = first_diff(a, b, f"{k}[{i}]")
                print(f"다름: {p}\n  py={json.dumps(x, ensure_ascii=False)[:300]}\n  js={json.dumps(y, ensure_ascii=False)[:300]}")
        if len(py[k]) != len(js[k]):
            bad += 1
            print(f"개수 다름: {k} py={len(py[k])} js={len(js[k])}")
    n = {k: len(v) for k, v in py.items()}
    print(f"비교: 코드 {n['code']}개 · 인라인 {n['runs']}줄 · plan {n['plan']}줄 · 표 {n['grid']}개 · 글머리 {n['bullets']}개 · 채우기 {n['fills']}개 → {'모두 같음' if not bad else f'{bad}건 다름'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
