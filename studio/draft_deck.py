# -*- coding: utf-8 -*-
"""덱 사본 만들기 - AI 세션이 덱을 고칠 때 쓴다. 덱 전체를 새로 쓰지 않고 사본의 필요한 줄만 고친 뒤 save_deck 으로 저장한다.

    python3 nexa.py draft_deck <덱> [--element <요소 id>] [--slide <슬라이드 id>]
    python3 nexa.py draft_deck <시트 문서> [--slide <탭 id>] [--range B2:D5]   # kind sheet - 탭과 범위 안 셀의 줄 번호
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


def sheet_range_lines(deck, lines, tab, rng):
    """시트 문서에서 범위 안 셀들의 줄 번호 - 탭(없으면 첫 탭)의 "cells" 줄부터 찾는다. 빈 셀은 cells 에 새 키로 넣는다."""
    import re

    def rc(ref):
        m = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]*)", ref.strip().upper().replace("$", ""))
        if not m:
            return None
        c = 0
        for ch in m.group(1):
            c = c * 26 + ord(ch) - 64
        return int(m.group(2)), c
    ends = [rc(x) for x in rng.split(":")]
    if None in ends:
        return f"범위 {rng}: 형식 오류(A1 · B2:D5)"
    (r1, c1), (r2, c2) = ends[0], ends[-1]
    tabs = deck.get("sheets") or []
    t = next((x for x in tabs if x.get("id") == tab), tabs[0] if tabs else None)
    if not t:
        return "탭 없음"
    start = next((i for i, l in enumerate(lines) if l.strip().startswith(f'"id": "{t["id"]}"')), 0)
    cl = next((i for i in range(start, len(lines)) if lines[i].strip().startswith('"cells"')), None)
    hits = []
    for ref in t.get("cells") or {}:
        p = rc(ref)
        if p and min(r1, r2) <= p[0] <= max(r1, r2) and min(c1, c2) <= p[1] <= max(c1, c2) and cl is not None:
            n = next((i + 1 for i in range(cl, len(lines)) if lines[i].strip().startswith(f'"{ref}"')), None)
            if n:
                hits.append(f"{ref}:{n}")
    head = f"탭 {t['id']}({t.get('name', '')}) cells: " + (f"{cl + 1}번째 줄" if cl is not None else "없음")
    return head + f" · 범위 {rng} 안 셀 " + (", ".join(hits[:40]) + (" …" if len(hits) > 40 else "") if hits else "없음(빈 칸 - cells 에 새 키로 넣는다)")


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="덱 사본(out/.studio/draft-<덱>.json) 만들기 - 고친 뒤 save_deck --from 으로 저장")
    ap.add_argument("deck")
    ap.add_argument("--element", help="이 요소 id 가 있는 줄 번호를 알려 준다(쉼표로 여러 개: e03,e05)")
    ap.add_argument("--slide", help="이 슬라이드 id(시트 문서면 탭 id)가 있는 줄 번호를 알려 준다")
    ap.add_argument("--range", help="시트 문서 - 이 범위(A1 · B2:D5) 안에 있는 셀의 줄 번호를 알려 준다(--slide 탭 안에서)")
    a = ap.parse_args()
    if not safe_id(a.deck):
        sys.exit("잘못된 덱 id")
    src = DECKS / f"{a.deck}.json"
    if not src.is_file():
        sys.exit(f"덱 없음: {src}")
    base = str(src.stat().st_mtime_ns)  # 사본의 기준 버전(서버 X-Deck-Version 과 같은 값) - 읽기 전에 재서 그 사이 바뀌면 save_deck 이 409 를 낸다
    deck = json.loads(src.read_text(encoding="utf-8"))
    STATE.mkdir(parents=True, exist_ok=True)
    out = STATE / f"draft-{a.deck}.json"
    (STATE / f"draft-{a.deck}.base").write_text(base, encoding="utf-8")  # save_deck --from 이 사본이면 이것을 base 로 보낸다
    text = json.dumps(deck, ensure_ascii=False, indent=1)
    out.write_text(text + "\n", encoding="utf-8", newline="\n")
    # 사본을 만든 때의 원본 - save_deck 이 병합 저장(3-way)의 기준본으로 쓴다(서버가 그 판을 기억하지 못할 때·서버 없이 저장할 때)
    (STATE / f"draft-{a.deck}.orig.json").write_text(text + "\n", encoding="utf-8", newline="\n")
    lines = text.splitlines()
    try:  # cwd(작업 공간) 기준 상대 경로로 알려 준다 - 명령에 그대로 쓰기 쉽게
        shown = out.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        shown = out.as_posix()
    out = Path(shown)
    sheet = deck.get("kind") == "sheet"
    print(f"사본: {out.as_posix()}  ({len(lines)}줄 · " + (f"시트 {len(deck.get('sheets') or [])}탭)" if sheet else f"슬라이드 {len(deck.get('slides', []))}장)"))
    for kind, sid in [("슬라이드", a.slide)] + [("요소", e.strip()) for e in (a.element or "").split(",") if e.strip()]:
        if sid:
            n = next((i + 1 for i, l in enumerate(lines) if l.strip().startswith(f'"id": "{sid}"')), None)
            print(f"{kind} {sid}: " + (f"{n}번째 줄부터" if n else "없음"))
    if sheet and a.range:
        print(sheet_range_lines(deck, lines, a.slide, a.range))
    print(f"다음: 사본을 Edit 로 고친 뒤  python3 nexa.py save_deck {a.deck} --from {out.as_posix()} --request <요청 id> --note \"…\"")


if __name__ == "__main__":
    main()
