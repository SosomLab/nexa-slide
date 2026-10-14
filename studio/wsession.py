# -*- coding: utf-8 -*-
"""웹 AI 세션 관리자 - 작업 공간 서버 프로세스 안에서 돈다(docs/dev/web-session-design.md 2·3·9절). server.py 의 /api/wsession 이 쓴다.

작업 공간 하나 = 세션 하나. 시작은 사용자가 [세션 시작] 으로(자동 시작 없음).
  상태  off → ready(대기: 하트비트·요청 판정) → running(턴 실행 중) → ready | error(마지막 턴 실패 - 다음 묶음에 재시도) → off([끊기]·유휴 초과·서버 종료)
  턴    요청 묶음(requests_core.RequestTracker - watch_requests 와 같은 규칙) 하나 = 어댑터 한 번 실행(cwd = 작업 공간, 프롬프트는 stdin).
        첫 턴의 세션 id 로 다음 턴을 이어 간다(--resume / exec resume). 턴 시간 한도(sessionTurnMinutes)를 넘으면 프로세스 트리 종료 → error.
  하트비트 out/.studio/session.json 에 kind=web·agent·model·user 를 더해 쓴다 → 편집기 칩·status.py 가 그대로 본다.
        수동 감시(watch_requests)가 살아 있으면 시작을 거절하고, 웹 세션이 살아 있으면 watch_requests 도 거절한다(--takeover 로도 서버를 죽이지 않는다).
  동시 수 사용자 설정 폴더 hub/.studio/wsessions/<작업 공간 id>.json 에 살아 있는 세션을 등록 - PC 단위 sessionMax.
  로그  out/.studio/sessions/<시작 시각>/turn-N.jsonl(어댑터 출력 원문) · session.log. 토큰·키는 환경 변수로만.
  권한  웹 세션은 agents.web_settings()(permissions.json 의 workspace+web)를 --settings 로 넘긴다(claude). 금지 옵션은 어댑터가 넣지 않는다.
"""
import collections
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
from common import STATE, WORKSPACE, read_config  # noqa: E402
from paths import user_dir  # noqa: E402
import agents  # noqa: E402
import requests_core as rc  # noqa: E402

PROMPT_FILE = STUDIO / "agents" / "turn_prompt.md"
SESS_FILE = STATE / "wsession.json"           # 마지막 세션 정보(서버 재시작 뒤에도 "마지막" 표시용)
LOG_ROOT = STATE / "sessions"
REGISTRY = user_dir() / "hub" / ".studio" / "wsessions"
INTERVAL = 1.0


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def _ws_id():
    from hub import ws_id
    return ws_id(WORKSPACE)


def live_sessions():
    """PC 전체에서 살아 있는 웹 세션 [{ws, user, agent, model, started}] - 등록 파일의 하트비트가 신선한 것만(죽은 등록은 지운다)."""
    out = []
    if not REGISTRY.is_dir():
        return out
    for f in REGISTRY.glob("*.json"):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
            hb = json.loads(Path(r["heartbeat"]).read_text(encoding="utf-8"))
            fresh = hb.get("kind") == "web" and not hb.get("stopped") and time.time() - float(hb.get("ts", 0)) <= float(hb.get("interval", 1)) * rc.STALE_FACTOR + 2
        except (OSError, ValueError, KeyError):
            fresh = False
        if fresh:
            out.append(r)
        else:
            f.unlink(missing_ok=True)
    return out


class WebSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.state = "off"
        self.agent = self.model = self.model_actual = self.session_id = None
        self.started_by = self.started_at = None
        self.turns = 0
        self.last_error = None
        self.last_activity = 0.0
        self.pending_model = None
        self.limits, self.flags = {}, {}
        self.events = collections.deque(maxlen=1000)
        self.seq = 0
        self._thread = None
        self._stop = threading.Event()
        self._proc = None
        self._tracker = None
        self._hb = None
        self._log_dir = None
        self._turn_log = None
        self.last = self._read_json(SESS_FILE)

    # ---------- 정보 ----------
    @staticmethod
    def _read_json(p):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def info(self):
        with self.lock:
            st = rc.session_status()
            manual = None
            if st.get("connected") and st.get("kind") != "web":
                manual = {"label": st.get("label"), "pid": st.get("pid"), "mode": st.get("mode"), "last_seen": st.get("last_seen")}
            d = {"state": self.state, "agent": self.agent, "model": self.model, "modelActual": self.model_actual, "pendingModel": self.pending_model,
                 "sessionId": self.session_id, "startedBy": self.started_by, "startedAt": self.started_at, "turns": self.turns,
                 "lastError": self.last_error, "lastActivity": dt.datetime.fromtimestamp(self.last_activity).isoformat(timespec="seconds") if self.last_activity else None,
                 "open": st.get("open", 0), "working": st.get("working", 0), "manual": manual, "limits": self.limits, "seq": self.seq,
                 "logDir": str(self._log_dir) if self._log_dir else None}
            if self.state == "off":
                d["last"] = self.last or None
            return d

    def _save(self, **extra):
        self.last = {"agent": self.agent, "model": self.model, "modelActual": self.model_actual, "sessionId": self.session_id, "startedBy": self.started_by,
                     "startedAt": self.started_at, "turns": self.turns, "lastError": self.last_error, "logDir": str(self._log_dir) if self._log_dir else None, **extra}
        rc.write_json(SESS_FILE, self.last)

    def emit(self, kind, **kw):
        with self.lock:
            self.seq += 1
            ev = {"seq": self.seq, "t": _now(), "type": kind, **kw}
            self.events.append(ev)
        try:
            if self._log_dir:
                with open(self._log_dir / "session.log", "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return ev

    def events_since(self, since):
        with self.lock:
            return [e for e in self.events if e["seq"] > since]

    # ---------- 시작 · 끊기 · 모델 ----------
    def start(self, agent=None, model=None, user=None):
        with self.lock:
            if self.state != "off":
                raise ValueError(f"이미 세션이 있다({self.state}) - 먼저 끊는다")
            st = rc.session_status()
            if st.get("connected") and st.get("kind") != "web" and rc.pid_alive(st.get("pid")):  # 끝난 감시의 "끝남" 표시가 파일 경합으로 안 써졌을 수 있다 → pid 로 확인
                raise ValueError(f"수동 감시({st.get('label') or '?'}, pid {st.get('pid')})가 이 작업 공간을 맡고 있다 - 그 세션의 감시를 끝낸 뒤 시작한다")
            eff = agents.effective(read_config())
            agent = (agent or eff["agent"]).lower()
            model = str(model or eff["model"]).strip()
            if agent not in agents.AGENTS:
                raise ValueError(f"모르는 에이전트: {agent}")
            if not model:
                raise ValueError("모델을 준다")
            others = [s for s in live_sessions() if s.get("ws") != str(WORKSPACE)]
            smax = eff["limits"].get("sessionMax")
            smax = 3 if smax is None else int(smax)  # 0 도 뜻이 있다(웹 세션 금지)
            if len(others) >= smax:
                raise ValueError(f"이 PC 의 동시 세션 한도({smax})에 닿았다 - 다른 작업 공간의 세션을 먼저 끊는다: " + ", ".join(Path(s['ws']).name for s in others))
            ag = agents.get(agent)
            p = ag.probe()
            if not p["installed"]:
                raise ValueError(p["hint"] or f"{ag.label} 가 설치되어 있지 않다")
            if not p["loggedIn"]:
                raise ValueError(p["hint"] or f"{ag.label} 에 로그인되어 있지 않다")
            self.agent, self.model, self.flags, self.limits = agent, model, p.get("flags") or {}, eff["limits"]
            self.model_actual = self.session_id = self.last_error = self.pending_model = None
            self.started_by, self.started_at, self.turns = user or "local", _now(), 0
            self.last_activity = time.time()
            self._log_dir = LOG_ROOT / self.started_at.replace(":", "").replace("-", "")
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._settings_path = LOG_ROOT / "claude-settings.json"
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            self._settings_path.write_text(json.dumps(self._web_settings(), ensure_ascii=False, indent=1), encoding="utf-8")
            self._hb = {"pid": os.getpid(), "label": f"web:{agent}", "mode": "web", "interval": INTERVAL, "started": self.started_at,
                        "kind": "web", "agent": agent, "model": model, "user": self.started_by}
            REGISTRY.mkdir(parents=True, exist_ok=True)
            rc.write_json(REGISTRY / f"{_ws_id()}.json", {"ws": str(WORKSPACE), "heartbeat": str(rc.SESSION), "user": self.started_by, "agent": agent,
                                                          "model": model, "started": self.started_at, "pid": os.getpid()})
            self.state = "ready"
            self._stop.clear()
            self._tracker = rc.RequestTracker(quiet=8.0)
            rc.heartbeat(self._hb)
            self._save()
            self.emit("state", state="ready", agent=agent, model=model, user=self.started_by)
            self._thread = threading.Thread(target=self._loop, name="wsession", daemon=True)
            self._thread.start()
            return self.info()

    @staticmethod
    def _web_settings():
        """웹 세션 권한 JSON - 템플릿(workspace+web)에 이 작업 공간 실행기의 절대 경로 변형을 더한다.
        안내 파일(CLAUDE.md)이 `python3 <절대 경로>/nexa.py …` 로 적힌 작업 공간(허브가 만든 것)에서도 그 명령이 허용되게 - 다른 폴더의 nexa.py 는 여전히 거절."""
        s = agents.web_settings()
        allow = list(s["permissions"].get("allow", []))
        launcher = (WORKSPACE / "nexa.py")
        forms = {launcher.as_posix(), str(launcher)}
        for py in ("python3", "python"):
            for f in sorted(forms):
                for rule in (f"Bash({py} {f} *)", f'Bash({py} "{f}" *)'):
                    if rule not in allow:
                        allow.append(rule)
        s["permissions"]["allow"] = allow
        return s

    def stop(self, reason="user"):
        with self.lock:
            if self.state == "off":
                return self.info()
            self._stop.set()
            self._kill()
            th = self._thread
        if th and th is not threading.current_thread():
            th.join(timeout=8)
        with self.lock:
            self.state = "off"
            if self._hb:
                rc.heartbeat(self._hb, stopped=True)
            (REGISTRY / f"{_ws_id()}.json").unlink(missing_ok=True)
            self._save(stoppedAt=_now(), reason=reason)
            self.emit("state", state="off", reason=reason)
            self._thread = self._tracker = self._hb = None
            return self.info()

    def set_model(self, model):
        model = str(model or "").strip()
        if not model:
            raise ValueError("모델을 준다")
        with self.lock:
            if self.state == "off":
                raise ValueError("세션이 없다")
            if self.state == "running":
                self.pending_model = model  # 턴이 끝난 뒤 적용(사용자 결정)
                self.emit("model", model=model, pending=True)
            else:
                self.model, self.pending_model = model, None
                if self._hb:
                    self._hb["model"] = model
                self.emit("model", model=model, pending=False)
            self._save()
            return self.info()

    # ---------- 루프 ----------
    def _loop(self):
        try:
            while not self._stop.is_set():
                try:
                    rc.heartbeat(self._hb)
                    idle = float(self.limits.get("sessionIdleMinutes") or 60) * 60
                    if self.state in ("ready", "error") and time.time() - self.last_activity > idle:
                        self.emit("idle", minutes=idle / 60)
                        threading.Thread(target=self.stop, args=("idle",), daemon=True).start()
                        return
                    batch, reason = self._tracker.poll()
                    if batch and not self._stop.is_set():
                        self._turn(batch, reason)
                except Exception as e:  # noqa: BLE001 - 한 주기의 오류로 루프를 멈추지 않는다
                    with self.lock:
                        self.last_error = f"{type(e).__name__}: {e}"
                        self.state = "error"
                    self.emit("error", message=self.last_error)
                self._stop.wait(INTERVAL)
        finally:
            if self._hb:
                rc.heartbeat(self._hb, stopped=True)

    def _prompt(self, batch, reason):
        ag = agents.get(self.agent)
        tpl = PROMPT_FILE.read_text(encoding="utf-8")
        items = [rc.brief(r) for r in batch]
        return tpl.replace("{guide}", ag.guide_file).replace("{reason}", str(reason)).replace("{batch}", json.dumps(items, ensure_ascii=False, indent=1))

    def _turn(self, batch, reason):
        ag = agents.get(self.agent)
        with self.lock:
            if self.pending_model:
                self.model, self.pending_model = self.pending_model, None
                self._hb["model"] = self.model
                self.emit("model", model=self.model, pending=False)
            self.state = "running"
            self.turns += 1
            n = self.turns
            cmd = ag.turn_cmd(self.model, self.session_id, self._settings_path if self.agent == "claude" else None,
                              max_turns=self.limits.get("sessionMaxTurns"), budget_usd=self.limits.get("sessionBudgetUsd"), flags=self.flags)
            self._turn_log = self._log_dir / f"turn-{n}.jsonl"
        self.emit("turn.start", turn=n, count=len(batch), reason=reason, ids=[r["id"] for r in batch], model=self.model)
        env = {**os.environ, **ag.env(), "NEXA_SLIDE_WORKSPACE": str(WORKSPACE), "NEXA_SLIDE_SESSION": f"web:{self.agent}",
               "NEXA_SLIDE_USER": self.started_by or "local"}
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kw["start_new_session"] = True
        result, stderr_tail, rc_code = None, [], None
        try:
            proc = subprocess.Popen([str(c) for c in cmd], cwd=str(WORKSPACE), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, **kw)
            with self.lock:
                self._proc = proc
            try:
                proc.stdin.write(self._prompt(batch, reason).encode("utf-8"))
                proc.stdin.close()
            except OSError:
                pass

            def read_err():
                for line in iter(proc.stderr.readline, b""):
                    stderr_tail.append(line.decode("utf-8", "replace").rstrip())
                    if len(stderr_tail) > 50:
                        del stderr_tail[0]

            def read_out():
                nonlocal result
                with open(self._turn_log, "a", encoding="utf-8", newline="\n") as log:
                    for raw in iter(proc.stdout.readline, b""):
                        line = raw.decode("utf-8", "replace").rstrip("\r\n")
                        log.write(line + "\n")
                        ev = ag.parse(line)
                        for e in (ev if isinstance(ev, list) else [ev] if ev else []):
                            kind = e.pop("type")
                            if kind == "init":
                                with self.lock:
                                    self.session_id = e.get("sessionId") or self.session_id
                                    self.model_actual = e.get("model") or self.model_actual
                            elif kind == "result":
                                result = e
                                with self.lock:
                                    self.session_id = e.get("sessionId") or self.session_id
                                    self.model_actual = self.model_actual or e.get("model")  # init 의 모델이 우선(result 의 사용량 표에는 보조 모델도 섞인다)
                            if kind == "text":
                                e["text"] = e["text"][:400]
                            self.emit(kind, turn=n, **e)
            t_err = threading.Thread(target=read_err, daemon=True)
            t_out = threading.Thread(target=read_out, daemon=True)
            t_err.start()
            t_out.start()
            limit = float(self.limits.get("sessionTurnMinutes") or 20) * 60
            try:
                rc_code = proc.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                self.emit("error", turn=n, message=f"턴이 {limit / 60:.0f}분 안에 끝나지 않아 끝냈다")
                self._kill()
                rc_code = -1
            t_out.join(timeout=5)
            t_err.join(timeout=2)
        except OSError as e:
            rc_code = -2
            stderr_tail.append(str(e))
        finally:
            with self.lock:
                self._proc = None
        with self.lock:
            ok = rc_code == 0 and (result is None or result.get("ok", True))
            if ok:
                self.state, self.last_error = "ready", None
            else:
                self.state = "error" if not self._stop.is_set() else self.state
                self.last_error = (result or {}).get("text") or "\n".join(stderr_tail[-5:]) or f"종료 코드 {rc_code}"
                self.last_error = self.last_error[:500]
            self.last_activity = time.time()
            self._save()
        self.emit("turn.end", turn=n, ok=ok, code=rc_code, sessionId=self.session_id, model=self.model_actual,
                  costUsd=(result or {}).get("costUsd"), usage=(result or {}).get("usage"), error=None if ok else self.last_error)

    def _kill(self):
        proc = self._proc
        if not proc or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=15)
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:  # noqa: BLE001 - 이미 끝났으면 그만
            pass

    def turn_log(self, n):
        p = (self._log_dir or Path(self.last.get("logDir") or "")) / f"turn-{int(n)}.jsonl"
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return ""
