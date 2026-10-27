# -*- coding: utf-8 -*-
"""0.22.27 - 엔진 세션 턴 뒤 처리(wsession EngineProfile/EngineQueueSource):
(a) 세션이 `status done --commit auto` 로 끝내면(Codex 는 .git 쓰기 불가) 허브가 worktree 변경을 대신 커밋하고 큐에 해시를 적는다 · 변경이 없으면 커밋하지 않는다
(b) 세션이 스스로 open 으로 되돌린 항목은 큐가 다시 보내지 않는다(무한 반복 방지) · 사람이 reply 를 고치면(updated 변화) 다시 보낸다
(c) working 이 남은 항목은 그대로 다시 받는다. 격리: NEXA_SLIDE_USER_DIR(큐) · 임시 git 저장소+worktree(EngineProfile 의 cwd/engine 을 바꿔 끼움) · NEXA_SLIDE_WORKSPACE 는 example 사본."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
ROOT = WORK / "engcommit"


def _onerr(fn, p, exc):
    try:
        os.chmod(p, 0o700); fn(p)
    except OSError:
        pass


if ROOT.exists():
    shutil.rmtree(ROOT, onerror=_onerr)
USER, WS, REPO, WT = ROOT / "user", ROOT / "ws", ROOT / "repo", ROOT / "wt"
USER.mkdir(parents=True)
shutil.copytree(STUDIO.parent / "example", WS)
os.environ["NEXA_SLIDE_USER_DIR"] = str(USER)
os.environ["NEXA_SLIDE_WORKSPACE"] = str(WS)
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, str(STUDIO))
import engine_requests as q  # noqa: E402
import wsession  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")


events = []


def emit(kind, **kw):
    events.append((kind, kw))


# 임시 저장소 + worktree(engine-dev 흉내)
REPO.mkdir()
git("init", "-q", cwd=REPO)
(REPO / "a.txt").write_text("a\n", encoding="utf-8")
git("add", "-A", cwd=REPO); git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "init", cwd=REPO)
git("worktree", "add", "-q", str(WT), "-b", "engine-dev", cwd=REPO)
prof = wsession.EngineProfile()
prof.engine, prof.cwd = REPO, WT

# (a) done --commit auto → 허브가 커밋
it = q.add("허브 커밋 시험", "본문", kind="cli")
q.update(it["id"], status="working", by="engine-session")
(WT / "studio_change.txt").write_text("세션이 고친 파일\n", encoding="utf-8")
q.update(it["id"], status="done", by="engine-session", commit="auto", reply="고쳤다")
x = q.get(it["id"])
check("--commit auto 는 큐에 'auto' 로 저장되지 않음", not x.get("commit"), x.get("commit"))
unhandled = prof.reconcile([x], {"ok": True, "text": ""}, 0, emit)
x = q.get(it["id"])
head = git("rev-parse", "--short", "HEAD", cwd=WT).stdout.strip()
check("허브가 worktree 변경을 커밋하고 해시를 적음", x.get("commit") == head and x.get("branch") == "engine-dev" and unhandled == [], (x.get("commit"), head, unhandled))
log = git("log", "-1", "--pretty=%s%n%b", cwd=WT).stdout
check("  커밋 메시지에 engine-request #n · Co-Authored-By", f"engine-request #{it['id']}" in log and "Co-Authored-By" in log, log[:200])
check("  worktree 깨끗", not git("status", "--porcelain", cwd=WT).stdout.strip())
check("  main 브랜치는 그대로", git("rev-parse", "--short", "HEAD", cwd=REPO).stdout.strip() != head)
# 변경 없이 done(commit 없음) → 커밋 없음, 해시도 없음
it2 = q.add("변경 없음", "", kind="cli")
q.update(it2["id"], status="working", by="engine-session"); q.update(it2["id"], status="done", by="engine-session", reply="할 것 없음")
prof.reconcile([q.get(it2["id"])], {"ok": True, "text": ""}, 0, emit)
check("변경이 없으면 커밋하지 않음", q.get(it2["id"]).get("commit") is None and git("rev-parse", "--short", "HEAD", cwd=WT).stdout.strip() == head)

# (b) 세션이 open 으로 되돌린 항목은 다시 보내지 않는다
src = wsession.EngineQueueSource()
it3 = q.add("질문 있음", "", kind="cli")
q.update(it3["id"], status="working", by="engine-session")
q.update(it3["id"], status="open", by="engine-session", reply="어느 레이아웃인가요?")
batch, _ = src.poll()
check("세션이 되돌린 open 은 poll 이 건너뜀", batch is None, str(batch)[:200])
q.update(it3["id"], by="admin", reply="어느 레이아웃인가요?\n→ cover 입니다")  # 사람이 답을 적음 → updated 변화
batch, reason = src.poll()
check("사람이 손대면 다시 보냄(working 으로)", batch and batch[0]["id"] == it3["id"] and batch[0]["status"] == "working" and reason == "queue", str(batch)[:200])
# (c) working 이 남은 것은 그대로 다시 받는다 · 다른 open 이 있으면 되돌린 것 대신 그것
q.update(it3["id"], status="open", by="engine-session", reply="또 질문")
it4 = q.add("다른 요청", "", kind="cli")
batch, _ = src.poll()
check("되돌린 항목이 있어도 다른 open 요청은 받는다", batch and batch[0]["id"] == it4["id"], str(batch)[:200])
batch, _ = src.poll()
check("working 이 남아 있으면 그것부터(같은 항목)", batch and batch[0]["id"] == it4["id"] and batch[0]["status"] == "working")

# (d) 세션이 끊긴 채 남은 working 은 새 세션 시작(check_start) 때 open 으로 되돌리고 새 세션이 받는다(awaiting 아님)
it5 = q.add("끊긴 세션이 남긴 것", "", kind="cli")
q.update(it5["id"], status="working", by="engine-session")
q.update(it4["id"], status="done", by="engine-session", reply="끝")
prof.check_start()
x5 = q.get(it5["id"])
check("check_start 가 고아 working → open(+안내) · awaiting 아님", x5["status"] == "open" and "끊겨" in (x5.get("reply") or "") and not x5.get("awaiting"), str(x5)[:200])
batch, _ = src.poll()
check("  새 세션이 바로 받는다", batch and batch[0]["id"] == it5["id"] and batch[0]["status"] == "working", str(batch)[:120])
# (e) 세션의 status 는 .nexa/outbox 에 적히고 허브가 턴 끝에 반영한다 - 실행 파일(shim)부터 실제로 돌린다
shim = WT / ".nexa" / "engine_request.py"
check("check_start 가 worktree 에 shim·outbox 를 둔다", shim.is_file() and (WT / ".nexa" / "outbox").is_dir())
(WT / "fix2.txt").write_text("둘째 수정\n", encoding="utf-8")
r = subprocess.run([sys.executable, str(shim), "status", str(it5["id"]), "done", "--by", "engine-session", "--commit", "auto", "--test", "py_compile", "--reply", "고쳤다 - 허브 커밋"],
                   cwd=str(WT), capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ})
box = sorted((WT / ".nexa" / "outbox").glob("*.json"))
check("shim status → outbox 파일 1개 · 큐는 아직 working", r.returncode == 0 and "턴 끝" in r.stdout and len(box) == 1 and q.get(it5["id"])["status"] == "working", r.stdout + r.stderr + str(box))
prof.reconcile([q.get(it5["id"])], {"ok": True, "text": ""}, 0, emit)
x5 = q.get(it5["id"])
head2 = git("rev-parse", "--short", "HEAD", cwd=WT).stdout.strip()
check("reconcile 이 outbox 를 반영(done·reply·test) 하고 허브가 커밋해 해시를 적음", x5["status"] == "done" and x5.get("reply") == "고쳤다 - 허브 커밋" and x5.get("test") == "py_compile" and x5.get("commit") == head2 and head2 != head, str(x5)[:300])
check("  outbox 비움", not list((WT / ".nexa" / "outbox").glob("*.json")))
r = subprocess.run([sys.executable, str(shim), "list"], cwd=str(WT), capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ})
check("shim 의 다른 명령(list)은 그대로 CLI 로", r.returncode == 0 and "끊긴 세션이 남긴 것" in r.stdout, r.stdout[-200:] + r.stderr[-200:])

# (f) 턴 직전 main 따라잡기(sync_main) - 뒤처졌으면 받는다: 배포 안 한 커밋이 있으면 병합, 없으면 ff, 커밋 안 한 변경·충돌이면 손대지 않음
def main_commit(name, text):
    (REPO / name).write_text(text, encoding="utf-8")
    git("add", "-A", cwd=REPO); git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", f"main {name}", cwd=REPO)


check("뒤처지지 않았으면 할 일 없음", prof.sync_main() == (True, ""))
main_commit("m1.txt", "main 새 파일\n")
(WT / "wip.txt").write_text("작업 중\n", encoding="utf-8"); git("add", "wip.txt", cwd=WT)
ok, msg = prof.sync_main()
check("커밋 안 한 변경이 있으면 손대지 않음", not ok and "커밋하지 않은 변경" in msg and not (WT / "m1.txt").exists(), msg)
git("reset", "-q", "--hard", cwd=WT)
ok, msg = prof.sync_main()
check("배포 안 한 커밋이 있으면 main 을 병합", ok and "맞췄다" in msg and "배포 안 한 커밋" in msg and (WT / "m1.txt").is_file()
      and not git("rev-list", "engine-dev..main", cwd=REPO).stdout.strip(), msg)
git("reset", "-q", "--hard", "main", cwd=WT)  # 배포가 끝난 상태(engine-dev = main)
main_commit("m2.txt", "또\n")
ok, msg = prof.sync_main()
check("배포 안 한 커밋이 없으면 fast-forward", ok and git("rev-parse", "HEAD", cwd=WT).stdout == git("rev-parse", "main", cwd=REPO).stdout, msg)
(WT / "m2.txt").write_text("engine-dev 쪽\n", encoding="utf-8"); git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qam", "dev m2", cwd=WT)
main_commit("m2.txt", "main 쪽\n")
ok, msg = prof.sync_main()
check("충돌이면 되돌리고 그대로(경고)", not ok and "충돌" in msg and not git("status", "--porcelain", "--untracked-files=no", cwd=WT).stdout.strip()
      and (WT / "m2.txt").read_text(encoding="utf-8") == "engine-dev 쪽\n", msg)
batch = [q.add("따라잡기 알림", "", kind="cli")]
git("reset", "-q", "--hard", "main", cwd=WT); main_commit("m3.txt", "셋\n")
seen = []
prof.prompt(batch, "queue", type("S", (), {"emit": lambda self, k, **kw: seen.append((k, kw))})(), type("A", (), {"shell_note": "", "engine_commit_note": ""})())
check("prompt(턴 직전)가 따라잡고 세션 로그에 알림", any(k == "text" and "맞췄다" in kw.get("text", "") for k, kw in seen) and (WT / "m3.txt").is_file(), seen)

print("\n실패:", ", ".join(FAILS) if FAILS else "없음")
sys.exit(1 if FAILS else 0)
