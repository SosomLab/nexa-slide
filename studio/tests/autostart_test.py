# -*- coding: utf-8 -*-
"""허브 자동 시작(service.py autostart) 시험 - 이 PC 의 작업 스케줄러는 바꾸지 않는다(--dry-run·status·거절만).
on 이 만들 명령(로그온 시 실행·이 사용자·작업 폴더 = 사용자 폴더·service.py start) · worktree 엔진에서 켜기 거절 · 작업 공간 안에서 거절 · status 는 읽기만."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent / "service.py"
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def run(*args, env=None, cwd=None):
    e = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    e.pop("NEXA_SLIDE_WORKSPACE", None) if not (env or {}).get("NEXA_SLIDE_WORKSPACE") else None
    r = subprocess.run([sys.executable, str(SERVICE), "autostart", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=e, cwd=str(cwd or Path.home()))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    if os.name != "nt":
        code, out = run("on", "--dry-run")
        check("Windows 가 아니면 안내만(종료 1)", code == 1 and "launchd" in out, out)
    else:
        code, out = run("on", "--dry-run")
        check("on --dry-run - 로그온 시 실행·이 사용자·사용자 폴더·service.py start", code == 0 and "-AtLogOn -User $env:USERNAME" in out
              and "-WorkingDirectory $env:USERPROFILE" in out and "service.py\" start" in out and "Register-ScheduledTask -TaskName 'nexa-slide hub'" in out, out)
        code, out = run("off", "--dry-run")
        check("off --dry-run - 작업 지우기", code == 0 and "Unregister-ScheduledTask -TaskName 'nexa-slide hub'" in out, out)
        code, out = run("status")
        check("status - 읽기만(켜짐/꺼짐 한 줄)", code == 0 and out.startswith("자동 시작:"), out)
        if ".claude" in SERVICE.parts and "worktrees" in SERVICE.parts:
            code, out = run("on")
            check("worktree 엔진에서는 켜지 않는다", code == 1 and "worktree" in out, out)
    ws = Path(tempfile.mkdtemp(prefix="nexa-autostart-"))
    (ws / "nexa-slide.json").write_text("{}", encoding="utf-8")
    code, out = run("status", env={"NEXA_SLIDE_WORKSPACE": str(ws)}, cwd=ws)
    check("작업 공간 안에서는 거절(허브만)", code == 1 and "허브만" in out, out)
    print("\n실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
