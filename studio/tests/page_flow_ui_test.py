# -*- coding: utf-8 -*-
"""page-flow.js 실시간 쪽 나눔 시험(헤드리스 Chrome) - 서버 없이 tests/page_flow_page.html 을 파일로 연다(PG-102).
    python studio/tests/page_flow_ui_test.py
쪽 본문 300px · 본문 사이 64px 인 작은 종이에 문서를 올리고(load), 쪽 경계에 끼운 빈 자리(밀기 · 문단 안 빈 줄 · 표의 빈 행)와
그 뒤에도 글 편집(위치 계산·치기)이 그대로인지를 본다. audit() = 쪽 본문 밖에 걸친 줄·행·개체 목록(비어야 한다)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tmpfiles  # noqa: E402

D = "|| JSON.stringify({L: LAST && {n: LAST.n, changed: LAST.changed}, gaps: gaps(), rows: gapRows(), pushed: pushed(), bad: audit().slice(0, 6)})"
STEPS = [
    ("한 쪽 - 빈 자리 없음", "const L = load([para('a', 3), para('b', 3)]); return L.n === 1 && gaps() === 0 && pushed().length === 0 && audit().length === 0 " + D),
    ("문단 여럿 - 쪽 경계에서 밀거나 나눈다 · 걸친 줄 없음",
     "const L = load(Array.from({length: 14}, (_, i) => para('p' + i, 4))); return L.n >= 3 && gaps() + pushed().length >= L.n - 1 && audit().length === 0 " + D),
    ("긴 문단 하나 - 줄 사이에 빈 줄을 끼운다(쪽 수 - 1 개) · 글은 그대로",
     "const L = load([para('a', 60)]); return L.n >= 3 && gaps() === L.n - 1 && audit().length === 0 && el('a').textContent === txt('a') " + D),
    ("다시 계산해도 그대로 둔다(DOM 을 건드리지 않는다)",
     "load([para('a', 60)]); const g = [...document.querySelectorAll('.pg-gap')]; const L = run(); const g2 = [...document.querySelectorAll('.pg-gap')]; return L.changed === 0 && g.length === g2.length && g.every((x, i) => x === g2[i]) " + D),
    ("나뉜 문단 - 글자 위치가 그대로(빈 줄 뒤에 커서 → 같은 위치 · 다음 쪽)",
     "load([para('a', 60)]); const off = document.querySelector('.pg-gap')._off; sel('a', off + 3); const c = caret(); return c === 'a:' + (off + 3) && pageOf('a', off + 3) === 1 && pageOf('a', off - 3) === 0 || JSON.stringify([c, off, pageOf('a', off + 3), pageOf('a', off - 3)])"),
    ("나뉜 문단에 글 치기 - 모델에 들어가고 빈 줄이 다시 끼워진다 · 커서 유지",
     "load([para('a', 60)]); const off = document.querySelector('.pg-gap')._off, before = txt('a'); sel('a', off + 3); bi('insertText', 'X'); const L = run(); "
     "return txt('a') === before.slice(0, off + 3) + 'X' + before.slice(off + 3) && el('a').textContent === txt('a') && gaps() === L.n - 1 && caret() === 'a:' + (off + 4) && audit().length === 0 " + D),
    ("서식이 다른 글 조각 가운데에서 나뉜다 - 조각을 나눠도 글·서식은 그대로, 걷으면 다시 한 조각",
     "const b = para('a', 60); b.runs = [{t: b.runs[0].t, b: true, ruby: 'x'}]; const L = load([b]); const spans = el('a').querySelectorAll('span:not(.pg-gap)').length; const rubies = el('a').querySelectorAll('[data-ruby]').length; "
     "FLOW.clear(); const after = el('a').querySelectorAll('span').length; return L.n >= 3 && spans === L.n && rubies === 1 && after === 1 && el('a').textContent === txt('a') || JSON.stringify([L.n, spans, rubies, after])"),
    ("외톨이 첫 줄 - 문단째 다음 쪽 머리로",
     "const L = load([{id: 'o', type: 'image', h: 262}, para('a', 6)]); return L.n === 2 && pushed().join() === 'a' && gaps() === 0 && pageOf('a') === 1 && topIn('a') === 0 && audit().length === 0 " + D + " + topIn('a')"),
    ("쪽 나누기 블록 - 다음 블록이 다음 쪽 머리",
     "const L = load([para('a', 2), {id: 'k', type: 'break'}, para('b', 2)]); return L.n === 2 && pageOf('a') === 0 && pageOf('b') === 1 && topIn('b') === 0 && audit().length === 0 " + D + " + topIn('b')"),
    ("개체(그림) - 안 들어가면 통째 다음 쪽",
     "const L = load([para('a', 10), {id: 'o', type: 'image', h: 150}, para('b', 2)]); return L.n === 2 && pushed().join() === 'o' && pageOf('o') === 1 && topIn('o') === 0 && audit().length === 0 " + D),
    ("표 - 행 사이에 빈 행 · 걸친 행 없음 · 행 수는 그대로",
     "const L = load([para('a', 3), table('t', 30)]); const rows = [...el('t').rows].filter((r) => !r.classList.contains('pg-gaprow') && !r.classList.contains('pg-headrep')).length; return L.n >= 3 && gapRows() === L.n - 1 && rows === 30 && audit().length === 0 " + D),
    ("표 - 머리글 행을 다음 쪽 머리에 되풀이(사본은 id·편집 없음) · 걷으면 사라진다",
     "const L = load([para('a', 3), table('t', 30)]); const reps = [...document.querySelectorAll('tr.pg-headrep')]; const top0 = host.getBoundingClientRect().top; "
     "const atTop = reps.every((r) => { const y = r.getBoundingClientRect().top - top0; return Math.abs(y - Math.floor((y + 1) / 364) * 364) < 1.5; }); const txt0 = reps.map((r) => r.textContent).join(); "
     "FLOW.clear(); return L.n >= 3 && reps.length === L.n - 1 && atTop && reps.every((r) => r.textContent === 'r0c0r0c1' && !r.dataset.id && r.contentEditable === 'false') && document.querySelectorAll('tr.pg-headrep').length === 0 "
     "|| JSON.stringify([L.n, reps.length, atTop, txt0])"),
    ("표 - 테두리 겹침·border-box 에서도 빈 행 뒤의 첫 행이 쪽 머리에 정확히(±0.6px)",
     "const st = document.createElement('style'); st.textContent = '* { box-sizing: border-box } td, th { border: .5pt solid #888 !important; padding: 2pt 4pt; height: auto } tr.head th { height: auto }'; document.head.appendChild(st); "
     "const L = load([para('a', 3), table('t', 40)]); const top0 = host.getBoundingClientRect().top; const firsts = [...document.querySelectorAll('.pg-gaprow')].map((g) => { let n = g.nextElementSibling; "
     "const y = n.getBoundingClientRect().top - top0; return +(y - Math.round(y / 364) * 364).toFixed(2); }); const bad = audit(); st.remove(); return L.n >= 3 && firsts.length === L.n - 1 && firsts.every((d) => Math.abs(d) <= 0.6) && bad.length === 0 || JSON.stringify([L.n, firsts, bad.slice(0, 4)])"),
    ("표 - 합친 칸이 걸친 행 사이에서는 나누지 않는다",
     "const L = load([{id: 'o', type: 'image', h: 150}, table('t', 12, [2, 6])]); const real = [...el('t').rows].filter((r) => !r.classList.contains('pg-gaprow') && !r.classList.contains('pg-headrep')); const at = [...document.querySelectorAll('.pg-gaprow')].map((g) => { let x = g.nextElementSibling; while (x && x.classList.contains('pg-headrep')) x = x.nextElementSibling; return real.indexOf(x); }); "
     "return L.n >= 2 && at.length === L.n - 1 && at.every((k) => k <= 2 || k >= 8) && audit().length === 0 || JSON.stringify([L.n, at, audit().slice(0, 4)])"),
    ("2단 - 블록이 단 너비(195)로 좁아지고 1단 → 2단 → 다음 쪽 1단 차례로 · 겹침 없음 · 쪽 밖으로 안 나감",
     "window.COLS = {count: 2, gap: 10}; const L = load(Array.from({length: 7}, (_, i) => ({id: 'o' + i, type: 'image', h: 110}))); const s = spots(); window.COLS = null; "
     "const want = [[0,0,0],[0,0,120],[205,0,0],[205,0,120],[0,1,0],[0,1,120],[205,1,0]]; return L.n === 2 && s.every((o, i) => o.w === 195 && o.x === want[i][0] && o.page === want[i][1] && Math.abs(o.y - want[i][2]) <= 1) && clash().length === 0 "
     "|| JSON.stringify([L.n, s.map((o) => [o.x, o.page, o.y, o.w]), clash()])"),
    ("2단 - 문단은 나누지 않고 통째로 다음 단으로 · 글·커서 위치는 그대로",
     "window.COLS = {count: 2, gap: 10}; const L = load([para('a', 6), para('b', 6), para('c', 6)]); const s = spots(), g = gaps(); sel('c', 5); const c = caret(); bi('insertText', 'X'); run(); const t = txt('c').slice(0, 8); window.COLS = null; "
     "return g === 0 && s[0].x === 0 && s.some((o) => o.x === 205) && clash().length === 0 && c === 'c:5' && t[5] === 'X' && el('c').textContent === txt('c') || JSON.stringify([g, s.map((o) => [o.id, o.x, o.page, o.y]), clash(), c, t])"),
    ("2단 - 긴 문단은 단 경계에서 나뉜다: 1쪽 1단 → 1쪽 2단 → 2쪽 1단 차례로 · 쪽 밖에 걸친 줄 없음 · 글은 그대로 · 뒤 문단은 꼬리 아래(그 자리가 꽉 찼으면 다음 자리 머리)",
     "window.COLS = {count: 2, gap: 10}; " + "const vis = (id) => { const h = el(id).parentNode.getBoundingClientRect(), rg = document.createRange(), w = document.createTreeWalker(el(id), 4), out = []; let n; while ((n = w.nextNode())) { rg.selectNodeContents(n); for (const r of rg.getClientRects()) if (r.width > 0 && r.height > 0) { const y = r.top - h.top, k = Math.floor((y + 1) / 364); out.push([Math.floor((r.left - h.left + 10) / 205), k, Math.round(y - k * 364), Math.round(r.bottom - h.top - k * 364)]); } } return out; }; const slots = (id) => [...new Set(vis(id).map((v) => v[1] + ':' + v[0]))]; const parts = () => [...document.querySelectorAll('.pg-colpart')]; " + "const L = load([para('a', 40), para('b', 3)]); const sa = slots('a'), sb = slots('b'), va = vis('a'), vb = vis('b'); "
     "const lastA = va[va.length - 1], firstB = vb[0], np = parts().length; window.COLS = null; "
     "return np >= 2 && sa[0] === '0:0' && sa.includes('0:1') && sa.includes('1:0') && audit().length === 0 && el('a').textContent === txt('a') "
     "&& sb.length === 1 && (sb[0] === lastA[1] + ':' + lastA[0] ? firstB[2] >= lastA[3] - 1 : firstB[2] <= 2) "
     "|| JSON.stringify({np, sa, sb, lastA, firstB, bad: audit().slice(0, 4), n: L.n})"),
    ("2단 - 나뉜 문단의 꼬리에 커서 · 글 치기: 위치 그대로 · 모델에 들어감 · 다시 나뉨 · 다시 계산하면 그대로",
     "window.COLS = {count: 2, gap: 10}; " + "const vis = (id) => { const h = el(id).parentNode.getBoundingClientRect(), rg = document.createRange(), w = document.createTreeWalker(el(id), 4), out = []; let n; while ((n = w.nextNode())) { rg.selectNodeContents(n); for (const r of rg.getClientRects()) if (r.width > 0 && r.height > 0) { const y = r.top - h.top, k = Math.floor((y + 1) / 364); out.push([Math.floor((r.left - h.left + 10) / 205), k, Math.round(y - k * 364), Math.round(r.bottom - h.top - k * 364)]); } } return out; }; const slots = (id) => [...new Set(vis(id).map((v) => v[1] + ':' + v[0]))]; const parts = () => [...document.querySelectorAll('.pg-colpart')]; " + "load([para('a', 40)]); const off = parseInt(parts()[0]._at, 10), before = txt('a'); sel('a', off + 3); const c = caret(); "
     "bi('insertText', 'X'); const L = run(); const after = txt('a'), c2 = caret(), np = parts().length, same = el('a').textContent === after, bad = audit().length; const L2 = run(); window.COLS = null; "
     "return c === 'a:' + (off + 3) && after === before.slice(0, off + 3) + 'X' + before.slice(off + 3) && same && c2 === 'a:' + (off + 4) && np >= 2 && bad === 0 && L2.changed === 0 "
     "|| JSON.stringify({off, c, c2, np, same, bad, changed: L2.changed, x: after.slice(off, off + 6)})"),
    ("2단 - 글이 줄거나 단 설정을 끄면 조각을 걷는다(나눠 둔 글 조각도 다시 하나로)",
     "window.COLS = {count: 2, gap: 10}; const b = para('a', 40); b.runs = [{t: b.runs[0].t, b: true}]; load([b]); const n1 = document.querySelectorAll('.pg-colpart').length, s1 = el('a').querySelectorAll('[data-pg-split]').length; "
     "window.COLS = null; run(); const n2 = document.querySelectorAll('.pg-colpart').length, s2 = el('a').querySelectorAll('[data-pg-split]').length, g2 = gaps(), spans = el('a').querySelectorAll('span:not(.pg-gap)').length; "
     "window.COLS = {count: 2, gap: 10}; load([para('a', 3)]); const n3 = document.querySelectorAll('.pg-colpart').length; window.COLS = null; "
     "return n1 >= 2 && s1 === n1 && n2 === 0 && s2 === g2 && n3 === 0 && el('a').textContent === txt('a') || JSON.stringify({n1, s1, n2, s2, spans, n3})"),
    ("구역 - 1단 머리 뒤 '여기서부터 2단': 2단 구역은 머리 아래에서 시작 · 다시 1단은 가장 긴 단 아래에서",
     "const L = load([para('h', 2), {id: 's1', type: 'break', kind: 'section', columns: {count: 2, gap: 10}}, {id: 'o1', type: 'image', h: 100}, {id: 'k', type: 'break', kind: 'column'}, {id: 'o2', type: 'image', h: 50}, {id: 'o3', type: 'image', h: 30}, "
     "{id: 's2', type: 'break', kind: 'section', columns: {count: 1}}, para('t', 2)]); const s = Object.fromEntries(spots().map((o) => [o.id, o])); "
     "return s.h.w === 400 && s.o1.w === 195 && s.o1.x === 0 && s.o2.x === 205 && Math.abs(s.o2.y - s.o1.y) <= 1 && s.o3.x === 205 && s.t.w === 400 && s.t.x === 0 && s.t.y >= s.o1.y + 100 && s.t.y >= s.o3.y + 30 && s.t.y <= s.o1.y + 100 + 30 && s.o1.y > s.h.y && clash().length === 0 && L.n === 1 "
     "|| JSON.stringify([L.n, Object.values(s).map((o) => [o.id, o.x, o.y, o.w]), clash()])"),
    ("단 나누기 - 다음 블록이 다음 단 머리 · 단 설정을 끄면(1단) 너비가 되돌아오고 단 나누기는 다음 쪽으로 넘긴다",
     "window.COLS = {count: 2, gap: 10}; load([{id: 'o1', type: 'image', h: 50}, {id: 'k', type: 'break', kind: 'column'}, {id: 'o2', type: 'image', h: 50}]); const a = Object.fromEntries(spots().map((o) => [o.id, o])); "
     "window.COLS = null; run(); const b = Object.fromEntries(spots().map((o) => [o.id, o])); "
     "return a.o2.x === 205 && Math.abs(a.o2.y - a.o1.y) <= 1 && b.o2.x === 0 && b.o2.w === 400 && b.o2.page === 1 && b.o1.page === 0 && el('o2').style.left === '' && el('o2').style.width === '' || JSON.stringify([a.o1, a.o2, b.o1, b.o2].map((o) => [o.x, o.page, o.y, o.w]))"),
    ("글이 줄면 빈 자리를 걷는다",
     "load([para('a', 60)]); DOC.blocks = [para('a', 3)]; ED.refresh(); const L = run(); return L.n === 1 && gaps() === 0 && audit().length === 0 " + D),
    ("밀린 블록 앞이 줄면 밀기를 풀고 위 여백을 되돌린다",
     "load([para('a', 10), {id: 'o', type: 'image', h: 150}]); const m = el('o').style.marginTop; DOC.blocks = [para('a', 2), blk('o')]; ED.refresh(); const L = run(); return m !== '' && L.n === 1 && pushed().length === 0 && el('o').style.marginTop === '' " + D),
    ("clear() - 빈 자리를 모두 걷는다(인쇄 전)",
     "load([para('a', 60), table('t', 30), {id: 'o', type: 'image', h: 280}]); const had = gaps() + gapRows() + pushed().length; FLOW.clear(); return had >= 3 && gaps() === 0 && gapRows() === 0 && pushed().length === 0 && el('a').textContent === txt('a') || JSON.stringify([had, gaps(), gapRows(), pushed()])"),
    ("한글 조합 중에는 고치지 않고, 끝나면 다시 계산한다",
     "load([para('a', 3)]); host.dispatchEvent(new CompositionEvent('compositionstart', {bubbles: true})); DOC.blocks = [blk('a'), para('b', 60)]; LAST = null; FLOW.run(); const mid = LAST; "
     "host.dispatchEvent(new CompositionEvent('compositionend', {bubbles: true, data: ''})); await new Promise((r) => setTimeout(r, 120)); ED.refresh(); const L = run(); return mid === null && L.n >= 3 && audit().length === 0 " + D),
    ("본문 너비가 바뀌면(쪽 설정) 빈 줄을 걷고 다시 잡는다 - 걸친 줄 없음 · 빈 줄은 줄 머리에만",
     "load([para('f', 1), para('a', 60), table('t', 30)]); host.style.width = '560px'; const L = run(); const mid = [...document.querySelectorAll('.pg-gap')].filter((g) => { const p = g.previousSibling, n = g.nextSibling; if (!p || !n) return false; "
     "const a = document.createRange(); a.selectNodeContents(p); const b = document.createRange(); b.selectNodeContents(n); const ra = [...a.getClientRects()].pop(), rb = b.getClientRects()[0]; return ra && rb && Math.abs(ra.top - rb.top) < 2; }).length; "
     "host.style.width = ''; const L2 = run(); const ok = L.n >= 2 && audit().length === 0 && mid === 0; return ok " + D),
    ("끼운 뒤 다시 재서 확인한다 - 처음 끼울 때 2번 재고, 그대로면 1번",
     "const L = load([para('a', 60)]); const first = L.passes; const L2 = run(); return first === 2 && L2.passes === 1 && L2.changed === 0 || JSON.stringify([first, L2.passes, L2.changed])"),
    ("여러 쪽에 걸친 선택으로 지우기 - 모델·화면이 맞고 쪽이 준다",
     "load([para('a', 30), para('b', 30)]); sel('a', 10, 'b', txt('b').length - 5); bi('deleteContentBackward'); const L = run(); return DOC.blocks.length === 1 && el('a').textContent === txt('a') && L.n === 1 && gaps() === 0 " + D),
]


def main():
    page = (HERE / "page_flow_page.html").resolve().as_uri()
    scn = {"base": page.rsplit("/", 1)[0], "pages": [{"url": "/page_flow_page.html", "wait": 300, "steps": [{"name": n, "js": js} for n, js in STEPS]}]}
    with tmpfiles.temp_dir("nx-flow-") as d:
        f = Path(d) / "page_flow_scn.json"
        f.write_text(json.dumps(scn, ensure_ascii=False), "utf-8")
        r = subprocess.run(["node", str(HERE / "smoke.js"), str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(r.stdout)
    if r.returncode:
        print(r.stderr[-1500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
