# 설치

## 요구 사항

| 구성 | 필수 여부 | 쓰는 곳 |
|---|---|---|
| Python 3.10 이상 | 필수 | 서버·빌드·내보내기 전부 |
| `python-pptx` | 필수 | PPTX 내보내기 |
| `Pillow` | 권장 | 글자 폭 정밀 측정(칩·코드 폭 자동 맞춤), `compare.py` |
| `pymupdf` | 선택 | PDF 첨부 내용 추출(`import_doc` - 글·표·그림). Word·Excel 추출은 추가 설치 없음 |
| Node.js 18 이상 | 선택 | `check_parity.py`(render.js 를 Node 로 실행), `render_mermaid.py`(npx mermaid-cli) |
| Chrome 또는 Edge | 선택 | `compare.py` 헤드리스 캡처 |
| PowerPoint + PowerShell (Windows) | 선택 | 편집기 "PPT 렌더 미리보기", `render_pptx.ps1` |
| Claude Code 또는 Codex CLI | 선택 | 편집기 요청을 AI 가 처리 — [claude-install.md](claude-install.md) · [openai-codex.md](openai-codex.md) |

macOS·Linux 에서도 서버·편집기·빌드·PPTX 내보내기는 된다. PowerPoint 렌더 미리보기와 `compare.py` 의 PowerPoint 쪽 비교만 Windows 전용이다.

## 설치 절차

```bash
git clone git@github.com:SosomLab/nexa-slide.git
cd nexa-slide
python3 -m pip install -r requirements.txt
python3 studio/server.py                          # 동작 확인 → http://127.0.0.1:5599/ 시작 페이지 → "데모"
```

> Windows Git Bash 에서는 `python` 이 다른 래퍼일 수 있다. `python-pptx` 가 설치된 `python3`(또는 venv 의 python)을 쓴다.

## 글꼴 (선택)

기본 프리셋 `default` 는 운영체제 글꼴(맑은 고딕·Consolas)을 쓴다. 추천 프리셋 `modern`(Pretendard · JetBrains Mono + D2Coding — 모두 SIL OFL)을 쓰려면:

```powershell
pwsh -NoProfile -File studio/install_fonts.ps1       # 현재 사용자에게 설치(관리자 권한 불필요). 내려받기 캐시 = .cache/fonts
python3 studio/set_fonts.py --workspace <작업 공간> modern
```

PowerPoint·브라우저는 글꼴 설치 후 다시 열어야 보인다. 편집기는 서버가 `/api/fontfile` 로 글꼴 파일을 직접 주므로 설치 직후에도 보인다.

## 새 작업 공간 만들기

> 처음부터 끝까지의 상세 절차(macOS·Windows, VS Code·Claude Desktop)는 **[new-project.md](new-project.md)**. 아래는 손으로 만드는 방법이다 — 보통은 `studio/init_workspace.py <저장소 폴더>` 한 줄이면 된다(그 아래 `slides/` 에 작업 공간, 루트에 `SLIDES.md`).

예제를 복사해서 시작한다.

```bash
cp -r example ../my-deck-repo/slides          # 작업 공간 = slides/
# slides/nexa-slide.json 의 title·brand·partLabels 를 고치고, content/<id>.json 을 쓴다
python3 studio/build_deck.py --workspace ../my-deck-repo/slides <id>
python3 studio/server.py --workspace ../my-deck-repo/slides
```

작업 공간 저장소의 `.gitignore` 에 넣을 것:

```gitignore
slides/out/              # PPTX·렌더 PNG·세션 상태(.studio)
slides/decks/.history/   # 자동 백업
```

## 기존 저장소에 붙이기 — 실행기

작업 공간 저장소에 실행기 `nexa.py` 를 두면 엔진 경로를 매번 적지 않아도 된다. `init_workspace.py` 가 만들고,
손으로 만든 작업 공간이면 엔진 도구로 넣는다: `python3 <엔진>/studio/update_launcher.py --workspace <작업 공간>`.

```
python3 <작업 공간>/nexa.py start|stop|status|url | build_deck ch00 --force | watch_requests --stream
python3 <작업 공간>/nexa.py engine [<엔진 폴더>]     # 이 PC 의 엔진 위치 보기 · 정하기
```

서비스 구성은 작업 공간에 둔다 — `nexa-slide.json` 의 `port`(다른 작업 공간과 겹치지 않게)·`title`·`brand`·경로.

엔진 위치 우선순위: `.env` 의 `NEXA_SLIDE_HOME`(PC 별, git 제외 — 있으면 가장 먼저, 샘플 `.env.example`) > `nexa-slide.local.json` > 셸 환경변수 `NEXA_SLIDE_HOME` > 이 PC 의 사용자 설정(엔진을 실행하면 기록) > `nexa-slide.json` 의 `engine`.
여러 PC 에서 같은 저장소를 쓰는 방법은 [configuration.md](configuration.md#여러-pc-에서-쓰기--pc-별-설정-env--nexa-slidelocaljson).

## 저장소를 받은 뒤 할 일 (clone 이후)

시작 페이지 머리의 **ⓘ 설정 안내**(최근 작업 카드의 ⓘ 도 같음)가 아래 명령을 **이 PC 의 실제 경로**로 채워 보여 주고 복사 단추를 둔다.

**엔진 저장소**(`nexa-slide`)를 받은 PC — 위 설치 절차가 전부다(`pip install`, `python3 studio/server.py`).
서버 작업(엔진 요청 큐)을 맡길 Claude Code 세션은 엔진 저장소에서 열고 `/nexa-slide-server` 를 입력하면 된다 — 슬래시 명령 파일 `.claude/commands/nexa-slide-server.md` 는 저장소에 들어 있어(0.21.12) 따로 둘 것이 없다.

**작업 공간 저장소**(슬라이드 내용)를 다른 PC 에서 받았을 때 — PC 마다 한 번:

| 순서 | 명령 | 하는 일 |
|---|---|---|
| ① 엔진 위치 | `python3 <작업 공간>/nexa.py engine <엔진 폴더>` | 이 PC 의 엔진을 `nexa-slide.local.json` 에 기록(PC 별, git 제외). `.env.example` 을 `.env` 로 복사해 `NEXA_SLIDE_HOME=` 을 적어도 된다 — [configuration.md](configuration.md#여러-pc-에서-쓰기--pc-별-설정-env--nexa-slidelocaljson) |
| ② 실행기·세션 파일 | `python3 <작업 공간>/nexa.py update_launcher` | 실행기 `nexa.py` 를 이 엔진 판으로 바꾸고, **없으면** `.claude/commands/nexa-slide-server.md`·`nexa-slide-session.md`(슬래시 명령 `/nexa-slide-server`·`/nexa-slide-session` — 저장소형이면 **루트 `.claude/commands/` 에도** 같은 명령을 둔다. Claude Code 는 연 폴더(cwd)의 명령만 읽으므로)·`.claude/settings.json`(세션 훅·권한)·`.env.example`·`.gitignore` 항목을 **자동으로 만든다**(복사가 아니라 엔진이 생성 — 있는 파일은 그대로, 설정·내용은 건드리지 않음) |
| ③ 서버 | `python3 <작업 공간>/nexa.py start` · `status` · `url` · `stop` | 작업 공간 서버(시작 페이지의 [서버 시작]과 같음) |
| ④ 세션 | 그 폴더(CLI) 또는 **저장소 루트**(VS Code 는 보통 루트에서 연다)에서 연 Claude Code 세션에 **`/nexa-slide-session`** | 이 작업 공간의 슬라이드 세션이 된다(편집기 요청 처리 — `watch_requests --stream` 을 Monitor 로, 규약은 `CLAUDE.md`). 서버 작업(엔진 요청 큐)을 맡기려면 **`/nexa-slide-server`**(하나뿐). 웹 세션이 맡고 있으면 `refused` — 먼저 [세션 중지]; 다른 터미널 세션이면 물은 뒤 `--takeover` |

`init_workspace.py` 로 만든 작업 공간은 ② 가 이미 되어 있다. 저장소 주인이 `nexa.py`·`.claude/commands/`·`.claude/settings.json`·`.env.example` 을 **커밋해 두면** clone 받은 사람은 ① 만 하면 된다
(`.env`·`nexa-slide.local.json` 은 PC 별 파일이라 `.gitignore` 에 있고 커밋하지 않는다). 엔진이 새 판이 되어 명령·훅이 바뀌었을 때도 ② 를 다시 돌리면 없는 것만 더해진다.
