# -*- coding: utf-8 -*-
"""Claude Code 훅 → 세션 활동 기록(out/.studio/activity.json). 편집기가 "대기 / 요청 처리 중 / 대화 작업 중"을 구분해 보여 준다.

작업 공간 .claude/settings.json(init_workspace.py 가 만든다)의 훅이 부른다 — 표준 입력으로 훅 JSON 을 받는다:
    UserPromptSubmit  → 이 세션 "대화 작업 중"(입력 첫 줄)        PreToolUse → 활동 시각 갱신(대기였으면 "작업 중 — 요청·자동")
    PostToolUse(Monitor, 명령에 watch_requests) → 이 세션 = 요청 감시 담당          Stop → "대기"
빨리 끝나야 하므로 엔진 모듈을 불러오지 않고 파일 하나만 고친다. 실패해도 조용히 끝낸다(세션을 막지 않게).
"""
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path


def workspace():
    for d in (os.environ.get("CLAUDE_PROJECT_DIR"), os.environ.get("NEXA_SLIDE_WORKSPACE"), os.getcwd()):
        if not d:
            continue
        p = Path(d).resolve()
        for q in (p, *p.parents):
            if (q / "nexa-slide.json").is_file():
                return q
    return None


def main():
    try:
        ev = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    ws = workspace()
    if not ws:
        return
    try:
        cfg = json.loads((ws / "nexa-slide.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    f = ws / cfg.get("out", "out") / ".studio" / "activity.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {"sessions": {}}
    now = dt.datetime.now().isoformat(timespec="seconds")
    sid = str(ev.get("session_id") or "unknown")
    s = data["sessions"].setdefault(sid, {"state": "idle", "since": now})
    name = ev.get("hook_event_name") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if name == "UserPromptSubmit":
        line = next((ln.strip() for ln in str(ev.get("prompt") or "").splitlines() if ln.strip()), "")
        s.update(state="busy", source="chat", prompt=line[:80], since=now)
    elif name == "PreToolUse":
        if s.get("state") != "busy":
            s.update(state="busy", source="auto", prompt="", since=now)
    elif name == "PostToolUse":
        cmd = json.dumps(ev.get("tool_input") or {}, ensure_ascii=False)
        if ev.get("tool_name") == "Monitor" and "watch_requests" in cmd:
            for o in data["sessions"].values():
                o["watcher"] = False
            s["watcher"] = True
    elif name in ("Stop", "SubagentStop") and name == "Stop":
        s.update(state="idle", source="", prompt="", since=now)
    s["last"] = now
    cut = (dt.datetime.now() - dt.timedelta(days=1)).isoformat(timespec="seconds")
    data["sessions"] = {k: v for k, v in data["sessions"].items() if v.get("last", "") >= cut}
    data["updated"] = now
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(f.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False))
    os.replace(tmp, f)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — 훅 실패가 세션을 막지 않게
        pass
