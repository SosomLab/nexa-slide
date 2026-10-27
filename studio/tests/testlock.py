# -*- coding: utf-8 -*-
"""시험 잠금 - 이 PC 에서 시험 실행은 한 번에 하나만(0.22.41).

시험들은 고정 포트(5799 허브·5667 작업 공간·9333 Chrome 디버그 등)와 같은 임시 폴더(<임시 폴더>/nexa-slide-tests)를 쓴다.
엔진 배포의 시험과 엔진 세션이 돌리는 시험이 겹치면 한쪽 서버가 포트를 못 잡고, 남의 서버(다른 작업 공간)에 물어 엉뚱하게 실패한다
(0.22.37 배포 실패: content_i18n 이 세션 쪽 'ui시험' 서버의 슬라이드 유형을 받고, uxpack 이 그 서버에 없는 덱 PDF 를 요청해 404).

    import testlock  # 시험 파일 머리 - 가져오는 순간 잠근다(다른 실행이 있으면 끝날 때까지 기다린다)

잠금은 OS 파일 잠금이라 잡은 프로세스가 죽으면 저절로 풀린다(남은 잠금 파일을 지울 필요 없음).
run_all 이 잡으면 NEXA_TEST_LOCK 을 자식에게 물려 묶음마다 다시 잡지 않는다.
"""
import atexit
import datetime as dt
import json
import os
import sys
import tempfile
import time
from pathlib import Path

LOCK = Path(tempfile.gettempdir()) / "nexa-slide-tests.lock"  # NEXA_TEST_DIR 와 무관 - 포트는 PC 전체에서 겹친다
INFO = LOCK.with_suffix(".lock.json")  # 지금 잡은 쪽 {pid, cmd, cwd, t} - 기다리는 쪽이 누구를 기다리는지 보인다
WAIT = int(os.environ.get("NEXA_TEST_LOCK_WAIT") or 2400)  # 최대 기다림(초)
_fd = None


def _try(fd):
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def holder():
    try:
        return json.loads(INFO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def hold():
    """잠근다 - 이미 이 프로세스(또는 부모 run_all)가 잡았으면 그대로. 기다리는 동안 '== 대기 · …' 줄을 찍는다(엔진 배포가 진행으로 보인다)."""
    global _fd
    if _fd is not None or os.environ.get("NEXA_TEST_LOCK"):
        return
    fd = os.open(str(LOCK), os.O_RDWR | os.O_CREAT, 0o644)
    t0, said = time.time(), 0.0
    while not _try(fd):
        if time.time() - t0 > WAIT:
            os.close(fd)
            sys.exit(f"시험 잠금을 {WAIT}초 동안 얻지 못했다 - 다른 시험 실행: {holder()}")
        if time.time() - said >= 30:
            h = holder()
            print(f"== 대기 · 다른 시험 실행이 끝나길 기다림(pid {h.get('pid', '?')} · {h.get('t', '?')} 시작 · {h.get('cmd', '?')[:80]})", flush=True)
            said = time.time()
        time.sleep(1)
    _fd = fd
    os.environ["NEXA_TEST_LOCK"] = str(os.getpid())  # 자식(run_all → 각 시험)은 다시 잡지 않는다
    try:
        INFO.write_text(json.dumps({"pid": os.getpid(), "cmd": " ".join(sys.argv), "cwd": os.getcwd(), "t": dt.datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    atexit.register(release)


def release():
    global _fd
    if _fd is None:
        return
    try:
        INFO.unlink(missing_ok=True)
    except OSError:
        pass
    os.close(_fd)  # 닫으면 잠금도 풀린다
    _fd = None
    os.environ.pop("NEXA_TEST_LOCK", None)


hold()
