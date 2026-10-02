# -*- coding: utf-8 -*-
"""템플릿 유형 15개 → 시작용 내용(starters/<이름>/) — 유형별 기본 구성(슬라이드 유형 순서)대로 예시 내용을 채운 덱.

    python docs/research/genspark-skills/build_type_starters.py

기본 구성은 아래 FLOW — 조사한 유형의 대표 장 흐름(data/template_types.json 의 flow)을 바탕으로 장 구분·근거·판단·마무리 장을
더해 여러 슬라이드 유형을 섞었다. 장마다 레이아웃 기본 예시 + 슬라이드 유형의 목적별 예시 내용(studio/slide_types.json)을 쓰고,
발표자 노트에 "유형·목적"을 적어 내용을 채울 때 길잡이로 쓴다. 장을 더하거나 바꿀 때는 편집기 "＋ 새 슬라이드 → 유형으로"·"유형 바꾸기".
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
    "research-report": ("research-report", "research", "swiss", "리서치"),
    "strategy-plan": ("strategy-plan", "plan", "proposal", "전략 계획"),
    "board-decision": ("board-decision", "board", "brief", "결정 요청"),
    "periodic-report": ("periodic-report", "report", "swiss", "정기 보고"),
    "investor-pitch": ("investor-pitch", "pitch", "keynote", "투자 유치"),
    "ir-finance": ("ir-finance", "ir", "proposal", "IR"),
    "sales-proposal": ("sales-proposal", "proposal", "proposal", "제안"),
    "case-story": ("case-story", "case", "archive", "사례"),
    "marketing-campaign": ("marketing-campaign", "campaign", "keynote", "캠페인"),
    "consulting": ("consulting", "consulting", "blueprint", "진단·제언"),
    "lecture": ("lecture-theory", "lecture", "swiss", "강의"),
    "training": ("training-course", "training", "notice", "교육"),
    "classroom": ("classroom", "class", "lecture", "수업"),
    "public-policy": ("public-policy", "policy", "blueprint", "정책"),
    "talk-story": ("talk-story", "talk", "keynote", "강연"),
}
# 기본 구성 — 슬라이드 유형 id, 장 구분은 ("section", "장 제목")
FLOW = {
    "research-report": ["cover-title", "exec-summary", "agenda", ("section", "무엇을 봤나"), "evidence-panel", "trend-line", "heatmap",
                        "share-donut", ("section", "무엇을 뜻하나"), "matrix-2x2", "number-evidence", "range-estimate", "risk-issues",
                        "summary", "references", "end"],
    "strategy-plan": ["cover-photo", "one-sentence", "agenda", ("section", "어디에 있나"), "kpi-dashboard", "trend-line", "issue-tree",
                      ("section", "무엇을 고르나"), "options", "matrix-2x2", ("section", "어떻게 가나"), "roadmap", "milestones", "gantt",
                      "risk-issues", "next-actions", "end"],
    "board-decision": ["cover-title", "exec-summary", "kpi-dashboard", "bar-compare", "options", "range-estimate", "risk-issues",
                       "decision-ask", "next-actions", "qa", "end"],
    "periodic-report": ["cover-title", "exec-summary", "kpi-dashboard", "trend-line", "bar-compare", "composition", "status-board",
                        "heatmap", "risk-issues", "milestones", "next-actions", "end"],
    "investor-pitch": ["cover-title", "hook-question", "big-number", "one-sentence", "before-after", "funnel", "number-evidence",
                       "process-flow", "team", "pricing", "roadmap", "decision-ask", "end"],
    "ir-finance": ["cover-title", "exec-summary", "kpi-dashboard", "trend-line", "data-table", "composition", "share-donut",
                   "range-estimate", "evidence-panel", "risk-issues", "qa", "end"],
    "sales-proposal": ["cover-title", "hook-question", "exec-summary", "before-after", ("section", "어떻게 푸나"), "process-flow",
                       "diagram", "case-story", "quote-voice", "number-evidence", ("section", "어떻게 시작하나"), "pricing", "gantt",
                       "team", "decision-ask", "end"],
    "case-story": ["cover-photo", "one-sentence", "profile", "quote-voice", "milestones", "photo-plates", "before-after",
                   "number-evidence", "numbered-steps", "dark-statement", "summary", "end"],
    "marketing-campaign": ["cover-photo", "one-sentence", "quote-voice", "funnel", "matrix-2x2", "share-donut", "photo-plates",
                           "roadmap", "gantt", "kpi-dashboard", "next-actions", "end"],
    "consulting": ["cover-title", "exec-summary", "agenda", ("section", "진단"), "issue-tree", "evidence-panel", "heatmap",
                   "number-evidence", ("section", "제언"), "matrix-2x2", "options", "pros-cons", "roadmap", "risk-issues",
                   "decision-ask", "end"],
    "lecture": ["cover-title", "agenda", "hook-question", ("section", "개념"), "concept", "diagram", "worked-example",
                ("section", "적용"), "code-walk", "lab", "quiz", "summary", "references", "end"],
    "training": ["cover-title", "agenda", "case-story", ("section", "알아야 할 것"), "concept", "process-flow", "numbered-steps",
                 "pros-cons", ("section", "해 보기"), "lab", "quiz", "case-choice", "summary", "next-actions", "end"],
    "classroom": ["cover-title", "hook-question", "agenda", "concept", "diagram", "worked-example", "quiz", "photo-plates",
                  "pros-cons", "summary", "qa", "end"],
    "public-policy": ["cover-title", "exec-summary", ("section", "현황과 근거"), "evidence-panel", "trend-line", "heatmap", "funnel",
                      ("section", "대안과 실행"), "options", "range-estimate", "gantt", "risk-issues", "decision-ask", "references", "end"],
    "talk-story": ["cover-photo", "hook-question", "photo-statement", "dark-statement", "big-number", "quote-voice", "milestones",
                   "photo-plates", "one-sentence", "numbered-steps", "end"],
}


def main():
    types = {t["id"]: t for t in json.loads((DATA / "template_types.json").read_text(encoding="utf-8"))["types"]}
    st = {t["id"]: t for t in json.loads((REPO / "studio/slide_types.json").read_text(encoding="utf-8"))["types"]}
    for tid, (name, deck, tpl, part) in STARTER.items():
        t = types[tid]
        slides, labels, chap = [], [], 0
        for i, step in enumerate(FLOW[tid]):
            if isinstance(step, tuple):  # 장 구분
                chap += 1
                slides.append({"layout": "chapter", **SAMPLES["chapter"], "number": f"{chap:02d}", "title": step[1],
                               "desc": "이 장에서 다룰 내용 한 문장", "notes": "유형: 장 구분 (section) — 긴 덱의 흐름을 나눈다."})
                labels.append(f"[{step[1]}]")
                continue
            ty = st[step]
            if i == 0 and step == "cover-title":
                slides.append({"layout": "cover", **SAMPLES["cover"], "title": "제목은 결론 한 문장으로", "subtitle": f"{t['label']} · 누구에게 · 언제",
                               "badge": part, "notes": f"표지 — {t['desc']}"})
            else:
                slides.append({"layout": ty["layout"], **SAMPLES.get(ty["layout"], {}), **ty.get("fields", {}),
                               "notes": f"유형: {ty['label']} ({ty['id']}) — {ty['purpose']}. 예시 내용을 이 덱의 내용으로 바꾼다."})
                if step == "end":
                    slides[-1]["sub"] = t["label"]
            labels.append(ty["label"])
        kinds = {s for s in FLOW[tid] if not isinstance(s, tuple)}
        d = REPO / "starters" / name
        (d / "content").mkdir(parents=True, exist_ok=True)
        (d / "content" / f"{deck}.json").write_text(json.dumps({"id": deck, "title": t["label"], "part": "day1", "version": "0.1",
                                                              "slides": slides}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        (d / "starter.json").write_text(json.dumps({
            "label": f"{t['label']} ({len(slides)}장)", "description": f"{t['desc']}. 기본 구성: " + " → ".join(labels),
            "template": tpl, "config": {"partLabels": {"day1": part, "day2": part, "day3": part, "apx": "부록"}, "coverBadge": part},
            "decks": [deck], "copy": ["content"],
            "source": f"템플릿 유형 {tid} — docs/research/genspark-skills/05-template-types.md (참고 덱 {', '.join(t.get('best', []))})"},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{name:20s} {len(slides):2d}장 · 슬라이드 유형 {len(kinds):2d} · 템플릿 {tpl}")


if __name__ == "__main__":
    main()
