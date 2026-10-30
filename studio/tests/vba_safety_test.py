# -*- coding: utf-8 -*-
"""VBA 보안 보완(0.25.8) 시험.

1. 위험 코드 검사 - 화면(vba.js NexaVBA.risks)과 Python(vba_project.risks)이 같은 줄·같은 낱말을 고르나(규칙은 vba.js RISKS 한 곳)
2. 내보내기 - 매크로 문서는 늘 모듈 소스로 다시 쓴 프로젝트(원본 p-code·__SRP_ 를 버리고 판 0xFFFF), --no-macros 면 .xlsx(vbaProject.bin 없음)
3. 서버 /api/export ?macros=0
VBA 프로젝트는 시험 안에서 만든다(vba_project.cfb_write - 엑셀이 만든 파일을 저장소에 넣지 않는다).
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
import vba_project  # noqa: E402

fails, ok = [], 0


def check(name, got, want):
    global ok
    if got == want:
        ok += 1
    else:
        fails.append(name)
        print(f"FAIL {name}\n  → {got!r}\n  기대 {want!r}")


CASES = [
    {"name": "ThisWorkbook", "kind": "doc", "code": "Private Sub Workbook_Open()\r\n    x = Shell(\"cmd /c calc.exe\")  ' Kill 은 주석\r\nEnd Sub\r\n"},
    {"name": "Module1", "kind": "std", "code": "\r\n".join([
        "Option Explicit",
        "Private Declare PtrSafe Function URLDownloadToFileA Lib \"urlmon\" (ByVal a As LongPtr) As Long",
        "Rem CreateObject 는 주석",
        "Function Safe(x)",
        "    Safe = \"it's \" & x  ' 문자열 안의 따옴표 뒤는 코드",
        "    MsgBox \"Shell 은 글\"",
        "End Function",
        "Sub Go()",
        "    Set o = CreateObject(\"WScript.Shell\")",
        "    Open \"C:\\a.txt\" For Output As #1",
        "    Kill \"C:\\a.txt\"",
        "    ThisWorkbook.VBProject.VBComponents.Add 1",
        "    ActiveWorkbook.SaveAs \"x.xlsm\"",
        "    Application.Run \"Other\"",
        "    가Shell = 1",
        "    obj.Shell",
        "End Sub",
        "Sub Auto_Open()",
        "End Sub",
    ])},
]

# ---------------------------------------------------------------- 1. 위험 코드 - 화면과 같은가
js = "const V=require(process.argv[1]); process.stdout.write(JSON.stringify(V.risks(JSON.parse(require('fs').readFileSync(0,'utf8')))));"
r = subprocess.run(["node", "-e", js, str(STUDIO / "vba.js")], input=json.dumps(CASES), capture_output=True, text=True, encoding="utf-8")
jr = json.loads(r.stdout or "[]")
pr = vba_project.risks(CASES)
key = lambda xs: [(x["module"], x["line"], x["kind"], x["word"]) for x in xs]  # noqa: E731
check("위험 코드 - 화면(vba.js)과 Python 이 같다", key(pr), key(jr))
got = {(x["module"], x["line"], x["word"].lower()) for x in pr}
for want in [("ThisWorkbook", 1, "workbook_open"), ("ThisWorkbook", 2, "shell"), ("ThisWorkbook", 2, "cmd /c"), ("Module1", 2, "urldownloadtofilea"),
             ("Module1", 9, "createobject"), ("Module1", 9, "wscript"), ("Module1", 10, "output"), ("Module1", 11, "kill"), ("Module1", 12, "vbproject"),
             ("Module1", 13, "saveas"), ("Module1", 14, "application.run"), ("Module1", 18, "auto_open")]:
    check(f"위험 코드 - {want}", want in got, True)
for nope in [("ThisWorkbook", 2, "kill"), ("Module1", 3, "createobject"), ("Module1", 5, "shell"), ("Module1", 16, "shell")]:
    check(f"위험 아님(주석·문자열 뒤·다른 개체 속성) - {nope}", nope in got, False)
check("Module1 6행 - 문자열 안 낱말은 위험 목록 낱말이면 고른다(Shell 은 낱말 경계 - 문자열 \"Shell 은\" 도 고름)", ("Module1", 6, "shell") in got, True)
check("한글에 붙은 Shell(가Shell)도 고른다 - 낱말 경계는 ASCII(두 곳 같게)", ("Module1", 15, "shell") in got, True)


# ---------------------------------------------------------------- 2. VBA 프로젝트 만들기(읽고 쓰기에 필요한 레코드만)
def rec(rid, b):
    return struct.pack("<H I", rid, 4 if rid == 0x0009 else len(b)) + b


def make_project(mods):
    cp = 949
    d = rec(0x0001, struct.pack("<I", 3)) + rec(0x0002, struct.pack("<I", 0x409)) + rec(0x0003, struct.pack("<H", cp)) + rec(0x0004, b"VBAProject")
    d += rec(0x000F, struct.pack("<H", len(mods))) + rec(0x0013, struct.pack("<H", 0xFFFF))
    streams = {}
    for m in mods:
        nm = m["name"].encode("cp949")
        d += rec(0x0019, nm) + rec(0x0047, m["name"].encode("utf-16-le")) + rec(0x001A, nm) + rec(0x0032, m["name"].encode("utf-16-le"))
        pcode = b"\x01\x02STALE-PCODE" * 4  # 성능 캐시(p-code) 자리 - 소스 앞에 둔다(오프셋)
        d += rec(0x0031, struct.pack("<I", len(pcode))) + rec(0x0021 if m["kind"] == "std" else 0x0022, b"") + rec(0x002B, b"")
        streams["VBA/" + m["name"]] = pcode + vba_project.compress(f'Attribute VB_Name = "{m["name"]}"\r\n{m["code"]}'.encode("cp949"))
    d += rec(0x0010, b"")
    streams["VBA/dir"] = vba_project.compress(d)
    streams["VBA/_VBA_PROJECT"] = bytes([0xCC, 0x61, 0xB2, 0x00, 0x00, 0x03, 0x00])  # 엑셀이 쓴 판(성능 캐시를 믿는다)
    streams["VBA/__SRP_0"] = b"STALE"
    streams["PROJECT"] = ("ID=\"{00000000-0000-0000-0000-000000000000}\"\r\n" + "".join(
        f"Module={m['name']}\r\n" if m["kind"] == "std" else f"Document={m['name']}/&H00000000\r\n" for m in mods) + "Name=\"VBAProject\"\r\n").encode("cp949")
    return vba_project.cfb_write(streams, ["VBA"])


T = Path(tempfile.mkdtemp(prefix="vbasafe-"))
WS = T / "ws"
mods = [{"name": "ThisWorkbook", "kind": "doc", "code": "Private Sub Workbook_Open()\r\nEnd Sub\r\n"}, {"name": "Module1", "kind": "std", "code": "Function Twice(x)\r\n    Twice = x * 2\r\nEnd Function\r\n"}]
binp = WS / "assets" / "sheets" / "zv" / "vbaProject.bin"
binp.parent.mkdir(parents=True, exist_ok=True)
binp.write_bytes(make_project(mods))
check("시험용 프로젝트를 다시 읽으면 같은 소스", [(m["name"], m["code"].strip()) for m in vba_project.read_modules(binp.read_bytes())], [(m["name"], m["code"].strip()) for m in mods])

(WS / "decks").mkdir(parents=True, exist_ok=True)
doc = {"id": "zv", "title": "VBA", "kind": "sheet", "slides": [], "macros": {"vba": "assets/sheets/zv/vbaProject.bin", "codeName": "ThisWorkbook", "modules": mods},
       "sheets": [{"id": "t01", "name": "S", "cells": {"A1": {"f": "=Twice(2)", "v": 4}}}]}
(WS / "decks" / "zv.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
env = {**os.environ, "NEXA_SLIDE_WORKSPACE": str(WS), "PYTHONIOENCODING": "utf-8"}


def export(*extra):
    r = subprocess.run([sys.executable, str(STUDIO / "export_xlsx.py"), "zv", *extra], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith(("xlsx:", "xlsm:"))]
    return Path(line[-1].split(":", 1)[1].strip()) if line else None, r.stdout + r.stderr


out, log = export()
check("매크로 문서 → .xlsm", out and out.suffix, ".xlsm")
if out and out.exists():
    data = zipfile.ZipFile(out).read("xl/vbaProject.bin")
    cf = vba_project.Cfb(data)
    check("고치지 않아도 소스로 다시 쓴다 - _VBA_PROJECT 판 0xFFFF(엑셀이 소스에서 다시 컴파일)", cf.streams.get("VBA/_VBA_PROJECT", b"")[2:4], b"\xff\xff")
    check("원본 성능 캐시(__SRP_)를 버린다", [p for p in cf.streams if "__SRP_" in p], [])
    check("모듈 스트림에 원본 p-code 가 남지 않는다", any(b"STALE-PCODE" in b for b in cf.streams.values()), False)
    check("다시 쓴 프로젝트의 소스 = 문서 소스", [(m["name"], m["code"].strip()) for m in vba_project.read_modules(data)], [(m["name"], m["code"].strip()) for m in mods])
check("내보내기 기록에 위험 매크로 알림(Workbook_Open)", "Workbook_Open" in log, True)
out2, log2 = export("--no-macros")
check("--no-macros → .xlsx", out2 and out2.suffix, ".xlsx")
if out2 and out2.exists():
    check("--no-macros - vbaProject.bin 없음", "xl/vbaProject.bin" in zipfile.ZipFile(out2).namelist(), False)

binp.write_bytes(b"broken")  # 깨진 프로젝트 - 원본(믿을 수 없는 p-code)을 넣지 않고 매크로를 뺀다
out3, log3 = export()
check("다시 쓰지 못하는 프로젝트 → 매크로 없이 .xlsx", out3 and out3.suffix, ".xlsx")

print(f"VBA 보안 {ok + len(fails)}개 중 {ok}개 통과")
print("\n실패:", ", ".join(fails) if fails else "없음")
sys.exit(1 if fails else 0)
