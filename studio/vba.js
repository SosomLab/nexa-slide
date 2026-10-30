/* nexa-slide VBA 실행기 - 시트 문서의 VBA 표준 모듈에 있는 Function(사용자 정의 함수)을 브라우저·node 에서 직접 계산한다.
   엑셀 없이 도는 부분 집합: Function·Sub · Dim·ReDim(Preserve)·Const · If/ElseIf/Else(한 줄 If 포함) · For/Next · For Each · Do/Loop(While·Until) · While/Wend ·
   Select Case · Exit · On Error Resume Next/GoTo 0 · 배열(여러 차원·LBound·UBound) · Range 인자(.Value·.Cells·.Count·.Rows.Count·For Each) ·
   자주 쓰는 내장 함수(문자열·변환·수학·IsEmpty/IsNumeric 등) · WorksheetFunction.<시트 함수>(계산기 함수 그대로).
   모르는 문법(With·GoTo·클래스·시트 조작 등)은 컴파일할 때 알려 주고 그 함수는 계산하지 않는다 - 칸은 엑셀이 저장해 둔 값을 그대로 둔다(sheetcalc.js #NAME? 규칙).
   NexaVBA.compile(modules) → {fns: {이름: 함수}, errors: [{module, line, msg}]}  · 쓰는 곳: sheet.js(화면), tests/vba_test.js
   보안(0.25.8): 해석만 한다(eval 없음 · 파일·네트워크·Shell·개체 만들기 없음). 문서의 코드가 화면을 멈추거나 탭을 죽이지 못하게
   배열 칸 수·문자열 길이·부르기 깊이·반복 수·실행 시간에 한도를 두고(LIMIT), Like 는 정규식 없이 비교한다.
   화면에서는 계산을 Worker(vbaworker.js)에서 돌린다 - NexaVBA.client. 엑셀에서 실제로 돌 위험한 코드는 NexaVBA.risks 로 알린다(vba_project.py risks 와 같은 규칙). */
(function (root) {
  "use strict";
  const EMPTY = { vba: "Empty" }, NULLV = { vba: "Null" }, NOTHING = { vba: "Nothing" }, MISSING = { vba: "Missing" };
  const LIMIT = { cells: 1e6, str: 1e7, depth: 500, steps: 5e6, ms: 2000 };  // 배열 칸 · 문자열 글자 · 부르기 깊이 · 반복 · 한 번 부르기 시간(ms)
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);  // 표 조회는 자기 키만(constructor·__proto__ 같은 이름이 새지 않게)
  const cap = (s) => { if (s.length > LIMIT.str) throw new VErr(14, "문자열이 너무 깁니다"); return s; };
  class Unsupported extends Error {}
  class VErr extends Error { constructor(num, msg) { super(msg); this.num = num; } }
  class ExitSig { constructor(kind) { this.kind = kind; } }
  class CVErr { constructor(code) { this.code = code; } }  // 엑셀 오류 값(#N/A 등)
  class VArr {  // 배열 - 차원마다 [하한, 상한], 값은 평평하게(첫 차원이 가장 빨리 - 순서는 안에서만 쓴다)
    constructor(bounds, data) {
      this.b = bounds; this.n = bounds.map(([l, u]) => Math.max(0, u - l + 1));
      const total = this.n.reduce((a, x) => a * x, 1);
      if (!data && !(total <= LIMIT.cells)) throw new VErr(7, `배열이 너무 큽니다(${LIMIT.cells}칸까지)`);
      this.d = data || new Array(total).fill(EMPTY);
    }
    at(idx) {
      if (idx.length !== this.b.length) throw new VErr(9, "첨자가 범위를 벗어났습니다(차원 수)");
      let k = 0, m = 1;
      for (let i = 0; i < idx.length; i++) { const j = Math.round(num(idx[i])) - this.b[i][0]; if (j < 0 || j >= this.n[i]) throw new VErr(9, "첨자가 범위를 벗어났습니다"); k += j * m; m *= this.n[i]; }
      return k;
    }
    copy() { return new VArr(this.b.map((x) => x.slice()), this.d.map((v) => (v instanceof VArr ? v.copy() : v))); }
  }
  class VRange {  // Range 인자 - rows(값 2차원) · 시트 위치(r0, c0)
    constructor(rows, r0, c0, sheet) { this.rows = rows; this.r0 = r0; this.c0 = c0; this.sheet = sheet; }
    get h() { return this.rows.length; } get w() { return this.rows[0] ? this.rows[0].length : 0; }
    cell(i, j) { return new VRange([[this.rows[i] && this.rows[i][j] !== undefined ? this.rows[i][j] : null]], this.r0 + i, this.c0 + j, this.sheet); }
    value() {
      if (this.h === 1 && this.w === 1) return fromCell(this.rows[0][0]);
      const a = new VArr([[1, this.h], [1, this.w]]);
      for (let i = 0; i < this.h; i++) for (let j = 0; j < this.w; j++) a.d[a.at([i + 1, j + 1])] = fromCell(this.rows[i][j]);
      return a;
    }
  }
  const fromCell = (v) => (v == null ? EMPTY : typeof v === "object" && v.code ? new CVErr(v.code) : v);  // 빈 칸 = Empty, 오류 칸 = 오류 값
  const isStr = (v) => typeof v === "string", isNum = (v) => typeof v === "number";

  // ---------------------------------------------------------------- 변환
  function num(v) {
    if (v instanceof VRange) v = v.value();
    if (isNum(v)) return v;
    if (typeof v === "boolean") return v ? -1 : 0;
    if (v === EMPTY || v === MISSING) return 0;
    if (isStr(v)) { const t = v.trim(); if (t === "") throw new VErr(13, "형식이 일치하지 않습니다"); const n = Number(t.replace(/,/g, "")); if (isNaN(n)) throw new VErr(13, `형식이 일치하지 않습니다: "${v}"`); return n; }
    if (v === NULLV) throw new VErr(94, "Null 을 잘못 사용했습니다");
    if (v instanceof CVErr) throw new VErr(13, "형식이 일치하지 않습니다(오류 값)");
    throw new VErr(13, "형식이 일치하지 않습니다");
  }
  function str(v) {
    if (v instanceof VRange) v = v.value();
    if (isStr(v)) return v;
    if (isNum(v)) return fmtNum(v);
    if (typeof v === "boolean") return v ? "True" : "False";
    if (v === EMPTY || v === MISSING) return "";
    if (v === NULLV) throw new VErr(94, "Null 을 잘못 사용했습니다");
    if (v instanceof CVErr) return "Error " + v.code;
    throw new VErr(13, "형식이 일치하지 않습니다");
  }
  const fmtNum = (n) => (Number.isInteger(n) ? String(n) : String(Number(n.toPrecision(15))));
  function bool(v) { if (v instanceof VRange) v = v.value(); if (typeof v === "boolean") return v; if (isStr(v)) { if (/^true$/i.test(v)) return true; if (/^false$/i.test(v)) return false; } return num(v) !== 0; }
  const roundEven = (x) => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : f % 2 === 0 ? f : f + 1; };
  const isNumeric = (v) => { if (v instanceof VRange) v = v.value(); if (isNum(v) || typeof v === "boolean" || v === EMPTY) return true; if (isStr(v)) { const t = v.trim().replace(/,/g, ""); return t !== "" && !isNaN(Number(t)); } return false; };
  function coerce(type, v) {
    if (v instanceof VRange && type !== "object" && type !== "range") v = v.value();
    switch (type) {
      case "long": case "integer": case "byte": case "longlong": { const n = roundEven(num(v)); if (!isFinite(n)) throw new VErr(6, "오버플로"); return n; }
      case "double": case "single": case "currency": case "decimal": return num(v);
      case "string": return str(v);
      case "boolean": return bool(v);
      case "date": return num(v);
      default: return v;
    }
  }
  const DEFAULT = { long: 0, integer: 0, byte: 0, longlong: 0, double: 0, single: 0, currency: 0, decimal: 0, string: "", boolean: false, date: 0 };

  // ---------------------------------------------------------------- 낱말
  const KW = new Set(["AND", "OR", "NOT", "XOR", "EQV", "IMP", "MOD", "IS", "LIKE", "TO", "STEP", "THEN", "ELSE", "ELSEIF", "END", "IF", "FOR", "EACH", "IN", "NEXT", "DO", "LOOP", "WHILE", "WEND", "UNTIL",
    "SELECT", "CASE", "EXIT", "FUNCTION", "SUB", "DIM", "REDIM", "PRESERVE", "AS", "CONST", "SET", "LET", "CALL", "BYVAL", "BYREF", "OPTIONAL", "PARAMARRAY", "PRIVATE", "PUBLIC", "STATIC", "ON", "ERROR", "RESUME", "GOTO", "WITH", "NEW", "OPTION", "TRUE", "FALSE", "EMPTY", "NULL", "NOTHING"]);
  function lex(line, ln) {
    const out = []; let i = 0;
    while (i < line.length) {
      const ch = line[i];
      if (ch === " " || ch === "\t") { i++; continue; }
      if (ch === "'") break;
      if (ch === '"') { let s = ""; i++; for (;;) { if (i >= line.length) throw new Unsupported(`${ln}행: 닫히지 않은 문자열`); if (line[i] === '"') { if (line[i + 1] === '"') { s += '"'; i += 2; continue; } i++; break; } s += line[i++]; } out.push(["str", s]); continue; }
      if (/[0-9]/.test(ch) || (ch === "." && /[0-9]/.test(line[i + 1] || ""))) { const m = /^(\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?)[#!@&%^]?/.exec(line.slice(i)); out.push(["num", parseFloat(m[1])]); i += m[0].length; continue; }
      if (ch === "&" && /[hH]/.test(line[i + 1] || "")) { const m = /^&[hH]([0-9A-Fa-f]+)&?/.exec(line.slice(i)); if (m) { out.push(["num", parseInt(m[1], 16)]); i += m[0].length; continue; } }
      if (ch === "#") throw new Unsupported(`${ln}행: 날짜 상수(#…#)는 아직 못 씁니다`);
      const id = /^[\p{L}_][\p{L}\p{N}_]*[$%&!#@]?/u.exec(line.slice(i));
      if (id) { const w = id[0].replace(/[$%&!#@]$/, ""), U = w.toUpperCase(); if (U === "REM" && !out.length) break; out.push([KW.has(U) ? "kw" : "id", KW.has(U) ? U : w]); i += id[0].length; continue; }
      const op = /^(<>|<=|>=|:=|[-+*/\\^&=<>(),.:;])/.exec(line.slice(i));
      if (op) { out.push(["op", op[0]]); i += op[0].length; continue; }
      throw new Unsupported(`${ln}행: 알 수 없는 글자 "${ch}"`);
    }
    return out;
  }
  /** 소스 → 문장 줄 목록 [{t: 낱말, ln}] - 줄 이음( _)·콜론으로 나눈 문장 */
  function lines(src) {
    const raw = String(src).replace(/\r\n?/g, "\n").split("\n"), out = [];
    for (let i = 0; i < raw.length; i++) {
      let s = raw[i], ln = i + 1;
      while (/\s_\s*$/.test(s) && i + 1 < raw.length) { s = s.replace(/\s_\s*$/, " ") + raw[++i]; }
      if (/^\s*Attribute\s+VB_/i.test(s)) continue;
      const toks = lex(s, ln); if (!toks.length) continue;
      let cur = [];
      for (const t of toks) {
        if (t[0] === "op" && t[1] === ":" ) { if (cur.length) out.push({ t: cur, ln }); cur = []; } else cur.push(t);
      }
      if (cur.length) out.push({ t: cur, ln });
    }
    return out;
  }

  // ---------------------------------------------------------------- 식 파서
  class P {
    constructor(t, ln) { this.t = t; this.i = 0; this.ln = ln; }
    peek(k = 0) { return this.t[this.i + k]; }
    is(kind, v) { const x = this.t[this.i]; return !!x && x[0] === kind && (v === undefined || (kind === "id" ? x[1].toUpperCase() === v : x[1] === v)); }
    kw(v) { return this.is("kw", v); }
    op(v) { return this.is("op", v); }
    eat(kind, v) { if (!this.is(kind, v)) throw new Unsupported(`${this.ln}행: "${v || kind}" 가 와야 하는데 "${this.peek() ? this.peek()[1] : "줄 끝"}"`); return this.t[this.i++]; }
    end() { return this.i >= this.t.length; }
    expr() { return this.imp(); }
    imp() { let a = this.eqv(); while (this.kw("IMP")) { this.i++; a = ["bin", "IMP", a, this.eqv()]; } return a; }
    eqv() { let a = this.xor(); while (this.kw("EQV")) { this.i++; a = ["bin", "EQV", a, this.xor()]; } return a; }
    xor() { let a = this.or(); while (this.kw("XOR")) { this.i++; a = ["bin", "XOR", a, this.or()]; } return a; }
    or() { let a = this.and(); while (this.kw("OR")) { this.i++; a = ["bin", "OR", a, this.and()]; } return a; }
    and() { let a = this.not(); while (this.kw("AND")) { this.i++; a = ["bin", "AND", a, this.not()]; } return a; }
    not() { if (this.kw("NOT")) { this.i++; return ["not", this.not()]; } return this.cmp(); }
    cmp() {
      let a = this.cat();
      for (;;) {
        const x = this.peek();
        if (x && x[0] === "op" && ["=", "<>", "<", ">", "<=", ">="].includes(x[1])) { this.i++; a = ["cmp", x[1], a, this.cat()]; continue; }
        if (this.kw("LIKE")) { this.i++; a = ["like", a, this.cat()]; continue; }
        if (this.kw("IS")) { this.i++; a = ["is", a, this.cat()]; continue; }
        return a;
      }
    }
    cat() { let a = this.add(); while (this.op("&")) { this.i++; a = ["bin", "&", a, this.add()]; } return a; }
    add() { let a = this.mod(); for (;;) { if (this.op("+") || this.op("-")) { const o = this.t[this.i++][1]; a = ["bin", o, a, this.mod()]; } else return a; } }
    mod() { let a = this.idiv(); while (this.kw("MOD")) { this.i++; a = ["bin", "MOD", a, this.idiv()]; } return a; }
    idiv() { let a = this.mul(); while (this.op("\\")) { this.i++; a = ["bin", "\\", a, this.mul()]; } return a; }
    mul() { let a = this.neg(); for (;;) { if (this.op("*") || this.op("/")) { const o = this.t[this.i++][1]; a = ["bin", o, a, this.neg()]; } else return a; } }
    neg() { if (this.op("-")) { this.i++; return ["neg", this.neg()]; } if (this.op("+")) { this.i++; return this.neg(); } return this.pow(); }
    pow() { let a = this.post(); while (this.op("^")) { this.i++; a = ["bin", "^", a, this.neg()]; } return a; }
    args() {  // ( 뒤 - 빈 인자(생략)도
      const out = [];
      if (this.op(")")) { this.i++; return out; }
      for (;;) {
        if (this.op(",")) { out.push(["missing"]); this.i++; continue; }
        if (this.is("id") && this.peek(1) && this.peek(1)[1] === ":=") { const nm = this.t[this.i][1]; this.i += 2; out.push(["named", nm, this.expr()]); }
        else out.push(this.expr());
        if (this.op(",")) { this.i++; if (this.op(")")) { out.push(["missing"]); } continue; }
        this.eat("op", ")"); return out;
      }
    }
    post() {
      let a = this.prim();
      for (;;) {
        if (this.op("(")) { this.i++; a = ["call", a, this.args()]; continue; }
        if (this.op(".")) { this.i++; const m = this.peek(); if (!m || (m[0] !== "id" && m[0] !== "kw")) throw new Unsupported(`${this.ln}행: . 뒤에 이름이 없습니다`); this.i++; a = ["mem", a, m[1]]; continue; }
        return a;
      }
    }
    prim() {
      const x = this.peek(); if (!x) throw new Unsupported(`${this.ln}행: 식이 끝났습니다`);
      if (x[0] === "num") { this.i++; return ["lit", x[1]]; }
      if (x[0] === "str") { this.i++; return ["lit", x[1]]; }
      if (x[0] === "op" && x[1] === "(") { this.i++; const e = this.expr(); this.eat("op", ")"); return ["paren", e]; }
      if (x[0] === "kw") {
        if (x[1] === "TRUE") { this.i++; return ["lit", true]; } if (x[1] === "FALSE") { this.i++; return ["lit", false]; }
        if (x[1] === "EMPTY") { this.i++; return ["lit", EMPTY]; } if (x[1] === "NULL") { this.i++; return ["lit", NULLV]; } if (x[1] === "NOTHING") { this.i++; return ["lit", NOTHING]; }
        if (x[1] === "NEW") throw new Unsupported(`${this.ln}행: New(개체 만들기)는 아직 못 씁니다`);
      }
      if (x[0] === "op" && x[1] === ".") throw new Unsupported(`${this.ln}행: With 블록(.속성)은 아직 못 씁니다`);
      if (x[0] === "id") { this.i++; return ["name", x[1]]; }
      throw new Unsupported(`${this.ln}행: 여기에 "${x[1]}" 를 쓸 수 없습니다`);
    }
  }

  // ---------------------------------------------------------------- 문장 파서
  function parseModule(src, modName) {
    const L = lines(src), procs = [], errors = [], consts = [];
    let k = 0;
    const T = (s) => s.t, first = (s) => s.t[0], kwAt = (s, i, v) => s.t[i] && s.t[i][0] === "kw" && s.t[i][1] === v;
    function typeOf(p) { if (p.kw("AS")) { p.i++; if (p.kw("NEW")) throw new Unsupported(`${p.ln}행: As New 는 아직 못 씁니다`); const t = p.eat(p.is("kw") ? "kw" : "id")[1]; let tn = t.toLowerCase(); if (p.op(".")) { p.i++; tn = p.eat("id")[1].toLowerCase(); } if (p.op("*")) { p.i++; p.expr(); } return tn; } return "variant"; }
    function declList(p) {  // Dim a As Long, b(1 To 3) As String, c()
      const out = [];
      do {
        if (p.op(",")) p.i++;
        if (p.kw("WITHEVENTS")) p.i++;
        const nm = p.eat("id")[1]; let dims = null;
        if (p.op("(")) { p.i++; dims = []; if (!p.op(")")) for (;;) { const a = p.expr(); if (p.kw("TO")) { p.i++; dims.push([a, p.expr()]); } else dims.push([["lit", 0], a]); if (p.op(",")) { p.i++; continue; } break; } p.eat("op", ")"); }
        out.push({ name: nm, dims, type: typeOf(p) });
      } while (p.op(","));
      return out;
    }
    function block(stops) {  // 끝 낱말(End If · Next 등)을 만날 때까지 문장들
      const body = [];
      while (k < L.length) {
        const s = L[k], t = s.t, a = t[0];
        if (stops(s)) return body;
        k++;
        body.push(stmt(s));
      }
      throw new Unsupported(`끝(End …)이 없는 블록`);
    }
    const isEnd = (s, w) => first(s)[0] === "kw" && first(s)[1] === "END" && kwAt(s, 1, w);
    function stmt(s) {
      const t = s.t, a = t[0], ln = s.ln, p = new P(t, ln);
      const K = a[0] === "kw" ? a[1] : null;
      if (K === "DIM" || K === "STATIC" || ((K === "PRIVATE" || K === "PUBLIC") && !kwAt(s, 1, "FUNCTION") && !kwAt(s, 1, "SUB") && !kwAt(s, 1, "CONST"))) { p.i++; return ["dim", declList(p), ln]; }
      if (K === "CONST" || ((K === "PRIVATE" || K === "PUBLIC") && kwAt(s, 1, "CONST"))) {
        p.i += K === "CONST" ? 1 : 2; const out = [];
        do { if (p.op(",")) p.i++; const nm = p.eat("id")[1]; typeOf(p); p.eat("op", "="); out.push([nm, p.expr()]); } while (p.op(","));
        return ["const", out, ln];
      }
      if (K === "REDIM") {
        p.i++; const pres = p.kw("PRESERVE"); if (pres) p.i++; const out = [];
        do { if (p.op(",")) p.i++; const nm = p.eat("id")[1]; p.eat("op", "("); const dims = []; for (;;) { const x = p.expr(); if (p.kw("TO")) { p.i++; dims.push([x, p.expr()]); } else dims.push([["lit", 0], x]); if (p.op(",")) { p.i++; continue; } break; } p.eat("op", ")"); out.push({ name: nm, dims, type: typeOf(p) }); } while (p.op(","));
        return ["redim", pres, out, ln];
      }
      if (K === "IF") {
        p.i++; const cond = p.expr(); p.eat("kw", "THEN");
        if (!p.end()) {  // 한 줄 If
          const rest = t.slice(p.i), ei = rest.findIndex((x) => x[0] === "kw" && x[1] === "ELSE");
          const thenT = ei >= 0 ? rest.slice(0, ei) : rest, elseT = ei >= 0 ? rest.slice(ei + 1) : null;
          return ["if", [[cond, [stmt({ t: thenT, ln })]]], elseT && elseT.length ? [stmt({ t: elseT, ln })] : null, ln];
        }
        const arms = []; let els = null, c = cond;
        for (;;) {
          const body = block((x) => (first(x)[0] === "kw" && (first(x)[1] === "ELSEIF" || first(x)[1] === "ELSE")) || isEnd(x, "IF"));
          arms.push([c, body]);
          const s2 = L[k++];
          if (first(s2)[1] === "ELSEIF") { const q = new P(s2.t, s2.ln); q.i++; c = q.expr(); q.eat("kw", "THEN"); continue; }
          if (first(s2)[1] === "ELSE") { els = block((x) => isEnd(x, "IF")); k++; }
          break;
        }
        return ["if", arms, els, ln];
      }
      if (K === "FOR") {
        p.i++;
        if (p.kw("EACH")) { p.i++; const v = p.eat("id")[1]; p.eat("kw", "IN"); const coll = p.expr(); const body = block((x) => first(x)[0] === "kw" && first(x)[1] === "NEXT"); k++; return ["foreach", v, coll, body, ln]; }
        const v = p.eat("id")[1]; p.eat("op", "="); const from = p.expr(); p.eat("kw", "TO"); const to = p.expr(); let step = ["lit", 1]; if (p.kw("STEP")) { p.i++; step = p.expr(); }
        const body = block((x) => first(x)[0] === "kw" && first(x)[1] === "NEXT"); k++;
        return ["for", v, from, to, step, body, ln];
      }
      if (K === "DO") {
        p.i++; let pre = null;
        if (p.kw("WHILE") || p.kw("UNTIL")) { const w = p.t[p.i++][1]; pre = [w, p.expr()]; }
        const body = block((x) => first(x)[0] === "kw" && first(x)[1] === "LOOP");
        const s2 = L[k++], q = new P(s2.t, s2.ln); q.i++; let post = null;
        if (q.kw("WHILE") || q.kw("UNTIL")) { const w = q.t[q.i++][1]; post = [w, q.expr()]; }
        return ["do", pre, post, body, ln];
      }
      if (K === "WHILE") { p.i++; const c = p.expr(); const body = block((x) => first(x)[0] === "kw" && first(x)[1] === "WEND"); k++; return ["do", ["WHILE", c], null, body, ln]; }
      if (K === "SELECT") {
        p.i++; p.eat("kw", "CASE"); const subj = p.expr(); const cases = []; let els = null;
        while (k < L.length && !(first(L[k])[0] === "kw" && first(L[k])[1] === "CASE")) { if (isEnd(L[k], "SELECT")) break; k++; }
        while (k < L.length && !isEnd(L[k], "SELECT")) {
          const s2 = L[k++], q = new P(s2.t, s2.ln); q.i++;
          const stop = (x) => (first(x)[0] === "kw" && first(x)[1] === "CASE") || isEnd(x, "SELECT");
          if (q.kw("ELSE")) { els = block(stop); continue; }
          const tests = [];
          for (;;) {
            if (q.kw("IS")) { q.i++; const o = q.eat("op")[1]; tests.push(["is", o, q.expr()]); }
            else { const x = q.expr(); if (q.kw("TO")) { q.i++; tests.push(["to", x, q.expr()]); } else tests.push(["eq", x]); }
            if (q.op(",")) { q.i++; continue; } break;
          }
          cases.push([tests, block(stop)]);
        }
        k++; return ["select", subj, cases, els, ln];
      }
      if (K === "EXIT") { const w = t[1] && t[1][1]; if (!["FOR", "DO", "FUNCTION", "SUB"].includes(w)) throw new Unsupported(`${ln}행: Exit ${w || ""}`); return ["exit", w, ln]; }
      if (K === "ON") {
        if (kwAt(s, 1, "ERROR") && kwAt(s, 2, "RESUME")) return ["onerr", true, ln];
        if (kwAt(s, 1, "ERROR") && kwAt(s, 2, "GOTO") && t[3] && t[3][0] === "num" && t[3][1] === 0) return ["onerr", false, ln];
        throw new Unsupported(`${ln}행: On Error GoTo 레이블은 아직 못 씁니다`);
      }
      if (K === "OPTION") return ["nop"];
      if (K === "WITH") throw new Unsupported(`${ln}행: With 블록은 아직 못 씁니다`);
      if (K === "GOTO" || K === "RESUME") throw new Unsupported(`${ln}행: ${K} 는 아직 못 씁니다`);
      if (K === "SET" || K === "LET") { p.i++; const lhs = p.post(); p.eat("op", "="); return ["assign", lhs, p.expr(), ln]; }
      if (K === "CALL") { p.i++; return ["callst", p.post(), ln]; }
      if (a[0] === "id" && /^debug$/i.test(a[1])) return ["nop"];
      if (K) throw new Unsupported(`${ln}행: "${K}" 문장은 아직 못 씁니다`);
      // 대입 또는 프로시저 부르기
      const lhs = p.post();
      if (p.op("=")) { p.i++; return ["assign", lhs, p.expr(), ln]; }
      if (p.end()) return ["callst", lhs, ln];
      const args = []; for (;;) { if (p.op(",")) { args.push(["missing"]); p.i++; continue; } args.push(p.expr()); if (p.op(",")) { p.i++; continue; } break; }  // Foo a, b
      return ["callst", ["call", lhs, args], ln];
    }
    while (k < L.length) {
      const s = L[k], t = s.t; let i = 0;
      while (t[i] && t[i][0] === "kw" && ["PRIVATE", "PUBLIC", "STATIC"].includes(t[i][1])) i++;
      const kind = t[i] && t[i][0] === "kw" && (t[i][1] === "FUNCTION" || t[i][1] === "SUB") ? t[i][1] : null;
      if (!kind) {
        k++;
        try { const st = stmt(s); if (st[0] === "const" || st[0] === "dim") consts.push(st); } catch (e) { if (e instanceof Unsupported) errors.push({ module: modName, line: s.ln, msg: e.message }); else throw e; }
        continue;
      }
      const p = new P(t, s.ln); p.i = i + 1; const name = p.eat("id")[1]; const params = [];
      const startK = k; k++;
      try {
        if (p.op("(")) {
          p.i++;
          if (!p.op(")")) for (;;) {
            const prm = { byval: false, optional: false, def: null, arr: false, rest: false };
            for (;;) { if (p.kw("OPTIONAL")) { p.i++; prm.optional = true; } else if (p.kw("BYVAL")) { p.i++; prm.byval = true; } else if (p.kw("BYREF")) { p.i++; } else if (p.kw("PARAMARRAY")) { p.i++; prm.rest = true; } else break; }
            prm.name = p.eat("id")[1]; if (p.op("(")) { p.i++; p.eat("op", ")"); prm.arr = true; }
            prm.type = typeOf(p); if (p.op("=")) { p.i++; prm.def = p.expr(); }
            params.push(prm); if (p.op(",")) { p.i++; continue; } break;
          }
          p.eat("op", ")");
        }
        const rtype = kind === "FUNCTION" ? typeOf(p) : null;
        const body = block((x) => isEnd(x, kind));
        k++;
        procs.push({ kind, name, params, rtype, body, module: modName, line: s.ln });
      } catch (e) {
        if (!(e instanceof Unsupported)) throw e;
        errors.push({ module: modName, line: s.ln, name, msg: e.message });
        k = startK + 1; while (k < L.length && !isEnd(L[k], kind)) k++; k++;
        procs.push({ kind, name, unsupported: e.message, module: modName, line: s.ln });
      }
    }
    return { procs, errors, consts };
  }

  // ---------------------------------------------------------------- 실행
  function Runtime(mods, host) {
    this.procs = new Map(); this.errors = []; this.globals = new Map(); this.host = host || {}; this.steps = 0; this.depth = 0; this.until = Infinity;
    const gconsts = [];
    for (const m of mods) {
      if (m.kind && m.kind !== "std") continue;  // 문서·클래스 모듈의 함수는 셀에서 못 부른다(엑셀과 같다)
      let r; try { r = parseModule(m.code || "", m.name); } catch (e) { this.errors.push({ module: m.name, line: 0, msg: e instanceof Unsupported ? e.message : `모듈을 읽지 못했습니다(${e.message})` }); continue; }
      this.errors.push(...r.errors);
      for (const pr of r.procs) this.procs.set(pr.name.toUpperCase(), pr);
      gconsts.push(...r.consts);
    }
    const env = { vars: this.globals, parent: null };
    this.until = Date.now() + LIMIT.ms;  // 모듈 수준 Const 식도 함수를 부를 수 있다 - 화면 쪽 컴파일이 멈추지 않게 같은 한도
    for (const st of gconsts) { try { this.exec([st], env); } catch (e) { /* 모듈 수준 선언 오류 - 무시 */ } }
    this.steps = 0; this.until = Infinity;
  }
  const R = Runtime.prototype;
  R.lookup = function (env, nm) { const k = nm.toUpperCase(); for (let e = env; e; e = e.parent) if (e.vars.has(k)) return e.vars.get(k); return null; };
  R.declare = function (env, nm, type, init) { const cell = { v: init !== undefined ? init : own(DEFAULT, type) ? DEFAULT[type] : EMPTY, type }; env.vars.set(nm.toUpperCase(), cell); return cell; };
  R.tick = function () {
    if (++this.steps > LIMIT.steps) throw new VErr(28, "실행이 너무 오래 걸립니다(반복 한도)");
    if ((this.steps & 4095) === 0 && Date.now() > this.until) throw new VErr(28, `실행이 너무 오래 걸립니다(${LIMIT.ms / 1000}초 한도)`);
  };
  /** 셀에서 부르기 - args 는 값·VRange·VArr */
  R.call = function (name, args) {
    const pr = this.procs.get(String(name).toUpperCase());
    if (!pr) throw new VErr(35, `함수 ${name} 이 없습니다`);
    if (pr.unsupported) throw new Unsupported(pr.unsupported);
    this.steps = 0; this.depth = 0; this.until = Date.now() + LIMIT.ms;
    return this.invoke(pr, args.map((v) => ({ v, type: "variant" })), true);
  };
  R.invoke = function (pr, cells, fromCell) {
    if (pr.unsupported) throw new Unsupported(pr.unsupported);
    const env = { vars: new Map(), parent: { vars: this.globals, parent: null } };
    pr.params.forEach((prm, i) => {
      if (prm.rest) { const rest = cells.slice(i).map((c) => (c ? c.v : MISSING)); this.declare(env, prm.name, "variant", new VArr([[0, rest.length - 1]], rest)); return; }
      const c = cells[i];
      if (!c || c.v === MISSING) { if (!prm.optional) throw new VErr(449, `인수 ${prm.name} 가 없습니다`); this.declare(env, prm.name, prm.type, prm.def ? coerce(prm.type, this.ev(prm.def, env)) : own(DEFAULT, prm.type) ? DEFAULT[prm.type] : MISSING); return; }
      if (!prm.byval && !fromCell && c.ref) { env.vars.set(prm.name.toUpperCase(), c.ref); return; }  // ByRef - 부른 쪽 변수와 같은 칸
      let v = c.v; if (v instanceof VArr && prm.byval) v = v.copy();
      this.declare(env, prm.name, prm.type, prm.type === "variant" || prm.type === "range" || prm.type === "object" ? v : coerce(prm.type, v));
    });
    const ret = pr.kind === "FUNCTION" ? this.declare(env, pr.name, pr.rtype || "variant") : null;
    if (++this.depth > LIMIT.depth) throw new VErr(28, "스택 공간이 부족합니다(부르기가 너무 깊습니다)");
    try { this.exec(pr.body, env, pr); } catch (e) { if (!(e instanceof ExitSig && (e.kind === "FUNCTION" || e.kind === "SUB"))) throw e; } finally { this.depth--; }
    return ret ? ret.v : EMPTY;
  };
  R.exec = function (body, env, pr) {
    for (let i = 0; i < body.length; i++) {
      const st = body[i];
      this.tick();
      if (env.resume) { try { this.stmt(st, env, pr); } catch (e) { if (e instanceof VErr) { env.err = e; continue; } throw e; } }
      else this.stmt(st, env, pr);
    }
  };
  R.stmt = function (st, env, pr) {
    switch (st[0]) {
      case "nop": return;
      case "dim": for (const d of st[1]) { const dims = d.dims && d.dims.length ? d.dims.map(([a, b]) => [num(this.ev(a, env)), num(this.ev(b, env))]) : null; this.declare(env, d.name, d.type, dims ? new VArr(dims) : d.dims ? new VArr([[0, -1]]) : undefined); } return;
      case "const": for (const [nm, e] of st[1]) this.declare(env, nm, "variant", this.ev(e, env)); return;
      case "redim": for (const d of st[2]) {
        let cell = this.lookup(env, d.name); if (!cell) cell = this.declare(env, d.name, "variant");
        const dims = d.dims.map(([a, b]) => [num(this.ev(a, env)), num(this.ev(b, env))]), arr = new VArr(dims);
        const ty = d.type !== "variant" ? d.type : cell.type;  // Dim a() As Long 뒤 ReDim a(…) - 선언한 형식
        if (own(DEFAULT, ty)) arr.d.fill(DEFAULT[ty]);
        if (st[1] && cell.v instanceof VArr) {  // Preserve - 마지막 차원만 바뀐다
          const old = cell.v;
          const walk = (k, idx) => { if (k === old.b.length) { try { arr.d[arr.at(idx)] = old.d[old.at(idx)]; } catch (e) { /* 새 범위 밖 */ } return; } for (let j = old.b[k][0]; j <= old.b[k][1]; j++) walk(k + 1, [...idx, j]); };
          walk(0, []);
        }
        cell.v = arr;
      } return;
      case "assign": return this.assign(st[1], this.ev(st[2], env), env);
      case "callst": { const e = st[1]; if (e[0] === "name") return void this.callName(e[1], [], env, true); this.ev(e, env, true); return; }
      case "if": {
        for (const [c, b] of st[1]) if (bool(this.ev(c, env))) return this.exec(b, env, pr);
        if (st[2]) this.exec(st[2], env, pr);
        return;
      }
      case "for": {
        const [, v, a, b, s, body] = st;
        let cell = this.lookup(env, v); if (!cell) cell = this.declare(env, v, "variant");
        const to = num(this.ev(b, env)), step = num(this.ev(s, env));
        cell.v = coerce(cell.type, num(this.ev(a, env)));
        for (;;) {
          const cur = num(cell.v);
          if (step >= 0 ? cur > to : cur < to) break;
          try { this.exec(body, env, pr); } catch (e) { if (e instanceof ExitSig && e.kind === "FOR") break; throw e; }
          cell.v = coerce(cell.type, num(cell.v) + step);
          this.tick();
        }
        return;
      }
      case "foreach": {
        const [, v, ce, body] = st;
        let cell = this.lookup(env, v); if (!cell) cell = this.declare(env, v, "variant");
        const coll = this.ev(ce, env), items = [];
        if (coll instanceof VRange) { for (let i = 0; i < coll.h; i++) for (let j = 0; j < coll.w; j++) items.push(coll.cell(i, j)); }
        else if (coll instanceof VArr) items.push(...coll.d);  // 배열 - 첫 차원부터(엑셀은 열 우선 순서)
        else throw new VErr(424, "For Each 에 쓸 수 없는 값입니다");
        for (const it of items) { cell.v = it; try { this.exec(body, env, pr); } catch (e) { if (e instanceof ExitSig && e.kind === "FOR") break; throw e; } }
        return;
      }
      case "do": {
        const [, pre, post, body] = st;
        const test = (c) => { const b = bool(this.ev(c[1], env)); return c[0] === "WHILE" ? b : !b; };
        for (;;) {
          if (pre && !test(pre)) break;
          try { this.exec(body, env, pr); } catch (e) { if (e instanceof ExitSig && e.kind === "DO") break; throw e; }
          if (post && !test(post)) break;
          this.tick();
        }
        return;
      }
      case "select": {
        const v = this.ev(st[1], env);
        for (const [tests, body] of st[2]) {
          const hit = tests.some((t) => (t[0] === "eq" ? compare(v, this.ev(t[1], env)) === 0 : t[0] === "to" ? compare(v, this.ev(t[1], env)) >= 0 && compare(v, this.ev(t[2], env)) <= 0 : cmpOp(t[1], compare(v, this.ev(t[2], env)))));
          if (hit) return this.exec(body, env, pr);
        }
        if (st[3]) this.exec(st[3], env, pr);
        return;
      }
      case "exit": throw new ExitSig(st[1]);
      case "onerr": env.resume = st[1]; return;
      default: throw new Unsupported(`알 수 없는 문장 ${st[0]}`);
    }
  };
  R.assign = function (lhs, v, env) {
    if (lhs[0] === "name") {
      let cell = this.lookup(env, lhs[1]); if (!cell) cell = this.declare(env, lhs[1], "variant");
      if (v instanceof VArr) v = v.copy();  // 배열 대입은 복사(VBA 값 의미)
      cell.v = cell.type === "variant" ? (v instanceof VRange ? v.value() : v) : cell.type === "range" || cell.type === "object" ? v : coerce(cell.type, v);
      return;
    }
    if (lhs[0] === "call" && lhs[1][0] === "name") {
      const cell = this.lookup(env, lhs[1][1]);
      if (cell && cell.v instanceof VArr) { const idx = lhs[2].map((a) => this.ev(a, env)); cell.v.d[cell.v.at(idx)] = v instanceof VRange ? v.value() : v; return; }
    }
    throw new Unsupported("이 대입(속성·시트 칸 쓰기)은 아직 못 씁니다 - 사용자 함수는 값만 돌려준다");
  };
  R.ev = function (n, env) {
    switch (n[0]) {
      case "lit": return n[1];
      case "paren": return this.ev(n[1], env);
      case "missing": return MISSING;
      case "name": {
        const c = this.lookup(env, n[1]); if (c) return c.v;
        const K = n[1].toUpperCase();
        if (own(CONSTS, K)) return CONSTS[K];
        if (this.procs.has(K)) return this.callName(n[1], [], env);
        if (own(BUILTIN, K)) return BUILTIN[K].call(this, [], env);
        return EMPTY;  // 선언 없는 변수(Option Explicit 없음) - Empty
      }
      case "neg": return -num(this.ev(n[1], env));
      case "not": { const v = this.ev(n[1], env); return typeof v === "boolean" ? !v : ~Math.round(num(v)); }
      case "bin": return binop(n[1], this.ev(n[2], env), this.ev(n[3], env));
      case "cmp": { const a = this.ev(n[2], env), b = this.ev(n[3], env); if (a === NULLV || b === NULLV) return NULLV; return cmpOp(n[1], compare(a, b)); }
      case "like": return like(str(this.ev(n[1], env)), str(this.ev(n[2], env)));
      case "is": { const a = this.ev(n[1], env), b = this.ev(n[2], env); return a === b; }
      case "call": {
        const f = n[1];
        if (f[0] === "name") {
          const cell = this.lookup(env, f[1]);
          if (cell && cell.v instanceof VArr) return cell.v.d[cell.v.at(n[2].map((a) => this.ev(a, env)))];
          if (cell && cell.v instanceof VRange) return rangeIndex(cell.v, n[2].map((a) => this.ev(a, env)));
          return this.callName(f[1], n[2], env);
        }
        if (f[0] === "mem") return this.member(this.ev(f[1], env), f[2], n[2], env, f[1]);
        const v = this.ev(f, env);
        if (v instanceof VArr) return v.d[v.at(n[2].map((a) => this.ev(a, env)))];
        if (v instanceof VRange) return rangeIndex(v, n[2].map((a) => this.ev(a, env)));
        throw new VErr(13, "부를 수 없는 값입니다");
      }
      case "mem": return this.member(this.ev(n[1], env), n[2], null, env, n[1]);
      default: throw new Unsupported(`알 수 없는 식 ${n[0]}`);
    }
  };
  R.callName = function (nm, argNodes, env) {
    const K = nm.toUpperCase(), pr = this.procs.get(K);
    if (pr) {
      const cells = argNodes.map((a) => {
        if (a[0] === "missing") return { v: MISSING };
        if (a[0] === "name") { const c = this.lookup(env, a[1]); if (c) return { v: c.v, ref: c }; }
        return { v: this.ev(a, env) };
      });
      return this.invoke(pr, cells, false);
    }
    const b = own(BUILTIN, K) && BUILTIN[K];
    if (b) return b.call(this, argNodes, env);
    throw new Unsupported(`함수 ${nm} 는 아직 못 씁니다`);
  };
  R.member = function (obj, name, argNodes, env, objNode) {
    const K = name.toUpperCase(), args = () => (argNodes || []).map((a) => this.ev(a, env));
    if (objNode && objNode[0] === "name" && /^(APPLICATION|WORKSHEETFUNCTION)$/i.test(objNode[1]) || obj === APP || obj === WSF) {
      if (K === "WORKSHEETFUNCTION") return WSF;
      if (K === "VOLATILE" || K === "SCREENUPDATING" || K === "ENABLEEVENTS") return EMPTY;
      if (K === "CALLER") throw new Unsupported("Application.Caller 는 아직 못 씁니다");
      if (!this.host.sheetFn) throw new Unsupported(`WorksheetFunction.${name} - 시트 계산기가 없습니다`);
      return this.host.sheetFn(name, args());
    }
    if (obj instanceof VRange) {
      if (K === "VALUE" || K === "VALUE2") { const v = obj.value(); return argNodes ? EMPTY : v; }
      if (K === "TEXT") return str(obj.value());
      if (K === "CELLS") { const a = args(); return a.length ? rangeIndex(obj, a) : obj; }
      if (K === "COUNT" || K === "COUNTLARGE") return obj.h * obj.w;
      if (K === "ROW") return obj.r0 + 1;
      if (K === "COLUMN") return obj.c0 + 1;
      if (K === "ROWS" || K === "COLUMNS") { const a = args(); if (a.length) { const i = Math.round(num(a[0])) - 1; return K === "ROWS" ? new VRange([obj.rows[i] || []], obj.r0 + i, obj.c0, obj.sheet) : new VRange(obj.rows.map((r) => [r[i]]), obj.r0, obj.c0 + i, obj.sheet); } return { vba: "rc", of: obj, rows: K === "ROWS" }; }
      if (K === "ADDRESS") { const a1 = (r, c) => { let s = "", x = c + 1; while (x) { const m = (x - 1) % 26; s = String.fromCharCode(65 + m) + s; x = Math.floor((x - 1) / 26); } return `$${s}$${r + 1}`; }; return obj.h * obj.w === 1 ? a1(obj.r0, obj.c0) : `${a1(obj.r0, obj.c0)}:${a1(obj.r0 + obj.h - 1, obj.c0 + obj.w - 1)}`; }
      if (K === "OFFSET" || K === "RESIZE") throw new Unsupported(`Range.${name} 는 아직 못 씁니다(인자로 받은 범위 밖은 읽을 수 없다)`);
    }
    if (obj && obj.vba === "rc" && K === "COUNT") return obj.rows ? obj.of.h : obj.of.w;
    throw new Unsupported(`.${name} 는 아직 못 씁니다`);
  };
  const APP = { vba: "Application" }, WSF = { vba: "WorksheetFunction" };
  function rangeIndex(r, a) {
    if (a.length === 1) { const k = Math.round(num(a[0])) - 1; const i = Math.floor(k / r.w), j = k % r.w; return r.cell(i, j); }
    return r.cell(Math.round(num(a[0])) - 1, Math.round(num(a[1])) - 1);
  }
  const CONSTS = { VBCRLF: "\r\n", VBCR: "\r", VBLF: "\n", VBNEWLINE: "\r\n", VBTAB: "\t", VBNULLSTRING: "", VBNULLCHAR: "\0", VBTEXTCOMPARE: 1, VBBINARYCOMPARE: 0,
    VBEMPTY: 0, VBNULL: 1, VBINTEGER: 2, VBLONG: 3, VBSINGLE: 4, VBDOUBLE: 5, VBSTRING: 8, VBBOOLEAN: 11, VBVARIANT: 12, VBARRAY: 8192, APPLICATION: APP, WORKSHEETFUNCTION: WSF,
    XLERRNA: 2042, XLERRVALUE: 2015, XLERRDIV0: 2007, XLERRREF: 2023, XLERRNAME: 2029, XLERRNUM: 2036, XLERRNULL: 2000 };

  // ---------------------------------------------------------------- 연산
  function rank(v) { return v === EMPTY ? 0 : isNum(v) || typeof v === "boolean" ? 1 : isStr(v) ? 2 : 3; }
  function compare(a, b) {  // -1 0 1 - Variant 규칙: 숫자끼리·글끼리, 숫자 꼴 글은 숫자와, 그 밖에 숫자 < 글
    if (a instanceof VRange) a = a.value(); if (b instanceof VRange) b = b.value();
    if (a === EMPTY && b === EMPTY) return 0;
    if (a === EMPTY) a = isStr(b) ? "" : 0; if (b === EMPTY) b = isStr(a) ? "" : 0;
    if (typeof a === "boolean") a = a ? -1 : 0; if (typeof b === "boolean") b = b ? -1 : 0;
    if (isNum(a) && isNum(b)) return a < b ? -1 : a > b ? 1 : 0;
    if (isStr(a) && isStr(b)) return a < b ? -1 : a > b ? 1 : 0;
    if (isNum(a) && isStr(b)) return isNumeric(b) ? compare(a, num(b)) : -1;
    if (isStr(a) && isNum(b)) return isNumeric(a) ? compare(num(a), b) : 1;
    throw new VErr(13, "형식이 일치하지 않습니다(비교)");
  }
  const cmpOp = (o, d) => ({ "=": d === 0, "<>": d !== 0, "<": d < 0, ">": d > 0, "<=": d <= 0, ">=": d >= 0 }[o]);
  function binop(o, a, b) {
    if (a instanceof VRange) a = a.value(); if (b instanceof VRange) b = b.value();
    if (o === "&") { if (a === NULLV && b === NULLV) return NULLV; return cap(str(a === NULLV ? "" : a) + str(b === NULLV ? "" : b)); }
    if (a === NULLV || b === NULLV) return NULLV;
    if (o === "+") { if (isStr(a) && isStr(b)) return cap(a + b); if (isStr(a) && b === EMPTY) return a; if (isStr(b) && a === EMPTY) return b; return num(a) + num(b); }
    if (["AND", "OR", "XOR", "EQV", "IMP"].includes(o)) {
      if (typeof a === "boolean" && typeof b === "boolean") return o === "AND" ? a && b : o === "OR" ? a || b : o === "XOR" ? a !== b : o === "EQV" ? a === b : !a || b;
      const x = Math.round(num(a)), y = Math.round(num(b));
      return o === "AND" ? x & y : o === "OR" ? x | y : o === "XOR" ? x ^ y : o === "EQV" ? ~(x ^ y) : ~x | y;
    }
    const x = num(a), y = num(b);
    switch (o) {
      case "-": return x - y;
      case "*": return x * y;
      case "/": if (y === 0) throw new VErr(11, "0 으로 나눴습니다"); return x / y;
      case "\\": { const p = roundEven(x), q = roundEven(y); if (q === 0) throw new VErr(11, "0 으로 나눴습니다"); return Math.trunc(p / q); }
      case "MOD": { const p = roundEven(x), q = roundEven(y); if (q === 0) throw new VErr(11, "0 으로 나눴습니다"); return p % q; }
      case "^": return Math.pow(x, y);
    }
    throw new Unsupported(`연산 ${o}`);
  }
  /** s Like p - * ? # [a-z] [!a-z]. 패턴을 조각으로 나눠 별(*) 하나만 되짚는 비교(길이 곱에 비례 - 정규식처럼 폭주하지 않는다) */
  function like(s, p) {
    const T = [];
    for (let i = 0; i < p.length; i++) {
      const c = p[i];
      if (c === "*") { if (T[T.length - 1] !== "*") T.push("*"); continue; }
      if (c === "?") { T.push((x) => true); continue; }
      if (c === "#") { T.push((x) => x >= "0" && x <= "9"); continue; }
      if (c === "[") {
        const j = p.indexOf("]", i + 1); if (j < 0) throw new VErr(93, "패턴 문자열이 잘못되었습니다");
        let body = p.slice(i + 1, j), neg = false; if (body[0] === "!") { neg = true; body = body.slice(1); }
        const parts = [];
        for (let k = 0; k < body.length; k++) {
          if (body[k + 1] === "-" && k + 2 < body.length) { const lo = body[k], hi = body[k + 2]; if (lo > hi) throw new VErr(93, "패턴 문자열이 잘못되었습니다"); parts.push([lo, hi]); k += 2; }
          else parts.push([body[k], body[k]]);
        }
        T.push((x) => parts.some(([lo, hi]) => x >= lo && x <= hi) !== neg); i = j; continue;
      }
      T.push((x) => x === c);
    }
    let i = 0, k = 0, star = -1, mark = 0;
    while (i < s.length) {
      if (k < T.length && T[k] !== "*" && T[k](s[i])) { i++; k++; }
      else if (k < T.length && T[k] === "*") { star = k++; mark = i; }
      else if (star >= 0) { k = star + 1; i = ++mark; }
      else return false;
    }
    while (k < T.length && T[k] === "*") k++;
    return k === T.length;
  }

  // ---------------------------------------------------------------- 내장 함수 (인자는 식 노드 - 이 런타임에서 계산)
  const V = (rt, a, env) => a.map((x) => (x[0] === "missing" ? MISSING : rt.ev(x, env)));
  const opt = (v, d) => (v === undefined || v === MISSING ? d : v);
  const plain = (f) => function (a, env) { return f.apply(null, V(this, a, env)); };
  const len = (n) => { const k = Math.max(0, Math.round(num(n))); if (k > LIMIT.str) throw new VErr(14, "문자열이 너무 깁니다"); return k; };
  const arrOf = (v) => { if (v instanceof VRange) v = v.value(); if (!(v instanceof VArr)) throw new VErr(13, "배열이 아닙니다"); return v; };
  const BUILTIN = {
    LEN: plain((s) => (s === NULLV ? NULLV : str(s).length)),
    LEFT: plain((s, n) => str(s).slice(0, Math.max(0, Math.round(num(n))))),
    RIGHT: plain((s, n) => { s = str(s); const k = Math.max(0, Math.round(num(n))); return k ? s.slice(-k) : ""; }),
    MID: plain((s, st, n) => { s = str(s); const a = Math.round(num(st)) - 1; if (a < 0) throw new VErr(5, "잘못된 인수"); return n === undefined || n === MISSING ? s.slice(a) : s.substr(a, Math.max(0, Math.round(num(n)))); }),
    INSTR: plain((...a) => { let st = 1; if (a.length >= 3 && a[0] !== MISSING && (isNum(a[0]) || isNumeric(a[0]) && !isStr(a[0]))) { st = Math.round(num(a[0])); a = a.slice(1); } const [s, f, cmp] = a; let x = str(s), y = str(f); if (num(opt(cmp, 0)) === 1) { x = x.toLowerCase(); y = y.toLowerCase(); } return x.indexOf(y, st - 1) + 1; }),
    INSTRREV: plain((s, f, st, cmp) => { let x = str(s), y = str(f); if (num(opt(cmp, 0)) === 1) { x = x.toLowerCase(); y = y.toLowerCase(); } const from = st === undefined || st === MISSING || num(st) < 0 ? x.length : Math.round(num(st)) - 1; return x.lastIndexOf(y, from) + 1; }),
    REPLACE: plain((s, f, r, st, cnt, cmp) => { s = str(s); f = str(f); r = str(r); if (!f) return s; let out = "", i = Math.round(num(opt(st, 1))) - 1, n = Math.round(num(opt(cnt, -1))); const text = num(opt(cmp, 0)) === 1; s = s.slice(i); const hay = text ? s.toLowerCase() : s, nd = text ? f.toLowerCase() : f; let p = 0; for (;;) { if (n === 0) break; const k = hay.indexOf(nd, p); if (k < 0) break; out += s.slice(p, k) + r; cap(out); p = k + f.length; n--; } return cap(out + s.slice(p)); }),
    TRIM: plain((s) => str(s).replace(/^ +| +$/g, "")), LTRIM: plain((s) => str(s).replace(/^ +/, "")), RTRIM: plain((s) => str(s).replace(/ +$/, "")),
    UCASE: plain((s) => str(s).toUpperCase()), LCASE: plain((s) => str(s).toLowerCase()),
    SPACE: plain((n) => " ".repeat(len(n))), STRING: plain((n, c) => (isNum(c) ? String.fromCharCode(c) : str(c)[0] || "").repeat(len(n))),
    STRREVERSE: plain((s) => [...str(s)].reverse().join("")),
    STRCOMP: plain((a, b, cmp) => { let x = str(a), y = str(b); if (num(opt(cmp, 0)) === 1) { x = x.toLowerCase(); y = y.toLowerCase(); } return x < y ? -1 : x > y ? 1 : 0; }),
    CHR: plain((n) => String.fromCharCode(Math.round(num(n)))), CHRW: plain((n) => String.fromCharCode(Math.round(num(n)))),
    ASC: plain((s) => { s = str(s); if (!s) throw new VErr(5, "잘못된 인수"); return s.charCodeAt(0); }), ASCW: plain((s) => str(s).charCodeAt(0)),
    CSTR: plain((v) => str(v)), CDBL: plain((v) => num(v)), CSNG: plain((v) => num(v)), CCUR: plain((v) => num(v)), CDEC: plain((v) => num(v)),
    CLNG: plain((v) => roundEven(num(v))), CINT: plain((v) => roundEven(num(v))), CBYTE: plain((v) => roundEven(num(v))), CLNGLNG: plain((v) => roundEven(num(v))), CBOOL: plain((v) => bool(v)), CVAR: plain((v) => v),
    CVERR: plain((n) => { const m = { 2042: "#N/A", 2015: "#VALUE!", 2007: "#DIV/0!", 2023: "#REF!", 2029: "#NAME?", 2036: "#NUM!", 2000: "#NULL!" }; return new CVErr(m[Math.round(num(n))] || "#VALUE!"); }),
    VAL: plain((s) => { const m = /^\s*[-+]?(\d[\d\s]*)?(\.\d*)?([eE][-+]?\d+)?/.exec(str(s)); const t = m ? m[0].replace(/\s/g, "") : ""; const n = parseFloat(t); return isNaN(n) ? 0 : n; }),
    INT: plain((v) => Math.floor(num(v))), FIX: plain((v) => Math.trunc(num(v))), ABS: plain((v) => Math.abs(num(v))), SGN: plain((v) => Math.sign(num(v))),
    SQR: plain((v) => { const x = num(v); if (x < 0) throw new VErr(5, "잘못된 인수"); return Math.sqrt(x); }), EXP: plain((v) => Math.exp(num(v))), LOG: plain((v) => Math.log(num(v))),
    SIN: plain((v) => Math.sin(num(v))), COS: plain((v) => Math.cos(num(v))), TAN: plain((v) => Math.tan(num(v))), ATN: plain((v) => Math.atan(num(v))),
    ROUND: plain((v, d) => { const k = Math.round(num(opt(d, 0))), f = Math.pow(10, k); return roundEven(Number((num(v) * f).toPrecision(15))) / f; }),
    ISEMPTY: plain((v) => (v instanceof VRange ? v.value() : v) === EMPTY), ISNULL: plain((v) => v === NULLV), ISMISSING: plain((v) => v === MISSING),
    ISNUMERIC: plain((v) => isNumeric(v)), ISARRAY: plain((v) => v instanceof VArr || (v instanceof VRange && v.h * v.w > 1)), ISERROR: plain((v) => (v instanceof VRange ? v.value() : v) instanceof CVErr),
    ISDATE: plain(() => false), ISOBJECT: plain((v) => v instanceof VRange || v === NOTHING),
    TYPENAME: plain((v) => { if (v instanceof VRange) return "Range"; if (v instanceof VArr) return "Variant()"; if (v === EMPTY) return "Empty"; if (v === NULLV) return "Null"; if (v === NOTHING) return "Nothing"; if (v instanceof CVErr) return "Error"; return isStr(v) ? "String" : isNum(v) ? (Number.isInteger(v) ? "Long" : "Double") : typeof v === "boolean" ? "Boolean" : "Object"; }),
    VARTYPE: plain((v) => (v === EMPTY ? 0 : v === NULLV ? 1 : isStr(v) ? 8 : typeof v === "boolean" ? 11 : isNum(v) ? 5 : v instanceof VArr ? 8204 : v instanceof CVErr ? 10 : 9)),
    IIF: plain((c, a, b) => (bool(c) ? a : b)),
    LBOUND: plain((a, d) => { a = arrOf(a); const k = Math.round(num(opt(d, 1))) - 1; if (!a.b[k]) throw new VErr(9, "차원이 없습니다"); return a.b[k][0]; }),
    UBOUND: plain((a, d) => { a = arrOf(a); const k = Math.round(num(opt(d, 1))) - 1; if (!a.b[k]) throw new VErr(9, "차원이 없습니다"); return a.b[k][1]; }),
    ARRAY: plain((...a) => new VArr([[0, a.length - 1]], a)),
    SPLIT: plain((s, d, lim) => { s = str(s); d = d === undefined || d === MISSING ? " " : str(d); let parts = d === "" ? [s] : s.split(d); const n = Math.round(num(opt(lim, -1))); if (n > 0 && parts.length > n) parts = [...parts.slice(0, n - 1), parts.slice(n - 1).join(d)]; if (s === "") parts = []; return new VArr([[0, parts.length - 1]], parts); }),
    JOIN: plain((a, d) => cap(arrOf(a).d.map(str).join(d === undefined || d === MISSING ? " " : str(d)))),
    FORMAT: plain((v, f) => { if (f === undefined || f === MISSING) return str(v); const fs = str(f); if (/^0+(\.0+)?$/.test(fs)) { const dec = (fs.split(".")[1] || "").length; const s = num(v).toFixed(dec); const [ip, dp] = s.split("."); return ip.padStart(fs.split(".")[0].length, "0") + (dp ? "." + dp : ""); } if (/^#,##0(\.0+)?$/.test(fs)) { const dec = (fs.split(".")[1] || "").length; return num(v).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }); } throw new Unsupported(`Format "${fs}" 는 아직 못 씁니다`); }),
    NOW: function () { throw new Unsupported("Now·Date·Time 은 아직 못 씁니다"); },
  };
  BUILTIN.DATE = BUILTIN.NOW; BUILTIN.TIME = BUILTIN.NOW; BUILTIN.TIMER = BUILTIN.NOW;
  BUILTIN["LEFT$"] = BUILTIN.LEFT;

  // ---------------------------------------------------------------- 밖에서 쓰는 것
  /** modules [{name, kind, code}] → {fns: {이름(대문자): (args) => 값}, errors, has(name), runtime} */
  function compile(modules, host) {
    const rt = new Runtime(modules || [], host), mods = new Set((modules || []).map((m) => String(m.name).toUpperCase()));  // 모듈과 이름이 같은 함수는 칸에서 못 부른다(엑셀 #NAME?)
    return { runtime: rt, errors: rt.errors, has: (nm) => { const k = String(nm).toUpperCase(); return !mods.has(k) && rt.procs.has(k) && rt.procs.get(k).kind === "FUNCTION"; }, call: (nm, args) => rt.call(nm, args), unsupported: (nm) => { const p = rt.procs.get(String(nm).toUpperCase()); return p && p.unsupported; } };
  }
  /** 셀 값으로 - Empty → 0(엑셀과 같다), 오류 값 → {code} */
  function toCell(v) {
    if (v instanceof VRange) v = v.value();
    if (v === EMPTY || v === MISSING) return 0;
    if (v === NULLV || v === NOTHING) return { code: "#VALUE!" };
    if (v instanceof CVErr) return { code: v.code };
    if (v instanceof VArr) {
      if (v.b.length === 1) return { rows: [v.d.map(toCell)] };
      if (v.b.length === 2) { const rows = []; for (let i = v.b[0][0]; i <= v.b[0][1]; i++) { const row = []; for (let j = v.b[1][0]; j <= v.b[1][1]; j++) row.push(toCell(v.d[v.at([i, j])])); rows.push(row); } return { rows }; }
      return { code: "#VALUE!" };
    }
    return v;
  }
  // ---------------------------------------------------------------- 위험 코드 - 엑셀에서 열면 실제로 도는 매크로(이 실행기는 하지 않는다). vba_project.py RISKS 와 같은 목록(tests/vba_test.js 가 맞춰 본다)
  const RISKS = [
    ["auto", "^\\s*(?:(?:Public|Private|Static)\\s+)*Sub\\s+(Auto_?Open|Auto_?Close|Auto_?Exec|Auto_?Exit|Workbook_[A-Za-z0-9_]+|Worksheet_[A-Za-z0-9_]+|Chart_[A-Za-z0-9_]+|App_[A-Za-z0-9_]+)\\s*\\(", "열거나 이벤트가 생기면 저절로 실행된다"],
    ["exec", "(?<![A-Za-z0-9_.])(Shell|ShellExecute[A-Za-z0-9_]*|WinExec|CreateProcess[A-Za-z0-9_]*|SendKeys|AppActivate|CallByName|MacScript|ExecuteExcel4Macro)(?![A-Za-z0-9_])", "다른 프로그램·명령을 실행할 수 있다"],
    ["exec", "(?<![A-Za-z0-9_])(Application\\.Run|Evaluate)(?![A-Za-z0-9_])","이름으로 다른 코드를 실행할 수 있다"],
    ["object", "(?<![A-Za-z0-9_.])(CreateObject|GetObject)(?![A-Za-z0-9_])", "외부 개체(셸·파일·네트워크·다른 앱)를 만든다"],
    ["api", "^\\s*(?:(?:Public|Private)\\s+)?Declare\\s", "윈도 API(DLL)를 직접 부른다"],
    ["file", "(?<![A-Za-z0-9_.])(Kill|RmDir|MkDir|ChDir|ChDrive|FileCopy|SetAttr)(?![A-Za-z0-9_])", "파일·폴더를 바꾸거나 지운다"],
    ["file", "^\\s*Open\\s.+\\sFor\\s+(Output|Append|Binary|Random)", "파일을 쓴다"],
    ["file", "\\.(SaveAs|SaveCopyAs|SaveAs2|ExportAsFixedFormat)(?![A-Za-z0-9_])", "파일을 다른 곳에 저장한다"],
    ["code", "(?<![A-Za-z0-9_])(VBProject|VBComponents|CodeModule)(?![A-Za-z0-9_])", "매크로 코드를 고친다"],
    ["net", "(URLDownloadToFile[A-Za-z0-9_]*|XMLHTTP|WinHttp|ServerXMLHTTP|InternetOpen[A-Za-z0-9_]*|Msxml2|https?://)", "네트워크로 내려받거나 보낸다"],
    ["exec", "(WScript|PowerShell|cmd\\.exe|cmd /c|mshta|rundll32|regsvr32|certutil|bitsadmin|\\.exe(?![A-Za-z0-9_])|\\.ps1(?![A-Za-z0-9_])|\\.bat(?![A-Za-z0-9_])|\\.vbs(?![A-Za-z0-9_])|\\.hta(?![A-Za-z0-9_]))", "명령·실행 파일을 가리킨다"],
    ["setting", "(?<![A-Za-z0-9_.])(SaveSetting|DeleteSetting|RegWrite|RegDelete)(?![A-Za-z0-9_])", "레지스트리를 바꾼다"],
  ];
  const RISK_RE = RISKS.map(([kind, re, msg]) => [kind, new RegExp(re, "i"), msg]);
  /** 한 줄에서 주석(' 또는 Rem)을 뺀 코드 - 문자열 안의 ' 는 그대로 */
  function codePart(ln) {
    if (/^\s*Rem(\s|$)/i.test(ln)) return "";
    let q = false;
    for (let i = 0; i < ln.length; i++) { const c = ln[i]; if (c === '"') q = !q; else if (c === "'" && !q) return ln.slice(0, i); }
    return ln;
  }
  /** modules [{name, kind, code}] → [{module, line, kind, word, msg}] - 엑셀에서 실제로 실행될 때 위험할 수 있는 줄(모듈 종류 무관) */
  function risks(modules) {
    const out = [];
    for (const m of modules || []) {
      String(m.code || "").replace(/\r\n?/g, "\n").split("\n").forEach((raw, i) => {
        const ln = codePart(raw); if (!ln.trim()) return;
        for (const [kind, re, msg] of RISK_RE) { const h = re.exec(ln); if (h) out.push({ module: m.name, line: i + 1, kind, word: h[1] || h[0], msg }); }
      });
    }
    return out;
  }

  // ---------------------------------------------------------------- 값 주고받기(Worker) - 구조화 복제가 되는 평범한 값으로
  function pack(v) {
    if (v === EMPTY) return { t: "E" }; if (v === MISSING) return { t: "M" }; if (v === NULLV) return { t: "N" }; if (v === NOTHING) return { t: "O" };
    if (v instanceof CVErr) return { t: "X", c: v.code };
    if (v instanceof VRange) return { t: "R", rows: v.rows, r: v.r0, c: v.c0, s: v.sheet };
    if (v instanceof VArr) return { t: "A", b: v.b, d: v.d.map(pack) };
    return v;
  }
  function unpack(v) {
    if (!v || typeof v !== "object") return v;
    switch (v.t) {
      case "E": return EMPTY; case "M": return MISSING; case "N": return NULLV; case "O": return NOTHING;
      case "X": return new CVErr(v.c);
      case "R": return new VRange(v.rows, v.r, v.c, v.s);
      case "A": return new VArr(v.b, v.d.map(unpack));
    }
    return v;
  }
  class Pending extends Error {}  // Worker 가 아직 계산 중 - 그 칸은 저장된 값을 그대로 둔다(sheetcalc.js)

  /** 화면용 - 계산은 Worker 에서, 결과는 (이름 + 인자)별로 기억한다. 처음 보는 부르기는 Pending 을 던지고 Worker 에 맡긴 뒤
   *  다 끝나면 onReady() (다시 계산하라는 신호). Worker 가 LIMIT.ms 의 두 배 넘게 답이 없으면 끝내고 그 부르기를 오류로 둔다.
   *  compiled = compile(modules) (has·오류 목록은 화면에서 - 읽기만 하고 실행하지 않는다) */
  function client(modules, compiled, opts) {
    const url = (opts && opts.url) || "vbaworker.js", onReady = (opts && opts.onReady) || (() => {}), wait = (opts && opts.wait) || LIMIT.ms * 2 + 500;
    const memo = new Map(), queue = [];  // queue: [{id, key, name, args}] - 앞의 것이 Worker 가 지금 계산하는 것
    let w = null, seq = 0, timer = null, dead = false, ready = false;  // ready - Worker 가 스크립트를 다 읽었다(감시 시간은 그 뒤부터 잰다)
    const start = () => {
      w = new Worker(url); ready = false;
      w.onmessage = (e) => {
        const m = e.data; if (m && m.type === "ready") { ready = true; arm(); return; }
        if (!queue.length || m.id !== queue[0].id) return;
        const q = queue.shift(); memo.set(q.key, m.err ? { err: m.err } : { v: m.v });
        if (memo.size > 20000) memo.delete(memo.keys().next().value);
        arm(); if (!queue.length) onReady();
      };
      w.onerror = (e) => { e.preventDefault(); fail("실행기 오류"); };
      w.postMessage({ type: "init", modules });
      for (const q of queue) w.postMessage({ type: "call", id: q.id, name: q.name, args: q.args });
    };
    const arm = () => { clearTimeout(timer); timer = queue.length && ready ? setTimeout(() => fail(`실행이 너무 오래 걸립니다(${wait / 1000}초 동안 답이 없어 멈췄습니다)`), wait) : null; };
    function fail(msg) {  // 지금 계산하던 부르기를 오류로 두고 Worker 를 새로(남은 것은 다시 보낸다)
      clearTimeout(timer); timer = null;
      if (w) { w.terminate(); w = null; }
      const q = queue.shift(); if (q) memo.set(q.key, { err: { kind: "verr", msg } });
      if (dead) return;
      if (queue.length) start(); else onReady();
    }
    return {
      has: compiled.has, errors: compiled.errors, unsupported: compiled.unsupported, runtime: compiled.runtime,
      call(name, args) {
        const pa = args.map(pack), key = String(name).toUpperCase() + "\u0000" + JSON.stringify(pa), hit = memo.get(key);
        if (hit) { if (hit.err) throw hit.err.kind === "unsupported" ? new Unsupported(hit.err.msg) : new VErr(hit.err.num || 0, hit.err.msg); return hit.v; }
        if (!queue.some((q) => q.key === key)) {
          const q = { id: ++seq, key, name, args: pa }; queue.push(q);
          if (!w) start(); else { w.postMessage({ type: "call", id: q.id, name, args: pa }); if (queue.length === 1) arm(); }
        }
        throw new Pending("계산 중");
      },
      busy: () => queue.length > 0,
      close() { dead = true; clearTimeout(timer); if (w) w.terminate(); w = null; queue.length = 0; },
    };
  }
  /** Worker 쪽 - 메시지 하나 처리(vbaworker.js). 결과는 toCell 한 평범한 값 */
  function serve(state, m, host) {
    if (m.type === "init") { state.c = compile(m.modules, host); return null; }
    try {
      const v = toCell(state.c.call(m.name, m.args.map(unpack)));
      return { id: m.id, v };
    } catch (e) {
      if (e instanceof Unsupported) return { id: m.id, err: { kind: "unsupported", msg: e.message } };
      return { id: m.id, err: { kind: "verr", num: e.num || 0, msg: e instanceof VErr ? e.message : `실행 오류(${e.message})` } };
    }
  }

  const API = { compile, toCell, risks, RISKS, client, serve, pack, unpack, LIMIT, VRange, VArr, EMPTY, MISSING, Unsupported, VErr, CVErr, Pending };
  if (typeof module === "object" && module.exports) module.exports = API; else root.NexaVBA = API;
})(typeof window !== "undefined" ? window : globalThis);
