# -*- coding: utf-8 -*-
"""C-3 검증 - 웹 세션 git 허용(git·push·root): 저장소(루트에 작업일지, 작업 공간은 slides/, bare 원격) 를 만들고
전역 스위치 켬 → 세션 시작(grants) → 권한 JSON 확인 → 실제 claude 턴으로 "루트 작업일지에 줄 추가 + commit + push" → 원격 로그·트레일러 확인.
거절 경로(전역 꺼짐·codex·저장소 아님)도 본다."""
import json
import os
import tempfile
import shutil
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
USER, PROJ = WORK / "user", WORK / "projects"
REPO, REMOTE = PROJ / "git시험", PROJ / "git시험-remote.git"
WS = REPO / "slides"
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")


# 저장소 준비 - 작업 공간은 중계시험-2 의 slides 를 복사
for p in (REPO, REMOTE):
    shutil.rmtree(p, ignore_errors=True)
def ensure_ws(ws, port):  # 시험용 작업 공간(저장소형 <상위>/slides)이 없으면 init_workspace 로 만들고, 덱이 없으면 시작용 덱을 빌드한다
    if not (ws / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(ws.parent), "--title", "중계시험", "--port", str(port)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    if not list((ws / "decks").glob("*.json")):
        subprocess.run([sys.executable, str(STUDIO / "build_deck.py"), "intro", "--force"], env={**ENV, "NEXA_SLIDE_WORKSPACE": str(ws)}, cwd=str(ws), capture_output=True, text=True, encoding="utf-8")


ensure_ws(PROJ / "중계시험-2" / "slides", 5654)
shutil.copytree(PROJ / "중계시험-2" / "slides", WS, ignore=shutil.ignore_patterns("out", "*.requests.json", ".history"))
cfg = json.loads((WS / "nexa-slide.json").read_text("utf-8")); cfg["port"] = 5660
(WS / "nexa-slide.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), "utf-8")
(REPO / "작업일지.md").write_text("# 작업일지\n\n- 2026-10-14 저장소 만듦\n", "utf-8")
(REPO / ".gitignore").write_text("slides/out/\n", "utf-8")
subprocess.run(["git", "init", "--bare", "-b", "main", str(REMOTE)], capture_output=True)
git("init", "-b", "main"); git("config", "user.name", "시험 사용자"); git("config", "user.email", "test@example.invalid")
git("add", "-A"); git("commit", "-qm", "init"); git("remote", "add", "origin", str(REMOTE)); git("push", "-q", "-u", "origin", "main")
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
settings = json.loads((USER / "settings.json").read_text("utf-8"))
for k in ("sessionAllowGit", "sessionAllowPush", "sessionRepoRoot", "sessionAllowWeb"):
    settings.pop(k, None)
(USER / "settings.json").write_text(json.dumps(settings), "utf-8")


def svc(*a):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), *a], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8")


print(svc("start").stdout.strip())
try:
    base = json.loads((WS / "out" / ".studio" / "server.json").read_text("utf-8"))["url"].rstrip("/")

    def req(method, path, body=None, timeout=60):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=timeout) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    st, a = req("GET", "/api/agent")
    check("전역 꺼짐: grants 모두 false · canGrant(로컬 직접) true", a.get("grants") == {"web": False, "git": False, "push": False, "root": False} and a.get("canGrant") is True, (a.get("grants"), a.get("canGrant")))
    st, s = req("POST", "/api/wsession", {"action": "start", "agent": "claude", "model": "sonnet", "grants": ["git"]})
    check("전역 꺼짐 + git → 400", st == 400 and "전역" in s.get("error", ""), (st, s))
    settings.update({"sessionAllowGit": True, "sessionAllowPush": True, "sessionRepoRoot": True})
    (USER / "settings.json").write_text(json.dumps(settings), "utf-8")
    st, a = req("GET", "/api/agent")
    check("전역 켬 → grants git·push·root true", all(a["grants"][k] for k in ("git", "push", "root")), a["grants"])
    st, s = req("POST", "/api/wsession", {"action": "start", "agent": "codex", "model": "x", "grants": ["git"]})
    check("codex + git → 400", st == 400, (st, s))
    st, s = req("POST", "/api/wsession", {"action": "start", "agent": "claude", "model": "sonnet", "grants": ["push", "root"]})
    check("시작(push·root) → grants 에 git 자동 포함 · repoRoot = 저장소 루트", st == 200 and s.get("grants") == ["git", "push", "root"] and Path(s.get("repoRoot") or "").resolve() == REPO.resolve(), (st, s.get("grants"), s.get("repoRoot")))
    perms = json.loads((WS / "out" / ".studio" / "sessions" / "claude-settings.json").read_text("utf-8"))["permissions"]
    check("  권한: git commit·push allow, 강제 push·reset --hard·-C·config deny", "Bash(git commit *)" in perms["allow"] and "Bash(git push*)" in perms["allow"] and all(x in perms["deny"] for x in ("Bash(git push --force*)", "Bash(git reset --hard*)", "Bash(git -C *)", "Bash(git config*)")), perms)
    check("  권한: 루트 Edit allow · .git Edit deny", any(x.startswith("Edit(//") and x.endswith("/**)") and ".git" not in x for x in perms["allow"]) and any(".git/**" in x for x in perms["deny"]), [x for x in perms["allow"] + perms["deny"] if x.startswith(("Edit", "Write", "Read"))])
    import sys as _s
    _s.path.insert(0, str(STUDIO))
    from agents.claude import ClaudeAgent
    cmd = ClaudeAgent().turn_cmd("sonnet", flags={"--restricted": True}, add_dirs=[REPO])
    check("  turn_cmd 에 --add-dir <루트>", "--add-dir" in cmd and str(REPO) in cmd)

    # 실제 턴
    st, decks = req("GET", "/api/decks")
    did = decks[0]["id"]
    st, deck = req("GET", f"/api/deck/{did}")
    sid = deck["slides"][0]["id"]
    text = ("슬라이드는 고치지 말고 저장소 작업만 해 줘: 저장소 루트의 작업일지.md 맨 끝에 '- 2026-10-14 웹 세션 git 시험' 한 줄을 덧붙이고, "
            "그 파일을 git add·commit(메시지: 'docs: 작업일지 - 웹 세션 git 시험') 한 뒤 origin main 으로 push 해 줘.")
    req("POST", f"/api/requests/{did}", {"action": "add", "status": "open", "slide": sid, "text": text})
    req("POST", f"/api/flush/{did}")
    t0 = time.time()
    while time.time() - t0 < 420:
        time.sleep(5)
        st, info = req("GET", "/api/wsession")
        st2, rs = req("GET", f"/api/requests/{did}")
        r = rs[-1]
        if info.get("state") == "ready" and info.get("turns", 0) >= 1 and r.get("status") in ("done", "open") and r.get("reply"):
            break
    print(f"   턴 결과: {int(time.time() - t0)}초 · status={r.get('status')} · reply={r.get('reply', '')[:300]}")
    log = (REPO / "작업일지.md").read_text("utf-8")
    check("실제 턴: 루트 작업일지.md 에 줄 추가(작업 공간 밖 쓰기)", "웹 세션 git 시험" in log, log)
    rl = git("log", "-1", "--format=%s%n%an%n%b", "main", cwd=REMOTE)
    check("  원격(bare) main 최신 커밋 = 요청한 메시지 · 작성자 = PC git 사용자", rl.stdout.startswith("docs: 작업일지 - 웹 세션 git 시험") and "시험 사용자" in rl.stdout, rl.stdout + rl.stderr)
    check("  커밋 메시지에 Requested-by 트레일러", "Requested-by:" in rl.stdout, rl.stdout)
    check("  요청 done", r.get("status") == "done", r)
    st, s = req("POST", "/api/wsession", {"action": "stop"})
finally:
    req("POST", "/api/wsession", {"action": "stop"}) if "base" in dir() else None
    print("  ", svc("stop").stdout.strip())
    for k in ("sessionAllowGit", "sessionAllowPush", "sessionRepoRoot"):
        settings.pop(k, None)
    (USER / "settings.json").write_text(json.dumps(settings), "utf-8")
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
