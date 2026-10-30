/* nexa-slide 시트 수식 계산기(화면) - sheet_calc.py 와 같은 규칙(두 곳 동일성). 같은 사례 파일 tests/sheetcalc_cases.json 로 시험한다.
     NexaCalc.recalc(doc)           → 모든 탭의 수식 칸 v 를 계산값(오류는 "#…" 문자열)으로. 바뀐 칸 수
     NexaCalc.cell(doc, tab, "B3")  → 한 칸 값
   문법: 사칙연산·^·&·비교·%, 셀·범위(열 전체 A:A·행 전체 1:1), 다른 탭 '이름'!A1, 함수 FUNCS(엑셀 기본 약 70개), 배열 수식(칸마다).
   node 에서도 쓴다(module.exports) - tests/sheetcalc_test.js. */
(function (root) {
  "use strict";
  const ERRS = ["#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#NULL!", "#SPILL!", "#CALC!"];
  const DYN = new Set(["FILTER", "SORT", "SORTBY", "UNIQUE", "SEQUENCE", "TRANSPOSE", "TAKE", "DROP", "CHOOSECOLS", "CHOOSEROWS", "HSTACK", "VSTACK", "TOCOL", "TOROW", "TEXTSPLIT", "GROUPBY", "PIVOTBY", "MAP", "BYROW", "BYCOL", "SCAN", "MAKEARRAY"]);  // 동적 배열 함수 - 이 함수를 쓴(또는 가져온 동적 배열 da) 수식만 옆 칸으로 넘친다
  const DAY0 = Date.UTC(1899, 11, 30);
  class FErr { constructor(code) { this.code = code; } }
  class Pend extends FErr { constructor() { super("#N/A"); } }  // VBA 사용자 함수가 Worker 에서 계산 중 - 이 칸과 이 칸에 기대는 칸은 저장된 값을 그대로(recalc)
  class Rng { constructor(rows) { this.rows = rows; } get vals() { return [].concat(...this.rows); } }
  const isNum = (v) => typeof v === "number";
  const isMulti = (v) => v instanceof Rng && v.vals.length > 1;

  const L = "[\\p{L}_]";
  const TOK = new RegExp([
    "(\\s+)",
    '("(?:[^"]|"")*")',
    `((?:'(?:[^']|'')+'|${L}[\\p{L}\\p{N}_.]*)!)?(\\$?[A-Za-z]{1,3}\\$?\\d+(?::\\$?[A-Za-z]{1,3}\\$?\\d+)?|\\$?[A-Za-z]{1,3}:\\$?[A-Za-z]{1,3}|\\$?\\d+:\\$?\\d+)(?![\\p{L}\\p{N}_(])`,
    `(${L}[\\p{L}\\p{N}_.]*)(?=\\s*\\()`,
    "(TRUE|FALSE)(?![\\p{L}\\p{N}_])",
    "(\\d+(?:\\.\\d*)?(?:[eE][+-]?\\d+)?|\\.\\d+(?:[eE][+-]?\\d+)?)",
    "(<=|>=|<>|[-+*/^&=<>(),%{};])",
    "(#[A-Z/0]+[!?])",
    `((?:${L}[\\p{L}\\p{N}_.]*)?\\[(?:[^\\[\\]]|\\[[^\\[\\]]*\\])*\\])`,  // 표 구조적 참조 표1[열] · [@열] · 표1[[#Headers],[열]]
    `(${L}[\\p{L}\\p{N}_.]*)`,
  ].join("|"), "uiy");
  const colIndex = (s) => { let n = 0; for (const ch of s.toUpperCase()) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; };
  const colName = (c) => { let s = ""; c += 1; while (c > 0) { const m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = Math.floor((c - 1) / 26); } return s; };
  const parseRef = (s) => { const m = /^\$?([A-Za-z]{1,3})\$?(\d+)$/.exec(String(s).trim()); return m ? [+m[2] - 1, colIndex(m[1])] : null; };

  function tokenize(src) {
    const out = []; let i = 0;
    while (i < src.length) {
      TOK.lastIndex = i; const m = TOK.exec(src);
      if (!m || TOK.lastIndex === i) throw new FErr("#NAME?");
      i = TOK.lastIndex;
      if (m[1]) continue;
      if (m[2]) out.push(["str", m[2].slice(1, -1).replace(/""/g, '"')]);
      else if (m[4]) {
        const t = ["ref", m[4], m[3] ? m[3].slice(0, -1).replace(/^'|'$/g, "").replace(/''/g, "'") : null];
        if (src[i] === "#" && !m[4].includes(":")) { i++; t.push("#"); }  // 넘친 범위 참조 H2# (엑셀 파일에는 ANCHORARRAY(H2))
        out.push(t);
      }
      else if (m[5]) out.push(["fn", m[5].toUpperCase().replace(/^(?:_XL(?:FN|WS)\.)+/, "")]);  // 파일에 저장된 새 함수 접두사(_xlfn.TEXTJOIN)
      else if (m[6]) out.push(["bool", m[6].toUpperCase() === "TRUE"]);
      else if (m[7]) out.push(["num", parseFloat(m[7])]);
      else if (m[8]) out.push(["op", m[8]]);
      else if (m[9]) out.push(["err", m[9]]);
      else if (m[10]) { const k = m[10].indexOf("["); out.push(["sref", m[10].slice(0, k) || null, m[10].slice(k + 1, -1)]); }
      else out.push(["name", m[11]]);
    }
    return out;
  }
  function parse(src) {
    const T = tokenize(src); let p = 0;
    const peek = () => T[p], isOp = (v) => T[p] && T[p][0] === "op" && T[p][1] === v;
    const eat = (v) => { if (!isOp(v)) throw new FErr("#NAME?"); p++; };
    const binl = (nxt, ops) => () => { let a = nxt(); while (T[p] && T[p][0] === "op" && ops.includes(T[p][1])) { const op = T[p++][1]; a = ["bin", op, a, nxt()]; } return a; };
    function unary() {
      if (isOp("-")) { p++; return ["neg", unary()]; }
      if (isOp("+")) { p++; return unary(); }
      let a = prim(); while (isOp("%")) { p++; a = ["pct", a]; } return a;
    }
    function prim() {
      const t = peek(); if (!t) throw new FErr("#NAME?"); p++;
      const k = t[0];
      if (k === "num" || k === "str" || k === "bool") return ["lit", t[1]];
      if (k === "err") return ["err", t[1]];
      if (k === "name") return ["name", t[1].toUpperCase()];  // LET 이름 - 밖에서는 #NAME?
      if (k === "sref") return ["sref", t[1], t[2]];
      if (k === "ref") {
        if (t.length > 3) { const a = parseRef(t[1]); return ["spill", t[2], a[0], a[1]]; }
        const ends = t[1].split(":");
        if (/^\$?[A-Za-z]{1,3}$/.test(ends[0])) return ["range", t[2], 0, colIndex(ends[0].replace("$", "")), -1, colIndex(ends[ends.length - 1].replace("$", ""))];
        if (/^\$?\d+$/.test(ends[0])) return ["range", t[2], +ends[0].replace("$", "") - 1, 0, +ends[ends.length - 1].replace("$", "") - 1, -1];
        const a = parseRef(ends[0]), b = parseRef(ends[ends.length - 1]);
        return ends.length > 1 ? ["range", t[2], Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])] : ["ref", t[2], a[0], a[1]];
      }
      if (k === "fn") {
        eat("("); const args = [];
        if (!isOp(")")) for (;;) { args.push(isOp(",") || isOp(")") ? ["lit", null] : cmp()); if (isOp(",")) { p++; continue; } break; }
        eat(")"); return ["fn", t[1], args];
      }
      if (k === "op" && t[1] === "(") { const a = cmp(); eat(")"); return a; }
      if (k === "op" && t[1] === "{") {  // 배열 상수 {1,-3;"가",TRUE} - 쉼표는 열, 세미콜론은 행
        const rows = [[]];
        for (;;) {
          const neg = isOp("-"); if (neg) p++;
          const e = peek(); if (!e || !["num", "str", "bool", "err"].includes(e[0]) || (neg && e[0] !== "num")) throw new FErr("#NAME?"); p++;
          rows[rows.length - 1].push(e[0] === "err" ? new FErr(e[1]) : neg ? -e[1] : e[1]);
          if (isOp(",")) { p++; continue; }
          if (isOp(";")) { p++; rows.push([]); continue; }
          eat("}"); break;
        }
        if (new Set(rows.map((r) => r.length)).size !== 1) throw new FErr("#VALUE!");
        return ["arr", new Rng(rows)];
      }
      throw new FErr("#NAME?");
    }
    const pow = binl(unary, ["^"]), mul = binl(pow, ["*", "/"]), add = binl(mul, ["+", "-"]), cat = binl(add, ["&"]), cmp = binl(cat, ["=", "<>", "<", ">", "<=", ">="]);
    const ast = cmp(); if (p < T.length) throw new FErr("#NAME?");
    return ast;
  }

  // ---------------------------------------------------------------- 값 바꾸기
  const fix = (x) => { if (typeof x !== "number") return x; if (!isFinite(x)) throw new FErr("#NUM!"); return Number(x.toPrecision(15)); };
  function parseNumberText(t) {
    const s = String(t).trim(); if (!s) return null;
    let m = /^([+-]?)((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?(%?)$/.exec(s);
    if (m) { let v = parseFloat(m[2].replace(/,/g, "")) * (m[3] ? Math.pow(10, +m[3]) : 1); if (m[1] === "-") v = -v; return m[4] ? v / 100 : v; }
    m = /^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/.exec(s);
    if (m) { const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])); if (d.getUTCMonth() !== +m[2] - 1) return null; return (d - DAY0) / 864e5; }
    return null;
  }
  function toNum(v) {
    if (v instanceof FErr) throw v;
    if (v == null || v === "") return 0;
    if (typeof v === "boolean") return v ? 1 : 0;
    if (isNum(v)) return v;
    if (ERRS.includes(v)) throw new FErr(v);
    const n = parseNumberText(v); if (n === null) throw new FErr("#VALUE!"); return n;
  }
  function general(v) {
    if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
    if (Number.isInteger(v)) return String(v);
    const a = Math.abs(v);
    if (a && (a < 1e-9 || a >= 1e15)) return v.toExponential(5).replace(/\.?0+e/, "E").replace("E+", "E+");
    return String(Number(v.toPrecision(11)));
  }
  const toStr = (v) => { if (v instanceof FErr) throw v; if (v == null) return ""; if (typeof v === "boolean") return v ? "TRUE" : "FALSE"; if (isNum(v)) return general(v); return String(v); };
  const toBool = (v) => { if (v instanceof FErr) throw v; if (typeof v === "string") { if (/^true$/i.test(v)) return true; if (/^false$/i.test(v)) return false; throw new FErr("#VALUE!"); } return !!toNum(v); };
  const rank = (v) => (v == null ? 0 : isNum(v) ? 1 : typeof v === "string" ? 2 : 3);
  function compare(a, b, op) {
    if (a == null) a = typeof b === "string" ? "" : typeof b === "boolean" ? false : 0;
    if (b == null) b = typeof a === "string" ? "" : typeof a === "boolean" ? false : 0;
    let d;
    if (rank(a) !== rank(b)) d = rank(a) - rank(b);
    else if (typeof a === "string") { const x = a.toLowerCase(), y = b.toLowerCase(); d = x < y ? -1 : x > y ? 1 : 0; }
    else d = (a > b) - (a < b);
    return { "=": d === 0, "<>": d !== 0, "<": d < 0, ">": d > 0, "<=": d <= 0, ">=": d >= 0 }[op];
  }
  const dateOf = (n) => new Date(DAY0 + Math.floor(toNum(n)) * 864e5);
  const serial = (d) => Math.round((d - DAY0) / 864e5);
  function addMonths(d, k) {
    const y = d.getUTCFullYear(), m = d.getUTCMonth() + k, last = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    return new Date(Date.UTC(y, m, Math.min(d.getUTCDate(), last)));
  }
  function criteria(c) {
    if (isNum(c)) return (v) => rank(v) === 1 && v === c;
    const s = toStr(c), m = /^(<=|>=|<>|<|>|=)?([\s\S]*)$/.exec(s), op = m[1] || "=", rest = m[2];
    const n = parseNumberText(rest);
    if (n !== null) return op !== "<>" ? (v) => rank(v) === 1 && compare(v, n, op) : (v) => !(rank(v) === 1 && v === n);
    if ((op === "=" || op === "<>") && /[*?]/.test(rest)) {
      const rx = new RegExp("^" + rest.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[\\s\\S]*").replace(/\?/g, "[\\s\\S]") + "$", "i");
      const hit = (v) => typeof v === "string" && rx.test(v);
      return op === "=" ? hit : (v) => !hit(v);
    }
    if (op === "=" && rest === "") return (v) => v == null || v === "";
    return (v) => (typeof v === "string" || v == null || op === "<>" ? compare(v == null ? "" : v, rest, op) : op === "<>");
  }
  function tref(t) { const [a, b] = String(t.ref || "").split(":"), pa = parseRef(a), pb = parseRef(b || a); if (!pa || !pb) throw new FErr("#REF!"); return [pa[0], pa[1], pb[0], pb[1]]; }
  /** 구조적 참조 안쪽 → [특수 지정 집합 {#all,#data,#headers,#totals,#this row,@}, 열 이름 [처음, 끝]] */
  function tableSpec(inner) {
    inner = inner.trim(); const spec = new Set(); let cols = [];
    if (inner.startsWith("@")) { spec.add("@"); inner = inner.slice(1).trim(); }
    const items = !inner.includes("[") ? (inner ? [inner] : []) : [...inner.matchAll(/\[([^\]]*)\]/g)].map((m) => m[1]);
    for (const it of items) { if (it.startsWith("#")) spec.add(it.toLowerCase()); else if (it) cols.push(it.replace(/'/g, "")); }
    if (cols.length > 2) cols = [cols[0], cols[cols.length - 1]];
    return [spec, cols];
  }
  const cellv = (f) => { try { return f(); } catch (e) { if (e instanceof FErr) return e; throw e; } };
  const amap = (f, r) => new Rng(r.rows.map((row) => row.map((v) => cellv(() => f(v)))));
  function azip(f, a, b) {
    const ra = a instanceof Rng ? a.rows : [[a]], rb = b instanceof Rng ? b.rows : [[b]];
    const h = Math.max(ra.length, rb.length), w = Math.max(ra[0].length, rb[0].length);
    const pick = (m, i, j) => m[m.length > 1 ? i : 0][m[0].length > 1 ? j : 0];
    return new Rng(Array.from({ length: h }, (_, i) => Array.from({ length: w }, (_, j) => cellv(() => f(pick(ra, i, j), pick(rb, i, j))))));
  }
  function roundX(x, n, how) {
    const f = Math.pow(10, n), y = Number((Math.abs(x) * f).toPrecision(15));
    const z = how === "up" ? Math.ceil(y) : how === "down" ? Math.floor(y) : Math.floor(y + 0.5);
    return z ? Math.sign(x) * z / f : 0;
  }

  // ---------------------------------------------------------------- 계산기
  /** LAMBDA 값 - 매개변수 이름·본문·만든 곳의 LET 이름 묶음 */
  class Lam { constructor(params, body, scope) { this.params = params; this.body = body; this.scope = scope; } }
  class Calc {
    constructor(doc) { this.doc = doc; this.sheets = doc.sheets || []; this.memo = new Map(); this.busy = new Set(); this.ast = new Map(); this.at = []; this.dims = new Map(); this.spill = new Map(); this.anchors = new Map(); this.dyn = new Map(); this.extent = new Map(); this.scope = []; this.names = new Map(); this.naming = new Set(); this.depth = 0; this.ids = []; this.links = new Map(); this.pend = new Set(); }
    /** f(…) 의 f - LET 이름이나 이름 정의에 담긴 LAMBDA(없으면 null) */
    lamOf(nm, sh) {
      for (let i = this.scope.length - 1; i >= 0; i--) if (this.scope[i].has(nm)) { const v = this.scope[i].get(nm); return v instanceof Lam ? v : null; }
      const node = this.named(nm, sh); if (!node || this.naming.has(nm)) return null;
      this.naming.add(nm); let f; try { f = cellv(() => this.ev(node, sh)); } finally { this.naming.delete(nm); }
      return f instanceof Lam ? f : null;
    }
    /** LAMBDA 부르기 - 매개변수를 만든 곳의 이름 묶음 위에 얹는다. 이름 정의 LAMBDA 는 자기를 부를 수 있다(깊이 200까지) */
    call(f, vals, sh) {
      if (vals.length !== f.params.length) throw new FErr("#VALUE!");
      if (this.depth > 200) throw new FErr("#NUM!");
      const saved = this.scope; this.scope = [...f.scope, new Map(f.params.map((p, i) => [p, vals[i]]))]; this.depth++;
      try { return this.ev(f.body, sh); } finally { this.scope = saved; this.depth--; }
    }
    /** 이름 정의 → 구문 트리(없으면 null). 탭 names(엑셀 시트 범위 이름)가 문서 names 보다 먼저, 이름은 대소문자 무시.
     *  탭 이름의 참조에 탭이 없으면 그 탭을 가리킨다(문서 이름은 계산하는 칸의 탭) - sheet_calc.py named 와 같다 */
    named(nm, sh) {
      for (const owner of [sh, null]) {
        const book = (owner || this.doc).names || {}, k = Object.keys(book).find((x) => x.toUpperCase() === nm);
        if (k === undefined) continue;
        const key = (owner ? owner.id : "") + "!" + nm;
        if (!this.names.has(key)) {
          const src = String(book[k]); let node;
          try { node = parse(src.replace(/^=/, "")); } catch (e) { node = ["err", e instanceof FErr ? e.code : "#NAME?"]; }
          if (owner && (node[0] === "ref" || node[0] === "range") && node[1] == null) node = [node[0], owner.name, ...node.slice(2)];
          this.names.set(key, node);
        }
        return this.names.get(key);
      }
      return null;
    }
    /** LET 이름이 아닌 이름 → 이름 정의의 참조·식 - 범위를 받는 함수(SUM·COUNT·ROW·OFFSET)가 참조로 보게 */
    deref(n, sh) {
      if (n[0] === "name" && !this.scope.some((sc) => sc.has(n[1]))) { const node = this.named(n[1], sh); if (node && !this.naming.has(n[1])) return node; }
      return n;
    }
    isDyn(raw) {
      if (raw.da) return true;
      if (!this.dyn.has(raw.f)) { let d = false; try { d = tokenize(raw.f.replace(/^=/, "")).some((t) => (t[0] === "fn" && DYN.has(t[1])) || (t[0] === "ref" && t.length > 3)); } catch (e) { /* 문법 오류 */ } this.dyn.set(raw.f, d); }
      return this.dyn.get(raw.f);
    }
    /** 표1[열] · [@열] · 표1[[#Headers],[열1]:[열2]] → ["ref"|"range", 탭 이름, …] */
    sref(n, sh) {
      const [, name, inner] = n, at = this.at[this.at.length - 1]; let hit = null;
      for (const s of this.sheets) for (const t of s.tables || []) {
        if (name && String(t.name || "").toLowerCase() === name.toLowerCase()) hit = [s, t];
        else if (!name && s === sh && at) { const [r1, c1, r2, c2] = tref(t); if (r1 <= at[0] && at[0] <= r2 && c1 <= at[1] && at[1] <= c2) hit = [s, t]; }
      }
      if (!hit) throw new FErr("#REF!");
      const [s, t] = hit, [spec, cols] = tableSpec(inner), [r1, c1, r2, c2] = tref(t), names = (t.cols || []).map((x) => String(x).toLowerCase());
      const head = t.header !== false, d1 = r1 + (head ? 1 : 0), d2 = r2 - (t.totals ? 1 : 0);
      let ra, rb;
      if (spec.has("@") || spec.has("#this row")) { if (!at || at[0] < d1 || at[0] > d2) throw new FErr("#VALUE!"); ra = rb = at[0]; }
      else if (spec.has("#all")) { ra = r1; rb = r2; }
      else {
        ra = d1; rb = d2;
        if (spec.has("#headers")) { ra = head ? r1 : d1; if (!spec.has("#data")) rb = ra; }
        if (spec.has("#totals")) { if (!t.totals) throw new FErr("#REF!"); rb = r2; if (!spec.has("#data")) ra = r2; }
      }
      let ca = c1, cb = c2;
      if (cols.length) { const k = cols.map((x) => names.indexOf(x.toLowerCase())); if (k.some((i) => i < 0)) throw new FErr("#REF!"); ca = c1 + Math.min(...k); cb = c1 + Math.max(...k); }
      const tab = s === sh ? null : s.name;
      return ra === rb && ca === cb ? ["ref", tab, ra, ca] : ["range", tab, ra, ca, rb, cb];
    }
    /** VBA 사용자 함수 부르기 - 칸 참조 인자는 Range(값·위치), 그 밖은 값. 못 쓰는 문법이면 #NAME?(엑셀이 저장한 값을 그대로 - recalc), 실행 오류는 #VALUE! */
    udf(name, args, sh) {
      const V = API.vba.lib, conv = (v) => (v instanceof FErr ? new V.CVErr(v.code) : v == null ? V.EMPTY : v);
      const vals = args.map((a) => {
        const d = this.deref(a, sh);
        if (d[0] === "ref" || d[0] === "range" || d[0] === "sref") {
          const node = d[0] === "sref" ? this.sref(d, sh) : d, r = this.area(node, sh), t = node[1] == null ? sh : this.sheet(node[1], sh);
          return new V.VRange(r.rows.map((row) => row.map((x) => (x instanceof FErr ? { code: x.code } : x))), node[2], node[3], t ? t.name : "");
        }
        const v = cellv(() => this.ev(a, sh));
        if (v instanceof Rng) { if (v.vals.length === 1) return conv(v.vals[0]); const out = new V.VArr([[1, v.rows.length], [1, v.rows[0].length]]); v.rows.forEach((row, i) => row.forEach((x, j) => { out.d[out.at([i + 1, j + 1])] = conv(x); })); return out; }
        if (v instanceof Lam) throw new FErr("#VALUE!");
        return conv(v);
      });
      API.vba.ctx = { c: this, sh };
      let res;
      try { res = API.vba.call(name, vals); } catch (e) {
        if (V.Pending && e instanceof V.Pending) { for (const x of this.ids) this.pend.add(x); throw new Pend(); }  // 계산하는 칸·그 칸을 부른 칸 모두
        if (e instanceof V.Unsupported) throw new FErr("#NAME?");
        if (e instanceof V.VErr) throw new FErr("#VALUE!");
        throw e;
      }
      const out = V.toCell(res);
      if (out && typeof out === "object" && out.code) throw new FErr(out.code);
      if (out && typeof out === "object" && out.rows) return new Rng(out.rows.map((row) => row.map((x) => (x && typeof x === "object" && x.code ? new FErr(x.code) : x))));
      return out;
    }
    /** 빈 칸(또는 넘친 칸)의 값 - 왼쪽 위의 동적 배열 수식을 먼저 계산해 넘친 값이 있으면 그것 */
    spilled(sh, r, c) {
      if (!this.anchors.has(sh.id)) this.anchors.set(sh.id, Object.entries(sh.cells || {}).filter(([k, raw]) => raw && typeof raw === "object" && raw.f && parseRef(k) && this.isDyn(raw)).map(([k]) => [parseRef(k), k]));
      for (const [[ar, ac], k] of this.anchors.get(sh.id)) { const id = sh.id + "!" + k; if (ar <= r && ac <= c && !this.memo.has(id) && !this.busy.has(id)) this.cell(sh, k); }
      const hit = this.spill.get(sh.id + "!" + r + "," + c);
      return hit ? hit[0] : null;
    }
    /** 배열 결과를 기준 칸 k 에서 오른쪽·아래로 넘긴다 - 자리에 값이 있으면 #SPILL! */
    spillOut(sh, k, v) {
      const [ar, ac] = parseRef(k), h = v.rows.length, w = v.rows[0].length, cells = sh.cells || {};
      if (h * w > 100000) return new FErr("#SPILL!");
      for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) {
        if (!i && !j) continue;
        const raw = cells[colName(ac + j) + (ar + i + 1)];
        const busy = raw && typeof raw === "object" ? !!raw.f || (raw.v != null && raw.v !== "" && !raw.sp) : raw != null && raw !== "";
        if (busy || this.spill.has(sh.id + "!" + (ar + i) + "," + (ac + j))) return new FErr("#SPILL!");
      }
      for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) if (i || j) { const x = v.rows[i][j]; this.spill.set(sh.id + "!" + (ar + i) + "," + (ac + j), [x == null ? 0 : x, k, sh.id, colName(ac + j) + (ar + i + 1)]); }
      this.extent.set(sh.id + "!" + k, [h, w]);
      return v.rows[0][0];
    }
    sheet(name, cur) { if (name == null) return cur; return this.sheets.find((s) => String(s.name || "").toLowerCase() === name.toLowerCase()) || null; }
    value(sh, r, c) {
      const k = colName(c) + (r + 1), raw = (sh.cells || {})[k];
      if (raw && typeof raw === "object" && raw.f) return this.cell(sh, k);
      let v = raw && typeof raw === "object" ? (raw.v === undefined || raw.sp ? null : raw.v) : raw === undefined ? null : raw;
      if (v == null) v = this.spilled(sh, r, c);
      return typeof v === "string" && ERRS.includes(v) ? new FErr(v) : v;
    }
    cell(sh, k) {
      const id = sh.id + "!" + k;
      if (this.memo.has(id)) { if (this.pend.has(id)) for (const x of this.ids) this.pend.add(x); return this.memo.get(id); }
      if (this.busy.has(id)) return new FErr("#REF!");
      this.busy.add(id); this.at.push(parseRef(k)); this.ids.push(id);
      const f = sh.cells[k].f; let v;
      try {
        let a = this.ast.get(f); if (!a) { try { a = parse(f.replace(/^=/, "")); } catch (e) { a = ["err", e instanceof FErr ? e.code : "#NAME?"]; } this.ast.set(f, a); }
        v = this.ev(a, sh);
        if (this.isDyn(sh.cells[k])) {
          if (isMulti(v)) v = this.spillOut(sh, k, v);
          if (!(v instanceof FErr) && !this.extent.has(id)) this.extent.set(id, [1, 1]);
        }
        if (v instanceof Lam) v = new FErr("#CALC!");  // 칸 값이 함수 - 엑셀도 #CALC!
        if (v instanceof Rng) v = v.vals.length === 1 ? v.vals[0] : new FErr("#VALUE!");
        if (v == null) v = 0;
        if (!(v instanceof FErr)) v = fix(v);
      } catch (e) { v = e instanceof FErr ? e : new FErr("#VALUE!"); }
      this.busy.delete(id); this.at.pop(); this.ids.pop(); this.memo.set(id, v);
      return v;
    }
    dim(s) {
      if (!this.dims.has(s.id)) { let rr = 0, cc = 0; for (const k of Object.keys(s.cells || {})) { const p = parseRef(k); if (p) { rr = Math.max(rr, p[0] + 1); cc = Math.max(cc, p[1] + 1); } } this.dims.set(s.id, [rr, cc]); }
      return this.dims.get(s.id);
    }
    bounds(n, s) {
      let [r1, c1, r2, c2] = [n[2], n[3], n[4], n[5]];
      if (r2 < 0 || c2 < 0) { const [rr, cc] = this.dim(s); if (r2 < 0) r2 = Math.max(rr - 1, r1); if (c2 < 0) c2 = Math.max(cc - 1, c1); }
      return [r1, c1, r2, c2];
    }
    rng(n, sh) {
      const s = this.sheet(n[1], sh); if (!s) throw new FErr("#REF!");
      const [r1, c1, r2, c2] = this.bounds(n, s), rows = [];
      for (let r = r1; r <= r2; r++) { const row = []; for (let c = c1; c <= c2; c++) row.push(this.value(s, r, c)); rows.push(row); }
      return new Rng(rows);
    }
    ev(n, sh) {
      switch (n[0]) {
        case "lit": return n[1];
        case "err": throw new FErr(n[1]);
        case "arr": return n[1];  // 계산된 배열을 범위처럼(GROUPBY 집계 - 빈 칸·글은 건너뜀)
        case "ref": { const s = this.sheet(n[1], sh); if (!s) throw new FErr("#REF!"); const v = this.value(s, n[2], n[3]); if (v instanceof FErr) throw v; return v; }
        case "range": return this.rng(n, sh);
        case "spill": {  // H2# - 그 칸의 동적 배열이 넘친 범위 전체
          const s = this.sheet(n[1], sh); if (!s) throw new FErr("#REF!");
          const key = colName(n[3]) + (n[2] + 1), raw = (s.cells || {})[key];
          if (raw && typeof raw === "object" && raw.f) this.cell(s, key);
          const [h, w] = this.extent.get(s.id + "!" + key) || [0, 0]; if (!h) throw new FErr("#REF!");
          return this.rng(["range", n[1], n[2], n[3], n[2] + h - 1, n[3] + w - 1], sh);
        }
        case "sref": return this.ev(this.sref(n, sh), sh);  // 표 구조적 참조 → 셀·범위
        case "name": {
          for (let i = this.scope.length - 1; i >= 0; i--) if (this.scope[i].has(n[1])) { const v = this.scope[i].get(n[1]); if (v instanceof FErr) throw v; return v; }
          const node = this.named(n[1], sh); if (!node) throw new FErr("#NAME?");  // 이름 정의(매출 = 데이터!$B$2:$B$5 · 세율 = 0.1)
          if (this.naming.has(n[1])) throw new FErr("#REF!");  // 이름이 자기를 부른다
          this.naming.add(n[1]); try { return this.ev(node, sh); } finally { this.naming.delete(n[1]); }
        }
        case "neg": { const x = this.ev(n[1], sh); return isMulti(x) ? amap((v) => -toNum(v), x) : -toNum(this.sc(x)); }
        case "pct": return toNum(this.sc(this.ev(n[1], sh))) / 100;
        case "bin": {
          const ra = this.ev(n[2], sh), rb = this.ev(n[3], sh);
          if (isMulti(ra) || isMulti(rb)) return azip((x, y) => this.binop(n[1], x, y), ra, rb);
          return this.binop(n[1], this.sc(ra), this.sc(rb));
        }
        case "fn": {
          const fn = FUNCS[n[1]];
          if (!fn) {
            const lam = this.lamOf(n[1], sh);
            if (lam) return this.call(lam, n[2].map((a) => cellv(() => this.ev(a, sh))), sh);  // LET 이름·이름 정의에 담긴 LAMBDA - f(1, 2)
            if (API.vba && API.vba.has(n[1])) return this.udf(n[1], n[2], sh);  // VBA 사용자 함수(vba.js - 화면이 setVba 로 넣는다)
            throw new FErr("#NAME?");
          }
          if (SCALAR.has(n[1])) {  // 한 칸 함수에 배열이 오면 칸마다
            const vals = n[2].map((a) => (a[0] !== "lit" ? cellv(() => this.ev(a, sh)) : a[1]));
            if (vals.some(isMulti)) {
              const big = vals.filter((v) => v instanceof Rng).sort((a, b) => b.vals.length - a.vals.length)[0], h = big.rows.length, w = big.rows[0].length;
              const pick = (v, i, j) => (v instanceof Rng ? v.rows[v.rows.length > 1 ? i : 0][v.rows[0].length > 1 ? j : 0] : v);
              return new Rng(Array.from({ length: h }, (_, i) => Array.from({ length: w }, (_, j) => cellv(() => fn(this, vals.map((v) => ["lit", pick(v, i, j)]), sh)))));
            }
          }
          return fn(this, n[2], sh);
        }
      }
      throw new FErr("#VALUE!");
    }
    binop(op, a, b) {
      if (a instanceof FErr) throw a; if (b instanceof FErr) throw b;
      switch (op) {
        case "+": return toNum(a) + toNum(b);
        case "-": return toNum(a) - toNum(b);
        case "*": return toNum(a) * toNum(b);
        case "/": { const d = toNum(b); if (d === 0) throw new FErr("#DIV/0!"); return toNum(a) / d; }
        case "^": { const r = Math.pow(toNum(a), toNum(b)); if (!isFinite(r) || Number.isNaN(r)) throw new FErr("#NUM!"); return r; }
        case "&": return toStr(a) + toStr(b);
      }
      return compare(a, b, op);
    }
    sc(v) {
      if (v instanceof FErr) throw v;
      if (v instanceof Rng) { if (v.vals.length !== 1) throw new FErr("#VALUE!"); const x = v.vals[0]; if (x instanceof FErr) throw x; return x; }
      return v;
    }
    one(A, i, sh, d) { return i >= A.length ? d : this.sc(this.ev(A[i], sh)); }
    nums(A, sh, mode = "") {
      const out = [];
      for (const a0 of A) {
        const a = this.deref(a0, sh), isRef = a[0] === "ref" || a[0] === "range" || a[0] === "arr", v = this.ev(a, sh);
        for (const x of v instanceof Rng ? v.vals : [v]) {
          if (x instanceof FErr) { if (mode === "count" || mode === "counta" || mode === "blank") { if (mode === "counta") out.push(x); continue; } throw x; }
          if (mode === "blank") { if (x == null || x === "") out.push(x); }
          else if (isRef) { if (isNum(x)) out.push(x); else if (mode === "counta" && x != null && x !== "") out.push(x); }
          else if (mode === "counta") { if (x != null) out.push(x); }
          else if (mode === "count") { if (isNum(x) || typeof x === "boolean" || (typeof x === "string" && parseNumberText(x) !== null)) out.push(x); }
          else out.push(toNum(x));
        }
      }
      return out;
    }
    area(a, sh) { const v = this.ev(a, sh); return v instanceof Rng ? v : new Rng([[v]]); }
    refnode(n, sh) {
      n = this.deref(n, sh);
      if (n[0] === "ref" || n[0] === "range") return n;
      if (n[0] === "fn" && n[1] === "INDIRECT") { let node; try { node = parse(toStr(this.one(n[2], 0, sh))); } catch (e) { throw new FErr("#REF!"); } if (node[0] !== "ref" && node[0] !== "range") throw new FErr("#REF!"); return node; }
      if (n[0] === "fn" && n[1] === "OFFSET") {
        const A = n[2], base = this.refnode(A[0], sh), dr = Math.trunc(toNum(this.one(A, 1, sh, 0))), dc = Math.trunc(toNum(this.one(A, 2, sh, 0))), s = this.sheet(base[1], sh) || sh;
        let r1 = base[2], c1 = base[3], h = 1, w = 1;
        if (base[0] === "range") { const b = this.bounds(base, s); [r1, c1] = b; h = b[2] - b[0] + 1; w = b[3] - b[1] + 1; }
        if (A.length > 3 && !(A[3][0] === "lit" && A[3][1] == null)) h = Math.trunc(toNum(this.one(A, 3, sh)));
        if (A.length > 4 && !(A[4][0] === "lit" && A[4][1] == null)) w = Math.trunc(toNum(this.one(A, 4, sh)));
        r1 += dr; c1 += dc;
        if (r1 < 0 || c1 < 0 || h < 1 || w < 1) throw new FErr("#REF!");
        return h === 1 && w === 1 ? ["ref", base[1], r1, c1] : ["range", base[1], r1, c1, r1 + h - 1, c1 + w - 1];
      }
      throw new FErr("#REF!");
    }
  }

  function matchPos(look, vals, mode) {
    if (mode === 0) {
      const ok = typeof look === "string" && /[*?]/.test(look) ? criteria(look) : (v) => rank(v) === rank(look) && compare(v, look, "=");
      for (let i = 0; i < vals.length; i++) if (ok(vals[i])) return i;
      throw new FErr("#N/A");
    }
    let best = null;
    for (let i = 0; i < vals.length; i++) {
      const v = vals[i]; if (v == null || rank(v) !== rank(look)) continue;
      if ((mode === 1 && compare(v, look, "<=")) || (mode === -1 && compare(v, look, ">="))) best = i; else if (best !== null) break;
    }
    if (best === null) throw new FErr("#N/A");
    return best;
  }
  const raise = (v) => { if (v instanceof FErr) throw v; return v; };
  function ifAgg(kind) {
    return (c, A, sh) => {
      const multi = kind.endsWith("S"), cnt = kind.startsWith("COUNT");
      const sumR = multi ? (cnt ? null : c.area(A[0], sh)) : (A.length > 2 && !cnt ? c.area(A[2], sh) : null);
      const pairs = multi ? (cnt ? A : A.slice(1)) : A.slice(0, 2), conds = [];
      for (let i = 0; i + 1 < pairs.length; i += 2) conds.push([c.area(pairs[i], sh).vals, criteria(c.one(pairs, i + 1, sh))]);
      const n = conds.length ? conds[0][0].length : 0, hits = [];
      for (let j = 0; j < n; j++) if (conds.every(([vals, ok]) => j < vals.length && ok(vals[j]))) hits.push(j);
      if (cnt) return hits.length;
      const src = sumR ? sumR.vals : conds[0][0], xs = hits.filter((j) => j < src.length && isNum(src[j])).map((j) => src[j]);
      if (kind.startsWith("AVERAGE")) { if (!xs.length) throw new FErr("#DIV/0!"); return xs.reduce((s, x) => s + x, 0) / xs.length; }
      return xs.reduce((s, x) => s + x, 0);
    };
  }
  function lookup(horiz) {
    return (c, A, sh) => {
      const look = c.one(A, 0, sh), tbl = c.area(A[1], sh), idx = Math.trunc(toNum(c.one(A, 2, sh)));
      const approx = A.length > 3 ? toBool(c.one(A, 3, sh, true)) : true;
      const rows = horiz ? tbl.rows[0].map((_, j) => tbl.rows.map((r) => r[j])) : tbl.rows;
      if (idx < 1 || idx > (rows[0] ? rows[0].length : 0)) throw new FErr("#REF!");
      return raise(rows[matchPos(look, rows.map((r) => r[0]), approx ? 1 : 0)][idx - 1]);
    };
  }
  function rowCol(which) {
    const f = (c, A, sh) => {
      if (!A.length) { const at = c.at.length ? c.at[c.at.length - 1] : [0, 0]; return at[which] + 1; }
      const n = c.deref(A[0], sh);
      if (n[0] === "ref") return n[2 + which] + 1;
      if (n[0] === "range") {
        const s = c.sheet(n[1], sh) || sh, [r1, c1, r2, c2] = c.bounds(n, s);
        if (which === 0) return r2 > r1 ? new Rng(Array.from({ length: r2 - r1 + 1 }, (_, i) => [r1 + i + 1])) : r1 + 1;
        return c2 > c1 ? new Rng([Array.from({ length: c2 - c1 + 1 }, (_, i) => c1 + i + 1)]) : c1 + 1;
      }
      if (n[0] === "fn" && (n[1] === "INDIRECT" || n[1] === "OFFSET")) return f(c, [c.refnode(n, sh)], sh);
      throw new FErr("#VALUE!");
    };
    return f;
  }
  const isF = (test) => (c, A, sh) => { let v; try { v = c.one(A, 0, sh); } catch (e) { if (e instanceof FErr) return test(e); throw e; } return test(v); };
  const t1 = (f) => (c, A, sh) => f(toStr(c.one(A, 0, sh)));
  const findF = (ci) => (c, A, sh) => {
    const what = toStr(c.one(A, 0, sh)), s = toStr(c.one(A, 1, sh)), st = A.length > 2 ? Math.trunc(toNum(c.one(A, 2, sh))) : 1;
    if (ci) {
      const rx = new RegExp(what.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[\\s\\S]*").replace(/\?/g, "[\\s\\S]"), "i"), m = rx.exec(s.slice(st - 1));
      if (!m) throw new FErr("#VALUE!"); return m.index + st;
    }
    const i = s.indexOf(what, st - 1); if (i < 0) throw new FErr("#VALUE!"); return i + 1;
  };
  function concatF(c, A, sh) { return A.map((a) => { const v = c.ev(a, sh); return v instanceof Rng ? v.vals.map(toStr).join("") : toStr(v); }).join(""); }
  function formatValue(v, fmt) {
    const secs = fmt.split(";"); let sec = secs[0], neg = v < 0;
    if (neg && secs[1]) { sec = secs[1]; v = -v; neg = false; }
    const bare = sec.replace(/"[^"]*"/g, "");
    if (/[yd]|mm(?!.*0)/i.test(bare) && !/[#0]/.test(bare)) {
      const d = new Date(DAY0 + v * 864e5), Y = d.getUTCFullYear(), M = d.getUTCMonth() + 1, D = d.getUTCDate(), p2 = (x) => String(x).padStart(2, "0");
      return sec.replace(/"([^"]*)"/g, "$1").replace(/yyyy/gi, Y).replace(/yy/gi, p2(Y % 100)).replace(/mm/g, p2(M)).replace(/(?<![A-Za-z])m(?![A-Za-z])/g, M).replace(/dd/gi, p2(D)).replace(/(?<![A-Za-z])d(?![A-Za-z])/gi, D);
    }
    const m = /([#0,]*0|#[#,]*)(\.([0#]+))?/.exec(sec); if (!m) return general(v);
    const x = Math.abs(sec.includes("%") ? v * 100 : v), dec = m[3] || "", minD = (dec.match(/0/g) || []).length, maxD = dec.length;
    let s = roundX(x, maxD).toFixed(maxD);
    if (maxD > minD) s = s.replace(new RegExp(`0{1,${maxD - minD}}$`), "").replace(/\.$/, "");
    if (m[1].includes(",")) { const [i, d] = s.split("."); s = i.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (d ? "." + d : ""); }
    const lit = (t) => t.replace(/"([^"]*)"|([^"]+)/g, (_, q, u) => (q != null ? q : u.replace(/\\/g, "").replace(/[#0,?]/g, "")));
    return (neg && roundX(x, maxD) !== 0 ? "-" : "") + lit(sec.slice(0, m.index)) + s + lit(sec.slice(m.index + m[0].length));
  }
  const modF = (a, b) => { if (b === 0) throw new FErr("#DIV/0!"); return a - b * Math.floor(a / b); };
  const n0 = (c, A, sh, i, d) => Math.trunc(toNum(c.one(A, i, sh, d)));
  const FUNCS = {
    SUM: (c, A, sh) => c.nums(A, sh).reduce((s, x) => s + x, 0),
    AVERAGE: (c, A, sh) => { const l = c.nums(A, sh); if (!l.length) throw new FErr("#DIV/0!"); return l.reduce((s, x) => s + x, 0) / l.length; },
    MEDIAN: (c, A, sh) => { const l = c.nums(A, sh).sort((a, b) => a - b); if (!l.length) throw new FErr("#NUM!"); const m = l.length >> 1; return l.length % 2 ? l[m] : (l[m - 1] + l[m]) / 2; },
    PRODUCT: (c, A, sh) => c.nums(A, sh).reduce((p, x) => p * x, 1),
    MIN: (c, A, sh) => { const l = c.nums(A, sh); return l.length ? Math.min(...l) : 0; },
    MAX: (c, A, sh) => { const l = c.nums(A, sh); return l.length ? Math.max(...l) : 0; },
    COUNT: (c, A, sh) => c.nums(A, sh, "count").length, COUNTA: (c, A, sh) => c.nums(A, sh, "counta").length, COUNTBLANK: (c, A, sh) => c.nums(A, sh, "blank").length,
    SUMIF: ifAgg("SUMIF"), SUMIFS: ifAgg("SUMIFS"), COUNTIF: ifAgg("COUNTIF"), COUNTIFS: ifAgg("COUNTIFS"), AVERAGEIF: ifAgg("AVERAGEIF"), AVERAGEIFS: ifAgg("AVERAGEIFS"),
    SUMPRODUCT: (c, A, sh) => {
      const arrs = A.map((a) => c.area(a, sh).vals); if (new Set(arrs.map((x) => x.length)).size > 1) throw new FErr("#VALUE!");
      let t = 0; for (let i = 0; i < (arrs[0] || []).length; i++) t += arrs.reduce((p, x) => p * (isNum(x[i]) ? x[i] : 0), 1); return t;
    },
    ROUND: (c, A, sh) => roundX(toNum(c.one(A, 0, sh)), n0(c, A, sh, 1, 0)), ROUNDUP: (c, A, sh) => roundX(toNum(c.one(A, 0, sh)), n0(c, A, sh, 1, 0), "up"),
    ROUNDDOWN: (c, A, sh) => roundX(toNum(c.one(A, 0, sh)), n0(c, A, sh, 1, 0), "down"),
    INT: (c, A, sh) => Math.floor(toNum(c.one(A, 0, sh))), ABS: (c, A, sh) => Math.abs(toNum(c.one(A, 0, sh))), MOD: (c, A, sh) => modF(toNum(c.one(A, 0, sh)), toNum(c.one(A, 1, sh))),
    IF: (c, A, sh) => {
      if (!A.length) throw new FErr("#VALUE!");
      const cond = c.ev(A[0], sh);
      if (isMulti(cond)) {
        const yes = A.length > 1 ? c.ev(A[1], sh) : true, no = A.length > 2 ? c.ev(A[2], sh) : false;
        const pick = (v, i, j) => (v instanceof Rng ? v.rows[v.rows.length > 1 ? i : 0][v.rows[0].length > 1 ? j : 0] : v);
        return new Rng(cond.rows.map((row, i) => row.map((v, j) => cellv(() => (toBool(v) ? pick(yes, i, j) : pick(no, i, j))))));
      }
      return toBool(c.sc(cond)) ? (A.length > 1 ? c.one(A, 1, sh, true) : true) : (A.length > 2 ? c.one(A, 2, sh, false) : false);
    },
    IFS: (c, A, sh) => { for (let i = 0; i + 1 < A.length; i += 2) if (toBool(c.one(A, i, sh))) return c.one(A, i + 1, sh); throw new FErr("#N/A"); },
    IFERROR: (c, A, sh) => { try { return c.one(A, 0, sh); } catch (e) { if (e instanceof FErr) return A.length > 1 ? c.one(A, 1, sh, "") : ""; throw e; } },
    IFNA: (c, A, sh) => { try { return c.one(A, 0, sh); } catch (e) { if (e instanceof FErr && e.code === "#N/A") return A.length > 1 ? c.one(A, 1, sh, "") : ""; throw e; } },
    SWITCH: (c, A, sh) => { const x = c.one(A, 0, sh); let i = 1; for (; i + 1 < A.length; i += 2) if (compare(x, c.one(A, i, sh), "=")) return c.one(A, i + 1, sh); if (i < A.length) return c.one(A, i, sh); throw new FErr("#N/A"); },
    CHOOSE: (c, A, sh) => { const i = n0(c, A, sh, 0); if (i < 1 || i >= A.length) throw new FErr("#VALUE!"); return c.one(A, i, sh); },
    AND: (c, A, sh) => A.every((_, i) => toBool(c.one(A, i, sh))), OR: (c, A, sh) => A.some((_, i) => toBool(c.one(A, i, sh))), NOT: (c, A, sh) => !toBool(c.one(A, 0, sh)),
    VLOOKUP: lookup(false), HLOOKUP: lookup(true),
    MATCH: (c, A, sh) => matchPos(c.one(A, 0, sh), c.area(A[1], sh).vals, A.length > 2 ? n0(c, A, sh, 2, 1) : 1) + 1,
    INDEX: (c, A, sh) => {
      const t = c.area(A[0], sh); let r = A.length > 1 ? n0(c, A, sh, 1, 0) : 0, k = A.length > 2 ? n0(c, A, sh, 2, 0) : 0;
      if (t.rows.length === 1 && A.length === 2) { k = r; r = 1; }
      if (r < 0 || k < 0 || r > t.rows.length || (t.rows[0] && k > t.rows[0].length)) throw new FErr("#REF!");
      return raise(t.rows[Math.max(r, 1) - 1][Math.max(k, 1) - 1]);
    },
    XLOOKUP: (c, A, sh) => {
      const look = c.one(A, 0, sh), src = c.area(A[1], sh).vals, ret = c.area(A[2], sh); let i;
      try { i = matchPos(look, src, 0); } catch (e) { if (e instanceof FErr && A.length > 3 && !(A[3][0] === "lit" && A[3][1] == null)) return c.one(A, 3, sh); throw e; }
      const rv = ret.rows.length === src.length && ret.rows.length > 1 ? ret.rows[i] : ret.vals.length === src.length ? [ret.vals[i]] : null;
      if (!rv) throw new FErr("#VALUE!"); return raise(rv[0]);
    },
    CONCAT: concatF, CONCATENATE: concatF,
    TEXTJOIN: (c, A, sh) => { const d = toStr(c.one(A, 0, sh)), skip = toBool(c.one(A, 1, sh)), parts = []; for (const a of A.slice(2)) { const v = c.ev(a, sh); for (const x of v instanceof Rng ? v.vals : [v]) { const s = toStr(x); if (s || !skip) parts.push(s); } } return parts.join(d); },
    LEFT: (c, A, sh) => toStr(c.one(A, 0, sh)).slice(0, A.length > 1 ? n0(c, A, sh, 1) : 1),
    RIGHT: (c, A, sh) => { const s = toStr(c.one(A, 0, sh)), n = A.length > 1 ? n0(c, A, sh, 1) : 1; return n ? s.slice(-n) : ""; },
    MID: (c, A, sh) => { const s = toStr(c.one(A, 0, sh)), st = n0(c, A, sh, 1), n = n0(c, A, sh, 2); if (st < 1 || n < 0) throw new FErr("#VALUE!"); return s.slice(st - 1, st - 1 + n); },
    LEN: t1((s) => [...s].length), TRIM: t1((s) => s.replace(/^ +| +$/g, "").replace(/ +/g, " ")), UPPER: t1((s) => s.toUpperCase()), LOWER: t1((s) => s.toLowerCase()),
    SUBSTITUTE: (c, A, sh) => {
      const s = toStr(c.one(A, 0, sh)), o = toStr(c.one(A, 1, sh)), nw = toStr(c.one(A, 2, sh));
      if (A.length > 3) { const k = n0(c, A, sh, 3); let idx = -1; for (let i = 0; i < k; i++) { idx = s.indexOf(o, idx + 1); if (idx < 0) return s; } return s.slice(0, idx) + nw + s.slice(idx + o.length); }
      return o ? s.split(o).join(nw) : s;
    },
    FIND: findF(false), SEARCH: findF(true),
    VALUE: (c, A, sh) => { const v = c.one(A, 0, sh); if (isNum(v)) return v; const n = parseNumberText(toStr(v)); if (n === null) throw new FErr("#VALUE!"); return n; },
    TEXT: (c, A, sh) => { const v = c.one(A, 0, sh), f = toStr(c.one(A, 1, sh)); let x; try { x = toNum(v); } catch (e) { return toStr(v); } return formatValue(x, f); },
    TODAY: () => serial(new Date(Date.UTC(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()))),
    NOW: () => { const t = new Date(); return serial(new Date(Date.UTC(t.getFullYear(), t.getMonth(), t.getDate()))) + (t.getHours() * 3600 + t.getMinutes() * 60 + t.getSeconds()) / 86400; },
    DATE: (c, A, sh) => { let y = n0(c, A, sh, 0); const m = n0(c, A, sh, 1), d = n0(c, A, sh, 2); if (y < 1900) y += 1900; return serial(addMonths(new Date(Date.UTC(y, 0, 1)), m - 1)) + d - 1; },
    YEAR: (c, A, sh) => dateOf(c.one(A, 0, sh)).getUTCFullYear(), MONTH: (c, A, sh) => dateOf(c.one(A, 0, sh)).getUTCMonth() + 1, DAY: (c, A, sh) => dateOf(c.one(A, 0, sh)).getUTCDate(),
    WEEKDAY: (c, A, sh) => { const d = dateOf(c.one(A, 0, sh)).getUTCDay(), t = A.length > 1 ? n0(c, A, sh, 1) : 1; return t === 2 ? (d + 6) % 7 + 1 : t === 3 ? (d + 6) % 7 : d + 1; },
    EDATE: (c, A, sh) => serial(addMonths(dateOf(c.one(A, 0, sh)), n0(c, A, sh, 1))),
    EOMONTH: (c, A, sh) => { const d = addMonths(dateOf(c.one(A, 0, sh)), n0(c, A, sh, 1)); return serial(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0))); },
    ROW: rowCol(0), COLUMN: rowCol(1),
    ROWS: (c, A, sh) => c.area(A[0], sh).rows.length, COLUMNS: (c, A, sh) => { const r = c.area(A[0], sh); return r.rows.length ? r.rows[0].length : 0; },
    INDIRECT: (c, A, sh) => c.ev(c.refnode(["fn", "INDIRECT", A], sh), sh), OFFSET: (c, A, sh) => c.ev(c.refnode(["fn", "OFFSET", A], sh), sh),
    SUBTOTAL: (c, A, sh) => { const k = n0(c, A, sh, 0) % 100, fn = { 1: "AVERAGE", 2: "COUNT", 3: "COUNTA", 4: "MAX", 5: "MIN", 6: "PRODUCT", 9: "SUM" }[k]; if (!fn) throw new FErr("#VALUE!"); return FUNCS[fn](c, A.slice(1), sh); },
    HYPERLINK: (c, A, sh) => {  // 값은 보이는 글 - 주소는 칸마다 links 에 둔다(시트 화면 Ctrl+클릭 이동, link())
      const v = A.length > 1 ? c.one(A, 1, sh) : c.one(A, 0, sh), id = c.ids[c.ids.length - 1];
      if (id) { const u = cellv(() => toStr(c.one(A, 0, sh))); if (!(u instanceof FErr)) c.links.set(id, u); }  // 값은 sheet_calc.py 와 같게 - 주소 오류는 값에 안 미친다
      return v;
    },
    ISBLANK: isF((v) => v == null || v === ""), ISNUMBER: isF((v) => isNum(v)), ISTEXT: isF((v) => typeof v === "string"), ISERROR: isF((v) => v instanceof FErr), ISNA: isF((v) => v instanceof FErr && v.code === "#N/A"),
  };
  // ---- 동적 배열 함수
  const opt = (c, A, i, sh, d) => (i >= A.length || (A[i][0] === "lit" && A[i][1] == null) ? d : c.one(A, i, sh));
  const truthy = (x) => { if (x instanceof FErr) throw x; if (x == null || x === "") return false; if (typeof x === "string") throw new FErr("#VALUE!"); return !!toNum(x); };
  const tr = (rows) => rows[0].map((_, j) => rows.map((r) => r[j]));
  /** 정렬 순서 - 숫자 < 글(대소문자 무시) < 논리 < 오류. 빈 칸은 따로 맨 뒤 */
  const skey = (v) => (v instanceof FErr ? [3, v.code] : typeof v === "boolean" ? [2, v ? 1 : 0] : isNum(v) ? [0, v] : [1, String(v).toLowerCase()]);
  function sortRows(rows, keys) {
    return rows.slice().sort((a, b) => {
      for (const [get, desc] of keys) {
        const x = get(a), y = get(b);
        if (x == null || y == null) { if ((x == null) !== (y == null)) return x == null ? 1 : -1; continue; }
        const kx = skey(x), ky = skey(y);
        if (kx[0] !== ky[0] || kx[1] !== ky[1]) return (kx[0] !== ky[0] ? kx[0] - ky[0] : kx[1] < ky[1] ? -1 : 1) * (desc ? -1 : 1);
      }
      return 0;
    });
  }
  const ukey = (v) => JSON.stringify(v instanceof FErr ? ["e", v.code] : typeof v === "boolean" ? ["b", v] : isNum(v) ? ["n", v] : v == null ? ["z"] : ["s", String(v).toLowerCase()]);
  Object.assign(FUNCS, {
    FILTER: (c, A, sh) => {
      const rows = c.area(A[0], sh).rows, inc = c.area(A[1], sh), h = rows.length, w = rows[0].length; let out;
      if (inc.rows.length === h && inc.rows[0].length === 1) out = rows.filter((_, i) => truthy(inc.rows[i][0]));
      else if (inc.rows.length === 1 && inc.rows[0].length === w) { const keep = inc.rows[0].map((x, j) => (truthy(x) ? j : -1)).filter((j) => j >= 0); out = keep.length ? rows.map((r) => keep.map((j) => r[j])) : []; }
      else throw new FErr("#VALUE!");
      if (!out.length) { if (A.length > 2 && !(A[2][0] === "lit" && A[2][1] == null)) return c.ev(A[2], sh); throw new FErr("#CALC!"); }
      return new Rng(out);
    },
    SORT: (c, A, sh) => {
      let rows = c.area(A[0], sh).rows; const idx = Math.trunc(toNum(opt(c, A, 1, sh, 1))), order = toNum(opt(c, A, 2, sh, 1)), byCol = toBool(opt(c, A, 3, sh, false));
      if (byCol) rows = tr(rows);
      if (idx < 1 || idx > rows[0].length || (order !== 1 && order !== -1)) throw new FErr("#VALUE!");
      const out = sortRows(rows, [[(r) => r[idx - 1], order === -1]]);
      return new Rng(byCol ? tr(out) : out);
    },
    SORTBY: (c, A, sh) => {
      const rows = c.area(A[0], sh).rows, h = rows.length, w = rows[0].length, keys = []; let byCol = null;
      for (let i = 1; i < A.length; i += 2) {
        const b = c.area(A[i], sh), order = toNum(opt(c, A, i + 1, sh, 1));
        if (order !== 1 && order !== -1) throw new FErr("#VALUE!");
        const col = (b.rows.length === h && b.rows[0].length === 1 && h > 1) || (h === 1 && w === 1), row = b.rows.length === 1 && b.rows[0].length === w;
        if (!(col || row) || (byCol !== null && byCol !== !col)) throw new FErr("#VALUE!");
        byCol = !col; const vals = byCol ? b.rows[0] : b.rows.map((r) => r[0]); keys.push([(k) => vals[k], order === -1]);
      }
      if (!keys.length) throw new FErr("#VALUE!");
      const base = byCol ? tr(rows) : rows, out = sortRows(base.map((_, i) => i), keys).map((i) => base[i]);
      return new Rng(byCol ? tr(out) : out);
    },
    UNIQUE: (c, A, sh) => {
      const rows = c.area(A[0], sh).rows, byCol = toBool(opt(c, A, 1, sh, false)), once = toBool(opt(c, A, 2, sh, false));
      const base = byCol ? tr(rows) : rows, seen = new Map();
      for (const r of base) { const k = r.map(ukey).join("|"); if (!seen.has(k)) seen.set(k, [r, 0]); seen.get(k)[1]++; }
      const out = [...seen.values()].filter(([, n]) => !once || n === 1).map(([r]) => r);
      if (!out.length) throw new FErr("#CALC!");
      return new Rng(byCol ? tr(out) : out);
    },
    SEQUENCE: (c, A, sh) => {
      const h = Math.trunc(toNum(c.one(A, 0, sh))), w = Math.trunc(toNum(opt(c, A, 1, sh, 1))), st = toNum(opt(c, A, 2, sh, 1)), step = toNum(opt(c, A, 3, sh, 1));
      if (h < 1 || w < 1) throw new FErr("#CALC!");
      if (h * w > 100000) throw new FErr("#NUM!");
      return new Rng(Array.from({ length: h }, (_, i) => Array.from({ length: w }, (_, j) => st + step * (i * w + j))));
    },
    TRANSPOSE: (c, A, sh) => new Rng(tr(c.area(A[0], sh).rows)),
    LET: (c, A, sh) => {  // LET(이름1, 값1, …, 계산)
      if (A.length < 3 || A.length % 2 === 0) throw new FErr("#VALUE!");
      c.scope.push(new Map());
      try {
        for (let i = 0; i + 1 < A.length; i += 2) { if (A[i][0] !== "name") throw new FErr("#NAME?"); c.scope[c.scope.length - 1].set(A[i][1], cellv(() => c.ev(A[i + 1], sh))); }
        return c.ev(A[A.length - 1], sh);
      } finally { c.scope.pop(); }
    },
    DATEDIF: (c, A, sh) => {
      const a = dateOf(c.one(A, 0, sh)), b = dateOf(c.one(A, 1, sh)), u = toStr(c.one(A, 2, sh)).toUpperCase();
      if (a > b) throw new FErr("#NUM!");
      const months = (b.getUTCFullYear() - a.getUTCFullYear()) * 12 + b.getUTCMonth() - a.getUTCMonth() - (b.getUTCDate() < a.getUTCDate() ? 1 : 0), days = (x, y) => Math.round((y - x) / 864e5);
      if (u === "Y") return Math.floor(months / 12);
      if (u === "M") return months;
      if (u === "D") return days(a, b);
      if (u === "YM") return months % 12;
      if (u === "MD") return days(addMonths(a, months), b);
      if (u === "YD") { const k = b.getUTCFullYear() - a.getUTCFullYear() - (b.getUTCMonth() * 100 + b.getUTCDate() < a.getUTCMonth() * 100 + a.getUTCDate() ? 1 : 0); return days(addMonths(a, 12 * k), b); }
      throw new FErr("#NUM!");
    },
    NETWORKDAYS: (c, A, sh) => {
      let a = Math.trunc(toNum(c.one(A, 0, sh))), b = Math.trunc(toNum(c.one(A, 1, sh))), sign = 1; const hol = holidays(c, A, 2, sh);
      if (a > b) { [a, b] = [b, a]; sign = -1; }
      let n = 0; for (let d = a; d <= b; d++) if (isWork(d) && !hol.has(d)) n++;
      return sign * n;
    },
    WORKDAY: (c, A, sh) => {
      let d = Math.trunc(toNum(c.one(A, 0, sh))), n = Math.trunc(toNum(c.one(A, 1, sh))); const hol = holidays(c, A, 2, sh), step = n >= 0 ? 1 : -1;
      while (n) { d += step; if (isWork(d) && !hol.has(d)) n -= step; }
      return d;
    },
    XMATCH: (c, A, sh) => {
      const look = c.one(A, 0, sh), vals = c.area(A[1], sh).vals, mode = Math.trunc(toNum(opt(c, A, 2, sh, 0))), order = Math.trunc(toNum(opt(c, A, 3, sh, 1)));
      const idx = vals.map((_, i) => i); if (order < 0) idx.reverse();
      const same = (v) => v != null && rank(v) === rank(look);
      let hit;
      if (mode === 2) { const ok = criteria(look); hit = idx.find((i) => ok(vals[i])); }
      else {
        hit = idx.find((i) => same(vals[i]) && compare(vals[i], look, "="));
        if (hit === undefined && (mode === 1 || mode === -1)) {
          const cand = idx.filter((i) => same(vals[i]) && compare(vals[i], look, mode === 1 ? ">" : "<"));
          if (cand.length) { hit = cand[0]; for (const i of cand) if (compare(vals[i], vals[hit], mode === 1 ? "<" : ">")) hit = i; }
        }
      }
      if (hit === undefined) throw new FErr("#N/A");
      return hit + 1;
    },
  });
  // ---- 배열 모양 함수
  const rowsOf = (c, A, i, sh) => c.area(A[i], sh).rows.map((r) => r.slice());
  const takeDrop = (drop) => (c, A, sh) => {
    const rows = rowsOf(c, A, 0, sh), h = rows.length, w = rows[0].length, r = opt(c, A, 1, sh, null), k = opt(c, A, 2, sh, null);
    const cut = (n, size) => { if (n == null) return [0, size]; n = Math.trunc(toNum(n)); if (drop) return n >= 0 ? [n, size] : [0, size + n]; return n >= 0 ? [0, n] : [size + n, size]; };
    const [r1, r2] = cut(r, h), [c1, c2] = cut(k, w);
    const out = rows.slice(Math.max(r1, 0), Math.max(r2, 0)).map((row) => row.slice(Math.max(c1, 0), Math.max(c2, 0)));
    if (!out.length || !out[0].length) throw new FErr("#CALC!");
    return new Rng(out);
  };
  const chooseRC = (cols) => (c, A, sh) => {
    const rows = rowsOf(c, A, 0, sh), size = cols ? rows[0].length : rows.length, idx = [];
    for (let i = 1; i < A.length; i++) for (const v of c.area(A[i], sh).vals) { const n = Math.trunc(toNum(v)); if (n === 0 || Math.abs(n) > size) throw new FErr("#VALUE!"); idx.push(n > 0 ? n - 1 : size + n); }
    if (!idx.length) throw new FErr("#VALUE!");
    return new Rng(cols ? rows.map((r) => idx.map((j) => r[j])) : idx.map((j) => rows[j]));
  };
  const stack = (horiz) => (c, A, sh) => {
    const parts = A.map((_, i) => rowsOf(c, A, i, sh));
    if (horiz) { const h = Math.max(...parts.map((p) => p.length)); return new Rng(Array.from({ length: h }, (_, i) => [].concat(...parts.map((p) => (i < p.length ? p[i] : Array(p[0].length).fill(new FErr("#N/A"))))))); }
    const w = Math.max(...parts.map((p) => p[0].length));
    return new Rng([].concat(...parts.map((p) => p.map((r) => r.concat(Array(w - r.length).fill(new FErr("#N/A")))))));
  };
  const toLine = (col) => (c, A, sh) => {
    const rows = rowsOf(c, A, 0, sh), ignore = Math.trunc(toNum(opt(c, A, 1, sh, 0))), byCol = toBool(opt(c, A, 2, sh, false));
    let vals = byCol ? [].concat(...rows[0].map((_, j) => rows.map((r) => r[j]))) : [].concat(...rows);
    vals = vals.filter((x) => !(((ignore === 1 || ignore === 3) && x == null) || ((ignore === 2 || ignore === 3) && x instanceof FErr)));
    if (!vals.length) throw new FErr("#CALC!");
    return new Rng(col ? vals.map((x) => [x]) : [vals]);
  };
  Object.assign(FUNCS, {
    TAKE: takeDrop(false), DROP: takeDrop(true), CHOOSECOLS: chooseRC(true), CHOOSEROWS: chooseRC(false), HSTACK: stack(true), VSTACK: stack(false), TOCOL: toLine(true), TOROW: toLine(false),
    TEXTSPLIT: (c, A, sh) => {
      const text = toStr(c.one(A, 0, sh)), cd = toStr(opt(c, A, 1, sh, "")), rd = opt(c, A, 2, sh, null), skip = toBool(opt(c, A, 3, sh, false));
      const pad = A.length > 5 && !(A[5][0] === "lit" && A[5][1] == null) ? opt(c, A, 5, sh, null) : new FErr("#N/A");
      const lines = rd != null && rd !== "" ? text.split(toStr(rd)) : [text];
      let rows = lines.map((ln) => (cd ? ln.split(cd) : [ln]));
      if (skip) rows = rows.map((r) => r.filter((x) => x !== "")).filter((r) => r.length);
      if (!rows.length) throw new FErr("#CALC!");
      const w = Math.max(...rows.map((r) => r.length));
      return new Rng(rows.map((r) => r.concat(Array(w - r.length).fill(pad))));
    },
  });
  function holidays(c, A, i, sh) { return i >= A.length || (A[i][0] === "lit" && A[i][1] == null) ? new Set() : new Set(c.area(A[i], sh).vals.filter((v) => v != null && v !== "").map((v) => Math.trunc(toNum(v)))); }
  function isWork(d) { const w = dateOf(d).getUTCDay(); return w !== 0 && w !== 6; }
  const SCALAR = new Set(["ISNUMBER", "ISTEXT", "ISBLANK", "ISERROR", "ISNA", "SEARCH", "FIND", "LEFT", "RIGHT", "MID", "LEN", "TRIM", "UPPER", "LOWER", "SUBSTITUTE",
    "VALUE", "TEXT", "ABS", "INT", "ROUND", "ROUNDUP", "ROUNDDOWN", "MOD", "YEAR", "MONTH", "DAY", "NOT"]);

  // 모르는 함수(매크로 사용자 함수 등)·읽지 못하는 수식(외부 통합 문서 참조 등) - 엑셀이 마지막에 계산한 값을 둔다
  // ---------------------------------------------------------------- LAMBDA (엑셀 365) - 값으로 넘기는 함수. MAP·BYROW·BYCOL·REDUCE·SCAN·MAKEARRAY·GROUPBY 가 부르고,
  // LET 이름·이름 정의(이름 관리자 사용자 함수 =세후(금액))에 담으면 f(값) 으로 부른다 - sheet_calc.py 와 같은 규칙
  /** 1×1 배열은 값, 더 크면 #CALC!(배열의 배열은 안 된다) */
  function scalar(v) { if (v instanceof Rng) { if (v.vals.length !== 1) throw new FErr("#CALC!"); v = v.vals[0]; } if (v instanceof FErr) throw v; return v; }
  function lamArg(c, A, i, sh) { const f = i < A.length ? c.ev(A[i], sh) : null; if (!(f instanceof Lam)) throw new FErr("#VALUE!"); return f; }
  function reduceF(scan) {
    return (c, A, sh) => {
      let acc = opt(c, A, 0, sh, 0); const arr = c.area(A[1], sh), lam = lamArg(c, A, 2, sh), out = arr.rows.map((row) => row.map((v) => (acc = scalar(c.call(lam, [acc, v], sh)))));
      return scan ? new Rng(out) : acc;
    };
  }
  Object.assign(FUNCS, {
    LAMBDA: (c, A) => { if (!A.length || A.slice(0, -1).some((a) => a[0] !== "name")) throw new FErr("#VALUE!"); return new Lam(A.slice(0, -1).map((a) => a[1]), A[A.length - 1], [...c.scope]); },
    MAP: (c, A, sh) => {
      if (A.length < 2) throw new FErr("#VALUE!");
      const f = lamArg(c, A, A.length - 1, sh), arrs = A.slice(0, -1).map((a) => c.area(a, sh)), h = arrs[0].rows.length, w = arrs[0].rows[0].length;
      if (arrs.some((a) => a.rows.length !== h || a.rows[0].length !== w)) throw new FErr("#VALUE!");
      return new Rng(Array.from({ length: h }, (_, i) => Array.from({ length: w }, (_, j) => cellv(() => scalar(c.call(f, arrs.map((a) => a.rows[i][j]), sh))))));
    },
    BYROW: (c, A, sh) => { const rows = c.area(A[0], sh).rows, lam = lamArg(c, A, 1, sh); return new Rng(rows.map((r) => [cellv(() => scalar(c.call(lam, [new Rng([r])], sh)))])); },
    BYCOL: (c, A, sh) => { const rows = c.area(A[0], sh).rows, lam = lamArg(c, A, 1, sh); return new Rng([rows[0].map((_, j) => cellv(() => scalar(c.call(lam, [new Rng(rows.map((r) => [r[j]]))], sh))))]); },
    REDUCE: reduceF(false), SCAN: reduceF(true),
    MAKEARRAY: (c, A, sh) => {
      const h = Math.trunc(toNum(c.one(A, 0, sh))), w = Math.trunc(toNum(c.one(A, 1, sh))), lam = lamArg(c, A, 2, sh);
      if (h < 1 || w < 1) throw new FErr("#VALUE!"); if (h * w > 100000) throw new FErr("#NUM!");
      return new Rng(Array.from({ length: h }, (_, i) => Array.from({ length: w }, (_, j) => cellv(() => scalar(c.call(lam, [i + 1, j + 1], sh))))));
    },
  });

  // ---------------------------------------------------------------- 수식형 요약 GROUPBY·PIVOTBY (엑셀 365) - sheet_calc.py 와 같은 규칙. 집계는 함수 이름(SUM, 파일에는 _xleta.SUM) 또는 LAMBDA
  const AGG = new Set(["SUM", "AVERAGE", "COUNT", "COUNTA", "MAX", "MIN", "MEDIAN", "PRODUCT"]);
  function aggFn(c, n, sh) { const nm = n[0] === "name" ? n[1].replace(/^_XLETA\./, "") : null; if (AGG.has(nm)) return nm; const f = c.ev(n, sh); if (!(f instanceof Lam)) throw new FErr("#VALUE!"); return f; }
  function agg(c, fn, vals, sh) {
    const arr = new Rng(vals.length ? vals.map((v) => [v]) : [[null]]);
    try { return fn instanceof Lam ? scalar(c.call(fn, [arr], sh)) : FUNCS[fn](c, [["arr", arr]], sh); } catch (e) { if (e instanceof FErr) return e; throw e; }
  }
  /** 머리글 인수(생략 = 값 첫 줄이 글이고 둘째 줄이 숫자면 1) → [자료 첫 줄이 머리글인가, 결과에 머리글을 보이나]. 0 없음 · 1 있음 · 2 없음(만들어 보임) · 3 있음(보임) */
  function fields(c, A, iHdr, vals, sh) {
    let hdr = opt(c, A, iHdr, sh, null);
    if (hdr == null) hdr = vals.length > 1 && typeof vals[0][0] === "string" && isNum(vals[1][0]) ? 1 : 0;
    hdr = Math.trunc(toNum(hdr));
    if (![0, 1, 2, 3].includes(hdr)) throw new FErr("#VALUE!");
    return [hdr === 1 || hdr === 3, hdr === 2 || hdr === 3];
  }
  /** 머리글 - 자료 첫 줄, 없으면 만든 이름(Row Field 1 · Column Field 1 · Value 1, 엑셀과 같게) */
  const names = (has, rows, w, label) => (has ? rows[0].map((v) => (v == null ? "" : v)) : Array.from({ length: w }, (_, i) => `${label} ${i + 1}`));
  /** 정렬 인수(한 값 또는 배열, 생략 = 1) → [단계별 내림차순인가, 값 정렬 [값 열, 내림차순인가] 또는 null]. ±n ≤ 키 열 수는 그 단계의 키(나머지 단계는 오름차순),
   *  그보다 크면 값 열 - 값 열은 혼자만(배열에 섞으면 #VALUE!). 0 은 #VALUE!(엑셀과 같게) */
  function sorts(c, A, i, sh, kw, vw) {
    const ks = i >= A.length || (A[i][0] === "lit" && A[i][1] == null) ? [1] : [].concat(...c.area(A[i], sh).rows).map((v) => Math.trunc(toNum(v)));
    const desc = Array(kw).fill(false); let val = null;
    for (const s of ks) {
      if (!s || Math.abs(s) > kw + vw) throw new FErr("#VALUE!");
      if (Math.abs(s) > kw) { if (ks.length > 1) throw new FErr("#VALUE!"); val = [Math.abs(s) - kw - 1, s < 0]; } else desc[Math.abs(s) - 1] = s < 0;
    }
    return [desc, val];
  }
  /** 필드(행 또는 열) → 줄 [보이는 키, 행 번호들, 소계·합계인가]. 단계마다 묶어 키로 정렬하고(desc), 값 정렬(val)이면 그 묶음의 집계값(score)으로 다시 - 같은 값은 키 순서.
   *  소계는 1 ~ |깊이|-1 단계, 합계는 맨 뒤(깊이 음수면 소계·합계가 묶음 앞). innerOnly: 소계 없는 바깥 단계는 값으로 정렬하지 않는다(PIVOTBY 열, 엑셀과 같게) */
  function tree(keys, idx, depth, desc, val, score, innerOnly) {
    const kw = keys[0].length, d = Math.abs(depth);
    if (d > kw) throw new FErr("#VALUE!");
    const cols = Array.from({ length: kw }, (_, lv) => keys.map((r) => [r[lv]]));
    const rec = (lv, ids, pre) => {
      let gs = sortRows(groups(cols[lv], ids), [[(g) => g[0][0], desc[lv]]]);
      if (val && (!innerOnly || lv === kw - 1 || lv < d - 1)) gs = sortRows(gs, [[(g) => score(g[1], val[0]), val[1]]]);
      const out = [];
      for (const [[k], ks] of gs) {
        if (lv === kw - 1) { out.push([[...pre, k], ks, false]); continue; }
        const sub = lv < d - 1 ? [[[...pre, k, ...Array(kw - lv - 1).fill("")], ks, true]] : [], kids = rec(lv + 1, ks, [...pre, k]);
        out.push(...(depth < 0 ? [...sub, ...kids] : [...kids, ...sub]));
      }
      return out;
    };
    let out = rec(0, idx, []);
    if (depth) { const tot = [[d === 1 ? "Total" : "Grand Total", ...Array(kw - 1).fill("")], idx.slice(), true]; out = depth < 0 ? [tot, ...out] : [...out, tot]; }
    return out;
  }
  function picked(c, A, i, n, sh) {  // 거르기 배열(행마다 참·거짓) → 남길 행 번호
    if (i >= A.length || (A[i][0] === "lit" && A[i][1] == null)) return [...Array(n).keys()];
    const f = c.area(A[i], sh).rows; if (f.length !== n) throw new FErr("#VALUE!");
    return [...Array(n).keys()].filter((k) => truthy(f[k][0]));
  }
  function groups(rows, idx) {  // 같은 키(대소문자 무시)끼리 - 처음 나온 순서, [보이는 키, 행 번호들]
    const seen = new Map(), out = [];
    for (const k of idx) { const key = rows[k].map(ukey).join("|"); if (!seen.has(key)) { const g = [rows[k].map((v) => (v == null ? "" : v)), []]; seen.set(key, g); out.push(g); } seen.get(key)[1].push(k); }
    return out;
  }
  Object.assign(FUNCS, {
    GROUPBY: (c, A, sh) => {  // GROUPBY(행 필드, 값, 함수, [머리글], [합계 깊이 1 - 2 이상은 소계], [정렬 1 - 배열이면 단계별], [거르기])
      let keys = c.area(A[0], sh).rows, vals = c.area(A[1], sh).rows; const fn = aggFn(c, A[2], sh);
      if (keys.length !== vals.length) throw new FErr("#VALUE!");
      const [has, show] = fields(c, A, 3, vals, sh), kw = keys[0].length, vw = vals[0].length, kh = names(has, keys, kw, "Row Field"), vh = names(has, vals, vw, "Value");
      if (has) { keys = keys.slice(1); vals = vals.slice(1); }
      const depth = Math.trunc(toNum(opt(c, A, 4, sh, 1))), [desc, val] = sorts(c, A, 5, sh, kw, vw), idx = picked(c, A, 6, keys.length, sh);
      if (!idx.length) throw new FErr("#CALC!");
      const v = (ks, j) => agg(c, fn, ks.map((i) => vals[i][j]), sh);
      const out = tree(keys, idx, depth, desc, val, v, false).map(([k, ks]) => [...k, ...Array.from({ length: vw }, (_, j) => v(ks, j))]);
      return new Rng(show ? [[...kh, ...vh], ...out] : out);
    },
    PIVOTBY: (c, A, sh) => {  // PIVOTBY(행 필드, 열 필드, 값, 함수, [머리글], [행 합계 1], [행 정렬 1], [열 합계 1], [열 정렬 1], [거르기]) - 필드·값 모두 여러 열 가능
      // 열 머리글은 열 필드 수만큼의 줄, 값이 여럿이면 열마다 값 수만큼 칸(이때 합계·소계 열은 빈 칸 - 엑셀과 같게)
      let rk = c.area(A[0], sh).rows, ck = c.area(A[1], sh).rows, vals = c.area(A[2], sh).rows; const fn = aggFn(c, A[3], sh);
      if (!(rk.length === ck.length && ck.length === vals.length)) throw new FErr("#VALUE!");
      const [has, show] = fields(c, A, 4, vals, sh), rw = rk[0].length, cw = ck[0].length, vw = vals[0].length;
      const rh = names(has, rk, rw, "Row Field"), ch = names(has, ck, cw, "Column Field"), vh = names(has, vals, vw, "Value");
      if (has) { rk = rk.slice(1); ck = ck.slice(1); vals = vals.slice(1); }
      const rd = Math.trunc(toNum(opt(c, A, 5, sh, 1))), cd = Math.trunc(toNum(opt(c, A, 7, sh, 1))), [rdesc, rval] = sorts(c, A, 6, sh, rw, vw), [cdesc, cval] = sorts(c, A, 8, sh, cw, vw);
      const idx = picked(c, A, 9, rk.length, sh);
      if (!idx.length) throw new FErr("#CALC!");
      const v = (ks, j) => agg(c, fn, ks.map((i) => vals[i][j]), sh);
      const rows = tree(rk, idx, rd, rdesc, rval, v, false), cols = tree(ck, idx, cd, cdesc, cval, v, true);
      const cell = (r, col, j) => { if (col[2] && vw > 1) return ""; const s = new Set(col[1]), both = r[1].filter((i) => s.has(i)); return both.length ? v(both, j) : ""; };
      const each = (f) => [].concat(...cols.map((col) => Array.from({ length: vw }, (_, j) => f(col, j))));
      const blank = Array(rw).fill(""), out = show ? [[...blank, ch.map(toStr).join(", "), ...Array(cols.length * vw - 1).fill("")]] : [];
      for (let lv = 0; lv < cw; lv++) out.push([...blank, ...each((col) => col[0][lv])]);
      if (show) out.push([...rh, ...each((_, j) => vh[j])]);
      for (const r of rows) out.push([...r[0], ...each((col, j) => cell(r, col, j))]);
      return new Rng(out);
    },
  });
  function unknownName(f, c, sh) { try { return tokenize(f.replace(/^=/, "")).some((t) => t[0] === "name" && !c.named(t[1].toUpperCase(), sh)); } catch (e) { return true; } }  // 정의를 모르는 이름(names 없이 가져온 문서)
  function unknownFn(f) { try { const src = f.replace(/^=/, ""); parse(src); return tokenize(src).some((t) => t[0] === "fn" && !FUNCS[t[1]]); } catch (e) { return true; } }
  /** 모든 탭의 수식 칸 v 를 계산값으로 - 바뀐 칸 수 */
  function recalc(doc) {
    const c = new Calc(doc); let changed = 0; const noTables = !(doc.sheets || []).some((s) => s.tables && s.tables.length);
    for (const sh of doc.sheets || []) for (const [k, raw] of Object.entries(sh.cells || {})) {
      if (!raw || typeof raw !== "object" || !raw.f) continue;
      let v = c.cell(sh, k); if (c.pend.has(sh.id + "!" + k)) continue;  // VBA 결과를 기다리는 칸 - 지금 값을 그대로(결과가 오면 다시 계산)
      v = v instanceof FErr ? v.code : v;
      if (v === "#NAME?" && raw.v != null && raw.v !== "#NAME?" && (unknownFn(raw.f) || unknownName(raw.f, c, sh))) continue;  // 매크로(VBA) 사용자 함수·정의를 모르는 이름 - 엑셀이 마지막에 계산한 값을 그대로
      if (v === "#REF!" && noTables && raw.f.includes("[") && raw.v != null && raw.v !== "#REF!") continue;  // 표 정의 없이 가져온 옛 문서의 구조적 참조 - 엑셀 값을 그대로
      if (raw.v !== v) { raw.v = v; changed++; }
    }
    return changed + syncSpill(doc, c);
  }
  /** 계산기의 넘친 값 → 칸 {v, sp: 기준 칸}. 더는 넘치지 않는 칸은 비운다(기준 칸 오른쪽·아래이거나 기준이 없어졌으면) - 다른 곳에 복사돼 온 sp 칸은 값만 남긴다 */
  function syncSpill(doc, c) {
    let changed = 0;
    for (const sh of doc.sheets || []) {
      const cells = sh.cells || {}, nw = new Map();
      for (const [v, a, sid, k] of c.spill.values()) if (sid === sh.id) nw.set(k, [v, a]);
      for (const [k, raw] of Object.entries(cells)) {
        if (!raw || typeof raw !== "object" || !raw.sp || nw.has(k) || c.pend.has(sh.id + "!" + raw.sp)) continue;  // 기준 칸이 VBA 결과를 기다리면 넘친 값을 그대로
        const a = cells[raw.sp], p = parseRef(k), ap = parseRef(raw.sp);
        const gone = !(a && typeof a === "object" && a.f) || (p && ap && p[0] >= ap[0] && p[1] >= ap[1]);
        delete raw.sp;
        if (gone) { delete raw.v; if (!Object.keys(raw).length) delete cells[k]; }
        changed++;
      }
      for (const [k, [v0, a]] of nw) {
        let raw = cells[k]; if (!raw || typeof raw !== "object") raw = cells[k] = {};
        const v = v0 instanceof FErr ? v0.code : fix(v0);
        if (raw.v !== v || raw.sp !== a) { raw.v = v; raw.sp = a; changed++; }
      }
    }
    return changed;
  }
  function cell(doc, tab, ref) {
    const sh = (doc.sheets || []).find((s) => s.id === tab || s.name === tab) || (doc.sheets || [])[0]; if (!sh) return null;
    const c = new Calc(doc), raw = (sh.cells || {})[ref];
    const v = raw && typeof raw === "object" && raw.f ? c.cell(sh, ref) : c.value(sh, parseRef(ref)[0], parseRef(ref)[1]);
    return v instanceof FErr ? v.code : v;
  }
  /** 칸의 HYPERLINK 주소(마지막으로 계산된 것) - 없거나 오류면 null */
  function link(doc, tab, ref) {
    const sh = (doc.sheets || []).find((s) => s.id === tab || s.name === tab), raw = sh && (sh.cells || {})[ref];
    if (!raw || typeof raw !== "object" || !raw.f) return null;
    const c = new Calc(doc); c.cell(sh, ref);
    return c.links.get(sh.id + "!" + ref) || null;
  }
  /** VBA 사용자 함수 - compiled = NexaVBA.compile(문서 macros.modules), lib = NexaVBA. WorksheetFunction.X 는 이 계산기 함수로 */
  function setVba(compiled, lib) {
    if (!compiled) { API.vba = null; return; }
    API.vba = { has: compiled.has, call: compiled.call, lib, ctx: null };
    if (compiled.runtime) compiled.runtime.host.sheetFn = sheetFn(lib, () => API.vba.ctx);
  }
  /** WorksheetFunction.X → 이 계산기 함수. ctx() = {c: Calc, sh} - 없으면(Worker) 빈 문서 문맥(인자는 값뿐이라 결과가 같다) */
  function sheetFn(lib, ctx) {
    return (name, args) => {
      const f = Object.prototype.hasOwnProperty.call(FUNCS, String(name).toUpperCase()) && FUNCS[String(name).toUpperCase()], x = (ctx && ctx()) || blank(); if (!f) throw new lib.Unsupported(`WorksheetFunction.${name} 는 없습니다`);
      const node = (v) => (v instanceof lib.VRange ? ["arr", new Rng(v.rows.map((r) => r.map((x) => (x && typeof x === "object" && x.code ? new FErr(x.code) : x))))] : v instanceof lib.VArr ? ["arr", new Rng(((t) => t.rows ? t.rows : [[t]])(lib.toCell(v)))] : ["lit", v === lib.EMPTY || v === lib.MISSING ? null : v instanceof lib.CVErr ? new FErr(v.code) : v]);
      let r; try { r = f(x.c, args.map(node), x.sh); } catch (e) { if (e instanceof FErr) throw new lib.VErr(1004, `WorksheetFunction.${name}: ${e.code}`); throw e; }
      if (r instanceof Rng) { if (r.vals.length === 1) r = r.vals[0]; else { const a = new lib.VArr([[1, r.rows.length], [1, r.rows[0].length]]); r.rows.forEach((row, i) => row.forEach((x, j) => { a.d[a.at([i + 1, j + 1])] = x == null ? lib.EMPTY : x; })); return a; } }
      if (r instanceof FErr) throw new lib.VErr(1004, `WorksheetFunction.${name}: ${r.code}`);
      return r == null ? lib.EMPTY : r;
    };
  }
  const blank = () => { const sh = { id: "", name: "", cells: {} }; return { c: new Calc({ sheets: [sh] }), sh }; };
  const API = { recalc, cell, link, setVba, sheetFn, vba: null, parse, tokenize, formatValue, parseNumberText, FUNCS: Object.keys(FUNCS), FErr };
  if (typeof module === "object" && module.exports) module.exports = API; else root.NexaCalc = API;
})(typeof window !== "undefined" ? window : globalThis);
