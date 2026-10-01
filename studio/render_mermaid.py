# -*- coding: utf-8 -*-
"""장 내용(content/<id>.json)의 diagram 슬라이드 — mermaid 코드 → PNG(img 경로).

    python3 studio/render_mermaid.py ch18            # 코드가 바뀐 도면만 다시 그린다
    python3 studio/render_mermaid.py ch18 --all      # 모두 다시

원본 코드는 img 옆에 같은 이름의 .mmd 로 남긴다(저장소에서 도면을 코드로 리뷰 — ch18 §18.14).
렌더러: @mermaid-js/mermaid-cli(npx, 처음 한 번 내려받는다), 2배 해상도, 흰 배경.
build_deck.py 보다 먼저 실행한다(레이아웃이 PNG 크기를 읽는다).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONTENT, REPO, safe_id  # noqa: E402

CONFIG = {
    "theme": "base",
    "themeVariables": {
        "fontFamily": "Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif",
        "fontSize": "16px",
        "primaryColor": "#EEF3F8", "primaryBorderColor": "#35506B", "primaryTextColor": "#1B1B1F",
        "lineColor": "#35506B", "secondaryColor": "#F6F1E7", "tertiaryColor": "#FFFFFF",
    },
    "er": {"useMaxWidth": False}, "flowchart": {"useMaxWidth": False, "htmlLabels": True},
    "sequence": {"useMaxWidth": False}, "state": {"useMaxWidth": False},
}


def render(code, png):
    png.parent.mkdir(parents=True, exist_ok=True)
    mmd = png.with_suffix(".mmd")
    cfg = png.parent / "_mermaid-config.json"
    cfg.write_text(json.dumps(CONFIG, ensure_ascii=False, indent=1), encoding="utf-8")
    mmd.write_text(code.rstrip() + "\n", encoding="utf-8")
    npx = "npx.cmd" if sys.platform.startswith("win") else "npx"
    r = subprocess.run([npx, "-y", "@mermaid-js/mermaid-cli", "-i", str(mmd), "-o", str(png), "-s", "2", "-b", "white",
                        "-c", str(cfg)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not png.exists():
        sys.exit(f"렌더 실패 {mmd}:\n{r.stdout}\n{r.stderr}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if not safe_id(a.id):
        sys.exit("잘못된 id")
    content = json.loads((CONTENT / f"{a.id}.json").read_text(encoding="utf-8"))
    n = 0
    for s in content["slides"]:
        if s.get("layout") != "diagram" or not s.get("mermaid"):
            continue
        png = REPO / s["img"]
        mmd = png.with_suffix(".mmd")
        same = mmd.exists() and mmd.read_text(encoding="utf-8").rstrip() == s["mermaid"].rstrip()
        if same and png.exists() and not a.all:
            continue
        render(s["mermaid"], png)
        n += 1
        print(f"  그림: {s['img']}")
    print(f"{a.id} — 다시 그린 도면 {n}개")


if __name__ == "__main__":
    main()
