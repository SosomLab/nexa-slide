# -*- coding: utf-8 -*-
"""다중 창 시뮬레이터(동시 편집 3-5, docs/collab.md) - 가짜 창 3개가 무작위로 고치고 작업 저장(POST /api/ops)·PUT 병합을 섞어 보낸다.
    python3 studio/tests/collab_sim.py [--seed N] [--steps N]
- 창마다 자기 몫(만든 요소·자기 열의 셀)이 있고, 끝에서 서버 파일의 자기 몫이 창이 마지막으로 본 자기 몫과 같아야 한다(잃어버린 갱신 없음).
  같은 곳을 함께 고치는 편집(덱 제목·공용 요소 글)은 어느 쪽이 이겨도 되고, 모든 창이 같은 결과로 모이는지만 본다.
- 창은 가끔만 다시 읽는다(오래된 판에서 고치기) - 실시간 연결이 늦게 오는 경우를 흉내 낸다.
- 시트는 가끔 행을 넣는다(구조 작업 - 창이 자기 문서를 sheet_struct 로 옮기고 다음 저장에 __struct 로 보낸다). 양쪽이 모두 행을 넣어
  409 struct-both 가 나면 그 창은 다시 읽는다(화면의 [밖의 것 다시 읽기]). 칸이 움직이므로 시트의 자기 몫은 "자기 열 값의 위→아래 순서"로 본다.
- 실패하면 씨앗(seed)을 알린다 - 같은 씨앗으로 다시 돌리면 같은 순서가 된다."""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "sim시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
os.environ["NEXA_SLIDE_WORKSPACE"] = str(WS)  # deckops·deckmerge 를 불러오려면 작업 공간이 있어야 한다
B = f"http://127.0.0.1:{PORT}"
FAILS = []
COLS = "ABC"  # 창 i 의 몫 = 시트 i 열
STRUCT = True  # --no-struct: 시트에 행 넣기를 섞지 않는다
STATS = {"struct": 0, "struct-both": 0, "ops400": 0}
LOST = []  # 저장마다 본 잃어버린 갱신(시트 - 병합 결과의 내 열이 보낸 것과 다름)
NAIVE = False  # --naive: 작업 저장 응답의 결과 문서(deck)를 무시하고 새 판만 받는다 - 잃어버린 갱신이 나야 한다(시뮬레이터가 잡는지 확인)


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def call(method, url, body=None):
    rq = urllib.request.Request(B + url, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(), method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=15) as r:
            return r.status, json.loads(r.read()), r.headers.get("X-Deck-Version")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), None


def clone(x):
    return json.loads(json.dumps(x))


class Win:
    """가짜 창 - doc(지금 화면), saved(마지막으로 서버와 맞춘 문서), version(그 판)"""

    def __init__(self, k, deck):
        self.k, self.deck, self.n = k, deck, 0
        self.refresh()

    def refresh(self):
        _, self.doc, self.version = call("GET", f"/api/deck/{self.deck}")
        self.saved = clone(self.doc)
        self.struct = []  # 다음 저장에 보낼 행·열 작업(시트)

    def uid(self):
        self.n += 1
        return f"w{self.k}n{self.n}"

    def save(self, rnd, log):
        import deckops
        if self.doc == self.saved:
            return
        sent = clone(self.doc)
        if self.deck == "simpage":  # 페이지 문서 - 화면(page.js)처럼 PUT 병합만(작업 저장은 아직 blocks 를 다루지 않는다)
            st, r, _ = call("PUT", f"/api/deck/{self.deck}?base={self.version}&merge=1", sent)
            how = "put"
        elif self.struct:  # 행·열 작업이 있으면 PUT(__struct) - 화면 planSave 와 같다
            st, r, _ = call("PUT", f"/api/deck/{self.deck}?base={self.version}&merge=1", {**sent, "__struct": self.struct})
            how = f"put struct {len(self.struct)}"
            if st == 409 and r.get("reason") == "struct-both":  # 다른 창도 행을 넣었다 - 다시 읽는다(내 것 버림)
                log.append(f"w{self.k} {how} → 409 struct-both · 다시 읽음")
                STATS["struct-both"] += 1
                self.refresh()
                return
            if st == 200:
                STATS["struct"] += 1
        elif rnd.random() < 0.5:
            ops = deckops.diff(self.saved, sent)
            st, r, _ = call("POST", f"/api/ops/{self.deck}", {"base": self.version, "ops": ops})
            how = f"ops {len(ops)}"
            if st == 400 and "행·열" in str(r.get("error", "")):  # 그 사이 행·열이 바뀌었다 - 화면처럼 PUT 으로
                STATS["ops400"] += 1
                st, r, _ = call("PUT", f"/api/deck/{self.deck}?base={self.version}&merge=1", sent)
                how = "ops→put"
        else:
            st, r, _ = call("PUT", f"/api/deck/{self.deck}?base={self.version}&merge=1", sent)
            how = "put"
        if st == 200:
            self.struct = []
        if st != 200:
            log.append(f"w{self.k} {how} → {st} {json.dumps(r, ensure_ascii=False)[:200]}")
            FAILS.append(f"저장 실패 w{self.k} {how} {st}")
            print("  ", log[-1])
            return
        log.append(f"w{self.k} {how} v{self.version[:6]}→{r['version'][:6]}" + (" 병합" if r.get("merged") else "") + (f" 버림{len(r['dropped'])}" if r.get("dropped") else ""))
        if self.deck == "simpage":  # 저장마다 - 병합 결과의 내 블록(글·순서) = 보낸 것
            got = r.get("deck") if r.get("deck") is not None else None
            if got is not None and mine_page(got, self.k) != mine_page(sent, self.k):
                LOST.append(f"w{self.k} {how} 저장 결과의 내 블록: 보냄 {json.dumps(mine_page(sent, self.k), ensure_ascii=False)[:160]} ≠ 결과 {json.dumps(mine_page(got, self.k), ensure_ascii=False)[:160]}")
        if self.deck == "simsheet":  # 저장마다 - 서버가 돌려준(또는 그대로 저장한) 문서의 내 열 = 보낸 문서의 내 열(남은 내 열을 건드리지 않는다 - 행이 들어가도 순서는 같다)
            got = r.get("deck") if r.get("deck") is not None else None
            if got is not None and col_values(got, COLS[self.k]) != col_values(sent, COLS[self.k]):
                LOST.append(f"w{self.k} {how} 저장 결과의 내 열 {COLS[self.k]}: 보냄 {json.dumps(col_values(sent, COLS[self.k]), ensure_ascii=False)[:160]} ≠ 결과 {json.dumps(col_values(got, COLS[self.k]), ensure_ascii=False)[:160]}")
        if r.get("merged"):  # 화면과 같다 - 병합 결과를 받아 둔다(NexaMerge.afterSave: 보낸 뒤 고친 것이 없으므로 그대로)
            self.doc, self.saved = clone(r["deck"]), clone(r["deck"])
            self.version = r["version"]
        elif how.startswith("put") or how == "ops→put":
            self.saved, self.version = sent, r["version"]
        elif how != "put" and r.get("deck") is not None and not NAIVE:  # 작업 저장 - 오래된 판 위에 얹었으면 서버가 결과 문서를 준다 → PUT 병합과 같게 받는다
            self.doc, self.saved, self.version = clone(r["deck"]), clone(r["deck"]), r["version"]
        else:  # 그대로 저장됨(작업 저장이 지금 판 위였거나 PUT) - 저장본 = 보낸 것
            self.saved, self.version = sent, r["version"]


def col_values(d, col):
    """시트의 자기 몫 - 그 열의 비지 않은 값을 위→아래 순서로(행이 들어가 칸 이름이 바뀌어도 같다). 수식의 행 번호는 지운다"""
    cells = d["sheets"][0].get("cells") or {}
    keys = sorted((k for k in cells if re.fullmatch(col + r"\d+", k)), key=lambda k: int(k[len(col):]))
    norm = lambda v: {**v, "f": re.sub(r"\d+", "#", v["f"])} if isinstance(v, dict) and v.get("f") else v  # noqa: E731
    return [norm(cells[k]) for k in keys]


def mine_page(d, k):
    """페이지 문서에서 창 k 가 만든 블록 - [(id, 글)] 순서대로"""
    return [(b["id"], "".join(r.get("t", "") for r in b.get("runs") or [])) for b in d.get("blocks") or [] if str(b.get("id", "")).startswith(f"w{k}n")]


def edit_page(w, rnd):
    bl = w.doc.setdefault("blocks", [])
    mine = [b for b in bl if str(b.get("id", "")).startswith(f"w{w.k}n")]
    r = rnd.random()
    if r < 0.35 or not mine:  # 문단 넣기 - 무작위 자리
        bl.insert(rnd.randint(0, len(bl)), {"id": w.uid(), "type": "p", "runs": [{"t": f"w{w.k}-{w.n}"}]})
    elif r < 0.65:  # 내 문단 글
        rnd.choice(mine)["runs"] = [{"t": f"w{w.k}-글{rnd.randint(0, 9999)}"}]
    elif r < 0.75:  # 내 문단 지우기
        bl.remove(rnd.choice(mine))
    else:  # 공용 문단(누가 이겨도 된다). 자리 바꾸기는 넣지 않는다 - deckmerge 규칙상 양쪽이 순서를 바꾸면 theirs(설계대로, 슬라이드 시뮬도 같다)
        c = next((b for b in bl if b.get("id") == "c1"), None)
        if c:
            c["runs"] = [{"t": f"공용 w{w.k}-{rnd.randint(0, 99)}"}]


def mine_slides(d, k):
    """창 k 가 만든 요소 {id: 요소} 와 장마다 순서"""
    out, order = {}, {}
    for s in d.get("slides") or []:
        for e in s.get("elements") or []:
            if str(e.get("id", "")).startswith(f"w{k}n"):
                out[e["id"]] = e
                order.setdefault(s["id"], []).append(e["id"])
    return out, order


def edit_slides(w, rnd):
    d = w.doc
    slides = d["slides"]
    s = rnd.choice(slides)
    els = s.setdefault("elements", [])
    mine = [e for e in els if str(e.get("id", "")).startswith(f"w{w.k}n")]
    r = rnd.random()
    if r < 0.25 or not mine:  # 요소 넣기 - 무작위 자리
        at = rnd.randint(0, len(els))
        els.insert(at, {"id": w.uid(), "type": "text", "x": rnd.randint(0, 800), "y": rnd.randint(0, 400), "w": 200, "h": 40, "text": f"w{w.k}-{w.n}"})
    elif r < 0.5:  # 내 요소 글
        rnd.choice(mine)["text"] = f"w{w.k}-글{rnd.randint(0, 9999)}"
    elif r < 0.62:  # 내 요소 위치
        e = rnd.choice(mine); e["x"], e["y"] = rnd.randint(0, 800), rnd.randint(0, 400)
    elif r < 0.7:  # 내 요소 지우기
        els.remove(rnd.choice(mine))
    elif r < 0.78:  # 내 요소 속성 지우기·넣기
        e = rnd.choice(mine)
        if "fill" in e:
            del e["fill"]
        else:
            e["fill"] = rnd.choice(["primary", "accent", "#ff0000"])
    elif r < 0.86:  # 공용 - 덱 제목(누가 이겨도 된다)
        d["title"] = f"제목 w{w.k}-{rnd.randint(0, 99)}"
    elif r < 0.93:  # 공용 - 첫 요소 글(같은 곳 함께 고침)
        shared = [e for e in els if e["id"] == "c1"]
        if shared:
            shared[0]["text"] = f"공용 w{w.k}-{rnd.randint(0, 99)}"
    else:  # 내 요소 둘 자리 바꾸기(같은 장 안)
        if len(mine) >= 2:
            a, b = rnd.sample(mine, 2)
            ia, ib = els.index(a), els.index(b)
            els[ia], els[ib] = b, a


def edit_sheet(w, rnd):
    cells = w.doc["sheets"][0].setdefault("cells", {})
    col = COLS[w.k]
    mine = [k for k in cells if k[0] == col]
    r = rnd.random()
    if STRUCT and r < 0.06:  # 행 넣기(구조 작업) - 모든 열이 같이 움직인다
        import sheet_struct
        so = [{"op": "insertRows", "tab": "t01", "at": rnd.randint(0, 25), "n": 1}]
        w.doc = sheet_struct.apply(w.doc, so)
        w.struct.extend(so)
        return
    if r < 0.55 or not mine:
        cells[f"{col}{rnd.randint(1, 30)}"] = f"w{w.k}-{rnd.randint(0, 9999)}"
    elif r < 0.7:
        cells[f"{col}{rnd.randint(1, 30)}"] = {"v": rnd.randint(0, 99), "b": True}
    elif r < 0.85:
        del cells[rnd.choice(mine)]
    elif r < 0.93:
        cells[f"{col}{rnd.randint(1, 30)}"] = {"f": f"=D1+{rnd.randint(1, 9)}"}
    else:  # 공용 칸 D1(누가 이겨도 된다)
        cells["D1"] = rnd.randint(0, 99)


def verify_dump(deck, problems):
    """원장 재생이 실패했을 때의 덤프(판정 아님) - 문제 줄 앞뒤 3줄 · 그 백업 파일의 실제 해시가 어느 줄의 것과 같은지 · 같은 백업 이름을 쓰는 줄 · python 판(PG-118)"""
    import hashlib
    hdir = WS / "decks" / ".history" / deck
    try:
        rows = [json.loads(x) for x in (hdir / "changes.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    except (OSError, ValueError) as e:
        print(f"   (덤프) {deck} 원장을 못 읽음: {e}")
        return
    print(f"   (덤프) python {sys.version.split()[0]} · {sys.executable} · {deck} 원장 {len(rows)}줄 · 백업 폴더 {hdir}")
    names = [(x.get("before") or {}).get("backup") for x in rows]
    twice = sorted({n for n in names if n and names.count(n) > 1})
    print(f"   (덤프) 같은 백업 이름을 두 줄 이상이 씀(이름 겹침 = 덮어씀): {twice[:5] or '없음'}")
    short = lambda h: (h or "-")[:19]  # noqa: E731
    for pr in problems[:3]:
        k = next((i for i, x in enumerate(rows) if x.get("seq") == pr.get("seq")), None)
        if k is None:
            print(f"   (덤프) seq {pr.get('seq')} 줄 없음 · {pr.get('what')}")
            continue
        for x in rows[max(0, k - 3):k + 4]:
            b, a = x.get("before") or {}, x.get("after") or {}
            print(f"   (덤프) {'>>' if x.get('seq') == pr.get('seq') else '  '} seq {x.get('seq')} · {x.get('ts')} · {x.get('action')} · before ver {b.get('ver')} {short(b.get('hash'))} 백업 {b.get('backup')} · after ver {a.get('ver')} {short(a.get('hash'))}")
        name = (rows[k].get("before") or {}).get("backup")
        f = hdir / name if name else None
        if f and f.is_file():
            h = "sha256:" + hashlib.sha256(f.read_bytes()).hexdigest()
            same_b = [x.get("seq") for x in rows if (x.get("before") or {}).get("hash") == h]
            same_a = [x.get("seq") for x in rows if (x.get("after") or {}).get("hash") == h]
            print(f"   (덤프) 백업 {name} 실제 {short(h)} · 이 줄 before {short((rows[k].get('before') or {}).get('hash'))} · 같은 before.hash 인 줄 {same_b[:6]} · 같은 after.hash 인 줄 {same_a[:6]} · 크기 {f.stat().st_size}")
        else:
            print(f"   (덤프) 백업 {name} 파일 없음")


def run(seed, steps):
    rnd = random.Random(seed)
    print(f"씨앗 {seed} · 걸음 {steps}")
    log = []
    for deck, edit, mine in (("sim", edit_slides, None), ("simsheet", edit_sheet, None), ("simpage", edit_page, None)):
        wins = [Win(k, deck) for k in range(3)]
        for step in range(steps):
            w = rnd.choice(wins)
            if rnd.random() < 0.15:
                w.refresh()  # 실시간 연결로 다시 읽음(가끔만)
            for _ in range(rnd.randint(1, 3)):
                edit(w, rnd)
            if rnd.random() < 0.8:
                w.save(rnd, log)
        for w in wins:  # 남은 것 저장
            w.save(rnd, log)
        _, final, _ = call("GET", f"/api/deck/{deck}")
        lost = []
        for w in wins:
            if deck == "sim":
                want, wo = mine_slides(w.doc, w.k)
                got, go = mine_slides(final, w.k)
                if want != got:
                    miss = sorted(set(want) ^ set(got)) or [i for i in want if want[i] != got.get(i)]
                    lost.append(f"w{w.k} 요소 {miss[:5]}")
                if wo != go:
                    lost.append(f"w{w.k} 순서 {json.dumps(wo)[:120]} ≠ {json.dumps(go)[:120]}")
            elif deck == "simpage":
                want, got = mine_page(w.doc, w.k), mine_page(final, w.k)
                if want != got:
                    lost.append(f"w{w.k} 블록 {json.dumps(want, ensure_ascii=False)[:160]} ≠ {json.dumps(got, ensure_ascii=False)[:160]}")
            else:
                col = COLS[w.k]
                want, got = col_values(w.doc, col), col_values(final, col)
                if want != got:
                    lost.append(f"w{w.k} 열 {col} 값 순서 {json.dumps(want, ensure_ascii=False)[:200]} ≠ {json.dumps(got, ensure_ascii=False)[:200]}")
        if deck == "simpage":
            check("simpage - 저장마다 병합 결과의 내 블록(글·순서)이 보낸 것과 같음", not LOST, f"씨앗 {seed}: {len(LOST)}건 · " + " | ".join(LOST[:3]))
            LOST.clear()
        if deck == "simsheet":
            check("simsheet - 저장마다 병합 결과의 내 열이 보낸 것과 같음(행이 들어간 뒤 옛 판 저장 포함)", not LOST, f"씨앗 {seed}: {len(LOST)}건 · " + " | ".join(LOST[:3]))
            print(f"   simsheet 구조 작업: 행 넣기 저장 {STATS['struct']} · 양쪽 행 넣기 409 {STATS['struct-both']} · 작업 저장 400 → PUT {STATS['ops400']}")
        check(f"{deck} - 창마다 자기 몫(요소·순서·셀)이 서버 파일에 그대로(잃어버린 갱신 없음)", not lost, f"씨앗 {seed}: " + "; ".join(lost))
        for w in wins:
            w.refresh()
        check(f"{deck} - 다시 읽은 창 3개가 같은 문서로 모임", all(w.doc == wins[0].doc for w in wins) and wins[0].doc == final, f"씨앗 {seed}")
        st, led, _ = call("GET", f"/api/changes/{deck}")
        check(f"{deck} - 원장이 읽힌다", st == 200, json.dumps(led, ensure_ascii=False)[:200])
        # 원장 재생(3-5) - 사슬·백업·작업 저장 재생·끝이 파일과 맞는가
        r = subprocess.run([sys.executable, str(STUDIO / "ledger.py"), "verify", deck, "--json"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            v = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            v = {"raw": (r.stdout + r.stderr)[-400:]}
        print(f"   {deck} 원장 {v.get('entries')}줄 · 사슬 {v.get('chain')} · 백업 {v.get('backup')} · 재생 {v.get('replay')} · 끝 {v.get('end')}")
        okv = r.returncode == 0 and v.get("ok")
        check(f"{deck} - 원장 재생(ledger verify) rc 0", okv, f"씨앗 {seed}: " + json.dumps(v.get("problems") or v, ensure_ascii=False)[:600])
        if not okv:
            verify_dump(deck, v.get("problems") or [])
    if FAILS:
        print("\n".join(log[-30:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--naive", action="store_true")
    ap.add_argument("--no-struct", action="store_true")
    a = ap.parse_args()
    global NAIVE, STRUCT
    NAIVE, STRUCT = a.naive, not a.no_struct
    seed = a.seed if a.seed is not None else int(time.time()) % 100000
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "sim시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    decks = WS / "decks"; decks.mkdir(parents=True, exist_ok=True)
    import shutil
    for d in ("sim", "simsheet", "simpage"):  # 지난 실행의 원장·백업 - 이번 실행만 재생해 본다
        shutil.rmtree(decks / ".history" / d, ignore_errors=True)
    slides =[{"id": f"s{k}", "elements": [{"id": "c1", "type": "text", "x": 10, "y": 10, "w": 300, "h": 40, "text": "공용"}] if k == 1 else []} for k in range(1, 4)]
    (decks / "sim.json").write_text(json.dumps({"id": "sim", "title": "시뮬", "slides": slides}, ensure_ascii=False), encoding="utf-8")
    import page_doc
    pg = page_doc.new_page("simpage", "시뮬 페이지"); pg["blocks"] = [{"id": "c1", "type": "p", "runs": [{"t": "공용"}]}]
    (decks / "simpage.json").write_text(json.dumps(pg, ensure_ascii=False), encoding="utf-8")
    (decks / "simsheet.json").write_text(json.dumps({"id": "simsheet", "title": "시뮬 시트", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "S", "cells": {"D1": 1}}]}, ensure_ascii=False), encoding="utf-8")
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{B}/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        run(seed, a.steps)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS) + f' (다시: --seed {seed})'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
