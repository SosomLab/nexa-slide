/* nexa-slide 시트 - 엑셀 기본 기능 모음(sheet.js 의 NexaSheet.x 를 쓴다). 조사: docs/research/sheet-survey.md, 계획: docs/sheets.md 6절.
   - 상태 표시줄: 고른 범위의 평균·개수·합계(누르면 최소·최대·숫자 개수까지)
   - 찾기·바꾸기(Ctrl+F · Ctrl+H): 이 탭/모든 탭, 대소문자, 셀 전체 일치, 수식 안
   - 채우기 단축키: Ctrl+D 아래로 · Ctrl+R 오른쪽으로 · 편집 중 Ctrl+Enter 고른 범위 모두에 같은 값(수식은 상대 참조 이동)
   - 값만 붙여넣기(Ctrl+Shift+V) · 자동 합계(Alt+=) · 정렬(도구 막대 ⇅ - 지금 열 기준, 첫 줄 머리글 자동 판정)
   - 데이터 ▾: 필터(머리글 ▼ - 값 고르기·정렬, 이 화면에서만 = 엑셀 "필터 보기") · 행·열 숨기기/숨기기 취소(저장 - 탭 hiddenRows·hiddenCols)
             드롭다운 목록(탭 validations [{range, list|source}] - 고른 칸 옆 ▼ 로 고르기, 목록에 없는 값은 칸 모서리 표시)
   - 함수 자동 완성: 수식 입력 중 =SU… → 맞는 함수 목록(Tab·클릭 = 넣기, ↑↓ 고르기, Esc 닫기), 괄호 안에서는 인수 안내
             조건부 서식(탭 conds [{range, type, value, value2, style{fill,color,b}, colors}] - gt·ge·lt·le·eq·ne·between·text·dup·top·bottom·scale, xlsx 왕복)
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
      "-",
      { label: "드롭다운 목록 만들기·고치기…", act: dvCreate }, { label: "드롭다운 지우기(고른 범위)", act: dvClear },
      "-",
      { label: "조건부 서식…", act: condDialog }, { label: "조건부 서식 지우기(고른 범위)", act: condClear },
    ]);
  }

  // ---------------------------------------------------------------- 드롭다운(목록 유효성)
  function dvAt(sh, r, c) {  // 이 칸에 걸린 목록 유효성(뒤에 정한 것이 이긴다)
    const x = X(); let hit = null;
    for (const dv of sh.validations || []) for (const part of String(dv.range || "").split(/\s+/)) { const g = x.parseRange(part); if (g && r >= g.r1 && r <= g.r2 && c >= g.c1 && c <= g.c2) hit = dv; }
    return hit;
  }
  function dvItems(dv) {  // 목록 - 직접 적은 것 또는 범위('탭'!A1:A5 · $D$1:$D$3)의 보이는 값
    if (dv.list) return dv.list.map(String);
    const x = X(), S = N().S, src = String(dv.source || "").replace(/^=/, "");
    const m = /^(?:'?(.+?)'?!)?(.+)$/.exec(src); if (!m) return [];
    const sh = m[1] ? S.deck.sheets.find((t) => t.name === m[1]) : x.sheet(), g = sh && x.parseRange(m[2].replace(/\$/g, ""));
    if (!g) return [];
    const out = []; x.eachCell(g, (r, c, k) => { const t = N().display(N().effCell(sh.cells[k])); if (t !== "" && !out.includes(t)) out.push(t); });
    return out;
  }
  function renderDv() {
    const x = X(); if (!x) return;
    let b = $("#dvBtn"); if (!b) { b = document.createElement("button"); b.id = "dvBtn"; b.textContent = "▼"; b.title = "목록에서 고르기 (Alt+↓)"; $("#gridIn").appendChild(b); }
    const S = N().S, sh = x.sheet(), dv = dvAt(sh, S.cur.r, S.cur.c);
    if (!dv || S.edit) { b.hidden = true; return; }
    const R = x.rectOf({ r1: S.cur.r, c1: S.cur.c, r2: S.cur.r, c2: S.cur.c });
    Object.assign(b.style, { left: R.x + R.w + 1 + "px", top: R.y + R.h - 18 + "px" }); b.hidden = false;
  }
  function dvMarks() {  // 목록에 없는 값 - 칸 오른쪽 위 붉은 삼각형
    const x = X(); if (!x) return;
    let lay = $("#dvLay"); if (!lay) { lay = document.createElement("div"); lay.id = "dvLay"; $("#gridIn").appendChild(lay); }
    const sh = x.sheet(), out = [];
    for (const dv of sh.validations || []) {
      const items = new Set(dvItems(dv));
      for (const part of String(dv.range || "").split(/\s+/)) {
        const g = x.parseRange(part); if (!g) continue;
        x.eachCell(x.clampRange(g), (r, c, k) => {
          const t = N().display(N().effCell(sh.cells[k])); if (t === "" || items.has(t)) return;
          const R = x.rectOf({ r1: r, c1: c, r2: r, c2: c }); out.push(`<i style="left:${R.x + R.w - 7}px;top:${R.y + 1}px" title="목록에 없는 값"></i>`);
        });
      }
    }
    lay.innerHTML = out.join("");
  }
  function dvPick() {
    const x = X(), S = N().S, sh = x.sheet(), dv = dvAt(sh, S.cur.r, S.cur.c); if (!dv) return;
    const items = dvItems(dv), at = { r: S.cur.r, c: S.cur.c };
    x.openMenu($("#dvBtn"), items.length ? items.map((t) => ({ label: t, act: () => { x.mutate(() => N().setInput(x.sheet(), x.key(at.r, at.c), t)); x.focusGrid(); } })) : [{ h: "목록이 비었습니다" }]);
  }
  function dvCreate() {
    const x = X(), S = N().S, g = x.clampRange(S.sel), sh = x.sheet();
    const cur = dvAt(sh, S.cur.r, S.cur.c);
    const t = prompt(`드롭다운 목록 - ${x.rangeName(g)}\n쉼표로 항목을 적거나(대기,진행,완료) = 로 범위를 적습니다(=$D$1:$D$5 · ='코드'!A2:A20)`, cur ? (cur.list ? cur.list.join(",") : "=" + String(cur.source || "").replace(/^=/, "")) : "");
    if (t == null || !t.trim()) return;
    const dv = { range: x.rangeName(g) };
    if (t.trim().startsWith("=")) dv.source = t.trim().slice(1); else dv.list = t.split(",").map((y) => y.trim()).filter(Boolean);
    x.mutate(() => { sh.validations = (sh.validations || []).filter((d) => d.range !== dv.range).concat([dv]); });
    x.toast(`${dv.range} 에 드롭다운을 걸었습니다 - 칸을 고르면 ▼`);
  }
  function dvClear() {
    const x = X(), S = N().S, g = x.clampRange(S.sel), sh = x.sheet();
    const over = (d) => String(d.range || "").split(/\s+/).some((part) => { const h = x.parseRange(part); return h && !(h.r2 < g.r1 || h.r1 > g.r2 || h.c2 < g.c1 || h.c1 > g.c2); });
    const n = (sh.validations || []).filter(over).length; if (!n) { x.toast("고른 범위에 드롭다운이 없습니다"); return; }
    x.mutate(() => { sh.validations = sh.validations.filter((d) => !over(d)); if (!sh.validations.length) delete sh.validations; });
    x.toast(`드롭다운 ${n}개를 지웠습니다`);
  }

  // ---------------------------------------------------------------- 조건부 서식
  const CF_TYPES = [["gt", "보다 큼"], ["ge", "이상"], ["lt", "보다 작음"], ["le", "이하"], ["eq", "같음"], ["ne", "같지 않음"], ["between", "사이(값1~값2)"],
    ["text", "글 포함"], ["dup", "중복 값"], ["top", "상위 N"], ["bottom", "하위 N"], ["scale", "색조(작은 값 → 큰 값)"]];
  const CF_STYLES = [["빨강 채움", { fill: "#FFC7CE", color: "#9C0006" }], ["초록 채움", { fill: "#C6EFCE", color: "#006100" }], ["노랑 채움", { fill: "#FFEB9C", color: "#9C5700" }],
    ["굵은 빨강 글자", { color: "#C0392B", b: true }], ["파랑 채움", { fill: "#DDEBF7", color: "#1F4E79" }]];
  const hexMix = (a, b, t) => "#" + [1, 3, 5].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * (1 - t) + parseInt(b.slice(i, i + 2), 16) * t).toString(16).padStart(2, "0")).join("").toUpperCase();
  /** 탭의 조건부 서식 → Map(행*4096+열 → 덧씌울 서식). 뒤 규칙이 앞 규칙을 덮는다 */
  function condMap(sh) {
    if (!sh.conds || !sh.conds.length) return null;
    const x = X(), out = new Map();
    for (const cd of sh.conds) {
      const cells = [];
      for (const part of String(cd.range || "").split(/\s+/)) { const g = x.parseRange(part); if (g) x.eachCell(x.clampRange(g), (r, c, k) => cells.push([r, c, valOf(sh.cells[k]), N().display(N().effCell(sh.cells[k]))])); }
      const nums = cells.map((q) => q[2]).filter(isNum), v1 = cd.value, v2 = cd.value2;
      const n1 = typeof v1 === "number" ? v1 : parseFloat(v1), n2 = typeof v2 === "number" ? v2 : parseFloat(v2);
      let test;
      if (cd.type === "scale") {
        if (!nums.length) continue;
        const lo = Math.min(...nums), hi = Math.max(...nums), [c1, c2] = cd.colors || ["#FFFFFF", "#63BE7B"];
        for (const [r, c, v] of cells) if (isNum(v)) out.set(r * 4096 + c, { ...(out.get(r * 4096 + c) || {}), fill: hexMix(c1, c2, hi === lo ? 1 : (v - lo) / (hi - lo)) });
        continue;
      }
      if (cd.type === "dup") { const cnt = new Map(); for (const q of cells) if (q[3] !== "") cnt.set(q[3], (cnt.get(q[3]) || 0) + 1); test = (v, t) => t !== "" && cnt.get(t) > 1; }
      else if (cd.type === "top" || cd.type === "bottom") { const srt = [...nums].sort((a, b) => (cd.type === "top" ? b - a : a - b)), cut = srt[Math.max(0, Math.min(srt.length, n1 || 10) - 1)]; test = (v) => isNum(v) && (cd.type === "top" ? v >= cut : v <= cut); }
      else if (cd.type === "text") test = (v, t) => t !== "" && t.toLowerCase().includes(String(v1 || "").toLowerCase());
      else if (cd.type === "between") test = (v) => isNum(v) && v >= Math.min(n1, n2) && v <= Math.max(n1, n2);
      else {
        const num = !isNaN(n1);
        test = (v, t) => {
          if (num && !isNum(v)) return false;
          const a = num ? v : t, b = num ? n1 : String(v1);
          return { gt: a > b, ge: a >= b, lt: a < b, le: a <= b, eq: a === b, ne: a !== b }[cd.type];
        };
      }
      for (const [r, c, v, t] of cells) if (test(v, t)) out.set(r * 4096 + c, { ...(out.get(r * 4096 + c) || {}), ...(cd.style || {}) });
    }
    return out;
  }
  function condDialog() {
    const x = X(), S = N().S, g = x.clampRange(S.sel), sh = x.sheet();
    document.querySelectorAll(".cfDlg").forEach((d) => d.remove());
    const dlg = document.createElement("div"); dlg.className = "cfDlg fltPop";
    dlg.innerHTML = `<b>조건부 서식 - ${x.rangeName(g)}</b>
      <label>조건 <select data-k="type">${CF_TYPES.map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select></label>
      <label class="v1">값 <input data-k="v1" placeholder="예: 1000 · 완료"></label><label class="v2">값2 <input data-k="v2"></label>
      <label class="st">서식 <select data-k="st">${CF_STYLES.map(([l], i) => `<option value="${i}">${l}</option>`).join("")}</select></label>
      <div class="acts"><button data-fa="ok" class="primary">적용</button><button data-fa="no">취소</button></div>`;
    const R = $("#xData").getBoundingClientRect(); Object.assign(dlg.style, { left: R.left + "px", top: R.bottom + 4 + "px", width: "280px" });
    document.body.appendChild(dlg);
    const q = (k) => dlg.querySelector(`[data-k="${k}"]`), sync = () => { const t = q("type").value; dlg.querySelector(".v1").hidden = ["dup", "scale"].includes(t); dlg.querySelector(".v2").hidden = t !== "between"; dlg.querySelector(".st").hidden = t === "scale"; };
    q("type").onchange = sync; sync();
    dlg.addEventListener("click", (e) => {
      const fa = e.target.closest("[data-fa]"); if (!fa) return;
      if (fa.dataset.fa === "ok") {
        const t = q("type").value, cd = { range: x.rangeName(g), type: t };
        const num = (v) => (v !== "" && !isNaN(+v) ? +v : v);
        if (!["dup", "scale"].includes(t)) cd.value = num(q("v1").value.trim());
        if (t === "between") cd.value2 = num(q("v2").value.trim());
        if (t === "scale") cd.colors = ["#FFFFFF", "#63BE7B"]; else cd.style = { ...CF_STYLES[+q("st").value][1] };
        x.mutate(() => { sh.conds = (sh.conds || []).concat([cd]); });
        x.toast(`${cd.range} 에 조건부 서식을 걸었습니다`);
      }
      dlg.remove();
    });
  }
  function condClear() {
    const x = X(), S = N().S, g = x.clampRange(S.sel), sh = x.sheet();
    const over = (d) => String(d.range || "").split(/\s+/).some((part) => { const h = x.parseRange(part); return h && !(h.r2 < g.r1 || h.r1 > g.r2 || h.c2 < g.c1 || h.c1 > g.c2); });
    const n = (sh.conds || []).filter(over).length; if (!n) { x.toast("고른 범위에 조건부 서식이 없습니다"); return; }
    x.mutate(() => { sh.conds = sh.conds.filter((d) => !over(d)); if (!sh.conds.length) delete sh.conds; });
    x.toast(`조건부 서식 ${n}개를 지웠습니다`);
  }

  // ---------------------------------------------------------------- 함수 자동 완성·인수 안내
  const FN_HELP = {
    SUM: ["수1, [수2], …", "합계"], AVERAGE: ["수1, [수2], …", "평균"], MIN: ["수1, …", "최솟값"], MAX: ["수1, …", "최댓값"], COUNT: ["값1, …", "숫자 칸 수"],
    COUNTA: ["값1, …", "비어 있지 않은 칸 수"], COUNTBLANK: ["범위", "빈 칸 수"], MEDIAN: ["수1, …", "가운데 값"], PRODUCT: ["수1, …", "곱"],
    SUMIF: ["범위, 조건, [합 범위]", "조건에 맞는 합계"], SUMIFS: ["합 범위, 조건 범위1, 조건1, …", "여러 조건 합계"], COUNTIF: ["범위, 조건", "조건에 맞는 칸 수"],
    COUNTIFS: ["조건 범위1, 조건1, …", "여러 조건 칸 수"], AVERAGEIF: ["범위, 조건, [평균 범위]", "조건에 맞는 평균"], AVERAGEIFS: ["평균 범위, 조건 범위1, 조건1, …", "여러 조건 평균"],
    SUMPRODUCT: ["배열1, [배열2], …", "곱의 합"], ROUND: ["수, 자릿수", "반올림"], ROUNDUP: ["수, 자릿수", "올림"], ROUNDDOWN: ["수, 자릿수", "내림"], INT: ["수", "정수(내림)"],
    MOD: ["수, 나눌 수", "나머지"], ABS: ["수", "절댓값"], IF: ["조건, 참일 때, [거짓일 때]", "조건에 따라 값"], IFS: ["조건1, 값1, …", "처음 맞는 조건의 값"],
    IFERROR: ["값, 오류일 때", "오류면 대신할 값"], IFNA: ["값, #N/A 일 때", "#N/A 면 대신할 값"], SWITCH: ["식, 값1, 결과1, …, [기본]", "값에 맞는 결과"],
    CHOOSE: ["번호, 값1, 값2, …", "번호째 값"], AND: ["조건1, …", "모두 참"], OR: ["조건1, …", "하나라도 참"], NOT: ["조건", "반대"],
    VLOOKUP: ["찾을 값, 표, 열 번호, [근사=TRUE]", "세로로 찾기"], HLOOKUP: ["찾을 값, 표, 행 번호, [근사]", "가로로 찾기"], MATCH: ["찾을 값, 범위, [방식 1·0·-1]", "위치"],
    INDEX: ["범위, 행, [열]", "그 자리의 값"], XLOOKUP: ["찾을 값, 찾을 범위, 돌려줄 범위, [없을 때]", "찾기(새)"], CONCAT: ["글1, …", "이어 붙이기"],
    CONCATENATE: ["글1, …", "이어 붙이기"], TEXTJOIN: ["구분자, 빈칸 무시, 글1, …", "구분자로 잇기"], LEFT: ["글, [글자 수]", "왼쪽"], RIGHT: ["글, [글자 수]", "오른쪽"],
    MID: ["글, 시작, 글자 수", "가운데"], LEN: ["글", "글자 수"], TRIM: ["글", "공백 정리"], UPPER: ["글", "대문자"], LOWER: ["글", "소문자"],
    SUBSTITUTE: ["글, 옛 글, 새 글, [몇 번째]", "바꾸기"], FIND: ["찾을 글, 글, [시작]", "위치(대소문자 구분)"], SEARCH: ["찾을 글, 글, [시작]", "위치(* ? 가능)"],
    VALUE: ["글", "숫자로"], TEXT: ["값, 형식", "형식 글로(#,##0 · yyyy-mm-dd)"], TODAY: ["", "오늘"], NOW: ["", "지금"], DATE: ["년, 월, 일", "날짜"],
    YEAR: ["날짜", "년"], MONTH: ["날짜", "월"], DAY: ["날짜", "일"], WEEKDAY: ["날짜, [방식]", "요일 번호(일=1)"], EDATE: ["날짜, 개월", "몇 달 뒤"],
    EOMONTH: ["날짜, 개월", "그 달 마지막 날"], ROW: ["[참조]", "행 번호"], COLUMN: ["[참조]", "열 번호"], ROWS: ["범위", "행 수"], COLUMNS: ["범위", "열 수"],
    INDIRECT: ["주소 글", "글로 적은 참조"], OFFSET: ["기준, 행, 열, [높이], [너비]", "옮긴 범위"], SUBTOTAL: ["함수 번호, 범위", "부분합(9=합계)"],
    HYPERLINK: ["주소, [보일 글]", "링크(보이는 글)"], ISBLANK: ["값", "빈 칸?"], ISNUMBER: ["값", "숫자?"], ISTEXT: ["값", "글?"], ISERROR: ["값", "오류?"], ISNA: ["값", "#N/A?"],
    FILTER: ["범위, 조건 배열, [없을 때]", "조건에 맞는 행만(넘침)"], SORT: ["범위, [기준 열], [1·-1], [열 방향]", "정렬(넘침)"], SORTBY: ["범위, 기준 범위1, [1·-1], …", "다른 범위로 정렬(넘침)"],
    UNIQUE: ["범위, [열 방향], [한 번만]", "중복 빼기(넘침)"], SEQUENCE: ["행 수, [열 수], [시작], [간격]", "일련번호(넘침)"], TRANSPOSE: ["범위", "행·열 바꾸기(넘침)"],
  };
  const AC = { list: [], i: 0, from: 0 };
  function fnNames() { return (window.NexaCalc && NexaCalc.FUNCS) || Object.keys(FN_HELP); }
  function acBox() { let b = $("#acBox"); if (!b) { b = document.createElement("div"); b.id = "acBox"; document.body.appendChild(b); } return b; }
  function acHide() { const b = $("#acBox"); if (b) b.hidden = true; AC.list = []; }
  function acUpdate() {
    const S = N().S, x = X(), ed = x.ED(); if (!S.edit) { acHide(); return; }
    const v = ed.value, pos = ed.selectionStart, before = v.slice(0, pos);
    if (v[0] !== "=") { acHide(); return; }
    const box = acBox(), R = ed.getBoundingClientRect();
    const m = /([A-Za-z][A-Za-z0-9.]*)$/.exec(before);
    const inStr = (before.match(/"/g) || []).length % 2 === 1;
    if (m && !inStr && !/[A-Za-z0-9$:]/.test(before.slice(0, -m[1].length).slice(-1) || "")) {
      const pre = m[1].toUpperCase();
      AC.list = fnNames().filter((f) => f.startsWith(pre)).sort().slice(0, 8); AC.from = pos - m[1].length;
      if (AC.list.length && !(AC.list.length === 1 && AC.list[0] === pre && v[pos] === "(")) {
        AC.i = Math.min(AC.i, AC.list.length - 1);
        box.innerHTML = AC.list.map((f, i) => `<div class="it${i === AC.i ? " on" : ""}" data-ac="${f}"><b>${f}</b>(${x.esc((FN_HELP[f] || [""])[0])}) <span>${x.esc((FN_HELP[f] || ["", ""])[1])}</span></div>`).join("") + `<div class="hint">Tab = 넣기 · ↑↓ 고르기 · Esc 닫기</div>`;
        Object.assign(box.style, { left: R.left + "px", top: R.bottom + 2 + "px" }); box.hidden = false; return;
      }
    }
    // 괄호 안 - 가장 안쪽 열린 함수의 인수 안내
    let depth = 0, name = null;
    for (let i = before.length - 1; i >= 0; i--) {
      const ch = before[i];
      if (ch === ")") depth++;
      else if (ch === "(") { if (depth) depth--; else { const mm = /([A-Za-z][A-Za-z0-9.]*)$/.exec(before.slice(0, i)); name = mm && mm[1].toUpperCase(); break; } }
    }
    AC.list = [];
    if (name && FN_HELP[name] && !inStr) {
      box.innerHTML = `<div class="sig"><b>${name}</b>(${x.esc(FN_HELP[name][0])}) - ${x.esc(FN_HELP[name][1])}</div>`;
      Object.assign(box.style, { left: R.left + "px", top: R.bottom + 2 + "px" }); box.hidden = false; return;
    }
    acHide();
  }
  function acPick(f) {
    const x = X(), ed = x.ED(), v = ed.value, pos = ed.selectionStart;
    const nv = v.slice(0, AC.from) + f + "(" + v.slice(pos).replace(/^\(/, "");
    ed.value = nv; const n = AC.from + f.length + 1; ed.setSelectionRange(n, n);
    ed.dispatchEvent(new Event("input", { bubbles: true })); acUpdate();
  }
  function acKey(e) {
    const b = $("#acBox"); if (!b || b.hidden || !AC.list.length) return false;
    if (e.key === "Tab") { e.preventDefault(); e.stopPropagation(); acPick(AC.list[AC.i]); return true; }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); e.stopPropagation(); AC.i = (AC.i + (e.key === "ArrowDown" ? 1 : AC.list.length - 1)) % AC.list.length; acUpdate(); return true; }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); acHide(); return true; }
    return false;
  }

  // ---------------------------------------------------------------- 연결
  function onKey(e) {
    if (!X() || e.isComposing) return;
    const S = N().S, x = X(), ctrl = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
    const inGrid = document.activeElement === x.ED();
    if (S.edit && inGrid && acKey(e)) return;
    if (S.edit && inGrid && ctrl && e.key === "Enter") { e.preventDefault(); e.stopPropagation(); fillSelectionWithEdit(); return; }
    if (ctrl && !e.altKey && (k === "f" || k === "h") && (inGrid || document.activeElement === document.body || e.target.closest("#findBox"))) { e.preventDefault(); e.stopPropagation(); if (S.edit) x.endEdit(true); findBox(k === "h"); return; }
    if (!inGrid || S.edit) return;
    if (ctrl && !e.altKey && !e.shiftKey && k === "d") { e.preventDefault(); e.stopPropagation(); fillDir(true); return; }
    if (ctrl && !e.altKey && !e.shiftKey && k === "r") { e.preventDefault(); e.stopPropagation(); fillDir(false); return; }
    if (ctrl && e.shiftKey && k === "v") { e.preventDefault(); e.stopPropagation(); pasteValues(); return; }
    if (e.altKey && !ctrl && (e.key === "=" || e.code === "Equal")) { e.preventDefault(); e.stopPropagation(); autoSum(); return; }
    if (e.altKey && !ctrl && e.key === "ArrowDown" && !$("#dvBtn").hidden) { e.preventDefault(); e.stopPropagation(); dvPick(); return; }
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
  document.addEventListener("mousedown", (e) => {
    const b = e.target.closest("#fltLay .flt"); if (b) { e.preventDefault(); e.stopPropagation(); filterMenu(b, +b.dataset.fc); return; }
    if (e.target.closest("#dvBtn")) { e.preventDefault(); e.stopPropagation(); dvPick(); }
  }, true);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", tools); else tools();
  // 자동 완성 - 편집칸 입력·커서 이동마다(편집이 끝나면 닫힘)
  document.addEventListener("input", (e) => { if (X() && e.target === X().ED()) { AC.i = 0; setTimeout(acUpdate, 0); } }, true);
  document.addEventListener("keyup", (e) => { if (X() && e.target === X().ED() && /^(Arrow(Left|Right)|Home|End)$/.test(e.key)) acUpdate(); }, true);
  document.addEventListener("mousedown", (e) => { const it = e.target.closest("#acBox [data-ac]"); if (it) { e.preventDefault(); acPick(it.dataset.ac); } else if (!e.target.closest("#acBox")) acHide(); }, true);
  setInterval(() => { if (X() && !N().S.edit) acHide(); }, 400);
  window.NexaSheetX = { onSel: () => { onSel(); renderFilterBtns(); renderDv(); dvMarks(); }, onChange: () => { onSel(); renderFilterBtns(); renderDv(); dvMarks(); }, dvCreate, dvClear, dvPick, condMap, condDialog, condClear, sortRange, fillDir, findBox, autoSum, hide, filterToggle, applyFilter, view };
})();
