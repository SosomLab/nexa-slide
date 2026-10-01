# 새 폴더·저장소에서 nexa-slide 로 슬라이드 초안 만들기 — 상세 설명서

다른 폴더(또는 git 저장소)에서 **VS Code(Claude Code 확장)** 나 **Claude Desktop** 으로 nexa-slide 를 연결해
슬라이드 초안을 만들고, 편집기에서 검토·요청하며 다듬는 전체 과정이다. 명령은 **macOS(zsh/bash)** 와 **Windows(PowerShell)** 를 함께 적는다.

> 이 문서의 예: 엔진은 `~/Projects/nexa-slide`(Windows `D:\Projects\nexa-slide`), 슬라이드를 만들 저장소는 `~/Projects/my-talk`(Windows `D:\Projects\my-talk`),
> 그 안의 작업 공간 폴더는 `slides/`. 경로는 자기 환경에 맞게 바꾼다.

---

## 0. 한눈에 보기

```
~/Projects/
├─ nexa-slide/            엔진 — 한 벌만 clone (실행 코드 + 디자인 템플릿)
└─ my-talk/               내 저장소 (VS Code·Claude Desktop 에서 이 폴더를 연다)
   └─ slides/             작업 공간 — init_workspace.py 가 만든다
      ├─ nexa-slide.json  선택만: 포트 · 제목 · 템플릿 · 글꼴 프리셋 · 엔진 위치 · 로고 파일
      ├─ nexa.py          실행기 (start · stop · status · build_deck · …)
      ├─ CLAUDE.md        이 폴더에서 일하는 Claude 세션 안내
      ├─ content/         내용 원본 <덱>.json  ← Claude 가 초안을 여기에 쓴다
      ├─ decks/           덱 <덱>.json(편집기가 고치는 대상) · 요청 메모 <덱>.requests.json
      ├─ assets/brand/    로고(처음엔 자리 표시 이미지)
      └─ out/             PPTX · 렌더 · 세션 상태 (git 제외)
```

| 단계 | 누가 | 무엇을 |
|---|---|---|
| 1. 준비 | 사람(한 번) | Python·git 설치, 엔진 clone, 패키지 설치 |
| 2. 작업 공간 만들기 | 사람 또는 Claude | `init_workspace.py` 한 줄 |
| 3. 세션 열기 | 사람 | VS Code 또는 Claude Desktop 에서 `my-talk` 폴더 열기 |
| 4. 연결·초안 | Claude | 서버 시작 · 요청 감시(Monitor) · 내용 원본 작성 → build → 검사 |
| 5. 검토·요청 | 사람 ↔ Claude | 편집기에서 직접 고치거나, 선택·그리기 모드로 메모 → "요청 N개 보내기" → Claude 처리 |
| 6. 내보내기 | 사람 또는 Claude | PPTX 내보내기 · (Windows) PowerPoint 렌더 대조 · git 커밋 |

---

## 1. 준비 (컴퓨터마다 한 번)

### 1.1 필요한 것

| 구성 | 필수 | macOS | Windows |
|---|---|---|---|
| Python 3.10 이상 | ● | `brew install python` (또는 python.org 설치본) | python.org 설치본(“Add to PATH” 체크) 또는 `winget install Python.Python.3.12` |
| git | ● | `xcode-select --install` 또는 `brew install git` | `winget install Git.Git` |
| python-pptx · Pillow | ● | `pip` 로 설치(아래) | 같음 |
| Claude Code | ● | VS Code 확장 “Claude Code” 또는 Claude Desktop | 같음 |
| Chrome 또는 Edge | 권장 | 편집기 화면·`compare.py` | 같음 |
| Node.js 18+ | 선택 | `brew install node` — `check_parity.py`·Mermaid 렌더 | `winget install OpenJS.NodeJS.LTS` |
| PowerPoint | 선택 | (렌더 미리보기는 Windows 전용) | 편집기 “PowerPoint 렌더 미리보기”·`compare.py` |

> **Windows 의 `python3`**: 설치 방식에 따라 `python3` 이 없거나 Microsoft Store 안내로 연결될 수 있다. 그때는 이 문서의 `python3` 을 **`py -3`** 또는 **`python`** 으로 바꿔 쓴다.
> 확인: `py -3 --version` 또는 `python --version` → 3.10 이상.

### 1.2 엔진 받기와 패키지 설치

**macOS**

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone git@github.com:SosomLab/nexa-slide.git        # 또는 https://github.com/SosomLab/nexa-slide.git
python3 -m pip install --user -r nexa-slide/requirements.txt
python3 -c "import pptx, PIL; print('ok')"               # ok 가 나오면 준비 끝
```

**Windows (PowerShell)**

```powershell
New-Item -ItemType Directory -Force D:\Projects | Out-Null; Set-Location D:\Projects
git clone git@github.com:SosomLab/nexa-slide.git        # 또는 https://github.com/SosomLab/nexa-slide.git
python3 -m pip install -r nexa-slide\requirements.txt   # python3 이 없으면 py -3 -m pip …
python3 -c "import pptx, PIL; print('ok')"
```

> 가상 환경을 쓰려면: macOS `python3 -m venv ~/.venvs/nexa && source ~/.venvs/nexa/bin/activate`,
> Windows `py -3 -m venv $HOME\.venvs\nexa; & $HOME\.venvs\nexa\Scripts\Activate.ps1` 후 같은 `pip install`.
> 이 경우 Claude 세션도 같은 python 을 쓰도록 첫 요청에 “`~/.venvs/nexa` 의 python 을 써” 라고 알려 준다.

### 1.3 글꼴 (선택 — 템플릿 기본 프리셋 `default` 는 설치 없이 동작)

| 프리셋 | 글꼴 | macOS | Windows |
|---|---|---|---|
| `default` | 맑은 고딕 · Consolas | 맑은 고딕이 없으면 시스템 한글 글꼴로 대체되어 PPTX 와 줄바꿈이 조금 달라질 수 있다 | 기본 설치 |
| `modern` | Pretendard · JetBrains Mono · D2Coding | `brew install --cask font-pretendard font-jetbrains-mono font-d2coding` | `pwsh -NoProfile -File D:\Projects\nexa-slide\studio\install_fonts.ps1` |

글꼴 프리셋은 작업 공간에서 고른다: 편집기 ⋯ → 글꼴 세트, 또는 `python3 slides/nexa.py set_fonts modern`.

---

## 2. 작업 공간 만들기

슬라이드를 만들 폴더(저장소)에서 한 줄로 뼈대를 만든다. 포트는 비어 있는 것을 자동으로 고르고(5600~), 이미 있는 파일은 건드리지 않는다.

**macOS**

```bash
cd ~/Projects/my-talk                     # 없으면: mkdir -p ~/Projects/my-talk && cd $_ && git init
python3 ~/Projects/nexa-slide/studio/init_workspace.py slides --title "신제품 소개" --deck intro
python3 slides/nexa.py build_deck intro
python3 slides/nexa.py start              # → http://127.0.0.1:<포트>/
open "$(python3 slides/nexa.py url)"      # 브라우저로 열기
```

**Windows (PowerShell)**

```powershell
Set-Location D:\Projects\my-talk          # 없으면: New-Item -ItemType Directory D:\Projects\my-talk; Set-Location D:\Projects\my-talk; git init
python3 D:\Projects\nexa-slide\studio\init_workspace.py slides --title "신제품 소개" --deck intro
python3 slides\nexa.py build_deck intro
python3 slides\nexa.py start
Start-Process (python3 slides\nexa.py url)
```

옵션: `--port 5610`(포트 지정) · `--template lecture-large`(템플릿) · `--asset-root ..`(덱 그림 경로를 저장소 루트 기준으로 — 저장소에 이미 로고·그림이 있을 때) · `--force`(설정·실행기 다시 쓰기).

### 2.1 만든 뒤 고칠 것 — `slides/nexa-slide.json` (선택만)

```json
{
  "port": 5601,
  "title": "신제품 소개",
  "engine": "../../nexa-slide",
  "template": "lecture",
  "fontPreset": "default",
  "assetRoot": ".",
  "brand": {"name": "우리 회사", "logo": "assets/brand/logo.png", "wordmark": "assets/brand/wordmark.png", "favicon": "assets/brand/favicon.png"},
  "partLabels": {"day1": "1부", "day2": "2부", "day3": "3부", "apx": "부록"},
  "coverBadge": "신제품 소개"
}
```

- **로고**: `assets/brand/` 의 자리 표시 이미지를 자기 로고 PNG 로 바꾼다(가로세로 비율은 자동으로 읽는다).
- **디자인 값(색·글꼴·크기·검사 기준)은 여기에 쓰지 않는다** — 템플릿 이름과 글꼴 프리셋만 고른다([templates.md](templates.md)).
- 엔진 위치 `engine` 은 이 폴더 기준 상대 경로(다른 드라이브면 절대 경로). 다른 사람과 저장소를 공유하면 각자 `NEXA_SLIDE_HOME` 환경변수로 덮어쓸 수 있다.
- 바꾼 뒤: `python3 slides/nexa.py restart`.

### 2.2 git 에 넣기

`slides/.gitignore` 가 `out/`·`decks/.history/` 를 뺀다. 나머지(설정·실행기·CLAUDE.md·content·decks·assets)는 커밋한다.

```bash
git add slides && git commit -m "슬라이드 작업 공간 추가 (nexa-slide)"
```

### 2.3 Claude 가 이 폴더를 알게 하기

`slides/CLAUDE.md` 에 세션 안내(요청 감시·처리 규약·명령)가 들어 있다. Claude Code 는 **연 폴더(저장소 루트)의 `CLAUDE.md`** 를 먼저 읽으므로,
저장소 루트 `CLAUDE.md` 에 한 줄을 넣어 두면 세션마다 확실히 찾는다:

```markdown
- 슬라이드 작업은 `slides/` (nexa-slide 작업 공간) — 먼저 `slides/CLAUDE.md` 를 읽는다.
```

---

## 3. 세션 열기

### 3.1 VS Code + Claude Code 확장

1. VS Code 에서 **파일 → 폴더 열기** 로 `my-talk`(저장소 루트)를 연다.
   - macOS 터미널: `code ~/Projects/my-talk` · Windows: `code D:\Projects\my-talk`
2. 확장 “Claude Code” 를 설치하고 로그인한다(처음 한 번).
3. 사이드바의 Claude Code 아이콘(또는 명령 팔레트 `Claude Code: Open`)으로 대화창을 연다. 작업 폴더가 `my-talk` 인지 확인한다.
4. 아래 4장의 **첫 요청**을 붙여 넣는다.

> 편집기는 VS Code 안에서 보려면 명령 팔레트 → `Simple Browser: Show` → `http://127.0.0.1:<포트>/`, 아니면 평소 브라우저.

### 3.2 Claude Desktop

1. Claude Desktop 을 열고 **Code(로컬 폴더) 세션**을 새로 만든다 → 폴더로 `my-talk` 를 고른다.
2. 아래 4장의 **첫 요청**을 붙여 넣는다.
3. 편집기는 Desktop 의 **내장 브라우저 패널**에서 `http://127.0.0.1:<포트>/` 를 열거나 평소 브라우저로 연다.
   내장 브라우저에서 열면 Claude 가 화면을 직접 보고 확인할 수도 있다(“편집기 화면을 열어서 3번 슬라이드 확인해 줘”).

> Desktop 세션도 VS Code 와 같은 Claude Code 도구(Bash·Monitor 등)를 쓴다. 감시(Monitor)는 세션이 열려 있는 동안만 동작하므로, 세션을 닫으면 편집기 칩이 “세션 연결 없음”이 된다.

### 3.3 여러 저장소를 동시에

저장소마다 작업 공간·포트·Claude 세션이 하나씩이다. `init_workspace.py` 가 겹치지 않는 포트를 고르므로 그대로 함께 띄울 수 있다.
같은 작업 공간을 두 세션이 감시하려 하면 뒤의 감시는 `{"event":"refused"}` 를 내고 멈춘다(요청이 두 번 처리되지 않게).

---

## 4. Claude 에게 맡기기 — 연결과 초안

### 4.1 첫 요청 (복사해 쓰기)

```text
slides/ 는 nexa-slide 작업 공간이야. slides/CLAUDE.md 를 읽고 다음을 해 줘.
1) python3 slides/nexa.py start 로 편집기를 띄우고 주소를 알려 줘.
2) Monitor 로 요청 감시를 걸어 줘:
   python3 slides/nexa.py watch_requests --stream --takeover --label "<저장소 이름>"   (timeout 1800000, ttl 이벤트가 오면 다시 걸기)
3) 아래 내용으로 slides/content/intro.json 초안을 써 줘. 레이아웃은 python3 slides/nexa.py layout_samples 로 확인하고,
   build_deck intro --force → check_layout intro 로 ERROR 를 줄인 뒤 편집기에서 볼 수 있게 해 줘.
   - 주제: <발표 주제>
   - 대상·시간: <누구에게, 몇 분>
   - 장 수: <예: 10~12장>
   - 구성: <표지 → 개요 → 본문 3절 → 비교 표 → 정리 → 끝>
   - 자료: <참고할 파일 경로·문서·URL> (근거가 없는 수치·인용은 지어내지 말 것)
```

Windows 에서 `python3` 이 없다면 첫 줄에 “Windows 이고 python3 대신 `py -3` 을 써” 라고 덧붙인다.

### 4.2 Claude 가 하는 일

1. `slides/CLAUDE.md` 와 엔진 문서(`docs/deck-format.md`·`docs/claude-session.md`)를 읽는다.
2. 서버를 띄우고(`nexa.py start`) Monitor 로 감시를 건다 → 편집기 머리줄 칩이 **“세션 연결됨”**.
3. `layout_samples` 로 레이아웃 21종의 필드를 보고 `content/intro.json` 을 쓴다. 슬라이드 한 장 = `{"layout": …, 필드…, "notes": 발표자 노트, "source": [근거]}`.
4. `build_deck intro --force` → `decks/intro.json` 생성 → `check_layout intro` 로 겹침·넘침·최소 글자 크기를 검사하고 고친다.
5. 편집기 주소와 남은 검사 결과를 보고한다.

### 4.3 내용 원본 형식 요약 (자세히는 [deck-format.md](deck-format.md))

```json
{
  "id": "intro", "title": "신제품 소개", "part": "day1", "version": "0.1",
  "slides": [
    {"layout": "cover", "title": "신제품 소개", "subtitle": "부제", "days": [["day1", "1부"]], "meta": "작성자\n날짜\nv0.1"},
    {"layout": "bullets", "title": "왜 바꾸나", "items": ["요점 1", {"text": "요점 2", "sub": ["보조"]}], "notes": "발표자 노트"},
    {"layout": "table", "title": "비교", "header": ["항목", "기존", "신규"], "rows": [["속도", "1x", "**3x**"]]},
    {"layout": "summary", "title": "정리", "items": ["기억할 것"]},
    {"layout": "end", "title": "End of Document", "sub": "신제품 소개"}
  ]
}
```

인라인 강조: `**굵게**` · `==강조==`(주색 굵게) · `[[토큰|색 글자]]` · `{page}`. 코드는 `code_plan`·`code_excerpt`, 도식은 `flow`·`sequence`·`cards`·`diagram`(Mermaid).

---

## 5. 검토하고 다듬기 (편집기)

편집기 사용법 전체는 [editor.md](editor.md). 초안 검토에 쓰는 흐름:

| 하고 싶은 것 | 방법 |
|---|---|
| 슬라이드 넘기며 보기 | 왼쪽 썸네일 · PageUp/PageDown · 아래 ◀ ▶ · 개요 탭 |
| 바로 고치기 | **✎ 편집(E)** — 끌기·크기·두 번 클릭 글자 편집, 위 서식 줄(크기·색·정렬·✥ 위치 조정) |
| Claude 에게 부탁 | **◎ 선택(M)** 요소 클릭 → 메모(Enter) / **✐ 그리기(D)** 박스·펜·핀 → 메모 → 아래 바 **“요청 N개 보내기”** |
| 검사 결과 고치기 | 아래 **검사** 탭에서 항목을 눌러 위치 확인 → 직접 고치거나 **✨ 레이아웃 고치기** |
| 문장·배치 정리 | **✨ 다듬기** (기존 스타일 유지) |
| 이전 상태로 | **기록** — 자동 백업 시점으로 되돌리기, Ctrl+Z |
| 발표 연습 | **▶ 발표**(F5) — N = 노트·시간 |

요청을 보내면 Claude 가 **처리 중 → 완료** 로 상태를 바꾸고 답변을 남기며, 편집기는 2초 안에 바뀐 덱을 다시 불러온다.

> **편집기에서 직접 고친 내용과 content**: build 는 `content/` 로 덱을 다시 만들기 때문에, 편집기에서 사람이 고친 슬라이드가 있으면 `build_deck --force` 가 멈추고 알려 준다.
> Claude 에게 “편집기에서 고친 내용을 content 에 옮겨 줘” 라고 하면 맞춘 뒤 다시 빌드한다.

---

## 6. 내보내기와 마무리

| 할 일 | macOS | Windows |
|---|---|---|
| PPTX 만들기 | 편집기 **내보내기 ▾ → PPTX** 또는 `python3 slides/nexa.py export_pptx intro` | 같음(`slides\nexa.py`) |
| 결과 열기 | `open slides/out/intro.pptx` | `Start-Process slides\out\intro.pptx` |
| PowerPoint 렌더 대조 | (지원 안 함) | 편집기 **내보내기 ▾ → PowerPoint 렌더 미리보기** · `python3 slides\nexa.py compare intro` |
| 검사 | `python3 slides/nexa.py check_layout intro` | 같음 |
| 커밋 | `git add slides && git commit -m "intro 초안"` | 같음 |
| 서버 끄기 | `python3 slides/nexa.py stop` | 같음 |

PPTX 는 이미지가 아니라 PowerPoint 기본 도형이라 받은 뒤에도 PowerPoint 에서 고칠 수 있다(단, PowerPoint 에서 고친 내용은 덱 JSON 으로 돌아오지 않는다).

---

## 7. 명령 요약

| 목적 | macOS | Windows (PowerShell) |
|---|---|---|
| 작업 공간 만들기 | `python3 ~/Projects/nexa-slide/studio/init_workspace.py slides --title "제목"` | `python3 D:\Projects\nexa-slide\studio\init_workspace.py slides --title "제목"` |
| 서버 시작 / 상태 / 주소 / 끄기 | `python3 slides/nexa.py start` · `status` · `url` · `stop` | `python3 slides\nexa.py start` · `status` · `url` · `stop` |
| 빌드 · 검사 | `python3 slides/nexa.py build_deck intro --force` · `check_layout intro` | `python3 slides\nexa.py build_deck intro --force` · `check_layout intro` |
| 레이아웃 예시 | `python3 slides/nexa.py layout_samples` | `python3 slides\nexa.py layout_samples` |
| 요청 감시(세션이 Monitor 로) | `python3 slides/nexa.py watch_requests --stream --takeover` | `python3 slides\nexa.py watch_requests --stream --takeover` |
| 글꼴 프리셋 | `python3 slides/nexa.py set_fonts modern` | `python3 slides\nexa.py set_fonts modern` |
| 엔진 업데이트 | `git -C ~/Projects/nexa-slide pull` 후 `nexa.py restart` | `git -C D:\Projects\nexa-slide pull` 후 `nexa.py restart` |

---

## 8. 문제 해결

| 증상 | 확인·조치 (macOS / Windows) |
|---|---|
| `python3` 을 찾을 수 없음 | macOS: `brew install python` / Windows: `py -3` 또는 `python` 으로 바꿔 실행, 설치 시 “Add to PATH” |
| `No module named pptx` | 같은 python 으로 `python3 -m pip install -r <엔진>/requirements.txt` (venv 를 쓰면 활성화 후) |
| 한글이 깨져 출력됨 (Windows) | 실행기 `nexa.py` 는 `PYTHONIOENCODING=utf-8` 을 넣는다. 직접 실행할 때는 `$env:PYTHONIOENCODING="utf-8"` |
| “포트를 쓸 수 없다” | 다른 작업 공간이 그 포트를 씀 → `nexa-slide.json` 의 `port` 를 바꾸거나 `nexa.py start --port auto`. 누가 쓰는지: macOS `lsof -iTCP:<포트> -sTCP:LISTEN` / Windows `Get-NetTCPConnection -LocalPort <포트> -State Listen` |
| “이미 실행 중” | 그 작업 공간 서버가 떠 있음 → `nexa.py url` 로 주소 확인 |
| 편집기 칩이 “세션 연결 없음” | 세션에서 감시가 꺼짐(세션 종료·Monitor 만료) → Claude 에게 “요청 감시 다시 걸어 줘”. 남긴 요청은 저장돼 있다가 전달된다 |
| `{"event":"refused"}` | 같은 작업 공간을 다른 세션이 감시 중 → 그 세션을 쓰거나, 넘겨받으려면 `--takeover` |
| 엔진을 찾지 못함 | `nexa-slide.json` 의 `engine` 경로 확인, 또는 macOS `export NEXA_SLIDE_HOME=~/Projects/nexa-slide` / Windows `$env:NEXA_SLIDE_HOME="D:\Projects\nexa-slide"` |
| 로고가 안 보임 | `brand.logo` 가 `assetRoot` 기준 경로인지, 파일이 PNG 인지 |
| 검사에 칩·각주 글자 크기 ERROR 가 많음 | 템플릿 `lecture` 기준(본문 11pt)보다 작은 디자인 요소다. 그대로 두고 장 단위로 검토하거나, 일괄 확대 템플릿 `lecture-large` 를 고른 뒤 다시 빌드 |
| 백그라운드 서버 프로세스 정리 | `nexa.py stop`. 안 되면 macOS `pkill -f "studio/server.py"` / Windows `Get-CimInstance Win32_Process -Filter "Name like 'python%'" \| ? CommandLine -like '*server.py*' \| % { Stop-Process -Id $_.ProcessId -Force }` |

관련 문서: [install.md](install.md) · [configuration.md](configuration.md) · [templates.md](templates.md) · [server.md](server.md) · [operation.md](operation.md) · [claude-session.md](claude-session.md) · [deck-format.md](deck-format.md) · [editor.md](editor.md)
