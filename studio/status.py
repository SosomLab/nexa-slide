# -*- coding: utf-8 -*-
"""작업 공간 상태 — 실행 중 서버(포트·URL)와 Claude 세션 감시 연결을 한눈에 본다 (DB·서버 변경 없음).

    python3 studio/status.py --workspace <작업 공간>
    python3 studio/status.py --workspace <작업 공간> --json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, DECKS, DEFAULT_PORT, HUB, REFUSED, SERVER_INFO, WORKSPACE, running_server  # noqa: E402
from watch_requests import session_status  # noqa: E402


def server_info():
    run = running_server()
    if run:
        return {**run, "running": True}
    try:
        info = json.loads(SERVER_INFO.read_text(encoding="utf-8"))
        return {**info, "running": False, "note": "server.json 은 남아 있지만 응답 없음(비정상 종료)"}
    except (OSError, ValueError):
        return {"running": False}


def main():
    sv, ss = server_info(), session_status()
    decks = sorted(p.stem for p in DECKS.glob("*.json") if not p.name.endswith(".requests.json"))
    out = {"workspace": "" if HUB else str(WORKSPACE), "mode": "hub" if HUB else "workspace",
           "title": "nexa-slide 시작 페이지" if HUB else CONFIG.get("title", WORKSPACE.name), "port": DEFAULT_PORT,
           "server": sv, "session": ss, "decks": decks}
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    if HUB:
        print("작업 공간  (없음 — 허브: 시작 페이지)" + (f" · 엔진 폴더 안이라 열지 않음: {REFUSED}" if REFUSED else ""))
    else:
        print(f"작업 공간  {out['title']}  ({WORKSPACE})")
    print(f"덱        {', '.join(decks) or '(없음)'}")
    if sv.get("running"):
        print(f"서버      실행 중 {sv['url']}  pid {sv['pid']} · {sv['started']}")
    else:
        print(f"서버      꺼짐 (설정 포트 {DEFAULT_PORT}){' — ' + sv['note'] if sv.get('note') else ''}")
    if ss["connected"]:
        print(f"세션      연결됨 — {ss['label']} (pid {ss['pid']}, {ss['age']}초 전) · 대기 {ss['open']} · 처리 중 {ss['working']}")
    else:
        print(f"세션      연결 없음{' — 마지막 ' + ss['last_seen'] if ss['last_seen'] else ''} · 대기 {ss['open']} · 처리 중 {ss['working']}")


if __name__ == "__main__":
    main()
