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

python3 studio/service.py --workspace example start   # 백그라운드 서버 → http://127.0.0.1:5601/ (예제 설정 포트)
python3 studio/export_pptx.py --workspace example demo # → example/out/demo.pptx
python3 studio/service.py --workspace example stop
```

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
│   ├─ common.py           작업 공간·설정 해석, 공용 규칙      ├─ render.js                요소 → HTML 렌더러
│   ├─ layouts.py          레이아웃 빌더 21종                  ├─ slide.html               검증용 1:1 슬라이드
│   ├─ build_deck.py       content → 덱 JSON                  ├─ (토큰은 templates/<이름>/)
│   ├─ export_pptx.py      덱 JSON → PPTX                     ├─ fonts.css                편집기 글꼴(@font-face)
│   ├─ watch_requests.py   요청 감시 → Claude 세션 전달        ├─ render_pptx.ps1          PowerPoint 렌더(Windows)
│   ├─ compare.py · check_parity.py   일치 검증                └─ install_fonts.ps1        OFL 글꼴 설치(Windows)
│   ├─ service.py · status.py   서비스 시작·중지·상태(작업 공간별 포트)
│   ├─ check_layout.py      레이아웃 검사 — 겹침·넘침·최소 글자(pt)·슬라이드 밖·고정폭 정렬
│   ├─ templates/          디자인 템플릿 — lecture(기존 디자인) · lecture-large(글자 확대). tokens.json · template.json · design/
│   └─ set_fonts.py · gen_tokens_css.py · render_mermaid.py
├─ example/                예제 작업 공간(nexa-slide.json · content · decks · 자리 표시 로고)
└─ docs/                   설치 · 설정 · 서버 · 운영 · 세션 연결 · 덱 형식 · 편집기
```

**작업 공간**은 덱을 만드는 쪽(교재·발표 저장소)의 폴더다. 엔진은 작업 공간의 `nexa-slide.json` 을 읽어
`content/`·`decks/`·`out/`·브랜드(로고)·토큰을 찾는다. 엔진과 내용이 분리되어 있어 엔진만 업데이트할 수 있다.

## 문서

| 문서 | 내용 |
|---|---|
| [docs/install.md](docs/install.md) | 요구 사항, 설치, 글꼴, 새 작업 공간 만들기, 기존 저장소에 붙이기(실행기) |
| [docs/templates.md](docs/templates.md) | 디자인 템플릿 — 제공 템플릿, 폴더 구성, 작업 공간이 고르는 것, 바꾸기·새로 만들기 |
| [docs/configuration.md](docs/configuration.md) | `nexa-slide.json` 전 항목·기본값, 작업 공간 찾기 순서, `tokens.json`·글꼴 프리셋 |
| [docs/server.md](docs/server.md) | 서버 실행 옵션, URL 구성, API 전체, 보안 범위, 동시 편집 처리 |
| [docs/operation.md](docs/operation.md) | 일상 운영 — 빌드·내보내기·렌더·비교, 백업·복원, 포트·프로세스 점검, 문제 해결 |
| [docs/claude-session.md](docs/claude-session.md) | Claude Code 세션 연결 — 상시 감시(Monitor), 세션 상태 표시, 지금 보내기, 처리 규약 |
| [docs/deck-format.md](docs/deck-format.md) | 덱 JSON·요소 모델, content 형식, 레이아웃, 인라인 강조, 각주 규칙 |
| [docs/editor.md](docs/editor.md) | 편집기 조작, 화면↔PPT 일치 규칙, 알려진 한계 |
