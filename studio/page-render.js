// 페이지 문서(kind = "page") 그리기 - 블록 → DOM. 편집기(page.js)·인쇄 미리 보기(page-print.html)가 같이 쓴다.
//   규칙은 서버 page_doc.py 와 같다(스타일 상속 · 목록 머리 기호 · 쪽 상자) - tests/page_render_check.js 가 같은 사례로 맞춘다.
//   NexaPage.styleOf(doc, name) · markers(blocks) · pageBox(doc) · blockCss(doc, block, ctx) → 인라인 스타일 객체
//          decorate(el, block, doc, ctx, marker) 문단 요소 꾸미기(NexaText.mount 의 decorate 로 쓴다)
//          blockEl(doc, block, ctx) 글이 아닌 블록(표·그림·나누기)의 요소 · renderInto(host, doc, blocks, ctx) 통째로 그리기(편집 없음)
//   ctx: { color(c), font(f) } 토큰 → CSS 값, asset(src) → 그림 주소
(function (root) {
  "use strict";
  const SIZES = { A4: [210, 297], A5: [148, 210], B5: [182, 257], Letter: [215.9, 279.4], Legal: [215.9, 355.6] };  // mm(세로 방향)
  const DEFAULT_MARGIN = { t: 25, r: 20, b: 25, l: 20 };
  const LIST_INDENT = 6;  // mm - 목록 한 단계의 들여쓰기(머리 기호 자리 포함)

  /** 쪽 크기와 본문 영역(mm) - {w, h, t, r, b, l, cw, ch} */
  function pageBox(doc) {
    const page = doc.page || {}, size = page.size || "A4";
    let [w, h] = SIZES[size] || [size.w, size.h];
    if (page.orient === "landscape") [w, h] = [h, w];
    const m = { ...DEFAULT_MARGIN, ...(page.margin || {}) };
    return { w, h, t: m.t, r: m.r, b: m.b, l: m.l, cw: w - m.l - m.r, ch: h - m.t - m.b };
  }
  /** 스타일의 상속(based)을 풀어 한 벌로 - 없는 이름은 body */
  function styleOf(doc, name) {
    const styles = doc.styles || {}, chain = [], seen = new Set();
    let cur = name && styles[name] ? name : "body";
    while (cur && styles[cur] && !seen.has(cur)) { seen.add(cur); chain.push(styles[cur]); cur = styles[cur].based; }
    const out = {};
    for (const st of chain.reverse()) for (const [k, v] of Object.entries(st)) if (k !== "based" && k !== "name") out[k] = v;
    return out;
  }
  function numberLabel(n, level) {
    const kind = level % 3;
    if (kind === 0) return n + ".";
    if (kind === 1) { let s = ""; while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(97 + r) + s; n = Math.floor((n - 1) / 26); } return s + "."; }
    let out = "";
    for (const [v, t] of [[1000, "m"], [900, "cm"], [500, "d"], [400, "cd"], [100, "c"], [90, "xc"], [50, "l"], [40, "xl"], [10, "x"], [9, "ix"], [5, "v"], [4, "iv"], [1, "i"]]) while (n >= v) { out += t; n -= v; }
    return out + ".";
  }
  /** 목록 문단의 머리 기호 {id: 글} - 번호는 이어진 목록 문단 안에서 단계별로 센다(끊기거나 restart 면 1부터) */
  function markers(blocks) {
    const out = {}; let counts = {}, prev = null;
    for (const b of blocks || []) {
      const ls = b && b.type === "p" ? b.list : null;
      if (!ls) { counts = {}; prev = null; continue; }
      const lv = ls.level || 0;
      if (!prev || ls.restart) counts = {};
      for (const k of Object.keys(counts)) if (+k > lv) delete counts[k];
      if (ls.kind === "number") { counts[lv] = (counts[lv] || 0) + 1; out[b.id] = numberLabel(counts[lv], lv); }
      else if (ls.kind === "check") out[b.id] = ls.done ? "☑" : "☐";
      else out[b.id] = "•◦▪"[lv % 3];
      prev = ls;
    }
    return out;
  }

  /** 문단의 CSS(스타일 + 문단 속성) - 길이 mm · 글자 pt 그대로(인쇄 치수) */
  function blockCss(doc, block, ctx = {}) {
    const st = styleOf(doc, block.style), css = {};
    if (st.font) css.fontFamily = ctx.font ? ctx.font(st.font) : st.font;
    if (st.size) css.fontSize = st.size + "pt";
    if (st.bold) css.fontWeight = "700";
    if (st.italic) css.fontStyle = "italic";
    if (st.color) css.color = ctx.color ? ctx.color(st.color) : st.color;
    const line = block.line !== undefined ? block.line : st.line;  // 문단이 직접 정한 줄 간격이 스타일보다 먼저
    if (line) css.lineHeight = String(line);
    css.marginTop = (st.before || 0) + "pt"; css.marginBottom = (st.after || 0) + "pt";
    const align = block.align || st.align; if (align) css.textAlign = align;
    const lv = block.list ? (block.list.level || 0) + 1 : 0;
    const indent = (block.indent !== undefined ? block.indent : st.indent || 0) + lv * LIST_INDENT;
    if (indent) css.paddingLeft = indent + "mm";
    const fill = block.fill !== undefined ? block.fill : st.fill;  // 문단 음영 - 배경색(상자처럼 보이게 안쪽 여백을 조금 둔다)
    if (fill) { css.backgroundColor = ctx.color ? ctx.color(fill) : fill; css.paddingRight = "2mm"; css.paddingLeft = (indent + 2) + "mm"; css.paddingTop = "1mm"; css.paddingBottom = "1mm"; }
    if (block.first !== undefined || st.first) css.textIndent = (block.first !== undefined ? block.first : st.first) + "mm";
    return css;
  }
  /** 문단 요소 꾸미기 - 스타일·정렬·들여쓰기와 목록 머리 기호(::before 가 data-marker 를 그린다) */
  function decorate(el, block, doc, ctx, marker) {
    Object.assign(el.style, blockCss(doc, block, ctx));
    el.classList.add("pg-p"); if (block.style) el.dataset.style = block.style;
    if (block.list) { el.classList.add("pg-li"); el.dataset.marker = marker || ""; el.dataset.list = block.list.kind; if (block.list.done) el.classList.add("done"); }
  }

  /** 표 테두리 종류의 클래스 - border: none(배치용, 테두리 없음) · inner-v(칸 사이 세로선만) */
  const tableClass = (b) => (b.border === "none" ? " pg-noborder" : b.border === "inner-v" ? " pg-noborder pg-innerv" : "");
  function tableEl(doc, b, ctx) {
    const d = (ctx && ctx.document) || document, t = d.createElement("table"); t.className = "pg-table" + tableClass(b);
    const total = b.cols.reduce((a, c) => a + c, 0) || 1, cg = d.createElement("colgroup");
    for (const c of b.cols) { const col = d.createElement("col"); col.style.width = (c / total * 100).toFixed(3) + "%"; cg.appendChild(col); }
    t.appendChild(cg);
    const body = d.createElement("tbody");
    for (const row of b.rows) {
      const tr = d.createElement("tr"); tr.dataset.id = row.id; if (row.head) tr.className = "head";
      for (const c of row.cells) {
        const td = d.createElement(row.head ? "th" : "td"); td.dataset.id = c.id;
        if (c.colspan > 1) td.colSpan = c.colspan; if (c.rowspan > 1) td.rowSpan = c.rowspan;
        if (c.fill) td.style.backgroundColor = ctx && ctx.color ? ctx.color(c.fill) : c.fill;
        if (c.valign) td.style.verticalAlign = c.valign;
        renderInto(td, doc, c.blocks && c.blocks.length ? c.blocks : [{ id: c.id + "-p", type: "p", runs: [] }], ctx);
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
    t.appendChild(body);
    return t;
  }
  /** 표의 칸이 놓인 격자 열 번호 - 행마다 [{c: 칸, col: 시작 열}]. 위에서 내려온 세로 병합(rowspan)이 차지한 열은 건너뛴다(export_docx.py 의 표 배치와 같은 규칙) */
  function tableGrid(t) {
    const busy = {}, out = [];  // busy[열] = 그 열이 위의 칸에 잡혀 있는 남은 행 수
    for (const row of t.rows || []) {
      const line = []; let col = 0;
      for (const c of row.cells || []) {
        while (busy[col] > 0) col++;
        line.push({ c, col });
        const span = c.colspan > 1 ? c.colspan : 1;
        if (c.rowspan > 1) for (let k = 0; k < span; k++) busy[col + k] = c.rowspan;  // 이 행 것까지 센다(아래에서 1 뺀다)
        col += span;
      }
      for (const k of Object.keys(busy)) if (busy[k] > 0) busy[k]--;
      out.push(line);
    }
    return out;
  }
  /** 글이 아닌 블록의 요소 - 표 · 그림 · 나누기 */
  function blockEl(doc, b, ctx = {}) {
    const d = ctx.document || document; let el;
    if (b.type === "table") el = tableEl(doc, b, ctx);
    else if (b.type === "image") {
      el = d.createElement("div"); el.className = "pg-image"; el.style.textAlign = b.align || "center";
      const img = d.createElement("img"); img.src = ctx.asset ? ctx.asset(b.src) : b.src; img.alt = b.alt || "";
      if (b.w) img.style.width = b.w + "mm"; if (b.h) img.style.height = b.h + "mm";
      el.appendChild(img);
      if (b.caption) { const c = d.createElement("div"); c.className = "pg-caption"; c.textContent = b.caption; Object.assign(c.style, blockCss(doc, { style: "caption" }, ctx)); el.appendChild(c); }
    } else { el = d.createElement("div"); el.className = "pg-break " + (b.kind || "page"); el.dataset.label = { page: "쪽 나누기", column: "단 나누기", section: "구역 나누기" }[b.kind || "page"];
      if (b.kind === "section") { const c = b.columns || {}, n = c.count > 1 ? c.count : 1; el.dataset.cols = n; if (c.gap !== undefined) el.dataset.gap = c.gap; el.dataset.label = `여기서부터 ${n}단`; } }
    el.dataset.id = b.id;
    return el;
  }
  // ---------------------------------------------------------------- 개체(도형·글 상자) - export_docx.py 의 _object 와 같은 모양·기본값
  const OBJ_CLOSED = ["rect", "round", "ellipse"], OBJ_LINES = ["line", "arrow"], PT = 0.3528;  // 1pt = 0.3528mm
  const safeColor = (c, ctx, dflt) => { const v = c && ctx.color ? ctx.color(c) : c; return typeof v === "string" && /^(#[0-9a-fA-F]{3,8}|[a-zA-Z]+|var\(--[\w-]+\))$/.test(v) ? v : dflt; };
  const f2 = (v) => Math.round(v * 100) / 100;
  /** 개체의 모양 → SVG 글(단위 mm). 선 = 기본 1pt #333(line: null 이면 없음) · 채움은 닫힌 도형만 */
  function objectSvg(o, ctx = {}) {
    const w = Math.max(o.w || 0, 0.01), h = Math.max(o.h || 0, 0.01), ln = o.line === null ? null : o.line || {};
    const sw = ln ? (ln.w === undefined ? 1 : ln.w) * PT : 0, stroke = ln && sw > 0 ? safeColor(ln.c, ctx, "#333333") : "none";
    const dash = !ln || !sw ? "" : ln.dash === "dash" ? ` stroke-dasharray="${f2(sw * 4)} ${f2(sw * 3)}"` : ln.dash === "dot" ? ` stroke-dasharray="${f2(sw)} ${f2(sw * 2)}"` : "";
    const fill = OBJ_CLOSED.includes(o.shape) && o.fill ? safeColor(o.fill, ctx, "none") : "none";
    const at = `fill="${fill}" stroke="${stroke}" stroke-width="${f2(sw)}"${dash} stroke-linecap="round" stroke-linejoin="round"`, i = sw / 2;
    let body;
    if (o.shape === "rect" || o.shape === "round") { const r = o.shape === "round" ? Math.min(w, h) / 6 : 0; body = `<rect x="${f2(i)}" y="${f2(i)}" width="${f2(Math.max(0, w - sw))}" height="${f2(Math.max(0, h - sw))}" rx="${f2(r)}" ${at}/>`; }
    else if (o.shape === "ellipse") body = `<ellipse cx="${f2(w / 2)}" cy="${f2(h / 2)}" rx="${f2(Math.max(0, (w - sw) / 2))}" ry="${f2(Math.max(0, (h - sw) / 2))}" ${at}/>`;
    else if (OBJ_LINES.includes(o.shape)) {
      const W = o.w || 0, Hh = o.h || 0, y1 = o.flip ? Hh : 0, y2 = o.flip ? 0 : Hh;
      body = `<line x1="0" y1="${f2(y1)}" x2="${f2(W)}" y2="${f2(y2)}" ${at}/>`;
      if (o.shape === "arrow") {
        const a = Math.atan2(y2 - y1, W), len = Math.max(2, sw * 5), wd = len * 0.4, bx = W - len * Math.cos(a), by = y2 - len * Math.sin(a);
        body += `<polygon points="${f2(W)},${f2(y2)} ${f2(bx - wd * Math.sin(a))},${f2(by + wd * Math.cos(a))} ${f2(bx + wd * Math.sin(a))},${f2(by - wd * Math.cos(a))}" fill="${stroke}" stroke="none"/>`;
      }
    } else {
      const brace = o.shape.startsWith("brace"), r = Math.min(brace ? w / 2 : w, h / (brace ? 4 : 2)), m = w / 2;
      const d = brace ? `M ${f2(w)},0 Q ${f2(m)},0 ${f2(m)},${f2(r)} L ${f2(m)},${f2(h / 2 - r)} Q ${f2(m)},${f2(h / 2)} 0,${f2(h / 2)} Q ${f2(m)},${f2(h / 2)} ${f2(m)},${f2(h / 2 + r)} L ${f2(m)},${f2(h - r)} Q ${f2(m)},${f2(h)} ${f2(w)},${f2(h)}`
        : `M ${f2(w)},0 Q 0,0 0,${f2(r)} L 0,${f2(h - r)} Q 0,${f2(h)} ${f2(w)},${f2(h)}`;
      body = `<path d="${d}" ${at}/>`;
      if (o.shape.endsWith("-r")) body = `<g transform="translate(${f2(w)},0) scale(-1,1)">${body}</g>`;
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${f2(w)} ${f2(h)}" width="${f2(w)}mm" height="${f2(h)}mm" aria-hidden="true">${body}</svg>`;
  }
  /** 개체의 요소(자리는 부르는 쪽이 잡는다) - 모양(SVG) + 안의 글(.pg-obj-text > .pg-obj-body). ctx.noText 면 글은 그리지 않는다(편집기가 붙인다) */
  function objectEl(doc, o, ctx = {}) {
    const d = ctx.document || document, el = d.createElement("div");
    el.className = "pg-obj " + o.shape; el.dataset.id = o.id; el.style.width = (o.w || 0) + "mm"; el.style.height = (o.h || 0) + "mm";
    el.innerHTML = objectSvg(o, ctx);
    if (Array.isArray(o.blocks) && !OBJ_LINES.includes(o.shape)) {
      const t = d.createElement("div"); t.className = "pg-obj-text"; t.style.padding = (o.pad === undefined ? 1.5 : o.pad) + "mm";
      t.style.justifyContent = { middle: "center", bottom: "flex-end" }[o.valign] || "flex-start";
      const inner = d.createElement("div"); inner.className = "pg-obj-body"; if (!ctx.noText) renderInto(inner, doc, o.blocks, ctx);
      t.appendChild(inner); el.appendChild(t);
    }
    return el;
  }
  /** 블록들을 host 에 통째로 그린다(편집 없음 - 미리 보기·인쇄·표 셀) */
  function renderInto(host, doc, blocks, ctx = {}) {
    const d = ctx.document || document, mk = markers(blocks), T = root.NexaText;
    for (const b of blocks || []) {
      if (b.type === "p") {
        const el = d.createElement("div"); el.className = "nt-p"; el.dataset.id = b.id;
        T.fillRuns(el, b.runs, ctx); decorate(el, b, doc, ctx, mk[b.id]); host.appendChild(el);
      } else host.appendChild(blockEl(doc, b, ctx));
    }
    return host;
  }

  // 화면·인쇄 공용 스타일 - 편집기와 미리 보기가 같은 것을 싣는다(쪽 상자 치수는 mm 그대로)
  const CSS = `
.pg-p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; position: relative; min-height: 1em; }
.pg-li::before { content: attr(data-marker); position: absolute; margin-left: -${LIST_INDENT}mm; width: ${LIST_INDENT - 1}mm; text-align: right; white-space: nowrap; font-weight: 400; font-style: normal; }
.pg-li[data-list="bullet"]::before, .pg-li[data-list="check"]::before { text-align: center; }
.pg-li.done { opacity: .6; text-decoration: line-through; }
.pg-table { border-collapse: collapse; width: 100%; table-layout: fixed; margin: 4pt 0 8pt; }
.pg-table td, .pg-table th { border: .5pt solid #8a8a8a; padding: 3pt 5pt; vertical-align: top; text-align: left; font-weight: 400; }
.pg-table tr.head th { background: #f0f0f0; font-weight: 700; }
.pg-table .pg-p { margin: 0 !important; }
.pg-table.pg-noborder td, .pg-table.pg-noborder th { border-color: transparent; padding: 0 6pt; }
.pg-table.pg-noborder tr.head th { background: transparent; }
.pg-table.pg-innerv td + td, .pg-table.pg-innerv th + th { border-left-color: #8a8a8a; }
.pg-table.pg-noborder td:first-child, .pg-table.pg-noborder th:first-child { padding-left: 0; } .pg-table.pg-noborder td:last-child, .pg-table.pg-noborder th:last-child { padding-right: 0; }
.pg-table.pg-noborder .pg-p { margin-bottom: 3pt !important; }
.pg-image { margin: 6pt 0; }
.pg-image img { max-width: 100%; }
.pg-break { border-top: 1px dashed #b5b5b5; margin: 8pt 0; height: 0; position: relative; }
.pg-break.page { break-after: page; }  /* 인쇄 - 쪽 나누기만 쪽을 넘긴다. 단 나누기·구역 나누기는 같은 쪽에서 이어진다(전에는 셋 다 쪽을 넘겨 다단 문서의 인쇄 쪽 수가 늘었다) */
.pg-break::after { content: attr(data-label); position: absolute; top: -.7em; left: 50%; transform: translateX(-50%); background: #fff; padding: 0 8px; font-size: 8pt; color: #999; }
.nt-link { color: #1a5fb4; text-decoration: underline; }
[data-fn]::after { content: attr(data-fnn); vertical-align: super; font-size: .62em; line-height: 1; font-weight: 400; font-style: normal; text-decoration: none; color: var(--accent, #c8553d); margin-left: .5px; }
[data-ruby] { position: relative; }
[data-ruby]::before { content: attr(data-ruby); position: absolute; left: 50%; bottom: 100%; transform: translateX(-50%); font-size: .55em; line-height: 1.1; white-space: nowrap; font-weight: 400; font-style: normal; text-decoration: none; pointer-events: none; }
.pg-obj { position: absolute; box-sizing: border-box; pointer-events: auto; }
.pg-obj > svg { position: absolute; left: 0; top: 0; overflow: visible; }
.pg-obj-text { position: absolute; inset: 0; display: flex; flex-direction: column; overflow: hidden; }
.pg-obj-body { outline: none; min-height: 1.2em; }
@media print { .pg-break { border: 0; margin: 0; } .pg-break::after { content: none; } }
`;
  function injectCss(d) { d = d || document; if (d.getElementById("pg-css")) return; const s = d.createElement("style"); s.id = "pg-css"; s.textContent = CSS; d.head.appendChild(s); }

  root.NexaPage = { SIZES, LIST_INDENT, pageBox, styleOf, numberLabel, markers, blockCss, decorate, tableGrid, tableClass, blockEl, objectSvg, objectEl, renderInto, CSS, injectCss };
})(typeof window !== "undefined" ? window : globalThis);
