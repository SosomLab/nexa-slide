# -*- coding: utf-8 -*-
"""세션의 python3·python 대리 파일(0.25.19) - procutil.py_shims · with_py_shims.

    python3 studio/tests/py_shims_test.py

Windows 는 PATH 에서 스토어 대리 실행기(WindowsApps\python3.exe)가 실제 파이썬보다 앞에 있으면 세션의 `python3 nexa.py` 가 종료 코드 49 로 끝났다.
대리 폴더를 PATH 맨 앞에 두면 cmd·PowerShell·Git Bash 어디서든 python3 = 이 서버의 파이썬(sys.executable)인지 본다(있는 셸만).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["NEXA_SLIDE_USER_DIR"] = tempfile.mkdtemp(prefix="nexa-pyshim-user-")  # with_py_shims 기본 폴더 - 실제 사용자 설정을 건드리지 않게
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import procutil  # noqa: E402

FAILS = []


def check(name, ok, got=""):
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f" → {got}"))
    if not ok:
        FAILS.append(name)


d = Path(tempfile.mkdtemp(prefix="nexa-pyshim-")) / "bin"
check("대리 폴더를 만든다(python3·python)", procutil.py_shims(d) == d and (d / "python3").is_file() and (d / "python").is_file()
      and (os.name != "nt" or (d / "python3.cmd").is_file()), sorted(p.name for p in d.iterdir()) if d.is_dir() else None)
env = procutil.with_py_shims({"PATH": os.environ.get("PATH", "")})
check("with_py_shims - PATH 맨 앞", env["PATH"].split(os.pathsep)[0].endswith("bin"), env["PATH"][:120])
env = {**os.environ, "PATH": str(d) + os.pathsep + os.environ.get("PATH", "")}
code = "import sys;print(sys.executable)"
want = os.path.normcase(os.path.realpath(sys.executable))
shells = []
if os.name == "nt":
    shells.append(("cmd", ["cmd", "/c", "python3", "-c", code]))
    if shutil.which("powershell"):
        shells.append(("PowerShell", ["powershell", "-NoProfile", "-Command", f"python3 -c '{code}'"]))
    gb = next((p for p in (r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash")) if p and os.path.isfile(p) and "System32" not in p), None)
    if gb:
        shells.append(("Git Bash", [gb, "-c", f"python3 -c '{code}'"]))
elif shutil.which("sh"):
    shells.append(("sh", ["sh", "-c", f"python3 -c '{code}'"]))
for name, cmd in shells:
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    got = os.path.normcase(os.path.realpath(r.stdout.strip())) if r.stdout.strip() else ""
    check(f"{name}: python3 = 이 서버의 파이썬", r.returncode == 0 and got == want, (r.returncode, r.stdout.strip(), r.stderr.strip()[:200]))
shutil.rmtree(d.parent, ignore_errors=True)
print("\n실패:", FAILS or "없음")
print("전부 통과" if not FAILS else "")
sys.exit(1 if FAILS else 0)
