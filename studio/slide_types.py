# -*- coding: utf-8 -*-
"""슬라이드 유형 목록·찾기 — 초안을 쓰거나 요청을 처리할 때 내용 성격에 맞는 유형(→ 레이아웃·필드)을 고르는 기준.

    python3 <작업 공간>/nexa.py slide_types                  # 목적별 묶음 · 유형 id · 레이아웃 · 고를 신호(when)
    python3 <작업 공간>/nexa.py slide_types 추이 비율         # 낱말로 찾기(이름·목적·신호·레이아웃)
    python3 <작업 공간>/nexa.py slide_types --json [낱말…]    # 예시 내용(fields)까지 JSON
    python3 <작업 공간>/nexa.py slide_types --group data      # 한 묶음만(intro·message·data·decide·plan·people·learn·close)

고른 유형은 content 에 {"layout": <레이아웃>, …필드} 로 쓴다 — 필드 형식은 `nexa.py layout_samples <레이아웃>`, 예시 내용은 --json 의 fields.
목록 원본은 엔진 studio/slide_types.json(문서 docs/slide-types.md).
"""
import argparse
import json
import sys
from pathlib import Path

CAT = Path(__file__).resolve().parent / "slide_types.json"


def main():
    ap = argparse.ArgumentParser(description="슬라이드 유형 목록·찾기")
    ap.add_argument("words", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--group")
    a = ap.parse_args()
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    gl = {g["id"]: g for g in cat["groups"]}
    ts = [t for t in cat["types"] if (not a.group or t["group"] == a.group)
          and all(w.lower() in f"{t['label']} {t['purpose']} {t.get('when', '')} {t['layout']} {t['id']}".lower() for w in a.words)]
    if a.json:
        print(json.dumps({"groups": cat["groups"], "types": ts}, ensure_ascii=False, indent=1))
        return
    if not ts:
        sys.exit("맞는 유형이 없다 — 낱말을 줄이거나 목록 전체(인자 없이)를 본다")
    cur = None
    for t in ts:
        if t["group"] != cur:
            cur = t["group"]
            print(f"\n## {gl[cur]['label']} ({cur}) — {gl[cur]['desc']}")
        print(f"  {t['id']:16s} {t['label']}  [layout {t['layout']}]")
        print(f"  {'':16s} 목적: {t['purpose']} · 고를 때: {t.get('when', '')}")


if __name__ == "__main__":
    main()
