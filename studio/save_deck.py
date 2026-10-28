# -*- coding: utf-8 -*-
"""Claude 세션용 덱 저장 - 덱 파일을 직접 덮어쓰는 대신 이것으로 저장하면 변경 원장에 "Claude(정확)" 로 남는다.

    python3 studio/save_deck.py <덱> --from <새 덱 JSON 파일> [--request <요청 id>] [--note "한 줄"] [--label "<세션 이름>"] [--force]
    cat new.json | python3 studio/save_deck.py <덱> --request r2026…
    실행기: python3 <작업 공간>/nexa.py save_deck <덱> --from …

동작
  - 서버가 떠 있으면 PUT /api/deck/<덱>?origin=claude&base=<기준 버전>&merge=1 을 보낸다. 백업(.history)·병합·원장 기록을 서버가 한다.
    기준 버전은 --from 이 draft_deck 사본이면 **사본을 만든 때의 버전**(out/.studio/draft-<덱>.base), 아니면 저장 직전 GET 의 X-Deck-Version.
  - **병합 저장(기본, docs/collab.md 1단계)**: 사본을 만든 뒤 편집기가 저장했으면 서버가 3-way 병합(deckmerge.py)으로 합친다.
    사람과 AI 가 같은 곳(요소 속성·셀)을 다르게 고쳤으면 **사람이 이긴다** - 진 AI 변경은 출력의 "충돌" 줄로 알려 주니 reply 에 적는다.
    기준본은 서버가 기억한 그 판, 없으면 사본과 함께 만든 원본(draft-<덱>.orig.json)을 보낸다. 병합되면 사본을 병합 결과로 바꿔 이어 고칠 수 있다.
    --no-merge 면 예전처럼 409(종료 코드 2)로 멈춘다. --force 는 덮어쓴다(사람의 변경을 지운다 - 꼭 필요할 때만).
  - 서버가 없으면 같은 병합을 여기서 하고, 백업한 뒤 원자적으로 쓰고 원장에 claude(정확) 줄을 남긴다(서버 기동 때 재대조와도 맞는다).
종료 코드: 0 저장됨(병합 포함) · 2 충돌(409 - 병합할 수 없거나 --no-merge) · 1 그 밖의 오류
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
from common import DECKS, STATE, running_server, safe_id  # noqa: E402
import deckmerge  # noqa: E402
import ledger  # noqa: E402


def load_new(src):
    raw = Path(src).read_text(encoding="utf-8") if src else sys.stdin.read()
    deck = json.loads(raw)
    if not isinstance(deck, dict) or not isinstance(deck.get("slides"), list):
        sys.exit("덱 형식이 아니다(slides 목록 필요)")
    if deck.get("kind") == "sheet" and not (isinstance(deck.get("sheets"), list) and deck["sheets"]
                                            and all(isinstance(t, dict) and t.get("id") and isinstance(t.get("cells", {}), dict) for t in deck["sheets"])):
        sys.exit("시트 형식이 아니다(sheets 목록, 탭마다 id·cells 필요 - docs/sheets.md)")
    return deck


def draft_base(deck_id, src):
    """--from 이 draft_deck 사본(out/.studio/draft-<덱>.json)이면 (.base 경로, 사본을 만든 때의 버전), 아니면 (None, None)."""
    if not src:
        return None, None
    try:
        same = Path(src).resolve() == (STATE / f"draft-{deck_id}.json").resolve()
    except OSError:
        same = False
    bp = STATE / f"draft-{deck_id}.base"
    if not same or not bp.is_file():
        return None, None
    return bp, bp.read_text(encoding="utf-8").strip() or None


def draft_orig(deck_id, bp):
    """사본을 만든 때의 원본(draft_deck 이 남김) - 병합 기준본. 사본 저장이 아니거나 없으면 None."""
    o = STATE / f"draft-{deck_id}.orig.json"
    if not bp or not o.is_file():
        return None
    try:
        return json.loads(o.read_text(encoding="utf-8"))
    except ValueError:
        return None


def after_merge(deck_id, bp, merged):
    """병합 저장 뒤 - 사본·원본을 병합 결과로 바꿔, 같은 사본으로 이어 고쳐 저장해도 사람의 변경을 되돌리지 않게."""
    if not bp or not isinstance(merged, dict):
        return
    text = json.dumps(merged, ensure_ascii=False, indent=1) + "\n"
    (STATE / f"draft-{deck_id}.json").write_text(text, encoding="utf-8", newline="\n")
    (STATE / f"draft-{deck_id}.orig.json").write_text(text, encoding="utf-8", newline="\n")


def show_conflicts(conflicts):
    if conflicts:
        print(f"충돌 {len(conflicts)}건 - 사람이 같은 곳을 고쳐 사람의 값을 남겼다(reply 에 알려 줄 것):")
        for line in deckmerge.describe(conflicts, 12):
            print("  " + line)


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
    elif not a.no_merge:
        q["merge"] = "1"
    bp, base = draft_base(deck_id, a.src)
    if base:
        q["base"] = base
    else:
        try:
            with urllib.request.urlopen(f"{url}api/deck/{deck_id}", timeout=10) as r:
                q["base"] = r.headers.get("X-Deck-Version") or ""
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            q["base"] = ""  # 새 덱
    orig = draft_orig(deck_id, bp) if q.get("merge") else None
    body = json.dumps({**deck, "__base": orig} if orig else deck, ensure_ascii=False).encode("utf-8")  # __base = 서버가 그 판을 기억하지 못할 때의 기준본
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
            print(f"충돌: 사본을 만든 뒤 편집기가 {deck_id} 를 저장했다(버전 {res.get('version')}) - "
                  + ("병합할 기준본이 없어 " if res.get("reason") == "no-base" else "")
                  + "사람의 변경을 덮지 않으려고 저장하지 않았다. draft_deck 으로 사본을 다시 만들어 같은 수정을 다시 하거나, 꼭 덮어써야 하면 --force", file=sys.stderr)
            return 2
        print(f"저장 실패 {e.code}: {res.get('error')}", file=sys.stderr)
        return 1
    if bp and res.get("version"):  # 같은 사본으로 이어 저장하면 내 저장이 기준
        bp.write_text(str(res["version"]), encoding="utf-8")
    if res.get("merged"):
        after_merge(deck_id, bp, res.get("deck"))
    print(f"저장됨(서버 {url}): {deck_id} · 원장 seq {res.get('seq')} · 버전 {res.get('version')}"
          + (" · 그 사이 편집기의 변경과 병합함" if res.get("merged") else ""))
    show_conflicts(res.get("conflicts") or [])
    return 0


def direct(deck_id, deck, a):
    p = DECKS / f"{deck_id}.json"
    bp, base = draft_base(deck_id, a.src)
    merged, conflicts = False, []
    if base and p.exists() and str(p.stat().st_mtime_ns) != base and not a.force:
        orig = None if a.no_merge else draft_orig(deck_id, bp)
        if orig is None:
            print(f"충돌: 사본을 만든 뒤 {deck_id} 가 바뀌었다 - draft_deck 으로 사본을 다시 만들어 고치거나 --force", file=sys.stderr)
            return 2
        deck, conflicts = deckmerge.merge3(orig, deck, json.loads(p.read_text(encoding="utf-8")), prefer="theirs")  # 사람이 이긴다
        merged = True
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
    if bp:
        bp.write_text(str(p.stat().st_mtime_ns), encoding="utf-8")
    if merged:
        after_merge(deck_id, bp, deck)
    print(f"저장됨(직접 - 서버 없음): {p} · 원장 seq {seq}" + (" · 그 사이 바뀐 것과 병합함" if merged else ""))
    show_conflicts(conflicts)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Claude 세션용 덱 저장(변경 원장에 claude 로 기록)")
    ap.add_argument("deck")
    ap.add_argument("--from", dest="src", help="새 덱 JSON 파일(없으면 표준 입력)")
    ap.add_argument("--request", help="처리 중인 요청 id")
    ap.add_argument("--note", help="무엇을 했는지 한 줄(200자)")
    ap.add_argument("--label", default=os.environ.get("NEXA_SLIDE_SESSION", ""), help="세션 이름(기본 NEXA_SLIDE_SESSION)")
    ap.add_argument("--action", default="save", choices=("save", "restore"))
    ap.add_argument("--force", action="store_true", help="편집기가 그 사이 저장했어도 덮어쓴다(사람의 변경을 지운다)")
    ap.add_argument("--no-merge", action="store_true", help="병합하지 않는다 - 그 사이 바뀌었으면 409(종료 코드 2)")
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
