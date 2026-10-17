# 설계 메모 — 회사 템플릿 만들기 마법사 (색 5개·로고·글꼴)

> 협업 세션 정리, 2026-10-17. 엔진 요청 큐 항목의 근거. "결정" 표시가 없는 것은 **제안**이다.
> 후보 출처: `docs/dev/feature-comparison.md:61,148`, `docs/dev/web-session-design.md:280`.

## 0. 먼저 정할 것 — 원칙 충돌

지금 템플릿은 **엔진 `studio/templates/` 에서만** 읽는다(`common.py:163`, `hub.py:26`, `set_template.py:17`, `init_workspace.py:708`, `hub.plan` `:475`, `hub.preview` `:700`). 문서도 "작업 공간에 tokens.json·design/·검사 기준값을 두지 않는다 … 새 템플릿은 엔진에 추가"(`docs/templates.md:3-5,59`, `home.html:368`, `init_workspace.py:316`)라고 막는다.
한편 회사 색·로고·글꼴은 **엔진 저장소에 넣으면 안 된다**(CLAUDE.md — 상표·글꼴). 그래서 "작업 공간에 템플릿 폴더" 는 원칙을 **좁게 바꾸는** 일이다. 안:

| 안 | 내용 | 평가 |
|---|---|---|
| **A (제안)** | 작업 공간 `templates/<이름>/template.json` **하나만** 허용 — 반드시 `extends: <엔진 템플릿>` + `tokenOverrides`·`label`·`description`·`parts`. `tokens.json`·`design/`·`sizes`·`check` 는 금지(엔진에서 물려받음) | 원칙("토큰 체계·검사 기준은 엔진이 소유")은 유지하고 색만 회사 것. 기존 16개 템플릿이 정확히 이 형태라 로더 변경이 작다 |
| B | 폴더 없이 `nexa-slide.json` 에 `tokenOverrides` 를 직접 둔다 | 더 작지만 "템플릿" 으로 고르거나 다른 작업 공간에 옮길 수 없다 |
| C | 엔진에 템플릿 추가(지금 원칙) | 회사 색을 공개 저장소에 넣게 됨 — 기각 |

**사용자 확인 필요**: A 로 갈지. 아래는 A 기준.

## 1. 요구사항

허브에서 색 5개·로고·글꼴(선택)을 넣으면 → 작업 공간에 템플릿이 생기고 → 미리 보기로 확인 → 그 작업 공간(또는 새 작업 공간)에 적용.

## 2. 지금 구조 (조사 결과)

- 템플릿 17개, `lecture` 만 완전체(`tokens.json`·`design/`), 나머지 16개는 `template.json` 에 `extends: lecture` + `tokenOverrides` 만(예 `templates/brief`, `keynote`). `template.json` 에 필수 키 없음 — `_merge` 깊은 병합(`common.py:174-190`), 해석 순서 `resolve_tokens`(`common.py:221-252`).
- 색 역할(`lecture/tokens.json` `groups`): 목적별 템플릿이 실제로 덮는 것은 약 20개 — `primary`·`on-primary`·`primary-container`·`on-primary-container`, `surface`·`surface-dim`·`surface-container(-high)`, `on-surface(-variant)`, `outline-variant`, `day1~3`·`-container`·`on-…-container`. keynote 는 `white`·`panel`·`on-panel`·`fonts.heading`·`radius` 까지.
- 로고는 template.json 이 아니라 작업 공간 `nexa-slide.json` `brand.{name,logo,wordmark,favicon}`(`docs/configuration.md:38-41`), 기본 `assets/brand/logo.png`(`layouts.py:37-40`), 비율은 PNG IHDR(`_png_ratio` `layouts.py:26`) — **PNG 만**.
- 글꼴: 파일은 작업 공간 `fonts/`, 세트는 `nexa-slide.json` `fontPresets` + `fontPreset`(`docs/fonts.md`), 저장 API `POST /api/fonts {savePreset}`.
- 고르기: `nexa-slide.json` `template`(`set_template.py`, local 이 우선), **서버 재시작 필요**(`TEMPLATE` 을 import 때 한 번 읽음 `common.py:207`; `docs/templates.md:65`). 편집기는 `workspace_stamp`(`server.py:316-323`)로 새로 고침 안내 — 엔진 `templates/**` 만 감시.
- 새로 만들기: `home.html:216-260` `#newForm`(① 제목·템플릿 격자 `#fTpls`·시작용 내용 ② 목적… ③ 위치) → `POST /api/project {plan|create}` → `hub.plan`(`:467-550`) → `init_workspace.py` 인자. 템플릿 탭 `#p-templates`(`home.html:366-369,1019-1043`).
- 미리 보기: `GET /api/preview?template=&starter=`(`hub.preview` `:692-746`)가 `hub/preview/` 에 임시 작업 공간을 실제로 만들고 빌드, 브라우저는 `Render.setTokens(tokens)` 로 그린다 — **화면은 토큰 JSON 만 바꾸면 된다**. 로고·`parts`·`sizes` 는 빌드 때 정해져 토큰만으론 안 보인다. 템플릿 이름은 엔진 폴더에 있어야 함(`:700`).
- 팔레트 파생 함수 없음. WCAG 대비 `check_layout.py:128-144`(`_lum`·`contrast`) 재사용 가능.

## 3. 설계 결정(제안, 안 A)

1. **입력 → 토큰**: 색 5개 = `primary`, `surface`(배경), `on-surface`(본문 글자), `accent1`→`day1`, `accent2`→`day2`(day3 은 primary 와 accent 사이 혼합). 나머지(`*-container`·`on-*`·`surface-dim/container`·`outline-variant`)는 **파생**: container = 해당 색을 surface 쪽으로 85~90% 섞기, on-색 = 대비 4.5:1 이상인 흑/백(또는 primary 진하게). 파생 함수는 `studio/palette.py`(새, 순수 함수 — 서버·CLI 공용). 사용자가 파생값을 고칠 수 있게 "고급" 펼침.
2. **기반 템플릿**: 마법사 첫 칸에서 엔진 템플릿 하나 고름(기본 `lecture`, 숨김 제외) → `extends`.
3. **생성물**(작업 공간만):
   - `templates/<이름>/template.json` = `{extends, label, description, tokenOverrides:{colors, fonts?}}`
   - 로고 → `assets/brand/logo.png`(·`wordmark.png`), `nexa-slide.json` `brand` 갱신. PNG 아니면 거부(또는 Pillow 있으면 변환).
   - 글꼴 → 파일은 `fonts/`, 세트는 `nexa-slide.json` `fontPresets.<이름>` + `fontPreset`. 공개 글꼴만 고르면 파일 없음.
   - 엔진 저장소에는 아무것도 쓰지 않는다(시험으로 확인).
4. **로더 변경**: 템플릿 찾기 순서 = 작업 공간 `templates/` → 엔진 `studio/templates/`(같은 이름이면 작업 공간 우선? → **금지 제안**: 엔진 이름과 겹치면 생성 거부, 혼동 방지). 고칠 곳: `common.py` 템플릿 경로 해석·`resolve_tokens`, `set_template.py` 목록, `hub.workspace templates`(`/api/home`·`/api/templates`), `init_workspace`, `hub.preview`, `workspace_stamp` 에 작업 공간 `templates/**` 추가, `render.js` 쪽 차이 없음(토큰으로 받음). 작업 공간 template.json 의 금지 키는 로더가 무시하고 경고.
5. **자리**: 허브 시작 페이지 **템플릿 탭 `#p-templates` 맨 앞 "＋ 회사 템플릿 만들기" 카드**(새로 만들기 ①의 템플릿 격자 끝에도 같은 카드 → 마법사 → 끝나면 그 템플릿이 선택된 채로 돌아옴). 대상 작업 공간: 새로 만들기 흐름이면 생성 후 그 작업 공간에, 템플릿 탭이면 "최근 작업" 중 하나 고름.
6. **미리 보기**: 서버 왕복 없이 브라우저에서 — 기반 템플릿의 `/api/preview` 결과(이미 빌드된 레이아웃 샘플)에 마법사 토큰을 `Render.setTokens` 로 덮어 그린다. 로고는 미리 보기 슬라이드의 로고 요소 `src` 를 올린 파일의 object URL 로 바꿔 보인다. 대비 경고(`contrast` < 4.5) 표시.
7. **생성 뒤**: 허브 API `POST /api/project {action:"template", ws, name, base, colors, brand, font}`(관리자 또는 그 작업 공간 사용자) → 파일 쓰기 → `set_template.py <이름>` 와 같은 처리 → **작업 공간 서버 재시작**을 허브가 제안(단추 "지금 다시 시작", 세션 턴 중이면 drain 뒤). 안내 문구에 "기존 덱의 글자 크기 하한은 `build_deck --force` 때 적용".
8. **접근 로그**: `template.create:<ws>:<이름>`.

## 4. 완료 기준

- 마법사로 만든 템플릿이 그 작업 공간에서만 목록에 보이고, 편집기·PPTX 양쪽에 같은 색으로 나온다(`check_parity -W <사본>`).
- 엔진 저장소 `git status` 깨끗(생성물 0).
- 파생 on-색 대비 4.5:1 이상, 아니면 경고.
- `docs/templates.md`(원칙 문구 수정 — "작업 공간 템플릿은 extends+tokenOverrides 만"), `docs/home.md`, `docs/configuration.md` `brand`, i18n(ko/en).

## 5. 시험

- `studio/tests/template_wizard_test.py`: 격리 사용자 폴더·example 사본 → API 로 생성 → 파일 3종(template.json·logo·nexa-slide.json) 확인 → `resolve_tokens` 결과 색 일치 → `export_pptx --out` 의 `srgbClr` 에 primary 값 존재 → 엔진 이름 충돌 거부 → 금지 키(tokens/design) 무시.
- `palette.py` 단위 시험(대비·혼합 값).
- 수동: 허브에서 색 5개·PNG 로고로 만들고 미리 보기·재시작·편집기 확인.
