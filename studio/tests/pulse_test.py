# -*- coding: utf-8 -*-
"""처리 중 턴의 맥박(wsession.pulse, #9) - 가짜 에이전트(도구 하나를 몇 초 '실행'하는 NDJSON)로 한 턴을 돌리며 본다:
도구가 도는 동안 tool{name·summary·sec}·alive·turnSec, 결과가 오면 tool 없음, 프로세스가 끝나면 alive 거짓, 처리 중이 아니면 {state} 만, info() 에 pulse.
격리: NEXA_SLIDE_USER_DIR · NEXA_SLIDE_WORKSPACE(example 사본) · EngineProfile 의 cwd 를 임시 폴더로."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
ROOT = WORK / "pulse"
shutil.rmtree(ROOT, ignore_errors=True)
(ROOT / "user").mkdir(parents=True)
shutil.copytree(STUDIO.parent / "example", ROOT / "ws", ignore=shutil.ignore_patterns("out", ".studio"))  # wsession 을 읽으려면 작업 공간이 있어야 한다
os.environ["NEXA_SLIDE_USER_DIR"] = str(ROOT / "user")
os.environ["NEXA_SLIDE_WORKSPACE"] = str(ROOT / "ws")
sys.path.insert(0, str(STUDIO))
import agents  # noqa: E402
import wsession  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


# 가짜 에이전트 - claude stream-json 모양으로 도구 시작 → 3초 → 도구 결과 → 3초 → 결과
FAKE = ROOT / "fake_agent.py"
FAKE.write_text("""import json, sys, time
sys.stdin.read()
p = lambda d: (print(json.dumps(d)), sys.stdout.flush())
p({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "python3 studio/tests/run_all.py"}}]}})
time.sleep(3)
p({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}})
time.sleep(3)
p({"type": "result", "subtype": "success", "is_error": False, "result": "끝"})
""", encoding="utf-8")


class Fake:
    def turn_cmd(self, *a, **kw):
        return [sys.executable, str(FAKE)]

    def parse(self, line):
        return agents.get("claude").parse(line)


prof = wsession.EngineProfile()
prof.cwd = ROOT
sess = wsession.WebSession(prof)
check("처리 중이 아니면 {state} 만", set(sess.pulse()) == {"state", "seq"}, sess.pulse())
sess.agent, sess.model, sess._log_dir = "fake", "m", ROOT / "log"
sess._log_dir.mkdir()
sess._turn_log = sess._log_dir / "turn-1.jsonl"
sess.state = "running"
sess._pulse = {"turn": 1, "t0": time.time(), "out": time.time(), "tool": None, "open": 0, "tools": 0}  # _turn 이 하는 것
out = {}
th = threading.Thread(target=lambda: out.update(r=sess._run_once(Fake(), 1, "p", None, dict(os.environ), {})), daemon=True)
th.start()
time.sleep(2.2)
p = sess.pulse()
check("도구 실행 중: tool = Bash · 요약 · 경과 ≥1초 · 도구 1회", (p.get("tool") or {}).get("name") == "Bash" and "run_all" in p["tool"]["summary"] and p["tool"]["sec"] >= 1 and p.get("tools") == 1, p)
check("  에이전트 프로세스 살아 있음 · 턴 경과 ≥2초", p.get("alive") is True and p.get("turnSec", 0) >= 2, p)
check("  info() 에 pulse", (sess.info().get("pulse") or {}).get("turn") == 1)
time.sleep(2.3)  # 도구 결과(약 3초) 뒤, 결과(약 6초) 전
p = sess.pulse()
check("도구 결과 뒤: tool 없음 · 마지막 출력 경과 작음", "tool" not in p and p.get("outSec", 99) <= 2 and p.get("alive") is True, p)
th.join(timeout=10)
p = sess.pulse()
check("프로세스가 끝나면 alive 거짓(턴 정리 전)", p.get("alive") is False and (out.get("r") or [None])[0] is not None, (p, out))
sess._pulse, sess.state = {}, "ready"
check("턴이 끝나면 맥박 없음", "turn" not in sess.pulse() and "pulse" not in sess.info())
shutil.rmtree(ROOT, ignore_errors=True)
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
