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


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    spec = json.loads((HERE / "sheetcalc_cases.json").read_text(encoding="utf-8"))
    ok = 0
    for f, want in spec["cases"]:
        doc = {"sheets": copy.deepcopy(spec["sheets"])}
        doc["sheets"][0]["cells"][spec["at"]] = {"f": f}
        sheet_calc.recalc(doc)
        got = doc["sheets"][0]["cells"][spec["at"]].get("v")
        if same(got, want):
            ok += 1
        else:
            FAILS.append(f)
            print(f"FAIL {f} → {got!r} (기대 {want!r})")
    # 순환 참조 · 내보내기 캐시
    doc = {"sheets": [{"id": "t01", "name": "S", "cells": {"A1": {"f": "=B1+1"}, "B1": {"f": "=A1+1"}}}]}
    sheet_calc.recalc(doc)
    if doc["sheets"][0]["cells"]["A1"]["v"] != "#REF!":
        FAILS.append("순환 참조")
        print("FAIL 순환 참조 →", doc["sheets"][0]["cells"]["A1"]["v"])
    print(f"사례 {len(spec['cases'])}개 중 {ok}개 같음(Python)")
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
