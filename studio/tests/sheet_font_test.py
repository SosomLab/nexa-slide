# -*- coding: utf-8 -*-
"""시트 글꼴(0.25.18) - 슬라이드와 같은 글꼴 세트를 시트에도. 문서 fontPreset · 셀 font(역할 또는 이름) → xlsx 글꼴 이름, 가져오기는 칸 글꼴을 되살린다.

    python3 studio/tests/sheet_font_test.py

화면 쪽 규칙(sheet.js baseFamily·cellFamily)은 시나리오 sheetfont_test 가 본다. 엑셀 파일은 시험 안에서 만든다.
"""
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="nexa-sheet-font-"))
(TMP / "nexa-slide.json").write_text(json.dumps({"fontPresets": {"corp": {"body": {"css": "\"사내체\", sans-serif", "latin": "CorpSans", "ea": "사내체"}}}}, ensure_ascii=False), encoding="utf-8")
os.environ["NEXA_SLIDE_WORKSPACE"] = str(TMP)
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import export_xlsx  # noqa: E402
import sheet_import  # noqa: E402

FAILS = []


def check(name, ok, got=None):
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f" → {got}"))
    if not ok:
        FAILS.append(name)


def fonts_of(p):
    """xlsx styles.xml 의 글꼴 이름 목록(첫째 = 기본)."""
    with zipfile.ZipFile(p) as z:
        s = z.read("xl/styles.xml").decode("utf-8")
    return re.findall(r'<name val="([^"]+)"', s)


def doc(**kw):
    return {"kind": "sheet", "title": "글꼴", "slides": [], **kw, "sheets": [{"id": "t01", "name": "S", "cells": {
        "A1": "기본", "A2": {"v": "고정폭", "font": "mono"}, "A3": {"v": "제목", "font": "heading"}, "A4": {"v": "이름", "font": "Consolas"}}}]}


modern = common.preset_fonts("modern")
check("엔진 세트 modern · 작업 공간 세트 corp 가 tokens 에 있다", modern and common.preset_fonts("corp") and common.preset_fonts("corp")["body"]["ea"] == "사내체",
      list((common.tokens().get("fontPresets") or {}).keys()))

out = TMP / "a.xlsx"
export_xlsx.export(doc(fontPreset="corp"), out)
fs = fonts_of(out)
check("문서 fontPreset → 기본 글꼴이 그 세트 본문(ea 사내체)", fs and fs[0] == "사내체", fs)
mono = (modern and common.preset_fonts("corp")["mono"]) or {}
check("셀 font 역할 mono → 세트의 고정폭 글꼴 이름 · 이름 Consolas 는 그대로", (mono.get("ea") or mono.get("latin")) in fs and "Consolas" in fs, (fs, mono))
check("셀 font 역할 heading → 세트에 제목이 없으면 본문(사내체)", fs.count("사내체") >= 1, fs)

out2 = TMP / "b.xlsx"
export_xlsx.export(doc(), out2)
fs2 = fonts_of(out2)
base = (common.tokens()["fonts"]["body"].get("ea") or common.tokens()["fonts"]["body"].get("latin"))
check("세트 없는 문서는 기본 글꼴을 바꾸지 않는다(엑셀 기본) · 역할은 작업 공간 세트", fs2[0] == "Calibri" and base in fs2, (fs2, base))

tabs, warn, bf = sheet_import.import_xlsx(str(out))
cells = tabs[0]["cells"]
check("가져오기: 기본 글꼴과 다른 칸 글꼴을 되살린다(Consolas) · 기본 글꼴 칸은 font 없음",
      cells["A4"].get("font") == "Consolas" and not (isinstance(cells["A1"], dict) and cells["A1"].get("font")) and bf.get("name") == "사내체",
      {k: cells[k] for k in ("A1", "A4")})

print("\n실패:", FAILS or "없음")
print("전부 통과" if not FAILS else "")
sys.exit(1 if FAILS else 0)
