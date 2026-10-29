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
    view: {},  // 탭 id → {filter, rows:Set(가린 행)} - 이 화면에서만(저장하지 않음, 엑셀 "필터 보기"처럼 사람마다)
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
  // 숨긴 행·열 - 탭 hiddenRows(["5", …] 행 번호)·hiddenCols(["C", …]) 는 저장, 필터로 가린 행(S.view[탭].rows)은 이 화면만(sheetx.js)
  const colHidden = (sh, c) => !!(sh.hiddenCols && sh.hiddenCols.includes(colName(c)));
  const rowHidden = (sh, r) => !!((sh.hiddenRows && sh.hiddenRows.includes(String(r + 1))) || (S.view && S.view[sh.id] && S.view[sh.id].rows && S.view[sh.id].rows.has(r)));
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
    const r = await api("PUT", `/api/deck/${encodeURIComponent(S.id)}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : "&merge=1"}`, sentStruct.length ? { ...JSON.parse(body), __struct: sentStruct } : JSON.parse(body));
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
      if (RQ) await RQ.sync(v);  // 요청 파일이 바뀌었으면 다시 읽기(편집기와 같다)
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
  function renderAll() { renderGrid(); renderTabs(); renderSel(); renderReqs(); }
  function cellStyle(o, isNum) {
    const st = [];
    if (o.fill) st.push(`background:${o.fill}`);
    const cv = [];
    if (o.color) cv.push(`color:${o.color}`);
    if (o.b) cv.push("font-weight:700");
    if (o.i) cv.push("font-style:italic");
    if (o.u) cv.push("text-decoration:underline");
    if (o.size) cv.push(`font-size:${+o.size}pt`);
    const al = o.align || (isNum === "num" ? "right" : isNum === "mid" ? "center" : "left");
    cv.push(`justify-content:${al === "right" ? "flex-end" : al === "center" ? "center" : "flex-start"}`, `text-align:${al}`);
    cv.push(`align-items:${o.valign === "top" ? "flex-start" : o.valign === "middle" ? "center" : "flex-end"}`);
    return [st.join(";"), cv.join(";")];
  }
  function renderGrid() {
    const sh = sheet(), { rows, cols } = dims(sh); G.rows = rows; G.cols = cols;
    G.colX = [HW]; for (let c = 0; c < cols; c++) G.colX.push(G.colX[c] + colW(sh, c));
    G.rowY = [HH]; for (let r = 0; r < rows; r++) G.rowY.push(G.rowY[r] + rowH(sh, r));
    const fz = parseRef(sh.freeze || "") || { r: 0, c: 0 };
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
    grid.style.fontFamily = T && T.font ? `"${String(T.font).replace(/"/g, "")}", var(--font)` : "";
    grid.style.fontSize = T && T.size ? `${+T.size}pt` : "";
    const h = [`<colgroup><col style="width:${HW}px">`];
    for (let c = 0; c < cols; c++) if (!colHidden(sh, c)) h.push(`<col style="width:${colW(sh, c)}px">`);
    h.push(`</colgroup><thead><tr><th class="corner" title="모두 선택 (Ctrl+A)"></th>`);
    for (let c = 0; c < cols; c++) if (!colHidden(sh, c)) h.push(`<th data-col="${c}"${colHidden(sh, c + 1) || (c > 0 && colHidden(sh, c - 1)) ? ' class="hidN" title="옆에 숨긴 열이 있습니다 - 오른쪽 클릭 → 숨기기 취소"' : ""}>${colName(c)}<span class="rz" data-rzc="${c}"></span></th>`);
    h.push("</tr></thead><tbody>");
    const visN = (a, b, hid) => { let n = 0; for (let i = a; i <= b; i++) if (!hid(sh, i)) n++; return n; };
    const CF = window.NexaSheetX && NexaSheetX.condMap ? NexaSheetX.condMap(sh) : null;  // 조건부 서식(sheetx.js) - 칸 → 덧씌울 서식
    for (let r = 0; r < rows; r++) {
      if (rowHidden(sh, r)) continue;
      const rh = rowH(sh, r);
      h.push(`<tr style="height:${rh}px"><th data-row="${r}"${rowHidden(sh, r + 1) || (r > 0 && rowHidden(sh, r - 1)) ? ' class="hidN"' : ""}>${r + 1}<span class="rz" data-rzr="${r}"></span></th>`);
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
        {  // 테두리
          const r2 = cm ? cm.r2 : r, c2 = cm ? cm.c2 : c, bb = eB.get(r2 * 4096 + c), br = eR.get(r * 4096 + c2), sh2 = [];
          if (bb) extra.push(`border-bottom-color:${bb}`); if (br) extra.push(`border-right-color:${br}`);
          if (r === 0 && eT.get(c)) sh2.push(`inset 0 1px 0 ${eT.get(c)}`); if (c === 0 && eL.get(r)) sh2.push(`inset 1px 0 0 ${eL.get(r)}`);
          if (sh2.length) extra.push(`box-shadow:${sh2.join(",")}`);
        }
        h.push(`<td data-r="${r}" data-c="${c}"${span}${cls.length ? ` class="${cls.join(" ")}"` : ""} style="${[tdS, ...extra.filter(Boolean)].filter(Boolean).join(";")}"${o.note ? ` title="${esc(o.note)}"` : ""}>`
          + `<div class="cv${o.wrap ? " wrap" : ""}" style="height:${hh - 1}px;${cvS}"><span>${esc(txt)}</span></div></td>`);
      }
      h.push("</tr>");
    }
    h.push("</tbody>");
    $("#grid").innerHTML = h.join("");
    renderMarks(); renderDrawings();
  }
  /** 탭 그림(drawings) - 셀 at 의 왼쪽 위 + (dx, dy)px 에 w×h. 격자와 같이 움직이고 누르기는 통과(선택을 막지 않는다) */
  function renderDrawings() {
    const sh = sheet(), out = [];
    for (const d of sh.drawings || []) {
      if (d.type && d.type !== "image") continue;
      const p = parseRef(d.at || "A1"); if (!p) continue;
      const x = (G.colX[Math.min(p.c, G.colX.length - 1)] || HW) + (+d.dx || 0), y = (G.rowY[Math.min(p.r, G.rowY.length - 1)] || HH) + (+d.dy || 0);
      const src = assetUrl(d.src); if (!src) continue;
      out.push(`<img class="drw" src="${esc(src)}" alt="" draggable="false" style="left:${x}px;top:${y}px;width:${+d.w || 120}px;height:${+d.h || 60}px">`);
    }
    const box = $("#draws"); box.innerHTML = out.join("");
    $$("img", box).forEach((i) => { i.onerror = () => { i.style.visibility = "hidden"; }; });
  }
  function rectOf(g) { return { x: G.colX[g.c1], y: G.rowY[g.r1], w: G.colX[g.c2 + 1] - G.colX[g.c1], h: G.rowY[g.r2 + 1] - G.rowY[g.r1] }; }
  function place(el, g, inset = 0) { const R = rectOf(g); Object.assign(el.style, { left: R.x - inset + "px", top: R.y - inset + "px", width: R.w + inset * 2 + 1 + "px", height: R.h + inset * 2 + 1 + "px" }); }
  function renderSel() {
    const sh = sheet(), g = clampRange(S.sel), cm = mergeAt(sh, S.cur.r, S.cur.c) || { r1: S.cur.r, c1: S.cur.c, r2: S.cur.r, c2: S.cur.c };
    place($("#selBox"), g); $("#selBox").hidden = g.r1 === g.r2 && g.c1 === g.c2 || rangeName(g) === rangeName(cm);
    place($("#curBox"), cm, 1);
    { const R = rectOf(g), H = $("#fillHandle"); H.style.left = R.x + R.w - 3 + "px"; H.style.top = R.y + R.h - 3 + "px"; H.hidden = !!S.edit; }  // 채우기 핸들 - 선택 범위 오른쪽 아래
    $$("#grid th.on").forEach((t) => t.classList.remove("on"));
    for (let c = g.c1; c <= g.c2; c++) { const t = $(`#grid th[data-col="${c}"]`); if (t) t.classList.add("on"); }
    for (let r = g.r1; r <= g.r2; r++) { const t = $(`#grid th[data-row="${r}"]`); if (t) t.classList.add("on"); }
    const cb = $("#clipBox"); cb.hidden = !(S.clip && S.clip.ti === sh.id && S.clip.show); if (!cb.hidden) place(cb, S.clip.g);
    $("#nameBox").value = rangeName(g);
    if (document.activeElement !== $("#fxIn")) $("#fxIn").value = rawText(sh, key(S.cur.r, S.cur.c));
    if (!S.edit) placeEditor();
    renderToolState(); renderReqTarget();
    if (window.NexaSheetX) NexaSheetX.onSel();  // 엑셀 기능(sheetx.js) - 상태 표시줄 합계 등
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
    if (c >= fz.c) { if (x1 - W.scrollLeft < leftFix) W.scrollLeft = x1 - leftFix; else if (x2 - W.scrollLeft > W.clientWidth) W.scrollLeft = x2 - W.clientWidth + 2; }
    if (r >= fz.r) { if (y1 - W.scrollTop < topFix) W.scrollTop = y1 - topFix; else if (y2 - W.scrollTop > W.clientHeight) W.scrollTop = y2 - W.clientHeight + 2; }
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
      if (k.startsWith("Arrow")) { e.preventDefault(); move(k === "ArrowDown" ? 1 : k === "ArrowUp" ? -1 : 0, k === "ArrowRight" ? 1 : k === "ArrowLeft" ? -1 : 0, e.shiftKey, true); return; }
      return;  // Ctrl+C·V·X 는 copy/paste/cut 이벤트로
    }
    if (k.startsWith("Arrow")) { e.preventDefault(); move(k === "ArrowDown" ? 1 : k === "ArrowUp" ? -1 : 0, k === "ArrowRight" ? 1 : k === "ArrowLeft" ? -1 : 0, e.shiftKey); return; }
    if (k === "Enter") { e.preventDefault(); advance(e.shiftKey ? -1 : 1, 0); return; }
    if (k === "Tab") { e.preventDefault(); advance(0, e.shiftKey ? -1 : 1); return; }
    if (k === "F2") { e.preventDefault(); startEdit("edit"); return; }
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
      const d = dims(sh); if (sh.size) sh.size = axis === "r" ? { ...sh.size, rows: Math.max(1, (+sh.size.rows || d.rows) + n) } : { ...sh.size, cols: Math.max(1, (+sh.size.cols || d.cols) + n) };
      // 수식 참조 - 이 탭을 가리키는 참조(같은 탭의 이름 없는 참조 · 다른 탭의 '이름!' 참조)
      for (const s2 of S.deck.sheets) for (const [k, raw] of Object.entries(s2.cells)) {
        if (!raw || typeof raw !== "object" || !raw.f) continue;
        raw.f = rewriteFormula(raw.f, (ends, nm) => {
          const target = nm == null ? s2 : sheetByName(nm, s2); if (target !== sh) return ends;
          if (ends.some((e) => (axis === "r" ? e.r : e.c) == null)) return ends;  // 열 전체(A:C)를 행 작업이 · 행 전체(3:5)를 열 작업이 - 그대로(서버 sheet_struct.py 와 같다)
          if (ends.length === 1) { const v = mv(ends[0]); return v === null ? null : [axis === "r" ? { ...ends[0], r: v } : { ...ends[0], c: v }]; }
          const g = mvRange({ r1: ends[0].r, c1: ends[0].c, r2: ends[1].r, c2: ends[1].c }); if (!g) return null;
          return [{ ...ends[0], r: g.r1, c: g.c1 }, { ...ends[1], r: g.r2, c: g.c2 }];
        });
      }
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
      tip.hidden = !tip.textContent; tip.style.left = ev.clientX - R.left + 14 + "px"; tip.style.top = ev.clientY - R.top + 16 + "px";
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
  function switchTab(i) { if (S.edit) endEdit(true); if (i === S.ti) return; S.ti = i; renderGrid(); renderTabs(); selectRange({ r1: 0, c1: 0, r2: 0, c2: 0 }); $("#gridWrap").scrollTo(0, 0); renderReqs(); focusGrid(); }
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
  function reqTargetRange() { return $("#reqWhole").checked ? null : rangeName(clampRange(S.sel)); }
  function renderReqTarget() {
    const t = reqTargetRange(); $("#reqTarget").textContent = `${sheet().name}${t ? "!" + t : " (탭 전체)"}`;
  }
  const typedKey = () => `typed-${NS}${S.id}/sheet`;
  const tabName = (sid) => { const s = S.deck && S.deck.sheets.find((x) => x.id === sid); return s ? s.name : sid || "?"; };
  /** 시트 대상 어댑터(RQ) - 탭 · 범위 */
  const SHEET_TARGET = {
    scope: "탭", key: (r) => r.slide, current: () => sheet().id, num: (r) => S.deck.sheets.findIndex((s) => s.id === r.slide) + 1,
    label: (r) => `${tabName(r.slide)}${r.range ? "!" + r.range : " (탭 전체)"}`,
    goto: (r) => gotoReq(r),
    extra: (r) => aiDiffHtml(r),  // 완료된 요청 - AI 가 바꾼 셀 n개 · 보기 · 되돌리기
  };
  /** 요청의 탭·범위로 - 카드를 누르거나 카드의 대상 링크 */
  function gotoReq(q) {
    const root = RQ.rootOf(q); S.reqCur = q.id;
    const i = S.deck.sheets.findIndex((s) => s.id === root.slide); if (i >= 0 && i !== S.ti) switchTab(i);
    const g = parseRange(root.range); if (g) selectRange(clampRange(g)); else renderSel();
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

  // ---------------------------------------------------------------- 끌기(범위 선택·열 너비·행 높이·패널 폭)
  function onGridDown(e) {
    if (e.button !== 0 && e.button !== 2) return;
    if (e.button === 0 && e.target.closest("#fillHandle")) { startFill(e); return; }
    const rzc = e.target.closest("[data-rzc]"), rzr = e.target.closest("[data-rzr]");
    if (rzc || rzr) { e.preventDefault(); startResize(e, rzc ? "c" : "r", +(rzc || rzr).dataset[rzc ? "rzc" : "rzr"]); return; }
    const td = e.target.closest("td[data-r]"), thc = e.target.closest("th[data-col]"), thr = e.target.closest("th[data-row]");
    if (e.target.closest("th.corner")) { e.preventDefault(); S.anchor = { r: 0, c: 0 }; S.sel = { r1: 0, c1: 0, r2: G.rows - 1, c2: G.cols - 1 }; renderSel(); focusGrid(); return; }
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
  function startResize(e, axis, i) {
    const sh = sheet(), x0 = axis === "c" ? e.clientX : e.clientY, w0 = axis === "c" ? colW(sh, i) : rowH(sh, i);
    // 여러 열(행)이 골라져 있고 그 안의 경계를 끌면 고른 것 모두 같은 크기로
    const g = S.sel, all = axis === "c" ? (g.r1 === 0 && g.r2 === G.rows - 1 && i >= g.c1 && i <= g.c2 ? [...Array(g.c2 - g.c1 + 1)].map((_, k) => g.c1 + k) : [i])
      : (g.c1 === 0 && g.c2 === G.cols - 1 && i >= g.r1 && i <= g.r2 ? [...Array(g.r2 - g.r1 + 1)].map((_, k) => g.r1 + k) : [i]);
    let snap = false, last = w0;
    const onMove = (ev) => {
      const v = Math.max(axis === "c" ? 24 : 16, Math.round(w0 + (axis === "c" ? ev.clientX : ev.clientY) - x0)); if (v === last) return; last = v;
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
  function gridMenu(e) {
    if (!e.target.closest("td, th")) return;
    e.preventDefault();
    const g = S.sel;
    openMenu({ x: e.clientX, y: e.clientY }, [
      { h: `${sheet().name}!${rangeName(g)}` },
      { label: "잘라내기", key: "Ctrl+X", act: () => { document.execCommand("cut") || copyRange(true); } },
      { label: "복사", key: "Ctrl+C", act: () => { document.execCommand("copy") || copyRange(); } },
      { label: "붙여넣기", key: "Ctrl+V", act: async () => { try { pasteText(await navigator.clipboard.readText()); } catch (er) { toast("Ctrl+V 로 붙여넣으세요(브라우저가 클립보드 읽기를 막았습니다)", 4000); } } },
      { label: "내용 지우기", key: "Delete", act: () => clearRange(g) },
      { label: "서식 지우기", act: () => mutate(() => { const sh = sheet(); eachCell(g, (r, c, k) => { const o = cellObj(sh, k); putCell(sh, k, { v: o.v, f: o.f }); }); }) },
      "-",
      { label: mergeAt(sheet(), S.cur.r, S.cur.c) ? "병합 해제" : "셀 병합", act: toggleMerge },
      { label: "행·열 삽입·삭제…", act: () => rowColMenu({ x: e.clientX, y: e.clientY }) },
      "-",
      { label: "이 범위에 AI 요청 남기기", act: () => { $("#reqWhole").checked = false; document.body.classList.remove("noside"); renderReqTarget(); $("#reqText").focus(); } },
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
    W.addEventListener("mousedown", onGridDown);
    W.addEventListener("contextmenu", gridMenu);
    W.addEventListener("dblclick", (e) => {
      if (e.target.closest("#fillHandle")) { e.preventDefault(); fillDownAuto(); return; }
      const td = e.target.closest("td[data-r]"); if (td) { e.preventDefault(); startEdit("edit"); }
    });
    W.addEventListener("click", (e) => { if (!S.edit && !e.target.closest("button")) focusGrid(); });
    const ed = ED();
    ed.addEventListener("keydown", onEditorKey);
    ed.addEventListener("input", onEditorInput);
    ed.addEventListener("blur", (e) => { if (S.edit && e.relatedTarget !== $("#fxIn")) endEdit(true); });  // 다른 곳을 누르면 입력을 넣는다(수식 줄로 옮길 때만 이어서)
    ed.addEventListener("compositionstart", () => { if (!S.edit) { S.edit = { r: S.cur.r, c: S.cur.c, mode: "enter", orig: rawText(sheet(), key(S.cur.r, S.cur.c)) }; ed.classList.add("on"); placeEditor(); } });
    $("#addRows").onclick = () => addRows(20);
    document.addEventListener("copy", (e) => { if (document.activeElement !== ed || S.edit) return; e.preventDefault(); e.clipboardData.setData("text/plain", copyRange(false)); });
    document.addEventListener("cut", (e) => { if (document.activeElement !== ed || S.edit) return; e.preventDefault(); e.clipboardData.setData("text/plain", copyRange(true)); });
    document.addEventListener("paste", (e) => { if (document.activeElement !== ed || S.edit) return; e.preventDefault(); const t = e.clipboardData.getData("text/plain"); if (t) pasteText(t); });
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
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { save(); e.preventDefault(); e.returnValue = ""; } });
  }
  // 시험용(브라우저 콘솔·스모크) - 수식 계산·표시 형식을 따로 불러 볼 수 있게
  window.NexaSheet = { S, TH, effCell, bdSides, fillVars, reload: reloadExternal, recalc, parseFormula, display, fmtNumber, parseNumberText, shiftFormula, setInput, parseTsv, fillSeries, fillTarget,
    // 엑셀 기능 모듈(sheetx.js)이 쓰는 안쪽 함수 - 격자·선택·고치기(실행 취소·저장 포함)
    x: { shiftAxis, G, sheet, key, parseRef, colHidden, rowHidden, rectOf, colIndex, parseRange, rangeName, colName, cellObj, putCell, mutate, renderAll, renderSel, selectRange, selectCell, clampRange, eachCell, toast, openMenu,
      endEdit, startEdit, focusGrid, pasteText, scrollIntoView, growSize, clone, ED, esc } };
  init();
})();
