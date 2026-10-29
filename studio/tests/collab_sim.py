# -*- coding: utf-8 -*-
"""다중 창 시뮬레이터(동시 편집 3-5, docs/collab.md) - 가짜 창 3개가 무작위로 고치고 작업 저장(POST /api/ops)·PUT 병합을 섞어 보낸다.
    python3 studio/tests/collab_sim.py [--seed N] [--steps N]
- 창마다 자기 몫(만든 요소·자기 열의 셀)이 있고, 끝에서 서버 파일의 자기 몫이 창이 마지막으로 본 자기 몫과 같아야 한다(잃어버린 갱신 없음).
  같은 곳을 함께 고치는 편집(덱 제목·공용 요소 글)은 어느 쪽이 이겨도 되고, 모든 창이 같은 결과로 모이는지만 본다.
- 창은 가끔만 다시 읽는다(오래된 판에서 고치기) - 실시간 연결이 늦게 오는 경우를 흉내 낸다.
- 실패하면 씨앗(seed)을 알린다 - 같은 씨앗으로 다시 돌리면 같은 순서가 된다."""
import argparse
import json
import os
import random
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

    def uid(self):
        self.n += 1
        return f"w{self.k}n{self.n}"

    def save(self, rnd, log):
        import deckops
        if self.doc == self.saved:
            return
        sent = clone(self.doc)
        if rnd.random() < 0.5:
            ops = deckops.diff(self.saved, sent)
            st, r, _ = call("POST", f"/api/ops/{self.deck}", {"base": self.version, "ops": ops})
            how = f"ops {len(ops)}"
        else:
            st, r, _ = call("PUT", f"/api/deck/{self.deck}?base={self.version}&merge=1", sent)
            how = "put"
        if st != 200:
            log.append(f"w{self.k} {how} → {st} {json.dumps(r, ensure_ascii=False)[:200]}")
            FAILS.append(f"저장 실패 w{self.k} {how} {st}")
            print("  ", log[-1])
            return
        log.append(f"w{self.k} {how} v{self.version[:6]}→{r['version'][:6]}" + (" 병합" if r.get("merged") else "") + (f" 버림{len(r['dropped'])}" if r.get("dropped") else ""))
        if r.get("merged"):  # 화면과 같다 - 병합 결과를 받아 둔다(NexaMerge.afterSave: 보낸 뒤 고친 것이 없으므로 그대로)
            self.doc, self.saved = clone(r["deck"]), clone(r["deck"])
            self.version = r["version"]
        elif how == "put":
            self.saved, self.version = sent, r["version"]
        elif how != "put" and r.get("deck") is not None and not NAIVE:  # 작업 저장 - 오래된 판 위에 얹었으면 서버가 결과 문서를 준다 → PUT 병합과 같게 받는다
            self.doc, self.saved, self.version = clone(r["deck"]), clone(r["deck"]), r["version"]
        else:  # 그대로 저장됨(작업 저장이 지금 판 위였거나 PUT) - 저장본 = 보낸 것
            self.saved, self.version = sent, r["version"]


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


def run(seed, steps):
    rnd = random.Random(seed)
    print(f"씨앗 {seed} · 걸음 {steps}")
    log = []
    for deck, edit, mine in (("sim", edit_slides, None), ("simsheet", edit_sheet, None)):
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
            else:
                col = COLS[w.k]
                want = {k: v for k, v in w.doc["sheets"][0]["cells"].items() if k[0] == col}
                got = {k: v for k, v in final["sheets"][0]["cells"].items() if k[0] == col}
                if want != got:
                    lost.append(f"w{w.k} 셀 {sorted(set(want) ^ set(got)) or [k for k in want if want[k] != got.get(k)]}")
        check(f"{deck} - 창마다 자기 몫(요소·순서·셀)이 서버 파일에 그대로(잃어버린 갱신 없음)", not lost, f"씨앗 {seed}: " + "; ".join(lost))
        for w in wins:
            w.refresh()
        check(f"{deck} - 다시 읽은 창 3개가 같은 문서로 모임", all(w.doc == wins[0].doc for w in wins) and wins[0].doc == final, f"씨앗 {seed}")
        st, led, _ = call("GET", f"/api/changes/{deck}")
        check(f"{deck} - 원장이 읽힌다", st == 200, json.dumps(led, ensure_ascii=False)[:200])
    if FAILS:
        print("\n".join(log[-30:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--naive", action="store_true")
    a = ap.parse_args()
    global NAIVE
    NAIVE = a.naive
    seed = a.seed if a.seed is not None else int(time.time()) % 100000
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "sim시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    decks = WS / "decks"; decks.mkdir(parents=True, exist_ok=True)
    slides = [{"id": f"s{k}", "elements": [{"id": "c1", "type": "text", "x": 10, "y": 10, "w": 300, "h": 40, "text": "공용"}] if k == 1 else []} for k in range(1, 4)]
    (decks / "sim.json").write_text(json.dumps({"id": "sim", "title": "시뮬", "slides": slides}, ensure_ascii=False), encoding="utf-8")
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
