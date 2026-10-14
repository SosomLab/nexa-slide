# -*- coding: utf-8 -*-
"""Claude 세션용 덱 저장 - 덱 파일을 직접 덮어쓰는 대신 이것으로 저장하면 변경 원장에 "Claude(정확)" 로 남는다.

    python3 studio/save_deck.py <덱> --from <새 덱 JSON 파일> [--request <요청 id>] [--note "한 줄"] [--label "<세션 이름>"] [--force]
    cat new.json | python3 studio/save_deck.py <덱> --request r2026…
    실행기: python3 <작업 공간>/nexa.py save_deck <덱> --from …

동작
  - 서버가 떠 있으면 GET /api/deck/<덱> 의 X-Deck-Version 을 base 로 PUT /api/deck/<덱>?origin=claude&… 를 보낸다.
    백업(.history)·충돌 검사(409)·원장 기록을 서버가 한다. 409 면 "편집기가 그 사이 저장했다" - 다시 읽어 합치거나 --force.
  - 서버가 없으면 직접 백업하고 원자적으로 쓴 뒤 원장에 claude(정확) 줄을 남긴다(서버 기동 때 재대조와도 맞는다).
종료 코드: 0 저장됨 · 2 충돌(409) · 1 그 밖의 오류
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS, running_server, safe_id  # noqa: E402
import ledger  # noqa: E402


def load_new(src):
    raw = Path(src).read_text(encoding="utf-8") if src else sys.stdin.read()
    deck = json.loads(raw)
    if not isinstance(deck, dict) or not isinstance(deck.get("slides"), list):
        sys.exit("덱 형식이 아니다(slides 목록 필요)")
    return deck


def via_server(url, deck_id, deck, a):
    q = {"origin": "claude", "action": a.action}
    if a.request:
        q["request"] = a.request
    if a.note:
        q["note"] = a.note[:200]
    if a.label:
        q["label"] = a.label[:80]
    if a.force:
        q["force"] = "1"
    try:
        with urllib.request.urlopen(f"{url}api/deck/{deck_id}", timeout=10) as r:
            q["base"] = r.headers.get("X-Deck-Version") or ""
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        q["base"] = ""  # 새 덱
    body = json.dumps(deck, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Nexa-Tab": "save_deck"}
    if os.environ.get("NEXA_SLIDE_USER"):  # 웹 세션이 준 시작 사용자 - 서버는 로컬(중계 아님) 요청에서만 받아 원장 actor.user 에 적는다
        headers["X-Nexa-Session-User"] = os.environ["NEXA_SLIDE_USER"][:40]
    req = urllib.request.Request(f"{url}api/deck/{deck_id}?{urllib.parse.urlencode(q)}", data=body, method="PUT", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            res = json.loads(e.read().decode("utf-8"))
        except ValueError:
            res = {"error": str(e)}
        if e.code == 409:
            print(f"충돌: 편집기가 그 사이 {deck_id} 를 저장했다(버전 {res.get('version')}). 다시 읽어 합치거나 --force 로 덮어쓴다", file=sys.stderr)
            return 2
        print(f"저장 실패 {e.code}: {res.get('error')}", file=sys.stderr)
        return 1
    print(f"저장됨(서버 {url}): {deck_id} · 원장 seq {res.get('seq')} · 버전 {res.get('version')}")
    return 0


def direct(deck_id, deck, a):
    p = DECKS / f"{deck_id}.json"
    old_obj, before = None, {"ver": "0", "size": 0, "hash": None, "backup": None}
    if p.exists():
        h = DECKS / ".history" / deck_id
        h.mkdir(parents=True, exist_ok=True)
        name = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"
        shutil.copy2(p, h / name)
        data = p.read_bytes()
        before = {**ledger.meta(p, data), "backup": name}
        try:
            old_obj = json.loads(data.decode("utf-8"))
        except ValueError:
            old_obj = None
        files = sorted(h.glob("*.json"))
        for old in files[:-50]:
            old.unlink(missing_ok=True)
    deck["id"] = deck_id
    deck["updated"] = dt.datetime.now().isoformat(timespec="seconds")
    ledger.atomic_write(p, json.dumps(deck, ensure_ascii=False, indent=1))
    actor = {"label": a.label or "", "request": a.request, "note": a.note}
    if os.environ.get("NEXA_SLIDE_USER"):
        actor["user"] = os.environ["NEXA_SLIDE_USER"][:40]
    seq = ledger.record(deck_id, old_obj, before, deck, ledger.meta(p), "claude", "exact", a.action, actor)
    print(f"저장됨(직접 - 서버 없음): {p} · 원장 seq {seq}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Claude 세션용 덱 저장(변경 원장에 claude 로 기록)")
    ap.add_argument("deck")
    ap.add_argument("--from", dest="src", help="새 덱 JSON 파일(없으면 표준 입력)")
    ap.add_argument("--request", help="처리 중인 요청 id")
    ap.add_argument("--note", help="무엇을 했는지 한 줄(200자)")
    ap.add_argument("--label", default=os.environ.get("NEXA_SLIDE_SESSION", ""), help="세션 이름(기본 NEXA_SLIDE_SESSION)")
    ap.add_argument("--action", default="save", choices=("save", "restore"))
    ap.add_argument("--force", action="store_true", help="편집기가 그 사이 저장했어도 덮어쓴다")
    a = ap.parse_args()
    if not safe_id(a.deck):
        sys.exit("잘못된 덱 id")
    deck = load_new(a.src)
    if deck.get("id", a.deck) != a.deck:
        sys.exit(f"덱 id 불일치: 파일 {deck.get('id')} / 인자 {a.deck}")
    if not a.label:
        try:
            from watch_requests import session_status
            st = session_status()
            a.label = st.get("label") or "" if st.get("connected") else ""
        except Exception:  # noqa: BLE001
            a.label = ""
    run = running_server()
    if run:
        return via_server(run["url"], a.deck, deck, a)
    return direct(a.deck, deck, a)


if __name__ == "__main__":
    sys.exit(main())
