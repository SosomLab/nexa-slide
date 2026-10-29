# -*- coding: utf-8 -*-
"""시트 구조 작업(sheet_struct.py) 골든 시험 - tests/sheet_struct_cases.json. 동시 편집 3-2(docs/collab.md).
    python3 studio/tests/sheet_struct_test.py
사례마다 (문서, 작업들) → 기대 문서가 같은지, 입력을 고치지 않는지 본다. 같은 사례를 화면(sheet.js shiftAxis)도 통과해야 한다(sheetstruct_test 시나리오)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import sheet_struct  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")


def main():
    cases = json.loads((HERE / "sheet_struct_cases.json").read_text(encoding="utf-8"))
    fails = 0
    for c in cases:
        before = copy.deepcopy(c["doc"])
        got = sheet_struct.apply(c["doc"], c["ops"])
        ok = got == c["expect"] and c["doc"] == before
        print(("OK  " if ok else "FAIL"), c["name"], "" if ok else f"\n  결과 {json.dumps(got, ensure_ascii=False)}\n  기대 {json.dumps(c['expect'], ensure_ascii=False)}")
        fails += not ok
    print(f"\n{'전부 통과' if not fails else f'실패 {fails}'} ({len(cases)}사례)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
