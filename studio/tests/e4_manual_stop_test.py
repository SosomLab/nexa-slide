# -*- coding: utf-8 -*-
"""0.21.14 검증 - 수동 세션 수명: stdout 닫히면 감시 종료 · --takeover 가 이전 감시를 끝냄 · 웹 [끊기](/api/engine/session stop)가 수동 감시를 끝냄 · 작업 공간 watch_requests 도 stdout 닫히면 종료."""
import http.cookiejar
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
STUDIO = Path(__file__).resolve().parents[1]  # studio/ (이 파일은 studio/tests/)
sys.path.insert(0, str(STUDIO))
import procutil  # noqa: E402

WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 시험 산출물(사용자 설정·작업 공간) - 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
USER, PROJ, HUB_PORT = WORK / "user", WORK / "projects", 5799
BASE = f"http://127.0.0.1:{HUB_PORT}"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
FAILS = []
HB = USER / "hub" / "engine" / ".studio" / "session.json"


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def svc(cmd):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")


def client():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def req(method, url, body=None):
        h = {"Accept": "application/json", "Origin": BASE}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        try:
            with op.open(urllib.request.Request(url, data=data, method=method, headers=h), timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    return req


def hb():
    try:
        return json.loads(HB.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def wait_dead(pid, sec=5):
    t0 = time.time()
    while procutil.pid_alive(pid) and time.time() - t0 < sec:
        time.sleep(0.2)
    return not procutil.pid_alive(pid)


(USER / "settings.json").write_text(json.dumps({"hubPort": HUB_PORT, "hubProxy": True, "engine": str(STUDIO.parent)}), encoding="utf-8")
(USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
HB.unlink(missing_ok=True)
W = [sys.executable, str(STUDIO / "watch_engine_requests.py")]
procs = []
try:
    print(svc("start").stdout.strip())
    (USER / "users.json").unlink(missing_ok=True)
    admin = client()
    admin("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "e4-test-pass-1"})

    # 1) stdout 의 읽는 쪽이 닫히면 감시가 스스로 끝난다
    p1 = subprocess.Popen(W + ["--stream", "--label", "e4:one"], env=ENV, cwd=str(USER), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    procs.append(p1)
    time.sleep(2.0)
    h1 = hb()
    check("감시 1 하트비트(manual, pid)", h1.get("kind") == "manual" and h1.get("pid") == p1.pid and not h1.get("stopped"), h1)
    p1.stdout.close()  # Monitor 를 건 세션이 닫힌 상황
    try:
        p1.wait(6)
    except subprocess.TimeoutExpired:
        pass
    check("읽는 쪽 닫힘 → 감시 1 스스로 종료(3초 안)", p1.poll() is not None, f"poll={p1.poll()}")
    check("  하트비트 stopped", hb().get("stopped") is True, hb())

    # 2) --takeover 가 이전 감시를 실제로 끝낸다
    p2 = subprocess.Popen(W + ["--stream", "--label", "e4:two"], env=ENV, cwd=str(USER), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    procs.append(p2)
    time.sleep(2.0)
    p3 = subprocess.Popen(W + ["--stream", "--takeover", "--label", "e4:three"], env=ENV, cwd=str(USER), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    procs.append(p3)
    time.sleep(3.0)
    check("takeover → 이전 감시 2 종료", wait_dead(p2.pid, 5), f"p2 alive={procutil.pid_alive(p2.pid)}")
    h3 = hb()
    check("  하트비트는 감시 3(pid)", h3.get("pid") == p3.pid and h3.get("label") == "e4:three" and not h3.get("stopped"), h3)
    first = p3.stdout.readline().decode("utf-8", "replace")
    check("  감시 3 첫 이벤트 takeover", '"event": "takeover"' in first, first)
    st, d = admin("GET", BASE + "/api/engine")
    check("  /api/engine state=manual label=e4:three", d["session"].get("state") == "manual" and d["session"].get("label") == "e4:three", d["session"])

    # 3) 웹 [끊기] - /api/engine/session stop 이 수동 감시를 끝낸다
    st, r = admin("POST", BASE + "/api/engine/session", {"action": "stop", "reason": "web"})
    check("웹 끊기 응답 stopped·manual.pid", st == 200 and r.get("stopped") is True and r.get("manual", {}).get("pid") == p3.pid, (st, r))
    check("  감시 3 프로세스 종료", wait_dead(p3.pid, 5), f"alive={procutil.pid_alive(p3.pid)}")
    time.sleep(0.5)
    st, d = admin("GET", BASE + "/api/engine")
    check("  /api/engine state=off", d["session"].get("state") == "off", d["session"])
    check("  하트비트 stopped(stoppedBy web)", hb().get("stopped") is True and hb().get("stoppedBy") == "web", hb())
    st, r = admin("POST", BASE + "/api/engine/session", {"action": "stop", "reason": "web"})
    check("수동 세션 없을 때 끊기 → stopped false, 오류 없음", st == 200 and r.get("stopped") is False, (st, r))
    st, r = admin("POST", BASE + "/api/engine/session", {"action": "start", "agent": "claude", "model": "haiku"})
    # 이 시험은 개발 worktree 를 엔진으로 쓰므로 engine-dev 브랜치가 운영 트리의 worktree 에 이미 있어 worktree 생성은 실패할 수 있다 - "수동 세션" 거절이 아니면 통과
    check("끊은 뒤 웹 엔진 세션 시작 허용(수동 세션 거절 아님)", st == 200 or "수동" not in str(r.get("error", "")), (st, r))
    if st == 200:
        admin("POST", BASE + "/api/engine/session", {"action": "stop"})

    # 4) 작업 공간 watch_requests 도 stdout 닫히면 종료
    ws = next((p for p in sorted(PROJ.glob("*/slides")) if (p / "nexa-slide.json").is_file()), None)
    if ws:
        wenv = {**ENV, "NEXA_SLIDE_WORKSPACE": str(ws)}
        p4 = subprocess.Popen([sys.executable, str(STUDIO / "watch_requests.py"), "--stream", "--takeover", "--label", "e4:ws"], env=wenv, cwd=str(ws), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p4)
        time.sleep(2.0)
        shb = ws / "out" / ".studio" / "session.json"
        try:
            h4 = json.loads(shb.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            h4 = {}
        check("작업 공간 감시 하트비트(pid)", h4.get("pid") == p4.pid and not h4.get("stopped"), h4)
        p4.stdout.close()
        try:
            p4.wait(6)
        except subprocess.TimeoutExpired:
            pass
        check("작업 공간 감시: 읽는 쪽 닫힘 → 종료", p4.poll() is not None, f"poll={p4.poll()}")
        try:
            h4 = json.loads(shb.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            h4 = {}
        check("  하트비트 stopped", h4.get("stopped") is True, h4)
    else:
        print("SKIP 작업 공간 없음(projects/*/slides)")
finally:
    for p in procs:
        if p.poll() is None:
            procutil.kill_tree(p.pid)
    print("  ", svc("stop").stdout.strip())
    (USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
    HB.unlink(missing_ok=True)
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
