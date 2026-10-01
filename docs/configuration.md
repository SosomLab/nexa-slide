# 설정

## 작업 공간을 찾는 순서

모든 도구(`server.py`·`build_deck.py`·`export_pptx.py`·`watch_requests.py` …)가 같은 규칙을 쓴다(`studio/common.py`).

1. 명령행 `--workspace <경로>` (또는 `-W`, `--workspace=<경로>`) — 어느 위치에 써도 된다
2. 환경변수 `NEXA_SLIDE_WORKSPACE`
3. 현재 폴더부터 위로 올라가며 `nexa-slide.json` 이 있는 첫 폴더

못 찾으면 현재 폴더를 작업 공간으로 쓰지 않는다(엔진 폴더에 내용이 생기지 않게).
서버·`service.py`·`status.py` 는 허브(시작 페이지)로 뜨고, 나머지 도구는 안내를 내고 끝난다.
엔진 폴더 안의 작업 공간(예: `example/`)은 서버가 열지 않는다 - 시작 페이지 "데모"가 기준 폴더로 복사해 연다([home.md](home.md)).

정해진 작업 공간은 `NEXA_SLIDE_WORKSPACE` 로 하위 프로세스에 넘어간다(서버가 실행하는 export·set_fonts·렌더도 같은 작업 공간을 쓴다).

## `nexa-slide.json`

경로는 모두 **작업 공간 폴더 기준 상대 경로**다. 파일이 없으면 전부 기본값으로 동작한다.

| 키 | 기본값 | 설명 |
|---|---|---|
| `port` | `5600` | 서버 포트. 함께 띄울 작업 공간끼리 다르게 준다(명령행 `--port` 가 우선) |
| `title` | 폴더 이름 | 편집기 머리줄·브라우저 탭 제목, 통합본(`book`) 덱 제목 |
| `engine` | — | 실행기(`nexa.py`)가 엔진을 찾는 경로. 엔진 자신은 읽지 않는다 |
| `assetRoot` | `.` | 덱의 그림 경로(`src`·`img`)의 기준 폴더. 서버가 이 폴더를 `/` 로 내준다 |
| `content` | `content` | 내용 원본 `<id>.json` · 공통 슬라이드 `_common.json` |
| `decks` | `decks` | 덱 `<id>.json` · 요청 메모 `<id>.requests.json` · 백업 `.history/` |
| `out` | `out` | PPTX · 렌더 PNG · 비교 이미지 · 세션 상태 `.studio/` |
| `template` | `lecture` | **디자인 템플릿 이름**(`studio/templates/<이름>/`) — 색·글꼴·글자 크기·검사 기준은 모두 템플릿에 있다([templates.md](templates.md)) |
| `fontPreset` | 템플릿 기본 | 템플릿 `fontPresets` 중 하나(편집기 글꼴 선택·`set_fonts.py` 가 바꾼다) |
| `brand.name` | `""` | 로고 대체 글자(alt) |
| `brand.logo` | `assets/brand/logo.png` | 머리 오른쪽·표지 로고(`assetRoot` 기준). 가로세로 비율은 PNG 머리에서 읽는다 |
| `brand.wordmark` | `assets/brand/wordmark.png` | 바닥 워드마크 |
| `brand.favicon` | — | 편집기 파비콘 |
| `partLabels` | `Part 1`·`Part 2`·`Part 3`·`Appendix` | 부(`day1`/`day2`/`day3`/`apx`) 칩 이름 |
| `coverBadge` | `Presentation` | 표지 배지 기본 문구(content 의 `badge` 가 우선) |
| `check` | `{}` | 검사에서 뺄 것만 — `ignore`(규칙 id 목록), `ignoreSlides`(덱별 슬라이드 id). 기준값(최소 pt)은 템플릿 |
| `endNextNote` | `""` | 문서 끝(EoD) "다음 순서" 칩 뒤에 붙일 설명(예: `"  (장 번호가 아니라 교육 순서)"`) |

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
