# -*- coding: utf-8 -*-
"""글꼴 프리셋 고르기 — 프리셋(fontPresets)은 템플릿 tokens.json 에 있고, 작업 공간은 이름만 고른다.

    python3 studio/set_fonts.py -W <작업 공간>              # 프리셋 목록과 현재 선택
    python3 studio/set_fonts.py -W <작업 공간> default      # 맑은 고딕 · Consolas
    python3 studio/set_fonts.py -W <작업 공간> modern       # Pretendard · JetBrains Mono + D2Coding

고른 이름은 작업 공간 nexa-slide.json 의 "fontPreset" 에 저장된다(템플릿 파일은 바꾸지 않는다).
글꼴은 덱 JSON에 들어가지 않고 편집기 표시(render.js)·PPTX 내보내기(export_pptx.py)가 읽는다.
바꾼 뒤: 편집기는 바로 반영, PPTX 는 다시 내보낸다. 새 글꼴은 install_fonts.ps1 로 먼저 설치.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG_NAME, TEMPLATE, WORKSPACE, read_config, resolve_tokens  # noqa: E402


def main():
    cfg = read_config()
    t = resolve_tokens(cfg)
    presets = t.get("fontPresets", {})
    if len(sys.argv) < 2:
        print(f"템플릿 {TEMPLATE['name']} · 현재:", t.get("fontPreset", "(템플릿 기본)"))
        for k, v in presets.items():
            print(f"  {k:10s} 본문 {v['body']['latin']} / {v['body']['ea']} · 코드 {v['mono']['latin']} / {v['mono']['ea']}")
        return
    name = sys.argv[1]
    if name not in presets:
        sys.exit(f"없는 프리셋: {name} — {', '.join(presets)}")
    cfg["fontPreset"] = name
    (WORKSPACE / CONFIG_NAME).write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"글꼴 프리셋 → {name} ({WORKSPACE / CONFIG_NAME})")


if __name__ == "__main__":
    main()
