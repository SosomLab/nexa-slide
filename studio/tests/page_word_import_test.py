# -*- coding: utf-8 -*-
"""Word 가 만든 문서 가져오기(import_docx) - 우리 내보내기와의 왕복이 아니라 Word(COM)가 직접 저장한 .docx 를 옮겨 본다.
    python studio/tests/page_word_import_test.py [--strict]
- docx_make_word.ps1 이 만든 문서(제목 1·2 · 굵게·빨강·형광 · 글머리·번호 2단계 · 가로·세로 병합 표 · 그림 · 쪽 나누기 · 머리말 + 쪽 번호 · 각주 · 글 상자)를
  import_docx.read 로 읽어 블록 종류·스타일·목록·표 병합·그림 수·머리말·경고를 기대와 대조한다. 틀리면 그 부분의 원본 XML 조각을 같이 찍는다.
- Word 가 없거나 사용자가 Word 를 띄워 두었으면 판정 불가 - SKIP 줄을 남기고 0(--strict 면 99)."""
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
os.environ.setdefault("NEXA_SLIDE_WORKSPACE", str(STUDIO.parent / "example"))
import tmpfiles  # noqa: E402
import testlock  # noqa: E402,F401 - Word 를 띄우는 시험은 한 번에 하나
import import_docx  # noqa: E402

for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else str(extra)[:900])
    if not cond:
        FAILS.append(name)


def text(runs):
    return "".join(r.get("t", "") for r in runs or [])


def xml_around(doc_xml, needle, n=500):
    i = doc_xml.find(needle)
    return doc_xml[max(0, i - 200):i + n] if i >= 0 else f"(원본에 '{needle}' 없음)"


def main():
    pw = shutil.which("pwsh") or shutil.which("powershell")
    if os.name != "nt" or not pw:
        print("SKIP 판정 불가 - Windows·PowerShell 이 아님"); return 99
    with tmpfiles.temp_dir("nx-wimp-") as d:
        f = Path(d) / "word_made.docx"
        r = subprocess.run([pw, "-NoProfile", "-File", str(HERE / "docx_make_word.ps1"), "-Out", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        if r.returncode == 99:
            print("SKIP 판정 불가 -", r.stdout.strip()[-120:]); return 99
        check("Word 가 시험 문서를 만들었다(.docx)", r.returncode == 0 and f.is_file(), (r.returncode, (r.stdout + r.stderr)[-300:]))
        if not f.is_file():
            return 1
        data = f.read_bytes()
        with zipfile.ZipFile(f) as z:  # 닫아야 임시 폴더를 지운다
            dx = z.read("word/document.xml").decode("utf-8")
            hdrs = {n: z.read(n).decode("utf-8") for n in z.namelist() if re.match(r"word/header\d+\.xml", n)}
    doc, images, warns = import_docx.read(data, doc_id="wimp")
    bl = doc["blocks"]
    kinds = [b["type"] for b in bl]
    paras = [b for b in bl if b["type"] == "p"]
    rows = []

    def row(what, want, got, ok, xml=""):
        rows.append((what, want, got, "OK" if ok else "FAIL"))
        check(f"{what} - 기대 {want}", ok, f"실제 {got}" + (f"\n    원본 XML: {xml[:600]}" if xml and not ok else ""))

    h1 = next((b for b in paras if text(b.get("runs")) == "제목 하나"), {})
    h2 = next((b for b in paras if text(b.get("runs")) == "제목 둘"), {})
    row("제목 1 스타일", "h1", h1.get("style"), h1.get("style") == "h1", xml_around(dx, "제목 하나"))
    row("제목 2 스타일", "h2", h2.get("style"), h2.get("style") == "h2", xml_around(dx, "제목 둘"))
    fmt = next((b for b in paras if "굵게" in text(b.get("runs"))), {})
    runs = fmt.get("runs") or []
    bold = any(x.get("b") and "굵게" in x.get("t", "") for x in runs)
    red = any(str(x.get("c", "")).lower() in ("#ff0000", "ff0000") and "빨강" in x.get("t", "") for x in runs)
    hl = any(x.get("hl") and "형광" in x.get("t", "") for x in runs)
    row("글자 서식(굵게·빨강·형광)", "b · c #FF0000 · hl", json.dumps(runs, ensure_ascii=False)[:200], bold and red and hl, xml_around(dx, "굵게"))
    lst = [(text(b.get("runs")), (b.get("list") or {}).get("kind"), (b.get("list") or {}).get("level")) for b in paras if b.get("list")]
    # 단계는 원본 XML 의 ilvl 과 같아야 한다(이 PC 의 Word 자동화는 기본 글머리·번호에서 2단계를 만들지 못하고 ilvl 0 + 들여쓰기로 저장한다 - 그래서 기대를 원본에서 읽는다)
    src_lv = {}
    for m in re.finditer(r'<w:p\b(?:(?!</w:p>).)*?<w:ilvl w:val="(\d+)"/>(?:(?!</w:p>).)*?<w:t>([^<]*)</w:t>', dx):
        src_lv.setdefault(m.group(2), int(m.group(1)))
    want = [("글머리 하나", "bullet", src_lv.get("글머리 하나")), ("글머리 둘째 단계", "bullet", src_lv.get("글머리 둘째 단계")),
            ("번호 하나", "number", src_lv.get("번호 하나")), ("번호 둘째 단계", "number", src_lv.get("번호 둘째 단계"))]
    row("목록 kind · level(= 원본 ilvl)", want, lst, lst == want, xml_around(dx, "글머리 하나", 900))
    if all(w_[2] == 0 for w_ in want):
        print("  참고: Word 원본의 목록이 모두 ilvl 0 이다 - 2단계 목록 옮기기는 이 문서로는 확인하지 못함(미확인)")
    tb = next((b for b in bl if b["type"] == "table"), {})
    tr = tb.get("rows") or []
    spans = [[(c.get("colspan", 1), c.get("rowspan", 1)) for c in r_.get("cells") or []] for r_ in tr]
    ok_t = len(tr) == 3 and spans and spans[0][0][0] == 2 and len(spans[0]) == 2 and any(c[1] == 2 for c in spans[1]) and len(spans[2]) == 2
    row("표 3×3 · 가로 병합(1행 colspan 2) · 세로 병합(2행 rowspan 2, 3행 칸 2개)", "colspan 2 · rowspan 2", spans, ok_t, xml_around(dx, "칸11", 1200))
    nimg = sum(1 for b in bl if b["type"] == "image")
    row("그림 수", 1, f"{nimg} (꺼낸 파일 {len(images)})", nimg == 1 and len(images) == 1, xml_around(dx, "<w:drawing", 300))
    row("쪽 나누기", "break 1", kinds.count("break"), kinds.count("break") >= 1, xml_around(dx, 'w:type="page"', 200))
    hd = text(((doc.get("page") or {}).get("header") or {}).get("blocks", [{}])[0].get("runs") if ((doc.get("page") or {}).get("header") or {}).get("blocks") else [])
    num = (doc.get("page") or {}).get("number") or {}
    row("머리말 글", "머리말 글", hd, "머리말 글" in hd, next(iter(hdrs.values()), "")[:600])
    row("쪽 번호(머리말 필드)", "number.show 또는 경고", json.dumps(num, ensure_ascii=False), bool(num.get("show")) or any("쪽 번호" in w for w in warns), next(iter(hdrs.values()), "")[:600])
    wtxt = " | ".join(warns)
    box = [text(b.get("runs")) for b in paras if "글 상자 글" in text(b.get("runs"))]
    row("글 상자의 글 - 문단으로 옮겨짐(한 번만)", "1개", len(box), len(box) == 1, xml_around(dx, "상자 글", 300))
    row("경고 - 각주", "경고에 각주", wtxt[:200], "각주" in wtxt)
    row("경고 - 글 상자·떠 있는 개체", "경고에 글 상자/떠 있는", wtxt[:200], bool(re.search("글 상자|떠 있는|도형|개체", wtxt)))
    row("문단 글 보존(각주 붙는 문단·둘째 쪽)", "둘 다", [text(b.get("runs")) for b in paras if "각주" in text(b.get("runs")) or "둘째 쪽" in text(b.get("runs"))],
        any("각주가 붙는 문단" in text(b.get("runs")) for b in paras) and any("둘째 쪽 문단" == text(b.get("runs")) for b in paras))
    print("\n블록 종류:", " ".join(kinds))
    print("경고:", wtxt or "(없음)")
    print("\n| 항목 | 기대 | 실제 | 결과 |\n|---|---|---|---|")
    for w_, a, g, o in rows:
        print(f"| {w_} | {str(a)[:60]} | {str(g)[:90]} | {o} |")
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc if rc != 99 or "--strict" in sys.argv else 0)
