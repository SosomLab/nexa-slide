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
