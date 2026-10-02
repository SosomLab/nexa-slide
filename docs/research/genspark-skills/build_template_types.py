# -*- coding: utf-8 -*-
"""템플릿 유형 15개 — 156개 덱을 목적·구성(장 흐름)·시각 계열의 유사성으로 묶은 추천 → data/template_types.json.

    python docs/research/genspark-skills/build_template_types.py

덱마다 하나의 유형에 배정한다(검사: 156개가 정확히 한 번). visual = 어울리는 시각 템플릿 후보(candidates.json),
flow = 대표 장 흐름(studio/slide_types.json 의 유형 id).
"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TYPES = [
    ("research-report", "리서치·리뷰 보고서", "조사·분석 결과를 논지로 전달 — 결론 먼저, 근거 패널, 참고문헌", ["editorial", "swiss"],
     ["cover-title", "exec-summary", "evidence-panel", "trend-line", "matrix-2x2", "number-evidence", "risk-issues", "summary", "references"],
     "001 004 006 007 046 049 056 078 103 107 108 117 118 125"),
    ("strategy-plan", "전략·연례 계획", "비전·전략·연간 계획을 한 흐름으로 — 목표·로드맵·투자", ["forest", "ledger"],
     ["cover-photo", "one-sentence", "kpi-dashboard", "issue-tree", "options", "roadmap", "milestones", "next-actions", "end"],
     "012 033 041 060 067 113 122 149"),
    ("board-decision", "이사회·경영 결정 요청", "결정권자가 한 번에 판단 — 요약·숫자·리스크·결정 요청·부록", ["ledger"],
     ["exec-summary", "kpi-dashboard", "options", "risk-issues", "decision-ask", "qa"],
     "005 010 017 018 030 063 082 094 114"),
    ("periodic-report", "정기 업무 보고(주간·월간·QBR)", "매 회차 같은 배치 — 결론 KPI·추이·상태·이슈·다음 행동", ["swiss", "ledger"],
     ["kpi-dashboard", "trend-line", "status-board", "bar-compare", "risk-issues", "next-actions"],
     "044 048 050 080 087 090 105 126 128 141"),
    ("investor-pitch", "투자 유치 피치", "문제→해결→시장→트랙션→팀→요청, 숫자 하나가 장마다", ["editorial", "keynote"],
     ["cover-title", "hook-question", "one-sentence", "funnel", "number-evidence", "team", "pricing", "options", "end"],
     "003 054 081 136 137 139 143 146 155"),
    ("ir-finance", "IR·재무 브리핑", "실적·전망·밸류에이션을 원장풍으로 — 표·범위·요약 패널", ["ledger"],
     ["cover-title", "kpi-dashboard", "data-table", "range-estimate", "evidence-panel", "qa"],
     "009 026 058 074"),
    ("sales-proposal", "B2B 영업·제안서", "고객 과제→해법→근거→가격·일정→약속, 평가자 채점표", ["ledger", "editorial"],
     ["cover-title", "exec-summary", "before-after", "process-flow", "case-story", "pricing", "gantt", "decision-ask"],
     "016 032 038 061 069 072 077 097 124 130 132"),
    ("case-story", "사례 연구·회고 이야기", "목표→사건→선택→결과를 잡지처럼 — 인용·증거·전후 숫자", ["archive", "editorial"],
     ["photo-statement", "one-sentence", "quote-voice", "milestones", "before-after", "number-evidence", "numbered-steps", "summary"],
     "024 047 076 088 098 156"),
    ("marketing-campaign", "마케팅 캠페인·브랜드", "인사이트→전략→실행→성과, 사진·브랜드 톤", ["keynote", "editorial"],
     ["cover-photo", "one-sentence", "funnel", "matrix-2x2", "roadmap", "kpi-dashboard", "photo-plates", "next-actions"],
     "011 013 019 020 021 022 025 075 089 096 109 140"),
    ("consulting", "컨설팅·문제 해결", "가설·이슈 트리·진단·권고 — 결론형 제목과 해석 패널", ["swiss", "editorial"],
     ["exec-summary", "issue-tree", "evidence-panel", "matrix-2x2", "options", "roadmap", "decision-ask"],
     "014 028 039 040 071 099 101 119 129"),
    ("lecture", "강의·교안(이론·이공계)", "직관→개념→풀이→한계→흔한 실수→과제", ["swiss", "editorial"],
     ["section", "concept", "diagram", "worked-example", "quiz", "code-walk", "summary"],
     "002 035 042 045 051 079 095 102 104 123 135 145 154"),
    ("training", "직무·자격 교육", "현장 사례→규칙→실습→확인→휴대 카드", ["signal", "archive"],
     ["agenda", "case-story", "concept", "process-flow", "lab", "quiz", "case-choice", "summary"],
     "027 029 031 034 037 053 055 062 064 084 091 100 115 116 120 131 133 151 152"),
    ("classroom", "수업·학생 발표", "목표→훅→시범→함께→혼자→나가기, 발표는 질문→방법→결과", ["signal"],
     ["hook-question", "agenda", "concept", "worked-example", "quiz", "photo-plates", "summary"],
     "023 052 070 073 083 127 142 144 150"),
    ("public-policy", "공공·정책·연구 지원", "결론 먼저(BLUF)·대안 비교·근거·예산·요청", ["ledger", "forest"],
     ["exec-summary", "evidence-panel", "options", "funnel", "gantt", "risk-issues", "decision-ask", "references"],
     "057 059 066 068 085 106 110 111 121 134 153"),
    ("talk-story", "강연·이야기·포트폴리오", "한 장 한 문장·사진·큰 숫자의 리듬", ["keynote", "archive"],
     ["cover-photo", "photo-statement", "dark-statement", "big-number", "quote-voice", "photo-plates", "one-sentence", "end"],
     "008 015 036 043 065 086 092 093 112 138 147 148"),
]


def main():
    census = {c["no"]: c for c in json.loads((DATA / "census.json").read_text(encoding="utf-8"))}
    seen = collections.Counter()
    out = []
    for tid, label, desc, visual, flow, members in TYPES:
        nos = members.split()
        seen.update(nos)
        ms = [census[n] for n in nos]
        fam = collections.Counter(m["familyGroup"] for m in ms).most_common(2)
        cats = collections.Counter(m["category"] for m in ms).most_common(3)
        out.append({"id": tid, "label": label, "desc": desc, "visual": visual, "flow": flow, "members": nos,
                    "count": len(nos), "slides": sum(m["slides"] for m in ms), "avgScore": round(sum(m["score"] for m in ms) / len(ms), 2),
                    "families": fam, "categories": cats,
                    "best": [m["no"] for m in sorted(ms, key=lambda m: -m["score"])[:4]]})
    missing = sorted(set(census) - set(seen))
    dup = [n for n, k in seen.items() if k > 1]
    assert not missing and not dup, (missing, dup)
    (DATA / "template_types.json").write_text(json.dumps({"types": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for t in out:
        print(f"{t['id']:20s} {t['count']:3d}덱 {t['slides']:4d}장 평균 {t['avgScore']} {t['families'][0][0]}")


if __name__ == "__main__":
    main()
