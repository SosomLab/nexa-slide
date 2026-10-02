# -*- coding: utf-8 -*-
"""작업 공간 글꼴 설치 — <작업 공간>/fonts/ 의 글꼴 파일을 현재 사용자에게 설치한다(관리자 권한 불필요).

    python3 <작업 공간>/nexa.py install_fonts          # fonts/ 의 .ttf · .otf 를 설치(이미 있으면 건너뜀)
    python3 <작업 공간>/nexa.py install_fonts --list   # 설치하지 않고 파일·글꼴 이름·설치 여부만

글꼴 파일은 엔진(nexa-slide 저장소)에 두지 않는다 — 작업 공간마다 fonts/ 에 둔다(docs/fonts.md).
편집기는 설치하지 않아도 서버가 fonts/ 를 직접 내보내 보이지만(/api/fontcss), PowerPoint(PPTX 열기·렌더)는
설치된 글꼴만 쓰므로 이 명령으로 설치한다. 설치 위치
    Windows  %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts + HKCU 글꼴 레지스트리
    macOS    ~/Library/Fonts
    Linux    ~/.local/share/fonts (+ fc-cache)
설치 뒤 PowerPoint·브라우저를 다시 열어야 보인다.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fonts_dir  # noqa: E402

EXT = (".ttf", ".otf")


def target_dir():
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "Microsoft/Windows/Fonts"
    if sys.platform == "darwin":
        return Path.home() / "Library/Fonts"
    return Path.home() / ".local/share/fonts"


def font_name(p):
    try:
        from PIL import ImageFont
        fam, style = ImageFont.truetype(str(p), 12).getname()
        return f"{fam} {style}".strip()
    except Exception:  # noqa: BLE001
        return p.stem


def register_windows(p, label):
    import winreg
    kind = "OpenType" if p.suffix.lower() == ".otf" else "TrueType"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, f"{label} ({kind})", 0, winreg.REG_SZ, str(p))


def main():
    ap = argparse.ArgumentParser(description="작업 공간 fonts/ 의 글꼴을 현재 사용자에게 설치")
    ap.add_argument("--list", action="store_true", help="설치하지 않고 목록만")
    a = ap.parse_args()
    src = fonts_dir()
    files = sorted(f for f in src.iterdir() if f.suffix.lower() in EXT) if src and src.is_dir() else []
    if not files:
        print(f"설치할 글꼴이 없다 — {src} 에 .ttf · .otf 파일을 둔다(docs/fonts.md)")
        return
    dest = target_dir()
    dest.mkdir(parents=True, exist_ok=True)
    done = 0
    for f in files:
        out = dest / f.name
        name = font_name(f)
        if a.list:
            print(f"{'설치됨' if out.exists() else '미설치'}  {f.name}  ({name})")
            continue
        if not out.exists():
            shutil.copy2(f, out)
            done += 1
            print(f"설치: {f.name}  ({name})")
        else:
            print(f"있음: {f.name}")
        if os.name == "nt":
            register_windows(out, name)
    if a.list:
        return
    if sys.platform.startswith("linux") and shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(dest)], check=False)
    print(f"완료 — 새로 {done}개 · 위치 {dest}. PowerPoint·브라우저를 다시 열면 적용된다.")


if __name__ == "__main__":
    main()
