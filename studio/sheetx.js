/* nexa-slide 시트 - 엑셀 기본 기능 모음(sheet.js 의 NexaSheet.x 를 쓴다). 조사: docs/research/sheet-survey.md, 계획: docs/sheets.md 6절.
   - 상태 표시줄: 고른 범위의 평균·개수·합계(누르면 최소·최대·숫자 개수까지)
   - 찾기·바꾸기(Ctrl+F · Ctrl+H): 이 탭/모든 탭, 대소문자, 셀 전체 일치, 수식 안
   - 채우기 단축키: Ctrl+D 아래로 · Ctrl+R 오른쪽으로 · 편집 중 Ctrl+Enter 고른 범위 모두에 같은 값(수식은 상대 참조 이동)
   - 값만 붙여넣기(Ctrl+Shift+V) · 자동 합계(Alt+=) · 정렬(도구 막대 ⇅ - 지금 열 기준, 첫 줄 머리글 자동 판정)
   - 데이터 ▾: 필터(머리글 ▼ - 값 고르기·정렬, 이 화면에서만 = 엑셀 "필터 보기") · 행·열 숨기기/숨기기 취소(저장 - 탭 hiddenRows·hiddenCols)
   모든 고치기는 x.mutate 로 - 실행 취소·저장·다시 계산이 같이 된다. */
(function () {
  "use strict";
  const N = () => window.NexaSheet, X = () => window.NexaSheet && window.NexaSheet.x;
  const $ = (s) => document.querySelector(s);
  const isNum = (v) => typeof v === "number" && isFinite(v);
  const valOf = (raw) => (raw == null ? null : typeof raw === "object" ? (raw.v === undefined ? null : raw.v) : raw);
  const fmtN = (v) => (Number.isInteger(v) ? v.toLocaleString("ko-KR") : Number(v.toPrecision(10)).toLocaleString("ko-KR", { maximumFractionDigits: 6 }));

  // ---------------------------------------------------------------- 상태 표시줄
  let more = false;
  function onSel() {
    const x = X(), bar = $("#sumBar"); if (!x || !bar) return;
    const S = N().S, sh = x.sheet(), g = x.clampRange(S.sel);
    const cells = (g.r2 - g.r1 + 1) * (g.c2 - g.c1 + 1);
    if (cells < 2 || cells > 200000) { bar.hidden = true; return; }
    let cnt = 0, n = 0, sum = 0, mn = Infinity, mx = -Infinity;
    x.eachCell(g, (r, c, k) => {
      const v = valOf(sh.cells[k]); if (v == null || v === "") return;
      cnt++;
      if (isNum(v)) { n++; sum += v; if (v < mn) mn = v; if (v > mx) mx = v; }
    });
    if (!cnt) { bar.hidden = true; return; }
    const parts = [];
    if (n) parts.push(`평균 ${fmtN(sum / n)}`);
    parts.push(`개수 ${cnt.toLocaleString("ko-KR")}`);
    if (n) parts.push(`합계 ${fmtN(Number(sum.toPrecision(15)))}`);
    if (more && n) parts.push(`숫자 ${n}`, `최소 ${fmtN(mn)}`, `최대 ${fmtN(mx)}`);
    bar.textContent = parts.join(" · "); bar.hidden = false;
  }

  // ---------------------------------------------------------------- 찾기·바꾸기
  const F = { at: null };
  function findBox(replace) {
    let b = $("#findBox");
    if (!b) {
      b = document.createElement("div"); b.id = "findBox";
      b.innerHTML = `<div class="row"><input id="fbFind" placeholder="찾을 내용" spellcheck="false"><button class="chip sm" id="fbNext" title="다음 찾기(Enter) · 이전(Shift+Enter)">다음</button><button class="ib" id="fbClose" title="닫기(Esc)">✕</button></div>
        <div class="row rp"><input id="fbRep" placeholder="바꿀 내용" spellcheck="false"><button class="chip sm" id="fbOne">바꾸기</button><button class="chip sm" id="fbAll">모두 바꾸기</button></div>
        <div class="row opt"><label><input type="checkbox" id="fbAllTabs"> 모든 탭</label><label><input type="checkbox" id="fbCase"> 대소문자</label><label><input type="checkbox" id="fbWhole"> 셀 전체 일치</label><label><input type="checkbox" id="fbF"> 수식 안</label><span id="fbMsg"></span></div>`;
      document.body.appendChild(b);
      $("#fbClose").onclick = closeFind;
      $("#fbNext").onclick = () => findNext(1);
      $("#fbOne").onclick = replaceOne;
      $("#fbAll").onclick = replaceAll;
      b.addEventListener("keydown", (e) => {
        if (e.key === "Escape") { e.preventDefault(); closeFind(); }
        else if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); if (e.target.id === "fbRep") replaceOne(); else findNext(e.shiftKey ? -1 : 1); }
      });
      ["#fbFind", "#fbCase", "#fbWhole", "#fbF", "#fbAllTabs"].forEach((s) => $(s).addEventListener("input", () => { F.at = null; $("#fbMsg").textContent = ""; }));
    }
    b.classList.toggle("rep", !!replace); b.hidden = false;
    const x = X(), S = N().S, g = x.clampRange(S.sel);
    if (!$("#fbFind").value && g.r1 === g.r2 && g.c1 === g.c2) { const v = valOf(x.sheet().cells[x.key(S.cur.r, S.cur.c)]); if (v != null && v !== "") $("#fbFind").value = String(v); }
    $("#fbFind").focus(); $("#fbFind").select();
  }
  function closeFind() { const b = $("#findBox"); if (b) b.hidden = true; X().focusGrid(); }
  function cellText(raw, inF) {
    if (inF && raw && typeof raw === "object" && raw.f) return raw.f;
    return N().display(N().effCell(raw));
  }
  function matcher() {
    const q = $("#fbFind").value; if (!q) return null;
    const cs = $("#fbCase").checked, whole = $("#fbWhole").checked;
    const norm = (s) => (cs ? s : s.toLowerCase()), nq = norm(q);
    return (t) => (whole ? norm(t) === nq : norm(t).includes(nq));
  }
  /** 찾을 칸 목록(탭 순서, 탭 안은 행 → 열) - [{ti, r, c, k}] */
  function hits() {
    const m = matcher(); if (!m) return [];
    const S = N().S, x = X(), inF = $("#fbF").checked, out = [];
    const tabs = $("#fbAllTabs").checked ? S.deck.sheets.map((_, i) => i) : [S.ti];
    for (const ti of tabs) {
      const sh = S.deck.sheets[ti], ks = [];
      for (const k of Object.keys(sh.cells)) { const p = x.parseRef(k); if (p && m(cellText(sh.cells[k], inF))) ks.push({ ti, r: p.r, c: p.c, k }); }
      ks.sort((a, b) => a.r - b.r || a.c - b.c); out.push(...ks);
    }
    return out;
  }
  function goTo(h) {
    const S = N().S, x = X();
    if (h.ti !== S.ti) { const b = document.querySelector(`#tabs [data-ti="${h.ti}"]`); if (b) b.click(); }
    x.selectCell(h.r, h.c); F.at = h;
  }
  function findNext(dir) {
    const hs = hits(), msg = $("#fbMsg");
    if (!hs.length) { msg.textContent = "찾는 내용이 없습니다"; return; }
    const S = N().S, cur = F.at || { ti: S.ti, r: S.cur.r, c: S.cur.c - (dir > 0 ? 1 : -1) };
    const after = (h) => h.ti > cur.ti || (h.ti === cur.ti && (h.r > cur.r || (h.r === cur.r && h.c > cur.c)));
    const before = (h) => h.ti < cur.ti || (h.ti === cur.ti && (h.r < cur.r || (h.r === cur.r && h.c < cur.c)));
    const h = dir > 0 ? hs.find(after) || hs[0] : [...hs].reverse().find(before) || hs[hs.length - 1];
    goTo(h); msg.textContent = `${hs.indexOf(h) + 1} / ${hs.length}`;
    $("#fbFind").focus();
  }
  /** 칸 하나 바꾸기 - 수식 안이면 f 글을, 아니면 값을(수식 칸은 건너뜀). 바꿨으면 true */
  function replaceIn(sh, k) {
    const x = X(), q = $("#fbFind").value, rep = $("#fbRep").value, cs = $("#fbCase").checked, whole = $("#fbWhole").checked, inF = $("#fbF").checked;
    const raw = sh.cells[k], o = x.cellObj(sh, k);
    const rx = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), cs ? "g" : "gi");
    if (o.f) {
      if (!inF) return false;
      const nf = whole ? rep : o.f.replace(rx, rep); if (nf === o.f) return false;
      x.putCell(sh, k, { ...o, f: nf.startsWith("=") ? nf : "=" + nf, v: undefined }); return true;
    }
    const t = cellText(raw, false), nt = whole ? rep : t.replace(rx, rep); if (nt === t) return false;
    const keep = { ...o }; delete keep.v; x.putCell(sh, k, keep); N().setInput(sh, k, nt); return true;
  }
  function replaceOne() {
    const S = N().S, x = X(), m = matcher(); if (!m) return;
    const sh = x.sheet(), k = x.key(S.cur.r, S.cur.c);
    if (m(cellText(sh.cells[k], $("#fbF").checked))) x.mutate(() => replaceIn(sh, k));
    findNext(1);
  }
  function replaceAll() {
    const S = N().S, x = X(), hs = hits(); if (!hs.length) { $("#fbMsg").textContent = "찾는 내용이 없습니다"; return; }
    let n = 0;
    x.mutate(() => { for (const h of hs) if (replaceIn(S.deck.sheets[h.ti], h.k)) n++; });
    $("#fbMsg").textContent = `${n}칸을 바꿨습니다`; F.at = null;
  }

  // ---------------------------------------------------------------- 채우기 단축키·값만 붙여넣기·자동 합계
  function fillDir(down) {  // Ctrl+D · Ctrl+R - 범위의 첫 줄(열)을 나머지로 복사, 한 줄만 고르면 위(왼쪽) 칸에서
    const S = N().S, x = X(), sh = x.sheet(), g = x.clampRange(S.sel);
    const one = down ? g.r1 === g.r2 : g.c1 === g.c2;
    const srcAt = (r, c) => (down ? (one ? [r - 1, c] : [g.r1, c]) : (one ? [r, c - 1] : [r, g.c1]));
    if (one && (down ? g.r1 === 0 : g.c1 === 0)) return;
    x.mutate(() => {
      x.eachCell(g, (r, c, k) => {
        const [sr, scc] = srcAt(r, c); if (sr === r && scc === c) return;
        const src = sh.cells[x.key(sr, scc)];
        if (src == null) { delete sh.cells[k]; return; }
        const v = x.clone(src);
        if (typeof v === "object" && v.f) { v.f = N().shiftFormula(v.f, r - sr, c - scc); delete v.v; }
        sh.cells[k] = v;
      });
    });
  }
  function fillSelectionWithEdit() {  // 편집 중 Ctrl+Enter - 입력한 값을 고른 범위 모두에(수식은 칸마다 상대 참조 이동)
    const S = N().S, x = X(), ed = x.ED(), text = ed.value, g = x.clampRange(S.sel), at = { r: S.edit.r, c: S.edit.c };
    x.endEdit(false);
    x.mutate(() => {
      const sh = x.sheet();
      x.eachCell(g, (r, c, k) => {
        const t = text[0] === "=" ? N().shiftFormula(text, r - at.r, c - at.c) : text;
        N().setInput(sh, k, t);
      });
    });
  }
  async function pasteValues() {
    let t = "";
    try { t = await navigator.clipboard.readText(); } catch (e) { X().toast("클립보드를 읽을 수 없습니다 - 브라우저가 막았습니다(Ctrl+V 는 됩니다)", 4000); return; }
    if (!t) return;
    const S = N().S, keep = S.clip; S.clip = null;  // 이 화면 안 복사도 값(보이는 글)으로
    X().pasteText(t); if (keep && !keep.cut) S.clip = { ...keep, show: false };
  }
  function autoSum() {  // Alt+= - 위(없으면 왼쪽)로 이어진 숫자 칸의 =SUM(…)
    const S = N().S, x = X(), sh = x.sheet(), r = S.cur.r, c = S.cur.c;
    const num = (rr, cc) => isNum(valOf(sh.cells[x.key(rr, cc)]));
    let f = null;
    if (r > 0 && num(r - 1, c)) { let a = r - 1; while (a > 0 && num(a - 1, c)) a--; f = `=SUM(${x.key(a, c)}:${x.key(r - 1, c)})`; }
    else if (c > 0 && num(r, c - 1)) { let a = c - 1; while (a > 0 && num(r, a - 1)) a--; f = `=SUM(${x.key(r, a)}:${x.key(r, c - 1)})`; }
    x.startEdit("edit", f || "=SUM()");
    if (!f) { const ed = x.ED(); ed.setSelectionRange(5, 5); }
  }

  // ---------------------------------------------------------------- 정렬
  function region(sh, r, c) {  // 지금 칸을 둘러싼 이어진 데이터 블록(엑셀 "현재 영역")
    const x = X(), has = (rr, cc) => rr >= 0 && cc >= 0 && valOf(sh.cells[x.key(rr, cc)]) != null && valOf(sh.cells[x.key(rr, cc)]) !== "";
    let g = { r1: r, c1: c, r2: r, c2: c }, grow = true;
    while (grow) {
      grow = false;
      const rowHas = (rr) => { for (let cc = g.c1; cc <= g.c2; cc++) if (has(rr, cc)) return true; return false; };
      const colHas = (cc) => { for (let rr = g.r1; rr <= g.r2; rr++) if (has(rr, cc)) return true; return false; };
      if (rowHas(g.r1 - 1)) { g.r1--; grow = true; } if (rowHas(g.r2 + 1)) { g.r2++; grow = true; }
      if (colHas(g.c1 - 1)) { g.c1--; grow = true; } if (colHas(g.c2 + 1)) { g.c2++; grow = true; }
    }
    return g;
  }
  function sortRange(desc, header) {
    const S = N().S, x = X(), sh = x.sheet();
    let g = x.clampRange(S.sel);
    if (g.r1 === g.r2 && g.c1 === g.c2) g = region(sh, S.cur.r, S.cur.c);
    if (g.r2 <= g.r1) { x.toast("정렬할 줄이 없습니다"); return; }
    const col = Math.min(Math.max(S.cur.c, g.c1), g.c2);
    // 첫 줄이 머리글인가: 모두 글이고 굵게·스타일이 있거나, 정렬 열의 아래 칸에 숫자가 있는데 첫 칸은 글
    const first = [], keyFirst = valOf(sh.cells[x.key(g.r1, col)]);
    for (let c = g.c1; c <= g.c2; c++) first.push(sh.cells[x.key(g.r1, c)]);
    const styled = first.some((o) => o && typeof o === "object" && (o.b || o.s || o.fill));
    const below = valOf(sh.cells[x.key(g.r1 + 1, col)]);
    if (header === undefined) header = first.every((o) => typeof valOf(o) === "string" || valOf(o) == null) && (styled || (typeof keyFirst === "string" && isNum(below)));
    const r0 = header ? g.r1 + 1 : g.r1;
    const rows = [];
    for (let r = r0; r <= g.r2; r++) { const cells = []; for (let c = g.c1; c <= g.c2; c++) cells.push(sh.cells[x.key(r, c)]); rows.push({ r, cells, key: valOf(sh.cells[x.key(r, col)]) }); }
    const rank = (v) => (v == null || v === "" ? 3 : isNum(v) ? 0 : typeof v === "string" ? 1 : 2);  // 숫자 → 글 → 불 → 빈 칸(빈 칸은 늘 뒤)
    rows.sort((a, b) => {
      const ra = rank(a.key), rb = rank(b.key);
      if (ra === 3 || rb === 3) return ra - rb;
      if (ra !== rb) return desc ? rb - ra : ra - rb;
      const d = ra === 0 ? a.key - b.key : String(a.key).localeCompare(String(b.key), "ko", { numeric: true, sensitivity: "base" });
      return desc ? -d : d;
    });
    x.mutate(() => {
      rows.forEach((row, i) => {
        const r = r0 + i;
        row.cells.forEach((v, j) => {
          const k = x.key(r, g.c1 + j);
          if (v == null) { delete sh.cells[k]; return; }
          const o = x.clone(v);
          if (typeof o === "object" && o.f && r !== row.r) { o.f = N().shiftFormula(o.f, r - row.r, 0); delete o.v; }
          sh.cells[k] = o;
        });
      });
      S.sel = g;
    });
    x.toast(`${x.rangeName({ ...g, r1: r0 })} 를 ${x.colName(col)} 열 ${desc ? "내림차순" : "오름차순"}으로 정렬했습니다${header ? " (첫 줄은 머리글)" : ""}`, 3500);
  }

  // ---------------------------------------------------------------- 행·열 숨기기(저장)
  function hide(axis, on) {
    const S = N().S, x = X(), g = x.clampRange(S.sel), sh = x.sheet();
    x.mutate(() => {
      const keyN = axis === "r" ? "hiddenRows" : "hiddenCols", set = new Set(sh[keyN] || []);
      const a = axis === "r" ? g.r1 : g.c1, b = axis === "r" ? g.r2 : g.c2;
      for (let i = on ? a : Math.max(0, a - 1); i <= (on ? b : b + 1); i++) { const id = axis === "r" ? String(i + 1) : x.colName(i); if (on) set.add(id); else set.delete(id); }
      if (set.size) sh[keyN] = [...set].sort((p, q) => (axis === "r" ? p - q : x.colIndex(p) - x.colIndex(q))); else delete sh[keyN];
    });
  }

  // ---------------------------------------------------------------- 필터(이 화면에서만)
  const view = () => { const S = N().S, id = X().sheet().id; return (S.view[id] = S.view[id] || {}); };
  function filterToggle() {
    const S = N().S, x = X(), v = view();
    if (v.filter) { delete v.filter; v.rows = new Set(); x.renderAll(); renderFilterBtns(); x.toast("필터를 껐습니다"); return; }
    let g = x.clampRange(S.sel);
    if (g.r1 === g.r2) g = region(x.sheet(), S.cur.r, S.cur.c);
    if (g.r2 <= g.r1) { x.toast("머리글과 데이터가 있는 범위에서 켭니다"); return; }
    v.filter = { r1: g.r1, c1: g.c1, r2: g.r2, c2: g.c2, crit: {} }; v.rows = new Set();
    x.renderAll(); renderFilterBtns(); x.toast(`필터: ${x.rangeName(g)} - 머리글의 ▼ 로 값을 고릅니다(이 화면에서만, 저장되지 않음)`, 4000);
  }
  function applyFilter() {
    const x = X(), v = view(), f = v.filter, sh = x.sheet(); if (!f) return;
    const rows = new Set();
    for (let r = f.r1 + 1; r <= f.r2; r++) for (const [c, ex] of Object.entries(f.crit)) {
      if (ex.size && ex.has(N().display(N().effCell(sh.cells[x.key(r, +c)])))) { rows.add(r); break; }
    }
    v.rows = rows; x.renderAll(); renderFilterBtns();
    const shown = f.r2 - f.r1 - rows.size;
    x.toast(`${f.r2 - f.r1}줄 중 ${shown}줄 보임`);
  }
  function renderFilterBtns() {
    let lay = $("#fltLay"); const x = X(); if (!x) return;
    if (!lay) { lay = document.createElement("div"); lay.id = "fltLay"; $("#gridIn").appendChild(lay); }
    const v = view(), f = v.filter;
    if (!f) { lay.innerHTML = ""; return; }
    const out = [];
    for (let c = f.c1; c <= f.c2; c++) {
      if (x.colHidden(x.sheet(), c)) continue;
      const R = x.rectOf({ r1: f.r1, c1: c, r2: f.r1, c2: c }), on = f.crit[c] && f.crit[c].size;
      out.push(`<button class="flt${on ? " on" : ""}" data-fc="${c}" style="left:${R.x + R.w - 17}px;top:${R.y + R.h - 17}px" title="${on ? "필터 걸림 - " : ""}값 고르기·정렬">${on ? "⏷" : "▼"}</button>`);
    }
    lay.innerHTML = out.join("");
  }
  function filterMenu(btn, c) {
    const x = X(), v = view(), f = v.filter, sh = x.sheet();
    const vals = new Map();
    for (let r = f.r1 + 1; r <= f.r2; r++) { const t = N().display(N().effCell(sh.cells[x.key(r, c)])); vals.set(t, (vals.get(t) || 0) + 1); }
    const ex = f.crit[c] || new Set();
    const list = [...vals.keys()].sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b, "ko", { numeric: true })));
    document.querySelectorAll(".fltPop").forEach((m) => m.remove());
    const pop = document.createElement("div"); pop.className = "fltPop";
    pop.innerHTML = `<button data-fs="a">오름차순 정렬</button><button data-fs="d">내림차순 정렬</button><hr>
      <label class="all"><input type="checkbox" data-all ${ex.size ? "" : "checked"}> (모두 선택)</label>
      <div class="vals">${list.map((t, i) => `<label><input type="checkbox" data-i="${i}" ${ex.has(t) ? "" : "checked"}> ${x.esc(t === "" ? "(빈 칸)" : t)} <small>${vals.get(t)}</small></label>`).join("")}</div>
      <div class="acts"><button data-fa="ok" class="primary">확인</button><button data-fa="no">취소</button></div>`;
    const R = btn.getBoundingClientRect(); Object.assign(pop.style, { left: Math.min(R.left, innerWidth - 260) + "px", top: R.bottom + 2 + "px" });
    document.body.appendChild(pop);
    const boxes = () => [...pop.querySelectorAll("input[data-i]")];
    pop.querySelector("[data-all]").onchange = (e) => boxes().forEach((b) => (b.checked = e.target.checked));
    pop.addEventListener("click", (e) => {
      const fs = e.target.closest("[data-fs]"), fa = e.target.closest("[data-fa]");
      if (fs) {
        pop.remove(); const S = N().S, keep = { sel: S.sel, cur: S.cur };
        S.sel = { r1: f.r1, c1: f.c1, r2: f.r2, c2: f.c2 }; S.cur = { r: f.r1, c: c };
        sortRange(fs.dataset.fs === "d", true); S.sel = keep.sel; S.cur = keep.cur; applyFilter();
      }
      if (fa) {
        if (fa.dataset.fa === "ok") { f.crit[c] = new Set(boxes().filter((b) => !b.checked).map((b) => list[+b.dataset.i])); applyFilter(); }
        pop.remove();
      }
    });
    setTimeout(() => document.addEventListener("mousedown", function off(e) { if (!pop.contains(e.target)) { pop.remove(); document.removeEventListener("mousedown", off); } }), 0);
  }
  function dataMenu(btn) {
    const x = X(), v = view();
    x.openMenu(btn, [
      { label: v.filter ? "필터 끄기" : "필터 켜기 (머리글 ▼ - 이 화면에서만)", act: filterToggle },
      "-",
      { label: "고른 행 숨기기", act: () => hide("r", true) }, { label: "고른 열 숨기기", act: () => hide("c", true) },
      { label: "행 숨기기 취소(고른 범위와 그 옆)", act: () => hide("r", false) }, { label: "열 숨기기 취소(고른 범위와 그 옆)", act: () => hide("c", false) },
    ]);
  }

  // ---------------------------------------------------------------- 연결
  function onKey(e) {
    if (!X() || e.isComposing) return;
    const S = N().S, x = X(), ctrl = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
    const inGrid = document.activeElement === x.ED();
    if (S.edit && inGrid && ctrl && e.key === "Enter") { e.preventDefault(); e.stopPropagation(); fillSelectionWithEdit(); return; }
    if (ctrl && !e.altKey && (k === "f" || k === "h") && (inGrid || document.activeElement === document.body || e.target.closest("#findBox"))) { e.preventDefault(); e.stopPropagation(); if (S.edit) x.endEdit(true); findBox(k === "h"); return; }
    if (!inGrid || S.edit) return;
    if (ctrl && !e.altKey && !e.shiftKey && k === "d") { e.preventDefault(); e.stopPropagation(); fillDir(true); return; }
    if (ctrl && !e.altKey && !e.shiftKey && k === "r") { e.preventDefault(); e.stopPropagation(); fillDir(false); return; }
    if (ctrl && e.shiftKey && k === "v") { e.preventDefault(); e.stopPropagation(); pasteValues(); return; }
    if (e.altKey && !ctrl && (e.key === "=" || e.code === "Equal")) { e.preventDefault(); e.stopPropagation(); autoSum(); return; }
  }
  function tools() {
    const t = $("#tools"); if (!t || $("#xSort")) return;
    const sep = document.createElement("span"); sep.className = "vsep";
    const sort = document.createElement("button"); sort.className = "ib"; sort.id = "xSort"; sort.title = "정렬 - 지금 열 기준(범위를 고르지 않으면 이어진 데이터 전체, 첫 줄 머리글 자동 판정)"; sort.textContent = "⇅ 정렬 ▾";
    sort.onclick = () => X().openMenu(sort, [{ label: "오름차순 (가 → 하, 작은 수 → 큰 수)", act: () => sortRange(false) }, { label: "내림차순", act: () => sortRange(true) }]);
    const sum = document.createElement("button"); sum.className = "ib"; sum.title = "자동 합계 (Alt+=) - 위(왼쪽)로 이어진 숫자의 합계"; sum.textContent = "Σ";
    sum.onclick = () => autoSum();
    const find = document.createElement("button"); find.className = "ib"; find.title = "찾기·바꾸기 (Ctrl+F · Ctrl+H)"; find.textContent = "🔍";
    find.onclick = () => findBox(true);
    const data = document.createElement("button"); data.className = "ib"; data.id = "xData"; data.title = "필터·행/열 숨기기"; data.textContent = "데이터 ▾";
    data.onclick = () => dataMenu(data);
    t.append(sep, sum, sort, data, find);
  }
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("click", (e) => { if (e.target.closest("#sumBar")) { more = !more; onSel(); } });
  document.addEventListener("mousedown", (e) => { const b = e.target.closest("#fltLay .flt"); if (b) { e.preventDefault(); e.stopPropagation(); filterMenu(b, +b.dataset.fc); } }, true);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", tools); else tools();
  window.NexaSheetX = { onSel: () => { onSel(); renderFilterBtns(); }, onChange: () => { onSel(); renderFilterBtns(); }, sortRange, fillDir, findBox, autoSum, hide, filterToggle, applyFilter, view };
})();
