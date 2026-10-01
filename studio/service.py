# -*- coding: utf-8 -*-
"""작업 공간 서비스 관리 — 서버를 백그라운드로 띄우고/멈추고/상태를 본다.

    python3 studio/service.py --workspace <작업 공간> start     # 백그라운드 실행(이미 떠 있으면 그대로 알림)
    python3 studio/service.py --workspace <작업 공간> stop      # 이 작업 공간 서버만 종료
    python3 studio/service.py --workspace <작업 공간> restart
    python3 studio/service.py --workspace <작업 공간> status    # status.py 와 같음
    python3 studio/service.py --workspace <작업 공간> url       # 접속 주소 한 줄

서비스 구성(포트·제목·브랜드·경로)은 모두 작업 공간의 nexa-slide.json 에 있다 — 엔진은 실행만 한다.
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
from common import DEFAULT_PORT, SERVER_INFO, STATE, WORKSPACE, running_server  # noqa: E402

LOG = STATE / "server.log"


def start(extra):
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
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    env = {**os.environ, "NEXA_SLIDE_WORKSPACE": str(WORKSPACE), "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    p = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), *extra], cwd=str(WORKSPACE), env=env,
                         stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **kw)
    for _ in range(40):  # 최대 10초 — 포트가 열리고 server.json 이 쓰일 때까지
        time.sleep(0.25)
        if p.poll() is not None:
            print(f"서버가 바로 끝났다(종료 코드 {p.returncode}) — 로그: {LOG}")
            print("".join(LOG.read_text(encoding="utf-8").splitlines(True)[-5:]))
            return 1
        run = running_server()
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
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        time.sleep(0.25)
        if not running_server():
            SERVER_INFO.unlink(missing_ok=True)
            print(f"종료: {run['url']} (pid {pid})")
            return 0
    print(f"종료 확인 실패 (pid {pid})")
    return 1


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("start", "stop", "restart", "status", "url"):
        sys.exit(__doc__)
    cmd, extra = sys.argv[1], sys.argv[2:]
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
