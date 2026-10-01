# -*- coding: utf-8 -*-
"""render.js(JS) 와 common.py(Python) 가 같은 결과를 내는지 확인 (검증 도구, node 필요).

    python3 studio/check_parity.py [ch00 …]

비교 대상: 덱의 모든 code 요소 줄 하이라이트(codeLines) · 모든 요소의 인라인 강조(runs) · plan 강조 · 표 격자(tableGrid).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS, STUDIO, code_lines, resolve_tokens, plan_runs, runs, table_grid  # noqa: E402

SAMPLES = [
    {"type": "code", "lang": "python", "text": "def f(x):\n    # 주석\n    return x * 2 + 'a'  # 끝\n"},
    {"type": "code", "lang": "sql", "text": "WITH t AS (SELECT a.id AS k FROM tab a JOIN tab2 b ON b.id = a.id)\nSELECT t.k, COUNT(*) cnt\nFROM t\nWHERE t.k > 10 AND x = 'it''s' -- c\n/* 여러\n 줄 */ AND y = :b1;"},
]

JS = r"""
const R = require(process.argv[1]);
const inp = JSON.parse(require('fs').readFileSync(0, 'utf8'));
R.setTokens(inp.tokens);
const out = {code: inp.code.map(e => R.codeLines(e).map(l => ({n: l.n, focus: l.focus, gap: l.gap, runs: l.runs}))),
  runs: inp.texts.map(t => R.runs(t, 3).map(([t2, st]) => [t2, {bold: st.bold, color: st.color}])),
  plan: inp.plans.map(p => R.planRuns(p)),
  grid: inp.tables.map(e => { const g = R.tableGrid(e); return {colW: g.colW.map(v => +v.toFixed(3)), rowH: g.rowH.map(v => +v.toFixed(3)), cells: g.cells, callouts: g.callouts.map(c => ({...c, x: +c.x.toFixed(3), y: +c.y.toFixed(3), h: +c.h.toFixed(3), cy: +c.cy.toFixed(3), tx: +c.tx.toFixed(3)}))}; })};
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
    code, texts, plans, tables = list(SAMPLES), [], [], []
    for i in ids:
        for s in json.loads((DECKS / f"{i}.json").read_text(encoding="utf-8"))["slides"]:
            for e in s["elements"]:
                if e["type"] == "code":
                    code.append(e)
                elif e["type"] == "plan":
                    plans += str(e.get("text", "")).split("\n")
                elif e["type"] in ("table", "plan-table"):
                    tables.append(e)
                if e["type"] in ("text", "pill", "rect", "ellipse") and e.get("text"):
                    texts += str(e["text"]).split("\n")
                if e["type"] == "table":
                    texts += [c for r in e["rows"] for c in r]
    tokens = resolve_tokens()
    inp = json.dumps({"tokens": tokens, "code": code, "texts": texts, "plans": plans, "tables": tables}, ensure_ascii=False)
    r = subprocess.run(["node", "-e", JS, str(STUDIO / "render.js")], input=inp.encode("utf-8"), capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode("utf-8", "replace"))
    js = json.loads(r.stdout.decode("utf-8"))

    def norm_runs(rs):
        return [[t, {"bold": st.get("bold"), "color": st.get("color")}] for t, st in rs]

    def rnd(g):
        return {"colW": [round(v, 3) for v in g["colW"]], "rowH": [round(v, 3) for v in g["rowH"]], "cells": g["cells"],
                "callouts": [{**c, **{k: round(c[k], 3) for k in ("x", "y", "h", "cy", "tx")}} for c in g["callouts"]]}

    py = {"code": [[{"n": l["n"], "focus": l["focus"], "gap": l["gap"], "runs": [list(x) for x in l["runs"]]} for l in code_lines(e)] for e in code],
          "runs": [norm_runs(runs(t, 3)) for t in texts],
          "plan": [[list(x) for x in plan_runs(p)] for p in plans],
          "grid": [rnd(table_grid(e)) for e in tables]}
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
    print(f"비교: 코드 {n['code']}개 · 인라인 {n['runs']}줄 · plan {n['plan']}줄 · 표 {n['grid']}개 → {'모두 같음' if not bad else f'{bad}건 다름'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
