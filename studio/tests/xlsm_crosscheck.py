# -*- coding: utf-8 -*-
"""엑셀 파일(xlsx·xlsm) 교차 검증 - 가져와서 저장한 파일이 원본과 같은 데이터·같은 기능인가.

    python3 studio/tests/xlsm_crosscheck.py <원본.xlsm> [--keep 폴더] [--max 20]

1. 가져오기(sheet_import.to_doc) → 문서 A
2. 계산기 - A 를 sheet_calc.py·sheetcalc.js 로 다시 계산한 값 = 원본 파일에 엑셀이 저장해 둔 값인가
3. 내보내기(export_xlsx) → 저장본. 저장본을 다시 가져온 문서 B = A 인가(값·수식·서식·병합·필터·유효성·조건부 서식·이름·그림 등 문서 전체)
4. 엑셀(Windows COM, xlsm_dump.ps1) - 원본과 저장본을 각각 열어 모두 다시 계산(VBA 사용자 함수 포함)한 수식·값·숨긴 행열·필터·이름이 같은가
5. VBA - 원본과 저장본의 모듈 소스가 같은가(vba_project.read_modules)
엑셀이 없으면 4 는 건너뛴다. 원본 파일은 읽기만 한다(복사본으로 작업).
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    return (a if a not in (None, "") else "") == (b if b not in (None, "") else "")


class Report:
    def __init__(self, cap):
        self.cap, self.parts = cap, []

    def part(self, title, diffs, total):
        self.parts.append((title, diffs, total))
        ok = not diffs
        print(f"{'OK  ' if ok else 'DIFF'} {title} - {total}개 중 {len(diffs)}개 다름")
        for d in diffs[:self.cap]:
            print("     ", d)
        if len(diffs) > self.cap:
            print(f"      … {len(diffs) - self.cap}개 더")

    @property
    def failed(self):
        return [t for t, d, _ in self.parts if d]


def val(c):
    return c.get("v") if isinstance(c, dict) else c


def norm_doc(d):
    d = copy.deepcopy(d)
    for k in ("updated", "source", "id"):
        d.pop(k, None)
    return d


def walk_diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a:
                out.append(f"{path}/{k}: (없음) → {json.dumps(b[k], ensure_ascii=False)[:120]}")
            elif k not in b:
                out.append(f"{path}/{k}: {json.dumps(a[k], ensure_ascii=False)[:120]} → (없음)")
            else:
                walk_diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk_diff(x, y, f"{path}[{i}]", out)
    elif not same(a, b) or type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        out.append(f"{path}: {json.dumps(a, ensure_ascii=False)[:120]} → {json.dumps(b, ensure_ascii=False)[:120]}")


def col_name(c):
    s = ""
    c += 1
    while c:
        c, m = divmod(c - 1, 26)
        s = chr(65 + m) + s
    return s


def ref_rc(ref):
    import re
    m = re.fullmatch(r"\$?([A-Z]+)\$?(\d+)", ref)
    c = 0
    for ch in m.group(1):
        c = c * 26 + ord(ch) - 64
    return int(m.group(2)) - 1, c - 1


def excel_dump(path, out):
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return None
    r = subprocess.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "xlsm_dump.ps1"), "-Path", str(path), "-Out", str(out)],
                       capture_output=True, text=True, timeout=600)
    if r.returncode or not Path(out).is_file():
        print("  엑셀 덤프 실패:", (r.stderr or r.stdout)[-400:])
        return None
    return json.loads(Path(out).read_text(encoding="utf-8-sig"))


def cells_of(dump):
    """덤프 → {탭: {A1: (수식, 값)}}"""
    out = {}
    for s in dump["sheets"]:
        r0, c0 = ref_rc(s["first"])
        m = {}
        for i, row in enumerate(s["f"] or []):
            for j, f in enumerate(row if isinstance(row, list) else [row]):
                v = s["v"][i][j] if isinstance(s["v"][i], list) else s["v"][i]
                v0 = s["v0"][i][j] if s.get("v0") and isinstance(s["v0"][i], list) else None
                if f in (None, "") and v in (None, ""):
                    continue
                m[f"{col_name(c0 + j)}{r0 + i + 1}"] = (f, v, v0)
        out[s["name"]] = m
    return out


def main():
    ap = argparse.ArgumentParser(description="엑셀 파일 가져오기·저장 교차 검증")
    ap.add_argument("src")
    ap.add_argument("--keep", help="저장본·덤프를 둘 폴더(없으면 임시 폴더)")
    ap.add_argument("--max", type=int, default=15, help="항목마다 보일 차이 수")
    ap.add_argument("--no-excel", action="store_true")
    a = ap.parse_args()
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    work = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="nexa-xcheck-"))
    work.mkdir(parents=True, exist_ok=True)
    (work / "nexa-slide.json").write_text("{}", encoding="utf-8")
    os.environ["NEXA_SLIDE_WORKSPACE"] = str(work)
    sys.path.insert(0, str(STUDIO))
    sys.path.insert(0, str(HERE))
    import export_xlsx  # noqa: E402
    import sheet_calc  # noqa: E402
    import sheet_import  # noqa: E402
    import vba_project  # noqa: E402

    src = Path(a.src)
    orig = work / ("원본" + src.suffix.lower())
    shutil.copyfile(src, orig)
    rep = Report(a.max)
    print(f"원본 {src} · 작업 폴더 {work}")

    # 1. 가져오기
    doc_a, warns = sheet_import.to_doc("xa", src.stem, orig, work)
    print("가져오기 경고:", warns or "없음")

    # 2. 계산기 = 엑셀 저장값
    calc = copy.deepcopy(doc_a)
    sheet_calc.recalc(calc)
    js_in, js_out = work / "calc_in.json", work / "calc_js.json"
    js_in.write_text(json.dumps(doc_a, ensure_ascii=False), encoding="utf-8")
    node = shutil.which("node")
    calc_js = None
    if node:
        r = subprocess.run([node, str(HERE / "xlsm_calc.js"), str(js_in), str(js_out)], capture_output=True, text=True, timeout=300)
        calc_js = json.loads(js_out.read_text(encoding="utf-8")) if not r.returncode else None
        if r.returncode:
            print("  sheetcalc.js 실패:", r.stderr[-300:])
    for name, got in (("sheet_calc.py", calc), ("sheetcalc.js", calc_js)):
        if got is None:
            continue
        diffs, n = [], 0
        for ta, tb in zip(doc_a["sheets"], got["sheets"]):
            for k, c in ta["cells"].items():
                if isinstance(c, dict) and c.get("f"):
                    n += 1
                    x, y = val(c), val(tb["cells"].get(k))
                    if not same(x, y):
                        diffs.append(f"{ta['name']}!{k} {c['f'][:70]} · 엑셀 {json.dumps(x, ensure_ascii=False)[:60]} · 계산 {json.dumps(y, ensure_ascii=False)[:60]}")
        rep.part(f"계산기({name}) = 원본 파일의 엑셀 계산값", diffs, n)

    # 3. 저장 → 다시 가져오기
    saved = work / ("저장본" + (".xlsm" if doc_a.get("macros") else ".xlsx"))
    export_xlsx.export(copy.deepcopy(doc_a), saved)
    saved = saved if saved.is_file() else next(work.glob("저장본.*"))
    doc_b, _ = sheet_import.to_doc("xa", src.stem, saved, work / "b")
    diffs = []
    walk_diff(norm_doc(doc_a), norm_doc(doc_b), "", diffs)
    diffs = [d for d in diffs if not d.startswith("/macros/vba")]
    rep.part("저장본을 다시 가져온 문서 = 처음 가져온 문서(문서 전체)", diffs, sum(len(t["cells"]) for t in doc_a["sheets"]))

    # 5. VBA
    zo, zs = zipfile.ZipFile(orig), zipfile.ZipFile(saved)
    if "xl/vbaProject.bin" in zo.namelist():
        mo = vba_project.read_modules(zo.read("xl/vbaProject.bin"))
        ms = vba_project.read_modules(zs.read("xl/vbaProject.bin")) if "xl/vbaProject.bin" in zs.namelist() else []
        d = [f"{m['name']}: 저장본에 없음" for m in mo if m["name"] not in {x['name'] for x in ms}]
        d += [f"{m['name']}: 소스가 다름" for m in mo for x in ms if x["name"] == m["name"] and x["code"] != m["code"]]
        rep.part("VBA 모듈 소스", d, len(mo))

    # 칸 서식 - 파일에서 바로 풀어 읽은 글꼴·채우기·테두리·표시 형식·맞춤(가져오기가 모르는 속성도 보인다)
    import xlsx_styles  # noqa: E402
    so, sv = xlsx_styles.cell_styles(orig), xlsx_styles.cell_styles(saved)
    d, n = [], 0
    for tab, m in so.items():
        m2 = sv.get(tab, {})
        for k in sorted(set(m) | set(m2), key=lambda r: (len(r), r)):
            n += 1
            if json.dumps(m.get(k, {}), sort_keys=True) != json.dumps(m2.get(k, {}), sort_keys=True):
                x, y = m.get(k, {}), m2.get(k, {})
                keys = sorted(set(x) | set(y))
                d.append(f"{tab}!{k} " + " · ".join(f"{kk}: {json.dumps(x.get(kk), ensure_ascii=False)} → {json.dumps(y.get(kk), ensure_ascii=False)}" for kk in keys if x.get(kk) != y.get(kk))[:260])
    rep.part("칸 서식(글꼴·채우기·테두리·표시 형식·맞춤·잠금) 원본 = 저장본", d, n)

    # 4. 엑셀로 다시 계산한 결과
    if not a.no_excel:
        do, ds = excel_dump(orig, work / "excel_원본.json"), excel_dump(saved, work / "excel_저장본.json")
        if do and ds:
            co, cs = cells_of(do), cells_of(ds)
            fd, vd, n = [], [], 0
            for tab, m in co.items():
                m2 = cs.get(tab, {})
                for k, (f, v, v0) in m.items():
                    n += 1
                    f2, v2, _ = m2.get(k, ("", "", ""))
                    if str(f) != str(f2):
                        fd.append(f"{tab}!{k} {str(f)[:80]} → {str(f2)[:80]}")
                    if not same(v, v2):
                        vd.append(f"{tab}!{k} {json.dumps(v, ensure_ascii=False)[:60]} → {json.dumps(v2, ensure_ascii=False)[:60]}" + (f"  (수식 {str(f)[:60]})" if str(f).startswith("=") else ""))
                for k in set(m2) - set(m):
                    fd.append(f"{tab}!{k} (없음) → {str(m2[k][0])[:80]}")
            rep.part("엑셀 - 수식(Formula2) 원본 = 저장본", fd, n)
            rep.part("엑셀 - 다시 계산한 값 원본 = 저장본(VBA 사용자 함수 포함)", vd, n)
            ch = [f"{tab}!{k} 저장값 {json.dumps(v0, ensure_ascii=False)[:50]} · 다시 계산 {json.dumps(v, ensure_ascii=False)[:50]}" for tab, m in co.items() for k, (f, v, v0) in m.items()
                  if str(f).startswith("=") and not same(v, v0)]
            print(f"참고 - 원본을 엑셀이 다시 계산하면 바뀌는 칸(시각·난수·외부 참조 등): {len(ch)}개" + ("".join("\n      " + x for x in ch[:a.max])))
            sd = []
            for so in do["sheets"]:
                ss = next((x for x in ds["sheets"] if x["name"] == so["name"]), None)
                if not ss:
                    sd.append(f"{so['name']}: 저장본에 없음")
                    continue
                for k in ("visible", "hiddenRows", "hiddenCols", "filter", "code", "shapes", "colW", "rowH"):
                    if json.dumps(so.get(k), sort_keys=True) != json.dumps(ss.get(k), sort_keys=True):
                        sd.append(f"{so['name']} {k}: {json.dumps(so.get(k), ensure_ascii=False)[:100]} → {json.dumps(ss.get(k), ensure_ascii=False)[:100]}")
            no = {x["name"]: x["ref"] for x in do["names"]}
            ns = {x["name"]: x["ref"] for x in ds["names"]}
            sd += [f"이름 {k}: {no.get(k)} → {ns.get(k)}" for k in sorted(set(no) | set(ns)) if no.get(k) != ns.get(k)]
            sd += [] if do["vba"] == ds["vba"] else [f"VBA 프로젝트: {do['vba']} → {ds['vba']}"]
            rep.part("엑셀 - 탭 표시·숨긴 행열·열 너비·행 높이·자동 필터·그림·도형·단추(자리·크기·매크로)·코드 이름·이름 정의·VBA", sd, len(do["sheets"]))
        else:
            print("엑셀 비교 건너뜀(엑셀 없음 또는 덤프 실패)")
    print("\n다른 항목:", rep.failed or "없음", f"\n작업 폴더: {work}")
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
