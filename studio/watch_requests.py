# -*- coding: utf-8 -*-
"""요청 메모 감시 — 편집기에서 남긴 열린(open) 요청을 Claude Code 세션에 전달한다.

    python3 studio/watch_requests.py --workspace <작업 공간> --stream   # 상시 감시(권장 — Monitor 도구용)
    python3 studio/watch_requests.py --workspace <작업 공간>            # 1회: 요청이 생기면 출력하고 끝(이전 방식)
    옵션: --quiet 8 (마지막 변경 뒤 조용히 기다릴 초) · --interval 1 (확인 주기 초) · --label <세션 이름>
          --force (이 작업 공간을 이미 다른 감시가 맡고 있어도 시작 — 기본은 거부)
          --takeover (살아 있는 이전 감시를 끝내고 넘겨받기 — Monitor 를 다시 걸 때)
          --ttl 1780 (이 초가 지나면 {"event":"ttl"} 한 줄을 내고 스스로 끝남. --stream 기본 1780 = Monitor 최대 30분보다 조금 짧게.
                      Monitor 가 만료되면 셸만 끝나고 python 이 남아 하트비트만 쓰는 "가짜 연결"을 막는다. 0 = 끝없이)

작업 공간 하나 = 감시 하나 = 세션 하나. 작업 공간(폴더·저장소)마다 그곳에서 연 Claude 세션이 자기 감시를 띄운다.
같은 작업 공간에 살아 있는 감시가 있으면 시작을 거부한다(같은 요청이 두 세션에 가지 않게) — 서버 안의 웹 세션도 같은 하트비트를 쓰므로 함께 거부된다.

출력(--stream): 요청 묶음마다 JSON 한 줄 — 표준 출력 한 줄 = Monitor 알림 하나.
    {"event": "requests", "reason": "quiet|flush", "count": 2, "items": [{"deck", "id", "slide", "element", "text"}]}
    reason=quiet  편집기에서 메모를 이어 남길 수 있게, 마지막 변경 뒤 --quiet 초 동안 조용해지면 내보낸다
    reason=flush  편집기 "지금 보내기" 버튼 — 기다리지 않고 바로 내보낸다(새 요청이 없으면 열린 요청 전체를 다시)
한 번 내보낸 요청은 내용이 바뀌거나 다시 열릴 때까지 다시 내보내지 않는다.

연결 상태: 확인할 때마다 <out>/.studio/session.json 에 하트비트를 쓴다. 서버(/api/session)가 이것으로
편집기 머리줄에 "세션 연결됨 / 처리 중 n / 연결 없음"을 표시한다. 감시가 멈추면(세션 종료·Monitor 만료)
하트비트가 끊겨 몇 초 안에 "연결 없음"으로 바뀐다.

판정 규칙·하트비트는 requests_core.py 에 있다(웹 세션 관리자와 공유). 세션 쪽 처리 순서(요청 1건): status=working → 덱 JSON 수정 → status=done, reply 작성 (docs/claude-session.md).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS  # noqa: E402
from requests_core import FLUSH, SESSION, STALE_FACTOR, RequestTracker, all_requests, brief, heartbeat, now, open_requests, session_status  # noqa: E402,F401 - 예전처럼 여기서도 가져다 쓴다(server·status·save_deck)


def _kill(pid):
    """이전 감시 프로세스를 자식까지 끝낸다(procutil.kill_tree - pyenv 같은 래퍼로 떠 있어도)."""
    try:
        import procutil
        procutil.kill_tree(pid)
    except Exception:  # noqa: BLE001 — 이미 끝났으면 그만
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", action="store_true", help="끝나지 않고 요청 묶음마다 JSON 한 줄을 출력")
    ap.add_argument("--quiet", type=float, default=8.0)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--label", default=os.environ.get("NEXA_SLIDE_SESSION", "Claude Code"))
    ap.add_argument("--force", action="store_true", help="다른 감시가 살아 있어도 시작")
    ap.add_argument("--takeover", action="store_true", help="살아 있는 이전 감시를 끝내고 넘겨받는다")
    ap.add_argument("--agent", default=None, help="이 감시를 띄운 AI(claude·codex …) - 세션 칩·카드에 표시. 기본: Claude Code 안이면 claude")
    ap.add_argument("--model", default=None, help="그 세션의 모델 ID(예: claude-fable-5-1) - 표시용. 기본: NEXA_SLIDE_MODEL/ANTHROPIC_MODEL")
    ap.add_argument("--ttl", type=float, default=None, help="이 초 뒤 스스로 끝남(--stream 기본 1780, 0=끝없이)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cur = session_status()
    if cur["connected"] and cur.get("kind") == "web":  # 서버 안의 웹 세션이 맡고 있다 - --takeover 로 서버를 죽이지 않고, --force 로도 겹치지 않게 거절
        print(json.dumps({"event": "refused", "reason": "web-session", "pid": cur["pid"], "label": cur["label"], "user": cur.get("user"),
                          "last_seen": cur["last_seen"], "workspace": str(DECKS.parent),
                          "message": "웹 세션이 이 작업 공간을 맡고 있다 - 허브(시작 페이지)나 Studio 세션 칩에서 끊은 뒤 시작한다"}, ensure_ascii=False), flush=True)
        sys.exit(2)
    if cur["connected"] and cur["pid"] not in (None, os.getpid()) and a.takeover:
        _kill(cur["pid"])
        time.sleep(0.5)
        cur = session_status()
        cur["connected"] = False  # 넘겨받음
    if cur["connected"] and cur["pid"] != os.getpid() and not a.force:
        # 표준 출력 = Monitor 알림이므로 거부 사유를 한 줄 이벤트로 남기고 끝낸다
        print(json.dumps({"event": "refused", "reason": "already-watched", "pid": cur["pid"], "label": cur["label"],
                          "last_seen": cur["last_seen"], "workspace": str(DECKS.parent)}, ensure_ascii=False), flush=True)
        sys.exit(2)

    hb = {"pid": os.getpid(), "label": a.label, "mode": "stream" if a.stream else "once",
          "interval": a.interval, "started": now(), "cwd": os.getcwd()}
    try:
        import procutil
        hb.update(procutil.session_meta(a.agent, a.model))  # agent·model·sessionId·entry - 세션 칩·카드에 모델·세션 ID
    except ImportError:
        pass
    ttl = a.ttl if a.ttl is not None else (1780 if a.stream else 0)
    t_end = time.time() + ttl if ttl else None
    tracker = RequestTracker(quiet=a.quiet)
    sw = None
    try:
        import procutil
        sw = procutil.StdoutWatch()
    except ImportError:
        pass
    try:
        while True:
            if a.stream and sw is not None and sw.closed():  # Monitor 를 건 세션이 닫혔다(몇 초 연속 + 실제 쓰기 실패로 확인) - 고아로 남지 않게 끝낸다
                return
            try:
                heartbeat(hb)
            except OSError as e:  # 하트비트 한 번 못 써도 감시는 계속
                print(f"하트비트 쓰기 실패(계속): {e}", file=sys.stderr, flush=True)
            batch, reason = tracker.poll()
            if batch:
                if a.stream:
                    print(json.dumps({"event": "requests", "reason": reason, "count": len(batch),
                                      "items": [brief(r) for r in batch]}, ensure_ascii=False), flush=True)
                else:
                    print(json.dumps(batch, ensure_ascii=False, indent=1), flush=True)
                    return
            if t_end and time.time() >= t_end:
                print(json.dumps({"event": "ttl", "seconds": ttl, "message": "감시 시간이 끝나 스스로 종료 — 같은 명령으로 다시 건다"},
                                 ensure_ascii=False), flush=True)
                return
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass
    except (BrokenPipeError, OSError) as e:
        print(f"감시 종료(출력 오류): {e}", file=sys.stderr, flush=True)
    finally:
        heartbeat(hb, stopped=True)


if __name__ == "__main__":
    main()
