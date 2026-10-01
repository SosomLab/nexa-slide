# 운영

아래 명령의 `-W <ws>` 는 `--workspace <작업 공간>` 의 줄임이다(실행기를 쓰면 생략).

## 작업 흐름

```bash
python3 studio/build_deck.py   -W <ws> ch00            # content/ch00.json → decks/ch00.json (덱이 있으면 멈춤)
python3 studio/build_deck.py   -W <ws> ch00 --force    # 덮어쓰기(기존 덱은 .history 백업)
python3 studio/build_deck.py   -W <ws> book [--chapters ch00 ch18]   # 통합본
python3 studio/export_pptx.py  -W <ws> ch00            # → out/ch00.pptx
python3 studio/render_mermaid.py -W <ws> ch18 [--all]  # content 의 mermaid → PNG (바뀐 것만)
pwsh -File studio/render_pptx.ps1 -Pptx <ws>/out/ch00.pptx -OutDir <ws>/out/ch00   # PowerPoint 렌더 PNG
python3 studio/compare.py      -W <ws> ch00 [--slides 1,5] [--port 5600]   # 브라우저 vs PowerPoint 픽셀 비교
python3 studio/check_parity.py -W <ws> [ch00 …]        # render.js ↔ common.py 결과 동일 확인(node 필요)
python3 studio/gen_tokens_css.py -W <ws> [--write]     # tokens.json ↔ designCss 값 일치 확인/갱신
python3 studio/set_fonts.py    -W <ws> [default|modern]   # 글꼴 프리셋
python3 studio/check_layout.py -W <ws> [ch00 …] [--json]  # 레이아웃 검사(ERROR 가 있으면 종료 코드 1)
```

## 레이아웃 검사

편집기 "검사" 탭이 저장할 때마다 자동으로 다시 검사한다(썸네일 ⚠ 배지 = 그 슬라이드 건수, 빨강 = ERROR 포함). 항목을 누르면 그 슬라이드·요소로 가고 해당 영역을 점선으로 표시한다.

| 규칙 | 등급 | 내용 |
|---|---|---|
| `t1.overlap.text-text` | ERROR(작은 쪽 10% 이상)/WARNING | 글자가 있는 두 요소의 실제 글자 영역이 겹침 |
| `t1.overlap.text-crosses-border` | WARNING | 글자 영역이 다른 도형의 경계에 걸침(시퀀스 다이어그램 이름표처럼 의도일 수 있음 — 눈으로 확인) |
| `t2.cutoff.spill` | ERROR(15% 이상)/WARNING | 글자가 자기 상자보다 높음(줄 수 추정) · 줄바꿈 없는 줄이 폭을 넘음 · 코드/실행계획 줄 수가 상자보다 김 |
| `t2.cutoff.container` | WARNING | 글자 영역이 그것을 담은 도형 밖으로 나감 |
| `t3.offslide` | ERROR | 요소가 1280×720 밖으로 나감 |
| `t4.font.min` | ERROR | 글자 크기 < 역할별 최소 pt(pt = px × 0.75). 기본 `default` 9pt · `footnotes` 7pt |
| `t5.mono.align` | WARNING | 실행계획의 `\|` 열 위치가 줄마다 다름(강조 표시를 뺀 원문 기준) |

규칙 id 는 Genspark `check_slide_layout` 형식(t1 겹침·t2 잘림 계층)을 본떴고, 최소 글자·고정폭 정렬·요소로 이동은 nexa-slide 에만 있다.
기준은 작업 공간 `nexa-slide.json` 의 `check` 로 바꾼다:

```json
"check": {"minFontPt": {"default": 9, "footnotes": 7, "crumb": 9}, "ignore": ["t1.overlap.text-crosses-border"], "ignoreSlides": {"ch00": ["s12"]}}
```

줄바꿈은 어절 단위로 글꼴 폭을 재서 흉내 내는 추정이다(Pillow 가 있으면 실제 글꼴). 최종 확인은 `compare.py`(PowerPoint 렌더 대조).

- **build 보호**: `--force` 여도 마지막 빌드 뒤 편집기에서 고친 슬라이드가 있으면 멈추고 번호·종류를 알려 준다.
  고친 내용을 content 에 옮긴 뒤 다시 빌드하거나, 버려도 되면 `--discard-edits`. 비교 기준 = `decks/.history/<id>/last-build.json`.
- 공통 슬라이드(`content/_common.json`)를 바꾸면 각 장을 `--force` 로 다시 빌드한다.

## 여러 작업 공간

엔진은 한 벌, 서비스 구성은 각 작업 공간(`nexa-slide.json` + `nexa.py`)에 둔다.

```bash
python3 <작업 공간>/nexa.py start      # 그 작업 공간의 설정 포트로 백그라운드 실행(이미 떠 있으면 주소만 알림)
python3 <작업 공간>/nexa.py status     # 작업 공간·덱·서버(포트·pid)·세션 연결·대기/처리 중 요청
python3 <작업 공간>/nexa.py url        # 접속 주소
python3 <작업 공간>/nexa.py stop       # 그 작업 공간 서버만 종료
```

| 원칙 | 이유 |
|---|---|
| 작업 공간마다 `port` 를 다르게 | 함께 띄우기. 겹치면 뒤에 띄운 쪽이 "포트를 쓸 수 없다"로 멈춘다 |
| 작업 공간당 서버 하나 | 두 번째 시작은 거부(기존 주소 안내) |
| 작업 공간당 요청 감시 하나 | 살아 있는 감시가 있으면 새 감시는 `{"event":"refused"}` 한 줄을 내고 끝난다 |
| Claude 세션은 그 작업 공간의 저장소에서 연다 | 세션의 작업 폴더·규칙(CLAUDE.md)·git 이 그 저장소이므로 요청 처리·커밋이 그 저장소에 남는다 |

## 백업 · 복원

| 대상 | 위치 | 보존 |
|---|---|---|
| 편집기 저장 전 덱 | `decks/.history/<id>/<시각>.json` | 최근 50개 |
| build 덮어쓰기 전 덱 | `decks/.history/<id>/<시각>-build.json` | 50개에 포함 |
| 마지막 빌드 결과 | `decks/.history/<id>/last-build.json` | 1개 |

복원 = 백업 파일을 `decks/<id>.json` 으로 복사. 편집기가 2초 안에 다시 불러온다(편집 중이면 충돌 선택).
`.history` 와 `out/` 은 git 에서 제외한다 — 덱 JSON 자체는 작업 공간 저장소에서 git 으로 관리한다.

## 포트·프로세스 점검

```powershell
# Windows — 5600 을 쓰는 프로세스와 명령줄
Get-NetTCPConnection -LocalPort 5600 -State Listen | % { Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" } | select ProcessId, CommandLine
# 요청 감시 프로세스
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ? CommandLine -like '*watch_requests*' | select ProcessId, CommandLine
Stop-Process -Id <PID> -Force
```

```bash
# macOS / Linux
lsof -iTCP:5600 -sTCP:LISTEN
pgrep -fl watch_requests
```

- 같은 작업 공간에 감시를 둘 이상 띄우지 않는다 — 같은 요청이 두 세션에 전달된다. 하트비트 파일(`out/.studio/session.json`)은 마지막에 쓴 감시의 것만 남는다.
- Windows Git Bash 의 `kill` 은 래퍼만 끝내고 python 이 남을 수 있다 — `Stop-Process`/`taskkill /F` 를 쓴다.

## 문제 해결

| 증상 | 확인 |
|---|---|
| 편집기 "덱 없음" | 작업 공간이 맞는지(`/api/config` 의 `workspace`), `decks/` 에 덱이 있는지 — 없으면 build_deck |
| 로고가 안 보임 | `nexa-slide.json` `brand.logo` 경로가 `assetRoot` 기준인지 |
| 그림이 깨짐(404) | 덱의 `src` 가 `assetRoot` 기준 상대 경로인지 |
| "포트를 쓸 수 없다" | 다른 작업 공간이 그 포트를 쓰는 중 — `nexa-slide.json` 의 `port` 를 바꾸거나 `--port auto` |
| "이미 실행 중" | 그 작업 공간 서버가 떠 있다 — `nexa.py url` 로 주소 확인 |
| "세션 연결 없음" | 세션이 감시를 실행 중인지([claude-session.md](claude-session.md)). Monitor 는 최대 30분 — 만료되면 다시 건다 |
| PPT 렌더 실패 | PowerPoint 설치·`pwsh` 경로, 이전 렌더가 진행 중이면 429 |
| PPT 와 화면 글자 위치가 다름 | 글꼴을 바꿨다면 `compare.py` 로 다시 재서 `pptTextShift` 수정 |
| 저장 충돌이 반복 | 같은 덱을 다른 브라우저 탭에서 열었는지 |
