# -*- coding: utf-8 -*-
"""그림 프레임 효과(effect·effectLevel) 시험 - 효과별 그림 요소를 둔 덱을 PPTX 로 내보내 슬라이드 XML 에 softEdge·glow·roundRect·ellipse·테두리가 들어갔는지,
편집기 render.js 가 효과 CSS(mask·border-radius·border·box-shadow)를 내는지(node 로 render.js 를 읽어) 확인한다."""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "effect시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "effect시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    (WS / "assets" / "images").mkdir(parents=True, exist_ok=True); (WS / "assets" / "images" / "t.png").write_bytes(PNG)
    fx = ["softEdge", "round", "circle", "frame", "glow"]
    els = [{"id": f"e{i:02d}", "type": "image", "x": 40 + i * 230, "y": 100, "w": 200, "h": 150, "src": "assets/images/t.png", "effect": e, "effectLevel": 3 if e == "round" else 2} for i, e in enumerate(fx, 1)]
    els.append({"id": "e09", "type": "image", "x": 40, "y": 400, "w": 200, "h": 150, "src": "assets/images/t.png"})
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "decks" / "fx.json").write_text(json.dumps({"title": "효과", "slides": [{"id": "s1", "elements": els}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(STUDIO / "export_pptx.py"), "fx", "--out", "out/fx.pptx"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("export_pptx 성공", r.returncode == 0 and (WS / "out" / "fx.pptx").is_file(), (r.stderr or r.stdout)[-300:])
    xml = ""
    if (WS / "out" / "fx.pptx").is_file():
        with zipfile.ZipFile(WS / "out" / "fx.pptx") as z:
            xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    check("softEdge → a:softEdge rad(12px)", re.search(r'<a:softEdge rad="\d+"', xml) is not None, xml[:0])
    check("round(수준 3) → prstGeom roundRect adj", 'prst="roundRect"' in xml and re.search(r'name="adj" fmla="val \d+"', xml) is not None)
    check("circle → prstGeom ellipse", xml.count('prst="ellipse"') >= 1)
    check("frame → 흰 테두리 a:ln + 그림자", re.search(r'<a:ln w="\d+"[^>]*>\s*<a:solidFill>\s*<a:srgbClr val="FFFFFF"', xml) is not None and "outerShdw" in xml)
    check("glow → a:glow rad + 색", re.search(r'<a:glow rad="\d+">\s*<a:srgbClr val="[0-9A-F]{6}">\s*<a:alpha val="60000"', xml) is not None)
    check("효과 없는 그림은 그대로(rect 기하)", xml.count('prst="rect"') >= 1)
    # render.js - 효과 CSS
    js = f'''
const fs=require("fs"); const src=fs.readFileSync({json.dumps(str(STUDIO / "render.js"))},"utf8");
const w={{document:{{createElement:()=>({{style:{{}}}}),querySelector:()=>null}},location:{{}},navigator:{{}}}}; w.window=w; w.self=w;
const vm=require("vm"); vm.createContext(w); vm.runInContext(src,w);
const R=w.Render; R.setTokens({{colors:{{primary:"#A91F24"}},fonts:{{body:{{css:"x"}},heading:{{css:"x"}},mono:{{css:"x"}}}}}});
const out={{}};
for (const [e,lv] of [["softEdge",2],["round",3],["circle",2],["frame",2],["glow",2]]) {{ out[e]=R.renderSlide({{id:"s1",elements:[{{id:"e1",type:"image",x:0,y:0,w:200,h:150,src:"t.png",effect:e,effectLevel:lv}}]}},1); }}
console.log(JSON.stringify(out));
'''
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = {}
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        check("render.js 실행", False, (r.stderr or r.stdout)[-300:])
    if out:
        check("render softEdge → mask 12px", "mask-image" in out["softEdge"] and "#000 12px" in out["softEdge"])
        check("render round(3) → border-radius 32px", "border-radius:32px" in out["round"])
        check("render circle → border-radius 50%", "border-radius:50%" in out["circle"])
        check("render frame → 6px 흰 테두리", "border:6px solid #fff" in out["frame"])
        check("render glow → box-shadow primary", "box-shadow:0 0 16px" in out["glow"] and "#A91F24" in out["glow"])
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
