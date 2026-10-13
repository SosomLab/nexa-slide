# -*- coding: utf-8 -*-
"""새 작업 공간 만들기 — 다른 폴더·저장소에 nexa-slide 를 연결하는 뼈대를 만든다.

    python3 <엔진>/studio/init_workspace.py <작업 공간 폴더> [--title "제목"] [--port 5610|auto] [--template lecture]
                                            [--deck intro] [--asset-root .] [--starter lecture-course] [--force]
                                            [--build] [--purpose …] [--audience …] [--direction …]… [--material …]… [--ask-draft]

    # 시작 페이지의 "만들고 Studio 열기"와 같은 결과(시작 페이지가 이 명령을 그대로 보여 주고 실행한다)
    python3 <엔진>/studio/init_workspace.py <폴더> --title "제목" --template report --port 5601 --build --purpose "…" --ask-draft
    python3 <폴더>/slides/nexa.py start

저장소형(기본): 준 폴더 = 저장소 관리 기준 폴더(루트), 작업 공간 = <폴더>/slides (--slides-dir 로 이름 변경).
    루트는 사용자가 기초 자료를 모아 정리하고 관련 소스를 개발하는 곳 — 폴더는 만들지 않고 md 파일만(이미 있으면 그대로) 둔다.
    SLIDES.md          개념 · 구조 · 슬라이드 서버 실행 방법
    CLAUDE.md          없을 때만 — @SLIDES.md 개념 + @slides/CLAUDE.md 규칙      AGENTS.md   없을 때만
    폴더 이름이 slides 면 그 폴더가 작업 공간(상위 = 루트). 이미 작업 공간(nexa-slide.json)이 있는 폴더나 --flat 이면 폴더 자체가 작업 공간.

작업 공간에 만드는 것(이미 있는 파일은 건드리지 않음 — --force 면 nexa-slide.json·nexa.py 만 다시 씀)
    nexa-slide.json    선택만 담은 설정: port · title · engine(이 폴더에서 엔진까지 상대 경로) · template · fontPreset · brand 파일 경로
    nexa.py            실행기 — python3 <폴더>/nexa.py start|stop|status|url|build_deck …
    content/<deck>.json  시작용 내용 원본(표지 · 글머리 · 표 · 정리 · 끝)
                       --starter 를 주면 대신 엔진 starters/<이름>/ 의 내용·그림을 복사한다
                       (lecture-course = 강의 교안 3일 과정 뼈대 — docs/lecture-starter.md)
    decks/  out/  assets/brand/   (로고는 엔진 예제의 자리 표시 이미지 — 자기 로고로 바꿔 쓴다)
    .gitignore         out/ · decks/.history/
    CLAUDE.md          이 작업 공간에서 일하는 Claude 세션 안내(요청 감시·처리 규약·명령)
    AGENTS.md          Claude 가 아닌 AI 도구(Codex·Gemini CLI·Cursor) 안내 — 같은 규칙, 요청은 1회 대기 반복
    .claude/settings.json  Claude Code 훅 — 세션 활동(대화 작업 중·요청 처리 중·대기)을 편집기에 표시(session_hook.py)
포트를 주지 않으면(또는 auto) 5600 부터 비어 있고 최근 작업 공간(사용자 설정 recent)이 쓰지 않는 포트를 고른다.
포트를 주면 지금 다른 프로그램이 쓰는 포트는 거절하고, 다른 작업 공간 설정과 겹치면 알린다(동시에 띄우지 않으면 괜찮다).
이미 작업 공간이 있는 폴더에 --port 를 주면 그 포트로 설정을 바꾼다.

--build       content/*.json(밑줄로 시작하는 공통 파일 제외)을 덱으로 빌드한다(이미 있는 덱은 그대로)
--purpose · --audience · --direction(여러 번) · --material(여러 번)
              작성 브리프 BRIEF.md 를 쓰고 CLAUDE.md 에 "초안 전에 BRIEF.md 를 읽는다"를 덧붙인다.
              --direction · --material 은 한 줄씩 — 여러 줄이면 옵션을 줄 수만큼 반복한다
--ask-draft   첫 덱 첫 슬라이드에 "브리프로 초안 써 주세요" 대기 요청을 남긴다(세션이 연결되면 전달) — --build 포함
만든 작업 공간은 사용자 설정의 최근 작업에 올린다(시작 페이지 "최근 작업").
"""
import argparse
import datetime as dt
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
EXAMPLE = ENGINE / "example"
STARTERS = ENGINE / "starters"
sys.path.insert(0, str(ENGINE / "studio"))
from paths import hub_port, load_settings, remember  # noqa: E402


def port_busy(p):
    """지금 이 PC 에서 다른 프로그램이 쓰는 포트인가."""
    with socket.socket() as s:
        if os.name != "nt":  # 서버와 같은 규칙 - 방금 끈 서버의 TIME_WAIT 는 "쓰는 중"이 아니다(server.py Server)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", p))
            return False
        except OSError:
            return True


def taken_ports(skip=None):
    """최근 작업 공간들이 설정에 정해 둔 포트 {포트: 작업 공간 경로} — 지금 꺼져 있어도 나중에 함께 띄울 수 있다."""
    out = {}
    for r in load_settings().get("recent", []):
        p = Path(r.get("path", ""))
        if skip and p.resolve() == Path(skip).resolve():
            continue
        try:
            port = json.loads((p / "nexa-slide.json").read_text(encoding="utf-8")).get("port")
        except (OSError, ValueError):
            continue
        if isinstance(port, int):
            out.setdefault(port, str(p))
    return out


def free_port(start=5600, span=100, skip=None):
    taken = taken_ports(skip)
    hub = hub_port()
    for p in range(start, start + span):
        if p != hub and p not in taken and not port_busy(p):
            return p
    return start


def brief_md(title, template, starter, deck, fields):
    lines = [f"# {title} - 작성 브리프", "",
             f"- 만든 날짜: {dt.date.today().isoformat()}",
             f"- 템플릿: {template}" + (f" · 시작용 내용: {starter}" if starter else ""),
             f"- 첫 덱: `{deck}`", ""]
    for head, v in (("목적", fields["purpose"]), ("대상(청중)", fields["audience"]), ("작성 방향", fields["direction"]), ("참고 자료", fields["materials"])):
        lines += [f"## {head}", "", v.strip() or "(비어 있음)", ""]
    lines += ["---", "", "> 이 파일은 작업 공간을 만들 때 받은 내용이다. Claude 세션은 초안을 쓰기 전에 먼저 읽는다.", ""]
    return "\n".join(lines)


def build_decks(ws, cfg):
    """content/*.json(밑줄로 시작하는 공통 파일 제외) → decks/. 이미 있는 덱은 편집 내용을 지키려고 그대로 둔다."""
    env = {**os.environ, "NEXA_SLIDE_WORKSPACE": str(ws), "PYTHONIOENCODING": "utf-8"}
    content, decks = ws / cfg.get("content", "content"), ws / cfg.get("decks", "decks")
    built = []
    for f in sorted(content.glob("*.json")) if content.is_dir() else []:
        if f.name.startswith("_"):
            continue
        if (decks / f.name).exists():
            built.append(f.stem)
            continue
        r = subprocess.run([sys.executable, str(ENGINE / "studio" / "build_deck.py"), f.stem], cwd=str(ws), env=env, capture_output=True)
        if r.returncode == 0:
            built.append(f.stem)
        else:
            print(f"  빌드 실패 {f.stem}: {(r.stderr or r.stdout).decode('utf-8', 'replace').strip().splitlines()[-1:]}", file=sys.stderr)
    return built


def ask_draft(ws, cfg, deck):
    """세션에 보낼 첫 요청 - 브리프로 초안 쓰기(대기 상태라 세션이 연결되면 전달된다)."""
    d = ws / cfg.get("decks", "decks")
    p = d / f"{deck}.requests.json"
    try:
        items = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        items = []
    try:
        first = (json.loads((d / f"{deck}.json").read_text(encoding="utf-8")).get("slides") or [{}])[0].get("id")
    except (OSError, ValueError):
        first = None
    items.append({"id": "r" + dt.datetime.now().strftime("%Y%m%d%H%M%S%f")[:17], "slide": first, "element": None,
                  "text": "BRIEF.md 의 목적·대상·작성 방향·참고 자료로 이 덱의 초안을 써 주세요. 템플릿 디자인은 그대로 두고, 자료에 없는 내용은 지어내지 말고 확인 질문으로 남겨 주세요.",
                  "status": "open", "reply": "", "created": dt.datetime.now().isoformat(timespec="seconds")})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


def rel(target, base):
    try:
        return os.path.relpath(target, base).replace("\\", "/")
    except ValueError:  # 드라이브가 다르면 절대 경로(역슬래시는 / 로 — 실행기 docstring 의 \U 이스케이프 오류 방지)
        return str(target).replace("\\", "/")


LAUNCHER = '''# -*- coding: utf-8 -*-
"""nexa-slide 실행기 — 이 폴더를 작업 공간으로 엔진 도구를 실행한다(init_workspace.py 가 만듦).

    python3 {ws}/nexa.py start | stop | restart | status | url     # 서비스(백그라운드 서버) 관리
    python3 {ws}/nexa.py build_deck <덱> [--force]                  # content → 덱
    python3 {ws}/nexa.py export_pptx <덱>                           # → out/<덱>.pptx
    python3 {ws}/nexa.py check_layout [<덱>]                        # 레이아웃 검사
    python3 {ws}/nexa.py layout_samples                             # 레이아웃·필드 예시
    python3 {ws}/nexa.py slide_types [낱말]                         # 슬라이드 유형(목적별) — 내용에 맞는 장 고르기
    python3 {ws}/nexa.py watch_requests --stream --takeover         # Claude 세션 요청 감시(Monitor 로 실행)

엔진 위치: 환경변수 NEXA_SLIDE_HOME > nexa-slide.json 의 "engine"(이 폴더 기준 상대 경로).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    home = os.environ.get("NEXA_SLIDE_HOME") or WS / json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8")).get("engine", "../nexa-slide")
    studio = Path(home).resolve() / "studio"
    if not (studio / "server.py").is_file():
        sys.exit(f"nexa-slide 엔진을 찾지 못했다: {{studio}} — nexa-slide.json 의 engine 또는 NEXA_SLIDE_HOME 을 맞춘다")
    tool, args = sys.argv[1].removesuffix(".py"), sys.argv[2:]
    if tool in ("start", "stop", "restart", "url"):
        tool, args = "service", [tool, *args]
    script = studio / f"{{tool}}.py"
    if not script.is_file():
        sys.exit(f"없는 도구: {{tool}}")
    env = {{**os.environ, "NEXA_SLIDE_WORKSPACE": str(WS), "PYTHONIOENCODING": "utf-8"}}
    sys.exit(subprocess.call([sys.executable, str(script), *args], env=env))


if __name__ == "__main__":
    main()
'''

CLAUDE_MD = '''# 슬라이드 작업 공간 (nexa-slide) — Claude 세션 안내

이 폴더는 nexa-slide 엔진({engine})으로 슬라이드를 만드는 **작업 공간**이다. 디자인(색·글꼴·크기)은 엔진 템플릿 `{template}` 을 고르기만 하고 여기에 두지 않는다.

- 편집기: `python3 {ws}/nexa.py start` → http://127.0.0.1:{port}/  (`status` · `url` · `stop`)
- 내용 원본은 `content/<덱>.json`(레이아웃 이름 + 필드), 빌드 결과(편집 대상)는 `decks/<덱>.json`.
  레이아웃·필드 예시: `python3 {ws}/nexa.py layout_samples` · 형식: 엔진 `docs/deck-format.md`
- **장 고르기 기준 = 슬라이드 유형**: 초안을 쓰거나 요청을 처리할 때, 각 장의 내용 성격(결론 숫자·추이·비교·결정 요청·사례·풀이 …)에 맞는 유형을
  `python3 {ws}/nexa.py slide_types [낱말]` 로 골라 그 레이아웃·필드 구조로 쓴다(유형의 목적·고를 신호 when — 엔진 `docs/slide-types.md`).
- 초안을 쓰거나 고치면: `build_deck <덱> --force` → `check_layout <덱>`(ERROR 0 목표) → 편집기에서 확인.
  편집기에서 사람이 고친 슬라이드가 있으면 build 가 멈춘다 — 고친 내용을 content 에 옮긴 뒤 다시.
- **요청 감시**: 세션을 시작하면 Monitor 도구로
  `python3 {ws}/nexa.py watch_requests --stream --takeover --label "<세션 이름>"` (timeout 1800000) 를 건다.
  `{{"event":"ttl"}}` 이 오면 같은 명령으로 다시 건다. `{{"event":"refused"}}` 는 다른 세션이 맡고 있다는 뜻.
- **요청 처리 규약**(엔진 `docs/claude-session.md`): `decks/<덱>.requests.json` 에서 status `working` → 덱 수정(요소 id 유지, 원자적 쓰기)
  → 같은 변경을 `content/` 에도 → status `done` + `reply` 한두 문장. 영역 요청(`region`)은 그 좌표와 겹치는 요소가 대상.
- 기존 디자인·레이아웃 규칙을 유지한다 — 검사 경고를 없애려고 요소를 지우지 않는다. 근거·각주는 지어내지 않는다.
- **글꼴 파일은 이 작업 공간 `fonts/` 에만 둔다**(엔진에 넣지 않는다). 전용 글꼴 세트는 `nexa-slide.json` 의 `fontPresets` 에 정의하고
  `fontPreset` 으로 고른다. PowerPoint 에 쓰려면 `python3 {ws}/nexa.py install_fonts` (엔진 `docs/fonts.md`).
- 사용자 답변은 한국어.
'''

AGENTS_MD = '''# 슬라이드 작업 공간 (nexa-slide) — AI 에이전트 안내 (Codex · Gemini CLI · Cursor 등)

이 파일은 Claude 가 아닌 AI 코딩 도구용이다. 규칙·명령은 같은 폴더의 `CLAUDE.md` 와 같고(먼저 읽는다), 요청 감시 방법만 다르다.
Gemini CLI 는 기본으로 `GEMINI.md` 를 읽는다 — 이 파일을 `GEMINI.md` 로 복사하거나 설정 `contextFileName` 에 `AGENTS.md` 를 넣는다.

- 편집기에서 오는 요청(1회 대기 반복): `python3 nexa.py watch_requests --label "<도구 이름>"` 실행 → 요청이 생기면 JSON 목록을 출력하고 끝난다
  → 요청마다 `decks/<덱>.requests.json` 의 status 를 "working" → `decks/<덱>.json` 수정(요소 id 유지, 임시 파일에 쓴 뒤 교체) → 같은 변경을 `content/` 에도
  → status "done" + reply 한두 문장 → 다시 실행해 다음 요청을 기다린다. 셸을 못 쓰면 사용자가 "열린 요청 처리해 줘"라고 할 때 위 파일을 직접 읽어 처리한다.
- 장 고르기 기준 = 슬라이드 유형: `python3 nexa.py slide_types [낱말]` — 내용 성격에 맞는 유형의 레이아웃·필드 구조로 쓴다.
- 빌드·검사: `python3 nexa.py build_deck <덱> --force` → `python3 nexa.py check_layout <덱>`(ERROR 0 목표).
- 글꼴 파일은 `fonts/` 에만(엔진에 넣지 않음). 근거·각주는 지어내지 않는다. 사용자 답변은 한국어.
- 엔진 문서: {engine}/docs/ai-editing.md (AI 로 고치기) · {engine}/docs/slide-types.md · {engine}/docs/claude-session.md(요청 규약)
'''

# ---------- 저장소형: 지정한 폴더 = 저장소 관리 기준 폴더(루트), 작업 공간 = <루트>/slides ----------
# 루트에는 폴더를 만들지 않는다 — 자료 수집·정리·소스 개발은 사용자가 원하는 구조로 한다. 루트에는 md 파일만(없을 때만) 둔다.
REPO_GUIDE = "SLIDES.md"

REPO_GUIDE_MD = '''# {title} — 슬라이드 (nexa-slide)

## 개념

이 폴더(저장소 루트)는 **저장소 관리 기준 폴더**다.

- 슬라이드에 쓸 기초 자료를 모으고 정리한다 — 문서 · 데이터 · 조사 메모 · 구성안 등.
- 필요하면 관련 소스도 여기서 개발한다 — 분석 스크립트 · 데모 코드 · 도식 생성 등.
- 폴더 구조는 정해 두지 않는다. 작업에 맞게 자유롭게 만든다.

슬라이드는 이 저장소의 자료와 소스를 근거로 **`{slides}/`** 에서 만든다. nexa-slide 가 관리하는 폴더는 `{slides}/` 하나뿐이다.

## 구조

```
<저장소 루트>/            저장소 관리 기준 — 자료 수집·정리, 관련 소스 개발 (구조 자유)
├─ SLIDES.md             이 안내
└─ {slides_col}  nexa-slide 작업 공간 = 최종 산출물
   ├─ nexa-slide.json    설정(포트 · 제목 · 템플릿 · 엔진 위치)
   ├─ nexa.py            실행기
   ├─ CLAUDE.md          슬라이드 작업 규칙(AI 세션)
   ├─ content/           내용 원본 <덱>.json — 저장소 자료를 정리해 여기에 쓴다
   ├─ decks/             편집 대상 <덱>.json(편집기가 고친다)
   ├─ assets/            슬라이드 그림 · 로고
   └─ out/               PPTX · 렌더 (git 제외)
```

## 흐름

1. 저장소에 자료를 모으고 정리한다(필요하면 소스 개발).
2. 정리한 내용으로 `{slides}/content/<덱>.json` 을 쓰고 빌드한다.
3. 편집기에서 다듬고 PPTX 로 내보낸다.

## 슬라이드 서버 실행 (저장소 루트에서)

```
python3 {slides}/nexa.py start      # 편집기 서버 시작 → http://127.0.0.1:{port}/
python3 {slides}/nexa.py status     # 실행 상태     (url: 접속 주소 · stop: 종료 · restart: 다시 시작)
python3 {slides}/nexa.py stop
```

- Windows 에 `python3` 이 없으면 `python` 또는 `py -3` 으로 바꿔 쓴다.
- 서버는 백그라운드로 뜬다(터미널을 닫아도 유지). 포트는 `{slides}/nexa-slide.json` 의 `port`.
- 그 밖: `build_deck <덱> --force`(content → 덱) · `check_layout <덱>`(검사) · `export_pptx <덱>`(→ `{slides}/out/<덱>.pptx`).
- nexa-slide 엔진 위치는 `{slides}/nexa-slide.json` 의 `engine`(다른 PC 에서는 환경변수 `NEXA_SLIDE_HOME` 으로 덮어쓸 수 있다).
'''

REPO_CLAUDE_MD = '''# {title}

이 저장소는 저장소 관리 기준 폴더다 — 기초 자료 수집·정리와 관련 소스 개발은 루트에서 자유로운 구조로 하고,
슬라이드는 그 자료·소스를 근거로 `{slides}/`(nexa-slide 작업 공간)에서 만든다. 개념·구조·서버 실행: `{guide}`.

- 슬라이드 내용의 근거는 저장소의 자료·소스에서만 찾는다. 없는 내용은 지어내지 않고 확인 질문으로 남긴다.
- nexa-slide 명령은 저장소 루트에서 `python3 {slides}/nexa.py …`.
- 슬라이드 작업 규칙(요청 감시·처리 규약·빌드·검사):

@{slides}/CLAUDE.md
'''

REPO_AGENTS_MD = '''# AI 에이전트 안내

이 저장소는 저장소 관리 기준 폴더다 — 기초 자료 수집·정리와 관련 소스 개발은 루트에서, 슬라이드는 그 자료를 근거로 `{slides}/`(nexa-slide 작업 공간)에서 만든다.
개념·구조·서버 실행은 `{guide}`, 슬라이드 작업 규칙은 `{slides}/AGENTS.md` 를 먼저 읽는다.

- 명령은 저장소 루트에서 `python3 {slides}/nexa.py …` (예: `start` · `build_deck <덱> --force` · `check_layout <덱>` · `watch_requests --label "<도구 이름>"`).
- 근거는 저장소 자료·소스에서만 — 없는 내용은 지어내지 않는다. 사용자 답변은 한국어.
'''

WS_REPO_SECTION = '''
## 저장소 자료 (이 작업 공간은 저장소 `{root}` 안에 있다)

- 저장소 루트(`{root}`)는 저장소 관리 기준 폴더다 — 기초 자료·정리·관련 소스가 사용자가 정한 구조로 있다. 개념·구조: `{root}/{guide}`.
- 슬라이드 내용은 그 자료·소스를 근거로 쓴다. 저장소에 없는 내용은 지어내지 않고 확인 질문으로 남긴다.
- 슬라이드 작업 파일(content · decks · assets)만 이 폴더에 둔다 — 자료·소스는 저장소 쪽에 둔다.
'''


def session_hooks(launcher):
    """Claude Code 훅 설정 — 세션 활동(대화 작업 중·요청 처리 중·대기)을 편집기에 보여 주려고(studio/session_hook.py, docs/ai-editing.md).
    파이썬 이름은 훅이 돌 때 고른다 — 만든 PC(python 만 있는 Windows)와 여는 PC(python3 만 있는 macOS)가 다를 수 있다."""
    run = f'P=python3; command -v python3 >/dev/null 2>&1 || P=python; cd "$CLAUDE_PROJECT_DIR" && "$P" {launcher} session_hook'
    hook = lambda: [{"type": "command", "command": run, "timeout": 10}]  # noqa: E731
    return {"UserPromptSubmit": [{"hooks": hook()}], "PreToolUse": [{"matcher": "*", "hooks": hook()}],
            "PostToolUse": [{"matcher": "Monitor", "hooks": hook()}], "Stop": [{"hooks": hook()}]}


FONTS_README = """# 글꼴 (이 작업 공간 전용)

이 작업 공간에서 쓰는 글꼴 파일(.ttf · .otf)을 여기에 둔다. **글꼴 파일은 nexa-slide 엔진 폴더에 두지 않는다.**

1. 파일을 이 폴더에 넣는다(굵기별 파일 - 예: `MyFont-Regular.ttf`, `MyFont-Bold.ttf`).
2. `nexa-slide.json` 에 글꼴 세트를 정의하고 고른다 - 형식은 엔진 `docs/fonts.md`.
3. PowerPoint 에서도 쓰려면 설치: `python3 nexa.py install_fonts` (편집기는 설치하지 않아도 이 폴더를 바로 쓴다).

라이선스: 배포가 허용되지 않은 글꼴(회사 전용 서체 등)을 공개 저장소에 커밋하지 않는다 - 필요하면 이 폴더를 `.gitignore` 에 넣는다.
"""


def resolve_target(folder, flat=False, slides_dir="slides"):
    """준 폴더 → (작업 공간, 저장소 루트 또는 None).
    기본은 저장소형: 폴더 = 저장소 루트, 작업 공간 = <폴더>/<slides_dir>. 다음은 폴더 자체가 작업 공간(루트 없음 = 예전 방식):
    --flat · 폴더에 이미 작업 공간이 있음. 폴더 이름이 <slides_dir> 이면 그 폴더가 작업 공간이고 상위 폴더가 루트(slides/slides 를 만들지 않는다)."""
    if flat:
        return folder, None
    if folder.name == slides_dir:
        return folder, folder.parent
    if (folder / "nexa-slide.json").is_file():
        return folder, None
    return folder / slides_dir, folder


def scaffold_repo(root, ws, title, port, write, made):
    """저장소 루트 — 폴더는 만들지 않고 md 파일만 둔다(이미 있으면 건드리지 않는다).
    SLIDES.md(개념·구조·서버 실행), CLAUDE.md·AGENTS.md 는 없을 때만. 작업 공간 CLAUDE.md 에 저장소 자료 안내를 덧붙인다."""
    slides = rel(ws, root)
    names = {"slides": slides, "guide": REPO_GUIDE}
    notes = []
    write(root / REPO_GUIDE, REPO_GUIDE_MD.format(title=title, port=port, slides_col=(slides + "/").ljust(20), **names))
    for fname, text, hint in (("CLAUDE.md", REPO_CLAUDE_MD, f"`{REPO_GUIDE}` 안내와 `@{slides}/CLAUDE.md`"),
                              ("AGENTS.md", REPO_AGENTS_MD, f"\"`{REPO_GUIDE}` 를 먼저 읽는다\"")):
        f = root / fname
        if not f.exists():
            write(f, text.format(title=title, **names))
        elif REPO_GUIDE not in f.read_text(encoding="utf-8", errors="replace"):
            notes.append(f"저장소 {fname} 가 이미 있어 고치지 않았다 — 슬라이드 작업도 안내하려면 {hint} 한 줄을 넣는다")
    cm = ws / "CLAUDE.md"
    if cm.is_file() and "## 저장소 자료" not in cm.read_text(encoding="utf-8"):
        with cm.open("a", encoding="utf-8", newline="\n") as fp:
            fp.write(WS_REPO_SECTION.format(root=rel(root, ws), guide=REPO_GUIDE))
    return notes


def starter(deck, title):
    return {
        "id": deck, "title": title, "part": "day1", "version": "0.1",
        "slides": [
            {"layout": "cover", "title": title, "subtitle": "부제 — 한두 줄", "days": [["day1", "1부"]], "meta": "작성자\n날짜\nv0.1",
             "notes": "표지 — 발표 목적을 한 문장으로."},
            {"layout": "bullets", "title": "이 발표에서 다룰 것", "sub": "핵심 메시지", "crumb": f"{deck} › 개요",
             "items": ["첫째 요점", {"text": "둘째 요점", "sub": ["보조 설명"]}, "셋째 요점"], "notes": "개요."},
            {"layout": "table", "title": "비교", "crumb": f"{deck} › 비교", "header": ["항목", "설명"], "rows": [["A", "설명"], ["B", "설명"]]},
            {"layout": "summary", "title": "정리", "crumb": f"{deck} › 정리", "items": ["기억할 것 1", "기억할 것 2"]},
            {"layout": "end", "title": "End of Document", "sub": title, "meta": "문의"},
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="nexa-slide 작업 공간 만들기")
    ap.add_argument("folder")
    ap.add_argument("--title")
    ap.add_argument("--port", help="포트 번호 또는 auto(기본 — 빈 포트를 고른다)")
    ap.add_argument("--template", help="디자인 템플릿(기본: 시작용 교안이 정한 것, 없으면 lecture)")
    ap.add_argument("--deck", default="intro")
    ap.add_argument("--asset-root", default=".", help="덱 그림 경로의 기준 폴더(작업 공간 기준). 저장소 루트 자산을 쓰려면 ..")
    ap.add_argument("--starter", help="시작용 교안(엔진 starters/ 폴더 이름) — 예: lecture-course")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--build", action="store_true", help="content → decks 빌드")
    ap.add_argument("--purpose", default="")
    ap.add_argument("--audience", default="")
    ap.add_argument("--direction", action="append", default=[], help="작성 방향 한 줄(여러 번)")
    ap.add_argument("--material", action="append", default=[], help="참고 자료 한 줄(여러 번)")
    ap.add_argument("--ask-draft", action="store_true", help="브리프로 초안 쓰기 요청을 남긴다(--build 포함)")
    ap.add_argument("--no-remember", action="store_true", help="최근 작업에 올리지 않는다(미리보기용 임시 작업 공간)")
    ap.add_argument("--flat", action="store_true", help="폴더 자체를 작업 공간으로(저장소 구조 없이) — 기본은 폴더 = 저장소 루트, 작업 공간 = <폴더>/slides")
    ap.add_argument("--slides-dir", default="slides", help="저장소형에서 작업 공간 폴더 이름(기본 slides)")
    a = ap.parse_args()
    port = None
    if a.port and a.port.lower() != "auto":
        try:
            port = int(a.port)
        except ValueError:
            sys.exit(f"포트는 숫자 또는 auto: {a.port}")
        if not 1024 <= port <= 65535:
            sys.exit(f"포트는 1024~65535: {port}")
    st = None
    if a.starter:
        if not (STARTERS / a.starter / "starter.json").is_file():
            names = ", ".join(p.name for p in STARTERS.iterdir() if (p / "starter.json").is_file())
            sys.exit(f"없는 시작용 교안: {a.starter} (있는 것: {names})")
        st = json.loads((STARTERS / a.starter / "starter.json").read_text(encoding="utf-8"))
    ws, root = resolve_target(Path(a.folder).resolve(), a.flat, a.slides_dir)
    if port is not None:
        cur = None
        try:
            cur = json.loads((ws / "nexa-slide.json").read_text(encoding="utf-8")).get("port")
        except (OSError, ValueError):
            pass
        if port == hub_port():
            sys.exit(f"포트 {port} 는 시작 페이지(허브) 포트다 — 다른 포트를 주거나 --port auto")
        if port != cur and port_busy(port):
            sys.exit(f"포트 {port} 는 지금 다른 프로그램이 쓰고 있다 — 다른 포트를 주거나 --port auto")
        other = taken_ports(skip=ws).get(port)
        if other:
            print(f"알림: 포트 {port} 는 작업 공간 {other} 설정과 같다 — 두 서버를 함께 띄우면 뒤에 띄운 쪽이 실패한다", file=sys.stderr)
    ws.mkdir(parents=True, exist_ok=True)
    a.template = a.template or (st or {}).get("template") or "lecture"
    if not (ENGINE / "studio" / "templates" / a.template / "template.json").is_file():
        sys.exit(f"없는 템플릿: {a.template}")
    made = []
    top = root or ws  # 만든 파일 목록은 저장소 루트(없으면 작업 공간) 기준으로 보인다
    name = a.title or top.name  # 저장소형이면 제목 기본값은 저장소 이름(slides 가 아니라)

    def write(path, text, overwrite=False):
        if path.exists() and not overwrite:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        made.append(rel(path, top))

    cfg_path = ws / "nexa-slide.json"
    if cfg_path.exists() and not a.force:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if port is not None and cfg.get("port") != port:  # 이미 있는 작업 공간: 포트만 바꾼다
            cfg["port"] = port
            write(cfg_path, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", overwrite=True)
    else:
        cfg = {"port": port or free_port(skip=ws), "title": name, "engine": rel(ENGINE, ws),
               "template": a.template, "fontPreset": "default", "assetRoot": a.asset_root,
               "brand": {"name": name, "logo": "assets/brand/logo.png", "wordmark": "assets/brand/wordmark.png",
                         "favicon": "assets/brand/favicon.png"},
               "partLabels": {"day1": "1부", "day2": "2부", "day3": "3부", "apx": "부록"}, "coverBadge": name}
        if root:  # 저장소형 — 저장소 루트와 자료·정리 폴더(작업 공간 기준 상대 경로)
            cfg["repo"] = {"root": rel(root, ws)}
        if st:
            cfg.update(st.get("config", {}))
        write(cfg_path, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", overwrite=True)
    show = rel(ws, root) if root else rel(ws, Path.cwd())  # 저장소형은 저장소 루트에서 실행하는 경로(slides)
    write(ws / "nexa.py", LAUNCHER.format(ws=show), overwrite=a.force)
    if st:  # 시작용 교안: content/ 는 작업 공간에, assets/ 는 assetRoot 아래에 복사(있는 파일은 그대로)
        sdir = STARTERS / a.starter
        for sub in st.get("copy", ["content"]):
            dest = ws if sub == "content" else ws / cfg.get("assetRoot", ".")
            for src in sorted((sdir / sub).rglob("*")):
                dst = dest / src.relative_to(sdir)
                if src.is_file() and not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    made.append(rel(dst, top))
    else:
        write(ws / "content" / f"{a.deck}.json", json.dumps(starter(a.deck, cfg.get("title", ws.name)), ensure_ascii=False, indent=1) + "\n")
    write(ws / "fonts" / "README.md", FONTS_README)
    write(ws / ".gitignore", "# nexa-slide 산출물·자동 백업 — 다시 만들 수 있음\nout/\ndecks/.history/\n")
    write(ws / "CLAUDE.md", CLAUDE_MD.format(engine=rel(ENGINE, ws), template=cfg.get("template"), ws=show, port=cfg.get("port")))
    write(ws / "AGENTS.md", AGENTS_MD.format(engine=rel(ENGINE, ws)))  # Claude 가 아닌 AI 도구(Codex 등)용
    write(ws / ".claude" / "settings.json", json.dumps({"hooks": session_hooks("nexa.py")}, ensure_ascii=False, indent=2) + "\n")
    notes = scaffold_repo(root, ws, cfg.get("title", name), cfg.get("port"), write, made) if root else []
    (ws / "decks").mkdir(exist_ok=True)
    for f in ("logo.png", "wordmark.png", "favicon.png"):
        dst = ws / cfg.get("assetRoot", ".") / "assets" / "brand" / f
        if not dst.exists() and (EXAMPLE / "assets" / "brand" / f).is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(EXAMPLE / "assets" / "brand" / f, dst)
            made.append(rel(dst, top))
    deck_ids = st["decks"] if st else [a.deck]
    fields = {"purpose": a.purpose, "audience": a.audience, "direction": "\n".join(a.direction), "materials": "\n".join(a.material)}
    if any(v.strip() for v in fields.values()) or a.ask_draft:  # 작성 브리프 — Claude 세션이 초안 전에 읽는다
        write(ws / "BRIEF.md", brief_md(cfg.get("title", ws.name), cfg.get("template"), a.starter, deck_ids[0], fields), overwrite=a.force)
        cm = ws / "CLAUDE.md"
        if cm.is_file() and "BRIEF.md" not in cm.read_text(encoding="utf-8"):
            with cm.open("a", encoding="utf-8", newline="\n") as f:
                f.write("\n## 작성 브리프\n\n- 작업 공간을 만들 때 받은 목적·대상·작성 방향·참고 자료는 `BRIEF.md` 에 있다. 초안을 쓰기 전에 먼저 읽고, 자료에 없는 내용은 지어내지 않는다.\n")
    built = build_decks(ws, cfg) if a.build or a.ask_draft else []
    if a.ask_draft and built:
        ask_draft(ws, cfg, deck_ids[0] if deck_ids[0] in built else built[0])
    if not a.no_remember:
        try:
            remember(ws, cfg.get("title", ws.name))
        except OSError:
            pass
    if root:
        print(f"저장소 루트: {root}  (저장소 관리 기준 폴더 · 안내 {REPO_GUIDE})")
    print(f"작업 공간: {ws}")
    print(f"  포트 {cfg.get('port')} · 템플릿 {cfg.get('template')} · 엔진 {cfg.get('engine')}")
    print("  만든 파일: " + (", ".join(made) or "(없음 — 이미 있음)"))
    for n in notes:
        print(f"  알림: {n}")
    if built:
        print("  빌드한 덱: " + ", ".join(built) + (" · 초안 요청을 남김" if a.ask_draft else ""))
    py = "python3" if shutil.which("python3") else "python"
    run = f'{py} "{ws / "nexa.py"}"'  # 그대로 붙여 넣을 수 있게 절대 경로 + 따옴표
    print("다음:")
    for d in ([] if built else deck_ids):
        print(f"  {run} build_deck {d}")
    print(f"  {run} start")
    print(f"  → http://127.0.0.1:{cfg.get('port')}/")


if __name__ == "__main__":
    main()
