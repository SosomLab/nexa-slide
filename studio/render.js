/* 요소 모델 → HTML(절대 위치) 순수 렌더러 - 썸네일·캔버스·검증 페이지 공용.
   export_pptx.py 와 같은 규칙으로 그린다. 한쪽을 고치면 다른 쪽(common.py·export_pptx.py)도 고친다.
     - 좌표·크기 px(1280×720), 글자 size px (PPT pt = px × 0.75)
     - 줄마다 한 단락, 줄 높이 = size × lineHeight (PPT "정확히" 줄 간격)
     - 인라인: **굵게**, ==강조==, [[토큰|색 글자]], {page}
     - plan: [[글자]] = warn 강조, [[ok:글자]] = ok 강조 (배경·글자색·굵게만 - 폭 불변) */
(function (root) {
  "use strict";
  let T = null; // tokens.json

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function setTokens(t) { T = t; }
  function color(v, dflt) {
    if (!v) return dflt || null;
    let x = v;
    for (let i = 0; i < 5; i++) {
      if (typeof x === "string" && x[0] === "#") return x.length === 7 ? x.toUpperCase() : (dflt || "#000000");
      if (T && T.colors && x in T.colors) x = T.colors[x]; else return dflt || "#000000";
    }
    return dflt || "#000000";
  }
  /** 토큰명 또는 #RRGGBB·#RRGGBBAA → ["#RRGGBB", 불투명도 0~1] (common.color_alpha 와 같은 규칙) */
  function colorAlpha(v, dflt) {
    if (!v) return null;
    let x = v;
    for (let i = 0; i < 5; i++) {
      if (typeof x !== "string") return [dflt || "#000000", 1];
      if (x[0] === "#") {
        if (x.length === 7) return [x.toUpperCase(), 1];
        if (x.length === 9 && /^[0-9A-Fa-f]{2}$/.test(x.slice(7, 9))) return [x.slice(0, 7).toUpperCase(), Math.round(parseInt(x.slice(7, 9), 16) / 255 * 1000) / 1000];
        return [dflt || "#000000", 1];
      }
      if (T && T.colors && x in T.colors) x = T.colors[x]; else return [dflt || "#000000", 1];
    }
    return [dflt || "#000000", 1];
  }
  const clamp01 = (v, d) => { const n = parseFloat(v); return isNaN(n) ? d : Math.max(0, Math.min(1, n)); };
  const r3 = (n) => Math.round(n * 1000) / 1000;
  /** 도형 채우기(fill) 값 정규화 - common.fill_spec 와 같은 규칙. 없으면 null.
   *  토큰·"#RRGGBB"·"#RRGGBBAA"·{color, alpha} → {kind:"solid", color, alpha}
   *  {gradient:{angle, stops:[[위치, 색, (불투명도)]…] | [색…]}, alpha} → {kind:"gradient", angle(0 = 왼→오, 90 = 위→아래, 시계 방향), stops:[[위치, "#RRGGBB", 불투명도]…]} */
  function fillSpec(v) {
    if (!v) return null;
    if (typeof v === "string") { const ca = colorAlpha(v); return ca ? { kind: "solid", color: ca[0], alpha: ca[1] } : null; }
    if (typeof v !== "object") return null;
    const baseA = clamp01(v.alpha === undefined ? 1 : v.alpha, 1);
    const g = v.gradient;
    if (!g || typeof g !== "object") { const ca = colorAlpha(v.color); return ca ? { kind: "solid", color: ca[0], alpha: r3(ca[1] * baseA) } : null; }
    const raw = Array.isArray(g.stops) ? g.stops : [], n = raw.length, stops = [];
    raw.forEach((st, i) => {
      let pos, col, a;
      if (typeof st === "string") { pos = n > 1 ? i / (n - 1) : 0; col = st; a = 1; }  // 색만 → 고른 간격
      else if (Array.isArray(st) && st.length >= 2) { pos = st[0]; col = st[1]; a = st.length > 2 ? st[2] : 1; }
      else return;
      const ca = colorAlpha(col);
      if (ca) stops.push([Math.round(clamp01(pos, 0) * 10000) / 10000, ca[0], r3(ca[1] * clamp01(a, 1) * baseA)]);
    });
    stops.sort((p, q) => p[0] - q[0]);
    if (!stops.length) return null;
    if (stops.length === 1) return { kind: "solid", color: stops[0][1], alpha: stops[0][2] };
    const ang = parseFloat(g.angle);
    return { kind: "gradient", angle: Math.round((((isNaN(ang) ? 0 : ang) % 360) + 360) % 360 * 100) / 100, stops };
  }
  const rgba = (hex, a) => a >= 1 ? hex : `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a})`;
  /** fill → CSS background 값. 그라데이션 각도: PPT 0 = 왼→오 = CSS 90deg */
  function fillCss(v) {
    const f = fillSpec(v);
    if (!f) return "transparent";
    if (f.kind === "solid") return rgba(f.color, f.alpha);
    return `linear-gradient(${f.angle + 90}deg, ${f.stops.map(([p, c, a]) => `${rgba(c, a)} ${+(p * 100).toFixed(2)}%`).join(", ")})`;
  }
  function radius(v, w, h) {
    if (v === undefined || v === null || v === 0 || v === "0" || v === "") return 0;
    let r = typeof v === "string" ? (T && T.radius && v in T.radius ? T.radius[v] : parseFloat(v)) : v;
    r = Number(r) || 0;
    return Math.max(0, Math.min(r, Math.min(w, h) / 2));
  }
  // style="…" 속성 안에 들어가므로 큰따옴표를 작은따옴표로 바꾼다
  /** 글꼴 역할 이름 정규화(common.font_role 와 같은 규칙): mono·code → mono, heading → heading, 그 밖(없음·body·모르는 값) → body */
  const fontRole = (k) => (k === "mono" || k === "code") ? "mono" : k === "heading" ? "heading" : "body";
  const shift = (k, s, lh) => {
    // PowerPoint 줄 배치 보정 - 서버가 글꼴 파일 메트릭으로 역할마다 계산해 tokens.fonts.pptTextShift(세트는 fontPresets[*].pptTextShift)에 넣는다(common.ppt_text_shift)
    k = fontRole(k);
    const fs = FO || (T && T.fonts), ps = fs && fs.pptTextShift;
    const c = ps && (ps[k] || ps[k === "mono" ? "mono" : "body"]);
    return c ? +(s * (c[0] * lh + c[1])).toFixed(2) : 0;
  };
  // 슬라이드·덱 글꼴 세트(fontPreset) - common.preset_fonts 와 같은 규칙. FO = 지금 그리는 장의 글꼴(없으면 작업 공간 글꼴)
  let FO = null, DECK_FP = null;
  function presetFonts(name) {
    const p = name && T && T.fontPresets && T.fontPresets[name]; if (!p) return null;
    const f = JSON.parse(JSON.stringify(p));
    for (const k of ["body", "mono"]) if (!f[k]) f[k] = T.fonts[k];
    for (const [k, v] of Object.entries(T.fontOverrides || {})) f[k] = { ...(f[k] || {}), ...v };
    if (!f.heading) f.heading = f.body;
    return f;
  }
  function setDeckFonts(name) { DECK_FP = name || null; }
  const font = (k) => { const fs = FO || (T && T.fonts), r = fontRole(k); return (fs && (fs[r] || fs.body) ? (fs[r] || fs.body).css : "'Malgun Gothic', sans-serif").replace(/"/g, "'"); };

  // ---------- 인라인 강조 ----------
  const MARK = /\*\*(.+?)\*\*|==(.+?)==|\[\[([#\w-]+)\|(.+?)\]\]|__(.+?)__|(?<![\w*])\*([^*\s](?:[^*]*?[^*\s])?)\*(?![\w*])|~~(.+?)~~|\^\{(.+?)\}|_\{(.+?)\}|\[\[(?:link|url):(\S+?)\|(.+?)\]\]|\[\[bg:([#\w-]+)\|(.+?)\]\]/g;
  // **굵게** ==강조== [[색|글]] __밑줄__ *기울임* ~~취소선~~ ^{위첨자} _{아래첨자} [[link:url|글]](글자 링크, #3 = 슬라이드) [[bg:색|글]](형광펜 배경) - common._MARK 와 같다
  function runs(text, page, base) {
    // 강조는 겹쳐 쓸 수 있다 - 안쪽 글을 다시 풀어 바깥 스타일과 합친다(예: [[s1|**굵은 색 글자**]], **[[s1|색]]**). common.runs 와 같은 규칙
    let s = String(text == null ? "" : text);
    if (page != null) s = s.split("{page}").join(String(page));
    const b = base || {}, out = [], re = new RegExp(MARK.source, "g");  // 재귀마다 새 정규식(lastIndex 공유 안 함)
    let pos = 0, m;
    const push = (t, st) => { for (const r of runs(t, null, { ...b, ...st })) out.push(r); };
    while ((m = re.exec(s))) {
      if (m.index > pos) out.push([s.slice(pos, m.index), { ...b }]);
      if (m[1] !== undefined) push(m[1], { bold: true });
      else if (m[2] !== undefined) push(m[2], { bold: true, color: "primary" });
      else if (m[5] !== undefined) push(m[5], { underline: true });
      else if (m[6] !== undefined) push(m[6], { italic: true });
      else if (m[7] !== undefined) push(m[7], { strike: true });
      else if (m[8] !== undefined) push(m[8], { sup: true });
      else if (m[9] !== undefined) push(m[9], { sub: true });
      else if (m[11] !== undefined) push(m[11], { link: m[10] });
      else if (m[13] !== undefined) push(m[13], { bg: m[12] });
      else push(m[4], { color: m[3] });
      pos = re.lastIndex;
    }
    if (pos < s.length) out.push([s.slice(pos), { ...b }]);
    return out.length ? out : [["", { ...b }]];
  }
  const plain = (s) => runs(s).map((r) => r[0]).join("");

  // ---------- 코드 하이라이트 (concept.html hlSQL() 이식 - common.py hl_sql 과 같은 결과) ----------
  // 역할: k 예약어·타입·함수(굵게) · tb 테이블·CTE · al 테이블 별칭(기울임) · ca 결과 컬럼 별칭(기울임)
  //       st 문자열 · nu 숫자 · co 주석 · bi 바인드 · null 일반
  const SQL_KW = new Set(("select from where and or not in exists join left right full outer inner cross on as group by order having union all with recursive " +
    "case when then else end between like is null distinct insert into values update set delete merge using matched connect prior start table desc asc over " +
    "partition fetch first rows only create index primary key foreign references constraint default level nocycle siblings search depth breadth cycle to").split(" "));
  const SQL_TYPE = new Set("varchar varchar2 number date text char integer int timestamp clob blob boolean".split(" "));
  const WS = /^\s+$/;
  function hlSQL(src) {
    const re = /(--[^\n]*|\/\*[\s\S]*?\*\/)|('(?:[^']|'')*')|(:[A-Za-z_]\w*)|(\b\d+(?:\.\d+)?\b)|("[^"]+"|[A-Za-z_][\w$#]*)|(\s+|[^\s])/g;
    const toks = []; let m;
    while ((m = re.exec(src))) toks.push(m[1] ? ["co", m[0]] : m[2] ? ["st", m[0]] : m[3] ? ["bi", m[0]] : m[4] ? ["nu", m[0]] : m[5] ? ["id", m[0]] : ["p", m[0]]);
    const tables = new Set(), aliases = new Set();
    const next = (i) => { for (let j = i + 1; j < toks.length; j++) if (!WS.test(toks[j][1])) return toks[j]; return null; };
    const pass = () => {
      let prev = "", expect = false;
      return toks.map(([t, v], i) => {
        if (t !== "id") {
          if (!(t === "p" && (WS.test(v) || v === "."))) expect = false;
          if (t === "p" && v === ",") prev = prev === "_t" ? "from" : prev;
          return [v, t === "p" ? null : t];
        }
        const low = v.toLowerCase(), nx = next(i);
        if (SQL_TYPE.has(low)) { prev = low; return [v, "k"]; }
        if (SQL_KW.has(low)) { if (low !== "recursive") prev = low; expect = false; return [v, "k"]; }
        if (nx && nx[1] === "(" && !["with", "_t"].includes(prev)) { prev = ""; return [v, "k"]; }
        if (nx && nx[1] === ".") return [v, aliases.has(low) ? "al" : "tb"];
        if (["from", "join", "into", "update", "with", "table", "using", "merge"].includes(prev)) { tables.add(low); prev = "_t"; expect = true; return [v, "tb"]; }
        if (expect && prev === "_t") { aliases.add(low); expect = false; prev = ""; return [v, "al"]; }
        if (prev === "as") { prev = ""; return [v, tables.has(low) ? "tb" : "ca"]; }
        if (tables.has(low)) return [v, "tb"];
        if (aliases.has(low)) return [v, "al"];
        prev = ""; return [v, null];
      });
    };
    pass();         // 1차: 테이블·별칭 수집
    return pass();  // 2차: 색 입히기
  }
  const PY_KW = new Set("def return import from as for in if elif else while with try except finally class lambda and or not is None True False yield pass break continue raise async await".split(" "));
  function hlPython(src) {
    const re = /(#[^\n]*)|('[^'\n]*'|"[^"\n]*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+|[^\s])/g;
    const out = []; let m;
    while ((m = re.exec(src))) out.push([m[0], m[1] ? "co" : m[2] ? "st" : m[3] ? "nu" : m[4] ? (PY_KW.has(m[0]) ? "k" : null) : null]);
    return out;
  }
  // ---------- 여러 언어 하이라이트 - 언어 정의는 code_langs.json(common.py 와 같은 파일·같은 알고리즘). setLangs 로 받는다 ----------
  let LANGS = null, LANG_SETS = {};
  function setLangs(d) { LANGS = d || null; LANG_SETS = {}; }
  /** el.lang → 정의 이름(별칭 포함, 대소문자 무시). 없으면 sql(예전 기본), 모르면 plain */
  function langOf(el) {
    const l = String(el.lang || "sql").toLowerCase();
    if (!LANGS) return l === "python" || l === "sql" ? l : "plain";
    if (LANGS[l] && l[0] !== "_") return l;
    for (const k of Object.keys(LANGS)) if (k[0] !== "_" && (LANGS[k].alias || []).includes(l)) return k;
    return "plain";
  }
  const isA = (c) => (c >= "A" && c <= "Z") || (c >= "a" && c <= "z") || c === "_";
  const isD = (c) => c >= "0" && c <= "9";
  function hlGeneric(src, name) {
    const sp = LANGS[name], n = src.length, out = [];
    if (!LANG_SETS[name]) { const low = (w) => (sp.ci ? w.toLowerCase() : w); LANG_SETS[name] = ["kw", "types", "lits", "fn"].map((k) => new Set((sp[k] || []).map(low))); }
    const [KW, TY, LI, FN] = LANG_SETS[name], idx = sp.idx || "";
    const id0 = (c) => isA(c) || (c !== "" && idx.includes(c)), id1 = (c) => isA(c) || isD(c) || (c !== "" && idx.includes(c));
    const push = (v, r) => { const L = out[out.length - 1]; if (L && L[1] === null && r === null) L[0] += v; else out.push([v, r]); };
    const eol = (i) => { const e = src.indexOf("\n", i); return e < 0 ? n : e; };
    const skipSp = (j) => { while (j < n && (src[j] === " " || src[j] === "\t")) j++; return j; };
    let i = 0;
    while (i < n) {
      const c = src[i], prev = i ? src[i - 1] : "\n", nx = i + 1 < n ? src[i + 1] : "";
      let k = i - 1; while (k >= 0 && (src[k] === " " || src[k] === "\t")) k--;
      const atLine = k < 0 || src[k] === "\n";
      let j = -1, role = null;
      if (sp.diff && (i === 0 || prev === "\n")) { j = eol(i); role = c === "+" ? "st" : c === "-" ? "bi" : c === "@" ? "co" : null; }
      if (j < 0 && sp.md && atLine && c === "#") { j = eol(i); role = "k"; }
      if (j < 0) for (const [a, b] of sp.block || []) if (src.startsWith(a, i)) { const e = src.indexOf(b, i + a.length); j = e < 0 ? n : e + b.length; role = "co"; break; }
      if (j < 0 && sp.vars && c === "$" && nx) {
        if (nx === "{" || nx === "(") { const e = src.indexOf(nx === "{" ? "}" : ")", i); j = e < 0 ? n : e + 1; }
        else if (id0(nx) || isD(nx)) { j = i + 2; while (j < n && id1(src[j])) j++; }
        else if ("@#?*!$-".includes(nx)) j = i + 2;
        if (j >= 0) role = "bi";
      }
      if (j < 0) for (const a of sp.line || []) if (src.startsWith(a, i) && !(sp.hashWs && a === "#" && !/\s/.test(prev))) { j = eol(i); role = "co"; break; }
      if (j < 0 && sp.pre && c === "#" && atLine) { j = eol(i); role = "bi"; }
      if (j < 0) for (const [a, b, raw] of sp.str || []) {
        if (!src.startsWith(a, i)) continue;
        let m = i + a.length;
        while (m < n) {
          if (!raw && sp.esc && src[m] === "\\") { m += 2; continue; }
          if (src.startsWith(b, m)) { if (raw && b.length === 1 && src[m + 1] === b) { m += 2; continue; } m += b.length; break; }
          if (b.length === 1 && !sp.ml && !raw && src[m] === "\n") break;
          m++;
        }
        j = Math.min(m, n); role = "st";
        if (sp.keys && src[skipSp(j)] === sp.keys) role = "tb";
        break;
      }
      if (j < 0 && sp.tags && c === "<" && (isA(nx) || nx === "/" || nx === "!" || nx === "?")) { j = i + 1; while (j < n && (id1(src[j]) || "/!?:-.".includes(src[j]))) j++; role = "tb"; }
      if (j < 0 && sp.deco && c === "@" && isA(nx)) { j = i + 1; while (j < n && (id1(src[j]) || src[j] === ".")) j++; role = "bi"; }
      if (j < 0 && (isD(c) || (c === "." && isD(nx))) && !(i > 0 && id1(prev))) { j = i + 1; while (j < n && (isA(src[j]) || isD(src[j]) || src[j] === ".")) j++; role = "nu"; }
      if (j < 0 && (id0(c) || ((KW.size || LI.size) && "@!$~".includes(c) && id0(nx)))) {
        j = i + 1; while (j < n && id1(src[j])) j++;
        const w = src.slice(i, j), lw = sp.ci ? w.toLowerCase() : w;
        role = KW.has(lw) ? "k" : TY.has(lw) ? "tb" : LI.has(lw) ? "nu" : FN.has(lw) ? "ca" : null;
        if (role === null && sp.keys) { const t = skipSp(j); if (src[t] === sp.keys && src[t + 1] !== sp.keys) role = "tb"; }
        if (role === null && sp.attrs && src[skipSp(j)] === "=") role = "ca";
        if (role === null && sp.calls !== false && src[skipSp(j)] === "(") role = "ca";
        if (role === null && !id0(c)) { j = i + 1; }  // 기호로 시작했는데 예약어가 아니면 기호 한 글자만
      }
      if (j < 0) { j = i + 1; role = null; }
      push(src.slice(i, j), role); i = j;
    }
    return out;
  }
  function highlight(src, el) {
    const name = langOf(el);
    if (name === "sql") return hlSQL(src);
    if (!LANGS) return name === "python" ? hlPython(src) : [[src, null]];
    return name === "plain" ? [[src, null]] : hlGeneric(src, name);
  }
  /** code 요소 → 표시 줄 [{n, focus, gap, runs:[[글자, 역할]]}] - start·focus·show(구간 발췌, 사이는 ⋮) */
  function codeLines(el) {
    const src = String(el.text == null ? "" : el.text);
    const toks = highlight(src, el);
    const lines = [[]];
    for (const [v, role] of toks) {
      v.split("\n").forEach((p, i) => { if (i) lines.push([]); if (p) lines[lines.length - 1].push([p, role]); });
    }
    const start = parseInt(el.start || 1, 10) || 1, focus = new Set((el.focus || []).map(Number)), show = el.show && el.show.length ? el.show : null;
    const out = []; let gap = false;
    lines.forEach((ln, i) => {
      const n = start + i;
      if (show && !show.some(([a, b]) => n >= a && n <= b)) {
        if (!gap) { out.push({ n: "⋮", focus: false, gap: true, runs: [] }); gap = true; }
        return;
      }
      gap = false;
      out.push({ n: String(n), focus: focus.has(n), gap: false, runs: ln });
    });
    return out;
  }
  const CODE_GUTTER_W = 48, CODE_PAD_Y = 12;
  function codeStyle(role) {
    const cs = (T && T.codeStyle) || {};
    return cs[role || "ink"] || cs.ink || ["code-ink", false, false];
  }

  // ---------- plan 강조 ----------
  const HL_ROLE = { warn: ["primary-container", "primary"], ok: ["lab-container", "lab"] };
  function planRuns(line) {
    const rx = /\[\[(?:(warn|ok):)?(.+?)\]\]/g; const out = []; let pos = 0, m;
    while ((m = rx.exec(line))) {
      if (m.index > pos) out.push([line.slice(pos, m.index), null]);
      out.push([m[2], m[1] || "warn"]);
      pos = rx.lastIndex;
    }
    if (pos < line.length) out.push([line.slice(pos), null]);
    return out;
  }

  // ---------- 표 격자 (common.py table_grid 와 같은 규칙) ----------
  const NUM = /^[\s*+\-]?[\d,.\s%:]*\d[\d,.\s%KMG]*$/;
  /** 행 높이(px) - rowH(행별 비율, colW 처럼)를 h 에 맞춰 나눈다. 없으면 고르게, 모자란 행은 준 값의 평균, 0 이하·숫자 아님이 있으면 무시. */
  function rowHeights(el, n) {
    const N = Math.max(1, n);
    let r = Array.isArray(el.rowH) ? el.rowH.map(Number) : [];
    if (!r.length || r.some((v) => !(v > 0))) return Array.from({ length: n }, () => el.h / N);
    const avg = r.reduce((a, b) => a + b, 0) / r.length;
    r = r.slice(0, n); while (r.length < n) r.push(avg);
    const tot = r.reduce((a, b) => a + b, 0);
    return r.map((v) => (el.h * v) / tot);
  }
  /** 셀 좌표 - null·'*'·'' = 그 줄 전체, 그 밖은 정수. 못 읽으면 false (common._tidx 와 같다) */
  const tidx = (v) => (v == null || v === "*" || v === "" ? null : isNaN(parseInt(v, 10)) ? false : parseInt(v, 10));
  /** 셀별 채움·테두리(0.22.12) - common.table_cell_styles 와 같은 규칙. cellFill [[행,열,색]] · gridLines(격자) · borders [[행,열,변,색?,두께?]] → cells[r][c].fill / .bd = {T|B|L|R: [색, 두께]} */
  function tableCellStyles(el, cells, nc) {
    const nr = cells.length;
    for (const f of el.cellFill || []) {
      if (!Array.isArray(f) || f.length < 3) continue;
      const r = tidx(f[0]), c = tidx(f[1]), col = f[2];
      if (r === false || c === false || !col) continue;
      for (let i = 0; i < nr; i++) { if (r != null && i !== r) continue; for (let j = 0; j < nc; j++) if (c == null || j === c) cells[i][j].fill = col; }
    }
    const rule = el.rule || "surface-container-high", bds = new Map();
    if (el.gridLines) for (let i = 0; i < nr; i++) for (let j = 0; j < nc; j++) { const d = { B: [rule, 1], R: [rule, 1] }; if (i === 0) d.T = [rule, 1]; if (j === 0) d.L = [rule, 1]; bds.set(`${i},${j}`, d); }
    for (const b of el.borders || []) {
      if (!Array.isArray(b) || b.length < 3) continue;
      const r = tidx(b[0]), c = tidx(b[1]), sides = String(b[2] || "").toUpperCase(), col = b.length > 3 && b[3] ? b[3] : rule, w = b.length > 4 && b[4] != null && b[4] !== "" && !isNaN(+b[4]) ? +b[4] : 1;
      if (r === false || c === false || !sides) continue;
      for (let i = 0; i < nr; i++) { if (r != null && i !== r) continue; for (let j = 0; j < nc; j++) { if (c != null && j !== c) continue; const k = `${i},${j}`; const d = bds.get(k) || {}; for (const sd of sides) if ("TBLR".includes(sd)) d[sd] = [col, w]; bds.set(k, d); } }
    }
    for (const [k, d] of bds) { if (Object.keys(d).length) { const [i, j] = k.split(",").map(Number); cells[i][j].bd = d; } }
  }
  function tableGrid(el) {
    const isPlan = el.type === "plan-table";
    let cols, n, tw, cw = 0, body = [];
    if (isPlan) {
      cols = el.columns || []; body = el.rows || []; n = body.length + 1;
      const hasNote = body.some((r) => r.note);
      cw = hasNote ? (el.calloutW || 0) : 0;
      tw = el.w - (cw ? cw + 24 : 0);
    } else {
      const rows = el.rows || []; cols = rows[0] || []; n = rows.length; tw = el.w;
    }
    const nc = Math.max(1, cols.length);
    let ratios = (el.colW && el.colW.length ? el.colW.slice() : []);
    while (ratios.length < nc) ratios.push(1);
    ratios = ratios.slice(0, nc);
    const tot = ratios.reduce((a, b) => a + b, 0) || 1;
    const colW = ratios.map((r) => (tw * r) / tot);
    const rowH = rowHeights(el, n);
    const even = rowH.every((v) => v === rowH[0]);
    const rowTop = (k) => (even ? rowH[0] * k : rowH.slice(0, k).reduce((a, b) => a + b, 0));
    const headFill = el.headFill || "surface-container-high", headColor = el.headColor || "on-surface";
    // 본문 셀 글꼴 = colFont[열](비어 있으면 el.font, 둘 다 없으면 body) - 값은 body·heading·mono("code" 도 mono). 머리 행은 항상 본문
    const fonts = el.colFont || [], aligns = el.align || [], defFont = fontRole(el.font);
    const cells = [];
    if (isPlan) {
      const op = el.opCol == null ? 1 : el.opCol;
      const auto = [];
      for (let j = 0; j < nc; j++) {
        const vals = body.map((r) => (r.cells && j < r.cells.length ? String(r.cells[j]) : ""));
        auto.push(j !== op && vals.some((v) => v.trim()) && vals.every((v) => !v.trim() || NUM.test(v)) ? "right" : "left");
      }
      cells.push(cols.map((c, j) => ({ text: String(c), fill: headFill, color: headColor, bold: true, font: "body", align: aligns[j] || auto[j] })));
      for (const r of body) {
        const rc = (r.cells || []).slice(); while (rc.length < nc) rc.push("");
        const hl = r.hl || {};
        const row = [];
        for (let j = 0; j < nc; j++) {
          let t = String(rc[j]);
          if (j === op) t = "  ".repeat(parseInt(r.depth || 0, 10)) + t;
          const role = hl[j] || hl[String(j)];
          const [fill, col] = HL_ROLE[role] || [null, el.color || "on-surface"];
          row.push({ text: t, fill, color: col, bold: !!role, font: "mono", align: aligns[j] || auto[j] });
        }
        cells.push(row);
      }
    } else {
      (el.rows || []).forEach((r, i) => {
        const rc = r.slice(); while (rc.length < nc) rc.push("");
        const hd = (el.header !== false) && i === 0;
        cells.push(rc.slice(0, nc).map((t, j) => ({
          text: String(t), fill: hd ? headFill : null, color: hd ? headColor : (el.color || "on-surface"), bold: hd,
          align: aligns[j] || "left", font: hd ? "body" : fontRole(fonts[j] || defFont),
        })));
      });
    }
    tableCellStyles(el, cells, nc);
    const callouts = [];
    if (isPlan && cw) {
      const size = el.size || 15;
      body.forEach((r, i) => {
        if (!r.note) return;
        const roles = Object.values(r.hl || {});
        const role = roles.includes("warn") ? "warn" : roles.includes("ok") ? "ok" : null;
        let [fill, col] = HL_ROLE[role] || ["surface-container", "on-surface-variant"];
        if (role && T && T.colors["on-" + fill]) col = "on-" + fill;
        const lines = String(r.note).split("\n").length;
        const bh = Math.max(rowH[i + 1] - 8, lines * size * 1.5 + 12);
        const cy = el.y + rowTop(i + 1) + rowH[i + 1] / 2;
        callouts.push({ row: i + 1, text: r.note, fill, color: col, line: role ? HL_ROLE[role][1] : "outline-variant",
          x: el.x + tw + 24, y: cy - bh / 2, w: cw, h: bh, cy, tx: el.x + tw });
      });
    }
    return { x: el.x, y: el.y, tw, colW, rowH, cells, rule: el.rule || "surface-container-high", size: el.size || 16, callouts };
  }

  /** 글 앞의 번호("1. " "1) " "(1) " "a. " "A) " "①" "가. " + 공백)를 떼어 {label, scheme, start, rest} - 없으면 null (common.bullet_num 과 같은 규칙).
      두 자리까지(2024. 같은 연도 제외), "1.5배" 처럼 공백 없는 것 제외. scheme 은 PPTX 자동 번호 종류(없으면 글자 그대로). */
  const NUM_PATTERNS = [
    [/^\s*(\d{1,2})([.)])\s+(?=\S)/, "arabic"], [/^\s*\((\d{1,2})\)\s+(?=\S)/, "arabicBoth"],
    [/^\s*([a-z])([.)])\s+(?=\S)/, "alphaLc"], [/^\s*([A-Z])([.)])\s+(?=\S)/, "alphaUc"],
    [/^\s*([\u2460-\u2473])\s*(?=\S)/, "circle"], [/^\s*([\uac00-\ud7a3])([.)])\s+(?=\S)/, "korean"],
    [/^\s*([*+\-\u2013\u2014])\s+(?=\S)/, "symbol"],  // * + - – — + 공백 → 그 기호가 글머리
    [/^\s*([·‧∙ㆍ•●○◦◎■□▪▫◆◇◈▲△▼▽▶►▸▹▷→➜➤➢✓✔✗✘✦✧★☆※◉⦁])\s*(?=\S)/, "symbol"],  // 글머리 기호(공백 없어도)
  ];
  const BULLET_HEAVY = "●■◆▲▼★◉";  // 글자 크기의 60% 로 그리는 굵은 기호(● 과 같게) - 나머지 기호·번호는 100%
  function bulletNum(text) {
    const s = String(text == null ? "" : text);
    for (const [rx, kind] of NUM_PATTERNS) {
      const m = rx.exec(s); if (!m) continue;
      const rest = s.slice(m[0].length);
      if (kind === "arabic") { const n = +m[1]; return { label: `${n}${m[2]}`, scheme: m[2] === "." ? "arabicPeriod" : "arabicParenR", start: n, rest }; }
      if (kind === "arabicBoth") { const n = +m[1]; return { label: `(${n})`, scheme: "arabicParenBoth", start: n, rest }; }
      if (kind === "alphaLc" || kind === "alphaUc") return { label: `${m[1]}${m[2]}`, scheme: (kind === "alphaLc" ? "alphaLc" : "alphaUc") + (m[2] === "." ? "Period" : "ParenR"), start: m[1].toLowerCase().charCodeAt(0) - 96, rest };
      if (kind === "circle") return { label: m[1], scheme: "circleNumDbPlain", start: m[1].charCodeAt(0) - 0x2460 + 1, rest };
      if (kind === "symbol") return { label: m[1], scheme: null, start: 0, kind: "symbol", rest };  // 글머리 기호 - 글머리 색으로
      return { label: `${m[1]}${m[2]}`, scheme: null, start: 1, rest };
    }
    return null;
  }
  /** 번호 글머리의 내어쓰기 폭 px - 번호가 ●보다 넓으면 넓힌다 (common.num_hang 과 같은 식) */
  const numHang = (label, size, hang) => label.length <= 1 ? hang : Math.max(hang, Math.ceil(size * ([...label].reduce((a, ch) => a + (ch.charCodeAt(0) > 0x2E80 ? 1.0 : 0.55), 0) + 0.25)));  // 한글·한자 같은 전각 글자는 1em

  /** 글머리 종류(marker · subMarker) - 번호 매기기 종류 → PPTX 자동 번호 type (common.NUM_STYLES 와 같다) */
  const NUM_STYLES = { "1.": "arabicPeriod", "1)": "arabicParenR", "(1)": "arabicParenBoth", "a.": "alphaLcPeriod", "a)": "alphaLcParenR", "A.": "alphaUcPeriod", "A)": "alphaUcParenR", "①": "circleNumDbPlain", "가.": null };
  const KOR_NUM = "가나다라마바사아자차카타파하";
  function numLabel(style, n) {
    if (!(style in NUM_STYLES)) return null;
    if (style === "①") return n >= 1 && n <= 20 ? String.fromCharCode(0x2460 + n - 1) : `(${n})`;
    if (style === "가.") return (n >= 1 && n <= KOR_NUM.length ? KOR_NUM[n - 1] : String(n)) + ".";
    const a = n >= 1 && n <= 26 ? String.fromCharCode(96 + n) : String(n);
    return { "1.": `${n}.`, "1)": `${n})`, "(1)": `(${n})`, "a.": `${a}.`, "a)": `${a})`, "A.": `${a.toUpperCase()}.`, "A)": `${a.toUpperCase()})` }[style];
  }
  /** 요소의 marker(수준 0)/subMarker(수준 1) → 행의 번호·기호 {label, scheme, start, kind} 또는 null(기본 ●/–). common.marker_num 과 같은 규칙 */
  function markerNum(style, lvl, n) {
    if (!style || style === (lvl === 0 ? "●" : "–")) return null;
    if (style in NUM_STYLES) return { label: numLabel(style, n), scheme: NUM_STYLES[style], start: n, kind: "auto" };
    if (style === "none") return { label: "", scheme: null, start: 0, kind: "none" };
    return { label: String(style), scheme: null, start: 0, kind: "symbol" };
  }

  /** bullets → [[글자, 수준, 뒤 간격 px, 번호]] (common.bullet_rows 와 같은 규칙). 번호 = 글 앞의 "1. " 같은 번호를 자동 감지한 {label, scheme, start}(글자에서는 뗀다) 또는 null - autoNum: false 면 감지하지 않는다.
      spread = 균등 간격: 행 높이(줄 수 = 줄바꿈 수 + 1, 자동 줄바꿈은 세지 않음)를 뺀 나머지를 행 사이에 고르게 - 마지막 행 뒤는 0 */
  function bulletRows(el) {
    const gap = el.gap == null ? 14 : el.gap, sub = el.subGap == null ? 6 : el.subGap, rows = [], auto = el.autoNum !== false, cnt = [0, 0];
    const row = (text, lvl, after) => {
      if (lvl === 0) { cnt[0] += 1; cnt[1] = 0; } else cnt[1] += 1;  // 수준별 순번(번호 매기기용) - 하위는 상위 항목마다 다시 1부터
      let num = auto ? bulletNum(text) : null;  // 글 앞에 적은 번호·기호가 먼저
      if (num) { text = num.rest; delete num.rest; } else num = markerNum(lvl === 0 ? el.marker : el.subMarker, lvl, cnt[lvl]);  // 요소에 고른 글머리 종류
      return [text, lvl, after, num];
    };
    for (let it of el.items || []) {
      if (typeof it === "string") it = { text: it };
      const subs = it.sub || [];
      rows.push(row(it.text || "", 0, subs.length ? sub : gap));
      subs.forEach((s, k) => rows.push(row(s, 1, k < subs.length - 1 ? sub : gap)));
    }
    if (el.spread && rows.length > 1) {
      const size = +el.size || 20, subSz = +el.subSize || 17, lh = +(el.lineHeight || 1.55), [pt, , pb] = padOf(el);
      const used = rows.reduce((a, [t, lvl]) => a + (lvl ? subSz : size) * lh * String(t == null ? "" : t).split("\n").length, 0);
      const g = Math.max(0, (+el.h - pt - pb - used) / (rows.length - 1));
      rows.forEach((r, i) => { r[2] = i < rows.length - 1 ? g : 0; });
    }
    return rows;
  }

  // ---------- HTML 조각 ----------
  function spanRuns(text, page, base, bold) {
    return runs(text, page).map(([t, st]) => {
      if (!t) return "";
      const c = st.color ? color(st.color) : base;
      const b = st.bold !== undefined ? st.bold : bold;
      const deco = [st.underline || st.link ? "underline" : "", st.strike ? "line-through" : ""].filter(Boolean).join(" ");
      // 위·아래 첨자: 글자 65%, 기준선에서 ±(PowerPoint baseline 30000/-25000 과 같은 모양) - 줄 높이는 바꾸지 않는다(line-height 0)
      const pos = st.sup ? ";font-size:65%;line-height:0;position:relative;top:-0.45em" : st.sub ? ";font-size:65%;line-height:0;position:relative;top:0.2em" : "";
      const bg = st.bg ? `;background:${color(st.bg)};border-radius:2px;padding:0 .08em;margin:0 -.08em` : "";
      const span = `<span style="color:${c};font-weight:${b ? 700 : 400}${st.italic ? ";font-style:italic" : ""}${deco ? `;text-decoration:${deco}` : ""}${pos}${bg}">${esc(t)}</span>`;
      return st.link ? `<a class="rs-a" data-link="${esc(String(st.link))}" style="color:inherit;text-decoration:none">${span}</a>` : span;  // href 없음 - 발표 화면의 [data-link] 처리기(followLink)가 이동(요소 링크와 같다), 편집 중 눌러도 안 움직인다
    }).join("");
  }
  function padOf(el, d) {
    let p = el.pad == null ? (d || 0) : el.pad;
    if (typeof p === "number") return [p, p, p, p];
    p = p.slice(); while (p.length < 4) p.push(0);
    return p;
  }
  const JUST = { top: "flex-start", middle: "center", bottom: "flex-end" };
  const HJUST = { left: "flex-start", center: "center", right: "flex-end" };

  /** 글자 단락들(한 줄 = 한 단락) */
  function textLines(el, page, o) {
    const size = +el.size || 20, lh = +(el.lineHeight || o.lh), L = size * lh;
    const base = color(el.color || "on-surface"), bold = el.bold !== undefined ? !!el.bold : !!o.bold;
    const align = el.align || o.align, wrap = el.wrap !== undefined ? el.wrap : o.wrap;
    const sh = shift(el.font, size, lh);
    return String(el.text == null ? "" : el.text).split("\n").map((line) => {
      const inner = spanRuns(line, page, base, bold) || "&#8203;";
      return wrap
        ? `<div class="rs-p" style="position:relative;top:${sh}px;line-height:${L}px;height:auto;min-height:${L}px;text-align:${align}">${inner}</div>`
        : `<div class="rs-p rs-nw" style="position:relative;top:${sh}px;line-height:${L}px;height:${L}px;justify-content:${HJUST[align] || "flex-start"}">${inner}</div>`;
    }).join("");
  }

  function boxStyle(el, kind) {
    const w = el.w, h = el.h;
    let r = 0;
    if (kind === "ellipse") r = "50%";
    else if (kind === "pill") r = Math.min(w, h) / 2 + "px";
    else r = radius(el.radius, w, h) + "px";
    let s = `border-radius:${r};`;
    if (el.fill) s += `background:${fillCss(el.fill)};`;
    if (el.stroke && !dashArray(el.strokeDash, 1)) s += `box-shadow:inset 0 0 0 ${el.strokeWidth || 1}px ${color(el.stroke)};`;  // 점선·파선은 strokeDashSvg 가 그린다
    return s;
  }
  /** 선 모양 dash(solid·dash·dot) → SVG stroke-dasharray (선 요소 lineSvg 와 같은 간격, PPTX prstDash dash·sysDot) */
  const dashArray = (d, w) => (d === "dot" ? `${w} ${w}` : d && d !== "solid" ? `${w * 4} ${w * 3}` : "");
  /** 도형(rect·pill·ellipse·글 상자) 테두리의 점선·파선 - box-shadow 는 점선을 못 그려 안쪽 선 자리에 SVG 로 */
  function strokeDashSvg(el, shape) {
    const sw = +el.strokeWidth || 1, da = dashArray(el.strokeDash, sw);
    if (!el.stroke || !da) return "";
    const w = +el.w, h = +el.h, sc = color(el.stroke), hf = sw / 2;
    const g = shape === "ellipse" ? `<ellipse cx="${R2(w / 2)}" cy="${R2(h / 2)}" rx="${R2(w / 2 - hf)}" ry="${R2(h / 2 - hf)}"`
      : `<rect x="${R2(hf)}" y="${R2(hf)}" width="${R2(w - sw)}" height="${R2(h - sw)}" rx="${R2(Math.max(0, (shape === "pill" ? Math.min(w, h) / 2 : radius(el.radius, w, h)) - hf))}"`;
    return `<svg class="rs-svg" style="left:0;top:0" width="${w}" height="${h}">${g} fill="none" stroke="${sc}" stroke-width="${sw}" stroke-dasharray="${da}"/></svg>`;
  }

  /** PowerPoint 기본 도형의 글 영역 들여넣기 - 타원 = 폭·높이 × 0.14645, 둥근 사각형·칩 = 반경 × 0.29289 (export_pptx.text_pad 와 같다). 글 상자(fill 없는 text)는 0 */
  function shapeInset(el, shape, isShape) {
    if (!isShape) return [0, 0];
    const w = +el.w, h = +el.h;
    if (shape === "ellipse") return [w * 0.14645, h * 0.14645];
    const r = shape === "pill" ? Math.min(w, h) / 2 : radius(el.radius, w, h);
    return [0.29289 * r, 0.29289 * r];
  }
  function elBox(el, page) {
    const t = el.type, pad0 = padOf(el);
    const shape = t === "text" ? "rect" : t;
    const isShape = t !== "text" || el.fill;
    const [ix, iy] = shapeInset(el, shape, isShape);  // 편집기 글 영역 = PowerPoint 와 같게(여백은 max(pad, 들여넣기)) - 줄바꿈이 같아진다
    const [pt, pr, pb, pl] = [Math.max(pad0[0], iy), Math.max(pad0[1], ix), Math.max(pad0[2], iy), Math.max(pad0[3], ix)];
    const valign = el.valign || (t === "text" ? "top" : "middle");
    const o = { lh: (t === "text" ? 1.4 : 1.2), bold: t === "pill", align: t === "pill" || t === "ellipse" ? "center" : "left", wrap: t === "text" || t === "rect" };
    const hasText = el.text != null && String(el.text) !== "";
    return `<div class="rs-box" style="${isShape ? boxStyle(el, shape) : ""}padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:${JUST[valign]};font-family:${font(el.font)};font-size:${+el.size || 20}px">${hasText ? textLines(el, page, o) : ""}</div>${isShape ? strokeDashSvg(el, shape) : ""}`;
  }


  // ---------- 도형(shape) - PowerPoint 기본 도형. 경로·글 영역(rect)은 프리셋의 기본 조정값 기하와 같게(export_pptx 는 prstGeom 으로 내보낸다).
  //   path(w,h,ss) → SVG 경로(d) · rect → 글 상자 [l,t,r,b] · faces → 면(정육면체 윗면·옆면: 밝게/어둡게) · over → 상자 아래로 더 그릴 비율(설명선 꼬리)
  const R2 = (v) => Math.round(v * 100) / 100;
  const P = (...pts) => "M" + pts.map(([x, y]) => `${R2(x)} ${R2(y)}`).join("L") + "Z";
  const starPts = (w, h, n, inner) => {  // 별 - PowerPoint 처럼 꼭짓점이 상자에 닿게(hf·vf), 안쪽 반지름 = inner × 바깥
    const cx = w / 2, cy = h * 0.5528, rx = w / 2, ry = h * 0.5528, out = [];
    for (let i = 0; i < n * 2; i++) { const a = -Math.PI / 2 + (i * Math.PI) / n, r = i % 2 ? inner : 1; out.push([cx + rx * r * Math.cos(a), cy + ry * r * Math.sin(a)]); }
    return out;
  };
  const SHAPES = {
    triangle: { ko: "삼각형", path: (w, h) => P([w / 2, 0], [w, h], [0, h]), rect: (w, h) => [w / 4, h / 2, (3 * w) / 4, h] },
    rtTriangle: { ko: "직각 삼각형", path: (w, h) => P([0, 0], [w, h], [0, h]), rect: (w, h) => [w / 12, h / 2, (7 * w) / 12, (11 * h) / 12] },
    diamond: { ko: "마름모", path: (w, h) => P([w / 2, 0], [w, h / 2], [w / 2, h], [0, h / 2]), rect: (w, h) => [w / 4, h / 4, (3 * w) / 4, (3 * h) / 4] },
    parallelogram: { ko: "평행사변형", path: (w, h, ss) => { const x = ss / 4; return P([x, 0], [w, 0], [w - x, h], [0, h]); }, rect: (w, h, ss) => [ss / 8, 0, w - ss / 8, h] },
    trapezoid: { ko: "사다리꼴", path: (w, h, ss) => { const x = ss / 4; return P([0, h], [x, 0], [w - x, 0], [w, h]); }, rect: (w, h, ss) => [ss / 8, 0, w - ss / 8, h] },
    pentagon: { ko: "오각형", path: (w, h) => P([w / 2, 0], [w, 0.382 * h], [0.809 * w, h], [0.191 * w, h], [0, 0.382 * h]), rect: (w, h) => [0.191 * w, 0.382 * h, 0.809 * w, h] },
    hexagon: { ko: "육각형", path: (w, h, ss) => { const x = ss / 4; return P([x, 0], [w - x, 0], [w, h / 2], [w - x, h], [x, h], [0, h / 2]); }, rect: (w, h, ss) => [ss / 8, 0, w - ss / 8, h] },
    octagon: { ko: "팔각형", path: (w, h, ss) => { const x = ss * 0.29289; return P([x, 0], [w - x, 0], [w, x], [w, h - x], [w - x, h], [x, h], [0, h - x], [0, x]); }, rect: (w, h, ss) => { const x = ss * 0.29289 / 2; return [x, x, w - x, h - x]; } },
    rightArrow: { ko: "오른쪽 화살표", path: (w, h, ss) => { const dx = ss / 2, y = h / 4; return P([0, y], [w - dx, y], [w - dx, 0], [w, h / 2], [w - dx, h], [w - dx, h - y], [0, h - y]); }, rect: (w, h, ss) => [0, h / 4, w - ss / 4, (3 * h) / 4] },
    leftArrow: { ko: "왼쪽 화살표", path: (w, h, ss) => { const dx = ss / 2, y = h / 4; return P([w, y], [dx, y], [dx, 0], [0, h / 2], [dx, h], [dx, h - y], [w, h - y]); }, rect: (w, h, ss) => [ss / 4, h / 4, w, (3 * h) / 4] },
    upArrow: { ko: "위쪽 화살표", path: (w, h, ss) => { const dy = ss / 2, x = w / 4; return P([x, h], [x, dy], [0, dy], [w / 2, 0], [w, dy], [w - x, dy], [w - x, h]); }, rect: (w, h, ss) => [w / 4, ss / 4, (3 * w) / 4, h] },
    downArrow: { ko: "아래쪽 화살표", path: (w, h, ss) => { const dy = ss / 2, x = w / 4; return P([x, 0], [x, h - dy], [0, h - dy], [w / 2, h], [w, h - dy], [w - x, h - dy], [w - x, 0]); }, rect: (w, h, ss) => [w / 4, 0, (3 * w) / 4, h - ss / 4] },
    leftRightArrow: { ko: "좌우 화살표", path: (w, h, ss) => { const dx = ss / 2, y = h / 4; return P([0, h / 2], [dx, 0], [dx, y], [w - dx, y], [w - dx, 0], [w, h / 2], [w - dx, h], [w - dx, h - y], [dx, h - y], [dx, h]); }, rect: (w, h, ss) => [ss / 4, h / 4, w - ss / 4, (3 * h) / 4] },
    chevron: { ko: "갈매기형 수장", path: (w, h, ss) => { const x = Math.min(ss / 2, w / 2); return P([0, 0], [w - x, 0], [w, h / 2], [w - x, h], [0, h], [x, h / 2]); }, rect: (w, h, ss) => { const x = Math.min(ss / 2, w / 2); return [x, 0, w - x / 2, h]; } },
    homePlate: { ko: "오각 화살표", path: (w, h, ss) => { const x = Math.min(ss / 2, w); return P([0, 0], [w - x, 0], [w, h / 2], [w - x, h], [0, h]); }, rect: (w, h, ss) => [0, 0, w - Math.min(ss / 2, w) / 2, h] },
    star5: { ko: "별", path: (w, h) => P(...starPts(w, h, 5, 0.382)), rect: (w, h) => [0.318 * w, 0.382 * h, 0.682 * w, 0.764 * h] },
    plus: { ko: "십자형", path: (w, h, ss) => { const x = ss / 4; return P([x, 0], [w - x, 0], [w - x, x], [w, x], [w, h - x], [w - x, h - x], [w - x, h], [x, h], [x, h - x], [0, h - x], [0, x], [x, x]); }, rect: (w, h, ss) => { const x = ss / 4; return [x, x, w - x, h - x]; } },
    callout: { ko: "사각형 설명선", over: 0.14, path: (w, h) => P([0, 0], [w, 0], [w, h], [0.4167 * w, h], [0.2917 * w, 1.125 * h], [0.1667 * w, h], [0, h]), rect: (w, h) => [0, 0, w, h] },
    roundCallout: { ko: "모서리가 둥근 설명선", over: 0.14, path: (w, h, ss) => { const r = ss / 6; return `M${R2(r)} 0L${R2(w - r)} 0A${R2(r)} ${R2(r)} 0 0 1 ${R2(w)} ${R2(r)}L${R2(w)} ${R2(h - r)}A${R2(r)} ${R2(r)} 0 0 1 ${R2(w - r)} ${R2(h)}L${R2(0.4167 * w)} ${R2(h)}L${R2(0.2917 * w)} ${R2(1.125 * h)}L${R2(Math.max(r, 0.1667 * w))} ${R2(h)}L${R2(r)} ${R2(h)}A${R2(r)} ${R2(r)} 0 0 1 0 ${R2(h - r)}L0 ${R2(r)}A${R2(r)} ${R2(r)} 0 0 1 ${R2(r)} 0Z`; }, rect: (w, h, ss) => { const r = ss / 6 * 0.29; return [r, r, w - r, h - r]; } },
    can: { ko: "원기둥", path: (w, h, ss) => { const y = ss / 8, rx = w / 2; return `M0 ${R2(y)}L0 ${R2(h - y)}A${R2(rx)} ${R2(y)} 0 0 0 ${R2(w)} ${R2(h - y)}L${R2(w)} ${R2(y)}A${R2(rx)} ${R2(y)} 0 0 0 0 ${R2(y)}Z`; }, rect: (w, h, ss) => [0, ss / 4, w, h - ss / 8],
      faces: (w, h, ss) => { const y = ss / 8, rx = w / 2; return [{ d: `M0 ${R2(y)}A${R2(rx)} ${R2(y)} 0 1 1 ${R2(w)} ${R2(y)}A${R2(rx)} ${R2(y)} 0 1 1 0 ${R2(y)}Z`, tint: "rgba(255,255,255,.3)" }]; } },
    cube: { ko: "정육면체", path: (w, h, ss) => { const y = ss / 4; return P([0, y], [y, 0], [w, 0], [w, h - y], [w - y, h], [0, h]); }, rect: (w, h, ss) => { const y = ss / 4; return [0, y, w - y, h]; },
      faces: (w, h, ss) => { const y = ss / 4; return [{ d: P([0, y], [y, 0], [w, 0], [w - y, y]), tint: "rgba(255,255,255,.3)" }, { d: P([w - y, y], [w, 0], [w, h - y], [w - y, h]), tint: "rgba(0,0,0,.2)" }]; } },
  };
  const shapePath = (name, w, h) => (SHAPES[name] || SHAPES.diamond).path(w, h, Math.min(w, h));
  const shapeNames = () => Object.keys(SHAPES).map((k) => [k, SHAPES[k].ko]);

  function elShape(el, page) {
    const w = +el.w, h = +el.h, ss = Math.min(w, h), g = SHAPES[el.shape] || SHAPES.diamond;
    const d = g.path(w, h, ss), [l, t, r, b] = g.rect(w, h, ss), over = g.over || 0;
    const fill = el.fill ? fillCss(el.fill) : "transparent", faces = g.faces ? g.faces(w, h, ss) : [];
    let html = `<div class="rs-shp" style="position:absolute;left:0;top:0;width:${w}px;height:${R2(h * (1 + over))}px;background:${fill};clip-path:path('${d}')"></div>`;
    for (const f of faces) html += `<div class="rs-shp" style="position:absolute;left:0;top:0;width:${w}px;height:${h}px;background:linear-gradient(${f.tint},${f.tint}),${fill};clip-path:path('${f.d}')"></div>`;
    if (el.stroke) {
      const sw = +el.strokeWidth || 1, sc = color(el.stroke), da = dashArray(el.strokeDash, sw), dd = da ? ` stroke-dasharray="${da}"` : "";
      html += `<svg style="position:absolute;left:0;top:0;overflow:visible" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><path d="${d}" fill="none" stroke="${sc}" stroke-width="${sw}" stroke-linejoin="round"${dd}/>${faces.map((f) => `<path d="${f.d}" fill="none" stroke="${sc}" stroke-width="${sw}" stroke-linejoin="round"${dd}/>`).join("")}</svg>`;
    }
    const hasText = el.text != null && String(el.text) !== "";
    if (hasText) {
      const [pt, pr, pb, pl] = padOf(el);
      html += `<div class="rs-box" style="position:absolute;left:${R2(l)}px;top:${R2(t)}px;width:${R2(r - l)}px;height:${R2(b - t)}px;right:auto;bottom:auto;padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:${JUST[el.valign || "middle"]};font-family:${font(el.font)};font-size:${+el.size || 20}px">${textLines(el, page, { lh: 1.2, bold: false, align: "center", wrap: true })}</div>`;
    }
    return html;
  }


  // ---------- 차트(chart) - 데이터에서 SVG 로 그린다. PPTX 는 PowerPoint 차트(export_pptx.do_chart, 같은 색·범례·눈금 규칙 - 그림은 PowerPoint 가 그린다)
  const CHART_PALETTE = ["primary", "#4C7A9E", "#E0A458", "#7BAE7F", "#B57BA6", "#8C8C8C", "#D97B66", "#5FA8A3"];
  const chartColor = (el, i) => color((el.colors && el.colors[i]) || CHART_PALETTE[i % CHART_PALETTE.length]) || "#888";
  /** 축 눈금 - 최댓값을 1·2·5 단위로 올려 5칸 안팎 (common.chart_axis 와 같은 규칙) */
  function chartAxis(max, min) {
    const hi = Math.max(max, 0), lo = Math.min(min, 0), span = Math.max(hi - lo, 1e-9);
    const raw = span / 5, p = Math.pow(10, Math.floor(Math.log10(raw))), step = [1, 2, 5, 10].map((k) => k * p).find((s) => span / s <= 5.5) || 10 * p;
    return { max: Math.ceil(hi / step) * step, min: Math.floor(lo / step) * step, step };
  }
  const chartNum = (v) => (Math.abs(v) >= 1000 ? v.toLocaleString("en-US") : String(Math.round(v * 100) / 100));
  /** 숫자 형식(numFmt, Excel 식 - PPTX 는 같은 문자열을 formatCode 로 쓴다): "#,##0" "0" "0.0" "0%" "#,##0.0" + 앞뒤 글자('#,##0"억"' 또는 '#,##0억'). 없으면 chartNum */
  function chartFmt(v, fmt) {
    if (v == null) return "";
    if (!fmt) return chartNum(v);
    const m = /^([^#0]*)([#,0]*)(?:\.(0+))?(%?)([^#0]*)$/.exec(String(fmt).replace(/"/g, ""));
    if (!m) return chartNum(v);
    const [, pre, intp, dec, pct, suf] = m;
    const x = pct ? v * 100 : v, d = dec ? dec.length : 0;
    let s = Math.abs(x).toFixed(d);
    if (intp.includes(",")) { const [a, b] = s.split("."); s = a.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (b ? "." + b : ""); }
    return (x < 0 ? "-" : "") + pre + s + pct + suf;
  }
  function chartData(el) {
    const cats = (el.categories || []).map((c) => String(c == null ? "" : c));
    const series = (el.series || []).map((s, i) => ({ name: String((s && s.name) || `계열 ${i + 1}`), values: ((s && s.values) || []).map((v) => (v == null || v === "" || isNaN(+v) ? null : +v)) }));
    const n = Math.max(cats.length, ...series.map((s) => s.values.length), 0);
    while (cats.length < n) cats.push("");
    series.forEach((s) => { while (s.values.length < n) s.values.push(null); });
    return { cats, series, n };
  }
  const CHART_H = new Set(["bar", "stackedBar", "stackedBar100"]), CHART_STK = new Set(["stackedColumn", "stackedBar", "stackedColumn100", "stackedBar100"]), CHART_PCT = new Set(["stackedColumn100", "stackedBar100"]);
  /** 콤보(combo) - 선으로 그릴 계열 번호 집합. lineSeries = 계열 이름 또는 0부터 번호(배열 또는 하나), 기본 = 마지막 계열. export_pptx._combo_lines 와 같은 규칙 */
  function comboLines(el, series) {
    if ((el.chart || "column") !== "combo" || series.length < 2) return new Set();
    const raw = el.lineSeries == null || el.lineSeries === "" ? null : Array.isArray(el.lineSeries) ? el.lineSeries : [el.lineSeries];
    if (!raw) return new Set([series.length - 1]);
    const out = new Set();
    for (const v of raw) {
      const byName = series.findIndex((s) => s.name === String(v));
      if (byName >= 0) out.add(byName);
      else if (/^\d+$/.test(String(v).trim()) && +v < series.length) out.add(+v);
    }
    return out.size && out.size < series.length ? out : new Set([series.length - 1]);  // 없거나 전부 선이면 마지막만 선
  }
  function elChart(el, page) {
    const w = +el.w, h = +el.h, kind = el.chart || "column", size = +el.size || 14, fam = font("body"), ink = color("on-surface"), ink2 = color("on-surface-variant"), rule = color("outline-variant") || "#ddd";
    const { cats, series, n } = chartData(el);
    const pie = kind === "pie" || kind === "doughnut";
    const legend = el.legend === undefined ? (series.length > 1 || pie ? "bottom" : "none") : el.legend;
    const labels = !!el.labels, stacked = CHART_STK.has(kind), pct = CHART_PCT.has(kind), horiz = CHART_H.has(kind), lines = comboLines(el, series);
    const sec = lines.size > 0 && !!el.secondaryAxis;  // 보조 축(오른쪽) - 콤보의 선 계열
    const afmt = el.numFmt || (pct ? "0%" : ""), lfmt = el.numFmt || "", afmt2 = el.numFmt2 || "", lfmt2 = el.numFmt2 || "";  // 축 눈금·값 표시 형식(보조 축은 2)
    let out = "", top = 6, bottom = h - 6, left = 6, right = w - 6;
    const T = (x, y, t, o = {}) => `<text x="${R2(x)}" y="${R2(y)}" font-family="${fam}" font-size="${o.size || size}" fill="${o.fill || ink}" text-anchor="${o.anchor || "start"}" dominant-baseline="${o.base || "middle"}"${o.bold ? ' font-weight="700"' : ""}${o.rot ? ` transform="rotate(${o.rot} ${R2(x)} ${R2(y)})"` : ""}>${esc(t)}</text>`;
    if (el.title) { out += T(w / 2, top + size * 0.8, String(el.title), { anchor: "middle", size: size * 1.15, bold: true }); top += size * 1.9; }
    const mark = (x, y, c, i) => (lines.has(i) ? `<line x1="${R2(x)}" y1="${R2(y)}" x2="${R2(x + size * 0.8)}" y2="${R2(y)}" stroke="${c}" stroke-width="2.5"/><circle cx="${R2(x + size * 0.4)}" cy="${R2(y)}" r="3" fill="${c}"/>` : `<rect x="${R2(x)}" y="${R2(y - size * 0.4)}" width="${R2(size * 0.8)}" height="${R2(size * 0.8)}" rx="2" fill="${c}"/>`);
    if (legend === "bottom" && series.length) {  // 범례 - 아래 한 줄(원형은 범주, 콤보의 선 계열은 선 표식)
      const items = pie ? cats.map((c, i) => [c, chartColor(el, i)]) : series.map((s, i) => [s.name, chartColor(el, i)]);
      const est = items.reduce((a, [t]) => a + t.length * size * 0.62 + size * 1.6 + 12, 0); let x = Math.max(left, (w - est) / 2); const y = bottom - size * 0.6;
      items.forEach(([t, c], i) => { out += mark(x, y, c, pie ? -1 : i); out += T(x + size * 1.1, y, t, { size: size * 0.9, fill: ink2 }); x += t.length * size * 0.62 + size * 1.6 + 12; });
      bottom -= size * 1.8;
    } else if (legend === "right" && series.length) {
      const items = pie ? cats.map((c, i) => [c, chartColor(el, i)]) : series.map((s, i) => [s.name, chartColor(el, i)]);
      const lw = Math.max(...items.map(([t]) => t.length * size * 0.62)) + size * 1.6 + 8; const x = right - lw; let y = top + size;
      items.forEach(([t, c], i) => { out += mark(x, y, c, pie ? -1 : i); out += T(x + size * 1.1, y, t, { size: size * 0.9, fill: ink2 }); y += size * 1.5; });
      right = x - 8;
    }
    if (pie) {
      const vals = (series[0] ? series[0].values : []).map((v) => Math.max(0, v || 0)), tot = vals.reduce((a, b) => a + b, 0) || 1;
      const cx = (left + right) / 2, cy = (top + bottom) / 2, r = Math.max(8, Math.min(right - left, bottom - top) / 2 - (labels ? size * 1.2 : 4)), r0 = kind === "doughnut" ? r * 0.55 : 0;
      let a0 = -Math.PI / 2;
      vals.forEach((v, i) => {
        const a1 = a0 + (v / tot) * Math.PI * 2, big = a1 - a0 > Math.PI ? 1 : 0;
        const P = (a, rr) => [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
        const [x0, y0] = P(a0, r), [x1, y1] = P(a1, r);
        let d = `M${R2(x0)} ${R2(y0)}A${R2(r)} ${R2(r)} 0 ${big} 1 ${R2(x1)} ${R2(y1)}`;
        if (r0) { const [u1, v1] = P(a1, r0), [u0, v0] = P(a0, r0); d += `L${R2(u1)} ${R2(v1)}A${R2(r0)} ${R2(r0)} 0 ${big} 0 ${R2(u0)} ${R2(v0)}Z`; } else d += `L${R2(cx)} ${R2(cy)}Z`;
        if (v > 0) out += `<path d="${d}" fill="${chartColor(el, i)}" stroke="#fff" stroke-width="1"/>`;
        if (labels && v > 0) { const am = (a0 + a1) / 2, [lx, ly] = P(am, r0 ? (r + r0) / 2 : r * 0.62); out += T(lx, ly, `${Math.round((v / tot) * 100)}%`, { anchor: "middle", size: size * 0.9, fill: "#fff", bold: true }); }
        a0 = a1;
      });
      return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="position:absolute;left:0;top:0">${out}</svg>`;
    }
    // 세로/가로 막대 · 누적(100%) · 선 · 영역 · 콤보 - 축과 눈금. 100% 누적은 범주 합 대비 비율(축 0~100%, 값 표시는 원래 값)
    const barIdx = series.map((_, i) => i).filter((i) => !lines.has(i)), lineIdx = [...lines].sort((a, b) => a - b), primIdx = sec ? barIdx : series.map((_, i) => i);
    const sums = cats.map((_, i) => barIdx.reduce((a, si) => a + Math.max(0, series[si].values[i] || 0), 0));
    const val = (si, i) => { const v = series[si].values[i]; return v == null ? null : pct ? (sums[i] ? Math.max(0, v) / sums[i] : 0) : v; };
    const allv = stacked ? (pct ? [1] : sums) : primIdx.flatMap((si) => series[si].values.filter((v) => v != null));
    const ax = pct ? { max: 1, min: 0, step: 0.2 } : chartAxis(Math.max(0, ...allv), Math.min(0, ...allv));
    if (!pct && el.axisMax != null && +el.axisMax > 0) ax.max = +el.axisMax;
    const lv2 = lineIdx.flatMap((si) => series[si].values.filter((v) => v != null)), ax2 = sec ? chartAxis(Math.max(0, ...lv2), Math.min(0, ...lv2)) : null;
    if (ax2 && el.axisMax2 != null && +el.axisMax2 > 0) ax2.max = +el.axisMax2;
    const tk = (a) => { const t = []; for (let v = a.min; v <= a.max + 1e-9; v += a.step) t.push(Math.round(v * 1e6) / 1e6); return t; };
    const ticks = tk(ax), ticks2 = ax2 ? tk(ax2) : [];
    const lab = (v) => chartFmt(v, afmt), lab2 = (v) => chartFmt(v, afmt2), catH = size * 1.5;
    const axW = Math.max(...ticks.map((v) => lab(v).length)) * size * 0.6 + 8, ax2W = ax2 ? Math.max(...ticks2.map((v) => lab2(v).length)) * size * 0.6 + 8 : 0;
    const tl = el.axisTitle ? size * 1.3 : 0, tc = el.catTitle ? size * 1.3 : 0, tr = ax2 && el.axisTitle2 ? size * 1.3 : 0;  // 축 제목 자리(값 축 = 왼쪽 세로, 범주 축 = 아래, 보조 축 = 오른쪽 세로; 가로 막대는 값·범주 자리가 바뀜)
    const px0 = (horiz ? left + Math.max(...cats.map((c) => c.length)) * size * 0.62 + 8 : left + axW) + (horiz ? tc : tl), py1 = bottom - catH - (horiz ? tl : tc), px1 = right - 4 - ax2W - tr, py0 = top + 4;
    const pw = px1 - px0, ph = py1 - py0;
    const vx = (v) => px0 + ((v - ax.min) / (ax.max - ax.min || 1)) * pw, vy = (v) => py1 - ((v - ax.min) / (ax.max - ax.min || 1)) * ph;
    const vy2 = ax2 ? (v) => py1 - ((v - ax2.min) / (ax2.max - ax2.min || 1)) * ph : vy;
    ticks.forEach((v) => {
      if (horiz) { const x = vx(v); if (el.grid !== false) out += `<line x1="${R2(x)}" y1="${R2(py0)}" x2="${R2(x)}" y2="${R2(py1)}" stroke="${rule}" stroke-width="1"/>`; out += T(x, py1 + catH / 2, lab(v), { anchor: "middle", size: size * 0.85, fill: ink2 }); }
      else { const y = vy(v); if (el.grid !== false) out += `<line x1="${R2(px0)}" y1="${R2(y)}" x2="${R2(px1)}" y2="${R2(y)}" stroke="${rule}" stroke-width="1"/>`; out += T(px0 - 6, y, lab(v), { anchor: "end", size: size * 0.85, fill: ink2 }); }
    });
    if (ax2) { ticks2.forEach((v) => { out += T(px1 + 6, vy2(v), lab2(v), { size: size * 0.85, fill: ink2 }); }); out += `<line x1="${R2(px1)}" y1="${R2(py0)}" x2="${R2(px1)}" y2="${R2(py1)}" stroke="${ink2}" stroke-width="1"/>`; }
    out += horiz ? `<line x1="${R2(px0)}" y1="${R2(py0)}" x2="${R2(px0)}" y2="${R2(py1)}" stroke="${ink2}" stroke-width="1"/>` : `<line x1="${R2(px0)}" y1="${R2(vy(0))}" x2="${R2(px1)}" y2="${R2(vy(0))}" stroke="${ink2}" stroke-width="1"/>`;
    const tO = { anchor: "middle", size: size * 0.9, fill: ink2 };
    if (el.axisTitle) out += horiz ? T((px0 + px1) / 2, bottom - size * 0.55, String(el.axisTitle), tO) : T(left + size * 0.6, (py0 + py1) / 2, String(el.axisTitle), { ...tO, rot: -90 });
    if (el.catTitle) out += horiz ? T(left + size * 0.6, (py0 + py1) / 2, String(el.catTitle), { ...tO, rot: -90 }) : T((px0 + px1) / 2, bottom - size * 0.55, String(el.catTitle), tO);
    if (ax2 && el.axisTitle2) out += T(right - size * 0.6, (py0 + py1) / 2, String(el.axisTitle2), { ...tO, rot: 90 });
    const slot = horiz ? ph / Math.max(1, n) : pw / Math.max(1, n), gw = slot / 1.8, nb = Math.max(1, barIdx.length);  // gap 80% (PowerPoint gapWidth 80 과 같다)
    cats.forEach((c, i) => { if (horiz) out += T(px0 - 6, py1 - slot * (i + 0.5), c, { anchor: "end", size: size * 0.9 }); else out += T(px0 + slot * (i + 0.5), py1 + catH / 2, c, { anchor: "middle", size: size * 0.9 }); });
    const drawLine = (si, yfn, fmt, area) => {
      const s = series[si], pts = s.values.map((v, i) => (v == null ? null : [px0 + slot * (i + 0.5), yfn(v)]));
      const segs = pts.filter(Boolean), c = chartColor(el, si);
      if (area && segs.length) out += `<path d="M${R2(segs[0][0])} ${R2(yfn(0))}${segs.map((p) => `L${R2(p[0])} ${R2(p[1])}`).join("")}L${R2(segs[segs.length - 1][0])} ${R2(yfn(0))}Z" fill="${c}" fill-opacity=".3"/>`;
      out += `<polyline points="${segs.map((p) => `${R2(p[0])},${R2(p[1])}`).join(" ")}" fill="none" stroke="${c}" stroke-width="2.5" stroke-linejoin="round"/>`;
      segs.forEach((p) => { out += `<circle cx="${R2(p[0])}" cy="${R2(p[1])}" r="3.5" fill="${c}"/>`; });
      if (labels) pts.forEach((p, i) => { if (p) out += T(p[0], p[1] - size * 0.8, chartFmt(s.values[i], fmt), { anchor: "middle", size: size * 0.85, fill: ink2 }); });
    };
    if (kind === "line" || kind === "area") series.forEach((_, si) => drawLine(si, vy, lfmt, kind === "area"));
    else {
      cats.forEach((_, i) => {
        let acc = 0;
        barIdx.forEach((si, bi) => {
          const v = val(si, i); if (v == null) return;
          const c = chartColor(el, si), vl = chartFmt(series[si].values[i], lfmt);
          if (stacked && horiz) {
            const v0 = acc, v1 = acc + Math.max(0, v); acc = v1;
            const y = py1 - slot * (i + 0.5) - gw / 2, x0 = vx(v0), x1 = vx(v1);
            out += `<rect x="${R2(x0)}" y="${R2(y)}" width="${R2(Math.max(0, x1 - x0))}" height="${R2(gw)}" fill="${c}"/>`;
            if (labels && v) out += T((x0 + x1) / 2, y + gw / 2, vl, { anchor: "middle", size: size * 0.85, fill: "#fff", bold: true });
          } else if (stacked) {
            const v0 = acc, v1 = acc + Math.max(0, v); acc = v1;
            const x = px0 + slot * (i + 0.5) - gw / 2, y = vy(v1), hh = vy(v0) - vy(v1);
            out += `<rect x="${R2(x)}" y="${R2(y)}" width="${R2(gw)}" height="${R2(Math.max(0, hh))}" fill="${c}"/>`;
            if (labels && v) out += T(x + gw / 2, y + hh / 2, vl, { anchor: "middle", size: size * 0.85, fill: "#fff", bold: true });
          } else if (horiz) {
            const bw = gw / nb, y = py1 - slot * (i + 0.5) - gw / 2 + bw * bi, x0 = vx(Math.min(0, v)), x1 = vx(Math.max(0, v));
            out += `<rect x="${R2(x0)}" y="${R2(y)}" width="${R2(x1 - x0)}" height="${R2(bw)}" fill="${c}"/>`;
            if (labels) out += T(x1 + 4, y + bw / 2, vl, { size: size * 0.85, fill: ink2 });
          } else {
            const bw = gw / nb, x = px0 + slot * (i + 0.5) - gw / 2 + bw * bi, y0 = vy(Math.max(0, v)), y1 = vy(Math.min(0, v));
            out += `<rect x="${R2(x)}" y="${R2(y0)}" width="${R2(bw)}" height="${R2(y1 - y0)}" fill="${c}"/>`;
            if (labels) out += T(x + bw / 2, y0 - size * 0.7, vl, { anchor: "middle", size: size * 0.85, fill: ink2 });
          }
        });
      });
      lineIdx.forEach((si) => drawLine(si, sec ? vy2 : vy, sec ? lfmt2 : lfmt, false));
    }
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="position:absolute;left:0;top:0">${out}</svg>`;
  }

  // ---------- 아이콘(icon) - 내장 아이콘(24×24 채움꼴, 층: fill = 아이콘 색 / on = 대비색). PPTX 는 custGeom 자유형(export_pptx.do_icon)
  const ICONS = {"check": {"ko": "확인 표시", "layers": [["M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z", "fill"]]}, "close": {"ko": "닫기 ×", "layers": [["M19 6.4L17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z", "fill"]]}, "plus": {"ko": "더하기", "layers": [["M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6z", "fill"]]}, "minus": {"ko": "빼기", "layers": [["M19 13H5v-2h14z", "fill"]]}, "arrowRight": {"ko": "오른쪽 화살", "layers": [["M4 11v2h12l-5.5 5.5 1.4 1.4L20 12l-8.1-7.9-1.4 1.4L16 11z", "fill"]]}, "arrowLeft": {"ko": "왼쪽 화살", "layers": [["M20 11v2H8l5.5 5.5-1.4 1.4L4 12l8.1-7.9 1.4 1.4L8 11z", "fill"]]}, "arrowUp": {"ko": "위 화살", "layers": [["M13 20h-2V8l-5.5 5.5-1.4-1.4L12 4l7.9 8.1-1.4 1.4L13 8z", "fill"]]}, "arrowDown": {"ko": "아래 화살", "layers": [["M11 4h2v12l5.5-5.5 1.4 1.4L12 20l-7.9-8.1 1.4-1.4L11 16z", "fill"]]}, "chevronRight": {"ko": "오른쪽 꺾쇠", "layers": [["M8.6 4.6L7.2 6l6 6-6 6 1.4 1.4L16 12z", "fill"]]}, "chevronLeft": {"ko": "왼쪽 꺾쇠", "layers": [["M15.4 4.6L16.8 6l-6 6 6 6-1.4 1.4L8 12z", "fill"]]}, "play": {"ko": "재생", "layers": [["M7 4l13 8-13 8z", "fill"]]}, "pause": {"ko": "일시정지", "layers": [["M6 4h4v16H6zM14 4h4v16h-4z", "fill"]]}, "stop": {"ko": "정지", "layers": [["M5 5h14v14H5z", "fill"]]}, "info": {"ko": "정보", "layers": [["M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z", "fill"], ["M11 10h2v7h-2zM11 7h2v2h-2z", "on"]]}, "checkCircle": {"ko": "확인 원", "layers": [["M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z", "fill"], ["M10 15.6l-3.3-3.3 1.4-1.4 1.9 1.9 5.5-5.5 1.4 1.4z", "on"]]}, "xCircle": {"ko": "취소 원", "layers": [["M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z", "fill"], ["M15.5 7.1L12 10.6 8.5 7.1 7.1 8.5l3.5 3.5-3.5 3.5 1.4 1.4 3.5-3.5 3.5 3.5 1.4-1.4-3.5-3.5 3.5-3.5z", "on"]]}, "warning": {"ko": "경고", "layers": [["M12 2L1 21h22z", "fill"], ["M11 9h2v6h-2zM11 16.5h2v2h-2z", "on"]]}, "question": {"ko": "물음표", "layers": [["M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z", "fill"], ["M11 16.5h2v2h-2zM12 6c-2.2 0-4 1.6-4 3.8h2c0-1 .9-1.8 2-1.8s2 .7 2 1.6c0 .8-.5 1.1-1.4 1.7-1 .7-1.6 1.3-1.6 2.9v.8h2v-.6c0-.9.3-1.2 1.2-1.8 1-.7 1.8-1.4 1.8-3 0-2.1-1.7-3.6-4-3.6z", "on"]]}, "home": {"ko": "집", "layers": [["M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3z", "fill"]]}, "user": {"ko": "사람", "layers": [["M16.5 8C16.5 10.48535 14.48535 12.5 12 12.5C9.51465 12.5 7.5 10.48535 7.5 8C7.5 5.51465 9.51465 3.5 12 3.5C14.48535 3.5 16.5 5.51465 16.5 8Z", "fill"], ["M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z", "fill"]]}, "users": {"ko": "사람들", "layers": [["M12.8 8C12.8 10.09874 11.09874 11.8 9 11.8C6.901260000000001 11.8 5.2 10.09874 5.2 8C5.2 5.901260000000001 6.901260000000001 4.2 9 4.2C11.09874 4.2 12.8 5.901260000000001 12.8 8Z", "fill"], ["M2 20c0-3.8 3-6.2 7-6.2s7 2.4 7 6.2z", "fill"], ["M20 8.5C20 10.1569 18.6569 11.5 17 11.5C15.3431 11.5 14 10.1569 14 8.5C14 6.8431 15.3431 5.5 17 5.5C18.6569 5.5 20 6.8431 20 8.5Z", "fill"], ["M15.5 13.2c3.7.2 6.5 2.5 6.5 6.8h-4.2c0-2.7-.8-4.9-2.3-6.8z", "fill"]]}, "mail": {"ko": "메일", "layers": [["M4 5L20 5C21.1046 5 22 5.8954 22 7L22 17C22 18.1046 21.1046 19 20 19L4 19C2.8954 19 2 18.1046 2 17L2 7C2 5.8954 2.8954 5 4 5Z", "fill"], ["M4 7.5l8 5.5 8-5.5V9.8l-8 5.4-8-5.4z", "on"]]}, "doc": {"ko": "문서", "layers": [["M6 2h8l5 5v15H6z", "fill"], ["M8 12h8v1.6H8zM8 15.5h8v1.6H8zM13 3.5V8h4.5z", "on"]]}, "folder": {"ko": "폴더", "layers": [["M2 5h7l2 2h11v13H2z", "fill"]]}, "calendar": {"ko": "달력", "layers": [["M5 4L19 4C20.1046 4 21 4.8954 21 6L21 19C21 20.1046 20.1046 21 19 21L5 21C3.8954 21 3 20.1046 3 19L3 6C3 4.8954 3.8954 4 5 4Z", "fill"], ["M3 9h18v1.5H3z", "on"], ["M7 2h2v4H7zM15 2h2v4h-2z", "fill"], ["M7 12h3v3H7zM11.5 12h3v3h-3zM16 12h3v3h-3z", "on"]]}, "clock": {"ko": "시계", "layers": [["M22 12C22 17.523 17.523 22 12 22C6.477 22 2 17.523 2 12C2 6.477 6.477 2 12 2C17.523 2 22 6.477 22 12Z", "fill"], ["M11 6h2v6.6l4 2.4-1 1.7-5-3z", "on"]]}, "pin": {"ko": "위치", "layers": [["M12 2c-4 0-7 3-7 7 0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z", "fill"], ["M14.6 9C14.6 10.43598 13.43598 11.6 12 11.6C10.56402 11.6 9.4 10.43598 9.4 9C9.4 7.56402 10.56402 6.4 12 6.4C13.43598 6.4 14.6 7.56402 14.6 9Z", "on"]]}, "chat": {"ko": "말풍선", "layers": [["M3 4h18v12H8l-5 4z", "fill"]]}, "heart": {"ko": "하트", "layers": [["M12 21s-8-5.6-8-11.2C4 7 6 5 8.5 5c1.6 0 2.8.8 3.5 2 .7-1.2 1.9-2 3.5-2C18 5 20 7 20 9.8 20 15.4 12 21 12 21z", "fill"]]}, "bolt": {"ko": "번개", "layers": [["M13 2L4 14h6l-1 8 9-12h-6z", "fill"]]}, "search": {"ko": "찾기", "layers": [["M17 10C17 13.8661 13.8661 17 10 17C6.1339 17 3 13.8661 3 10C3 6.1339 6.1339 3 10 3C13.8661 3 17 6.1339 17 10Z", "fill"], ["M14.6 10C14.6 12.54058 12.54058 14.6 10 14.6C7.45942 14.6 5.4 12.54058 5.4 10C5.4 7.45942 7.45942 5.4 10 5.4C12.54058 5.4 14.6 7.45942 14.6 10Z", "on"], ["M14.5 15.9l1.4-1.4L21 19.6 19.6 21z", "fill"]]}, "star": {"ko": "별", "layers": [["M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z", "fill"]]}, "flag": {"ko": "깃발", "layers": [["M5 2h2v20H5zM7 3h12l-3 4 3 4H7z", "fill"]]}, "gear": {"ko": "톱니", "layers": [["M12 2l1.8 2.6 3-.9 .9 3L20.3 8.5 19 11.3l1.3 2.8-2.6 1.8.3 3.1-3.1.3-1.5 2.7L12 20.5l-1.4 1.5-1.5-2.7-3.1-.3.3-3.1-2.6-1.8L5 11.3 3.7 8.5l2.6-1.8-.9-3 3 .9z", "fill"], ["M15.2 11.5C15.2 13.26736 13.76736 14.7 12 14.7C10.23264 14.7 8.8 13.26736 8.8 11.5C8.8 9.73264 10.23264 8.3 12 8.3C13.76736 8.3 15.2 9.73264 15.2 11.5Z", "on"]]}};
  const iconNames = () => Object.keys(ICONS).map((k) => [k, ICONS[k].ko]);
  function elIcon(el) {
    const ic = ICONS[el.icon] || ICONS.check, w = +el.w, h = +el.h, s = Math.min(w, h), ox = (w - s) / 2, oy = (h - s) / 2;
    const c1 = color(el.fill || "primary"), c2 = color(el.color || "white");
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="position:absolute;left:0;top:0"><g transform="translate(${R2(ox)} ${R2(oy)}) scale(${R2(s / 24)})">${ic.layers.map(([d, tone]) => `<path d="${d}" fill="${tone === "on" ? c2 : c1}"/>`).join("")}</g></svg>`;
  }

  /** 그림 프레임 효과(effect · effectLevel 1~3, 원본 파일은 그대로) - export_pptx.apply_effect 와 같은 수치. softEdge 는 가장자리 흐림(px), round 는 모서리 반경, frame 은 흰 테두리 두께, glow 는 빛 번짐 */
  const EFFECT_PX = { softEdge: [6, 12, 24], round: [8, 16, 32], frame: [3, 6, 10], glow: [8, 16, 24] };
  function effectPx(el) { const lv = Math.max(1, Math.min(3, +el.effectLevel || 2)); return (EFFECT_PX[el.effect] || [0, 0, 0])[lv - 1]; }
  function effectCss(el) {
    const e = el.effect, px = effectPx(el);
    if (e === "softEdge") return `-webkit-mask-image:linear-gradient(to right,transparent,#000 ${px}px,#000 calc(100% - ${px}px),transparent),linear-gradient(to bottom,transparent,#000 ${px}px,#000 calc(100% - ${px}px),transparent);-webkit-mask-composite:source-in;mask-image:linear-gradient(to right,transparent,#000 ${px}px,#000 calc(100% - ${px}px),transparent),linear-gradient(to bottom,transparent,#000 ${px}px,#000 calc(100% - ${px}px),transparent);mask-composite:intersect;`;
    if (e === "round") return `border-radius:${px}px;overflow:hidden;`;
    if (e === "circle") return "border-radius:50%;overflow:hidden;";
    if (e === "frame") return `border:${+el.frameWidth || px}px solid ${el.frameColor ? color(el.frameColor) : "#fff"};box-sizing:border-box;box-shadow:0 2px 6px rgba(0,0,0,.3);overflow:hidden;`;  // 액자 - 두께 frameWidth(기본 = 수준)·색 frameColor(기본 흰색)
    if (e === "glow") { const c = color(el.effectColor || "primary"); return `box-shadow:0 0 ${px}px ${Math.round(px / 2)}px ${c}99;`; }
    return "";
  }
  let LAZY = true;  // 그림을 보일 때 읽기(loading=lazy) - 그림 많은 덱에서 썸네일 수십 장이 한꺼번에 내려받다 끊기지 않게. 인쇄·발표자 보기는 setLazy(false)
  function setLazy(v) { LAZY = !!v; }
  const IMG_ATTR = () => (LAZY ? ' loading="lazy" decoding="async"' : ' decoding="sync"');
  function elImage(el) {
    const src = `${esc(root.RENDER_BASE || "/")}${esc(el.src)}`, op = el.opacity != null && el.opacity !== 1 ? `opacity:${+el.opacity};` : "";
    const c = Array.isArray(el.crop) && el.crop.some((v) => v) ? el.crop.map((v) => Math.max(0, Math.min(0.95, +v || 0))) : null;
    const fx = effectCss(el);
    const wrap = (inner) => (fx ? `<div class="rs-fx" style="position:absolute;inset:0;${fx}">${inner}</div>` : inner);
    const alt = esc(el.alt || "");
    if (!c) return wrap(`<img class="rs-img" src="${src}" alt="${alt}" draggable="false"${IMG_ATTR()}${op ? ` style="${op}"` : ""}>`);
    const [l, t, r, b] = c, W = el.w / Math.max(0.05, 1 - l - r), H = el.h / Math.max(0.05, 1 - t - b);  // 자르기 - 원본을 키워 상자 밖은 감춘다(PowerPoint crop 과 같은 뜻, 비율은 상자 비율)
    return wrap(`<div style="position:absolute;inset:0;overflow:hidden;${op}"><img class="rs-img" src="${src}" alt="${alt}" draggable="false"${IMG_ATTR()} style="position:absolute;left:${R2(-l * W)}px;top:${R2(-t * H)}px;width:${R2(W)}px;height:${R2(H)}px;object-fit:fill"></div>`);
  }

  /** 선·화살표: 요소 상자(x,y,w,h) 기준 SVG. 화살 머리 = 선 두께 × 5 (PPT 'lg') */
  function lineSvg(el, ox, oy) {
    const x1 = el.x1 - ox, y1 = el.y1 - oy, x2 = el.x2 - ox, y2 = el.y2 - oy;
    const w = +el.width || 2, c = color(el.color || "on-surface");
    const head = el.head || (el.type === "arrow" ? "end" : "none");
    const hl = w * 5, hw = w * 5;
    const len = Math.hypot(x2 - x1, y2 - y1) || 1, ux = (x2 - x1) / len, uy = (y2 - y1) / len;
    let ax = x1, ay = y1, bx = x2, by = y2, polys = "";
    const tri = (tx, ty, dx, dy) => {
      const bx0 = tx - dx * hl, by0 = ty - dy * hl, nx = -dy * hw / 2, ny = dx * hw / 2;
      return `<polygon points="${tx},${ty} ${bx0 + nx},${by0 + ny} ${bx0 - nx},${by0 - ny}" fill="${c}"/>`;
    };
    if (head === "end" || head === "both") { bx = x2 - ux * hl * 0.9; by = y2 - uy * hl * 0.9; polys += tri(x2, y2, ux, uy); }
    if (head === "start" || head === "both") { ax = x1 + ux * hl * 0.9; ay = y1 + uy * hl * 0.9; polys += tri(x1, y1, -ux, -uy); }
    const dash = el.dash === "dot" ? `stroke-dasharray="${w} ${w}"` : el.dash && el.dash !== "solid" ? `stroke-dasharray="${w * 4} ${w * 3}"` : "";
    return `<line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="${c}" stroke-width="${w}" ${dash}/>${polys}`;
  }
  function elLine(el) {
    const m = 20; // 화살 머리가 상자 밖으로 나가도 보이게
    return `<svg class="rs-svg" style="left:${-m}px;top:${-m}px" width="${Math.max(1, el.w) + 2 * m}" height="${Math.max(1, el.h) + 2 * m}">${lineSvg(el, el.x - m, el.y - m)}</svg>`;
  }

  /** 곡선(꺾은선 근사): points = 요소 상자 기준 [[x,y],…], head = end/none - 화살 머리는 마지막 선분 방향 */
  function elCurve(el) {
    const m = 20, pts = el.points || [], w = +el.width || 2, c = color(el.color || "on-surface");
    const dash = el.dash === "dot" ? `stroke-dasharray="${w} ${w}"` : el.dash && el.dash !== "solid" ? `stroke-dasharray="${w * 4} ${w * 3}"` : "";
    if (pts.length < 2) return "";
    const P = pts.map(([x, y]) => [x + m, y + m]);
    let polys = "";
    if ((el.head || "end") !== "none") {
      const [ax, ay] = P[P.length - 2], [bx, by] = P[P.length - 1];
      const len = Math.hypot(bx - ax, by - ay) || 1, ux = (bx - ax) / len, uy = (by - ay) / len, hl = w * 5, hw = w * 5;
      const b0x = bx - ux * hl, b0y = by - uy * hl, nx = -uy * hw / 2, ny = ux * hw / 2;
      polys = `<polygon points="${bx},${by} ${b0x + nx},${b0y + ny} ${b0x - nx},${b0y - ny}" fill="${c}"/>`;
      P[P.length - 1] = [bx - ux * hl * 0.9, by - uy * hl * 0.9];
    }
    return `<svg class="rs-svg" style="left:${-m}px;top:${-m}px" width="${Math.max(1, el.w) + 2 * m}" height="${Math.max(1, el.h) + 2 * m}">` +
      `<polyline points="${P.map((q) => q.join(",")).join(" ")}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linejoin="round" ${dash}/>${polys}</svg>`;
  }

  /** 표 merge → {span: Map("r,c" → [rows, cols]), skip: Set("r,c")} (common.table_merges 와 같은 규칙) */
  function tableMerges(el, nr, nc) {
    const span = new Map(), skip = new Set();
    for (const m of el.merge || []) {
      if (!Array.isArray(m) || m.length < 4) continue;
      let [r, c, rs, cs] = m.map((v) => parseInt(v, 10));
      if ([r, c, rs, cs].some((v) => isNaN(v)) || r < 0 || c < 0 || r >= nr || c >= nc) continue;
      rs = Math.max(1, Math.min(rs, nr - r)); cs = Math.max(1, Math.min(cs, nc - c));
      if (rs === 1 && cs === 1) continue;
      const cells = []; for (let i = 0; i < rs; i++) for (let j = 0; j < cs; j++) cells.push(`${r + i},${c + j}`);
      if (cells.some((k) => skip.has(k) || span.has(k))) continue;
      span.set(`${r},${c}`, [rs, cs]); cells.slice(1).forEach((k) => skip.add(k));
    }
    return { span, skip };
  }
  function elTable(el, page) {
    const g = tableGrid(el);
    let html = "", y = 0;
    const size = g.size, mg = el.type === "plan-table" ? { span: new Map(), skip: new Set() } : tableMerges(el, g.cells.length, g.colW.length);
    g.cells.forEach((row, i) => {
      let x = 0;
      const isHead = i === 0 && (el.type === "plan-table" || el.header !== false);
      row.forEach((c, j) => {
        const sp = mg.span.get(`${i},${j}`);
        if (mg.skip.has(`${i},${j}`)) { x += g.colW[j]; return; }  // 병합에 덮인 셀
        const w = sp ? g.colW.slice(j, j + sp[1]).reduce((a, b) => a + b, 0) : g.colW[j], h = sp ? g.rowH.slice(i, i + sp[0]).reduce((a, b) => a + b, 0) : g.rowH[i];
        const bd = c.bd || {}, SIDE = { T: "top", B: "bottom", L: "left", R: "right" };
        const side = (k, dflt) => { const v = bd[k] || dflt; return v ? `border-${SIDE[k]}:${v[1]}px solid ${color(v[0])};` : ""; };
        const bb = side("T") + side("B", isHead ? null : [g.rule, 1]) + side("L") + side("R");  // 기본 = 본문 행 아래 선(rule), 셀별 bd 가 덮어씀(export_pptx.do_table 과 같다)
        html += `<div class="rs-cell" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;${c.fill ? `background:${color(c.fill)};` : ""}${bb}justify-content:${HJUST[c.align] || "flex-start"};font-family:${font(c.font)};font-size:${size}px;line-height:${size * 1.4}px;text-align:${c.align}">` +
          `<div class="rs-ct" style="position:relative;top:${shift(c.font, size, 1.4)}px">${spanRuns(c.text, page, color(c.color), c.bold) || "&#8203;"}</div></div>`;
        x += g.colW[j];
      });
      y += g.rowH[i];
    });
    for (const co of g.callouts) {
      const lx = co.tx + 4 - el.x, ly = co.cy - el.y;
      html += `<div class="rs-cell" style="left:${lx}px;top:${ly - 1}px;width:${co.x - co.tx - 4}px;height:2px;background:${color(co.line)}"></div>`;
      const box = { type: "text", x: 0, y: 0, w: co.w, h: co.h, text: co.text, size, lineHeight: 1.5, fill: co.fill, color: co.color, radius: "r-s", pad: [6, 14, 6, 14], valign: "middle" };
      html += `<div class="rs-cell" style="left:${co.x - el.x}px;top:${co.y - el.y}px;width:${co.w}px;height:${co.h}px;display:block">${elBox(box, page)}</div>`;
    }
    return html;
  }

  /** plan: 실행계획 원문(고정폭) + [[강조]] - 배경·글자색·굵게만(폭 불변) */
  function elPlan(el) {
    const size = +el.size || 14, lh = +(el.lineHeight || 1.5), L = size * lh;
    const [pt, pr, pb, pl] = padOf(el, [16, 18, 16, 18]);
    const base = color(el.color || "on-surface");
    const body = String(el.text || "").split("\n").map((ln) => planRuns(ln).map(([t, role]) => {
      if (!role) return `<span style="color:${base}">${esc(t)}</span>`;
      const [bg, fg] = HL_ROLE[role] || HL_ROLE.warn;
      return `<span style="background:${color(bg)};color:${color(fg)};font-weight:700">${esc(t)}</span>`;
    }).join("")).map((h) => `<div class="rs-p rs-pre" style="position:relative;top:${shift("mono", size, lh)}px;line-height:${L}px;height:${L}px">${h || "&#8203;"}</div>`).join("");
    return `<div class="rs-box" style="${boxStyle({ ...el, fill: el.fill || "surface-container", radius: el.radius == null ? "r-m" : el.radius }, "rect")}padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:flex-start;font-family:${font("mono")};font-size:${size}px">${body}</div>`;
  }

  /** code: DBeaver 라이트 - 줄 번호 여백 + 강조 줄 면 + 역할별 색·굵게·기울임 (export_pptx.do_code 와 같은 배치) */
  function elCode(el) {
    const size = +el.size || 15, lh = +(el.lineHeight || 1.6), L = size * lh, gw = el.lineNo === false ? 0 : el.gutterW || CODE_GUTTER_W;
    const r = radius(el.radius == null ? "r-m" : el.radius, el.w, el.h);
    const lines = codeLines(el);
    let html = `<div class="rs-code" style="border-radius:${r}px;background:${color("code-bg")};box-shadow:inset 0 0 0 1px ${color("surface-container-high")};font-family:${font("mono")};font-size:${size}px">`;
    if (gw) html += `<div class="rs-abs" style="left:0;top:0;width:${gw}px;height:100%;background:${color("code-gutter-bg")}"></div>`;
    const sh = shift("mono", size, lh);
    lines.forEach((ln, i) => {
      const top = CODE_PAD_Y + i * L;
      if (ln.focus) html += `<div class="rs-abs" style="left:${gw}px;top:${top}px;right:0;height:${L}px;background:${color("code-focus")}"></div>`;
      const gc = ln.focus ? color("on-surface") : color("code-gutter");
      if (gw) html += `<div class="rs-abs rs-pre" style="left:0;top:${top + sh}px;width:${gw - 12}px;height:${L}px;line-height:${L}px;text-align:right;color:${gc};font-weight:${ln.focus ? 700 : 400}">${esc(ln.n)}</div>`;
      const body = ln.runs.map(([t, role]) => {
        const [c, b, it] = codeStyle(role);
        return `<span style="color:${color(c)};font-weight:${b ? 700 : 400};font-style:${it ? "italic" : "normal"}">${esc(t)}</span>`;
      }).join("");
      html += `<div class="rs-abs rs-pre" style="left:${gw + 14}px;top:${top + sh}px;right:0;height:${L}px;line-height:${L}px">${body || "&#8203;"}</div>`;
    });
    return html + "</div>";
  }

  function elBullets(el, page) {
    const size = +el.size || 20, sub = +el.subSize || 17, lh = +(el.lineHeight || 1.55);
    const [pt, pr, pb, pl] = padOf(el);
    const rows = bulletRows(el).map(([t, lvl, after, num]) => {
      const sz = lvl ? sub : size, hang0 = lvl ? 20 : 28, none = num && num.kind === "none", hang = none ? 0 : num ? numHang(num.label, sz, hang0) : hang0, marL = (lvl ? 48 : 28) - hang0 + hang;
      const base = color(lvl ? el.subColor || "on-surface-variant" : el.color || "on-surface");
      const sym = num && num.kind === "symbol";
      const bc = num && !sym ? base : color(lvl ? el.subColor || "on-surface-variant" : el.dot || "primary");  // 번호는 글 색(PowerPoint 자동 번호 기본), 기호는 글머리 색
      const pct = num ? (sym && BULLET_HEAVY.includes(num.label) ? 60 : 100) : lvl ? 100 : 60;
      const L = sz * lh;  // 글머리는 첫 줄 상자(높이 L)의 세로 가운데 - 글자 기준선에 두면 작은 ● 가 아래로 처진다. 글은 marL 에서 시작(내어쓰기 = 여백)
      const bu = none ? "" : `<span class="rs-bu" style="left:${marL - hang}px;width:${hang}px;height:${L}px;font-size:${pct}%;color:${bc}">${num ? esc(num.label) : lvl ? "–" : "●"}</span>`;
      return `<div class="rs-p" style="position:relative;top:${shift("body", sz, lh)}px;font-size:${sz}px;line-height:${L}px;padding-left:${marL}px;padding-bottom:${after}px">${bu}${spanRuns(t, page, base, false)}</div>`;
    }).join("");
    return `<div class="rs-box" style="padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:${JUST[el.valign || "top"]};font-family:${font("body")}">${rows}</div>`;
  }

  function lineBox(el) {
    // 선 요소의 x,y,w,h 를 끝점에서 다시 계산(편집 중 어긋남 방지)
    if (el.x1 == null) return el;
    return { ...el, x: Math.min(el.x1, el.x2), y: Math.min(el.y1, el.y2), w: Math.abs(el.x2 - el.x1), h: Math.abs(el.y2 - el.y1) };
  }

  const isLineType = (t) => t === "line" || t === "arrow" || t === "curve";
  /** 그림자 - true 면 기본(blur 6 · dx 2 · dy 3 · 검정 30%), 객체면 {blur, dx, dy, color, alpha}. export_pptx.apply_shadow 와 같은 기본값 */
  const SHADOW_DEF = { blur: 6, dx: 2, dy: 3, color: "#000000", alpha: 0.3 };
  function shadowSpec(v) { const o = typeof v === "object" && v ? v : {}; const s = { ...SHADOW_DEF, ...o }; s.color = color(s.color) || "#000000"; return s; }
  function shadowCss(v) { const s = shadowSpec(v); const h = s.color.replace("#", ""), r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16); return `;filter:drop-shadow(${s.dx}px ${s.dy}px ${s.blur / 2}px rgba(${r},${g},${b},${s.alpha}))`; }
  function renderElement(el0, page) {
    const el = (el0.type === "line" || el0.type === "arrow") ? lineBox(el0) : el0;
    let inner = "";
    switch (el.type) {
      case "rect": case "ellipse": case "pill": case "text": inner = elBox(el, page); break;
      case "image": inner = elImage(el); break;
      case "shape": inner = elShape(el, page); break;
      case "chart": inner = elChart(el, page); break;
      case "icon": inner = elIcon(el); break;
      case "group": inner = (el.children || []).map((c) => renderElement(c, page)).join(""); break;  // 자식은 묶음 상자 기준 좌표 - 묶음의 회전·뒤집기가 함께 적용된다
      case "line": case "arrow": inner = elLine(el); break;
      case "curve": inner = elCurve(el); break;
      case "table": case "plan-table": inner = elTable(el, page); break;
      case "code": inner = elCode(el); break;
      case "plan": inner = elPlan(el); break;
      case "bullets": inner = elBullets(el, page); break;
      default: inner = `<div class="rs-box" style="outline:1px dashed red">? ${esc(el.type)}</div>`;
    }
    const sh = el.shadow && !isLineType(el.type) ? shadowCss(el.shadow) : "";
    const xf = !isLineType(el.type) && (el.rot || el.flipH || el.flipV) ? `;transform:${el.rot ? `rotate(${+el.rot}deg) ` : ""}${el.flipH ? "scaleX(-1) " : ""}${el.flipV ? "scaleY(-1)" : ""};transform-origin:center center` : "";  // PPT 처럼 중심 기준 - 뒤집은 뒤 회전
    return `<div class="rs-el" data-id="${esc(el.id)}" data-type="${esc(el.type)}"${el.flipH && !isLineType(el.type) ? ' data-fliph="1"' : ""} style="left:${el.x}px;top:${el.y}px;width:${el.w}px;height:${el.h}px${xf}${sh}"${el.link ? ` data-link="${esc(String(el.link))}"` : ""}>${inner}</div>`;  // 좌우 뒤집기는 글은 읽히게(PowerPoint 와 같다) - css 의 [data-fliph] .rs-box
  }

  function sorted(els) {
    return (els || []).map((e, i) => [e, i]).sort((a, b) => ((a[0].z || 0) - (b[0].z || 0)) || (a[1] - b[1])).map((x) => x[0]);
  }

  /** 슬라이드 → HTML 문자열 (1280×720, 축소는 호출자가 transform 으로) */
  function renderSlide(slide, page) {
    const bg = color(slide.bg || "surface");
    FO = presetFonts(slide.fontPreset || DECK_FP);
    return `<div class="rs-slide" style="background:${bg}${FO ? `;font-family:${font("body")}` : ""}">${sorted(slide.elements).map((e) => renderElement(e, page)).join("")}</div>`;
  }

  /** 렌더러용 CSS (토큰 → CSS 변수 포함) */
  function css() {
    const vars = T ? Object.keys(T.colors).map((k) => `--${k}:${color(k)};`).join("") : "";
    return `:root{${vars}}
.rs-slide{position:relative;width:1280px;height:720px;overflow:hidden;font-family:${font("body")};color:${color("on-surface")};-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;font-kerning:none;font-variant-ligatures:none}
.rs-el{position:absolute;box-sizing:border-box}.rs-el[data-fliph] .rs-box{transform:scaleX(-1)}
.rs-box{position:absolute;inset:0;box-sizing:border-box;display:flex;flex-direction:column;overflow:visible}
.rs-p{white-space:pre-wrap;word-break:keep-all;overflow-wrap:break-word;margin:0;flex:none}
.rs-nw{display:flex;white-space:pre;align-items:center}
.rs-pre{white-space:pre}
.rs-code{position:absolute;inset:0;overflow:hidden}
.rs-abs{position:absolute;box-sizing:border-box}
.rs-bu{position:absolute;top:0;display:flex;align-items:center;justify-content:flex-start;text-indent:0;line-height:1;white-space:nowrap}
.rs-img{position:absolute;inset:0;width:100%;height:100%;display:block;user-select:none}
.rs-svg{position:absolute;overflow:visible;pointer-events:none}
.rs-cell{position:absolute;box-sizing:border-box;display:flex;align-items:center;padding:0 14px;overflow:visible}
.rs-cell>.rs-ct{white-space:pre-wrap;word-break:keep-all;flex:1}`;
  }

  const api = { setLazy, setDeckFonts, presetFonts, fontRole, setTokens, setLangs, langOf, color, colorAlpha, fillSpec, fillCss, radius, runs, plain, hlSQL, hlPython, codeLines, planRuns, tableGrid, tableMerges, chartAxis, chartData, chartFmt, comboLines, iconNames, bulletRows, bulletNum, numHang, markerNum, numLabel, shapePath, shapeNames, renderElement, renderSlide, css, esc, lineBox };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Render = api;
})(typeof window !== "undefined" ? window : globalThis);
