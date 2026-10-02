# -*- coding: utf-8 -*-
"""글꼴 포함 PPTX — out/<덱>.pptx 를 PowerPoint(Windows)로 "글꼴 포함" 저장해 out/<덱>-fonts.pptx 를 만든다.

    python3 <작업 공간>/nexa.py embed_fonts <덱>              # 내보내기 → 글꼴 포함 저장 → 기록(out/<덱>.fonts.json 의 embedded)
    python3 <작업 공간>/nexa.py embed_fonts <덱> --install    # 쓴 글꼴 중 작업 공간 fonts/ 에 있고 설치 안 된 것을 먼저 설치

PowerPoint 는 설치된 글꼴만 넣을 수 있다. 작업 공간 글꼴이 설치되어 있지 않으면 끝 코드 3 과 함께 JSON 한 줄
{"needInstall": [파일…]} 을 내고 멈춘다(--install 이면 설치하고 계속). 포함 금지 글꼴(fsType 2)은 PowerPoint 가 넣지 않는다.
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, STUDIO, safe_id  # noqa: E402
import font_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    if not safe_id(a.id):
        sys.exit("잘못된 덱 id")
    src, dst = OUT / f"{a.id}.pptx", OUT / f"{a.id}-fonts.pptx"
    r = subprocess.run([sys.executable, str(STUDIO / "export_pptx.py"), a.id], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not src.exists():
        sys.exit("내보내기 실패\n" + r.stdout + r.stderr)
    rep = font_report.report(a.id, src)
    need = sorted({f["path"] for u in rep["used"] for f in u["files"][:1] if f["where"] == "workspace" and not f["installed"]})
    if need and not a.install:
        print(json.dumps({"needInstall": need}, ensure_ascii=False))
        sys.exit(3)
    if need:
        subprocess.run([sys.executable, str(STUDIO / "install_fonts.py")], check=False)
    r = subprocess.run(["pwsh", "-NoProfile", "-File", str(STUDIO / "embed_fonts.ps1"), "-Pptx", str(src), "-Out", str(dst)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not dst.exists():
        sys.exit("PowerPoint 글꼴 포함 저장 실패(PowerPoint 설치 필요)\n" + (r.stdout or "") + (r.stderr or ""))
    with zipfile.ZipFile(dst) as z:
        emb = sorted(n for n in z.namelist() if n.startswith("ppt/fonts/"))
    fo, rep = font_report.write(a.id, src, {"embeddedPptx": dst.name, "embedded": emb})
    names = sorted({u["typeface"] for u in rep["used"]})
    print(json.dumps({"ok": True, "pptx": dst.name, "embedded": len(emb), "typefaces": names,
                      "sizeKB": round(dst.stat().st_size / 1024), "installed": need}, ensure_ascii=False))


if __name__ == "__main__":
    main()
