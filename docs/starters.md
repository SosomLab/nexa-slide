# 시작용 교안과 목적별 템플릿

새 작업 공간을 **목적에 맞는 구성 + 디자인**으로 시작한다. 시작용 교안(`starters/<이름>/`)은 내용 뼈대(장 구성·작성 규칙·예시 내용)이고,
디자인은 엔진 템플릿(`studio/templates/<이름>/`)을 고른다. 시작용 교안마다 어울리는 템플릿이 정해져 있다.

```
python3 <엔진>/studio/init_workspace.py <폴더> --title "제목" --starter weekly-report
python3 <폴더>/nexa.py build_deck weekly --force
python3 <폴더>/nexa.py start
```

시작 페이지(허브)의 "새로 만들기"에서도 같은 목록을 고를 수 있다. 내용은 가상의 예시(주문 시스템 개편 프로젝트, 가명)이며, 숫자·이름·날짜를 바꿔 쓴다.

## 목록

| 시작용 교안 | 디자인 템플릿 | 장 수 | 구성 |
|---|---|---|---|
| `weekly-report` 주간 진행 보고 | `report` | 8 | 결론 KPI → 약속 대비 채점 → 이슈·요청 → 간트 → 다음 주 약속 → 요청 → 다음 보고 |
| `monthly-report` 월간 운영 보고 | `report` | 11 | 순서 → 결론 KPI → 추이 차트 → 목표 대비 → 잘된 것·미달 → 리스크 → 원인 워터폴 → 로드맵 → 결정 요청 |
| `decision-brief` 결정 요청 1~2장 | `brief` | 2 | 결론 배너·근거 3열·결정 띠(무엇을·누가·언제까지·안 하면) → 대안 비교 표 |
| `lecture-course` 강의 교안 3일 | `lecture` | 2장(29·17) | 공통 표지·목차·EoD + 과정 안내 장·이론 장 - [lecture-starter.md](lecture-starter.md) |
| `schedule` 일정·로드맵 | `schedule` | 7 | 마일스톤 → 로드맵(Now·Next·Later) → 13주 간트 → 3일 시간표 → 이번 달 일정표 |
| `story-retro` 프로젝트 회고·사례 | `story` | 12 | 한 문장 축 → 큰 숫자 → 흐름 → 목소리 → 잘된 것 → 어려웠던 순간 → 바꾼 것 → 가져갈 것 → 처음 문장으로 |
| `notice-onboarding` 사내 공지·온보딩 | `notice` | 10 | 인사 → 숫자로 보는 팀 → 첫 주 할 일 → 일정 → 담당 표 → 일하는 방식 → 버디 한마디 → 시간표 → 부탁 |
| `rfp-owner` 제안요청서 요약(발주자) | `proposal` | 12 | 사업 한 문장 → 개요 2×2 → 기능·비기능 요구(조항 번호) → 범위 밖 → 평가 기준 → 일정 → 제출물 → 제약 → 접수 |
| `rfp-response` 제안서(응답자) | `proposal` | 14 | 제안 요약 → 준수 매트릭스 → 과제 → 접근 → 일정 → 팀 → 평가 기준별 강점 → 효과 → 리스크 → 범위 밖·가정 → 가격 → 약속 |

## 디자인 템플릿 (목적별)

모두 `lecture` 를 바탕으로 색·글꼴·모서리만 바꾼다(`template.json` 의 `tokenOverrides`). 칩·글자는 역할별 최소 15px 로 빌드한다.

| 템플릿 | 톤 | 색 배치 |
|---|---|---|
| `report` | 업무 보고 - 신뢰 네이비 | 네이비 한 색 + 상태색(신호등), 차가운 회색 면. 표·KPI 숫자가 주인공 |
| `brief` | 결정 요청 - 차콜·딥 틸 | 차콜 글자 + 딥 틸 강조 한 색. 결론 배너·결정 띠가 먼저 보이게 |
| `story` | 이야기·회고 - 따뜻한 미색 | 미색 바탕, 테라코타 강조, **명조 제목**(`heading` 글꼴 = Noto Serif KR) |
| `notice` | 공지·온보딩 - 밝은 오렌지 | 오렌지 강조 + 틸·바이올렛·그린 보조, 큰 둥근 모서리 |
| `schedule` | 일정·로드맵 - 차분한 블루 | 단계마다 블루·틸·바이올렛, 옅은 회청색 면 |
| `proposal` | RFP·제안 - 인디고·골드 | 인디고 기본 + 골드 보조, 격식 있는 표 중심 |

상태색 토큰은 모든 템플릿 공통: `ok`(정상·완료) · `caution`(주의) · `bad`(위험·미달) · `info`(진행) · `idle`(대기), 각각 `-container`(옅은 면).
글꼴 키 `heading` 은 제목용(기본은 본문과 같고 `story` 만 명조).

## 공통 작성 규칙

용도별 인기 템플릿을 조사해 반복해서 나온 규칙이다. 시작용 교안의 예시도 이 규칙대로 썼다.

1. **제목 = 결론.** "현황", "Next Steps" 같은 범주형 제목 대신 "약속한 5건 중 4건 완료 - 성능 개선만 다음 주로".
2. **결론을 2장 안에.** 결론 KPI·결론 배너·한 문장 축·제안 요약.
3. **마지막 장은 다음 행동.** 요청·결정(무엇을·누가·언제까지·안 하면), 다음 보고일, 가져갈 것 하나 - "감사합니다" 장 대신.
4. **숫자에는 기준·실명·기한.** 목표·전기·전년 중 둘 이상과 비교, 담당자 이름, 마감일.
5. **나쁜 소식도 같은 무게로.** 미달·리스크·범위 밖을 성과와 같은 비중으로, 대응과 짝지어.
6. **매 회차 같은 배치.** 보고·간트는 덱을 복제해 숫자와 NOW 선만 바꾼다.
7. **항목 수 상한.** 표 9행·간트 10행·카드 4개·KPI 4개 이내 - 넘치면 글자를 줄이지 말고 장을 나눈다.
8. **수치가 예시면 밝힌다.** "수치는 예시" - 실제 값은 근거(출처·측정일)를 붙인다.

## 새 레이아웃 (`studio/layouts_extra.py`)

기존 요소(상자·글자·칩·원·선·곡선)만 조합해 편집기와 PPTX 가 같은 규칙으로 그린다. 필드 예시는 `nexa.py layout_samples`.

| 레이아웃 | 쓰임 | 주요 필드 |
|---|---|---|
| `status_table` | 상태 표 | `header`, `rows`(셀 = 글 또는 `{text, status}`, 행 = `{cells, fill, total}`), `colW`, `align`, `conclusion` |
| `kpi_tiles` | KPI 타일 2~4개 | `tiles`: `{label, value, unit, target, delta, status}`, `items`(요약 줄) |
| `issue_cards` | 이슈 카드 1~3개 | `issues`: `{title, status, situation, impact, ask, owner, due}` |
| `grid_cards` | 격자 카드 | `items`: `{num 또는 label, title, body, tone, status}`, `cols` |
| `statement` | 한 문장 | `text`, `kicker`, `sub`, `dark` |
| `quote` | 인용 | `text`, `who`, `role`, `context` |
| `big_number` | 큰 숫자 | `value`, `unit`, `label`, `context`, `compare` |
| `decision_brief` | 결정 요청 1장 | `kicker`, `title`, `sub`, `columns`, `ask`, `owner`, `due`, `impact` |
| `milestones` | 마일스톤 | `items`: `{date, title, desc, status, at}`, `now`(0~1) |
| `roadmap` | Now·Next·Later | `columns`: `{label, sub, items: [{title, desc, status}]}` |
| `gantt` | 간트 | `periods`, `rows`: `{task, owner, bars: [[시작, 끝, 상태·톤, 글]]}`, `gates`, `now` |
| `week_grid` | 시간표 | `days`, `slots`, `sessions`: `{day, slot, span, days, title, sub, tone}` |
| `photo_text` | 사진 + 글 | `img`(없으면 자리 표시), `imgSide`, `kicker`, `title`, `body`, `items` |
| `agenda` | 진행 순서 | `items`: `{title, desc, time, owner}`, `current` |
| `column_chart` | 세로 막대 | `categories`, `values`, `mode`(plain·cumulative·waterfall), `highlight`, `totals`, `line`, `panels`(여러 판) |
| `stack_bars` | 가로 누적 막대 | `rows`: `{label, sub, segments: [[이름, 값, 톤]]}`, `unit`, `legend` |

여러 레이아웃이 함께 쓰는 필드: `action`(아래 행동 띠 한 줄, `actionLabel`), `footnote`, `kick`(머리 칩), `crumb`.
기존 `bullets` 에는 `aside`(오른쪽 작은 그림: `{kind: columns|stack, title, …, note}` 목록)가 추가됐다 - 글머리 옆에 개념용 차트를 작게 둔다.
