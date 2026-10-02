# 05. 템플릿 유형 15개 — 추천

> 156개 덱을 **목적·구성(장 흐름)·시각 계열의 유사성**으로 묶었다(덱마다 한 유형). 만든 스크립트 `build_template_types.py`, 데이터 `data/template_types.json`.
> 대표 장 흐름은 슬라이드 유형 id([../../slide-types.md](../../slide-types.md)). 검토·승인은 시작 페이지 **템플릿 검토 → 추천**.

| 유형 | 목적·구성 | 덱 | 장 | 평균 점수 | 어울리는 시각 템플릿 | 대표 장 흐름 |
|---|---|---:|---:|---:|---|---|
| **리서치·리뷰 보고서** (`research-report`) | 조사·분석 결과를 논지로 전달 — 결론 먼저, 근거 패널, 참고문헌 | 14 | 230 | 3.71 | editorial, swiss | cover-title → exec-summary → evidence-panel → trend-line → matrix-2x2 → number-evidence → risk-issues → summary → references |
| **전략·연례 계획** (`strategy-plan`) | 비전·전략·연간 계획을 한 흐름으로 — 목표·로드맵·투자 | 8 | 117 | 4.25 | forest, ledger | cover-photo → one-sentence → kpi-dashboard → issue-tree → options → roadmap → milestones → next-actions → end |
| **이사회·경영 결정 요청** (`board-decision`) | 결정권자가 한 번에 판단 — 요약·숫자·리스크·결정 요청·부록 | 9 | 90 | 3.44 | ledger | exec-summary → kpi-dashboard → options → risk-issues → decision-ask → qa |
| **정기 업무 보고(주간·월간·QBR)** (`periodic-report`) | 매 회차 같은 배치 — 결론 KPI·추이·상태·이슈·다음 행동 | 10 | 120 | 3.1 | swiss, ledger | kpi-dashboard → trend-line → status-board → bar-compare → risk-issues → next-actions |
| **투자 유치 피치** (`investor-pitch`) | 문제→해결→시장→트랙션→팀→요청, 숫자 하나가 장마다 | 9 | 112 | 3.33 | editorial, keynote | cover-title → hook-question → one-sentence → funnel → number-evidence → team → pricing → options → end |
| **IR·재무 브리핑** (`ir-finance`) | 실적·전망·밸류에이션을 원장풍으로 — 표·범위·요약 패널 | 4 | 124 | 4.0 | ledger | cover-title → kpi-dashboard → data-table → range-estimate → evidence-panel → qa |
| **B2B 영업·제안서** (`sales-proposal`) | 고객 과제→해법→근거→가격·일정→약속, 평가자 채점표 | 11 | 150 | 3.64 | ledger, editorial | cover-title → exec-summary → before-after → process-flow → case-story → pricing → gantt → decision-ask |
| **사례 연구·회고 이야기** (`case-story`) | 목표→사건→선택→결과를 잡지처럼 — 인용·증거·전후 숫자 | 6 | 77 | 4.0 | archive, editorial | photo-statement → one-sentence → quote-voice → milestones → before-after → number-evidence → numbered-steps → summary |
| **마케팅 캠페인·브랜드** (`marketing-campaign`) | 인사이트→전략→실행→성과, 사진·브랜드 톤 | 12 | 204 | 3.92 | keynote, editorial | cover-photo → one-sentence → funnel → matrix-2x2 → roadmap → kpi-dashboard → photo-plates → next-actions |
| **컨설팅·문제 해결** (`consulting`) | 가설·이슈 트리·진단·권고 — 결론형 제목과 해석 패널 | 9 | 142 | 3.78 | swiss, editorial | exec-summary → issue-tree → evidence-panel → matrix-2x2 → options → roadmap → decision-ask |
| **강의·교안(이론·이공계)** (`lecture`) | 직관→개념→풀이→한계→흔한 실수→과제 | 13 | 186 | 3.85 | swiss, editorial | section → concept → diagram → worked-example → quiz → code-walk → summary |
| **직무·자격 교육** (`training`) | 현장 사례→규칙→실습→확인→휴대 카드 | 19 | 268 | 3.58 | signal, archive | agenda → case-story → concept → process-flow → lab → quiz → case-choice → summary |
| **수업·학생 발표** (`classroom`) | 목표→훅→시범→함께→혼자→나가기, 발표는 질문→방법→결과 | 9 | 112 | 3.44 | signal | hook-question → agenda → concept → worked-example → quiz → photo-plates → summary |
| **공공·정책·연구 지원** (`public-policy`) | 결론 먼저(BLUF)·대안 비교·근거·예산·요청 | 11 | 175 | 3.91 | ledger, forest | exec-summary → evidence-panel → options → funnel → gantt → risk-issues → decision-ask → references |
| **강연·이야기·포트폴리오** (`talk-story`) | 한 장 한 문장·사진·큰 숫자의 리듬 | 12 | 167 | 4.33 | keynote, archive | cover-photo → photo-statement → dark-statement → big-number → quote-voice → photo-plates → one-sentence → end |

## 근거 덱

- **리서치·리뷰 보고서**: 001 004 006 007 046 049 056 078 103 107 108 117 118 125
- **전략·연례 계획**: 012 033 041 060 067 113 122 149
- **이사회·경영 결정 요청**: 005 010 017 018 030 063 082 094 114
- **정기 업무 보고(주간·월간·QBR)**: 044 048 050 080 087 090 105 126 128 141
- **투자 유치 피치**: 003 054 081 136 137 139 143 146 155
- **IR·재무 브리핑**: 009 026 058 074
- **B2B 영업·제안서**: 016 032 038 061 069 072 077 097 124 130 132
- **사례 연구·회고 이야기**: 024 047 076 088 098 156
- **마케팅 캠페인·브랜드**: 011 013 019 020 021 022 025 075 089 096 109 140
- **컨설팅·문제 해결**: 014 028 039 040 071 099 101 119 129
- **강의·교안(이론·이공계)**: 002 035 042 045 051 079 095 102 104 123 135 145 154
- **직무·자격 교육**: 027 029 031 034 037 053 055 062 064 084 091 100 115 116 120 131 133 151 152
- **수업·학생 발표**: 023 052 070 073 083 127 142 144 150
- **공공·정책·연구 지원**: 057 059 066 068 085 106 110 111 121 134 153
- **강연·이야기·포트폴리오**: 008 015 036 043 065 086 092 093 112 138 147 148
