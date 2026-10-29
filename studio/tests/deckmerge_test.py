# -*- coding: utf-8 -*-
"""덱·시트 3-way 병합(deckmerge.py) 골든 시험 - tests/deckmerge_cases.json 의 (기준, 보낸 것, 파일, 기대) 묶음.
    python3 studio/tests/deckmerge_test.py
사례마다 병합 결과가 기대와 같고 충돌 수가 맞는지, 입력을 고치지 않는지, 기준과 같은 쪽은 그대로 다른 쪽을 돌려주는지(항등)를 본다."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import deckmerge  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")


def main():
    cases = json.loads((HERE / "deckmerge_cases.json").read_text(encoding="utf-8"))
    fails = 0
    for c in cases:
        ins = copy.deepcopy((c["base"], c["ours"], c["theirs"]))
        got, conf = deckmerge.merge3(c["base"], c["ours"], c["theirs"], c.get("prefer", "ours"))
        ok = got == c["expect"] and len(conf) == c["conflicts"] and ins == (c["base"], c["ours"], c["theirs"])
        try:  # 충돌 기록은 원장·응답에 JSON 으로 쓴다 - 내부 표식(MISSING)이 새면 저장이 500
            cj = json.loads(json.dumps(conf, ensure_ascii=False))
            ok = ok and cj == c.get("conflictList", cj)
        except TypeError:
            ok = False
        print(("OK  " if ok else "FAIL"), c["name"], "" if ok else f"\n  충돌 {len(conf)}(기대 {c['conflicts']}) {conf}\n  결과 {json.dumps(got, ensure_ascii=False)}\n  기대 {json.dumps(c['expect'], ensure_ascii=False)}")
        fails += not ok
        for side in ("ours", "theirs"):  # 항등 - 한쪽이 기준 그대로면 결과는 다른 쪽
            other = "theirs" if side == "ours" else "ours"
            args = {"base": c["base"], side: c["base"], other: c[other]}
            g, cf = deckmerge.merge3(args["base"], args["ours"], args["theirs"])
            strip = lambda d: {k: v for k, v in d.items() if k != "updated"}  # noqa: E731 - updated 는 저장할 때 서버가 새로 넣는다
            if strip(g) != strip(c[other]) or cf:
                print("FAIL", c["name"], f"- 항등({side} = 기준) 깨짐", cf)
                fails += 1
    print(f"\n{'전부 통과' if not fails else f'실패 {fails}'} ({len(cases)}사례)")
    # 화면 병합(nexa-merge.js)도 같은 사례로 - 서버와 화면의 규칙이 같아야 한다(render.js ↔ export_pptx 처럼)
    import shutil
    import subprocess
    if shutil.which("node"):
        r = subprocess.run(["node", str(HERE / "nexa_merge_check.js")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("nexa-merge.js:", (r.stdout.strip().splitlines() or ["?"])[-1])
        if r.returncode:
            print(r.stdout[-2000:])
            fails += 1
    else:
        print("nexa-merge.js: node 없음 - 건너뜀")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
