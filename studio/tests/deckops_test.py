# -*- coding: utf-8 -*-
"""작업(op) 저장(deckops.py, 동시 편집 3-4) 골든 시험 - tests/deckops_cases.json 의 (저장본, 지금, 작업, 얹을 파일, 기준본, 기대) 묶음.
    python3 studio/tests/deckops_test.py
사례마다 diff 가 같은 작업 목록을 만들고, 그 작업을 얹은 결과·적용 수·버린 수가 기대와 같은지, 저장본에 얹으면 지금 문서가 되는지(왕복),
입력을 고치지 않는지 본다. 화면(nexa-merge.js ops·applyOps)도 같은 사례로(nexa_ops_check.js)."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import deckops  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")


def ids(d):
    return [[s.get("id"), [e.get("id") for e in s.get("elements") or []]] for s in d.get("slides") or []], [t.get("id") for t in d.get("sheets") or []]


def main():
    cases = json.loads((HERE / "deckops_cases.json").read_text(encoding="utf-8"))
    fails = 0
    for c in cases:
        ins = copy.deepcopy(c)
        ops = deckops.diff(c["old"], c["new"])
        got, n, dr = deckops.apply(c["doc"], c["ops"], base=c["base"])
        rt = deckops.apply(c["old"], ops)[0]
        ok = ops == c["ops"] and got == c["expect"] and ids(got) == ids(c["expect"]) and n == c["applied"] and len(dr) == c["dropped"] \
            and rt == c["new"] and ids(rt) == ids(c["new"]) and ins == c
        print(("OK  " if ok else "FAIL"), c["name"], "" if ok else f"\n  작업 {json.dumps(ops, ensure_ascii=False)[:500]}\n  결과 {ids(got)} / 기대 {ids(c['expect'])} · 왕복 {rt == c['new']}")
        fails += not ok
    print(f"\n{'전부 통과' if not fails else f'실패 {fails}'} ({len(cases)}사례)")
    if shutil.which("node"):
        r = subprocess.run(["node", str(HERE / "nexa_ops_check.js")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("nexa-merge.js 작업:", (r.stdout.strip().splitlines() or ["?"])[-1])
        if r.returncode:
            print(r.stdout[-2000:])
            fails += 1
    else:
        print("nexa-merge.js 작업: node 없음 - 건너뜀")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
