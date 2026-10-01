# -*- coding: utf-8 -*-
"""브라우저 렌더 vs PowerPoint 렌더 비교 (검증 도구).

    python3 studio/compare.py ch00 [--slides 1,5,9] [--port N]

전제: server.py 실행 중, out/<id>/slide-NN.png(PowerPoint 렌더)가 있음(편집기 "PPT 렌더" 또는 render_pptx.ps1).
결과: out/<id>/web-NN.png(헤드리스 Chrome/Edge 캡처), compare-NN.png(위: 브라우저 · 가운데: PPT · 아래: 차이),
      콘솔에 슬라이드별 차이 비율(픽셀 중 눈에 띄게 다른 비율).
Pillow 필요(검증 도구 전용 — 편집기·변환기는 필요 없음).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, load_deck, server_port  # noqa: E402

BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


def browser():
    for b in BROWSERS:
        if Path(b).exists():
            return b
    return shutil.which("chrome") or shutil.which("msedge")


def shot(exe, url, out: Path):
    prof = OUT / ".chrome-profile"
    cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
           f"--user-data-dir={prof}", "--window-size=1280,720", "--virtual-time-budget=4000",
           f"--screenshot={out}", url]
    subprocess.run(cmd, capture_output=True, timeout=60)
    return out.exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--slides")
    ap.add_argument("--port", type=int, default=None, help="기본: 이 작업 공간에서 실행 중인 서버 포트(out/.studio/server.json) → 설정 port → 5600")
    a = ap.parse_args()
    a.port = a.port or server_port()
    from PIL import Image, ImageChops, ImageDraw, ImageFont

    deck = load_deck(a.id)
    n = len(deck["slides"])
    nums = [int(x) for x in a.slides.split(",")] if a.slides else list(range(1, n + 1))
    exe = browser()
    if not exe:
        sys.exit("Chrome/Edge 없음")
    d = OUT / a.id
    d.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 20)
    except Exception:
        font = None
    for k in nums:
        web = d / f"web-{k:02d}.png"
        web.unlink(missing_ok=True)
        ok = shot(exe, f"http://127.0.0.1:{a.port}/studio/slide.html?deck={a.id}&n={k}", web)
        ppt = d / f"slide-{k:02d}.png"
        if not ok or not ppt.exists():
            print(f"{k:02d}: 캡처 {'성공' if ok else '실패'} · PPT 렌더 {'있음' if ppt.exists() else '없음'}")
            continue
        A = Image.open(web).convert("RGB").resize((1280, 720))
        B = Image.open(ppt).convert("RGB").resize((1280, 720))
        diff = ImageChops.difference(A, B).convert("L")
        mask = diff.point(lambda v: 255 if v > 60 else 0)
        ratio = sum(1 for v in mask.getdata() if v) / (1280 * 720)
        heat = Image.composite(Image.new("RGB", (1280, 720), (220, 0, 0)), Image.blend(A, B, 0.5).convert("L").convert("RGB"), mask)
        canvas = Image.new("RGB", (1280, 720 * 3 + 60), "white")
        for i, (img, label) in enumerate([(A, "브라우저(render.js)"), (B, "PowerPoint(export_pptx)"), (heat, f"차이 {ratio:.2%}")]):
            canvas.paste(img, (0, i * 740 + 20))
            ImageDraw.Draw(canvas).text((8, i * 740), label, fill=(169, 31, 36), font=font)
        canvas.save(d / f"compare-{k:02d}.png")
        print(f"{k:02d}: 차이 {ratio:.2%}  → {d / f'compare-{k:02d}.png'}")


if __name__ == "__main__":
    main()
