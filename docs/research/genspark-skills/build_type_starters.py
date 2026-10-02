# -*- coding: utf-8 -*-
"""승인된 템플릿 유형 → 시작용 내용(starters/<이름>/) — 유형의 대표 장 흐름(슬라이드 유형 순서)대로 예시 내용을 채운 덱.

    python docs/research/genspark-skills/build_type_starters.py

장마다 레이아웃 기본 예시 + 슬라이드 유형의 목적별 예시 내용(studio/slide_types.json)을 쓰고, 발표자 노트에 "유형·목적"을 적어
내용을 채울 때 길잡이로 쓴다. 승인 목록은 검토 등록부(docs/research/review/registry.json — rec-ttype-* 이 approved 인 것).
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
os.environ.setdefault("NEXA_SLIDE_WORKSPACE", str(REPO / "example"))  # 엔진 모듈(레이아웃 예시)을 불러오기 위한 작업 공간
sys.path.insert(0, str(REPO / "studio"))
import layouts  # noqa: E402,F401  (layouts_more 순환 참조 방지 — 먼저)
from layouts import SAMPLES  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"
# 템플릿 유형 id → (시작용 이름, 덱 id, 시각 템플릿, 부 이름)
STARTER = {
    "periodic-report": ("periodic-report", "report", "swiss", "정기 보고"),
    "lecture": ("lecture-theory", "lecture", "swiss", "강의"),
    "board-decision": ("board-decision", "board", "brief", "결정 요청"),
    "ir-finance": ("ir-finance", "ir", "proposal", "IR"),
    "strategy-plan": ("strategy-plan", "plan", "proposal", "전략 계획"),
}


def main():
    reg = json.loads((REPO / "docs/research/review/registry.json").read_text(encoding="utf-8"))["items"]
    approved = {x["id"][len("rec-ttype-"):] for x in reg if x["id"].startswith("rec-ttype-") and x["status"] == "approved"}
    types = {t["id"]: t for t in json.loads((DATA / "template_types.json").read_text(encoding="utf-8"))["types"]}
    st = {t["id"]: t for t in json.loads((REPO / "studio/slide_types.json").read_text(encoding="utf-8"))["types"]}
    for tid in sorted(approved):
        if tid not in STARTER:
            print("건너뜀(시작용 매핑 없음):", tid)
            continue
        name, deck, tpl, part = STARTER[tid]
        t = types[tid]
        slides = [{"layout": "cover", **SAMPLES["cover"], "title": "제목은 결론 한 문장으로", "subtitle": f"{t['label']} · 누구에게 · 언제",
                   "badge": part, "notes": f"표지 — {t['desc']}"}]
        for sid in t["flow"]:
            if sid.startswith("cover"):
                continue
            ty = st[sid]
            slides.append({"layout": ty["layout"], **SAMPLES.get(ty["layout"], {}), **ty.get("fields", {}),
                           "notes": f"유형: {ty['label']} ({ty['id']}) — {ty['purpose']}. 예시 내용을 이 덱의 내용으로 바꾼다."})
        if slides[-1]["layout"] != "end":
            slides.append({"layout": "end", **SAMPLES["end"], "sub": t["label"]})
        d = REPO / "starters" / name
        (d / "content").mkdir(parents=True, exist_ok=True)
        (d / "content" / f"{deck}.json").write_text(json.dumps({"id": deck, "title": t["label"], "part": "day1", "version": "0.1",
                                                              "slides": slides}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        (d / "starter.json").write_text(json.dumps({
            "label": f"{t['label']} ({len(slides)}장)", "description": f"{t['desc']}. 흐름: " + " → ".join(st[s]["label"] for s in t["flow"] if s in st),
            "template": tpl, "config": {"partLabels": {"day1": part, "day2": part, "day3": part, "apx": "부록"}, "coverBadge": part},
            "decks": [deck], "copy": ["content"], "source": f"템플릿 유형 {tid}(검토 승인) — docs/research/genspark-skills/05-template-types.md"},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{name:18s} {len(slides):2d}장 · 템플릿 {tpl}")


if __name__ == "__main__":
    main()
