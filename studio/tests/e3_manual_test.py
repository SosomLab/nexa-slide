# -*- coding: utf-8 -*-
"""E-3 검증 - 수동 엔진 세션(watch_engine_requests): 1회 출력·stream 하트비트 → /api/engine state=manual·notice sessionOff false·웹 엔진 세션 시작 거절, 끝나면 off."""
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
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 시험 산출물(사용자 설정·작업 공간) - 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
USER, PROJ, HUB_PORT = WORK / "user", WORK / "projects", 5799
BASE = f"http://127.0.0.1:{HUB_PORT}"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
FAILS = []


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


(USER / "settings.json").write_text(json.dumps({"hubPort": HUB_PORT, "hubProxy": True, "engine": str(STUDIO.parent)}), encoding="utf-8")
(USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
(USER / "hub" / "engine" / ".studio" / "session.json").unlink(missing_ok=True)
W = [sys.executable, str(STUDIO / "watch_engine_requests.py")]
try:
    print(svc("start").stdout.strip())
    (USER / "users.json").unlink(missing_ok=True)
    admin = client()
    admin("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "e3-test-pass-1"})
    st, r = admin("POST", BASE + "/api/engine/requests", {"action": "add", "title": "수동 시험 요청", "body": "b"})
    rid = r["item"]["id"]
    one = subprocess.run(W, env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")
    ev = [json.loads(l) for l in one.stdout.splitlines() if l.startswith("{")]
    check("1회 실행: open 요청 1건 이벤트", any(e.get("event") == "request" and e["item"]["id"] == rid for e in ev), one.stdout + one.stderr)
    st, d = admin("GET", BASE + "/api/engine")
    check("1회 실행 뒤 세션 off(stopped 하트비트)", d["session"].get("state") == "off" and d.get("sessionOff") is True, d["session"])
    p = subprocess.Popen(W + ["--stream", "--label", "e3:claude"], env=ENV, cwd=str(USER), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    time.sleep(2.5)
    st, d = admin("GET", BASE + "/api/engine")
    check("stream 중 /api/engine state=manual · label · sessionOff false", d["session"].get("state") == "manual" and d["session"].get("label") == "e3:claude" and d.get("sessionOff") is False, d["session"])
    st, n = admin("GET", BASE + "/api/engine/notice")
    check("  notice sessionOff false", n.get("sessionOff") is False, n)
    st, h = admin("GET", BASE + "/api/home")
    check("  /api/home engineWork.sessionOff false", h.get("engineWork", {}).get("sessionOff") is False, h.get("engineWork"))
    st, s = admin("POST", BASE + "/api/engine/session", {"action": "start", "agent": "claude", "model": "haiku"})
    check("수동 감시 중 웹 엔진 세션 시작 → 거절", st == 400 and "수동" in s.get("error", ""), (st, s))
    two = subprocess.run(W, env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")
    check("다른 수동 감시 → refused(already-watched)", "already-watched" in two.stdout, two.stdout)
    admin("POST", BASE + "/api/engine/requests", {"action": "add", "title": "두 번째", "body": "b"})
    time.sleep(2.5)
    p.terminate()
    try:
        out = p.communicate(timeout=10)[0]
    except subprocess.TimeoutExpired:
        p.kill(); out = p.communicate()[0]
    evs = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    check("stream: 두 요청 모두 이벤트로", sum(1 for e in evs if e.get("event") == "request") >= 2, out[-400:])
    time.sleep(0.5)
    st, d = admin("GET", BASE + "/api/engine")
    check("감시가 끝나면 off (stopped 하트비트 또는 pid 사망)", d["session"].get("state") == "off" or not d["session"].get("pid"), d["session"])
finally:
    print("  ", svc("stop").stdout.strip())
    (USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
    (USER / "hub" / "engine" / ".studio" / "session.json").unlink(missing_ok=True)
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
