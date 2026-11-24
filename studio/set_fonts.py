# -*- coding: utf-8 -*-
"""글꼴 프리셋 고르기 — 프리셋(fontPresets)은 템플릿 tokens.json 에 있고, 작업 공간은 이름만 고른다.

    python3 studio/set_fonts.py -W <작업 공간>              # 프리셋 목록과 현재 선택
    python3 studio/set_fonts.py -W <작업 공간> default      # 맑은 고딕 · Consolas
    python3 studio/set_fonts.py -W <작업 공간> modern       # Pretendard · JetBrains Mono + D2Coding
    python3 nexa.py set_fonts sebang --from Sebang-Regular.ttf --bold Sebang-Bold.ttf   # 작업 공간 fonts/ 에 넣어 둔 파일로 세트를 만들고 고른다
                                                                                        # (회사 서체 - nexa-slide.json fontPresets, --family 로 이름 직접)

고른 이름은 작업 공간 nexa-slide.json 의 "fontPreset" 에 저장된다(템플릿 파일은 바꾸지 않는다).
글꼴은 덱 JSON에 들어가지 않고 편집기 표시(render.js)·PPTX 내보내기(export_pptx.py)가 읽는다.
바꾼 뒤: 편집기는 바로 반영, PPTX 는 다시 내보낸다. 새 글꼴은 python3 nexa.py install_fonts 로 먼저 설치.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG_NAME, LOCAL_NAME, TEMPLATE, WORKSPACE, fonts_dir, read_config, resolve_tokens  # noqa: E402


def define(name, args):
    """fonts/ 에 이미 넣어 둔 글꼴 파일로 작업 공간 글꼴 세트(nexa-slide.json fontPresets.<name>)를 만들고 고른다 - 웹에서 받을 때의 fetch_asset --preset 과 같은 결과."""
    import argparse
    import fetch_asset as fa
    ap = argparse.ArgumentParser(prog=f"set_fonts {name}")
    ap.add_argument("--from", dest="regular", required=True, help="fonts/ 안의 보통 굵기 글꼴 파일 이름(.ttf·.otf)")
    ap.add_argument("--bold", help="fonts/ 안의 굵은 글꼴 파일 이름")
    ap.add_argument("--family", help="글꼴 패밀리 이름(비우면 글꼴 파일에서 읽는다)")
    a = ap.parse_args(args)
    try:
        fa.preset_check(name, "regular")
        data = {}
        for fn in filter(None, (a.regular, a.bold)):
            p = fonts_dir() / fn
            if Path(fn).name != fn or p.suffix.lower() not in fa.FONT_EXTS or not p.is_file():
                raise fa.Refuse(f"fonts/ 에 없는 글꼴 파일: {fn} - 작업 공간 fonts/ 바로 아래의 .ttf·.otf 파일 이름만 적는다({fonts_dir()})")
            data[fn] = p.read_bytes()
            fa.sniff(data[fn], p.suffix.lower())
        family = " ".join((a.family or fa.family_name(data[a.regular]) or "").split())
        pr = fa.set_preset(name, "regular", a.regular, family)
        if a.bold:
            pr = fa.set_preset(name, "bold", a.bold, family)
    except fa.Refuse as e:
        sys.exit(f"글꼴 세트를 만들지 않음: {e}")
    ms = pr["body"]["measure"]
    print(f"글꼴 세트 {name}: {pr['body']['latin']} · 보통 {ms['regular']} · 굵게 {ms['bold']} → fontPreset = {name} ({WORKSPACE / CONFIG_NAME})")
    if read_config().get("fontPreset") != name:
        print(f"알림: 이 PC 의 {LOCAL_NAME} 에 fontPreset 이 있어 이 PC 에서는 그 값이 쓰인다")
    print("다음: 편집기는 새로 고치면 이 글꼴로 보인다. PowerPoint 에 쓰려면 install_fonts, PPTX 는 다시 내보낸다.")


def main():
    if len(sys.argv) > 2:  # set_fonts <세트> --from <파일> … = 세트 만들기
        return define(sys.argv[1], sys.argv[2:])
    cfg = read_config()
    t = resolve_tokens(cfg)
    presets = t.get("fontPresets", {})
    if len(sys.argv) < 2:
        print(f"템플릿 {TEMPLATE['name']} · 현재:", t.get("fontPreset", "(템플릿 기본)"))
        for k, v in presets.items():
            v = {"mono": t["fonts"]["mono"], **v}  # 작업 공간 세트(회사 서체)는 코드 글꼴이 없을 수 있다 - 템플릿 것을 쓴다(목록이 KeyError 로 죽던 것)
            print(f"  {k:10s} 본문 {v['body']['latin']} / {v['body']['ea']} · 코드 {v['mono']['latin']} / {v['mono']['ea']}")
        return
    name = sys.argv[1]
    if name not in presets:
        sys.exit(f"없는 프리셋: {name} — {', '.join(presets)}")
    shared = read_config(shared=True)  # 공유 파일에만 쓴다(PC 별 nexa-slide.local.json 값은 섞지 않는다)
    shared["fontPreset"] = name
    (WORKSPACE / CONFIG_NAME).write_text(json.dumps(shared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"글꼴 프리셋 → {name} ({WORKSPACE / CONFIG_NAME})")
    if read_config().get("fontPreset") != name:
        print(f"알림: 이 PC 의 {LOCAL_NAME} 에 fontPreset 이 있어 이 PC 에서는 그 값이 쓰인다")


if __name__ == "__main__":
    main()
