# -*- coding: utf-8 -*-
"""새 작업 공간 만들기 — 다른 폴더·저장소에 nexa-slide 를 연결하는 뼈대를 만든다.

    python3 <엔진>/studio/init_workspace.py <작업 공간 폴더> [--title "제목"] [--port 5610] [--template lecture]
                                            [--deck intro] [--asset-root .] [--force]

만드는 것(이미 있는 파일은 건드리지 않음 — --force 면 nexa-slide.json·nexa.py 만 다시 씀)
    nexa-slide.json    선택만 담은 설정: port · title · engine(이 폴더에서 엔진까지 상대 경로) · template · fontPreset · brand 파일 경로
    nexa.py            실행기 — python3 <폴더>/nexa.py start|stop|status|url|build_deck …
    content/<deck>.json  시작용 내용 원본(표지 · 글머리 · 표 · 정리 · 끝)
    decks/  out/  assets/brand/   (로고는 엔진 예제의 자리 표시 이미지 — 자기 로고로 바꿔 쓴다)
    .gitignore         out/ · decks/.history/
    CLAUDE.md          이 작업 공간에서 일하는 Claude 세션 안내(요청 감시·처리 규약·명령)
포트를 주지 않으면 5600 부터 이 PC 에서 비어 있는 포트를 고른다(다른 작업 공간과 겹치지 않게).
"""
import argparse
import json
import os
import shutil
import socket
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
EXAMPLE = ENGINE / "example"


def free_port(start=5600, span=100):
    for p in range(start, start + span):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start


def rel(target, base):
    try:
        return os.path.relpath(target, base).replace("\\", "/")
    except ValueError:  # 드라이브가 다르면 절대 경로
        return str(target)


LAUNCHER = '''# -*- coding: utf-8 -*-
"""nexa-slide 실행기 — 이 폴더를 작업 공간으로 엔진 도구를 실행한다(init_workspace.py 가 만듦).

    python3 {ws}/nexa.py start | stop | restart | status | url     # 서비스(백그라운드 서버) 관리
    python3 {ws}/nexa.py build_deck <덱> [--force]                  # content → 덱
    python3 {ws}/nexa.py export_pptx <덱>                           # → out/<덱>.pptx
    python3 {ws}/nexa.py check_layout [<덱>]                        # 레이아웃 검사
    python3 {ws}/nexa.py layout_samples                             # 레이아웃 21종·필드 예시
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
- 초안을 쓰거나 고치면: `build_deck <덱> --force` → `check_layout <덱>`(ERROR 0 목표) → 편집기에서 확인.
  편집기에서 사람이 고친 슬라이드가 있으면 build 가 멈춘다 — 고친 내용을 content 에 옮긴 뒤 다시.
- **요청 감시**: 세션을 시작하면 Monitor 도구로
  `python3 {ws}/nexa.py watch_requests --stream --takeover --label "<세션 이름>"` (timeout 1800000) 를 건다.
  `{{"event":"ttl"}}` 이 오면 같은 명령으로 다시 건다. `{{"event":"refused"}}` 는 다른 세션이 맡고 있다는 뜻.
- **요청 처리 규약**(엔진 `docs/claude-session.md`): `decks/<덱>.requests.json` 에서 status `working` → 덱 수정(요소 id 유지, 원자적 쓰기)
  → 같은 변경을 `content/` 에도 → status `done` + `reply` 한두 문장. 영역 요청(`region`)은 그 좌표와 겹치는 요소가 대상.
- 기존 디자인·레이아웃 규칙을 유지한다 — 검사 경고를 없애려고 요소를 지우지 않는다. 근거·각주는 지어내지 않는다.
- 사용자 답변은 한국어.
'''


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
    ap.add_argument("--port", type=int)
    ap.add_argument("--template", default="lecture")
    ap.add_argument("--deck", default="intro")
    ap.add_argument("--asset-root", default=".", help="덱 그림 경로의 기준 폴더(작업 공간 기준). 저장소 루트 자산을 쓰려면 ..")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    ws = Path(a.folder).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    if not (ENGINE / "studio" / "templates" / a.template / "template.json").is_file():
        sys.exit(f"없는 템플릿: {a.template}")
    made = []

    def write(path, text, overwrite=False):
        if path.exists() and not overwrite:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        made.append(path.relative_to(ws).as_posix())

    cfg_path = ws / "nexa-slide.json"
    if cfg_path.exists() and not a.force:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    else:
        cfg = {"port": a.port or free_port(), "title": a.title or ws.name, "engine": rel(ENGINE, ws),
               "template": a.template, "fontPreset": "default", "assetRoot": a.asset_root,
               "brand": {"name": a.title or ws.name, "logo": "assets/brand/logo.png", "wordmark": "assets/brand/wordmark.png",
                         "favicon": "assets/brand/favicon.png"},
               "partLabels": {"day1": "1부", "day2": "2부", "day3": "3부", "apx": "부록"}, "coverBadge": a.title or ws.name}
        write(cfg_path, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", overwrite=True)
    show = rel(ws, Path.cwd())
    write(ws / "nexa.py", LAUNCHER.format(ws=show), overwrite=a.force)
    write(ws / "content" / f"{a.deck}.json", json.dumps(starter(a.deck, cfg.get("title", ws.name)), ensure_ascii=False, indent=1) + "\n")
    write(ws / ".gitignore", "# nexa-slide 산출물·자동 백업 — 다시 만들 수 있음\nout/\ndecks/.history/\n")
    write(ws / "CLAUDE.md", CLAUDE_MD.format(engine=rel(ENGINE, ws), template=cfg.get("template"), ws=show, port=cfg.get("port")))
    (ws / "decks").mkdir(exist_ok=True)
    for f in ("logo.png", "wordmark.png", "favicon.png"):
        dst = ws / cfg.get("assetRoot", ".") / "assets" / "brand" / f
        if not dst.exists() and (EXAMPLE / "assets" / "brand" / f).is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(EXAMPLE / "assets" / "brand" / f, dst)
            made.append(rel(dst, ws))
    print(f"작업 공간: {ws}")
    print(f"  포트 {cfg.get('port')} · 템플릿 {cfg.get('template')} · 엔진 {cfg.get('engine')}")
    print("  만든 파일: " + (", ".join(made) or "(없음 — 이미 있음)"))
    print("다음:")
    print(f"  python3 {show}/nexa.py build_deck {a.deck}")
    print(f"  python3 {show}/nexa.py start      → http://127.0.0.1:{cfg.get('port')}/")


if __name__ == "__main__":
    main()
