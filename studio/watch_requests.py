# -*- coding: utf-8 -*-
"""요청 메모 감시 — 편집기에서 남긴 열린(open) 요청을 Claude Code 세션에 전달한다.

    python3 studio/watch_requests.py --workspace <작업 공간> --stream   # 상시 감시(권장 — Monitor 도구용)
    python3 studio/watch_requests.py --workspace <작업 공간>            # 1회: 요청이 생기면 출력하고 끝(이전 방식)
    옵션: --quiet 8 (마지막 변경 뒤 조용히 기다릴 초) · --interval 1 (확인 주기 초) · --label <세션 이름>
          --force (이 작업 공간을 이미 다른 감시가 맡고 있어도 시작 — 기본은 거부)

작업 공간 하나 = 감시 하나 = 세션 하나. 작업 공간(폴더·저장소)마다 그곳에서 연 Claude 세션이 자기 감시를 띄운다.
같은 작업 공간에 살아 있는 감시가 있으면 시작을 거부한다(같은 요청이 두 세션에 가지 않게).

출력(--stream): 요청 묶음마다 JSON 한 줄 — 표준 출력 한 줄 = Monitor 알림 하나.
    {"event": "requests", "reason": "quiet|flush", "count": 2, "items": [{"deck", "id", "slide", "element", "text"}]}
    reason=quiet  편집기에서 메모를 이어 남길 수 있게, 마지막 변경 뒤 --quiet 초 동안 조용해지면 내보낸다
    reason=flush  편집기 "지금 보내기" 버튼 — 기다리지 않고 바로 내보낸다(새 요청이 없으면 열린 요청 전체를 다시)
한 번 내보낸 요청은 내용이 바뀌거나 다시 열릴 때까지 다시 내보내지 않는다.

연결 상태: 확인할 때마다 <out>/.studio/session.json 에 하트비트를 쓴다. 서버(/api/session)가 이것으로
편집기 머리줄에 "세션 연결됨 / 처리 중 n / 연결 없음"을 표시한다. 감시가 멈추면(세션 종료·Monitor 만료)
하트비트가 끊겨 몇 초 안에 "연결 없음"으로 바뀐다.

세션 쪽 처리 순서(요청 1건): status=working → 덱 JSON 수정 → status=done, reply 작성 (docs/claude-session.md).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS, STATE  # noqa: E402

SESSION = STATE / "session.json"
FLUSH = STATE / "flush.json"
STALE_FACTOR = 4  # 하트비트가 interval × 4 (+2초) 넘게 끊기면 연결 없음


def _now():
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


def _key(r):
    return hashlib.sha1(json.dumps([r.get("deck"), r.get("id"), r.get("text"), r.get("slide"), r.get("element")],
                                   ensure_ascii=False).encode("utf-8")).hexdigest()


def _brief(r):
    return {k: r.get(k) for k in ("deck", "id", "slide", "element", "text")}


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:  # Windows 에서 서버가 읽는 순간과 겹치면 다음 주기에 다시 쓴다
        tmp.unlink(missing_ok=True)


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
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", action="store_true", help="끝나지 않고 요청 묶음마다 JSON 한 줄을 출력")
    ap.add_argument("--quiet", type=float, default=8.0)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--label", default=os.environ.get("NEXA_SLIDE_SESSION", "Claude Code"))
    ap.add_argument("--force", action="store_true", help="다른 감시가 살아 있어도 시작")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cur = session_status()
    if cur["connected"] and cur["pid"] != os.getpid() and not a.force:
        # 표준 출력 = Monitor 알림이므로 거부 사유를 한 줄 이벤트로 남기고 끝낸다
        print(json.dumps({"event": "refused", "reason": "already-watched", "pid": cur["pid"], "label": cur["label"],
                          "last_seen": cur["last_seen"], "workspace": str(DECKS.parent)}, ensure_ascii=False), flush=True)
        sys.exit(2)

    hb = {"pid": os.getpid(), "label": a.label, "mode": "stream" if a.stream else "once",
          "interval": a.interval, "started": _now()}
    emitted = {}  # 요청 id → 내보낸 내용 키
    last_key, since = None, None
    flush_seen = FLUSH.stat().st_mtime_ns if FLUSH.exists() else 0
    try:
        while True:
            _write_json(SESSION, {**hb, "ts": time.time(), "last_seen": _now()})
            cur = open_requests()
            ids = {r["id"] for r in cur}
            for rid in list(emitted):  # 처리됐거나 지워진 요청은 잊는다 → 다시 열리면 다시 내보낸다
                if rid not in ids:
                    del emitted[rid]
            pending = [r for r in cur if emitted.get(r["id"]) != _key(r)]

            fm = FLUSH.stat().st_mtime_ns if FLUSH.exists() else 0
            flush = fm > flush_seen
            flush_seen = max(flush_seen, fm)

            batch, reason = None, None
            if flush and (pending or cur):
                batch, reason = (pending or cur), "flush"
            elif pending:
                key = json.dumps(sorted(_key(r) for r in pending))
                if key != last_key:
                    last_key, since = key, time.time()
                elif time.time() - since >= a.quiet:
                    batch, reason = pending, "quiet"
            else:
                last_key, since = None, None

            if batch:
                for r in batch:
                    emitted[r["id"]] = _key(r)
                last_key, since = None, None
                if a.stream:
                    print(json.dumps({"event": "requests", "reason": reason, "count": len(batch),
                                      "items": [_brief(r) for r in batch]}, ensure_ascii=False), flush=True)
                else:
                    print(json.dumps(batch, ensure_ascii=False, indent=1), flush=True)
                    return
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass
    finally:
        _write_json(SESSION, {**hb, "ts": time.time(), "last_seen": _now(), "stopped": True})


if __name__ == "__main__":
    main()
