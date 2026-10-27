# -*- coding: utf-8 -*-
"""엔진 요청 CLI(studio/engine_request.py) - 0.22.24 (엔진 요청 #5).
--body-file(파일·표준 입력)로 여러 줄·< > | & 가 든 본문이 그대로 저장되는가, 래퍼에 잘린 값("|| goto :error")은 거부하는가,
status applied --applied-commit 이 appliedCommit 에 들어가는가, --reply-file. 격리된 사용자 설정 폴더에서 python.exe 를 직접 부른다(pyenv 래퍼를 거치지 않음)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER = WORK / "engine-request-cli" / "user"
shutil.rmtree(USER.parent, ignore_errors=True)
USER.mkdir(parents=True)
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "PYTHONIOENCODING": "utf-8"}
for k in ("NEXA_SLIDE_WORKSPACE", "NEXA_SLIDE_SESSION", "NEXA_SLIDE_USER"):
    ENV.pop(k, None)
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def cli(*args, inp=None):
    return subprocess.run([sys.executable, str(STUDIO / "engine_request.py"), *args], env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", input=inp)


def show(rid):
    r = cli("show", str(rid))
    return json.loads(r.stdout) if r.returncode == 0 else {}


BODY = "첫 줄\n둘째 줄: a < b > c | d & e\n\n셋째 줄 `--allow <덱>[:<장>]`\n"
f = USER / "body.md"
f.write_text(BODY, encoding="utf-8")
r = cli("add", "--title", "본문 파일", "--body-file", str(f), "--kind", "cli")
check("add --body-file → open", r.returncode == 0 and "#1 (open)" in r.stdout, r.stdout + r.stderr)
check("여러 줄·< > | & 본문이 그대로 저장", show(1).get("body") == BODY, repr(show(1).get("body"))[:200])

r = cli("add", "--title", "표준 입력", "--body-file", "-", "--kind", "cli", inp=BODY)
check("add --body-file - (stdin)", r.returncode == 0 and show(2).get("body") == BODY, r.stderr[-200:])

r = cli("add", "--title", "잘린 본문", "--body", "설계 메모: docs/dev/x.md ||  goto :error", "--kind", "cli")
check("래퍼에 잘린 --body 는 거부(종료 1·안내)", r.returncode != 0 and "goto :error" in (r.stderr + r.stdout) and "--body-file" in (r.stderr + r.stdout), r.stdout + r.stderr)
check("거부된 요청은 저장되지 않음", not show(3))

for st in ("working", "done"):
    cli("status", "1", st, "--by", "t", *(("--commit", "abc1234") if st == "done" else ()))
r = cli("status", "1", "applied", "--applied-commit", "def5678", "--by", "admin")
x = show(1)
check("status applied --applied-commit → appliedCommit", r.returncode == 0 and x.get("appliedCommit") == "def5678" and x.get("commit") == "abc1234", json.dumps(x, ensure_ascii=False)[:300])
cli("status", "2", "working", "--by", "t")
rf = USER / "reply.md"
rf.write_text("답 1줄\n답 2줄 <x>\n", encoding="utf-8")
r = cli("status", "2", "done", "--by", "t", "--commit", "aaa", "--reply-file", str(rf))
check("status --reply-file", r.returncode == 0 and show(2).get("reply") == "답 1줄\n답 2줄 <x>\n", r.stderr[-200:])
r = cli("status", "2", "applied", "--commit", "bbb", "--by", "admin")
check("applied 의 옛 --commit 도 appliedCommit 으로(처리 커밋 보존)", show(2).get("appliedCommit") == "bbb" and show(2).get("commit") == "aaa")
r = cli("status", "2", "open", "--reply", "x || goto :error", "--by", "t")
check("잘린 --reply 도 거부", r.returncode != 0)

print("\n실패:", ", ".join(FAILS) if FAILS else "없음")
sys.exit(1 if FAILS else 0)
