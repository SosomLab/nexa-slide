# 설치

## 요구 사항

| 구성 | 필수 여부 | 쓰는 곳 |
|---|---|---|
| Python 3.10 이상 | 필수 | 서버·빌드·내보내기 전부 |
| `python-pptx` | 필수 | PPTX 내보내기 |
| `Pillow` | 권장 | 글자 폭 정밀 측정(칩·코드 폭 자동 맞춤), `compare.py` |
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
