# nexa-slide

**웹 편집기에서 고치고, PowerPoint 기본 도형으로 된 _편집 가능한_ PPTX 를 만드는 슬라이드 엔진.**
덱 JSON 하나가 원본이고, 브라우저 렌더(`render.js`)와 PPTX 변환(`export_pptx.py`)이 같은 규칙으로 각각 그린다.
Claude Code 세션과 연결하면 편집기에 남긴 요청 메모가 세션에 바로 전달되어 처리된다.

- 서버는 Python 표준 라이브러리만 쓴다(외부 웹 프레임워크·CDN·npm 없음). PPTX 생성에 `python-pptx`.
- PPTX 는 이미지로 굽지 않는다 — 글상자·도형·표·연결선·그룹 그대로라 PowerPoint 에서 계속 고칠 수 있다.
- 화면과 PPT 의 어긋남을 수치로 검증한다(`compare.py` 픽셀 차이, `check_parity.py` JS↔Python 결과 동일성).
- 라이선스: [MIT](LICENSE) — 상업적 사용 포함 무료. 제3자 구성요소는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## 빠른 시작

```bash
git clone git@github.com:SosomLab/nexa-slide.git
cd nexa-slide
python3 -m pip install -r requirements.txt

python3 studio/service.py start      # 시작 페이지 → http://127.0.0.1:5599/  (새로 만들기 · 열기 · 튜토리얼 · 데모 · 템플릿 · 샘플)

# 명령으로 작업 공간 만들기 → docs/new-project.md
python3 studio/init_workspace.py ../my-talk/slides --title "신제품 소개"
# 강의 교안이면 시작용 교안으로 → docs/lecture-starter.md
python3 studio/init_workspace.py ../my-course/slides --title "과정 이름" --starter lecture-course
python3 ../my-talk/slides/nexa.py start   # 덱이 있으면 바로 Studio
```

**엔진에는 슬라이드 내용을 저장하지 않는다.** 시작 페이지에서 템플릿·작성 방향·자료를 받고 **내용을 둘 폴더·저장소를 먼저 정한다**.
정하지 않으면 운영체제의 문서 폴더 아래 `NexaSlide/<제목>` 에 만든다. 자세히는 [docs/home.md](docs/home.md).

## 여러 작업 공간을 함께 운영

엔진은 **실행 코드와 디자인 템플릿**을 제공하고, 각 폴더·저장소는 `nexa-slide.json` 에서 **고르기만** 한다(포트·템플릿·글꼴 프리셋·브랜드 파일·경로) — 디자인 값은 저장소에 두지 않는다([docs/templates.md](docs/templates.md)).

```
D:\Projects\
├─ nexa-slide\                 엔진(이 저장소) — 한 벌만 clone
├─ repo-A\slides\  nexa-slide.json {"port": 5600, …} + nexa.py   ← repo-A 에서 연 Claude 세션이 감시
└─ repo-B\deck\    nexa-slide.json {"port": 5610, …} + nexa.py   ← repo-B 에서 연 Claude 세션이 감시
```

- 작업 공간마다 포트가 다르면 서버를 함께 띄울 수 있다. 같은 포트·같은 작업 공간의 두 번째 서버는 거부한다(`--port auto` 는 빈 포트를 찾는다).
- **작업 공간 하나 = 서버 하나 = 요청 감시 하나 = Claude 세션 하나.** 상태 파일(`out/.studio/`)이 작업 공간마다 따로라 서로 섞이지 않는다.
- `python3 <작업 공간>/nexa.py start | stop | restart | status | url` — [docs/operation.md](docs/operation.md#여러-작업-공간)

## 구조

```
nexa-slide/
├─ studio/                 엔진 — 이 폴더만 있으면 어디서든 동작(작업 공간은 --workspace 로 지정)
│   ├─ server.py           로컬 서버(정적 파일 + API)          ├─ index.html · studio.js   편집기
│   ├─ hub.py · paths.py   시작 페이지 동작 · 기준 폴더·사용자 설정 ├─ home.html · menu.js     시작 페이지 · 기본 메뉴
│   ├─ common.py           작업 공간·설정 해석, 공용 규칙      ├─ render.js                요소 → HTML 렌더러
│   ├─ layouts.py          레이아웃 빌더 21종                  ├─ slide.html               검증용 1:1 슬라이드
│   ├─ build_deck.py       content → 덱 JSON                  ├─ (토큰은 templates/<이름>/)
│   ├─ export_pptx.py      덱 JSON → PPTX                     ├─ fonts.css                편집기 글꼴(@font-face)
│   ├─ watch_requests.py   요청 감시 → Claude 세션 전달        ├─ render_pptx.ps1          PowerPoint 렌더(Windows)
│   ├─ compare.py · check_parity.py   일치 검증                └─ install_fonts.ps1        OFL 글꼴 설치(Windows)
│   ├─ service.py · status.py   서비스 시작·중지·상태(작업 공간별 포트)
│   ├─ init_workspace.py    새 작업 공간 만들기(설정·실행기·CLAUDE.md·시작 내용·빈 포트)
│   ├─ layout_samples.py    레이아웃 21종과 필드 예시(초안 작성용)
│   ├─ check_layout.py      레이아웃 검사 — 겹침·넘침·최소 글자(pt)·슬라이드 밖·고정폭 정렬
│   ├─ templates/          디자인 템플릿 — lecture(기존 디자인) · lecture-large(글자 확대). tokens.json · template.json · design/
│   └─ set_fonts.py · gen_tokens_css.py · render_mermaid.py
├─ example/                예제(데모 원본) - 서버는 엔진 안에서 열지 않고 시작 페이지 "데모"가 기준 폴더로 복사해 연다
├─ starters/               시작용 교안 9종 — 강의 교안·주간/월간 보고·결정 요청·일정·회고·공지·RFP(발주/응답) (init_workspace.py --starter)
└─ docs/                   설치 · 설정 · 서버 · 운영 · 세션 연결 · 덱 형식 · 편집기
```

**작업 공간**은 덱을 만드는 쪽(교재·발표 저장소)의 폴더다. 엔진은 작업 공간의 `nexa-slide.json` 을 읽어
`content/`·`decks/`·`out/`·브랜드(로고)·토큰을 찾는다. 엔진과 내용이 분리되어 있어 엔진만 업데이트할 수 있다.

## 문서

| 문서 | 내용 |
|---|---|
| **[docs/home.md](docs/home.md)** | **시작 페이지·기본 메뉴 — 기준 폴더(OS 문서 폴더), 새로 만들기·열기·데모·템플릿·샘플, 사용자 설정** |
| **[docs/new-project.md](docs/new-project.md)** | **새 폴더·저장소에서 시작하기 — VS Code·Claude Desktop 연결, 슬라이드 초안 작성·검토·내보내기 상세 절차(macOS·Windows 명령)** |
| [docs/install.md](docs/install.md) | 요구 사항, 설치, 글꼴, 새 작업 공간 만들기, 기존 저장소에 붙이기(실행기) |
| [docs/starters.md](docs/starters.md) | 목적별 시작용 교안 9종과 디자인 템플릿 6종 — 구성, 공통 작성 규칙, 새 레이아웃 16종 필드 |
| [docs/lecture-starter.md](docs/lecture-starter.md) | 강의 교안 시작용(`--starter lecture-course`) — 구성 순서, 장·절·실습 번호 체계, 각주·노트 규약, 작성 규칙 |
| [docs/templates.md](docs/templates.md) | 디자인 템플릿 — 제공 템플릿, 폴더 구성, 작업 공간이 고르는 것, 바꾸기·새로 만들기 |
| [docs/configuration.md](docs/configuration.md) | `nexa-slide.json` 전 항목·기본값, 작업 공간 찾기 순서, `tokens.json`·글꼴 프리셋 |
| [docs/server.md](docs/server.md) | 서버 실행 옵션, URL 구성, API 전체, 보안 범위, 동시 편집 처리 |
| [docs/operation.md](docs/operation.md) | 일상 운영 — 빌드·내보내기·렌더·비교, 백업·복원, 포트·프로세스 점검, 문제 해결 |
| **[docs/ai-editing.md](docs/ai-editing.md)** | **새로 만든 작업 공간에서 AI 로 고치기 — Claude Code(터미널·VS Code·Desktop)·그 밖의 AI(Codex·Gemini CLI·Cursor) 연결, 요청·초안·마무리 과정** |
| [docs/claude-session.md](docs/claude-session.md) | Claude Code 세션 연결 — 상시 감시(Monitor), 세션 상태 표시, 지금 보내기, 처리 규약 |
| [docs/fonts.md](docs/fonts.md) | 글꼴 — 기본 세트(엔진)와 작업 공간 전용 글꼴(`fonts/` · `fontPresets`), 편집기 글꼴 창, `install_fonts` |
| [docs/slide-types.md](docs/slide-types.md) | 슬라이드 유형 54개 — 목적·구성 기준, 고를 신호, 초안·요청 처리의 장 선별 기준, 편집기 "유형으로 추가" |
| [docs/deck-format.md](docs/deck-format.md) | 덱 JSON·요소 모델, content 형식, 레이아웃, 인라인 강조, 각주 규칙 |
| [docs/editor.md](docs/editor.md) | 편집기 조작, 화면↔PPT 일치 규칙, 알려진 한계 |
| [docs/research/](docs/research/genspark-ai-slides.md) | 참고 조사 — Genspark AI Slides 실측(진행 과정·저장 구조·편집 화면·레이아웃 검사 원문) |
