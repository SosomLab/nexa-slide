# -*- coding: utf-8 -*-
"""후속 요청(thread) 검증 - 작업 공간 서버 직접: parent → thread·대상 물려받기, 없는 parent 400, brief context, 질문 판정 정규식."""
import json
import os
import tempfile
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 시험 산출물(사용자 설정·작업 공간) - 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
STUDIO = Path(__file__).resolve().parents[1]  # studio/ (이 파일은 studio/tests/)
USER, PROJ = WORK / "user", WORK / "projects"
WS = PROJ / "nexa-slide-demo"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def svc(*a):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), *a], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8")


for f in (WS / "decks").glob("*.requests.json"):
    f.unlink()
print(svc("start").stdout.strip())
try:
    base = json.loads((WS / "out" / ".studio" / "server.json").read_text("utf-8"))["url"].rstrip("/")

    def req(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=30) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    st, decks = req("GET", "/api/decks")
    did = decks[0]["id"]
    st, deck = req("GET", f"/api/deck/{did}")
    sid = deck["slides"][1]["id"]
    st, rs = req("POST", f"/api/requests/{did}", {"action": "add", "status": "open", "slide": sid, "element": "e02", "region": {"kind": "rect", "box": [1, 2, 3, 4]}, "text": "왜 위치가 다른가"})
    root = rs[-1]
    req("POST", f"/api/requests/{did}", {"action": "update", "id": root["id"], "status": "done", "reply": "e46 에 pad 를 주거나 e43 pad 를 빼면 됩니다. 원하는 쪽을 알려 주세요."})
    st, rs = req("POST", f"/api/requests/{did}", {"action": "add", "status": "open", "parent": root["id"], "text": "e43 pad 를 빼 주세요"})
    fu = rs[-1]
    check("후속 요청: parent·thread = 뿌리, slide·element·region 물려받음", st == 200 and fu.get("parent") == root["id"] and fu.get("thread") == root["id"] and fu["slide"] == sid and fu["element"] == "e02" and fu.get("region", {}).get("box") == [1, 2, 3, 4], fu)
    check("  원 요청은 done 그대로", next(r for r in rs if r["id"] == root["id"])["status"] == "done")
    st, rs = req("POST", f"/api/requests/{did}", {"action": "add", "status": "open", "parent": fu["id"], "text": "그리고 색도 맞춰 줘"})
    fu2 = rs[-1]
    check("후속의 후속: thread 는 뿌리 그대로, parent = 직전", fu2.get("thread") == root["id"] and fu2.get("parent") == fu["id"], fu2)
    st, e = req("POST", f"/api/requests/{did}", {"action": "add", "parent": "r-none", "text": "x"})
    check("없는 parent → 400", st == 400, (st, e))

    sys.path.insert(0, str(STUDIO))
    os.environ["NEXA_SLIDE_WORKSPACE"] = str(WS)
    import requests_core as rc
    b = rc.brief({"deck": did, **fu2})
    ctx = b.get("context") or []
    check("brief: parent·thread·context(앞선 2개, 오래된 순, reply 포함)", b.get("thread") == root["id"] and [c["id"] for c in ctx] == [root["id"], fu["id"]] and "pad" in ctx[0]["reply"], b)
    check("  뿌리 요청 brief 에는 context 없음", "context" not in rc.brief({"deck": did, **root}))
    import importlib
    import wsession
    importlib.reload(wsession)
    rx = wsession.QUESTION_RX
    check("질문 판정: '알려 주세요.'·'할까요?'·'?' 는 질문", all(rx.search(t) for t in ("원하는 쪽을 알려 주세요.", "둘 중 무엇으로 할까요?", "맞나요?")))
    check("  '바꿨습니다.' 는 질문 아님", not rx.search("e43 의 pad 를 0 으로 바꿨습니다."))
    tpl = (STUDIO / "agents" / "turn_prompt.md").read_text("utf-8")
    check("turn_prompt: context 규칙 · 질문이면 done 금지", "`context`" in tpl and "done` 으로 하지 않는다" in tpl)
finally:
    for f in (WS / "decks").glob("*.requests.json"):
        f.unlink()
    print("  ", svc("stop").stdout.strip())
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
