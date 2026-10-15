# -*- coding: utf-8 -*-
"""C-4 검증 - 실제 웹 세션 턴이 Excel·PDF 첨부를 import_doc 로 읽어 답하는지(슬라이드는 고치지 않음)."""
import base64
import json
import os
import tempfile
import subprocess
import sys
import time
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
WS = WORK / "projects" / "중계시험-2" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(WORK / "user"), "NEXA_SLIDE_PROJECTS": str(WORK / "projects"), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def ensure_ws(ws, port):  # 시험용 작업 공간(저장소형 <상위>/slides)이 없으면 init_workspace 로 만들고, 덱이 없으면 시작용 덱을 빌드한다
    if not (ws / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(ws.parent), "--title", "중계시험", "--port", str(port)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    if not list((ws / "decks").glob("*.json")):
        subprocess.run([sys.executable, str(STUDIO / "build_deck.py"), "intro", "--force"], env={**ENV, "NEXA_SLIDE_WORKSPACE": str(ws)}, cwd=str(ws), capture_output=True, text=True, encoding="utf-8")


def svc(*a):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), *a], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8")


ensure_ws(WS, 5654)
(WS / ".env").write_text("NEXA_SLIDE_HOME=" + str(STUDIO.parent).replace(chr(92), "/") + "\n", encoding="utf-8")  # 실행기가 worktree 엔진을 쓰게
DOCS = Path(os.environ.get("NEXA_TEST_DOCS") or WS / "out" / "attach" / "intro")  # 표본 문서(real.xlsx · report.pdf) 자리 - 저장소에 넣지 않는다
if not all((DOCS / n).is_file() for n in ("real.xlsx", "report.pdf")):
    print(f"SKIP 표본 문서(real.xlsx · report.pdf)가 없다: {DOCS} - NEXA_TEST_DOCS=<폴더> 로 준다")
    sys.exit(0)
for f in (WS / "decks").glob("*.requests.json"):
    f.unlink()
print(svc("start").stdout.strip())
try:
    base = json.loads((WS / "out" / ".studio" / "server.json").read_text("utf-8"))["url"].rstrip("/")

    def req(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=60) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    st, decks = req("GET", "/api/decks")
    did = decks[0]["id"]
    st, deck = req("GET", f"/api/deck/{did}")
    sid = deck["slides"][0]["id"]
    att = []
    for name, ctype in (("real.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("report.pdf", "application/pdf")):
        st, a = req("POST", f"/api/attach/{did}", {"name": name, "type": ctype, "data": base64.b64encode((DOCS / name).read_bytes()).decode()})
        att.append(a)
    req("POST", f"/api/requests/{did}", {"action": "add", "status": "open", "slide": sid, "attachments": att,
                                       "text": "슬라이드는 고치지 마. 첨부한 엑셀의 차트 '월별 매출' 계열 값과, PDF 1쪽 표의 Busan Q2 값을 reply 에 적어 줘."})
    st, s = req("POST", "/api/wsession", {"action": "start", "agent": "claude", "model": "sonnet"})
    check("세션 시작 · 세션 ID 미리 정해짐(UUID)", st == 200 and len(s.get("sessionId") or "") == 36, (st, s.get("sessionId")))
    sid0 = s.get("sessionId")
    st, ss = req("GET", "/api/session")
    check("  /api/session 에 sessionId·cwd(턴 0)", ss.get("sessionId") == sid0 and ss.get("cwd"), ss)
    req("POST", f"/api/flush/{did}")
    t0 = time.time()
    while time.time() - t0 < 420:
        time.sleep(5)
        st, info = req("GET", "/api/wsession")
        st2, rs = req("GET", f"/api/requests/{did}")
        r = rs[-1]
        if info.get("state") == "ready" and info.get("turns", 0) >= 1 and r.get("reply"):
            break
    print(f"   턴: {int(time.time() - t0)}초 · status={r.get('status')} · reply={r.get('reply', '')[:400]}")
    check("세션 ID 가 턴 뒤에도 같다(--session-id 로 만들어짐)", info.get("sessionId") == sid0, (info.get("sessionId"), sid0))
    log = (Path(info["logDir"]) / "turn-1.jsonl").read_text("utf-8")
    check("  턴이 import_doc 를 실행", "import_doc" in log)
    rep = r.get("reply", "")
    check("  답에 엑셀 차트 값(95.5)과 PDF 표 값(95)", "95.5" in rep and "95" in rep.replace("95.5", ""), rep)
    claude_dir = Path.home() / ".claude" / "projects"
    check("  claude 세션 파일 <ID>.jsonl 이 생김(claude --resume 로 열림)", any(claude_dir.glob(f"*/{sid0}.jsonl")))
    req("POST", "/api/wsession", {"action": "stop"})
finally:
    print("  ", svc("stop").stdout.strip())
    for f in (WS / "decks").glob("*.requests.json"):
        f.unlink()
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)


