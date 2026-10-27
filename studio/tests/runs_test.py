# -*- coding: utf-8 -*-
"""인라인 강조 겹치기 시험 - common.runs(Python) 과 render.js runs(node) 가 겹친 표기에서 같은 결과(글자·bold·color·underline·italic)를 내는지."""
import json
import subprocess
import sys
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
import os
os.environ.setdefault("NEXA_SLIDE_WORKSPACE", str(STUDIO.parent / "example"))  # common 은 작업 공간이 있어야 읽힌다 - 엔진의 example
sys.path.insert(0, str(STUDIO))
from common import runs  # noqa: E402

CASES = [
    "보통 **굵게** 보통",
    "[[s1|**굵은 색 글자**]] 뒤",
    "**[[s1|색]] 굵게** 끝",
    "**==강조== 안 __밑줄__**",
    "[[#FF0000|*기울임 색*]]",
    "__[[s2|밑줄 색]]__",
    "앞 **굵게 [[s1|색 *기울임*]] 끝** 뒤 {page}",
    "**a** [[s1|b]] 평범 ==c==",
    # 0.22.11 - 취소선 · 위/아래 첨자 · 글자 링크 · 형광펜(겹치기 포함)
    "~~취소~~ 그대로 m^{2} CO_{2}",
    "[[link:https://example.com/a?b=1|문서]] [[link:#3|3장]] [[url:#s07|id]]",
    "[[bg:s1|형광]] **[[bg:#FFFF00|~~굵은 취소~~]]** a_b 2^10",
]
EXPECT = {
    "[[s1|**굵은 색 글자**]] 뒤": [("굵은 색 글자", {"bold": True, "color": "s1"}), (" 뒤", {})],
    "**[[s1|색]] 굵게** 끝": [("색", {"bold": True, "color": "s1"}), (" 굵게", {"bold": True}), (" 끝", {})],
    "~~취소~~ 그대로 m^{2} CO_{2}": [("취소", {"strike": True}), (" 그대로 m", {}), ("2", {"sup": True}), (" CO", {}), ("2", {"sub": True})],
    "[[link:https://example.com/a?b=1|문서]] [[link:#3|3장]] [[url:#s07|id]]": [("문서", {"link": "https://example.com/a?b=1"}), (" ", {}), ("3장", {"link": "#3"}), (" ", {}), ("id", {"link": "#s07"})],
    "[[bg:s1|형광]] **[[bg:#FFFF00|~~굵은 취소~~]]** a_b 2^10": [("형광", {"bg": "s1"}), (" ", {}), ("굵은 취소", {"bg": "#FFFF00", "bold": True, "strike": True}), (" a_b 2^10", {})],
}
fails = []


def norm(rs):
    return [[t, {k: v for k, v in sorted(st.items()) if v}] for t, st in rs]


py = {c: norm(runs(c, 3)) for c in CASES}
for c, exp in EXPECT.items():
    got = py[c]
    ok = got == norm(exp)
    print("OK  " if ok else "FAIL", "python", c, "" if ok else f"→ {got}")
    if not ok:
        fails.append(c)
js = f'''
const fs=require("fs"), vm=require("vm"); const src=fs.readFileSync({json.dumps(str(STUDIO / "render.js"))},"utf8");
const w={{document:{{createElement:()=>({{style:{{}}}}),querySelector:()=>null}},location:{{}},navigator:{{}}}}; w.window=w; w.self=w; vm.createContext(w); vm.runInContext(src,w);
const cases={json.dumps(CASES, ensure_ascii=False)};
const out={{}}; for (const c of cases) out[c]=w.Render.runs(c,3).map(([t,st])=>[t, Object.fromEntries(Object.entries(st).filter(([k,v])=>v).sort())]);
console.log(JSON.stringify(out));
'''
r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    jsout = json.loads(r.stdout.strip().splitlines()[-1])
except Exception:  # noqa: BLE001
    print("FAIL render.js 실행", (r.stderr or r.stdout)[-300:]); fails.append("node"); jsout = {}
for c in CASES:
    if c not in jsout:
        continue
    ok = jsout[c] == py[c]
    print("OK  " if ok else "FAIL", "parity", c, "" if ok else f"\n   py={py[c]}\n   js={jsout[c]}")
    if not ok:
        fails.append(c)
print("실패:", fails or "없음")
sys.exit(1 if fails else 0)
