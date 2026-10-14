# -*- coding: utf-8 -*-
"""프로세스 사이 파일 잠금 - 허브·작업 공간 서버·CLI·세션이 같은 파일(접근 로그·엔진 요청 큐)을 함께 쓸 때.

    with FileLock(path_to_lock_file):   # Windows msvcrt.locking, 그 밖 fcntl.flock. 최대 wait 초 기다리고 못 얻으면 그냥 진행(서비스가 멈추지 않게)
        ...
"""
import os
import time


class FileLock:
    def __init__(self, path, wait=3.0):
        self.path = str(path)
        self.wait = wait
        self.fd = None

    def __enter__(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT, 0o644)
            if os.name == "nt":
                import msvcrt
                end = time.time() + self.wait
                while True:
                    try:
                        msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                        return self
                    except OSError:
                        if time.time() >= end:
                            return self
                        time.sleep(0.05)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX)
        except OSError:
            pass
        return self

    def __exit__(self, *a):
        if self.fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(self.fd)
        self.fd = None
