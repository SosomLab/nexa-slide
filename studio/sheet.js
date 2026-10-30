/* nexa-slide 시트 편집 화면(/studio/sheet.html?deck=<id>) - kind:"sheet" 문서(docs/sheets.md)의 격자 편집·서식·수식 계산·요청·xlsx 내보내기.
   저장·충돌·폴링·요청은 슬라이드 편집기(studio.js)와 같은 서버 API 를 쓴다.
     GET/PUT /api/deck/<id>(?base=버전·force=1)   GET /api/version/<id>(2초)   GET·POST /api/requests/<id>   POST /api/export/<id>
   구성
     머리줄     ← 편집기 · 목록 · 제목 · 저장 상태 · 세션 · 실행 취소 · 엑셀로 내보내기 · 요청 패널
     서식 줄    굵게·기울임·밑줄 · 크기 · 글자색·배경 · 정렬 · 줄바꿈 · 표시 형식 · 병합 · 행·열 · 틀 고정
     수식 줄    셀 주소(이동) · 값/수식
     격자       선택(클릭·끌기·Shift) · 입력(바로 치기·F2·두 번 클릭) · 복사/붙여넣기(탭 구분 - 엑셀과 주고받기) · 열 너비·행 높이 끌기
     아래       시트 탭(전환·추가·이름 바꾸기·삭제)
     오른쪽     AI 요청 - 고른 범위(range)와 글을 남기면 세션이 sheets[].cells 를 고치고 done + reply
   셀 입력 규칙: 숫자로 읽히면 숫자, '=' 로 시작하면 수식(f, 계산값은 v 에 캐시), ' 로 시작하면 글자 그대로. */
(function () {
  "use strict";
  // 허브 중계(/w/<id>/studio/)로 열렸으면 그 접두를 서버 경로 앞에 붙인다(studio.js 와 같다)
  const BASE = (location.pathname.match(/^\/w\/[^/]+/) || [""])[0];
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const NS = BASE ? BASE.slice(3) + ":" : "";
  const LS = { get(k, d) { try { const v = localStorage.getItem("nexa-" + k); return v == null ? d : v; } catch (e) { return d; } },
               set(k, v) { try { if (v === "" || v == null) localStorage.removeItem("nexa-" + k); else localStorage.setItem("nexa-" + k, v); } catch (e) { /* 저장소 없음 */ } } };
  const TAB = (() => { try { let t = sessionStorage.getItem("nexaTab"); if (!t) { t = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)).slice(0, 8); sessionStorage.setItem("nexaTab", t); } return t; } catch (e) { return Math.random().toString(36).slice(2, 10); } })();

  const DEF_W = 96, DEF_H = 24, HW = 46, HH = 24, DEF_ROWS = 100, DEF_COLS = 26;
  const S = {
    id: new URLSearchParams(location.search).get("deck") || "", deck: null, version: null, savedJson: null, reqVersion: null,
    dirty: false, saving: false, conflict: false, undo: [], redo: [], decks: [],
    ti: 0, cur: { r: 0, c: 0 }, anchor: { r: 0, c: 0 }, sel: { r1: 0, c1: 0, r2: 0, c2: 0 },
    edit: null,  // {r, c, mode:"enter"|"edit", orig}
    clip: null, reqs: [], reqTab: LS.get("sheetReqTab", "1") !== "0", reqDone: false, fu: null, reqCur: null, session: null,
  };
  const sheet = () => S.deck.sheets[S.ti];

  // ---------------------------------------------------------------- 공통
  async function api(method, url, body) {
    const headers = { "X-Nexa-Tab": TAB }; if (body !== undefined) headers["Content-Type"] = "application/json";
    const r = await fetch(BASE + url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined, cache: "no-store" });
    let data = null;
    try { data = await r.json(); } catch (e) { /* 빈 응답 */ }
    if (window.NexaMenu && NexaMenu.auth401) NexaMenu.auth401(r, data);
    return { ok: r.ok, status: r.status, data, headers: r.headers };
  }
  let toastT = 0;
  function toast(msg, ms = 2400) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), ms); }
  function setStatus(kind, text) { const s = $("#status"); s.className = "chip sm " + kind; s.textContent = text; }
  function banner(on, msg) { $("#banner").classList.toggle("show", !!on); if (msg) $("#bannerMsg").textContent = msg; }
  function closeMenu() { $$(".menu").forEach((m) => m.remove()); }
  /** items: [{label, key, act, disabled, on}] | "-" | {h} - anchor 요소 아래(또는 {x,y}) */
  function openMenu(anchor, items) {
    closeMenu();
    const m = document.createElement("div"); m.className = "menu";
    m.innerHTML = items.map((it, i) => it === "-" ? "<hr>" : it.h ? `<div class="h">${esc(it.h)}</div>`
      : it.html ? `<div data-i="${i}">${it.html}</div>`
      : `<button data-i="${i}" ${it.disabled ? "disabled" : ""}>${it.on ? "✓ " : ""}${it.icon ? `<span>${it.icon}</span>` : ""}<span>${esc(it.label)}</span>${it.key ? `<span class="k">${esc(it.key)}</span>` : ""}</button>`).join("");
    document.body.appendChild(m);
    let x, y;
    if (anchor.getBoundingClientRect) { const r = anchor.getBoundingClientRect(); x = r.left; y = r.bottom + 4; } else { x = anchor.x; y = anchor.y; }
    x = Math.max(6, Math.min(x, innerWidth - m.offsetWidth - 6));
    if (y + m.offsetHeight > innerHeight - 6) y = Math.max(6, y - m.offsetHeight - (anchor.getBoundingClientRect ? anchor.getBoundingClientRect().height + 8 : 0));
    m.style.left = x + "px"; m.style.top = y + "px";
    m.addEventListener("mousedown", (e) => e.preventDefault());  // 격자 입력칸의 초점을 뺏지 않게
    m.addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (!b || b.disabled) return; const it = items[+b.dataset.i]; closeMenu(); it.act && it.act(); });
  }
  document.addEventListener("mousedown", (e) => { if (!e.target.closest(".menu")) closeMenu(); });

  // ---------------------------------------------------------------- 주소
  const colName = (c) => { let s = ""; c += 1; while (c > 0) { const m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = Math.floor((c - 1) / 26); } return s; };
  const colIndex = (s) => { let n = 0; for (const ch of s.toUpperCase()) n = n * 26 + (ch.charCodeAt(0) - 64); return n - 1; };
  const key = (r, c) => colName(c) + (r + 1);
  const parseRef = (s) => { const m = /^\$?([A-Za-z]{1,3})\$?(\d+)$/.exec(String(s).trim()); return m ? { r: +m[2] - 1, c: colIndex(m[1]) } : null; };
  function parseRange(s) {
    const [a, b] = String(s || "").split(":"); const p = parseRef(a), q = b ? parseRef(b) : p; if (!p || !q) return null;
    return { r1: Math.min(p.r, q.r), c1: Math.min(p.c, q.c), r2: Math.max(p.r, q.r), c2: Math.max(p.c, q.c) };
  }
  const rangeName = (g) => (g.r1 === g.r2 && g.c1 === g.c2 ? key(g.r1, g.c1) : `${key(g.r1, g.c1)}:${key(g.r2, g.c2)}`);
  const inRange = (g, r, c) => r >= g.r1 && r <= g.r2 && c >= g.c1 && c <= g.c2;

  // ---------------------------------------------------------------- 셀 읽기·쓰기 - 값만 있는 셀은 값 그대로(문자열·숫자·불), 서식·수식이 있으면 객체
  const cellObj = (sh, k) => { const v = sh.cells[k]; return v == null ? {} : typeof v === "object" ? v : { v }; };
  function putCell(sh, k, o) {
    const x = {}; for (const [kk, vv] of Object.entries(o)) if (vv !== undefined && vv !== null && vv !== "" && (vv !== false || kk === "v" || o.s)) x[kk] = vv;  // 서식 끔(false)은 키를 지운다 - 값 FALSE·스타일(s)을 덮는 false 는 남긴다
    const ks = Object.keys(x);
    if (!ks.length) delete sh.cells[k]; else if (ks.length === 1 && ks[0] === "v") sh.cells[k] = x.v; else sh.cells[k] = x;
  }
  const cellVal = (sh, k) => { const v = sh.cells[k]; return v == null ? null : typeof v === "object" ? (v.v === undefined ? null : v.v) : v; };

  function normSheet(sh, i) {
    if (!sh.id) sh.id = "t" + String(i + 1).padStart(2, "0");
    if (!sh.name) sh.name = "Sheet" + (i + 1);
    if (!sh.cells || typeof sh.cells !== "object") sh.cells = {};
    return sh;
  }
  /** 화면 격자 크기 - size(없으면 100×26), 데이터가 더 크면 데이터에 맞춘다 */
  function dims(sh) {
    let rows = (sh.size && +sh.size.rows) || DEF_ROWS, cols = (sh.size && +sh.size.cols) || DEF_COLS;
    for (const k of Object.keys(sh.cells)) { const p = parseRef(k); if (p) { rows = Math.max(rows, p.r + 1); cols = Math.max(cols, p.c + 1); } }
    for (const m of merges(sh)) { rows = Math.max(rows, m.r2 + 1); cols = Math.max(cols, m.c2 + 1); }
    return { rows, cols };
  }
  // 숨긴 행·열 - 탭 hiddenRows(["5", …] 행 번호)·hiddenCols(["C", …]) 와 필터로 가린 행(filter.rows, sheetx.js) - 모두 저장
  const colHidden = (sh, c) => !!(sh.hiddenCols && sh.hiddenCols.includes(colName(c)));
  const ROWSET = new WeakMap(), rowSet = (a) => { let s = ROWSET.get(a); if (!s) ROWSET.set(a, (s = new Set(a))); return s; };  // 행 번호 목록 → Set(목록이 바뀌면 새 배열이라 다시 만든다)
  const rowHidden = (sh, r) => !!((Array.isArray(sh.hiddenRows) && rowSet(sh.hiddenRows).has(String(r + 1))) || (sh.filter && Array.isArray(sh.filter.rows) && rowSet(sh.filter.rows).has(String(r + 1))));
  const colW = (sh, c) => (colHidden(sh, c) ? 0 : (sh.cols && +sh.cols[colName(c)]) || DEF_W);
  const rowH = (sh, r) => (rowHidden(sh, r) ? 0 : (sh.rows && +sh.rows[String(r + 1)]) || DEF_H);
  const merges = (sh) => (sh.merges || []).map(parseRange).filter(Boolean);
  const mergeAt = (sh, r, c) => merges(sh).find((m) => inRange(m, r, c)) || null;
  function expandForMerges(sh, g) {  // 범위가 병합 셀에 걸치면 병합 전체가 들어가게 넓힌다
    let changed = true; g = { ...g };
    while (changed) { changed = false; for (const m of merges(sh)) if (!(m.r2 < g.r1 || m.r1 > g.r2 || m.c2 < g.c1 || m.c1 > g.c2) && (m.r1 < g.r1 || m.c1 < g.c1 || m.r2 > g.r2 || m.c2 > g.c2)) { g = { r1: Math.min(g.r1, m.r1), c1: Math.min(g.c1, m.c1), r2: Math.max(g.r2, m.r2), c2: Math.max(g.c2, m.c2) }; changed = true; } }
    return g;
  }

  // ---------------------------------------------------------------- 수식 - 토큰 → 구문 트리 → 계산. 사칙연산·^·&·비교·%, 셀·범위 참조(다른 탭: 이름!A1), 함수
  const ERR = ["#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#NULL!", "#SPILL!", "#CALC!"];
  // 오류 칸 뜻 - 칸에 마우스를 올리면 한 줄로(메모가 있으면 메모)
  const ERR_WHY = { "#DIV/0!": "0 으로 나눴습니다", "#VALUE!": "값의 종류가 맞지 않습니다(글을 숫자로 계산하는 등)", "#REF!": "가리키는 칸이 없어졌거나 순환 참조입니다",
    "#NAME?": "모르는 함수나 이름입니다", "#NUM!": "숫자가 계산할 수 있는 범위를 벗어났습니다", "#N/A": "찾는 값이 없습니다", "#NULL!": "두 범위가 겹치지 않습니다",
    "#SPILL!": "넘칠 자리에 다른 값이 있습니다", "#CALC!": "결과가 비었거나 계산할 수 없는 배열입니다" };
  class FErr { constructor(code) { this.code = code; } }
  const isErrStr = (v) => typeof v === "string" && ERR.includes(v);
  const TOK = new RegExp([
    "(\\s+)",                                                                     // 1 공백
    '("(?:[^"]|"")*")',                                                          // 2 글자
    "((?:'(?:[^']|'')+'|[\\p{L}_][\\p{L}\\p{N}_.]*)!)?(\\$?[A-Za-z]{1,3}\\$?\\d+(?::\\$?[A-Za-z]{1,3}\\$?\\d+)?)(?![\\p{L}\\p{N}_(])", // 3 탭 이름! 4 참조·범위
    "([\\p{L}_][\\p{L}\\p{N}_.]*)(?=\\s*\\()",                                   // 5 함수
    "(TRUE|FALSE)(?![\\p{L}\\p{N}_])",                                           // 6 불
    "(\\d+(?:\\.\\d*)?(?:[eE][+-]?\\d+)?|\\.\\d+(?:[eE][+-]?\\d+)?)",           // 7 숫자
    "(<=|>=|<>|[-+*/^&=<>(),%])",                                                // 8 연산자
    "(#[A-Z/0]+[!?])",                                                           // 9 오류 값
    "([\\p{L}_][\\p{L}\\p{N}_.]*)",                                              // 10 이름(정의 안 됨 → #NAME?)
  ].join("|"), "uiy");
  function tokenize(src) {
    const out = []; TOK.lastIndex = 0; let i = 0;
    while (i < src.length) {
      TOK.lastIndex = i; const m = TOK.exec(src);
      if (!m) throw new FErr("#NAME?");
      const s = i, e = TOK.lastIndex; i = e;
      if (m[1]) continue;
      if (m[2]) out.push({ t: "str", v: m[2].slice(1, -1).replace(/""/g, '"'), s, e });
      else if (m[4]) out.push({ t: "ref", sheet: m[3] ? m[3].slice(0, -1).replace(/^'|'$/g, "").replace(/''/g, "'") : null, v: m[4], s, e, ss: s + (m[3] ? m[3].length : 0) });
      else if (m[5]) out.push({ t: "fn", v: m[5].toUpperCase(), s, e });
      else if (m[6]) out.push({ t: "bool", v: m[6].toUpperCase() === "TRUE", s, e });
      else if (m[7]) out.push({ t: "num", v: parseFloat(m[7]), s, e });
      else if (m[8]) out.push({ t: "op", v: m[8], s, e });
      else if (m[9]) out.push({ t: "err", v: m[9], s, e });
      else out.push({ t: "name", v: m[10], s, e });
    }
    return out;
  }
  function parseFormula(src) {
    const T = tokenize(src); let p = 0;
    const peek = () => T[p], isOp = (v) => T[p] && T[p].t === "op" && T[p].v === v;
    const eat = (v) => { if (!isOp(v)) throw new FErr("#NAME?"); p++; };
    function cmp() { let a = cat(); while (T[p] && T[p].t === "op" && ["=", "<>", "<", ">", "<=", ">="].includes(T[p].v)) { const op = T[p++].v; a = { k: "bin", op, a, b: cat() }; } return a; }
    function cat() { let a = add(); while (isOp("&")) { p++; a = { k: "bin", op: "&", a, b: add() }; } return a; }
    function add() { let a = mul(); while (isOp("+") || isOp("-")) { const op = T[p++].v; a = { k: "bin", op, a, b: mul() }; } return a; }
    function mul() { let a = pow(); while (isOp("*") || isOp("/")) { const op = T[p++].v; a = { k: "bin", op, a, b: pow() }; } return a; }
    function pow() { let a = unary(); while (isOp("^")) { p++; a = { k: "bin", op: "^", a, b: unary() }; } return a; }
    function unary() { if (isOp("-")) { p++; return { k: "neg", a: unary() }; } if (isOp("+")) { p++; return unary(); } return postfix(); }
    function postfix() { let a = prim(); while (isOp("%")) { p++; a = { k: "pct", a }; } return a; }
    function prim() {
      const t = peek(); if (!t) throw new FErr("#NAME?");
      p++;
      if (t.t === "num") return { k: "lit", v: t.v };
      if (t.t === "str") return { k: "lit", v: t.v };
      if (t.t === "bool") return { k: "lit", v: t.v };
      if (t.t === "err") return { k: "err", v: t.v };
      if (t.t === "name") return { k: "err", v: "#NAME?" };
      if (t.t === "ref") { const g = parseRange(t.v); return t.v.includes(":") ? { k: "range", sheet: t.sheet, g } : { k: "ref", sheet: t.sheet, r: g.r1, c: g.c1 }; }
      if (t.t === "fn") {
        eat("("); const args = [];
        if (!isOp(")")) { for (;;) { args.push(isOp(",") || isOp(")") ? { k: "lit", v: null } : cmp()); if (isOp(",")) { p++; continue; } break; } }
        eat(")"); return { k: "fn", name: t.v, args };
      }
      if (t.t === "op" && t.v === "(") { const a = cmp(); eat(")"); return a; }
      throw new FErr("#NAME?");
    }
    const ast = cmp(); if (p < T.length) throw new FErr("#NAME?");
    return ast;
  }
  const ASTC = new Map();
  function astOf(f) { let a = ASTC.get(f); if (!a) { try { a = parseFormula(f.replace(/^=/, "")); } catch (e) { a = { k: "err", v: e instanceof FErr ? e.code : "#NAME?" }; } ASTC.set(f, a); } return a; }

  const fix = (x) => (typeof x === "number" && !Number.isInteger(x) ? Number(x.toPrecision(15)) : x);
  function toNum(v) {
    if (v instanceof FErr) throw v;
    if (v == null || v === "") return 0;
    if (typeof v === "boolean") return v ? 1 : 0;
    if (typeof v === "number") return v;
    if (isErrStr(v)) throw new FErr(v);
    const n = parseNumberText(String(v)); if (n === null) throw new FErr("#VALUE!"); return n.v;
  }
  const toStr = (v) => { if (v instanceof FErr) throw v; if (v == null) return ""; if (typeof v === "boolean") return v ? "TRUE" : "FALSE"; if (typeof v === "number") return generalNum(v); return String(v); };
  const toBool = (v) => { if (v instanceof FErr) throw v; if (typeof v === "string") { if (/^true$/i.test(v)) return true; if (/^false$/i.test(v)) return false; throw new FErr("#VALUE!"); } return !!toNum(v); };

  const CALC = { memo: null, busy: null };
  function sheetByName(name, from) { if (name == null) return from; return S.deck.sheets.find((s) => s.name.toLowerCase() === name.toLowerCase()) || null; }
  function valueAt(sh, r, c) {
    const k = key(r, c), raw = sh.cells[k];
    if (raw && typeof raw === "object" && raw.f) return evalCell(sh, k);
    const v = raw == null ? null : typeof raw === "object" ? (raw.v === undefined ? null : raw.v) : raw;
    if (isErrStr(v)) return new FErr(v);
    return v;
  }
  function evalCell(sh, k) {
    const id = sh.id + "!" + k;
    if (CALC.memo.has(id)) return CALC.memo.get(id);
    if (CALC.busy.has(id)) return new FErr("#REF!");  // 순환 참조
    CALC.busy.add(id);
    let v;
    try { v = ev(astOf(sh.cells[k].f), sh); if (v && v.range) v = v.vals.length === 1 ? v.vals[0] : new FErr("#VALUE!"); if (v == null) v = 0; v = fix(v); }
    catch (e) { v = e instanceof FErr ? e : new FErr("#VALUE!"); }
    CALC.busy.delete(id); CALC.memo.set(id, v);
    return v;
  }
  function rangeVals(sh, g) { const out = []; for (let r = g.r1; r <= g.r2; r++) for (let c = g.c1; c <= g.c2; c++) out.push(valueAt(sh, r, c)); return out; }
  function ev(n, sh) {
    switch (n.k) {
      case "lit": return n.v;
      case "err": throw new FErr(n.v);
      case "ref": { const s = sheetByName(n.sheet, sh); if (!s) throw new FErr("#REF!"); const v = valueAt(s, n.r, n.c); if (v instanceof FErr) throw v; return v; }
      case "range": { const s = sheetByName(n.sheet, sh); if (!s) throw new FErr("#REF!"); return { range: true, vals: rangeVals(s, n.g) }; }
      case "neg": return -toNum(sc(ev(n.a, sh)));
      case "pct": return toNum(sc(ev(n.a, sh))) / 100;
      case "bin": {
        const a = sc(ev(n.a, sh)), b = sc(ev(n.b, sh));
        switch (n.op) {
          case "+": return toNum(a) + toNum(b);
          case "-": return toNum(a) - toNum(b);
          case "*": return toNum(a) * toNum(b);
          case "/": { const d = toNum(b), x = toNum(a); if (d === 0) throw new FErr("#DIV/0!"); return x / d; }
          case "^": { const r = Math.pow(toNum(a), toNum(b)); if (!isFinite(r)) throw new FErr("#NUM!"); return r; }
          case "&": return toStr(a) + toStr(b);
          default: return compare(a, b, n.op);
        }
      }
      case "fn": return callFn(n, sh);
    }
    throw new FErr("#VALUE!");
  }
  const sc = (v) => { if (v instanceof FErr) throw v; if (v && v.range) { if (v.vals.length !== 1) throw new FErr("#VALUE!"); const x = v.vals[0]; if (x instanceof FErr) throw x; return x; } return v; };
  function compare(a, b, op) {
    if (a instanceof FErr) throw a; if (b instanceof FErr) throw b;
    const rank = (v) => (v == null ? 0 : typeof v === "number" ? 1 : typeof v === "string" ? 2 : 3);
    if (a == null) a = typeof b === "string" ? "" : typeof b === "boolean" ? false : 0;
    if (b == null) b = typeof a === "string" ? "" : typeof a === "boolean" ? false : 0;
    let d;
    if (rank(a) !== rank(b)) d = rank(a) - rank(b);
    else if (typeof a === "string") { const x = a.toLowerCase(), y = b.toLowerCase(); d = x < y ? -1 : x > y ? 1 : 0; }
    else d = (a > b) - (a < b);
    return { "=": d === 0, "<>": d !== 0, "<": d < 0, ">": d > 0, "<=": d <= 0, ">=": d >= 0 }[op];
  }
  /** 집계 함수의 인수 - 참조·범위 안은 숫자만(글·빈 칸 무시, 오류는 그대로), 직접 쓴 값은 숫자로 바꾼다 */
  function nums(args, sh, opt = {}) {
    const out = [];
    for (const a of args) {
      const isRef = a.k === "ref" || a.k === "range";
      const v = ev(a, sh);
      const list = v && v.range ? v.vals : [v];
      for (const x of list) {
        if (x instanceof FErr) { if (opt.count) continue; throw x; }
        if (isRef) { if (typeof x === "number") out.push(x); else if (opt.counta && x != null && x !== "") out.push(x); }
        else if (opt.counta) { if (x != null) out.push(x); }
        else if (opt.count) { if (typeof x === "number" || (typeof x === "string" && parseNumberText(x)) || typeof x === "boolean") out.push(x); }
        else out.push(toNum(x));
      }
    }
    return out;
  }
  function roundX(x, n, how) {
    const f = Math.pow(10, n), y = Number((Math.abs(x) * f).toPrecision(15));
    const z = how === "up" ? Math.ceil(y) : how === "down" ? Math.floor(y) : Math.round(y);
    return Math.sign(x) * z / f;
  }
  function callFn(n, sh) {
    const A = n.args, one = (i) => sc(ev(A[i], sh));
    switch (n.name) {
      case "SUM": return nums(A, sh).reduce((s, x) => s + x, 0);
      case "AVERAGE": { const l = nums(A, sh); if (!l.length) throw new FErr("#DIV/0!"); return l.reduce((s, x) => s + x, 0) / l.length; }
      case "MIN": { const l = nums(A, sh); return l.length ? Math.min(...l) : 0; }
      case "MAX": { const l = nums(A, sh); return l.length ? Math.max(...l) : 0; }
      case "COUNT": return nums(A, sh, { count: true }).length;
      case "COUNTA": return nums(A, sh, { counta: true }).length;
      case "ROUND": case "ROUNDUP": case "ROUNDDOWN": {
        if (!A.length) throw new FErr("#VALUE!");
        return roundX(toNum(one(0)), A[1] ? Math.trunc(toNum(one(1))) : 0, n.name === "ROUNDUP" ? "up" : n.name === "ROUNDDOWN" ? "down" : "");
      }
      case "ABS": return Math.abs(toNum(one(0)));
      case "IF": { if (!A.length) throw new FErr("#VALUE!"); return toBool(one(0)) ? (A[1] ? one(1) : true) : (A[2] ? one(2) : false); }
      case "IFERROR": { try { return one(0); } catch (e) { if (e instanceof FErr) return A[1] ? one(1) : ""; throw e; } }
      case "AND": { const l = A.map((_, i) => toBool(one(i))); return l.every(Boolean); }
      case "OR": { const l = A.map((_, i) => toBool(one(i))); return l.some(Boolean); }
      case "NOT": return !toBool(one(0));
      case "CONCAT": case "CONCATENATE": return A.map((a) => { const v = ev(a, sh); return v && v.range ? v.vals.map(toStr).join("") : toStr(v); }).join("");
    }
    throw new FErr("#NAME?");
  }
  /** 모든 탭의 수식을 다시 계산해 v 에 넣는다. 바뀐 셀이 있으면 true */
  function recalc() {
    // 계산은 sheetcalc.js(NexaCalc - Python sheet_calc 와 같은 규칙, 엑셀 함수 약 70개·배열 수식). 모르는 함수(매크로 사용자 함수)는 마지막 엑셀 값을 그대로 둔다
    // - 아래 옛 계산기(16개 함수)는 모르는 함수를 #NAME? 로 덮어 가져온 엑셀의 계산값을 잃었다. NexaCalc 가 없을 때만 쓴다
    if (window.NexaCalc) return NexaCalc.recalc(S.deck) > 0;
    CALC.memo = new Map(); CALC.busy = new Set(); let changed = false;
    for (const sh of S.deck.sheets) for (const [k, raw] of Object.entries(sh.cells)) {
      if (!raw || typeof raw !== "object" || !raw.f) continue;
      let v = evalCell(sh, k); v = v instanceof FErr ? v.code : v;
      if (raw.v !== v) { raw.v = v; changed = true; }
    }
    CALC.memo = null; CALC.busy = null;
    return changed;
  }

  // ---------------------------------------------------------------- 수식 안 참조 고쳐 쓰기 - 복사·붙여넣기(상대 이동), 행·열 삽입·삭제
  // 참조 끝점 - 칸 A1 · 열 전체의 끝 A(r = null) · 행 전체의 끝 3(c = null)
  function refParts(s) { const m = /^(\$?)([A-Za-z]{1,3})?(\$?)(\d+)?$/.exec(s); return { ca: !!m[1], c: m[2] ? colIndex(m[2]) : null, ra: !!m[3], r: m[4] ? +m[4] - 1 : null }; }
  const refText = (p) => (p.c != null ? `${p.ca ? "$" : ""}${colName(p.c)}` : "") + (p.r != null ? `${p.ra ? "$" : ""}${p.r + 1}` : "");
  // 참조 고쳐 쓰기용 토큰 - 계산기(sheetcalc.js TOK)와 같은 모양: 칸·범위·열 전체 A:C·행 전체 3:5·넘친 범위 H2#·표 구조적 참조(그대로 둔다)
  const REF_TOK = new RegExp([
    "(\\s+)", '("(?:[^"]|"")*")',
    "((?:'(?:[^']|'')+'|[\\p{L}_][\\p{L}\\p{N}_.]*)!)?(\\$?[A-Za-z]{1,3}\\$?\\d+(?::\\$?[A-Za-z]{1,3}\\$?\\d+)?|\\$?[A-Za-z]{1,3}:\\$?[A-Za-z]{1,3}|\\$?\\d+:\\$?\\d+)(?![\\p{L}\\p{N}_(])",
    "([\\p{L}_][\\p{L}\\p{N}_.]*)(?=\\s*\\()", "(TRUE|FALSE)(?![\\p{L}\\p{N}_])", "(\\d+(?:\\.\\d*)?(?:[eE][+-]?\\d+)?|\\.\\d+(?:[eE][+-]?\\d+)?)",
    "(<=|>=|<>|[-+*/^&=<>(),%])", "(#[A-Z/0]+[!?])", "((?:[\\p{L}_][\\p{L}\\p{N}_.]*)?\\[(?:[^\\[\\]]|\\[[^\\[\\]]*\\])*\\])", "([\\p{L}_][\\p{L}\\p{N}_.]*)",
  ].join("|"), "uiy");
  /** fn(끝점들[], 탭 이름|null) → 새 끝점들 또는 null(#REF!) */
  function rewriteFormula(f, fn) {
    const src = f.replace(/^=/, ""); let out = "", last = 0, i = 0;
    while (i < src.length) {
      REF_TOK.lastIndex = i; const m = REF_TOK.exec(src);
      if (!m || REF_TOK.lastIndex === i) return f;  // 읽지 못하는 수식은 그대로
      i = REF_TOK.lastIndex;
      if (!m[4]) continue;
      const sheetName = m[3] ? m[3].slice(0, -1).replace(/^'|'$/g, "").replace(/''/g, "'") : null;
      const at = m.index + (m[3] ? m[3].length : 0), ends = m[4].split(":").map(refParts), nw = fn(ends, sheetName);
      out += src.slice(last, at) + (nw ? nw.map(refText).join(":") : "#REF!"); last = at + m[4].length;
      if (src[i] === "#" && !m[4].includes(":")) i++;  // 넘친 범위 참조 H2# - '#' 는 그대로 뒤에 남는다
    }
    return "=" + out + src.slice(last);
  }
  const shiftFormula = (f, dr, dc) => rewriteFormula(f, (ends) => {
    const n = ends.map((p) => ({ ...p, r: p.r == null || p.ra ? p.r : p.r + dr, c: p.c == null || p.ca ? p.c : p.c + dc }));  // 열 전체·행 전체는 없는 쪽을 두고
    return n.some((p) => (p.r != null && p.r < 0) || (p.c != null && p.c < 0)) ? null : n;
  });

  // ---------------------------------------------------------------- 표시 형식 - 엑셀 형식 문자열의 흔한 것(#,##0 · 0.0% · 날짜 yyyy-mm-dd · 앞뒤 글)
  function generalNum(v) {
    if (!isFinite(v)) return String(v);
    if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
    const a = Math.abs(v);
    if (a !== 0 && (a < 1e-9 || a >= 1e15)) return v.toExponential(5).replace(/\.?0+e/, "E").replace("E+", "E+");
    return String(Number(v.toPrecision(11)));
  }
  const DAY0 = Date.UTC(1899, 11, 30);
  const serialOf = (y, m, d) => (Date.UTC(y, m - 1, d) - DAY0) / 864e5;
  function fmtDate(v, f) {
    const t = new Date(DAY0 + Math.round(v * 864e5)), Y = t.getUTCFullYear(), M = t.getUTCMonth() + 1, D = t.getUTCDate(), h = t.getUTCHours(), mi = t.getUTCMinutes();
    const p2 = (x) => String(x).padStart(2, "0");
    return f.replace(/"([^"]*)"/g, "$1").replace(/yyyy/gi, Y).replace(/yy/gi, String(Y).slice(2)).replace(/hh/gi, p2(h)).replace(/(\d{2}:)mm/g, (_, a) => a + p2(mi))
      .replace(/mm/g, p2(M)).replace(/(?<![A-Za-z])m(?![A-Za-z])/g, M).replace(/dd/gi, p2(D)).replace(/(?<![A-Za-z])d(?![A-Za-z])/gi, D);
  }
  function fmtNumber(v, fmt) {
    const secs = fmt.split(";"); let sec = secs[0], neg = v < 0;
    if (neg && secs[1]) { sec = secs[1]; v = -v; neg = false; }
    if (/[yd]|mm(?!.*0)/i.test(sec.replace(/"[^"]*"/g, "")) && !/[#0]/.test(sec.replace(/"[^"]*"/g, ""))) return fmtDate(v, sec);
    const m = /([#0,]*0|#[#,]*)(\.([0#]+))?/.exec(sec); if (!m) return generalNum(v);
    const pct = sec.includes("%"); let x = Math.abs(pct ? v * 100 : v);
    const dec = m[3] || "", minD = (dec.match(/0/g) || []).length, maxD = dec.length;
    let s = roundX(x, maxD).toFixed(maxD);
    if (maxD > minD) s = s.replace(new RegExp(`0{1,${maxD - minD}}$`), "").replace(/\.$/, "");
    if (m[1].includes(",")) { const [i, d] = s.split("."); s = i.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (d ? "." + d : ""); }
    const lit = (t) => t.replace(/"([^"]*)"|([^"]+)/g, (_, q, u) => (q != null ? q : u.replace(/_./g, "").replace(/\\(.)/g, "$1").replace(/[#0,?]/g, "")));  // 따옴표 안 글은 그대로
    const pre = lit(sec.slice(0, m.index)), post = lit(sec.slice(m.index + m[0].length));
    return (neg && roundX(x, maxD) !== 0 ? "-" : "") + pre + s + post;
  }
  function display(raw) {
    const o = raw == null ? {} : typeof raw === "object" ? raw : { v: raw };
    const v = o.v;
    if (v == null) return "";
    if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
    if (typeof v === "number") { if (o.fmt && o.fmt !== "General" && o.fmt !== "@") { try { return fmtNumber(v, o.fmt); } catch (e) { return generalNum(v); } } return generalNum(v); }
    return String(v);
  }
  /** 입력 글이 숫자로 읽히면 {v, fmt?}. 1,234 · -3.5 · 15% · 1e3 · 2026-10-28(날짜 일련번호 + yyyy-mm-dd) */
  function parseNumberText(t) {
    const s = t.trim(); if (!s) return null;
    let m = /^([+-]?)((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?(%?)$/.exec(s);
    if (m) {
      let v = parseFloat(m[2].replace(/,/g, "")) * (m[3] ? Math.pow(10, +m[3]) : 1); if (m[1] === "-") v = -v;
      if (m[4]) return { v: fix(v / 100), fmt: "0%" };
      return { v: fix(v), fmt: m[2].includes(",") ? "#,##0" : undefined };
    }
    m = /^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/.exec(s);
    if (m && +m[2] >= 1 && +m[2] <= 12 && +m[3] >= 1 && +m[3] <= 31) return { v: serialOf(+m[1], +m[2], +m[3]), fmt: "yyyy-mm-dd" };
    return null;
  }
  /** 셀에 글을 넣는다(서식은 남긴다) */
  function setInput(sh, k, text) {
    const o = { ...cellObj(sh, k) }; delete o.f; delete o.v; delete o.sp;  // 넘친 칸(sp)에 쓰면 내 값 - 동적 배열은 #SPILL! 이 된다
    if (text === "" || text == null) { /* 값 지움 */ }
    else if (text[0] === "=" && text.length > 1) o.f = text;
    else if (text[0] === "'") o.v = text.slice(1);
    else if (/^(true|false)$/i.test(text.trim())) o.v = /^true$/i.test(text.trim());
    else { const n = parseNumberText(text); if (n) { o.v = n.v; if (n.fmt && !o.fmt) o.fmt = n.fmt; } else o.v = text; }
    putCell(sh, k, o);
  }
  /** 입력칸에 보일 원문 - 수식은 f, 날짜 형식이면 날짜 글 */
  function rawText(sh, k) {
    const o = cellObj(sh, k);
    if (o.f) return o.f;
    if (o.v == null) return "";
    if (typeof o.v === "boolean") return o.v ? "TRUE" : "FALSE";
    if (typeof o.v === "number") { if (o.fmt && /y|d/i.test(o.fmt) && !/[#0]/.test(o.fmt)) return fmtDate(o.v, "yyyy-mm-dd"); if (o.fmt && o.fmt.includes("%")) return generalNum(fix(o.v * 100)) + "%"; return generalNum(o.v); }
    if (typeof o.v === "string" && (o.v[0] === "=" || parseNumberText(o.v) || /^(true|false)$/i.test(o.v))) return "'" + o.v;
    return String(o.v);
  }

  // ---------------------------------------------------------------- 실행 취소·저장
  const deckJson = () => JSON.stringify(S.deck);
  function snapshot() { aiBusyWarn(); S.undo.push(deckJson()); if (S.undo.length > 150) S.undo.shift(); S.redo = []; updUndo(); }
  // AI 가 처리 중인 범위를 고치기 시작하면 한 번 알린다(잠그지 않음 - 저장은 병합되고 같은 셀은 사람 값이 남는다). 편집기와 같다 - docs/collab.md 2단계
  const aiWarned = new Set();
  function aiBusyWarn() {
    if (!S.deck || !S.reqs) return;
    const sh = sheet(), g = S.sel;
    for (const r of S.reqs) {
      if (r.status !== "working" || reqSlide(r) !== sh.id) continue;
      const q = parseRange(r.range);
      if (q && (q.r2 < g.r1 || q.r1 > g.r2 || q.c2 < g.c1 || q.c1 > g.c2)) continue;  // 고르는 범위와 겹치지 않음
      const k = `${r.id}`;
      if (aiWarned.has(k)) continue;
      aiWarned.add(k);
      toast(`${RQ ? RQ.agentName() : "AI"} 가 ${q ? `${r.range} 범위를` : "이 탭을"} 처리하는 중입니다 - 지금 고치면 AI 의 변경과 합쳐지고, 같은 셀은 내 값이 남습니다`, 5000);
      return;
    }
  }
  function updUndo() { $("#undoBtn").disabled = !S.undo.length; $("#redoBtn").disabled = !S.redo.length; }
  // 남의 변경(다른 창·AI·병합 저장)을 받은 뒤의 실행 취소는 내 편집만 되돌린다 - NexaMerge.seal/undoTarget(nexa-merge.js, 편집기와 같다 - docs/collab.md 1단계)
  function undo() { if (!S.undo.length) return; const now = deckJson(); S.redo.push(now); S.deck = NexaMerge.undoTarget(S.undo.pop(), now); S.struct = []; afterChange(); }  // 구조 작업은 실행 취소와 짝을 맞출 수 없어 비운다(그 저장은 예전처럼 셀 병합만)
  function redo() { if (!S.redo.length) return; S.undo.push(deckJson()); S.deck = JSON.parse(S.redo.pop()); S.struct = []; afterChange(); }
  /** 바꾼 뒤: 다시 계산 · 그리기 · 자동 저장 예약 */
  function afterChange() {
    if (S.ti >= S.deck.sheets.length) S.ti = S.deck.sheets.length - 1;
    recalc(); S.dirty = true; setStatus("dirty", "저장 대기"); updUndo();
    renderAll(); scheduleSave();
    if (window.NexaSheetX) NexaSheetX.onChange();
    if ((S.deck.theme || null) !== TH.name) loadTheme(S.deck.theme).then(() => { renderThemeChip(); renderAll(); });  // 실행 취소로 테마가 바뀌었으면
  }
  /** 고치기 - snapshot → fn → afterChange */
  function mutate(fn) { snapshot(); const r = fn(); afterChange(); return r; }
  let saveT = 0;
  function scheduleSave() { clearTimeout(saveT); saveT = setTimeout(save, 700); }
  async function save(force) {
    if (!S.deck || (S.conflict && !force)) return;
    if (S.saving) { scheduleSave(); return; }
    const body = deckJson();
    if (!force && body === S.savedJson) { S.dirty = false; setStatus("saved", "저장됨"); return; }
    S.saving = true; setStatus("dirty", "저장 중…");
    // 병합 저장(merge=1) - 그 사이 다른 창·AI 가 저장했어도 서버가 탭·셀 단위로 합친다(같은 셀은 나중 저장인 내 값). 409 는 기준본을 모를 때뿐
    // 행·열 삽입·삭제(동시 편집 3-2) - 기준판 이후의 구조 작업을 함께 보내면 서버가 기준본·지금 파일도 같이 옮긴 뒤 셀을 합친다
    const sentStruct = force ? [] : (S.struct || []).slice();
    const meta = S.saveMeta ? `&action=${encodeURIComponent(S.saveMeta.action)}${S.saveMeta.note ? "&note=" + encodeURIComponent(S.saveMeta.note) : ""}` : ""; S.saveMeta = null;  // 되돌리기 등 - 변경 원장에 action 으로 남는다
    const r = await api("PUT", `/api/deck/${encodeURIComponent(S.id)}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : "&merge=1"}${meta}`, sentStruct.length ? { ...JSON.parse(body), __struct: sentStruct } : JSON.parse(body));
    if (r.ok) S.struct = (S.struct || []).slice(sentStruct.length);  // 저장된 판이 새 기준 - 보낸 구조 작업은 그 안에 들어 있다
    S.saving = false;
    if (r.ok && r.data.merged && r.data.deck) {  // 합쳐졌다 - 병합 결과(+ 저장하는 사이 더 고친 것)를 화면에, 남의 변경은 내 실행 취소에 섞지 않는다
      const now = deckJson();
      NexaMerge.seal(S.undo, S.redo, now); updUndo();
      S.version = r.data.version; S.savedJson = JSON.stringify(r.data.deck);
      const d = NexaMerge.afterSave(body, now, r.data.deck);
      if (!Array.isArray(d.slides)) d.slides = [];
      (d.sheets || []).forEach(normSheet);
      S.deck = d; if (S.ti >= S.deck.sheets.length) S.ti = Math.max(0, S.deck.sheets.length - 1);
      recalc();  // 합쳐진 셀의 계산값을 다시
      S.dirty = deckJson() !== S.savedJson; S.conflict = false; banner(false);
      renderAll();
      if (window.NexaSheetX) NexaSheetX.onChange();
      setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
      const nt = NexaMerge.notice(r.data.conflicts), n = (r.data.conflicts || []).length;
      toast(nt.text + (n ? "\n" + nt.detail : ""), n ? 7000 : 3500);
      if (S.dirty) scheduleSave();
    } else if (r.ok) {
      S.version = r.data.version; if (r.data.updated) S.deck.updated = r.data.updated;
      S.savedJson = body; if (r.data.updated) { const o = JSON.parse(body); o.updated = r.data.updated; S.savedJson = JSON.stringify(o); }
      S.dirty = deckJson() !== S.savedJson; S.conflict = false; banner(false);
      setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
      if (S.dirty) scheduleSave();
    } else if (r.status === 409) {
      S.conflict = true; setStatus("conflict", "충돌");
      banner(true, "저장하려는 사이 시트 파일이 밖에서(Claude 등) 바뀌었고, 자동으로 합칠 수 없습니다(서버가 다시 시작됨 등). 어느 쪽을 남길까요?");
    } else { setStatus("error", "저장 실패"); toast("저장 실패: " + ((r.data && r.data.error) || r.status), 5000); }
  }

  // ---------------------------------------------------------------- 불러오기·외부 변경 감지
  async function loadDeck(keepView) {
    const r = await fetch(`${BASE}/api/deck/${encodeURIComponent(S.id)}`, { cache: "no-store" });
    if (r.status === 401) { if (window.NexaMenu) NexaMenu.auth401(r, await r.json().catch(() => null)); return false; }
    if (!r.ok) { setStatus("error", "읽기 실패"); toast("시트를 불러오지 못했습니다 (" + r.status + ")", 6000); return false; }
    const deck = await r.json();
    if (deck.kind !== "sheet") { location.replace(`index.html#${encodeURIComponent(S.id)}`); return false; }  // 슬라이드 덱이면 편집기로
    if (!keepView) S.struct = [];
    if (keepView && S.deck) NexaMerge.seal(S.undo, S.redo, deckJson());  // 밖의 변경을 받는다 - 내 실행 취소에 넣지 않고, 이전 기록은 내 편집만 되돌리게 봉인
    else { S.undo = []; S.redo = []; }
    S.version = r.headers.get("X-Deck-Version");
    if (!Array.isArray(deck.sheets) || !deck.sheets.length) deck.sheets = [{ id: "t01", name: "Sheet1", cells: {} }];
    if (!Array.isArray(deck.slides)) deck.slides = [];
    deck.sheets.forEach(normSheet);
    await loadTheme(deck.theme);
    await setupVba(deck);  // VBA 사용자 함수 - recalc 전에
    if (!keepView) { const z = +LS.get(`sheetZoom-${S.id}`, 1) || 1; Z = 1; $("#gridIn").style.zoom = ""; if (z !== 1) setTimeout(() => setZoom(z), 0); renderZoom(); }
    S.deck = deck; S.savedJson = deckJson();
    S.dirty = false; S.conflict = false; banner(false);
    if (!keepView) {
      const [tid, ref] = decodeURIComponent(location.hash.slice(1)).split("!");
      S.ti = Math.max(0, deck.sheets.findIndex((s) => s.id === tid));
      const g = parseRange(ref); if (g) selectRange(g, true); else selectRange({ r1: 0, c1: 0, r2: 0, c2: 0 }, true);
    } else if (S.ti >= deck.sheets.length) S.ti = 0;
    document.title = `${deck.title || S.id} - 시트 - nexa-slide`;
    $("#titleText").textContent = deck.title || S.id; $("#title").title = `${deck.title || ""} · id ${S.id}`;
    setStatus("saved", "저장됨"); updUndo(); renderThemeChip();
    // 세션이 값만 넣고 계산값(v)을 비웠으면 여기서 계산해 저장(엑셀 내보내기에 계산값이 들어가게)
    if (recalc() && !reqBusy()) { S.dirty = true; setStatus("dirty", "저장 대기"); scheduleSave(); }
    renderAll();
    return true;
  }
  // ---------------------------------------------------------------- VBA(사용자 함수 실행기 vba.js · 코드 창)
  // 모듈 소스 = 문서 macros.modules(가져올 때 넣는다). 없으면(0.25.3 전에 가져온 문서) 서버가 vbaProject.bin 에서 읽어 준다(/api/vba) - 고치기 전에는 문서에 넣지 않는다
  const VB = { mods: null, compiled: null, sel: 0, draft: null };
  async function setupVba(deck) {
    const mc = deck.macros || {};
    let mods = Array.isArray(mc.modules) ? mc.modules : null;
    if (!mods && mc.vba) { try { const r = await api("GET", `/api/vba/${encodeURIComponent(S.id)}`); mods = r.ok ? r.data.modules || [] : []; } catch (e) { mods = []; } }
    VB.mods = mods; compileVba();
    const b = $("#vbaBtn"); if (b) b.hidden = !mc.vba;
  }
  function compileVba() {
    if (!window.NexaVBA || !window.NexaCalc) return;
    VB.compiled = VB.mods && VB.mods.length ? NexaVBA.compile(VB.mods) : null;
    NexaCalc.setVba(VB.compiled, NexaVBA);
  }
  function vbaOpen() {
    if (!VB.mods) return toast("이 문서에는 VBA 프로젝트가 없습니다(엑셀 매크로 통합 문서 .xlsm 을 가져오면 생긴다)");
    VB.draft = VB.mods.map((m) => ({ ...m })); VB.sel = Math.max(0, VB.draft.findIndex((m) => m.kind === "std"));
    vbaRender(); $("#vbaDlg").classList.add("show"); $("#vbaCode").focus();
  }
  function vbaErrors(list) { const c = NexaVBA.compile(list); return c.errors; }
  function vbaRender() {
    const errs = vbaErrors(VB.draft), kind = { std: "표준", cls: "클래스", doc: "문서" };
    $("#vbaMods").innerHTML = VB.draft.map((m, i) => { const n = errs.filter((e) => e.module === m.name).length; return `<button data-vm="${i}" class="${i === VB.sel ? "on" : ""}${n ? " err" : ""}" title="${esc(kind[m.kind] || m.kind)} 모듈">${esc(m.name)}<small>${n ? "⚠" + n : esc(kind[m.kind] || "")}</small></button>`; }).join("");
    const m = VB.draft[VB.sel], ta = $("#vbaCode");
    if (m) { if (ta.dataset.i !== String(VB.sel) || ta.value !== m.code) { ta.value = m.code || ""; ta.dataset.i = String(VB.sel); } }
    const fns = m ? [...(m.code || "").matchAll(/^\s*(?:Public\s+|Private\s+)?Function\s+([\p{L}_][\p{L}\p{N}_]*)/gimu)].map((x) => x[1]) : [];
    const mine = errs.filter((e) => m && e.module === m.name);
    $("#vbaMsgs").innerHTML = (mine.length ? mine.map((e) => `<div class="e" data-ln="${e.line}">⚠ ${esc(e.line ? e.line + "행" : "")} ${esc(e.name ? e.name + ": " : "")}${esc(e.msg.replace(/^\d+행: /, ""))} - 이 함수는 계산하지 않고 엑셀이 저장한 값을 그대로 둔다</div>`).join("") : "")
      + (m && m.kind === "std" ? `<div>칸에서 부를 수 있는 함수: ${fns.length ? fns.map((f) => `<code>=${esc(f)}(…)</code>`).join(" ") : "없음"}</div>` : m ? "<div>문서·클래스 모듈 - 칸에서 부를 수 없다(이벤트·매크로는 엑셀에서 돈다). 코드는 고쳐서 내보낼 수 있다</div>" : "");
    $("#vbaDel").disabled = !m || m.kind !== "std";
    $("#vbaSub").textContent = `모듈 ${VB.draft.length}개 · 함수 ${VB.compiled ? [...VB.compiled.runtime.procs.values()].filter((p) => p.kind === "FUNCTION").length : 0}개`;
  }
  function vbaApply() {
    const cur = VB.draft[VB.sel]; if (cur) cur.code = $("#vbaCode").value;
    const before = JSON.stringify(VB.mods), after = JSON.stringify(VB.draft);
    if (before === after) { toast("바뀐 코드가 없습니다"); return; }
    VB.mods = VB.draft.map((m) => ({ ...m }));
    mutate(() => {
      S.deck.macros = { ...(S.deck.macros || {}), modules: VB.mods.map((m) => ({ ...m })) }; compileVba();
      // 계산할 수 있게 된 VBA 함수를 쓰는 칸만 저장값을 지우고 다시 계산(못 쓰는 문법 함수 칸은 엑셀 값을 지키게 그대로)
      const fns = VB.compiled ? [...VB.compiled.runtime.procs.values()].filter((p) => p.kind === "FUNCTION" && !p.unsupported && VB.compiled.has(p.name)).map((p) => p.name) : [];
      const re = fns.length ? new RegExp(`(^|[^\\p{L}\\p{N}_.])(${fns.map((f) => f.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\s*\\(`, "iu") : null;
      if (re) for (const t of S.deck.sheets) for (const c of Object.values(t.cells)) if (c && typeof c === "object" && c.f && re.test(c.f)) delete c.v;
      recalc();
    });
    const n = VB.compiled ? VB.compiled.errors.length : 0;
    toast(n ? `적용했습니다 - 계산하지 못하는 곳 ${n}개(코드 창 아래)` : "적용하고 다시 계산했습니다", 3500);
    vbaRender();
  }
  async function reloadExternal(msg) {
    const was = { ti: S.deck && sheet().id, sel: { ...S.sel }, cur: { ...S.cur }, anchor: { ...S.anchor } };
    if (!(await loadDeck(true))) return;
    const i = S.deck.sheets.findIndex((s) => s.id === was.ti); S.ti = i >= 0 ? i : 0;
    S.sel = was.sel; S.cur = was.cur; S.anchor = was.anchor;
    renderAll(); if (msg && !(AI.at && Date.now() - AI.at < 5000)) toast(msg);  // 방금 AI 변경 알림을 띄웠으면 그것을 덮지 않는다
  }
  // 갱신 - 실시간 연결(nexa-live.js SSE, 동시 편집 2단계)이 살아 있으면 바뀔 때마다 applyVersion 이 바로 불리고, 2초 폴링은 15초 안전망만(편집기와 같다)
  let LIVE = null, pollAt = 0, applying = false, pendingV = null;
  async function poll() {
    if (!S.deck) return;
    if (LIVE && LIVE.healthy() && Date.now() - pollAt < 15000) return;
    pollAt = Date.now();
    try {
      const r = await api("GET", `/api/version/${encodeURIComponent(S.id)}`);
      if (!r.ok) return;
      await applyVersion(r.data);
    } catch (e) { setStatus("error", "서버 끊김"); }
  }
  async function applyVersion(v) {
    if (!S.deck) return;
    if (applying) { pendingV = v; return; }
    applying = true;
    try {
      if (v.session) renderSession(v.session, v.activity);
      if (v.engine) {  // 편집기 코드·템플릿(엔진)이 바뀌면 새로 고침 안내(편집기 checkWorkspace 와 같다)
        if (S.engine == null) S.engine = v.engine;
        else if (v.engine !== S.engine) { S.engine = v.engine; $("#engReload").textContent = S.dirty ? "저장하고 새로 고침" : "새로 고침"; $("#engNotice").classList.add("show"); }
      }
      if (RQ) await RQ.sync(v);  // 요청 파일이 바뀌었으면 다시 읽기(편집기와 같다)
      if (window.NexaSheetSide) NexaSheetSide.onVersion(v);  // 변경 원장이 바뀌었으면 변경 탭·표시 갱신
      if (v.deck !== S.version && !S.saving) {
        // 편집 중에 밖에서 바뀌었다 - 배너로 고르게 하지 않고, 내 저장이 서버에서 합쳐지게 바로 저장한다(셀 입력 중이면 입력을 넣고 저장할 때)
        if (S.dirty || S.edit) { if (S.dirty && !S.edit && !S.conflict) { clearTimeout(saveT); await save(); } }
        else await reloadExternal("밖에서 바뀐 시트를 다시 불러왔습니다");
      }
    } finally {
      applying = false;
      if (pendingV) { const n = pendingV; pendingV = null; await applyVersion(n); }
    }
  }
  /** 함께 보는 사람에게 내 위치 - 탭·고른 범위·셀 입력 중(바뀔 때만 보낸다) */
  function livePresence() { if (LIVE && S.deck) LIVE.where({ tab: sheet().id, range: rangeName(clampRange(S.sel)) }, !!S.edit); }
  // 세션 칩·웹 AI 세션 - wsession.js(NexaSession, 슬라이드 편집기와 같다)
  let SESS = null;
  function renderSession(st, act) { if (SESS) SESS.render(st, act); else S.session = st; }
  /** 세션이 요청을 처리하는 중 - 세션이 시트 파일을 고칠 수 있으므로 화면의 자동 저장(계산값 채우기)을 미룬다 */
  const reqBusy = () => S.reqs.some((q) => q.status === "working") || !!(SESS && SESS.busy());

  // ---------------------------------------------------------------- 테마(docs/sheets.md 5절) - 셀 s(스타일 이름)를 테마 styles 에서 찾아 셀 키 아래에 깔고(셀 키가 이긴다),
  // 색 값이 팔레트 이름이면 #RRGGBB 로 바꾼다. 내보내기(export_xlsx.py)와 같은 규칙
  const TH = { name: null, theme: null, brandLogo: null };
  const theme = () => TH.theme;
  async function loadTheme(name) {
    if ((name || null) === TH.name) return;
    TH.name = name || null; TH.theme = null;
    if (!name) return;
    const r = await api("GET", `/api/sheet-themes/${encodeURIComponent(name)}`);
    if (r.ok && r.data && typeof r.data === "object" && !Array.isArray(r.data)) TH.theme = r.data;
    else toast(`시트 테마 "${name}" 를 읽지 못했습니다 - 테마 없이 보입니다`, 5000);
  }
  const styleOf = (s) => (s && theme() && theme().styles && theme().styles[s]) || null;
  const palColor = (c) => { if (typeof c !== "string") return c; const p = theme() && theme().palette; return p && p[c] ? p[c] : c; };
  const LINE_DEF = "#BFBFBF";  // 팔레트에 line 이 없을 때 테두리 색
  function bdColor(v) { if (v === true) v = "line"; if (typeof v !== "string" || !v) return null; const c = palColor(v); return /^#[0-9a-f]{3,8}$/i.test(c) ? c : LINE_DEF; }
  /** 테두리 값 → {t, r, b, l} 색. "line"·"#hex" = 네 변, {t,r,b,l} = 변마다(없는 변은 선 없음) */
  function bdSides(bd) {
    if (bd == null || bd === false) return {};
    if (typeof bd === "object") { const o = {}; for (const s of ["t", "r", "b", "l"]) { const c = bdColor(bd[s]); if (c) o[s] = c; } return o; }
    const c = bdColor(bd); return c ? { t: c, r: c, b: c, l: c } : {};
  }
  /** 화면에 그릴 셀 - 스타일(s) 위에 셀 키, 글자색·배경의 팔레트 이름 → 색 */
  function effCell(raw) {
    const o = raw == null ? {} : typeof raw === "object" ? raw : { v: raw };
    const st = styleOf(o.s), e = st ? { ...st, ...o } : { ...o };
    if (e.color) e.color = palColor(e.color);
    if (e.fill) e.fill = palColor(e.fill);
    return e;
  }
  function renderThemeChip() {
    const c = $("#themeChip"); if (!c) return;
    c.textContent = TH.name ? `테마 ${(theme() && theme().label) || TH.name}` : "테마 없음";
    c.title = TH.name ? `시트 테마 ${TH.name}${theme() ? "" : " (읽지 못함)"} - 눌러서 바꾸기` : "시트 테마 고르기 - 셀 스타일·색·글꼴·페이지 틀";
  }
  async function themeMenu(btn) {
    const r = await api("GET", "/api/sheet-themes"), list = r.ok && Array.isArray(r.data) ? r.data : [];
    openMenu(btn, [{ h: "시트 테마 - 셀 스타일(s)·색·글꼴" }, { label: "테마 없음", on: !TH.name, act: () => setTheme(null) },
      ...list.map((t) => ({ label: `${t.label || t.name}${t.source === "workspace" ? " · 작업 공간" : ""}`, on: t.name === TH.name, act: () => setTheme(t.name) })),
      ...(list.length ? [] : [{ label: "(테마 목록을 읽지 못했습니다)", disabled: true }])]);
  }
  async function setTheme(name) {
    if (S.edit) endEdit(true);
    if ((name || null) === TH.name) return;
    snapshot(); await loadTheme(name);
    if (name) S.deck.theme = name; else delete S.deck.theme;
    renderThemeChip(); afterChange();
  }
  const defSize = () => (theme() && +theme().size) || 11;
  /** 눈금선 - 탭 grid 가 있으면 그것, 없으면 테마 grid(기본 보임) */
  const gridOn = (sh) => (sh.grid !== undefined ? sh.grid !== false : !(theme() && theme().grid === false));
  /** 그림 주소 - "@brand/logo" = 작업 공간 brand 로고, "assets/…" = 작업 공간, 그 밖의 상대 경로 = 테마 폴더(base) */
  function assetUrl(src) {
    const pre = (u) => (u && u[0] === "/" ? BASE + u : u || "");
    if (!src) return "";
    if (src === "@brand/logo") return pre((theme() && theme().brandLogo) || TH.brandLogo);
    if (/^(https?:|data:)/.test(src)) return src;
    if (src[0] === "/") return BASE + src;
    if (src.startsWith("assets/")) return BASE + "/" + src;
    const b = theme() && theme().base; return b ? pre(b) + src : BASE + "/" + src;
  }
  /** 문서 정보 - 테마 페이지의 {{자리}} 를 채우는 값(문서 vars > 테마 vars, title·date 는 문서 제목·오늘) */
  function docVars() {
    const d = new Date(), today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    return { ...((theme() && theme().vars) || {}), ...(S.deck.vars || {}), title: (S.deck.vars && S.deck.vars.title) || S.deck.title || "", date: (S.deck.vars && S.deck.vars.date) || today };
  }
  function fillVars(x, vars) {
    if (typeof x === "string") return x.replace(/\{\{\s*([\w.-]+)\s*\}\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
    if (Array.isArray(x)) return x.map((y) => fillVars(y, vars));
    if (x && typeof x === "object") { const o = {}; for (const [k, v] of Object.entries(x)) o[k] = fillVars(v, vars); return o; }
    return x;
  }

  // ---------------------------------------------------------------- 그리기
  const G = { colX: [], rowY: [], rows: 0, cols: 0 };
  function renderAll() { renderGrid(); renderTabs(); renderSel(); renderReqs(); if (window.NexaSheetSide) NexaSheetSide.onRender(); }
  function cellStyle(o, isNum) {
    const st = [];
    if (o.fill) st.push(`background:${o.fill}`);
    const cv = [];
    if (o.color) cv.push(`color:${o.color}`);
    if (o.b) cv.push("font-weight:700");
    if (o.i) cv.push("font-style:italic");
    if (o.u || o.strike) cv.push(`text-decoration:${[o.u ? "underline" : "", o.strike ? "line-through" : ""].filter(Boolean).join(" ")}`);
    if (o.size) cv.push(`font-size:${+o.size}pt`);
    const al = o.align || (isNum === "num" ? "right" : isNum === "mid" ? "center" : "left");
    cv.push(`justify-content:${al === "right" ? "flex-end" : al === "center" ? "center" : "flex-start"}`, `text-align:${al}`);
    cv.push(`align-items:${o.valign === "top" ? "flex-start" : o.valign === "middle" ? "center" : "flex-end"}`);
    return [st.join(";"), cv.join(";")];
  }
  // 가상 스크롤 - 행이 VIRT 개를 넘으면 보이는 행 ± VBUF 만 그린다(5,000행에서 고칠 때마다 13만 칸을 다시 그리던 것). 범위에 걸친 병합은 끝까지 넓힌다
  const VIRT = 300, VBUF = 40;
  // 확대·축소(엑셀 아래 확대 막대 · Ctrl+휠) - #gridIn 에 CSS zoom. 격자 좌표(G.colX·rowY·offsetLeft)는 확대 전 px, 스크롤·마우스 이동은 화면 px 라 Z 로 나눈다
  let Z = 1;
  const sx = () => $("#gridWrap").scrollLeft / Z, sy = () => $("#gridWrap").scrollTop / Z;
  function setZoom(z, keepAt) {
    z = Math.round(Math.max(0.25, Math.min(4, z)) * 100) / 100; if (z === Z) return;
    const W = $("#gridWrap"), cx = keepAt ? keepAt[0] : W.clientWidth / 2, cy = keepAt ? keepAt[1] : W.clientHeight / 2;
    const gx = (W.scrollLeft + cx) / Z, gy = (W.scrollTop + cy) / Z;  // 이 격자 점을 같은 자리에
    Z = z; $("#gridIn").style.zoom = String(z);
    W.scrollLeft = gx * Z - cx; W.scrollTop = gy * Z - cy;
    LS.set(`sheetZoom-${S.id}`, String(z)); renderZoom();
    if (G.rows > VIRT) renderGrid(); renderSel();
  }
  function renderZoom() { const b = $("#zoomPct"); if (b) b.textContent = Math.round(Z * 100) + "%"; }
  function rowAt(y) { let lo = 0, hi = G.rows - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (G.rowY[m] <= y) lo = m; else hi = m - 1; } return lo; }
  function rowWindow(sh, rows, fz, ms) {
    if (rows <= VIRT) return [0, rows - 1];
    const W = $("#gridWrap"), top = W ? W.scrollTop / Z : 0, hgt = ((W && W.clientHeight) || 800) / Z;
    let r0 = Math.max(fz.r, rowAt(top) - VBUF), r1 = Math.min(rows - 1, rowAt(top + hgt) + VBUF);
    for (let changed = true; changed;) {
      changed = false;
      for (const m of ms) { if (m.r1 < r0 && m.r2 >= r0 && m.r1 >= fz.r) { r0 = m.r1; changed = true; } if (m.r1 <= r1 && m.r2 > r1) { r1 = m.r2; changed = true; } }
    }
    return [r0, r1];
  }
  let vRaf = 0;
  function onGridScroll() {  // 그린 범위 끝에 가까워지면 다시 그린다
    if (S.deck && sheet().freeze) placeSel();  // 틀 고정 - 고정 칸 쪽 선택 표시가 따라오고 스크롤 쪽은 고정 칸 밑으로
    if (G.rows <= VIRT || vRaf) return;
    vRaf = requestAnimationFrame(() => {
      vRaf = 0;
      const W = $("#gridWrap"), a = rowAt(W.scrollTop / Z), b = rowAt((W.scrollTop + W.clientHeight) / Z), [r0, r1] = G.win || [0, 0];
      if ((a < r0 + 10 && r0 > 0) || (b > r1 - 10 && r1 < G.rows - 1)) { renderGrid(); renderSel(); }
    });
  }
  function renderGrid() {
    const sh = sheet(), { rows, cols } = dims(sh); G.rows = rows; G.cols = cols;
    G.colX = [HW]; for (let c = 0; c < cols; c++) G.colX.push(G.colX[c] + colW(sh, c));
    G.rowY = [HH]; for (let r = 0; r < rows; r++) G.rowY.push(G.rowY[r] + rowH(sh, r));
    const fz = parseRef(sh.freeze || "") || { r: 0, c: 0 };
    const fg = sh.filter && sh.filter.cols && Object.keys(sh.filter.cols).length ? parseRange(sh.filter.ref) : null;
    const ms = merges(sh), cover = new Map();
    for (const m of ms) for (let r = m.r1; r <= m.r2; r++) for (let c = m.c1; c <= m.c2; c++) cover.set(r * 4096 + c, r === m.r1 && c === m.c1 ? m : "x");
    // 테두리(bd) - 칸 사이 선은 한 줄만: 아래·오른쪽 변은 그 칸의 border 색, 위·왼쪽 변은 위·왼쪽 칸의 아래·오른쪽 border 색. 1행·A열의 위·왼쪽만 안쪽 그림자
    const eB = new Map(), eR = new Map(), eT = new Map(), eL = new Map();
    for (const [k, raw] of Object.entries(sh.cells)) {
      const p = parseRef(k); if (!p) continue;
      const cm0 = cover.get(p.r * 4096 + p.c); if (cm0 === "x") continue;
      const e = effCell(raw); if (!e.bd) continue;
      const sd = bdSides(e.bd), g = cm0 || { r1: p.r, c1: p.c, r2: p.r, c2: p.c };
      for (let c = g.c1; c <= g.c2; c++) { if (sd.b) eB.set(g.r2 * 4096 + c, sd.b); if (sd.t) { if (g.r1 > 0) { if (!eB.has((g.r1 - 1) * 4096 + c)) eB.set((g.r1 - 1) * 4096 + c, sd.t); } else eT.set(c, sd.t); } }
      for (let r = g.r1; r <= g.r2; r++) { if (sd.r) eR.set(r * 4096 + g.c2, sd.r); if (sd.l) { if (g.c1 > 0) { if (!eR.has(r * 4096 + g.c1 - 1)) eR.set(r * 4096 + g.c1 - 1, sd.l); } else eL.set(r, sd.l); } }
    }
    const T = theme(), grid = $("#grid");
    grid.classList.toggle("nogrid", !gridOn(sh));
    grid.style.width = G.colX[cols] + "px";  // 표 너비가 auto 면 table-layout: fixed 가 무시돼 긴 글이 열을 넓힌다 - 선택 상자(G.colX)와 칸이 어긋남
    grid.style.fontFamily = T && T.font ? `"${String(T.font).replace(/"/g, "")}", var(--font)` : "";
    grid.style.fontSize = T && T.size ? `${+T.size}pt` : "";
    const h = [`<colgroup><col style="width:${HW}px">`];
    for (let c = 0; c < cols; c++) if (!colHidden(sh, c)) h.push(`<col style="width:${colW(sh, c)}px">`);
    h.push(`</colgroup><thead><tr><th class="corner" title="모두 선택 (Ctrl+A)"></th>`);
    for (let c = 0; c < cols; c++) if (!colHidden(sh, c)) h.push(`<th data-col="${c}"${colHidden(sh, c + 1) || (c > 0 && colHidden(sh, c - 1)) ? ' class="hidN" title="옆에 숨긴 열이 있습니다 - 오른쪽 클릭 → 숨기기 취소"' : ""}>${colName(c)}<span class="rz" data-rzc="${c}"></span></th>`);
    h.push("</tr></thead><tbody>");
    const visN = (a, b, hid) => { let n = 0; for (let i = a; i <= b; i++) if (!hid(sh, i)) n++; return n; };
    const CF = window.NexaSheetX && NexaSheetX.condMap ? NexaSheetX.condMap(sh) : null;  // 조건부 서식(sheetx.js) - 칸 → 덧씌울 서식
    const [r0, r1] = G.win = rowWindow(sh, rows, fz, ms), nVis = visN(0, cols - 1, colHidden) + 1;
    const spacer = (a, b) => (G.rowY[b] > G.rowY[a] ? `<tr class="vsp" aria-hidden="true"><td colspan="${nVis}" style="height:${G.rowY[b] - G.rowY[a]}px"></td></tr>` : "");
    for (let r = 0; r < rows; r++) {
      if (r >= fz.r && (r < r0 || r > r1)) {  // 가상 스크롤 - 보이는 범위 밖은 높이만(틀 고정 행은 늘 그린다)
        if (r === Math.max(fz.r, 0) && r < r0) { h.push(spacer(r, r0)); r = r0 - 1; continue; }
        if (r === r1 + 1) { h.push(spacer(r, rows)); break; }
        continue;
      }
      if (rowHidden(sh, r)) continue;
      const rh = rowH(sh, r);
      const thc = [rowHidden(sh, r + 1) || (r > 0 && rowHidden(sh, r - 1)) ? "hidN" : "", fg && r > fg.r1 && r <= fg.r2 ? "flr" : ""].filter(Boolean).join(" ");  // flr - 조건이 걸린 필터의 데이터 행(엑셀은 행 번호가 파랗다)
      h.push(`<tr style="height:${rh}px"><th data-row="${r}"${thc ? ` class="${thc}"` : ""}>${r + 1}<span class="rz" data-rzr="${r}"></span></th>`);
      for (let c = 0; c < cols; c++) {
        if (colHidden(sh, c)) continue;
        const cm = cover.get(r * 4096 + c); if (cm === "x") continue;
        const k = key(r, c), raw = sh.cells[k];
        let o = effCell(raw);
        if (CF && CF.has(r * 4096 + c)) o = { ...o, ...CF.get(r * 4096 + c) };
        const txt = display(o), err = o.f && isErrStr(o.v);
        const kind = typeof o.v === "number" ? "num" : typeof o.v === "boolean" || err ? "mid" : "txt";
        const [tdS, cvS] = cellStyle(o, kind);
        let span = "", hh = rh;
        if (cm) { span = ` rowspan="${visN(cm.r1, cm.r2, rowHidden)}" colspan="${visN(cm.c1, cm.c2, colHidden)}"`; hh = G.rowY[cm.r2 + 1] - G.rowY[cm.r1]; }
        const cls = [], extra = [];
        if (r < fz.r || c < fz.c) { cls.push("fz"); extra.push(r < fz.r ? `top:${G.rowY[r]}px` : "", c < fz.c ? `left:${G.colX[c]}px` : ""); if (r < fz.r && c < fz.c) extra.push("z-index:2"); }
        if (fz.r && r === fz.r - 1) cls.push("fzr"); if (fz.c && c === fz.c - 1) cls.push("fzc");
        if (err) cls.push("err");
        if (o.note) cls.push("nt");  // 메모 - 오른쪽 위 빨간 삼각형(엑셀과 같다)
        const hl = o.f && !err && HL_RE.test(o.f);
        {  // 테두리
          const r2 = cm ? cm.r2 : r, c2 = cm ? cm.c2 : c, bb = eB.get(r2 * 4096 + c), br = eR.get(r * 4096 + c2), sh2 = [];
          if (bb) extra.push(`border-bottom-color:${bb}`); if (br) extra.push(`border-right-color:${br}`);
          if (r === 0 && eT.get(c)) sh2.push(`inset 0 1px 0 ${eT.get(c)}`); if (c === 0 && eL.get(r)) sh2.push(`inset 1px 0 0 ${eL.get(r)}`);
          if (sh2.length) extra.push(`box-shadow:${sh2.join(",")}`);
        }
        h.push(`<td data-r="${r}" data-c="${c}"${span}${cls.length ? ` class="${cls.join(" ")}"` : ""} style="${[tdS, ...extra.filter(Boolean)].filter(Boolean).join(";")}"${o.note ? ` title="${esc(o.note)}"` : err && ERR_WHY[o.v] ? ` title="${esc(o.v + " - " + ERR_WHY[o.v])}"` : hl ? ' title="Ctrl+클릭 = 링크로 이동"' : ""}>`
          + `<div class="cv${o.wrap ? " wrap" : ""}" style="height:${hh - 1}px;${cvS}"><span>${esc(txt)}</span></div></td>`);
      }
      h.push("</tr>");
    }
    h.push("</tbody>");
    $("#grid").innerHTML = h.join("");
    renderMarks(); renderDrawings();
  }
  /** 그림 id - drawings[].id, 없으면 파일 이름(가져온 그림 d02-01.png → d02-01), 그것도 없으면 순번(img3). 요청 대상(elements)에 쓴다 */
  const drawId = (d, i) => String(d.id || (String(d.src || "").split("/").pop() || "").replace(/\.[^.]+$/, "") || "img" + (i + 1));
  /** 고른 그림(이 탭) - 누르면 하나, Ctrl·Shift 로 더하기·빼기. 칸을 누르면 풀린다 */
  function drawPick(id, add) {
    const cur = S.drawSel || new Set();
    if (add) { if (cur.has(id)) cur.delete(id); else cur.add(id); S.drawSel = cur; } else S.drawSel = new Set([id]);
    if (!S.drawSel.size) S.drawSel = null;
    markDrawings(); renderReqTarget();
  }
  function markDrawings() {
    $$("#draws img.drw").forEach((im) => im.classList.toggle("on", !!(S.drawSel && S.drawSel.has(im.dataset.did))));
    let hd = $("#drawHandle"); if (!hd) { hd = document.createElement("div"); hd.id = "drawHandle"; hd.title = "끌어서 크기(Shift = 비율 그대로)"; $("#gridIn").appendChild(hd); }
    const one = S.drawSel && S.drawSel.size === 1 ? $(`#draws img.drw[data-did="${CSS.escape([...S.drawSel][0])}"]`) : null;
    hd.hidden = !one; if (one) { hd.style.left = one.offsetLeft + one.offsetWidth - 4 + "px"; hd.style.top = one.offsetTop + one.offsetHeight - 4 + "px"; }
    if (window.NexaSheetSide) NexaSheetSide.onSel();
  }
  const drawIdx = (sh) => (sh.drawings || []).map((d, i) => [drawId(d, i), i]);
  /** 그림 끌기 - move: 고른 그림 모두 옮김(놓은 자리의 칸 + 남는 px 로 at·dx·dy) · size: 하나의 w·h */
  function startDrawDrag(e, mode) {
    const sh = sheet(), x0 = e.clientX, y0 = e.clientY, ids = new Set(S.drawSel || []), imgs = $$("#draws img.drw").filter((im) => ids.has(im.dataset.did));
    const start = imgs.map((im) => ({ im, l: im.offsetLeft, t: im.offsetTop, w: im.offsetWidth, h: im.offsetHeight }));
    let moved = false;
    const onMove = (ev) => {
      const dx = (ev.clientX - x0) / Z, dy = (ev.clientY - y0) / Z; if (!moved && Math.abs(dx) + Math.abs(dy) < 4) return; moved = true;
      for (const st of start) {
        if (mode === "move") { st.im.style.left = Math.max(HW, st.l + dx) + "px"; st.im.style.top = Math.max(HH, st.t + dy) + "px"; }
        else { let w = Math.max(8, st.w + dx), h = Math.max(8, st.h + dy); if (ev.shiftKey) { const k = Math.max(w / st.w, h / st.h); w = st.w * k; h = st.h * k; } st.im.style.width = Math.round(w) + "px"; st.im.style.height = Math.round(h) + "px"; }
      }
      markDrawings();
    };
    const onUp = () => {
      removeEventListener("mousemove", onMove); removeEventListener("mouseup", onUp);
      if (!moved) return;
      const at = (px, axis) => { const A = axis === "c" ? G.colX : G.rowY; let i = 0; while (i + 1 < A.length - 1 && A[i + 1] <= px) i++; return [i, px - A[i]]; };
      mutate(() => {
        const idx = new Map(drawIdx(sh));
        for (const st of start) {
          const d = sh.drawings[idx.get(st.im.dataset.did)]; if (!d) continue;
          if (!d.id) d.id = st.im.dataset.did;  // 고친 그림은 id 를 남긴다(요청 대상이 그대로이게)
          if (mode === "move") { const [c, dx] = at(st.im.offsetLeft, "c"), [r, dy] = at(st.im.offsetTop, "r"); d.at = key(r, c); d.dx = Math.round(dx); d.dy = Math.round(dy); }
          else { d.w = st.im.offsetWidth; d.h = st.im.offsetHeight; }
        }
      });
    };
    addEventListener("mousemove", onMove); addEventListener("mouseup", onUp);
  }
  function drawDelete() {
    const ids = new Set(S.drawSel || []); if (!ids.size) return;
    mutate(() => { const sh = sheet(); sh.drawings = (sh.drawings || []).filter((d, i) => !ids.has(drawId(d, i))); if (!sh.drawings.length) delete sh.drawings; });
    S.drawSel = null; markDrawings(); renderReqTarget(); toast(`그림 ${ids.size}개를 지웠습니다 (Ctrl+Z 로 되돌리기)`);
  }
  /** 탭 그림(drawings) - 셀 at 의 왼쪽 위 + (dx, dy)px 에 w×h. 격자와 같이 움직이고, 누르면 그림 고르기(onGridDown) */
  function renderDrawings() {
    const sh = sheet(), out = [];
    for (const [i, d] of (sh.drawings || []).entries()) {
      if (d.type && d.type !== "image") continue;
      const p = parseRef(d.at || "A1"); if (!p) continue;
      const x = (G.colX[Math.min(p.c, G.colX.length - 1)] || HW) + (+d.dx || 0), y = (G.rowY[Math.min(p.r, G.rowY.length - 1)] || HH) + (+d.dy || 0);
      const src = assetUrl(d.src); if (!src) continue;
      const id = drawId(d, i);
      out.push(`<img class="drw" data-did="${esc(id)}" src="${esc(src)}" alt="${esc(d.alt || id)}" title="그림 ${esc(id)} - 누르면 고르기(Ctrl·Shift = 여럿) · 요청 대상" draggable="false" style="left:${x}px;top:${y}px;width:${+d.w || 120}px;height:${+d.h || 60}px">`);
    }
    const box = $("#draws"); box.innerHTML = out.join("");
    if (S.drawSel) { const have = new Set((sh.drawings || []).map(drawId)); for (const id of [...S.drawSel]) if (!have.has(id)) S.drawSel.delete(id); if (!S.drawSel.size) S.drawSel = null; }
    markDrawings();
    $$("img", box).forEach((i) => { i.onerror = () => { i.style.visibility = "hidden"; }; });
  }
  function rectOf(g) { return { x: G.colX[g.c1], y: G.rowY[g.r1], w: G.colX[g.c2 + 1] - G.colX[g.c1], h: G.rowY[g.r2 + 1] - G.rowY[g.r1] }; }
  function place(el, g, inset = 0) { const R = rectOf(g); Object.assign(el.style, { left: R.x - inset + "px", top: R.y - inset + "px", width: R.w + inset * 2 + 1 + "px", height: R.h + inset * 2 + 1 + "px" }); }
  // 틀 고정 - 고정 행·열 칸(sticky)은 스크롤만큼 따라 움직인다. 선택 표시를 고정·스크롤 사분면으로 나눠 고정 쪽은 같이 옮기고, 스크롤 쪽은 고정 칸 밑으로 가린다(엑셀과 같다)
  const frz = () => parseRef(sheet().freeze || "") || { r: 0, c: 0 };
  function paneOf(r, c) {  // 그 칸이 있는 사분면의 이동량(dx·dy)과 가림 선(cx·cy, 내용 좌표 - 이보다 왼쪽·위는 고정 칸이 덮는다)
    const fz = frz(), W = $("#gridWrap");
    if (!fz.r && !fz.c) return { dx: 0, dy: 0, cx: null, cy: null };
    const fr = r < fz.r, fc = c < fz.c;
    return { dx: fc ? sx() : 0, dy: fr ? sy() : 0, cx: fc ? null : sx() + G.colX[fz.c], cy: fr ? null : sy() + G.rowY[fz.r] };
  }
  function placeQ(el, g, inset = 0) {
    const fz = frz(), parts = [];
    if (!el.hidden) for (const [r1, r2] of [[g.r1, Math.min(g.r2, fz.r - 1)], [Math.max(g.r1, fz.r), g.r2]]) for (const [c1, c2] of [[g.c1, Math.min(g.c2, fz.c - 1)], [Math.max(g.c1, fz.c), g.c2]]) if (r1 <= r2 && c1 <= c2) parts.push({ r1, c1, r2, c2 });
    const extra = [...el.parentNode.querySelectorAll(`.q-${el.id}`)];
    parts.forEach((q, i) => {
      let e = el;
      if (i) { e = extra[i - 1]; if (!e) { e = document.createElement("div"); e.className = `ov q-${el.id}`; (extra[extra.length - 1] || el).after(e); extra.push(e); } e.hidden = false; }
      const R = rectOf(q), p = paneOf(q.r1, q.c1), x = R.x - inset + p.dx, y = R.y - inset + p.dy, w = R.w + inset * 2 + 1, h = R.h + inset * 2 + 1;
      const t = p.cy == null ? 0 : Math.max(0, p.cy - y), l = p.cx == null ? 0 : Math.max(0, p.cx - x);
      Object.assign(e.style, { left: x + "px", top: y + "px", width: w + "px", height: h + "px", clipPath: t || l ? `inset(${t}px 0 0 ${l}px)` : "", visibility: t >= h || l >= w ? "hidden" : "",
        borderTopStyle: q.r1 > g.r1 ? "none" : "", borderLeftStyle: q.c1 > g.c1 ? "none" : "", borderBottomStyle: q.r2 < g.r2 ? "none" : "", borderRightStyle: q.c2 < g.c2 ? "none" : "" });  // 사분면 사이 경계선은 안 그린다
    });
    extra.slice(Math.max(0, parts.length - 1)).forEach((e) => { e.hidden = true; });
  }
  function placeSel() {
    const sh = sheet(), g = clampRange(S.sel), cm = mergeAt(sh, S.cur.r, S.cur.c) || { r1: S.cur.r, c1: S.cur.c, r2: S.cur.r, c2: S.cur.c };
    $("#selBox").hidden = g.r1 === g.r2 && g.c1 === g.c2 || rangeName(g) === rangeName(cm); placeQ($("#selBox"), g);
    placeQ($("#curBox"), cm, 1);
    {  // 채우기 핸들 - 선택 범위 오른쪽 아래, 고정 칸에 덮이면 감춘다
      const R = rectOf(g), H = $("#fillHandle"), p = paneOf(g.r2, g.c2), x = R.x + R.w - 3 + p.dx, y = R.y + R.h - 3 + p.dy;
      H.style.left = x + "px"; H.style.top = y + "px"; H.hidden = !!S.edit || (p.cx != null && x < p.cx) || (p.cy != null && y < p.cy);
    }
    const cb = $("#clipBox"); cb.hidden = !(S.clip && S.clip.ti === sh.id && S.clip.show); placeQ(cb, cb.hidden ? g : S.clip.g);
    if (window.NexaSheetSide) NexaSheetSide.onPlace();  // 변경 표시(sheetside.js) - 선택 표시와 같은 좌표·틀 고정 규칙
  }
  function renderSel() {
    const sh = sheet(), g = clampRange(S.sel);
    placeSel();
    $$("#grid th.on").forEach((t) => t.classList.remove("on"));
    for (let c = g.c1; c <= g.c2; c++) { const t = $(`#grid th[data-col="${c}"]`); if (t) t.classList.add("on"); }
    for (let r = g.r1; r <= g.r2; r++) { const t = $(`#grid th[data-row="${r}"]`); if (t) t.classList.add("on"); }
    $("#nameBox").value = rangeName(g);
    if (document.activeElement !== $("#fxIn")) $("#fxIn").value = rawText(sh, key(S.cur.r, S.cur.c));
    if (!S.edit) placeEditor();
    renderToolState(); renderReqTarget();
    if (window.NexaSheetX) NexaSheetX.onSel();  // 엑셀 기능(sheetx.js) - 상태 표시줄 합계 등
    if (window.NexaSheetSide) NexaSheetSide.onSel();  // 패널 속성 탭(sheetside.js)
    clearTimeout(renderSel.t); renderSel.t = setTimeout(() => history.replaceState(null, "", `#${encodeURIComponent(sh.id)}!${rangeName(g)}`), 300);  // 새로 고쳐도 같은 탭·범위
  }
  function clampRange(g) { return { r1: Math.max(0, Math.min(g.r1, G.rows - 1)), c1: Math.max(0, Math.min(g.c1, G.cols - 1)), r2: Math.max(0, Math.min(g.r2, G.rows - 1)), c2: Math.max(0, Math.min(g.c2, G.cols - 1)) }; }
  function renderTabs() {
    const cnt = (sid) => activeReqs().filter((q) => reqSlide(q) === sid).length;
    $("#tabs").innerHTML = S.deck.sheets.map((s, i) => `<button class="t${i === S.ti ? " on" : ""}${s.hidden ? " hid" : ""}" data-ti="${i}" title="${esc(s.name)} · id ${esc(s.id)}${s.hidden ? " · 엑셀에서 숨긴 시트" : ""} - 두 번 클릭: 이름 바꾸기 · 오른쪽 클릭: 메뉴">${esc(s.name)}${cnt(s.id) ? `<span class="n">${cnt(s.id)}</span>` : ""}</button>`).join("")
      + `<button class="ib add" data-addtab="1" title="${theme() && (theme().pages || []).length ? "새 탭 · 테마 페이지 추가" : "새 탭"}">＋</button>`;
  }
  function renderToolState() {
    const sh = sheet(), own = cellObj(sh, key(S.cur.r, S.cur.c)), o = effCell(own);
    for (const t of ["b", "i", "u"]) $(`#tools [data-t="${t}"]`).classList.toggle("on", !!o[t]);
    $$('#tools [data-t="al"]').forEach((b) => b.classList.toggle("on", o.align === b.dataset.v));
    $('#tools [data-t="wrap"]').classList.toggle("on", !!o.wrap);
    $('#tools [data-t="merge"]').classList.toggle("on", !!mergeAt(sh, S.cur.r, S.cur.c));
    $('#tools [data-t="freeze"]').classList.toggle("on", !!sh.freeze);
    $("#colorBar").style.background = o.color || "#000"; $("#fillBar").style.background = o.fill || "#fff";
    fillFmtSel(o.fmt || ""); $("#sizeSel").value = String(o.size || defSize());
    $('#tools [data-t="grid"]').classList.toggle("on", gridOn(sh));
    $('#tools [data-t="border"]').classList.toggle("on", !!o.bd && Object.keys(bdSides(o.bd)).length > 0);
    const ss = $("#styleSel"), names = Object.keys((theme() && theme().styles) || {});
    ss.hidden = !names.length; $("#styleSep").hidden = !names.length;
    if (names.length) {
      const opts = ["", ...names, ...(own.s && !names.includes(own.s) ? [own.s] : [])];
      const html = opts.map((n) => `<option value="${esc(n)}">${n ? esc(n) : "스타일 없음"}</option>`).join("");
      if (ss.dataset.h !== html) { ss.innerHTML = html; ss.dataset.h = html; }
      ss.value = own.s || "";
    }
  }
  const FMTS = [["", "일반"], ["#,##0", "#,##0 (천 단위)"], ["#,##0.00", "#,##0.00"], ["0.0", "0.0"], ["0%", "0%"], ["0.0%", "0.0%"], ["yyyy-mm-dd", "날짜 yyyy-mm-dd"], ["@", "텍스트"]];
  /** 표시 형식 빠른 단추 - pct·comma·inc(자릿수 늘림)·dec(줄임). 날짜·글 형식 칸은 건너뛴다(엑셀과 같다) */
  function bumpFmt(f, how) {
    if (/[ymdhs]/i.test(f.replace(/"[^"]*"/g, "")) || f === "@") return f;
    if (how === "pct") return "0%";
    if (how === "comma") return "#,##0" + ((/\.(0+)/.exec(f) || [])[0] || "");
    const base = f || "0", m = /^([^.;%]*)(\.(0+))?(%?)(.*)$/.exec(base.split(";")[0]);
    if (!m) return f;
    const dec = (m[3] || "").length, n = Math.max(0, dec + (how === "inc" ? 1 : -1));
    return (m[1] || "0") + (n ? "." + "0".repeat(n) : "") + m[4] + m[5];
  }
  function numFmt(how) {
    const sh = sheet(), first = effCell(sh.cells[key(S.cur.r, S.cur.c)]);
    let start = first.fmt || "";
    if (!start && (how === "inc" || how === "dec")) {  // 일반 - 지금 값의 소수 자릿수부터(엑셀과 같다)
      const v = first.v; const d = typeof v === "number" && !Number.isInteger(v) ? Math.min(10, (String(Number(v.toPrecision(15))).split(".")[1] || "").length) : 0;
      start = d ? "0." + "0".repeat(d) : "0";
    }
    const nf = bumpFmt(start, how);
    mutate(() => eachCell(S.sel, (r, c, k) => { const o = { ...cellObj(sh, k) }; const f2 = how === "pct" || how === "comma" ? nf : o.fmt ? bumpFmt(o.fmt, how) : nf; if (f2) o.fmt = f2; else delete o.fmt; putCell(sh, k, o); }));
  }
  /** 셀 서식(Ctrl+1) - 표시 형식·맞춤·글꼴·채우기를 한 창에서. 바꾼 칸만 고른 범위 모두에 */
  function formatDialog() {
    if (S.edit) endEdit(true);
    const o = effCell(sheet().cells[key(S.cur.r, S.cur.c)]);
    document.querySelectorAll(".fmtDlg").forEach((x) => x.remove());
    const dlg = document.createElement("div"); dlg.className = "fmtDlg";
    const opt = (v, cur, label) => `<option value="${esc(v)}"${v === (cur || "") ? " selected" : ""}>${esc(label)}</option>`;
    const sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36];
    dlg.innerHTML = `<b>셀 서식 - ${esc(sheet().name)}!${esc(rangeName(clampRange(S.sel)))}</b>
      <div class="sec"><h4>표시 형식</h4><div class="row"><select data-k="fmtp">${FMTS.map(([f, l]) => opt(f, FMTS.some(([x]) => x === (o.fmt || "")) ? o.fmt : "__", l)).join("")}<option value="__"${FMTS.some(([x]) => x === (o.fmt || "")) ? "" : " selected"}>직접 입력</option></select><input data-k="fmt" value="${esc(o.fmt || "")}" placeholder="예: #,##0.00 · 0.0% · yyyy-mm-dd · @"></div><div class="hint" data-k="prev"></div></div>
      <div class="sec"><h4>맞춤</h4><div class="row">가로 <select data-k="align">${opt("", o.align, "일반")}${opt("left", o.align, "왼쪽")}${opt("center", o.align, "가운데")}${opt("right", o.align, "오른쪽")}</select> 세로 <select data-k="valign">${opt("", o.valign, "아래")}${opt("middle", o.valign, "가운데")}${opt("top", o.valign, "위")}</select><label><input type="checkbox" data-k="wrap"${o.wrap ? " checked" : ""}> 줄바꿈</label></div></div>
      <div class="sec"><h4>글꼴</h4><div class="row"><label><input type="checkbox" data-k="b"${o.b ? " checked" : ""}> <b>굵게</b></label><label><input type="checkbox" data-k="i"${o.i ? " checked" : ""}> <i>기울임</i></label><label><input type="checkbox" data-k="u"${o.u ? " checked" : ""}> <u>밑줄</u></label><label><input type="checkbox" data-k="strike"${o.strike ? " checked" : ""}> <s>취소선</s></label> 크기 <select data-k="size">${sizes.map((n) => opt(String(n), String(o.size || defSize()), String(n))).join("")}</select></div>
        <div class="row">글자색 <input type="color" data-k="color" value="${esc(/^#[0-9a-f]{6}$/i.test(o.color || "") ? o.color : "#000000")}"><label><input type="checkbox" data-k="colorOn"${o.color ? " checked" : ""}> 지정</label> 채우기 <input type="color" data-k="fill" value="${esc(/^#[0-9a-f]{6}$/i.test(o.fill || "") ? o.fill : "#FFFFFF")}"><label><input type="checkbox" data-k="fillOn"${o.fill ? " checked" : ""}> 지정</label></div></div>
      <div class="acts"><span class="hint">Enter = 확인 · Esc = 닫기</span><span style="flex:1"></span><button class="chip sm" data-d="no">취소</button><button class="chip sm primary" data-d="ok">확인</button></div>`;
    document.body.appendChild(dlg);
    const g = (k) => dlg.querySelector(`[data-k="${k}"]`);
    const prev = () => { const f = g("fmt").value, v = typeof o.v === "number" ? o.v : 1234.5; g("prev").textContent = "보기: " + (f ? fmtNumber(v, f) : display({ v })); };
    g("fmtp").onchange = () => { if (g("fmtp").value !== "__") g("fmt").value = g("fmtp").value; prev(); };
    g("fmt").oninput = prev; prev();
    g("color").oninput = () => (g("colorOn").checked = true); g("fill").oninput = () => (g("fillOn").checked = true);
    const close = () => { dlg.remove(); focusGrid(); };
    const ok = () => {
      const want = { fmt: g("fmt").value.trim() || undefined, align: g("align").value || undefined, valign: g("valign").value || undefined, wrap: g("wrap").checked || undefined,
        b: g("b").checked || undefined, i: g("i").checked || undefined, u: g("u").checked || undefined, strike: g("strike").checked || undefined,
        size: +g("size").value === defSize() ? undefined : +g("size").value, color: g("colorOn").checked ? g("color").value.toUpperCase() : undefined, fill: g("fillOn").checked ? g("fill").value.toUpperCase() : undefined };
      const have = { fmt: o.fmt || undefined, align: o.align || undefined, valign: o.valign || undefined, wrap: o.wrap || undefined, b: o.b || undefined, i: o.i || undefined, u: o.u || undefined, strike: o.strike || undefined,
        size: o.size && +o.size !== defSize() ? +o.size : undefined, color: o.color ? String(o.color).toUpperCase() : undefined, fill: o.fill ? String(o.fill).toUpperCase() : undefined };
      const patch = {}; for (const k of Object.keys(want)) if (want[k] !== have[k]) patch[k] = want[k];
      close();
      if (Object.keys(patch).length) mutate(() => { const sh = sheet(); eachCell(S.sel, (r, c, k) => { const x = { ...cellObj(sh, k), ...patch }; for (const kk of Object.keys(patch)) if (patch[kk] === undefined) { const st = styleOf(x.s); if (st && st[kk]) x[kk] = kk === "size" ? defSize() : false; else delete x[kk]; } putCell(sh, k, x); }); });
    };
    dlg.addEventListener("click", (e) => { const b = e.target.closest("[data-d]"); if (b) (b.dataset.d === "ok" ? ok : close)(); });
    dlg.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Escape") close(); if (e.key === "Enter" && e.target.tagName !== "SELECT") { e.preventDefault(); ok(); } });
    g("fmt").focus();
  }
  /** 하이퍼링크 넣기(Ctrl+K) - 칸에 =HYPERLINK(주소, 보일 글) 수식(Ctrl+클릭으로 이동) */
  function insertLink() {
    if (S.edit) endEdit(true);
    const sh = sheet(), k = key(S.cur.r, S.cur.c), o = cellObj(sh, k);
    const m = o.f && /^=HYPERLINK\(\s*"((?:[^"]|"")*)"\s*(?:,\s*"((?:[^"]|"")*)")?\s*\)$/i.exec(o.f);
    const addr = prompt("링크 주소 - https://… · #탭!A1 · #A1 · mailto:…", m ? m[1].replace(/""/g, '"') : ""); if (addr == null) return;
    if (!addr.trim()) { if (m) mutate(() => { const x = { ...cellObj(sh, k) }; delete x.f; x.v = m[2] ? m[2].replace(/""/g, '"') : ""; putCell(sh, k, x); }); return; }
    const cur = m ? (m[2] || "").replace(/""/g, '"') : String(display(effCell(sh.cells[k])) || "");
    const text = prompt("보일 글", cur || addr.trim()); if (text == null) return;
    const q = (t) => '"' + t.replace(/"/g, '""') + '"';
    mutate(() => { const x = { ...cellObj(sh, k) }; delete x.v; x.f = `=HYPERLINK(${q(addr.trim())}${text && text !== addr.trim() ? ", " + q(text) : ""})`; putCell(sh, k, x); recalc(); });
  }
  function fillFmtSel(cur) {
    const list = FMTS.some(([f]) => f === cur) ? FMTS : [...FMTS, [cur, cur]];
    $("#fmtSel").innerHTML = list.map(([f, l]) => `<option value="${esc(f)}">${esc(l)}</option>`).join("") + `<option value="__custom">직접 입력…</option>`;
    $("#fmtSel").value = cur;
  }
  /** 요청 표시 - 끝나지 않은 요청의 범위를 점선 상자 + 번호로 */
  function renderMarks() {
    const sh = sheet(); const html = [];
    activeReqs().filter((q) => q.slide === sh.id && q.range).forEach((q) => {
      const g = parseRange(q.range); if (!g) return;
      const R = rectOf(clampRange(g));
      const tag = q.status === "working" ? `${RQ ? RQ.agentName() : "AI"} 처리 중` : ST[q.status] || "요청";  // AI 가 처리 중인 범위 - 사람이 같은 곳을 고치기 전에 알 수 있게
      html.push(`<div class="ov reqBox ${esc(q.status)}" style="left:${R.x}px;top:${R.y}px;width:${R.w + 1}px;height:${R.h + 1}px"><span class="reqTag">${esc(tag)}</span></div>`);
    });
    if (AI.hl) AI.hl.cells.filter((c) => c.tab === sh.id).forEach((c, k) => {  // AI 가 바꾼 셀 - 초록 테두리
      const p = parseRef(c.key); if (!p) return;
      const m = mergeAt(sh, p.r, p.c) || { r1: p.r, c1: p.c, r2: p.r, c2: p.c }, R = rectOf(clampRange(m));
      html.push(`<div class="ov aiCell" style="left:${R.x}px;top:${R.y}px;width:${R.w + 1}px;height:${R.h + 1}px">${k ? "" : '<span class="aiTag">AI 변경</span>'}</div>`);
    });
    if (LIVE) for (const x of LIVE.others()) {  // 함께 보는 사람(동시 편집 2단계) - 다른 창이 고른 범위에 그 창 색 테두리·이름
      if (!x.where || x.where.tab !== sh.id) continue;
      const g = parseRange(x.where.range); if (!g) continue;
      const R = rectOf(clampRange(g));
      html.push(`<div class="ov presBox" style="left:${R.x}px;top:${R.y}px;width:${R.w + 1}px;height:${R.h + 1}px;border-color:${esc(x.color)}"><span class="presTag" style="background:${esc(x.color)}">${esc(x.user || "다른 창")}${x.editing ? " · 입력 중" : ""}</span></div>`);
    }
    $("#marks").innerHTML = html.join("");
  }
  function scrollIntoView(r, c) {
    const W = $("#gridWrap"), sh = sheet(), fz = parseRef(sh.freeze || "") || { r: 0, c: 0 };
    const topFix = G.rowY[fz.r] || HH, leftFix = G.colX[fz.c] || HW;
    const x1 = G.colX[c], x2 = G.colX[c + 1], y1 = G.rowY[r], y2 = G.rowY[r + 1];
    const vw = W.clientWidth / Z, vh = W.clientHeight / Z, L = sx(), T = sy();  // 격자 좌표로
    if (c >= fz.c) { if (x1 - L < leftFix) W.scrollLeft = (x1 - leftFix) * Z; else if (x2 - L > vw) W.scrollLeft = (x2 - vw + 2) * Z; }
    if (r >= fz.r) { if (y1 - T < topFix) W.scrollTop = (y1 - topFix) * Z; else if (y2 - T > vh) W.scrollTop = (y2 - vh + 2) * Z; }
  }

  // ---------------------------------------------------------------- 선택·이동
  function selectRange(g, quiet) {
    const sh = S.deck ? sheet() : null;
    S.sel = sh ? expandForMerges(sh, g) : g; S.anchor = { r: g.r1, c: g.c1 }; S.cur = { r: g.r1, c: g.c1 };
    if (!quiet) { renderSel(); scrollIntoView(S.cur.r, S.cur.c); }
  }
  function selectCell(r, c, extend) {
    r = Math.max(0, Math.min(r, G.rows - 1)); c = Math.max(0, Math.min(c, G.cols - 1));
    const sh = sheet();
    if (extend) {
      S.sel = expandForMerges(sh, { r1: Math.min(S.anchor.r, r), c1: Math.min(S.anchor.c, c), r2: Math.max(S.anchor.r, r), c2: Math.max(S.anchor.c, c) });
      S.ext = { r, c };
    } else {
      const m = mergeAt(sh, r, c); if (m) { r = m.r1; c = m.c1; }
      S.cur = { r, c }; S.anchor = { r, c }; S.ext = null;
      S.sel = m ? { ...m } : { r1: r, c1: c, r2: r, c2: c };
    }
    renderSel(); scrollIntoView(extend ? r : S.cur.r, extend ? c : S.cur.c);
  }
  /** 값·수식이 있는 마지막 행·마지막 열(엑셀 Ctrl+End) */
  function lastCell(sh) { let r = 0, c = 0; for (const [k, raw] of Object.entries(sh.cells)) { const v = cellVal(sh, k); if (v == null || v === "") continue; const p = parseRef(k); if (p) { r = Math.max(r, p.r); c = Math.max(c, p.c); } } return { r: Math.min(r, G.rows - 1), c: Math.min(c, G.cols - 1) }; }
  function move(dr, dc, extend, jump) {
    const sh = sheet();
    let { r, c } = extend && S.ext ? S.ext : S.cur;
    if (!extend) { const m = mergeAt(sh, r, c); if (m) { if (dr > 0) r = m.r2; if (dc > 0) c = m.c2; } }
    if (jump) {  // Ctrl+화살표 - 데이터 덩어리의 끝으로
      const filled = (rr, cc) => cellVal(sh, key(rr, cc)) != null && cellVal(sh, key(rr, cc)) !== "";
      const inb = (rr, cc) => rr >= 0 && cc >= 0 && rr < G.rows && cc < G.cols;
      if (!inb(r + dr, c + dc)) { /* 끝 */ }
      else if (filled(r, c) && filled(r + dr, c + dc)) { while (inb(r + dr, c + dc) && filled(r + dr, c + dc)) { r += dr; c += dc; } }
      else { r += dr; c += dc; while (inb(r + dr, c + dc) && !filled(r, c)) { r += dr; c += dc; } }
    } else { r += dr; c += dc; }
    while (dr && r > 0 && r < G.rows - 1 && rowHidden(sh, r)) r += dr > 0 ? 1 : -1;  // 숨긴 행·열은 건너뛴다
    while (dc && c > 0 && c < G.cols - 1 && colHidden(sh, c)) c += dc > 0 ? 1 : -1;
    selectCell(r, c, extend);
  }
  /** Enter·Tab 이동 - 범위가 골라져 있으면 그 안에서 돈다 */
  function advance(dr, dc) {
    const g = S.sel;
    if (g.r1 === g.r2 && g.c1 === g.c2 || rangeName(g) === rangeName(mergeAt(sheet(), S.cur.r, S.cur.c) || { r1: -1, c1: 0, r2: -1, c2: 0 })) { move(dr, dc); return; }
    let { r, c } = S.cur;
    if (dc) { c += dc; if (c > g.c2) { c = g.c1; r = r + 1 > g.r2 ? g.r1 : r + 1; } if (c < g.c1) { c = g.c2; r = r - 1 < g.r1 ? g.r2 : r - 1; } }
    else { r += dr; if (r > g.r2) { r = g.r1; c = c + 1 > g.c2 ? g.c1 : c + 1; } if (r < g.r1) { r = g.r2; c = c - 1 < g.c1 ? g.c2 : c - 1; } }
    S.cur = { r, c }; renderSel(); scrollIntoView(r, c);
  }

  // ---------------------------------------------------------------- 셀 입력칸 - 늘 초점을 갖는 textarea(한글 입력기 조합이 첫 글자부터 들어가게). 편집 중이 아니면 보이지 않는다
  const ED = () => $("#editor");
  function placeEditor() {
    const sh = sheet(), m = mergeAt(sh, S.cur.r, S.cur.c) || { r1: S.cur.r, c1: S.cur.c, r2: S.cur.r, c2: S.cur.c };
    const R = rectOf(m), e = ED();
    Object.assign(e.style, { left: R.x - 1 + "px", top: R.y - 1 + "px", minWidth: R.w + 3 + "px", width: R.w + 3 + "px", height: Math.max(R.h + 3, 26) + "px" });
    if (S.edit) {
      const o = effCell(sh.cells[key(S.cur.r, S.cur.c)]);
      e.style.fontWeight = o.b ? "700" : ""; e.style.fontStyle = o.i ? "italic" : ""; e.style.fontSize = (o.size || defSize()) + "pt";
      e.style.fontFamily = $("#grid").style.fontFamily;
      e.style.width = "1px"; e.style.width = Math.max(R.w + 3, Math.min(e.scrollWidth + 8, 640)) + "px";
      e.style.height = "1px"; e.style.height = Math.max(R.h + 3, e.scrollHeight + 2) + "px";
    }
  }
  function focusGrid() { const e = ED(); if (document.activeElement !== e) e.focus({ preventScroll: true }); }
  function startEdit(mode, text) {
    const sh = sheet(), k = key(S.cur.r, S.cur.c);
    S.edit = { r: S.cur.r, c: S.cur.c, mode, orig: rawText(sh, k) };
    const e = ED(); e.classList.add("on");
    if (text !== undefined) e.value = text; else e.value = S.edit.orig;
    focusGrid(); const n = e.value.length; e.setSelectionRange(n, n);
    placeEditor(); $("#fxIn").value = e.value;
  }
  function endEdit(commit) {
    if (!S.edit) return;
    const e = ED(), text = e.value, { r, c, orig } = S.edit;
    S.edit = null; e.classList.remove("on"); e.value = "";
    if (commit && text !== orig) mutate(() => { const sh = sheet(); setInput(sh, key(r, c), text); growSize(sh, r, c); });
    else renderSel();
  }
  function growSize(sh, r, c) {
    const d = dims(sh); if (r < d.rows && c < d.cols) return;
    sh.size = { rows: Math.max(d.rows, r + 1), cols: Math.max(d.cols, c + 1) };
  }
  /** 수식 입력 중에 셀을 누르면 참조를 넣는다(연산자·괄호·쉼표 뒤일 때) */
  function wantsRef() {
    if (!S.edit) return false; const e = ED(); if (e.value[0] !== "=") return false;
    const before = e.value.slice(0, e.selectionStart).trimEnd();
    return /[=(+\-*/^,&<>:]$/.test(before);
  }
  function insertRef(text) { const e = ED(), s = e.selectionStart, t = e.selectionEnd; e.value = e.value.slice(0, s) + text + e.value.slice(t); const n = s + text.length; e.setSelectionRange(n, n); S.edit.mode = "edit"; placeEditor(); $("#fxIn").value = e.value; }

  function onEditorKey(e) {
    if (e.isComposing || e.keyCode === 229) return;  // 한글 조합 중 - 입력기에 맡긴다
    const ctrl = e.ctrlKey || e.metaKey;
    if (S.edit) {
      if (e.key === "Escape") { e.preventDefault(); endEdit(false); return; }
      if (e.key === "Enter" && e.altKey) { e.preventDefault(); insertRef("\n"); return; }
      if (e.key === "Enter") { e.preventDefault(); endEdit(true); advance(e.shiftKey ? -1 : 1, 0); return; }
      if (e.key === "Tab") { e.preventDefault(); endEdit(true); advance(0, e.shiftKey ? -1 : 1); return; }
      if (S.edit.mode === "enter" && e.key.startsWith("Arrow")) {
        e.preventDefault(); endEdit(true);
        move(e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0, e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0); return;
      }
      if (e.key === "F2") { e.preventDefault(); S.edit.mode = S.edit.mode === "enter" ? "edit" : "enter"; return; }
      return;
    }
    const k = e.key;
    if (ctrl && !e.altKey) {
      const lk = k.toLowerCase();
      if (lk === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
      if (lk === "y") { e.preventDefault(); redo(); return; }
      if (lk === "b" || lk === "i" || lk === "u") { e.preventDefault(); toggleStyle(lk); return; }
      if (lk === "a") { e.preventDefault(); S.anchor = { r: 0, c: 0 }; S.sel = { r1: 0, c1: 0, r2: G.rows - 1, c2: G.cols - 1 }; renderSel(); return; }
      if (lk === "s") { e.preventDefault(); save(); return; }
      if (k === "Home") { e.preventDefault(); selectCell(0, 0); return; }
      if (k === "End") { e.preventDefault(); const L = lastCell(sheet()); selectCell(L.r, L.c, e.shiftKey); return; }  // 데이터가 있는 마지막 행·열
      if (k === " " || e.code === "Space") { e.preventDefault(); if (e.shiftKey) { S.anchor = { r: 0, c: 0 }; S.sel = { r1: 0, c1: 0, r2: G.rows - 1, c2: G.cols - 1 }; } else { S.sel = { r1: 0, r2: G.rows - 1, c1: S.sel.c1, c2: S.sel.c2 }; S.anchor = { r: 0, c: S.sel.c1 }; } renderSel(); return; }  // 열 전체 · Ctrl+Shift+Space = 모두
      if (k === ";" && !e.shiftKey) { e.preventDefault(); const d = new Date(), v = Math.round((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - Date.UTC(1899, 11, 30)) / 864e5); mutate(() => { const sh = sheet(), kk = key(S.cur.r, S.cur.c), o = cellObj(sh, kk); delete o.f; putCell(sh, kk, { ...o, v, fmt: o.fmt || "yyyy-mm-dd" }); }); return; }  // 오늘 날짜
      if (k === "PageDown" || k === "PageUp") { e.preventDefault(); const n = S.deck.sheets.length, i = (S.ti + (k === "PageDown" ? 1 : -1) + n) % n; switchTab(i); return; }  // 다음·이전 탭
      if (lk === "5") { e.preventDefault(); toggleStyle("strike"); return; }  // 취소선
      if (lk === "k") { e.preventDefault(); insertLink(); return; }  // 하이퍼링크
      if (lk === "1" && !e.shiftKey) { e.preventDefault(); formatDialog(); return; }  // 셀 서식
      if (e.shiftKey && (k === "%" || e.code === "Digit5")) { e.preventDefault(); numFmt("pct"); return; }
      if (e.shiftKey && (k === "!" || e.code === "Digit1")) { e.preventDefault(); numFmt("comma"); return; }
      if (e.shiftKey && (k === "$" || e.code === "Digit4")) { e.preventDefault(); numFmt("comma"); return; }  // 통화 - 원화는 천 단위 구분과 같게
      if ((lk === "9" || lk === "0") && !e.shiftKey && window.NexaSheetX) { e.preventDefault(); NexaSheetX.hide(lk === "9" ? "r" : "c", true); return; }  // 행·열 숨기기
      if (k === "-" || k === "+" || (k === "=" && e.shiftKey)) {  // 행·열 지우기·넣기 - 행(열) 전체를 골랐을 때(엑셀은 아니면 창을 띄운다)
        e.preventDefault(); const g = S.sel, rows = g.c1 === 0 && g.c2 === G.cols - 1, cols = g.r1 === 0 && g.r2 === G.rows - 1, del = k === "-";
        if (rows && !cols) shiftAxis("r", g.r1, del ? -(g.r2 - g.r1 + 1) : g.r2 - g.r1 + 1);
        else if (cols && !rows) shiftAxis("c", g.c1, del ? -(g.c2 - g.c1 + 1) : g.c2 - g.c1 + 1);
        else toast(`행 번호(Shift+Space) 또는 열 머리(Ctrl+Space)로 행·열 전체를 고른 뒤 Ctrl+${del ? "-" : "+"} - 칸만 ${del ? "지우기" : "넣기"}는 행·열 메뉴`);
        return;
      }
      if (k.startsWith("Arrow")) { e.preventDefault(); move(k === "ArrowDown" ? 1 : k === "ArrowUp" ? -1 : 0, k === "ArrowRight" ? 1 : k === "ArrowLeft" ? -1 : 0, e.shiftKey, true); return; }
      return;  // Ctrl+C·V·X 는 copy/paste/cut 이벤트로
    }
    if (k.startsWith("Arrow")) { e.preventDefault(); move(k === "ArrowDown" ? 1 : k === "ArrowUp" ? -1 : 0, k === "ArrowRight" ? 1 : k === "ArrowLeft" ? -1 : 0, e.shiftKey); return; }
    if (k === "Enter") { e.preventDefault(); advance(e.shiftKey ? -1 : 1, 0); return; }
    if (k === "Tab") { e.preventDefault(); advance(0, e.shiftKey ? -1 : 1); return; }
    if (e.altKey && e.shiftKey && !ctrl && (e.code === "Digit5" || k === "%")) { e.preventDefault(); toggleStyle("strike"); return; }  // 취소선(구글 시트와 같다 - 브라우저가 Ctrl+5 를 탭 바꾸기로 가져갈 때)
    if (k === "F2" && e.shiftKey) { e.preventDefault(); noteEdit(); return; }  // 메모
    if (k === "F2") { e.preventDefault(); startEdit("edit"); return; }
    if ((k === "Delete" || k === "Backspace") && S.drawSel) { e.preventDefault(); drawDelete(); return; }  // 고른 그림 지우기
    if (k === " " && e.shiftKey) { e.preventDefault(); S.sel = { r1: S.sel.r1, r2: S.sel.r2, c1: 0, c2: G.cols - 1 }; S.anchor = { r: S.sel.r1, c: 0 }; renderSel(); return; }  // 행 전체
    if (k === "Delete") { e.preventDefault(); clearRange(S.sel); return; }
    if (k === "Backspace") { e.preventDefault(); startEdit("enter", ""); return; }
    if (k === "Escape") { if (S.clip) { S.clip.show = false; renderSel(); } return; }
    if (k === "Home") { e.preventDefault(); selectCell(S.cur.r, 0, e.shiftKey); return; }
    if (k === "PageDown" || k === "PageUp") { e.preventDefault(); move(k === "PageDown" ? 20 : -20, 0, e.shiftKey); return; }
    // 글자 키는 막지 않는다 → input 이벤트에서 편집 시작(바로 치기)
  }
  function onEditorInput() {
    const e = ED();
    if (!S.edit) { const v = e.value; startEdit("enter", v); return; }
    placeEditor(); $("#fxIn").value = e.value;
  }

  // ---------------------------------------------------------------- 고치기(서식·지우기·병합·행열)
  function eachCell(g, fn) { for (let r = g.r1; r <= g.r2; r++) for (let c = g.c1; c <= g.c2; c++) fn(r, c, key(r, c)); }
  function clearRange(g) { mutate(() => { const sh = sheet(); eachCell(g, (r, c, k) => { const o = { ...cellObj(sh, k) }; delete o.v; delete o.f; putCell(sh, k, o); }); }); }
  function applyStyle(patch) {
    mutate(() => { const sh = sheet(); eachCell(S.sel, (r, c, k) => { putCell(sh, k, { ...cellObj(sh, k), ...patch }); }); });
  }
  /** 켜고 끄기(굵게·줄바꿈 등) - 지금 셀(스타일까지 푼 값) 기준. 스타일이 켠 것을 끌 때는 false 로 덮는다 */
  function toggleStyle(t) {
    const on = !effCell(sheet().cells[key(S.cur.r, S.cur.c)])[t];
    mutate(() => { const sh = sheet(); eachCell(S.sel, (r, c, k) => { const o = cellObj(sh, k), st = styleOf(o.s); putCell(sh, k, { ...o, [t]: on ? true : st && st[t] ? false : undefined }); }); });
  }
  /** 테두리 - all 모든 칸 네 변 · outline 바깥 · bottom 아래 · none 지움(스타일 테두리도 {} 로 덮는다) */
  function applyBorder(kind) {
    const g = S.sel, L = "line";
    mutate(() => {
      const sh = sheet();
      eachCell(g, (r, c, k) => {
        const o = cellObj(sh, k), st = styleOf(o.s);
        if (kind === "none") { putCell(sh, k, { ...o, bd: st && st.bd ? {} : undefined }); return; }
        if (kind === "all") { putCell(sh, k, { ...o, bd: L }); return; }
        const want = kind === "bottom" ? { b: r === g.r2 } : { t: r === g.r1, b: r === g.r2, l: c === g.c1, r: c === g.c2 };
        if (!Object.values(want).some(Boolean)) return;
        const cur = o.bd == null ? (st && st.bd) || {} : o.bd;
        const sides = typeof cur === "object" ? { ...cur } : { t: cur, r: cur, b: cur, l: cur };
        for (const [s2, on] of Object.entries(want)) if (on) sides[s2] = L;
        putCell(sh, k, { ...o, bd: ["t", "r", "b", "l"].every((x) => sides[x] === L) ? L : sides });
      });
    });
  }
  function toggleGrid() {
    mutate(() => { const sh = sheet(), def = !(theme() && theme().grid === false), nv = !gridOn(sh); if (nv === def) delete sh.grid; else sh.grid = nv; });
  }
  function toggleMerge() {
    const sh = sheet(), m = mergeAt(sh, S.cur.r, S.cur.c), g = S.sel;
    if (m && rangeName(g) === rangeName(m)) { mutate(() => { sh.merges = (sh.merges || []).filter((x) => rangeName(parseRange(x)) !== rangeName(m)); if (!sh.merges.length) delete sh.merges; }); return; }
    if (g.r1 === g.r2 && g.c1 === g.c2) { toast("병합할 범위를 먼저 고르세요"); return; }
    let lost = 0; eachCell(g, (r, c, k) => { if ((r !== g.r1 || c !== g.c1) && cellVal(sh, k) != null) lost++; });
    if (lost && !confirm(`병합하면 왼쪽 위 셀의 값만 남고 다른 셀 ${lost}개의 값은 지워집니다. 병합할까요?`)) return;
    mutate(() => {
      sh.merges = (sh.merges || []).filter((x) => { const q = parseRange(x); return q && (q.r2 < g.r1 || q.r1 > g.r2 || q.c2 < g.c1 || q.c1 > g.c2); });
      sh.merges.push(rangeName(g));
      eachCell(g, (r, c, k) => { if (r !== g.r1 || c !== g.c1) { const o = { ...cellObj(sh, k) }; delete o.v; delete o.f; putCell(sh, k, o); } });
      S.cur = { r: g.r1, c: g.c1 };
    });
  }
  /** 행(axis "r")·열("c") 삽입(n>0)·삭제(n<0) - 셀·병합·너비·높이·틀 고정·모든 탭 수식의 참조를 같이 옮긴다 */
  function shiftAxis(axis, at, n) {
    (S.struct = S.struct || []).push({ op: (n < 0 ? "delete" : "insert") + (axis === "r" ? "Rows" : "Cols"), tab: sheet().id, at, n: Math.abs(n) });  // 다음 저장에 함께(서버 sheet_struct.py - 같은 규칙)
    mutate(() => {
      const sh = sheet(), del = n < 0, cnt = Math.abs(n), end = at + cnt - 1;
      const mv = (p) => {  // 끝점 하나 → 새 위치(지워지면 null)
        const v = axis === "r" ? p.r : p.c;
        if (!del) return v >= at ? v + cnt : v;
        if (v > end) return v - cnt; if (v >= at) return null; return v;
      };
      const cells = {};
      for (const [k, raw] of Object.entries(sh.cells)) {
        const p = parseRef(k); if (!p) { cells[k] = raw; continue; }
        const v = mv(p); if (v === null) continue;
        cells[axis === "r" ? key(v, p.c) : key(p.r, v)] = raw;
      }
      sh.cells = cells;
      const mvRange = (g) => {  // 범위 → 새 범위(통째로 지워지면 null). 삭제가 범위 안이면 줄어든다
        let a = axis === "r" ? g.r1 : g.c1, b = axis === "r" ? g.r2 : g.c2;
        if (del) { if (a >= at && b <= end) return null; const na = a > end ? a - cnt : a >= at ? at : a, nb = b > end ? b - cnt : b >= at ? at - 1 : b; a = na; b = nb; }
        else { if (a >= at) a += cnt; if (b >= at) b += cnt; }
        return axis === "r" ? { ...g, r1: a, r2: b } : { ...g, c1: a, c2: b };
      };
      if (sh.merges) { sh.merges = sh.merges.map(parseRange).filter(Boolean).map(mvRange).filter((g) => g && (g.r1 !== g.r2 || g.c1 !== g.c2)).map(rangeName); if (!sh.merges.length) delete sh.merges; }
      const remap = (obj, toIdx, toKey) => { if (!obj) return obj; const o = {}; for (const [k, v] of Object.entries(obj)) { const nv = mv(axis === "r" ? { r: toIdx(k), c: 0 } : { r: 0, c: toIdx(k) }); if (nv !== null) o[toKey(nv)] = v; } return o; };
      if (axis === "r" && sh.rows) sh.rows = remap(sh.rows, (k) => +k - 1, (i) => String(i + 1));
      if (axis === "c" && sh.cols) sh.cols = remap(sh.cols, colIndex, colName);
      if (sh.freeze) { const f = parseRef(sh.freeze); const v = axis === "r" ? f.r : f.c; if (v > at) { const nv = del ? Math.max(at, v - cnt) : v + cnt; sh.freeze = axis === "r" ? key(nv, f.c) : key(f.r, nv); } }
      if (sh.filter) {  // 필터(엑셀 자동 필터) - 범위·가린 행·열 조건 - sheet_struct.py 와 같다
        const fg = parseRange(sh.filter.ref || ""), ng = fg && mvRange(fg);
        if (!ng) delete sh.filter;
        else {
          const f = sh.filter; f.ref = rangeName(ng);
          if (axis === "r" && Array.isArray(f.rows)) { f.rows = f.rows.filter((k) => /^\d+$/.test(k)).map((k) => mv({ r: +k - 1, c: 0 })).filter((v) => v !== null).map((v) => String(v + 1)); if (!f.rows.length) delete f.rows; }
          if (axis === "c" && f.cols) { f.cols = remap(f.cols, colIndex, colName); if (!Object.keys(f.cols).length) delete f.cols; }
        }
      }
      const d = dims(sh); if (sh.size) sh.size = axis === "r" ? { ...sh.size, rows: Math.max(1, (+sh.size.rows || d.rows) + n) } : { ...sh.size, cols: Math.max(1, (+sh.size.cols || d.cols) + n) };
      // 수식 참조 - 이 탭을 가리키는 참조(같은 탭의 이름 없는 참조 · 다른 탭의 '이름!' 참조)
      // own = 이름 없는 참조가 가리키는 탭(문서 이름 정의는 없음 - 그때는 '이름!' 참조만 옮긴다)
      const moveRefs = (own) => (ends, nm) => {
        const target = nm == null ? own : sheetByName(nm, own || sh); if (!target || target !== sh) return ends;
        if (ends.some((e) => (axis === "r" ? e.r : e.c) == null)) return ends;  // 열 전체(A:C)를 행 작업이 · 행 전체(3:5)를 열 작업이 - 그대로(서버 sheet_struct.py 와 같다)
        if (ends.length === 1) { const v = mv(ends[0]); return v === null ? null : [axis === "r" ? { ...ends[0], r: v } : { ...ends[0], c: v }]; }
        const g = mvRange({ r1: ends[0].r, c1: ends[0].c, r2: ends[1].r, c2: ends[1].c }); if (!g) return null;
        return [{ ...ends[0], r: g.r1, c: g.c1 }, { ...ends[1], r: g.r2, c: g.c2 }];
      };
      for (const s2 of S.deck.sheets) for (const [k, raw] of Object.entries(s2.cells)) {
        if (!raw || typeof raw !== "object" || !raw.f) continue;
        raw.f = rewriteFormula(raw.f, moveRefs(s2));
      }
      // 이름 정의(엑셀 이름 관리자) - 문서 names·탭 names 의 값도 같은 규칙으로(범위 안에 넣으면 늘고, 지운 칸만 가리키면 #REF!)
      const nameDef = (v, own) => { if (typeof v !== "string" || !v) return v; const f = v[0] === "=" ? v : "=" + v, out = rewriteFormula(f, moveRefs(own)); return v[0] === "=" ? out : out.slice(1); };
      if (S.deck.names && typeof S.deck.names === "object") for (const k of Object.keys(S.deck.names)) S.deck.names[k] = nameDef(S.deck.names[k], null);
      for (const s2 of S.deck.sheets) if (s2.names && typeof s2.names === "object") for (const k of Object.keys(s2.names)) s2.names[k] = nameDef(s2.names[k], s2);
    });
  }
  function rowColMenu(anchor) {
    const g = S.sel, nr = g.r2 - g.r1 + 1, nc = g.c2 - g.c1 + 1;
    openMenu(anchor, [
      { h: "행" },
      { label: `위에 행 ${nr}개 삽입`, act: () => shiftAxis("r", g.r1, nr) },
      { label: `아래에 행 ${nr}개 삽입`, act: () => shiftAxis("r", g.r2 + 1, nr) },
      { label: `행 ${g.r1 + 1}${nr > 1 ? "~" + (g.r2 + 1) : ""} 삭제`, act: () => shiftAxis("r", g.r1, -nr) },
      { h: "열" },
      { label: `왼쪽에 열 ${nc}개 삽입`, act: () => shiftAxis("c", g.c1, nc) },
      { label: `오른쪽에 열 ${nc}개 삽입`, act: () => shiftAxis("c", g.c2 + 1, nc) },
      { label: `열 ${colName(g.c1)}${nc > 1 ? "~" + colName(g.c2) : ""} 삭제`, act: () => shiftAxis("c", g.c1, -nc) },
      "-",
      { label: "끝에 행 20개 더", act: () => addRows(20) },
      { label: "끝에 열 5개 더", act: () => mutate(() => { const sh = sheet(), d = dims(sh); sh.size = { rows: d.rows, cols: d.cols + 5 }; }) },
    ]);
  }
  function addRows(n) { mutate(() => { const sh = sheet(), d = dims(sh); sh.size = { rows: d.rows + n, cols: d.cols }; }); }
  function toggleFreeze() {
    mutate(() => { const sh = sheet(); if (sh.freeze) delete sh.freeze; else if (S.cur.r || S.cur.c) sh.freeze = key(S.cur.r, S.cur.c); else toast("고정할 경계의 오른쪽 아래 셀(예: A2 = 1행 고정)을 고른 뒤 누르세요"); });
  }

  // ---------------------------------------------------------------- 복사·붙여넣기 - 탭 구분 글(엑셀과 주고받기) + 이 화면 안에서는 서식·수식까지(상대 참조 이동)
  const tsvField = (s) => (/[\t\n"]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
  function copyRange(cut) {
    const sh = sheet(), g = S.sel, rows = [], cells = [];
    for (let r = g.r1; r <= g.r2; r++) { const line = [], cl = []; for (let c = g.c1; c <= g.c2; c++) { const k = key(r, c); line.push(tsvField(display(effCell(sh.cells[k])))); cl.push(sh.cells[k] == null ? null : clone(sh.cells[k])); } rows.push(line.join("\t")); cells.push(cl); }
    S.clip = { tsv: rows.join("\r\n"), cells, g: { ...g }, ti: sh.id, show: true, cut: !!cut };
    renderSel();
    return S.clip.tsv;
  }
  /** 고른 범위 → HTML 표(엑셀·워드에 붙이면 서식이 따라간다) - 굵게·기울임·밑줄·취소선·글자색·채우기·맞춤·크기·병합 */
  function copyHtml() {
    const sh = sheet(), g = S.sel, ms = merges(sh), skip = new Set(), out = ["<table style=\"border-collapse:collapse\">"];
    for (let r = g.r1; r <= g.r2; r++) {
      out.push("<tr>");
      for (let c = g.c1; c <= g.c2; c++) {
        if (skip.has(r * 4096 + c)) continue;
        const o = effCell(sh.cells[key(r, c)]), m = ms.find((x) => x.r1 === r && x.c1 === c);
        if (m) for (let rr = m.r1; rr <= Math.min(m.r2, g.r2); rr++) for (let cc = m.c1; cc <= Math.min(m.c2, g.c2); cc++) skip.add(rr * 4096 + cc);
        const st = [o.b ? "font-weight:700" : "", o.i ? "font-style:italic" : "", o.u || o.strike ? `text-decoration:${[o.u ? "underline" : "", o.strike ? "line-through" : ""].filter(Boolean).join(" ")}` : "",
          o.color ? `color:${o.color}` : "", o.fill ? `background:${o.fill}` : "", o.align ? `text-align:${o.align}` : "", o.valign ? `vertical-align:${o.valign}` : "", o.size ? `font-size:${+o.size}pt` : "", o.wrap ? "white-space:normal" : ""].filter(Boolean).join(";");
        const span = m ? ` rowspan="${Math.min(m.r2, g.r2) - r + 1}" colspan="${Math.min(m.c2, g.c2) - c + 1}"` : "";
        const num = typeof o.v === "number" && !o.f ? ` x:num="${o.v}"` : "";
        out.push(`<td${span}${num}${st ? ` style="${st}"` : ""}>${esc(String(display(o))).replace(/\n/g, "<br>")}</td>`);
      }
      out.push("</tr>");
    }
    out.push("</table>");
    return `<html><head><meta charset="utf-8"></head><body>${out.join("")}</body></html>`;
  }
  /** 엑셀 등에서 복사한 HTML 표 → [[{text, style}]] (서식은 인라인 style 과 <style> 의 .xlNN 규칙에서) - 표가 없으면 null */
  function parseHtmlTable(html) {
    if (!/<table/i.test(html)) return null;
    const doc = new DOMParser().parseFromString(html, "text/html"), tb = doc.querySelector("table"); if (!tb) return null;
    const rules = {};
    for (const st of doc.querySelectorAll("style")) for (const m of st.textContent.matchAll(/\.([\w-]+)\s*\{([^}]*)\}/g)) rules[m[1]] = (rules[m[1]] || "") + ";" + m[2];
    const toHex = (v) => { v = String(v || "").trim(); if (/^#[0-9a-f]{6}$/i.test(v)) return v.toUpperCase(); if (/^#[0-9a-f]{3}$/i.test(v)) return ("#" + v.slice(1).split("").map((x) => x + x).join("")).toUpperCase(); const m = /rgb\((\d+),\s*(\d+),\s*(\d+)\)/i.exec(v); return m ? "#" + [m[1], m[2], m[3]].map((x) => (+x).toString(16).padStart(2, "0")).join("").toUpperCase() : null; };
    const styleOf2 = (td) => {
      const css = [...td.classList].map((c) => rules[c] || "").join(";") + ";" + (td.getAttribute("style") || ""), get = (k) => { let v = null; for (const m of css.matchAll(new RegExp(`(?:^|;)\\s*${k}\\s*:\\s*([^;]+)`, "gi"))) v = m[1].trim(); return v; };
      const o = {};
      const fw = get("font-weight"); if (fw && (fw === "bold" || +fw >= 600)) o.b = true;
      if (/italic/i.test(get("font-style") || "")) o.i = true;
      const td2 = get("text-decoration") || ""; if (/underline/i.test(td2)) o.u = true; if (/line-through/i.test(td2)) o.strike = true;
      const col = toHex(get("color")); if (col && col !== "#000000" && col !== "#000") o.color = col;
      const bg = toHex(get("background") || get("background-color")); if (bg && bg !== "#FFFFFF") o.fill = bg;
      const al = (get("text-align") || "").toLowerCase(); if (["left", "center", "right"].includes(al)) o.align = al;
      const va = (get("vertical-align") || "").toLowerCase(); if (va === "top") o.valign = "top"; else if (va === "middle") o.valign = "middle";
      const fs2 = /([\d.]+)pt/.exec(get("font-size") || ""); if (fs2 && +fs2[1] !== defSize()) o.size = +fs2[1];
      if (/normal/i.test(get("white-space") || "")) o.wrap = true;
      return o;
    };
    const grid = [], taken = [];
    [...tb.rows].forEach((tr, r) => {
      grid[r] = grid[r] || []; let c = 0;
      for (const td of tr.cells) {
        while (taken[r] && taken[r][c]) c++;
        const rs = Math.max(1, +td.rowSpan || 1), cs = Math.max(1, +td.colSpan || 1);
        for (let i = 0; i < rs; i++) for (let j = 0; j < cs; j++) { (taken[r + i] = taken[r + i] || [])[c + j] = true; if (i || j) (grid[r + i] = grid[r + i] || [])[c + j] = { text: "", style: {} }; }
        const text = [...td.childNodes].map((n) => (n.nodeName === "BR" ? "\n" : n.textContent)).join("").replace(/\u00a0/g, " ").replace(/\n$/, "");
        grid[r][c] = { text: text.trim() === "" ? "" : text, style: styleOf2(td), span: rs > 1 || cs > 1 ? [rs, cs] : null };
        c += cs;
      }
    });
    return grid.map((row) => Array.from({ length: Math.max(...grid.map((x) => x.length)) }, (_, j) => row[j] || { text: "", style: {} }));
  }
  /** HTML 표 붙여넣기 - 값은 입력처럼(숫자·날짜 알아봄), 서식은 칸에 · 병합은 병합으로 */
  function pasteHtml(grid) {
    const sh = sheet(), at = { r: S.sel.r1, c: S.sel.c1 }, h = grid.length, w = grid[0].length, target = { r1: at.r, c1: at.c, r2: at.r + h - 1, c2: at.c + w - 1 };
    mutate(() => {
      const newMerges = [];
      for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) {
        const cell = grid[i][j], k = key(at.r + i, at.c + j);
        setInput(sh, k, cell.text);
        const o = { ...cellObj(sh, k) };
        for (const kk of ["b", "i", "u", "strike", "color", "fill", "align", "valign", "size", "wrap"]) delete o[kk];
        putCell(sh, k, { ...o, ...cell.style });
        if (cell.span) newMerges.push(rangeName({ r1: at.r + i, c1: at.c + j, r2: at.r + i + cell.span[0] - 1, c2: at.c + j + cell.span[1] - 1 }));
      }
      const outside = (m) => m.r2 < target.r1 || m.r1 > target.r2 || m.c2 < target.c1 || m.c1 > target.c2;  // 붙인 자리에 걸친 옛 병합은 지우고 붙인 표의 병합으로
      const keep = merges(sh).filter(outside).map(rangeName);
      if (keep.length + newMerges.length) sh.merges = [...keep, ...newMerges]; else delete sh.merges;
      growSize(sh, target.r2, target.c2);
      S.sel = target; S.cur = { r: target.r1, c: target.c1 }; S.anchor = { ...S.cur };
    });
  }
  function parseTsv(t) {
    t = t.replace(/\r\n?/g, "\n"); if (t.endsWith("\n")) t = t.slice(0, -1);
    const rows = [[]]; let i = 0, f = "";
    while (i <= t.length) {
      const ch = t[i];
      if (f === "" && ch === '"') {  // 따옴표 칸
        let j = i + 1, s = "";
        for (;;) { if (j >= t.length) break; if (t[j] === '"') { if (t[j + 1] === '"') { s += '"'; j += 2; continue; } j++; break; } s += t[j++]; }
        if (j >= t.length || t[j] === "\t" || t[j] === "\n") { f = s; i = j; continue; }
        f = t.slice(i, j); i = j; continue;
      }
      if (ch === undefined) { rows[rows.length - 1].push(f); break; }
      if (ch === "\t") { rows[rows.length - 1].push(f); f = ""; i++; continue; }
      if (ch === "\n") { rows[rows.length - 1].push(f); f = ""; rows.push([]); i++; continue; }
      f += ch; i++;
    }
    return rows;
  }
  function pasteText(text) {
    const sh = sheet(), at = { r: S.sel.r1, c: S.sel.c1 }, clip = S.clip && text.replace(/\r\n?/g, "\n").replace(/\n$/, "") === S.clip.tsv.replace(/\r\n?/g, "\n") ? S.clip : null;
    const grid = clip ? clip.cells : parseTsv(text);
    const h = grid.length, w = Math.max(...grid.map((r) => r.length));
    const one = h === 1 && w === 1, sel = S.sel, fill = one && (sel.r1 !== sel.r2 || sel.c1 !== sel.c2);
    const target = fill ? { ...sel } : { r1: at.r, c1: at.c, r2: at.r + h - 1, c2: at.c + w - 1 };
    mutate(() => {
      if (clip && clip.cut) {  // 잘라내기 - 원래 자리를 비운다(같은 탭 안)
        const src = S.deck.sheets.find((s) => s.id === clip.ti);
        if (src) eachCell(clip.g, (r, c, k) => { if (!(src === sh && inRange(target, r, c))) delete src.cells[k]; });
      }
      eachCell(target, (r, c, k) => {
        const sr = (r - target.r1) % h, scc = (c - target.c1) % w;
        if (clip) {
          let v = grid[sr][scc]; if (v == null) { delete sh.cells[k]; return; }
          v = clone(v);
          if (typeof v === "object" && v.f && !clip.cut) v.f = shiftFormula(v.f, r - (clip.g.r1 + sr), c - (clip.g.c1 + scc));
          sh.cells[k] = v;
        } else {
          const t = (grid[sr] || [])[scc]; setInput(sh, k, t == null ? "" : t);
        }
      });
      growSize(sh, target.r2, target.c2);
      if (clip && clip.cut) S.clip = null;
      S.sel = target; S.cur = { r: target.r1, c: target.c1 }; S.anchor = { ...S.cur };
    });
  }

  // ---------------------------------------------------------------- 탭
  // ---------------------------------------------------------------- 채우기 핸들 - 선택 오른쪽 아래 사각을 끌어 엑셀처럼 채운다
  // 숫자 2개 이상은 직선 추세(최소제곱), 숫자 1개는 복사(Ctrl = 1씩 증가 - 날짜는 반대로 기본이 1일씩), 글+숫자(항목1)·요일·월 목록은 이어서,
  // 수식은 상대 참조 이동($ 고정), 서식은 원본 칸을 돌아가며 복사. 범위 안으로 되끌면 빠지는 칸의 값을 지운다. 두 번 누르면 옆 열 데이터 끝까지 아래로.
  const FILL_LISTS = [
    ["일", "월", "화", "수", "목", "금", "토"], ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"],
    ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"], ["1분기", "2분기", "3분기", "4분기"],
  ];
  const mod = (a, n) => ((a % n) + n) % n;
  const isDateFmt = (f) => !!f && /[yd]/i.test(f.replace(/"[^"]*"/g, "")) && !/[#0]/.test(f.replace(/"[^"]*"/g, ""));
  function fillKind(o) {
    if (o.f) return { k: "f" };
    const v = o.v;
    if (typeof v === "number") return { k: "n", v, date: isDateFmt(o.fmt) };
    if (typeof v === "string" && v !== "") {
      for (const L of FILL_LISTS) { const i = L.findIndex((x) => x.toLowerCase() === v.toLowerCase()); if (i >= 0) return { k: "l", L, i, up: v.length > 1 && v === v.toUpperCase() && v !== v.toLowerCase() }; }
      const m = /^(.*?)(\d+)(\D*)$/.exec(v);  // 마지막 숫자를 늘린다(엑셀과 같이) - 앞자리 0 은 자릿수 유지
      if (m) return { k: "t", pre: m[1], num: +m[2], post: m[3], w: m[2][0] === "0" ? m[2].length : 0 };
    }
    return { k: "s" };
  }
  function trend(ys) {  // 최소제곱 직선 a + b·x (x = 0..n-1)
    const n = ys.length, mx = (n - 1) / 2, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sxx = 0; ys.forEach((y, x) => { sxy += (x - mx) * (y - my); sxx += (x - mx) ** 2; });
    const b = sxx ? sxy / sxx : 0; return { a: my - b * mx, b };
  }
  /** 한 줄(원본 src[0..n-1])을 위치 ks(원본 첫 칸 기준, 앞으로는 n…, 뒤로는 -1…)로 늘린 셀 객체들 */
  function fillSeries(src, ks, ctrl, vert) {
    const n = src.length, K = src.map(fillKind);
    const base = (j) => { const o = { ...src[j] }; delete o.v; delete o.f; return o; };
    const all = (k) => K.every((x) => x.k === k);
    const line = (vals) => { if (n === 1) return (k) => fix(vals[0] + k); const { a, b } = trend(vals); return (k) => fix(a + b * k); };
    if (all("n") && (n === 1 ? K[0].date !== ctrl : !ctrl)) {
      const f = line(K.map((x) => x.v)); return ks.map((k) => ({ ...base(mod(k, n)), v: f(k) }));
    }
    if (!ctrl && all("l") && K.every((x) => x.L === K[0].L)) {
      const L = K[0].L, st = n === 1 ? 1 : mod(K[1].i - K[0].i, L.length);
      if (K.every((x, j) => !j || mod(x.i - K[j - 1].i, L.length) === st)) return ks.map((k) => { const w = L[mod(K[0].i + st * k, L.length)]; return { ...base(mod(k, n)), v: K[0].up ? w.toUpperCase() : w }; });
    }
    const tnum = (x, v) => x.pre + String(Math.abs(v)).padStart(x.w, "0") + x.post;
    if (!ctrl && all("t") && K.every((x) => x.pre === K[0].pre && x.post === K[0].post)) {
      const f = line(K.map((x) => x.num)); return ks.map((k) => ({ ...base(mod(k, n)), v: tnum(K[0], Math.round(f(k))) }));
    }
    return ks.map((k) => {  // 돌아가며 복사 - 수식은 상대 이동, 글+숫자는 한 바퀴마다 +1(Ctrl 이면 그대로)
      const j = mod(k, n), x = K[j], o = { ...src[j] };
      if (x.k === "f") { o.f = shiftFormula(src[j].f, vert ? k - j : 0, vert ? 0 : k - j); delete o.v; }
      else if (x.k === "t" && !ctrl) o.v = tnum(x, x.num + Math.floor(k / n));
      return o;
    });
  }
  /** 끌어 놓은 셀 → {axis r|c, dir ±1, area 채울(또는 지울) 범위, shrink} - 범위 밖으로 더 멀리 나간 축으로 */
  function fillTarget(g, r, c) {
    const outR = r > g.r2 ? r - g.r2 : r < g.r1 ? g.r1 - r : 0, outC = c > g.c2 ? c - g.c2 : c < g.c1 ? g.c1 - c : 0;
    if (!outR && !outC) {  // 범위 안 - 줄여서 빠지는 칸을 지운다
      if (g.r2 - r >= g.c2 - c && r < g.r2) return { axis: "r", shrink: true, area: { r1: r + 1, r2: g.r2, c1: g.c1, c2: g.c2 }, keep: { ...g, r2: r } };
      if (c < g.c2) return { axis: "c", shrink: true, area: { r1: g.r1, r2: g.r2, c1: c + 1, c2: g.c2 }, keep: { ...g, c2: c } };
      return null;
    }
    if (outR >= outC) return r > g.r2 ? { axis: "r", dir: 1, area: { r1: g.r2 + 1, r2: r, c1: g.c1, c2: g.c2 } } : { axis: "r", dir: -1, area: { r1: r, r2: g.r1 - 1, c1: g.c1, c2: g.c2 } };
    return c > g.c2 ? { axis: "c", dir: 1, area: { r1: g.r1, r2: g.r2, c1: g.c2 + 1, c2: c } } : { axis: "c", dir: -1, area: { r1: g.r1, r2: g.r2, c1: c, c2: g.c1 - 1 } };
  }
  const unionRange = (a, b) => ({ r1: Math.min(a.r1, b.r1), c1: Math.min(a.c1, b.c1), r2: Math.max(a.r2, b.r2), c2: Math.max(a.c2, b.c2) });
  /** 채울 값 계산 - [{k: 셀 주소, o: 셀 객체}] (줄마다 fillSeries) */
  function fillPlan(sh, g, t, ctrl) {
    const vert = t.axis === "r", n = vert ? g.r2 - g.r1 + 1 : g.c2 - g.c1 + 1, m = vert ? t.area.r2 - t.area.r1 + 1 : t.area.c2 - t.area.c1 + 1;
    const ks = Array.from({ length: m }, (_, i) => (t.dir > 0 ? n + i : -1 - i));
    const out = [];
    for (let L = vert ? g.c1 : g.r1; L <= (vert ? g.c2 : g.r2); L++) {
      const at = (j) => (vert ? key(g.r1 + j, L) : key(L, g.c1 + j));
      const src = Array.from({ length: n }, (_, j) => cellObj(sh, at(j)));
      fillSeries(src, ks, ctrl, vert).forEach((o, i) => out.push({ k: at(ks[i]), o }));
    }
    return out;
  }
  function doFill(g, t, ctrl) {
    if (t.shrink) { clearRange(t.area); S.sel = t.keep; renderSel(); return; }
    mutate(() => {
      const sh = sheet();
      for (const { k, o } of fillPlan(sh, g, t, ctrl)) putCell(sh, k, o);
      growSize(sh, Math.max(g.r2, t.area.r2), Math.max(g.c2, t.area.c2));
    });
    S.sel = unionRange(g, t.area); renderSel();
  }
  function startFill(e) {
    e.preventDefault(); e.stopPropagation();
    if (S.edit) endEdit(true);
    const g = clampRange(S.sel), box = $("#fillBox"), tip = $("#fillTip"), H = $("#fillHandle");
    let tgt = null;
    H.style.pointerEvents = "none";
    const onMove = (ev) => {
      const el = document.elementFromPoint(ev.clientX, ev.clientY), d = el && el.closest("td[data-r]"); if (!d) return;
      tgt = fillTarget(g, +d.dataset.r, +d.dataset.c);
      if (!tgt) { box.hidden = tip.hidden = true; return; }
      place(box, tgt.shrink ? tgt.area : unionRange(g, tgt.area)); box.classList.toggle("shrink", !!tgt.shrink); box.hidden = false;
      if (tgt.shrink) { tip.hidden = true; return; }
      const a = tgt.area, lastK = tgt.axis === "r" ? key(tgt.dir > 0 ? a.r2 : a.r1, g.c1) : key(g.r1, tgt.dir > 0 ? a.c2 : a.c1);  // 미리보기 글 - 첫 줄의 마지막 칸 값
      const p = fillPlan(sheet(), g, tgt, ev.ctrlKey || ev.metaKey).find((x) => x.k === lastK), R = $("#gridIn").getBoundingClientRect();
      tip.textContent = p ? p.o.f || display(p.o) : "";
      tip.hidden = !tip.textContent; tip.style.left = (ev.clientX - R.left) / Z + 14 + "px"; tip.style.top = (ev.clientY - R.top) / Z + 16 + "px";
    };
    const onUp = (ev) => {
      removeEventListener("mousemove", onMove); removeEventListener("mouseup", onUp);
      box.hidden = tip.hidden = true; H.style.pointerEvents = "";
      if (tgt) doFill(g, tgt, ev.ctrlKey || ev.metaKey);
      focusGrid();
    };
    addEventListener("mousemove", onMove); addEventListener("mouseup", onUp);
  }
  /** 핸들 두 번 누르기 - 왼쪽(없으면 오른쪽) 이웃 열의 이어진 데이터 끝까지 아래로 채운다 */
  function fillDownAuto() {
    if (S.edit) endEdit(true);
    const sh = sheet(), g = clampRange(S.sel);
    const has = (r, c) => { if (c < 0) return false; const o = cellObj(sh, key(r, c)); return !!o.f || (o.v != null && o.v !== ""); };
    const col = has(g.r2 + 1, g.c1 - 1) ? g.c1 - 1 : has(g.r2 + 1, g.c2 + 1) ? g.c2 + 1 : -1;
    if (col < 0) return;
    let end = g.r2; while (has(end + 1, col)) end++;
    doFill(g, { axis: "r", dir: 1, area: { r1: g.r2 + 1, r2: end, c1: g.c1, c2: g.c2 } }, false);
  }

  function newTabId() { const ids = new Set(S.deck.sheets.map((s) => s.id)); for (let i = 1; ; i++) { const id = "t" + String(i).padStart(2, "0"); if (!ids.has(id)) return id; } }
  function newTabName() { const ns = new Set(S.deck.sheets.map((s) => s.name.toLowerCase())); for (let i = S.deck.sheets.length + 1; ; i++) if (!ns.has("sheet" + i)) return "Sheet" + i; }
  function switchTab(i) { if (S.edit) endEdit(true); if (i === S.ti) return; S.ti = i; S.drawSel = null; renderGrid(); renderTabs(); selectRange({ r1: 0, c1: 0, r2: 0, c2: 0 }); $("#gridWrap").scrollTo(0, 0); renderReqs(); focusGrid(); }
  /** 테마 페이지(표지·이력·…)를 새 탭으로 - {{자리}} 는 문서 정보(vars)로 채운다 */
  function addThemePage(pg) {
    mutate(() => {
      const t = fillVars(clone(pg), docVars()); delete t.id;
      const ns = new Set(S.deck.sheets.map((s) => s.name.toLowerCase()));
      let name = String(t.name || pg.kind || "Sheet").slice(0, 31); for (let i = 2; ns.has(name.toLowerCase()); i++) name = `${String(t.name || "Sheet").slice(0, 26)} (${i})`;
      const tab = normSheet({ ...t, id: newTabId(), name }, S.deck.sheets.length);
      S.deck.sheets.push(tab); S.ti = S.deck.sheets.length - 1;
      S.sel = { r1: 0, c1: 0, r2: 0, c2: 0 }; S.cur = { r: 0, c: 0 }; S.anchor = { r: 0, c: 0 };
    });
  }
  function addTabMenu(btn) {
    const pages = (theme() && theme().pages) || [];
    if (!pages.length) { addTab(); return; }
    openMenu(btn, [{ label: "빈 탭", act: addTab }, { h: `테마 페이지 - ${theme().label || TH.name}` }, ...pages.map((pg) => ({ label: `${pg.name || pg.kind}${pg.kind && pg.kind !== pg.name ? ` (${pg.kind})` : ""}`, act: () => addThemePage(pg) }))]);
  }
  function addTab() { mutate(() => { S.deck.sheets.push({ id: newTabId(), name: newTabName(), cells: {} }); S.ti = S.deck.sheets.length - 1; S.sel = { r1: 0, c1: 0, r2: 0, c2: 0 }; S.cur = { r: 0, c: 0 }; S.anchor = { r: 0, c: 0 }; }); }
  function renameTab(i) {
    const b = $(`#tabs [data-ti="${i}"]`); if (!b) return;
    const sh = S.deck.sheets[i], inp = document.createElement("input"); inp.value = sh.name; b.replaceWith(inp); inp.focus(); inp.select();
    let done = false;
    const fin = (ok) => {
      if (done) return; done = true;
      const v = inp.value.trim();
      if (ok && v && v !== sh.name) {
        if (/[\\/?*[\]:]/.test(v) || v.length > 31) { toast("탭 이름에는 \\ / ? * [ ] : 를 쓸 수 없고 31자까지입니다(엑셀 규칙)", 4000); renderTabs(); return; }
        if (S.deck.sheets.some((s, j) => j !== i && s.name.toLowerCase() === v.toLowerCase())) { toast("같은 이름의 탭이 있습니다"); renderTabs(); return; }
        const old = sh.name;
        mutate(() => {  // 다른 탭 수식의 '옛이름!' 참조도 새 이름으로
          sh.name = v;
          const q = /^[\p{L}_][\p{L}\p{N}_.]*$/u.test(v) ? v : `'${v.replace(/'/g, "''")}'`;
          for (const s2 of S.deck.sheets) for (const raw of Object.values(s2.cells)) {
            if (!raw || typeof raw !== "object" || !raw.f) continue;
            let toks; try { toks = tokenize(raw.f.slice(1)); } catch (e) { continue; }
            let out = "", last = 0; const src = raw.f.slice(1);
            for (const t of toks) if (t.t === "ref" && t.sheet && t.sheet.toLowerCase() === old.toLowerCase()) { out += src.slice(last, t.s) + q + "!"; last = t.ss; }
            raw.f = "=" + out + src.slice(last);
          }
        });
      } else renderTabs();
    };
    inp.addEventListener("keydown", (e) => { if (e.isComposing) return; if (e.key === "Enter") fin(true); if (e.key === "Escape") fin(false); });
    inp.addEventListener("blur", () => fin(true));
  }
  function tabMenu(e, i) {
    e.preventDefault();
    const sh = S.deck.sheets[i], n = S.deck.sheets.length;
    openMenu({ x: e.clientX, y: e.clientY }, [
      { h: `${sh.name} · id ${sh.id}` },
      { label: "이름 바꾸기", act: () => renameTab(i) },
      { label: "왼쪽으로 옮기기", disabled: i === 0, act: () => mutate(() => { const a = S.deck.sheets; [a[i - 1], a[i]] = [a[i], a[i - 1]]; S.ti = i - 1; }) },
      { label: "오른쪽으로 옮기기", disabled: i === n - 1, act: () => mutate(() => { const a = S.deck.sheets; [a[i + 1], a[i]] = [a[i], a[i + 1]]; S.ti = i + 1; }) },
      { label: "복제", act: () => mutate(() => { const c = clone(sh); c.id = newTabId(); c.name = (sh.name + " (2)").slice(0, 31); S.deck.sheets.splice(i + 1, 0, c); S.ti = i + 1; }) },
      "-",
      { label: "탭 삭제", disabled: n <= 1, act: () => { if (!confirm(`탭 "${sh.name}" 을 지울까요? (Ctrl+Z 로 되돌릴 수 있습니다)`)) return; mutate(() => { S.deck.sheets.splice(i, 1); S.ti = Math.max(0, Math.min(S.ti, S.deck.sheets.length - 1)); }); } },
    ]);
  }

  // ---------------------------------------------------------------- 요청 - 범위(range)와 글. 세션이 sheets[].cells 를 고치고 done + reply(docs/sheets.md 3절)
  // 목록·카드·후속·첨부·기록 창·동기화는 nexa-requests.js(RQ, 편집기와 같은 뿌리 - docs/collab.md 0단계). 여기는 시트 쪽 대상(탭·범위)과 머리(대상 표시·보내기)만
  let RQ = null;
  const ST = { draft: "초안", open: "대기", working: "처리 중", done: "완료" };
  const activeReqs = () => S.reqs.filter((q) => q.status !== "done");
  /** 요청의 탭 id - 후속 요청(parent)에 slide 가 없으면 뿌리 요청(thread)의 것 */
  const reqSlide = (q) => (RQ ? RQ.rootOf(q) : q).slide || null;
  async function loadReqs() { if (RQ) await RQ.load(); }
  function reqTargetRange() { return $("#reqWhole").checked || S.drawSel ? null : rangeName(clampRange(S.sel)); }
  const reqDraws = () => (S.drawSel && !$("#reqWhole").checked ? [...S.drawSel] : null);
  const drawLabel = (ids) => (ids.length > 1 ? `그림 ${ids[0]} 외 ${ids.length - 1}` : `그림 ${ids[0]}`);
  function renderReqTarget() {
    const t = reqTargetRange(), ds = reqDraws(); $("#reqTarget").textContent = `${sheet().name}${ds ? " · " + drawLabel(ds) : t ? "!" + t : " (탭 전체)"}`;
  }
  const typedKey = () => `typed-${NS}${S.id}/sheet`;
  const tabName = (sid) => { const s = S.deck && S.deck.sheets.find((x) => x.id === sid); return s ? s.name : sid || "?"; };
  /** 시트 대상 어댑터(RQ) - 탭 · 범위 */
  const SHEET_TARGET = {
    scope: "탭", key: (r) => r.slide, current: () => sheet().id, num: (r) => S.deck.sheets.findIndex((s) => s.id === r.slide) + 1,
    label: (r) => `${tabName(r.slide)}${r.elements && r.elements.length ? " · " + drawLabel(r.elements) : r.range ? "!" + r.range : " (탭 전체)"}`,
    goto: (r) => gotoReq(r),
    extra: (r) => aiDiffHtml(r),  // 완료된 요청 - AI 가 바꾼 셀 n개 · 보기 · 되돌리기
  };
  /** 요청의 탭·범위로 - 카드를 누르거나 카드의 대상 링크 */
  function gotoReq(q) {
    const root = RQ.rootOf(q); S.reqCur = q.id;
    const i = S.deck.sheets.findIndex((s) => s.id === root.slide); if (i >= 0 && i !== S.ti) switchTab(i);
    const g = parseRange(root.range); if (g) selectRange(clampRange(g)); else renderSel();
    S.drawSel = root.elements && root.elements.length ? new Set(root.elements) : null; markDrawings(); renderReqTarget();
    if (S.drawSel) { const im = $(`#draws img.drw[data-did="${CSS.escape(root.elements[0])}"]`); if (im) im.scrollIntoView({ block: "nearest", inline: "nearest" }); }
    renderReqs(); focusGrid();
  }
  function renderReqs() {
    if (!S.deck || !RQ) return;
    // 기본 보기 = 최근 24시간에 진행된 것 + 끝나지 않은 것(편집기와 같은 규칙) · 이 탭 / 최근 · 이전 것은 [더보기]
    const recent = S.reqs.filter(RQ.recent), older = S.reqs.length - recent.length;
    const list = recent.filter((q) => !S.reqTab || reqSlide(q) === sheet().id);
    $("#reqFilter").innerHTML = `<span class="seg"><button data-v="1" class="${S.reqTab ? "on" : ""}">이 탭</button><button data-v="0" class="${S.reqTab ? "" : "on"}">최근 (${recent.length})</button></span><span style="flex:1"></span><button class="chip sm" id="reqMore" title="이전 요청까지 모두 찾아보기(편집 화면 위에 뜹니다)">더보기${older ? ` · 이전 ${older}` : ""}</button>`;
    $("#reqList").innerHTML = (older ? `<div class="hint" style="font-size:11.5px;margin:2px 4px 6px">최근 24시간에 진행된 요청과 아직 끝나지 않은 요청만 보입니다 - 이전 것은 [더보기]</div>` : "")
      + (list.length ? RQ.threadsHtml(list) : `<div class="hint" style="padding:18px;text-align:center">${S.reqTab ? "이 탭에 최근 요청이 없습니다" : "최근 요청이 없습니다"}<br>셀 범위를 고르고 위에 적어 보내세요.</div>`);
    if (S.reqCur) { const c = $(`#reqList .req[data-rid="${CSS.escape(S.reqCur)}"]`); if (c) c.classList.add("cur"); }
    $("#reqHint").innerHTML = RQ.sessionHint();
    RQ.afterRender();
  }
  async function sendReq() {
    const text = $("#reqText").value.trim(); if (!text && !RQ.att.slot("tab").length) { $("#reqText").focus(); return; }
    if (S.edit) endEdit(true);
    if (S.dirty) await save();  // 세션이 지금 화면 내용을 보고 고치게 먼저 저장
    const body = { action: "add", status: "open", slide: sheet().id, text: text || "(첨부 참고)" };
    const rg = reqTargetRange(); if (rg) body.range = rg;
    const ds = reqDraws(); if (ds) { body.elements = ds; body.element = ds[0]; }  // 고른 그림(슬라이드 요청의 element·elements 와 같은 칸) - 세션은 탭 drawings 에서 id(또는 파일 이름)로 찾는다
    const r = await RQ.add(body, "tab", { flush: true }); if (!r) return;
    $("#reqText").value = ""; LS.set(typedKey(), "");
    toast(RQ.connected() ? "요청을 세션에 보냈습니다" : "요청을 남겼습니다 - 세션이 연결되면 전달됩니다");
  }
  // ---- AI 가 바꾼 셀 - 요청 하나로 AI 가 저장한 변경(/api/reqdiff, 원장 백업 비교). 카드에 "바뀐 셀 n개 · 보기 · 되돌리기",
  //      이 화면을 연 동안 요청이 완료되면 그 셀을 초록 테두리로 강조한다. 되돌리기는 그 뒤 아무도 고치지 않은 셀만(지금 값 = AI 가 넣은 값)
  const AI = { diff: {}, hl: null, prev: null };
  async function loadAiDiff(rid) {
    if (AI.diff[rid] && AI.diff[rid] !== "loading") return AI.diff[rid];
    AI.diff[rid] = "loading";
    const r = await api("GET", `/api/reqdiff/${encodeURIComponent(S.id)}?request=${encodeURIComponent(rid)}`);
    AI.diff[rid] = r.ok ? r.data : { found: false };
    renderReqs();
    return AI.diff[rid];
  }
  function aiDiffHtml(r) {
    if (r.status !== "done") return "";
    const D = AI.diff[r.id];
    if (D === undefined) { loadAiDiff(r.id); return ""; }
    if (D === "loading" || !D.found || !D.count) return "";
    const on = AI.hl && AI.hl.rid === r.id;
    return `<div class="aichg"><span>AI 가 바꾼 셀 <b>${D.count}</b>개</span><span style="flex:1"></span><button class="chip sm" data-aishow="${esc(r.id)}">${on ? "강조 끄기" : "보기"}</button><button class="chip sm" data-aiundo="${esc(r.id)}" title="그 뒤 아무도 고치지 않은 셀만 AI 전 값으로 (Ctrl+Z 로 다시)">되돌리기</button></div>`;
  }
  /** 바뀐 셀 강조 - 지금 탭에 없으면 바뀐 셀이 있는 첫 탭으로 */
  function showAi(rid, on) {
    const D = AI.diff[rid];
    if (!on || !D || !D.cells || !D.cells.length) { AI.hl = null; renderMarks(); renderReqs(); return; }
    AI.hl = { rid, cells: D.cells };
    if (!D.cells.some((c) => c.tab === sheet().id)) { const i = S.deck.sheets.findIndex((s) => s.id === D.cells[0].tab); if (i >= 0) switchTab(i); }
    const first = D.cells.find((c) => c.tab === sheet().id), p = first && parseRef(first.key);
    if (p) scrollIntoView(p.r, p.c);
    renderMarks(); renderReqs();
  }
  function aiUndo(rid) {
    const D = AI.diff[rid]; if (!D || !D.cells) return;
    const norm = (x) => (x == null ? null : typeof x === "object" ? x : { v: x });
    let done = 0, kept = 0;
    mutate(() => {
      for (const c of D.cells) {
        const sh = S.deck.sheets.find((t) => t.id === c.tab); if (!sh) { kept++; continue; }
        if (!NexaMerge.eq(norm(sh.cells[c.key]), norm(c.after))) { kept++; continue; }  // 그 뒤 누가 고쳤다 - 두기
        if (c.before == null) delete sh.cells[c.key]; else sh.cells[c.key] = JSON.parse(JSON.stringify(c.before));
        done++;
      }
    });
    AI.hl = null; renderMarks(); renderReqs();
    toast(`AI 가 바꾼 셀 ${done}개를 되돌렸습니다${kept ? ` · 그 뒤 고친 ${kept}개는 그대로` : ""} (Ctrl+Z 로 다시)`, 4500);
  }
  /** 요청 목록이 바뀔 때 - 이 화면을 연 동안 완료로 바뀐 요청이면 바뀐 셀을 강조하고 알린다 */
  async function aiWatch() {
    const now = Object.fromEntries(S.reqs.map((q) => [q.id, q.status]));
    const prev = AI.prev; AI.prev = now;
    if (!prev) return;  // 처음 열 때는 강조하지 않는다
    for (const q of S.reqs) {
      if (q.status !== "done" || !prev[q.id] || prev[q.id] === "done") continue;
      delete AI.diff[q.id];
      const D = await loadAiDiff(q.id);
      if (D && D.count) { showAi(q.id, true); AI.at = Date.now(); toast(`${RQ.agentName()} 가 셀 ${D.count}개를 바꿨습니다 - 초록 테두리 · 요청 카드에서 되돌리기`, 4500); }
    }
  }
  async function onReqClick(e) {
    const ab = e.target.closest("[data-aishow],[data-aiundo]");
    if (ab) { if (ab.dataset.aishow) showAi(ab.dataset.aishow, !(AI.hl && AI.hl.rid === ab.dataset.aishow)); else aiUndo(ab.dataset.aiundo); return; }
    if (await RQ.click(e)) return;  // 상태·삭제·후속·첨부·대상 링크 - 편집기와 같다
    const card = e.target.closest(".req"); if (!card || e.target.closest("button, a, textarea, input, details, .fu-form")) return;
    const q = S.reqs.find((x) => x.id === card.dataset.rid); if (q) gotoReq(q);  // 카드 → 그 탭·범위로
  }

  // ---------------------------------------------------------------- 내보내기·목록
  async function exportXlsx() {
    if (S.edit) endEdit(true);
    if (S.dirty) await save();
    const b = $("#exportBtn"); b.disabled = true; const t0 = b.textContent; b.textContent = "내보내는 중…";
    try {
      const r = await api("POST", `/api/export/${encodeURIComponent(S.id)}`);
      if (!r.ok || !r.data || !r.data.url) { toast("내보내기 실패: " + ((r.data && r.data.error) || r.status), 6000); return; }
      const a = document.createElement("a"); a.href = (r.data.url.startsWith("/") ? BASE : "") + r.data.url; a.download = r.data.name || `${S.deck.title || S.id}.xlsx`;
      document.body.appendChild(a); a.click(); a.remove();
      toast(`내보냈습니다: ${r.data.name || "xlsx"}`);
    } finally { b.disabled = false; b.textContent = t0; }
  }
  async function deckListMenu(btn) {
    const r = await api("GET", "/api/decks"); S.decks = r.ok && Array.isArray(r.data) ? r.data : [];
    const go = (d) => { location.href = d.kind === "sheet" ? `sheet.html?deck=${encodeURIComponent(d.id)}` : `index.html#${encodeURIComponent(d.id)}`; };
    openMenu(btn, [{ h: `덱·시트 ${S.decks.length}개` },
      ...S.decks.map((d) => ({ label: `${d.kind === "sheet" ? "▦ " : d.start ? "★ " : ""}${d.title || d.id}${d.kind === "sheet" ? "" : ` (${d.slides}장)`}`, on: d.id === S.id, act: () => { if (d.id !== S.id) leave(() => go(d)); } })),
      "-", { label: "새 시트", act: newSheet }]);
  }
  async function newSheet() {
    if (window.NexaSheetNew) { const id = await NexaSheetNew.open(); if (id) leave(() => { location.href = `sheet.html?deck=${encodeURIComponent(id)}`; }); return; }
    const title = (prompt("새 시트 제목", "") || "").trim(); if (!title) return;
    const r = await api("POST", "/api/decks", { action: "create", kind: "sheet", title });
    if (!r.ok || !r.data || !r.data.id) { toast("시트를 만들지 못했습니다: " + ((r.data && r.data.error) || r.status), 6000); return; }
    leave(() => { location.href = `sheet.html?deck=${encodeURIComponent(r.data.id)}`; });
  }
  async function leave(fn) { if (S.edit) endEdit(true); if (S.dirty && !S.conflict) await save(); fn(); }

  // ---------------------------------------------------------------- HYPERLINK 따라가기 - "#탭!A1"·"#'탭 이름'!A1:B2"·"#A1"(이 탭)·"#이름"(이름 정의) · 웹 주소는 새 탭
  const HL_RE = /\bHYPERLINK\s*\(/i;
  function followCell(r, c) {
    const raw = sheet().cells[key(r, c)];
    if (!raw || typeof raw !== "object" || !raw.f || !HL_RE.test(raw.f) || !window.NexaCalc) return false;
    const u = NexaCalc.link(S.deck, sheet().id, key(r, c));
    if (u) followHref(u); else toast("링크 주소를 계산하지 못했습니다");
    return true;
  }
  const tabIndex = (name) => S.deck.sheets.findIndex((s) => s.id === name || String(s.name).toLowerCase() === name.replace(/''/g, "'").toLowerCase());
  function followHref(u) {
    u = String(u).trim();
    if (u.startsWith("#")) {
      const m = /^#(?:'((?:[^']|'')+)'!|([^'!]+)!)?(.+)$/.exec(u); if (!m) { toast(`찾을 수 없는 링크 대상: ${u}`); return; }
      let name = m[1] || m[2] || null, g = parseRange(m[3].replace(/\$/g, ""));
      if (!g && !name) {  // 이름 정의 - 탭 것이 먼저(계산기 named 와 같다)
        const nm = m[3].toUpperCase(), def = [sheet().names, S.deck.names].map((b) => b || {}).map((b) => b[Object.keys(b).find((x) => x.toUpperCase() === nm)]).find((x) => x != null);
        const d = def != null && /^=?(?:'((?:[^']|'')+)'!|([^'!]+)!)?(\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)$/.exec(String(def).trim());
        if (d) { name = d[1] || d[2] || null; g = parseRange(d[3].replace(/\$/g, "")); }
      }
      const ti = name ? tabIndex(name) : S.ti;
      if (ti < 0 || !g) { toast(`찾을 수 없는 링크 대상: ${u}`); return; }
      switchTab(ti); selectRange(g); focusGrid(); return;
    }
    if (/^(https?:|mailto:|ftp:)/i.test(u)) { window.open(u, "_blank", "noopener"); return; }
    if (/^www\./i.test(u)) { window.open("https://" + u, "_blank", "noopener"); return; }
    toast(`열 수 없는 링크 주소: ${u}`);
  }

  // ---------------------------------------------------------------- 끌기(범위 선택·열 너비·행 높이·패널 폭)
  function onGridDown(e) {
    if (e.button !== 0 && e.button !== 2) return;
    if (e.button === 0 && e.target.closest("#fillHandle")) { startFill(e); return; }
    const rzc = e.target.closest("[data-rzc]"), rzr = e.target.closest("[data-rzr]");
    if (rzc || rzr) { e.preventDefault(); startResize(e, rzc ? "c" : "r", +(rzc || rzr).dataset[rzc ? "rzc" : "rzr"]); return; }
    const td = e.target.closest("td[data-r]"), thc = e.target.closest("th[data-col]"), thr = e.target.closest("th[data-row]");
    if (e.target.closest("th.corner")) { e.preventDefault(); S.anchor = { r: 0, c: 0 }; S.sel = { r1: 0, c1: 0, r2: G.rows - 1, c2: G.cols - 1 }; renderSel(); focusGrid(); return; }
    const im2 = e.button === 2 && e.target.closest("#draws img.drw");
    if (im2) { if (S.edit) endEdit(true); if (!(S.drawSel && S.drawSel.has(im2.dataset.did))) drawPick(im2.dataset.did, false); return; }  // 그림 오른쪽 클릭 - 고르고 그림 메뉴(gridMenu)
    if (e.button === 2) {  // 오른쪽 클릭 - 선택 밖이면 그 셀로 옮기고 메뉴
      if (td && !inRange(S.sel, +td.dataset.r, +td.dataset.c)) { if (S.edit) endEdit(true); selectCell(+td.dataset.r, +td.dataset.c); }
      return;
    }
    if (td && wantsRef()) {  // 수식 입력 중 - 누른 셀의 주소를 넣는다
      e.preventDefault(); const r0 = +td.dataset.r, c0 = +td.dataset.c;
      insertRef(key(r0, c0));
      const startPos = ED().selectionStart - key(r0, c0).length;
      const onMove = (ev) => {
        const t = document.elementFromPoint(ev.clientX, ev.clientY); const d = t && t.closest("td[data-r]"); if (!d) return;
        const g = { r1: Math.min(r0, +d.dataset.r), c1: Math.min(c0, +d.dataset.c), r2: Math.max(r0, +d.dataset.r), c2: Math.max(c0, +d.dataset.c) };
        const ed = ED(), txt = rangeName(g), cur = ed.selectionStart; ed.value = ed.value.slice(0, startPos) + txt + ed.value.slice(cur); const n = startPos + txt.length; ed.setSelectionRange(n, n); placeEditor(); $("#fxIn").value = ed.value;
      };
      const onUp = () => { removeEventListener("mousemove", onMove); removeEventListener("mouseup", onUp); };
      addEventListener("mousemove", onMove); addEventListener("mouseup", onUp);
      return;
    }
    const im = e.button === 0 && e.target.closest("#draws img.drw");
    if (im) { e.preventDefault(); if (S.edit) endEdit(true); const add = e.ctrlKey || e.metaKey || e.shiftKey; if (!(S.drawSel && S.drawSel.has(im.dataset.did) && !add)) drawPick(im.dataset.did, add); focusGrid(); if (!add) startDrawDrag(e, "move"); return; }  // 그림 고르기 · 끌어 옮기기 - 칸 선택은 그대로
    if (e.button === 0 && e.target.closest("#drawHandle")) { e.preventDefault(); startDrawDrag(e, "size"); return; }
    if (S.drawSel && !e.ctrlKey && !e.metaKey) { S.drawSel = null; markDrawings(); }  // 칸·머리를 누르면 그림 선택이 풀린다
    if (td && (e.ctrlKey || e.metaKey) && followCell(+td.dataset.r, +td.dataset.c)) { e.preventDefault(); return; }  // HYPERLINK 칸 - 엑셀은 그냥 클릭이지만 여기는 고르기·고치기가 먼저라 Ctrl
    if (S.edit) endEdit(true);
    e.preventDefault(); focusGrid();
    let mode;
    if (td) { mode = "cell"; selectCell(+td.dataset.r, +td.dataset.c, e.shiftKey); }
    else if (thc) { mode = "col"; const c = +thc.dataset.col; if (!e.shiftKey) S.anchor = { r: 0, c }; S.cur = { r: 0, c: e.shiftKey ? S.cur.c : c }; S.sel = { r1: 0, r2: G.rows - 1, c1: Math.min(S.anchor.c, c), c2: Math.max(S.anchor.c, c) }; renderSel(); }
    else if (thr) { mode = "row"; const r = +thr.dataset.row; if (!e.shiftKey) S.anchor = { r, c: 0 }; S.cur = { r: e.shiftKey ? S.cur.r : r, c: 0 }; S.sel = { c1: 0, c2: G.cols - 1, r1: Math.min(S.anchor.r, r), r2: Math.max(S.anchor.r, r) }; renderSel(); }
    else return;
    const onMove = (ev) => {
      const t = document.elementFromPoint(ev.clientX, ev.clientY); if (!t) return;
      if (mode === "cell") { const d = t.closest("td[data-r]"); if (d) { const r = +d.dataset.r, c = +d.dataset.c; if (!S.ext || S.ext.r !== r || S.ext.c !== c) selectCell(r, c, true); } }
      if (mode === "col") { const d = t.closest("th[data-col], td[data-c]"); if (d) { const c = +(d.dataset.col ?? d.dataset.c); S.sel = { r1: 0, r2: G.rows - 1, c1: Math.min(S.anchor.c, c), c2: Math.max(S.anchor.c, c) }; renderSel(); } }
      if (mode === "row") { const d = t.closest("th[data-row], td[data-r]"); if (d) { const r = +(d.dataset.row ?? d.dataset.r); S.sel = { c1: 0, c2: G.cols - 1, r1: Math.min(S.anchor.r, r), r2: Math.max(S.anchor.r, r) }; renderSel(); } }
    };
    const onUp = () => { removeEventListener("mousemove", onMove); removeEventListener("mouseup", onUp); S.ext = null; };
    addEventListener("mousemove", onMove); addEventListener("mouseup", onUp);
  }
  // ---------------------------------------------------------------- 열 너비·행 높이 자동 맞춤(엑셀 경계 두 번 누르기)
  let measureCtx = null;
  function textPx(o, txt) {
    measureCtx = measureCtx || document.createElement("canvas").getContext("2d");
    const fam = getComputedStyle(document.body).getPropertyValue("--font") || "sans-serif";
    measureCtx.font = `${o.i ? "italic " : ""}${o.b ? "700 " : ""}${+o.size || defSize()}pt ${fam}`;
    return Math.max(...String(txt).split("\n").map((t) => measureCtx.measureText(t).width));
  }
  const fitTargets = (axis, i) => { const g = S.sel, full = axis === "c" ? g.r1 === 0 && g.r2 === G.rows - 1 : g.c1 === 0 && g.c2 === G.cols - 1; const a = axis === "c" ? g.c1 : g.r1, b = axis === "c" ? g.c2 : g.r2; return full && i >= a && i <= b ? [...Array(b - a + 1)].map((_, k) => a + k) : [i]; };
  function autoFitCols(i) {
    const sh = sheet(), cover = new Set(merges(sh).flatMap((m) => (m.c1 === m.c2 ? [] : [...Array((m.r2 - m.r1 + 1) * (m.c2 - m.c1 + 1))].map((_, k) => key(m.r1 + Math.floor(k / (m.c2 - m.c1 + 1)), m.c1 + (k % (m.c2 - m.c1 + 1)))))));
    mutate(() => {
      for (const c of fitTargets("c", i)) {
        let w = 0;
        for (const [k, raw] of Object.entries(sh.cells)) { const p = parseRef(k); if (!p || p.c !== c || rowHidden(sh, p.r) || cover.has(k)) continue; const o = effCell(raw), t = display(o); if (t === "" || o.wrap) continue; w = Math.max(w, textPx(o, t)); }
        const px = Math.max(24, Math.ceil(w + 10)); sh.cols = sh.cols || {};
        if (!w || px === DEF_W) delete sh.cols[colName(c)]; else sh.cols[colName(c)] = px;
      }
      if (sh.cols && !Object.keys(sh.cols).length) delete sh.cols;
    });
  }
  function autoFitRows(i) {
    const sh = sheet();
    mutate(() => {
      for (const r of fitTargets("r", i)) {
        let h = 0;
        for (const [k, raw] of Object.entries(sh.cells)) { const p = parseRef(k); if (!p || p.r !== r) continue; const o = effCell(raw), t = display(o); if (t === "") continue; const lines = o.wrap ? Math.max(1, Math.ceil(textPx(o, t) / Math.max(10, colW(sh, p.c) - 8))) : String(t).split("\n").length; h = Math.max(h, Math.ceil(lines * (+o.size || defSize()) * 1.333 * 1.25 + 6)); }
        sh.rows = sh.rows || {};
        if (!h || h <= DEF_H) delete sh.rows[String(r + 1)]; else sh.rows[String(r + 1)] = h;
      }
      if (sh.rows && !Object.keys(sh.rows).length) delete sh.rows;
    });
  }
  function startResize(e, axis, i) {
    const sh = sheet(), x0 = axis === "c" ? e.clientX : e.clientY, w0 = axis === "c" ? colW(sh, i) : rowH(sh, i);
    // 여러 열(행)이 골라져 있고 그 안의 경계를 끌면 고른 것 모두 같은 크기로
    const g = S.sel, all = axis === "c" ? (g.r1 === 0 && g.r2 === G.rows - 1 && i >= g.c1 && i <= g.c2 ? [...Array(g.c2 - g.c1 + 1)].map((_, k) => g.c1 + k) : [i])
      : (g.c1 === 0 && g.c2 === G.cols - 1 && i >= g.r1 && i <= g.r2 ? [...Array(g.r2 - g.r1 + 1)].map((_, k) => g.r1 + k) : [i]);
    let snap = false, last = w0;
    const onMove = (ev) => {
      const v = Math.max(axis === "c" ? 24 : 16, Math.round(w0 + ((axis === "c" ? ev.clientX : ev.clientY) - x0) / Z)); if (v === last) return; last = v;
      if (!snap) { snapshot(); snap = true; }
      for (const j of all) { if (axis === "c") { sh.cols = sh.cols || {}; if (v === DEF_W) delete sh.cols[colName(j)]; else sh.cols[colName(j)] = v; } else { sh.rows = sh.rows || {}; if (v === DEF_H) delete sh.rows[String(j + 1)]; else sh.rows[String(j + 1)] = v; } }
      renderGrid(); renderSel();
    };
    const onUp = () => {
      removeEventListener("mousemove", onMove); removeEventListener("mouseup", onUp);
      if (sh.cols && !Object.keys(sh.cols).length) delete sh.cols; if (sh.rows && !Object.keys(sh.rows).length) delete sh.rows;
      if (snap) { S.dirty = true; setStatus("dirty", "저장 대기"); scheduleSave(); }
    };
    addEventListener("mousemove", onMove); addEventListener("mouseup", onUp);
  }
  // ---------------------------------------------------------------- 메모(엑셀 메모 · Shift+F2)
  function noteEdit() {
    if (S.edit) endEdit(true);
    const sh = sheet(), k = key(S.cur.r, S.cur.c), cur = cellObj(sh, k).note || "";
    document.querySelectorAll(".notePop").forEach((x) => x.remove());
    const td = $(`#grid td[data-r="${S.cur.r}"][data-c="${S.cur.c}"]`), R = td ? td.getBoundingClientRect() : { right: 200, top: 200 };
    const pop = document.createElement("div"); pop.className = "notePop";
    pop.innerHTML = `<b>${esc(sheet().name)}!${k} 메모</b><textarea rows="5" placeholder="메모 - 칸에 마우스를 올리면 보인다(엑셀 메모로 내보낸다)">${esc(cur)}</textarea><div class="acts">${cur ? '<button class="chip sm" data-n="del">지우기</button>' : ""}<span style="flex:1"></span><button class="chip sm" data-n="no">취소</button><button class="chip sm primary" data-n="ok">저장</button></div>`;
    Object.assign(pop.style, { left: Math.min(R.right + 6, innerWidth - 300) + "px", top: Math.min(R.top, innerHeight - 220) + "px" });
    document.body.appendChild(pop);
    const ta = $("textarea", pop); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
    const done = (v) => {
      pop.remove();
      if (v !== null && v !== cur) mutate(() => { const o = { ...cellObj(sheet(), k) }; if (v) o.note = v; else delete o.note; putCell(sheet(), k, o); });
      focusGrid();
    };
    pop.addEventListener("click", (e2) => { const b = e2.target.closest("[data-n]"); if (!b) return; done(b.dataset.n === "ok" ? ta.value.trim() : b.dataset.n === "del" ? "" : null); });
    pop.addEventListener("keydown", (e2) => { e2.stopPropagation(); if (e2.key === "Escape") done(null); if (e2.key === "Enter" && (e2.ctrlKey || e2.metaKey)) done(ta.value.trim()); });
  }
  // ---------------------------------------------------------------- 그림 넣기(붙여넣기·파일) - 작업 공간 그림 폴더에 올리고 지금 칸에 고정한 drawings
  async function insertImages(files) {
    const list = [...files].filter((f) => /^image\//.test(f.type)); if (!list.length) return false;
    if (S.edit) endEdit(true);
    const at = key(S.cur.r, S.cur.c), added = [];
    for (const f of list) {
      const data = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1] || ""); fr.readAsDataURL(f); });
      const r = await api("POST", "/api/image", { name: f.name || "붙여넣은 그림.png", type: f.type, data });
      if (!r.ok) { toast(`그림을 넣지 못했습니다: ${(r.data && r.data.error) || r.status}`); continue; }
      const dim = await new Promise((res) => { const im = new Image(); im.onload = () => res([im.naturalWidth, im.naturalHeight]); im.onerror = () => res([240, 160]); im.src = URL.createObjectURL(f); });
      const k = Math.min(1, 600 / Math.max(1, dim[0]), 400 / Math.max(1, dim[1]));
      added.push({ type: "image", id: "pic" + Date.now().toString(36) + added.length, src: r.data.src, at, dx: added.length * 16, dy: added.length * 16, w: Math.round(dim[0] * k), h: Math.round(dim[1] * k) });
    }
    if (!added.length) return true;
    mutate(() => { const sh = sheet(); sh.drawings = [...(sh.drawings || []), ...added]; });
    S.drawSel = new Set(added.map((d) => d.id)); markDrawings(); renderReqTarget();
    toast(`그림 ${added.length}개를 ${at} 에 넣었습니다 - 끌어 옮기기 · 모서리로 크기 · Delete 로 지우기`);
    return true;
  }
  function pickImages() { const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.multiple = true; inp.onchange = () => insertImages(inp.files); inp.click(); }
  function gridMenu(e) {
    const im = e.target.closest("#draws img.drw");
    if (im && window.NexaSheetSide) { e.preventDefault(); NexaSheetSide.drawMenu(e); return; }  // 그림 - 슬라이드 요소 메뉴처럼(sheetside.js)
    if (!e.target.closest("td, th")) return;
    e.preventDefault();
    const g = S.sel;
    openMenu({ x: e.clientX, y: e.clientY }, [
      { h: `${sheet().name}!${rangeName(g)}` },
      { label: "잘라내기", key: "Ctrl+X", act: () => { document.execCommand("cut") || copyRange(true); } },
      { label: "복사", key: "Ctrl+C", act: () => { document.execCommand("copy") || copyRange(); } },
      { label: "붙여넣기", key: "Ctrl+V", act: async () => { try { pasteText(await navigator.clipboard.readText()); } catch (er) { toast("Ctrl+V 로 붙여넣으세요(브라우저가 클립보드 읽기를 막았습니다)", 4000); } } },
      { label: "내용 지우기", key: "Delete", act: () => clearRange(g) },
      { label: "셀 서식…", key: "Ctrl+1", act: formatDialog },
      { label: "서식 지우기", act: () => mutate(() => { const sh = sheet(); eachCell(g, (r, c, k) => { const o = cellObj(sh, k); putCell(sh, k, { v: o.v, f: o.f }); }); }) },
      "-",
      { label: cellObj(sheet(), key(S.cur.r, S.cur.c)).note ? "메모 고치기…" : "메모 넣기…", key: "Shift+F2", act: noteEdit },
      ...(cellObj(sheet(), key(S.cur.r, S.cur.c)).note ? [{ label: "메모 지우기", act: () => mutate(() => { const sh = sheet(); eachCell(g, (r, c, k) => { const o = { ...cellObj(sh, k) }; if (o.note) { delete o.note; putCell(sh, k, o); } }); }) }] : []),
      { label: "그림 넣기…", act: pickImages },
      "-",
      { label: mergeAt(sheet(), S.cur.r, S.cur.c) ? "병합 해제" : "셀 병합", act: toggleMerge },
      { label: "행·열 삽입·삭제…", act: () => rowColMenu({ x: e.clientX, y: e.clientY }) },
      "-",
      { label: "이 범위에 AI 요청 남기기", act: () => { $("#reqWhole").checked = false; document.body.classList.remove("noside"); if (window.NexaSheetSide) NexaSheetSide.showTab("reqs"); renderReqTarget(); $("#reqText").focus(); } },
    ]);
  }

  // ---------------------------------------------------------------- 시작
  async function init() {
    if (window.NexaMenu && NexaMenu.mount) NexaMenu.mount($("#menuBtn")); else $("#menuBtn").remove();
    if (!S.id) { location.replace("index.html"); return; }
    $("#sizeSel").innerHTML = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36].map((n) => `<option value="${n}">${n}</option>`).join("");
    fillFmtSel("");
    if (LS.get("sheetNoSide", "0") === "1") document.body.classList.add("noside");
    { const w = +LS.get("sheetSideW", 0); if (w) document.documentElement.style.setProperty("--sideW", w + "px"); }
    { const c = await api("GET", "/api/config"); if (c.ok && c.data && c.data.brand && c.data.brand.logo) TH.brandLogo = "/" + String(c.data.brand.logo).replace(/^[/]+/, ""); }
    if (window.NexaSession) SESS = NexaSession.create({ api, toast, openMenu, esc, base: BASE, deckId: () => S.id, onChange: (st, changed) => { S.session = st; if (changed && S.deck) renderReqs(); } });
    $("#sessChip").onclick = (e) => (SESS ? SESS.menu(e.currentTarget) : null);  // 웹 세션 시작·끊기·모델·진행
    RQ = NexaRequests.create({ api, toast, esc, base: BASE, deckId: () => S.id, session: SESS,
      getReqs: () => S.reqs, setReqs: (l) => { S.reqs = l; }, onChange: () => { if (!S.deck) return; renderReqs(); renderMarks(); renderTabs(); aiWatch(); },
      target: SHEET_TARGET, att: { boxes: { tab: "#reqAtt", fu: "#fuAtt" } }, onDeckChanged: () => { pollAt = 0; poll(); } });
    { const [q, ss] = await Promise.all([api("GET", `/api/requests/${encodeURIComponent(S.id)}`), api("GET", "/api/session")]);
      if (q.ok && Array.isArray(q.data)) S.reqs = q.data; if (ss.ok && ss.data) renderSession(ss.data); }
    if (!(await loadDeck(false))) return;
    {  // 엑셀 가져오기 경고(그림·조건부 서식·배열 수식 등 - sheetnew.js 가 남김) - 한 번 보이고 지운다
      let w = ""; try { w = sessionStorage.getItem("nexaImportWarn") || ""; sessionStorage.removeItem("nexaImportWarn"); } catch (e) { /* 저장소 없음 */ }
      if (w) toast(`엑셀에서 가져오며 바뀐 것\n${w}`, 12000);
    }
    { const t = LS.get(typedKey(), ""); if (t) $("#reqText").value = t; }
    await loadReqs();
    { const v = await api("GET", `/api/version/${encodeURIComponent(S.id)}`); if (v.ok && v.data.session) renderSession(v.data.session, v.data.activity); }
    scrollIntoView(S.cur.r, S.cur.c); focusGrid();
    setInterval(poll, 2000);
    // 실시간 연결(동시 편집 2단계) - 바뀌면 바로 applyVersion · 함께 보는 사람은 격자 테두리와 머리줄 칩. 내 위치는 1초마다 보고 바뀐 때만 보낸다
    if (window.NexaLive) { LIVE = NexaLive.create({ api, base: BASE, deckId: () => S.id, tab: TAB, onVersion: (v) => applyVersion(v), onPresence: () => renderMarks(), chip: "#sessChip" }); setInterval(livePresence, 1000); }

    const W = $("#gridWrap");
    W.addEventListener("scroll", onGridScroll, { passive: true });
    W.addEventListener("mousedown", onGridDown);
    W.addEventListener("contextmenu", gridMenu);
    W.addEventListener("dblclick", (e) => {
      if (e.target.closest("#fillHandle")) { e.preventDefault(); fillDownAuto(); return; }
      const rz = e.target.closest("[data-rzc]"); if (rz) { e.preventDefault(); autoFitCols(+rz.dataset.rzc); return; }  // 열 경계 두 번 = 내용에 맞춤(고른 열 모두)
      const rr = e.target.closest("[data-rzr]"); if (rr) { e.preventDefault(); autoFitRows(+rr.dataset.rzr); return; }  // 행 경계 두 번 = 기본 높이(줄바꿈 칸은 줄 수만큼)
      const td = e.target.closest("td[data-r]"); if (td) { e.preventDefault(); startEdit("edit"); }
    });
    W.addEventListener("click", (e) => { if (!S.edit && !e.target.closest("button")) focusGrid(); });
    const ed = ED();
    ed.addEventListener("keydown", onEditorKey);
    ed.addEventListener("input", onEditorInput);
    ed.addEventListener("blur", (e) => { if (S.edit && e.relatedTarget !== $("#fxIn")) endEdit(true); });  // 다른 곳을 누르면 입력을 넣는다(수식 줄로 옮길 때만 이어서)
    ed.addEventListener("compositionstart", () => { if (!S.edit) { S.edit = { r: S.cur.r, c: S.cur.c, mode: "enter", orig: rawText(sheet(), key(S.cur.r, S.cur.c)) }; ed.classList.add("on"); placeEditor(); } });
    $("#addRows").onclick = () => addRows(20);
    document.addEventListener("copy", (e) => { if (document.activeElement !== ed || S.edit) return; e.preventDefault(); e.clipboardData.setData("text/plain", copyRange(false)); e.clipboardData.setData("text/html", copyHtml()); });  // HTML - 엑셀에 붙이면 서식도
    document.addEventListener("cut", (e) => { if (document.activeElement !== ed || S.edit) return; e.preventDefault(); e.clipboardData.setData("text/plain", copyRange(true)); e.clipboardData.setData("text/html", copyHtml()); });
    document.addEventListener("paste", (e) => {
      if (document.activeElement !== ed || S.edit) return; e.preventDefault();
      const t = e.clipboardData.getData("text/plain"), imgs = [...(e.clipboardData.files || [])].filter((f) => /^image\//.test(f.type));
      if (imgs.length && !t) { insertImages(imgs); return; }  // 그림만 있으면 지금 칸에 그림(엑셀과 같다)
      const mine = S.clip && t && t.replace(/\r\n?/g, "\n").replace(/\n$/, "") === S.clip.tsv.replace(/\r\n?/g, "\n");  // 이 화면에서 복사한 것 - 수식·서식 그대로(pasteText)
      const html = !mine && e.clipboardData.getData("text/html"), grid = html ? parseHtmlTable(html) : null;
      if (grid && grid.length && grid[0].length) { pasteHtml(grid); return; }  // 엑셀·웹 표 - 값 + 서식
      if (t) pasteText(t);
    });
    W.addEventListener("dragover", (e) => { if ([...(e.dataTransfer.items || [])].some((i) => i.kind === "file")) e.preventDefault(); });
    W.addEventListener("drop", (e) => { const fs2 = [...(e.dataTransfer.files || [])]; if (!fs2.some((f) => /^image\//.test(f.type))) return; e.preventDefault(); const td = document.elementFromPoint(e.clientX, e.clientY); const c = td && td.closest("td[data-r]"); if (c) selectCell(+c.dataset.r, +c.dataset.c); insertImages(fs2); });
    // 수식 줄
    const fx = $("#fxIn");
    fx.addEventListener("focus", () => { if (S.edit) { fx.value = ED().value; } });
    fx.addEventListener("input", () => { if (S.edit) { ED().value = fx.value; placeEditor(); } });
    fx.addEventListener("keydown", (e) => {
      if (e.isComposing) return;
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault(); const v = fx.value, k = key(S.cur.r, S.cur.c);
        if (S.edit) { S.edit = null; ED().classList.remove("on"); ED().value = ""; }
        if (v !== rawText(sheet(), k)) mutate(() => setInput(sheet(), k, v));
        focusGrid(); if (e.key === "Enter") advance(e.shiftKey ? -1 : 1, 0); else advance(0, e.shiftKey ? -1 : 1);
      }
      if (e.key === "Escape") { e.preventDefault(); if (S.edit) endEdit(false); fx.value = rawText(sheet(), key(S.cur.r, S.cur.c)); focusGrid(); }
    });
    $("#nameBox").addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return; e.preventDefault();
      let v = $("#nameBox").value.trim(), ti = S.ti;
      const m = /^(.+)!(.+)$/.exec(v); if (m) { const i = S.deck.sheets.findIndex((s) => s.name.toLowerCase() === m[1].replace(/^'|'$/g, "").toLowerCase()); if (i >= 0) ti = i; v = m[2]; }
      const g = parseRange(v.toUpperCase()); if (!g) { toast("셀 주소를 읽지 못했습니다 - 예: B3 · B2:D5 · Sheet2!A1"); return; }
      if (ti !== S.ti) switchTab(ti);
      const d = dims(sheet()); if (g.r2 >= d.rows || g.c2 >= d.cols) mutate(() => growSize(sheet(), g.r2, g.c2));
      selectRange(g); focusGrid();
    });
    // 서식 줄
    $("#tools").addEventListener("mousedown", (e) => { if (e.target.closest("button")) e.preventDefault(); });
    $("#tools").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-t]"); if (!b) return;
      if (S.edit) endEdit(true);
      const t = b.dataset.t;
      if (t === "b" || t === "i" || t === "u") toggleStyle(t);
      else if (t === "al") { const cur = cellObj(sheet(), key(S.cur.r, S.cur.c)).align; applyStyle({ align: cur === b.dataset.v ? undefined : b.dataset.v }); }
      else if (t === "wrap") toggleStyle("wrap");
      else if (t === "clearClr") applyStyle({ color: undefined, fill: undefined });
      else if (t === "merge") toggleMerge();
      else if (t === "rowcol") { rowColMenu(b); return; }
      else if (t === "freeze") toggleFreeze();
      else if (t === "grid") toggleGrid();
      else if (t === "border") { openMenu(b, [{ label: "모든 테두리", act: () => applyBorder("all") }, { label: "바깥 테두리", act: () => applyBorder("outline") }, { label: "아래 테두리", act: () => applyBorder("bottom") }, "-", { label: "테두리 없음", act: () => applyBorder("none") }]); return; }
      focusGrid();
    });
    $("#colorIn").addEventListener("change", (e) => { applyStyle({ color: e.target.value.toUpperCase() }); focusGrid(); });
    $("#fillIn").addEventListener("change", (e) => { applyStyle({ fill: e.target.value.toUpperCase() }); focusGrid(); });
    $("#sizeSel").addEventListener("change", (e) => { const n = +e.target.value; applyStyle({ size: n === defSize() ? undefined : n }); focusGrid(); });
    $("#styleSel").addEventListener("change", (e) => { applyStyle({ s: e.target.value || undefined }); focusGrid(); });
    $("#themeChip").onclick = (e) => themeMenu(e.currentTarget);
    $$("#tools [data-nf]").forEach((b) => b.addEventListener("click", () => { numFmt(b.dataset.nf); focusGrid(); }));
    $("#fmtSel").addEventListener("change", (e) => {
      let f = e.target.value;
      if (f === "__custom") { f = prompt("엑셀 표시 형식 - 예: #,##0\"원\" · 0.00% · yyyy.mm.dd", cellObj(sheet(), key(S.cur.r, S.cur.c)).fmt || ""); if (f == null) { renderToolState(); return; } f = f.trim(); }
      applyStyle({ fmt: f || undefined }); focusGrid();
    });
    // 탭
    $("#tabs").addEventListener("click", (e) => { if (e.target.closest("[data-addtab]")) { addTabMenu(e.target.closest("[data-addtab]")); return; } const b = e.target.closest("[data-ti]"); if (b) switchTab(+b.dataset.ti); });
    $("#tabs").addEventListener("dblclick", (e) => { const b = e.target.closest("[data-ti]"); if (b) renameTab(+b.dataset.ti); });
    $("#tabs").addEventListener("contextmenu", (e) => { const b = e.target.closest("[data-ti]"); if (b) tabMenu(e, +b.dataset.ti); });
    // 머리줄
    $("#undoBtn").onclick = () => { undo(); focusGrid(); }; $("#redoBtn").onclick = () => { redo(); focusGrid(); };
    $("#exportBtn").onclick = exportXlsx;
    $("#deckList").onclick = (e) => deckListMenu(e.currentTarget);
    $("#backLink").addEventListener("click", (e) => { if (S.dirty || S.edit) { e.preventDefault(); leave(() => { location.href = "index.html"; }); } });
    $("#sideBtn").onclick = () => { const off = document.body.classList.toggle("noside"); LS.set("sheetNoSide", off ? "1" : ""); };
    $("#bnTheirs").onclick = async () => { S.dirty = false; S.conflict = false; if (S.edit) endEdit(false); await reloadExternal("밖의 버전을 불러왔습니다(내 편집은 Ctrl+Z 로 복구)"); };
    $("#bnMine").onclick = async () => { S.conflict = false; if (S.edit) endEdit(true); await save(true); };
    // 요청 패널
    $("#reqList").addEventListener("click", onReqClick);
    $("#reqSend").onclick = sendReq;
    // 예시 칩 - 누르면 요청 칸에 문장을 넣는다(보내지는 않는다 - 고쳐 쓰고 Enter). 칸에 글이 있으면 다음 줄에 덧붙인다
    const CHIPS = ["합계 행 추가", "이 열은 % 형식으로", "빈칸은 0 으로", "머리글 굵게·채우기", "상위 3개 강조", "오류 칸 원인 설명"];
    $("#reqChips").innerHTML = CHIPS.map((t) => `<button type="button" data-chip="${esc(t)}">${esc(t)}</button>`).join("");
    $("#reqChips").addEventListener("click", (e) => {
      const b = e.target.closest("[data-chip]"); if (!b) return;
      const ta = $("#reqText"), cur = ta.value.trimEnd(), k = key(S.cur.r, S.cur.c), v = S.deck ? effCell(sheet().cells[k]).v : null;
      const line = b.dataset.chip === "오류 칸 원인 설명" && isErrStr(v) ? `${k} 의 ${v} 원인을 설명하고 고쳐 주세요` : b.dataset.chip;  // 지금 칸이 오류면 그 칸·오류로
      ta.value = cur ? `${cur}\n${line}` : line; ta.dispatchEvent(new Event("input")); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
    });
    // Enter = 보내기, Shift+Enter = 줄바꿈(편집기 요청 칸과 같다 - 한글 조합 중 Enter 는 조합 확정만)
    $("#reqText").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendReq(); } });
    $("#reqText").addEventListener("input", () => LS.set(typedKey(), $("#reqText").value.trim() ? $("#reqText").value : ""));
    $("#reqWhole").addEventListener("change", renderReqTarget);
    $("#reqList").addEventListener("keydown", (e) => RQ.keydown(e));  // 후속 입력칸 Enter = 보내기 · Esc = 닫기
    RQ.att.wire($("#side .compose"), "tab");  // 요청 첨부 - 붙여넣기(그림)·끌어다 놓기
    $("#side .compose").addEventListener("click", (e) => RQ.click(e));  // ＋ 첨부 · 빼기 · 축소판 · 세션 시작 링크
    $("#reqFilter").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      if (b.id === "reqMore") { RQ.openHist(); return; }
      if (b.dataset.v) { S.reqTab = b.dataset.v === "1"; LS.set("sheetReqTab", S.reqTab ? "" : "0"); renderReqs(); }
    });
    $("#sideSplit").addEventListener("mousedown", (e) => {
      e.preventDefault(); const x0 = e.clientX, w0 = $("#side").offsetWidth;
      const mv = (ev) => { const w = Math.max(240, Math.min(720, w0 - (ev.clientX - x0))); document.documentElement.style.setProperty("--sideW", w + "px"); LS.set("sheetSideW", String(w)); };
      const up = () => { removeEventListener("mousemove", mv); removeEventListener("mouseup", up); };
      addEventListener("mousemove", mv); addEventListener("mouseup", up);
    });
    $("#vbaClose").addEventListener("click", () => { const cur = VB.draft && VB.draft[VB.sel]; if (cur && cur.code !== $("#vbaCode").value) cur.code = $("#vbaCode").value; if (VB.draft && JSON.stringify(VB.draft) !== JSON.stringify(VB.mods) && !confirm("적용하지 않은 코드 변경이 있습니다. 버리고 닫을까요?")) return; $("#vbaDlg").classList.remove("show"); focusGrid(); });
    $("#vbaApply").addEventListener("click", vbaApply);
    $("#vbaRevert").addEventListener("click", () => { VB.draft = VB.mods.map((m) => ({ ...m })); $("#vbaCode").dataset.i = ""; vbaRender(); });
    $("#vbaMods").addEventListener("click", (e) => { const b = e.target.closest("[data-vm]"); if (!b) return; const cur = VB.draft[VB.sel]; if (cur) cur.code = $("#vbaCode").value; VB.sel = +b.dataset.vm; vbaRender(); });
    $("#vbaCode").addEventListener("keydown", (e) => {
      e.stopPropagation();  // 격자 단축키가 먹지 않게
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); vbaApply(); return; }
      if (e.key === "Tab") { e.preventDefault(); const t = e.target, a = t.selectionStart; t.setRangeText("    ", a, t.selectionEnd, "end"); }
      if (e.key === "Escape") $("#vbaClose").click();
    });
    $("#vbaCode").addEventListener("input", () => { clearTimeout(VB.t); VB.t = setTimeout(() => { const cur = VB.draft[VB.sel]; if (cur) { cur.code = $("#vbaCode").value; vbaRender(); } }, 500); });
    $("#vbaMsgs").addEventListener("click", (e) => { const d = e.target.closest("[data-ln]"); if (!d) return; const ta = $("#vbaCode"), ln = +d.dataset.ln, lines = ta.value.split("\n"); const at = lines.slice(0, ln - 1).join("\n").length + (ln > 1 ? 1 : 0); ta.focus(); ta.setSelectionRange(at, at + (lines[ln - 1] || "").length); });
    $("#vbaAdd").addEventListener("click", () => { const cur = VB.draft[VB.sel]; if (cur) cur.code = $("#vbaCode").value; let n = 1; while (VB.draft.some((m) => m.name.toLowerCase() === "module" + n)) n++; const nm = prompt("새 모듈 이름(함수 이름과 같으면 칸에서 못 부른다)", "Module" + n); if (!nm) return; if (!/^[\p{L}][\p{L}\p{N}_]{0,30}$/u.test(nm) || VB.draft.some((m) => m.name.toLowerCase() === nm.toLowerCase())) return toast("쓸 수 없는 이름입니다(글자로 시작, 31자 안, 겹치지 않게)"); VB.draft.push({ name: nm, kind: "std", code: "Option Explicit\r\n\r\nFunction 새함수(x)\r\n    새함수 = x\r\nEnd Function\r\n" }); VB.sel = VB.draft.length - 1; vbaRender(); });
    $("#vbaDel").addEventListener("click", () => { const m = VB.draft[VB.sel]; if (!m || m.kind !== "std" || !confirm(`모듈 ${m.name} 를 지울까요? (적용해야 반영)`)) return; VB.draft.splice(VB.sel, 1); VB.sel = Math.max(0, VB.sel - 1); $("#vbaCode").dataset.i = ""; vbaRender(); });
    $("#engReload").addEventListener("click", async () => { if (S.edit) endEdit(true); if (S.dirty) { clearTimeout(saveT); await save(); } if (!S.dirty) location.reload(); else toast("저장하지 못했습니다 - 저장된 뒤 다시 누르세요"); });
    $("#engClose").addEventListener("click", () => $("#engNotice").classList.remove("show"));
    $("#vbaBtn").addEventListener("click", vbaOpen);
    $("#zoomOut").onclick = () => setZoom(Z - 0.1); $("#zoomIn").onclick = () => setZoom(Z + 0.1);
    $("#zoomPct").onclick = (e) => openMenu(e.currentTarget, [50, 75, 90, 100, 125, 150, 200].map((n) => ({ label: n + "%", act: () => setZoom(n / 100) })));
    W.addEventListener("wheel", (e) => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault(); const R = W.getBoundingClientRect(); setZoom(Z * (e.deltaY < 0 ? 1.1 : 1 / 1.1), [e.clientX - R.left, e.clientY - R.top]); }, { passive: false });
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { save(); e.preventDefault(); e.returnValue = ""; } });
  }
  // 시험용(브라우저 콘솔·스모크) - 수식 계산·표시 형식을 따로 불러 볼 수 있게
  window.NexaSheet = { S, TH, VB, copyHtml, parseHtmlTable, pasteHtml, setZoom, zoom: () => Z, numFmt, bumpFmt, insertLink, formatDialog, drawDelete, autoFitCols, lastCell, noteEdit, insertImages, vbaOpen, vbaApply, effCell, bdSides, fillVars, reload: reloadExternal, applyVersion, recalc, parseFormula, display, fmtNumber, parseNumberText, shiftFormula, setInput, parseTsv, fillSeries, fillTarget,
    // 엑셀 기능 모듈(sheetx.js)이 쓰는 안쪽 함수 - 격자·선택·고치기(실행 취소·저장 포함)
    x: { shiftAxis, G, sheet, key, parseRef, colHidden, rowHidden, rectOf, colIndex, parseRange, rangeName, colName, cellObj, putCell, mutate, renderAll, renderSel, selectRange, selectCell, clampRange, eachCell, toast, openMenu,
      endEdit, startEdit, focusGrid, pasteText, scrollIntoView, growSize, clone, ED, esc,
      // 패널 속성·기록·변경 탭(sheetside.js)
      api, TAB, LS, FMTS, paneOf, mergeAt, styleOf, defSize, rawText, normSheet, setupVba, place, drawId, drawPick, markDrawings, drawDelete, assetUrl, inRange, switchTab, save, snapshot, afterChange, setZoomRef: () => Z } };
  init();
})();
