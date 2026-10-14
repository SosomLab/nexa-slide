# -*- coding: utf-8 -*-
"""첨부 문서 내용 추출 - Word(.docx)·Excel(.xlsx/.xlsm)·PDF 에서 글·표·그림을 Markdown·JSON 으로 꺼낸다(PPTX 는 import_pptx).

    python3 nexa.py import_doc <파일> [--out <폴더>] [--no-images] [--json] [--max-rows N]
    → <폴더>/content.md      읽기용 - Word: 제목(수준)·문단(굵게 **…**)·목록(수준)·표·그림 / Excel: 시트별 표(값, 수식은 json)·병합·차트 값 / PDF: 쪽별 글·표
      <폴더>/content.json    같은 내용의 구조
      <폴더>/images/…        그림(Word·PDF). 덱 image 요소의 src 에 이 경로를 그대로 쓴다
    기본 폴더: out/import/<파일 이름>/ (산출물 폴더, git 제외). 입력 파일과 --out 은 작업 공간 안(저장소 루트 접근 세션이면 그 루트까지).

    python3 nexa.py import_doc --selftest [--out <폴더>]   # 견본 docx·xlsx(·pdf)를 만들어 추출을 확인

Word·Excel 은 표준 라이브러리(zip + XML)로 읽는다 - 추가 설치 없음. PDF 는 PyMuPDF(`pip install pymupdf`)가 있으면 글·표·그림을,
없고 pypdf 가 있으면 글만 꺼낸다. 옛 형식(.doc·.xls)은 Word·Excel 에서 .docx·.xlsx 로 저장해 다시 올린다.
문서를 덱으로 자동 변환하지는 않는다 - 세션이 content.md 를 읽고 slide_types·layout_samples 로 장을 고른다.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT  # noqa: E402
from import_pptx import _allowed_roots, _inside, _rel  # noqa: E402 - 같은 경로 제한·상대 경로 표기

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
MAX_ROWS, MAX_COLS, MAX_CELL = 300, 40, 300  # Excel 시트마다 md 에 싣는 범위(json 은 MAX_ROWS 까지 같음) · 칸 글자 수


def _rels(z, part):
    """part 의 관계 {rId: 대상 경로(zip 안)}."""
    p = PurePosixPath(part)
    rp = str(p.parent / "_rels" / (p.name + ".rels"))
    if rp not in z.namelist():
        return {}
    out = {}
    for r in ET.fromstring(z.read(rp)).iter(PR + "Relationship"):
        t = r.get("Target", "")
        if r.get("TargetMode") == "External":
            continue
        out[r.get("Id")] = str(PurePosixPath(t.lstrip("/"))) if t.startswith("/") else _norm(p.parent / t)
    return out


def _norm(p):
    parts = []
    for x in PurePosixPath(p).parts:
        if x == "..":
            parts and parts.pop()
        elif x != ".":
            parts.append(x)
    return "/".join(parts)


class _Images:
    """그림 저장 - 같은 내용은 한 번만. 이름은 <접두>-<n>.<확장자>."""

    def __init__(self, out_dir, save=True):
        self.dir, self.save, self.seen, self.n, self.saved = Path(out_dir) / "images", save, {}, 0, 0

    def put(self, blob, ext, prefix="img"):
        h = hashlib.sha1(blob).hexdigest()
        if h in self.seen:
            return self.seen[h]
        self.n += 1
        name = f"{prefix}-{self.n:02d}.{ext.lower().lstrip('.') or 'bin'}"
        path = self.dir / name
        if self.save:
            self.dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            self.saved += 1
        self.seen[h] = _rel(path)
        return self.seen[h]


def _cell_md(t):
    t = " ".join(str(t if t is not None else "").split())
    return (t[:MAX_CELL] + "…" if len(t) > MAX_CELL else t).replace("|", "\\|")


def _table_md(rows):
    if not rows:
        return []
    n = max(len(r) for r in rows)
    rows = [list(r) + [""] * (n - len(r)) for r in rows]
    out = ["| " + " | ".join(_cell_md(c) for c in rows[0]) + " |", "|" + "---|" * n]
    out += ["| " + " | ".join(_cell_md(c) for c in r) + " |" for r in rows[1:]]
    return out


# ---------- Word ----------
def _docx_styles(z):
    """styleId → 제목 수준(1~9) - 이름이 heading N·제목 N·Title 인 스타일."""
    out = {}
    if "word/styles.xml" not in z.namelist():
        return out
    for st in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
        sid, nm = st.get(W + "styleId"), st.find(W + "name")
        name = (nm.get(W + "val") if nm is not None else sid or "").lower()
        m = re.match(r"^(heading|제목)\s*(\d)$", name) or re.match(r"^(heading|제목)(\d)$", (sid or "").lower())
        if m:
            out[sid] = int(m.group(2))
        elif name == "title":
            out[sid] = 0
    return out


def _runs(p, imgs, rels, z):
    """문단의 글(굵게 **…**)과 그림 경로."""
    parts, pics = [], []
    for r in p.iter():
        if r.tag == W + "r":
            bold = r.find(W + "rPr/" + W + "b")
            on = bold is not None and bold.get(W + "val", "true") not in ("0", "false")
            t = "".join(x.text or "" if x.tag == W + "t" else "\t" if x.tag == W + "tab" else "\n" if x.tag in (W + "br", W + "cr") else ""
                        for x in r)
            if t:
                parts.append(f"**{t.strip()}**" if on and t.strip() else t)
        elif r.tag == A + "blip":
            target = rels.get(r.get(R + "embed"))
            if target and target in z.namelist():
                pics.append(imgs.put(z.read(target), PurePosixPath(target).suffix, "word"))
    txt = re.sub(r"\*\*\*\*", "", "".join(parts))
    return txt.strip(), pics


def read_docx(src, imgs):
    z = zipfile.ZipFile(src)
    if "word/document.xml" not in z.namelist():
        raise ValueError("word/document.xml 이 없다 - Word 문서가 아니다")
    styles, rels = _docx_styles(z), _rels(z, "word/document.xml")
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    blocks = []

    def para(p):
        txt, pics = _runs(p, imgs, rels, z)
        ppr = p.find(W + "pPr")
        sid = ppr.find(W + "pStyle").get(W + "val") if ppr is not None and ppr.find(W + "pStyle") is not None else None
        num = ppr.find(W + "numPr") if ppr is not None else None
        b = {"kind": "p", "text": txt}
        if sid in styles:
            b = {"kind": "heading", "level": styles[sid], "text": txt.replace("**", "")}
        elif num is not None:
            lv = num.find(W + "ilvl")
            b = {"kind": "li", "level": int(lv.get(W + "val", "0")) if lv is not None else 0, "text": txt}
        if pics:
            b["images"] = pics
        return b if (txt or pics) else None

    def table(t):
        rows = []
        for tr in t.findall(W + "tr"):
            row = []
            for tc in tr.findall(W + "tc"):
                txt = " / ".join(x for x in (_runs(p, imgs, rels, z)[0] for p in tc.iter(W + "p")) if x)
                row.append(txt)
                span = tc.find(W + "tcPr/" + W + "gridSpan")
                row += [""] * (int(span.get(W + "val", "1")) - 1 if span is not None else 0)
            rows.append(row)
        return {"kind": "table", "rows": rows}

    for el in list(body) if body is not None else []:
        if el.tag == W + "p":
            b = para(el)
            if b:
                blocks.append(b)
        elif el.tag == W + "tbl":
            blocks.append(table(el))
        elif el.tag == W + "sdt":  # 내용 컨트롤(목차 등) 안의 문단
            for p in el.iter(W + "p"):
                b = para(p)
                if b:
                    blocks.append(b)
    notes = []
    for part, tag in (("word/footnotes.xml", "footnote"), ("word/endnotes.xml", "endnote")):
        if part in z.namelist():
            for fn in ET.fromstring(z.read(part)).iter(W + tag):
                if int(fn.get(W + "id", "0")) > 0:
                    t = " ".join(x for x in ("".join(t.text or "" for t in p.iter(W + "t")) for p in fn.iter(W + "p")) if x.strip())
                    if t.strip():
                        notes.append({"id": fn.get(W + "id"), "kind": tag, "text": t.strip()})
    return {"type": "docx", "blocks": blocks, "notes": notes}


def md_docx(doc):
    L = []
    for b in doc["blocks"]:
        if b["kind"] == "heading":
            L += ["", "#" * min(6, max(1, b["level"] + 1)) + " " + b["text"], ""]
        elif b["kind"] == "li":
            L.append("  " * b["level"] + "- " + b["text"])
        elif b["kind"] == "table":
            L += [""] + _table_md(b["rows"]) + [""]
        elif b["text"]:
            L += [b["text"], ""]
        for im in b.get("images", []):
            L.append(f"![그림]({im})")
    if doc["notes"]:
        L += ["", "## 각주·미주", ""] + [f"- [{n['id']}] {n['text']}" for n in doc["notes"]]
    return L


# ---------- Excel ----------
_DATE_IDS = set(range(14, 23)) | {45, 46, 47}


def _col(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref or "")
    if not m:
        return None, None
    c = 0
    for ch in m.group(1):
        c = c * 26 + ord(ch) - 64
    return c - 1, int(m.group(2)) - 1


def _colname(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def read_xlsx(src, imgs, max_rows=MAX_ROWS):
    z = zipfile.ZipFile(src)
    if "xl/workbook.xml" not in z.namelist():
        raise ValueError("xl/workbook.xml 이 없다 - Excel 통합 문서가 아니다")
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(S + "si"):
            ss.append("".join(t.text or "" for t in si.iter(S + "t")))
    date_styles = set()
    if "xl/styles.xml" in z.namelist():
        st = ET.fromstring(z.read("xl/styles.xml"))
        custom = {int(n.get("numFmtId")) for n in st.iter(S + "numFmt") if re.search(r"[ymd]", re.sub(r'"[^"]*"|\[[^\]]*\]', "", n.get("formatCode", "").lower()))}
        xfs = st.find(S + "cellXfs")
        for i, xf in enumerate(xfs.findall(S + "xf") if xfs is not None else []):
            nid = int(xf.get("numFmtId", "0"))
            if nid in _DATE_IDS or nid in custom:
                date_styles.add(i)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    date1904 = (wb.find(S + "workbookPr") is not None and wb.find(S + "workbookPr").get("date1904") in ("1", "true"))
    rels = _rels(z, "xl/workbook.xml")
    names = [{"name": n.get("name"), "ref": n.text} for n in wb.iter(S + "definedName")][:50]
    sheets, books = [], {}
    for sh in wb.iter(S + "sheet"):
        part = rels.get(sh.get(R + "id"))
        if not part or part not in z.namelist():
            continue
        x = ET.fromstring(z.read(part))
        cells, formulas = {}, {}
        for c in x.iter(S + "c"):
            ci, ri = _col(c.get("r"))
            if ci is None or ri >= max_rows or ci >= MAX_COLS:
                continue
            t, v, f = c.get("t"), c.find(S + "v"), c.find(S + "f")
            val = v.text if v is not None else None
            if t == "s" and val is not None:
                val = ss[int(val)] if int(val) < len(ss) else ""
            elif t == "inlineStr":
                val = "".join(tt.text or "" for tt in c.iter(S + "t"))
            elif t == "b":
                val = "TRUE" if val == "1" else "FALSE"
            elif val is not None and t in (None, "n") and int(c.get("s", "0")) in date_styles:
                try:
                    d = dt.datetime(1904 if date1904 else 1899, 1 if date1904 else 12, 1 if date1904 else 30) + dt.timedelta(days=float(val))
                    val = d.strftime("%Y-%m-%d") if d.time() == dt.time(0) else d.strftime("%Y-%m-%d %H:%M")
                except (ValueError, OverflowError):
                    pass
            elif val is not None and t in (None, "n"):
                try:
                    fv = float(val)
                    val = str(int(fv)) if fv.is_integer() and abs(fv) < 1e15 else repr(round(fv, 10)).rstrip("0").rstrip(".") if "e" not in repr(fv) else val
                except ValueError:
                    pass
            if f is not None and (f.text or f.get("t") == "shared"):
                formulas[c.get("r")] = "=" + (f.text or f"(공유 수식 {f.get('si')})")
                if val in (None, ""):  # 계산값을 저장하지 않은 파일(Excel 이 아닌 도구로 만든 것) - 수식을 그대로 보인다
                    val = formulas[c.get("r")]
            if val not in (None, ""):
                cells[(ri, ci)] = val
        dim = x.find(S + "dimension")
        merges = [m.get("ref") for m in x.iter(S + "mergeCell")]
        rows = []
        if cells:
            r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
            c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
            rows = [[cells.get((r, c), "") for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
            origin = f"{_colname(c0)}{r0 + 1}"
        else:
            origin = "A1"
        charts = _xlsx_charts(z, part)
        books[sh.get("name")] = cells
        sheets.append({"name": sh.get("name"), "hidden": sh.get("state") in ("hidden", "veryHidden"), "dimension": dim.get("ref") if dim is not None else None,
                       "origin": origin, "rows": rows, "formulas": dict(list(formulas.items())[:500]), "merged": merges[:200], "charts": charts,
                       "truncated": bool(dim is not None and _col((dim.get("ref") or "A1").split(":")[-1])[1] is not None
                                         and (_col((dim.get("ref") or "A1").split(":")[-1])[1] >= max_rows or _col((dim.get("ref") or "A1").split(":")[-1])[0] >= MAX_COLS))})
    for s in sheets:  # 차트 계열에 캐시 값이 없으면 참조(시트!$B$2:$B$3)를 읽은 셀에서 찾는다
        for ch in s["charts"]:
            for se in ch["series"]:
                for k in ("name", "categories", "values"):
                    ref = se.pop(k + "Ref", None)
                    if ref and not se[k]:
                        got = _resolve(ref, books, s["name"])
                        se[k] = (got[0] if got else "") if k == "name" else got
    return {"type": "xlsx", "sheets": sheets, "names": names}


def _resolve(ref, books, cur):
    """'시트'!$B$2:$B$3 → 그 범위의 값 목록(읽은 행·열 안에서)."""
    m = re.match(r"^(?:'?(.+?)'?!)?\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?$", (ref or "").strip())
    if not m:
        return []
    cells = books.get(m.group(1) or cur, {})
    c0, r0 = _col(m.group(2) + m.group(3))
    c1, r1 = _col((m.group(4) or m.group(2)) + (m.group(5) or m.group(3)))
    return [cells.get((r, c), "") for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]


def _xlsx_charts(z, sheet_part):
    """시트에 붙은 차트(그리기 → 차트)의 제목·종류·계열(캐시 값)."""
    out = []
    for dpart in _rels(z, sheet_part).values():
        if "/drawings/" not in dpart or dpart not in z.namelist():
            continue
        for cpart in _rels(z, dpart).values():
            if "/charts/" not in cpart or cpart not in z.namelist():
                continue
            x = ET.fromstring(z.read(cpart))
            title = " ".join(t.text or "" for t in (x.find(C + "chart/" + C + "title") or ET.Element("x")).iter(A + "t")).strip()
            pa = x.find(C + "chart/" + C + "plotArea")
            kind = next((el.tag.replace(C, "") for el in (pa if pa is not None else []) if el.tag.endswith("Chart")), "")
            series = []
            for ser in x.iter(C + "ser"):
                def part(tag):
                    el = ser.find(C + tag)
                    el = el if el is not None else ET.Element("x")
                    f = el.find(".//" + C + "f")
                    return [v.text for v in el.iter(C + "v")], (f.text if f is not None else None)
                nm, nref = part("tx")
                cats, cref = part("cat")
                vals, vref = part("val")
                series.append({"name": " ".join(x or "" for x in nm).strip(), "categories": cats[:100], "values": vals[:100],
                               "nameRef": nref, "categoriesRef": cref, "valuesRef": vref})
            out.append({"title": title, "kind": kind, "series": series})
    return out


def md_xlsx(doc):
    L = []
    if doc["names"]:
        L += ["이름 정의: " + ", ".join(f"{n['name']}={n['ref']}" for n in doc["names"][:20]), ""]
    for s in doc["sheets"]:
        L += ["", f"## 시트: {s['name']}" + (" (숨김)" if s["hidden"] else "") + (f" - 범위 {s['dimension']}" if s.get("dimension") else ""), ""]
        if s["rows"]:
            L.append(f"(표의 첫 칸 = {s['origin']}, 첫 줄을 머리로 그렸다)")
            L += _table_md(s["rows"])
        else:
            L.append("(빈 시트)")
        if s["truncated"]:
            L.append(f"\n※ 시트가 커서 {MAX_ROWS}행·{MAX_COLS}열까지만 꺼냈다 - 전체는 원본에서(--max-rows 로 늘릴 수 있다)")
        if s["merged"]:
            L.append("병합: " + ", ".join(s["merged"][:30]))
        if s["formulas"]:
            L.append(f"수식 {len(s['formulas'])}개(content.json formulas) - 예: " + ", ".join(f"{k} {v}" for k, v in list(s["formulas"].items())[:5]))
        for ch in s["charts"]:
            L += ["", f"차트 [{ch['kind']}] {ch['title']}"]
            for se in ch["series"]:
                L.append(f"- {se['name'] or '(계열)'}: " + ", ".join(f"{c}={v}" if c is not None else str(v) for c, v in zip(se["categories"] or [None] * len(se["values"]), se["values"])))
    return L


# ---------- PDF ----------
def read_pdf(src, imgs):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None
    if fitz is None:
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("PDF 를 읽을 라이브러리가 없다 - `python3 -m pip install pymupdf`(글·표·그림) 또는 `pypdf`(글만). "
                             "그 전에는 세션이 Read 로 PDF 를 직접 열어 볼 수 있다")
        rd = PdfReader(str(src))
        if rd.is_encrypted:
            raise ValueError("암호가 걸린 PDF 다")
        return {"type": "pdf", "engine": "pypdf", "pages": [{"n": i + 1, "text": (p.extract_text() or "").strip(), "tables": [], "images": []} for i, p in enumerate(rd.pages)],
                "meta": {k.lstrip("/"): str(v) for k, v in (rd.metadata or {}).items()}}
    d = fitz.open(str(src))
    if d.needs_pass:
        raise ValueError("암호가 걸린 PDF 다")
    pages = []
    for i, pg in enumerate(d):
        item = {"n": i + 1, "text": pg.get_text("text").strip(), "tables": [], "images": []}
        try:  # PyMuPDF 1.23+ (표 찾기가 표준 출력에 안내 글을 찍어 조용히 한다)
            import contextlib
            import io as _io
            with contextlib.redirect_stdout(_io.StringIO()):
                found = pg.find_tables().tables
            for t in found:
                rows = [[c if c is not None else "" for c in r] for r in t.extract()]
                if rows and any(any(str(c).strip() for c in r) for r in rows):
                    item["tables"].append(rows)
        except Exception:  # noqa: BLE001 - 표 찾기가 없는 판·실패는 글만
            pass
        for im in pg.get_images(full=True):
            try:
                info = d.extract_image(im[0])
            except Exception:  # noqa: BLE001
                continue
            if info and info.get("image") and info.get("width", 0) * info.get("height", 0) >= 64 * 64:  # 아이콘·선 조각은 뺀다
                item["images"].append(imgs.put(info["image"], info.get("ext", "png"), f"p{i + 1:02d}"))
        pages.append(item)
    meta = {k: v for k, v in (d.metadata or {}).items() if v}
    return {"type": "pdf", "engine": "pymupdf", "pages": pages, "meta": meta, "toc": [{"level": l, "title": t, "page": p} for l, t, p in d.get_toc()][:200]}


def md_pdf(doc):
    L = []
    if doc.get("meta", {}).get("title"):
        L += [f"제목(메타): {doc['meta']['title']}", ""]
    if doc.get("toc"):
        L += ["## 목차(책갈피)", ""] + ["  " * (t["level"] - 1) + f"- {t['title']} (p.{t['page']})" for t in doc["toc"]] + [""]
    for p in doc["pages"]:
        L += ["", f"## {p['n']}쪽", ""]
        L.append(p["text"] or "(글 없음 - 스캔 이미지일 수 있다. 그림을 Read 로 열어 본다)")
        for t in p["tables"]:
            L += ["", "표:"] + _table_md(t)
        for im in p["images"]:
            L.append(f"![그림]({im})")
    return L


# ---------- 실행 ----------
KINDS = {".docx": ("Word", read_docx, md_docx), ".docm": ("Word", read_docx, md_docx), ".xlsx": ("Excel", read_xlsx, md_xlsx),
         ".xlsm": ("Excel", read_xlsx, md_xlsx), ".pdf": ("PDF", read_pdf, md_pdf)}
OLD = {".doc": "Word 에서 .docx 로", ".xls": "Excel 에서 .xlsx 로", ".ppt": "PowerPoint 에서 .pptx 로 저장하고 import_pptx"}


def run(src, out_dir, images=True, as_json=False, max_rows=MAX_ROWS):
    src = Path(src)
    if not _inside(src, _allowed_roots()):
        sys.exit(f"작업 공간 안의 파일만 열 수 있다: {src} - 요청 첨부(out/attach/<덱>/…)나 작업 공간 폴더에 둔 파일을 준다")
    if not src.is_file():
        sys.exit(f"파일 없음: {src}")
    ext = src.suffix.lower()
    if ext == ".pptx":
        sys.exit("PPTX 는 import_pptx 로 꺼낸다: python3 nexa.py import_pptx " + src.as_posix())
    if ext in OLD:
        sys.exit(f"옛 형식({ext})은 읽지 않는다 - {OLD[ext]} 저장해 다시 올린다")
    if ext not in KINDS:
        sys.exit(f"지원하지 않는 형식: {ext or '(확장자 없음)'} - .docx · .xlsx · .xlsm · .pdf (PPTX 는 import_pptx)")
    out_dir = Path(out_dir)
    if not _inside(out_dir, _allowed_roots()):
        sys.exit(f"--out 은 작업 공간 안이어야 한다: {out_dir}")
    label, reader, to_md = KINDS[ext]
    imgs = _Images(out_dir, images)
    try:
        doc = reader(src, imgs, max_rows) if reader is read_xlsx else reader(src, imgs)
    except zipfile.BadZipFile:
        sys.exit(f"{label} 파일을 열지 못했다(손상되었거나 암호가 걸린 문서) - {src}")
    except ValueError as e:
        sys.exit(f"{label} 파일을 열지 못했다: {e}")
    doc["source"] = src.name
    doc["images"] = {"saved": imgs.saved, "found": imgs.n}
    out_dir.mkdir(parents=True, exist_ok=True)
    md = [f"# {src.name} - {label}", ""] + to_md(doc)
    (out_dir / "content.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8", newline="\n")
    (out_dir / "content.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    if doc["type"] == "docx":
        summary = f"블록 {len(doc['blocks'])}개(제목 {sum(b['kind'] == 'heading' for b in doc['blocks'])} · 표 {sum(b['kind'] == 'table' for b in doc['blocks'])}) · 각주 {len(doc['notes'])}"
    elif doc["type"] == "xlsx":
        summary = f"시트 {len(doc['sheets'])}개 · " + " · ".join(f"{s['name']} {len(s['rows'])}행" for s in doc["sheets"][:6])
    else:
        summary = f"{len(doc['pages'])}쪽 · 표 {sum(len(p['tables']) for p in doc['pages'])} ({doc['engine']})"
    if as_json:
        print(json.dumps({"ok": True, "type": doc["type"], "out": _rel(out_dir), "md": _rel(out_dir / "content.md"), "json": _rel(out_dir / "content.json"),
                          "summary": summary, "images": doc["images"]}, ensure_ascii=False))
        return doc
    print(f"추출: {_rel(out_dir / 'content.md')}  ({label} · {summary} · 그림 파일 {imgs.saved}개)")
    print(f"구조: {_rel(out_dir / 'content.json')}" + (f" · 그림: {_rel(out_dir / 'images')}/" if imgs.saved else ""))
    print("다음: content.md 를 Read 로 읽고 slide_types·layout_samples 로 장을 골라 덱을 쓴다. 그림은 image 요소 src 에 위 경로 그대로.")
    return doc


# ---------- 견본으로 자기 점검 ----------
_PNG1 = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")
_CT = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>{}</Types>'


def _make_docx(path):
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    doc = (f'<w:document {w}><w:body>'
           '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>견본 보고서</w:t></w:r></w:p>'
           '<w:p><w:r><w:t xml:space="preserve">본문 첫 문단 </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>강조</w:t></w:r></w:p>'
           '<w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>둘째 수준 항목</w:t></w:r></w:p>'
           '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>항목</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>값</w:t></w:r></w:p></w:tc></w:tr>'
           '<w:tr><w:tc><w:p><w:r><w:t>매출</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>120</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
           '<w:p><w:r><w:drawing><a:graphic><a:graphicData><a:blip r:embed="rId9"/></a:graphicData></a:graphic></w:drawing></w:r></w:p>'
           '</w:body></w:document>')
    styles = f'<w:styles {w}><w:style w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>'
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId9" Type="image" Target="media/image1.png"/></Relationships>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", _CT.format('<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'))
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", rels)
        z.writestr("word/media/image1.png", _PNG1)


def _make_xlsx(path):
    s = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", _CT.format('<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'))
        z.writestr("xl/workbook.xml", f'<workbook {s}><sheets><sheet name="실적" sheetId="1" r:id="rId1"/><sheet name="숨김" sheetId="2" state="hidden" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="ws" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="ws" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst {s}><si><t>분기</t></si><si><t>매출</t></si><si><t>1분기</t></si></sst>')
        z.writestr("xl/styles.xml", f'<styleSheet {s}><cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {s}><dimension ref="A1:C3"/><sheetData>'
                   '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="inlineStr"><is><t>날짜</t></is></c></row>'
                   '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>10.5</v></c><c r="C2" s="1"><v>45580</v></c></row>'
                   '<row r="3"><c r="A3" t="inlineStr"><is><t>합계</t></is></c><c r="B3"><f>SUM(B2:B2)</f><v>10.5</v></c></row>'
                   '</sheetData><mergeCells><mergeCell ref="A3:A3"/></mergeCells></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", f'<worksheet {s}><sheetData/></worksheet>')


def selftest(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = []
    _make_docx(out_dir / "sample.docx")
    d = run(out_dir / "sample.docx", out_dir / "docx")
    bl = d["blocks"]
    checks += [("Word 제목", bl[0] == {"kind": "heading", "level": 1, "text": "견본 보고서"}),
               ("Word 굵게", bl[1]["text"] == "본문 첫 문단 **강조**"),
               ("Word 목록 수준", bl[2]["kind"] == "li" and bl[2]["level"] == 1),
               ("Word 표", bl[3] == {"kind": "table", "rows": [["항목", "값"], ["매출", "120"]]}),
               ("Word 그림", bool(bl[4].get("images")) and d["images"]["saved"] == 1)]
    _make_xlsx(out_dir / "sample.xlsx")
    x = run(out_dir / "sample.xlsx", out_dir / "xlsx")
    s1, s2 = x["sheets"]
    checks += [("Excel 공유 문자열·인라인", s1["rows"][0] == ["분기", "매출", "날짜"]),
               ("Excel 숫자·날짜", s1["rows"][1] == ["1분기", "10.5", "2024-10-15"]),
               ("Excel 수식", s1["formulas"].get("B3") == "=SUM(B2:B2)" and s1["rows"][2][1] == "10.5"),
               ("Excel 숨긴 시트", s2["hidden"] and s2["rows"] == [])]
    try:
        import fitz
        pdf = fitz.open()
        pg = pdf.new_page()
        pg.insert_text((72, 72), "Sample PDF page one", fontsize=14)
        pdf.save(str(out_dir / "sample.pdf"))
        p = run(out_dir / "sample.pdf", out_dir / "pdf")
        checks.append(("PDF 글(PyMuPDF)", "Sample PDF page one" in p["pages"][0]["text"]))
    except ImportError:
        print("알림: PyMuPDF 가 없어 PDF 점검은 건너뛴다(pip install pymupdf)")
    bad = [n for n, ok in checks if not ok]
    print("selftest: " + ("모두 통과 " if not bad else f"실패 {bad} ") + str([n for n, _ in checks]))
    return 1 if bad else 0


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Word·Excel·PDF 내용 추출 → content.md · content.json · images/ (작업 공간 out/import/<이름>/)")
    ap.add_argument("file", nargs="?", help="파일(.docx·.xlsx·.xlsm·.pdf - 요청 첨부 out/attach/<덱>/… 등)")
    ap.add_argument("--out", help="결과 폴더(작업 공간 안). 기본 out/import/<파일 이름>/")
    ap.add_argument("--no-images", action="store_true", help="그림 파일을 쓰지 않는다")
    ap.add_argument("--json", action="store_true", help="요약을 JSON 한 줄로")
    ap.add_argument("--max-rows", type=int, default=MAX_ROWS, help=f"Excel 시트마다 꺼낼 행 수(기본 {MAX_ROWS})")
    ap.add_argument("--selftest", action="store_true", help="견본 문서를 만들어 추출을 점검")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.out or (OUT / ".studio" / "import-doc-selftest")))
    if not a.file:
        ap.error("파일을 준다")
    src = Path(a.file)
    out = Path(a.out) if a.out else OUT / "import" / src.stem
    run(src, out, images=not a.no_images, as_json=a.json, max_rows=max(1, a.max_rows))


if __name__ == "__main__":
    main()
