# -*- coding: utf-8 -*-
"""작업 공간 실행기(nexa.py)를 이 엔진의 최신 판으로 바꾼다 — 설정·내용은 건드리지 않는다.

    python3 <작업 공간>/nexa.py update_launcher        # 예전 실행기에서도 동작(엔진 도구로 실행된다)
    python3 studio/update_launcher.py --workspace <작업 공간>

함께 하는 일: .gitignore 에 PC 별 설정(.env · nexa-slide.local.json)을 더하고, .env 샘플(.env.example)과
이 PC 의 .env(지금 엔진 위치)를 둔다(없을 때만 — 있는 .env 는 고치지 않는다).
.claude/settings.json 에 AI 세션 권한(쓰기 범위 = 이 폴더, 명령은 nexa.py 만 - studio/agents/permissions.json)과 훅을 없는 키만 더한다.
새 실행기는 PC 마다 엔진 위치를 찾는다 — .env > nexa-slide.local.json > 환경변수 > PC 설정 > nexa-slide.json(docs/configuration.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, WORKSPACE  # noqa: E402
from paths import ROOT_MARKER, write_root_marker  # noqa: E402
from init_workspace import ensure_claude_commands, LAUNCHER, ensure_claude_settings, ensure_env_files, ensure_gitignore  # noqa: E402


def main():
    f = WORKSPACE / "nexa.py"
    new = LAUNCHER.format(ws=WORKSPACE.name)
    old = f.read_text(encoding="utf-8") if f.is_file() else ""
    if old == new:
        print(f"실행기는 이미 최신이다: {f}")
    else:
        f.write_text(new, encoding="utf-8", newline="\n")
        print(f"실행기를 바꿨다: {f}")
    if ensure_gitignore(WORKSPACE):
        print(f".gitignore 에 PC 별 설정(.env · nexa-slide.local.json)을 더했다: {WORKSPACE / '.gitignore'}")
    repo = CONFIG.get("repo") if isinstance(CONFIG.get("repo"), dict) else None
    root = (WORKSPACE / repo["root"]).resolve() if repo and repo.get("root") else None
    if root and root != WORKSPACE and write_root_marker(root, WORKSPACE):  # 저장소형 - 루트 표식
        print(f"저장소 표식을 두었다: {root / ROOT_MARKER} (workspace = {WORKSPACE.name})")
    for name in ensure_env_files(WORKSPACE):
        print(f"{name} 를 두었다: {WORKSPACE / name}" + (" — NEXA_SLIDE_HOME 에 이 엔진 위치(가장 먼저 쓰인다)" if name == ".env" else " — 샘플(커밋)"))
    if ensure_claude_commands(WORKSPACE):
        print("추가: .claude/commands/nexa-engine.md - 이 폴더의 Claude Code 세션에서 /nexa-engine 으로 서버 작업 큐를 맡을 수 있다")
    if ensure_claude_settings(WORKSPACE):  # AI 세션 권한(쓰기 범위 = 이 폴더, 명령은 nexa.py 만) - 없는 키만 더한다
        print(f".claude/settings.json 에 훅·권한을 더했다: {WORKSPACE / '.claude' / 'settings.json'}")
    print(f"엔진 위치 확인: python3 {f} engine")


if __name__ == "__main__":
    main()
