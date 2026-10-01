# -*- coding: utf-8 -*-
"""레이아웃 목록과 필드 예시 — 내용 원본(content/<id>.json)을 쓸 때 참고용 (DB·서버 불필요).

    python3 studio/layout_samples.py                 # 레이아웃 이름 · 한글 이름 · 필드 예시(JSON 한 줄씩)
    python3 studio/layout_samples.py --json          # {이름: {label, sample}} 전체 JSON
    python3 studio/layout_samples.py bullets table   # 몇 개만

슬라이드 한 장 = {"layout": "<이름>", ...필드, "notes": "발표자 노트", "source": ["근거 1", …]}.
필드 의미·인라인 강조·각주 규칙은 docs/deck-format.md.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layouts import LAYOUTS, SAMPLES  # noqa: E402


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = [n for n in LAYOUTS if not want or n in want]
    if "--json" in sys.argv:
        print(json.dumps({n: {"label": LAYOUTS[n][0], "sample": {"layout": n, **SAMPLES.get(n, {})}} for n in names},
                         ensure_ascii=False, indent=1))
        return
    for n in names:
        print(f"# {n} — {LAYOUTS[n][0]}")
        print(json.dumps({"layout": n, **SAMPLES.get(n, {})}, ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()
