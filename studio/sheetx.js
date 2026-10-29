/* nexa-slide 시트 - 엑셀 기본 기능 모음(sheet.js 의 NexaSheet.x 를 쓴다). 조사: docs/research/sheet-survey.md, 계획: docs/sheets.md 6절.
   - 상태 표시줄: 고른 범위의 평균·개수·합계(누르면 최소·최대·숫자 개수까지)
   - 찾기·바꾸기(Ctrl+F · Ctrl+H): 이 탭/모든 탭, 대소문자, 셀 전체 일치, 수식 안
   - 채우기 단축키: Ctrl+D 아래로 · Ctrl+R 오른쪽으로 · 편집 중 Ctrl+Enter 고른 범위 모두에 같은 값(수식은 상대 참조 이동)
   - 값만 붙여넣기(Ctrl+Shift+V) · 자동 합계(Alt+=) · 정렬(도구 막대 ⇅ - 지금 열 기준, 첫 줄 머리글 자동 판정)
   - 데이터 ▾: 필터(Ctrl+Shift+L, 탭 filter 에 저장 - 머리글 ▼: 정렬·값 검색·체크·텍스트/숫자 조건·상위 10·색 기준) · 행·열 숨기기/숨기기 취소(저장 - 탭 hiddenRows·hiddenCols)
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
  function sortRange(desc, header, byColor) {  // byColor {k: "fill"|"color", v} - 그 색인 줄을 위로(나머지 순서는 그대로, 엑셀 "색 기준 정렬")
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
    for (let r = r0; r <= g.r2; r++) { const cells = []; for (let c = g.c1; c <= g.c2; c++) cells.push(sh.cells[x.key(r, c)]); rows.push({ r, cells, key: byColor ? (String(N().effCell(sh.cells[x.key(r, col)])[byColor.k] || "").toUpperCase() === String(byColor.v).toUpperCase() ? 0 : 1) : valOf(sh.cells[x.key(r, col)]) }); }
    const rank = (v) => (v == null || v === "" ? 3 : isNum(v) ? 0 : typeof v === "string" ? 1 : 2);  // 숫자 → 글 → 불 → 빈 칸(빈 칸은 늘 뒤)
    rows.sort((a, b) => {
      if (byColor) return a.key - b.key;
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
    x.toast(`${x.rangeName({ ...g, r1: r0 })} 를 ${x.colName(col)} 열 ${byColor ? "색 기준" : desc ? "내림차순" : "오름차순"}으로 정렬했습니다${header ? " (첫 줄은 머리글)" : ""}`, 3500);
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

  // ---------------------------------------------------------------- 필터(엑셀 자동 필터 - 탭 filter 에 저장, Ctrl+Shift+L)
  // filter = { ref: "A1:D20"(첫 줄 = 머리글), cols: { 열 문자: 조건 }, rows: ["5", …](조건으로 가린 행) }
  // 가린 행은 엑셀처럼 조건을 바꾸거나 [다시 적용] 할 때만 다시 계산한다 - 값을 고쳤다고 그 행이 바로 사라지지 않는다
  // 조건: {vals: [보일 글…, ""=빈 칸]} · {cond: [{op, v}, {op, v}], or} · {top: n, bottom, pct} · {fill: "#RRGGBB"|""(채우기 없음)} · {font: "#RRGGBB"|""(자동)}
  const OPS = { eq: "같음", ne: "같지 않음", gt: "보다 큼", ge: "크거나 같음", lt: "보다 작음", le: "작거나 같음", begins: "시작 문자", ends: "끝 문자", contains: "포함", notContains: "포함하지 않음" };
  const fRange = (sh) => (sh.filter ? X().parseRange(sh.filter.ref || "") : null);
  const fText = (sh, r, c) => N().display(N().effCell(sh.cells[X().key(r, c)]));
  const fColor = (sh, r, c, k) => String(N().effCell(sh.cells[X().key(r, c)])[k] || "").toUpperCase();
  const wildRe = (p) => new RegExp("^" + String(p).replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".") + "$", "i");  // 엑셀 같음·같지 않음의 * ?
  function condOk(op, want, v, t) {  // v 값, t 보이는 글
    const w = want === "" || want == null ? NaN : Number(want), numCmp = typeof v === "number" && !isNaN(w);
    const s = t.toLowerCase(), q = String(want == null ? "" : want).toLowerCase();
    if (op === "eq") return numCmp ? v === w : wildRe(want == null ? "" : want).test(t);
    if (op === "ne") return numCmp ? v !== w : !wildRe(want == null ? "" : want).test(t);
    if (op === "begins") return s.startsWith(q);
    if (op === "ends") return s.endsWith(q);
    if (op === "contains") return s.includes(q);
    if (op === "notContains") return !s.includes(q);
    let d;
    if (numCmp) d = v - w; else if (typeof v !== "number" && isNaN(w) && t !== "") d = s.localeCompare(q, "ko"); else return false;  // 숫자끼리·글끼리만, 빈 칸은 안 맞음
    return op === "gt" ? d > 0 : op === "ge" ? d >= 0 : op === "lt" ? d < 0 : op === "le" ? d <= 0 : true;
  }
  function topCut(sh, g, c, cr) {  // 상위·하위 n(%) 의 경계값
    const nums = [];
    for (let r = g.r1 + 1; r <= g.r2; r++) { const v = valOf(sh.cells[X().key(r, c)]); if (isNum(v)) nums.push(v); }
    if (!nums.length) return null;
    nums.sort((a, b) => (cr.bottom ? a - b : b - a));
    const k = cr.pct ? Math.max(1, Math.floor((nums.length * cr.top) / 100)) : Math.max(1, cr.top);
    return nums[Math.min(k, nums.length) - 1];
  }
  function critOk(sh, r, c, cr, cut) {
    const t = fText(sh, r, c);
    if (cr.vals) return cr.vals.includes(t);
    if (cr.cond) { const rs = cr.cond.filter((q) => q && q.op).map((q) => condOk(q.op, q.v, valOf(sh.cells[X().key(r, c)]), t)); return !rs.length || (cr.or ? rs.some(Boolean) : rs.every(Boolean)); }
    if (cr.top) { const v = valOf(sh.cells[X().key(r, c)]); return isNum(v) && cut != null && (cr.bottom ? v <= cut : v >= cut); }
    if ("fill" in cr) return fColor(sh, r, c, "fill") === String(cr.fill).toUpperCase();
    if ("font" in cr) return fColor(sh, r, c, "color") === String(cr.font).toUpperCase();
    return true;
  }
  function hiddenBy(sh, skip) {  // 조건으로 가릴 행 번호(0부터) - skip 열의 조건은 빼고(▼ 목록은 다른 열 조건을 통과한 행의 값만)
    const x = X(), g = fRange(sh), out = new Set(); if (!g) return out;
    const crit = Object.entries((sh.filter && sh.filter.cols) || {}).map(([L, cr]) => [x.colIndex(L), cr]).filter(([c]) => c >= g.c1 && c <= g.c2 && c !== skip);
    const cuts = new Map(crit.filter(([, cr]) => cr.top).map(([c, cr]) => [c, topCut(sh, g, c, cr)]));
    for (let r = g.r1 + 1; r <= g.r2; r++) if (!crit.every(([c, cr]) => critOk(sh, r, c, cr, cuts.get(c)))) out.add(r);
    return out;
  }
  function growRange(sh) {  // 범위 아래에 이어 붙인 줄이 있으면 넓힌다(엑셀도 다시 적용할 때 넓힌다)
    const x = X(), g = fRange(sh); if (!g) return;
    const has = (r) => { for (let c = g.c1; c <= g.c2; c++) { const v = valOf(sh.cells[x.key(r, c)]); if (v != null && v !== "") return true; } return false; };
    let r2 = g.r2; while (has(r2 + 1)) r2++;
    if (r2 !== g.r2) sh.filter.ref = x.rangeName({ ...g, r2 });
  }
  function shownMsg(sh) { const g = fRange(sh); if (!g) return ""; const n = g.r2 - g.r1, h = (sh.filter.rows || []).length; return `${n}줄 중 ${n - h}줄 보임`; }
  /** 고치기(실행 취소·저장) - fn 으로 필터를 바꾸고 가릴 행을 다시 계산 */
  function setFilter(fn, msg) {
    const x = X(), sh = x.sheet();
    x.mutate(() => {
      fn(sh);
      const f = sh.filter; if (!f) return;
      if (f.cols && !Object.keys(f.cols).length) delete f.cols;
      growRange(sh);
      const rows = [...hiddenBy(sh)].sort((a, b) => a - b).map((r) => String(r + 1));
      if (rows.length) f.rows = rows; else delete f.rows;
    });
    renderFilterBtns();
    const m = typeof msg === "function" ? msg(x.sheet()) : msg; if (m) x.toast(m, 3500);
  }
  function filterToggle() {
    const S = N().S, x = X(), sh = x.sheet();
    if (sh.filter) { setFilter((t) => { delete t.filter; }, "필터를 껐습니다"); return; }
    let g = x.clampRange(S.sel);
    if (g.r1 === g.r2) g = region(sh, S.cur.r, S.cur.c);
    if (g.r2 <= g.r1) { x.toast("머리글과 데이터가 있는 범위에서 켭니다"); return; }
    setFilter((t) => { t.filter = { ref: x.rangeName(g) }; }, `필터: ${x.rangeName(g)} - 머리글의 ▼ 로 고릅니다 (Ctrl+Shift+L = 끄기)`);
  }
  const filterClear = () => setFilter((t) => { delete t.filter.cols; }, (t) => `필터 조건을 모두 지웠습니다 · ${shownMsg(t)}`);
  const filterReapply = () => setFilter(() => {}, shownMsg);
  function setCrit(c, cr) { setFilter((t) => { const cols = (t.filter.cols = t.filter.cols || {}); const L = X().colName(c); if (cr) cols[L] = cr; else delete cols[L]; }, shownMsg); }
  function renderFilterBtns() {
    let lay = $("#fltLay"); const x = X(); if (!x) return;
    if (!lay) { lay = document.createElement("div"); lay.id = "fltLay"; $("#gridIn").appendChild(lay); }
    const sh = x.sheet(), g = fRange(sh);
    if (!g) { lay.innerHTML = ""; return; }
    const out = [], cols = sh.filter.cols || {};
    for (let c = g.c1; c <= g.c2; c++) {
      if (x.colHidden(sh, c)) continue;
      const R = x.rectOf({ r1: g.r1, c1: c, r2: g.r1, c2: c }), on = !!cols[x.colName(c)];
      out.push(`<button class="flt${on ? " on" : ""}" data-fc="${c}" style="left:${R.x + R.w - 17}px;top:${R.y + R.h - 17}px" title="${on ? "필터 걸림 - " : ""}값 고르기·조건·정렬">${on ? "⏷" : "▼"}</button>`);
    }
    lay.innerHTML = out.join("");
  }
  function filterMenu(btn, c) {
    const x = X(), sh = x.sheet(), g = fRange(sh), L = x.colName(c), cr = (sh.filter.cols || {})[L] || null;
    const other = hiddenBy(sh, c), vals = new Map(), fills = new Set(), fonts = new Set(); let nums = 0, texts = 0;
    const cut = cr && cr.top ? topCut(sh, g, c, cr) : null, pass = new Set();
    for (let r = g.r1 + 1; r <= g.r2; r++) {
      if (other.has(r)) continue;
      const t = fText(sh, r, c), v = valOf(sh.cells[x.key(r, c)]);
      vals.set(t, (vals.get(t) || 0) + 1); fills.add(fColor(sh, r, c, "fill")); fonts.add(fColor(sh, r, c, "color"));
      if (isNum(v)) nums++; else if (t !== "") texts++;
      if (!cr || critOk(sh, r, c, cr, cut)) pass.add(t);
    }
    const isNumCol = nums > texts, list = [...vals.keys()].sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b, "ko", { numeric: true })));
    const kind = isNumCol ? "숫자" : "텍스트";
    const condItems = isNumCol ? [["eq", "같음…"], ["ne", "같지 않음…"], ["gt", "보다 큼…"], ["ge", "크거나 같음…"], ["lt", "보다 작음…"], ["le", "작거나 같음…"], ["between", "해당 범위…"], ["top", "상위 10…"], ["custom", "사용자 지정 필터…"]]
      : [["eq", "같음…"], ["ne", "같지 않음…"], ["begins", "시작 문자…"], ["ends", "끝 문자…"], ["contains", "포함…"], ["notContains", "포함하지 않음…"], ["custom", "사용자 지정 필터…"]];
    const sw = (col, k, at = "col") => `<button class="sw" data-${at}="${k}:${x.esc(col)}" title="${col ? x.esc(col) : k === "fill" ? "채우기 없음" : "자동(기본 글자색)"}"><i style="background:${col || (k === "fill" ? "#fff" : "#000")}"></i>${col ? "" : k === "fill" ? "채우기 없음" : "자동"}</button>`;
    const colorSec = (at) => (fills.size > 1 ? `<div class="sub"><small>셀 색</small>${[...fills].map((f) => sw(f, "fill", at)).join("")}</div>` : "") + (fonts.size > 1 ? `<div class="sub"><small>글꼴 색</small>${[...fonts].map((f) => sw(f, "font", at)).join("")}</div>` : "");
    const hasColor = fills.size > 1 || fonts.size > 1;
    document.querySelectorAll(".fltPop").forEach((m) => m.remove());
    const pop = document.createElement("div"); pop.className = "fltPop";
    pop.innerHTML = `<button data-fs="a">오름차순 정렬</button><button data-fs="d">내림차순 정렬</button>
      <button data-fx="csort" ${hasColor ? "" : "disabled"}>색 기준 정렬 ▸</button><div class="more" data-more="csort" hidden>${colorSec("scol")}</div><hr>
      <button data-fx="clear" ${cr ? "" : "disabled"}>"${x.esc(fText(sh, g.r1, c) || L)}"에서 필터 해제</button>
      <button data-fx="color" ${hasColor ? "" : "disabled"}>색 기준 필터 ▸</button><div class="more" data-more="color" hidden>${colorSec("col")}</div>
      <button data-fx="cond">${kind} 필터 ▸</button><div class="more" data-more="cond" hidden>${condItems.map(([k, t]) => `<button data-op="${k}">${t}</button>`).join("")}</div><hr>
      <input type="search" class="q" placeholder="검색">
      <label class="all"><input type="checkbox" data-all checked> <span>(모두 선택)</span></label>
      <label class="add" hidden title="지금 필터에 걸린 값은 그대로 두고 검색 결과에서 고른 값을 더합니다"><input type="checkbox" data-add> 현재 선택 영역을 필터에 추가</label>
      <div class="vals">${list.map((t, i) => `<label data-t="${i}"><input type="checkbox" data-i="${i}" ${pass.has(t) ? "checked" : ""}> ${x.esc(t === "" ? "(빈 칸)" : t)} <small>${vals.get(t)}</small></label>`).join("")}</div>
      <div class="acts"><button data-fa="ok" class="primary">확인</button><button data-fa="no">취소</button></div>`;
    const R = btn.getBoundingClientRect(); Object.assign(pop.style, { left: Math.min(R.left, innerWidth - 260) + "px", top: Math.min(R.bottom + 2, innerHeight - 420) + "px" });
    document.body.appendChild(pop);
    const shown = () => [...pop.querySelectorAll("label[data-t]")].filter((l) => !l.hidden).map((l) => l.querySelector("input"));
    const syncAll = () => { const b = shown(); pop.querySelector("[data-all]").checked = b.length > 0 && b.every((i) => i.checked); };
    syncAll();
    const q = pop.querySelector(".q");
    q.oninput = () => {  // 검색 - 맞는 값만 보이고 모두 체크(엑셀과 같다)
      const s = q.value.trim().toLowerCase();
      pop.querySelectorAll("label[data-t]").forEach((l) => { const t = list[+l.dataset.t]; l.hidden = !!s && !(t === "" ? "(빈 칸)" : t).toLowerCase().includes(s); if (s) l.querySelector("input").checked = !l.hidden; });
      pop.querySelector("label.all span").textContent = s ? "(검색 결과 모두 선택)" : "(모두 선택)"; pop.querySelector("label.add").hidden = !s; syncAll();
    };
    pop.querySelector("[data-all]").onchange = (e) => shown().forEach((b) => (b.checked = e.target.checked));
    pop.addEventListener("change", (e) => { if (e.target.matches("input[data-i]")) syncAll(); });
    const close = () => { pop.remove(); document.removeEventListener("mousedown", off); };
    function off(e) { if (!pop.contains(e.target) && !e.target.closest(".fltDlg")) close(); }
    setTimeout(() => document.addEventListener("mousedown", off), 0);
    pop.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); if (e.key === "Enter" && e.target === q) pop.querySelector('[data-fa="ok"]').click(); e.stopPropagation(); });
    pop.addEventListener("click", (e) => {
      const fs = e.target.closest("[data-fs]"), fx = e.target.closest("[data-fx]"), op = e.target.closest("[data-op]"), col = e.target.closest("[data-col]"), scol = e.target.closest("[data-scol]"), fa = e.target.closest("[data-fa]");
      if (fs) {
        close(); const S = N().S, keep = { sel: S.sel, cur: S.cur };
        S.sel = { ...g }; S.cur = { r: g.r1, c };
        sortRange(fs.dataset.fs === "d", true); S.sel = keep.sel; S.cur = keep.cur; filterReapply();
      } else if (fx && !fx.disabled) {
        if (fx.dataset.fx === "clear") { close(); setCrit(c, null); }
        else { const m = pop.querySelector(`[data-more="${fx.dataset.fx}"]`); m.hidden = !m.hidden; }
      } else if (scol) {
        close(); const S = N().S, keep = { sel: S.sel, cur: S.cur }, i = scol.dataset.scol.indexOf(":");
        S.sel = { ...g }; S.cur = { r: g.r1, c };
        sortRange(false, true, { k: scol.dataset.scol.slice(0, i) === "fill" ? "fill" : "color", v: scol.dataset.scol.slice(i + 1) }); S.sel = keep.sel; S.cur = keep.cur; filterReapply();
      } else if (col) { close(); const i = col.dataset.col.indexOf(":"), k = col.dataset.col.slice(0, i), v = col.dataset.col.slice(i + 1); setCrit(c, k === "fill" ? { fill: v } : { font: v }); }
      else if (op) { close(); condDlg(c, op.dataset.op, cr, list.filter((t) => t !== ""), isNumCol); }
      else if (fa) {
        if (fa.dataset.fa === "ok") {
          const searching = !!q.value.trim(), picked = (searching ? shown() : [...pop.querySelectorAll("input[data-i]")]).filter((b) => b.checked).map((b) => list[+b.dataset.i]);
          const add = searching && pop.querySelector("[data-add]").checked;  // 엑셀 "현재 선택 영역을 필터에 추가" - 지금 보이는 값에 검색해 고른 값을 더한다
          const keep = add ? (cr && cr.vals ? cr.vals : [...pass]) : [], vs = [...new Set([...keep, ...picked])];
          const all = (!searching || add) && list.every((t) => vs.includes(t)) && !other.size;
          setCrit(c, all ? null : { vals: vs });
        }
        close();
      }
    });
    q.focus();
  }
  function condDlg(c, op, cr, items, isNumCol) {  // 사용자 지정 자동 필터 - 조건 두 개(그리고·또는) · 상위 10
    const x = X(), L = x.colName(c);
    document.querySelectorAll(".fltDlg").forEach((m) => m.remove());
    const dlg = document.createElement("div"); dlg.className = "fltDlg";
    const opts = (sel) => `<option value="">(없음)</option>` + Object.entries(OPS).map(([k, t]) => `<option value="${k}"${k === sel ? " selected" : ""}>${t}</option>`).join("");
    const dl = `<datalist id="fltVals">${items.slice(0, 300).map((t) => `<option value="${x.esc(t)}">`).join("")}</datalist>`;
    if (op === "top") {
      const t = cr && cr.top ? cr : { top: 10 };
      dlg.innerHTML = `<b>상위 10 자동 필터 - ${L} 열</b><div class="row"><select data-k="dir"><option value="top">상위</option><option value="bottom"${t.bottom ? " selected" : ""}>하위</option></select><input type="number" data-k="n" min="1" value="${t.top}" style="width:70px"><select data-k="pct"><option value="">항목</option><option value="1"${t.pct ? " selected" : ""}>%</option></select></div><div class="acts"><button data-d="ok" class="primary">확인</button><button data-d="no">취소</button></div>`;
    } else {
      const cur = cr && cr.cond ? cr.cond : [], a = op === "custom" ? cur[0] || { op: "eq" } : op === "between" ? { op: "ge" } : { op }, b = op === "custom" ? cur[1] || {} : op === "between" ? { op: "le" } : {};
      const orOn = op === "custom" ? !!(cr && cr.or) : false;
      const row = (q, i) => `<div class="row"><select data-k="op${i}">${opts(q.op)}</select><input type="text" list="fltVals" data-k="v${i}" value="${x.esc(q.v == null ? "" : String(q.v))}"></div>`;
      dlg.innerHTML = `<b>사용자 지정 자동 필터 - ${L} 열</b><small>찾을 조건 · 같음·같지 않음은 ? = 한 글자, * = 여러 글자</small>${row(a, 0)}<div class="row andor"><label><input type="radio" name="fao" value="and"${orOn ? "" : " checked"}> 그리고</label><label><input type="radio" name="fao" value="or"${orOn ? " checked" : ""}> 또는</label></div>${row(b, 1)}${dl}<div class="acts"><button data-d="ok" class="primary">확인</button><button data-d="no">취소</button></div>`;
    }
    document.body.appendChild(dlg);
    const get = (k) => dlg.querySelector(`[data-k="${k}"]`);
    const ok = () => {
      if (op === "top") { const n = Math.max(1, Math.round(+get("n").value || 10)); setCrit(c, { top: n, ...(get("dir").value === "bottom" ? { bottom: true } : {}), ...(get("pct").value ? { pct: true } : {}) }); }
      else {
        const num = (s) => (s !== "" && isFinite(+s) ? +s : s);
        const cond = [0, 1].map((i) => ({ op: get("op" + i).value, v: num(get("v" + i).value.trim()) })).filter((q) => q.op);
        if (!cond.length) { setCrit(c, null); dlg.remove(); return; }
        setCrit(c, { cond, ...(dlg.querySelector('input[name="fao"]:checked').value === "or" && cond.length > 1 ? { or: true } : {}) });
      }
      dlg.remove();
    };
    dlg.addEventListener("click", (e) => { const d = e.target.closest("[data-d]"); if (!d) return; if (d.dataset.d === "ok") ok(); else dlg.remove(); });
    dlg.addEventListener("keydown", (e) => { if (e.key === "Escape") dlg.remove(); if (e.key === "Enter") ok(); e.stopPropagation(); });
    const first = dlg.querySelector("input"); if (first) { first.focus(); first.select(); }
  }
  // ---------------------------------------------------------------- 중복된 항목 제거 · 텍스트 나누기(엑셀 데이터 탭)
  function dataRange() {
    const S = N().S, x = X(); let g = x.clampRange(S.sel);
    if (g.r1 === g.r2 && g.c1 === g.c2) g = region(x.sheet(), S.cur.r, S.cur.c);
    return g;
  }
  function removeDuplicates() {
    const x = X(), sh = x.sheet(), g = dataRange();
    if (g.r2 <= g.r1) { x.toast("두 줄 이상인 범위에서 씁니다"); return; }
    const first = [];
    for (let c = g.c1; c <= g.c2; c++) first.push(valOf(sh.cells[x.key(g.r1, c)]));
    const head = first.every((v) => typeof v === "string" || v == null) && first.some((v) => v);
    const hasHead = head && confirm(`${x.rangeName(g)} 의 중복된 행을 지웁니다(모든 열이 같은 행 - 처음 것만 남김).\n\n첫 줄(${first.filter(Boolean).slice(0, 4).join(", ")}…)이 머리글인가요? [확인] = 머리글은 그대로 · [취소] = 첫 줄도 데이터`);
    const r0 = hasHead ? g.r1 + 1 : g.r1, seen = new Set(), keep = [];
    for (let r = r0; r <= g.r2; r++) {
      const sig = JSON.stringify(Array.from({ length: g.c2 - g.c1 + 1 }, (_, j) => String(N().display(N().effCell(sh.cells[x.key(r, g.c1 + j)]))).toLowerCase()));
      if (seen.has(sig)) continue; seen.add(sig); keep.push(r);
    }
    const removed = g.r2 - r0 + 1 - keep.length;
    if (!removed) { x.toast("중복된 행이 없습니다"); return; }
    x.mutate(() => {
      const rows = keep.map((r) => Array.from({ length: g.c2 - g.c1 + 1 }, (_, j) => sh.cells[x.key(r, g.c1 + j)]));
      for (let i = 0; i <= g.r2 - r0; i++) for (let j = 0; j <= g.c2 - g.c1; j++) {
        const k = x.key(r0 + i, g.c1 + j), v = rows[i] ? rows[i][j] : undefined;
        if (v === undefined) delete sh.cells[k];
        else { const o = x.clone(v); if (o && typeof o === "object" && o.f && keep[i] !== r0 + i) { o.f = N().shiftFormula(o.f, r0 + i - keep[i], 0); delete o.v; } sh.cells[k] = o; }
      }
    });
    x.toast(`중복된 행 ${removed}개를 지웠습니다 - ${keep.length}개 남음`, 3500);
  }
  function textToColumns() {
    const S = N().S, x = X(), sh = x.sheet(), g = x.clampRange(S.sel);
    if (g.c1 !== g.c2) { x.toast("한 열만 고른 뒤 씁니다(나눈 값은 오른쪽 열로)"); return; }
    const ans = prompt("나눌 기호 - 쉼표(,) · 탭 · 공백 · 세미콜론(;) 또는 직접 입력", ","); if (ans == null) return;
    const sep = { "탭": "\t", "tab": "\t", "공백": " ", "space": " " }[ans.trim().toLowerCase()] || ans;
    if (!sep) return;
    const parts = []; let width = 0;
    for (let r = g.r1; r <= g.r2; r++) { const t = String(N().display(N().effCell(sh.cells[x.key(r, g.c1)])) || ""); const ps = t === "" ? [] : sep === " " ? t.trim().split(/\s+/) : t.split(sep); parts.push(ps); width = Math.max(width, ps.length); }
    if (width < 2) { x.toast(`"${ans}" 로 나눌 값이 없습니다`); return; }
    let busy = 0; for (let r = g.r1; r <= g.r2; r++) for (let j = 1; j < width; j++) { const v = valOf(sh.cells[x.key(r, g.c1 + j)]); if (v != null && v !== "") busy++; }
    if (busy && !confirm(`오른쪽 ${width - 1}열에 값이 있는 칸 ${busy}개를 덮어씁니다. 계속할까요?`)) return;
    x.mutate(() => { for (let i = 0; i < parts.length; i++) for (let j = 0; j < width; j++) { const k = x.key(g.r1 + i, g.c1 + j); const t = parts[i][j]; if (t === undefined) { if (j) { const o = { ...x.cellObj(sh, k) }; delete o.v; delete o.f; x.putCell(sh, k, o); } continue; } N().setInput(sh, k, t.trim()); } });
    x.toast(`${parts.length}줄을 ${width}열로 나눴습니다`);
  }
  function dataMenu(btn) {
    const x = X(), sh = x.sheet();
    x.openMenu(btn, [
      { label: sh.filter ? "필터 끄기 (Ctrl+Shift+L)" : "필터 켜기 (Ctrl+Shift+L)", act: filterToggle },
      { label: "필터 지우기(모든 조건)", disabled: !(sh.filter && sh.filter.cols), act: filterClear },
      { label: "다시 적용", disabled: !sh.filter, act: filterReapply },
      "-",
      { label: "중복된 항목 제거…", act: removeDuplicates }, { label: "텍스트 나누기…(한 열 → 여러 열)", act: textToColumns },
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
    LET: ["이름1, 값1, …, 계산", "이름을 붙여 계산"], XMATCH: ["찾을 값, 범위, [0·-1·1·2], [1·-1]", "위치(새 - 정렬 안 해도 근사)"], DATEDIF: ["시작, 끝, \"Y·M·D·YM·MD·YD\"", "두 날짜 사이"],
    NETWORKDAYS: ["시작, 끝, [휴일]", "평일 수"], WORKDAY: ["시작, 평일 수, [휴일]", "평일로 며칠 뒤"],
    GROUPBY: ["행 필드, 값, SUM·AVERAGE·COUNT…|LAMBDA, [머리글 0·1·2·3], [합계 1·0·-1 · 2↑ 소계], [정렬 ±n|{±n,±m}], [거르기]", "묶어서 요약(넘침)"],
    LAMBDA: ["매개변수1, …, 계산", "함수 만들기 - MAP 등에 넘기거나 LET·이름 정의에 담아 f(값)"], MAP: ["범위1, …, LAMBDA(값1, …)", "칸마다(넘침)"],
    BYROW: ["범위, LAMBDA(행)", "행마다 한 값(넘침)"], BYCOL: ["범위, LAMBDA(열)", "열마다 한 값(넘침)"], REDUCE: ["[처음 값], 범위, LAMBDA(누적, 값)", "누적해서 한 값"],
    SCAN: ["[처음 값], 범위, LAMBDA(누적, 값)", "누적 과정(넘침)"], MAKEARRAY: ["행 수, 열 수, LAMBDA(행, 열)", "배열 만들기(넘침)"],
    PIVOTBY: ["행 필드, 열 필드, 값, SUM·AVERAGE·COUNT…|LAMBDA, [머리글 0·1·2·3], [행 합계 · 2↑ 소계], [행 정렬 ±n], [열 합계], [열 정렬 ±n], [거르기]", "피벗 요약(넘침)"],
    TAKE: ["범위, 행 수, [열 수]", "앞(음수면 뒤)에서 가져오기(넘침)"], DROP: ["범위, 행 수, [열 수]", "앞(음수면 뒤)에서 빼기(넘침)"], CHOOSECOLS: ["범위, 열 번호1, …", "열 고르기(넘침)"],
    CHOOSEROWS: ["범위, 행 번호1, …", "행 고르기(넘침)"], HSTACK: ["범위1, 범위2, …", "옆으로 잇기(넘침)"], VSTACK: ["범위1, 범위2, …", "아래로 잇기(넘침)"],
    TOCOL: ["범위, [무시 0·1·2·3], [열 방향]", "한 열로(넘침)"], TOROW: ["범위, [무시], [열 방향]", "한 행으로(넘침)"], TEXTSPLIT: ["글, 열 구분자, [행 구분자], [빈 값 무시]", "글 나누기(넘침)"],
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
  // ---------------------------------------------------------------- 서식 복사(엑셀 서식 복사 붓) - 누르면 고른 칸의 서식을 잡고, 다음에 고른 칸(범위)에 바둑판처럼 붙인다. 두 번 누르면 계속(Esc 끝)
  const PAINT = { grid: null, keep: false };
  const CONTENT = ["v", "f", "sp", "da", "note"];
  function paintArm(keep) {
    const S = N().S, x = X(), sh = x.sheet(), g = x.clampRange(S.sel);
    if (PAINT.grid && !keep) { paintOff(); return; }
    const grid = [];
    for (let r = g.r1; r <= g.r2; r++) { const row = []; for (let c = g.c1; c <= g.c2; c++) { const o = { ...x.cellObj(sh, x.key(r, c)) }; for (const k of CONTENT) delete o[k]; row.push(o); } grid.push(row); }
    PAINT.grid = grid; PAINT.keep = !!keep;
    const b = $("#xPaint"); if (b) b.classList.add("on");
    document.body.classList.add("painting");
    x.toast(keep ? "서식 복사(계속) - 칸을 고를 때마다 붙입니다 · Esc 끝" : "서식 복사 - 붙일 칸(범위)을 고르세요 · Esc 취소", 3000);
  }
  function paintOff() { PAINT.grid = null; PAINT.keep = false; const b = $("#xPaint"); if (b) b.classList.remove("on"); document.body.classList.remove("painting"); }
  function paintApply() {
    if (!PAINT.grid) return;
    const S = N().S, x = X(), g = x.clampRange(S.sel), src = PAINT.grid, h = src.length, w = src[0].length;
    x.mutate(() => {
      const sh = x.sheet();
      for (let r = g.r1; r <= g.r2; r++) for (let c = g.c1; c <= g.c2; c++) {
        const k = x.key(r, c), o = x.cellObj(sh, k), keep = {};
        for (const kk of CONTENT) if (o[kk] !== undefined) keep[kk] = o[kk];
        x.putCell(sh, k, { ...src[(r - g.r1) % h][(c - g.c1) % w], ...keep });
      }
    });
    if (!PAINT.keep) paintOff();
  }
  document.addEventListener("mouseup", (e) => { if (PAINT.grid && e.target.closest && e.target.closest("#gridWrap td[data-r]")) setTimeout(paintApply, 0); }, true);
  function onKey(e) {
    if (PAINT.grid && e.key === "Escape") { paintOff(); return; }
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
    if (ctrl && e.shiftKey && !e.altKey && k === "l") { e.preventDefault(); e.stopPropagation(); filterToggle(); return; }  // 엑셀 필터 켜기·끄기
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
    const paint = document.createElement("button"); paint.className = "ib"; paint.id = "xPaint"; paint.title = "서식 복사 - 고른 칸의 서식을 다음에 고르는 칸에 붙인다(두 번 누르면 계속 · Esc 끝)"; paint.textContent = "🖌";
    let pt = 0; paint.onclick = () => { clearTimeout(pt); pt = setTimeout(() => paintArm(false), 220); }; paint.ondblclick = () => { clearTimeout(pt); paintOff(); paintArm(true); };
    const data = document.createElement("button"); data.className = "ib"; data.id = "xData"; data.title = "필터·행/열 숨기기"; data.textContent = "데이터 ▾";
    data.onclick = () => dataMenu(data);
    t.append(sep, paint, sum, sort, data, find);
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
  window.NexaSheetX = { onSel: () => { onSel(); renderFilterBtns(); renderDv(); dvMarks(); }, onChange: () => { onSel(); renderFilterBtns(); renderDv(); dvMarks(); }, dvCreate, dvClear, dvPick, condMap, condDialog, condClear, sortRange, fillDir, findBox, autoSum, hide, filterToggle, filterClear, filterReapply, setCrit, hiddenBy, paintArm, paintOff, paintApply, removeDuplicates, textToColumns };
})();
