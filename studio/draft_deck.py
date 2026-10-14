# -*- coding: utf-8 -*-
"""덱 사본 만들기 - AI 세션이 덱을 고칠 때 쓴다. 덱 전체를 새로 쓰지 않고 사본의 필요한 줄만 고친 뒤 save_deck 으로 저장한다.

    python3 nexa.py draft_deck <덱> [--element <요소 id>] [--slide <슬라이드 id>]
    → out/.studio/draft-<덱>.json 에 보기 좋게(한 필드 한 줄) 복사하고 경로를 출력한다. --element/--slide 를 주면 그 id 가 있는 줄 번호도 알려 준다.
    다음: 사본을 Edit 도구로 고친다(요소 id 유지) → python3 nexa.py save_deck <덱> --from <사본 경로> --request <요청 id> --note "…"

웹 세션(권한이 Edit/Write 와 nexa.py 명령으로 제한)에서 수천 줄 덱을 통째로 손으로 옮기지 않게 하려는 명령이다. 사본은 산출물 폴더(out/, git 제외)에 둔다.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DECKS, STATE, safe_id  # noqa: E402


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="덱 사본(out/.studio/draft-<덱>.json) 만들기 - 고친 뒤 save_deck --from 으로 저장")
    ap.add_argument("deck")
    ap.add_argument("--element", help="이 요소 id 가 있는 줄 번호를 알려 준다(쉼표로 여러 개: e03,e05)")
    ap.add_argument("--slide", help="이 슬라이드 id 가 있는 줄 번호를 알려 준다")
    a = ap.parse_args()
    if not safe_id(a.deck):
        sys.exit("잘못된 덱 id")
    src = DECKS / f"{a.deck}.json"
    if not src.is_file():
        sys.exit(f"덱 없음: {src}")
    deck = json.loads(src.read_text(encoding="utf-8"))
    STATE.mkdir(parents=True, exist_ok=True)
    out = STATE / f"draft-{a.deck}.json"
    text = json.dumps(deck, ensure_ascii=False, indent=1)
    out.write_text(text + "\n", encoding="utf-8", newline="\n")
    lines = text.splitlines()
    try:  # cwd(작업 공간) 기준 상대 경로로 알려 준다 - 명령에 그대로 쓰기 쉽게
        shown = out.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        shown = out.as_posix()
    out = Path(shown)
    print(f"사본: {out.as_posix()}  ({len(lines)}줄 · 슬라이드 {len(deck.get('slides', []))}장)")
    for kind, sid in [("슬라이드", a.slide)] + [("요소", e.strip()) for e in (a.element or "").split(",") if e.strip()]:
        if sid:
            n = next((i + 1 for i, l in enumerate(lines) if l.strip().startswith(f'"id": "{sid}"')), None)
            print(f"{kind} {sid}: " + (f"{n}번째 줄부터" if n else "없음"))
    print(f"다음: 사본을 Edit 로 고친 뒤  python3 nexa.py save_deck {a.deck} --from {out.as_posix()} --request <요청 id> --note \"…\"")


if __name__ == "__main__":
    main()
