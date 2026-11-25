# -*- coding: utf-8 -*-
"""페이지 DOCX 를 Word 로 실제 열어 본다(PG-062) - 템플릿 11종 + page_docx_test 의 종합 문서. Windows + Word 가 있을 때만.
    python studio/tests/page_word_test.py
- 문서마다 export_docx.build → 파일 → docx_open_check.ps1(매크로 끔 · 읽기 전용 · 우리 Word 만 끝냄)로 쪽·문단·표·머리말·꼬리말·목록 번호 글·제목 크기를 받아
  문서 모델과 대조한다: 열림(Word 가 읽을 수 없는 내용이라고 하지 않음) · 표 수 = table 블록 수 · 머리말 글 = page.header 글.
- 종합 문서는 render_docx.ps1 로 PDF 도 만든다(파일 생김 · 우리가 띄운 WINWORD 가 남지 않음).
- Word 가 없거나 사용자가 Word 를 띄워 두었으면 판정 불가로 99(run_all·verify 의 SKIP)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
os.environ.setdefault("NEXA_SLIDE_WORKSPACE", str(STUDIO.parent / "example"))
import tmpfiles  # noqa: E402
import testlock  # noqa: E402,F401 - Word 를 띄우는 시험은 한 번에 하나
import export_docx  # noqa: E402
import page_doc  # noqa: E402
import page_templates  # noqa: E402

for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
FAILS, ROWS = [], []
PWSH = shutil.which("pwsh") or shutil.which("powershell")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else str(extra)[:700])
    if not cond:
        FAILS.append(name)


def word_procs():
    if os.name != "nt":
        return set()
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return {l.split(",")[1].strip('"') for l in out.splitlines() if l.startswith('"WINWORD')}


def open_check(path):
    r = subprocess.run([PWSH, "-NoProfile", "-File", str(HERE / "docx_open_check.ps1"), "-Docx", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    try:
        return r.returncode, json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return r.returncode, {"raw": (r.stdout + r.stderr)[-400:]}


def text_of(blocks):
    return " ".join("".join(x.get("t", "") for x in b.get("runs") or []) for b in blocks or []).strip()


def count_tables(blocks):
    n = 0
    for b in blocks or []:
        if b.get("type") == "table":
            n += 1
            for row in b.get("rows") or []:
                for c in row.get("cells") or []:
                    n += count_tables(c.get("blocks"))
    return n


def main():
    if os.name != "nt" or not PWSH:
        print("SKIP 판정 불가 - Windows·PowerShell 이 아님"); return 99
    if word_procs():
        print("SKIP 판정 불가 - 사용자 Word 가 실행 중(건드리지 않는다)"); return 99
    docs = []
    for name in page_templates.names():
        t = page_templates.load(name, title=f"{name} 시험")
        docs.append((name, page_doc.new_page(f"w{name.replace('-', '')}", f"{name} 시험", template=t), None))
    # 종합 문서(서식 전부·표 병합·그림·윗주·링크) - 그 시험의 doc·그림 그대로(그 시험은 끝에서 sys.exit 하므로 전역을 직접 받는다)
    src = HERE / "page_docx_test.py"
    g = {"__name__": "page_docx_for_word", "__file__": str(src)}
    try:
        exec(compile(src.read_text(encoding="utf-8"), str(src), "exec"), g)
    except SystemExit:
        pass
    docs.append(("종합(page_docx_test)", g["doc"], {"assets/a.png": (g["png"](4, 2), 400, 200)}))
    with tmpfiles.temp_dir("nx-word-") as d:
        for name, doc, images in docs:
            f = Path(d) / f"{name.split('(')[0]}.docx"
            f.write_bytes(export_docx.build(doc, images=images))
            rc, j = open_check(f)
            if rc == 99:
                print(f"SKIP 판정 불가 - {j.get('skip')}"); return 99
            want_tables, want_head = count_tables(doc.get("blocks")), text_of(((doc.get("page") or {}).get("header") or {}).get("blocks"))
            row = {"문서": name, "열림": j.get("ok"), "쪽": j.get("pages"), "문단": j.get("paragraphs"), "표": j.get("tables"), "머리말": j.get("header"), "꼬리말": j.get("footer"),
                   "목록": " ".join(x["s"] for x in j.get("lists") or [])[:80], "제목": " ".join(f"{h['style']}={h['size']}" for h in (j.get("heads") or [])[:3]), "오류": j.get("error") or ""}
            ROWS.append(row)
            check(f"{name} - Word 가 연다(읽을 수 없는 내용 없음)", rc == 0 and j.get("ok"), json.dumps(j, ensure_ascii=False))
            check(f"{name} - 표 {want_tables}개 · 머리말 '{want_head[:20]}'", j.get("tables") == want_tables and (j.get("header") or "").strip() == want_head, json.dumps({k: j.get(k) for k in ("tables", "header")}, ensure_ascii=False))
        # 종합 문서의 번호 목록 - 1. 2. (a.) · 사이 문단 뒤 이어 가는지 / 다시 시작하는지는 보고만
        comp = next(r for r in ROWS if r["문서"].startswith("종합"))
        print("  종합 문서 목록 번호 글:", comp["목록"])
        # PDF - render_docx.ps1
        before = word_procs()
        f = Path(d) / "종합.docx"
        pdf = Path(d) / "종합.pdf"
        r = subprocess.run([PWSH, "-NoProfile", "-File", str(STUDIO / "render_docx.ps1"), "-Docx", str(f), "-Pdf", str(pdf)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        after = word_procs()
        check("render_docx.ps1 - PDF 파일 생김 · 우리가 띄운 WINWORD 가 남지 않음", r.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 1000 and after <= before,
              json.dumps({"rc": r.returncode, "out": (r.stdout + r.stderr)[-300:], "before": sorted(before), "after": sorted(after)}, ensure_ascii=False))
        print("  render_docx 출력:", (r.stdout or "").strip()[-200:])
    print("\n| 문서 | 열림 | 쪽 | 문단 | 표 | 머리말 | 꼬리말 | 목록 번호 글 | 제목 크기 | 오류 |\n|---|---|---|---|---|---|---|---|---|---|")
    for x in ROWS:
        print("| " + " | ".join(str(x[k]) for k in ("문서", "열림", "쪽", "문단", "표", "머리말", "꼬리말", "목록", "제목", "오류")) + " |")
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    rc = main()
    # run_all 은 0 이 아니면 실패로 센다 - 판정 불가(Word 없음·사용자 Word 실행 중)는 SKIP 줄만 남기고 0. 직접 돌릴 때는 --strict 로 99 를 그대로
    sys.exit(rc if rc != 99 or "--strict" in sys.argv else 0)
