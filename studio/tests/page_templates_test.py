# -*- coding: utf-8 -*-
"""page_templates.py 시험 - 모든 템플릿이 페이지 문서로 만들어지고 형식을 통과하며 DOCX 로 나가는지.  python studio/tests/page_templates_test.py"""
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_docx as X  # noqa: E402
import page_doc as P  # noqa: E402
import page_templates as PT  # noqa: E402

fails, n = [], 0


def check(name, ok, got=None):
    global n
    n += 1
    if not ok:
        fails.append(name)
        print(f"FAIL {name}" + (f" - {got!r}" if got is not None else ""))


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
names = PT.names()
check("템플릿 11종", len(names) == 11 and names[0] == "blank", names)
inf = PT.info()
check("목록 - 이름·설명·묶음", all(x["label"] and x["desc"] and x["group"] in PT.GROUPS for x in inf) and sum(x["group"] == "study" for x in inf) == 3, [(x["name"], x["group"]) for x in inf])
check("없는 이름은 None", PT.load("nope") is None)
for name in names:
    t = PT.load(name, "시험 제목", "2026-11-26")
    doc = P.new_page("d-" + name, "시험 제목", t)
    e = P.validate(doc)
    check(f"{name} - 형식 통과", e is None, e)
    text = json.dumps(doc, ensure_ascii=False)
    check(f"{name} - 자리 채움({{title}}·{{date}} 가 남지 않음)", "{title}" not in text and "{date}" not in text)
    check(f"{name} - 템플릿 이름 기록·id 겹침 없음", doc.get("template") == name and len({b['id'] for _, b in P.walk(doc)}) == len(list(P.walk(doc))))
    for st in {b.get("style") for _, b in P.walk(doc) if b.get("style")}:
        check(f"{name} - 스타일 {st} 가 있다", st in doc["styles"])
    try:
        z = zipfile.ZipFile(io.BytesIO(X.build(doc)))
        ET.fromstring(z.read("word/document.xml")); ET.fromstring(z.read("word/styles.xml"))
        check(f"{name} - DOCX 로 나간다", True)
    except Exception as ex:  # noqa: BLE001
        check(f"{name} - DOCX 로 나간다", False, str(ex))
    if name != "blank":
        check(f"{name} - 제목 자리에 제목이 들어간다(또는 이름 자리)", "시험 제목" in text or name == "resume", None)
src = json.dumps(PT.T, ensure_ascii=False)
check("템플릿 원본은 load 로 바뀌지 않는다", "{title}" in src)
check("로고·글꼴 파일을 가리키지 않는다", not any(x in src for x in (".ttf", ".otf", ".woff", "logo")))

print(f"\n실패 {len(fails)}" if fails else f"\n전부 통과 ({n}사례)")
sys.exit(1 if fails else 0)
