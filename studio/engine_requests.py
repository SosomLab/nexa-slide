# -*- coding: utf-8 -*-
"""엔진 요청 큐 - 작업 공간 세션·사람·다른 세션이 nexa-slide 엔진 변경을 요청하고, 엔진 개발 세션(하나)이 순서대로 처리한다.
docs/dev/engine-request-design.md. 큐는 사용자 설정 폴더 hub/engine/requests.json(저장소 밖) - 여러 프로세스가 쓰므로 잠금 + 원자적 쓰기.

항목  {id, status, title, body, from: {kind: user|session|cli, ws, wsId, user, request, deck, slide}, evidence: [경로…], priority,
       created, updated, reply, branch, commit, test, appliedCommit, appliedAt, engineVersion, history: [{t, status, by}]}
상태  triage(세션이 넣음 - 관리자 승인 대기) → open → working → done → applied · rejected
      사람·CLI 가 넣은 것은 바로 open. 개발 세션이 꺼내면 working, 끝내면 done(+reply·commit) 또는 rejected. 관리자가 병합·재시작 뒤 applied.
"""
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filelock import FileLock  # noqa: E402
from paths import user_dir  # noqa: E402

ENGINE_DIR = user_dir() / "hub" / "engine"
QUEUE = ENGINE_DIR / "requests.json"
LOCK = ENGINE_DIR / "requests.lock"
STATUSES = ("triage", "open", "working", "done", "rejected", "applied")
TRANSITIONS = {"triage": ("open", "rejected"), "open": ("working", "rejected", "triage"), "working": ("done", "rejected", "open"),
               "done": ("applied", "open", "rejected"), "rejected": ("open",), "applied": ()}
MAX_BODY = 4000
ATTACH_DIR = ENGINE_DIR / "attach"  # 요청 첨부(허브 화면에서 올린 그림·파일) - <요청 id>/<파일>, 올리는 중에는 _new/<파일>
START_REQ = ENGINE_DIR / "start-request.json"  # 일반 사용자가 관리자에게 엔진 세션 시작을 요청한 기록 {at, by: [이름…], count}
HEARTBEAT = ENGINE_DIR / ".studio" / "session.json"  # 엔진 개발 세션(웹·수동)의 하트비트


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def _read():
    try:
        d = json.loads(QUEUE.read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("items"), list):
            return d
    except (OSError, ValueError):
        pass
    return {"next": 1, "items": []}


def _write(d):
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="requests.", suffix=".tmp", dir=str(ENGINE_DIR))
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, QUEUE)


def session_state():
    """엔진 개발 세션이 살아 있는가 - 하트비트 파일로 본다(허브 프로세스 밖의 CLI 도 쓴다). {connected, kind, label, agent, model}
    requests_core.heartbeat_status 와 같은 판정이지만 그 모듈은 작업 공간(common)을 요구해 여기서 다시 적는다."""
    import time
    try:
        hb = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"connected": False}
    age = time.time() - float(hb.get("ts", 0))
    alive = not hb.get("stopped") and age <= float(hb.get("interval", 1)) * 4 + 2
    if alive and hb.get("kind") == "manual" and hb.get("pid") and not pid_alive(hb["pid"]):  # 강제 종료돼 stopped 를 못 쓴 수동 감시
        alive = False
    return {"connected": alive, "age": round(age, 1), **{k: hb.get(k) for k in ("kind", "label", "agent", "model", "user", "pid", "cwd", "started", "sessionId", "entry")}}


def pid_alive(pid):
    """그 pid 가 살아 있는가(Windows 는 OpenProcess - os.kill(pid, 0) 은 Windows 에서 프로세스를 죽이므로 쓰지 않는다)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE - 끝났지만 핸들이 남아 열리는 프로세스는 죽은 것으로
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def pending_note(status="open"):
    """요청을 넣은 쪽에 돌려줄 안내 - 세션이 꺼져 있으면 처리되지 않는다는 말(넣는 것 자체는 세션이 없어도 된다)."""
    st = session_state()
    if st.get("connected"):
        return ""
    return "엔진 개발 세션이 꺼져 있어 관리자가 시작해야 처리됩니다" + (" (관리자 승인도 필요)" if status == "triage" else "")


def start_request():
    """관리자에게 보낸 세션 시작 요청(없으면 None)."""
    try:
        d = json.loads(START_REQ.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and d.get("at") else None
    except (OSError, ValueError):
        return None


def request_start(user):
    """일반 사용자가 [관리자에게 시작 요청] - 같은 요청은 묶는다(처음 시각 유지, 사용자 목록·횟수 누적)."""
    with FileLock(LOCK):
        d = start_request() or {"at": _now(), "by": [], "count": 0}
        if user and user not in d["by"]:
            d["by"].append(str(user)[:40])
        d["count"] = int(d.get("count") or 0) + 1
        d["last"] = _now()
        ENGINE_DIR.mkdir(parents=True, exist_ok=True)
        START_REQ.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d


def clear_start_request():
    try:
        START_REQ.unlink()
    except OSError:
        pass


def attach_files(rid):
    """요청의 첨부 파일 목록 [{path(절대), name, size}]."""
    d = ATTACH_DIR / str(rid)
    if not d.is_dir():
        return []
    return [{"path": str(p), "name": p.name, "size": p.stat().st_size} for p in sorted(d.iterdir()) if p.is_file()]


def claim_attachments(rid, names):
    """_new/ 에 올려 둔 파일을 요청 폴더로 옮기고 evidence 에 쓸 경로(사용자 설정 폴더 기준 상대) 목록을 돌려준다."""
    out = []
    src = ATTACH_DIR / "_new"
    dst = ATTACH_DIR / str(rid)
    for n in names or []:
        n = Path(str(n)).name
        p = src / n
        if not n or not p.is_file():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        os.replace(p, dst / n)
        out.append(f"attach/{rid}/{n}")
    return out


def load():
    """항목 목록(읽기만)."""
    return _read()["items"]


def get(rid):
    return next((x for x in load() if x.get("id") == int(rid)), None)


def counts():
    c = {s: 0 for s in STATUSES}
    for x in load():
        c[x.get("status", "open")] = c.get(x.get("status", "open"), 0) + 1
    return c


def add(title, body="", kind="user", user=None, ws=None, ws_id=None, request=None, deck=None, slide=None, evidence=None, priority=0):
    """요청을 넣는다. kind=session(작업 공간 세션이 넘김)은 triage, 그 밖은 open. 같은 작업 공간·같은 원 요청이 이미 열려 있으면 그 항목에 덧붙인다. 항목을 돌려준다."""
    title = " ".join(str(title or "").split())[:200]
    body = str(body or "")[:MAX_BODY]
    if not title:
        raise ValueError("제목을 준다")
    if kind not in ("user", "session", "cli"):
        raise ValueError("kind = user|session|cli")
    with FileLock(LOCK):
        d = _read()
        if ws and request:  # 중복 - 같은 작업 공간·같은 원 요청이 아직 열려 있으면 덧붙인다
            for x in d["items"]:
                if x.get("status") in ("triage", "open", "working") and (x.get("from") or {}).get("ws") == str(ws) and (x.get("from") or {}).get("request") == request:
                    x["body"] = (x.get("body") or "") + f"\n\n--- 덧붙임 {_now()} ---\n{body}"
                    x["updated"] = _now()
                    _write(d)
                    return x
        item = {"id": d["next"], "status": "triage" if kind == "session" else "open", "title": title, "body": body,
                "from": {"kind": kind, "ws": str(ws) if ws else None, "wsId": ws_id, "user": user, "request": request, "deck": deck, "slide": slide},
                "evidence": [str(e) for e in (evidence or [])][:10], "priority": int(priority or 0), "created": _now(), "updated": _now(),
                "reply": "", "branch": None, "commit": None, "test": None, "appliedCommit": None, "appliedAt": None, "engineVersion": None,
                "history": [{"t": _now(), "status": "triage" if kind == "session" else "open", "by": user or kind}]}
        d["next"] += 1
        d["items"].append(item)
        _write(d)
        return item


def update(rid, status=None, by=None, **fields):
    """상태 전이(TRANSITIONS 안에서만)와 필드 갱신(reply·branch·commit·test·appliedCommit·engineVersion·priority·title·body)."""
    with FileLock(LOCK):
        d = _read()
        x = next((x for x in d["items"] if x.get("id") == int(rid)), None)
        if not x:
            raise ValueError(f"없는 요청: {rid}")
        if status:
            if status not in STATUSES:
                raise ValueError(f"상태는 {'|'.join(STATUSES)}")
            if status != x["status"] and status not in TRANSITIONS.get(x["status"], ()):
                raise ValueError(f"{x['status']} → {status} 로 바꿀 수 없다")
            if status != x["status"]:
                x["status"] = status
                x["history"].append({"t": _now(), "status": status, "by": by or "?"})
                if status == "applied":
                    x["appliedAt"] = _now()
        for k, v in fields.items():
            if k in ("reply", "branch", "commit", "test", "appliedCommit", "engineVersion", "title", "body") and v is not None:
                x[k] = str(v)[:MAX_BODY if k == "body" else 500]
            elif k == "priority" and v is not None:
                x["priority"] = int(v)
            elif k == "evidence" and v is not None:  # 첨부를 요청 폴더로 옮긴 뒤 경로를 덧붙일 때
                x["evidence"] = [str(e) for e in v][:20]
        x["updated"] = _now()
        _write(d)
        return x


def next_open():
    """개발 세션이 다음에 처리할 요청 - open 중 priority 큰 것, 같으면 먼저 들어온 것. working 이 있으면 그것(한 번에 하나)."""
    items = load()
    w = [x for x in items if x.get("status") == "working"]
    if w:
        return w[0]
    o = sorted((x for x in items if x.get("status") == "open"), key=lambda x: (-int(x.get("priority") or 0), x["id"]))
    return o[0] if o else None


def remove(rid):
    with FileLock(LOCK):
        d = _read()
        n = len(d["items"])
        d["items"] = [x for x in d["items"] if x.get("id") != int(rid)]
        if len(d["items"]) == n:
            raise ValueError(f"없는 요청: {rid}")
        _write(d)
    import shutil
    shutil.rmtree(ATTACH_DIR / str(int(rid)), ignore_errors=True)  # 첨부도 같이(남으면 고아)


def tidy_scan(new_age_hours=24):
    """첨부 정리 보고 - 큐에 없는 요청의 attach/<id>/ 와, 올려만 두고 요청에 붙지 않은 _new/ 파일(new_age_hours 보다 오래된 것)."""
    import time
    ids = {str(x.get("id")) for x in load()}
    items = []
    if ATTACH_DIR.is_dir():
        now = time.time()
        for d in sorted(ATTACH_DIR.iterdir()):
            if d.name == "_new":
                for f in sorted(d.iterdir()):
                    if f.is_file() and now - f.stat().st_mtime > new_age_hours * 3600:
                        items.append({"path": f"attach/_new/{f.name}", "size": f.stat().st_size, "reason": "요청에 붙지 않은 올린 파일(하루 지남)"})
            elif d.is_dir() and d.name not in ids:
                size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                items.append({"path": f"attach/{d.name}", "size": size, "reason": f"큐에 없는 요청 #{d.name} 의 첨부"})
    return {"items": items, "total": sum(i["size"] for i in items)}


def tidy_clean(new_age_hours=24):
    """tidy_scan 이 보고한 것을 지운다 → {removed, size}."""
    import shutil
    rep = tidy_scan(new_age_hours)
    n = size = 0
    for it in rep["items"]:
        p = ENGINE_DIR / it["path"]
        try:
            if p.is_dir():
                shutil.rmtree(p)
            elif p.is_file():
                p.unlink()
            n += 1; size += it["size"]
        except OSError:
            continue
    return {"removed": n, "size": size}
