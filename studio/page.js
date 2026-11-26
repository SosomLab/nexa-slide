// 페이지 편집기(kind = "page", Word·Pages 형) - 실험 기능. 설계 = docs/dev/page-editor/design.md
//   뼈대(서버 요청·알림·상태·메뉴) = nexa-shell.js · 글 편집 = nexa-text.js · 그리기 = page-render.js · 종류 = nexa-kinds.js
//   1단계: 본문 문단 편집(서식·스타일·정렬·목록) · 저장(PUT ?merge=1) · 실행 취소 · 쪽 경계선(근사). 표·그림·머리말·내보내기는 뒤 단계.
(function () {
  "use strict";
  const BASE = (location.pathname.match(/^\/w\/[^/]+/) || [""])[0];
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const TAB = (() => { try { let t = sessionStorage.getItem("nexaTab"); if (!t) { t = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)).slice(0, 8); sessionStorage.setItem("nexaTab", t); } return t; } catch (e) { return "t" + Date.now().toString(36); } })();
  const { api, toast, setStatus, banner, openMenu, closeMenu } = NexaShell.create({ base: BASE, tab: TAB, cache: "no-store", toastMs: 2400 });
  const T = NexaText, P = NexaPage;
  const S = { id: new URLSearchParams(location.search).get("deck") || "", deck: null, version: null, savedJson: null, dirty: false, saving: false, conflict: false, undo: [], redo: [], lastWhy: "", lastAt: 0 };
  let ed = null;   // 본문 편집기
  let flow = null; // 실시간 쪽 나눔(page-flow.js)
  let cur = null;  // 지금 글을 치고 있는 편집기 - 본문이거나 표 칸(칸마다 따로 붙는다). 서식 막대는 이것에 건다
  // 색·글꼴 토큰 → CSS 값. 작업 공간 토큰(tokens.json)을 읽어 오는 것은 서식 막대 작업(PG-043)에서 - 그 전에는 기본값
  const COLORS = { accent: "#c8553d", muted: "#7a756d", ink: "#1f1f1f" };
  const FONTS = { body: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif', title: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif', mono: 'Consolas, "D2Coding", monospace' };
  // 템플릿 토큰(tokens.json - 슬라이드와 같은 것)을 읽으면 그 글꼴·색을 쓴다. 페이지 스타일의 이름 → 토큰 이름은 export_docx.py 의 별칭과 같다
  const TOKEN_ALIAS = { color: { accent: "primary", muted: "on-surface-variant", ink: "on-surface" }, font: { title: "heading" } };
  async function loadTokens() {
    try {
      const t = await (await fetch("tokens.json", { cache: "no-store" })).json();
      for (const [k, v] of Object.entries(t.colors || {})) if (typeof v === "string") COLORS[k] = v;
      for (const [a, n] of Object.entries(TOKEN_ALIAS.color)) if (t.colors && t.colors[n]) COLORS[a] = t.colors[n];
      for (const [k, v] of Object.entries(t.fonts || {})) if (v && v.css) FONTS[k] = v.css;
      for (const [a, n] of Object.entries(TOKEN_ALIAS.font)) if (t.fonts && t.fonts[n] && t.fonts[n].css) FONTS[a] = t.fonts[n].css;
    } catch (e) { /* 토큰을 못 읽으면 기본값 */ }
  }
  const ctx = { color: (c) => COLORS[c] || c, font: (f) => FONTS[f] || f, asset: (src) => (/^(https?:|data:|\/)/.test(src) ? src : `${BASE}/${src}`) };
  const deckJson = () => JSON.stringify(S.deck);
  const blocks = () => S.deck.blocks;
  let idSeq = 0;
  function newId() { const used = new Set(blocks().map((b) => b.id)); let id; do { id = "b" + Date.now().toString(36).slice(-4) + (idSeq++).toString(36); } while (used.has(id)); return id; }

  // ---------------------------------------------------------------- 실행 취소·저장
  /** 바꾸기 직전의 문서를 기록한다 - 이어서 치는 글(같은 이유, 1.2초 안)은 한 묶음으로 */
  function snapshot(why) {
    const now = Date.now(), join = (why === "type" || why === "ime") && (S.lastWhy === "type" || S.lastWhy === "ime") && now - S.lastAt < 1200;
    S.lastWhy = why; S.lastAt = now;
    if (join) return;
    S.undo.push({ json: deckJson(), sel: ed && ed.selection() }); if (S.undo.length > 200) S.undo.shift();
    S.redo = [];
  }
  /** 남의 변경을 받기 직전 - 실행 취소 기록마다 "그 편집 뒤의 문서"를 붙여 둔다(now = 받기 직전의 내 문서). 그러면 되돌릴 때
   *  문서를 통째로 옛 모습으로 바꾸지 않고 내 편집만 거꾸로 얹는다 - Ctrl+Z 가 남의 변경을 지우지 않는다(슬라이드·시트의 NexaMerge.seal 과 같은 뜻). 다시 실행 기록은 비운다 */
  function sealUndo(now) {
    for (let k = 0; k < S.undo.length; k++) if (!S.undo[k].after) S.undo[k].after = k + 1 < S.undo.length ? S.undo[k + 1].json : now;
    S.redo = []; S.lastWhy = "";
  }
  function restore(from, to) {
    const e = from.pop(); if (!e) return;
    to.push({ json: deckJson(), sel: ed.selection() });
    S.deck = e.after ? NexaMerge.merge3(JSON.parse(e.after), JSON.parse(e.json), JSON.parse(deckJson()), "ours").merged : JSON.parse(e.json); S.lastWhy = "";
    cur = ed; S.pick = null; layout(); ed.refresh(e.sel); afterChange(true);
  }
  const undo = () => restore(S.undo, S.redo), redo = () => restore(S.redo, S.undo);
  function afterChange(noMark) {
    S.dirty = deckJson() !== S.savedJson;
    setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
    if (!noMark) queueMicrotask(decorateAll); else decorateAll();
    updTools(); scheduleSave();
  }
  let saveT = 0;
  function scheduleSave() { clearTimeout(saveT); if (S.dirty) saveT = setTimeout(save, 700); }
  async function save(force) {
    if (!S.deck || (S.conflict && !force)) return;
    if (S.saving) { scheduleSave(); return; }
    const body = deckJson();
    if (!force && body === S.savedJson) { S.dirty = false; setStatus("saved", "저장됨"); return; }
    S.saving = true; setStatus("dirty", "저장 중…");
    const r = await api("PUT", `/api/deck/${encodeURIComponent(S.id)}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : "&merge=1"}`, JSON.parse(body));
    S.saving = false;
    if (r.ok) {
      S.version = r.data.version; S.conflict = false; banner(false);
      if (r.data.merged && r.data.deck) {  // 그 사이 다른 저장과 합쳐졌다 - 결과(+ 저장하는 사이 더 고친 것)를 화면에
        const now = deckJson(), sel = ed.selection();
        sealUndo(now);
        S.savedJson = JSON.stringify(r.data.deck); S.deck = NexaMerge.afterSave(body, now, r.data.deck);
        cur = ed; layout(); ed.refresh(sel); toast(NexaMerge.notice(r.data.conflicts).text, 3500);
      } else {
        const same = deckJson() === body;
        if (r.data.updated) S.deck.updated = r.data.updated;
        if (same) S.savedJson = deckJson(); else { const o = JSON.parse(body); if (r.data.updated) o.updated = r.data.updated; S.savedJson = JSON.stringify(o); }
      }
      S.dirty = deckJson() !== S.savedJson;
      setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
      if (S.dirty) scheduleSave();
    } else if (r.status === 409) {
      S.conflict = true; setStatus("conflict", "충돌");
      banner(true, "저장하려는 사이 문서가 밖에서 바뀌었고 자동으로 합칠 수 없습니다. 어느 쪽을 남길까요?");
    } else { setStatus("error", "저장 실패"); toast("저장 실패: " + ((r.data && r.data.error) || r.status), 6000); }
  }

  // ---------------------------------------------------------------- 그리기
  /** 종이 치수(mm) - 쪽 나눔(어느 블록·줄·행이 어느 쪽인가)은 page-flow.js 가 그린 것을 재서 정하고, 정해지면 drawSheets 가 종이 장을 그린다 */
  function layout() {
    const box = P.pageBox(S.deck), paper = $("#paper");
    paper.style.width = box.w + "mm"; paper.style.padding = `${box.t}mm ${box.r}mm ${box.b}mm ${box.l}mm`;
    S.box = box; S.sheetKey = ""; drawSheets(S.pages || 1); pageLines();
    // 브라우저 인쇄(PDF 로 저장)도 같은 용지·여백으로 - 종이의 안쪽 여백은 인쇄 때 빼고 @page 여백이 대신한다
    let st = document.getElementById("pg-print"); if (!st) { st = document.createElement("style"); st.id = "pg-print"; document.head.appendChild(st); }
    // 머리말·꼬리말·쪽 번호는 @page 의 여백 상자로(Chrome 131+) - 한 줄 글과 정렬만 옮긴다. 아래 여백은 1mm 덜어 쪽 끝 줄이 반올림으로 넘치지 않게 한다
    const page = S.deck.page || {}, num = page.number || {}, q = (t) => `"${String(t).replace(/[\\"]/g, "\\$&").replace(/\n/g, " ")}"`, boxes = [];
    for (const part of ["header", "footer"]) for (const al of ["left", "center", "right"]) {
      const c = [];
      if (hfText(part) && hfAlign(part) === al) c.push(q(hfText(part)));
      if (num.show && String(num.pos || "footer-center") === `${part}-${al}`) c.push("counter(page)");
      if (c.length) boxes.push(`@${part === "header" ? "top" : "bottom"}-${al} { content: ${c.join(' " " ')}; font-size: 9pt; color: #8a857d; }`);
    }
    st.textContent = `@page { size: ${box.w}mm ${box.h}mm; margin: ${box.t}mm ${box.r}mm ${Math.max(0, box.b - 1)}mm ${box.l}mm; ${boxes.join(" ")} }`;
  }
  /** 종이 장 n 개와 덮개(여백 가림 · 쪽 틈 · 머리말·꼬리말·쪽 번호)를 그린다 - 쪽 수·쪽 설정이 같으면 다시 그리지 않는다.
   *  첫 쪽의 머리말·꼬리말은 id pgHeader · pgFooter(쪽 설정 확인용) */
  function drawSheets(n) {
    const box = S.box, page = S.deck.page || {}, num = page.number || {}, gap = flow ? flow.gap : 24;
    const key = JSON.stringify([n, box, page.header, page.footer, num, gap]);
    S.pages = n; $("#paper").style.minHeight = `calc(${n * box.h}mm + ${(n - 1) * gap}px)`;
    if (key === S.sheetKey) return; S.sheetKey = key;
    const sheets = $("#sheets"), covers = $("#covers"); sheets.replaceChildren(); covers.replaceChildren();
    for (let k = 0; k < n; k++) {
      const top = `calc(${k * box.h}mm + ${k * gap}px)`;
      const sh = document.createElement("div"); sh.className = "pg-sheet"; sh.style.top = top; sh.style.height = box.h + "mm"; sh.dataset.n = k + 1; sheets.appendChild(sh);
      const pb = document.createElement("div"); pb.className = "pg-pagebox"; pb.style.top = top; pb.style.height = box.h + "mm";
      for (const [cls, h] of [["t", box.t], ["b", box.b]]) { const m = document.createElement("div"); m.className = "pg-mask " + cls; m.style.height = h + "mm"; m.style[cls === "t" ? "top" : "bottom"] = "0"; pb.appendChild(m); }
      if (k < n - 1) { const bt = document.createElement("div"); bt.className = "pg-between"; bt.style.height = gap + "px"; pb.appendChild(bt); }
      for (const part of ["header", "footer"]) {
        const el = document.createElement("div"); el.className = "pg-hf"; if (k === 0) el.id = part === "header" ? "pgHeader" : "pgFooter";
        el.style.padding = `0 ${box.r}mm 0 ${box.l}mm`;
        if (part === "header") el.style.top = Math.max(2, box.t / 2 - 2) + "mm"; else el.style.bottom = Math.max(2, box.b / 2 - 2) + "mm";
        P.renderInto(el, S.deck, (page[part] || {}).blocks || [], ctx);
        if (num.show && String(num.pos || "footer-center").startsWith(part)) {
          const d = document.createElement("div"); d.className = "pg-p pg-num"; d.style.textAlign = String(num.pos || "footer-center").split("-")[1] || "center"; d.textContent = String(k + 1); d.title = "쪽 번호"; el.appendChild(d);
        }
        pb.appendChild(el);
      }
      covers.appendChild(pb);
    }
  }
  const hfText = (part) => (((S.deck.page || {})[part] || {}).blocks || []).map((b) => T.text(b.runs || [])).join(" ");
  const hfAlign = (part) => ((((S.deck.page || {})[part] || {}).blocks || [])[0] || {}).align || "left";
  /** 쪽 설정 대화 상자 - 용지·방향·여백(mm)·머리말·꼬리말(한 줄 글 + 정렬)·쪽 번호 */
  function pageSetup() {
    const page = S.deck.page || {}, m = { t: 25, r: 20, b: 25, l: 20, ...(page.margin || {}) }, num = page.number || {};
    const size = typeof page.size === "string" ? page.size : "A4";
    const opt = (list, cur) => list.map(([v, t]) => `<option value="${v}" ${v === cur ? "selected" : ""}>${t}</option>`).join("");
    const aligns = [["left", "왼쪽"], ["center", "가운데"], ["right", "오른쪽"]];
    const back = document.createElement("div"); back.className = "dlg-back";
    back.innerHTML = `<div class="dlg" role="dialog" aria-label="쪽 설정"><h3>쪽 설정</h3><div class="grid">
      <label>용지</label><select id="psSize">${opt(Object.keys(P.SIZES).map((k) => [k, `${k} (${P.SIZES[k][0]} × ${P.SIZES[k][1]} mm)`]), size)}</select>
      <label>방향</label><select id="psOrient">${opt([["portrait", "세로"], ["landscape", "가로"]], page.orient || "portrait")}</select>
      <label>여백 (mm)</label><div class="margins">${[["t", "위"], ["b", "아래"], ["l", "왼쪽"], ["r", "오른쪽"]].map(([k, t]) => `<div><label>${t}</label><input type="number" id="psM${k}" min="0" max="150" step="1" value="${m[k]}"></div>`).join("")}</div>
      <label>머리말</label><div style="display:flex;gap:6px"><input type="text" id="psHeader" maxlength="200"><select id="psHeaderAlign" style="width:96px">${opt(aligns, hfAlign("header"))}</select></div>
      <label>꼬리말</label><div style="display:flex;gap:6px"><input type="text" id="psFooter" maxlength="200"><select id="psFooterAlign" style="width:96px">${opt(aligns, hfAlign("footer"))}</select></div>
      <label>단</label><select id="psCols">${opt([["1", "1단"], ["2", "2단"], ["3", "3단"]], String((page.columns || {}).count || 1))}</select>
      <label>쪽 번호</label><select id="psNum">${opt([["", "없음"], ["footer-center", "아래 가운데"], ["footer-right", "아래 오른쪽"], ["footer-left", "아래 왼쪽"], ["header-right", "위 오른쪽"], ["header-center", "위 가운데"]], num.show ? num.pos || "footer-center" : "")}</select>
      </div><div class="err" id="psErr"></div><div class="foot"><button class="btn" id="psCancel">취소</button><button class="btn primary" id="psOk">적용</button></div></div>`;
    document.body.appendChild(back);
    const q = (s) => back.querySelector(s);
    q("#psHeader").value = hfText("header"); q("#psFooter").value = hfText("footer");
    const close = () => { back.remove(); document.removeEventListener("keydown", onEsc, true); ed.focus(); };
    function onEsc(e) { if (e.key === "Escape") { e.stopPropagation(); close(); } }
    document.addEventListener("keydown", onEsc, true);
    back.addEventListener("mousedown", (e) => { if (e.target === back) close(); });
    q("#psCancel").onclick = close;
    q("#psOk").onclick = () => {
      const mg = {}; for (const k of "tblr") { const v = Number(q("#psM" + k).value); if (!Number.isFinite(v) || v < 0 || v > 150) { q("#psErr").textContent = "여백은 0~150 mm 로 적어 주세요"; return; } mg[k] = v; }
      const sz = P.SIZES[q("#psSize").value], land = q("#psOrient").value === "landscape", w = land ? sz[1] : sz[0], h = land ? sz[0] : sz[1];
      if (w - mg.l - mg.r < 30 || h - mg.t - mg.b < 30) { q("#psErr").textContent = "여백이 너무 커서 본문 자리가 없습니다"; return; }
      const part = (name, old) => {  // 한 줄 글 - 글이 그대로면 있던 블록(서식 포함)을 두고 정렬만 바꾼다
        const text = q(name === "header" ? "#psHeader" : "#psFooter").value.trim(), align = q(name === "header" ? "#psHeaderAlign" : "#psFooterAlign").value;
        if (!text) return { blocks: [] };
        const keep = (old.blocks || [])[0], same = keep && hfText(name) === text;
        const b = same ? { ...keep } : { id: (keep && keep.id) || `${name}-1`, type: "p", runs: [{ t: text }] };
        if (align === "left") delete b.align; else b.align = align;
        return { blocks: [b] };
      };
      const next = { ...page, size: q("#psSize").value, orient: q("#psOrient").value, margin: mg, header: part("header", page.header || {}), footer: part("footer", page.footer || {}),
        number: q("#psNum").value ? { show: true, pos: q("#psNum").value } : { show: false, pos: num.pos || "footer-center" } };
      if (+q("#psCols").value > 1) next.columns = { count: +q("#psCols").value, gap: (page.columns || {}).gap === undefined ? 8 : page.columns.gap }; else delete next.columns;
      if (JSON.stringify(next) !== JSON.stringify(page)) { snapshot("format"); S.deck.page = next; layout(); afterChange(true); }
      close();
    };
    q("#psSize").focus();
  }
  /** 확대 - 종이를 화면에서만 키우고 줄인다(CSS zoom). "fit" 은 창 너비에 종이를 맞춘다. 고른 값은 이 브라우저에 기억한다 */
  function applyZoom(v) {
    const paper = $("#paper"), box = S.box; if (!box) return;
    let z = Number(v);
    if (v === "fit" || !z) { paper.style.zoom = 1; const w = paper.getBoundingClientRect().width || 1; z = Math.max(0.3, Math.min(3, ($("#scroll").clientWidth - 32) / w)); }
    paper.style.zoom = z; S.zoom = v;
    try { localStorage.setItem("nexaPageZoom", String(v)); } catch (e) { /* 저장 못 해도 그대로 */ }
    pageLines();
  }
  /** 쪽 나눔을 다시 잡는다(글·서식·확대가 바뀔 때마다 - 실제 계산은 한 박자 뒤에 한 번) */
  function pageLines() { if (flow) flow.schedule(); pageInfo(); }
  function pageInfo() {
    const chars = blocks().reduce((a, b) => a + (T.isText(b) ? T.length(b.runs) : 0), 0);
    $("#pageInfo").textContent = `${S.pages || 1}쪽 · ${typeof S.deck.page.size === "string" ? S.deck.page.size : "사용자 크기"} · ${chars.toLocaleString()}자`;
    $("#pageInfo").title = "쪽 수는 이 화면의 쪽 나눔 기준(Word 로 내보내면 글꼴·줄 나눔 차이로 달라질 수 있다) · 글자 수는 본문 문단 기준(표 칸 제외)";
  }
  /** 목록 머리 기호는 다른 문단이 바뀌어도 달라진다(번호) - 저장할 때마다 전부 다시 단다 */
  function decorateAll() {
    const mk = P.markers(blocks());
    for (const el of $$("#ed > .pg-li")) el.dataset.marker = mk[el.dataset.id] || "";
    numberNotes();
    pageLines();
  }
  const blockAt = (id) => blocks().find((b) => b.id === id);
  /** 선택에 걸친 문단들을 fn(문단) → 새 문단으로 바꾼다(목록 단계처럼 문단마다 값이 다른 속성) */
  function mapSel(fn, why) {
    const s = ed.selection(); if (!s) return;
    const o = T.ordered(blocks(), s.a, s.f); if (!o) return;
    const ia = blocks().findIndex((b) => b.id === o[0].id), ib = blocks().findIndex((b) => b.id === o[1].id);
    snapshot(why || "format");
    S.deck.blocks = blocks().map((b, k) => (k >= ia && k <= ib && T.isText(b) ? fn(b) : b));
    ed.refresh(s); afterChange();
  }
  function setList(kind) {
    const s = ed.selection(); if (!s) return;
    const cur = blockAt(s.f.id), off = cur && cur.list && cur.list.kind === kind;  // 이미 그 목록이면 끈다
    mapSel((b) => { const y = { ...b }; if (off) delete y.list; else y.list = { kind, level: (b.list && b.list.level) || 0 }; return y; });
  }
  function shiftLevel(d) {
    mapSel((b) => {
      if (!b.list) { const ind = Math.max(0, (b.indent || 0) + d * 6); const y = { ...b }; if (ind) y.indent = ind; else delete y.indent; return y; }
      return { ...b, list: { ...b.list, level: Math.max(0, Math.min(8, (b.list.level || 0) + d)) } };
    });
  }
  // ---------------------------------------------------------------- 표 - 칸마다 편집기를 붙인다(칸 안에는 문단들)
  const rid = (p) => p + Date.now().toString(36).slice(-4) + (idSeq++).toString(36) + Math.random().toString(36).slice(2, 4);
  const newPara = () => ({ id: rid("p"), type: "p", runs: [] });
  const newCell = () => ({ id: rid("c"), blocks: [newPara()] });
  const newTable = (rows, cols) => ({ id: rid("t"), type: "table", cols: Array.from({ length: cols }, () => Math.round(100 / cols)),
    rows: Array.from({ length: rows }, (_, r) => ({ id: rid("r"), ...(r === 0 ? { head: true } : {}), cells: Array.from({ length: cols }, newCell) })) });
  /** 표 블록 → 요소. 칸의 글을 고치면 칸 객체를 **그 자리에서** 고친다(표 블록 객체가 그대로라 바깥 편집기가 표를 다시 그리지 않고, 칸 편집기의 초점이 남는다) */
  function tableEl(b) {
    const t = document.createElement("table"); t.className = "pg-table" + P.tableClass(b);
    const total = b.cols.reduce((a, c) => a + c, 0) || 1, cg = document.createElement("colgroup");
    for (const c of b.cols) { const col = document.createElement("col"); col.style.width = (c / total * 100).toFixed(3) + "%"; cg.appendChild(col); }
    t.appendChild(cg);
    const body = document.createElement("tbody");
    for (const row of b.rows) {
      const tr = document.createElement("tr"); tr.dataset.id = row.id; if (row.head) tr.className = "head";
      for (const c of row.cells) {
        const td = document.createElement(row.head ? "th" : "td"); td.dataset.id = c.id;
        if (c.colspan > 1) td.colSpan = c.colspan; if (c.rowspan > 1) td.rowSpan = c.rowspan;
        if (c.fill) td.style.backgroundColor = ctx.color(c.fill);
        if (!Array.isArray(c.blocks) || !c.blocks.length) c.blocks = [newPara()];
        const host = document.createElement("div"); host.className = "pg-cell"; td.appendChild(host);
        const ce = T.mount(host, {
          get: () => c.blocks, set: (bs, why) => { snapshot(why); c.blocks = bs.length ? bs : [newPara()]; afterChange(); }, newId: () => rid("p"),
          decorate: (el, x) => P.decorate(el, x, S.deck, ctx, P.markers(c.blocks)[x.id]), renderBlock: (x) => P.blockEl(S.deck, x, ctx),
          color: ctx.color, font: ctx.font, onSelect: () => { cur = ce; updTools(); }, undo, redo,
        });
        host.addEventListener("focus", () => { cur = ce; });
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
    t.appendChild(body);
    t.addEventListener("contextmenu", (e) => { const td = e.target.closest("td,th"); if (!td) return; e.preventDefault(); tableMenu(b.id, td.dataset.id, { x: e.clientX, y: e.clientY }); });
    return t;
  }
  /** 표를 바꾼다 - fn(표 사본) 이 고친 표로 블록을 갈아 끼운다(새 객체라 표가 다시 그려진다). null 을 돌려주면 표를 지운다 */
  function changeTable(tid, fn) {
    const i = blocks().findIndex((b) => b.id === tid); if (i < 0) return;
    snapshot("format");
    const next = fn(JSON.parse(JSON.stringify(blocks()[i])));
    S.deck.blocks = next ? blocks().map((b, k) => (k === i ? next : b)) : blocks().filter((_, k) => k !== i);
    if (!S.deck.blocks.some(T.isText)) S.deck.blocks.push(newPara());
    cur = ed; ed.refresh(); afterChange();
  }
  const tableGrid = (t) => P.tableGrid(t);  // 칸이 놓인 격자 열 번호(page-render.js)
  const spanOf = (c) => [c.colspan > 1 ? c.colspan : 1, c.rowspan > 1 ? c.rowspan : 1];
  /** 합칠 수 있는 이웃 - 오른쪽(같은 행의 다음 칸, 세로 크기가 같고 맞닿음) · 아래(바로 아래 행에서 같은 열·같은 너비로 시작하는 칸) */
  function mergeTargets(t, ri, ci) {
    const g = tableGrid(t), me = g[ri][ci], [cs, rs] = spanOf(me.c);
    const right = g[ri][ci + 1] && g[ri][ci + 1].col === me.col + cs && spanOf(g[ri][ci + 1].c)[1] === rs ? ci + 1 : -1;
    const below = g[ri + rs] ? g[ri + rs].findIndex((x) => x.col === me.col && spanOf(x.c)[0] === cs) : -1;
    return { right, below, belowRow: ri + rs, cs, rs };
  }
  function mergeCell(tid, ri, ci, dir) {
    changeTable(tid, (x) => {
      const m = mergeTargets(x, ri, ci), c = x.rows[ri].cells[ci];
      const take = (o) => { const add = (o.blocks || []).filter((b) => !(T.isText(b) && !b.runs.length)); c.blocks = [...(c.blocks || []).filter((b, k, a) => a.length === 1 || !(T.isText(b) && !b.runs.length) || add.length === 0), ...add]; if (!c.blocks.length) c.blocks = [newPara()]; };
      if (dir === "right" && m.right >= 0) { const o = x.rows[ri].cells[m.right]; c.colspan = m.cs + spanOf(o)[0]; take(o); x.rows[ri].cells.splice(m.right, 1); }
      else if (dir === "below" && m.below >= 0) { const o = x.rows[m.belowRow].cells[m.below]; c.rowspan = m.rs + spanOf(o)[1]; take(o); x.rows[m.belowRow].cells.splice(m.below, 1); }
      return x;
    });
  }
  /** 합친 칸을 다시 나눈다 - 가로는 그 행에, 세로는 아래 행들의 제 열 자리에 빈 칸을 넣는다 */
  function splitCell(tid, ri, ci) {
    changeTable(tid, (x) => {
      const g = tableGrid(x), me = g[ri][ci], [cs, rs] = spanOf(me.c), c = x.rows[ri].cells[ci];
      delete c.colspan; delete c.rowspan;
      x.rows[ri].cells.splice(ci + 1, 0, ...Array.from({ length: cs - 1 }, newCell));
      for (let r = 1; r < rs; r++) {
        const line = g[ri + r] || [], at = line.filter((y) => y.col < me.col).length;  // 그 행에서 이 열보다 앞에 있는 칸 수 = 끼워 넣을 자리
        x.rows[ri + r].cells.splice(at, 0, ...Array.from({ length: cs }, newCell));
      }
      return x;
    });
  }
  function tableMenu(tid, cid, at) {
    const t = blockAt(tid); if (!t) return;
    const ri = t.rows.findIndex((r) => r.cells.some((c) => c.id === cid)), ci = ri < 0 ? -1 : t.rows[ri].cells.findIndex((c) => c.id === cid); if (ri < 0) return;
    const plain = t.rows.every((r) => r.cells.every((c) => !(c.colspan > 1) && !(c.rowspan > 1)));  // 합친 칸이 있으면 열 작업은 막는다(칸 위치 계산이 달라진다)
    const addRow = (d) => changeTable(tid, (x) => { x.rows.splice(ri + d, 0, { id: rid("r"), cells: Array.from({ length: x.cols.length }, newCell) }); return x; });
    const addCol = (d) => changeTable(tid, (x) => { x.cols.splice(ci + d, 0, x.cols[ci]); for (const r of x.rows) r.cells.splice(ci + d, 0, newCell()); return x; });
    openMenu(at, [
      { label: "위에 행 넣기", act: () => addRow(0) }, { label: "아래에 행 넣기", act: () => addRow(1) },
      { label: "왼쪽에 열 넣기", disabled: !plain, act: () => addCol(0) }, { label: "오른쪽에 열 넣기", disabled: !plain, act: () => addCol(1) }, "-",
      { label: "행 지우기", disabled: t.rows.length < 2, act: () => changeTable(tid, (x) => { x.rows.splice(ri, 1); return x; }) },
      { label: "열 지우기", disabled: !plain || t.cols.length < 2, act: () => changeTable(tid, (x) => { x.cols.splice(ci, 1); for (const r of x.rows) r.cells.splice(ci, 1); return x; }) }, "-",
      { label: "오른쪽 칸과 합치기", disabled: mergeTargets(t, ri, ci).right < 0, act: () => mergeCell(tid, ri, ci, "right") },
      { label: "아래 칸과 합치기", disabled: mergeTargets(t, ri, ci).below < 0, act: () => mergeCell(tid, ri, ci, "below") },
      { label: "칸 나누기", disabled: !(t.rows[ri].cells[ci].colspan > 1 || t.rows[ri].cells[ci].rowspan > 1), act: () => splitCell(tid, ri, ci) }, "-",
      { label: "머리글 행", on: !!t.rows[ri].head, act: () => changeTable(tid, (x) => { if (x.rows[ri].head) delete x.rows[ri].head; else x.rows[ri].head = true; return x; }) },
      { label: "칸 채우기(회색)", on: !!t.rows[ri].cells[ci].fill, act: () => changeTable(tid, (x) => { const c = x.rows[ri].cells[ci]; if (c.fill) delete c.fill; else c.fill = "#eeeeee"; return x; }) }, "-",
      { label: "테두리 없음(배치용 표)", on: t.border === "none", act: () => changeTable(tid, (x) => { if (x.border === "none") delete x.border; else x.border = "none"; return x; }) },
      { label: "칸 사이 세로선만", on: t.border === "inner-v", act: () => changeTable(tid, (x) => { if (x.border === "inner-v") delete x.border; else x.border = "inner-v"; return x; }) }, "-",
      { label: "표 지우기", act: () => changeTable(tid, () => null) },
    ]);
  }
  function insertTable() {
    const s = ed.selection(), ans = prompt("표 크기 - 행×열", "3×3"); if (!ans) return;
    const m = ans.match(/(\d+)\D+(\d+)/); if (!m) { toast("행×열 꼴로 적어 주세요(예: 3×4)"); return; }
    const rows = Math.max(1, Math.min(50, +m[1])), cols = Math.max(1, Math.min(12, +m[2]));
    const i = s ? blocks().findIndex((b) => b.id === s.f.id) : blocks().length - 1;
    snapshot("format");
    const tb = newTable(rows, cols), after = newPara();
    S.deck.blocks = [...blocks().slice(0, i + 1), tb, ...(blocks()[i + 1] && T.isText(blocks()[i + 1]) ? [] : [after]), ...blocks().slice(i + 1)];
    ed.refresh(); afterChange();
    const first = document.querySelector(`[data-id="${tb.id}"] .pg-cell`); if (first) first.focus();
  }

  // ---------------------------------------------------------------- 그림 - 글자처럼 놓인 블록(가운데·왼쪽·오른쪽). Word 로 나갈 수 있는 png·jpg·gif 만
  /** 블록 뒤에 넣는다 - 선택이 있는 문단 뒤(없으면 맨 끝). 그림·표 뒤에 칠 자리가 없으면 빈 문단을 붙인다 */
  function insertAfterSel(block) {
    const s = ed.selection(), i = s ? blocks().findIndex((b) => b.id === s.f.id) : blocks().length - 1;
    snapshot("format");
    const tailP = blocks()[i + 1] && T.isText(blocks()[i + 1]) ? [] : [newPara()];
    S.deck.blocks = [...blocks().slice(0, i + 1), block, ...tailP, ...blocks().slice(i + 1)];
    ed.refresh(); afterChange();
  }
  async function insertImage(file) {
    if (!file) return;
    if (!/^image\/(png|jpeg|gif)$/.test(file.type)) { toast("png · jpg · gif 그림만 넣을 수 있습니다"); return; }
    const dataUrl = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(file); });
    const size = await new Promise((res) => { const im = new Image(); im.onload = () => res([im.naturalWidth, im.naturalHeight]); im.onerror = () => res([0, 0]); im.src = dataUrl; });
    const r = await api("POST", "/api/image", { name: file.name, type: file.type, data: String(dataUrl).split(",")[1] || "" });
    if (!r.ok || !r.data || !r.data.src) { toast("그림을 올리지 못했습니다: " + ((r.data && r.data.error) || r.status), 6000); return; }
    const w = Math.min(S.box.cw, Math.max(10, Math.round((size[0] || 400) * 25.4 / 96)));  // 원래 크기(96dpi 기준 mm), 본문 너비를 넘지 않게
    insertAfterSel({ id: rid("i"), type: "image", src: r.data.src, w });
  }
  /** 그림·나누기 같은 블록을 바꾼다 - fn(블록 사본) → 새 블록(null 이면 지운다) */
  function changeBlock(id, fn) {
    const i = blocks().findIndex((b) => b.id === id); if (i < 0) return;
    snapshot("format");
    const next = fn({ ...blocks()[i] });
    S.deck.blocks = next ? blocks().map((b, k) => (k === i ? next : b)) : blocks().filter((_, k) => k !== i);
    if (!S.deck.blocks.some(T.isText)) S.deck.blocks.push(newPara());
    S.pick = next ? id : null; ed.refresh(); afterChange(); markPick();
  }
  function markPick() { for (const el of $$("#ed > .nt-obj")) el.classList.toggle("sel", el.dataset.id === S.pick); }
  function imageMenu(id, at) {
    const b = blockAt(id); if (!b) return;
    const width = (f) => changeBlock(id, (x) => ({ ...x, w: Math.max(10, Math.min(S.box.cw, Math.round(f(x.w || 60)))) }));
    const align = (a) => changeBlock(id, (x) => { const y = { ...x }; if (a === "center") delete y.align; else y.align = a; return y; });
    openMenu(at, [{ h: `그림 · 너비 ${Math.round(b.w || 0)}mm` },
      { label: "작게 (-20%)", act: () => width((w) => w * 0.8) }, { label: "크게 (+25%)", act: () => width((w) => w * 1.25) },
      { label: "본문 너비에 맞춤", act: () => width(() => S.box.cw) }, { label: "본문 너비의 절반", act: () => width(() => S.box.cw / 2) }, "-",
      { label: "왼쪽", on: b.align === "left", act: () => align("left") }, { label: "가운데", on: !b.align || b.align === "center", act: () => align("center") }, { label: "오른쪽", on: b.align === "right", act: () => align("right") }, "-",
      { label: "설명(캡션)", act: () => { const t = prompt("그림 설명", b.caption || ""); if (t === null) return; changeBlock(id, (x) => { const y = { ...x }; if (t.trim()) y.caption = t.trim(); else delete y.caption; return y; }); } },
      { label: "그림 지우기", key: "Del", act: () => changeBlock(id, () => null) }]);
  }

  // ---------------------------------------------------------------- 개체(도형·글 상자, PG-103) - 본문 문단에 매이고(anchor) 그 문단이 놓인 쪽(rel page) 또는 그 문단(rel para) 기준 자리에 뜬다
  const objEls = new Map(); let geo = null;  // geo = 쪽 나눔이 정한 치수 {mm, H, G, gap}
  const objs = () => (Array.isArray(S.deck.objects) ? S.deck.objects : (S.deck.objects = []));
  const objAt = (id) => objs().find((o) => o.id === id);
  const lined = (o) => o.shape === "line" || o.shape === "arrow";
  const r1 = (v) => Math.round(v * 10) / 10;
  const edScale = () => { const h = $("#ed"); return h.getBoundingClientRect().width / h.offsetWidth || 1; };
  const blockElOf = (id) => [...$("#ed").children].find((e) => e.dataset.id === id);
  /** 본문 블록 요소의 위(본문 맨 위 기준 px)와 놓인 쪽(0부터) */
  function elPos(el) { const y = (el.getBoundingClientRect().top - $("#ed").getBoundingClientRect().top) / edScale(); return { y, page: Math.max(0, Math.floor((y + 1) / (geo.H + geo.G))) }; }
  function objEl(o) {
    const el = P.objectEl(S.deck, o, { ...ctx, noText: true }); el._obj = o;
    const body = el.querySelector(".pg-obj-body");
    if (body) {  // 안의 글 - 표 칸처럼 편집기를 붙이고 개체를 그 자리에서 고친다(개체 객체가 그대로라 다시 그리지 않아 초점이 남는다)
      if (!o.blocks.length) o.blocks = [newPara()];
      const ce = T.mount(body, {
        get: () => o.blocks, set: (bs, why) => { snapshot(why); o.blocks = bs.length ? bs : [newPara()]; afterChange(); }, newId: () => rid("p"),
        decorate: (x, b) => P.decorate(x, b, S.deck, ctx, P.markers(o.blocks)[b.id]), renderBlock: (b) => P.blockEl(S.deck, b, ctx),
        color: ctx.color, font: ctx.font, onSelect: () => { cur = ce; updTools(); }, undo, redo,
      });
      body.addEventListener("focus", () => { cur = ce; });
      body.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); } });
    }
    const h = document.createElement("i"); h.className = "pg-obj-h"; h.title = "크기"; el.appendChild(h);
    return el;
  }
  /** 개체를 제자리에 놓는다 - 쪽 나눔이 끝날 때마다(매인 문단이 다른 쪽으로 가면 따라간다). 개체 객체가 바뀐 것만 다시 만든다 */
  function drawObjects() {
    if (!geo) return;
    const box = S.box, keep = new Set(), sheet = box.h * geo.mm + geo.gap;
    for (const o of objs()) {
      const a = blockElOf(o.anchor); if (!a) continue;
      const pos = elPos(a); let el = objEls.get(o.id);
      if (!el || el._obj !== o) { if (el) el.remove(); el = objEl(o); objEls.set(o.id, el); }
      const layer = $(o.z === "behind" ? "#objsBack" : "#objs"); if (el.parentNode !== layer) layer.appendChild(el);
      el.style.left = (o.rel === "para" ? box.l + o.x : o.x) * geo.mm + "px";
      el.style.top = (o.rel === "para" ? box.t * geo.mm + pos.y + o.y * geo.mm : pos.page * sheet + o.y * geo.mm) + "px";
      el._page = pos.page; el.classList.toggle("sel", S.obj === o.id); keep.add(o.id);
    }
    for (const [id, el] of [...objEls]) if (!keep.has(id)) { el.remove(); objEls.delete(id); }
  }
  /** 인쇄 직전 - 확대를 풀고 쪽 나눔을 다시 잡은 뒤(끼운 빈 자리가 인쇄의 강제 쪽 나눔이 된다) 개체를 매인 문단 안으로 옮긴다.
   *  인쇄에서는 쪽이 종이 장으로 나뉘어 화면의 자리(종이 기준 px)를 쓸 수 없다 - 문단 기준 자리로 바꿔 그 문단을 따라 찍히게 한다 */
  function enterPrint() {
    if (S.printing || !flow) return;
    $("#paper").style.zoom = 1; flow.rerun();
    if (geo) for (const o of objs()) {
      const el = objEls.get(o.id), a = blockElOf(o.anchor); if (!el || !a) continue;
      const pos = elPos(a), inPage = pos.y - pos.page * (geo.H + geo.G), box = S.box;
      el.style.left = (o.rel === "para" ? o.x : o.x - box.l) * geo.mm - a.offsetLeft + "px";
      el.style.top = (o.rel === "para" ? o.y * geo.mm : (o.y - box.t) * geo.mm - inPage) + "px";
      el.style.zIndex = o.z === "behind" ? "-1" : "2"; el.classList.remove("sel"); a.appendChild(el);
    }
    const refs = $$("#ed [data-fn]").filter((sp) => !sp.closest(".pg-headrep"));
    if (refs.length) {  // 브라우저 인쇄에서는 쪽 아래 각주를 놓을 수 없어 문서 끝에 모아 찍는다(쪽 아래 각주는 Word 로 내보낸 문서에서)
      const d = document.createElement("div"); d.className = "pg-endnotes"; d.contentEditable = "false";
      for (const sp of refs) { const n = document.createElement("div"); n.className = "pg-fnote"; const s = document.createElement("sup"); s.textContent = sp.dataset.fnn || ""; n.append(s, sp.dataset.fn); d.appendChild(n); }
      $("#ed").appendChild(d);
    }
    S.printing = true;
  }
  function leavePrint() {
    if (!S.printing) return; S.printing = false;
    for (const [, el] of objEls) { el.style.zIndex = ""; el.remove(); }
    for (const d of $$("#ed > .pg-endnotes")) d.remove();
    applyZoom(S.zoom || "1"); flow.rerun();
  }
  function pickObj(id) { S.obj = id || null; for (const [k, el] of objEls) el.classList.toggle("sel", k === S.obj); if (id) { S.pick = null; markPick(); } }
  function changeObj(id, fn, why) {
    snapshot(why || "format");
    S.deck.objects = objs().map((o) => (o.id === id ? fn({ ...o }) : o)).filter(Boolean);
    if (!objAt(id)) S.obj = null;
    drawObjects(); afterChange(true);
  }
  /** 문단이 지워지면(합치기·지우기) 거기 매인 개체를 그 자리의 문단(없으면 앞 문단)에 다시 맨다 */
  function reanchor(old, next) {
    const ok = new Set(next.filter((b) => b.type === "p").map((b) => b.id));
    for (const o of objs()) {
      if (ok.has(o.anchor)) continue;
      let j = Math.max(0, Math.min(old.findIndex((b) => b.id === o.anchor), next.length - 1));
      while (j >= 0 && !(next[j] && next[j].type === "p")) j--;
      if (j < 0) j = next.findIndex((b) => b.type === "p");
      if (j >= 0) o.anchor = next[j].id;
    }
  }
  /** 끌어 옮긴 뒤 - 쪽 기준 개체가 다른 쪽으로 가면 그 쪽의 첫 문단에 다시 맨다 */
  function moveObj(o, el, dx, dy) {
    if (o.rel === "para") return changeObj(o.id, (x) => ({ ...x, x: r1(x.x + dx), y: r1(x.y + dy) }));
    const sheet = S.box.h * geo.mm + geo.gap, top = parseFloat(el.style.top) + dy * geo.mm;
    const k = Math.max(0, Math.min((S.pages || 1) - 1, Math.floor((top + 1) / sheet)));
    let anchor = o.anchor, page = el._page;
    if (k !== el._page) { const on = [...$("#ed").children].find((e) => e.classList.contains("nt-p") && elPos(e).page === k); if (on) { anchor = on.dataset.id; page = k; } }
    changeObj(o.id, (x) => ({ ...x, anchor, x: r1(x.x + dx), y: r1((top - page * sheet) / geo.mm) }));
  }
  function onObjDown(e) {
    const el = e.target.closest(".pg-obj"), o = el && objAt(el.dataset.id); if (!o) return;
    pickObj(o.id);
    const handle = e.target.closest(".pg-obj-h");
    if (e.button !== 0 || (e.target.closest(".pg-obj-body") && !handle)) return;  // 글 안을 누르면 글 편집
    e.preventDefault(); if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    const px = geo.mm * edScale(), sx = e.clientX, sy = e.clientY; let dx = 0, dy = 0, moved = false;
    const move = (ev) => {
      dx = (ev.clientX - sx) / px; dy = (ev.clientY - sy) / px; if (!moved && Math.abs(dx) + Math.abs(dy) < 0.5) return; moved = true;
      if (handle) { el.style.width = Math.max(lined(o) ? 0 : 2, o.w + dx) + "mm"; el.style.height = Math.max(lined(o) ? 0 : 2, o.h + dy) + "mm"; }
      else el.style.transform = `translate(${dx * geo.mm}px, ${dy * geo.mm}px)`;
    };
    const up = () => {
      window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up);
      if (!moved) return; el.style.transform = "";
      if (handle) { const min = lined(o) ? 0 : 2, w = r1(Math.max(min, o.w + dx)), h = r1(Math.max(min, o.h + dy)); changeObj(o.id, (x) => ({ ...x, w: w || (h ? 0 : 1), h })); }
      else moveObj(o, el, dx, dy);
    };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
  }
  /** [단] 메뉴 - 지금 커서가 있는 구역의 단 수를 보이고, 여기서부터 단 수 바꾸기(구역 나누기)·단 나누기를 넣는다. 문서 전체의 단 수는 [쪽 설정] */
  function colsMenu(at) {
    const s = ed.selection(), i = s ? blocks().findIndex((b) => b.id === s.f.id) : -1;
    let now = ((S.deck.page || {}).columns || {}).count || 1;
    for (let k = 0; k <= i; k++) { const b = blocks()[k]; if (b.type === "break" && b.kind === "section") now = (b.columns || {}).count || 1; }
    openMenu(at, [{ h: `지금 구역 · ${now}단` }, ...[1, 2, 3].map((n) => ({ label: `여기서부터 ${n}단`, on: n === now, disabled: n === now || i < 0, act: () => insertBreak("section", { count: n, gap: 8 }) })), "-",
      { label: "단 나누기(다음 단으로)", disabled: now < 2 || i < 0, act: () => insertBreak("column") }, { label: "문서 전체의 단 수…(쪽 설정)", act: pageSetup }]);
  }
  const SHAPES = [["rect", "사각형"], ["round", "둥근 사각형"], ["ellipse", "타원"], ["line", "선"], ["arrow", "화살표"], ["bracket-l", "대괄호 ["], ["bracket-r", "대괄호 ]"], ["brace-l", "중괄호 {"], ["brace-r", "중괄호 }"]];
  function insertObj(shape, text) {
    if (!geo) return;
    const paras = blocks().filter((b) => b.type === "p"), s = ed.selection(); if (!paras.length) { toast("문단이 하나는 있어야 도형을 넣을 수 있습니다"); return; }
    let a = s && paras.find((b) => b.id === s.f.id);
    if (!a) { const top = $("#scroll").getBoundingClientRect().top; a = paras.find((b) => { const e = blockElOf(b.id); return e && e.getBoundingClientRect().bottom > top; }) || paras[0]; }
    const pos = elPos(blockElOf(a.id)), box = S.box;
    const size = { line: [40, 0], arrow: [40, 0], "bracket-l": [4, 25], "bracket-r": [4, 25], "brace-l": [5, 25], "brace-r": [5, 25] }[shape] || (text ? [60, 20] : [40, 20]);
    const o = { id: rid("o"), type: "shape", shape, anchor: a.id, rel: "page", x: r1(box.l + 10), y: r1(box.t + (pos.y - pos.page * (geo.H + geo.G)) / geo.mm + 2), w: size[0], h: size[1] };
    if (text) { o.blocks = [newPara()]; o.fill = "#ffffff"; }
    snapshot("format"); S.deck.objects = [...objs(), o]; drawObjects(); pickObj(o.id); afterChange(true);
    if (text) { const b = objEls.get(o.id) && objEls.get(o.id).querySelector(".pg-obj-body"); if (b) b.focus(); }
  }
  function shapeMenu(at) {
    openMenu(at, [{ label: "글 상자", act: () => insertObj("rect", true) }, "-", ...SHAPES.slice(0, 3).map(([k, t]) => ({ label: t, act: () => insertObj(k) })), "-",
      ...SHAPES.slice(3, 5).map(([k, t]) => ({ label: t, act: () => insertObj(k) })), "-", ...SHAPES.slice(5).map(([k, t]) => ({ label: t, act: () => insertObj(k) }))]);
  }
  function objMenu(id, at) {
    const o = objAt(id); if (!o) return;
    const set = (patch) => changeObj(id, (x) => { const y = { ...x, ...patch }; for (const k of Object.keys(y)) if (y[k] === undefined) delete y[k]; return y; });
    const ln = o.line === null ? null : o.line || {}, closed = ["rect", "round", "ellipse"].includes(o.shape), name = (SHAPES.find((x) => x[0] === o.shape) || [])[1] || o.shape;
    const line = (patch) => set({ line: { ...(ln || {}), ...patch } });
    const toRel = () => {  // 기준을 바꿔도 화면의 자리는 그대로 - 좌표만 다시 잰다
      const el = objEls.get(id), a = blockElOf(o.anchor); if (!el || !a) return;
      const pos = elPos(a), sheet = S.box.h * geo.mm + geo.gap, left = parseFloat(el.style.left) / geo.mm, top = parseFloat(el.style.top);
      if (o.rel === "para") set({ rel: "page", x: r1(left), y: r1((top - pos.page * sheet) / geo.mm) });
      else set({ rel: "para", x: r1(left - S.box.l), y: r1((top - S.box.t * geo.mm - pos.y) / geo.mm) });
    };
    const items = [{ h: `${Array.isArray(o.blocks) ? "글 상자 · " : ""}${name} · ${r1(o.w)} × ${r1(o.h)} mm` }];
    if (closed) items.push({ label: "채움 없음", on: !o.fill, act: () => set({ fill: undefined }) }, { label: "채움 - 흰색", on: o.fill === "#ffffff", act: () => set({ fill: "#ffffff" }) },
      { label: "채움 - 회색", on: o.fill === "#eeeeee", act: () => set({ fill: "#eeeeee" }) }, { label: "채움 - 노랑", on: o.fill === "#fff59d", act: () => set({ fill: "#fff59d" }) }, "-");
    if (closed) items.push({ label: "선 없음", on: ln === null, act: () => set({ line: null }) });
    items.push({ label: "실선", on: !!ln && (ln.dash || "solid") === "solid", act: () => line({ dash: "solid" }) }, { label: "긴 점선", on: !!ln && ln.dash === "dash", act: () => line({ dash: "dash" }) }, { label: "점선", on: !!ln && ln.dash === "dot", act: () => line({ dash: "dot" }) },
      { label: "선 가늘게 (0.5pt)", on: !!ln && ln.w === 0.5, act: () => line({ w: 0.5 }) }, { label: "선 보통 (1pt)", on: !!ln && (ln.w === undefined || ln.w === 1), act: () => line({ w: 1 }) }, { label: "선 굵게 (2pt)", on: !!ln && ln.w === 2, act: () => line({ w: 2 }) },
      { label: "선 색 - 검정", on: !!ln && !ln.c, act: () => line({ c: undefined }) }, { label: "선 색 - 강조", on: !!ln && ln.c === "accent", act: () => line({ c: "accent" }) }, { label: "선 색 - 회색", on: !!ln && ln.c === "#999999", act: () => line({ c: "#999999" }) }, "-");
    if (lined(o)) items.push({ label: "기울기 뒤집기(↗ ↘)", on: !!o.flip, act: () => set({ flip: o.flip ? undefined : true }) });
    else if (Array.isArray(o.blocks)) items.push({ label: "글 세로 - 위", on: !o.valign || o.valign === "top", act: () => set({ valign: undefined }) }, { label: "글 세로 - 가운데", on: o.valign === "middle", act: () => set({ valign: "middle" }) }, { label: "안의 글 지우기", act: () => set({ blocks: undefined, valign: undefined }) });
    else items.push({ label: "글 넣기", act: () => { set({ blocks: [newPara()] }); const b = objEls.get(id) && objEls.get(id).querySelector(".pg-obj-body"); if (b) b.focus(); } });
    items.push("-", { label: "글 뒤로", on: o.z === "behind", act: () => set({ z: o.z === "behind" ? undefined : "behind" }) }, { label: "문단을 따라 움직임(문단 기준)", on: o.rel === "para", act: toRel }, "-",
      { label: "지우기", key: "Del", act: () => changeObj(id, () => null) });
    openMenu(at, items);
  }
  /** 그 자리 아래의 개체(글 뒤로 보낸 것 포함) */
  const objUnder = (e) => { const el = document.elementsFromPoint(e.clientX, e.clientY).find((x) => x.classList && x.classList.contains("pg-obj")); return el ? el.dataset.id : null; };
  function bindObjects() {
    for (const layer of [$("#objs"), $("#objsBack")]) {
      layer.addEventListener("pointerdown", onObjDown);
      layer.addEventListener("contextmenu", (e) => { const el = e.target.closest(".pg-obj"); if (!el || e.target.closest(".pg-obj-body")) return; e.preventDefault(); pickObj(el.dataset.id); objMenu(el.dataset.id, { x: e.clientX, y: e.clientY }); });
    }
    // 글 뒤로 보낸 개체는 본문에 가려 눌리지 않는다 - Alt+클릭으로 고르고 Alt+오른쪽 클릭으로 메뉴
    $("#ed").addEventListener("mousedown", (e) => { if (!e.altKey) return; const id = objUnder(e); if (id) { e.preventDefault(); e.stopPropagation(); pickObj(id); if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); } }, true);
    $("#ed").addEventListener("contextmenu", (e) => { if (!e.altKey) return; const id = objUnder(e); if (id) { e.preventDefault(); e.stopPropagation(); pickObj(id); objMenu(id, { x: e.clientX, y: e.clientY }); } }, true);
    document.addEventListener("mousedown", (e) => { if (S.obj && !e.altKey && !e.target.closest(".pg-obj, .menu")) pickObj(null); });
    document.addEventListener("keydown", (e) => {
      if (!S.obj || e.isComposing || (e.key !== "Delete" && e.key !== "Backspace")) return;
      if (e.target.closest && e.target.closest("input, select, textarea, .dlg, .nd-box, [contenteditable=true]")) return;
      e.preventDefault(); changeObj(S.obj, () => null);
    }, true);
  }

  // ---------------------------------------------------------------- AI 요청(공용 패널 nexa-requests.js · 세션 표시 wsession.js) - 슬라이드·시트 편집기와 같은 흐름(PG-081)
  //   요청의 대상 = 본문에서 고른 맨 위 단계 블록들. 요청에는 slide·element = 첫 블록 id, 여러 개면 elements = 블록 id 목록(문서 전체면 비운다) - agents/turn_prompt.md
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let SESS = null, RQ = null; S.reqs = []; S.reqSel = [];
  const topOf = (node) => { let el = node && (node.nodeType === 1 ? node : node.parentElement); const host = $("#ed"); while (el && el.parentElement !== host) el = el.parentElement; return el && el.dataset.id ? el.dataset.id : null; };
  /** 본문의 선택이 걸친 맨 위 단계 블록 id 들(표 칸 안이면 그 표) - 요청 칸으로 초점이 가도 남게 기억해 둔다 */
  function trackReqSel() {
    const s = document.getSelection(); if (!s || !s.rangeCount || !$("#ed").contains(s.anchorNode)) return;
    const a = topOf(s.anchorNode), f = topOf(s.focusNode), ids = blocks().map((b) => b.id), ia = ids.indexOf(a), ib = ids.indexOf(f); if (ia < 0 || ib < 0) return;
    S.reqSel = ids.slice(Math.min(ia, ib), Math.max(ia, ib) + 1); renderReqTarget();
  }
  const reqBlocks = () => ($("#reqWhole").checked ? [] : S.reqSel.filter((id) => blockAt(id)));
  const blockBrief = (b) => { if (!b) return "?"; if (b.type === "table") return "표"; if (b.type === "image") return "그림"; if (b.type === "break") return "쪽 나누기"; const t = T.text(b.runs || []).trim(); return t ? `"${t.length > 14 ? t.slice(0, 14) + "…" : t}"` : "빈 문단"; };
  function renderReqTarget() {
    const ids = reqBlocks(), on = document.activeElement && document.activeElement.closest && !!document.activeElement.closest("#side .compose");
    $("#reqTarget").textContent = !ids.length ? "문서 전체" : ids.length === 1 ? blockBrief(blockAt(ids[0])) : `${blockBrief(blockAt(ids[0]))} 부터 블록 ${ids.length}개`;
    for (const el of $("#ed").children) el.classList.toggle("req-on", on && ids.includes(el.dataset.id));
  }
  const reqIds = (r) => (Array.isArray(r.elements) && r.elements.length ? r.elements : r.element ? [r.element] : r.slide ? [r.slide] : []);
  function gotoReq(r) {
    const ids = reqIds(r).filter((id) => blockAt(id)); if (!ids.length) return;
    const el = blockElOf(ids[0]); if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
    const a = blockAt(ids[0]), z = blockAt(ids[ids.length - 1]);
    if (T.isText(a) && T.isText(z)) { ed.focus(); ed.select({ id: a.id, off: 0 }, { id: z.id, off: T.length(z.runs) }); }
  }
  const PAGE_TARGET = { key: () => S.id, current: () => S.id, num: () => 1, scope: "문서", goto: gotoReq,
    label: (r) => { const ids = reqIds(r); return !ids.length ? "문서 전체" : ids.length === 1 ? blockBrief(blockAt(ids[0])) : `${blockBrief(blockAt(ids[0]))} 부터 ${ids.length}개`; } };
  function renderReqs() {
    if (!S.deck || !RQ) return;
    const recent = S.reqs.filter(RQ.recent), older = S.reqs.length - recent.length, open = S.reqs.filter((q) => q.status === "open" || q.status === "working").length;
    $("#reqFilter").innerHTML = `<span class="hint">최근 요청 ${recent.length}건</span><span style="flex:1"></span><button class="chip sm" id="reqMore" title="이전 요청까지 모두 찾아보기">더보기${older ? ` · 이전 ${older}` : ""}</button>`;
    $("#reqList").innerHTML = recent.length ? RQ.threadsHtml(recent) : `<div class="hint" style="padding:18px;text-align:center">최근 요청이 없습니다<br>문단을 고르고 위에 적어 보내세요.</div>`;
    $("#reqHint").innerHTML = RQ.sessionHint();
    $("#sideBtn").textContent = open ? `AI 요청 · ${open}` : "AI 요청";
    RQ.afterRender();
  }
  async function sendReq() {
    const text = $("#reqText").value.trim(); if (!text && !RQ.att.slot("tab").length) { $("#reqText").focus(); return; }
    clearTimeout(saveT); if (S.dirty) await save();  // 세션이 지금 화면 내용을 보고 고치게 먼저 저장
    const ids = reqBlocks(), body = { action: "add", status: "open", slide: ids[0] || null, text: text || "(첨부 참고)" };
    if (ids.length) { body.element = ids[0]; if (ids.length > 1) body.elements = ids.slice(0, 50); }
    const r = await RQ.add(body, "tab", { flush: true }); if (!r) return;
    $("#reqText").value = "";
    toast(RQ.connected() ? "요청을 세션에 보냈습니다" : "요청을 남겼습니다 - 세션이 연결되면 전달됩니다");
  }
  function showSide(on) {
    document.body.classList.toggle("noside", !on);
    try { localStorage.setItem("nexaPageSide", on ? "1" : "0"); } catch (e) { /* 기억 못 해도 그대로 */ }
    if (S.zoom === "fit") applyZoom("fit");
  }
  async function bindRequests() {
    if (!window.NexaRequests) return;
    if (window.NexaSession) SESS = NexaSession.create({ api, toast, openMenu, esc, base: BASE, deckId: () => S.id, onChange: (st, changed) => { S.session = st; if (changed) renderReqs(); } });
    $("#sessChip").onclick = (e) => (SESS ? SESS.menu(e.currentTarget) : null);
    RQ = NexaRequests.create({ api, toast, esc, base: BASE, deckId: () => S.id, session: SESS, getReqs: () => S.reqs, setReqs: (l) => { S.reqs = l; }, onChange: renderReqs,
      target: PAGE_TARGET, att: { boxes: { tab: "#reqAtt", fu: "#fuAtt" } }, onDeckChanged: () => poll() });
    $("#sideBtn").onclick = () => { const on = document.body.classList.contains("noside"); showSide(on); if (on) $("#reqText").focus(); };
    $("#reqSend").onclick = sendReq;
    $("#reqText").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendReq(); } });
    $("#reqWhole").addEventListener("change", renderReqTarget);
    $("#side .compose").addEventListener("focusin", renderReqTarget); $("#side .compose").addEventListener("focusout", () => setTimeout(renderReqTarget, 0));
    $("#reqList").addEventListener("click", async (e) => { if (await RQ.click(e)) return; const c = e.target.closest(".req[data-rid]"); const r = c && S.reqs.find((q) => q.id === c.dataset.rid); if (r && !e.target.closest("button, a, textarea, input")) gotoReq(r); });
    $("#reqList").addEventListener("keydown", (e) => RQ.keydown(e));
    RQ.att.wire($("#side .compose"), "tab");
    $("#side .compose").addEventListener("click", (e) => RQ.click(e));
    $("#reqFilter").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b && b.id === "reqMore") RQ.openHist(); });
    document.addEventListener("selectionchange", trackReqSel);
    await RQ.load(); renderReqs(); renderReqTarget();
  }

  // ---------------------------------------------------------------- 링크 · 찾기/바꾸기
  function setLink() {
    const e0 = cur || ed, st = e0.state(); if (!st.sel) return;
    if (st.sel.a.id === st.sel.f.id && st.sel.a.off === st.sel.f.off) { toast("링크를 걸 글을 먼저 고르세요"); return; }
    const url = prompt("링크 주소(비우면 링크를 풉니다)", st.marks.link || "https://"); if (url === null) return;
    const u = url.trim();
    if (u && !/^(https?:|mailto:)/i.test(u)) { toast("http(s):// 또는 mailto: 로 시작하는 주소만 걸 수 있습니다", 4000); return; }
    e0.setMark("link", u || null);
  }
  // ---------------------------------------------------------------- 각주(PG-105) - 글 조각의 fn(각주 글). 번호는 문서 순서, 글은 그 참조가 놓인 쪽의 아래
  const FN = { cache: new Map() };
  /** 각주 한 줄의 높이(px) - 쪽 나눔이 자리를 내줄 때 쓴다. 본문 너비에 그려 재고 (글 + 자릿수)로 기억한다 */
  function noteH(span) {
    const key = (span.dataset.fnn || "0").length + "|" + S.box.cw + "|" + span.dataset.fn;
    if (!FN.cache.has(key)) {
      const m = $("#fnMeasure"); m.style.width = S.box.cw + "mm"; m.innerHTML = "";
      const d = document.createElement("div"); d.className = "pg-fnote"; const s = document.createElement("sup"); s.textContent = span.dataset.fnn || "0"; d.append(s, span.dataset.fn); m.appendChild(d);
      FN.cache.set(key, d.getBoundingClientRect().height / edScale()); if (FN.cache.size > 2000) FN.cache.clear();
    }
    return FN.cache.get(key);
  }
  const noteSep = () => (geo ? geo.mm : 3.78) * 2.5;  // 구분선 + 위아래 틈(mm 2.5)
  /** 각주 번호를 문서 순서로 다시 매긴다(쪽 나눔 전에 - 번호 자릿수가 줄 나눔에 든다) */
  function numberNotes() { let k = 0; for (const sp of $$("#ed [data-fn]")) { if (sp.closest(".pg-headrep")) continue; const v = String(++k); if (sp.dataset.fnn !== v) sp.dataset.fnn = v; } }
  /** 쪽마다 그 쪽에 참조가 있는 각주를 본문 아래에 그린다(쪽 나눔이 끝날 때마다) */
  function drawNotes() {
    const layer = $("#fnotes"); layer.replaceChildren(); if (!geo) return;
    const box = S.box, sheet = box.h * geo.mm + geo.gap, by = new Map(), top0 = $("#ed").getBoundingClientRect().top, z = edScale();
    for (const sp of $$("#ed [data-fn]")) {
      if (sp.closest(".pg-headrep")) continue;
      const rs = sp.getClientRects(), r = rs[rs.length - 1]; if (!r) continue;
      const k = Math.max(0, Math.floor(((r.top - top0) / z + 1) / (geo.H + geo.G)));
      if (!by.has(k)) by.set(k, []); by.get(k).push(sp);
    }
    for (const [k, list] of by) {
      const d = document.createElement("div"); d.className = "pg-fnotes"; d.dataset.page = k + 1;
      d.style.left = box.l + "mm"; d.style.width = box.cw + "mm"; d.style.top = `calc(${k * sheet}px + ${box.h - box.b}mm)`;
      for (const sp of list) { const n = document.createElement("div"); n.className = "pg-fnote"; const s = document.createElement("sup"); s.textContent = sp.dataset.fnn || ""; n.append(s, sp.dataset.fn); d.appendChild(n); }
      layer.appendChild(d);
    }
  }
  /** 각주 달기·고치기·떼기 - 고른 글 뒤(선택이 비었으면 커서 앞 글자 뒤)에 번호를 단다 */
  function setFn() {
    const e0 = cur || ed, st = e0.state(); if (!st.sel) return;
    let { a, f } = st.sel;
    if (a.id === f.id && a.off === f.off) {
      if (a.off < 1) { toast("각주를 달 글자 뒤에 커서를 두거나 글을 고르세요"); return; }
      a = { id: f.id, off: f.off - 1 }; e0.select(a, f);
    }
    const cur0 = e0.state().marks.fn || "";
    const t = prompt(cur0 ? "각주 글(비우면 각주를 뗍니다)" : "각주 글", cur0); if (t === null) return;
    e0.setMark("fn", t.trim().slice(0, 2000) || null);
    e0.select(f, f);
  }

  /** 윗주 - 고른 글 위에 작은 글을 단다(비우면 뗀다). 줄 간격이 좁으면 윗줄과 겹치므로 그 문단의 줄 간격이 2 보다 작으면 2 로 넓힌다 */
  function setRuby() {
    const e0 = cur || ed, st = e0.state(); if (!st.sel) return;
    if (st.sel.a.id === st.sel.f.id && st.sel.a.off === st.sel.f.off) { toast("윗주를 달 글을 먼저 고르세요"); return; }
    const t = prompt("윗주(비우면 뗍니다)", st.marks.ruby || ""); if (t === null) return;
    const v = t.trim().slice(0, 60);
    e0.setMark("ruby", v || null);
    if (v && e0 === ed) {
      const b = blockAt(st.sel.f.id), line = b && (b.line !== undefined ? b.line : P.styleOf(S.deck, b.style).line || 1.6);
      if (b && line < 2) { ed.select(st.sel.a, st.sel.f); ed.blockAttrs({ line: 2 }); }
    }
  }
  /** 본문 문단에서 글을 찾는다(대소문자 무시) → [{id, from, to}]. 표 칸 안은 [모두 바꾸기]만 다룬다 */
  function findAll(q) {
    const out = []; if (!q) return out;
    const low = q.toLowerCase();
    for (const b of blocks()) {
      if (!T.isText(b)) continue;
      const t = T.text(b.runs).toLowerCase();
      for (let i = t.indexOf(low); i >= 0; i = t.indexOf(low, i + Math.max(1, low.length))) out.push({ id: b.id, from: i, to: i + q.length });
    }
    return out;
  }
  const FD = { hits: [], at: -1 };
  function findNext(step = 1) {
    FD.hits = findAll($("#fdFind").value);
    if (!FD.hits.length) { $("#fdInfo").textContent = "없음"; return null; }
    const s = ed.selection();
    if (FD.at < 0 && s) {  // 처음에는 커서 뒤의 첫 것부터
      const order = blocks().map((b) => b.id), k = FD.hits.findIndex((h) => order.indexOf(h.id) > order.indexOf(s.f.id) || (h.id === s.f.id && h.from >= s.f.off));
      FD.at = (k < 0 ? 0 : k) - step;
    }
    FD.at = (FD.at + step + FD.hits.length) % FD.hits.length;
    const h = FD.hits[FD.at];
    cur = ed; ed.select({ id: h.id, off: h.from }, { id: h.id, off: h.to });
    const el = document.querySelector(`#ed > [data-id="${h.id}"]`); if (el) el.scrollIntoView({ block: "center" });
    $("#fdInfo").textContent = `${FD.at + 1} / ${FD.hits.length}`;
    return h;
  }
  /** 글을 바꾼다 - 그 자리의 서식을 잇는다. 뒤에서부터 바꿔 앞의 위치가 밀리지 않게 */
  function replaceHits(hits, repl) {
    if (!hits.length) return 0;
    snapshot("format");
    let bs = blocks();
    for (const h of hits.slice().reverse()) bs = bs.map((b) => (b.id === h.id ? { ...b, runs: T.replaceText(b.runs, h.from, h.to, repl) } : b));
    S.deck.blocks = bs;
    return hits.length;
  }
  function replaceAll() {
    const q = $("#fdFind").value, repl = $("#fdRepl").value; if (!q) return;
    let n = replaceHits(findAll(q), repl);
    // 표 칸 안의 문단도 - 표 블록을 새로 만들어 갈아 끼운다
    const low = q.toLowerCase();
    S.deck.blocks = blocks().map((b) => {
      if (b.type !== "table") return b;
      let hit = 0;
      const rows = b.rows.map((r) => ({ ...r, cells: r.cells.map((c) => ({ ...c, blocks: (c.blocks || []).map((x) => {
        if (!T.isText(x)) return x;
        let runs = x.runs; const t = T.text(runs).toLowerCase(), at = [];
        for (let i = t.indexOf(low); i >= 0; i = t.indexOf(low, i + Math.max(1, low.length))) at.push(i);
        for (const i of at.reverse()) { runs = T.replaceText(runs, i, i + q.length, repl); hit++; }
        return at.length ? { ...x, runs } : x;
      }) })) }));
      if (!hit) return b;
      if (!n) snapshot("format");
      n += hit; return { ...b, rows };
    });
    if (n) { cur = ed; ed.refresh(); afterChange(); }
    FD.at = -1; $("#fdInfo").textContent = n ? `${n}곳 바꿈` : "없음";
  }
  function replaceOne() {
    const q = $("#fdFind").value; if (!q) return;
    const s = ed.selection(), h = FD.hits[FD.at];
    if (h && s && s.a.id === h.id && Math.min(s.a.off, s.f.off) === h.from && Math.max(s.a.off, s.f.off) === h.to) {
      replaceHits([h], $("#fdRepl").value); cur = ed; ed.refresh(); afterChange(); FD.at -= 1;
    }
    findNext(1);
  }
  function openFind() {
    const bar = $("#findBar"); bar.style.display = "flex"; FD.at = -1; $("#fdInfo").textContent = "";
    const st = ed.state();
    if (st.sel && st.sel.a.id === st.sel.f.id && st.sel.a.off !== st.sel.f.off) { const b = blockAt(st.sel.a.id); if (b) $("#fdFind").value = T.text(b.runs).slice(Math.min(st.sel.a.off, st.sel.f.off), Math.max(st.sel.a.off, st.sel.f.off)); }
    $("#fdFind").focus(); $("#fdFind").select();
  }
  function closeFind() { $("#findBar").style.display = "none"; ed.focus(); }

  /** 나누기 넣기 - 쪽(기본) · 단("column" - 다음 단으로) · 구역("section" + columns - 여기서부터 단 수를 바꾼다) */
  function insertBreak(kind, columns) {
    const s = ed.selection(); if (!s) return;
    const i = blocks().findIndex((b) => b.id === s.f.id); if (i < 0) return;
    snapshot("enter");
    const br = { id: newId(), type: "break", kind: typeof kind === "string" ? kind : "page", ...(columns ? { columns } : {}) }, p = { id: newId(), type: "p", runs: [] };
    S.deck.blocks = [...blocks().slice(0, i + 1), br, p, ...blocks().slice(i + 1)];
    ed.refresh({ a: { id: p.id, off: 0 }, f: { id: p.id, off: 0 } }); afterChange();
  }

  // ---------------------------------------------------------------- 서식 막대
  function updTools() {
    if (!ed) return;
    const e0 = cur || ed, st = e0.state(), inCell = e0 !== ed, b = st.sel ? (inCell ? null : blockAt(st.sel.f.id)) : null;
    for (const el of $$("#tools [data-mark]")) el.classList.toggle("on", !!st.marks[el.dataset.mark]);
    const align = b && (b.align || P.styleOf(S.deck, b.style).align || "left");
    for (const el of $$("#tools [data-align]")) el.classList.toggle("on", !!b && el.dataset.align === align);
    for (const el of $$("#tools [data-list]")) el.classList.toggle("on", !!(b && b.list && b.list.kind === el.dataset.list));
    $("#selStyle").value = (b && T.isText(b) && (b.style || "body")) || "body";
    $("#selSize").value = st.marks.size ? String(st.marks.size) : "";
    $("#selFont").value = ["body", "title", "mono"].includes(st.marks.font) ? st.marks.font : "";
    $("#selLine").value = b && b.line ? String(b.line) : "";
    const lk = $("[data-act=link]"); if (lk) lk.classList.toggle("on", !!st.marks.link);
    const rb = $("[data-act=ruby]"); if (rb) rb.classList.toggle("on", !!st.marks.ruby);
    const fb = $("[data-act=fn]"); if (fb) fb.classList.toggle("on", !!st.marks.fn);
    const sh = $("[data-act=shade]"); if (sh) sh.classList.toggle("on", !!(b && b.fill));
    $("[data-act=undo]").disabled = !S.undo.length; $("[data-act=redo]").disabled = !S.redo.length;
  }
  function bindTools() {
    const sel = $("#selStyle");
    sel.replaceChildren(...Object.entries(S.deck.styles).map(([k, v]) => { const o = document.createElement("option"); o.value = k; o.textContent = v.name || k; return o; }));
    sel.onchange = () => { (cur || ed).blockAttrs({ style: sel.value === "body" ? null : sel.value }); };
    $("#selSize").onchange = (e) => { (cur || ed).setMark("size", e.target.value ? +e.target.value : null); };
    $("#selFont").onchange = (e) => { (cur || ed).setMark("font", e.target.value || null); };
    $("#selLine").onchange = (e) => { (cur || ed).blockAttrs({ line: e.target.value ? +e.target.value : null }); };
    $("#fdNext").onclick = () => findNext(1); $("#fdOne").onclick = replaceOne; $("#fdAll").onclick = replaceAll; $("#fdClose").onclick = closeFind;
    $("#fdFind").oninput = () => { FD.at = -1; $("#fdInfo").textContent = ""; };
    $("#findBar").addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); closeFind(); } else if (e.key === "Enter") { e.preventDefault(); if (e.target.id === "fdRepl") replaceOne(); else findNext(e.shiftKey ? -1 : 1); } });
    document.addEventListener("keydown", (e) => {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === "f" || k === "h") { e.preventDefault(); openFind(); } else if (k === "k") { e.preventDefault(); setLink(); }
    });
    $("#tools").addEventListener("mousedown", (e) => { if (e.target.closest("button")) e.preventDefault(); });  // 누를 때 본문 선택을 잃지 않게
    $("#tools").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b || b.disabled) return;
      const now = cur || ed, body = now === ed;  // 표 칸 안에서는 글자 서식·정렬만(목록·들여쓰기·쪽 나누기는 본문에서)
      if (b.dataset.mark) now.toggle(b.dataset.mark);
      else if (b.dataset.align) now.blockAttrs({ align: b.dataset.align === "left" ? null : b.dataset.align });
      else if (!body && (b.dataset.list || ["indent", "outdent", "break", "clear", "table", "image"].includes(b.dataset.act))) toast("표 칸 안에서는 아직 쓸 수 없습니다");
      else if (b.dataset.list) setList(b.dataset.list);
      else ({ undo, redo, indent: () => shiftLevel(1), outdent: () => shiftLevel(-1), break: insertBreak, setup: pageSetup,
        color: () => now.toggle("c", $("#inColor").value), hl: () => now.toggle("hl", $("#inHl").value), table: insertTable, cols: () => colsMenu(b), shape: () => shapeMenu(b), image: () => $("#inImage").click(), link: setLink, ruby: setRuby, fn: setFn, find: openFind,
        shade: () => { const e0 = cur || ed, st0 = e0.state(), b0 = st0.sel && e0 === ed ? blockAt(st0.sel.f.id) : null; e0.blockAttrs({ fill: b0 && b0.fill ? null : "#e6e6e6" }); },
        clear: () => { const s = ed.selection(); if (s) { snapshot("format"); let bs = blocks(); for (const x of T.spans(bs, s.a, s.f)) bs = bs.map((y, k) => (k === x.i ? { ...y, runs: T.clearMarks(y.runs, x.from, x.to, ["link"]) } : y)); S.deck.blocks = bs; ed.refresh(s); afterChange(); } },
      })[b.dataset.act]?.();
      updTools();
    });
  }
  /** 본문 키 - 편집 엔진보다 먼저 본다(목록 단계 · 빈 목록 문단에서 Enter/Backspace 는 목록 풀기 · Ctrl+Enter 쪽 나누기 · Ctrl+S) */
  function onKey(e) {
    if (e.isComposing) return;
    if (e.target.closest && e.target.closest(".pg-cell")) {  // 표 칸 안 - Tab 은 다음 칸으로, 그 밖의 본문 전용 키는 건드리지 않는다
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
      else if (e.key === "Tab") {
        e.preventDefault();
        const cells = [...e.target.closest("table").querySelectorAll(".pg-cell")], k = cells.indexOf(e.target.closest(".pg-cell")) + (e.shiftKey ? -1 : 1);
        if (cells[k]) { cells[k].focus(); const r = document.createRange(); r.selectNodeContents(cells[k]); r.collapse(false); const sl = getSelection(); sl.removeAllRanges(); sl.addRange(r); }
      }
      return;
    }
    const s = ed.selection(), b = s && blockAt(s.f.id), mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); save(); return; }
    if (mod && e.key === "Enter") { e.preventDefault(); e.stopPropagation(); insertBreak(); return; }
    if (e.key === "Tab" && !mod && !e.altKey) { e.preventDefault(); shiftLevel(e.shiftKey ? -1 : 1); return; }
    const emptyList = b && b.list && T.isText(b) && !b.runs.length && s.a.id === s.f.id;
    const headOfList = b && b.list && s.a.id === s.f.id && s.a.off === 0 && s.f.off === 0;
    if ((e.key === "Enter" && !e.shiftKey && emptyList) || (e.key === "Backspace" && headOfList)) {  // 단계가 있으면 한 단계 내어쓰고, 없으면 목록을 푼다
      e.preventDefault(); e.stopPropagation();
      mapSel((x) => { if ((x.list.level || 0) > 0) return { ...x, list: { ...x.list, level: x.list.level - 1 } }; const y = { ...x }; delete y.list; return y; });
    }
  }

  // ---------------------------------------------------------------- 시작
  async function loadDeck() {
    if (!S.id) { setStatus("error", "문서 없음"); toast("주소에 ?deck=<문서 id> 가 필요합니다", 6000); return false; }
    const r = await fetch(`${BASE}/api/deck/${encodeURIComponent(S.id)}`, { cache: "no-store" });
    if (!r.ok) { setStatus("error", "열기 실패"); toast(`문서를 열지 못했습니다(${r.status})`, 6000); return false; }
    const deck = await r.json();
    if (deck.kind !== "page") { location.replace(NexaKinds.url({ id: S.id, kind: deck.kind })); return false; }  // 다른 종류면 그 편집기로
    if (!Array.isArray(deck.blocks) || !deck.blocks.length) deck.blocks = [{ id: "b01", type: "p", runs: [] }];
    S.deck = deck; S.version = r.headers.get("X-Deck-Version"); S.savedJson = deckJson(); S.undo = []; S.redo = []; S.dirty = false; S.conflict = false;
    return true;
  }
  // ---------------------------------------------------------------- 밖의 변경 받기 - 다른 창·AI(save_deck)가 저장하면 따라간다
  //   3초마다 판(/api/version)을 본다. 내가 고치는 중이면 바로 저장해 서버에서 합치고(문단 단위 병합), 아니면 문서를 다시 읽는다.
  //   실시간 연결(SSE)·함께 보는 사람 표시는 공용 뼈대로 옮길 때(PG-109) 슬라이드·시트와 같이 쓴다
  let pollT = 0, polling = false;
  async function poll() {
    if (polling || !S.deck || S.saving || S.conflict || document.hidden) return;
    polling = true;
    try {
      const r = await api("GET", `/api/version/${encodeURIComponent(S.id)}`);
      if (!r.ok || !r.data) return;
      if (Array.isArray(r.data.deckIds) && !r.data.deckIds.includes(S.id)) { clearInterval(pollT); setStatus("error", "지워진 문서"); toast("이 문서가 지워졌습니다", 8000); return; }
      if (r.data.session && SESS) SESS.render(r.data.session, r.data.activity);  // 세션 연결 표시
      if (RQ) await RQ.sync(r.data);                                              // 요청 파일이 바뀌었으면 다시 읽기(슬라이드·시트와 같다)
      if (r.data.deck === S.version || S.saving) return;
      if (S.dirty) { clearTimeout(saveT); await save(); return; }  // 내 변경이 있으면 저장하면서 합친다
      const d = await fetch(`${BASE}/api/deck/${encodeURIComponent(S.id)}`, { cache: "no-store" });
      if (!d.ok) return;
      const deck = await d.json(), ver = d.headers.get("X-Deck-Version");
      if (S.dirty || S.saving || deck.kind !== "page") return;  // 읽는 사이 내가 고쳤으면 다음 번에
      const sel = cur === ed ? ed.selection() : null;
      const cell = document.activeElement && document.activeElement.closest ? document.activeElement.closest("#ed td, #ed th") : null, cellId = cell && cell.dataset.id;  // 표 칸에서 치던 중이면 그 칸으로 돌아간다
      sealUndo(deckJson());  // 실행 취소 기록은 남긴다 - 되돌리면 내 편집만 거꾸로
      S.deck = deck; S.version = ver; S.savedJson = deckJson();
      cur = ed; S.pick = null; layout(); ed.refresh(sel && blockAt(sel.f.id) ? sel : null); decorateAll(); updTools();
      if (cellId) {  // 표가 다시 그려져 칸의 초점이 빠졌다 - 같은 칸(id)이 남아 있으면 글 끝에 커서를 둔다
        const host = [...document.querySelectorAll("#ed td, #ed th")].find((x) => x.dataset.id === cellId);
        const box = host && host.querySelector(".pg-cell");
        if (box) { box.focus(); const rg = document.createRange(); rg.selectNodeContents(box); rg.collapse(false); const sl = getSelection(); sl.removeAllRanges(); sl.addRange(rg); }
      }
      $("#docTitle").value = S.deck.title || "";
      toast("밖에서 바뀐 내용을 불러왔습니다", 2500);
    } catch (e) { /* 서버가 잠깐 끊김 - 다음 번에 */ } finally { polling = false; }
  }
  async function deckListMenu(btn) {
    const r = await api("GET", "/api/decks"), list = r.ok && Array.isArray(r.data) ? r.data : [];
    openMenu(btn, [{ h: `문서 ${list.length}개` }, ...list.map((d) => ({ label: `${NexaKinds.of(d).icon} ${d.title || d.id}`, on: d.id === S.id, act: async () => { if (d.id === S.id) return; if (S.dirty) await save(); location.href = NexaKinds.url(d); } })),
      "-", { label: "새 문서", act: async () => { const n = await NexaNewDoc.open({ api, kind: "page" }); if (!n) return; if (S.dirty) await save(); location.href = NexaKinds.url(n); } }]);
  }
  /** 내보내기 - 저장한 뒤 서버가 out/<id>.docx(·pdf)를 만들고 내려받는다. PDF 는 Word 가 있을 때만(없으면 [인쇄] 안내) */
  async function doExport(pdf, via) {
    if (S.dirty) await save();
    if (S.dirty || S.conflict) { toast("저장되지 않은 변경이 있어 내보내지 못했습니다", 5000); return; }
    toast(pdf ? "PDF 를 만드는 중…" : "Word 문서를 만드는 중…", 60000);
    const r = await api("POST", `/api/export/${encodeURIComponent(S.id)}${pdf ? "?pdf=1" + (via ? "&via=" + via : "") : ""}`);
    if (!r.ok || !r.data || !r.data.ok) { toast((r.data && r.data.error) || `내보내기 실패(${r.status})`, 8000); return; }
    const a = document.createElement("a"); a.href = BASE + r.data.url; a.download = r.data.name || ""; document.body.appendChild(a); a.click(); a.remove();
    toast(`내보냈습니다: ${r.data.name || r.data.url}${r.data.pages ? ` (${r.data.pages}쪽)` : ""}`, 5000);
  }
  async function init() {
    { let on = "0"; try { on = localStorage.getItem("nexaPageSide") || "0"; } catch (e) { /* 기본값 */ } document.body.classList.toggle("noside", on !== "1"); }
    P.injectCss();
    await loadTokens();
    if (!(await loadDeck())) return;
    document.title = `${S.deck.title || S.id} - 페이지`;
    $("#docTitle").value = S.deck.title || "";
    $("#docTitle").onchange = (e) => { const t = e.target.value.trim(); if (!t || t === S.deck.title) { e.target.value = S.deck.title || ""; return; } snapshot("format"); S.deck.title = t; document.title = `${t} - 페이지`; afterChange(true); };
    layout();
    ed = T.mount($("#ed"), {
      get: blocks, set: (b, why) => { snapshot(why); reanchor(S.deck.blocks, b); S.deck.blocks = b; afterChange(); }, newId,
      nextStyle: (b) => { const n = P.styleOf(S.deck, b.style).next; return n === undefined ? undefined : n === "body" ? null : n; },
      decorate: (el, b) => P.decorate(el, b, S.deck, ctx, P.markers(blocks())[b.id]),
      renderBlock: (b) => (b.type === "table" ? tableEl(b) : P.blockEl(S.deck, b, ctx)),
      color: ctx.color, font: ctx.font, onSelect: () => { cur = ed; updTools(); }, undo, redo,
    });
    cur = ed;
    // 실시간 쪽 나눔 - 쪽 경계에 빈 자리를 끼운다. 인쇄(브라우저·서버 Chrome)는 브라우저가 쪽을 나누므로 쉰다
    flow = NexaPageFlow.create({
      host: $("#ed"), box: () => S.box, off: () => !!S.printing,
      saveSel: () => (document.activeElement === $("#ed") ? ed.selection() : null), restoreSel: (s) => ed.select(s.a, s.f),
      noteH, noteSep, prepare: numberNotes, columns: () => (S.deck.page || {}).columns,
      onPages: (n, info) => { geo = info; drawSheets(n); pageInfo(); drawObjects(); drawNotes(); },
    });
    window.addEventListener("beforeprint", enterPrint);
    window.addEventListener("afterprint", leavePrint);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => flow.reflow());
    $("#ed").addEventListener("keydown", onKey, true);
    bindTools(); bindObjects(); decorateAll(); updTools();
    $("#inImage").onchange = async (e) => { const f = e.target.files[0]; e.target.value = ""; await insertImage(f); };
    // 그림·쪽 나누기 고르기 - 누르면 고르고(Del·Backspace 로 지움), 그림은 오른쪽 클릭으로 크기·정렬
    $("#ed").addEventListener("mousedown", (e) => { const o = e.target.closest("#ed > .nt-obj"); S.pick = o && !o.classList.contains("pg-table") ? o.dataset.id : null; markPick(); });
    $("#ed").addEventListener("contextmenu", (e) => { const o = e.target.closest("#ed > .pg-image"); if (!o) return; e.preventDefault(); S.pick = o.dataset.id; markPick(); imageMenu(o.dataset.id, { x: e.clientX, y: e.clientY }); });
    document.addEventListener("keydown", (e) => {
      if (!S.pick || e.isComposing || (e.key !== "Delete" && e.key !== "Backspace")) return;
      if (e.target.closest && e.target.closest("input, select, textarea, .dlg, .nd-box")) return;
      e.preventDefault(); changeBlock(S.pick, () => null);
    }, true);
    $("#btnDecks").onclick = (e) => deckListMenu(e.currentTarget);
    $("#btnPrint").onclick = () => window.print();
    $("#btnExport").onclick = (e) => openMenu(e.currentTarget, [{ label: "Word 문서 (.docx)", act: () => doExport(false) }, { label: "PDF (Word 로 변환)", act: () => doExport(true) }, { label: "PDF (화면 그대로)", act: () => doExport(true, "chrome") }], { right: true });
    $("#bnMine").onclick = () => save(true);
    $("#bnTheirs").onclick = async () => { if (await loadDeck()) { banner(false); cur = ed; S.pick = null; layout(); ed.refresh(); decorateAll(); setStatus("saved", "저장됨"); } };
    document.addEventListener("mousedown", (e) => { if (!e.target.closest(".menu")) closeMenu(); });
    window.addEventListener("resize", () => { if (S.zoom === "fit") applyZoom("fit"); else pageLines(); });
    $("#selZoom").onchange = (e) => applyZoom(e.target.value);
    { let z = "1"; try { z = localStorage.getItem("nexaPageZoom") || "1"; } catch (e) { /* 기본값 */ } if ([...$("#selZoom").options].some((o) => o.value === z)) { $("#selZoom").value = z; applyZoom(z); } }
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });
    setStatus("saved", "저장됨");
    if (new URLSearchParams(location.search).get("print") === "1") {
      if (document.fonts && document.fonts.ready) await Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 3000))]);  // 글꼴이 떠야 줄 나눔이 인쇄와 같다
      enterPrint(); document.body.classList.add("printing"); return;
    }  // 서버의 Chrome 인쇄(PDF) - 커서·초점 없이 그대로 찍힌다
    await bindRequests(); poll();
    pollT = setInterval(poll, 3000);  // 밖의 변경(다른 창·AI 저장) 따라가기
    const first = blocks().find(T.isText); if (first) { ed.focus(); ed.select({ id: first.id, off: T.length(first.runs) }); }
    window.NexaPageEditor = { S, ed, save, undo, redo, poll, flow };  // 시험·디버깅용
  }
  init();
})();
