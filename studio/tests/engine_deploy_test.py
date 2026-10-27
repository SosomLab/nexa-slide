# -*- coding: utf-8 -*-
"""엔진 배포(studio/engine_deploy.py) - 0.22.29. 임시 저장소(엔진 사본 + bare origin)와 격리된 사용자 설정 폴더에서:
계획(커밋·요청·막는 이유) · 배포(--no-tests --no-restart: 병합 커밋·push·적용됨·engine-dev 맞춤) · 충돌이면 main 불변 ·
커밋하지 않은 변경이 겹치면 막음 · 시험 비교(원래 있던 실패는 통과, 새 실패는 막음). 실제 허브 재시작·운영 원격 push 는 하지 않는다."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests") / "engine-deploy"
shutil.rmtree(WORK, ignore_errors=True)
USER, ORIGIN, ENG = WORK / "user", WORK / "origin.git", WORK / "engine"
USER.mkdir(parents=True)
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "PYTHONIOENCODING": "utf-8", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
for k in ("NEXA_SLIDE_WORKSPACE", "NEXA_SLIDE_SESSION", "NEXA_SLIDE_USER"):
    ENV.pop(k, None)
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def git(*args, cwd=ENG):
    r = subprocess.run(["git", *args], cwd=str(cwd), env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip() if r.returncode == 0 else "ERR " + (r.stderr or r.stdout or "").strip()


def deploy(*args):
    r = subprocess.run([sys.executable, str(ENG / "studio" / "engine_deploy.py"), *args], cwd=str(ENG), env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def plan():
    code, out = deploy("plan")
    return json.loads(out) if code == 0 else {"error": out}


def req(*args):
    r = subprocess.run([sys.executable, str(ENG / "studio" / "engine_request.py"), *args], env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def queue(rid):
    return json.loads(req("show", str(rid)) or "{}")


def dev_commit(path, text, msg):
    wt = ENG / ".claude" / "worktrees" / "engine-dev"
    (wt / path).write_text(text, encoding="utf-8", newline="\n")
    git("add", path, cwd=wt)
    return git("commit", "-q", "-m", msg, cwd=wt)


# 엔진 사본 - studio(시험 제외)·CHANGELOG 만, main 에서 시작해 bare origin 에 올린다
shutil.copytree(SRC / "studio", ENG / "studio", ignore=shutil.ignore_patterns("tests", "__pycache__", "i18n", "templates", "*.html", "*.js"))
shutil.copy(SRC / "CHANGELOG.md", ENG / "CHANGELOG.md")
(ENG / ".gitignore").write_text(".claude/\n__pycache__/\n", encoding="utf-8")
(ENG / "note.txt").write_text("a\nb\nc\n", encoding="utf-8")
git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-q", "-m", "init")
subprocess.run(["git", "init", "-q", "--bare", str(ORIGIN)], env=ENV, capture_output=True)
git("remote", "add", "origin", str(ORIGIN))
git("push", "-q", "origin", "main")
git("worktree", "add", "-q", "-b", "engine-dev", str(ENG / ".claude" / "worktrees" / "engine-dev"), "main")

# (a) 앞선 커밋이 없으면 막는다
p = plan()
check("(a) 커밋 없음 → 막음", not p.get("ok") and any("앞선 커밋이 없다" in b for b in p.get("blockers", [])), json.dumps(p, ensure_ascii=False)[:300])

# (b) 요청 #1 처리(done) + engine-dev 커밋 → 계획 → 배포
req("add", "--title", "새 파일 추가", "--body", "x", "--kind", "cli")
c1 = dev_commit("added.txt", "hello\n", "feat: 새 파일 (engine-request #1)")
h1 = git("rev-parse", "--short", "engine-dev")
for st in ("working", "done"):
    req("status", "1", st, "--commit", h1)
p = plan()
check("(b) 계획: 커밋 1 · 요청 #1 · 막는 이유 없음", p.get("ok") and len(p.get("commits", [])) == 1 and [r["id"] for r in p.get("requests", [])] == [1] and p.get("files") == ["added.txt"],
      json.dumps(p, ensure_ascii=False)[:400])
prev = git("rev-parse", "main")
code, out = deploy("run", "--by", "admin1", "--no-tests", "--no-restart")
st = json.loads(deploy("status")[1])
check("(b) 배포 성공(state ok)", code == 0 and st.get("state") == "ok", out[-600:])
head = git("rev-parse", "main")
parents = git("rev-list", "--parents", "-n", "1", "main").split()
check("(b) main = --no-ff 병합 커밋(부모 2: 이전 main · engine-dev)", len(parents) == 3 and parents[1] == prev, " ".join(parents))
body = git("log", "-1", "--format=%B", "main")
check("(b) 병합 메시지: 요청 제목·#1·Deployed-by", "새 파일 추가" in body and "engine-request #1" in body and "Deployed-by: admin1" in body, body)
check("(b) origin/main 에 push", git("rev-parse", "main", cwd=ORIGIN) == head)
q = queue(1)
check("(b) #1 applied · appliedCommit = 병합 커밋 · engineVersion", q.get("status") == "applied" and q.get("appliedCommit") == head[:7] and q.get("engineVersion"), json.dumps(q, ensure_ascii=False)[:300])
check("(b) engine-dev 를 main 으로 맞춤", git("rev-parse", "engine-dev") == head)
check("(b) 시험용 worktree 정리", not (ENG / ".claude" / "worktrees" / "deploy-merge").exists())
check("(b) 단계 기록(확인·병합·main 반영·push·적용됨 표시)", [s["step"] for s in st.get("steps", [])][:5] == ["확인", "병합", "시험", "main 반영", "push"], [s["step"] for s in st.get("steps", [])])

# (c) 충돌 - 같은 줄을 main 과 engine-dev 가 다르게 고침 → 실패, main 불변
dev_commit("note.txt", "a\nDEV\nc\n", "fix: note (engine-request #2)")
(ENG / "note.txt").write_text("a\nMAIN\nc\n", encoding="utf-8")
git("commit", "-q", "-am", "main 쪽 수정")
git("push", "-q", "origin", "main")
before = git("rev-parse", "main")
code, out = deploy("run", "--by", "admin1", "--no-tests", "--no-restart")
st = json.loads(deploy("status")[1])
check("(c) 충돌 → failed · main 불변", code != 0 and st.get("state") == "failed" and "충돌" in st.get("message", "") and git("rev-parse", "main") == before, out[-400:])
git("reset", "-q", "--hard", "HEAD~1", cwd=ENG / ".claude" / "worktrees" / "engine-dev")

# (d) 운영 트리의 커밋하지 않은 변경이 병합할 파일과 겹치면 막는다
dev_commit("note.txt", "a\nMAIN\nc\nDEV\n", "fix: note 끝 줄")
(ENG / "note.txt").write_text("a\nMAIN\nc\nlocal\n", encoding="utf-8")
p = plan()
check("(d) 겹치는 미커밋 변경 → 막음", not p.get("ok") and any("겹친다" in b for b in p.get("blockers", [])), p.get("blockers"))
git("checkout", "--", "note.txt")

# (e) 시험 비교 - 병합본 실패 묶음을 병합 전에서도 다시 돌려 원래 있던 실패면 통과, 새 실패면 막는다(run_all 대신 가짜)
helper = WORK / "fake_tests.py"
helper.write_text(f'''import sys
sys.path.insert(0, {str(ENG / "studio")!r})
import engine_deploy as d
mode = sys.argv[1]
def fake(self, root, names=()):
    if root.name == "deploy-merge":
        return ["smoke", "share"] if mode == "new" else ["smoke"]
    return ["smoke"]
d.Run._run_tests = fake
sys.exit(d.Run("admin1", tests=True, restart=False, push=False).run())
''', encoding="utf-8")
before = git("rev-parse", "main")
r = subprocess.run([sys.executable, str(helper), "new"], env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
st = json.loads(deploy("status")[1])
check("(e) 새 실패(share) → 막음 · main 불변", r.returncode != 0 and "share" in st.get("message", "") and "smoke" not in st.get("message", "") and git("rev-parse", "main") == before, st.get("message"))
r = subprocess.run([sys.executable, str(helper), "old"], env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
st = json.loads(deploy("status")[1])
check("(e) 원래 있던 실패만(smoke) → 통과 · main 이동 · push 안 함(--no-push)", r.returncode == 0 and git("rev-parse", "main") != before and git("rev-parse", "main", cwd=ORIGIN) == before,
      (r.stdout + r.stderr)[-400:])

shutil.rmtree(WORK, ignore_errors=True)
print("\n전부 통과" if not FAILS else f"\n실패: {FAILS}")
sys.exit(1 if FAILS else 0)
