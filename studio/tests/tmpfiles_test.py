# -*- coding: utf-8 -*-
"""임시 파일 정리(tmpfiles.py, docs/dev/temp-files-design.md) 시험.

    python3 studio/tests/tmpfiles_test.py

temp_dir 은 블록이 끝나면(예외여도) 지운다 · process_dir 은 프로세스가 끝나면 지운다 · leftovers·sweep 은 엔진 이름(PATTERNS)만,
하루 넘은 것만 · 다른 앱의 nexa-* 는 건드리지 않는다 · engine_tidy 의 temp 범주가 보고하고 지운다.
실제 OS 임시 폴더를 쓰되 이 시험이 만든 이름만 만들고 지운다.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(testlock.py)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
import tmpfiles  # noqa: E402
USER = tmpfiles.process_dir("tmpfiles-user")  # engine_tidy 가 읽는 사용자 설정 - 실제 큐를 건드리지 않게
os.environ["NEXA_SLIDE_USER_DIR"] = str(USER)
FAILS = []
OLD = time.time() - 2 * 86400


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def plant(name, old=True):
    p = tmpfiles.root() / name
    p.mkdir(exist_ok=True)
    (p / "x.txt").write_text("x", encoding="utf-8")
    if old:
        os.utime(p, (OLD, OLD))
    return p


# 1. temp_dir - 정상·예외 모두 지운다, 이름은 PREFIX
with tmpfiles.temp_dir("t1") as d:
    (d / "a").write_text("a", encoding="utf-8")
    check("temp_dir - 엔진 접두사로 임시 폴더 아래", d.name.startswith(tmpfiles.PREFIX + "t1-") and d.parent == tmpfiles.root(), d)
check("temp_dir - 블록 뒤 지움", not d.exists(), d)
try:
    with tmpfiles.temp_dir("t2") as d2:
        raise RuntimeError("시험")
except RuntimeError:
    pass
check("temp_dir - 예외여도 지움", not d2.exists(), d2)

# 2. process_dir - 자식 프로세스가 만들고 끝나면 사라진다(sys.exit 1 이어도)
code = f"import sys; sys.path.insert(0, {str(STUDIO)!r}); import tmpfiles; d = tmpfiles.process_dir('t3'); (d / 'f').write_text('f'); print(d); sys.exit(1)"
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8")
p3 = Path(r.stdout.strip()) if r.stdout.strip() else None
check("process_dir - 프로세스가 끝나면 지움", p3 is not None and p3.name.startswith(tmpfiles.PREFIX) and not p3.exists(), (r.stdout, r.stderr))

# 3. leftovers·sweep - 엔진 이름만, 하루 넘은 것만
tag = f"{os.getpid()}"
old_new = plant(f"{tmpfiles.PREFIX}tfold-{tag}")
old_legacy = plant(f"nexa-vba-tf{tag}")
old_smoke = plant(f"nx-smoke-tf{tag}")
young = plant(f"{tmpfiles.PREFIX}tfyoung-{tag}", old=False)
other = plant(f"nexa-otherapp-tf{tag}")  # 다른 Nexa 앱 - 이름이 nexa- 로 시작해도 엔진 것이 아니다
left = tmpfiles.leftovers()
check("leftovers - 엔진·smoke·예전 이름", {old_new.name, old_legacy.name, old_smoke.name, young.name} <= left, sorted(left))
check("leftovers - 다른 앱의 nexa-* 는 빼고", other.name not in left)
done, busy = tmpfiles.sweep()
check("sweep - 하루 넘은 것 지움", not old_new.exists() and not old_legacy.exists() and not old_smoke.exists(), (done, busy))
check("sweep - 새것·다른 앱의 것은 남김", young.exists() and other.exists())
tmpfiles.remove(young)
tmpfiles.remove(other)

# 4. engine_tidy - temp 범주(한 시간 넘은 것) 보고 → 지움, 다른 앱의 것은 보고하지 않음
import engine_tidy as et  # noqa: E402
t_old = plant(f"{tmpfiles.PREFIX}tftidy-{tag}")
t_other = plant(f"nexa-otherapp2-tf{tag}")
rep = et.scan()
paths = {Path(i["path"]).name: i["category"] for i in rep["items"]}
check("engine_tidy - temp 범주로 보고", paths.get(t_old.name) == "temp" and "temp" in rep["categories"], sorted(paths))
check("engine_tidy - 다른 앱의 것은 보고하지 않음", t_other.name not in paths)
res = et.clean(["temp"])
check("engine_tidy clean temp - 지움", not t_old.exists(), res["items"])
check("engine_tidy clean temp - 다른 앱의 것은 남김", t_other.exists())
tmpfiles.remove(t_other)

# 5. status - 임시 폴더 항목 수·잔여물·경고(허브로 - 작업 공간 밖에서)
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
env.pop("NEXA_SLIDE_WORKSPACE", None)
r = subprocess.run([sys.executable, str(STUDIO / "status.py"), "--json"], capture_output=True, text=True, encoding="utf-8", cwd=str(USER), env=env)
try:
    st = json.loads(r.stdout)["temp"]
except (ValueError, KeyError):
    st = None
check("status --json - 임시 폴더 항목 수·잔여물·경고", isinstance(st, dict) and isinstance(st["count"], int) and isinstance(st["leftovers"], int)
      and st["warn"] == (st["count"] > tmpfiles.WARN_COUNT), (st, r.stdout[-300:], r.stderr[-300:]))

print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
