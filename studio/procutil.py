# -*- coding: utf-8 -*-
"""프로세스 도우미 - 수동 세션 감시(watch_requests · watch_engine_requests)와 서버가 같이 쓴다.

    pid_alive(pid)        살아 있는가(Windows 는 OpenProcess+GetExitCodeProcess - os.kill(pid, 0) 은 Windows 에서 프로세스를 죽이므로 쓰지 않는다)
    kill_tree(pid)        그 프로세스와 자식을 끝낸다(Windows taskkill /T /F, 그 밖은 SIGTERM → SIGKILL). 끝났으면 True
    stdout_closed()       표준 출력의 읽는 쪽(Monitor 를 건 세션)이 닫혔는가 - 세션·VS Code 가 닫히면 감시가 스스로 끝나게
                          (Windows: 0바이트 WriteFile 이 ERROR_NO_DATA/BROKEN_PIPE · POSIX: poll 의 POLLERR/POLLHUP)
    stop_manual(hb_path)  하트비트 파일의 수동 감시를 끝내고 stopped 로 표시 - 웹 카드 [세션 중지]가 수동 세션에도 통하게
    session_meta()        감시를 띄운 AI 세션의 agent·model·sessionId·entry(인자 > 환경변수 CLAUDE_CODE_*) - 카드에 모델·세션 ID 를 보이게
"""
import json
import os
import sys
import time


def session_meta(agent=None, model=None):
    """감시를 띄운 AI 세션의 정보 - 인자(--agent/--model) > 환경변수. Claude Code 가 내보내는 CLAUDE_CODE_SESSION_ID·CLAUDE_CODE_ENTRYPOINT 도 담는다.
    {agent, model, sessionId, entry(vscode|cli|…)} - 빈 값은 뺀다."""
    env = os.environ
    agent = agent or env.get("NEXA_SLIDE_AGENT") or ("claude" if env.get("CLAUDECODE") else "")
    model = model or env.get("NEXA_SLIDE_MODEL") or env.get("ANTHROPIC_MODEL") or ""
    entry = env.get("CLAUDE_CODE_ENTRYPOINT") or ""
    if entry.startswith("claude-"):
        entry = entry[7:]  # claude-vscode → vscode
    out = {"agent": agent, "model": model, "sessionId": env.get("CLAUDE_CODE_SESSION_ID") or "", "entry": entry}
    return {k: v for k, v in out.items() if v}


def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_tree(pid, wait=3.0):
    """pid 와 그 자식을 끝낸다. pyenv 같은 래퍼(sh → cmd → python)로 떠 있어도 묶어서. 끝났으면 True."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0 or pid == os.getpid() or not pid_alive(pid):
        return not pid_alive(pid)
    try:
        if os.name == "nt":
            import subprocess
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15)
        else:
            import signal
            os.kill(pid, signal.SIGTERM)
    except (OSError, Exception):  # noqa: BLE001
        pass
    t0 = time.time()
    while pid_alive(pid) and time.time() - t0 < wait:
        time.sleep(0.1)
    if pid_alive(pid) and os.name != "nt":
        try:
            import signal
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        time.sleep(0.2)
    return not pid_alive(pid)


def stdout_closed():
    """표준 출력의 읽는 쪽이 닫혔는가. 모르면(터미널·파일·판정 불가) False."""
    try:
        fd = sys.stdout.fileno()
    except (OSError, ValueError, AttributeError):
        return False
    try:
        if os.isatty(fd):
            return False
    except OSError:
        return False
    if os.name == "nt":
        try:
            import ctypes
            import msvcrt
            h = msvcrt.get_osfhandle(fd)
            n = ctypes.c_ulong(0)
            ok = ctypes.windll.kernel32.WriteFile(ctypes.c_void_p(h), b"", 0, ctypes.byref(n), None)
            if ok:
                return False
            return ctypes.windll.kernel32.GetLastError() in (232, 109)  # ERROR_NO_DATA · ERROR_BROKEN_PIPE
        except Exception:  # noqa: BLE001
            return False
    try:
        import select
        p = select.poll()
        p.register(fd, select.POLLERR | select.POLLHUP)
        return bool(p.poll(0))
    except Exception:  # noqa: BLE001
        return False


def stop_manual(hb_path):
    """하트비트 파일(session.json)의 수동 감시가 살아 있으면 끝내고 stopped 로 표시. {stopped: bool, pid, label}"""
    from pathlib import Path
    p = Path(hb_path)
    try:
        hb = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"stopped": False}
    kind = hb.get("kind") or "manual"
    if kind not in ("manual",) or hb.get("stopped"):
        return {"stopped": False, "pid": hb.get("pid"), "label": hb.get("label"), "kind": kind}
    pid = hb.get("pid")
    gone = kill_tree(pid) if pid else True
    hb["stopped"] = True
    hb["stoppedBy"] = "web"
    hb["ts"] = time.time()
    try:
        tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(hb, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass
    return {"stopped": bool(gone), "pid": pid, "label": hb.get("label"), "kind": kind}
