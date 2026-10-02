# 변경 이력

## 0.13.2 - 2026-10-02 · 추천 시각 템플릿 4개

- **추천 시각 템플릿 4개** 엔진에 추가(`lecture` 바탕, 색·글꼴·모서리·부품만): `editorial`(미색·명조·진홍, 고정폭 라벨 + 검정 띠) · `ledger`(크림·남색·금색, 명조, 모서리 없음, 남색 띠) · `signal`(노랑·검정·빨강, 굵은 고딕, 검정 띠) · `forest`(숲녹색·크림·테라코타, 명조, 큰 장식 쪽 번호). 레이아웃 견본·시작용 짝 모두 검사 ERROR 0.
- 검토 등록부에는 "추천" 상태 그대로 구현 기록만 남겼다 — `/review` 에서 승인·보류를 계속 정한다.

## 0.13.1 - 2026-10-02 · 템플릿 유형 15개 시작용 기본 구성

- **템플릿 유형 15개 모두 시작용 내용으로**: 목적별로 슬라이드 유형 11~14가지를 섞은 기본 구성(11~17장, 긴 덱은 장 구분 포함). 새로 10개 — `research-report` · `investor-pitch` · `sales-proposal` · `case-story` · `marketing-campaign` · `consulting` · `training-course` · `classroom` · `public-policy` · `talk-story`. 기존 5개(`periodic-report` 등)도 같은 방식으로 늘렸다. 내용은 유형별 예시 — 장을 더하거나 바꾸는 것은 편집기 "유형으로"·"유형 바꾸기".
- 15개 모두 빌드·레이아웃 검사 ERROR 0. 검토 등록부의 템플릿 유형에 구현 기록(승인 상태는 그대로 — 검토는 계속).

## 0.13.0 - 2026-10-02 · 템플릿 부품 · 유형 바꾸기 · 덱·슬라이드 글꼴 · 세션 활동 · 이미지 자리 보완

- **템플릿 부품 `parts`**: 레이아웃 코드는 그대로 두고 공통 부품 모양만 템플릿이 고른다 — `labels: "mono"`, `foot: "band" | "titleblock" | "minimal"`, `pageGhost`. `swiss`(고정폭 라벨 + 아래 띠) · `blueprint`(고정폭 라벨 + 도면 테두리·SHEET) · `archive`(큰 옅은 쪽 번호) · `keynote`(쪽 번호만). 장식은 `role: "decor"` 로 검사에서 뺀다.
- 편집기 **유형 바꾸기**: 썸네일 메뉴 "유형 바꾸기…" — 제목 글자·노트·id 를 남기고 다른 슬라이드 유형으로 바꾼다.
- **덱·슬라이드별 글꼴 세트**(`fontPreset`): 슬라이드 > 덱 > 작업 공간. 슬라이드 속성에서 고르고 편집기·PPTX·검사·쓴 글꼴 기록이 같은 규칙(`preset_fonts` ↔ `presetFonts`).
- **세션 활동 표시**: 새 작업 공간에 Claude Code 훅(`.claude/settings.json` → `nexa.py session_hook`)을 만들어 세션 칩에 "대화 작업 중 N분째 · 요청 n 대기" / "요청 처리 중" / "대기 — 요청 바로 처리" / "다른 세션 N" 을 보인다(`out/.studio/activity.json`).
- 새 작업 공간에 **`AGENTS.md`**(Codex·Gemini CLI·Cursor 용 같은 규칙 — 요청은 1회 대기 반복).
- 시작 페이지: 경로에 `&` 가 있으면 경고하고 명령을 실제 파이썬 실행 파일 경로로 안내(pyenv-win `python3` .bat 대리 실행기 문제).
- `lecture` 알약·태그 글자 15px 로(최소 글자 크기 검사 통과).
- Genspark 이미지 자리: CSS 배경(style 속성·`<style>` 클래스)으로 넣은 사진 11개 보완 — 199개(`04-image-slots.md`).

## 0.12.0 - 2026-10-02 · 승인 템플릿 반영 · 겹치는 기존 것 정리 · 슬라이드 유형 = 장 선별 기준

- **승인한 시각 템플릿 4개** 엔진에 추가: `keynote`(어두운 무대·금색·명조) · `archive`(종이 미색·테라코타·명조) · `blueprint`(도면 청록·주황·각진 모서리) · `swiss`(흰 바탕·빨강 하나·모서리 없음). 레이아웃 56종 견본 검사 ERROR 0.
- **승인한 템플릿 유형 5개 → 시작용 내용**: `periodic-report`(swiss) · `board-decision`(brief) · `ir-finance`(proposal) · `strategy-plan`(proposal) · `lecture-theory`(swiss) — 대표 장 흐름대로, 장마다 노트에 유형·목적(`build_type_starters.py`).
- **겹치는 기존 것은 숨기고 검토 대상으로**: 템플릿 `story`(→ archive)·`report`(→ swiss), 시작용 내용 `weekly-report`·`monthly-report`(→ periodic-report)·`decision-brief`(→ board-decision). `hidden: true` — 목록에서만 빠지고 이미 쓰는 작업 공간·`--starter` 는 그대로. `story-retro` 는 `archive` 로.
- 레이아웃 2종 추가(승인): `donut`(원호를 굵은 곡선으로 — PPTX 편집 가능) · `heatmap`(값 4단 색, 코호트 빈 칸). 결론 패널 색 토큰 `panel`·`on-panel`(어두운 템플릿에서도 읽히게).
- **슬라이드 유형 = 장 선별 기준**: 54개로(도넛·히트맵 추가), 유형마다 고를 신호 `when`. `nexa.py slide_types [낱말] [--json] [--group]`, 작업 공간 `CLAUDE.md` 에 "초안·요청 처리 때 내용 성격에 맞는 유형으로 고른다". 문서 `docs/slide-types.md` 선별 기준.
- 검토 등록부: 승인 안 된 대상 상태 초기화, 승인 대상에 구현 기록("구현됨"), 숨긴 기존 템플릿·시작용 내용을 검토 대상으로(그 템플릿으로 빌드한 미리보기).

## 0.11.0 - 2026-10-02 · 슬라이드 유형 52개 · 새 레이아웃 17종 · 템플릿 유형 15개 · 유형 검토

- **새 레이아웃 17종**(`studio/layouts_more.py`, 기존 요소만 — 렌더러 그대로): 본문 + 결론 패널 · 선 그래프 · 숫자 + 근거 차트 · 범위 막대 · 깔때기 · 선택지 열(추천 강조) · 사분면 · 큰 번호 행 · 트리 · 인물 카드 · 사례 제시 · 사진 도판 · 사진 + 한 문장 · 단계별 풀이 · 확인 문제 · 참고문헌 · 예상 질문. Genspark 전수 조사의 새 유형(03-slide-archetypes) 1·2순위 구현.
- **슬라이드 유형 52개**(`studio/slide_types.json`, 문서 `docs/slide-types.md`): 색·배치가 아닌 목적·구성 기준 8묶음. 유형마다 레이아웃 + 목적에 맞는 예시 내용 + 이미지 자리 안내. `GET /api/slidetypes`(유형별로 빌드한 슬라이드).
- 편집기 **슬라이드 추가 창**: "＋ 새 슬라이드" → 유형으로(목적별 미리보기 카드·찾기) / 레이아웃으로.
- **템플릿 유형 15개**(추천): 156개 덱을 목적·구성·시각 유사성으로 묶음 — 근거 덱·어울리는 시각 템플릿·대표 장 흐름(`docs/research/genspark-skills/05-template-types.md`).
- **검토 등록부**: 추천 상태("추천")와 분석 대상("등록") 구분, **슬라이드 유형 검토**(`/review/slides`, 기본 메뉴) 추가 — 엔진으로 그린 예시 + 근거 장, 템플릿 유형은 대표 장 흐름을 엔진으로 그려 미리보기.

## 0.10.2 - 2026-10-02 · 템플릿 검토를 시작 페이지에

- 검토 등록부를 별도 서버 첫 화면이 아니라 **시작 페이지(허브)에 붙는 페이지** `/review` 로 — 시작 페이지 탭·기본 메뉴 "템플릿 검토", 검토 화면에도 기본 메뉴. API 는 `/api/review/…`, 원본은 `/review/gs/…`(허브 서버가 `review_server` 모듈을 불러 처리, 따로 실행도 같은 경로).

## 0.10.1 - 2026-10-02 · 검토 등록부

- `docs/research/review/` - 템플릿·레이아웃 후보와 참고 자료(덱·사이트·파일)를 등록·미리보기·검토·승인하는 로컬 도구(`review_server.py` → http://127.0.0.1:5590/). 등록일·검토일·승인일·이력·메모를 `registry.json` 에 남기고 최근 등록 순으로 검토한다. 참고 덱은 전체 장 썸네일과 원본 HTML 실제 비율 보기. Genspark 조사 결과(템플릿 후보 8 · 레이아웃 28 · 참고 덱 156)를 `import_genspark.py` 로 등록. 원본은 저장소 밖에서 읽기만 한다.

## 0.10.0 - 2026-10-02 · 변경 기록 · 작업 공간 글꼴 · 글꼴 포함 PPTX · Genspark 전수 조사

- 편집기 **변경** 탭: 밖에서(Claude 등) 바뀐 덱을 다시 불러올 때 전·후를 비교해 장(수정·추가·삭제·이동 - 순서 유지 최장 흐름 밖만 이동)·요소(글자 전 → 후·위치·크기·모양·그림)별로 남긴다. 썸네일·개요 배지, 캔버스 파란 점선, 변경 묶음별 표시·숨기기.
- **작업 공간 글꼴**: 글꼴 파일은 엔진에 두지 않는다(`.gitignore`) — 작업 공간 `fonts/` + `nexa-slide.json` 의 `fontPresets`(전용 세트, 템플릿 세트보다 우선). 서버가 `fonts/` 를 내보내고(`/wsfonts/…`, `GET /api/fontcss` 자동 @font-face), 레이아웃 검사도 `fonts/` 로 잰다. `nexa.py install_fonts`(현재 사용자 설치), 새 작업 공간에 `fonts/README.md`. 추천 글꼴 내려받기 캐시는 엔진 밖으로.
- 편집기 글꼴 표시: 작업 공간 세트를 쓰면 머리줄 칩, ⋯ 메뉴 세트를 템플릿 기본/작업 공간 지정으로 나눔, **글꼴 창**(역할별 글꼴·견본·측정 파일, fonts/ 파일·설치 여부, 세트 JSON 수정·저장 - `POST /api/fonts savePreset`).
- **쓴 글꼴 기록**: 내보낼 때마다 `out/<덱>.fonts.json`(세트·역할별 글꼴·PPTX 에 실제로 들어간 글꼴마다 무료/시스템/전용·원본 파일·설치·포함 허용 fsType) — `font_report.py`.
- **글꼴 포함 PPTX**: 내보내기 메뉴 "PPTX — 글꼴 포함" · `nexa.py embed_fonts <덱>` → `out/<덱>-fonts.pptx`(PowerPoint COM, 쓴 글자만). 작업 공간 글꼴이 설치 안 됐으면 설치할지 묻는다.
- **무료 글꼴 목록·안내 페이지**: `studio/font_catalog.json`(무료 OFL 10종 · 시스템 기본 2종, 이름·라이선스·공식 받는 곳만), `/studio/fonts.html`(규칙, 이 작업 공간 글꼴 상태, 받기 링크, OS별 설치) · `GET /api/fontguide`. 목록 밖 글꼴은 "전용"으로 경고.
- 문서 `docs/fonts.md`, 엔진 `CLAUDE.md` 규칙(글꼴 파일 금지).
- 조사 `docs/research/genspark-skills/` - Genspark 공개 스킬 156개(2,274장) 전수 조사: 01 전수 표 · 02 시각 계열 9묶음과 템플릿 후보 8개 · 03 기존 레이아웃 대응 76% 와 새 유형 28개(우선순위) · 04 이미지 자리 6형태·역할 8가지·어울리는 이미지, `data/`(우리 말 요약만 — 원본은 저장소 밖).

## 0.9.0 - 2026-10-02 · 미리 보기 · 명령으로 만들기 · AI 연결 문서 · 새 덱 안내

- 시작 페이지 **미리 보기**: 템플릿 카드·시작용 내용 카드·새로 만들기 양식에서 템플릿 × 내용으로 실제 빌드한 슬라이드를 창으로 본다(썸네일 → 크게 보기·← →, 덱 탭, "이 조합으로 만들기"). 내용을 고르지 않으면 레이아웃 견본(레이아웃마다 한 장). 사용자 설정 폴더 `hub/preview/<템플릿>--<내용>/` 에 임시 작업 공간을 만들어 빌드하고 엔진·템플릿·내용이 바뀌면 다시 만든다(`GET /api/preview`).
- **명령으로 만들기**: 새로 만들기 양식 아래에 양식 값으로 채운 `init_workspace.py` 명령과 서버 시작 명령을 보여 준다(PowerShell · bash, 복사 버튼, 경고). 서버 `plan`(`POST /api/project action=plan`)이 폴더·포트·명령을 정하고 "만들고 Studio 열기"도 같은 명령을 실행한다.
- 포트 칸: 비우면 비어 있고 최근 작업 공간 설정이 쓰지 않는 포트(허브 포트 제외)를 제안, 적으면 그 포트. 하위 폴더는 폴더·저장소 지정일 때 제목으로 자동 채움(저장소면 `slides`, 직접 고치면 유지, 기본 위치로 돌아가면 비움).
- `init_workspace.py`: `--port N|auto`(쓰는 포트·허브 포트 거절, 다른 작업 공간 설정과 겹치면 알림, 기존 작업 공간은 포트만 변경) · `--build` · `--purpose` `--audience` `--direction`… `--material`…(BRIEF.md) · `--ask-draft` · `--no-remember`. 만든 작업 공간을 최근 작업에 올리고, 끝에 붙여 넣을 수 있는 절대 경로 명령을 안내한다. 브리프·빌드·초안 요청 로직을 허브에서 옮겨 와 버튼과 명령이 같은 결과를 낸다.
- 편집기: 2초 확인에 덱 목록·설정·엔진 버전을 함께 받아(`/api/version` 의 `deckIds`·`decksVer`·`config`·`engine`) 새 덱이 생기면 덱 탭을 바로 갱신하고 "새 덱 — [열기]" 안내, 설정이 바뀌면 자동 다시 적용, 엔진이 바뀌면 [새로 고침] 안내.
- 문서 `docs/ai-editing.md` - 새로 만든 작업 공간에서 AI 로 고치기: Claude Code(터미널·VS Code·Desktop) 상시 감시, 그 밖의 AI(Codex·Gemini CLI·Cursor) 1회 대기 반복·수동 방식, 요청·초안·마무리·문제 해결.
- 수정: `column_chart`·`stack_bars` 필드 예시가 비어 있어 "새 슬라이드"·레이아웃 견본에서 빌드 오류가 나던 문제.
- 조사 `docs/research/genspark-skills/` - Genspark 공개 슬라이드 스킬 156개 전수 조사 계획·원칙·진행 현황(원본은 저장소 밖).

## 0.8.0 - 2026-10-02 · 목적별 시작용 교안 8종 · 목적별 디자인 6종 · 레이아웃 16종

- 시작용 교안(`starters/`): `weekly-report`(8장) · `monthly-report`(11장) · `decision-brief`(2장) · `schedule`(7장) · `story-retro`(12장) · `notice-onboarding`(10장) · `rfp-owner`(12장) · `rfp-response`(14장), `lecture-course` 보강(3일 시간표·한 문장 장). 용도별 인기 템플릿 조사에서 나온 공통 규칙(제목 = 결론, 결론 2장 안, 마지막 장 = 다음 행동, 숫자에 기준·실명·기한, 나쁜 소식 같은 무게)대로 예시를 썼다. `init_workspace.py --starter` 는 시작용 교안이 정한 디자인 템플릿을 기본으로 고른다.
- 디자인 템플릿 6종(`lecture` 바탕, `tokenOverrides` 로 색·글꼴·모서리만): `report`(네이비) · `brief`(차콜·딥 틸) · `story`(미색·테라코타·명조 제목) · `notice`(오렌지·큰 모서리) · `schedule`(블루) · `proposal`(인디고·골드). 칩·글자 최소 15px.
- 토큰: 상태색 `ok`·`caution`·`bad`·`info`·`idle`(+`-container`), 글꼴 키 `heading`(제목용, 기본 = 본문). `template.json` 의 `tokenOverrides` 를 `resolve_tokens` 가 적용(편집기·PPTX·허브 미리보기 공통).
- 레이아웃 16종(`studio/layouts_extra.py`, 기존 요소만 조합): `status_table` · `kpi_tiles` · `issue_cards` · `grid_cards` · `statement` · `quote` · `big_number` · `decision_brief` · `milestones` · `roadmap` · `gantt` · `week_grid` · `photo_text` · `agenda` · `column_chart`(누적·워터폴·합계 막대·여러 판) · `stack_bars`. 공통 필드 `action`(행동 띠)·`footnote`·`kick`.
- `bullets` 에 `aside`(오른쪽 작은 개념 차트 - 세로 막대·가로 누적 막대·범례).
- 문서 `docs/starters.md`(목록·디자인·공통 작성 규칙·레이아웃 필드).

## 0.7.0 - 2026-10-02 · 시작 페이지 · 기본 메뉴 · 제작 도구와 내용 분리

- 엔진에 슬라이드 내용을 두지 않는다: 작업 공간을 못 찾으면 현재 폴더를 쓰지 않고, 서버는 **허브(시작 페이지)** 로 뜬다(포트 5599, 실행 정보는 사용자 설정 폴더). 엔진 폴더 안의 작업 공간(`example/`)은 서버가 열지 않는다. 작업 공간이 필요한 도구는 안내를 내고 끝난다.
- 기준 폴더: 운영체제 기본 문서 폴더(Windows 알려진 폴더 - OneDrive 이동 포함, macOS `~/Documents`, Linux XDG) 아래 `NexaSlide/`, 제작마다 하위 폴더. `NEXA_SLIDE_PROJECTS` · 사용자 설정 `projectsRoot` 로 바꾼다. 사용자가 폴더·저장소를 지정하면 그 아래에 내용과 서버 실행 정보를 넣는다(`studio/paths.py`).
- 시작 페이지 `studio/home.html`(`hub.py`): 새 슬라이드 만들기(템플릿 · 목적·대상·작성 방향·참고 자료 → `BRIEF.md` · 저장 위치 · 첫 초안 요청), 폴더·저장소 열기(폴더 고르기 창, 작업 공간 없으면 그 자리에 만들기), 최근 작업, 튜토리얼, 데모(예제를 기준 폴더로 복사해 열기), 템플릿 목록, 샘플 사이트 등록·둘러보기.
- `/` 이동: 작업할 덱이 있으면 Studio, 없으면 시작 페이지. 만들기·열기는 그 작업 공간 서버를 띄워 Studio 로 넘긴다.
- 기본 메뉴 `studio/menu.js`: Studio·시작 페이지 머리줄 왼쪽 위 메뉴 단추 → 왼쪽 서랍(GitHub 방식) - 홈 · 새로 만들기 · 열기 · Studio · 튜토리얼 · 데모 · 템플릿 · 샘플 · 최근 작업(찾기) · 기준 폴더 설정.
- API: `GET /api/home` · `POST /api/project`(create/open/demo/forget) · `POST /api/settings` · `GET /api/fs`. 문서 `docs/home.md`.
- 0.6.0 시작용 교안(`starters/`)과 함께 병합 - 시작 페이지는 `starters/<이름>/starter.json` 을 인식한다.

## 0.6.0 - 2026-10-02 · 강의 교안 시작용(lecture-course)

- `starters/lecture-course/` - 실제 강의 교재(3일 과정)의 구성을 익명화한 시작용 교안: 공통 표지·전체 목차·EoD(`_common.json`), 과정 안내 장 ch00(본문 24장, 레이아웃 17종 예시)·이론 장 ch01(본문 12장, Mermaid 다이어그램), 일차 이름·표지 배지 선택값. 로고는 자리 표시, 내용은 자리 표시와 일반 예제(주문 관리).
- `init_workspace.py --starter lecture-course` - 시작용 내용·그림 복사, `partLabels`·`coverBadge` 반영, 빌드할 덱 안내.
- `docs/lecture-starter.md` - 구성 순서, 장·절·소분류·실습 번호 체계(장 번호 = 교육 순서), 각주·노트(원문) 규약, 작성 규칙.
- 수정: 작업 공간이 엔진과 다른 드라이브(Windows)에 있으면 실행기 `nexa.py` 안내 문구의 절대 경로 역슬래시가 문법 오류(유니코드 이스케이프)를 내던 문제 - 경로를 `/` 로 쓴다.

## 0.5.3 - 2026-10-02 · 요청 칸 Enter 남기기

- 편집기 요청 탭의 슬라이드 요청 칸: Enter = 메모 남기기(초안), Shift+Enter = 줄바꿈 - 요소 메모 팝오버와 같은 동작. 보내기는 그대로 아래 바 "요청 N개 보내기".

## 0.5.2 - 2026-10-02 · 바닥 각주 가로 배치 · 요청 입력 보관

- 바닥 각주(`role: footnotes`): 위치 표시(crumb)는 각주가 없는 슬라이드와 같은 왼쪽 아래 자리에 고정하고, 각주는 그 바로 위(아래 끝 668, 쪽번호 칩 위)에 9pt(12px)로 1, 2, 3 순서대로 가로로 잇는다. 한 줄 폭을 넘으면 각주 단위로 줄을 바꾼다(`layouts.foot_lines`).
- 바닥 각주 번호는 위첨자 대신 보통 숫자를 굵은 강조색(`==n==`)으로 - 작은 글씨에서도 번호가 잘 보이게. 본문 표식(`[[theory|¹]]`)은 그대로.
- 편집기: 아직 남기지 않은 요청 입력(요청 탭 슬라이드 요청 칸 · 요소 메모)을 덱·슬라이드·요소별로 브라우저에 보관 - 슬라이드를 옮기거나 새로 고쳐도 유지, 메모를 남기면 지움.

## 0.5.1 — 2026-10-01 · 새 프로젝트 시작 도구·설명서

- `studio/init_workspace.py <폴더>` — 작업 공간 뼈대(선택만 담은 nexa-slide.json · 실행기 nexa.py · CLAUDE.md 세션 안내 · 시작용 content · .gitignore · 자리 표시 로고), 빈 포트 자동 선택.
- `studio/layout_samples.py` — 레이아웃 21종과 필드 예시(초안 작성용, 실행기 `nexa.py layout_samples`).
- `docs/new-project.md` — 다른 폴더·저장소에서 VS Code(Claude Code)·Claude Desktop 으로 연결해 초안 작성·검토·내보내기까지, macOS·Windows 명령 병기.

## 0.5.0 — 2026-10-01 · 편집기 UI 개편 (Genspark 작업 화면 방식 차용, 슬라이드 디자인 불변)

- 모드 3분할 **편집(E) · 선택(M) · 그리기(D)** — 선택은 요소를, 그리기는 박스·펜·핀 영역을 눌러 그 자리 **메모 팝오버**(개체 종류별 빠른 칩, Enter = 추가) → 번호 배지·레일 ✎ 배지 → 아래 바 **"요청 N개 보내기"**(초안 → 대기, 즉시 전달). 취소 범위 = 이 슬라이드(없으면 전체).
- 모드 바 아래 **붙박이 서식 줄**: 글꼴 · 크기 px(프리셋)·pt · 글자색 · 굵게 · 정렬 · 줄 간격·세로 정렬 · 채우기 · 테두리 · 선 속성 · 복제 · 삭제 · 잠금 · **위치 조정 ▾**(정렬 6 · 순서 4 · 너비/높이/X/Y). 색은 템플릿 토큰 팔레트.
- 오른쪽 클릭 메뉴, 순서 단축키(Ctrl+] [ · Alt+Ctrl+] [), Ctrl+X/B, 모드 키 E/M/D, 도움말 ?.
- ✨ 레이아웃 고치기(검사 결과를 담아 바로 요청) · ✨ 다듬기.
- 바닥줄: 노트 · 개요 · 검사 탭, ◀ n/N ▶, **확대 10~300%**(Ctrl+휠 포인터 기준 · Ctrl+= - 0 1) · Space+끌기 화면 이동.
- 머리줄: 덱 탭 · ▶ 발표(F5 · Shift+F5 · N 노트·시간) · 기록(자동 백업 되돌리기) · 내보내기 ▾ · 더보기(글꼴 세트·템플릿·단축키).
- **바뀐 것이 없으면 저장하지 않음**. 레일 폭 조절·오른쪽 패널 접기·배치 기억.
- 서버: 요청 `draft`·`region`·`send`·`discard`, `GET /api/history/<id>`. 감시 이벤트에 `region` 포함.

## 0.4.1 — 2026-10-01 · 요청 감시 "가짜 연결" 방지

- Monitor 만료 시 셸만 끝나고 python 감시가 남아 하트비트만 쓰던 문제(편집기는 "연결됨", 요청은 전달 안 됨)를 막음:
  - `--ttl`(`--stream` 기본 1780초) 뒤 `{"event":"ttl"}` 을 내고 스스로 종료
  - `--takeover` 로 남은 이전 감시를 끝내고 넘겨받기

## 0.4.0 — 2026-10-01 · 디자인 템플릿

- `studio/templates/<이름>/`(template.json · tokens.json · design/) — 색·글꼴·글자 크기·검사 기준·디자인 기준 문서를 템플릿으로 묶음.
  - `lecture`(기본): 기존 디자인·크기 그대로(0.3 까지와 결과 동일 확인), 검사 기준 11·8·9pt — 크기 조정은 장 단위 검토에서
  - `lecture-large`: 글자만 일괄 확대(본문 15px · 각주 11px · 경로·쪽번호 12px) — 선택 사항
  - 원칙: 기능(검사·세션 연결·템플릿)은 Genspark 등에서 차용하되 구성·디자인은 기존 형태 유지
- 작업 공간은 선택만: `template`·`fontPreset`. 작업 공간 `tokens.json`·`designCss`·`check.minFontPt` 는 더 쓰지 않는다(`check` 는 ignore·ignoreSlides 만).
  - 글꼴 선택(`set_fonts.py`·편집기)은 `nexa-slide.json` 의 `fontPreset` 을 바꾼다
  - `/studio/tokens.json` 은 템플릿 + 선택을 매번 계산해 준다. `GET /api/templates`
  - `NEXA_SLIDE_TEMPLATE` 로 설정을 바꾸지 않고 미리보기
- 디자인 기준 문서(concept.html·tokens.css)를 템플릿으로 옮기고 회사 로고·문구를 자리 표시로 바꿈.

## 0.3.0 — 2026-10-01 · 레이아웃 검사

- `check_layout.py` + `GET /api/check/<id>` + 편집기 "검사" 탭(저장마다 자동 · 항목 클릭 = 요소로 이동·영역 표시 · 썸네일 ⚠ 배지).
- 규칙: `t1.overlap.text-text` · `t1.overlap.text-crosses-border` · `t2.cutoff.spill` · `t2.cutoff.container` · `t3.offslide` · `t4.font.min`(역할별 최소 pt) · `t5.mono.align`(실행계획 열 정렬).
  Genspark `check_slide_layout` 실측(규칙 id·기하 판정)을 본뜨고, Genspark 에 없는 최소 글자·고정폭 정렬·요소 이동을 더했다.
- 기준 설정 `nexa-slide.json` `check`(minFontPt · ignore · ignoreSlides).
- 검사로 찾은 실제 결함 예(교재 덱): 파일 경로 줄바꿈 겹침, 장 표지 설명 넘침, 8.25pt 글자.

## 0.2.0 — 2026-10-01 · 독립 저장소로 분리

sql-tutorial-with-oracle 저장소의 `ppt/studio`(슬라이드 스튜디오 v0)를 엔진으로 분리했다. 렌더·PPTX 규칙은 그대로다
(분리 전후 ch00·ch18 덱 빌드 JSON 과 PPTX 184·259 파트가 완전히 같음).

- **작업 공간 분리**: `--workspace` / `NEXA_SLIDE_WORKSPACE` / 위로 찾기, 설정 `nexa-slide.json`(경로·`assetRoot`·토큰·브랜드·부 이름·표지 배지·EoD 안내·포트).
  - URL `/studio/`(엔진) · `/out/`(산출물) · 그 밖 `assetRoot`.
- **여러 작업 공간 동시 운영**:
  - 작업 공간별 포트
  - 작업 공간당 서버 하나(중복 시작 거부)
  - 배타적 포트 열기(Windows `SO_EXCLUSIVEADDRUSE`)
  - `service.py start|stop|restart|status|url` 백그라운드 서비스, `status.py`
  - 실행 정보 `out/.studio/server.json`
- **Claude 세션 연결**:
  - `watch_requests.py --stream`(요청 묶음마다 JSON 한 줄 — Monitor 알림), 하트비트 `out/.studio/session.json`
  - 작업 공간당 감시 하나(중복 시 `refused`)
  - 편집기 세션 칩(연결됨/처리 중/연결 없음) · "요청 보내기"/"지금 보내기"(flush) · 요청 상태 `working`
- **배포**: MIT `LICENSE`, `THIRD_PARTY_NOTICES.md`(외부 구성요소 재배포 없음, 회사 CI 미포함), 예제 작업 공간 `example/`(자리 표시 로고), 문서 `docs/` 7편.

## 0.1 — 2026-09 · 슬라이드 스튜디오 v0 (sql-tutorial-with-oracle `ppt/studio`)

덱 JSON 단일 원본, 브라우저 편집기, python-pptx 기본 도형 PPTX, PowerPoint 렌더 미리보기·픽셀 비교, 요청 메모 → 세션 전달(1회 감시).
이력은 원 저장소 git 기록에 있다.
