// page-flow.js - 페이지 편집기의 실시간 쪽 나눔(PG-102 · docs/dev/page-editor/design.md 10-1)
//   모델(평평한 blocks)과 DOM 구조(#ed 의 자식 = 블록)는 그대로 두고, 쪽 경계에 **빈 자리**만 끼워 넣는다:
//     · 블록째 다음 쪽으로  = 그 블록의 위 여백을 늘린다(push)
//     · 문단 가운데(줄 사이) = 그 줄 앞에 글이 없는 줄(span.pg-gap - 너비 100% inline-block)을 끼운다(split)
//     · 표의 행 사이        = 빈 행(tr.pg-gaprow)을 끼우고, 머리글 행이 있으면 그 사본(tr.pg-headrep)을 다음 쪽 머리에 되풀이한다(row)
//   빈 자리에는 글이 없어 nexa-text 의 위치 계산(글자 수)·한글 조합·선택이 그대로 돈다.
//   NexaPageFlow.plan(items, H, G, linesOf) → {breaks, pages}  순수 계산(시험: tests/page_flow_check.js)
//   NexaPageFlow.create(opts) → {schedule(), run(), clear(), pages()}  화면에 붙이기
(function (root) {
  "use strict";
  const EPS = 0.5;

  /** 쪽 나눔 계산. items = 문서 순서의 블록 [{id, kind: "p"|"table"|"break"|"obj", top, bottom, rows?: [{top, bottom, ok}]}] -
   *  좌표는 **빈 자리를 뺀 자연 위치**(px, 본문 맨 위 = 0). H = 쪽 본문 높이, G = 쪽 본문 사이 거리(아래 여백 + 쪽 틈 + 위 여백).
   *  linesOf(item) → [{top, bottom}] 그 문단의 줄(넘칠 때만 부른다). 돌려주는 breaks = [{id, type: "push"|"split"|"row", h, gap?, line?, row?}] */
  function plan(items, H, G, linesOf) {
    const out = []; let shift = 0, page = 0, force = false, prevBottom = 0;
    const start = (p) => p * (H + G), end = () => page * (H + G) + H;
    const push = (it) => { const top = it.top + shift; page++; const h = start(page) - top; out.push({ id: it.id, type: "push", h, gap: Math.max(0, it.top - prevBottom) }); shift += h; };
    const settle = (y) => { while (y >= start(page + 1) - EPS) page++; };  // 나눌 수 없는 것이 쪽을 넘겨 버렸을 때 - 놓인 자리의 쪽으로 맞춘다

    function para(it) {
      const L = (linesOf && linesOf(it)) || [], n = L.length; let from = 0;
      if (!n) { if (it.top + shift > start(page) + EPS) push(it); return; }
      for (let guard = 0; guard < 5000; guard++) {
        let k = from; while (k < n && L[k].bottom + shift <= end() + EPS) k++;
        if (k >= n) return;
        if (from === 0 && k < 2) {  // 첫 줄만 남는다(외톨이 줄) - 문단째 다음 쪽으로. 이미 쪽 머리면 한 줄은 둔다
          if (it.top + shift > start(page) + EPS) { push(it); continue; }
          k = 1; if (k >= n) return;
        } else {
          if (n - k < 2 && k - from >= 3) k = n - 2;  // 끝 줄만 넘어간다 - 한 줄 더 데려간다
          if (k === from) { k = from + 1; if (k >= n) return; }  // 쪽 머리인데 한 줄도 안 들어간다(줄이 쪽보다 크다) - 한 줄은 둔다
        }
        const boxTop = (L[k - 1].bottom + L[k].top) / 2;
        page++; const h = start(page) - (boxTop + shift);
        if (h > EPS) { out.push({ id: it.id, type: "split", line: k, h }); shift += h; } else settle(boxTop + shift);
        from = k;
      }
    }
    function table(it) {
      const R = it.rows || []; let from = 0;
      if (!R.length) { if (it.top + shift > start(page) + EPS) push(it); return; }
      for (let guard = 0; guard < 5000; guard++) {
        let k = from; while (k < R.length && R[k].bottom + shift <= end() + EPS) k++;
        if (k >= R.length) return;
        while (k > from && !R[k].ok) k--;  // 합친 칸이 걸친 행 · 머리글 바로 아래는 나누지 않는다
        if (k === from) {
          if (from === 0 && it.top + shift > start(page) + EPS) { push(it); continue; }
          k = from + 1; while (k < R.length && !R[k].ok) k++;
          if (k >= R.length) return;
        }
        page++; const h = start(page) - (R[k].top + shift), hh = it.headH > 0 && it.headH < H / 2 ? it.headH : 0;  // 다음 쪽 머리에 머리글 행을 되풀이할 자리
        if (h > EPS) { out.push({ id: it.id, type: "row", row: k, h, head: hh }); shift += h + hh; } else settle(R[k].top + shift);
        from = k;
      }
    }

    for (const it of items) {
      settle(it.top + shift);
      if (force) { push(it); force = false; }
      if (it.kind === "break") { force = true; prevBottom = it.bottom; continue; }
      if (it.bottom + shift > end() + EPS) {
        if (it.kind === "p") para(it);
        else if (it.kind === "table") table(it);
        else if (it.top + shift > start(page) + EPS) push(it);
      }
      prevBottom = it.bottom;
    }
    if (items.length) { const y = items[items.length - 1].bottom + shift; while (y > start(page + 1) + EPS) page++; }
    return { breaks: out, pages: page + 1 };
  }

  /** 화면에 붙인다. opts: host(#ed) · box() → NexaPage.pageBox · gap 쪽 사이 틈(px) · off() → true 면 쉰다(인쇄)
   *  saveSel() / restoreSel(sel) 빈 자리를 고칠 때 선택 지키기 · onPages(n, {mm, H, G, gap}) 쪽 수·치수가 정해질 때마다 */
  function create(opts) {
    const host = opts.host, doc = host.ownerDocument, GAP = opts.gap || 24;
    let timer = 0, composing = false, pages = 1, lastW = 0, stale = false;
    const schedule = () => { if (!timer) timer = setTimeout(() => run(0), 16); };
    host.addEventListener("compositionstart", () => { composing = true; });
    host.addEventListener("compositionend", () => { composing = false; schedule(); });
    host.addEventListener("load", schedule, true);  // 그림이 늦게 뜨면 높이가 달라진다

    const kindOf = (el) => (el.classList.contains("nt-p") ? "p" : el.tagName === "TABLE" ? "table" : el.classList.contains("pg-break") ? (el.classList.contains("page") ? "break" : "obj") : "obj");
    const gapsOf = (el) => [...el.children].filter((c) => c.classList.contains("pg-gap"));

    /** 지금 화면을 잰다 - 끼워 둔 빈 자리를 빼서 자연 위치로 돌려준다. applied = 지금 끼워져 있는 빈 자리 */
    function measure() {
      const hr = host.getBoundingClientRect(), z = hr.width / host.offsetWidth || 1, y = (v) => (v - hr.top) / z;
      let A = 0; const items = [], applied = [];
      for (const el of host.children) {
        const id = el.dataset.id; if (!id) continue;
        const r = el.getBoundingClientRect(), own = el._pgPush ? el._pgPush.h : 0;
        if (own) applied.push({ id, type: "push", h: own });
        const it = { id, el, kind: kindOf(el), top: y(r.top) - A - own, base: A + own, z, y };
        let inner = 0;
        if (it.kind === "table") {
          it.rows = []; let gapRow = null, prevRaw = null; const blocked = new Set();
          for (const tr of el.rows) {
            if (tr.classList.contains("pg-gaprow") || tr.classList.contains("pg-headrep")) { gapRow = gapRow || tr; continue; }
            const rr = tr.getBoundingClientRect(), i = it.rows.length;
            if (gapRow && prevRaw !== null) { inner += Math.max(0, y(rr.top) - prevRaw); applied.push({ id, type: "row", at: i, h: gapRow._h }); }
            gapRow = null; prevRaw = y(rr.bottom);
            for (const c of tr.cells) for (let s = 1; s < (c.rowSpan || 1); s++) blocked.add(i + s);
            if (i > 0 && it.rows[i - 1].head) blocked.add(i);
            it.rows.push({ top: y(rr.top) - it.base - inner, bottom: y(rr.bottom) - it.base - inner, head: tr.classList.contains("head"), tr });
          }
          it.rows.forEach((row, i) => { row.ok = !blocked.has(i); });
          let hn = 0; while (hn < it.rows.length && it.rows[hn].head) hn++;  // 맨 위에 이어진 머리글 행만 되풀이한다(Word 의 머리글 행 반복과 같다)
          it.headN = hn < it.rows.length ? hn : 0; it.headH = it.headN ? it.rows[it.headN - 1].bottom - it.rows[0].top : 0;
        } else if (it.kind === "p") {
          for (const g of gapsOf(el)) { inner += g.getBoundingClientRect().height / z; applied.push({ id, type: "split", at: g._off, h: g._h }); }
        }
        it.bottom = y(r.bottom) - A - own - inner;
        A += own + inner; items.push(it);
      }
      return { items, applied };
    }
    /** 문단의 줄 - 글 조각의 사각형을 세로로 겹치는 것끼리 묶는다. raw = 화면 좌표(줄 머리 글자 찾기용) */
    function linesOf(it) {
      if (it.lines) return it.lines;
      const el = it.el, gaps = gapsOf(el).map((g) => { const r = g.getBoundingClientRect(); return { top: r.top, h: r.height / it.z }; });
      const w = doc.createTreeWalker(el, 4 /* SHOW_TEXT */), rg = doc.createRange(), rects = []; let n; it.nodes = [];
      while ((n = w.nextNode())) {
        it.nodes.push(n); rg.selectNodeContents(n);
        for (const r of rg.getClientRects()) {
          if (!(r.width > 0 && r.height > 0)) continue;
          const sub = gaps.reduce((a, g) => a + (g.top < r.top ? g.h : 0), 0);
          rects.push({ top: it.y(r.top) - it.base - sub, bottom: it.y(r.bottom) - it.base - sub, rawTop: r.top, rawBottom: r.bottom });
        }
      }
      rects.sort((a, b) => a.top - b.top);
      const lines = []; let cur = null;
      for (const r of rects) {
        if (cur && r.top < cur.bottom - Math.min(r.bottom - r.top, cur.bottom - cur.top) * 0.5) {
          cur.bottom = Math.max(cur.bottom, r.bottom); cur.rawTop = Math.min(cur.rawTop, r.rawTop); cur.rawBottom = Math.max(cur.rawBottom, r.rawBottom);
        } else { cur = { ...r }; lines.push(cur); }
      }
      return (it.lines = lines);
    }
    /** k 번째 줄의 첫 글자 위치(문단 안의 글자 수) - 글자의 세로 가운데가 줄 경계 아래인 첫 글자를 이분 탐색으로 */
    function offsetOfLine(it, k) {
      const L = it.lines, bound = (L[k - 1].rawBottom + L[k].rawTop) / 2, nodes = it.nodes, starts = []; let N = 0;
      for (const n of nodes) { starts.push(N); N += n.data.length; }
      const rg = doc.createRange();
      const mid = (o) => {  // 사각형이 없는 글자(줄바꿈·접힌 공백)는 앞 글자의 줄로 본다
        for (; o >= 0; o--) {
          let i = starts.length - 1; while (i > 0 && starts[i] > o) i--;
          const local = o - starts[i]; if (local >= nodes[i].data.length) continue;
          rg.setStart(nodes[i], local); rg.setEnd(nodes[i], local + 1);
          for (const r of rg.getClientRects()) if (r.height > 0) return (r.top + r.bottom) / 2;
        }
        return -Infinity;
      };
      let lo = 0, hi = N;
      while (lo < hi) { const m = (lo + hi) >> 1; if (mid(m) > bound) hi = m; else lo = m + 1; }
      return lo;
    }

    function clearEl(el) {
      if (el._pgPush) { el.style.marginTop = el._pgPush.mt; el._pgPush = null; }
      if (el.tagName === "TABLE") { for (const tr of [...el.rows]) if (tr.classList.contains("pg-gaprow") || tr.classList.contains("pg-headrep")) tr.remove(); return; }
      for (const g of gapsOf(el)) {
        const pv = g.previousSibling, nx = g.nextSibling; g.remove();
        if (pv && nx && nx.dataset && nx.dataset.pgSplit) { pv.append(...nx.childNodes); nx.remove(); pv.normalize(); }  // 나눠 둔 글 조각을 다시 하나로
      }
    }
    function put(it, b) {
      const el = it.el;
      if (b.type === "push") { el._pgPush = { h: b.h, mt: el.style.marginTop }; el.style.marginTop = (b.gap + b.h) + "px"; return; }
      if (b.type === "row") {
        const row = it.rows[b.row]; if (!row || !row.tr.isConnected) return;
        const tr = doc.createElement("tr"), td = doc.createElement("td"); tr.className = "pg-gaprow"; tr.contentEditable = "false"; tr._h = b.h;
        td.colSpan = [...row.tr.parentNode.rows].reduce((m, r) => Math.max(m, [...r.cells].reduce((a, c) => a + (c.colSpan || 1), 0)), 1);
        const bw = parseFloat(doc.defaultView.getComputedStyle(row.tr.cells[0] || row.tr).borderTopWidth) || 0;
        td.style.height = Math.max(0, b.h - bw) + "px"; tr.appendChild(td); row.tr.before(tr);
        if (b.head) for (let k = 0; k < it.headN; k++) {  // 머리글 행의 사본 - 보이기만 한다(고칠 수 없고 id 가 없다). 머리글을 고치면 다음에 다시 끼울 때 따라온다
          const c = it.rows[k].tr.cloneNode(true); c.classList.add("pg-headrep"); c.removeAttribute("data-id"); c.contentEditable = "false";
          for (const x of c.querySelectorAll("[data-id], [contenteditable]")) { x.removeAttribute("data-id"); x.removeAttribute("contenteditable"); x.classList.remove("nt-host"); }
          row.tr.before(c);
        }
        // 실제로 벌어진 만큼을 재서 맞춘다 - 테두리 겹침(border-collapse)·box-sizing 에 따라 빈 행이 차지하는 높이가 준 값과 조금 다르다
        let prev = tr.previousElementSibling; while (prev && (prev.classList.contains("pg-gaprow") || prev.classList.contains("pg-headrep"))) prev = prev.previousElementSibling;
        if (prev) { const diff = b.h + (b.head || 0) - (row.tr.getBoundingClientRect().top - prev.getBoundingClientRect().bottom) / it.z; if (Math.abs(diff) > 0.05) td.style.height = Math.max(0, parseFloat(td.style.height) + diff) + "px"; }
        return;
      }
      // split - 글자 위치 b.off 앞에 빈 줄을 끼운다. 글 조각 가운데면 조각을 둘로 나눈다(윗주는 앞 조각에만 남긴다)
      const g = doc.createElement("span"); g.className = "pg-gap"; g.contentEditable = "false"; g.style.height = b.h + "px"; g._off = b.off; g._h = b.h;
      const w = doc.createTreeWalker(el, 4); let n, left = b.off;
      while ((n = w.nextNode())) { if (left < n.data.length) break; left -= n.data.length; }
      if (!n) return;
      const span = n.parentNode === el ? n : n.parentNode;
      if (left === 0 && !n.previousSibling) { el.insertBefore(g, span); return; }
      const tail = left === 0 ? n : n.splitText(left);
      if (span === n) { el.insertBefore(g, tail); return; }
      const s2 = span.cloneNode(false); s2.dataset.pgSplit = "1"; s2.removeAttribute("data-ruby");
      while (tail.nextSibling) s2.appendChild(tail.nextSibling);
      s2.insertBefore(tail, s2.firstChild); span.after(s2); el.insertBefore(g, s2);
    }
    const key = (list, id) => list.filter((b) => b.id === id).map((b) => `${b.type}:${b.at === undefined ? "" : b.at}`).join(",");
    const near = (a, b) => a.length === b.length && a.every((x, i) => Math.abs(x.h - b[i].h) <= 1.5);

    function run(pass) {
      timer = 0;
      if (composing) return;
      if (opts.off && opts.off()) return;
      const box = opts.box(); if (!box || !host.offsetWidth) return;
      // 본문 너비가 바뀌었으면(쪽 설정) 줄 나눔이 달라진다 - 예전 줄 머리에 끼워 둔 빈 줄이 줄 가운데에 남아 그 뒤의 줄을 흩뜨리므로 먼저 걷고 잰다
      if (host.offsetWidth !== lastW || stale) {
        if (lastW || stale) { const sel = opts.saveSel ? opts.saveSel() : null; for (const el of host.children) clearEl(el); if (sel && opts.restoreSel) opts.restoreSel(sel); }
        lastW = host.offsetWidth; stale = false;
      }
      const mm = host.offsetWidth / box.cw, H = box.ch * mm, G = (box.b + box.t) * mm + GAP;
      const m = measure(), p = plan(m.items, H, G, linesOf), byId = new Map(m.items.map((it) => [it.id, it]));
      for (const b of p.breaks) { if (b.type === "split") b.at = b.off = offsetOfLine(byId.get(b.id), b.line); else if (b.type === "row") b.at = b.row; }
      // 블록마다 - 끼워 둔 것과 끼울 것이 다를 때만 고친다(글을 치는 동안 쓸데없이 DOM 을 건드리지 않게)
      const ids = new Set([...m.applied, ...p.breaks].map((b) => b.id)), todo = [];
      for (const id of ids) {
        const a = m.applied.filter((b) => b.id === id), d = p.breaks.filter((b) => b.id === id);
        if (key(m.applied, id) !== key(p.breaks, id) || !near(a, d)) todo.push([byId.get(id), d]);
      }
      if (todo.length) {
        const sel = opts.saveSel ? opts.saveSel() : null;
        for (const [it] of todo) clearEl(it.el);
        for (const [it, d] of todo) for (const b of [...d].reverse()) put(it, b);  // 뒤에서부터 - 앞의 글자 위치·행이 그대로다
        if (sel && opts.restoreSel) opts.restoreSel(sel);
        if ((pass || 0) < 3) return run((pass || 0) + 1);  // 끼운 뒤 다시 재서 확인한다 - 어긋난 데가 없으면 고칠 것이 없어 여기서 끝난다
      }
      pages = p.pages;
      if (opts.onPages) opts.onPages(pages, { mm, H, G, gap: GAP, changed: todo.length, passes: (pass || 0) + 1 });
    }
    /** 끼워 둔 빈 자리를 모두 걷는다(인쇄 전 - 인쇄는 브라우저가 쪽을 나눈다) */
    function clear() { clearTimeout(timer); timer = 0; for (const el of host.children) clearEl(el); }
    /** 글꼴이 늦게 뜨는 등 줄 나눔이 통째로 달라졌을 때 - 걷고 처음부터 */
    function reflow() { stale = true; schedule(); }
    return { schedule, run: () => run(0), reflow, clear, pages: () => pages, gap: GAP };
  }

  root.NexaPageFlow = { plan, create };
  if (typeof module !== "undefined" && module.exports) module.exports = root.NexaPageFlow;
})(typeof window !== "undefined" ? window : globalThis);
