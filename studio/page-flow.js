// page-flow.js - 페이지 편집기의 실시간 쪽 나눔(PG-102 · docs/dev/page-editor/design.md 10-1)
//   모델(평평한 blocks)과 DOM 구조(#ed 의 자식 = 블록)는 그대로 두고, 쪽 경계에 **빈 자리**만 끼워 넣는다:
//     · 블록째 다음 쪽으로  = 그 블록의 위 여백을 늘린다(push)
//     · 문단 가운데(줄 사이) = 그 줄 앞에 글이 없는 줄(span.pg-gap - 너비 100% inline-block)을 끼운다(split)
//     · 표의 행 사이        = 빈 행(tr.pg-gaprow)을 끼우고, 머리글 행이 있으면 그 사본(tr.pg-headrep)을 다음 쪽 머리에 되풀이한다(row)
//     · 다단 구역의 문단 가운데 = 그 줄부터의 꼬리를 감싸(span.pg-colpart - position relative) **보이는 곳만** 다음 단·다음 쪽 첫 단으로 옮긴다(colsplit).
//       문단의 실제 자리(한 줄기)와 글자 수는 그대로라 편집 엔진이 그대로 돈다. 뒤 블록이 그 이동을 위 여백으로 받는다
//   빈 자리에는 글이 없어 nexa-text 의 위치 계산(글자 수)·한글 조합·선택이 그대로 돈다.
//   NexaPageFlow.plan(items, H, G, linesOf) → {breaks, pages}  순수 계산(시험: tests/page_flow_check.js)
//   NexaPageFlow.create(opts) → {schedule(), run(), clear(), pages()}  화면에 붙이기
(function (root) {
  "use strict";
  const EPS = 0.5;

  /** 쪽 나눔 계산. items = 문서 순서의 블록 [{id, kind: "p"|"table"|"break"|"obj", top, bottom, rows?: [{top, bottom, ok}]}] -
   *  좌표는 **빈 자리를 뺀 자연 위치**(px, 본문 맨 위 = 0). H = 쪽 본문 높이, G = 쪽 본문 사이 거리(아래 여백 + 쪽 틈 + 위 여백).
   *  linesOf(item) → [{top, bottom, fn?}] 그 문단의 줄(넘칠 때만 부른다). 각주: 블록·줄·행의 fn = 달린 각주들의 높이 합, opt.sep = 구분선 높이 -
   *  각주는 그 참조가 놓인 쪽의 아래에 자리를 잡고 본문은 그만큼 덜 들어간다(돌려주는 notes = {쪽: 내준 높이}). 돌려주는 breaks = [{id, type: "push"|"split"|"row", h, gap?, line?, row?}] */
  function plan(items, H, G, linesOf, opt) {
    const out = []; let shift = 0, page = 0, force = false, prevBottom = 0;
    // 각주 - 쪽마다 아래쪽에 각주 자리를 내준다. res[쪽] = 그 쪽에 내준 높이(구분선 SEP 포함). 줄·행·블록의 fn = 거기 달린 각주들의 높이 합
    const res = {}, SEP = (opt && opt.sep) || 0;
    const start = (p) => p * (H + G), end = () => page * (H + G) + H;
    const need = (fn) => (fn > 0 ? fn + (res[page] ? 0 : SEP) : 0);        // 이 쪽에 각주 fn 을 더 놓는 데 드는 높이
    const room = (fn) => end() - (res[page] || 0) - need(fn);                // 그 각주까지 놓고 본문이 쓸 수 있는 아래 끝
    const take = (fn) => { if (fn > 0) res[page] = (res[page] || 0) + need(fn); };
    const untake = (fn) => { if (fn > 0 && res[page]) { res[page] -= fn; if (res[page] <= SEP + EPS) delete res[page]; } };
    const emitPush = (it, h, paged) => {  // 블록의 위 여백으로 실제 자리를 옮긴다. 같은 블록의 밀기는 하나로 합친다
      const last = out[out.length - 1];
      if (last && last.type === "push" && last.id === it.id) { last.h += h; if (paged) last.page = true; }
      else out.push({ id: it.id, type: "push", h, gap: Math.max(0, it.top - prevBottom), page: !!paged });
    };
    const push = (it) => { const top = it.top + shift; page++; const h = start(page) - top; emitPush(it, h, true); shift += h; };
    const settle = (y) => { while (y >= start(page + 1) - EPS) page++; };  // 나눌 수 없는 것이 쪽을 넘겨 버렸을 때 - 놓인 자리의 쪽으로 맞춘다

    function para(it) {
      const L = (linesOf && linesOf(it)) || [], n = L.length; let from = 0;
      if (!n) { if (it.top + shift > start(page) + EPS) push(it); take(it.fn || 0); return; }
      for (let guard = 0; guard < 5000; guard++) {
        let k = from; while (k < n && L[k].bottom + shift <= room(L[k].fn || 0) + EPS) { take(L[k].fn || 0); k++; }
        if (k >= n) return;
        const back = (to) => { while (k > to) { k--; untake(L[k].fn || 0); } };
        if (from === 0 && k < 2) {  // 첫 줄만 남는다(외톨이 줄) - 문단째 다음 쪽으로. 이미 쪽 머리면 한 줄은 둔다
          if (it.top + shift > start(page) + EPS) { back(0); push(it); continue; }
          if (k < 1) { take(L[0].fn || 0); k = 1; }
          if (k >= n) return;
        } else {
          if (n - k < 2 && k - from >= 3) back(n - 2);  // 끝 줄만 넘어간다 - 한 줄 더 데려간다
          if (k === from) { take(L[k].fn || 0); k = from + 1; if (k >= n) return; }  // 쪽 머리인데 한 줄도 안 들어간다(줄·각주가 쪽보다 크다) - 한 줄은 둔다
        }
        const boxTop = (L[k - 1].bottom + L[k].top) / 2;
        page++; const h = start(page) - (boxTop + shift);
        if (h > EPS) { out.push({ id: it.id, type: "split", line: k, h }); shift += h; } else settle(boxTop + shift);
        from = k;
      }
    }
    function table(it) {
      const R = it.rows || []; let from = 0;
      if (!R.length) { if (it.top + shift > start(page) + EPS) push(it); take(it.fn || 0); return; }
      for (let guard = 0; guard < 5000; guard++) {
        let k = from; while (k < R.length && R[k].bottom + shift <= room(R[k].fn || 0) + EPS) { take(R[k].fn || 0); k++; }
        if (k >= R.length) return;
        while (k > from && !R[k].ok) { k--; untake(R[k].fn || 0); }  // 합친 칸이 걸친 행 · 머리글 바로 아래는 나누지 않는다
        if (k === from) {
          if (from === 0 && it.top + shift > start(page) + EPS) { push(it); continue; }
          do { take(R[k].fn || 0); k++; } while (k < R.length && !R[k].ok);
          if (k >= R.length) return;
        }
        page++; const h = start(page) - (R[k].top + shift), hh = it.headH > 0 && it.headH < H / 2 ? it.headH : 0;  // 다음 쪽 머리에 머리글 행을 되풀이할 자리
        if (h > EPS) { out.push({ id: it.id, type: "row", row: k, h, head: hh }); shift += h + hh; } else settle(R[k].top + shift);
        from = k;
      }
    }

    // 다단(PG-101) - 블록의 cols = 그 블록이 놓인 구역의 단 수. 단이 여럿인 구역에서는 블록을 나누지 않고 통째로 다음 단(마지막 단이면 다음 쪽 첫 단)으로 넘긴다.
    //   자연 위치는 "단 너비로 좁힌 한 줄기"로 잰 것이라, 다음 단으로 넘길 때의 밀기는 음수(위로 끌어올림)가 된다. place[id] = 놓인 단(0부터)
    let n = 1, col = 0, regionTop = 0, regionPage = 0, colMax = 0, colMaxPage = 0, forceCol = false;
    const place = {};
    const slotTop = () => (page === regionPage ? regionTop : start(page));
    const mark = (bottom) => { if (colMaxPage !== page) { colMaxPage = page; colMax = start(page); } if (bottom > colMax) colMax = bottom; };
    const shiftTo = (it, y, paged) => { const h = y - (it.top + shift); if (Math.abs(h) > EPS) { emitPush(it, h, paged); shift += h; } };
    const moveSlot = (it, toPage) => { let paged = false; if (!toPage && col < n - 1) col++; else { page++; col = 0; paged = true; } shiftTo(it, slotTop(), paged); };
    // 다단 구역의 문단을 단 경계에서 나눈다(opt.colSplit) - 꼬리 줄들은 **자리를 옮기지 않고 보이는 곳만** 다음 단(마지막 단이면 다음 쪽 첫 단)으로 옮긴다
    //   (colsplit: 그 줄부터를 감싼 조각의 left = dcol × 단 걸음, top = dy). 문단의 실제 자리는 한 줄기 그대로라 그 뒤 블록이 이월분(carry)을 위 여백으로 받는다.
    //   외톨이 줄 규칙 · 각주 자리(줄의 fn - 그 줄이 놓인 쪽의 아래에 자리를 낸다)는 1단의 줄 나눔(para)과 같다. 줄을 잴 수 없는 문단 · nosplit 은 통째로 넘긴다
    let carry = 0;
    function colPara(it) {
      const L = (linesOf && linesOf(it)) || [], m = L.length; let head = col, from = 0, base = 0;  // base = 이 문단 안에서 쌓인 보이는 자리 이동(세로)
      if (m < 2) return false;
      for (let guard = 0; guard < 5000; guard++) {
        let k = from; while (k < m && L[k].bottom + shift <= room(L[k].fn || 0) + EPS) { take(L[k].fn || 0); k++; }
        if (k >= m) break;
        const back = (to) => { while (k > to) { k--; untake(L[k].fn || 0); } };
        if (from === 0 && k < 2) {  // 첫 줄만 남는다 - 문단째 다음 단으로(이미 단 머리면 한 줄은 둔다)
          if (it.top + shift > slotTop() + EPS) { back(0); moveSlot(it); head = col; continue; }
          if (k < 1) { take(L[0].fn || 0); k = 1; }
          if (k >= m) break;
        } else {
          if (m - k < 2 && k - from >= 3) back(m - 2);  // 끝 줄만 넘어간다 - 한 줄 더 데려간다
          if (k === from) { take(L[k].fn || 0); k = from + 1; if (k >= m) break; }  // 단 머리인데 한 줄도 안 들어간다 - 한 줄은 둔다
        }
        mark(L[k - 1].bottom + shift);  // 이 단에 남긴 줄의 끝 - 구역이 바뀔 때 "가장 아래까지 내려간 단"에 들어가야 한다(빠지면 다음 구역이 이 단의 글 위에 겹친다)
        let paged = false; if (col < n - 1) col++; else { page++; col = 0; paged = true; }
        const dy = slotTop() - ((L[k - 1].bottom + L[k].top) / 2 + shift);  // 줄 사이 가운데를 단 머리에 맞춘다(1단의 줄 나눔과 같은 기준) - 글자 상자의 위 끝을 맞추면 줄 간격의 반만큼 올라가 단 머리 밖으로 삐져나온다
        shift += dy; base += dy; carry += dy;
        out.push({ id: it.id, type: "colsplit", line: k, dcol: col - head, dy: base, page: paged });
        from = k;
      }
      place[it.id] = head;
      return true;
    }

    const CS = !!(opt && opt.colSplit);
    for (const it of items) {
      const cn = it.cols > 1 ? it.cols : 1;
      if (Math.abs(carry) > EPS) { emitPush(it, carry, false); carry = 0; }  // 앞 문단이 단을 넘어가며 생긴 이동을 이 블록의 실제 자리로 옮긴다
      if (n === 1 && cn === 1) settle(it.top + shift);
      if (cn !== n) {  // 단 수가 바뀐다 - 지금 쪽에서 가장 아래까지 내려간 단의 끝에서 새 구역이 시작한다
        mark(-Infinity); n = cn; col = 0; regionPage = page; regionTop = colMax + Math.max(0, it.top - prevBottom);  /* 앞 구역 끝 + 블록 사이의 자연 간격 */
        shiftTo(it, regionTop);
      }
      if (force) { if (n > 1) moveSlot(it, true); else push(it); force = false; forceCol = false; }
      if (forceCol) { if (n > 1) moveSlot(it); else push(it); forceCol = false; }
      if (it.kind === "break") { force = true; if (n > 1) place[it.id] = col; mark(it.bottom + shift); prevBottom = it.bottom; continue; }
      if (it.kind === "colbreak") { forceCol = true; if (n > 1) place[it.id] = col; mark(it.bottom + shift); prevBottom = it.bottom; continue; }
      const fn = it.fn || 0;
      if (n > 1) {
        const over = it.bottom + shift > room(fn) + EPS;
        if (over && CS && it.kind === "p" && !it.nosplit && colPara(it)) { /* 단 경계에서 나눴다(각주 자리는 줄마다 잡았다) */ }
        else { if (over && it.top + shift > slotTop() + EPS) moveSlot(it); take(fn); place[it.id] = col; }
      } else if (it.bottom + shift > room(fn) + EPS) {
        if (it.kind === "p") para(it);
        else if (it.kind === "table") table(it);
        else { if (it.top + shift > start(page) + EPS) push(it); take(fn); }
      } else take(fn);
      mark(it.bottom + shift);
      prevBottom = it.bottom;
    }
    if (items.length && n === 1) { const y = items[items.length - 1].bottom + shift; while (y > start(page + 1) + EPS) page++; }
    return { breaks: out, pages: page + 1, notes: res, place };
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

    const kindOf = (el) => (el.classList.contains("nt-p") ? "p" : el.tagName === "TABLE" ? "table" : el.classList.contains("pg-break") ? (el.classList.contains("page") ? "break" : el.classList.contains("column") ? "colbreak" : "obj") : "obj");
    /** 다단 - 블록마다 그 구역의 단 너비로 좁힌다(구역 = 문서의 단 설정 opts.columns(), 구역 나누기 블록 .pg-break.section[data-cols] 뒤부터는 그 설정).
     *  좁힌 한 줄기로 잰 뒤 plan 이 단·쪽에 나눠 놓는다. 단 설정이 바뀐 블록은 끼워 둔 빈 자리를 걷는다 */
    function widths(box, mm) {
      let cur = (opts.columns && opts.columns()) || null;
      for (const el of host.children) {
        if (!el.dataset.id) continue;
        const c = cur && cur.count > 1 ? cur : null, gap = c ? (c.gap === undefined || c.gap === null ? 8 : +c.gap) : 0;
        const w = c ? Math.max(15, (box.cw - (c.count - 1) * gap) / c.count) : 0, k = c ? c.count + ":" + w.toFixed(2) : "";
        if ((el._pgCols || "") !== k) { clearEl(el); el._pgCols = k; el._pgN = c ? c.count : 1; el._pgStep = c ? (w + gap) * mm : 0; el.style.width = c ? w * mm + "px" : ""; }
        if (el.classList.contains("pg-break") && el.classList.contains("section")) cur = { count: +el.dataset.cols || 1, gap: el.dataset.gap === undefined ? undefined : +el.dataset.gap };
      }
    }
    const gapsOf = (el) => [...el.children].filter((c) => c.classList.contains("pg-gap"));
    const partsOf = (el) => [...el.children].filter((c) => c.classList.contains("pg-colpart"));
    /** 단 경계에서 나누지 않을 문단 - 바탕색·테두리가 있거나(상자가 한 단에만 그려진다) 윗주·그림이 든 문단(1차 범위 밖) */
    const noSplit = (el) => !!(el.style.backgroundColor || el.style.border || el.style.borderLeft || el.querySelector("[data-ruby], img, .pg-obj"));

    /** 지금 화면을 잰다 - 끼워 둔 빈 자리를 빼서 자연 위치로 돌려준다. applied = 지금 끼워져 있는 빈 자리 */
    function measure() {
      const hr = host.getBoundingClientRect(), z = hr.width / host.offsetWidth || 1, y = (v) => (v - hr.top) / z;
      let A = 0; const items = [], applied = [];
      const noteH = opts.noteH && host.querySelector("[data-fn]") ? opts.noteH : null;  // 각주가 하나도 없으면 찾지 않는다
      const refsOf = (el) => (noteH ? [...el.querySelectorAll("[data-fn]")].filter((x) => !x.closest(".pg-headrep")).map((span) => ({ span, h: noteH(span) })) : []);
      for (const el of host.children) {
        const id = el.dataset.id; if (!id) continue;
        const r = el.getBoundingClientRect(), own = el._pgPush ? el._pgPush.h : 0;
        if (own) applied.push({ id, type: "push", h: own });
        if (el._pgCol) applied.push({ id, type: "col", at: el._pgCol, h: 0 });
        const it = { id, el, kind: kindOf(el), top: y(r.top) - A - own, base: A + own, z, y };
        it.refs = refsOf(el); it.fn = it.refs.reduce((a, x) => a + x.h, 0); it.cols = el._pgN || 1;
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
            it.rows.push({ top: y(rr.top) - it.base - inner, bottom: y(rr.bottom) - it.base - inner, head: tr.classList.contains("head"), tr, fn: it.refs.reduce((a, x) => a + (tr.contains(x.span) ? x.h : 0), 0) });
          }
          it.rows.forEach((row, i) => { row.ok = !blocked.has(i); });
          let hn = 0; while (hn < it.rows.length && it.rows[hn].head) hn++;  // 맨 위에 이어진 머리글 행만 되풀이한다(Word 의 머리글 행 반복과 같다)
          it.headN = hn < it.rows.length ? hn : 0; it.headH = it.headN ? it.rows[it.headN - 1].bottom - it.rows[0].top : 0;
        } else if (it.kind === "p") {
          for (const g of gapsOf(el)) { inner += g.getBoundingClientRect().height / z; applied.push({ id, type: "split", at: g._off, h: g._h }); }
          for (const w of partsOf(el)) applied.push({ id, type: "colsplit", at: w._at, h: w._dy });  // 보이는 곳만 옮긴 조각 - 실제 높이에는 영향이 없다
          if (it.cols > 1 && noSplit(el)) it.nosplit = true;
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
      const w = doc.createTreeWalker(el, 4 /* SHOW_TEXT */), rg = doc.createRange(), rects = []; let n; it.nodes = []; it.offs = [];
      while ((n = w.nextNode())) {
        const part = n.parentElement && n.parentElement.closest(".pg-colpart"), dy = part && el.contains(part) ? (part._dy || 0) * it.z : 0;  // 단 조각이 세로로 옮겨 보이는 만큼(화면 px)
        it.nodes.push(n); it.offs.push(dy); rg.selectNodeContents(n);
        for (const r of rg.getClientRects()) {
          if (!(r.width > 0 && r.height > 0)) continue;
          const sub = gaps.reduce((a, g) => a + (g.top < r.top ? g.h : 0), 0);
          rects.push({ top: it.y(r.top - dy) - it.base - sub, bottom: it.y(r.bottom - dy) - it.base - sub, rawTop: r.top - dy, rawBottom: r.bottom - dy });
        }
      }
      rects.sort((a, b) => a.top - b.top);
      const lines = []; let cur = null;
      for (const r of rects) {
        if (cur && r.top < cur.bottom - Math.min(r.bottom - r.top, cur.bottom - cur.top) * 0.5) {
          cur.bottom = Math.max(cur.bottom, r.bottom); cur.rawTop = Math.min(cur.rawTop, r.rawTop); cur.rawBottom = Math.max(cur.rawBottom, r.rawBottom);
        } else { cur = { ...r }; lines.push(cur); }
      }
      for (const ref of it.refs || []) {  // 각주 참조가 놓인 줄 - 번호는 그 글 조각의 끝에 붙는다
        const rs = ref.span.getClientRects(), r = rs[rs.length - 1]; if (!r || !lines.length) continue;
        const mid = (r.top + r.bottom) / 2; let best = lines[0];
        for (const ln of lines) if (Math.abs((ln.rawTop + ln.rawBottom) / 2 - mid) < Math.abs((best.rawTop + best.rawBottom) / 2 - mid)) best = ln;
        best.fn = (best.fn || 0) + ref.h;
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
          for (const r of rg.getClientRects()) if (r.height > 0) return (r.top + r.bottom) / 2 - (it.offs ? it.offs[i] : 0);
        }
        return -Infinity;
      };
      let lo = 0, hi = N;
      while (lo < hi) { const m = (lo + hi) >> 1; if (mid(m) > bound) hi = m; else lo = m + 1; }
      return lo;
    }

    function clearEl(el) {
      if (el._pgPush) { el.style.marginTop = el._pgPush.mt; el._pgPush = null; el.classList.remove("pg-pushed"); }
      if (el._pgCol) { el.style.left = ""; if (el._pgPos !== undefined) el.style.position = el._pgPos; el._pgCol = 0; }
      if (el.tagName === "TABLE") { for (const tr of [...el.rows]) if (tr.classList.contains("pg-gaprow") || tr.classList.contains("pg-headrep")) tr.remove(); return; }
      const parts = partsOf(el);
      for (const w of parts) {  // 단 조각 - 안의 것을 제자리로 꺼내고, 나눠 둔 글 조각은 다시 하나로
        const pv = w.previousSibling, first = w.firstChild; w.replaceWith(...w.childNodes);
        if (pv && first && first.dataset && first.dataset.pgSplit && pv.nodeType === 1) { pv.append(...first.childNodes); first.remove(); pv.normalize(); if (pv.dataset.fnHold !== undefined) { pv.dataset.fn = pv.dataset.fnHold; delete pv.dataset.fnHold; } }
      }
      if (parts.length) el.normalize();
      for (const g of gapsOf(el)) {
        const pv = g.previousSibling, nx = g.nextSibling; g.remove();
        if (pv && nx && nx.dataset && nx.dataset.pgSplit) { pv.append(...nx.childNodes); nx.remove(); pv.normalize(); if (pv.dataset.fnHold !== undefined) { pv.dataset.fn = pv.dataset.fnHold; delete pv.dataset.fnHold; } }  // 나눠 둔 글 조각을 다시 하나로
      }
    }
    function put(it, b) {
      const el = it.el;
      if (b.type === "push") {
        // 앞 블록과의 간격을 (자연 간격 + h)로 - 여백은 겹치므로(큰 쪽이 이긴다) 앞 블록의 아래 여백보다 작거나 음수면 그만큼 빼서 준다(다음 단으로 끌어올릴 때)
        const D = b.gap + b.h, pv = el.previousElementSibling, mb = pv ? parseFloat(doc.defaultView.getComputedStyle(pv).marginBottom) || 0 : 0;
        el._pgPush = { h: b.h, mt: el.style.marginTop }; el.style.marginTop = (D >= mb ? D : D - mb) + "px"; if (b.page) el.classList.add("pg-pushed");
        return;
      }
      if (b.type === "col") {  // 놓인 단 - 왼쪽으로 단 너비 + 간격만큼씩(배치만 옮긴다 - 문단의 들여쓰기 여백은 그대로)
        el._pgCol = b.at; el._pgPos = el.style.position; if (doc.defaultView.getComputedStyle(el).position === "static") el.style.position = "relative";
        el.style.left = b.at * (el._pgStep || 0) + "px"; return;
      }
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
      if (b.type === "colsplit") {  // 글자 위치 b.off 부터(다음 조각 앞까지)를 감싸 보이는 곳만 옮긴다 - 뒤에서부터 끼우므로 뒤 조각은 이미 감싸져 있다
        const w0 = doc.createTreeWalker(el, 4); let n0, left0 = b.off;
        while ((n0 = w0.nextNode())) { if (left0 < n0.data.length) break; left0 -= n0.data.length; }
        if (!n0 || (n0.parentElement && n0.parentElement.closest(".pg-colpart"))) return;
        const run = n0.parentNode === el ? n0 : n0.parentNode; let first;
        if (run.parentNode !== el) return;  // 글 조각이 문단의 직계가 아니다(예상 밖의 구조) - 나누지 않는다
        if (left0 === 0 && !n0.previousSibling) first = run;
        else {
          const tail0 = left0 === 0 ? n0 : n0.splitText(left0);
          if (run === n0) first = tail0;
          else {
            const s2 = run.cloneNode(false); s2.dataset.pgSplit = "1";
            if (run.dataset.fn !== undefined) { run.dataset.fnHold = run.dataset.fn; run.removeAttribute("data-fn"); }  // 각주 번호는 뒤쪽 조각에만(줄 나눔과 같다)
            while (tail0.nextSibling) s2.appendChild(tail0.nextSibling); s2.insertBefore(tail0, s2.firstChild); run.after(s2); first = s2;
          }
        }
        const part = doc.createElement("span"); part.className = "pg-colpart"; part._at = b.at; part._dy = b.dy;
        part.style.position = "relative"; part.style.left = b.dcol * (el._pgStep || 0) + "px"; part.style.top = b.dy + "px";
        el.insertBefore(part, first);
        for (let x = first; x && !(x.nodeType === 1 && x.classList.contains("pg-colpart") && x !== part);) { const nx = x.nextSibling; part.appendChild(x); x = nx; }
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
      if (span.dataset.fn !== undefined) { span.dataset.fnHold = span.dataset.fn; span.removeAttribute("data-fn"); }  // 각주 번호는 뒤쪽 조각에만
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
      if (!pass && opts.prepare) opts.prepare();
      widths(box, host.offsetWidth / box.cw);
      // 본문 너비가 바뀌었으면(쪽 설정) 줄 나눔이 달라진다 - 예전 줄 머리에 끼워 둔 빈 줄이 줄 가운데에 남아 그 뒤의 줄을 흩뜨리므로 먼저 걷고 잰다
      if (host.offsetWidth !== lastW || stale) {
        if (lastW || stale) { const sel = opts.saveSel ? opts.saveSel() : null; for (const el of host.children) clearEl(el); if (sel && opts.restoreSel) opts.restoreSel(sel); }
        lastW = host.offsetWidth; stale = false;
      }
      const mm = host.offsetWidth / box.cw, H = box.ch * mm, G = (box.b + box.t) * mm + GAP;
      const m = measure(), p = plan(m.items, H, G, linesOf, { sep: opts.noteSep ? opts.noteSep() : 0, colSplit: !!opts.colSplit }), byId = new Map(m.items.map((it) => [it.id, it]));
      for (const b of p.breaks) {
        if (b.type === "split") b.at = b.off = offsetOfLine(byId.get(b.id), b.line);
        else if (b.type === "row") b.at = b.row;
        else if (b.type === "colsplit") { b.off = offsetOfLine(byId.get(b.id), b.line); b.at = b.off + "/" + b.dcol; b.h = b.dy; }
      }
      for (const id of Object.keys(p.place)) if (p.place[id] > 0) p.breaks.push({ id, type: "col", at: p.place[id], h: 0 });
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
      if (opts.onPages) opts.onPages(pages, { mm, H, G, gap: GAP, changed: todo.length, passes: (pass || 0) + 1, notes: p.notes });
    }
    /** 끼워 둔 빈 자리를 모두 걷는다(인쇄 전 - 인쇄는 브라우저가 쪽을 나눈다) */
    function clear() { clearTimeout(timer); timer = 0; for (const el of host.children) clearEl(el); }
    /** 글꼴이 늦게 뜨는 등 줄 나눔이 통째로 달라졌을 때 - 걷고 처음부터 */
    function reflow() { stale = true; schedule(); }
    /** 지금 바로 걷고 처음부터 다시(인쇄 직전 - 확대를 풀어 줄 나눔이 달라졌을 수 있다) */
    function rerun() { clearTimeout(timer); stale = true; run(0); }
    return { schedule, run: () => run(0), reflow, rerun, clear, pages: () => pages, gap: GAP };
  }

  root.NexaPageFlow = { plan, create };
  if (typeof module !== "undefined" && module.exports) module.exports = root.NexaPageFlow;
})(typeof window !== "undefined" ? window : globalThis);
