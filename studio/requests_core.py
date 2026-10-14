# -*- coding: utf-8 -*-
"""요청 메모 판정 - 편집기가 남긴 요청(decks/<덱>.requests.json) · "지금 보내기"(out/.studio/flush.json) · 세션 하트비트(out/.studio/session.json).

watch_requests.py(수동 세션 - Monitor 로 실행)와 서버 안의 웹 세션 관리자가 **같은 규칙**을 쓰도록 한 곳에 둔다.
규칙(docs/claude-session.md 2절):
  - 열린(open) 요청만 본다. 한 번 보낸 요청은 내용(text·slide·element)이 바뀌거나 다시 열릴(done → open) 때까지 다시 보내지 않는다.
  - flush(편집기 "지금 보내기")면 바로 보낸다 - 새 요청이 없으면 열린 요청 전체를 다시.
  - 아니면 마지막 변경 뒤 quiet 초(기본 8) 동안 조용할 때 보낸다(메모를 이어 남길 시간).
하트비트: 확인할 때마다 session.json 에 {pid, label, mode, interval, started, ts, last_seen[, stopped]} - 서버(/api/session)가 연결 여부를 판정한다.
"""
import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS, STATE  # noqa: E402

SESSION = STATE / "session.json"
FLUSH = STATE / "flush.json"
STALE_FACTOR = 4  # 하트비트가 interval × 4 (+2초) 넘게 끊기면 연결 없음


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def all_requests():
    out = []
    for p in sorted(DECKS.glob("*.requests.json")):
        try:
            rs = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # 저장 중인 파일은 다음 확인 때 다시 읽는다
        deck = p.name.split(".")[0]
        out += [{"deck": deck, **r} for r in rs]
    return out


def open_requests():
    return [r for r in all_requests() if r.get("status") == "open"]


def request_key(r):
    """보낸 내용의 지문 - 이것이 바뀌면 다시 보낸다."""
    return hashlib.sha1(json.dumps([r.get("deck"), r.get("id"), r.get("text"), r.get("slide"), r.get("element")],
                                   ensure_ascii=False).encode("utf-8")).hexdigest()


CONTEXT_MAX, CONTEXT_CHARS = 6, 800  # 후속 요청에 붙이는 앞선 대화 - 최대 항목 수 · 항목당 글자 수


def thread_context(r):
    """후속 요청(thread)이면 같은 thread 의 앞선 요청들 [{id, text, reply, status, attachments?}] - 오래된 것부터, 최근 CONTEXT_MAX 개."""
    th = r.get("thread")
    if not th or not r.get("deck"):
        return []
    try:
        rs = json.loads((DECKS / f"{r['deck']}.requests.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    prev = [x for x in rs if (x.get("id") == th or x.get("thread") == th) and x.get("id") != r.get("id") and str(x.get("created", "")) <= str(r.get("created", "~"))]
    prev.sort(key=lambda x: (str(x.get("created", "")), str(x.get("id"))))
    out = []
    for x in prev[-CONTEXT_MAX:]:
        c = {"id": x.get("id"), "status": x.get("status"), "text": str(x.get("text") or "")[:CONTEXT_CHARS], "reply": str(x.get("reply") or "")[:CONTEXT_CHARS]}
        if x.get("attachments"):
            c["attachments"] = [a.get("path") for a in x["attachments"] if isinstance(a, dict)]
        out.append(c)
    return out


def brief(r):
    """세션에 넘기는 요약 - deck·id·slide·element·text(·region·attachments). 후속 요청이면 parent·thread 와 앞선 대화 context."""
    out = {k: r.get(k) for k in ("deck", "id", "slide", "element", "text")}
    if r.get("thread"):
        out["parent"], out["thread"] = r.get("parent"), r["thread"]
        out["context"] = thread_context(r)
    if r.get("region"):
        out["region"] = r["region"]
    if r.get("attachments"):  # 첨부(클립보드 그림·파일) - 작업 공간 안 경로(out/attach/<덱>/…), 세션이 Read 로 본다
        out["attachments"] = [{k: a.get(k) for k in ("path", "name", "type", "size")} for a in r["attachments"] if isinstance(a, dict)]
    return out


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:  # Windows 에서 서버가 읽는 순간과 겹치면 다음 주기에 다시 쓴다
        tmp.unlink(missing_ok=True)


def heartbeat(hb, stopped=False, path=None):
    """하트비트 한 번 - hb 는 {pid, label, mode, interval, started, …}. stopped 면 끝났다는 표시(연결 없음으로 바로 바뀐다). path 로 다른 파일에(엔진 세션)."""
    write_json(Path(path) if path else SESSION, {**hb, "ts": time.time(), "last_seen": now(), **({"stopped": True} if stopped else {})})


def heartbeat_status(path):
    """하트비트 파일 하나의 연결 여부 {connected, kind, label, agent, model, user, pid, last_seen, age} - 작업 공간 밖(엔진 세션)용."""
    try:
        hb = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"connected": False}
    age = time.time() - float(hb.get("ts", 0))
    return {"connected": not hb.get("stopped") and age <= float(hb.get("interval", 1)) * STALE_FACTOR + 2, "age": round(age, 1),
            **{k: hb.get(k) for k in ("kind", "label", "agent", "model", "user", "pid", "last_seen", "started")}}


def pid_alive(pid):
    """그 pid 의 프로세스가 살아 있는가. Windows 는 OpenProcess 로 묻는다 - os.kill(pid, 0) 은 Windows 에서 프로세스를 죽이므로 쓰지 않는다."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def session_status():
    """서버·편집기용 — 감시 하트비트와 요청 상태를 묶어 돌려준다."""
    reqs = all_requests()
    st = {"connected": False, "label": "", "mode": "", "last_seen": "", "age": None, "pid": None,
          "open": sum(r.get("status") == "open" for r in reqs),
          "working": sum(r.get("status") == "working" for r in reqs)}
    try:
        hb = json.loads(SESSION.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return st
    age = time.time() - float(hb.get("ts", 0))
    st.update(pid=hb.get("pid"), label=hb.get("label", ""), mode=hb.get("mode", ""), last_seen=hb.get("last_seen", ""), age=round(age, 1),
              connected=not hb.get("stopped") and age <= float(hb.get("interval", 1)) * STALE_FACTOR + 2)
    for k in ("kind", "agent", "model", "user", "state", "turn", "allowWeb"):  # 웹 세션이 더 적는 값(없으면 빠진다) - state=running 이면 턴 실행 중
        if hb.get(k) is not None:
            st[k] = hb[k]
    if not st["connected"]:  # 마지막 웹 세션이 왜 끝났는지(서버 재시작·유휴·사용자) - 편집기가 "세션 종료됨" 안내에 쓴다
        try:
            last = json.loads((STATE / "wsession.json").read_text(encoding="utf-8"))
            st["last"] = {k: last.get(k) for k in ("agent", "model", "startedBy", "stoppedAt", "reason")}
        except (OSError, ValueError):
            pass
    return st


class RequestTracker:
    """요청 묶음 판정 - 주기마다 poll() 을 부르면 보낼 묶음이 있을 때 (목록, 이유) 를, 없으면 (None, None) 을 돌려준다.
    이유: "flush"(지금 보내기) · "quiet"(마지막 변경 뒤 quiet 초 조용함)."""

    def __init__(self, quiet=8.0):
        self.quiet = quiet
        self.emitted = {}  # 요청 id → 보낸 내용 키
        self.last_key, self.since = None, None
        self.flush_seen = FLUSH.stat().st_mtime_ns if FLUSH.exists() else 0

    def poll(self):
        cur = open_requests()
        ids = {r["id"] for r in cur}
        for rid in list(self.emitted):  # 처리됐거나 지워진 요청은 잊는다 → 다시 열리면 다시 보낸다
            if rid not in ids:
                del self.emitted[rid]
        pending = [r for r in cur if self.emitted.get(r["id"]) != request_key(r)]

        fm = FLUSH.stat().st_mtime_ns if FLUSH.exists() else 0
        flush = fm > self.flush_seen
        self.flush_seen = max(self.flush_seen, fm)

        batch, reason = None, None
        if flush and (pending or cur):
            batch, reason = (pending or cur), "flush"
        elif pending:
            key = json.dumps(sorted(request_key(r) for r in pending))
            if key != self.last_key:
                self.last_key, self.since = key, time.time()
            elif time.time() - self.since >= self.quiet:
                batch, reason = pending, "quiet"
        else:
            self.last_key, self.since = None, None

        if batch:
            for r in batch:
                self.emitted[r["id"]] = request_key(r)
            self.last_key, self.since = None, None
        return batch, reason
