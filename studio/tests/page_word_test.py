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


SHADES = {}  # 문서 이름 → Word 에서 음영이 있는 문단 [{n, c, t}]
BORDERS = {}  # 문서 이름 → Word 표마다 테두리 선 종류(docx_open_check.ps1)


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
    for bd in ("none", "inner-v"):  # 배치용 표(합치지 않은 1×2) - Word 의 표 테두리 선 종류를 본다
        d_ = page_doc.new_page(f"wbd{bd.replace('-', '')}", f"배치용 표 {bd}")
        d_["blocks"] = [{"id": "t", "type": "table", "cols": [67, 33], "border": bd, "rows": [{"head": True, "cells": [{"blocks": [{"type": "p", "runs": [{"t": "왼쪽"}]}]}, {"blocks": [{"type": "p", "runs": [{"t": "오른쪽"}]}]}]},
                                                                                         {"cells": [{"blocks": [{"type": "p", "runs": [{"t": "아래"}]}]}, {"blocks": []}]}]}]
        docs.append((f"배치용 표 {bd}", d_, None))
    d_ = page_doc.new_page("wobj", "도형 문서")  # 개체(PG-103) - 글 상자 · 타원(글 뒤) · 화살표 · 중괄호, 둘째 문단은 문단 기준
    d_["blocks"] = [{"id": "p1", "type": "p", "runs": [{"t": "도형이 매인 문단"}]}, {"id": "p2", "type": "p", "runs": [{"t": "둘째 문단"}]}]
    d_["objects"] = [{"id": "o1", "type": "shape", "shape": "rect", "anchor": "p1", "rel": "page", "x": 30, "y": 40, "w": 60, "h": 25, "blocks": [{"id": "ob1", "type": "p", "runs": [{"t": "상자 글"}]}]},
                     {"id": "o2", "type": "shape", "shape": "ellipse", "anchor": "p1", "rel": "page", "x": 100, "y": 40, "w": 40, "h": 25, "fill": "#eeeeee", "z": "behind"},
                     {"id": "o3", "type": "shape", "shape": "arrow", "anchor": "p2", "rel": "para", "x": 10, "y": 5, "w": 50, "h": 0},
                     {"id": "o4", "type": "shape", "shape": "brace-l", "anchor": "p2", "rel": "para", "x": 70, "y": 0, "w": 6, "h": 20}]
    docs.append(("도형 문서", d_, None))
    d_ = page_doc.new_page("wcols", "다단 문서")  # 다단(PG-101) - 2단 → 구역 나누기(1단)
    d_["page"]["columns"] = {"count": 2, "gap": 8}
    d_["blocks"] = [{"id": f"c{k}", "type": "p", "runs": [{"t": f"2단 문단 {k} " + "가나다라마바사 " * 8}]} for k in range(6)] + \
        [{"id": "sb", "type": "break", "kind": "section", "columns": {"count": 1}}] + [{"id": f"d{k}", "type": "p", "runs": [{"t": f"1단 문단 {k}"}]} for k in range(3)]
    docs.append(("다단 문서", d_, None))
    d_ = page_doc.new_page("wfn", "각주 문서")  # 각주(PG-105) - 본문 2개 · 표 칸 1개
    d_["blocks"] = [{"id": "f1", "type": "p", "runs": [{"t": "각주가 붙는 "}, {"t": "글", "fn": "첫 각주"}]}, {"id": "f2", "type": "p", "runs": [{"t": "둘째"}, {"t": "끝", "fn": "둘째 각주"}]},
                    {"id": "ft", "type": "table", "cols": [50, 50], "rows": [{"cells": [{"blocks": [{"type": "p", "runs": [{"t": "칸"}, {"t": "글", "fn": "칸 각주"}]}]}, {"blocks": [{"type": "p", "runs": [{"t": "둘"}]}]}]}]}]
    docs.append(("각주 문서", d_, None))
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
            if name == "다단 문서":
                check(f"{name} - Word 구역 2개 · 단 수 [2, 1]", j.get("sections") == 2 and list(j.get("cols") or []) == [2, 1], json.dumps({k: j.get(k) for k in ("sections", "cols")}, ensure_ascii=False))
            if name == "각주 문서":
                check(f"{name} - Word 각주(Footnotes) 수 = 3", j.get("footnotes") == 3, json.dumps({k: j.get(k) for k in ("footnotes",)}, ensure_ascii=False))
            if doc.get("objects"):
                check(f"{name} - Word 의 떠 있는 도형(Shapes) 수 = 개체 수 {len(doc['objects'])}", j.get("shapes") == len(doc["objects"]), json.dumps({k: j.get(k) for k in ("shapes", "inlineShapes")}, ensure_ascii=False))
            BORDERS[name] = j.get("borders")
            SHADES[name] = j.get("shades") or []
            check(f"{name} - Word 가 연다(읽을 수 없는 내용 없음)", rc == 0 and j.get("ok"), json.dumps(j, ensure_ascii=False))
            check(f"{name} - 표 {want_tables}개 · 머리말 '{want_head[:20]}'", j.get("tables") == want_tables and (j.get("header") or "").strip() == want_head, json.dumps({k: j.get(k) for k in ("tables", "header")}, ensure_ascii=False))
        BD = {name: j_ for name, j_ in BORDERS.items()}
        nb, iv, sgb = ((BD.get(k) or [{}])[0] for k in ("배치용 표 none", "배치용 표 inner-v", "study-guide"))
        def cells_of(b):  # "행,열:T L B R" → {(행, 열): (T, L, B, R)}
            out = {}
            for x in (b or {}).get("cells") or []:
                rc, v = x.split(":"); r_, c_ = map(int, rc.split(",")); out[(r_, c_)] = tuple(int(n) for n in v.split())
            return out

        def inner_v(b):  # 칸 위·아래 선 없음 · 첫 칸 왼쪽·끝 칸 오른쪽 없음 · 칸 사이(왼쪽 칸의 오른쪽 또는 오른쪽 칸의 왼쪽)에 선
            cs = cells_of(b)
            if not cs:
                return False
            last = max(c for _, c in cs)
            return all(t == 0 and bt == 0 and (c > 1 or l == 0) and (c < last or rt == 0) and (c == 1 or l != 0 or cs.get((r, c - 1), (0, 0, 0, 0))[3] != 0) for (r, c), (t, l, bt, rt) in cs.items())
        check("배치용 표 none - Word 에서 칸마다 선이 하나도 없음(위·왼쪽·아래·오른쪽 LineStyle 0)", bool(cells_of(nb)) and all(v == (0, 0, 0, 0) for v in cells_of(nb).values()), json.dumps(nb, ensure_ascii=False)[:400])
        check("배치용 표 inner-v - Word 에서 칸 사이 세로선만(바깥·가로 선 없음)", inner_v(iv), json.dumps(iv, ensure_ascii=False)[:400])
        check("study-guide 의 2단 표 - Word 에서 칸 사이 세로선만", inner_v(sgb), json.dumps(sgb, ensure_ascii=False)[:400])
        # 빈 칸의 문단 = 1개(빈 칸 내용이 <w:p/> 인데 하나를 더 붙이던 결함 - bb88ff0)
        import re as _re2, zipfile as _zf, io as _io  # noqa: E401
        nd = next(x for x in docs if x[0] == "배치용 표 none")[1]
        dx = _zf.ZipFile(_io.BytesIO(export_docx.build(nd))).read("word/document.xml").decode("utf-8")
        tcs = _re2.findall(r"<w:tc>(.*?)</w:tc>", dx)
        np_ = [len(_re2.findall(r"<w:p[ />]", tc)) for tc in tcs]
        check("빈 칸의 문단 수 = 1(document.xml 의 tc 마다 w:p 1개 · 2,2 칸은 빈 칸)", len(tcs) == 4 and all(n == 1 for n in np_), json.dumps(np_))
        sh = SHADES.get("study-guide") or []
        print("  study-guide 음영 문단:", json.dumps(sh, ensure_ascii=False)[:300])
        check("study-guide - Word 에서 회색 상자 문단(흐름 설명·어휘) 음영이 있음(BackgroundPatternColor 회색 계열)", len(sh) >= 2 and all(len(set((x["c"][0:2], x["c"][2:4], x["c"][4:6]))) == 1 and x["c"] != "FFFFFF" for x in sh), json.dumps(sh, ensure_ascii=False)[:300])
        cs_ = SHADES.get("종합(page_docx_test)") or []
        print("  종합 문서 음영 문단:", json.dumps(cs_, ensure_ascii=False)[:200])
        sg = next((r for r in ROWS if r["문서"] == "study-guide"), None)
        check("study-guide(해설지 2단) - Word 에서 1쪽 · 머리말에 날짜(YYYY-MM-DD)와 제목 · 자리 글 없음", sg and sg["쪽"] == 1 and __import__("re").search(r"\d{4}-\d{2}-\d{2}", sg["머리말"] or "") and "study-guide 시험" in (sg["머리말"] or "") and "{" not in (sg["머리말"] or ""),
              json.dumps(sg, ensure_ascii=False))
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
