# -*- coding: utf-8 -*-
"""시트 수식 계산기(sheet_calc.py) 시험 - sheetcalc_cases.json 의 사례를 '데이터' 탭 H10 칸에 넣고 계산해 기대값과 비교한다.
화면(sheet.js)도 같은 사례 파일을 쓴다 - 두 곳의 계산 규칙이 같아야 한다."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import sheet_calc  # noqa: E402

FAILS = []


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-9
    return a == b


def a1(r, k):
    """0 부터 센 행·열 → A1."""
    s, k = "", k + 1
    while k:
        k, m = divmod(k - 1, 26)
        s = chr(65 + m) + s
    return f"{s}{r + 1}"


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    spec = json.loads((HERE / "sheetcalc_cases.json").read_text(encoding="utf-8"))
    ok = 0
    for f, want in spec["cases"]:
        doc = {"sheets": copy.deepcopy(spec["sheets"]), "names": spec.get("names") or {}}
        doc["sheets"][0]["cells"][spec["at"]] = {"f": f}
        sheet_calc.recalc(doc)
        got = doc["sheets"][0]["cells"][spec["at"]].get("v")
        if same(got, want):
            ok += 1
        else:
            FAILS.append(f)
            print(f"FAIL {f} → {got!r} (기대 {want!r})")
    for sp in spec.get("spills", []):  # 동적 배열 - 넘친 칸
        doc = {"sheets": copy.deepcopy(spec["sheets"]), "names": spec.get("names") or {}}
        doc["sheets"][0]["cells"].update(copy.deepcopy(sp["cells"]))
        if sp.get("tables"):
            doc["sheets"][0]["tables"] = copy.deepcopy(sp["tables"])
        sheet_calc.recalc(doc)
        cells = doc["sheets"][0]["cells"]
        got = {k: (cells.get(k).get("v") if isinstance(cells.get(k), dict) else cells.get(k)) for k in sp["expect"]}
        if all(same(got[k], w) for k, w in sp["expect"].items()):
            ok += 1
        else:
            FAILS.append(sp["name"])
            print(f"FAIL {sp['name']} → {got} (기대 {sp['expect']})")
    pv = spec.get("pivot") or {"arrays": []}
    for f, grid in pv["arrays"]:  # GROUPBY·PIVOTBY - 넘친 배열 전체(엑셀 값)와 크기
        doc = {"sheets": copy.deepcopy(spec["sheets"]) + [copy.deepcopy(pv["sheet"]), {"id": "t04", "name": "F", "cells": {"A1": {"f": f}}}], "names": spec.get("names") or {}}
        sheet_calc.recalc(doc)
        cells = doc["sheets"][-1]["cells"]
        val = lambda r, k: (lambda x: "" if x is None else x)(cells.get(a1(r, k)).get("v") if isinstance(cells.get(a1(r, k)), dict) else cells.get(a1(r, k)))  # noqa: E731
        got = [[val(r, k) for k in range(len(grid[0]))] for r in range(len(grid))]
        extra = val(len(grid), 0) != "" or val(0, len(grid[0])) != ""
        if not extra and all(same(g, w) for gr, wr in zip(got, grid) for g, w in zip(gr, wr)):
            ok += 1
        else:
            FAILS.append(f)
            print(f"FAIL {f}\n  결과 {got}{' (더 넘침)' if extra else ''}\n  기대 {grid}")
    # 순환 참조 · 내보내기 캐시
    doc = {"sheets": [{"id": "t01", "name": "S", "cells": {"A1": {"f": "=B1+1"}, "B1": {"f": "=A1+1"}}}]}
    sheet_calc.recalc(doc)
    if doc["sheets"][0]["cells"]["A1"]["v"] != "#REF!":
        FAILS.append("순환 참조")
        print("FAIL 순환 참조 →", doc["sheets"][0]["cells"]["A1"]["v"])
    # 이름 정의 없이 가져온 문서 - 모르는 이름의 수식은 엑셀이 계산해 둔 값을 #NAME? 로 덮지 않는다
    doc = {"sheets": [{"id": "t01", "name": "S", "cells": {"A1": {"f": "=없는이름*2", "v": 42}}}]}
    sheet_calc.recalc(doc)
    if doc["sheets"][0]["cells"]["A1"]["v"] != 42:
        FAILS.append("모르는 이름 - 엑셀 값 유지")
        print("FAIL 모르는 이름 - 엑셀 값 유지 →", doc["sheets"][0]["cells"]["A1"]["v"])
    print(f"사례 {len(spec['cases']) + len(spec.get('spills', [])) + len(pv['arrays'])}개 중 {ok}개 같음(Python)")
    import shutil
    import subprocess
    if shutil.which("node"):  # 화면 계산기(sheetcalc.js)도 같은 사례로 - 두 곳 동일성
        r = subprocess.run(["node", str(HERE / "sheetcalc_test.js")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print((r.stdout or "").strip().replace("실패:", "화면 실패:"))
        if r.returncode:
            FAILS.append("화면 계산기(sheetcalc.js)")
    print("\n실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
