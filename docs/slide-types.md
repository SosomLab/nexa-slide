# 슬라이드 유형 — 목적·구성으로 고르는 낱장 52개

색·배치가 아니라 **이 장이 하는 일**(목적·구성)로 나눈 낱장 목록이다. 편집기 **＋ 새 슬라이드 → 슬라이드 추가 창 → 유형으로**에서 미리보기를 보고 고르면
그 목적에 맞는 예시 내용이 채워진 장이 지금 슬라이드 다음에 들어간다. 목록 파일은 `studio/slide_types.json`(`layout` = 그리는 레이아웃, `fields` = 예시 내용).

근거: Genspark 공개 슬라이드 스킬 2,274장 전수 조사([research/genspark-skills/03-slide-archetypes.md](research/genspark-skills/03-slide-archetypes.md)).
새 레이아웃 17종(`studio/layouts_more.py`)은 그 조사의 새 유형을 기존 요소로 구현한 것이다. 검토·승인은 시작 페이지 **슬라이드 유형 검토**(`/review/slides`).

## 시작·도입 (6) — 덱을 열고 길을 보여 주는 장

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 표지 — 제목형 | `cover-title` | 덱 제목·부제·발표자로 시작 | `cover` |  |
| 표지 — 사진 전면 | `cover-photo` | 장면 하나로 분위기를 먼저 | `photo_statement` (새) | 전면 · 분위기 · 아래 1/3 어둡게 |
| 진행 순서 | `agenda` | 시간·담당이 있는 순서 | `agenda` |  |
| 목차 | `toc` | 장 목록으로 길 안내 | `toc` |  |
| 장 구분 | `section` | 새 장을 여는 표지 | `chapter` |  |
| 질문으로 열기 | `hook-question` | 청중이 답을 궁금해하게 만드는 질문 하나 | `statement` |  |

## 메시지 (6) — 한 장에 하나의 주장·장면

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 핵심 한 문장 | `one-sentence` | 덱 전체를 꿰는 문장(축) | `statement` |  |
| 어두운 전환 문장 | `dark-statement` | 흐름을 끊고 강조하는 쉼표 장 | `statement` |  |
| 사진 + 한 문장 | `photo-statement` | 현장 사진 위에 기억할 문장 | `photo_statement` (새) | 전면 · 장소·분위기 · 피사체 위쪽 |
| 인용 — 고객·현장의 말 | `quote-voice` | 실명 화자의 한마디로 신뢰 | `quote` |  |
| 숫자 하나 | `big-number` | 결론이 되는 숫자 하나와 맥락 | `big_number` |  |
| 요약 — 결론 먼저 | `exec-summary` | 근거 3개와 결론 수치를 첫 장에 | `insight_panel` (새) |  |

## 근거·데이터 (10) — 숫자·추이·표로 근거를 보이는 장

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| KPI 대시보드 | `kpi-dashboard` | 핵심 지표 2~4개를 목표·비교와 함께 | `kpi_tiles` |  |
| 추이 — 선 그래프 | `trend-line` | 시간에 따른 변화·계획 대비·이벤트 전후 | `line_chart` (새) |  |
| 막대 비교 | `bar-compare` | 항목·기간별 크기 비교 | `column_chart` |  |
| 구성비 | `composition` | 전체 안의 비율 비교 | `stack_bars` |  |
| 숫자 + 근거 차트 | `number-evidence` | 결론 숫자와 그 추이를 한 장에 | `number_chart` (새) |  |
| 근거 + 해석 패널 | `evidence-panel` | 표·목록 근거 옆에 해석을 고정 | `insight_panel` (새) |  |
| 표 | `data-table` | 여러 항목을 같은 기준으로 | `table` |  |
| 상태 표(신호등) | `status-board` | 계획 대비 실적과 상태 | `status_table` |  |
| 범위·민감도 | `range-estimate` | 추정치를 범위로·기준선과 함께 | `range_bars` (새) |  |
| 깔때기·시장 규모 | `funnel` | 단계별로 줄어드는 수(전환·TAM) | `funnel` (새) |  |

## 비교·판단 (7) — 선택지를 비교하고 결정을 요청하는 장

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 전후 비교 | `before-after` | 바꾸기 전과 후 | `compare` |  |
| 선택지 비교(추천 강조) | `options` | 대안 2~4개 중 추천안 | `tier_columns` (새) |  |
| 사분면 우선순위 | `matrix-2x2` | 효과×실행으로 항목 배치 | `matrix_plot` (새) |  |
| 장단점·대비 카드 | `pros-cons` | 두세 가지를 나란히 대비 | `cards` |  |
| 결정 요청 | `decision-ask` | 무엇을·누가·언제까지 결정 | `decision_brief` |  |
| 리스크·이슈와 요청 | `risk-issues` | 상황·영향·요청·담당·기한 | `issue_cards` |  |
| 가격·패키지 | `pricing` | 등급별 값과 포함 항목 | `tier_columns` (새) |  |

## 과정·계획 (8) — 순서·일정·구조를 보여 주는 장

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 단계 흐름 | `process-flow` | 화살표로 잇는 순서 | `flow` |  |
| 마일스톤 | `milestones` | 날짜가 있는 주요 시점 | `milestones` |  |
| 로드맵 Now·Next·Later | `roadmap` | 시기별 할 일 묶음 | `roadmap` |  |
| 간트 | `gantt` | 기간×작업 일정 | `gantt` |  |
| 시간표 | `week-schedule` | 일자×시간 칸 | `week_grid` |  |
| 큰 번호 단계·요점 | `numbered-steps` | 세 가지 원인·요청·교훈을 번호로 | `numbered_rows` (새) |  |
| 이슈·지표 트리 | `issue-tree` | 하나를 갈래로 나눠 원인·구성 보기 | `tree` (새) |  |
| 구조도 | `diagram` | 시스템·관계도(Mermaid) | `diagram` |  |

## 사람·사례 (5) — 사람·사례·현장으로 설득하는 장

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 팀·인물 카드 | `team` | 사람 2~4명 소개 | `people_cards` (새) | 카드 사진 · 인물 · 세로 3:4 · 줄 단위 톤 통일 |
| 인물·대상 소개(사진+글) | `profile` | 한 사람·한 대상을 깊게 | `photo_text` | 반쪽 · 인물·장소 · 시선이 글 쪽 |
| 사례 제시 | `case-story` | 사례와 생각해 볼 질문 | `case_story` (새) |  |
| 사례 판단(선택지) | `case-choice` | 사례를 보고 A~D 중 판단 | `case_story` (새) |  |
| 사진 도판 | `photo-plates` | 현장·결과물 사진 여러 장 | `photo_plates` (새) | 가로 띠·카드 · 증거·과정 · 같은 톤 |

## 학습·확인 (5) — 개념·풀이·실습·확인 문제

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 개념 설명 | `concept` | 핵심 개념 글머리 | `bullets` |  |
| 단계별 풀이 | `worked-example` | 문제 → 단계 → 답, 규칙·함정 | `worked_example` (새) |  |
| 확인 문제 | `quiz` | 보기 4개로 이해도 확인 | `quiz` (새) |  |
| 실습 | `lab` | 실습 과제와 단계 | `lab` |  |
| 코드 설명 | `code-walk` | 코드와 실행 계획 | `code_plan` |  |

## 마무리·부록 (5) — 정리·다음 행동·근거·질의응답

| 유형 | id | 목적 | 레이아웃 | 이미지 자리 |
|---|---|---|---|---|
| 정리 | `summary` | 기억할 것 | `summary` |  |
| 다음 행동·부탁 | `next-actions` | 누가 무엇을 언제까지 | `numbered_rows` (새) |  |
| 참고문헌·출처 | `references` | 근거 목록과 쓴 장 | `references` (새) |  |
| 예상 질문(부록) | `qa` | 질문·답·근거를 미리 | `qa` (새) |  |
| 끝 | `end` | 문서 끝 | `end` |  |
