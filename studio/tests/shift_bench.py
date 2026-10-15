# -*- coding: utf-8 -*-
"""글 세로 위치 대조 벤치(PowerPoint 필요, 수동) - 글꼴 세트(preset)로 상자·타원(흰 글, 어두운 면)을 크기×줄 높이로 깔고
PowerPoint 렌더(render_pptx.ps1)와 브라우저 캡처(slide.html)에서 글자 흰 픽셀의 세로 중심을 재 PPT−브라우저 차이를 낸다.
    python3 studio/tests/shift_bench.py <작업 공간> <preset|-> [--role body|heading|mono] [--only rect] [--pad12]
결과: 요소마다 (size, lh) → 차이 px, 그리고 shift = size×(a×lh+b) 최소제곱 a,b - 보정이 맞으면 a≈0, b≈0, 잔차 ±1px.
common.ppt_text_shift 의 상수(SHIFT_A·SHIFT_C)를 바꿀 때 이 벤치로 확인한다(docs/editor.md "줄 배치 보정")."""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
WS = Path(sys.argv[1]); PRESET = sys.argv[2] if len(sys.argv) > 2 else "-"
ROLE = sys.argv[sys.argv.index("--role") + 1] if "--role" in sys.argv else "heading"
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
ENG = Path(__file__).resolve().parents[2]
PORT = 5664
els = []
k = 0
SIZES = [16, 22, 28, 36, 44]; LHS = [1.0, 1.2, 1.4, 1.6]
PADS = {"ellipse": [0, 0, 0, 0], "rect": [0, 0, 0, 0]}
if "--pad12" in sys.argv: PADS = {"ellipse": [0, 0, 12, 0], "rect": [0, 0, 12, 0]}
for r, lh in enumerate(LHS):
    for c, size in enumerate(SIZES):
        for kind in ("ellipse", "rect"):
            k += 1
            x = 20 + c * 240 + (0 if kind == "ellipse" else 120); y = 20 + r * 170
            w, h = (100, 100) if kind == "ellipse" else (110, 100)
            els.append({"id": f"e{k:03d}", "type": kind, "x": x, "y": y, "w": w, "h": h, "fill": "#002F7B", "text": "I가", "size": size, "color": "#FFFFFF", "font": ROLE, "align": "center", "valign": "middle", "lineHeight": lh, "pad": PADS[kind], "_lh": lh, "_size": size})
deck = {"title": "shift bench", "slides": [{"id": "s1", "elements": [{k: v for k, v in e.items() if not k.startswith("_")} for e in els]}]}
if PRESET != "-":
    deck["fontPreset"] = PRESET
(WS / "decks").mkdir(exist_ok=True)
(WS / "decks" / "shiftbench.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
env = {**os.environ, "NEXA_SLIDE_WORKSPACE": str(WS), "PYTHONIOENCODING": "utf-8"}
r = subprocess.run([sys.executable, str(ENG / "studio/export_pptx.py"), "shiftbench", "--out", "out/shiftbench.pptx"], cwd=str(WS), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("export:", r.returncode, (r.stderr or r.stdout)[-200:].strip())
r = subprocess.run(["pwsh", "-NoProfile", "-File", str(ENG / "studio/render_pptx.ps1"), "-Pptx", str(WS / "out/shiftbench.pptx"), "-OutDir", str(WS / "out/shiftbench")], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("render:", r.returncode, (r.stderr or r.stdout)[-200:].strip())
ppt = Image.open(WS / "out/shiftbench/slide-01.png").convert("RGB")
if ppt.size != (1280, 720):
    ppt = ppt.resize((1280, 720), Image.LANCZOS)
srv = subprocess.Popen([sys.executable, str(ENG / "studio/server.py"), "--workspace", str(WS), "--port", str(PORT)], env=env, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/decks", timeout=2).read(); break
        except Exception:
            time.sleep(0.5)
    sys.path.insert(0, str(ENG / "studio"))
    exe = next(b for b in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if Path(b).exists())
    web_png = WS / "out/shiftbench/web-01.png"
    prof = WS / "out/.chrome-profile"
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", f"--user-data-dir={prof}", "--window-size=1280,720", "--virtual-time-budget=5000", f"--screenshot={web_png}", f"http://127.0.0.1:{PORT}/studio/slide.html?deck=shiftbench&n=1"], capture_output=True, timeout=90)
finally:
    srv.terminate()
web = Image.open(web_png).convert("RGB")
def center_y(img, e):
    px = img.load(); ys = []
    cx = e["x"] + e["w"] // 2
    xr = range(cx - 14, cx + 14) if e["type"] == "ellipse" else range(e["x"], e["x"] + e["w"])
    for yy in range(e["y"] + 3, e["y"] + e["h"] - 3):  # 타원 가장자리의 흐린 픽셀은 뺀다
        for xx in xr:
            r_, g_, b_ = px[xx, yy]
            if r_ > 180 and g_ > 180 and b_ > 180:
                ys.append(yy); break
    return (min(ys) + max(ys)) / 2 if ys else None, (min(ys), max(ys)) if ys else None
rows = []
for e in els:
    cp, bp = center_y(ppt, e); cw, bw = center_y(web, e)
    if cp is None or cw is None:
        continue
    rows.append((e["_size"], e["_lh"], e["type"], cp - cw, bp, bw))
print("size lh type  ppt-web(px)  ppt(top,bot) web(top,bot)")
for s, lh, t, d, bp, bw in rows:
    print(f"{s:4d} {lh:3.1f} {t:7s} {d:+6.1f}   {bp} {bw}")
# 최소제곱: d = size*(a*lh + b)  → d/size = a*lh + b
import statistics
rows = [r for r in rows if not ONLY or r[2] == ONLY]
xs = [lh for s, lh, t, d, *_ in rows]; ys = [d / s for s, lh, t, d, *_ in rows]
n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs); b = my - a * mx
res = [d - s * (a * lh + b) for s, lh, t, d, *_ in rows]
print(f"fit: a={a:.4f} b={b:.4f}  잔차 max {max(abs(v) for v in res):.1f}px  (현재 브라우저 보정이 이미 들어간 상태의 잔여 차이)")
