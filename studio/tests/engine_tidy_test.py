# -*- coding: utf-8 -*-
"""엔진 개발 영역 정리(studio/engine_tidy.py) 시험 - 시험용 사용자 설정 폴더(NEXA_SLIDE_USER_DIR)에 큐·첨부·회귀 사본·임시 파일·로그를 심고,
worktree 자리는 임시 폴더로 바꿔 끼워 scan 보고(남길 것은 빠지는지) → clean(고른 범주만) → 배포 중이면 로그·worktree 를 건너뛰는지 확인한다."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(tempfile.mkdtemp(prefix="nexa-engine-tidy-"))
os.environ["NEXA_SLIDE_USER_DIR"] = str(WORK / "user")
sys.path.insert(0, str(STUDIO))
import engine_requests  # noqa: E402
import engine_tidy as et  # noqa: E402
FAILS = []
OLD = time.time() - 2 * 3600


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def put(p, text="x", old=True):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if old:
        os.utime(p, (OLD, OLD))
    return p


def old_dir(p):
    p.mkdir(parents=True, exist_ok=True)
    put(p / "a.txt")
    os.utime(p, (OLD, OLD))
    return p


E = engine_requests.ENGINE_DIR
check("격리된 사용자 설정 폴더", str(E).startswith(str(WORK)), E)
et.WORKTREES = WORK / "worktrees"
et.WORKTREE = et.WORKTREES / "engine-dev"
# 큐: #1 open(첨부·사본 남김), #2 done(사본만 지움) - 첨부 #9 는 큐에 없음
engine_requests.add("열린 요청", kind="cli")
engine_requests.add("끝난 요청", kind="cli")
engine_requests.update(2, status="working", by="t"); engine_requests.update(2, status="done", by="t")
put(E / "attach" / "1" / "a.png"); put(E / "attach" / "9" / "b.png"); os.utime(put(E / "attach" / "_new" / "c.png"), (OLD - 86400, OLD - 86400)); put(E / "attach" / "_new" / "fresh.png", old=False)
put(et.WORKTREE / ".nexa" / "attach" / "1" / "a.png"); put(et.WORKTREE / ".nexa" / "attach" / "2" / "a.png")
put(et.WORKTREE / ".nexa" / "outbox" / "2-1.json")
old_dir(E / "scratch" / "regress-20261001-000000"); (E / "scratch" / "regress-now").mkdir(parents=True)
old_dir(E / "scratch" / "engine-abc1234"); put(E / "scratch" / "engine-def5678.zip")
put(E / "requests.123.tmp"); put(E / "deploy.456.tmp", old=False)
for i in range(12):
    old_dir(E / ".studio" / "sessions" / f"202610{i + 10:02d}-000000")
for i in range(22):
    put(E / "deploy-logs" / f"202610{i + 1:02d}-000000.log")
old_dir(et.WORKTREES / "deploy-merge")

rep = et.scan()
paths = {Path(i["path"]).relative_to(WORK).as_posix(): i["category"] for i in rep["items"]}
print(json.dumps(sorted(paths), ensure_ascii=False))
check("고아 첨부: 큐에 없는 #9 · 하루 지난 _new", paths.get("user/hub/engine/attach/9") == "attach" and "user/hub/engine/attach/_new/c.png" in paths, paths)
check("  열린 요청 첨부·새로 올린 _new 는 남김", "user/hub/engine/attach/1" not in paths and "user/hub/engine/attach/_new/fresh.png" not in paths)
check("worktree 사본: 끝난 #2 만", paths.get("worktrees/engine-dev/.nexa/attach/2") == "copy" and "worktrees/engine-dev/.nexa/attach/1" not in paths)
check("  .nexa/outbox 는 손대지 않음", not any("outbox" in p for p in paths))
check("회귀 사본·남은 zip·오래된 tmp", all(paths.get(p) == "scratch" for p in ("user/hub/engine/scratch/regress-20261001-000000", "user/hub/engine/scratch/engine-def5678.zip", "user/hub/engine/requests.123.tmp")), paths)
check("  새 regress·기준 엔진 사본·새 tmp·requests.json 은 남김", not any(p.endswith(("regress-now", "engine-abc1234", "deploy.456.tmp", "requests.json")) for p in paths))
logs = [p for p, c in paths.items() if c == "log"]
check("로그: 세션 12-10=2 · 배포 22-20=2, 오래된 것부터", len(logs) == 4 and "user/hub/engine/.studio/sessions/20261010-000000" in paths and "user/hub/engine/deploy-logs/20261001-000000.log" in paths, logs)
check("시험용 worktree", paths.get("worktrees/deploy-merge") == "worktree")
check("기본 범주에 로그 없음", "log" not in rep["defaults"] and rep["order"] == list(et.CATEGORIES))

r = et.clean(["attach", "copy", "scratch"])
check("clean: 고른 범주만 지움", r["moved"] == 6 and not (E / "attach" / "9").exists() and not (et.WORKTREE / ".nexa" / "attach" / "2").exists()
      and not (E / "scratch" / "regress-20261001-000000").exists(), r)
check("  남길 것은 그대로", (E / "attach" / "1" / "a.png").is_file() and (et.WORKTREE / ".nexa" / "attach" / "1").is_dir() and (E / "scratch" / "engine-abc1234").is_dir()
      and (E / "requests.json").is_file() and (E / ".studio" / "sessions" / "20261010-000000").is_dir() and (et.WORKTREES / "deploy-merge").is_dir())
check("  보고가 갱신됨", {i["category"] for i in r["report"]["items"]} == {"log", "worktree"}, r["report"]["summary"])

(E / "deploy.json").write_text(json.dumps({"state": "running", "pid": os.getpid()}), encoding="utf-8")
rep = et.scan()
check("배포 중: 배포 로그·worktree 건너뜀", rep["deploying"] and rep["summary"]["worktree"]["count"] == 0 and not any("deploy-logs" in i["path"] for i in rep["items"]), rep["summary"])
(E / "deploy.json").write_text(json.dumps({"state": "ok"}), encoding="utf-8")
r = et.clean(["log", "worktree"])
check("clean: 로그·worktree", r["moved"] == 5 and not (et.WORKTREES / "deploy-merge").exists() and len(list((E / "deploy-logs").glob("*.log"))) == 20, r)

print("\n실패:", FAILS if FAILS else "없음")
sys.exit(1 if FAILS else 0)
