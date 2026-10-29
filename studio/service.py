# -*- coding: utf-8 -*-
"""작업 공간 서비스 관리 — 서버를 백그라운드로 띄우고/멈추고/상태를 본다.

    python3 studio/service.py --workspace <작업 공간> start     # 백그라운드 실행(이미 떠 있으면 그대로 알림)
    python3 studio/service.py --workspace <작업 공간> stop      # 이 작업 공간 서버만 종료
    python3 studio/service.py --workspace <작업 공간> restart
    python3 studio/service.py --workspace <작업 공간> status    # status.py 와 같음
    python3 studio/service.py --workspace <작업 공간> url       # 접속 주소 한 줄
    python3 studio/service.py autostart on|off|status [--dry-run]   # 허브 - PC 를 켜고 로그인하면 자동으로 띄우기(Windows 작업 스케줄러)

서비스 구성(포트·제목·브랜드·경로)은 모두 작업 공간의 nexa-slide.json 에 있다 — 엔진은 실행만 한다.
작업 공간 없이(작업 공간 밖에서) 실행하면 허브(시작 페이지) 서버를 다룬다 — 포트 5599, 로그·실행 정보는 사용자 설정 폴더.
작업 공간마다 포트를 다르게 두면 여러 작업 공간을 함께 띄울 수 있다(같은 작업 공간은 서버 하나).
서버 로그: <out>/.studio/server.log · 실행 정보: <out>/.studio/server.json
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
from common import DEFAULT_PORT, HUB, SERVER_INFO, STATE, WORKSPACE, running_server  # noqa: E402
from filelock import FileLock  # noqa: E402

LOG = STATE / "server.log"
START_LOCK = STATE / "start.lock"  # 시작 잠금 - 같은 작업 공간의 start 가 동시에 들어와도(허브 중계 자동 기동 + nexa.py restart) 하나만 띄운다


def start(extra):
    STATE.mkdir(parents=True, exist_ok=True)
    with FileLock(START_LOCK, wait=25):  # 먼저 잡은 쪽이 서버를 띄우고 server.json 을 쓸 때까지 기다린다 - 뒤의 쪽은 "이미 실행 중" 을 본다
        return _start(extra)


def _start(extra):
    run = running_server()
    if run:
        print(f"이미 실행 중: {run['url']} (pid {run['pid']})")
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    log = open(LOG, "a", encoding="utf-8")
    log.write(f"\n=== start {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    log.flush()
    kw = {}
    if os.name == "nt":  # 창 없이, 이 터미널·세션이 끝나도 살아 있게
        # DETACHED_PROCESS 를 쓰지 않는다 - venv 의 python.exe 는 기본 Python 을 자식으로 띄우는 런처라,
        # 콘솔이 없으면 그 자식이 새 콘솔 창을 연다(창을 닫으면 서버도 끝남). 숨은 콘솔을 주면 자식이 물려받는다.
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    if HUB:  # 허브: 작업 공간 없이 — 현재 폴더가 어디든 엔진·그 폴더에 쓰지 않는다
        env.pop("NEXA_SLIDE_WORKSPACE", None)
        cwd = STATE
    else:
        env["NEXA_SLIDE_WORKSPACE"] = str(WORKSPACE)
        cwd = WORKSPACE
    p = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), *extra], cwd=str(cwd), env=env,
                         stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **kw)
    for _ in range(40):  # 최대 10초 — 포트가 열리고 server.json 이 쓰일 때까지
        time.sleep(0.25)
        if p.poll() is not None:
            print(f"서버가 바로 끝났다(종료 코드 {p.returncode}) — 로그: {LOG}")
            print("".join(LOG.read_text(encoding="utf-8").splitlines(True)[-5:]))
            return 1
        run = running_server()
        if run and not isinstance(run.get("pid"), int):  # 포트는 답하는데 server.json 을 아직 안 썼다(설정 포트로 찾음) - 조금 더 기다려 실제 pid 를 본다
            for _ in range(12):
                time.sleep(0.25)
                again = running_server()
                if again and isinstance(again.get("pid"), int):
                    run = again
                    break
        if run:
            print(f"시작: {run['url']} (pid {run['pid']}) · 로그 {LOG}")
            return 0
    print(f"10초 안에 응답이 없다 — 로그 확인: {LOG}")
    return 1


def stop():
    run = running_server()
    if not run:
        print(f"실행 중인 서버 없음 (설정 포트 {DEFAULT_PORT})")
        return 0
    pid = run.get("pid")
    if not isinstance(pid, int):
        print(f"{run['url']} 에 이 작업 공간 서버가 있지만 pid 를 모른다(server.json 없음) — 직접 종료가 필요하다")
        return 1
    if not HUB:  # 웹 AI 세션이 있으면 먼저 끊는다(실행 중 턴의 프로세스 트리까지) - 서버를 바로 죽이면 자식이 남는다
        import urllib.request
        try:
            req = urllib.request.Request(run["url"] + "api/wsession", data=b'{"action":"stop","reason":"server-stop"}', method="POST",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                if json.loads(r.read().decode("utf-8")).get("stopped"):
                    print("웹 AI 세션을 끊었다")
        except Exception:  # noqa: BLE001 - 세션이 없거나 구 판 서버
            pass
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:  # 이미 끝남 - 아래 확인에서 정리
            pass
        except PermissionError:
            print(f"pid {pid} 를 끝낼 권한이 없다 — 다른 사용자의 프로세스인지 확인한다")
            return 1
    for _ in range(20):
        time.sleep(0.25)
        if not running_server():
            SERVER_INFO.unlink(missing_ok=True)
            print(f"종료: {run['url']} (pid {pid})")
            return 0
    print(f"종료 확인 실패 (pid {pid})")
    return 1


TASK = "nexa-slide hub"  # 작업 스케줄러 이름(docs/server-admin.md 6절과 같다)


def _ps(script):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, text=True, encoding="utf-8", errors="replace")


def autostart(arg, dry=False):
    """PC 를 켜고 로그인하면 허브를 띄운다 - Windows 작업 스케줄러 "로그온 시 실행"(관리자 권한 불필요, 이 사용자 계정으로).
    on · off · status. 다른 OS 는 할 일을 안내만 한다(docs/server-admin.md 6절)."""
    if not HUB:
        print("자동 시작은 허브만 - 작업 공간 밖에서 실행한다(작업 공간 서버는 허브가 띄운다)")
        return 1
    if os.name != "nt":
        print(f"Windows 가 아니다 - 로그인 때 `{sys.executable} {STUDIO / 'service.py'} start` 를 실행하게 한다"
              " (macOS launchd 사용자 에이전트 · Linux systemd --user). docs/server-admin.md 6절")
        return 1
    q = lambda s: "'" + str(s).replace("'", "''") + "'"  # noqa: E731 - PowerShell 작은따옴표 글
    if arg == "on" and not dry and ".claude" in STUDIO.parts and "worktrees" in STUDIO.parts:
        print(f"이 엔진은 개발용 worktree 다({STUDIO.parent}) - 운영 엔진(main 체크아웃)의 service.py 로 켠다")
        return 1
    if arg == "on":
        # 작업 폴더는 사용자 폴더(작업 공간 밖) - 작업 공간 안이면 허브가 아니라 그 작업 공간 서버가 뜬다
        script = (f"$a = New-ScheduledTaskAction -Execute {q(sys.executable)} -Argument {q(chr(34) + str(STUDIO / 'service.py') + chr(34) + ' start')}"
                  f" -WorkingDirectory $env:USERPROFILE; "
                  f"$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; "
                  f"$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0; "
                  f"Register-ScheduledTask -TaskName {q(TASK)} -Action $a -Trigger $t -Settings $s -Force | Out-Null")
    elif arg == "off":
        script = f"Unregister-ScheduledTask -TaskName {q(TASK)} -Confirm:$false"
    elif arg == "status":
        script = f"$t = Get-ScheduledTask -TaskName {q(TASK)} -ErrorAction SilentlyContinue; if ($t) {{ ($t.State.ToString() + ' · ' + $t.Actions[0].Execute + ' ' + $t.Actions[0].Arguments) }} else {{ 'none' }}"
    else:
        print("autostart on | off | status")
        return 1
    if dry:
        print(script)
        return 0
    r = _ps(script)
    out = (r.stdout or "").strip()
    if arg == "status":
        print("자동 시작: 꺼짐" if out in ("", "none") else f"자동 시작: 켜짐 ({out})")
        return 0
    if r.returncode:
        print(f"실패: {(r.stderr or out).strip()[:300]}")
        return 1
    print(f"자동 시작 {'켬' if arg == 'on' else '끔'} - 작업 스케줄러 '{TASK}'" + (" (로그인하면 허브가 뜬다)" if arg == "on" else ""))
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("start", "stop", "restart", "status", "url", "autostart"):
        sys.exit(__doc__)
    cmd, extra = sys.argv[1], sys.argv[2:]
    if cmd == "autostart":
        return autostart(extra[0] if extra else "status", "--dry-run" in extra)
    if cmd == "start":
        return start(extra)
    if cmd == "stop":
        return stop()
    if cmd == "restart":
        stop()
        return start(extra)
    if cmd == "url":
        run = running_server()
        print(run["url"] if run else f"(꺼짐) http://127.0.0.1:{DEFAULT_PORT}/")
        return 0 if run else 1
    import status
    status.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
