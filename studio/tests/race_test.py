# -*- coding: utf-8 -*-
"""서버 2중 기동 경합 시험 - 같은 작업 공간에 `service.py start`(설정 포트)와 `service.py start --port auto` 를 동시에 여러 번 넣어도 서버가 하나만 떠야 한다."""
import json
import os
import tempfile
import subprocess
import sys
import time
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
WS = PROJ / "중계시험-2" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
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


ensure_ws(WS, 5654)


def svc(*args):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), *args], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8")


def listening():
    """이 작업 공간을 내주는 서버 포트 목록(5600~5660 두드림)."""
    out = []
    for p in range(5650, 5700):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{p}/api/config", timeout=0.4) as r:
                cfg = json.loads(r.read().decode("utf-8"))
            if cfg.get("path") and Path(cfg["path"]).resolve() == WS.resolve():
                out.append(p)
        except Exception:  # noqa: BLE001
            pass
    return out


svc("stop")
try:
    for rnd in range(3):
        print(f"-- {rnd + 1}회: 동시 start ×4 (설정 포트 2 + auto 2)")
        procs = [subprocess.Popen([sys.executable, str(STUDIO / "service.py"), "start", *extra], env=ENV, cwd=str(WS), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
                 for extra in ([], ["--port", "auto"], [], ["--port", "auto"])]
        outs = [p.communicate(timeout=90)[0].strip().splitlines()[-1] if p.communicate(timeout=90)[0].strip() else "" for p in procs]
        time.sleep(1)
        ports = listening()
        check(f"  서버 하나만 떠 있음 {ports}", len(ports) == 1, outs)
        info = json.loads((WS / "out" / ".studio" / "server.json").read_text("utf-8"))
        check(f"  server.json 포트 = 그 서버({info.get('port')})", ports and info.get("port") == ports[0])
        check("  나머지 start 는 '이미 실행 중' 또는 '시작'", all(("이미 실행 중" in o) or ("시작:" in o) for o in outs), outs)
        print("   ", svc("stop").stdout.strip())
        time.sleep(0.5)
        check("  stop 뒤 서버 없음", not listening())
finally:
    svc("stop")
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
