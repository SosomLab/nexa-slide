# -*- coding: utf-8 -*-
"""수동 엔진 개발 세션 - 터미널의 Claude Code 세션이 엔진 요청 큐를 맡는다(웹 엔진 세션 대신). docs/dev/engine-request-design.md 수동 세션 절.

    python3 studio/watch_engine_requests.py --stream [--label "<이름>"]     # Monitor 로 실행 - 처리할 요청(open)이 생길 때마다 JSON 한 줄
    python3 studio/watch_engine_requests.py                                 # 1회: 지금 대기 중인 요청을 출력하고 끝

하트비트: 사용자 설정 폴더 hub/engine/.studio/session.json (kind=manual) - 시작 페이지 "서버 작업" 카드가 "수동 세션 · <이름>" 으로 보이고,
허브의 [세션 시작](웹 엔진 세션)은 이 감시가 살아 있는 동안 거절된다. 웹 엔진 세션이 살아 있으면 이 감시가 거절된다.
이벤트: {"event":"request","item":{id,title,body,from,evidence,…},"triage":n}  - 처리는 docs/dev/engine-request-design.md 의 순서대로
         (worktree 에서 구현 → 검증 → 커밋 → python3 studio/engine_request.py status <id> done …). 승인 대기(triage)는 관리자가 카드에서 승인한다.
작업 공간이 없어도 된다(엔진 저장소 어디서나).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_requests as q  # noqa: E402

INTERVAL = 1.0


def _beat(hb, stopped=False):
    q.HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    tmp = q.HEARTBEAT.with_name(q.HEARTBEAT.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({**hb, "ts": time.time(), "last_seen": time.strftime("%Y-%m-%dT%H:%M:%S"), **({"stopped": True} if stopped else {})}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, q.HEARTBEAT)


_pid_alive = q.pid_alive


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="수동 엔진 개발 세션 - 엔진 요청 큐 감시")
    ap.add_argument("--stream", action="store_true", help="끝나지 않고 처리할 요청이 생길 때마다 JSON 한 줄")
    ap.add_argument("--label", default=os.environ.get("NEXA_SLIDE_SESSION") or "Claude Code")
    ap.add_argument("--takeover", action="store_true", help="살아 있는 이전 수동 감시를 넘겨받는다(웹 엔진 세션은 넘겨받지 않는다)")
    ap.add_argument("--ttl", type=float, default=None, help="이 초 뒤 스스로 끝남(--stream 기본 1780, 0=끝없이)")
    a = ap.parse_args()
    cur = q.session_state()
    if cur.get("connected") and cur.get("kind") == "engine" and _pid_alive(cur.get("pid")):
        print(json.dumps({"event": "refused", "reason": "web-engine-session", "pid": cur.get("pid"), "label": cur.get("label"),
                          "hint": "허브가 띄운 웹 엔진 세션이 큐를 맡고 있다 - 시작 페이지 서버 작업 카드에서 [세션 중지] 뒤 다시"}, ensure_ascii=False), flush=True)
        return 2
    if cur.get("connected") and cur.get("pid") not in (None, os.getpid()) and _pid_alive(cur.get("pid")) and not a.takeover:
        print(json.dumps({"event": "refused", "reason": "already-watched", "pid": cur.get("pid"), "label": cur.get("label"),
                          "hint": "--takeover 로 넘겨받는다"}, ensure_ascii=False), flush=True)
        return 2
    hb = {"pid": os.getpid(), "label": a.label, "mode": "stream" if a.stream else "once", "interval": INTERVAL, "kind": "manual",
          "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "cwd": os.getcwd(), "user": os.environ.get("NEXA_SLIDE_USER") or os.environ.get("USERNAME") or "local"}
    ttl = a.ttl if a.ttl is not None else (1780 if a.stream else 0)
    t0 = time.time()
    emitted = {}  # id → updated(변경이 있으면 다시 알린다)
    try:
        while True:
            _beat(hb)
            c = q.counts()
            fresh = []
            for x in q.load():
                if x.get("status") == "open" and emitted.get(x["id"]) != x.get("updated"):
                    emitted[x["id"]] = x.get("updated")
                    fresh.append(x)
            for x in fresh:
                show = {k: x.get(k) for k in ("id", "title", "body", "from", "evidence", "priority", "created", "reply")}
                show["attachments"] = [f["path"] for f in q.attach_files(x["id"])]
                print(json.dumps({"event": "request", "item": show, "open": c.get("open", 0), "triage": c.get("triage", 0)}, ensure_ascii=False), flush=True)
            if not a.stream:
                if not fresh:
                    print(json.dumps({"event": "idle", "open": c.get("open", 0), "triage": c.get("triage", 0)}, ensure_ascii=False), flush=True)
                return 0
            if ttl and time.time() - t0 > ttl:
                print(json.dumps({"event": "expired", "ttl": ttl, "hint": "다시 실행하면 이어진다"}, ensure_ascii=False), flush=True)
                return 0
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            _beat(hb, stopped=True)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
