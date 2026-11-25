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
  let ed = null;
  // 색·글꼴 토큰 → CSS 값. 작업 공간 토큰(tokens.json)을 읽어 오는 것은 서식 막대 작업(PG-043)에서 - 그 전에는 기본값
  const COLORS = { accent: "#c8553d", muted: "#7a756d", ink: "#1f1f1f" };
  const FONTS = { body: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif', title: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif', mono: 'Consolas, "D2Coding", monospace' };
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
  function restore(from, to) {
    const e = from.pop(); if (!e) return;
    to.push({ json: deckJson(), sel: ed.selection() });
    S.deck = JSON.parse(e.json); S.lastWhy = "";
    layout(); ed.refresh(e.sel); afterChange(true);
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
        S.savedJson = JSON.stringify(r.data.deck); S.deck = NexaMerge.afterSave(body, now, r.data.deck);
        layout(); ed.refresh(sel); toast(NexaMerge.notice(r.data.conflicts).text, 3500);
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
  /** 종이 치수(mm)와 쪽 경계선 - 본문 높이(ch)마다 점선. 블록이 쪽에 걸리는 것은 재지 않는 근사다(정확한 쪽 모양은 인쇄 미리 보기) */
  function layout() {
    const box = P.pageBox(S.deck), paper = $("#paper");
    paper.style.width = box.w + "mm"; paper.style.padding = `${box.t}mm ${box.r}mm ${box.b}mm ${box.l}mm`; paper.style.minHeight = box.h + "mm";
    S.box = box; pageLines(); drawHeaderFooter();
    // 브라우저 인쇄(PDF 로 저장)도 같은 용지·여백으로 - 종이의 안쪽 여백은 인쇄 때 빼고 @page 여백이 대신한다
    let st = document.getElementById("pg-print"); if (!st) { st = document.createElement("style"); st.id = "pg-print"; document.head.appendChild(st); }
    st.textContent = `@page { size: ${box.w}mm ${box.h}mm; margin: ${box.t}mm ${box.r}mm ${box.b}mm ${box.l}mm; }`;
  }
  /** 머리말·꼬리말·쪽 번호를 종이의 위·아래 여백에 흐리게 보인다(첫 쪽 자리) */
  function drawHeaderFooter() {
    const page = S.deck.page || {}, box = S.box, num = page.number || {};
    for (const [part, el] of [["header", $("#pgHeader")], ["footer", $("#pgFooter")]]) {
      el.replaceChildren();
      el.style.padding = `0 ${box.r}mm 0 ${box.l}mm`;
      if (part === "header") { el.style.top = Math.max(2, box.t / 2 - 2) + "mm"; el.style.bottom = ""; } else { el.style.bottom = Math.max(2, box.b / 2 - 2) + "mm"; el.style.top = ""; }
      P.renderInto(el, S.deck, (page[part] || {}).blocks || [], ctx);
      if (num.show && String(num.pos || "footer-center").startsWith(part)) {
        const d = document.createElement("div"); d.className = "pg-p"; d.style.textAlign = String(num.pos || "footer-center").split("-")[1] || "center"; d.textContent = "1"; d.title = "쪽 번호"; el.appendChild(d);
      }
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
      if (JSON.stringify(next) !== JSON.stringify(page)) { snapshot("format"); S.deck.page = next; layout(); afterChange(true); }
      close();
    };
    q("#psSize").focus();
  }
  function pageLines() {
    const box = S.box, host = $("#ed"), wrap = $("#pagelines"); if (!box) return;
    const mm = host.getBoundingClientRect().width / box.cw || 3.78, n = Math.max(1, Math.ceil(host.scrollHeight / (box.ch * mm) - 0.001));
    wrap.replaceChildren();
    for (let k = 1; k < n; k++) { const i = document.createElement("i"); i.style.top = (box.t + box.ch * k) * mm + "px"; i.dataset.n = `${k + 1}쪽`; wrap.appendChild(i); }
    $("#pageInfo").textContent = `${n}쪽 · ${typeof S.deck.page.size === "string" ? S.deck.page.size : "사용자 크기"}`;
  }
  /** 목록 머리 기호는 다른 문단이 바뀌어도 달라진다(번호) - 저장할 때마다 전부 다시 단다 */
  function decorateAll() {
    const mk = P.markers(blocks());
    for (const el of $$("#ed > .pg-li")) el.dataset.marker = mk[el.dataset.id] || "";
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
  function insertBreak() {
    const s = ed.selection(); if (!s) return;
    const i = blocks().findIndex((b) => b.id === s.f.id); if (i < 0) return;
    snapshot("enter");
    const br = { id: newId(), type: "break", kind: "page" }, p = { id: newId(), type: "p", runs: [] };
    S.deck.blocks = [...blocks().slice(0, i + 1), br, p, ...blocks().slice(i + 1)];
    ed.refresh({ a: { id: p.id, off: 0 }, f: { id: p.id, off: 0 } }); afterChange();
  }

  // ---------------------------------------------------------------- 서식 막대
  function updTools() {
    if (!ed) return;
    const st = ed.state(), b = st.sel ? blockAt(st.sel.f.id) : null;
    for (const el of $$("#tools [data-mark]")) el.classList.toggle("on", !!st.marks[el.dataset.mark]);
    const align = b && (b.align || P.styleOf(S.deck, b.style).align || "left");
    for (const el of $$("#tools [data-align]")) el.classList.toggle("on", !!b && el.dataset.align === align);
    for (const el of $$("#tools [data-list]")) el.classList.toggle("on", !!(b && b.list && b.list.kind === el.dataset.list));
    $("#selStyle").value = (b && T.isText(b) && (b.style || "body")) || "body";
    $("#selSize").value = st.marks.size ? String(st.marks.size) : "";
    $("[data-act=undo]").disabled = !S.undo.length; $("[data-act=redo]").disabled = !S.redo.length;
  }
  function bindTools() {
    const sel = $("#selStyle");
    sel.replaceChildren(...Object.entries(S.deck.styles).map(([k, v]) => { const o = document.createElement("option"); o.value = k; o.textContent = v.name || k; return o; }));
    sel.onchange = () => { ed.blockAttrs({ style: sel.value === "body" ? null : sel.value }); ed.focus(); };
    $("#selSize").onchange = (e) => { ed.setMark("size", e.target.value ? +e.target.value : null); ed.focus(); };
    $("#tools").addEventListener("mousedown", (e) => { if (e.target.closest("button")) e.preventDefault(); });  // 누를 때 본문 선택을 잃지 않게
    $("#tools").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b || b.disabled) return;
      if (b.dataset.mark) ed.toggle(b.dataset.mark);
      else if (b.dataset.align) ed.blockAttrs({ align: b.dataset.align === "left" ? null : b.dataset.align });
      else if (b.dataset.list) setList(b.dataset.list);
      else ({ undo, redo, indent: () => shiftLevel(1), outdent: () => shiftLevel(-1), break: insertBreak, setup: pageSetup,
        color: () => ed.toggle("c", $("#inColor").value), hl: () => ed.toggle("hl", $("#inHl").value),
        clear: () => { const s = ed.selection(); if (s) { snapshot("format"); let bs = blocks(); for (const x of T.spans(bs, s.a, s.f)) bs = bs.map((y, k) => (k === x.i ? { ...y, runs: T.clearMarks(y.runs, x.from, x.to, ["link"]) } : y)); S.deck.blocks = bs; ed.refresh(s); afterChange(); } },
      })[b.dataset.act]?.();
      updTools();
    });
  }
  /** 본문 키 - 편집 엔진보다 먼저 본다(목록 단계 · 빈 목록 문단에서 Enter/Backspace 는 목록 풀기 · Ctrl+Enter 쪽 나누기 · Ctrl+S) */
  function onKey(e) {
    if (e.isComposing) return;
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
  async function deckListMenu(btn) {
    const r = await api("GET", "/api/decks"), list = r.ok && Array.isArray(r.data) ? r.data : [];
    openMenu(btn, [{ h: `문서 ${list.length}개` }, ...list.map((d) => ({ label: `${NexaKinds.of(d).icon} ${d.title || d.id}`, on: d.id === S.id, act: async () => { if (d.id === S.id) return; if (S.dirty) await save(); location.href = NexaKinds.url(d); } })),
      "-", { label: "새 문서…", act: async () => { const n = await NexaNewDoc.open({ api, kind: "page" }); if (!n) return; if (S.dirty) await save(); location.href = NexaKinds.url(n); } }]);
  }
  /** 내보내기 - 저장한 뒤 서버가 out/<id>.docx(·pdf)를 만들고 내려받는다. PDF 는 Word 가 있을 때만(없으면 [인쇄] 안내) */
  async function doExport(pdf) {
    if (S.dirty) await save();
    if (S.dirty || S.conflict) { toast("저장되지 않은 변경이 있어 내보내지 못했습니다", 5000); return; }
    toast(pdf ? "PDF 를 만드는 중…(Word 변환)" : "Word 문서를 만드는 중…", 60000);
    const r = await api("POST", `/api/export/${encodeURIComponent(S.id)}${pdf ? "?pdf=1" : ""}`);
    if (!r.ok || !r.data || !r.data.ok) { toast((r.data && r.data.error) || `내보내기 실패(${r.status})`, 8000); return; }
    const a = document.createElement("a"); a.href = BASE + r.data.url; a.download = r.data.name || ""; document.body.appendChild(a); a.click(); a.remove();
    toast(`내보냈습니다: ${r.data.name || r.data.url}${r.data.pages ? ` (${r.data.pages}쪽)` : ""}`, 5000);
  }
  async function init() {
    P.injectCss();
    if (!(await loadDeck())) return;
    document.title = `${S.deck.title || S.id} - 페이지`;
    $("#docTitle").value = S.deck.title || "";
    $("#docTitle").onchange = (e) => { const t = e.target.value.trim(); if (!t || t === S.deck.title) { e.target.value = S.deck.title || ""; return; } snapshot("format"); S.deck.title = t; document.title = `${t} - 페이지`; afterChange(true); };
    layout();
    ed = T.mount($("#ed"), {
      get: blocks, set: (b, why) => { snapshot(why); S.deck.blocks = b; afterChange(); }, newId,
      nextStyle: (b) => { const n = P.styleOf(S.deck, b.style).next; return n === undefined ? undefined : n === "body" ? null : n; },
      decorate: (el, b) => P.decorate(el, b, S.deck, ctx, P.markers(blocks())[b.id]),
      renderBlock: (b) => P.blockEl(S.deck, b, ctx),
      color: ctx.color, font: ctx.font, onSelect: updTools, undo, redo,
    });
    $("#ed").addEventListener("keydown", onKey, true);
    bindTools(); decorateAll(); updTools();
    $("#btnDecks").onclick = (e) => deckListMenu(e.currentTarget);
    $("#btnPrint").onclick = () => window.print();
    $("#btnExport").onclick = (e) => openMenu(e.currentTarget, [{ label: "Word 문서 (.docx)", act: () => doExport(false) }, { label: "PDF (Word 로 변환)", act: () => doExport(true) }], { right: true });
    $("#bnMine").onclick = () => save(true);
    $("#bnTheirs").onclick = async () => { if (await loadDeck()) { banner(false); layout(); ed.refresh(); decorateAll(); setStatus("saved", "저장됨"); } };
    document.addEventListener("mousedown", (e) => { if (!e.target.closest(".menu")) closeMenu(); });
    window.addEventListener("resize", pageLines);
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });
    setStatus("saved", "저장됨");
    const first = blocks().find(T.isText); if (first) { ed.focus(); ed.select({ id: first.id, off: T.length(first.runs) }); }
    window.NexaPageEditor = { S, ed, save, undo, redo };  // 시험·디버깅용
  }
  init();
})();
