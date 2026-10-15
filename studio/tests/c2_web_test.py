# -*- coding: utf-8 -*-
"""C-2 검증(서버 쪽) - 웹 세션 웹 검색 허용(sessionAllowWeb): 전역 스위치(관리자만)·세션 단위 체크·권한 JSON·표시·거절 경로. 실제 턴은 돌리지 않는다."""
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


def svc(cmd, ws=None):
    env = dict(ENV)
    if ws:
        env["NEXA_SLIDE_WORKSPACE"] = str(ws)
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=env, cwd=str(ws or USER), capture_output=True, text=True, encoding="utf-8")


def client():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def req(method, url, body=None, timeout=120):
        h = {"Accept": "application/json", "Origin": BASE}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        try:
            with op.open(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    return req, jar


(USER / "settings.json").write_text(json.dumps({"hubPort": HUB_PORT, "hubProxy": True, "engine": str(STUDIO.parent)}), encoding="utf-8")
started = []
try:
    print(svc("start").stdout.strip())
    (USER / "users.json").unlink(missing_ok=True)
    admin, _ = client()
    admin("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "c2-test-pass-1"})
    st, d = admin("POST", BASE + "/api/project", {"action": "demo"})
    ws = Path(d["path"]); started.append(ws); wid = d["id"]
    admin("POST", BASE + "/api/auth/users", {"action": "add", "id": "bob", "password": "bob-pass-123", "role": "user"})
    bob, _j = client()
    bob("POST", BASE + "/api/auth/login", {"id": "bob", "password": "bob-pass-123"})

    # 1) 기본: 전역 꺼짐 → allowWeb false, 세션에서 allowWeb 요청하면 400
    st, a = admin("GET", BASE + "/api/agent")
    check("/api/agent 기본 allowWeb=false · canAllowWeb=false", a.get("allowWeb") is False and a.get("canAllowWeb") is False, a)
    st, s = admin("POST", BASE + "/api/project", {"action": "session", "op": "start", "path": str(ws), "agent": "claude", "model": "haiku", "allowWeb": True})
    check("전역 꺼짐 + allowWeb 시작 → 400(전역 설정 안내)", st == 400 and "전역" in s.get("error", ""), (st, s))

    # 2) 전역 켜기 - 관리자만, 접근 로그 이벤트
    st, h = bob("POST", BASE + "/api/settings", {"sessionAllowWeb": True})
    check("일반 사용자 sessionAllowWeb → 403", st == 403, (st, h))
    st, h = admin("POST", BASE + "/api/settings", {"sessionAllowWeb": True})
    check("관리자 sessionAllowWeb 켜기 → sessionGlobal 에 true", st == 200 and h.get("sessionGlobal", {}).get("sessionAllowWeb") is True, (st, h.get("sessionGlobal")))
    st, a = admin("GET", BASE + "/api/agent")
    check("  관리자 /api/agent allowWeb=true · canAllowWeb=true", a.get("allowWeb") is True and a.get("canAllowWeb") is True, a)
    st, a = bob("GET", BASE + "/api/agent")
    check("  일반 사용자 /api/agent allowWeb=true · canAllowWeb=false", a.get("allowWeb") is True and a.get("canAllowWeb") is False, a)

    # 3) 세션 단위 - 일반 사용자 403, codex 400, 관리자 claude 성공 → 권한 JSON·하트비트·/api/home 배지
    st, s = bob("POST", BASE + "/api/project", {"action": "session", "op": "start", "path": str(ws), "agent": "claude", "model": "haiku", "allowWeb": True})
    check("일반 사용자 allowWeb 시작 → 거절(허브는 작업 공간 서버의 403 을 400 으로 전달)", st in (400, 403) and "관리자" in s.get("error", ""), (st, s))
    st, s = admin("POST", BASE + "/api/project", {"action": "session", "op": "start", "path": str(ws), "agent": "codex", "model": "x", "allowWeb": True})
    check("codex + allowWeb → 400(지원 안 함)", st == 400 and ("codex" in s.get("error", "") or "지원" in s.get("error", "")), (st, s))
    st, s = admin("POST", BASE + "/api/project", {"action": "session", "op": "start", "path": str(ws), "agent": "claude", "model": "haiku", "allowWeb": True})
    check("관리자 claude + allowWeb 시작 → ready · allowWeb true", st == 200 and s.get("state") == "ready" and s.get("allowWeb") is True, (st, s))
    cfg = json.loads((ws / "nexa-slide.json").read_text("utf-8"))
    sp = ws / cfg.get("out", "out") / ".studio" / "sessions" / "claude-settings.json"
    perms = json.loads(sp.read_text("utf-8"))["permissions"]
    check("  권한 JSON: WebSearch·WebFetch 가 allow 에, deny 에 없음", all(x in perms["allow"] for x in ("WebSearch", "WebFetch")) and not any(x in perms["deny"] for x in ("WebSearch", "WebFetch")), perms)
    check("  권한 JSON: curl·mcp__* 는 여전히 deny", "Bash(curl *)" in perms["deny"] and "mcp__*" in perms["deny"], perms["deny"])
    time.sleep(1.5)
    st, h = admin("GET", BASE + "/api/home")
    item = next(r for r in h["recent"] if r["path"] == str(ws))
    check("  /api/home session.allowWeb=true", item["session"].get("allowWeb") is True, item["session"])
    st, s = admin("POST", BASE + "/api/project", {"action": "session", "op": "stop", "path": str(ws)})
    check("  끊기 → off", st == 200 and s.get("state") == "off")
    # 허용 없이 시작하면 권한 JSON 은 원래대로
    st, s = admin("POST", BASE + "/api/project", {"action": "session", "op": "start", "path": str(ws), "agent": "claude", "model": "haiku"})
    perms = json.loads(sp.read_text("utf-8"))["permissions"]
    check("allowWeb 없이 시작 → allowWeb false · 권한 JSON 에 WebSearch deny", st == 200 and s.get("allowWeb") is False and "WebSearch" in perms["deny"] and "WebSearch" not in perms["allow"], (st, s.get("allowWeb"), perms))
    admin("POST", BASE + "/api/project", {"action": "session", "op": "stop", "path": str(ws)})

    # 4) 턴 명령·프롬프트(모듈 단위)
    sys.path.insert(0, str(STUDIO))
    import agents
    from agents.claude import ClaudeAgent
    c1 = ClaudeAgent().turn_cmd("haiku", flags={"--restricted": True}, allow_web=True)
    c0 = ClaudeAgent().turn_cmd("haiku", flags={"--restricted": True}, allow_web=False)
    check("turn_cmd --tools 에 WebFetch,WebSearch(허용) / 없음(기본)", "WebSearch" in c1[c1.index("--tools") + 1] and "WebSearch" not in c0[c0.index("--tools") + 1], (c1, c0))
    c2 = ClaudeAgent().turn_cmd("haiku", flags={"--restricted": False}, allow_web=True)
    check("  구판 --disallowedTools 에서 WebFetch·WebSearch 제외", "WebSearch" not in c2[c2.index("--disallowedTools") + 1], c2)
    tpl = (STUDIO / "agents" / "turn_prompt.md").read_text("utf-8")
    check("turn_prompt.md 에 {web} 자리", "{web}" in tpl)
    ws_perm = agents.web_settings(False)["permissions"]
    check("web_settings(False) 기본 deny 유지", "WebSearch" in ws_perm["deny"])

    # 5) 전역 끄기 → 다시 막힘, 접근 로그 이벤트
    st, h = admin("POST", BASE + "/api/settings", {"sessionAllowWeb": False})
    check("관리자 sessionAllowWeb 끄기 → sessionGlobal 에서 사라짐", st == 200 and "sessionAllowWeb" not in h.get("sessionGlobal", {}), h.get("sessionGlobal"))
    import datetime
    logf = USER / "hub" / "logs" / f"access-{datetime.date.today().isoformat()}.log"
    lines = [json.loads(l) for l in logf.read_text(encoding="utf-8").splitlines()[-400:] if l.startswith("{")]
    evs = [l.get("event") for l in lines if l.get("event")]
    check("접근 로그: settings.sessionAllowWeb:on/off · session.start:…:web", "settings.sessionAllowWeb:on" in evs and "settings.sessionAllowWeb:off" in evs and any(str(e).startswith("web.session.start:claude:haiku:web") for e in evs) and "session.start:nexa-slide-demo:web" in evs, evs[-12:])
finally:
    for w in started:
        print("  ", svc("stop", w).stdout.strip())
    print("  ", svc("stop").stdout.strip())
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
