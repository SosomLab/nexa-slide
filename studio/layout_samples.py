# -*- coding: utf-8 -*-
"""레이아웃 목록과 필드 예시 — 내용 원본(content/<id>.json)을 쓸 때 참고용 (DB·서버 불필요).

    python3 studio/layout_samples.py                 # 레이아웃 이름 · 한글 이름 · 필드 예시(JSON 한 줄씩)
    python3 studio/layout_samples.py --json          # {이름: {label, sample}} 전체 JSON
    python3 studio/layout_samples.py bullets table   # 몇 개만
    python3 studio/layout_samples.py --json --lang en # 견본 글을 영어로(studio/i18n/content.en.json)

슬라이드 한 장 = {"layout": "<이름>", ...필드, "notes": "발표자 노트", "source": ["근거 1", …]}.
필드 의미·인라인 강조·각주 규칙은 docs/deck-format.md.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layouts import LAYOUTS, SAMPLES  # noqa: E402


def main():
    args = sys.argv[1:]
    lang = args[args.index("--lang") + 1] if "--lang" in args and args.index("--lang") + 1 < len(args) else "ko"  # 견본 글 언어(studio/i18n/content.<lang>.json)
    args = [x for i, x in enumerate(args) if x != "--lang" and not (i > 0 and args[i - 1] == "--lang")]
    want = [a for a in args if not a.startswith("--")]
    names = [n for n in LAYOUTS if not want or n in want]
    from content_i18n import tr
    sample = lambda n: tr({"layout": n, **SAMPLES.get(n, {})}, lang)  # noqa: E731
    if "--json" in args:
        print(json.dumps({n: {"label": LAYOUTS[n][0], "sample": sample(n)} for n in names}, ensure_ascii=False, indent=1))
        return
    for n in names:
        print(f"# {n} — {LAYOUTS[n][0]}")
        print(json.dumps(sample(n), ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()
