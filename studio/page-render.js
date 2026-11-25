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
    if (block.first !== undefined || st.first) css.textIndent = (block.first !== undefined ? block.first : st.first) + "mm";
    return css;
  }
  /** 문단 요소 꾸미기 - 스타일·정렬·들여쓰기와 목록 머리 기호(::before 가 data-marker 를 그린다) */
  function decorate(el, block, doc, ctx, marker) {
    Object.assign(el.style, blockCss(doc, block, ctx));
    el.classList.add("pg-p"); if (block.style) el.dataset.style = block.style;
    if (block.list) { el.classList.add("pg-li"); el.dataset.marker = marker || ""; el.dataset.list = block.list.kind; if (block.list.done) el.classList.add("done"); }
  }

  function tableEl(doc, b, ctx) {
    const d = (ctx && ctx.document) || document, t = d.createElement("table"); t.className = "pg-table";
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
    } else { el = d.createElement("div"); el.className = "pg-break " + (b.kind || "page"); el.dataset.label = { page: "쪽 나누기", column: "단 나누기", section: "구역 나누기" }[b.kind || "page"]; }
    el.dataset.id = b.id;
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
.pg-image { margin: 6pt 0; }
.pg-image img { max-width: 100%; }
.pg-break { border-top: 1px dashed #b5b5b5; margin: 8pt 0; height: 0; position: relative; break-after: page; }
.pg-break::after { content: attr(data-label); position: absolute; top: -.7em; left: 50%; transform: translateX(-50%); background: #fff; padding: 0 8px; font-size: 8pt; color: #999; }
.nt-link { color: #1a5fb4; text-decoration: underline; }
@media print { .pg-break { border: 0; margin: 0; } .pg-break::after { content: none; } }
`;
  function injectCss(d) { d = d || document; if (d.getElementById("pg-css")) return; const s = d.createElement("style"); s.id = "pg-css"; s.textContent = CSS; d.head.appendChild(s); }

  root.NexaPage = { SIZES, LIST_INDENT, pageBox, styleOf, numberLabel, markers, blockCss, decorate, tableGrid, blockEl, renderInto, CSS, injectCss };
})(typeof window !== "undefined" ? window : globalThis);
