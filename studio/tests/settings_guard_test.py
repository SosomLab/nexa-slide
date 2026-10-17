# -*- coding: utf-8 -*-
"""0.22.24 - paths.remember 가드: OS 임시 폴더 안의 작업 공간은 사용자 설정이 격리(NEXA_SLIDE_USER_DIR)되지 않았으면 '최근 작업' 에 올리지 않는다
(시험·임시 서버가 실제 settings.json recent 를 더럽히던 결함 - 협업 세션 발견). 실제 사용자 설정은 건드리지 않도록 APPDATA/XDG_CONFIG_HOME 을 임시 폴더로 바꿔 하위 프로세스로 확인한다."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parents[1]
FAILS = []
if sys.platform == "darwin":
    print("SKIP macOS 는 사용자 설정 폴더가 홈 아래라 격리할 수 없다")
    sys.exit(0)


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


SCRIPT = "import sys, paths; paths.remember(sys.argv[1], 't'); print(paths.SETTINGS)"
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    fake_cfg = td / "cfg"; fake_cfg.mkdir()
    temp_ws = td / "ws"; temp_ws.mkdir()
    base = {**os.environ, "APPDATA": str(fake_cfg), "XDG_CONFIG_HOME": str(fake_cfg), "PYTHONIOENCODING": "utf-8"}
    base.pop("NEXA_SLIDE_USER_DIR", None)

    def run(env, ws):
        return subprocess.run([sys.executable, "-c", SCRIPT, str(ws)], cwd=str(STUDIO), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")

    def recent(user_dir):
        f = Path(user_dir) / "nexa-slide" / "settings.json" if (Path(user_dir) / "nexa-slide").exists() else Path(user_dir) / "settings.json"
        try:
            return json.loads(f.read_text(encoding="utf-8")).get("recent", [])
        except (OSError, ValueError):
            return []

    r = run(base, temp_ws)
    check("격리 없이 임시 폴더 작업 공간 → recent 에 올리지 않음", r.returncode == 0 and not recent(fake_cfg), r.stdout + r.stderr + str(recent(fake_cfg)))
    iso = td / "iso"
    r = run({**base, "NEXA_SLIDE_USER_DIR": str(iso)}, temp_ws)
    check("NEXA_SLIDE_USER_DIR 격리 아래서는 임시 폴더도 기록(시험용)", r.returncode == 0 and len(recent(iso)) == 1, r.stdout + r.stderr)
    home_like = Path.home() / "nexa-slide-guard-test-ws"  # 임시 폴더 밖 - 기록돼야 한다(폴더는 만들지 않는다, 경로만)
    r = run(base, home_like)
    check("임시 폴더 밖 작업 공간은 기록", r.returncode == 0 and len(recent(fake_cfg)) == 1, r.stdout + r.stderr)

print("\n실패:", ", ".join(FAILS) if FAILS else "없음")
sys.exit(1 if FAILS else 0)
