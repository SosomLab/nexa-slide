# -*- coding: utf-8 -*-
"""OS 임시 폴더(%TEMP%) 사용 - 엔진·시험은 임시 폴더를 여기서만 만든다(docs/dev/temp-files-design.md).

    with tmpfiles.temp_dir("vba") as d:   # <임시 폴더>/nexa-slide-tmp-vba-xxxx - 블록이 끝나면 지운다
    tmpfiles.process_dir("tplrec")        # 프로세스가 끝날 때 지운다(모듈 머리에서 환경 변수로 넘길 때)
    tmpfiles.sweep()                      # 비정상 종료로 남은 것(PATTERNS) 중 하루 넘은 것을 지운다
    tmpfiles.leftovers()                  # 지금 남아 있는 것(PATTERNS) 이름(누수 시험이 전후를 비교한다)
    python3 studio/tmpfiles.py [sweep]    # 보고 · 쓸어내기

Temp 에 남은 것이 쌓이면 로그온 때 Temp 를 훑는 작업이 느려진다(smoke.js 프로필 2,000개 → 로그온 4~5분).
common.py 와 달리 불러와도 작업 공간·설정을 읽지 않는다 - 시험이 머리에서 불러도 된다.
"""
import atexit
import os
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

PREFIX = "nexa-slide-tmp-"
# 엔진·시험이 Temp 에 만드는 이름 - 이것만 쓸어낸다(다른 Nexa 앱의 nexa-* 는 건드리지 않는다).
# nx-smoke- 는 smoke.js, 나머지는 2026-11-03 전 엔진이 직접 mkdtemp 로 만들던 이름
PATTERNS = (PREFIX, "nx-smoke-", "nexa-vba-", "nexa-shapes-", "nexa-autostart-", "nexa-engine-tidy-", "nexa-sheet-rt-", "nexa-sheet-font-",
            "nexa-tplrec-", "nexa-pyshim-", "nexa-pptx-start-", "nexa-xcheck-", "vbasafe-")
WARN_COUNT = 500  # Temp 항목이 이보다 많으면 허브 상태에 경고


def root():
    return Path(tempfile.gettempdir())


def remove(p, tries=10, delay=0.2):
    """폴더·파일을 지운다 - Windows 에서 방금 끝난 프로세스가 파일을 쥐고 있을 수 있어 다시 시도. 지웠거나 없으면 True."""
    p = Path(p)
    for i in range(tries):
        try:
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
            elif p.exists() or p.is_symlink():
                p.unlink()
            return True
        except FileNotFoundError:
            return True
        except OSError:
            if i + 1 < tries:
                time.sleep(delay)
    return not p.exists()


def _new(prefix):
    return Path(tempfile.mkdtemp(prefix=f"{PREFIX}{prefix}-"))


@contextmanager
def temp_dir(prefix):
    """<임시 폴더>/nexa-<prefix>-xxxx 를 만들고 블록이 끝나면(예외여도) 지운다."""
    d = _new(prefix)
    try:
        yield d
    finally:
        _remove_or_warn(d)


def process_dir(prefix):
    """프로세스가 끝날 때 지우는 임시 폴더 - 모듈 머리에서 만들어 환경 변수 등으로 넘겨야 할 때.
    그 안의 파일을 연 채(zipfile 등) 끝나면 Windows 에서 지우지 못한다 - with 로 닫는다."""
    d = _new(prefix)
    atexit.register(_remove_or_warn, d)
    return d


def _remove_or_warn(d):
    if not remove(d):
        print(f"임시 폴더를 지우지 못했다(파일을 연 채인지 본다): {d}", file=sys.stderr)


def leftovers():
    """Temp 바로 아래 엔진·시험이 만든 이름(PATTERNS) 집합."""
    try:
        return {e.name for e in os.scandir(root()) if e.name.startswith(PATTERNS)}
    except OSError:
        return set()


def sweep(max_age=86400):
    """비정상 종료(시간 초과·Ctrl+C·kill)로 남은 것(PATTERNS) 중 max_age 초 넘게 지난 것을 지운다. (지운 수, 못 지운 수)."""
    now, done, failed = time.time(), 0, 0
    for name in leftovers():
        p = root() / name
        try:
            if now - p.lstat().st_mtime < max_age:
                continue
        except OSError:
            continue
        if remove(p, tries=2, delay=0.1):
            done += 1
        else:
            failed += 1  # 사용 중 - 다음에
    return done, failed


def count():
    """Temp 바로 아래 항목 수(못 읽으면 None)."""
    try:
        return sum(1 for _ in os.scandir(root()))
    except OSError:
        return None


if __name__ == "__main__":
    if sys.argv[1:] == ["sweep"]:
        print("지움 %d · 사용 중 %d" % sweep())
    else:
        left = sorted(leftovers())
        print(f"Temp {root()} · 항목 {count()} · nexa-slide 잔여물 {len(left)}")
        for n in left:
            print("  " + n)
