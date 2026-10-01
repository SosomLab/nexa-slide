# -*- coding: utf-8 -*-
"""글꼴 프리셋 바꾸기 — tokens.json 의 fontPresets 중 하나를 fonts(현재 사용)로 복사한다.

    python3 studio/set_fonts.py              # 프리셋 목록과 현재 값
    python3 studio/set_fonts.py default      # 원래 설정(맑은 고딕 · Consolas)으로
    python3 studio/set_fonts.py modern       # 추천(Pretendard · JetBrains Mono + D2Coding)으로

글꼴은 덱 JSON에 들어가지 않고 편집기 표시(render.js)·PPTX 내보내기(export_pptx.py)가 tokens.json 에서 읽는다.
바꾼 뒤: 편집기는 새로 고침, PPTX 는 export_pptx.py 로 다시 내보낸다. 새 글꼴은 install_fonts.ps1 로 먼저 설치.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TOKENS as P  # noqa: E402  작업 공간 tokens.json(없으면 엔진 기본값)


def main():
    t = json.loads(P.read_text(encoding="utf-8"))
    presets = t.get("fontPresets", {})
    if len(sys.argv) < 2:
        print("현재:", t.get("fontPreset", "(이름 없음)"))
        for k, v in presets.items():
            print(f"  {k:10s} 본문 {v['body']['latin']} / {v['body']['ea']} · 코드 {v['mono']['latin']} / {v['mono']['ea']}")
        return
    name = sys.argv[1]
    if name not in presets:
        sys.exit(f"없는 프리셋: {name} — {', '.join(presets)}")
    t["fonts"] = json.loads(json.dumps(presets[name]))
    t["fontPreset"] = name
    P.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"글꼴 프리셋 → {name}")


if __name__ == "__main__":
    main()
