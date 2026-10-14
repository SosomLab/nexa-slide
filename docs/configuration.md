# 설정

## 작업 공간을 찾는 순서

모든 도구(`server.py`·`build_deck.py`·`export_pptx.py`·`watch_requests.py` …)가 같은 규칙을 쓴다(`studio/common.py`).

1. 명령행 `--workspace <경로>` (또는 `-W`, `--workspace=<경로>`) — 어느 위치에 써도 된다
2. 환경변수 `NEXA_SLIDE_WORKSPACE`
3. 현재 폴더부터 위로 올라가며 `nexa-slide.json` 이 있는 첫 폴더 — 저장소 루트면 **루트 표식 `.nexa-slide.json`** 의 `workspace`(예: `slides`·`ppt`)가 가리키는 폴더,
   표식이 없으면 `slides/`(저장소형: 저장소 루트나 그 아래 폴더에서 실행)

**루트 표식 `.nexa-slide.json`**(저장소 루트, 커밋한다) — `{"workspace": "ppt"}`. 이 저장소의 작업 공간 폴더 이름이다.
`init_workspace.py` 가 만들고(이미 다른 작업 공간을 가리키면 고치지 않음), 예전 저장소는 `nexa.py update_launcher` 가 더한다.
시작 페이지 "열기"·엔진 도구·세션 훅이 이것으로 작업 공간을 찾는다 — 작업 공간 폴더 이름을 바꿔도(`--slides-dir`) 루트에서 그대로 동작한다.

못 찾으면 현재 폴더를 작업 공간으로 쓰지 않는다(엔진 폴더에 내용이 생기지 않게).
서버·`service.py`·`status.py` 는 허브(시작 페이지)로 뜨고, 나머지 도구는 안내를 내고 끝난다.
엔진 폴더 안의 작업 공간(예: `example/`)은 서버가 열지 않는다 - 시작 페이지 "데모"가 기준 폴더로 복사해 연다([home.md](home.md)).

정해진 작업 공간은 `NEXA_SLIDE_WORKSPACE` 로 하위 프로세스에 넘어간다(서버가 실행하는 export·set_fonts·렌더도 같은 작업 공간을 쓴다).

## `nexa-slide.json`

경로는 모두 **작업 공간 폴더 기준 상대 경로**다. 파일이 없으면 전부 기본값으로 동작한다.

| 키 | 기본값 | 설명 |
|---|---|---|
| `port` | `5600` | 서버 포트. 함께 띄울 작업 공간끼리 다르게 준다(명령행 `--port` 가 우선). 허브 중계(`/w/<이름>/`)로 열 때는 이 포트가 쓰는 중이면 다음 빈 포트로 띄우므로 겹쳐도 멈추지 않는다([operation.md](operation.md#허브-중계--포트-하나5599로-여러-studio)) |
| `title` | 폴더 이름 | 편집기 머리줄·브라우저 탭 제목, 통합본(`book`) 덱 제목 |
| `engine` | — | 실행기(`nexa.py`)가 엔진을 찾는 기본 경로. PC 마다 다르면 `nexa-slide.local.json` 또는 PC 설정이 우선([아래](#여러-pc-에서-쓰기--pc-별-설정-env--nexa-slidelocaljson)). 엔진 자신은 읽지 않는다 |
| `assetRoot` | `.` | 덱의 그림 경로(`src`·`img`)의 기준 폴더. 서버가 이 폴더를 `/` 로 내준다 |
| `content` | `content` | 내용 원본 `<id>.json` · 공통 슬라이드 `_common.json` |
| `decks` | `decks` | 덱 `<id>.json` · 요청 메모 `<id>.requests.json` · 백업 `.history/` |
| `out` | `out` | PPTX · 렌더 PNG · 비교 이미지 · 세션 상태 `.studio/` |
| `template` | `lecture` | **디자인 템플릿 이름**(`studio/templates/<이름>/`) — 색·글꼴·글자 크기·검사 기준은 모두 템플릿에 있다([templates.md](templates.md)) |
| `fontPreset` | 템플릿 기본 | 템플릿 `fontPresets` 또는 작업 공간 `fontPresets` 중 하나(편집기 글꼴 선택·`set_fonts.py` 가 바꾼다) |
| `fontPresets` | 없음 | 작업 공간 전용 글꼴 세트 `{이름: {body, heading?, mono?}}` — 글꼴 파일은 `fonts/`(`fontsDir` 로 바꿀 수 있음). [fonts.md](fonts.md) |
| `brand.name` | `""` | 로고 대체 글자(alt) |
| `brand.logo` | `assets/brand/logo.png` | 머리 오른쪽·표지 로고(`assetRoot` 기준). 가로세로 비율은 PNG 머리에서 읽는다 |
| `brand.wordmark` | `assets/brand/wordmark.png` | 바닥 워드마크 |
| `brand.favicon` | — | 편집기 파비콘 |
| `partLabels` | `Part 1`·`Part 2`·`Part 3`·`Appendix` | 부(`day1`/`day2`/`day3`/`apx`) 칩 이름 |
| `coverBadge` | `Presentation` | 표지 배지 기본 문구(content 의 `badge` 가 우선) |
| `check` | `{}` | 검사에서 뺄 것만 — `ignore`(규칙 id 목록), `ignoreSlides`(덱별 슬라이드 id). 기준값(최소 pt)은 템플릿 |
| `endNextNote` | `""` | 문서 끝(EoD) "다음 순서" 칩 뒤에 붙일 설명(예: `"  (장 번호가 아니라 교육 순서)"`) |
| `repo` | 없음 | 저장소형 작업 공간 표시(`init_workspace.py` 가 씀) — `root`(저장소 관리 기준 폴더, 보통 `..`). 시작 페이지가 저장소 루트를 보인다 |

예 — 교재 저장소의 `ppt/` 를 작업 공간으로, 그림 경로는 저장소 루트 기준:

```json
{
  "port": 5600,
  "title": "SQL 튜닝 교재",
  "engine": "../../nexa-slide",
  "template": "lecture",
  "fontPreset": "modern",
  "assetRoot": "..",
  "brand": {"name": "ACME", "logo": "assets/brand/acme-ci.png",
            "wordmark": "assets/brand/acme-wordmark.png", "favicon": "assets/brand/favicon.png"},
  "partLabels": {"day1": "Day1 · 설계", "day2": "Day2 · 쿼리와 옵티마이저", "day3": "Day3 · 실무 종합", "apx": "부록"},
  "coverBadge": "SQL 실무 교육",
  "endNextNote": "  (장 번호가 아니라 교육 순서)"
}
```

> 기존 덱의 그림 경로가 저장소 루트 기준이면 `assetRoot` 를 그 루트로 맞춘다. 덱 JSON 은 고치지 않아도 된다.

> **원칙**: 작업 공간은 고르기만 한다 — `tokens.json`·디자인 기준 문서·검사 기준값을 작업 공간에 두지 않는다. 다른 디자인이 필요하면 엔진에 템플릿을 추가한다.

## 여러 PC 에서 쓰기 — PC 별 설정 `.env` · `nexa-slide.local.json`

작업 공간 저장소를 여러 PC 에서 clone 해 고치면, PC 마다 다른 값(엔진 위치·포트 등)이 생긴다. 이것은 공유 설정에 커밋하지 않고
작업 공간 폴더의 PC 별 파일에 둔다 — 둘 다 `.gitignore` 에 들어 있다.

**`.env`** — 실행기(`nexa.py`) 환경. `NEXA_SLIDE_HOME=<엔진 폴더>` 를 적으면 그 엔진이 **가장 먼저** 쓰인다.
`init_workspace.py` 가 샘플 **`.env.example`**(커밋)과 이 PC 의 **`.env`**(지금 엔진 위치가 채워짐)를 함께 만든다.
다른 PC 에서 clone 했으면 `.env.example` 을 `.env` 로 복사해 그 PC 의 엔진 위치를 적는다.

```
# slides/.env
NEXA_SLIDE_HOME=D:/Projects/nexa-slide       # 절대 경로 또는 작업 공간 기준 상대 경로, Windows 도 / 가능, ~ 가능
```

`.env` 의 다른 `KEY=VALUE` 도 실행기가 엔진 도구에 환경변수로 넘긴다(셸 환경변수보다 우선). `#` 주석·`export` 접두·따옴표 값을 읽는다.

**`nexa-slide.local.json`** — 설정 덮어쓰기. 모든 도구가 이 파일의 값을 `nexa-slide.json` 위에 덮어써 읽는다
(dict 값은 안쪽 항목만 — 예: `{"brand": {"logo": "…"}}`). 편집기·`set_fonts` 가 설정을 저장할 때는 공유 `nexa-slide.json` 에만 쓴다.

```json
{ "engine": "D:/Tools/nexa-slide", "port": 5610 }
```

**엔진 위치**는 실행기(`nexa.py`)가 다음 순서로 찾는다 — 실제로 엔진(`studio/server.py`)이 있는 첫 경로:

1. `.env` 의 `NEXA_SLIDE_HOME` — git 에서 제외되는 이 PC 전용 파일, **있으면 가장 먼저**
2. `nexa-slide.local.json` 의 `engine` — 이 PC 전용. `python3 nexa.py engine <엔진 폴더>` 가 쓴다(`--clear` 로 지움)
3. 셸 환경변수 `NEXA_SLIDE_HOME`
4. 이 PC 의 사용자 설정(`settings.json`) `engine` — 엔진을 한 번 실행하면(시작 페이지·`service.py start`·`init_workspace.py`) 그 위치가 기록된다
5. `nexa-slide.json` 의 `engine` — 저장소에 커밋된 기본값(작업 공간 기준 상대 경로)

앞 순서(`.env`·`nexa-slide.local.json`)에 적은 경로에 엔진이 없으면 알림 한 줄을 내고 다음 순서로 넘어간다.

그래서 PC 마다 엔진을 다른 곳에 두어도, 그 PC 에서 엔진을 한 번 실행하면 저장소의 실행기가 그 엔진을 쓴다. 엔진을 옮겼으면 새 위치에서 다시 실행하거나
`nexa.py engine <새 위치>` 로 정한다. 지금 어느 엔진을 쓰는지: `python3 nexa.py engine`.

예전에 만든 작업 공간은 실행기를 새 판으로 바꾼다 — `python3 <작업 공간>/nexa.py update_launcher`
(실행기를 바꾸고, `.gitignore` 에 `.env`·`nexa-slide.local.json` 을 더하고, 없으면 `.env.example`·`.env` 를 둔다. 설정·내용은 그대로).

## 템플릿 `tokens.json` — 디자인 토큰

`studio/templates/<이름>/tokens.json`. 단위는 px(슬라이드 1280×720 기준). 편집기(`render.js`)와 PPTX(`export_pptx.py`)가 같은 값을 읽는다.

| 키 | 내용 |
|---|---|
| `colors` | 색 역할 → `#RRGGBB` 또는 다른 토큰 이름(따라감). 부 색 `day1`·`day1-container`·`on-day1-container` … |
| `radius` | `r-s`·`r-m`·`r-l`·`r-full` → px |
| `fonts` | 현재 글꼴 `body`·`mono` — 각각 `latin`(라틴)·`ea`(한글) |
| `fontPresets` · `fontPreset` | 글꼴 세트 목록과 현재 이름. `set_fonts.py <이름>` 또는 편집기 글꼴 선택이 `fonts` 를 바꾼다 |
| `codeStyle` | 코드 색(예약어·함수·테이블·별칭·문자열·숫자·주석·바인드) |
| `pptTextShift` | PowerPoint 줄 배치 보정 측정값 — 글꼴을 바꾸면 `compare.py` 로 다시 잰다 |

작업 공간이 고른 `fontPreset` 이 `fonts` 를 정한다. 색·반경·보정값을 바꾸려면 새 템플릿을 만든다([templates.md](templates.md#새-템플릿-만들기)).
