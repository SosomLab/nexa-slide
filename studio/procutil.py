# -*- coding: utf-8 -*-
"""프로세스 도우미 - 수동 세션 감시(watch_requests · watch_engine_requests)와 서버가 같이 쓴다.

    pid_alive(pid)        살아 있는가(Windows 는 OpenProcess+GetExitCodeProcess - os.kill(pid, 0) 은 Windows 에서 프로세스를 죽이므로 쓰지 않는다)
    kill_tree(pid)        그 프로세스와 자식을 끝낸다(Windows taskkill /T /F, 그 밖은 SIGTERM → SIGKILL). 끝났으면 True
    stdout_closed()       표준 출력의 읽는 쪽(Monitor 를 건 세션)이 닫혔는가 - 세션·VS Code 가 닫히면 감시가 스스로 끝나게
    StdoutWatch().closed() 위 판정의 오판 방지판(몇 초 연속 + 실제 한 줄 쓰기 실패일 때만 True) - 감시 루프는 이것을 쓴다
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


def py_shims(root=None):
    """세션이 부를 python3·python 을 이 서버의 파이썬(sys.executable)으로 - 대리 파일 폴더를 만들어 돌려준다(실패하면 None).
    Windows 는 PATH 에서 스토어 대리 실행기(WindowsApps\python3.exe - 실행하면 종료 코드 49 나 9009)가 pyenv 등 실제 파이썬보다
    앞에 있는 일이 흔해, 세션의 `python3 nexa.py …` 가 아무것도 못 하던 것(0.25.19). Git Bash 용 확장자 없는 스크립트와 cmd·PowerShell 용 .cmd 를 둔다.
    pyenv-win 의 .bat 대리 실행기(여러 줄·< > | & 인자가 깨진다)도 거치지 않게 된다."""
    try:
        if root is None:
            from paths import user_dir
            root = user_dir() / "hub" / "bin"
        root.mkdir(parents=True, exist_ok=True)
        exe = sys.executable
        posix = exe.replace("\\", "/")
        if os.name == "nt" and len(posix) > 2 and posix[1] == ":":  # C:/… → /c/… (Git Bash)
            posix = "/" + posix[0].lower() + posix[2:]
        for n in ("python3", "python"):
            sh, cmd = f'#!/bin/sh\nexec "{posix}" "$@"\n', f'@"{exe}" %*\r\n'
            p = root / n
            if not p.is_file() or p.read_text(encoding="utf-8") != sh:
                p.write_text(sh, encoding="utf-8", newline="\n")
                try:
                    p.chmod(0o755)
                except OSError:
                    pass
            if os.name == "nt":
                c = root / f"{n}.cmd"
                if not c.is_file() or c.read_text(encoding="utf-8") != cmd:
                    c.write_text(cmd, encoding="utf-8", newline="")
        return root
    except OSError:
        return None


def with_py_shims(env):
    """env(dict)의 PATH 맨 앞에 py_shims 폴더 - 세션·도구가 부르는 python3 가 이 서버의 파이썬이 되게."""
    d = py_shims()
    if d:
        env["PATH"] = str(d) + os.pathsep + env.get("PATH", "")
    return env


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


class StdoutWatch:
    """stdout_closed() 의 오판 방지 - Node(Monitor) 파이프에서는 읽는 쪽이 살아 있어도 0바이트 WriteFile 이 간혹 ERROR_NO_DATA 를 낸다(운영 재현).
    그래서 '닫힘' 판정이 confirm 초 이상 이어질 때 실제 한 줄 {"event":"ping"} 을 써 보고, 그 쓰기가 실패할 때만 닫힌 것으로 본다(성공하면 판정 초기화).
    Monitor 에는 오판 때만 ping 한 줄이 드물게 보인다 - 무시하면 된다."""

    def __init__(self, confirm=3.0):
        self.confirm = confirm
        self.since = None

    def closed(self):
        if not stdout_closed():
            self.since = None
            return False
        now = time.time()
        if self.since is None:
            self.since = now
            return False
        if now - self.since < self.confirm:
            return False
        try:
            sys.stdout.write('{"event": "ping"}\n')
            sys.stdout.flush()
        except (OSError, ValueError):
            return True
        self.since = None  # 실제 쓰기가 됐다 - 오판
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
